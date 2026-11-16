"""Fragments to markdown.

Unreleased changes exist only as fragments under preview/. Nothing renders them
into CHANGELOG.md until a release does -- see release.py.
"""
from pathlib import Path

from fragments import BREAKING_SECTION, CATEGORY, Rc, load_preview

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


def cmd_render(args):
    """Print the unreleased changes, rendered from preview/, without writing anything."""
    print(render_grouped(load_preview(args.changes_dir)) or "_Nothing yet._", end="")
    return Rc.OK
