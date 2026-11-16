"""Cutting a release: render the fragments awaiting one, then drop them.

No version guard. The version comes from the release job, and a mistake in the
rendered file is fixed by a chore -- the file is markdown, not a database.
"""
import re
from pathlib import Path

from fragments import Rc, _err, load_preview
from render import render_grouped

HEADING = "# Changelog"
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SECTION_RE = re.compile(r"^## \[(\d+)\.(\d+)\.\d+\]")
EARLIER = "## Earlier releases"


def parse(text):
    """The file as (heading, [section, ...]), newest section first.

    The archive list at the bottom is dropped: it is rebuilt from the archives
    present. A file with no heading of its own, such as an adopting repo's, gains one.
    """
    text = text.partition("\n" + EARLIER)[0].strip()
    head, *sections = re.split(r"(?m)^(?=## \[)", text)
    head = head.strip()
    if not head.startswith("# "):
        head = f"{HEADING}\n\n{head}".strip()
    return head, [s.strip() for s in sections]


def line_of(section):
    return SECTION_RE.match(section).group(1, 2)


def archive_lines(sections, keep, changes):
    """Move every minor line except `keep` out to .changes/<M>.<N>.x.md.

    Returns the sections that stay, or None when an existing archive would be
    overwritten with different content -- it is the permanent record for that
    line. An identical write is allowed, being a retry.
    """
    stay, moved = [], {}
    for s in sections:
        (stay if line_of(s) == keep else moved.setdefault(line_of(s), [])).append(s)
    for (major, minor), group in moved.items():
        line = f"{major}.{minor}.x"
        archive = (f"{HEADING} — {line}\n\nCurrent releases are in the "
                   f"[top-level changelog](../CHANGELOG.md).\n\n" + "\n\n".join(group) + "\n")
        target = changes / f"{line}.md"
        if target.exists() and target.read_text() != archive:
            _err(f"{target} already exists with different content; archiving {line} "
                 f"would overwrite it")
            return None
        target.write_text(archive)
    return stay


def archive_list(changes):
    """The trailing list of archived lines, newest first, rebuilt from the files present."""
    archives = sorted(changes.glob("*.x.md"), reverse=True,
                      key=lambda p: [int(x) for x in p.name.split(".")[:2]])
    if not archives:
        return ""
    return (f"\n\n{EARLIER}\n\n"
            + "\n".join(f"- [{p.stem}]({changes.name}/{p.name})" for p in archives))


def cmd_rollup(args):
    """The only way a release edits the file: validate, render, insert.

    The release's section goes directly below the heading, so releases accumulate
    newest-first and published ones are never rewritten. Archiving is the
    developer's call: with --archive, every minor line other than the one being
    released into moves to its own file.

    Re-running it is a no-op: the fragments are gone, so there is nothing left to
    insert. That matters because a release job that fails after this step -- on the
    tag, or on the GitHub release -- is retried. An invalid fragment stops the
    release instead, since releasing would delete it unrendered and lose the entry
    rather than merely delay it.
    """
    if not ISO_DATE_RE.match(args.date):
        _err(f"--date must be YYYY-MM-DD, got {args.date!r}")
        return Rc.CALLER_ERROR
    opening = SECTION_RE.match(f"## [{args.version}]")
    if not opening:
        _err(f"--version must be x.y.z, got {args.version!r}")
        return Rc.CALLER_ERROR

    changes = Path(args.changes_dir)
    on_disk = sorted((changes / "preview").glob("*.json"))
    fragments = load_preview(changes)
    if len(fragments) != len(on_disk):
        _err(f"{len(on_disk) - len(fragments)} of {len(on_disk)} fragment(s) in "
             f"{changes / 'preview'} are invalid (see the warnings above); "
             f"fix them first")
        return Rc.CALLER_ERROR

    labelled = [p.strip() for p in args.minor_prs.split(",") if p.strip()]
    if not all(p.isdigit() for p in labelled):
        _err(f"--minor-prs must be pull request numbers, got {args.minor_prs!r}")
        return Rc.CALLER_ERROR

    body = render_grouped(fragments, {int(p) for p in labelled})
    section = f"## [{args.version}] — {args.date}\n\n{body}" if body else ""

    path = Path(args.changelog)
    head, sections = parse(path.read_text() if path.exists() else "")
    if section:
        if args.archive:
            sections = archive_lines(sections, opening.group(1, 2), changes)
            if sections is None:
                return Rc.CALLER_ERROR
        sections.insert(0, section.strip())

    path.write_text("\n\n".join([head, *sections]) + archive_list(changes) + "\n")

    for f in on_disk:
        f.unlink()
    print(f"released {len(fragments)} fragment(s) as {args.version}"
          + ("" if section else " (nothing customer-facing, so no section)"))
    return Rc.OK
