"""Cutting a release."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import render  # noqa: E402
from helpers import _changes, _rollup, _seed, _write  # noqa: E402


def _changelog(tmp_path):
    return (tmp_path / "CHANGELOG.md").read_text()


def test_a_release_renders_its_section_and_drops_the_fragments(tmp_path):
    _seed(tmp_path, 1, "feat: Add a widget")
    _seed(tmp_path, 2, "chore: Bump the CI image")
    assert _rollup(tmp_path, "1.0.2", "2026-09-06") == 0
    text = _changelog(tmp_path)
    assert "## [1.0.2] — 2026-09-06" in text
    assert "Add a widget." in text
    # The fragment is the input, not the record: it is gone once rendered.
    assert list((tmp_path / ".changes" / "preview").glob("*.json")) == []


def test_the_newest_release_sits_above_the_older_ones(tmp_path):
    # Two patches, so both stay in the root: a minor bump would archive the first.
    _seed(tmp_path, 1, "feat: First")
    _rollup(tmp_path, "1.0.2", "2026-09-06")
    _seed(tmp_path, 2, "feat: Second")
    _rollup(tmp_path, "1.0.3", "2026-09-10")
    text = _changelog(tmp_path)
    assert text.index("## [1.0.3]") < text.index("## [1.0.2]")
    # A blank line between them, or the sections run together when rendered.
    assert "\n\n## [1.0.2]" in text


def test_a_released_section_is_never_rewritten(tmp_path):
    _seed(tmp_path, 1, "feat: First")
    _rollup(tmp_path, "1.0.2", "2026-09-06")
    before = _changelog(tmp_path).split("## [1.0.2]", 1)[1]
    _seed(tmp_path, 2, "feat: Second")
    _rollup(tmp_path, "1.0.3", "2026-09-10")
    assert _changelog(tmp_path).split("## [1.0.2]", 1)[1] == before


def test_re_running_a_release_changes_nothing(tmp_path):
    # The release job can fail after this step -- on the tag, or on the GitHub
    # release -- and be retried. The retry must not add a second section.
    _seed(tmp_path, 1, "feat: Add a widget")
    _rollup(tmp_path, "1.0.2", "2026-09-06")
    before = _changelog(tmp_path)
    assert _rollup(tmp_path, "1.0.2", "2026-09-06") == 0
    assert _changelog(tmp_path) == before


def test_a_release_with_nothing_visible_renders_no_section(tmp_path):
    # A bare header with nothing under it reads as a broken file.
    _seed(tmp_path, 1, "chore: Internal only")
    assert _rollup(tmp_path, "1.0.2", "2026-09-06") == 0
    assert "## [1.0.2]" not in _changelog(tmp_path)
    assert list((tmp_path / ".changes" / "preview").glob("*.json")) == []


def test_a_release_with_no_fragments_at_all_still_succeeds(tmp_path):
    # Failing here would fail the release job after it has already tagged.
    _changes(tmp_path)
    assert _rollup(tmp_path, "1.0.2", "2026-09-06") == 0


def test_the_release_branch_shows_the_pointer_not_the_unreleased_list(tmp_path):
    _seed(tmp_path, 1, "feat: Add a widget")
    _rollup(tmp_path, "1.0.2", "2026-09-06")
    text = _changelog(tmp_path)
    assert "## [Unreleased]" not in text
    assert "[here](../../blob/docs/CHANGELOG.md)" in text


def test_the_docs_branch_name_is_the_consumers_choice(tmp_path):
    _seed(tmp_path, 1, "feat: Add a widget")
    _rollup(tmp_path, "1.0.2", "2026-09-06", docs_branch="changelog-docs")
    assert "[here](../../blob/changelog-docs/CHANGELOG.md)" in _changelog(tmp_path)


def test_a_slashed_docs_branch_is_named_rather_than_linked(tmp_path):
    # ../../blob/<branch>/ reaches the repo root only for a one-segment name, so a
    # branch with a slash in it would link somewhere that does not resolve.
    _seed(tmp_path, 1, "feat: Add a widget")
    _rollup(tmp_path, "1.0.2", "2026-09-06", docs_branch="team/docs")
    text = _changelog(tmp_path)
    assert "`team/docs`" in text and "](../../blob/" not in text


def test_the_abi_label_decides_the_breaking_section(tmp_path):
    _seed(tmp_path, 20, "feat: Replace the socket options layout")
    _seed(tmp_path, 21, "feat: Add a knob")
    assert _rollup(tmp_path, "1.1.0", "2026-09-10", minor_prs="20") == 0
    text = _changelog(tmp_path)
    breaking = text.split("### Possible Breaking Changes", 1)[1].split("###", 1)[0]
    assert "#20" in breaking and "#21" not in breaking


def test_an_invalid_fragment_stops_the_release(tmp_path):
    # Releasing would delete it unrendered, so the entry would be lost rather
    # than merely late.
    _seed(tmp_path, 1, "feat: Good")
    (tmp_path / ".changes" / "preview" / "2.json").write_text("{ not json")
    assert _rollup(tmp_path, "1.0.2", "2026-09-06") == 2
    assert not (tmp_path / "CHANGELOG.md").exists()
    assert len(list((tmp_path / ".changes" / "preview").glob("*.json"))) == 2


def test_a_malformed_date_stops_the_release(tmp_path):
    _seed(tmp_path, 1, "feat: Good")
    assert _rollup(tmp_path, "1.0.2", "06-09-2026") == 2


def test_a_release_preserves_hand_written_content(tmp_path):
    # Adoption: whatever is in the file before the first release stays there.
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [1.0.0]\n\nOfficial release of 1.0.0.\n")
    _seed(tmp_path, 1, "feat: Add a widget")
    _rollup(tmp_path, "1.0.2", "2026-09-06")
    text = _changelog(tmp_path)
    assert "Official release of 1.0.0." in text
    assert text.index("## [1.0.2]") < text.index("## [1.0.0]")


def test_a_new_minor_line_archives_the_old_one(tmp_path):
    _seed(tmp_path, 1, "feat: First")
    _rollup(tmp_path, "1.0.2", "2026-09-01")
    _seed(tmp_path, 2, "fix: Second")
    _rollup(tmp_path, "1.0.3", "2026-09-05")
    _seed(tmp_path, 3, "feat: Third")
    _rollup(tmp_path, "1.1.0", "2026-09-10")

    root = _changelog(tmp_path)
    # The root carries only the line being released into, plus a link out.
    assert "## [1.1.0]" in root
    assert "## [1.0.2]" not in root and "## [1.0.3]" not in root
    assert "- [1.0.x](.changes/1.0.x.md)" in root

    archive = (tmp_path / ".changes" / "1.0.x.md").read_text()
    assert archive.startswith("# Changelog — 1.0.x")
    assert "## [1.0.3]" in archive and "## [1.0.2]" in archive
    assert "## [1.1.0]" not in archive
    # One directory deeper, so the links need one more `..`.
    assert "(../../../pull/1)" in archive
    assert "(../CHANGELOG.md)" in archive


def test_a_patch_archives_nothing(tmp_path):
    _seed(tmp_path, 1, "feat: First")
    _rollup(tmp_path, "1.0.2", "2026-09-01")
    _seed(tmp_path, 2, "fix: Second")
    _rollup(tmp_path, "1.0.3", "2026-09-05")
    assert list((tmp_path / ".changes").glob("*.x.md")) == []
    root = _changelog(tmp_path)
    assert "## [1.0.2]" in root and "## [1.0.3]" in root


def test_archived_lines_are_listed_newest_first(tmp_path):
    # Sorted on the numbers, not the text: 1.10.x is newer than 1.2.x.
    _changes(tmp_path)
    for line in ("1.0.x", "1.2.x", "1.10.x"):
        (tmp_path / ".changes" / f"{line}.md").write_text(f"# Changelog — {line}\n")
    _seed(tmp_path, 1, "feat: A thing")
    _rollup(tmp_path, "1.11.0", "2026-09-10")
    listed = _changelog(tmp_path).split("## Earlier releases", 1)[1]
    assert [ln.strip() for ln in listed.strip().splitlines()] == [
        "- [1.10.x](.changes/1.10.x.md)",
        "- [1.2.x](.changes/1.2.x.md)",
        "- [1.0.x](.changes/1.0.x.md)",
    ]


def test_the_first_release_of_all_archives_nothing(tmp_path):
    _seed(tmp_path, 1, "feat: First")
    assert _rollup(tmp_path, "1.0.2", "2026-09-01") == 0
    assert list((tmp_path / ".changes").glob("*.x.md")) == []
    assert "Earlier releases" not in _changelog(tmp_path)


def test_archiving_refuses_to_overwrite_a_different_archive(tmp_path):
    # An archive is the permanent record for a line. Releasing into a line whose
    # archive already says something else would delete released entries.
    _seed(tmp_path, 1, "feat: First")
    _rollup(tmp_path, "1.0.2", "2026-09-01")
    (tmp_path / ".changes" / "1.0.x.md").write_text("# Changelog — 1.0.x\n\nsomething else\n")
    _seed(tmp_path, 2, "feat: Second")
    assert _rollup(tmp_path, "1.1.0", "2026-09-10") == 2
    assert "something else" in (tmp_path / ".changes" / "1.0.x.md").read_text()


def test_re_archiving_identical_content_is_allowed(tmp_path):
    # A crash between writing the archive and writing the root leaves the archive
    # behind; the retry writes the same bytes and must not be refused.
    _seed(tmp_path, 1, "feat: First")
    _rollup(tmp_path, "1.0.2", "2026-09-01")
    before = _changelog(tmp_path)
    _seed(tmp_path, 2, "feat: Second")
    _rollup(tmp_path, "1.1.0", "2026-09-10")
    archived = (tmp_path / ".changes" / "1.0.x.md").read_text()
    # Rewind the root and re-run: the archive is already there, byte for byte.
    (tmp_path / "CHANGELOG.md").write_text(before)
    _seed(tmp_path, 3, "feat: Second again")
    assert _rollup(tmp_path, "1.1.0", "2026-09-10") == 0
    assert (tmp_path / ".changes" / "1.0.x.md").read_text() == archived


def test_a_release_with_no_section_archives_nothing(tmp_path):
    # Archiving on a chore-only release would empty the root and put nothing back.
    _seed(tmp_path, 1, "feat: First")
    _rollup(tmp_path, "1.0.2", "2026-09-01")
    _seed(tmp_path, 2, "chore: Internal only")
    assert _rollup(tmp_path, "1.1.0", "2026-09-10") == 0
    assert list((tmp_path / ".changes").glob("*.x.md")) == []
    assert "## [1.0.2]" in _changelog(tmp_path)


def test_the_line_is_read_from_the_first_heading_only(tmp_path):
    """A first section that is not a version means the line is unknown.

    Searching the rest of the document instead would find a later version and
    archive against it, sweeping the unversioned section away with it.
    """
    _changes(tmp_path)
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [Unreleased notes]\n\nHand-written.\n\n"
        "## [1.0.2] — 2026-09-01\n\n### Fixes\n- Old. ([#1](../../pull/1))\n")
    _seed(tmp_path, 2, "feat: Next line")
    assert _rollup(tmp_path, "1.1.0", "2026-09-10") == 0
    assert list((tmp_path / ".changes").glob("*.x.md")) == []
    text = _changelog(tmp_path)
    assert "Hand-written." in text and "## [1.0.2]" in text


def test_a_non_numeric_minor_prs_is_a_caller_error(tmp_path):
    _seed(tmp_path, 1, "feat: First")
    assert _rollup(tmp_path, "1.0.2", "2026-09-01", minor_prs="oops") == 2
    assert not (tmp_path / "CHANGELOG.md").exists()
    assert (tmp_path / ".changes" / "preview" / "1.json").exists()
