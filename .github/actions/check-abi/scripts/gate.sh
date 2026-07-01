#!/usr/bin/env bash
#
# gate.sh - Interpret the recorded ABI verdict and fail the job if the change
# is an unauthorized break.
#
# abi-compliance-checker exit codes:
#   0      compatible, ran clean                -> PASS
#   1      incompatible, ran clean              -> PASS only if SOVERSION bumped
#   2-11   tool error (bad input, can't compile, empty symbol set, ...)
#          -> always FAIL; a tool error means no trustworthy verdict, so it can
#             never be masked by a SOVERSION bump.
#
# Inputs (env): ABI_RC, ABI_PCT, ABI_BASE_SOVER, ABI_HEAD_SOVER, ABI_ACC_LOG

set -uo pipefail

RC="${ABI_RC:--1}"
PCT="${ABI_PCT:-?}"
BASE_SOVER="${ABI_BASE_SOVER:-}"
HEAD_SOVER="${ABI_HEAD_SOVER:-}"

# A genuine bump requires BOTH sovers to be readable and to differ. base->empty
# is a packaging regression (lost SONAME), not a bump — it must not clear a break.
BUMPED=false
[[ -n "$BASE_SOVER" && -n "$HEAD_SOVER" && "$BASE_SOVER" != "$HEAD_SOVER" ]] && BUMPED=true

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
  echo "PASS: ABI backward-compatible (${PCT}%)"
  exit 0
fi

# RC == 1: genuine incompatibility. A SOVERSION bump is the only valid escape.
if [[ "$BUMPED" == true ]]; then
  echo "PASS: ABI changed (${PCT}%) but SOVERSION bumped (${BASE_SOVER} -> ${HEAD_SOVER})"
  exit 0
fi

echo "FAIL: ABI incompatible (${PCT}%) and SOVERSION unchanged (${BASE_SOVER:-none})"
exit 1
