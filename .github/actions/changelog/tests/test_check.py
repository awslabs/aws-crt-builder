"""The CI gate."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import changelog  # noqa: E402
import check  # noqa: E402
import fragments  # noqa: E402
from helpers import _changes, _check, _check_paths, _paths, _seed, _write  # noqa: E402


def test_check_passes_when_fragment_present(tmp_path):
    _seed(tmp_path, 5, "feat: hello")
    assert changelog.main([
        "check", "--pr", "5", "--title", "feat: hello",
        "--changes-dir", str(tmp_path / ".changes")
    ]) == 0


def test_check_rejects_an_invalid_fragment(tmp_path, capsys):
    _changes(tmp_path)
    p = tmp_path / ".changes" / "preview" / "5.json"
    p.write_text(json.dumps(
        {"pr": 5, "type": "feat", "summary": "s", "notes": 7}))
    assert changelog.main(["check", "--pr", "5", "--title", "feat: x",
                    "--changes-dir", _changes(tmp_path)]) == 1
    assert "CHANGELOG_CHECK_REASON::invalid-fragment" in capsys.readouterr().out


def test_check_fails_on_pr_mismatch(tmp_path):
    _seed(tmp_path, 5, "feat: hello")
    src = tmp_path / ".changes" / "preview" / "5.json"
    dst = tmp_path / ".changes" / "preview" / "7.json"
    src.rename(dst)
    assert changelog.main([
        "check", "--pr", "7", "--title", "feat: hello",
        "--changes-dir", str(tmp_path / ".changes")
    ]) == 1


def test_chore_needs_no_fragment(tmp_path):
    _changes(tmp_path)
    for title in ("chore: tidy", "chore(ci): bump runner", "chore(release): 1.2.3"):
        assert _check(tmp_path, 1, title) == 0


def test_feat_fix_and_revert_all_need_a_fragment(tmp_path):
    _changes(tmp_path)
    for title in ("feat: x", "fix: y", 'Revert "feat: z (#9)"'):
        assert _check(tmp_path, 1, title) == 1


def test_revert_button_title_is_accepted(tmp_path):
    # GitHub's Revert button emits no `<type>:` prefix.
    assert fragments.parse_title('Revert "Fix CI issues (#538)"') == (
        "revert", 'Fix CI issues (#538)')
    _write(tmp_path, 4, "revert", summary='Revert "Fix CI issues".',
           notes="Broke the macos job.")
    assert _check(tmp_path, 4, 'Revert "Fix CI issues (#538)"') == 0


def test_title_without_a_recognised_prefix_fails(tmp_path):
    _changes(tmp_path)
    assert _check(tmp_path, 1, "Add more getters for metrics") == 1
    assert _check(tmp_path, 1, "perf: make it faster") == 1


def test_type_mismatch_between_title_and_fragment_fails(tmp_path):
    _write(tmp_path, 5, "chore")
    assert _check(tmp_path, 5, "feat: a real feature") == 1


def test_bot_author_waives_everything(tmp_path):
    _changes(tmp_path)
    assert _check(tmp_path, 6, "Bump actions/checkout from 4 to 7",
                  bot="dependabot[bot]") == 0


def test_missing_title_is_a_caller_error_not_an_author_error(tmp_path):
    assert changelog.main(["check", "--pr", "1", "--changes-dir", _changes(tmp_path)]) == 2


def test_check_reason_is_emitted_for_each_outcome(tmp_path, capsys):
    cases = [
        ("chore: x", "exempt-type"),
        ("feat: x", "missing-fragment"),
        ("nonsense title", "bad-title"),
    ]
    for title, expected in cases:
        _check(tmp_path, 1, title)
        assert f"CHANGELOG_CHECK_REASON::{expected}" in capsys.readouterr().out


def test_one_added_fragment_at_the_expected_path_passes(tmp_path):
    _write(tmp_path, 1259, "feat")
    p = _paths(tmp_path, ("added", ".changes/preview/1259.json"))
    assert _check_paths(tmp_path, 1259, "feat: x", p) == 0


def test_a_stray_fragment_for_another_pr_fails(tmp_path):
    # Would otherwise render an entry attributed to PR 9999.
    _write(tmp_path, 1259, "feat")
    _write(tmp_path, 9999, "feat")
    p = _paths(tmp_path,
               ("added", ".changes/preview/1259.json"),
               ("added", ".changes/preview/9999.json"))
    assert _check_paths(tmp_path, 1259, "feat: x", p) == 1


def test_fragment_at_the_wrong_path_fails(tmp_path):
    p = _paths(tmp_path, ("added", ".changes/1259.json"))
    assert _check_paths(tmp_path, 1259, "feat: x", p) == 1


def test_modifying_an_existing_fragment_fails(tmp_path):
    # Only reachable when the path already exists on the base branch: the files
    # API reports status against base, so a fragment added and then edited inside
    # one pull request stays `added`. Verified against real GitHub.
    _write(tmp_path, 1259, "feat")
    p = _paths(tmp_path, ("modified", ".changes/preview/1259.json"))
    assert _check_paths(tmp_path, 1259, "feat: x", p) == 1


def test_touching_anything_else_under_changes_fails(tmp_path):
    _write(tmp_path, 1259, "feat")
    p = _paths(tmp_path,
               ("added", ".changes/preview/1259.json"),
               ("modified", ".changes/README.md"))
    assert _check_paths(tmp_path, 1259, "feat: x", p) == 1


def test_chore_ignores_fragment_shape_entirely(tmp_path):
    p = _paths(tmp_path,
               ("added", ".changes/preview/9999.json"),
               ("modified", ".changes/README.md"))
    assert _check_paths(tmp_path, 1259, "chore: x", p) == 0


def test_no_changes_paths_still_reports_a_missing_fragment(tmp_path):
    # Must stay `missing-fragment` so the author still gets a template.
    p = _paths(tmp_path)
    assert _check_paths(tmp_path, 1259, "feat: x", p) == 1


def test_changes_outside_the_changes_dir_are_ignored(tmp_path):
    _write(tmp_path, 1259, "feat")
    p = _paths(tmp_path,
               ("modified", "source/event_loop.c"),
               ("added", ".changes/preview/1259.json"))
    assert _check_paths(tmp_path, 1259, "feat: x", p) == 0




def test_every_reason_the_gate_can_emit_is_exercised(tmp_path, capsys):
    """The reason tag is the action's only machine-readable output."""
    seen = set()

    def reason_of(rc_call):
        rc_call()
        out = capsys.readouterr().out
        for line in out.splitlines():
            if line.startswith("CHANGELOG_CHECK_REASON::"):
                seen.add(line.split("::", 1)[1])

    reason_of(lambda: _check(tmp_path, 1, "feat: x", bot="dependabot[bot]"))
    reason_of(lambda: _check(tmp_path, 1, "nonsense title"))
    reason_of(lambda: _check(tmp_path, 1, "chore: tidy"))
    reason_of(lambda: _check(tmp_path, 2, "feat: missing its fragment"))
    _write(tmp_path, 3, "feat", summary="")
    reason_of(lambda: _check(tmp_path, 3, "feat: invalid"))
    _changes(tmp_path)
    (tmp_path / ".changes" / "preview" / "4.json").write_text(json.dumps(
        {"pr": 9, "type": "feat", "summary": "s", "notes": ""}))
    reason_of(lambda: _check(tmp_path, 4, "feat: mismatched number"))
    _write(tmp_path, 5, "fix")
    reason_of(lambda: _check(tmp_path, 5, "feat: mismatched type"))
    _write(tmp_path, 6, "feat")
    reason_of(lambda: _check(tmp_path, 6, "feat: good"))
    paths = _paths(tmp_path, ("added", ".changes/preview/99.json"))
    reason_of(lambda: _check_paths(tmp_path, 7, "feat: someone else's", paths))
    paths = _paths(tmp_path, ("modified", ".changes/preview/8.json"))
    reason_of(lambda: _check_paths(tmp_path, 8, "feat: rewritten", paths))

    assert seen == {"waived-bot", "bad-title", "exempt-type", "missing-fragment",
                    "invalid-fragment", "pr-mismatch", "type-mismatch", "ok",
                    "stray-fragment", "modified-fragment"}
