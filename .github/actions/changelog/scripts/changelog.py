#!/usr/bin/env python3
"""Changelog fragment tooling: seed, validate, check, render, rollup.

Fragments (`.changes/preview/<pr>.json`) are the source of truth. CHANGELOG.md
is fully regenerated from them — nothing appends manually.

Directory layout on the docs branch (see README for the two-branch model):
  .changes/
  ├── preview/                        fragments awaiting the next release
  ├── latest/<version>/               per-patch dirs of the active minor line
  ├── <M>.<N>.x/                      frozen previous minor line + snapshot
  └── ...
"""
import argparse
import json
import re
import sys
from pathlib import Path

VALID_TYPES = {"feat", "fix", "chore", "revert"}
CATEGORIES = ["Features", "Fixes", "Reverts", "Maintenance"]
# chore is internal-only: it renders nowhere, so requiring a fragment would
# force authors to write invisible text.
HIDDEN_TYPES = {"chore"}
FRAGMENT_EXEMPT_TYPES = {"chore"}

TITLE_RE = re.compile(
    r"^(feat|fix|chore|revert)(?:\([^)]+\))?:\s*(.+)$", re.IGNORECASE
)
# GitHub's Revert button generates `Revert "<original title> (#<n>)"`, which
# carries no `<type>:` prefix. Accepting it verbatim means a maintainer using
# the button never has to retitle; the author still writes the fragment, since
# only they can say WHY it was reverted.
REVERT_TITLE_RE = re.compile(r'^revert\s+"(.+)"\s*$', re.IGNORECASE)
SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
MINOR_LINE_RE = re.compile(r"^(\d+)\.(\d+)\.x$")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ---------- parsing / schema ----------

def parse_title(title):
    title = title.strip()
    m = TITLE_RE.match(title)
    if m:
        return m.group(1).lower(), m.group(2).strip()
    m = REVERT_TITLE_RE.match(title)
    if m:
        return "revert", m.group(1).strip()
    return None, title


REQUIRED_FRAGMENT = {"pr", "type", "summary", "url"}


def validate_fragment(path):
    errs = []
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError) as e:
        return [f"{path}: invalid JSON: {e}"]
    for k in sorted(REQUIRED_FRAGMENT - set(data)):
        errs.append(f"{path}: missing field: {k}")
    if data.get("type") not in VALID_TYPES:
        errs.append(f"{path}: type must be one of {sorted(VALID_TYPES)}")
    s = data.get("summary")
    if not isinstance(s, str) or not s.strip():
        errs.append(f"{path}: summary must be non-empty string")
    if not isinstance(data.get("pr"), int):
        errs.append(f"{path}: pr must be int")
    notes = data.get("notes", "")
    if not isinstance(notes, str):
        errs.append(f"{path}: notes must be a string")
    return errs


META_REQUIRED = {"version", "date"}


def validate_meta(path):
    errs = []
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError) as e:
        return [f"{path}: invalid JSON: {e}"]
    for k in sorted(META_REQUIRED - set(data)):
        errs.append(f"{path}: missing field: {k}")
    if not SEMVER_RE.match(str(data.get("version", ""))):
        errs.append(f"{path}: version must be x.y.z")
    if not ISO_DATE_RE.match(str(data.get("date", ""))):
        errs.append(f"{path}: date must be YYYY-MM-DD")
    return errs


def parse_semver(s):
    m = SEMVER_RE.match(s)
    if not m:
        raise ValueError(f"not a semver x.y.z: {s!r}")
    return tuple(int(g) for g in m.groups())


# ---------- render primitives ----------

def categorize(frag):
    return {
        "feat": "Features",
        "fix": "Fixes",
        "revert": "Reverts",
        "chore": "Maintenance",
    }[frag["type"]]


SENTENCE_END = (".", "!", "?")


def render_entry(frag):
    summary = frag["summary"].strip()
    if not summary.endswith(SENTENCE_END):
        summary += "."
    line = f"- {summary} (#{frag['pr']})"
    if frag.get("notes"):
        indented = "\n  ".join(frag["notes"].splitlines())
        line += "\n  " + indented
    return line


