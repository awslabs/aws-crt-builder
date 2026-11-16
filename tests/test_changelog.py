import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / ".github/actions/changelog/scripts/changelog.py"
sys.path.insert(0, str(SCRIPT.parent))
from fragments import parse_title, validate_fragment  # noqa: E402


def run(*args, cwd):
    p = subprocess.run([sys.executable, str(SCRIPT), *args], cwd=cwd,
                       capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


class Repo(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.addCleanup(self._t.cleanup)
        self.d = Path(self._t.name)
        (self.d / ".changes/preview").mkdir(parents=True)

    def frag(self, pr, type_, summary="Did a thing", **extra):
        (self.d / f".changes/preview/{pr}.json").write_text(
            json.dumps({"pr": pr, "type": type_, "summary": summary, **extra}))

    def check(self, pr, title, paths=None, bot=""):
        args = ["check", "--pr", str(pr), "--title", title, "--bot-author", bot]
        if paths is not None:
            f = self.d / "paths.tsv"
            f.write_text("".join(f"{s}\t{p}\n" for s, p in paths))
            args += ["--changed-paths-file", str(f)]
        rc, out, _ = run(*args, cwd=self.d)
        reason = [ln for ln in out.splitlines() if "CHANGELOG_CHECK_REASON" in ln]
        return rc, reason[-1].split("::")[1] if reason else ""

    def rollup(self, version, *extra, minor=""):
        return run("rollup", "--version", version, "--date", "2026-01-01",
                   "--minor-prs", minor, *extra, cwd=self.d)

    def text(self):
        return (self.d / "CHANGELOG.md").read_text()


class Titles(unittest.TestCase):
    def test_types(self):
        for t, want in [("feat: x", "feat"), ("change(s3): x", "change"),
                        ("feat!: x", "feat"), ("fix(io)!: x", "fix"),
                        ('Revert "fix: x (#1)"', "revert"),
                        ('Revert "Revert "fix: x""', "chore"), ("Add x", None)]:
            self.assertEqual(parse_title(t)[0], want, t)


class Schema(Repo):
    def test_notes_rejected(self):
        self.frag(1, "revert", notes="why")
        errs = validate_fragment(self.d / ".changes/preview/1.json")
        self.assertTrue(any("unexpected field" in e for e in errs))

    def test_unhashable_type(self):
        self.frag(1, [])
        self.assertTrue(validate_fragment(self.d / ".changes/preview/1.json"))

    def test_seed_has_no_notes_and_escapes_backtick(self):
        out = self.d / "t.json"
        run("seed", "--pr", "7", "--title", "fix: a ``` b", "--out", str(out), cwd=self.d)
        self.assertNotIn("```", out.read_text())
        self.assertEqual(set(json.loads(out.read_text())), {"pr", "type", "summary"})


class Check(Repo):
    def test_outcomes(self):
        self.frag(5, "change")
        add = [("added", ".changes/preview/5.json")]
        self.assertEqual(self.check(5, "change: bump part size", add), (0, "ok"))
        self.assertEqual(self.check(5, "feat: x", add), (1, "type-mismatch"))
        self.assertEqual(self.check(6, "change: x", []), (1, "missing-fragment"))
        self.assertEqual(self.check(5, "Bump part size"), (1, "bad-title"))
        self.assertEqual(self.check(5, "x", bot="dependabot[bot]"), (0, "waived-bot"))
        self.assertEqual(self.check(9, "chore: x", []), (0, "exempt-type"))
        self.assertEqual(self.check(9, 'Revert "Revert "x""', []), (0, "exempt-type"))

    def test_chore_must_not_touch_changes(self):
        for st in ("added", "modified", "removed"):
            self.assertEqual(self.check(9, "chore: x", [(st, ".changes/preview/3.json")]),
                             (1, "stray-fragment"))

    def test_stray_and_modified(self):
        self.frag(5, "fix")
        self.assertEqual(self.check(5, "fix: x", [("added", ".changes/preview/5.json"),
                                                  ("removed", ".changes/preview/4.json")]),
                         (1, "stray-fragment"))
        self.assertEqual(self.check(5, "fix: x", [("modified", ".changes/preview/5.json")]),
                         (1, "modified-fragment"))


class Release(Repo):
    def test_render_has_no_links_or_notes(self):
        self.frag(1, "feat", "Add A")
        self.frag(2, "change", "Raise part size to 16 MiB.")
        self.frag(3, "fix", "Fix C")
        self.frag(4, "revert", "Reverted D")
        self.assertEqual(self.rollup("1.1.0", minor="3")[0], 0)
        t = self.text()
        for bad in ("pull/", "#1", "(#", "](", "Notes", "<!--"):
            self.assertNotIn(bad, t)
        self.assertLess(t.index("Possible Breaking Changes"), t.index("### Features"))
        self.assertLess(t.index("### Features"), t.index("### Changes"))
        self.assertLess(t.index("### Changes"), t.index("### Reverts"))
        self.assertIn("- Raise part size to 16 MiB.", t)
        self.assertEqual(list((self.d / ".changes/preview").glob("*.json")), [])

    def test_render_preview_prints_only(self):
        self.frag(1, "feat", "Add A")
        rc, out, _ = run("render", cwd=self.d)
        self.assertEqual((rc, out), (0, "### Features\n- Add A.\n"))
        self.assertFalse((self.d / "CHANGELOG.md").exists())

    def test_newest_first_and_idempotent(self):
        self.frag(1, "fix", "One")
        self.rollup("1.0.1")
        self.frag(2, "fix", "Two")
        self.rollup("1.0.2")
        before = self.text()
        self.rollup("1.0.2")
        self.assertEqual(self.text(), before)
        self.assertLess(before.index("1.0.2"), before.index("1.0.1"))
        self.assertTrue(before.startswith("# Changelog\n"))

    def test_no_archive_without_flag(self):
        self.frag(1, "fix", "One")
        self.rollup("1.0.1")
        self.frag(2, "feat", "Two")
        self.rollup("1.1.0")
        self.assertFalse(list((self.d / ".changes").glob("*.x.md")))
        self.assertIn("1.0.1", self.text())

    def test_archive_flag_moves_other_lines(self):
        for pr, v in [(1, "1.0.1"), (2, "1.1.0"), (3, "1.2.0")]:
            self.frag(pr, "feat", f"F{pr}")
            self.rollup(v)
        self.frag(4, "feat", "F4")
        self.assertEqual(self.rollup("1.2.1", "--archive")[0], 0)
        t = self.text()
        self.assertIn("1.2.1", t)
        self.assertIn("1.2.0", t)
        self.assertNotIn("[1.1.0]", t)
        self.assertNotIn("[1.0.1]", t)
        self.assertTrue((self.d / ".changes/1.0.x.md").exists())
        self.assertTrue((self.d / ".changes/1.1.x.md").exists())
        self.assertIn("[1.1.x](.changes/1.1.x.md)", t)
        self.assertLess(t.index("1.1.x"), t.index("1.0.x"))
        self.assertNotIn("pull/", (self.d / ".changes/1.1.x.md").read_text())

    def test_adopting_heading_kept(self):
        (self.d / "CHANGELOG.md").write_text("# Old\n\n## [0.9.0] — 2025-01-01\n\n- old\n")
        self.frag(1, "fix", "One")
        self.rollup("1.0.0")
        t = self.text()
        self.assertTrue(t.startswith("# Old\n"))
        self.assertEqual(t.count("# Old"), 1)
        self.assertLess(t.index("1.0.0"), t.index("0.9.0"))

    def test_release_with_only_chore_fragments_adds_no_section(self):
        (self.d / "CHANGELOG.md").write_text("# Changelog\n\n## [1.0.0] — 2026-01-01\n\n- old\n")
        before = self.text()
        self.assertEqual(self.rollup("1.0.1")[0], 0)
        self.assertEqual(self.text().strip(), before.strip())

    def test_archive_never_overwrites_a_different_archive(self):
        self.frag(1, "fix", "One")
        self.rollup("1.0.1")
        (self.d / ".changes/1.0.x.md").write_text("hand written\n")
        self.frag(2, "feat", "Two")
        self.assertEqual(self.rollup("1.1.0", "--archive")[0], 2)
        self.assertEqual((self.d / ".changes/1.0.x.md").read_text(), "hand written\n")

    def test_invalid_fragment_stops_release(self):
        self.frag(1, "fix", "One", notes="x")
        self.assertEqual(self.rollup("1.0.1")[0], 2)
        self.assertTrue((self.d / ".changes/preview/1.json").exists())


if __name__ == "__main__":
    unittest.main()
