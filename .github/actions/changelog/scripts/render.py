"""Fragments to markdown, and the one edit the docs branch makes.

The file is not regenerated. Only the unreleased block is rewritten, and only on
the docs branch, where it is derived from preview/ on every merge. A release
inserts its section below that block and never touches what is already there, so a
published entry cannot change under a reader -- see release.py.
"""
from pathlib import Path

from fragments import BREAKING_SECTION, CATEGORY, load_preview

HEADING = "# Changelog"
# The unreleased block is bounded by markers rather than found by position, so an
# editor adding prose around it cannot move what gets replaced. It holds the
# unreleased list on the docs branch and a link to it on the release branch; every
# line outside it is history and is never rewritten.
UNRELEASED_START = "<!-- changelog:unreleased -->"
UNRELEASED_END = "<!-- /changelog:unreleased -->"
SENTENCE_END = (".", "!", "?")
# Relative, so no repo name is stored. An archive one directory deeper needs one
# more `..`, which the release derives from this rather than restating it.
PR_PREFIX = "../../pull/"


def render_grouped(fragments, minor_prs=()):
    """Sections in a fixed order, each omitted when it would be empty.

    A chore renders nowhere, so a chore whose pull request carries the `minor`
    label does not surface under breaking changes either.
    """
    buckets = [(BREAKING_SECTION, [f for f in fragments
                                   if f["pr"] in minor_prs and f["type"] in CATEGORY])]
    buckets += [(cat, [f for f in fragments
                       if f["type"] == pr_type and f["pr"] not in minor_prs])
                for pr_type, cat in CATEGORY.items()]
    buckets.append(("Notes", [f for f in fragments if f.get("notes", "").strip()]))

    lines = []
    for heading, entries in buckets:
        if not entries:
            continue
        lines.append(f"### {heading}")
        for f in sorted(entries, key=lambda x: x["pr"]):
            link = f"[#{f['pr']}]({PR_PREFIX}{f['pr']})"
            if heading == "Notes":
                body = f["notes"].strip().splitlines()
                lines.append("\n  ".join([f"- {link} — {body[0]}", *body[1:]]))
            else:
                summary = f["summary"].strip()
                dot = "" if summary.endswith(SENTENCE_END) else "."
                lines.append(f"- {summary}{dot} ({link})")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n" if lines else ""


def set_unreleased(text, block):
    """Replace the unreleased block, adding it and the file's shape on a first run.

    A file that already has a heading -- an adopting repo's does -- keeps it rather
    than gaining a second one above it.
    """
    if UNRELEASED_START in text and UNRELEASED_END in text:
        head, _, rest = text.partition(UNRELEASED_START)
        _, _, tail = rest.partition(UNRELEASED_END)
        return f"{head}{UNRELEASED_START}\n{block}{UNRELEASED_END}{tail}"
    body = text.lstrip("\n")
    heading, _, rest = body.partition("\n") if body.startswith("# ") else (HEADING, "", body)
    rest = rest.lstrip("\n")
    return (f"{heading}\n\n{UNRELEASED_START}\n{block}{UNRELEASED_END}\n"
            + (f"\n{rest}" if rest.strip() else ""))


def cmd_render(args):
    """Refresh the unreleased block. The docs branch runs this on every merge."""
    path = Path(args.changelog)
    body = render_grouped(load_preview(args.changes_dir)) or "_Nothing yet._\n"
    text = path.read_text() if path.exists() else ""
    path.write_text(set_unreleased(text, f"## [Unreleased]\n\n{body}"))
    print(f"rendered → {args.changelog}")
    return 0