def render_grouped(fragments):
    """Render visible fragments as `### Category` sections, or '' if none are."""
    grouped = {c: [] for c in CATEGORIES}
    for f in fragments:
        if f["type"] not in HIDDEN_TYPES:
            grouped[categorize(f)].append(f)
    lines = []
    for cat in CATEGORIES:
        entries = sorted(grouped[cat], key=lambda f: f["pr"])
        if not entries:
            continue
        lines.append(f"### {cat}")
        lines.extend(render_entry(e) for e in entries)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n" if lines else ""


# ---------- fragment / release IO ----------

def _safe_load_json(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError) as e:
        print(f"WARN: skipping {path}: {e}", file=sys.stderr)
        return None


def _load_valid_fragment(path):
    data = _safe_load_json(path)
    if data is None:
        return None
    errs = validate_fragment(path)
    stem = Path(path).stem
    if stem.isdigit() and data.get("pr") != int(stem):
        errs.append(f"{path}: pr {data.get('pr')!r} does not match the filename")
    if errs:
        for e in errs:
            print(f"WARN: skipping {e}", file=sys.stderr)
        return None
    return data


def load_preview(changes_dir):
    d = Path(changes_dir) / "preview"
    if not d.exists():
        return []
    out = []
    for f in sorted(d.glob("*.json")):
        data = _load_valid_fragment(f)
        if data is not None:
            out.append(data)
    return out


def load_release(release_dir):
    """Return (meta, [fragments]) for a single release directory."""
    release_dir = Path(release_dir)
    meta_path = release_dir / "_meta.json"
    if not meta_path.exists():
        return None, []
    meta_errs = validate_meta(meta_path)
    if meta_errs:
        for e in meta_errs:
            print(f"WARN: skipping release ({e})", file=sys.stderr)
        return None, []
    meta = json.loads(meta_path.read_text())
    frags = []
    for f in sorted(release_dir.glob("*.json")):
        if f.name == "_meta.json":
            continue
        data = _load_valid_fragment(f)
        if data is not None:
            frags.append(data)
    return meta, frags


def list_releases_in(line_dir):
    """List release dirs under a minor-line dir, semver-desc."""
    line_dir = Path(line_dir)
    if not line_dir.exists():
        return []
    dirs = [d for d in line_dir.iterdir() if d.is_dir() and SEMVER_RE.match(d.name)]
    return sorted(dirs, key=lambda d: parse_semver(d.name), reverse=True)


def render_release_section(meta, fragments):
    header = f"## [{meta['version']}] — {meta['date']}\n"
    if meta.get("highlights"):
        header += f"Highlights: {meta['highlights']}\n\n"
    else:
        header += "\n"
    return header + render_grouped(fragments)


def render_root_changelog(changes_dir):
    """Regenerate the whole root CHANGELOG.md content from preview/ + latest/."""
    body = [
        "# Changelog",
        "",
        "## [Preview]",
        "",
        (render_grouped(load_preview(changes_dir)) or "_Nothing yet._\n").rstrip(),
        "",
    ]
    latest = Path(changes_dir) / "latest"
    for rel_dir in list_releases_in(latest):
        meta, frags = load_release(rel_dir)
        if meta is None:
            continue
        body.append(render_release_section(meta, frags).rstrip())
        body.append("")
    return "\n".join(body).rstrip() + "\n"


def render_frozen_line(line_dir):
    """Render a self-contained CHANGELOG.md for a frozen minor line."""
    releases = list_releases_in(line_dir)
    if not releases:
        return "# Changelog\n"
    M, N, _ = parse_semver(releases[0].name)
    body = [f"# Changelog — {M}.{N}.x", ""]
    for rel_dir in releases:
        meta, frags = load_release(rel_dir)
        if meta is None:
            continue
        body.append(render_release_section(meta, frags).rstrip())
        body.append("")
    return "\n".join(body).rstrip() + "\n"


# ---------- commands ----------

