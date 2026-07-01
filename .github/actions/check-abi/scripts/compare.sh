#!/usr/bin/env bash
#
# compare.sh - Run abi-compliance-checker on the two ABI dumps and record the
# verdict. This step never gates the build; it only captures state. The gate
# step interprets the recorded rc + SOVERSION.
#
# Flags:
#   -binary : gate on binary compatibility (old apps run against the new .so).
#             Every break we care about (added/removed struct member, changed
#             param/return type, removed symbol) is a binary break.
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
#   ABI_BASE_SO    base .so (for SONAME read)
#   ABI_HEAD_SO    head .so (for SONAME read)
#
# Outputs (appended to $GITHUB_ENV):
#   ABI_RC          abi-compliance-checker exit code
#   ABI_PCT         parsed binary compatibility percentage (or '?')
#   ABI_BASE_SOVER  base SONAME version (or empty)
#   ABI_HEAD_SOVER  head SONAME version (or empty)

set -uo pipefail

LIB_NAME="${ABI_LIB_NAME:?ABI_LIB_NAME must be set}"
OUT_DIR="${ABI_OUT_DIR:?ABI_OUT_DIR must be set}"
BASE_DUMP="${ABI_BASE_DUMP:?ABI_BASE_DUMP must be set}"
HEAD_DUMP="${ABI_HEAD_DUMP:?ABI_HEAD_DUMP must be set}"

REPORT_HTML="${OUT_DIR}/compat_report.html"
ACC_LOG="${OUT_DIR}/acc.log"

soversion() {
  local v
  v="$(readelf -d "$1" 2>/dev/null | grep -oP 'SONAME.*\.so\.\K[^\]]+' | head -n1)"
  # Validate before it flows into $GITHUB_ENV -> step summary; reject anything
  # that isn't a plain version string. Empty on no/invalid SONAME.
  [[ "$v" =~ ^[a-zA-Z0-9._-]+$ ]] && printf '%s' "$v"
}
BASE_SOVER="$(soversion "${ABI_BASE_SO:-}")"
HEAD_SOVER="$(soversion "${ABI_HEAD_SO:-}")"

echo "Comparing ABI"
rc=0
abi-compliance-checker -l "$LIB_NAME" \
  -old "$BASE_DUMP" -new "$HEAD_DUMP" \
  -report-path "$REPORT_HTML" \
  -strict -ext -binary \
  > "$ACC_LOG" 2>&1 || rc=$?

# abicc prints "Binary compatibility: N%" to stdout (captured in acc.log).
PCT="$(grep -oP 'Binary compatibility: \K[0-9.]+' "$ACC_LOG" 2>/dev/null | head -n1)"
[[ -n "$PCT" ]] || PCT='?'

echo "abi-compliance-checker exit code: $rc (binary compatibility: ${PCT}%)"

{
  echo "ABI_RC=${rc}"
  echo "ABI_PCT=${PCT}"
  echo "ABI_BASE_SOVER=${BASE_SOVER}"
  echo "ABI_HEAD_SOVER=${HEAD_SOVER}"
  echo "ABI_REPORT_HTML=${REPORT_HTML}"
  echo "ABI_ACC_LOG=${ACC_LOG}"
} >> "$GITHUB_ENV"
