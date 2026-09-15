#!/usr/bin/env python3
"""Changelog fragment tooling: seed, validate, check, render, rollup, revert.

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

VALID_TYPES = {"feat", "fix", "doc", "chore", "revert"}
CATEGORIES = ["Features", "Fixes", "Docs", "Maintenance"]
HIDDEN_TYPES_CUSTOMER = {"chore"}

PREVIEW_START = "<!-- changelog:preview:start -->"
PREVIEW_END = "<!-- changelog:preview:end -->"

TITLE_RE = re.compile(
    r"^(feat|fix|docs?|chore|revert)(?:\([^)]+\))?:\s*(.+)$", re.IGNORECASE
)
SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
MINOR_LINE_RE = re.compile(r"^(\d+)\.(\d+)\.x$")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ---------- parsing / schema ----------

def parse_title(title):
    m = TITLE_RE.match(title.strip())
    if not m:
        return None, title.strip()
    t = m.group(1).lower()
    if t == "docs":
        t = "doc"
    return t, m.group(2).strip()


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
        "doc": "Docs",
        "chore": "Maintenance",
        "revert": "Maintenance",
    }.get(frag["type"], "Maintenance")


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


def render_grouped(fragments, hidden_types=HIDDEN_TYPES_CUSTOMER):
    grouped = {c: [] for c in CATEGORIES}
    for f in fragments:
        if f["type"] in hidden_types:
            continue
        grouped[categorize(f)].append(f)
    lines = []
    for cat in CATEGORIES:
        entries = sorted(grouped[cat], key=lambda f: f["pr"])
        if not entries:
            continue
        lines.append(f"### {cat}")
        for e in entries:
            lines.append(render_entry(e))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n" if lines else "_Nothing yet._\n"


# ---------- fragment / release IO ----------

def _safe_load_json(path):
    """Load a JSON file; on parse failure emit a warning and return None."""
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError) as e:
        print(f"WARN: skipping {path}: {e}", file=sys.stderr)
        return None


def _load_valid_fragment(path):
    """Load a fragment JSON; skip with warning if malformed or schema-invalid."""
    data = _safe_load_json(path)
    if data is None:
        return None
    errs = validate_fragment(path)
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


def render_release_section(meta, fragments, hidden_types=HIDDEN_TYPES_CUSTOMER):
    header = f"## [{meta['version']}] — {meta['date']}\n"
    if meta.get("highlights"):
        header += f"Highlights: {meta['highlights']}\n\n"
    else:
        header += "\n"
    return header + render_grouped(fragments, hidden_types=hidden_types)


def render_root_changelog(changes_dir):
    """Regenerate the whole root CHANGELOG.md content from preview/ + latest/."""
    preview = load_preview(changes_dir)
    preview_block = render_grouped(preview)
    body = [
        "# Changelog",
        "",
        PREVIEW_START,
        "## [Preview]",
        "",
        preview_block.rstrip(),
        PREVIEW_END,
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
    line_dir = Path(line_dir)
    # Derive minor label from constituent versions (they should all share major.minor).
    releases = list_releases_in(line_dir)
    if not releases:
        return "# Changelog\n"
    first_version = releases[0].name
    M, N, _ = parse_semver(first_version)
    body = [f"# Changelog — {M}.{N}.x", ""]
    for rel_dir in releases:
        meta, frags = load_release(rel_dir)
        if meta is None:
            continue
        body.append(render_release_section(meta, frags, hidden_types=set()).rstrip())
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
        print(f"exists (use --force to overwrite): {out}", file=sys.stderr)
        return 0
    out.write_text(json.dumps(frag, indent=2) + "\n")
    print(str(out))
    return 0


def cmd_validate(args):
    target = Path(args.target)
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


def cmd_check(args):
    frag = Path(args.changes_dir) / "preview" / f"{args.pr}.json"
    if not frag.exists():
        print(
            f"ERROR: no changelog fragment for PR #{args.pr}.\n"
            f"       expected: {frag}\n"
            f"       run `.github/actions/changelog/scripts/new-change` locally and commit the file,\n"
            f"       or apply the `skip-changelog` label for CI-only / pure-infra PRs.",
            file=sys.stderr,
        )
        return 1
    errs = validate_fragment(frag)
    if errs:
        for e in errs:
            print(e, file=sys.stderr)
        return 1
    declared_pr = json.loads(frag.read_text()).get("pr")
    if declared_pr != args.pr:
        print(
            f"ERROR: {frag} declares pr={declared_pr} but this PR is #{args.pr}",
            file=sys.stderr,
        )
        return 1
    print(f"OK: fragment for #{args.pr} is present and valid")
    return 0


def cmd_render(args):
    text = render_root_changelog(args.changes_dir)
    Path(args.changelog).write_text(text)
    print(f"rendered → {args.changelog}")
    return 0


def _current_line_minor(latest_dir):
    """Return (M, N) of the latest/ line by inspecting its release dirs."""
    releases = list_releases_in(latest_dir)
    if not releases:
        return None
    M, N, _ = parse_semver(releases[0].name)
    return M, N


def _latest_version_in_line(line_dir):
    """Return the highest semver tuple in a line dir, or None if empty."""
    releases = list_releases_in(line_dir)
    if not releases:
        return None
    return parse_semver(releases[0].name)


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


def _check_no_downgrade(changes, latest, new_tuple, new_version):
    """Return an error string if new_version is not strictly newer than every prior release."""
    highest = _latest_version_in_line(latest)
    if highest is not None and new_tuple <= highest:
        return (
            f"{new_version} is not newer than the latest released "
            f"{'.'.join(str(x) for x in highest)} in latest/"
        )
    for frozen in _frozen_lines(changes):
        highest = _latest_version_in_line(frozen)
        if highest is not None and new_tuple <= highest:
            return (
                f"{new_version} is not newer than frozen line's latest "
                f"{'.'.join(str(x) for x in highest)} in {frozen.name}/"
            )
    return None


def _infer_bump(current_minor, new_tuple):
    M_new, N_new, _ = new_tuple
    if current_minor is None:
        return "minor"
    if (M_new, N_new) == current_minor:
        return "patch"
    if M_new != current_minor[0]:
        return "major"
    return "minor"


def _freeze_current_line(changes, latest, current_minor):
    """Rename latest/ → M.N.x/, write a frozen CHANGELOG.md, recreate empty latest/.

    The two-step rename + write is not atomic. If interrupted between them,
    the frozen directory exists without a CHANGELOG.md snapshot. That
    half-state is detected by _check_no_half_freeze before rollup starts
    (see cmd_rollup); this function assumes it starts clean.
    """
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
    if release_dir.exists():
        return None, f"release dir {release_dir} already exists"
    release_dir.mkdir(parents=True)
    meta = {"version": new_version, "date": date, "highlights": highlights or ""}
    (release_dir / "_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    for f in (changes / "preview").glob("*.json"):
        f.rename(release_dir / f.name)
    return release_dir, None


def cmd_rollup(args):
    """Two flows: patch accretes into latest/; minor/major freezes latest/ → M.N.x/."""
    changes = Path(args.changes_dir)
    latest = changes / "latest"
    latest.mkdir(parents=True, exist_ok=True)

    half = _check_no_half_freeze(changes)
    if half:
        _err(half)
        return 2

    preview = load_preview(changes)
    if not preview:
        print("nothing to roll up (preview/ empty)", file=sys.stderr)
        return 1

    try:
        new_tuple = parse_semver(args.version)
    except ValueError as e:
        _err(str(e))
        return 2

    if not ISO_DATE_RE.match(args.date):
        _err(f"--date must be YYYY-MM-DD, got {args.date!r}")
        return 2

    err = _check_no_downgrade(changes, latest, new_tuple, args.version)
    if err:
        _err(err)
        return 2

    current = _current_line_minor(latest)
    bump = args.bump or _infer_bump(current, new_tuple)
    if bump not in ("patch", "minor", "major"):
        _err(f"--bump must be patch|minor|major, got {bump!r}")
        return 2

    M_new, N_new, _ = new_tuple
    if bump == "patch" and current is not None and (M_new, N_new) != current:
        _err(
            f"--bump patch requires {args.version} to share a minor line with "
            f"current {'.'.join(str(x) for x in current)}"
        )
        return 2

    if bump in ("minor", "major") and current is not None:
        err = _freeze_current_line(changes, latest, current)
        if err:
            _err(err)
            return 2

    _, err = _open_release_dir(changes, latest, args.version, args.date, args.highlights)
    if err:
        _err(err)
        return 2

    Path(args.changelog).write_text(render_root_changelog(changes))
    print(f"rolled up {len(preview)} fragment(s) into {args.version} ({bump})")
    return 0


def _find_original_fragment(changes_dir, pr):
    """Locate a merged PR's fragment across preview/, latest/, and frozen lines."""
    changes = Path(changes_dir)
    candidates = [changes / "preview" / f"{pr}.json"]
    latest = changes / "latest"
    if latest.exists():
        for rel_dir in list_releases_in(latest):
            candidates.append(rel_dir / f"{pr}.json")
    for line_dir in _frozen_lines(changes):
        for rel_dir in list_releases_in(line_dir):
            candidates.append(rel_dir / f"{pr}.json")
    for c in candidates:
        if c.exists():
            return c
    return None


