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
#   ABI_BASE_REF      explicit base ref override (e.g. a previous release tag).
#                      Takes precedence over GITHUB_BASE_REF/merge-base. Set by
#                      the release workflow to diff "previous tag vs current
#                      ref" instead of "PR base vs PR head".
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
if [[ -n "${ABI_BASE_REF:-}" ]]; then
  BASE_REF="${ABI_BASE_REF}"
elif [[ -n "${GITHUB_BASE_REF:-}" ]]; then
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
  # CMake appends CMAKE_C_FLAGS_RELWITHDEBINFO (default "-O2 -g -DNDEBUG")
  # after CMAKE_C_FLAGS for builder's default --config RelWithDebInfo, so
  # gcc's last -Ox flag (-O2) wins over a plain CMAKE_C_FLAGS override.
  # Overriding CMAKE_C_FLAGS_RELWITHDEBINFO directly makes -Og the only
  # optimization flag, which abi-dumper needs for accurate analysis.
  #
  # -gdwarf-4: GCC 11+ defaults to DWARF5, whose .debug_loclists format
  # abi-dumper's parser can't resolve (github.com/lvc/abi-dumper/issues/33),
  # logging a harmless "invalid debug_loc section" warning that only affects
  # dropped Source/SourceLine metadata, not the struct/type data
  # abi-compliance-checker compares. Forcing DWARF4 just silences the noise.
  #
  # --branch main: ensure both sides clone the same dep branch regardless of
  # the source project's current branch.
  ( cd "$src_dir" && python3 "$BUILDER_PYZ" build -p "$LIB_NAME" \
      --branch main \
      --cmake-extra=-DBUILD_SHARED_LIBS=ON \
      --cmake-extra=-DBUILD_TESTING=OFF \
      --cmake-extra="-DCMAKE_C_FLAGS_RELWITHDEBINFO=-g -Og -gdwarf-4 -DNDEBUG" \
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

# --- Log resolved dep SHAs ---------------------------------------------------
log_dep_shas() {
  local label="$1" src_dir="$2"
  local deps_dir="${src_dir}/build/deps" dep dep_name sha describe
  echo "=== deps resolved for ${label} build (${src_dir}) ==="
  if [[ ! -d "$deps_dir" ]]; then
    echo "  (no build/deps dir found at ${deps_dir})"
    return
  fi
  for dep in "$deps_dir"/*/; do
    [[ -d "${dep}.git" ]] || continue
    dep_name="$(basename "$dep")"
    sha="$(git -C "$dep" rev-parse HEAD 2>/dev/null || echo '?')"
    describe="$(git -C "$dep" describe --tags --always --long 2>/dev/null || echo '?')"
    printf '  %-25s %s  (%s)\n' "$dep_name" "$sha" "$describe"
  done
}

log_dep_shas "HEAD" "$HEAD_DIR"
log_dep_shas "BASE (${BASE_REF})" "$BASE_WORKTREE"

if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  head_deps_dir="${HEAD_DIR}/build/deps"
  base_deps_dir="${BASE_WORKTREE}/build/deps"
  {
    echo
    echo "### Resolved dependency versions"
    echo
    echo "| Dep | Base SHA | Head SHA | Match |"
    echo "|-----|----------|----------|-------|"
    if [[ -d "$head_deps_dir" || -d "$base_deps_dir" ]]; then
      { ls "$head_deps_dir" 2>/dev/null; ls "$base_deps_dir" 2>/dev/null; } | sort -u | while read -r dep_name; do
        [[ -z "$dep_name" ]] && continue
        base_sha="$(git -C "${base_deps_dir}/${dep_name}" rev-parse HEAD 2>/dev/null || echo 'missing')"
        head_sha="$(git -C "${head_deps_dir}/${dep_name}" rev-parse HEAD 2>/dev/null || echo 'missing')"
        if [[ "$base_sha" == "$head_sha" ]]; then match=":white_check_mark:"; else match=":warning:"; fi
        printf '| %s | `%s` | `%s` | %s |\n' "$dep_name" "${base_sha:0:12}" "${head_sha:0:12}" "$match"
      done
    else
      echo "| (no build/deps dirs found) | - | - | - |"
    fi
  } >> "$GITHUB_STEP_SUMMARY"
fi

if [[ "$rc_head" -ne 0 ]]; then
  echo "ERROR: HEAD build failed (exit $rc_head)" >&2
  exit 1
fi
if [[ "$rc_base" -ne 0 ]]; then
  echo "ERROR: base build failed (exit $rc_base)" >&2
  exit 1
fi
