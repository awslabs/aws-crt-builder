#!/usr/bin/env bash
#
# cut-release.sh - Fetch a repo-scoped deploy key from AWS Secrets Manager,
# use it to push the bumped VERSION file straight to the default branch over
# SSH, then tag the new commit and create the GitHub Release. The key is
# fetched fresh each run via the already-assumed CRT_CI_ROLE_ARN role, used
# once, never persisted past the job, and authorized to push directly -- no
# PR/admin-merge needed and no standing broad-scope PAT.
#
# Inputs (env):
#   DEPLOY_KEY_SECRET_ID  Secrets Manager secret ID whose SecretString is a
#                          JSON blob for this repo's deploy key
#                          (`.private_key` extracted below)
#   GH_TOKEN        token used to create the release (gh release create)
#   REPO            "owner/repo"
#   VERSION_FILE    path to the version file to write NEW_VERSION into
#   NEW_VERSION     "major.minor.patch"
#   NEW_SOVERSION   "major.minor"
#   PREVIOUS_TAG    the previous release tag (for the notes range)
#   BUMP            "minor" | "patch" -- for the commit/release message
#   DRY_RUN         "true" | "false" -- if true, log the plan and stop before
#                    touching the deploy key, writing, committing, tagging,
#                    or publishing anything

set -euo pipefail

DEPLOY_KEY_SECRET_ID="${DEPLOY_KEY_SECRET_ID:?DEPLOY_KEY_SECRET_ID must be set}"
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

# symbolic-ref (unlike rev-parse --abbrev-ref) fails loudly on a detached
# HEAD instead of returning the literal string "HEAD", which would otherwise
# be pushed as a real ref name.
DEFAULT_BRANCH="$(git symbolic-ref --short HEAD)" || {
  echo "ERROR: HEAD is not on a branch (detached); refusing to push." >&2
  exit 1
}

# A tag that already exists means a previous run got at least this far --
# never re-push a differing commit under the same tag. Fail clearly so a
# partial-run recovery is a deliberate, informed human decision, not an
# automatic retry that could double-bump or collide.
if git ls-remote --exit-code --tags origin "refs/tags/v${NEW_VERSION}" > /dev/null 2>&1; then
  echo "ERROR: tag 'v${NEW_VERSION}' already exists on origin; a previous run may have" >&2
  echo "       partially completed. Inspect the remote before retrying." >&2
  exit 1
fi

# Detect a half-completed prior release: tip of the default branch is a
# "Release X" commit but no matching tag exists on origin. Refuse to layer a
# new release on top of the broken state.
git fetch origin --tags --quiet
LATEST_MSG="$(git log -1 --format=%s "origin/$(git symbolic-ref --short HEAD)")"
if [[ "$LATEST_MSG" =~ ^Release[[:space:]]+([0-9]+\.[0-9]+\.[0-9]+) ]]; then
  ORPHAN_VER="${BASH_REMATCH[1]}"
  if ! git ls-remote --exit-code --tags origin "refs/tags/v${ORPHAN_VER}" >/dev/null 2>&1; then
    echo "ERROR: tip of default branch is 'Release ${ORPHAN_VER}' but tag 'v${ORPHAN_VER}' is absent on origin." >&2
    echo "       A previous release run half-completed. Recover manually before re-running:" >&2
    echo "         gh release create v${ORPHAN_VER} --repo ${REPO} --generate-notes --notes-start-tag <prev>" >&2
    echo "       or revert the release commit if the release was abandoned." >&2
    exit 1
  fi
fi

trap 'rm -f ~/.ssh/deploy_key' EXIT

mkdir -p ~/.ssh
# The secret's SecretString is a JSON blob; we want just the .private_key field.
aws secretsmanager get-secret-value --secret-id "$DEPLOY_KEY_SECRET_ID" \
  --query SecretString --output text | jq -r .private_key > ~/.ssh/deploy_key
if [[ ! -s ~/.ssh/deploy_key ]] || ! head -1 ~/.ssh/deploy_key | grep -q "BEGIN"; then
  echo "ERROR: '${DEPLOY_KEY_SECRET_ID}' did not yield a private key (jq .private_key produced no key material)." >&2
  exit 1
fi
chmod 600 ~/.ssh/deploy_key

ssh-keyscan -H github.com >> ~/.ssh/known_hosts

cat > ~/.ssh/config << EOF
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/deploy_key
EOF
chmod 600 ~/.ssh/config

git remote set-url origin "git@github.com:${GITHUB_REPOSITORY}.git"

git config user.name "aws-crt-bot"
git config user.email "aws-sdk-common-runtime@amazon.com"

printf '%s\n' "$NEW_VERSION" > "$VERSION_FILE"
git add "$VERSION_FILE"
git commit -m "Release ${NEW_VERSION} (${BUMP})"
git tag -a "$NEW_TAG" -m "Release ${NEW_VERSION}"

# --atomic: server updates both refs in a single receive-pack transaction, so
# a mid-push failure leaves origin untouched (main and tag either both land or
# neither does).
PUSH_SUCCEEDED=0
trap 'if [[ "$PUSH_SUCCEEDED" -eq 1 ]] && ! gh release view "$NEW_TAG" --repo "$REPO" >/dev/null 2>&1; then
        echo "WARNING: commit + tag are pushed but the GitHub Release was not created." >&2
        echo "         Recover with: gh release create $NEW_TAG --repo $REPO --title $NEW_VERSION --generate-notes --notes-start-tag $PREVIOUS_TAG" >&2
      fi
      rm -f ~/.ssh/deploy_key' EXIT

git push --atomic origin "$DEFAULT_BRANCH" "$NEW_TAG"
PUSH_SUCCEEDED=1

gh release create "$NEW_TAG" \
  --repo "$REPO" \
  --title "$NEW_VERSION" \
  --generate-notes \
  --notes-start-tag "$PREVIOUS_TAG"

summary ""
summary "**Released \`${NEW_TAG}\`.** [View release](https://github.com/${REPO}/releases/tag/${NEW_TAG})"