def cmd_revert(args):
    orig_summary = ""
    orig_path = _find_original_fragment(args.changes_dir, args.original_pr)
    if orig_path is not None:
        data = _safe_load_json(orig_path)
        if data:
            orig_summary = (data.get("summary") or "").strip()
    frag = {
        "pr": args.revert_pr,
        "type": "revert",
        "summary": f"Revert #{args.original_pr}"
        + (f": {orig_summary}" if orig_summary else ""),
        "url": args.url,
        "notes": f"Reverts #{args.original_pr}.",
    }
    out = Path(args.changes_dir) / "preview" / f"{args.revert_pr}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(frag, indent=2) + "\n")
    print(str(out))
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

    c = sub.add_parser("check", help="CI: assert a valid fragment exists for a given PR")
    c.add_argument("--pr", type=int, required=True)
    c.add_argument("--changes-dir", default=".changes")
    c.set_defaults(func=cmd_check)

    r = sub.add_parser("render", help="regenerate root CHANGELOG.md from preview/ + latest/")
    r.add_argument("--changes-dir", default=".changes")
    r.add_argument("--changelog", default="CHANGELOG.md")
    r.set_defaults(func=cmd_render)

    u = sub.add_parser("rollup", help="cut a release: patch accretes into latest/; minor/major freezes latest/ → M.N.x/")
    u.add_argument("--version", required=True)
    u.add_argument("--date", required=True)
    u.add_argument("--highlights", default="")
    u.add_argument("--bump", choices=["patch", "minor", "major"],
                   help="Optional; inferred from --version and current latest/ if omitted.")
    u.add_argument("--changes-dir", default=".changes")
    u.add_argument("--changelog", default="CHANGELOG.md")
    u.set_defaults(func=cmd_rollup)

    rv = sub.add_parser("revert", help="create a revert fragment (never deletes original)")
    rv.add_argument("--original-pr", type=int, required=True)
    rv.add_argument("--revert-pr", type=int, required=True)
    rv.add_argument("--url", required=True)
    rv.add_argument("--changes-dir", default=".changes")
    rv.set_defaults(func=cmd_revert)

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
