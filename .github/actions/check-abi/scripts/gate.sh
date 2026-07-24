#!/usr/bin/env bash
#
# gate.sh - Interpret the recorded ABI verdict, choose a semver label, and fail
# the job ONLY when abi-compliance-checker could not produce a verdict.
#
# The label is computed from each report's own structured verdict comment
# (the first line of abi.html / src.html, e.g.
#   <!-- verdict:incompatible;affected:25;added:0;removed:1;
#        type_problems_high:0;type_problems_medium:0;type_problems_low:1;
#        interface_problems_high:0;interface_problems_medium:0;
#        interface_problems_low:0;changed_constants:0;tool_version:2.3 -->
# ), not from abicc's own exit code / overall verdict field: that field
# treats any Low-severity finding as "incompatible" (e.g. a pure parameter
# rename, confirmed against aws-c-common: rc=1, 99.97% binary, for
# `int local_time` -> `int is_local_time`), which would false-positive
# constantly if used directly. An axis has a real problem iff removed>0, any
# *_high/*_medium field is >0, or changed_constants>0 -- Low-severity-only
# findings are excluded as semantic-only advisories, not actual breaks.
#
#   source has a real problem                -> needs-review (a compile
#                                                break is never "just minor")
#   binary has a real problem, source clean   -> minor
#   neither                                   -> patch
#
# abicc's process exit code is used only to detect a tool failure (exit >= 2:
# no verdict, no report to parse) -- never to choose the label.
#
# SUPPLEMENTARY CHECK: abicc gives no signal at all for a removed constant
# declared via an anonymous or named enum (only #define removals surface via
# changed_constants) -- exactly aws-c-common's style for its length
# constants. check_constants.sh (ctags-based) catches this and is always
# treated as a source break.
#
# Inputs (env): ABI_RC, ABI_PCT, ABI_SRC_PCT, ABI_ACC_LOG, ABI_REPORT_HTML,
#               ABI_SRC_REPORT_HTML, ABI_REMOVED_CONSTANTS_COUNT
#
# Outputs: appends ABI_LABEL / ABI_LABEL_REMOVE to $GITHUB_ENV, and prints
# "ABI_LABEL_RESULT::<label>" as the last stdout line on success -- the
# marker action.yml greps out of the captured `docker run` output.

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

# Extract one field (e.g. "type_problems_high") as an integer from a report's
# verdict comment. Missing field or missing/unreadable file -> 0 (treated as
# "no problem"), since a field abicc doesn't emit for a given report mode
# means it found nothing to report in that category.
verdict_field() {
  local report_html="$1" field="$2"
  [[ -n "$report_html" && -f "$report_html" ]] || { echo 0; return; }
  grep -oP "${field}:\K[0-9]+" "$report_html" 2>/dev/null | head -n1 || echo 0
}

axis_has_real_problem() {
  local report_html="$1"
  local removed high1 med1 high2 med2 constants
  removed="$(verdict_field "$report_html" removed)"
  high1="$(verdict_field "$report_html" type_problems_high)"
  med1="$(verdict_field "$report_html" type_problems_medium)"
  high2="$(verdict_field "$report_html" interface_problems_high)"
  med2="$(verdict_field "$report_html" interface_problems_medium)"
  constants="$(verdict_field "$report_html" changed_constants)"
  [[ "${removed:-0}" -gt 0 || "${high1:-0}" -gt 0 || "${med1:-0}" -gt 0 || \
     "${high2:-0}" -gt 0 || "${med2:-0}" -gt 0 || "${constants:-0}" -gt 0 ]]
}

BIN_BROKEN=0
SRC_BROKEN=0
axis_has_real_problem "${ABI_REPORT_HTML:-}" && BIN_BROKEN=1
axis_has_real_problem "${ABI_SRC_REPORT_HTML:-}" && SRC_BROKEN=1

REMOVED_CONSTANTS_COUNT="${ABI_REMOVED_CONSTANTS_COUNT:-0}"
if [[ "$REMOVED_CONSTANTS_COUNT" -gt 0 ]]; then
  SRC_BROKEN=1
fi

if [[ "$SRC_BROKEN" -eq 1 ]]; then
  LABEL=needs-review; REMOVE=""
  echo "FLAG: source compatibility broken (binary: ${PCT}%, source: ${SRC_PCT}%) -> label: ${LABEL}"
  echo "      A source break means callers fail to RECOMPILE -- this is always a real"
  echo "      API-contract violation regardless of what the binary axis shows."
  if [[ "$REMOVED_CONSTANTS_COUNT" -gt 0 ]]; then
    echo "      Additionally, ${REMOVED_CONSTANTS_COUNT} macro/enum constant(s) were removed"
    echo "      (abicc gives no signal on this class of break -- see check_constants.sh)."
    if [[ -n "${ABI_REMOVED_CONSTANTS_FILE:-}" && -f "$ABI_REMOVED_CONSTANTS_FILE" ]]; then
      sed 's/^/        - /' "$ABI_REMOVED_CONSTANTS_FILE"
    fi
  fi
elif [[ "$BIN_BROKEN" -eq 1 ]]; then
  LABEL=minor; REMOVE=patch
  echo "PASS: binary compatibility broken, source clean (binary: ${PCT}%, source: ${SRC_PCT}%) -> label: ${LABEL}"
else
  LABEL=patch; REMOVE=minor
  echo "PASS: ABI+API backward-compatible (binary: ${PCT}%, source: ${SRC_PCT}%) -> label: ${LABEL}"
fi

{
  echo "ABI_LABEL=${LABEL}"
  echo "ABI_LABEL_REMOVE=${REMOVE}"
} >> "$GITHUB_ENV"

echo "ABI_LABEL_RESULT::${LABEL}"

exit 0
