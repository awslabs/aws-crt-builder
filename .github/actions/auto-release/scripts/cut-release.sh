#!/usr/bin/env bash
#
# cut-release.sh - Write the bumped VERSION file, push it straight to the
# default branch over SSH using the deploy key setup-deploy-key.sh just
# configured, then tag the new commit and create the GitHub Release. Same
# mechanism as aws-crt-swift's update-version.yml: a repo-scoped deploy key
# authorized to push directly, no PR/admin-merge needed.
#
# Inputs (env):
#   GH_TOKEN        token used to create the release (gh release create)
#   REPO            "owner/repo"
#   VERSION_FILE    path to the version file to write NEW_VERSION into
#   NEW_VERSION     "major.minor.patch"
#   NEW_SOVERSION   "major.minor"
#   PREVIOUS_TAG    the previous release tag (for the notes range)
#   BUMP            "minor" | "patch" -- for the commit/release message
#   DRY_RUN         "true" | "false" -- if true, log the plan and stop before
#                    writing, committing, tagging, or publishing anything

set -euo pipefail

VERSION_FILE="${VERSION_FILE:?VERSION_FILE must be set}"
NEW_VERSION="${NEW_VERSION:?NEW_VERSION must be set}"
NEW_SOVERSION="${NEW_SOVERSION:?NEW_SOVERSION must be set}"
PREVIOUS_TAG="${PREVIOUS_TAG:?PREVIOUS_TAG must be set}"
BUMP="${BUMP:?BUMP must be set}"
NEW_TAG="v${NEW_VERSION}"

summary() { [[ -n "${GITHUB_STEP_SUMMARY:-}" ]] && printf '%s\n' "$1" >> "$GITHUB_STEP_SUMMARY"; true; }

echo "Plan: ${PREVIOUS_TAG} -> ${NEW_TAG} (${BUMP} bump, SOVERSION=${NEW_SOVERSION})"

if [[ "${DRY_RUN:-false}" == "true" ]]; then
  echo "DRY RUN: would write '${NEW_VERSION}' to '${VERSION_FILE}', push to the default branch, tag '${NEW_TAG}', and create a GitHub Release."
  summary ""
  summary "**DRY RUN: would have tagged \`${NEW_TAG}\` and created a GitHub Release. No changes were made.**"
  exit 0
fi

DEFAULT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"

git config user.name "aws-crt-bot"
git config user.email "aws-sdk-common-runtime@amazon.com"

printf '%s\n' "$NEW_VERSION" > "$VERSION_FILE"
git add "$VERSION_FILE"
git commit -m "Release ${NEW_VERSION} (${BUMP})"
git push origin "$DEFAULT_BRANCH"

git tag -a "$NEW_TAG" -m "Release ${NEW_VERSION}"
git push origin "$NEW_TAG"

gh release create "$NEW_TAG" \
  --repo "$REPO" \
  --title "$NEW_VERSION" \
  --generate-notes \
  --notes-start-tag "$PREVIOUS_TAG"

summary ""
summary "**Released \`${NEW_TAG}\`.** [View release](https://github.com/${REPO}/releases/tag/${NEW_TAG})"
