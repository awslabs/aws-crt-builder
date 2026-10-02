#!/usr/bin/env bash
# Replay the release branch's new commits onto the docs branch, rendering
# CHANGELOG.md into each one -- one docs commit per release-branch commit, so the
# release branch itself stays free of bot commits.
#
# Run by changelog-render.yml and changelog-rollup.yml. A consumer repository
# holds a trigger that calls those workflows and nothing else.
#
#   TRIGGER_SHA   newest release-branch commit to replay (required)
#   DOCS_BRANCH   branch holding the rendered changelog  (default: docs)
#   CHANGELOG_PY  path to changelog.py                   (required)
#   PUSH          "true" to push the result              (default: true)
set -euo pipefail

: "${TRIGGER_SHA:?TRIGGER_SHA is required}"
: "${CHANGELOG_PY:?CHANGELOG_PY is required}"
DOCS_BRANCH="${DOCS_BRANCH:-docs}"
PUSH="${PUSH:-true}"

git config user.name "aws-sdk-common-runtime-bot"
git config user.email "aws-sdk-common-runtime@amazon.com"

if git ls-remote --exit-code --heads origin "${DOCS_BRANCH}" >/dev/null 2>&1; then
  # Not suppressed: the line above proved the branch is there, so a failure here
  # is real, and swallowing it would replay onto the clone-time tip instead.
  git fetch origin "${DOCS_BRANCH}:${DOCS_BRANCH}"
  git checkout "${DOCS_BRANCH}"
elif git rev-parse --verify --quiet "refs/heads/${DOCS_BRANCH}" >/dev/null; then
  git checkout "${DOCS_BRANCH}"
else
  # First run: branch from the parent of the triggering commit, so the first
  # cherry-pick introduces changes rather than replaying history. The mirror
  # starts here; nothing earlier is replayed.
  git checkout -B "${DOCS_BRANCH}" "${TRIGGER_SHA}^"
fi

# Replay one release-branch commit onto the docs branch and render into it.
#
# A merge commit needs its mainline named, since branches taking pull requests as
# merges rather than squashes produce them. -x records the origin sha, which is
# also how the next run works out where to resume; --allow-empty tolerates an
# identical tree, and -Xno-renames avoids false renames once a rollup has moved
# fragments out of preview/. A conflict in CHANGELOG.md carries no information,
# because the file is derived entirely from .changes/ and the render below rewrites
# it; a conflict anywhere else is fatal. A commit that is already on the branch is
# skipped rather than failed, so a re-run is a no-op.
#
# The render runs unconditionally -- cheaper than working out whether this commit
# touched fragments, and it self-heals drift. A fragment the render rejected is left
# out of the changelog: that must not fail anything, since the merge has already
# happened and a release must stay cuttable, but it surfaces as a warning rather
# than one line in a log. When nothing was replayed, any drift becomes its own
# commit rather than an amend, which would rewrite a commit an earlier run pushed.
replay_one() {
  local sha="$1" pre_head unmerged mainline=()
  pre_head="$(git rev-parse HEAD)"

  if git rev-parse --verify --quiet "${sha}^2" >/dev/null; then
    mainline=(-m 1)
  fi

  if ! git cherry-pick -x --allow-empty ${mainline[@]+"${mainline[@]}"} \
         --strategy=recursive -Xno-renames "${sha}"; then
    unmerged="$(git diff --name-only --diff-filter=U | sort -u)"
    if [[ -z "$unmerged" ]] && git diff --cached --quiet; then
      echo "${sha} is already on ${DOCS_BRANCH}; nothing to replay"
      git cherry-pick --skip || git cherry-pick --abort || true
    elif [[ "$unmerged" == "CHANGELOG.md" ]]; then
      echo "auto-resolving the derived CHANGELOG.md conflict"
      git checkout --theirs CHANGELOG.md
      git add CHANGELOG.md
      GIT_EDITOR=true git cherry-pick --continue
    else
      echo "ERROR: cherry-pick conflict in: ${unmerged:-<none>}" >&2
      git cherry-pick --abort || true
      exit 1
    fi
  fi

  log="${TMPDIR:-/tmp}/changelog-render.log"
  python3 "${CHANGELOG_PY}" render 2>&1 | tee "${log}"
  sed -n 's/^WARN: /::warning::/p' "${log}"
  git add CHANGELOG.md

  if [[ "$(git rev-parse HEAD)" == "$pre_head" ]]; then
    git diff --cached --quiet || git commit -q -m "Render the changelog"
  elif git diff --cached --quiet "${pre_head}"; then
    echo "${sha} changed nothing on ${DOCS_BRANCH}; dropping the replay"
    git reset --hard -q "${pre_head}"
  elif ! git diff --cached --quiet; then
    git commit --amend --no-edit
  fi
}

# Replay every commit not yet on the docs branch, oldest first. The gap is read
# from the docs branch rather than from the push event: one push can carry
# several commits, and a pending run can be cancelled -- a concurrency group
# holds one running and one pending run -- so the triggering commit alone is
# never the whole story. Each run therefore closes whatever gap it finds.
LAST="$(git log -1 --grep='^(cherry picked from commit' --pretty=%B "${DOCS_BRANCH}" \
          | sed -n 's/^(cherry picked from commit \([0-9a-f]\{7,\}\))$/\1/p' | tail -n1)"
: "${LAST:=$(git merge-base "${DOCS_BRANCH}" "${TRIGGER_SHA}")}"

for sha in $(git rev-list --reverse "${LAST}..${TRIGGER_SHA}"); do
  echo "replaying ${sha} onto ${DOCS_BRANCH}"
  replay_one "${sha}"
done

if [[ "$PUSH" == "true" ]]; then
  git push origin "${DOCS_BRANCH}"
else
  echo "PUSH=false, leaving ${DOCS_BRANCH} local"
fi
