"""Cutting a release: render the fragments awaiting one, then drop them.

No version guard. The version comes from the release job, and a mistake in the
rendered file is fixed by a chore -- the file is markdown, not a database.
"""
import re
from pathlib import Path

from fragments import _err, load_preview
from render import archive_line, earlier_releases, insert_release, \
    render_release_section, set_earlier, set_region, unreleased_pointer

ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
VERSION_RE = re.compile(r"(\d+)\.(\d+)\.\d+")


def _line(text):
    """(major, minor) of the version `text` starts with, or None.

    Anchored: searching would match a version inside an entry's prose and archive
    the wrong line.
    """
    m = VERSION_RE.match(text)
    return (int(m.group(1)), int(m.group(2))) if m else None


def cmd_rollup(args):
    """Insert this release's section, then delete the fragments it rendered.

    Re-running it is a no-op: the fragments are gone, so there is nothing left to
    insert. That matters because a release job that fails after this step -- on
    the tag, or on the GitHub release -- is retried.
    """
    if not ISO_DATE_RE.match(args.date):
        _err(f"--date must be YYYY-MM-DD, got {args.date!r}")
        return 2

    changes = Path(args.changes_dir)
    on_disk = sorted((changes / "preview").glob("*.json"))
    fragments = load_preview(changes)
    if len(fragments) != len(on_disk):
        # Releasing anyway would delete the rejected fragments unrendered, so the
        # entry would be lost rather than merely late.
        _err(f"{len(on_disk) - len(fragments)} of {len(on_disk)} fragment(s) in "
             f"{changes / 'preview'} are invalid (see the warnings above); "
             f"fix them first")
        return 2

    labelled = [p.strip() for p in args.minor_prs.split(",") if p.strip()]
    if not all(p.isdigit() for p in labelled):
        _err(f"--minor-prs must be pull request numbers, got {args.minor_prs!r}")
        return 2
    minor_prs = {int(p) for p in labelled}
    section = render_release_section(args.version, args.date, fragments, minor_prs)

    path = Path(args.changelog)
    text = path.read_text() if path.exists() else ""
    # The release branch's region is the pointer, not the unreleased list: only a
    # release rewrites this file, so a list of unreleased changes would sit stale.
    text = set_region(text, unreleased_pointer(args.docs_branch))

    # A new minor version line closes the old one: its sections move to an
    # archive, so the root only ever carries the line being released into. Nothing
    # to close if
    # this release renders nothing, or if either version does not parse.
    closing = _line(text.partition("\n## [")[2])
    opening = _line(args.version)
    if section and closing and opening and closing != opening:
        text, archive = archive_line(text, f"{closing[0]}.{closing[1]}.x")
        target = changes / f"{closing[0]}.{closing[1]}.x.md"
        if target.exists() and target.read_text() != archive:
            # An archive is the permanent record for a line. Overwriting it would
            # delete released entries; an identical write is a retry, so allow it.
            _err(f"{target} already exists with different content; releasing "
                 f"{args.version} would overwrite it")
            return 2
        target.write_text(archive)

    path.write_text(set_earlier(insert_release(text, section),
                                earlier_releases(changes)))

    for f in on_disk:
        f.unlink()
    print(f"released {len(fragments)} fragment(s) as {args.version}"
          + ("" if section else " (nothing customer-facing, so no section)"))
    return 0
