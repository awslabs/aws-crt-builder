#!/usr/bin/env bash
#
# abi_check.sh - In-container orchestrator for the ABI check.
#
# The individual stages (build/dump/compare/gate) chain state through
# $GITHUB_ENV: build.sh writes ABI_HEAD_INSTALL, dump.sh reads it, and so on.
# That channel only exists within a single process. When the check runs inside
# a `docker run` (so the ABI toolchain is baked into the image instead of being
# apt-get-installed on every run), the whole chain must execute as ONE process.
# This script is that process: it points GITHUB_ENV at a temp file and re-sources
# it between stages, so the stage scripts keep working unmodified.
#
# Only two things escape the container: the step-summary file (mounted from the
# host via GITHUB_STEP_SUMMARY) and this script's exit code (the gate verdict).
#
# Inputs (env, set by action.yml and passed through `docker run --env`):
#   ABI_LIB_NAME       library name (e.g. aws-c-s3)
#   BUILDER_VERSION    builder version/channel
#   BUILDER_SOURCE     releases | channels
#   BUILDER_HOST       builder artifact host URL
#   GITHUB_WORKSPACE   the PR head checkout (mounted into the container)
#   GITHUB_BASE_REF    target branch on pull_request events (may be empty)
#   ABI_BASE_REF       explicit base ref override (e.g. a release tag), passed
#                      through as-is to build.sh; see action.yml's base-ref input
#   GITHUB_STEP_SUMMARY  job summary file (mounted; optional)
#   GITHUB_RUN_ID / GITHUB_RUN_NUMBER  cache-buster for the builder download

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_NAME="${ABI_LIB_NAME:?ABI_LIB_NAME must be set}"
HEAD_DIR="${GITHUB_WORKSPACE:?GITHUB_WORKSPACE must be set}"

# The repo is bind-mounted from the host and owned by a different UID than the
# container's root; git refuses to operate on it without this.
git config --global --add safe.directory '*'

# --- Download builder.pyz (building is the only stage that needs it) ----------
BUILDER_HOST="${BUILDER_HOST:-https://d19elf31gohf1l.cloudfront.net}"
BUILDER_SOURCE="${BUILDER_SOURCE:-releases}"
BUILDER_VERSION="${BUILDER_VERSION:?BUILDER_VERSION must be set}"
RUN="${GITHUB_RUN_ID:-0}-${GITHUB_RUN_NUMBER:-0}"

BUILDER_PYZ="$(mktemp -d)/builder.pyz"
echo "Downloading builder from ${BUILDER_HOST}/${BUILDER_SOURCE}/${BUILDER_VERSION}/builder.pyz"
python3 -c "from urllib.request import urlretrieve; urlretrieve('${BUILDER_HOST}/${BUILDER_SOURCE}/${BUILDER_VERSION}/builder.pyz?run=${RUN}', '${BUILDER_PYZ}')"

# --- Bridge $GITHUB_ENV between stages ----------------------------------------
# Redirect GITHUB_ENV to a scratch file and export everything the stages append
# to it before invoking the next stage.
export GITHUB_ENV="$(mktemp)"
export ABI_LIB_NAME="$LIB_NAME"
export ABI_BUILDER_PYZ="$BUILDER_PYZ"

load_env() {
  # Export the KEY=value lines the previous stage appended, so the next stage
  # (and report.py, which reads os.environ) sees them.
  set -a
  # shellcheck source=/dev/null
  source "$GITHUB_ENV"
  set +a
}

# Remove any base worktree we registered in the mounted repo, so we don't leave
# stale worktree refs behind on the host. Runs on every exit path.
cleanup() {
  load_env 2>/dev/null || true
  if [[ -n "${ABI_BASE_WORKTREE:-}" ]]; then
    git -C "$HEAD_DIR" worktree remove --force "$ABI_BASE_WORKTREE" 2>/dev/null || true
  fi
  if [[ -n "${ABI_BASE_TMPDIR:-}" ]]; then
    rm -rf "$ABI_BASE_TMPDIR"
  fi
}
trap cleanup EXIT

# --- Run the stages -----------------------------------------------------------
# build/dump/compare each exit non-zero on a hard failure; stop there and let the
# gate/report see whatever state was recorded. report.py + gate.sh always run so
# the verdict is published even when an earlier stage failed.
run_stage() {
  local script="$1"
  bash "${SCRIPT_DIR}/${script}"
  local rc=$?
  load_env
  return "$rc"
}

run_stage build.sh   && \
run_stage dump.sh    && \
run_stage compare.sh
# (intentionally not gating here — gate.sh is the single source of pass/fail)

# Publish the summary and gate, mirroring action.yml's always() steps.
python3 "${SCRIPT_DIR}/report.py" || true
bash "${SCRIPT_DIR}/gate.sh"
