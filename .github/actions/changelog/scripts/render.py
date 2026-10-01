"""Fragments to markdown, and the three edits made to CHANGELOG.md.

The file is not regenerated. A release inserts one section below the unreleased
region and never touches what is already there, so a published entry cannot
change under a reader. Only the unreleased region is rewritten, and only on the
docs branch, where it is derived from preview/ on every merge.
"""
from pathlib import Path

from fragments import BREAKING_SECTION, CATEGORY, load_preview

HEADING = "# Changelog"
# Archived lines are listed last, after every release section.
EARLIER = "## Earlier releases"
# The region is bounded by markers rather than found by position, so an editor
# adding prose around it cannot move what gets replaced.
START = "<!-- changelog:unreleased -->"
END = "<!-- /changelog:unreleased -->"
SENTENCE_END = (".", "!", "?")
# Relative, so no repo name is stored. An archive one directory deeper needs one
# more `..`, which archive_line derives from this rather than restating it.
PR_PREFIX = "../../pull/"


def pr_link(frag):
    """`#843` linked relative to the repo root."""
    return f"[#{frag['pr']}]({PR_PREFIX}{frag['pr']})"


def render_entry(frag):
    summary = frag["summary"].strip()
    if not summary.endswith(SENTENCE_END):
        summary += "."
    return f"- {summary} ({pr_link(frag)})"


def render_note(frag):
    """A note is its own entry, led by the pull request it explains."""
    body = frag["notes"].strip().splitlines()
    return "\n  ".join([f"- {pr_link(frag)} — {body[0]}", *body[1:]])


def _section(heading, entries, render):
    if not entries:
        return []
    return [f"### {heading}",
            *(render(e) for e in sorted(entries, key=lambda f: f["pr"])), ""]


def render_grouped(fragments, minor_prs=()):
    """Sections in a fixed order, each omitted when it would be empty."""
    # A chore renders nowhere, so a chore whose pull request carries the label
    # does not surface here either.
    breaking = [f for f in fragments
                if f["pr"] in minor_prs and f["type"] in CATEGORY]
    lines = _section(BREAKING_SECTION, breaking, render_entry)
    for pr_type, cat in CATEGORY.items():
        rest = [f for f in fragments
                if f["type"] == pr_type and f["pr"] not in minor_prs]
        lines += _section(cat, rest, render_entry)
    lines += _section("Notes", [f for f in fragments if f.get("notes", "").strip()],
                      render_note)
    return "\n".join(lines).rstrip() + "\n" if lines else ""


def set_region(text, region):
    """Replace the unreleased region, adding it and the file's shape on a first run."""
    if START in text and END in text:
        head, _, rest = text.partition(START)
        _, _, tail = rest.partition(END)
        return f"{head}{START}\n{region}{END}{tail}"
    body = text.lstrip("\n")
    # Reuse the file's own heading when it has one -- an adopting repo does --
    # rather than adding a second heading above it.
    heading, _, rest = body.partition("\n") if body.startswith("# ") else (HEADING, "", body)
    rest = rest.lstrip("\n")
    return (f"{heading}\n\n{START}\n{region}{END}\n"
            + (f"\n{rest}" if rest.strip() else ""))


def insert_release(text, section):
    """Put a new release directly below the region, above every older one."""
    if not section:
        return text
    head, _, tail = text.partition(END)
    body = f"{head}{END}\n\n{section.rstrip()}\n\n{tail.lstrip()}"
    return body.rstrip() + "\n"


def _without_earlier(text):
    """`text` with any trailing list of archived lines removed."""
    return text.partition("\n" + EARLIER)[0].rstrip() + "\n"


def set_earlier(text, changes_dir):
    """Replace the trailing list of archived lines, newest first.

    Only a release needs this; the docs render never touches the listing. It is
    rebuilt from the archives present rather than from a list kept in the file, so
    one written by hand at adoption is picked up without being registered anywhere.
    """
    d = Path(changes_dir)
    files = sorted(d.glob("*.x.md"), reverse=True,
                   key=lambda p: [int(x) for x in p.name.split(".")[:2]])
    body = _without_earlier(text)
    if not files:
        return body
    return (f"{body}\n{EARLIER}\n\n"
            + "\n".join(f"- [{p.stem}]({d.name}/{p.name})" for p in files) + "\n")


def archive_line(text, line):
    """Move the released sections out of the root and into one archive file.

    The root only ever holds the current minor version line, so everything below
    the unreleased region *is* that line: nothing needs reading to decide what
    belongs. The caller only reaches here having found a release section, so there
    is one.
    """
    head, _, body = text.partition(END)
    at = body.find("\n## ")
    # The archive sits one directory down, so every link needs one more `..`.
    # The list of archives belongs to the root only, and it sits below the release
    # sections, so it would otherwise be carried into the archive.
    moved = _without_earlier(body[at + 1:]).replace(f"]({PR_PREFIX}", f"](../{PR_PREFIX}")
    return (head + END + body[:at + 1].rstrip() + "\n",
            f"{HEADING} — {line}\n\nCurrent releases are in the "
            f"[top-level changelog](../CHANGELOG.md).\n\n{moved.strip()}\n")


def cmd_render(args):
    """Refresh the unreleased region. The docs branch runs this on every merge."""
    path = Path(args.changelog)
    body = render_grouped(load_preview(args.changes_dir)) or "_Nothing yet._\n"
    text = path.read_text() if path.exists() else ""
    path.write_text(set_region(text, f"## [Unreleased]\n\n{body}"))
    print(f"rendered → {args.changelog}")
    return 0
