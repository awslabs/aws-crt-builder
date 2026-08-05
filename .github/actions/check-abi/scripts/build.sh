#!/usr/bin/env bash
#
# build.sh - Build the library (and its dependencies) for both the PR head and
# its base ref, as shared libraries with debug info, ready for ABI dumping.
#
# Building is the one part of the ABI check that uses builder.pyz, because
# builder owns the CRT dependency graph (aws-c-common, aws-c-io, ...).
#
# Inputs (env):
#   ABI_LIB_NAME      library / project name passed to `builder build -p`
#   ABI_BUILDER_PYZ   absolute path to the downloaded builder.pyz
#   GITHUB_WORKSPACE  the PR head checkout (set by GitHub Actions)
#   GITHUB_BASE_REF   target branch name on pull_request events (may be empty)
#
# Outputs (appended to $GITHUB_ENV):
#   ABI_BASE_WORKTREE  path to the base-ref git worktree
#   ABI_BASE_TMPDIR    parent tmp dir owning the worktree (for cleanup)
#   ABI_HEAD_INSTALL   install prefix of the head build
#   ABI_BASE_INSTALL   install prefix of the base build

set -uo pipefail

LIB_NAME="${ABI_LIB_NAME:?ABI_LIB_NAME must be set}"
BUILDER_PYZ="${ABI_BUILDER_PYZ:?ABI_BUILDER_PYZ must be set}"
HEAD_DIR="${GITHUB_WORKSPACE:?GITHUB_WORKSPACE must be set}"

# --- Resolve the base ref ----------------------------------------------------
if [[ -n "${GITHUB_BASE_REF:-}" ]]; then
  BASE_REF="origin/${GITHUB_BASE_REF}"
else
  BASE_REF="$(git -C "$HEAD_DIR" merge-base HEAD origin/main 2>/dev/null)"
  if [[ -z "$BASE_REF" ]]; then
    echo "ERROR: cannot determine ABI base ref. GITHUB_BASE_REF is unset and" >&2
    echo "       'git merge-base HEAD origin/main' failed. Trigger via a" >&2
    echo "       pull_request event, or ensure the default branch is named" >&2
    echo "       'main' and is fetchable (checkout with fetch-depth: 0)." >&2
    exit 1
  fi
fi
echo "ABI base ref: $BASE_REF"

# Verify the base ref actually resolves to a commit. With the default
# fetch-depth, origin/<base> may not be present in the checkout; fail with an
# actionable message instead of a confusing downstream build error.
if ! git -C "$HEAD_DIR" rev-parse --verify --quiet "${BASE_REF}^{commit}" >/dev/null; then
  echo "ERROR: base ref '${BASE_REF}' does not resolve to a commit in this checkout." >&2
  echo "       Ensure the consumer workflow checks out with 'fetch-depth: 0' so the" >&2
  echo "       base branch history is available." >&2
  exit 1
fi

# --- Create an isolated worktree for the base ref ----------------------------
BASE_TMPDIR="$(mktemp -d)" || { echo "ERROR: mktemp -d failed" >&2; exit 1; }
BASE_WORKTREE="${BASE_TMPDIR}/worktree"

# Record the tmp dir immediately so the cleanup step can remove it even if the
# worktree add or a later build fails.
echo "ABI_BASE_TMPDIR=${BASE_TMPDIR}" >> "$GITHUB_ENV"

if ! git -C "$HEAD_DIR" worktree add "$BASE_WORKTREE" "$BASE_REF"; then
  echo "ERROR: 'git worktree add' failed for base ref '${BASE_REF}'." >&2
  exit 1
fi
echo "ABI_BASE_WORKTREE=${BASE_WORKTREE}" >> "$GITHUB_ENV"

HEAD_INSTALL="${HEAD_DIR}/build/install"
BASE_INSTALL="${BASE_WORKTREE}/build/install"

# --- Build both refs in parallel ---------------------------------------------
# builder installs to <source_dir>/build/install. The same builder.pyz builds
# both refs; each invocation is an independent process with its own source dir.
build_ref() {
  local src_dir="$1"
  ( cd "$src_dir" && python3 "$BUILDER_PYZ" build -p "$LIB_NAME" \
      --cmake-extra=-DBUILD_SHARED_LIBS=ON \
      --cmake-extra=-DBUILD_TESTING=OFF \
      --cmake-extra="-DCMAKE_C_FLAGS=-g -Og" \
      run_tests=false )
}

echo "Building HEAD ($HEAD_DIR) and base ($BASE_WORKTREE) in parallel"
build_ref "$HEAD_DIR" &
pid_head=$!
build_ref "$BASE_WORKTREE" &
pid_base=$!

rc_head=0; wait "$pid_head" || rc_head=$?
rc_base=0; wait "$pid_base" || rc_base=$?

{
  echo "ABI_HEAD_INSTALL=${HEAD_INSTALL}"
  echo "ABI_BASE_INSTALL=${BASE_INSTALL}"
} >> "$GITHUB_ENV"

if [[ "$rc_head" -ne 0 ]]; then
  echo "ERROR: HEAD build failed (exit $rc_head)" >&2
  exit 1
fi
if [[ "$rc_base" -ne 0 ]]; then
  echo "ERROR: base build failed (exit $rc_base)" >&2
  exit 1
fi
