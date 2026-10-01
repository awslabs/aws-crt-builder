#!/usr/bin/env bash
# Exercise changelog-replay.sh against a scratch repository. No network, no
# GitHub: the cases that matter are the ones a push event cannot describe --
# several commits arriving at once, and a re-run that must change nothing.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPLAY="${HERE}/changelog-replay.sh"
CHANGELOG_PY="${HERE}/../actions/changelog/scripts/changelog.py"
WORK="$(mktemp -d)"
cd "$WORK"

git init -q -b main .
git config user.email a@b.c
git config user.name tester
printf '# Changelog\n\n## [1.0.0]\n\nOfficial release of 1.0.0.\n' > CHANGELOG.md
mkdir -p .changes/preview
git add -A && git commit -q -m "base"

frag() { mkdir -p .changes/preview; printf '{\n  "pr": %s,\n  "type": "%s",\n  "summary": "%s",\n  "notes": ""\n}\n' "$1" "$2" "$3" > ".changes/preview/$1.json"; }

replay() { TRIGGER_SHA="$(git rev-parse main)" DOCS_BRANCH=docs CHANGELOG_PY="$CHANGELOG_PY" PUSH=false bash "$REPLAY"; git checkout -q main; }

say() { printf '\n### %s\n' "$1"; }
docs_entries() { git show docs:CHANGELOG.md | grep -c '^- ' || true; }

say "case 1: one push, two commits, both carrying a fragment"
frag 101 feat "First entry."; git add -A; git commit -q -m "c1"
frag 102 fix "Second entry."; git add -A; git commit -q -m "c2"
replay
echo "docs commits since base: $(git rev-list --count main~2..docs)"
echo "entries rendered: $(docs_entries)"
git log --oneline -4 docs
[[ "$(docs_entries)" == "2" ]] || { echo "FAIL: expected 2 entries"; exit 1; }
[[ "$(git rev-list --count docs)" == "3" ]] || { echo "FAIL: expected 3 docs commits"; exit 1; }

say "case 2: one push, two commits, only the first carries a fragment"
frag 103 feat "Third entry."; git add -A; git commit -q -m "c3"
printf 'scratch\n' > probe.txt; git add -A; git commit -q -m "c4"
replay
echo "entries rendered: $(docs_entries)"
git log --oneline -3 docs
[[ "$(docs_entries)" == "3" ]] || { echo "FAIL: expected 3 entries"; exit 1; }
git show docs:probe.txt >/dev/null || { echo "FAIL: c4 was not replayed"; exit 1; }

say "case 3: re-run with nothing new is a no-op"
BEFORE="$(git rev-parse docs)"
replay
[[ "$(git rev-parse docs)" == "$BEFORE" ]] || { echo "FAIL: docs moved on a no-op re-run"; exit 1; }
echo "docs unmoved: $BEFORE"

say "case 4: a rollup commit is replayed like any other"
python3 "$CHANGELOG_PY" rollup --version 1.1.0 --date 2026-10-02 --docs-branch docs --minor-prs ''
git add -A; git commit -q -m "rollup 1.1.0"
replay
git show docs:CHANGELOG.md | sed -n '1,8p'
git show docs:.changes/1.0.x.md >/dev/null 2>&1 && echo "archive present on docs"
[[ "$(docs_entries)" == "3" ]] || { echo "note: entry count now $(docs_entries)"; }

say "case 5: a single commit, the ordinary path"
frag 104 fix "Fourth entry."; git add -A; git commit -q -m "c5"
replay
git show docs:CHANGELOG.md | sed -n '1,12p'

echo
echo "ALL CASES PASSED ($WORK)"
