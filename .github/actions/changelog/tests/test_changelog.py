"""Local tests: python3 -m pytest .github/actions/changelog/tests -v"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import changelog as cl  # noqa: E402


def _seed(tmp_path, pr, title):
    return cl.main([
        "seed", "--pr", str(pr), "--title", title, "--url", f"https://x/pr/{pr}",
        "--changes-dir", str(tmp_path / ".changes"),
    ])


def _render(tmp_path):
    cl.main([
        "render",
        "--changes-dir", str(tmp_path / ".changes"),
        "--changelog", str(tmp_path / "CHANGELOG.md"),
    ])
    return (tmp_path / "CHANGELOG.md").read_text()


def _rollup(tmp_path, version, date, bump=None, highlights=""):
    argv = [
        "rollup", "--version", version, "--date", date,
        "--changes-dir", str(tmp_path / ".changes"),
        "--changelog", str(tmp_path / "CHANGELOG.md"),
    ]
    if bump:
        argv += ["--bump", bump]
    if highlights:
        argv += ["--highlights", highlights]
    return cl.main(argv)


# ---------- seed / validate ----------

def test_seed_writes_fragment(tmp_path):
    _seed(tmp_path, 843, "feat: Add SSO sign-in for enterprise accounts.")
    p = tmp_path / ".changes" / "preview" / "843.json"
    data = json.loads(p.read_text())
    assert data == {
        "pr": 843,
        "type": "feat",
        "summary": "Add SSO sign-in for enterprise accounts.",
        "url": "https://x/pr/843",
        "notes": "",
    }


def test_seed_no_prefix_becomes_chore(tmp_path):
    _seed(tmp_path, 500, "Just some cleanup")
    d = json.loads((tmp_path / ".changes" / "preview" / "500.json").read_text())
    assert d["type"] == "chore"
    assert d["summary"] == "Just some cleanup"


def test_seed_does_not_overwrite_without_force(tmp_path):
    _seed(tmp_path, 1, "feat: a")
    # Non-zero, so a caller cannot mistake "declined" for "wrote it".
    assert _seed(tmp_path, 1, "feat: b") == 1
    d = json.loads((tmp_path / ".changes" / "preview" / "1.json").read_text())
    assert d["summary"] == "a"


def test_seed_accepts_placeholder_pr_zero(tmp_path):
    assert _seed(tmp_path, 0, "feat: something") == 0
    assert (tmp_path / ".changes" / "preview" / "0.json").exists()


def test_validate_rejects_missing_fields(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"pr": 1, "type": "feat"}))
    assert cl.main(["validate", str(bad)]) == 1


def test_validate_rejects_bad_type(tmp_path):
    p = tmp_path / "x.json"
    p.write_text(json.dumps({"pr": 1, "type": "bogus", "summary": "x", "url": "u"}))
    assert cl.main(["validate", str(p)]) == 1


def test_validate_accepts_good_dir(tmp_path):
    _seed(tmp_path, 1, "feat: a")
    assert cl.main(["validate", str(tmp_path / ".changes" / "preview")]) == 0


# ---------- check ----------

def test_check_missing_fragment_fails(tmp_path):
    (tmp_path / ".changes" / "preview").mkdir(parents=True)
    assert cl.main([
        "check", "--pr", "5", "--title", "feat: hello",
        "--changes-dir", str(tmp_path / ".changes")
    ]) == 1


def test_check_passes_when_fragment_present(tmp_path):
    _seed(tmp_path, 5, "feat: hello")
    assert cl.main([
        "check", "--pr", "5", "--title", "feat: hello",
        "--changes-dir", str(tmp_path / ".changes")
    ]) == 0


def test_check_fails_on_pr_mismatch(tmp_path):
    _seed(tmp_path, 5, "feat: hello")
    src = tmp_path / ".changes" / "preview" / "5.json"
    dst = tmp_path / ".changes" / "preview" / "7.json"
    src.rename(dst)
    assert cl.main([
        "check", "--pr", "7", "--title", "feat: hello",
        "--changes-dir", str(tmp_path / ".changes")
    ]) == 1


# ---------- render ----------

def test_render_only_preview_when_no_releases(tmp_path):
    _seed(tmp_path, 843, "feat: SSO sign-in")
    text = _render(tmp_path)
    assert text.startswith("# Changelog")
    assert "## [Preview]" in text
    assert "### Features" in text
    assert text.count("## [") == 1


def test_render_groups_by_category_and_hides_chore(tmp_path):
    _seed(tmp_path, 843, "feat: Add SSO sign-in")
    _seed(tmp_path, 850, "fix: retry token drop")
    _seed(tmp_path, 855, 'Revert "feat: something earlier"')
    _seed(tmp_path, 858, "chore: bump aws-lc to 1.34")
    text = _render(tmp_path)

    assert "### Features" in text
    assert "### Fixes" in text
    assert "### Reverts" in text
    assert "### Maintenance" not in text  # chore hidden from customer view
    # Order: Features -> Fixes -> Reverts
    assert text.index("### Features") < text.index("### Fixes") < text.index("### Reverts")


def test_render_omits_reverts_section_when_none(tmp_path):
    _seed(tmp_path, 1, "feat: a")
    _seed(tmp_path, 2, "fix: b")
    text = _render(tmp_path)
    assert "### Reverts" not in text


def test_render_is_idempotent(tmp_path):
    _seed(tmp_path, 1, "feat: a")
    a = _render(tmp_path)
    b = _render(tmp_path)
    assert a == b


def test_render_preserves_summary_punctuation(tmp_path):
    _seed(tmp_path, 1, "fix: Retries no longer drop 429?")
    _seed(tmp_path, 2, "fix: Handle overflow!")
    _seed(tmp_path, 3, "feat: Add SSO")
    text = _render(tmp_path)
    assert "429? (#1)" in text
    assert "overflow! (#2)" in text
    assert "SSO. (#3)" in text
    assert "429?." not in text and "overflow!." not in text


# ---------- rollup: patch ----------

def test_rollup_patch_moves_fragments_and_creates_meta(tmp_path):
    _seed(tmp_path, 1, "feat: initial")
    _seed(tmp_path, 2, "chore: bump")
    assert _rollup(tmp_path, "0.29.0", "2026-08-01") == 0
    assert list((tmp_path / ".changes" / "preview").glob("*.json")) == []
    rel = tmp_path / ".changes" / "latest" / "0.29.0"
    meta = json.loads((rel / "_meta.json").read_text())
    assert meta["version"] == "0.29.0" and meta["date"] == "2026-08-01"
    assert {p.name for p in rel.glob("*.json") if p.name != "_meta.json"} == {"1.json", "2.json"}


def test_rollup_patch_accretes_into_same_line(tmp_path):
    _seed(tmp_path, 1, "feat: a")
    _rollup(tmp_path, "0.29.0", "2026-08-01")
    _seed(tmp_path, 2, "fix: b")
    _rollup(tmp_path, "0.29.1", "2026-08-15")
    latest = tmp_path / ".changes" / "latest"
    assert (latest / "0.29.0").is_dir() and (latest / "0.29.1").is_dir()
    assert not (tmp_path / ".changes" / "0.29.x").exists()
    text = (tmp_path / "CHANGELOG.md").read_text()
    assert "## [0.29.1] — 2026-08-15" in text
    assert "## [0.29.0] — 2026-08-01" in text
    assert text.index("[0.29.1]") < text.index("[0.29.0]")


def test_rollup_root_hides_chore_only_release(tmp_path):
    _seed(tmp_path, 1, "chore: internal cleanup")
    _rollup(tmp_path, "0.29.0", "2026-08-01")
    text = (tmp_path / "CHANGELOG.md").read_text()
    assert "## [0.29.0]" in text
    assert "### Maintenance" not in text


def test_rollup_empty_preview_fails(tmp_path):
    (tmp_path / ".changes" / "preview").mkdir(parents=True)
    assert _rollup(tmp_path, "0.1.0", "2026-01-01") == 1


# ---------- rollup: minor / freeze ----------

def test_rollup_minor_freezes_previous_line(tmp_path):
    _seed(tmp_path, 1, "feat: a")
    _rollup(tmp_path, "0.29.0", "2026-08-01")
    _seed(tmp_path, 2, "fix: b")
    _rollup(tmp_path, "0.29.1", "2026-08-15")
    _seed(tmp_path, 3, "feat: tcp_nodelay")
    _rollup(tmp_path, "0.30.0", "2026-08-19")

    changes = tmp_path / ".changes"
    assert (changes / "latest" / "0.30.0").is_dir()
    assert not (changes / "latest" / "0.29.0").exists()
    assert (changes / "0.29.x" / "0.29.0").is_dir()
    assert (changes / "0.29.x" / "0.29.1").is_dir()
    frozen = (changes / "0.29.x" / "CHANGELOG.md").read_text()
    assert "## [Preview]" not in frozen
    assert frozen.startswith("# Changelog — 0.29.x")
    assert "## [0.29.1]" in frozen and "## [0.29.0]" in frozen
    assert "## [0.30.0]" not in frozen

    root = (tmp_path / "CHANGELOG.md").read_text()
    assert "## [0.30.0]" in root
    assert "## [0.29.0]" not in root and "## [0.29.1]" not in root
    assert "## [Preview]" in root


def test_rollup_minor_from_empty_latest(tmp_path):
    _seed(tmp_path, 1, "feat: initial")
    assert _rollup(tmp_path, "0.1.0", "2026-01-01") == 0
    assert (tmp_path / ".changes" / "latest" / "0.1.0").is_dir()
    assert [p for p in (tmp_path / ".changes").iterdir()
            if p.is_dir() and p.name.endswith(".x")] == []


def test_rollup_major_freezes_current_minor_line(tmp_path):
    _seed(tmp_path, 1, "feat: a")
    _rollup(tmp_path, "0.29.0", "2026-08-01")
    _seed(tmp_path, 2, "feat: big change")
    _rollup(tmp_path, "1.0.0", "2027-01-01")
    changes = tmp_path / ".changes"
    assert (changes / "0.29.x" / "0.29.0").is_dir()
    assert (changes / "latest" / "1.0.0").is_dir()


def test_rollup_rejects_duplicate_version(tmp_path):
    _seed(tmp_path, 1, "feat: a")
    _rollup(tmp_path, "0.29.0", "2026-08-01")
    _seed(tmp_path, 2, "fix: b")
    assert _rollup(tmp_path, "0.29.0", "2026-08-02") == 2


def test_rollup_bad_semver_rejected(tmp_path):
    _seed(tmp_path, 1, "feat: a")
    assert _rollup(tmp_path, "notaversion", "2026-01-01") == 2


def test_rollup_bad_date_rejected(tmp_path):
    _seed(tmp_path, 1, "feat: a")
    assert _rollup(tmp_path, "0.1.0", "not-a-date") == 2


def test_rollup_rejects_downgrade_in_latest(tmp_path):
    _seed(tmp_path, 1, "feat: a")
    _rollup(tmp_path, "0.29.1", "2026-08-15")
    _seed(tmp_path, 2, "fix: b")
    assert _rollup(tmp_path, "0.29.0", "2026-08-20") == 2


def test_rollup_rejects_downgrade_vs_frozen_line(tmp_path):
    _seed(tmp_path, 1, "feat: a")
    _rollup(tmp_path, "0.29.0", "2026-08-01")
    _seed(tmp_path, 2, "feat: b")
    _rollup(tmp_path, "0.30.0", "2026-08-19")
    _seed(tmp_path, 3, "fix: c")
    assert _rollup(tmp_path, "0.29.1", "2026-08-20") == 2


def test_rollup_patch_requires_matching_minor(tmp_path):
    _seed(tmp_path, 1, "feat: a")
    _rollup(tmp_path, "0.29.0", "2026-08-01")
    _seed(tmp_path, 2, "fix: b")
    argv = [
        "rollup", "--version", "0.30.0", "--date", "2026-08-19",
        "--bump", "patch",
        "--changes-dir", str(tmp_path / ".changes"),
        "--changelog", str(tmp_path / "CHANGELOG.md"),
    ]
    assert cl.main(argv) == 2


# ---------- resilience ----------

def test_render_skips_malformed_fragment(tmp_path, capsys):
    _seed(tmp_path, 1, "feat: good")
    (tmp_path / ".changes" / "preview" / "2.json").write_text("{not valid json")
    text = _render(tmp_path)
    assert "#1" in text
    err = capsys.readouterr().err
    assert "WARN" in err and "2.json" in err


def test_render_skips_schema_invalid_fragment(tmp_path, capsys):
    _seed(tmp_path, 1, "feat: good")
    (tmp_path / ".changes" / "preview" / "2.json").write_text(
        json.dumps({"pr": 2, "type": "feat"})  # missing summary+url
    )
    text = _render(tmp_path)
    assert "#1" in text
    assert "#2" not in text
    err = capsys.readouterr().err
    assert "WARN" in err


def test_render_skips_release_with_malformed_meta(tmp_path, capsys):
    _seed(tmp_path, 1, "feat: a")
    _rollup(tmp_path, "0.29.0", "2026-08-01")
    (tmp_path / ".changes" / "latest" / "0.29.0" / "_meta.json").write_text(
        '{"version": "0.29.0"}'
    )
    text = _render(tmp_path)
    assert "## [0.29.0]" not in text
    err = capsys.readouterr().err
    assert "WARN" in err


def test_render_excludes_frozen_lines(tmp_path):
    _seed(tmp_path, 1, "feat: a")
    _rollup(tmp_path, "0.29.0", "2026-08-01")
    _seed(tmp_path, 2, "feat: b")
    _rollup(tmp_path, "0.30.0", "2026-08-19")
    root = (tmp_path / "CHANGELOG.md").read_text()
    assert "## [0.30.0]" in root and "## [0.29.0]" not in root
    frozen = (tmp_path / ".changes" / "0.29.x" / "CHANGELOG.md").read_text()
    assert "## [0.29.0]" in frozen and "## [0.30.0]" not in frozen


def test_rollup_recovers_from_half_freeze(tmp_path):
    _seed(tmp_path, 1, "feat: a")
    _rollup(tmp_path, "0.29.0", "2026-08-01")
    latest = tmp_path / ".changes" / "latest"
    frozen = tmp_path / ".changes" / "0.29.x"
    latest.rename(frozen)
    latest.mkdir()
    _seed(tmp_path, 2, "feat: b")
    assert _rollup(tmp_path, "0.30.0", "2026-08-19") == 2

    rc = cl.main([
        "freeze-snapshot", "--line", "0.29.x",
        "--changes-dir", str(tmp_path / ".changes"),
    ])
    assert rc == 0
    assert (frozen / "CHANGELOG.md").exists()
    assert _rollup(tmp_path, "0.30.0", "2026-08-19") == 0


def test_freeze_snapshot_rejects_non_frozen_dir(tmp_path):
    (tmp_path / ".changes" / "not-a-line").mkdir(parents=True)
    rc = cl.main([
        "freeze-snapshot", "--line", "not-a-line",
        "--changes-dir", str(tmp_path / ".changes"),
    ])
    assert rc == 2


# ---------- list smoke ----------

def test_list_smoke(tmp_path, capsys):
    _seed(tmp_path, 1, "feat: a")
    _rollup(tmp_path, "0.1.0", "2026-01-01")
    _seed(tmp_path, 2, "fix: b")
    assert cl.main(["list", "--changes-dir", str(tmp_path / ".changes")]) == 0
    out = capsys.readouterr().out
    assert "preview" in out and "latest" in out


# ---------- full lifecycle ----------

def test_full_lifecycle_end_to_end(tmp_path):
    _seed(tmp_path, 843, "feat: SSO sign-in")
    _seed(tmp_path, 850, "fix: idempotency token drop on 429")
    _seed(tmp_path, 858, "chore: bump aws-lc")
    _rollup(tmp_path, "0.29.0", "2026-08-01", highlights="SSO sign-in")

    _seed(tmp_path, 867, "fix: leaking fd on socket teardown")
    _seed(tmp_path, 870, 'Revert "feat: clarify retry defaults"')
    _seed(tmp_path, 872, "fix: null-deref in event loop")
    _render(tmp_path)

    root = (tmp_path / "CHANGELOG.md").read_text()
    assert "## [Preview]" in root
    assert "#867" in root and "#870" in root and "#872" in root

    _rollup(tmp_path, "0.29.1", "2026-08-15")
    root = (tmp_path / "CHANGELOG.md").read_text()
    assert "## [0.29.1] — 2026-08-15" in root
    assert "## [0.29.0] — 2026-08-01" in root
    assert not (tmp_path / ".changes" / "0.29.x").exists()

    _seed(tmp_path, 875, "fix: retry backoff off-by-one")
    _seed(tmp_path, 878, "feat: add tcp_nodelay to socket options")
    _rollup(tmp_path, "0.30.0", "2026-08-19")

    frozen = (tmp_path / ".changes" / "0.29.x" / "CHANGELOG.md").read_text()
    assert frozen.startswith("# Changelog — 0.29.x")
    assert "## [0.29.1]" in frozen and "## [0.29.0]" in frozen
    assert "## [Preview]" not in frozen

    root = (tmp_path / "CHANGELOG.md").read_text()
    assert "## [0.30.0] — 2026-08-19" in root
    assert "## [0.29.1]" not in root and "## [0.29.0]" not in root
    assert "## [Preview]" in root


# ---------- type set, title forms, and the fragment waiver ----------

def _changes(tmp_path):
    d = tmp_path / ".changes" / "preview"
    d.mkdir(parents=True, exist_ok=True)
    return str(tmp_path / ".changes")


def _write(tmp_path, pr, typ, summary="s", notes=""):
    _changes(tmp_path)
    (tmp_path / ".changes" / "preview" / f"{pr}.json").write_text(json.dumps(
        {"pr": pr, "type": typ, "summary": summary,
         "url": f"https://x/pull/{pr}", "notes": notes}) + "\n")


def _check(tmp_path, pr, title, bot=""):
    args = ["check", "--pr", str(pr), "--title", title,
            "--changes-dir", _changes(tmp_path)]
    if bot:
        args += ["--bot-author", bot]
    return cl.main(args)


def test_valid_types_are_exactly_the_four():
    assert cl.VALID_TYPES == {"feat", "fix", "chore", "revert"}


def test_doc_is_no_longer_a_type(tmp_path):
    # Neither the title form nor the fragment field accepts it any more.
    assert cl.parse_title("doc: add a design doc") == (None, "doc: add a design doc")
    assert cl.parse_title("docs: add a design doc") == (None, "docs: add a design doc")
    _write(tmp_path, 1, "doc")
    assert _check(tmp_path, 1, "feat: x") == 1


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
    assert cl.parse_title('Revert "Fix CI issues (#538)"') == (
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
    assert cl.main(["check", "--pr", "1", "--changes-dir", _changes(tmp_path)]) == 2


def test_check_reason_is_emitted_for_each_outcome(tmp_path, capsys):
    cases = [
        ("chore: x", None, "exempt-type"),
        ("feat: x", None, "missing-fragment"),
        ("nonsense title", None, "bad-title"),
    ]
    for title, _frag, expected in cases:
        _check(tmp_path, 1, title)
        assert f"CHANGELOG_CHECK_REASON::{expected}" in capsys.readouterr().out


def test_reverts_render_under_their_own_heading(tmp_path):
    _write(tmp_path, 1, "revert", summary='Revert "feat: a".', notes="Broke X.")
    text = _render(tmp_path)
    assert "### Reverts" in text
    assert "Broke X." in text


# ---------- exactly one fragment, at the right path, added ----------

def _paths(tmp_path, *entries):
    f = tmp_path / "paths.tsv"
    f.write_text("".join(f"{st}\t{p}\n" for st, p in entries))
    return str(f)


def _check_paths(tmp_path, pr, title, paths_file):
    return cl.main([
        "check", "--pr", str(pr), "--title", title,
        "--changes-dir", _changes(tmp_path),
        "--changed-paths-file", paths_file,
        "--changes-prefix", ".changes",
    ])


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


# ---------- the version decides the bump ----------

def _preview(tmp_path, name, text):
    p = tmp_path / ".changes" / "preview" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def test_rollup_rejects_a_bump_that_contradicts_the_version(tmp_path):
    _seed(tmp_path, 1, "feat: a")
    assert _rollup(tmp_path, "0.29.0", "2026-01-01") == 0
    _seed(tmp_path, 2, "feat: b")
    # A patch version declared as a minor used to freeze 0.29.x while opening
    # latest/0.29.1, splitting the line and wedging every later minor rollup.
    assert _rollup(tmp_path, "0.29.1", "2026-02-01", bump="minor") == 2
    assert not (tmp_path / ".changes" / "0.29.x").exists()
    assert "## [0.29.0]" in (tmp_path / "CHANGELOG.md").read_text()


def test_rollup_rejects_a_major_bump_on_a_minor_version(tmp_path):
    _seed(tmp_path, 1, "feat: a")
    _rollup(tmp_path, "0.29.0", "2026-01-01")
    _seed(tmp_path, 2, "feat: b")
    assert _rollup(tmp_path, "0.30.0", "2026-02-01", bump="major") == 2


def test_rollup_accepts_a_bump_that_agrees(tmp_path):
    _seed(tmp_path, 1, "feat: a")
    _rollup(tmp_path, "0.29.0", "2026-01-01")
    _seed(tmp_path, 2, "feat: b")
    assert _rollup(tmp_path, "0.29.1", "2026-02-01", bump="patch") == 0


def test_rollup_refuses_to_reopen_a_frozen_line(tmp_path):
    _seed(tmp_path, 1, "feat: a")
    _rollup(tmp_path, "0.29.0", "2026-01-01")
    _seed(tmp_path, 2, "feat: b")
    _rollup(tmp_path, "0.30.0", "2026-02-01")
    _seed(tmp_path, 3, "fix: backport")
    assert _rollup(tmp_path, "0.29.1", "2026-03-01") == 2
    assert not (tmp_path / ".changes" / "latest" / "0.29.1").exists()


# ---------- a release never silently drops a fragment ----------

def test_rollup_refuses_a_malformed_fragment(tmp_path):
    _seed(tmp_path, 1, "feat: a")
    _preview(tmp_path, "2.json", "{ not json")
    assert _rollup(tmp_path, "0.1.0", "2026-01-01") == 2
    assert (tmp_path / ".changes" / "preview" / "1.json").exists()
    assert not (tmp_path / ".changes" / "latest" / "0.1.0").exists()


def test_rollup_refuses_a_schema_invalid_fragment(tmp_path):
    _seed(tmp_path, 1, "feat: a")
    _preview(tmp_path, "2.json", json.dumps(
        {"pr": "two", "type": "feat", "summary": "", "url": "u"}))
    assert _rollup(tmp_path, "0.1.0", "2026-01-01") == 2


def test_rollup_refuses_a_fragment_whose_name_and_pr_disagree(tmp_path):
    # Would render the entry under someone else's number.
    _preview(tmp_path, "1.json", json.dumps(
        {"pr": 999, "type": "feat", "summary": "Mislabelled", "url": "u", "notes": ""}))
    assert _rollup(tmp_path, "0.1.0", "2026-01-01") == 2


def test_rollup_reports_an_all_invalid_preview_as_invalid_not_empty(tmp_path):
    _preview(tmp_path, "1.json", "{ not json")
    assert _rollup(tmp_path, "0.1.0", "2026-01-01") == 2


# ---------- one hiding policy, one placeholder ----------

def test_frozen_line_hides_chores_like_the_root_does(tmp_path):
    _seed(tmp_path, 1, "feat: visible")
    _seed(tmp_path, 2, "chore: internal only")
    _rollup(tmp_path, "0.1.0", "2026-01-01")
    _seed(tmp_path, 3, "feat: next line")
    _rollup(tmp_path, "0.2.0", "2026-02-01")
    frozen = (tmp_path / ".changes" / "0.1.x" / "CHANGELOG.md").read_text()
    assert "visible" in frozen
    assert "internal only" not in frozen and "### Maintenance" not in frozen


def test_a_release_with_nothing_visible_has_no_placeholder(tmp_path):
    _seed(tmp_path, 1, "chore: internal only")
    _rollup(tmp_path, "0.1.0", "2026-01-01")
    root = (tmp_path / "CHANGELOG.md").read_text()
    released = root.split("## [0.1.0]", 1)[1]
    assert "_Nothing yet._" not in released
    # The empty preview block keeps it, so the file never looks truncated.
    assert "_Nothing yet._" in root


# ---------- changed-paths hygiene ----------

def test_changes_outside_the_changes_dir_are_ignored(tmp_path):
    _write(tmp_path, 1259, "feat")
    p = _paths(tmp_path,
               ("modified", "source/event_loop.c"),
               ("added", ".changes/preview/1259.json"))
    assert _check_paths(tmp_path, 1259, "feat: x", p) == 0


def test_validate_rejects_a_missing_target(tmp_path):
    assert cl.main(["validate", str(tmp_path / "nope")]) == 2
