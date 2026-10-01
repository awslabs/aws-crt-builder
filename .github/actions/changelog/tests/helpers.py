"""Fixtures shared by the per-module test files."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import changelog  # noqa: E402


def _changes(tmp_path):
    d = tmp_path / ".changes" / "preview"
    d.mkdir(parents=True, exist_ok=True)
    return str(tmp_path / ".changes")


def _write(tmp_path, pr, pr_type, summary="s", notes="", **over):
    """Put a fragment where an author would have committed it."""
    _changes(tmp_path)
    frag = {"pr": pr, "type": pr_type, "summary": summary, "notes": notes}
    frag.update(over)
    (tmp_path / ".changes" / "preview" / f"{pr}.json").write_text(
        json.dumps(frag) + "\n")


def _seed(tmp_path, pr, title):
    """Seed writes a template; the author is the one who commits it."""
    out = tmp_path / "template.json"
    rc = changelog.main(["seed", "--pr", str(pr), "--title", title, "--out", str(out)])
    if rc == 0:
        frag = tmp_path / ".changes" / "preview" / f"{pr}.json"
        frag.parent.mkdir(parents=True, exist_ok=True)
        frag.write_text(out.read_text())
    return rc


def _render(tmp_path):
    changelog.main(["render", "--changes-dir", _changes(tmp_path),
                    "--changelog", str(tmp_path / "CHANGELOG.md")])
    return (tmp_path / "CHANGELOG.md").read_text()
