"""Cutting a release: render the fragments awaiting one, then drop them.

No version guard. The version comes from the release job, and a mistake in the
rendered file is fixed by a chore -- the file is markdown, not a database.
"""
import re
from pathlib import Path

from fragments import _err, load_preview
from render import HEADING, PR_PREFIX, UNRELEASED_END, render_grouped, set_unreleased

ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
VERSION_RE = re.compile(r"(\d+)\.(\d+)\.\d+")
EARLIER = "## Earlier releases"


def insert_section(text, section):
    """Add a release's section to the file, directly below the unreleased block.

    Every release does this and nothing else does. Releases therefore accumulate
    newest-first, and the ones already published are never rewritten.
    """
    head, _, tail = text.partition(UNRELEASED_END)
    return f"{head}{UNRELEASED_END}\n\n{section.rstrip()}\n\n{tail.lstrip()}".rstrip() + "\n"


def archive_closed_line(text, changes, line):
    """Move a closed minor version line's releases out to .changes/<line>.md.

    Only a release opening a new minor line does this, so the root carries just the
    line being released into. Everything below the unreleased block *is* the closing
    line, so nothing needs reading to decide what belongs. The root's own list of
    archives is dropped rather than carried along, and every link gains one `..`
    because the archive sits a directory deeper.

    Returns the remaining text, or None when an existing archive would be
    overwritten with different content -- it is the permanent record for that line.
    An identical write is allowed, being a retry.
    """
    head, _, below = text.partition(UNRELEASED_END)
    at = below.find("\n## ")
    moved = below[at + 1:].partition("\n" + EARLIER)[0].strip()
    archive = (f"{HEADING} — {line}\n\nCurrent releases are in the "
               f"[top-level changelog](../CHANGELOG.md).\n\n"
               f"{moved.replace(f']({PR_PREFIX}', f'](../{PR_PREFIX}')}\n")
    target = changes / f"{line}.md"
    if target.exists() and target.read_text() != archive:
        _err(f"{target} already exists with different content; archiving {line} "
             f"would overwrite it")
        return None
    target.write_text(archive)
    return head + UNRELEASED_END + below[:at + 1].rstrip() + "\n"


def set_archive_list(text, changes):
    """Replace the trailing list of archived lines, newest first.

    Rebuilt from the archives present rather than from a list kept in the file, so
    one written by hand at adoption is picked up without being registered anywhere.
    """
    text = text.partition("\n" + EARLIER)[0].rstrip() + "\n"
    archives = sorted(changes.glob("*.x.md"), reverse=True,
                      key=lambda p: [int(x) for x in p.name.split(".")[:2]])
    if not archives:
        return text
    return (f"{text}\n{EARLIER}\n\n"
            + "\n".join(f"- [{p.stem}]({changes.name}/{p.name})" for p in archives) + "\n")


def cmd_rollup(args):
    """The only way a release edits the file: validate, render, then route.

    A patch release adds its section and stops. A release opening a new minor
    version line archives the line it closes first, and that is the whole difference
    between the two.

    Re-running it is a no-op: the fragments are gone, so there is nothing left to
    insert. That matters because a release job that fails after this step -- on the
    tag, or on the GitHub release -- is retried. An invalid fragment stops the
    release instead, since releasing would delete it unrendered and lose the entry
    rather than merely delay it.

    In the release branch's copy of the file, the unreleased block holds a link to
    the docs branch rather than the list of unreleased changes itself: only a release
    rewrites this file, so a list of what is in flight would sit permanently stale. A
    docs branch whose name contains a slash is named rather than linked, since
    ../../blob/<branch>/CHANGELOG.md reaches the repo root only for a one-segment
    name.
    """
    if not ISO_DATE_RE.match(args.date):
        _err(f"--date must be YYYY-MM-DD, got {args.date!r}")
        return 2

    changes = Path(args.changes_dir)
    on_disk = sorted((changes / "preview").glob("*.json"))
    fragments = load_preview(changes)
    if len(fragments) != len(on_disk):
        _err(f"{len(on_disk) - len(fragments)} of {len(on_disk)} fragment(s) in "
             f"{changes / 'preview'} are invalid (see the warnings above); "
             f"fix them first")
        return 2

    labelled = [p.strip() for p in args.minor_prs.split(",") if p.strip()]
    if not all(p.isdigit() for p in labelled):
        _err(f"--minor-prs must be pull request numbers, got {args.minor_prs!r}")
        return 2

    body = render_grouped(fragments, {int(p) for p in labelled})
    section = f"## [{args.version}] — {args.date}\n\n{body}" if body else ""

    path = Path(args.changelog)
    text = path.read_text() if path.exists() else ""
    docs = args.docs_branch
    text = set_unreleased(text, f"Unreleased changes are on the `{docs}` branch.\n"
                          if "/" in docs else "Unreleased changes can be found "
                          f"[here](../../blob/{docs}/CHANGELOG.md).\n")

    if section:
        closing = VERSION_RE.match(text.partition("\n## [")[2])
        opening = VERSION_RE.match(args.version)
        if closing and opening and closing.group(1, 2) != opening.group(1, 2):
            text = archive_closed_line(
                text, changes, f"{closing.group(1)}.{closing.group(2)}.x")
            if text is None:
                return 2
        text = insert_section(text, section)

    path.write_text(set_archive_list(text, changes))

    for f in on_disk:
        f.unlink()
    print(f"released {len(fragments)} fragment(s) as {args.version}"
          + ("" if section else " (nothing customer-facing, so no section)"))
    return 0
