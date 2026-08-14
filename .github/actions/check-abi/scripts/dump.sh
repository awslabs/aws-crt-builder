#!/usr/bin/env bash
#
# dump.sh - Locate the built shared library for each ref and dump its ABI.
#
# The install tree at <install>/include/aws/ is a UNION of every library in
# the dep graph: aws-c-common/, aws-c-io/, aws-c-cal/, ... and finally the
# target library's own headers. Pointing abi-dumper at <install>/include
# would silently pull transitive dep types into this library's ABI dump, so
# an aws-c-io struct change would surface as this library's ABI drift.
# Scope -public-headers to just <install>/include/aws/<subdir>/ instead --
# subdir derived from LIB_NAME (aws-c-X -> X, aws-X -> X), overridable via
# ABI_HEADER_SUBDIR for outliers (aws-c-iot installs under aws/iotdevice/).
#
# Inputs (env):
#   ABI_LIB_NAME       library name -> lib<name>.so
#   ABI_HEAD_INSTALL   install prefix of the head build
#   ABI_BASE_INSTALL   install prefix of the base build
#   ABI_HEADER_SUBDIR  optional: subdir under include/aws/ containing this
#                       library's public headers. Defaults to LIB_NAME with
#                       the leading "aws-c-" (else "aws-") prefix stripped.
#
# Outputs (appended to $GITHUB_ENV):
#   ABI_OUT_DIR    report/work directory
#   ABI_BASE_DUMP  base ABI dump file
#   ABI_HEAD_DUMP  head ABI dump file

set -uo pipefail

LIB_NAME="${ABI_LIB_NAME:?ABI_LIB_NAME must be set}"
HEAD_INSTALL="${ABI_HEAD_INSTALL:?ABI_HEAD_INSTALL must be set}"
BASE_INSTALL="${ABI_BASE_INSTALL:?ABI_BASE_INSTALL must be set}"

find_so() {
  find "$1" -maxdepth 5 -name "lib${LIB_NAME}.so" 2>/dev/null | head -n1
}

BASE_SO="$(find_so "$BASE_INSTALL")"
HEAD_SO="$(find_so "$HEAD_INSTALL")"
[[ -n "$BASE_SO" ]] || { echo "ERROR: lib${LIB_NAME}.so not found under $BASE_INSTALL" >&2; exit 1; }
[[ -n "$HEAD_SO" ]] || { echo "ERROR: lib${LIB_NAME}.so not found under $HEAD_INSTALL" >&2; exit 1; }

# Derive the header subdir from the library name unless the caller overrode it.
SUBDIR="${ABI_HEADER_SUBDIR:-}"
if [[ -z "$SUBDIR" ]]; then
  SUBDIR="${LIB_NAME#aws-c-}"
  [[ "$SUBDIR" == "$LIB_NAME" ]] && SUBDIR="${LIB_NAME#aws-}"
fi

BASE_HEADERS="${BASE_INSTALL}/include/aws/${SUBDIR}"
HEAD_HEADERS="${HEAD_INSTALL}/include/aws/${SUBDIR}"
[[ -d "$BASE_HEADERS" ]] || { echo "ERROR: public headers not found at $BASE_HEADERS. Override with the check-abi action's 'header-subdir' input." >&2; exit 1; }
[[ -d "$HEAD_HEADERS" ]] || { echo "ERROR: public headers not found at $HEAD_HEADERS. Override with the check-abi action's 'header-subdir' input." >&2; exit 1; }

OUT_DIR="$(mktemp -d)" || { echo "ERROR: mktemp -d failed" >&2; exit 1; }
BASE_DUMP="${OUT_DIR}/base.dump"
HEAD_DUMP="${OUT_DIR}/head.dump"

echo "Dumping ABI for base ($BASE_SO) and head ($HEAD_SO); headers scoped to aws/${SUBDIR}/"
abi-dumper "$BASE_SO" -o "$BASE_DUMP" -lver base \
  -public-headers "$BASE_HEADERS" &
pid_base=$!
abi-dumper "$HEAD_SO" -o "$HEAD_DUMP" -lver head \
  -public-headers "$HEAD_HEADERS" &
pid_head=$!

rc_base=0; wait "$pid_base" || rc_base=$?
rc_head=0; wait "$pid_head" || rc_head=$?

{
  echo "ABI_OUT_DIR=${OUT_DIR}"
  echo "ABI_BASE_DUMP=${BASE_DUMP}"
  echo "ABI_HEAD_DUMP=${HEAD_DUMP}"
} >> "$GITHUB_ENV"

if [[ "$rc_base" -ne 0 ]]; then
  echo "ERROR: abi-dumper failed for base (exit $rc_base)" >&2
  exit 1
fi
if [[ "$rc_head" -ne 0 ]]; then
  echo "ERROR: abi-dumper failed for head (exit $rc_head)" >&2
  exit 1
fi
