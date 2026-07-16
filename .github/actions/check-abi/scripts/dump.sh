#!/usr/bin/env bash
#
# dump.sh - Locate the built shared library for each ref and dump its ABI.
#
# cmake installs only public headers to the install tree, so we point abidw's
# --headers-dir at <install>/include to scope the dump to the public API
# (abidw drops types not reachable from those headers; it does not filter
# exported-but-undeclared functions -- not an issue for CRT libs, which use
# -fvisibility=hidden + explicit _API export macros).
#
# Inputs (env):
#   ABI_LIB_NAME      library name -> lib<name>.so
#   ABI_HEAD_INSTALL  install prefix of the head build
#   ABI_BASE_INSTALL  install prefix of the base build
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

# abidw succeeds (rc 0) even on a .so with no debug info, emitting a
# near-empty corpus (just symbol names, no struct/type layout). A later
# abidiff on two such corpora would then also report rc 0 -- "no ABI
# difference" -- even if the underlying binaries changed completely. build.sh
# always compiles with "-g -Og", so debug info should always be present;
# checking for it here turns a silent false-negative into a loud failure
# instead of trusting abidw's own exit code (which doesn't reflect this).
check_debug_info() {
  local so="$1"
  local label="$2"
  if ! readelf -S "$so" 2>/dev/null | grep -q '\.debug_info'; then
    echo "ERROR: ${label} ($so) has no .debug_info section; ABI dump would be" >&2
    echo "       symbol-names-only and comparisons against it are unreliable." >&2
    exit 1
  fi
}
check_debug_info "$BASE_SO" "base"
check_debug_info "$HEAD_SO" "head"

OUT_DIR="$(mktemp -d)" || { echo "ERROR: mktemp -d failed" >&2; exit 1; }
BASE_DUMP="${OUT_DIR}/base.dump"
HEAD_DUMP="${OUT_DIR}/head.dump"

echo "Dumping ABI for base ($BASE_SO) and head ($HEAD_SO) in parallel"
abidw --headers-dir "${BASE_INSTALL}/include" "$BASE_SO" --out-file "$BASE_DUMP" &
pid_base=$!
abidw --headers-dir "${HEAD_INSTALL}/include" "$HEAD_SO" --out-file "$HEAD_DUMP" &
pid_head=$!

rc_base=0; wait "$pid_base" || rc_base=$?
rc_head=0; wait "$pid_head" || rc_head=$?

{
  echo "ABI_OUT_DIR=${OUT_DIR}"
  echo "ABI_BASE_DUMP=${BASE_DUMP}"
  echo "ABI_HEAD_DUMP=${HEAD_DUMP}"
} >> "$GITHUB_ENV"

if [[ "$rc_base" -ne 0 ]]; then
  echo "ERROR: abidw failed for base (exit $rc_base)" >&2
  exit 1
fi
if [[ "$rc_head" -ne 0 ]]; then
  echo "ERROR: abidw failed for head (exit $rc_head)" >&2
  exit 1
fi