def cmd_seed(args):
    typ, summary = parse_title(args.title)
    if typ is None:
        typ = "chore"
        summary = args.title.strip()
    frag = {
        "pr": args.pr,
        "type": typ,
        "summary": summary,
        "url": args.url,
        "notes": "",
    }
    out = Path(args.out) if args.out else Path(args.changes_dir) / "preview" / f"{args.pr}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() and not args.force:
        # Non-zero, so a caller cannot mistake "declined" for "wrote it".
        print(f"exists (use --force to overwrite): {out}", file=sys.stderr)
        return 1
    out.write_text(json.dumps(frag, indent=2) + "\n")
    print(str(out))
    return 0


def cmd_validate(args):
    target = Path(args.target)
    if not target.exists():
        _err(f"{target}: no such file or directory")
        return 2
    files = [target] if target.is_file() else sorted(target.glob("*.json"))
    if not files:
        print(f"no fragments found under {target}")
        return 0
    errs = []
    for f in files:
        errs.extend(validate_fragment(f))
    if errs:
        for e in errs:
            print(e, file=sys.stderr)
        return 1
    print(f"OK: {len(files)} fragment(s)")
    return 0


def parse_changed_paths(path, prefix):
    """Read `status<TAB>path` lines, keeping only entries under `prefix`."""
    out = []
    for line in Path(path).read_text().splitlines():
        status, _, p = line.strip().partition("\t")
        p = p.strip()
        if p.startswith(f"{prefix}/"):
            out.append((status.strip(), p))
    return out


def check_fragment_changes(args, typ, reason):
    """Assert the PR's changes under `prefix` are exactly one new fragment.

    Returns an exit code to stop on, or None to carry on with the usual checks.
    """
    prefix = args.changes_prefix.rstrip("/")
    expected = f"{prefix}/preview/{args.pr}.json"
    entries = parse_changed_paths(args.changed_paths_file, prefix)

    if not entries:
        # Nothing under .changes/ at all -- the normal "author forgot" case,
        # which the fragment check below reports and which earns a template.
        return None

    wrong = [(st, p) for st, p in entries if p != expected]
    if wrong:
        listed = "\n".join(f"         {st:<10} {p}" for st, p in wrong)
        print(
            f"ERROR: a `{typ}` change may only add its own changelog fragment.\n"
            f"       expected exactly one new file:\n"
            f"         added      {expected}\n"
            f"       but this pull request also changes:\n{listed}\n"
            f"       A fragment named for another pull request renders under that\n"
            f"       number; one at another path renders nowhere.",
            file=sys.stderr,
        )
        reason("stray-fragment")
        return 1

    status = entries[0][0]
    if status and status != "added":
        print(
            f"ERROR: {expected} is `{status}` in this pull request, not `added`.\n"
            f"       That path already exists on the base branch, so this pull\n"
            f"       request is rewriting a released or in-flight entry rather than\n"
            f"       contributing its own. Move the change to a new fragment.",
            file=sys.stderr,
        )
        reason("modified-fragment")
        return 1

    return None


