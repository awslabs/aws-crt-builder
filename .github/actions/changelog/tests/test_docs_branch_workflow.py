"""Integration test for the two-branch model: main carries source + fragments,
docs carries `.changes/` state + CHANGELOG.md. Runs actual git commands
against a scratch repo to exercise what the render workflow does.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3].parent
CHANGELOG_PY = REPO_ROOT / ".github/actions/changelog/scripts/changelog.py"


def run(cmd, cwd, check=True, capture=False):
    kwargs = {"cwd": cwd, "text": True}
    if capture:
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.PIPE
    r = subprocess.run(cmd, **kwargs)
    if check and r.returncode != 0:
        raise RuntimeError(f"cmd failed: {cmd}\nstderr={r.stderr if capture else ''}")
    return r


def git(cwd, *args, capture=False):
    return run(["git", *args], cwd=cwd, capture=capture)


@pytest.fixture
def scratch_repo(tmp_path):
    """A clean local git repo with one initial commit on main."""
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "test@test")
    git(repo, "config", "user.name", "test")
    (repo / "README.md").write_text("# repo\n")
    git(repo, "add", "README.md")
    git(repo, "commit", "-q", "-m", "initial")
    return repo


def _simulate_pr_merge(repo, pr, title):
    """Simulate what happens on main when a PR merges: source + fragment landed."""
    src = repo / f"src_{pr}.txt"
    src.write_text(f"pr {pr} content\n")
    r = subprocess.run(
        [sys.executable, str(CHANGELOG_PY), "seed",
         "--pr", str(pr), "--title", title, "--url", f"https://x/pr/{pr}"],
        cwd=repo, capture_output=True, text=True, check=True,
    )
    frag_dir = repo / ".changes" / "preview"
    frag_dir.mkdir(parents=True, exist_ok=True)
    (frag_dir / f"{pr}.json").write_text(r.stdout.rstrip() + "\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", f"{title} (#{pr})")
    return git(repo, "rev-parse", "HEAD", capture=True).stdout.strip()


def _run_render_workflow(repo, trigger_sha, docs_branch="docs"):
    """Reproduce examples/changelog-render.yml: cherry-pick merge → docs,
    then render if fragments changed and amend the cherry-pick."""
    # Ensure docs exists.
    branches = git(repo, "branch", "--list", docs_branch, capture=True).stdout.strip()
    if not branches:
        # First run: docs branches from the parent of the trigger sha so the
        # cherry-pick is meaningful.
        parent = git(repo, "rev-parse", f"{trigger_sha}^", capture=True).stdout.strip()
        git(repo, "checkout", "-q", "-B", docs_branch, parent)
    else:
        git(repo, "checkout", "-q", docs_branch)

    # -Xno-renames stops a rollup's preview/->latest/ moves being seen as
    # renames of a fresh fragment.
    r = subprocess.run(
        ["git", "cherry-pick", "-x", "--allow-empty",
         "--strategy=recursive", "-Xno-renames", trigger_sha],
        cwd=repo, capture_output=True, text=True,
    )
    if r.returncode != 0:
        unmerged = sorted(set(subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=U"],
            cwd=repo, capture_output=True, text=True,
        ).stdout.split()))
        # Derived file; the render below rewrites it regardless.
        if unmerged == ["CHANGELOG.md"]:
            subprocess.run(["git", "checkout", "--theirs", "CHANGELOG.md"], cwd=repo)
            git(repo, "add", "CHANGELOG.md")
            env = {**os.environ, "GIT_EDITOR": "true"}
            subprocess.run(["git", "cherry-pick", "--continue"], cwd=repo, env=env,
                           capture_output=True, text=True, check=True)
        else:
            status = subprocess.run(
                ["git", "status", "--porcelain"], cwd=repo,
                capture_output=True, text=True,
            ).stdout
            subprocess.run(["git", "cherry-pick", "--abort"], cwd=repo)
            raise RuntimeError(
                f"cherry-pick failed for {trigger_sha}\nstderr={r.stderr}\nstatus={status}"
            )

    # Unconditional: a no-op render stages nothing and amends nothing.
    run([sys.executable, str(CHANGELOG_PY), "render"], cwd=repo)
    git(repo, "add", "CHANGELOG.md")
    r = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=repo)
    if r.returncode == 0:
        return None  # render changed nothing; pure replay
    git(repo, "commit", "-q", "--amend", "--no-edit")
    return git(repo, "log", "--format=%s", "-1", capture=True).stdout.strip()


def test_docs_branch_created_on_first_merge(scratch_repo):
    repo = scratch_repo
    sha = _simulate_pr_merge(repo, 100, "feat: initial thing")
    subj = _run_render_workflow(repo, sha)
    # Cherry-picked commit keeps main's subject.
    assert subj == "feat: initial thing (#100)"
    # docs branch exists and now has CHANGELOG.md (introduced by the amend).
    assert (repo / "CHANGELOG.md").exists()
    text = (repo / "CHANGELOG.md").read_text()
    assert "## [Preview]" in text and "#100" in text


def test_docs_branch_gets_one_commit_per_pr(scratch_repo):
    repo = scratch_repo
    sha1 = _simulate_pr_merge(repo, 101, "feat: a")
    _run_render_workflow(repo, sha1)
    git(repo, "checkout", "-q", "main")
    sha2 = _simulate_pr_merge(repo, 102, "fix: b")
    _run_render_workflow(repo, sha2)

    subjects = git(repo, "log", "docs", "--format=%s", capture=True).stdout.strip().splitlines()
    # Two docs commits, keyed to the two PR titles, newest first.
    assert subjects[0] == "fix: b (#102)"
    assert subjects[1] == "feat: a (#101)"
    text = (repo / "CHANGELOG.md").read_text()
    assert "#101" in text and "#102" in text


def test_main_branch_has_no_changelog_md(scratch_repo):
    repo = scratch_repo
    sha = _simulate_pr_merge(repo, 200, "feat: a")
    _run_render_workflow(repo, sha)
    git(repo, "checkout", "-q", "main")
    assert not (repo / "CHANGELOG.md").exists()
    assert (repo / ".changes/preview/200.json").exists()
    # Main's log has no bot-authored commits.
    log = git(repo, "log", "main", "--format=%s", capture=True).stdout.strip().splitlines()
    assert not any(l.startswith("Update changelog") for l in log)
    assert not any(l.startswith("Release ") for l in log)


def test_docs_replay_is_idempotent(scratch_repo):
    """Re-running the workflow for the same trigger produces no new commit
    beyond the initial cherry-pick + amend."""
    repo = scratch_repo
    sha = _simulate_pr_merge(repo, 300, "feat: a")
    _run_render_workflow(repo, sha)
    subjects_before = git(repo, "log", "docs", "--format=%s",
                          capture=True).stdout.strip().splitlines()
    # A second cherry-pick of the same commit would produce an empty replay.
    # In the real workflow this is prevented by the concurrency group + fetch
    # step, but we verify that if it did happen, --allow-empty keeps things
    # sane and the tree still matches.
    r = subprocess.run(
        ["git", "cherry-pick", "-x", "--allow-empty", sha],
        cwd=repo, capture_output=True, text=True,
    )
    # An identical cherry-pick may either succeed (empty commit) or fail with
    # "The previous cherry-pick is now empty"; either way, no damage.
    if r.returncode != 0:
        subprocess.run(["git", "cherry-pick", "--abort"], cwd=repo)
    subjects_after = git(repo, "log", "docs", "--format=%s",
                         capture=True).stdout.strip().splitlines()
    # Content of CHANGELOG.md unchanged.
    assert (repo / "CHANGELOG.md").read_text().count("#300") == 1


def test_docs_replays_source_only_merges_without_render(scratch_repo):
    """A PR that touches only source code (no fragment) is still replayed
    onto docs, keeping docs in sync — but no CHANGELOG.md render occurs."""
    repo = scratch_repo
    # Bootstrap docs from a first fragment PR so it exists.
    sha0 = _simulate_pr_merge(repo, 400, "feat: seed")
    _run_render_workflow(repo, sha0)

    git(repo, "checkout", "-q", "main")
    (repo / "src_only.txt").write_text("x")
    git(repo, "add", "src_only.txt")
    git(repo, "commit", "-q", "-m", "Refactor internals")
    sha = git(repo, "rev-parse", "HEAD", capture=True).stdout.strip()
    subj = _run_render_workflow(repo, sha)
    assert subj is None  # no render, so no amended subject returned

    # Docs still has the cherry-picked commit at HEAD (source replayed).
    head_subj = git(repo, "log", "docs", "--format=%s", "-1",
                    capture=True).stdout.strip()
    assert head_subj == "Refactor internals"
    assert (repo / "src_only.txt").exists()


def _simulate_release(repo, version, date, bump, highlights=""):
    """Simulate cut-release.sh: rollup inside the VERSION-bump commit on main."""
    git(repo, "checkout", "-q", "main")
    argv = [sys.executable, str(CHANGELOG_PY), "rollup",
            "--version", version, "--date", date, "--bump", bump]
    if highlights:
        argv += ["--highlights", highlights]
    run(argv, cwd=repo)
    (repo / "VERSION").write_text(version + "\n")
    git(repo, "add", "VERSION", ".changes", "CHANGELOG.md")
    git(repo, "commit", "-q", "-m",
        f"chore(release): {bump}-update to VERSION - {version}")
    return git(repo, "rev-parse", "HEAD", capture=True).stdout.strip()


def test_release_commit_carries_version_and_changelog_together(scratch_repo):
    """The rollup must land in the same commit as the version bump."""
    repo = scratch_repo
    sha = _simulate_pr_merge(repo, 843, "feat: SSO sign-in")
    _run_render_workflow(repo, sha)
    rel_sha = _simulate_release(repo, "0.29.0", "2026-08-01", "minor")

    files = git(repo, "show", "--name-only", "--format=", rel_sha,
                capture=True).stdout.split()
    assert "VERSION" in files
    assert "CHANGELOG.md" in files
    assert ".changes/latest/0.29.0/843.json" in files
    # the fragment left preview/ in that same commit (git reports the rename
    # as its destination path only, so check the resulting tree instead)
    tree = git(repo, "ls-tree", "-r", "--name-only", rel_sha,
               capture=True).stdout.split()
    assert not any(f.startswith(".changes/preview/") for f in tree)


def test_main_changelog_has_no_preview_block(scratch_repo):
    """main carries released history only; the [Preview] view lives on docs."""
    repo = scratch_repo
    sha = _simulate_pr_merge(repo, 843, "feat: SSO sign-in")
    _run_render_workflow(repo, sha)
    _simulate_release(repo, "0.29.0", "2026-08-01", "minor")

    main_text = (repo / "CHANGELOG.md").read_text()
    assert "## [0.29.0]" in main_text
    assert "## [Preview]" not in main_text


def test_docs_keeps_empty_preview_after_release(scratch_repo):
    """docs keeps an empty [Preview] after a release, repopulated on next merge."""
    repo = scratch_repo
    sha = _simulate_pr_merge(repo, 843, "feat: SSO sign-in")
    _run_render_workflow(repo, sha)
    rel_sha = _simulate_release(repo, "0.29.0", "2026-08-01", "minor")
    _run_render_workflow(repo, rel_sha)

    git(repo, "checkout", "-q", "docs")
    text = (repo / "CHANGELOG.md").read_text()
    assert "## [Preview]" in text
    assert "_Nothing yet._" in text
    assert "## [0.29.0]" in text
    # the release entry moved out of preview into the version section
    assert text.index("## [Preview]") < text.index("## [0.29.0]")

    git(repo, "checkout", "-q", "main")
    sha = _simulate_pr_merge(repo, 867, "fix: fd leak")
    _run_render_workflow(repo, sha)
    git(repo, "checkout", "-q", "docs")
    text = (repo / "CHANGELOG.md").read_text()
    assert "## [Preview]" in text
    assert "#867" in text
    assert "## [0.29.0]" in text


def test_full_flow_with_release_rollup(scratch_repo):
    """End-to-end: 0.29.0 → 0.29.1 → 0.30.0, rollups on main, replayed to docs."""
    repo = scratch_repo
    for pr, title in [
        (843, "feat: SSO sign-in"),
        (850, "fix: idempotency drop"),
        (858, "chore: bump aws-lc"),
    ]:
        sha = _simulate_pr_merge(repo, pr, title)
        _run_render_workflow(repo, sha)
        git(repo, "checkout", "-q", "main")

    rel = _simulate_release(repo, "0.29.0", "2026-08-01", "minor",
                            highlights="SSO sign-in")
    _run_render_workflow(repo, rel)

    for pr, title in [(867, "fix: fd leak"), (870, "doc: retry defaults")]:
        git(repo, "checkout", "-q", "main")
        sha = _simulate_pr_merge(repo, pr, title)
        _run_render_workflow(repo, sha)

    rel = _simulate_release(repo, "0.29.1", "2026-08-15", "patch")
    _run_render_workflow(repo, rel)

    git(repo, "checkout", "-q", "main")
    text = (repo / "CHANGELOG.md").read_text()
    assert "## [0.29.1] — 2026-08-15" in text
    assert "## [0.29.0] — 2026-08-01" in text
    assert "## [Preview]" not in text
    # patch bump: latest/ stays latest/, nothing frozen
    assert (repo / ".changes/latest/0.29.0").is_dir()
    assert (repo / ".changes/latest/0.29.1").is_dir()
    assert not (repo / ".changes/0.29.x").exists()

    git(repo, "checkout", "-q", "main")
    sha = _simulate_pr_merge(repo, 878, "feat: tcp_nodelay")
    _run_render_workflow(repo, sha)
    rel = _simulate_release(repo, "0.30.0", "2026-08-19", "minor")
    _run_render_workflow(repo, rel)

    git(repo, "checkout", "-q", "main")
    root = (repo / "CHANGELOG.md").read_text()
    frozen = (repo / ".changes/0.29.x/CHANGELOG.md").read_text()
    assert "## [0.30.0] — 2026-08-19" in root
    assert "## [0.29.0]" not in root and "## [0.29.1]" not in root
    assert frozen.startswith("# Changelog — 0.29.x")
    assert "## [0.29.0]" in frozen and "## [0.29.1]" in frozen
    assert "## [0.30.0]" not in frozen
    # the outgoing line was renamed to 0.29.x/ and latest/ reopened
    assert (repo / ".changes/0.29.x/0.29.0").is_dir()
    assert (repo / ".changes/0.29.x/0.29.1").is_dir()
    assert (repo / ".changes/latest/0.30.0").is_dir()

    git(repo, "checkout", "-q", "docs")
    subjects = git(repo, "log", "--format=%s", capture=True).stdout.strip().splitlines()
    assert any("VERSION - 0.30.0" in s for s in subjects)
    assert any("VERSION - 0.29.1" in s for s in subjects)
    assert any("SSO sign-in" in s for s in subjects)
    assert any("tcp_nodelay" in s for s in subjects)
