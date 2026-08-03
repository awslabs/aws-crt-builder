#!/usr/bin/env bash
#
# cut-release.sh - Land the bumped VERSION file on the default branch via a
# PR (not a direct push -- the default branch is expected to require review,
# same assumption aws-crt-cpp's update-version.sh makes), then tag the merged
# commit and create the GitHub Release.
#
# GH_TOKEN pushes the branch and opens/creates the PR; MERGE_TOKEN merges it.
# Two tokens because a repo's default GITHUB_TOKEN cannot bypass required
# reviews/status checks on a protected branch -- only a PAT with admin rights
# can, the same reason aws-crt-cpp's release workflow takes a second token
# (TAG_PR_TOKEN) solely for the merge step.
#
# Inputs (env):
#   GH_TOKEN        pushes the branch, creates the PR and the release
#   MERGE_TOKEN      merges the PR with --admin (bypasses branch protection)
#   REPO            "owner/repo"
#   VERSION_FILE    path to the version file to write NEW_VERSION into
#   NEW_VERSION     "major.minor.patch"
#   NEW_SOVERSION   "major.minor"
#   PREVIOUS_TAG    the previous release tag (for the notes range and diff)
#   BUMP            "minor" | "patch" -- for the commit/PR/release message
#   DRY_RUN         "true" | "false" -- if true, log the plan and stop before
#                    writing, committing, or opening anything

set -euo pipefail

VERSION_FILE="${VERSION_FILE:?VERSION_FILE must be set}"
NEW_VERSION="${NEW_VERSION:?NEW_VERSION must be set}"
NEW_SOVERSION="${NEW_SOVERSION:?NEW_SOVERSION must be set}"
PREVIOUS_TAG="${PREVIOUS_TAG:?PREVIOUS_TAG must be set}"
BUMP="${BUMP:?BUMP must be set}"
MERGE_TOKEN="${MERGE_TOKEN:?MERGE_TOKEN must be set}"
NEW_TAG="v${NEW_VERSION}"
BUMP_BRANCH="release-${NEW_VERSION}"

summary() { [[ -n "${GITHUB_STEP_SUMMARY:-}" ]] && printf '%s\n' "$1" >> "$GITHUB_STEP_SUMMARY"; true; }

echo "Plan: ${PREVIOUS_TAG} -> ${NEW_TAG} (${BUMP} bump, SOVERSION=${NEW_SOVERSION})"

if [[ "${DRY_RUN:-false}" == "true" ]]; then
  echo "DRY RUN: would write '${NEW_VERSION}' to '${VERSION_FILE}', open and merge a PR, tag '${NEW_TAG}', and create a GitHub Release."
  summary ""
  summary "**DRY RUN: would have tagged \`${NEW_TAG}\` and created a GitHub Release. No changes were made.**"
  exit 0
fi

DEFAULT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"

git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"

printf '%s\n' "$NEW_VERSION" > "$VERSION_FILE"

git checkout -b "$BUMP_BRANCH"
git add "$VERSION_FILE"
git commit -m "Release ${NEW_VERSION} (${BUMP})"
git push origin "$BUMP_BRANCH"

gh pr create --repo "$REPO" --base "$DEFAULT_BRANCH" --head "$BUMP_BRANCH" \
  --title "Release ${NEW_VERSION}" --body "Automated version bump for release ${NEW_VERSION} (${BUMP})."

GH_TOKEN="$MERGE_TOKEN" gh pr merge --repo "$REPO" "$BUMP_BRANCH" --admin --squash

git checkout "$DEFAULT_BRANCH"
git pull origin "$DEFAULT_BRANCH"

git tag -a "$NEW_TAG" -m "Release ${NEW_VERSION}"
git push origin "$NEW_TAG"

gh release create "$NEW_TAG" \
  --repo "$REPO" \
  --title "$NEW_VERSION" \
  --generate-notes \
  --notes-start-tag "$PREVIOUS_TAG"

summary ""
summary "**Released \`${NEW_TAG}\`.** [View release](https://github.com/${REPO}/releases/tag/${NEW_TAG})"
