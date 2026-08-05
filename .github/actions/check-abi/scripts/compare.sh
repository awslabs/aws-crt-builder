#!/usr/bin/env bash
#
# compare.sh - Run abidiff on the two ABI dumps and record the verdict. This
# step never gates the build; it only captures state. The gate step maps the
# recorded exit code to a patch/minor label.
#
# abidiff's exit code is a bitmask (confirmed empirically -- see
# https://sourceware.org/libabigail/manual/abidiff.html):
#   bit 0 (1)  ABIDIFF_ERROR         - tool error
#   bit 1 (2)  ABIDIFF_USAGE_ERROR   - bad invocation (implies bit 0)
#   bit 2 (4)  ABIDIFF_ABI_CHANGE    - a reviewable ABI diff exists
#   bit 3 (8)  ABIDIFF_ABI_INCOMPATIBLE_CHANGE (implies bit 2, so 4|8=12)
# So: 0 = no change, 4 = compatible change, 12 = incompatible change, any
# value with bit 0 or bit 1 set (odd, or >=2 with bit1) = tool error.
#
# Diffing the two abidw XML dumps (rather than the two .so files directly) is
# deliberate: dumping first and diffing the dumps catches struct-layout
# changes that a direct .so-to-.so abidiff can miss.
#
# Inputs (env):
#   ABI_OUT_DIR    work directory
#   ABI_BASE_DUMP  base ABI dump
#   ABI_HEAD_DUMP  head ABI dump
#
# Outputs (appended to $GITHUB_ENV):
#   ABI_RC          abidiff exit code (bitmask)
#   ABI_INCOMPATIBLE  1 if bit 3 (ABIDIFF_ABI_INCOMPATIBLE_CHANGE) is set, else 0

set -uo pipefail

OUT_DIR="${ABI_OUT_DIR:?ABI_OUT_DIR must be set}"
BASE_DUMP="${ABI_BASE_DUMP:?ABI_BASE_DUMP must be set}"
HEAD_DUMP="${ABI_HEAD_DUMP:?ABI_HEAD_DUMP must be set}"

DIFF_LOG="${OUT_DIR}/abidiff.log"

echo "Comparing ABI"
rc=0
abidiff "$BASE_DUMP" "$HEAD_DUMP" > "$DIFF_LOG" 2>&1 || rc=$?

INCOMPATIBLE=0
if (( (rc & 8) != 0 )); then
  INCOMPATIBLE=1
fi

echo "abidiff exit code: $rc (incompatible: ${INCOMPATIBLE})"

{
  echo "ABI_RC=${rc}"
  echo "ABI_INCOMPATIBLE=${INCOMPATIBLE}"
  echo "ABI_DIFF_LOG=${DIFF_LOG}"
} >> "$GITHUB_ENV"