def cmd_check(args):
    """CI gate. Exit 0 pass, 1 author-fixable, 2 caller error.

    Two independent assertions:
      * the PR title follows the convention, so a type can be derived at all;
      * a fragment exists and agrees with that type -- unless the type is
        exempt (chore), or the author is a bot we waive.
    """
    title = (args.title or "").strip()
    frag = Path(args.changes_dir) / "preview" / f"{args.pr}.json"

    # A single machine-readable reason on stdout, so a caller can tell an
    # author who does not know the convention (missing-fragment -> show them a
    # template) from one who does (everything else -> just the diagnostic).
    def reason(tag):
        print(f"CHANGELOG_CHECK_REASON::{tag}")

    if args.bot_author:
        print(f"OK: #{args.pr} is authored by a bot ({args.bot_author}); "
              "title convention and changelog fragment both waived")
        reason("waived-bot")
        return 0

    if not title:
        print("ERROR: --title is required to derive the change type", file=sys.stderr)
        return 2

    typ, _summary = parse_title(title)
    if typ is None:
        print(
            f'ERROR: PR title does not follow the convention: "{title}"\n'
            f"       expected `<type>: <summary>` with type one of "
            f"{sorted(VALID_TYPES)}, an optional scope such as `chore(ci):`,\n"
            f'       or the Revert button\'s `Revert "<original title>"`.',
            file=sys.stderr,
        )
        reason("bad-title")
        return 1

    if typ in FRAGMENT_EXEMPT_TYPES:
        print(f"OK: #{args.pr} is a `{typ}` change; no changelog fragment required")
        reason("exempt-type")
        return 0

    if args.changed_paths_file:
        rc = check_fragment_changes(args, typ, reason)
        if rc is not None:
            return rc

    if not frag.exists():
        print(
            f"ERROR: no changelog fragment for PR #{args.pr}.\n"
            f"       expected: {frag}\n"
            f"       a `{typ}` change is customer-visible, so it needs an entry.\n"
            f"       commit that file with this pull request -- the bot comments a\n"
            f"       ready-to-paste template -- or apply the `skip-changelog` label\n"
            f"       for CI-only / pure-infra changes.",
            file=sys.stderr,
        )
        reason("missing-fragment")
        return 1

    errs = validate_fragment(frag)
    if errs:
        for e in errs:
            print(e, file=sys.stderr)
        reason("invalid-fragment")
        return 1

    data = json.loads(frag.read_text())
    declared_pr = data.get("pr")
    if declared_pr != args.pr:
        print(
            f"ERROR: {frag} declares pr={declared_pr} but this PR is #{args.pr}",
            file=sys.stderr,
        )
        reason("pr-mismatch")
        return 1

    if data.get("type") != typ:
        print(
            f'ERROR: type mismatch. The PR title says `{typ}` but {frag} says '
            f'`{data.get("type")}`.\n'
            f"       Fix whichever is wrong -- they must agree.",
            file=sys.stderr,
        )
        reason("type-mismatch")
        return 1

    print(f"OK: #{args.pr} title is `{typ}` and its fragment is present and valid")
    reason("ok")
    return 0


def cmd_render(args):
    text = render_root_changelog(args.changes_dir)
    Path(args.changelog).write_text(text)
    print(f"rendered → {args.changelog}")
    return 0


def _latest_version_in_line(line_dir):
    """Highest semver tuple in a line dir, or None if it holds no release."""
    releases = list_releases_in(line_dir)
    return parse_semver(releases[0].name) if releases else None


def _current_line_minor(latest_dir):
    """(M, N) of the active latest/ line, or None if it holds no release."""
    v = _latest_version_in_line(latest_dir)
    return v[:2] if v else None


def _frozen_lines(changes_dir):
    """Return frozen minor-line directories (e.g. 0.29.x/), semver-desc by (M, N)."""
    changes_dir = Path(changes_dir)
    if not changes_dir.exists():
        return []
    lines = [d for d in changes_dir.iterdir() if d.is_dir() and MINOR_LINE_RE.match(d.name)]
    return sorted(
        lines,
        key=lambda d: tuple(int(x) for x in MINOR_LINE_RE.match(d.name).groups()),
        reverse=True,
    )


def _err(msg):
    print(f"ERROR: {msg}", file=sys.stderr)


def _check_version_is_next(changes, new_tuple, new_version):
    """Error string if new_version is not strictly newer than every release so
    far, or belongs to a minor line that has already been frozen."""
    highest = _latest_version_in_line(changes / "latest")
    if highest is not None and new_tuple <= highest:
        return (
            f"{new_version} is not newer than the latest released "
            f"{'.'.join(str(x) for x in highest)} in latest/"
        )
    for frozen in _frozen_lines(changes):
        # Reopening a frozen line would split it: its snapshot is already
        # written and the root changelog only ever renders latest/.
        if new_tuple[:2] == tuple(int(x) for x in MINOR_LINE_RE.match(frozen.name).groups()):
            return f"{new_version} belongs to {frozen.name}/, which is already frozen"
        highest = _latest_version_in_line(frozen)
        if highest is not None and new_tuple <= highest:
            return (
                f"{new_version} is not newer than frozen line's latest "
                f"{'.'.join(str(x) for x in highest)} in {frozen.name}/"
            )
    return None


