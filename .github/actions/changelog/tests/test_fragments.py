"""The fragment schema, and reading the directory of them."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fragments  # noqa: E402
from helpers import _changes, _seed, _write  # noqa: E402


def _valid(pr=1, **over):
    frag = {"pr": pr, "type": "feat", "summary": "A thing", "notes": ""}
    frag.update(over)
    return frag


def _at(tmp_path, frag, name="1.json"):
    p = tmp_path / name
    p.write_text(json.dumps(frag))
    return p


# ---------- title convention ----------

def test_a_conventional_title_yields_its_type():
    for title, want in (("feat: add SSO", ("feat", "add SSO")),
                        ("fix(io): handle EINTR", ("fix", "handle EINTR")),
                        ("CHORE: bump", ("chore", "bump")),
                        ("revert: undo it", ("revert", "undo it"))):
        assert fragments.parse_title(title) == want


def test_the_revert_button_title_is_accepted_verbatim():
    assert fragments.parse_title('Revert "feat: add SSO (#843)"') == \
        ("revert", "feat: add SSO (#843)")


def test_an_unconventional_title_yields_no_type():
    assert fragments.parse_title("Add more getters") == (None, "Add more getters")
    assert fragments.parse_title("perf: make it faster") == (None, "perf: make it faster")


# ---------- schema ----------

def test_a_valid_fragment_has_no_errors(tmp_path):
    assert fragments.validate_fragment(_at(tmp_path, _valid())) == []


def test_every_required_field_is_required(tmp_path):
    for missing in ("pr", "type", "summary"):
        frag = _valid()
        del frag[missing]
        assert any(missing in e for e in
                   fragments.validate_fragment(_at(tmp_path, frag)))


def test_the_schema_is_closed(tmp_path):
    # A misspelled field would otherwise be ignored in silence, and `impact`
    # would let a pull request put itself under Possible Breaking Changes.
    for extra in ("impact", "summry", "version"):
        errs = fragments.validate_fragment(_at(tmp_path, _valid(**{extra: "x"})))
        assert any("unexpected field" in e and extra in e for e in errs)


def test_an_unknown_type_is_rejected(tmp_path):
    assert fragments.validate_fragment(_at(tmp_path, _valid(type="doc")))


def test_an_empty_summary_is_rejected(tmp_path):
    assert fragments.validate_fragment(_at(tmp_path, _valid(summary="  ")))


def test_a_placeholder_pr_number_is_rejected(tmp_path):
    assert fragments.validate_fragment(_at(tmp_path, _valid(pr=0)))
    assert fragments.validate_fragment(_at(tmp_path, _valid(pr=True)))


def test_malformed_json_is_reported_not_raised(tmp_path):
    p = tmp_path / "x.json"
    p.write_text("{ not json")
    assert fragments.validate_fragment(p)


def test_a_revert_must_explain_itself(tmp_path):
    assert fragments.validate_fragment(_at(tmp_path, _valid(type="revert")))
    assert not fragments.validate_fragment(
        _at(tmp_path, _valid(type="revert", notes="It broke downstream.")))


# ---------- reading the directory ----------

def test_loading_skips_what_it_cannot_render(tmp_path, capsys):
    _write(tmp_path, 1, "feat")
    (tmp_path / ".changes" / "preview" / "2.json").write_text("{ not json")
    loaded = fragments.load_preview(tmp_path / ".changes")
    assert [f["pr"] for f in loaded] == [1]
    assert "WARN" in capsys.readouterr().err


def test_a_fragment_must_be_named_for_its_own_pull_request(tmp_path, capsys):
    _write(tmp_path, 7, "feat")
    (tmp_path / ".changes" / "preview" / "7.json").write_text(
        json.dumps(_valid(pr=9)))
    assert fragments.load_preview(tmp_path / ".changes") == []
    assert "does not match the filename" in capsys.readouterr().err


def test_no_changes_directory_loads_nothing(tmp_path):
    assert fragments.load_preview(tmp_path / ".changes") == []


# ---------- seed ----------

def test_seed_derives_the_type_from_the_title(tmp_path):
    _seed(tmp_path, 843, "feat: Add SSO sign-in.")
    assert json.loads((tmp_path / ".changes" / "preview" / "843.json").read_text()) == {
        "pr": 843, "type": "feat", "summary": "Add SSO sign-in.", "notes": ""}


def test_seed_defaults_an_unprefixed_title_to_chore(tmp_path):
    _seed(tmp_path, 500, "Just some cleanup")
    assert json.loads(
        (tmp_path / ".changes" / "preview" / "500.json").read_text())["type"] == "chore"


def test_seed_cleans_up_a_revert_button_title(tmp_path):
    _seed(tmp_path, 900, 'Revert "feat: add SSO sign-in (#843)"')
    d = json.loads((tmp_path / ".changes" / "preview" / "900.json").read_text())
    assert d["type"] == "revert" and d["summary"] == "Reverted add SSO sign-in"


def test_seed_does_not_double_prefix_a_revert(tmp_path):
    _seed(tmp_path, 2, "revert: Reverted the retry default")
    assert json.loads((tmp_path / ".changes" / "preview" / "2.json").read_text()
                      )["summary"] == "Reverted the retry default"


def test_seed_refuses_a_placeholder_pr(tmp_path):
    assert _seed(tmp_path, 0, "feat: x") == 2
    assert not (tmp_path / "template.json").exists()


def test_seed_output_is_valid(tmp_path):
    # Whatever the bot pastes must pass the check an author will face.
    _seed(tmp_path, 12, "fix: Handle EINTR")
    assert fragments.validate_fragment(
        tmp_path / ".changes" / "preview" / "12.json") == []


def test_a_marker_cannot_be_smuggled_into_an_entry(tmp_path):
    # An entry renders inside a marked region; text that closes the marker would
    # break every later render of the file.
    for field in ("summary", "notes"):
        errs = fragments.validate_fragment(
            _at(tmp_path, _valid(**{field: "x <!-- /changelog:unreleased --> y"})))
        assert any("HTML comment" in e for e in errs)


def test_a_fragment_whose_filename_is_not_a_number_is_still_read(tmp_path):
    # The filename check only applies when the name is a number; a path like
    # preview/notes.json cannot be cross-checked, so it is read as written.
    _changes(tmp_path)
    (tmp_path / ".changes" / "preview" / "extra.json").write_text(
        json.dumps(_valid(pr=5)))
    assert [f["pr"] for f in fragments.load_preview(tmp_path / ".changes")] == [5]
