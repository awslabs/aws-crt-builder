#!/usr/bin/env bash
#
# gate.sh - Interpret the recorded ABI verdict, choose a semver label, and fail
# the job ONLY when abi-compliance-checker could not produce a verdict.
#
# This check is informational, not pass/fail: a compatible or incompatible ABI
# both succeed and are surfaced as a PR label. The job fails only when the check
# itself could not run (so there is no trustworthy verdict to label with).
#
# abi-compliance-checker exit codes:
#   0      compatible                -> label: patch
#   1      incompatible (ran clean)  -> label: minor (ABI changed; next release
#                                       is at least a minor bump)
#   2-11   tool error (bad input, can't compile, empty symbol set, ...)
#          -> FAIL: the check could not run, no verdict was produced.
#
# Inputs (env): ABI_RC, ABI_PCT, ABI_ACC_LOG, ABI_LABEL_FILE (optional)
#
# Outputs:
#   Appends ABI_LABEL / ABI_LABEL_REMOVE to $GITHUB_ENV, and (if ABI_LABEL_FILE
#   is set) writes the chosen label there. ABI_LABEL_FILE is a host-mounted file,
#   so it is how the verdict escapes the container to the labeling step.

set -uo pipefail

RC="${ABI_RC:--1}"
PCT="${ABI_PCT:-?}"

if ! [[ "$RC" =~ ^-?[0-9]+$ ]]; then
  echo "FAIL: ABI_RC is not an integer ('$RC'); cannot determine a verdict."
  exit 1
fi

if [[ "$RC" -lt 0 ]]; then
  echo "FAIL: ABI check did not produce a verdict (a prior step failed)."
  exit 1
fi

if [[ "$RC" -ge 2 ]]; then
  echo "ERROR: abi-compliance-checker tool error (exit $RC). No verdict produced."
  if [[ -n "${ABI_ACC_LOG:-}" && -f "$ABI_ACC_LOG" ]]; then
    echo "----- acc.log (last 200 lines) -----"
    tail -n 200 "$ABI_ACC_LOG"
    echo "------------------------------------"
  fi
  exit "$RC"
fi

if [[ "$RC" -eq 0 ]]; then
  LABEL=patch; REMOVE=minor
  echo "PASS: ABI backward-compatible (${PCT}%) -> label: ${LABEL}"
else
  LABEL=minor; REMOVE=patch
  echo "PASS: ABI incompatible (${PCT}%) -> label: ${LABEL}"
fi

{
  echo "ABI_LABEL=${LABEL}"
  echo "ABI_LABEL_REMOVE=${REMOVE}"
} >> "$GITHUB_ENV"

if [[ -n "${ABI_LABEL_FILE:-}" ]]; then
  printf '%s\n' "$LABEL" > "$ABI_LABEL_FILE"
fi

exit 0