def _infer_bump(current_minor, new_tuple):
    """The bump the version itself implies. minor and major both freeze the
    current line and differ only in the message."""
    M_new, N_new, _ = new_tuple
    if current_minor is None:
        return "minor"
    if (M_new, N_new) == current_minor:
        return "patch"
    if M_new != current_minor[0]:
        return "major"
    return "minor"


def _freeze_current_line(changes, latest, current_minor):
    """Rename latest/ → M.N.x/, snapshot its CHANGELOG.md, reopen an empty
    latest/. Not atomic; a crash between the two is caught next run by
    _check_no_half_freeze."""
    M_old, N_old = current_minor
    frozen_dir = changes / f"{M_old}.{N_old}.x"
    if frozen_dir.exists():
        return f"freeze target {frozen_dir} already exists"
    latest.rename(frozen_dir)
    (frozen_dir / "CHANGELOG.md").write_text(render_frozen_line(frozen_dir))
    latest.mkdir(parents=True, exist_ok=True)
    return None


def _check_no_half_freeze(changes):
    """Detect a frozen minor-line dir that has no CHANGELOG.md snapshot yet."""
    for line in _frozen_lines(changes):
        if not (line / "CHANGELOG.md").exists() and list_releases_in(line):
            return (
                f"half-frozen state detected: {line}/ has releases but no CHANGELOG.md. "
                f"Re-run: python3 changelog.py freeze-snapshot --line {line.name} "
                f"(or manually write {line}/CHANGELOG.md then retry rollup)"
            )
    return None


