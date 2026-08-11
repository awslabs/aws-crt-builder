#!/usr/bin/env bash
#
# compute-version-bump.sh - Decide the next version for a CRT C library
# release, and explain the decision in $GITHUB_STEP_SUMMARY. See the parent
# README for the full precedence rationale; the numbered "Rule N" markers
# below implement it in order, first match wins.
#
# SOVERSION is always major.minor of the resulting version, per the CRT C
# library convention.
#
# Inputs (env):
#   GH_TOKEN         token with pull-requests: read, used by `gh pr list`
#   REPO             "owner/repo", for `gh pr list --repo`
#   PREVIOUS_TAG     the previous release tag, "vMAJOR.MINOR.PATCH" (the
#                    previously released version is parsed from this name,
#                    never read from a file's content at that tag)
#   ABI_LABEL        "patch" | "minor" | "needs-review" | "" -- output of the
#                    check-abi action (see its gate.sh for how this is chosen)
#   VERSION_FILE     path (relative to repo root) where the current version
#                    at HEAD is expected. If present, it must match the
#                    previous tag's version (drift check). If absent, this
#                    release creates it -- the file is not a hard prerequisite.
#   MAJOR_PR_LABEL   PR label that hard-fails the release (major bumps are
#                    never automated). Defense-in-depth: PRs with this label
#                    are not supposed to be merged in the first place.
#   MINOR_PR_LABEL   PR label that forces a minor bump
#
# Outputs (appended to $GITHUB_OUTPUT):
#   skip              "true" if there is nothing to release (rule 0) or the
#                      workflow failed before a version could be computed
#   bump              "minor" | "patch" (unset if skipped)
#   previous_version, new_version, new_soversion (unset if skipped)

set -uo pipefail

PREVIOUS_TAG="${PREVIOUS_TAG:?PREVIOUS_TAG must be set}"
VERSION_FILE="${VERSION_FILE:?VERSION_FILE must be set}"
MAJOR_PR_LABEL="${MAJOR_PR_LABEL:?MAJOR_PR_LABEL must be set}"
MINOR_PR_LABEL="${MINOR_PR_LABEL:?MINOR_PR_LABEL must be set}"
REPO="${REPO:?REPO must be set}"
[[ "$REPO" =~ ^[^/[:space:]]+/[^/[:space:]]+$ ]] || {
  echo "ERROR: REPO ('$REPO') is not a valid 'owner/repo'." >&2
  exit 1
}

summary() { [[ -n "${GITHUB_STEP_SUMMARY:-}" ]] && printf '%s\n' "$1" >> "$GITHUB_STEP_SUMMARY"; }

summary "## Release version computation"
summary ""
summary "Comparing against previous release tag \`${PREVIOUS_TAG}\`."

# --- Rule 0 -------------------------------------------------------------------
COMMITS_SINCE="$(git rev-list "${PREVIOUS_TAG}..HEAD")" || {
  echo "ERROR: 'git rev-list ${PREVIOUS_TAG}..HEAD' failed." >&2
  exit 1
}
if [[ -z "$COMMITS_SINCE" ]]; then
  echo "No commits since ${PREVIOUS_TAG}; nothing to release."
  summary ""
  summary "**No changes since \`${PREVIOUS_TAG}\`. No release was cut.**"
  echo "skip=true" >> "$GITHUB_OUTPUT"
  exit 0
fi

# For an annotated tag, anchor on the tag's own creation date, not the
# committer date of the commit it points at -- those can diverge (e.g. an
# annotated tag cut well after its target commit was authored), which would
# otherwise widen or narrow the "merged since" window incorrectly. Lightweight
# tags have no tagger date, so fall back to the commit's date for those.
MERGE_BASE_DATE="$(git for-each-ref --format='%(creatordate:iso-strict)' "refs/tags/${PREVIOUS_TAG}")"
if [[ -z "$MERGE_BASE_DATE" ]]; then
  MERGE_BASE_DATE="$(git log -1 --format=%cI "$PREVIOUS_TAG")" || {
    echo "ERROR: could not read the date of '${PREVIOUS_TAG}'." >&2
    exit 1
  }
