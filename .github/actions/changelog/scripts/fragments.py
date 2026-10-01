"""The fragment: what one contains, and how a directory of them is read.

A fragment is the only state this tool keeps. Once a release renders it into
CHANGELOG.md the fragment is deleted -- the rendered file is the record from
then on, and `git log -- .changes` still has every fragment that made it.
"""
import json
import re
import sys
from pathlib import Path

VALID_TYPES = {"feat", "fix", "chore", "revert"}

# Section order for the rendered file. chore has no row: documentation and
# maintenance are internal, so requiring a fragment would force authors to
# write text no customer reads.
CATEGORY = {"feat": "Features", "fix": "Fixes", "revert": "Reverts"}

# A pull request carrying the `minor` label renders here instead of its own
# type section: a consumer may have to change something to take the release.
# The label settles it -- the ABI check proposes a verdict, a maintainer can
# override it, and the release reads whatever the label ended up saying.
BREAKING_SECTION = "Possible Breaking Changes"

# Every accepted type either renders or is chore. Without this, narrowing the
# type set would silently drop entries from a release.
assert set(CATEGORY) | {"chore"} == VALID_TYPES

TITLE_RE = re.compile(
    r"^(feat|fix|chore|revert)(?:\([^)]+\))?:\s*(.+)$", re.IGNORECASE
)
# GitHub's Revert button generates `Revert "<original title> (#<n>)"`, which
# carries no `<type>:` prefix. Accepting it verbatim means a maintainer using
# the button never has to retitle; the author still writes the fragment, since
# only they can say WHY it was reverted.
REVERT_TITLE_RE = re.compile(r'^revert\s+"(.+)"\s*$', re.IGNORECASE)

REQUIRED = {"pr", "type", "summary"}
OPTIONAL = {"notes"}


def parse_title(title):
    title = title.strip()
    m = TITLE_RE.match(title)
    if m:
        return m.group(1).lower(), m.group(2).strip()
    m = REVERT_TITLE_RE.match(title)
    if m:
        return "revert", m.group(1).strip()
    return None, title


def validate_fragment(path):
    """Every problem with one fragment, as a list of messages.

    The schema is closed, so a misspelled field is an error rather than a value
    silently ignored. Text containing an HTML comment is refused because an entry
    is rendered inside a marked region and would break every later render. A
    revert must carry notes, since saying why is the only reason it earns an entry.
    Whether `pr` names a real pull request cannot be settled here -- this runs with
    no token and no network -- so only the placeholder is caught, and `check`
    asserts the fragment agrees with the pull request its trigger fired for.
    """
    errs = []
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError) as e:
        return [f"{path}: invalid JSON: {e}"]
    for k in sorted(REQUIRED - set(data)):
        errs.append(f"{path}: missing field: {k}")
    extra = sorted(set(data) - REQUIRED - OPTIONAL)
    if extra:
        errs.append(f"{path}: unexpected field(s): {', '.join(extra)}")
    if data.get("type") not in VALID_TYPES:
        errs.append(f"{path}: type must be one of {sorted(VALID_TYPES)}")
    s = data.get("summary")
    if not isinstance(s, str) or not s.strip():
        errs.append(f"{path}: summary must be non-empty string")
    pr = data.get("pr")
    if not isinstance(pr, int) or isinstance(pr, bool):
        errs.append(f"{path}: pr must be int")
    elif pr <= 0:
        errs.append(f"{path}: pr must be the real pull request number, not {pr}")
    for field in ("summary", "notes"):
        if isinstance(data.get(field), str) and "<!--" in data[field]:
            errs.append(f"{path}: {field} must not contain an HTML comment")
    notes = data.get("notes", "")
    if not isinstance(notes, str):
        errs.append(f"{path}: notes must be a string")
    elif data.get("type") == "revert" and not notes.strip():
        errs.append(f"{path}: a revert needs notes explaining why")
    return errs


def _err(msg):
    print(f"ERROR: {msg}", file=sys.stderr)


def load_preview(changes_dir):
    """Every valid fragment awaiting release. Invalid ones warn and drop out, so
    one bad fragment cannot stop the unreleased view from rendering."""
    d = Path(changes_dir) / "preview"
    out = []
    for path in sorted(d.glob("*.json")):
        errs = validate_fragment(path)
        if not errs:
            data = json.loads(path.read_text())
            if path.stem.isdigit() and data.get("pr") != int(path.stem):
                errs.append(f"{path}: pr {data.get('pr')!r} does not match the filename")
        if errs:
            for e in errs:
                print(f"WARN: skipping {e}", file=sys.stderr)
            continue
        out.append(data)
    return out


# ---------- commands ----------
#
# One `cmd_<verb>` per CLI subcommand, wired to its subparser in changelog.py.
# Each returns the process exit code rather than raising, so a caller in a shell
# step can branch on it.

def cmd_seed(args):
    """Write the template the bot comments with when a fragment is missing.

    The counterpart to validate_fragment, not a duplicate of it: this produces a
    fragment and validation consumes one. It exists for the two fields a comment
    cannot state generically -- the type, derived from the title prefix, and a
    revert's summary, derived from the Revert button's generated title -- whose
    shape is `Revert "<original title> (#N)"`, so neither the original type prefix
    nor its number belongs in the entry.

    It writes to --out, outside the tree the check reads, and the author copies
    it from the comment. So it writes without validating: the summary is a
    starting point they are expected to rewrite, and `check` refuses a bad one.
    """
    if args.pr <= 0:
        _err(f"--pr must be the real pull request number, not {args.pr}")
        return 2
    pr_type, summary = parse_title(args.title)
    if pr_type is None:
        pr_type = "chore"
    if pr_type == "revert":
        summary = re.sub(r"^(feat|fix|chore|revert)(\([^)]+\))?:\s*", "", summary,
                         flags=re.IGNORECASE)
        summary = re.sub(r"\s*\(#\d+\)\s*$", "", summary)
        if not summary.lower().startswith("revert"):
            summary = f"Reverted {summary}"
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(
        {"pr": args.pr, "type": pr_type, "summary": summary, "notes": ""},
        indent=2) + "\n")
    print(str(out))
    return 0
