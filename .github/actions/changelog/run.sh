#!/usr/bin/env bash
# The body of action.yml's one step; every input arrives as an env var it sets.
set -euo pipefail
# TITLE and BOT_AUTHOR stay env vars throughout: interpolating a PR
# title into a command line would be a shell-injection vector.
SCRIPT="${GITHUB_ACTION_PATH}/scripts/changelog.py"
case "${MODE}" in
  check)
    # Does not fail the step. The caller reads `rc` and `reason` and
    # decides -- a missing fragment earns a template comment first,
    # every other failure only gets the diagnostic above.
    OUT_FILE="$(mktemp)"
    set +e
    python3 "${SCRIPT}" check --pr "${PR}" --title "${TITLE}" \
      --bot-author "${BOT_AUTHOR}" --changes-dir "${CHANGES_DIR}" \
      --changed-paths-file "${CHANGED_PATHS_FILE}" \
      --changes-prefix "${CHANGES_PREFIX}" | tee "${OUT_FILE}"
    rc="${PIPESTATUS[0]}"
    set -e
    {
      echo "rc=${rc}"
      echo "reason=$(grep -o 'CHANGELOG_CHECK_REASON::[a-z-]*' "${OUT_FILE}" \
                      | tail -n1 | cut -d: -f3 || true)"
    } >> "${GITHUB_OUTPUT}"
    rm -f "${OUT_FILE}"
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