fi

# gh pr list can't filter by "merged after a tag" directly, so use --search
# with a merged-date range instead.
prs_with_label() {
  gh pr list --repo "$REPO" --state merged \
    --search "merged:>${MERGE_BASE_DATE} label:${1}" \
    --json number --jq '[.[].number] | join(", ")'
}

# --- Rule 1 -------------------------------------------------------------------
# The major PR label is human-set; recovering from a fail here just means
# removing the label and retrying. The ABI verdict below is automated, and the
# code that produced it is already merged -- so a needs-review verdict does
# NOT fail here; it just steers the bump (see Rule 2). The PR label is the
# only mechanism for gating a release.
MAJOR_PRS="$(prs_with_label "$MAJOR_PR_LABEL")" || {
  echo "ERROR: 'gh pr list' failed while checking for '${MAJOR_PR_LABEL}'-labeled PRs." >&2
  exit 1
}
if [[ -n "$MAJOR_PRS" ]]; then
  echo "ERROR: PR(s) #${MAJOR_PRS} merged since ${PREVIOUS_TAG} carry the '${MAJOR_PR_LABEL}' label." >&2
  echo "       Major version bumps are never automated. Remove the label if this was" >&2
  echo "       resolved, or cut the major tag manually, then re-run." >&2
  summary ""
  summary "**FAILED: PR(s) #${MAJOR_PRS} merged since \`${PREVIOUS_TAG}\` are labeled \`${MAJOR_PR_LABEL}\`.**"
  summary ""
  summary "Major version bumps are never automated by this workflow. Remove the label if this was resolved, or cut the major tag manually, then re-run."
  echo "skip=true" >> "$GITHUB_OUTPUT"
  exit 1
fi

# An empty ABI_LABEL means the ABI check itself never produced a verdict, which
# means something upstream failed before we got here -- refuse rather than
# silently fall through to a patch bump. Any real verdict is fine here.
if [[ -z "${ABI_LABEL:-}" ]]; then
  echo "ERROR: no ABI check result was produced; refusing to compute a bump." >&2
  summary ""
  summary "**FAILED: no ABI check result was produced.**"
  echo "skip=true" >> "$GITHUB_OUTPUT"
  exit 1
fi

# --- Derive the previously released version from the TAG NAME ---------------
# Never from a file's content at that tag: an older release may predate
# VERSION_FILE existing, or may have used a different convention. The tag
# name is the one thing guaranteed to reflect what was actually released.
if ! [[ "$PREVIOUS_TAG" =~ ^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$ ]]; then
  echo "ERROR: '${PREVIOUS_TAG}' is not of the form vMAJOR.MINOR.PATCH." >&2
  summary ""
  summary "**FAILED: \`${PREVIOUS_TAG}\` is not of the form \`vMAJOR.MINOR.PATCH\`.**"
  exit 1
fi
MAJOR="${BASH_REMATCH[1]}"
MINOR="${BASH_REMATCH[2]}"
PATCH="${BASH_REMATCH[3]}"
PREVIOUS_VERSION="${MAJOR}.${MINOR}.${PATCH}"

# --- Drift check: if VERSION_FILE exists at HEAD, it must match PREVIOUS_TAG -
# The tag is the source of truth for what was released. If the file exists on
# HEAD but says something else, someone edited it out of sync and we're one
# step away from releasing from a state that misrepresents the previous
# version. If the file doesn't exist yet (this repo is adopting a VERSION
# file for the first time via this release), that's fine -- cut-release.sh
# will create it with the newly computed version.
if [[ -f "$VERSION_FILE" ]]; then
  CURRENT_FILE_VERSION="$(tr -d '[:space:]' < "$VERSION_FILE")"
  if [[ "$CURRENT_FILE_VERSION" != "$PREVIOUS_VERSION" ]]; then
    echo "ERROR: drift detected. '${VERSION_FILE}' at HEAD says '${CURRENT_FILE_VERSION}'," >&2
    echo "       but the previous release tag '${PREVIOUS_TAG}' implies '${PREVIOUS_VERSION}'." >&2
    echo "       Reconcile before releasing." >&2
    summary ""
    summary "**FAILED: \`${VERSION_FILE}\` (\`${CURRENT_FILE_VERSION}\`) drifted from the previous release tag \`${PREVIOUS_TAG}\` (\`${PREVIOUS_VERSION}\`). Reconcile before releasing.**"
    exit 1
  fi
