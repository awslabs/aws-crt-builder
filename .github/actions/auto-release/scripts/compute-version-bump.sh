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
#   PREVIOUS_TAG     the previous release tag (comparison base)
#   ABI_LABEL        "patch" | "minor" | "needs-review" | "" -- output of the
#                    check-abi action (see its gate.sh for how this is chosen)
#   VERSION_FILE     path (relative to repo root) holding "major.minor.patch"
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
MINOR_PR_LABEL="${MINOR_PR_LABEL:?MINOR_PR_LABEL must be set}"

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

MERGE_BASE_DATE="$(git log -1 --format=%cI "$PREVIOUS_TAG")" || {
  echo "ERROR: could not read the commit date of '${PREVIOUS_TAG}'." >&2
  exit 1
}

# gh pr list can't filter by "merged after a tag" directly, so use --search
# with a merged-date range instead.
prs_with_label() {
  gh pr list --repo "$REPO" --state merged \
    --search "merged:>${MERGE_BASE_DATE} label:${1}" \
    --json number --jq '[.[].number] | join(", ")'
}

# --- Rule 1 -------------------------------------------------------------------
if [[ "${ABI_LABEL:-}" == "needs-review" ]]; then
  echo "ERROR: the ABI check between ${PREVIOUS_TAG} and this ref returned 'needs-review'" >&2
  echo "       (an API break -- callers fail to recompile). Major version bumps are" >&2
  echo "       never automated. Cut that tag yourself, then re-run this workflow." >&2
  summary ""
  summary "**FAILED: the ABI check returned \`needs-review\` -- an API break between \`${PREVIOUS_TAG}\` and this ref.**"
  summary ""
  summary "Major version bumps are never automated by this workflow. Cut the major tag manually, then re-run."
  echo "skip=true" >> "$GITHUB_OUTPUT"
  exit 1
fi

# --- Read the previously released version -----------------------------------
PREVIOUS_VERSION="$(git show "${PREVIOUS_TAG}:${VERSION_FILE}" 2>/dev/null | tr -d '[:space:]')"
if [[ -z "$PREVIOUS_VERSION" ]]; then
  echo "ERROR: could not read '${VERSION_FILE}' at tag '${PREVIOUS_TAG}'." >&2
  summary ""
  summary "**FAILED: could not read \`${VERSION_FILE}\` at tag \`${PREVIOUS_TAG}\`.**"
  exit 1
fi
if ! [[ "$PREVIOUS_VERSION" =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
  echo "ERROR: '${VERSION_FILE}' at '${PREVIOUS_TAG}' is not major.minor.patch (got '${PREVIOUS_VERSION}')." >&2
  summary ""
  summary "**FAILED: \`${VERSION_FILE}\` at \`${PREVIOUS_TAG}\` is not major.minor.patch (got \`${PREVIOUS_VERSION}\`).**"
  exit 1
fi
MAJOR="${BASH_REMATCH[1]}"
MINOR="${BASH_REMATCH[2]}"
PATCH="${BASH_REMATCH[3]}"

# --- Rule 2 -------------------------------------------------------------------
BUMP=""
REASON=""
if [[ "${ABI_LABEL:-}" == "minor" ]]; then
  BUMP="minor"
  REASON="the ABI check found an incompatible change between \`${PREVIOUS_TAG}\` and this ref"
  echo "ABI check reported an incompatible change -> minor bump (no debate)."
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
