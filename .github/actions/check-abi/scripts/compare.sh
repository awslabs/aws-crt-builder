#!/usr/bin/env bash
#
# compare.sh - Run abi-compliance-checker on the two ABI dumps and record the
# verdict. This step never gates the build; it only captures state. The gate
# step maps the recorded exit code to a patch/minor label.
#
# Flags:
#   -binary : gate on binary compatibility (old apps run against the new .so).
#             Every break we care about (added/removed struct member, changed
#             param/return type, removed symbol) is a binary break.
#   -source : gate on SOURCE compatibility (does a consumer's .c file still
#             compile against the new headers). This catches renamed/removed
#             enum constants, macros, and typedefs -- changes that are 100%
#             binary-compatible (same underlying value, nothing in the .so
#             changes) but break `gcc` the moment anyone rebuilds against the
#             new header. -binary alone is blind to this class of break; see
#             the "Name of member ... has been changed from X to Y" finding
#             abicc's -source mode produces for a renamed enum constant.
#   -ext    : check ALL public data types, even those only reachable via a
#             callback fn-ptr (e.g. aws_s3_meta_request_progress via
#             progress_callback). Without it abicc's reachability filter would
#             silently report adding a member to such a struct as compatible.
#   -strict : treat low-severity issues as problems too.
#
# Inputs (env):
#   ABI_LIB_NAME   library name (abicc -l)
#   ABI_OUT_DIR    work directory
#   ABI_BASE_DUMP  base ABI dump
#   ABI_HEAD_DUMP  head ABI dump
#
# Outputs (appended to $GITHUB_ENV):
#   ABI_RC          abi-compliance-checker exit code (reflects both binary
#                    AND source compatibility -- non-zero if either fails)
#   ABI_PCT         parsed binary compatibility percentage (or '?')
#   ABI_SRC_PCT     parsed source compatibility percentage (or '?')

set -uo pipefail

LIB_NAME="${ABI_LIB_NAME:?ABI_LIB_NAME must be set}"
OUT_DIR="${ABI_OUT_DIR:?ABI_OUT_DIR must be set}"
BASE_DUMP="${ABI_BASE_DUMP:?ABI_BASE_DUMP must be set}"
HEAD_DUMP="${ABI_HEAD_DUMP:?ABI_HEAD_DUMP must be set}"

BIN_REPORT_HTML="${OUT_DIR}/abi_compat_report.html"
SRC_REPORT_HTML="${OUT_DIR}/src_compat_report.html"
ACC_LOG="${OUT_DIR}/acc.log"

echo "Comparing ABI and API (binary + source compatibility)"
rc=0
abi-compliance-checker -l "$LIB_NAME" \
  -old "$BASE_DUMP" -new "$HEAD_DUMP" \
  -bin-report-path "$BIN_REPORT_HTML" \
  -src-report-path "$SRC_REPORT_HTML" \
  -strict -ext -binary -source \
  > "$ACC_LOG" 2>&1 || rc=$?

# abicc prints "Binary compatibility: N%" / "Source compatibility: N%" to
# stdout (captured in acc.log).
PCT="$(grep -oP 'Binary compatibility: \K[0-9.]+' "$ACC_LOG" 2>/dev/null | head -n1)"
[[ -n "$PCT" ]] || PCT='?'
SRC_PCT="$(grep -oP 'Source compatibility: \K[0-9.]+' "$ACC_LOG" 2>/dev/null | head -n1)"
[[ -n "$SRC_PCT" ]] || SRC_PCT='?'

echo "abi-compliance-checker exit code: $rc (binary: ${PCT}%, source: ${SRC_PCT}%)"

{
  echo "ABI_RC=${rc}"
  echo "ABI_PCT=${PCT}"
  echo "ABI_SRC_PCT=${SRC_PCT}"
  echo "ABI_REPORT_HTML=${BIN_REPORT_HTML}"
  echo "ABI_SRC_REPORT_HTML=${SRC_REPORT_HTML}"
  echo "ABI_ACC_LOG=${ACC_LOG}"
} >> "$GITHUB_ENV"