fi

# --- Rule 2 -------------------------------------------------------------------
# Any incompatible ABI verdict -- both "minor" (binary-only break) and
# "needs-review" (source/API break) -- forces a minor bump. A needs-review
# verdict does NOT hard-fail (see Rule 1's rationale): the maintainer chose to
# ship it, so we bump minor and move on.
BUMP=""
REASON=""
if [[ "${ABI_LABEL:-}" == "minor" || "${ABI_LABEL:-}" == "needs-review" ]]; then
  BUMP="minor"
  REASON="the ABI check found an incompatible change (\`${ABI_LABEL}\`) between \`${PREVIOUS_TAG}\` and this ref"
  echo "ABI check reported '${ABI_LABEL}' -> minor bump."
fi

# --- Rule 3 -------------------------------------------------------------------
MINOR_PRS=""
if [[ -z "$BUMP" ]]; then
  MINOR_PRS="$(prs_with_label "$MINOR_PR_LABEL")" || {
    echo "ERROR: 'gh pr list' failed while checking for '${MINOR_PR_LABEL}'-labeled PRs." >&2
    exit 1
  }
  if [[ -n "$MINOR_PRS" ]]; then
    BUMP="minor"
    REASON="the ABI is backward-compatible, but PR(s) #${MINOR_PRS} merged since \`${PREVIOUS_TAG}\` are labeled \`${MINOR_PR_LABEL}\`"
    echo "PR(s) #${MINOR_PRS} carry the '${MINOR_PR_LABEL}' label -> minor bump."
  fi
fi

# --- Rule 4 -------------------------------------------------------------------
if [[ -z "$BUMP" ]]; then
  BUMP="patch"
  REASON="the ABI is backward-compatible and no merged PR since \`${PREVIOUS_TAG}\` is labeled \`${MINOR_PR_LABEL}\`"
  echo "No ABI break and no '${MINOR_PR_LABEL}'-labeled PRs since ${PREVIOUS_TAG} -> patch bump."
fi

if [[ "$BUMP" == "minor" ]]; then
  NEW_MINOR="$((MINOR + 1))"
  NEW_PATCH=0
else
  NEW_MINOR="$MINOR"
  NEW_PATCH="$((PATCH + 1))"
fi

NEW_VERSION="${MAJOR}.${NEW_MINOR}.${NEW_PATCH}"
NEW_SOVERSION="${MAJOR}.${NEW_MINOR}"

echo "Previous version: ${PREVIOUS_VERSION} (tag ${PREVIOUS_TAG})"
echo "Bump: ${BUMP}"
echo "New version: ${NEW_VERSION}"
echo "New SOVERSION: ${NEW_SOVERSION}"

summary ""
summary "- ABI check result: **${ABI_LABEL:-unknown}**"
summary "- Bump: **${BUMP}** -- ${REASON}."
summary "- Version: \`${PREVIOUS_VERSION}\` -> \`${NEW_VERSION}\` (SOVERSION \`${NEW_SOVERSION}\`)"

{
  echo "skip=false"
  echo "bump=${BUMP}"
  echo "previous_version=${PREVIOUS_VERSION}"
  echo "new_version=${NEW_VERSION}"
  echo "new_soversion=${NEW_SOVERSION}"
} >> "$GITHUB_OUTPUT"
