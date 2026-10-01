"""Fragments to markdown, and the two edits made to the file."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import render  # noqa: E402
from helpers import _render, _seed, _write  # noqa: E402


def test_entries_group_under_their_type(tmp_path):
    _seed(tmp_path, 1, "feat: Add a widget")
    _seed(tmp_path, 2, "fix: Stop a leak")
    _write(tmp_path, 3, "revert", summary="Reverted the default", notes="It broke.")
    text = _render(tmp_path)
    assert "### Features" in text and "### Fixes" in text and "### Reverts" in text
    assert text.index("### Features") < text.index("### Fixes") < text.index("### Reverts")


def test_a_chore_renders_nowhere(tmp_path):
    _seed(tmp_path, 1, "chore: Bump the CI image")
    text = _render(tmp_path)
    assert "Bump the CI image" not in text
    assert "_Nothing yet._" in text


def test_an_empty_section_is_omitted(tmp_path):
    _seed(tmp_path, 1, "feat: Only a feature")
    text = _render(tmp_path)
    assert "### Features" in text
    for absent in ("### Fixes", "### Reverts", "### Notes",
                   "### Possible Breaking Changes"):
        assert absent not in text


def test_a_summary_gets_a_full_stop_unless_it_has_one(tmp_path):
    _seed(tmp_path, 1, "fix: Retries no longer drop 429?")
    _seed(tmp_path, 2, "feat: Add SSO")
    text = _render(tmp_path)
    assert "429? (" in text and "429?." not in text
    assert "Add SSO. (" in text


def test_every_entry_links_its_pull_request(tmp_path):
    # Relative to the repo root, so no repo name is stored in a fragment and an
    # entry keeps working when the file is read on any branch.
    _seed(tmp_path, 843, "feat: Add SSO")
    assert "([#843](../../pull/843))" in _render(tmp_path)


def test_notes_render_as_their_own_section_last(tmp_path):
    _write(tmp_path, 40, "revert", summary="Reverted the retry default",
           notes="It changed behaviour customers relied on.\nA replacement lands later.")
    _seed(tmp_path, 41, "feat: A widget")
    text = _render(tmp_path)
    assert text.index("### Features") < text.index("### Notes")
    notes = text.split("### Notes", 1)[1]
    assert "- [#40](" in notes
    assert "\n  A replacement lands later." in notes
    # And lifted out of the entry itself.
    assert "It changed behaviour" not in text.split("### Reverts", 1)[1].split("###", 1)[0]


def test_a_minor_labelled_pull_request_renders_as_breaking_only(tmp_path):
    frags = [{"pr": 1, "type": "feat", "summary": "Replace the layout", "notes": ""},
             {"pr": 2, "type": "feat", "summary": "Add a knob", "notes": ""}]
    body = render.render_grouped(frags, minor_prs={1})
    breaking = body.split("### Possible Breaking Changes", 1)[1].split("###", 1)[0]
    assert "#1" in breaking and "#2" not in breaking
    features = body.split("### Features", 1)[1]
    assert "#2" in features and "#1" not in features


def test_the_unreleased_region_is_replaced_not_appended(tmp_path):
    _seed(tmp_path, 1, "feat: First")
    _render(tmp_path)
    (tmp_path / ".changes" / "preview" / "1.json").unlink()
    _seed(tmp_path, 2, "feat: Second")
    text = _render(tmp_path)
    assert "Second" in text and "First" not in text
    assert text.count(render.START) == 1


def test_rendering_leaves_released_sections_alone(tmp_path):
    (tmp_path / "CHANGELOG.md").write_text(
        render.set_region("", "") + "\n## [1.0.0] — 2026-01-01\n\n### Features\n- Old. (#1)\n")
    _seed(tmp_path, 2, "feat: New")
    text = _render(tmp_path)
    assert "## [1.0.0]" in text and "Old." in text and "New." in text


def test_a_file_with_no_markers_gains_them(tmp_path):
    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n\n## [0.9.0]\n\nHand-written.\n")
    text = _render(tmp_path)
    assert render.START in text and "Hand-written." in text


def test_an_existing_heading_is_reused_not_duplicated(tmp_path):
    # An adopting repo already has `# Changelog`; a second one renders as two
    # titles stacked on top of each other.
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [1.0.0]\n\nOfficial release of 1.0.0.\n")
    text = _render(tmp_path)
    assert text.count("# Changelog") == 1
    assert text.index(render.START) < text.index("## [1.0.0]")
    assert "Official release of 1.0.0." in text


def test_a_labelled_chore_still_renders_nowhere(tmp_path):
    # The label decides the section, not whether an entry exists at all.
    frags = [{"pr": 1, "type": "chore", "summary": "Bump the image", "notes": ""},
             {"pr": 2, "type": "feat", "summary": "Add a knob", "notes": ""}]
    body = render.render_grouped(frags, minor_prs={1, 2})
    assert "Bump the image" not in body
    assert "Add a knob" in body


def test_an_entry_lands_under_its_own_heading(tmp_path):
    _seed(tmp_path, 1, "feat: A feature")
    _seed(tmp_path, 2, "fix: A fix")
    text = _render(tmp_path)
    features = text.split("### Features", 1)[1].split("###", 1)[0]
    fixes = text.split("### Fixes", 1)[1]
    assert "A feature." in features and "A fix." not in features
    assert "A fix." in fixes and "A feature." not in fixes


def test_entries_within_a_section_are_ordered_by_pull_request(tmp_path):
    for pr in (30, 10, 20):
        _write(tmp_path, pr, "fix", summary=f"Fix number {pr}")
    import re
    fixes = _render(tmp_path).split("### Fixes", 1)[1]
    assert re.findall(r"\(\[#(\d+)\]", fixes) == ["10", "20", "30"]


def test_the_rendered_section_is_exact():
    # One test pins the whole shape, so a change to it has to be deliberate.
    assert render.render_grouped([{"pr": 7, "type": "feat", "summary": "Add a widget",
                                   "notes": "Worth knowing."}]) == (
        "### Features\n"
        "- Add a widget. ([#7](../../pull/7))\n"
        "\n"
        "### Notes\n"
        "- [#7](../../pull/7) — Worth knowing.\n"
    )
