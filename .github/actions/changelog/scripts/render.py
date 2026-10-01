"""Fragments to markdown, and the one edit the docs branch makes.

The file is not regenerated. Only the unreleased region is rewritten, and only on
the docs branch, where it is derived from preview/ on every merge. A release
inserts its section below that region and never touches what is already there, so
a published entry cannot change under a reader -- see release.py.
"""
from pathlib import Path

from fragments import BREAKING_SECTION, CATEGORY, load_preview

HEADING = "# Changelog"
# The region is bounded by markers rather than found by position, so an editor
# adding prose around it cannot move what gets replaced.
START = "<!-- changelog:unreleased -->"
END = "<!-- /changelog:unreleased -->"
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


def set_region(text, region):
    """Replace the unreleased region, adding it and the file's shape on a first run.

    A file that already has a heading -- an adopting repo's does -- keeps it rather
    than gaining a second one above it.
    """
    if START in text and END in text:
        head, _, rest = text.partition(START)
        _, _, tail = rest.partition(END)
        return f"{head}{START}\n{region}{END}{tail}"
    body = text.lstrip("\n")
    heading, _, rest = body.partition("\n") if body.startswith("# ") else (HEADING, "", body)
    rest = rest.lstrip("\n")
    return (f"{heading}\n\n{START}\n{region}{END}\n"
            + (f"\n{rest}" if rest.strip() else ""))


def cmd_render(args):
    """Refresh the unreleased region. The docs branch runs this on every merge."""
    path = Path(args.changelog)
    body = render_grouped(load_preview(args.changes_dir)) or "_Nothing yet._\n"
    text = path.read_text() if path.exists() else ""
    path.write_text(set_region(text, f"## [Unreleased]\n\n{body}"))
    print(f"rendered → {args.changelog}")
    return 0