def _open_release_dir(changes, latest, new_version, date, highlights):
    """Create latest/<version>/ with _meta.json and move preview fragments in."""
    release_dir = latest / new_version
    release_dir.mkdir(parents=True)
    meta = {"version": new_version, "date": date, "highlights": highlights or ""}
    (release_dir / "_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    for f in (changes / "preview").glob("*.json"):
        f.rename(release_dir / f.name)


def cmd_rollup(args):
    """Two flows: patch accretes into latest/; minor/major freezes latest/ → M.N.x/."""
    changes = Path(args.changes_dir)
    latest = changes / "latest"
    latest.mkdir(parents=True, exist_ok=True)

    half = _check_no_half_freeze(changes)
    if half:
        _err(half)
        return 2

    preview_dir = changes / "preview"
    on_disk = sorted(preview_dir.glob("*.json")) if preview_dir.exists() else []
    if not on_disk:
        print("nothing to roll up (preview/ empty)", file=sys.stderr)
        return 1
    preview = load_preview(changes)
    if len(preview) != len(on_disk):
        # Releasing anyway would move the rejected files into the release
        # directory, where they render nowhere and are never looked at again.
        _err(f"{len(on_disk) - len(preview)} of {len(on_disk)} fragment(s) in "
             f"{preview_dir} are invalid (see the warnings above); fix them first")
        return 2

    try:
        new_tuple = parse_semver(args.version)
    except ValueError as e:
        _err(str(e))
        return 2

    if not ISO_DATE_RE.match(args.date):
        _err(f"--date must be YYYY-MM-DD, got {args.date!r}")
        return 2

    err = _check_version_is_next(changes, new_tuple, args.version)
    if err:
        _err(err)
        return 2

    current = _current_line_minor(latest)
    bump = _infer_bump(current, new_tuple)
    if args.bump and args.bump != bump:
        # The version decides; an explicit --bump is only a cross-check. Acting
        # on a contradictory one freezes the active line under its own name,
        # which wedges every later minor rollup with no way back.
        _err(f"--bump {args.bump} contradicts --version {args.version}, which is a "
             f"{bump} bump relative to latest/")
        return 2

    if bump in ("minor", "major") and current is not None:
        err = _freeze_current_line(changes, latest, current)
        if err:
            _err(err)
            return 2

    _open_release_dir(changes, latest, args.version, args.date, args.highlights)
    Path(args.changelog).write_text(render_root_changelog(changes))
    print(f"rolled up {len(preview)} fragment(s) into {args.version} ({bump})")
    return 0


def cmd_freeze_snapshot(args):
    """Recovery: (re-)write the CHANGELOG.md snapshot inside a frozen minor line."""
    line = Path(args.changes_dir) / args.line
    if not line.exists() or not MINOR_LINE_RE.match(line.name):
        _err(f"{line}: not a frozen minor-line directory (expected name like 0.29.x)")
        return 2
    (line / "CHANGELOG.md").write_text(render_frozen_line(line))
    print(f"wrote {line / 'CHANGELOG.md'}")
    return 0


def cmd_list(args):
    """Debugging aid: show what's staged and what's released in the current line."""
    changes = Path(args.changes_dir)
    unrel = load_preview(changes)
    print(f"[preview]  {len(unrel)} fragment(s)")
    for f in unrel:
        print(f"  #{f['pr']:<6} {f['type']:<6} {f['summary']}")
    latest = changes / "latest"
    print("\n[latest/]")
    for rel_dir in list_releases_in(latest):
        meta, frags = load_release(rel_dir)
        v = meta["version"] if meta else rel_dir.name
        d = meta["date"] if meta else "?"
        print(f"  {v}  {d}  ({len(frags)} fragment(s))")
    print("\n[frozen lines]")
    for line in _frozen_lines(changes):
        releases = list_releases_in(line)
        print(f"  {line.name}  ({len(releases)} release(s))")
    return 0


# ---------- CLI ----------

def main(argv=None):
    p = argparse.ArgumentParser(prog="changelog")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("seed", help="create a fragment for a PR (usually via new-change helper)")
    s.add_argument("--pr", type=int, required=True)
    s.add_argument("--title", required=True)
    s.add_argument("--url", required=True)
    s.add_argument("--changes-dir", default=".changes")
    s.add_argument("--out")
    s.add_argument("--force", action="store_true")
    s.set_defaults(func=cmd_seed)

    v = sub.add_parser("validate", help="validate a fragment file or directory")
    v.add_argument("target")
    v.set_defaults(func=cmd_validate)

    c = sub.add_parser("check", help="CI: assert the PR title and its fragment are valid")
    c.add_argument("--pr", type=int, required=True)
    c.add_argument("--title", default="", help="PR title; the change type is derived from it")
    c.add_argument("--bot-author", default="",
                   help="login of the PR author when it is a bot; waives both checks")
    c.add_argument("--changes-dir", default=".changes")
    c.add_argument("--changed-paths-file", default="",
                   help="file of `status<TAB>path` lines for the PR's changes under .changes/")
    c.add_argument("--changes-prefix", default=".changes",
                   help="repo-relative changes directory, for matching changed paths")
    c.set_defaults(func=cmd_check)

    r = sub.add_parser("render", help="regenerate root CHANGELOG.md from preview/ + latest/")
    r.add_argument("--changes-dir", default=".changes")
    r.add_argument("--changelog", default="CHANGELOG.md")
    r.set_defaults(func=cmd_render)

    u = sub.add_parser("rollup",
                       help="cut a release: patch accretes into latest/; minor/major freezes it")
    u.add_argument("--version", required=True)
    u.add_argument("--date", required=True)
    u.add_argument("--highlights", default="")
    u.add_argument("--bump", choices=["patch", "minor", "major"],
                   help="Optional; inferred from --version and current latest/ if omitted.")
    u.add_argument("--changes-dir", default=".changes")
    u.add_argument("--changelog", default="CHANGELOG.md")
    u.set_defaults(func=cmd_rollup)

    ls = sub.add_parser("list", help="show preview, latest/, and frozen lines")
    ls.add_argument("--changes-dir", default=".changes")
    ls.set_defaults(func=cmd_list)

    fs = sub.add_parser("freeze-snapshot",
                        help="recovery: re-render a frozen line's CHANGELOG.md")
    fs.add_argument("--line", required=True, help="frozen minor-line dir name, e.g. 0.29.x")
    fs.add_argument("--changes-dir", default=".changes")
    fs.set_defaults(func=cmd_freeze_snapshot)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
