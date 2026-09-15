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
    _seed(tmp_path, 1, "feat: b")
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
        "check", "--pr", "5", "--changes-dir", str(tmp_path / ".changes")
    ]) == 1


def test_check_passes_when_fragment_present(tmp_path):
    _seed(tmp_path, 5, "feat: hello")
    assert cl.main([
        "check", "--pr", "5", "--changes-dir", str(tmp_path / ".changes")
    ]) == 0


def test_check_fails_on_pr_mismatch(tmp_path):
    _seed(tmp_path, 5, "feat: hello")
    src = tmp_path / ".changes" / "preview" / "5.json"
    dst = tmp_path / ".changes" / "preview" / "7.json"
    src.rename(dst)
    assert cl.main([
        "check", "--pr", "7", "--changes-dir", str(tmp_path / ".changes")
    ]) == 1


# ---------- render ----------

def test_render_only_preview_when_no_releases(tmp_path):
    _seed(tmp_path, 843, "feat: SSO sign-in")
    text = _render(tmp_path)
    assert text.startswith("# Changelog")
    assert cl.PREVIEW_START in text and cl.PREVIEW_END in text
    assert "### Features" in text
    assert "## [" not in text.split(cl.PREVIEW_END, 1)[1]


def test_render_groups_by_category_and_hides_chore(tmp_path):
    _seed(tmp_path, 843, "feat: Add SSO sign-in")
    _seed(tmp_path, 850, "fix: retry token drop")
    _seed(tmp_path, 855, "doc: retry defaults")
    _seed(tmp_path, 858, "chore: bump aws-lc to 1.34")
    text = _render(tmp_path)

    assert "### Features" in text
    assert "### Fixes" in text
    assert "### Docs" in text
    assert "### Maintenance" not in text  # chore hidden from customer view
    # Order: Features → Fixes → Docs
    assert text.index("### Features") < text.index("### Fixes") < text.index("### Docs")


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
    assert cl.PREVIEW_START not in frozen
    assert frozen.startswith("# Changelog — 0.29.x")
    assert "## [0.29.1]" in frozen and "## [0.29.0]" in frozen
    assert "## [0.30.0]" not in frozen

    root = (tmp_path / "CHANGELOG.md").read_text()
    assert "## [0.30.0]" in root
    assert "## [0.29.0]" not in root and "## [0.29.1]" not in root
    assert cl.PREVIEW_START in root


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


# ---------- revert ----------

def test_revert_creates_fragment_keeps_original(tmp_path):
    _seed(tmp_path, 843, "feat: SSO sign-in")
    cl.main([
        "revert", "--original-pr", "843", "--revert-pr", "900",
        "--url", "https://x/pr/900",
        "--changes-dir", str(tmp_path / ".changes"),
    ])
    unrel = tmp_path / ".changes" / "preview"
    assert (unrel / "843.json").exists()
    r = json.loads((unrel / "900.json").read_text())
    assert r["type"] == "revert"
    assert "SSO sign-in" in r["summary"]
    text = _render(tmp_path)
    assert "#843" in text and "#900" in text


def test_revert_looks_up_original_in_latest(tmp_path):
    _seed(tmp_path, 843, "feat: SSO sign-in")
    _rollup(tmp_path, "0.29.0", "2026-08-01")
    cl.main([
        "revert", "--original-pr", "843", "--revert-pr", "900",
        "--url", "https://x/pr/900",
        "--changes-dir", str(tmp_path / ".changes"),
    ])
    r = json.loads((tmp_path / ".changes" / "preview" / "900.json").read_text())
    assert "SSO sign-in" in r["summary"]


def test_revert_looks_up_original_in_frozen_line(tmp_path):
    _seed(tmp_path, 843, "feat: SSO sign-in")
    _rollup(tmp_path, "0.29.0", "2026-08-01")
    _seed(tmp_path, 999, "feat: bump")
    _rollup(tmp_path, "0.30.0", "2026-08-19")
    cl.main([
        "revert", "--original-pr", "843", "--revert-pr", "900",
        "--url", "https://x/pr/900",
        "--changes-dir", str(tmp_path / ".changes"),
    ])
    r = json.loads((tmp_path / ".changes" / "preview" / "900.json").read_text())
    assert "SSO sign-in" in r["summary"]


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
    _seed(tmp_path, 870, "doc: clarify retry defaults")
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
    assert cl.PREVIEW_START not in frozen

    root = (tmp_path / "CHANGELOG.md").read_text()
    assert "## [0.30.0] — 2026-08-19" in root
    assert "## [0.29.1]" not in root and "## [0.29.0]" not in root
    assert cl.PREVIEW_START in root
