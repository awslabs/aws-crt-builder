"""Cutting a release: render the fragments awaiting one, then drop them.

No version guard. The version comes from the release job, and a mistake in the
rendered file is fixed by a chore -- the file is markdown, not a database.
"""
import re
from pathlib import Path

from fragments import _err, load_preview
from render import END, HEADING, PR_PREFIX, render_grouped, set_region

ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Anchored where it is used: searching would match a version inside an entry's
# prose and archive the wrong line.
VERSION_RE = re.compile(r"(\d+)\.(\d+)\.\d+")
# Archived lines are listed last, after every release section. Only a release
# writes this; the docs render never touches it.
EARLIER = "## Earlier releases"


def cmd_rollup(args):
    """Insert this release's section, archive the line it closes, drop the fragments.

    Re-running it is a no-op: the fragments are gone, so there is nothing left to
    insert. That matters because a release job that fails after this step -- on the
    tag, or on the GitHub release -- is retried. An invalid fragment stops the
    release instead, since releasing would delete it unrendered and lose the entry
    rather than merely delay it.

    The region on this branch points at the docs branch instead of holding the
    unreleased list, because only a release rewrites this file and a list would sit
    permanently stale. A docs branch whose name contains a slash is named rather
    than linked, since ../../blob/<branch>/CHANGELOG.md reaches the repo root only
    for a one-segment name.

    A release opening a new minor version line closes the old one, moving its
    sections to .changes/<M>.<N>.x.md so the root only ever carries the line being
    released into. Everything below the region *is* the closing line, so nothing
    needs reading to decide what belongs; the root's own list of archives is dropped
    rather than carried along, and every link gains one `..` because the archive
    sits a directory deeper. An existing archive is never overwritten with different
    content -- it is the permanent record for that line -- but an identical write is
    allowed, being a retry.

    The section goes directly below the region, so a line's releases accumulate
    newest-first and older ones are never rewritten. The trailing list of archives
    is rebuilt from the files present rather than kept in the file, so one written
    by hand at adoption is picked up without being registered anywhere.
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
    text = set_region(text, f"Unreleased changes are on the `{docs}` branch.\n"
                      if "/" in docs else "Unreleased changes can be found "
                      f"[here](../../blob/{docs}/CHANGELOG.md).\n")

    closing = VERSION_RE.match(text.partition("\n## [")[2])
    opening = VERSION_RE.match(args.version)
    if section and closing and opening and closing.group(1, 2) != opening.group(1, 2):
        line = f"{closing.group(1)}.{closing.group(2)}.x"
        head, _, below = text.partition(END)
        at = below.find("\n## ")
        moved = below[at + 1:].partition("\n" + EARLIER)[0].strip()
        archive = (f"{HEADING} — {line}\n\nCurrent releases are in the "
                   f"[top-level changelog](../CHANGELOG.md).\n\n"
                   f"{moved.replace(f']({PR_PREFIX}', f'](../{PR_PREFIX}')}\n")
        target = changes / f"{line}.md"
        if target.exists() and target.read_text() != archive:
            _err(f"{target} already exists with different content; releasing "
                 f"{args.version} would overwrite it")
            return 2
        target.write_text(archive)
        text = head + END + below[:at + 1].rstrip() + "\n"

    if section:
        head, _, tail = text.partition(END)
        text = f"{head}{END}\n\n{section.rstrip()}\n\n{tail.lstrip()}".rstrip() + "\n"

    text = text.partition("\n" + EARLIER)[0].rstrip() + "\n"
    archives = sorted(changes.glob("*.x.md"), reverse=True,
                      key=lambda p: [int(x) for x in p.name.split(".")[:2]])
    if archives:
        text += (f"\n{EARLIER}\n\n"
                 + "\n".join(f"- [{p.stem}]({changes.name}/{p.name})" for p in archives)
                 + "\n")
    path.write_text(text)

    for f in on_disk:
        f.unlink()
    print(f"released {len(fragments)} fragment(s) as {args.version}"
          + ("" if section else " (nothing customer-facing, so no section)"))
    return 0
