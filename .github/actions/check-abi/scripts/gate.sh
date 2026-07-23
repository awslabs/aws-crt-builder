#!/usr/bin/env bash
#
# gate.sh - Interpret the recorded ABI verdict, choose a semver label, and fail
# the job ONLY when abi-compliance-checker could not produce a verdict.
#
# This check is informational, not pass/fail: every real verdict (patch,
# minor, or needs-review) succeeds -- the job fails only when the check itself
# could not run (so there is no trustworthy verdict to label with).
#
# LABEL DECISION -- three-way, not two-way. abicc's own exit code / overall
# "verdict:compatible|incompatible" field is NOT used to choose the label,
# because it conflates two things a reviewer needs to see separately:
#   - abicc flags plenty of harmless changes at Low severity (a pure
#     parameter-name rename, an enum-member rename with a value that doesn't
#     change) as "incompatible" -- confirmed empirically against the real
#     aws-c-common library: rc=1, "verdict:incompatible", 99.97% binary, for
#     nothing more than `int local_time` -> `int is_local_time`. Gating on
#     rc/verdict alone would false-positive on this constantly.
#   - a SOURCE break is categorically different from a binary-only break: it
#     means callers fail to *recompile*, a real, unconditional API-contract
#     violation with no legitimate "I meant to do that" reading the way a
#     binary-only break sometimes has. It must never be silently downgraded
#     to a routine minor-bump label.
#
# So the real signal is each report's own structured verdict comment (the
# first line of abi.html / src.html, e.g.:
#   <!-- verdict:incompatible;affected:25;added:0;removed:1;
#        type_problems_high:0;type_problems_medium:0;type_problems_low:1;
#        interface_problems_high:0;interface_problems_medium:0;
#        interface_problems_low:0;changed_constants:0;tool_version:2.3 -->
# ) -- parsed independently for the binary and the source report. An axis
# has a REAL problem iff removed>0, or any *_high/*_medium field is >0, or
# changed_constants>0. Low-severity-only fields are deliberately excluded:
# every empirical Low finding we found in a large scenario sweep (parameter
# renames, enum-member renames, struct-field renames) was a semantic-only
# advisory, not an actual break -- see the scenario matrix in the abi-gail
# session history. Excluding Low keeps the gate from crying wolf on those.
#
#   source has a real problem                -> needs-review (unconditional:
#                                                a compile-break is never "just minor")
#   binary has a real problem, source clean   -> minor (reviewer can decide;
#                                                intentional binary breaks do
#                                                happen and are a normal
#                                                minor-version-bump event)
#   neither axis has a real problem           -> patch
#
# abi-compliance-checker's own process exit code is used ONLY to detect a
# tool failure (exit >= 2 = could not run at all, no verdict, no report to
# parse), not to choose the label:
#   0/1    ran successfully, produced reports -> parse verdict comments (above)
#   2-11   tool error (bad input, can't compile, empty symbol set, ...)
#          -> FAIL: the check could not run, no verdict was produced.
#
# SUPPLEMENTARY CHECK: abicc has a confirmed blind spot for constants declared
# via an anonymous or named enum (`enum { X = 20 };`) -- it flags a REMOVED
# #define correctly via changed_constants, but a removed enum-based constant
# produces zero signal on either report (verified directly: 100%/100%, all
# fields 0, despite a real "undeclared identifier" compile error). This is
# exactly aws-c-common's own style for its length constants, so it's not a
# hypothetical gap. check_constants.sh (ctags-based, independent of abicc)
# catches this and is always treated as a source break -- there is no
# legitimate reading of "a public constant a caller might reference by name
# just vanished" other than "this breaks compilation."
#
# Inputs (env): ABI_RC, ABI_PCT, ABI_SRC_PCT, ABI_ACC_LOG, ABI_REPORT_HTML,
#               ABI_SRC_REPORT_HTML, ABI_REMOVED_CONSTANTS_COUNT
#
# Outputs:
#   Appends ABI_LABEL / ABI_LABEL_REMOVE to $GITHUB_ENV (for stages within this
#   container run), and prints "ABI_LABEL_RESULT::<label>" as the last stdout
#   line on success. That line is how the verdict escapes the container: the
#   composite action step captures this script's stdout via command
#   substitution and greps out the marker -- no host-mounted file needed,
#   since docker already streams stdout back to the host process.

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

# This marker line is the only channel the verdict needs out of the
# container: action.yml captures this script's stdout (docker already
# streams a container's stdout to the host process) and greps the marker
# out of it. No host-mounted file, no cross-UID write, nothing to fail on.
echo "ABI_LABEL_RESULT::${LABEL}"

exit 0
