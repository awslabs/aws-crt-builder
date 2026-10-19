#!/usr/bin/env bash
# The body of action.yml's one step; every input arrives as an env var it sets.
set -euo pipefail
# TITLE and BOT_AUTHOR stay env vars throughout: interpolating a PR
# title into a command line would be a shell-injection vector.
SCRIPT="${GITHUB_ACTION_PATH}/scripts/changelog.py"
case "${MODE}" in
  check)
    EV="${GITHUB_EVENT_PATH:-/dev/null}"
    PR="${PR:-$(jq -r '.pull_request.number // empty' "${EV}")}"
    TITLE="${TITLE:-$(jq -r '.pull_request.title // empty' "${EV}")}"
    BOT_AUTHOR="${BOT_AUTHOR:-$(jq -r \
      'select(.pull_request.user.type == "Bot") | .pull_request.user.login // empty' \
      "${EV}")}"
    if [[ -z "${CHANGED_PATHS_FILE}" ]]; then
      BASE="$(jq -r '.pull_request.base.sha // empty' "${EV}")"
      HEAD="$(jq -r '.pull_request.head.sha // empty' "${EV}")"
      if [[ -n "${BASE}" && -n "${HEAD}" ]]; then
        CHANGED_PATHS_FILE="${RUNNER_TEMP}/changed-paths.tsv"
        # The status is spelled the way the pull request files API spells
        # it, not as git's single letter.
        git diff --name-status "${BASE}...${HEAD}" \
          | awk -F'\t' 'BEGIN{OFS="\t"} {s=substr($1,1,1); n="changed"; if(s=="A")n="added"; else if(s=="M")n="modified"; else if(s=="D")n="removed"; else if(s=="R")n="renamed"; print n,$NF}' \
          > "${CHANGED_PATHS_FILE}"
      fi
    fi

    OUT_FILE="$(mktemp)"
    set +e
    python3 "${SCRIPT}" check --pr "${PR}" --title "${TITLE}" \
      --bot-author "${BOT_AUTHOR}" --changes-dir "${CHANGES_DIR}" \
      --changed-paths-file "${CHANGED_PATHS_FILE}" \
      --changes-prefix "${CHANGES_PREFIX}" | tee "${OUT_FILE}"
    rc="${PIPESTATUS[0]}"
    set -e
    reason="$(grep -o 'CHANGELOG_CHECK_REASON::[a-z-]*' "${OUT_FILE}" \
                | tail -n1 | cut -d: -f3 || true)"
    { echo "rc=${rc}"; echo "reason=${reason}"; } >> "${GITHUB_OUTPUT}"
    rm -f "${OUT_FILE}"

    if [[ "${reason}" == "missing-fragment" ]]; then
      TEMPLATE="${RUNNER_TEMP}/fragment-template.json"
      python3 "${SCRIPT}" seed --pr "${PR}" --title "${TITLE}" --out "${TEMPLATE}"
      COMMENT="${RUNNER_TEMP}/fragment-comment.md"
      { echo "${MARKER}"
        echo "Commit this as \`${CHANGES_PREFIX}/preview/${PR}.json\`:"
        echo
        echo '```json'
        cat "${TEMPLATE}"
        echo '```'
      } > "${COMMENT}"
      cat "${COMMENT}" >> "${GITHUB_STEP_SUMMARY:-/dev/stdout}"
      if gh pr view "${PR}" --repo "${GITHUB_REPOSITORY}" --json comments -q '.comments[].body' 2>/dev/null \
           | grep -qF "${MARKER}"; then
        echo "the template has already been commented"
      else
        gh pr comment "${PR}" --repo "${GITHUB_REPOSITORY}" --body-file "${COMMENT}" \
          || echo "::notice::Could not comment (a pull request from a fork gets a read-only token); the template is in this run's summary."
      fi
    fi
    exit "${rc}"
    ;;
  seed)
    python3 "${SCRIPT}" seed --pr "${PR}" --title "${TITLE}" --out "${OUT}"
    ;;
  render)
    python3 "${SCRIPT}" render \
      --changes-dir "${CHANGES_DIR}" --changelog "${CHANGELOG}"
    ;;
  rollup)
    python3 "${SCRIPT}" rollup \
      --version "${VERSION}" --date "${DATE}" \
      --changes-dir "${CHANGES_DIR}" --changelog "${CHANGELOG}" \
      --docs-branch "${DOCS_BRANCH}" --minor-prs "${MINOR_PRS}"
    ;;
  *)
    echo "ERROR: unknown mode '${MODE}'" >&2; exit 2 ;;
esac
