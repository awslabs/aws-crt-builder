#!/usr/bin/env bash
#
# dump.sh - Locate the built shared library for each ref and dump its ABI.
#
# cmake installs only public headers to the install tree, so we point
# abi-dumper at <install>/include to scope the dump to the public API.
#
# Inputs (env):
#   ABI_LIB_NAME      library name -> lib<name>.so
#   ABI_HEAD_INSTALL  install prefix of the head build
#   ABI_BASE_INSTALL  install prefix of the base build
#
# Outputs (appended to $GITHUB_ENV):
#   ABI_OUT_DIR    report/work directory
#   ABI_BASE_SO    resolved path to the base .so
#   ABI_HEAD_SO    resolved path to the head .so
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

OUT_DIR="$(mktemp -d)" || { echo "ERROR: mktemp -d failed" >&2; exit 1; }
BASE_DUMP="${OUT_DIR}/base.dump"
HEAD_DUMP="${OUT_DIR}/head.dump"

echo "Dumping ABI for base ($BASE_SO) and head ($HEAD_SO) in parallel"
abi-dumper "$BASE_SO" -o "$BASE_DUMP" -lver base \
  -public-headers "${BASE_INSTALL}/include" &
pid_base=$!
abi-dumper "$HEAD_SO" -o "$HEAD_DUMP" -lver head \
  -public-headers "${HEAD_INSTALL}/include" &
pid_head=$!

rc_base=0; wait "$pid_base" || rc_base=$?
rc_head=0; wait "$pid_head" || rc_head=$?

{
  echo "ABI_OUT_DIR=${OUT_DIR}"
  echo "ABI_BASE_SO=${BASE_SO}"
  echo "ABI_HEAD_SO=${HEAD_SO}"
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
