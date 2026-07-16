#!/usr/bin/env bash
#
# gate.sh - Interpret the recorded ABI verdict, choose a semver label, and fail
# the job ONLY when abidiff could not produce a verdict.
#
# This check is informational, not pass/fail: a compatible or incompatible ABI
# both succeed and are surfaced as a PR label. The job fails only when the check
# itself could not run (so there is no trustworthy verdict to label with).
#
# abidiff's exit code is a bitmask (see compare.sh for the bit layout):
#   bit 0/1 set (tool/usage error)      -> FAIL: no trustworthy verdict.
#   bit 3 set (ABIDIFF_INCOMPATIBLE)    -> label: minor (ABI changed; next
#                                          release is at least a minor bump)
#   bit 2 set only, or 0                -> label: patch (no change, or a
#                                          reviewable-but-compatible change)
#
# Inputs (env): ABI_RC, ABI_DIFF_LOG, ABI_LABEL_FILE (optional)
#
# Outputs:
#   Appends ABI_LABEL / ABI_LABEL_REMOVE to $GITHUB_ENV, and (if ABI_LABEL_FILE
#   is set) writes the chosen label there. ABI_LABEL_FILE is a host-mounted file,
#   so it is how the verdict escapes the container to the labeling step.

set -uo pipefail

RC="${ABI_RC:--1}"

if ! [[ "$RC" =~ ^-?[0-9]+$ ]]; then
  echo "FAIL: ABI_RC is not an integer ('$RC'); cannot determine a verdict."
  exit 1
fi

if [[ "$RC" -lt 0 ]]; then
  echo "FAIL: ABI check did not produce a verdict (a prior step failed)."
  exit 1
fi

if (( (RC & 3) != 0 )); then
  echo "ERROR: abidiff tool/usage error (exit $RC). No verdict produced."
  if [[ -n "${ABI_DIFF_LOG:-}" && -f "$ABI_DIFF_LOG" ]]; then
    echo "----- abidiff.log (last 200 lines) -----"
    tail -n 200 "$ABI_DIFF_LOG"
    echo "-----------------------------------------"
  fi
  exit "$RC"
fi

if (( (RC & 8) != 0 )); then
  LABEL=minor; REMOVE=patch
  echo "PASS: ABI incompatible (exit $RC) -> label: ${LABEL}"
else
  LABEL=patch; REMOVE=minor
  echo "PASS: ABI backward-compatible (exit $RC) -> label: ${LABEL}"
fi

{
  echo "ABI_LABEL=${LABEL}"
  echo "ABI_LABEL_REMOVE=${REMOVE}"
} >> "$GITHUB_ENV"

if [[ -n "${ABI_LABEL_FILE:-}" ]]; then
  if ! printf '%s\n' "$LABEL" > "$ABI_LABEL_FILE"; then
    echo "FAIL: could not write verdict to ABI_LABEL_FILE ('$ABI_LABEL_FILE')." >&2
    exit 1
  fi
  # The write can succeed by shell's reckoning yet leave the file unreadable
  # or empty on a mismatched-UID bind mount; verify what's actually on disk
  # instead of trusting the write call's exit code.
  WRITTEN="$(cat "$ABI_LABEL_FILE" 2>/dev/null || true)"
  if [[ "$(tr -d '[:space:]' <<< "$WRITTEN")" != "$LABEL" ]]; then
    echo "FAIL: verdict '${LABEL}' was not persisted to ABI_LABEL_FILE; read back '${WRITTEN}'." >&2
    exit 1
  fi
fi

exit 0
