"""Cutting a release: render the fragments awaiting one, then drop them.

Unreleased changes exist only as fragments, so a release is the one place
anything is rendered.

No version guard. The version comes from the release job, and a mistake in the
rendered file is fixed by a chore -- the file is markdown, not a database.
"""
import re
from pathlib import Path

from fragments import BREAKING_SECTION, CATEGORY, Rc, _err, load_preview

HEADING = "# Changelog"
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SECTION_RE = re.compile(r"^## \[(\d+)\.(\d+)\.(\d+)\]")
ARCHIVE_RE = re.compile(r"^(\d+\.\d+\.\d+)-(\d+\.\d+\.\d+)\.md$")
EARLIER = "## Earlier releases"
SENTENCE_END = (".", "!", "?")


def render_grouped(fragments, minor_prs=()):
    """Sections in a fixed order, each omitted when it would be empty.

    An entry is its summary alone: it links to nothing, so a rendered file never
    depends on where the repository is hosted.
    """
    buckets = [(BREAKING_SECTION, [f for f in fragments
                                   if f["pr"] in minor_prs and f["type"] in CATEGORY])]
    buckets += [(cat, [f for f in fragments
                       if f["type"] == pr_type and f["pr"] not in minor_prs])
                for pr_type, cat in CATEGORY.items()]

    lines = []
    for heading, entries in buckets:
        if not entries:
            continue
        lines.append(f"### {heading}")
        for f in sorted(entries, key=lambda x: x["pr"]):
            summary = f["summary"].strip()
            dot = "" if summary.endswith(SENTENCE_END) else "."
            lines.append(f"- {summary}{dot}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n" if lines else ""


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


def version_of(section):
    return ".".join(SECTION_RE.match(section).groups())


def archive_older(sections, keep, changes):
    """Move every release outside the minor line `keep` into one archive file.

    The file is named for the releases it holds, .changes/<oldest>-<newest>.md: an
    archive is cut when the developer asks, so it can span several minor lines.

    Returns the sections that stay, or None when the archive would overwrite a
    file with different content -- it is the permanent record for those releases.
    An identical write is allowed, being a retry.
    """
    stay = [s for s in sections if line_of(s) == keep]
    moved = [s for s in sections if line_of(s) != keep]
    if not moved:
        return stay
    span = f"{version_of(moved[-1])}-{version_of(moved[0])}"
    archive = (f"{HEADING} — {span.replace('-', ' to ')}\n\nCurrent releases are in the "
               f"[top-level changelog](../CHANGELOG.md).\n\n" + "\n\n".join(moved) + "\n")
    target = changes / f"{span}.md"
    if target.exists() and target.read_text() != archive:
        _err(f"{target} already exists with different content; archiving {span} "
             f"would overwrite it")
        return None
    target.write_text(archive)
    return stay


def archive_list(changes):
    """The trailing list of archives, newest first, rebuilt from the files present."""
    found = [(p, ARCHIVE_RE.match(p.name)) for p in changes.glob("*.md")]
    archives = sorted(((p, m) for p, m in found if m), reverse=True,
                      key=lambda pm: [int(x) for x in pm[1].group(2).split(".")])
    if not archives:
        return ""
    return (f"\n\n{EARLIER}\n\n"
            + "\n".join(f"- [{p.stem}]({changes.name}/{p.name})" for p, _ in archives))


def cmd_rollup(args):
    """The only way a release edits the file: validate, render, insert.

    The release's section goes directly below the heading, so releases accumulate
    newest-first and published ones are never rewritten. Archiving is the
    developer's call: with --archive, every release outside the minor line being
    released into moves to one archive file.

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
            sections = archive_older(sections, opening.group(1, 2), changes)
            if sections is None:
                return Rc.CALLER_ERROR
        sections.insert(0, section.strip())

    path.write_text("\n\n".join([head, *sections]) + archive_list(changes) + "\n")

    for f in on_disk:
        f.unlink()
    print(f"released {len(fragments)} fragment(s) as {args.version}"
          + ("" if section else " (nothing customer-facing, so no section)"))
    return Rc.OK
