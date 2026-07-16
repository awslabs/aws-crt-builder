#!/usr/bin/env bash
#
# gate.sh - Interpret the recorded ABI verdict, choose a semver label, and fail
# the job ONLY when abi-compliance-checker could not produce a verdict.
#
# This check is informational, not pass/fail: a compatible or incompatible ABI
# both succeed and are surfaced as a PR label. The job fails only when the check
# itself could not run (so there is no trustworthy verdict to label with).
#
# abi-compliance-checker exit codes (compare.sh runs -binary AND -source, so
# "incompatible" below covers BOTH: a binary break (old compiled callers
# misbehave) and a source break (callers fail to recompile, e.g. a renamed
# public enum constant/macro/typedef -- invisible to -binary alone):
#   0      compatible                -> label: patch
#   1      incompatible (ran clean)  -> label: minor (ABI or API changed; next
#                                       release is at least a minor bump)
#   2-11   tool error (bad input, can't compile, empty symbol set, ...)
#          -> FAIL: the check could not run, no verdict was produced.
#
# Inputs (env): ABI_RC, ABI_PCT, ABI_SRC_PCT, ABI_ACC_LOG
#
# Outputs:
#   Appends ABI_LABEL / ABI_LABEL_REMOVE to $GITHUB_ENV (for stages within this
#   container run), and prints "ABI_LABEL_RESULT::<label>" as the last stdout
#   line on success. That line is how the verdict escapes the container: the
#   composite action step captures this script's stdout via command
#   substitution and greps out the marker -- no host-mounted file needed,
#   since docker already streams stdout back to the host process. (A prior
#   version wrote the label to a host-mounted file created by mktemp; that
#   file defaults to mode 600 owned by the runner's UID, and the container
#   -- a different UID -- couldn't reliably write to it, silently losing the
#   verdict. Docker's stdout stream doesn't have that problem.)

set -uo pipefail

RC="${ABI_RC:--1}"
PCT="${ABI_PCT:-?}"
SRC_PCT="${ABI_SRC_PCT:-?}"

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
  echo "PASS: ABI+API backward-compatible (binary: ${PCT}%, source: ${SRC_PCT}%) -> label: ${LABEL}"
else
  LABEL=minor; REMOVE=patch
  echo "PASS: ABI or API incompatible (binary: ${PCT}%, source: ${SRC_PCT}%) -> label: ${LABEL}"
fi

{
  echo "ABI_LABEL=${LABEL}"
  echo "ABI_LABEL_REMOVE=${REMOVE}"
} >> "$GITHUB_ENV"

# This marker line is the only channel the verdict needs out of the
# container: action.yml captures this script's stdout (docker already
# streams a container's stdout to the host process) and greps the marker
# out of it. No host-mounted file, no cross-UID write, nothing to fail on.
echo "ABI_LABEL_RESULT::${LABEL}"

exit 0
