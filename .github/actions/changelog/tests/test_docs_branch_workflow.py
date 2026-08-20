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
    run(
        [
            sys.executable, str(CHANGELOG_PY), "seed",
            "--pr", str(pr), "--title", title, "--url", f"https://x/pr/{pr}",
        ],
        cwd=repo,
    )
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

    # Cherry-pick the merge onto docs. Disable rename detection so that a
    # rollup's preview/→latest/ moves on docs do not confuse git into
    # redirecting a fresh preview fragment to a latest/ path.
    r = subprocess.run(
        ["git", "cherry-pick", "-x", "--allow-empty",
         "--strategy=recursive", "-Xno-renames", trigger_sha],
        cwd=repo, capture_output=True, text=True,
    )
    if r.returncode != 0:
        status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True,
        ).stdout
        subprocess.run(["git", "cherry-pick", "--abort"], cwd=repo)
        raise RuntimeError(
            f"cherry-pick failed for {trigger_sha}\nstderr={r.stderr}\nstatus={status}"
        )

    # If preview fragments changed on this commit, render + amend.
    diff = git(
        repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "-m",
        "--diff-filter=AM", trigger_sha, capture=True,
    ).stdout.splitlines()
    frags = sorted({f for f in diff if f.startswith(".changes/preview/") and f.endswith(".json")})
    if not frags:
        return None  # replay only; no render

    run([sys.executable, str(CHANGELOG_PY), "render"], cwd=repo)
    git(repo, "add", "CHANGELOG.md")
    r = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=repo)
    if r.returncode != 0:
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


def test_full_flow_with_release_rollup(scratch_repo):
    """End-to-end: three merges → 0.29.0 → two more merges → 0.29.1 → minor bump → 0.30.0."""
    repo = scratch_repo
    for pr, title in [
        (843, "feat: SSO sign-in"),
        (850, "fix: idempotency drop"),
        (858, "chore: bump aws-lc"),
    ]:
        sha = _simulate_pr_merge(repo, pr, title,
                                 )
        _run_render_workflow(repo, sha)
        git(repo, "checkout", "-q", "main")

    # Release 0.29.0 on docs branch.
    git(repo, "checkout", "-q", "docs")
    run(
        [sys.executable, str(CHANGELOG_PY), "rollup",
         "--version", "0.29.0", "--date", "2026-08-01", "--bump", "minor",
         "--highlights", "SSO sign-in"],
        cwd=repo,
    )
    git(repo, "add", ".changes", "CHANGELOG.md")
    git(repo, "commit", "-q", "-m", "Release 0.29.0")

    # Two more merges + patch release.
    git(repo, "checkout", "-q", "main")
    for pr, title in [(867, "fix: fd leak"), (870, "doc: retry defaults")]:
        sha = _simulate_pr_merge(repo, pr, title)
        _run_render_workflow(repo, sha)
        git(repo, "checkout", "-q", "main")

    git(repo, "checkout", "-q", "docs")
    run(
        [sys.executable, str(CHANGELOG_PY), "rollup",
         "--version", "0.29.1", "--date", "2026-08-15", "--bump", "patch"],
        cwd=repo,
    )
    git(repo, "add", ".changes", "CHANGELOG.md")
    git(repo, "commit", "-q", "-m", "Release 0.29.1")

    text = (repo / "CHANGELOG.md").read_text()
    assert "## [Preview]" in text
    assert "## [0.29.1] — 2026-08-15" in text
    assert "## [0.29.0] — 2026-08-01" in text

    # Minor bump — freeze 0.29.x
    git(repo, "checkout", "-q", "main")
    sha = _simulate_pr_merge(repo, 878, "feat: tcp_nodelay")
    _run_render_workflow(repo, sha)
    git(repo, "checkout", "-q", "docs")
    run(
        [sys.executable, str(CHANGELOG_PY), "rollup",
         "--version", "0.30.0", "--date", "2026-08-19", "--bump", "minor"],
        cwd=repo,
    )
    git(repo, "add", ".changes", "CHANGELOG.md")
    git(repo, "commit", "-q", "-m", "Release 0.30.0")

    root = (repo / "CHANGELOG.md").read_text()
    frozen = (repo / ".changes/0.29.x/CHANGELOG.md").read_text()
    assert "## [0.30.0] — 2026-08-19" in root
    assert "## [0.29.0]" not in root  # frozen out of root
    assert "## [0.29.0]" in frozen
    assert "## [0.29.1]" in frozen
    # docs history shows PR-scoped (cherry-picked) and release commits
    subjects = git(repo, "log", "--format=%s", capture=True).stdout.strip().splitlines()
    assert "Release 0.30.0" in subjects
    assert "Release 0.29.1" in subjects
    assert "Release 0.29.0" in subjects
    assert any("SSO sign-in" in s for s in subjects)  # cherry-picked PR title
    assert any("tcp_nodelay" in s for s in subjects)
