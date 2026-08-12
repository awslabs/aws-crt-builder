#!/usr/bin/env bash
# Resolves commit pins from a nightly-pins.yml file.
#
# Usage:
#   resolve-pin.sh <pins-file> --package <name>
#     Looks up a single package pin. Writes 'branch_arg=-b <sha>' or
#     'branch_arg=' to $GITHUB_OUTPUT.
#
#   resolve-pin.sh <pins-file> --submodule-dirs <glob...>
#     Updates submodule directories to pinned commit or origin/main.

set -euo pipefail

PINS_FILE="$1"
shift

lookup_pin() {
    local name="$1"
    grep -E "^\s+${name}:" "$PINS_FILE" 2>/dev/null | awk '{print $2}' || true
}

mode_package() {
    local package="$1"
    local pin
    pin=$(lookup_pin "$package")
    if [ -n "$pin" ]; then
        echo "PINNED: $package -> $pin"
        echo "branch_arg=-b $pin" >> "$GITHUB_OUTPUT"
    else
        echo "No pin for $package, using main"
        echo "branch_arg=" >> "$GITHUB_OUTPUT"
    fi
}

mode_submodules() {
    for dir in "$@"; do
        local repo
        repo=$(basename "$dir")
        local pin
        pin=$(lookup_pin "$repo")
        if [ -n "$pin" ]; then
            echo "PINNED: $dir -> $pin"
            (cd "$dir" && git fetch origin && git checkout "$pin")
        else
            echo "Updating $dir to main..."
            (cd "$dir" && git fetch origin main && git checkout origin/main)
        fi
    done
}

case "${1:-}" in
    --package)
        shift
        mode_package "$1"
        ;;
    --submodule-dirs)
        shift
        mode_submodules "$@"
        ;;
    *)
        echo "Usage: resolve-pin.sh <pins-file> --package <name>" >&2
        echo "       resolve-pin.sh <pins-file> --submodule-dirs <glob...>" >&2
        exit 1
        ;;
esac
