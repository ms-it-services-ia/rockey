#!/usr/bin/env bash
# Git extension: git-common.sh
# Shared helper functions for the git extension's scripts (create-new-feature.sh,
# initialize-repo.sh). Meant to be sourced, not executed directly.
#
# auto-commit.sh predates this file and keeps its own inline copy of similar
# project-root/config-parsing logic; it is intentionally left alone here.

# Walk upward from $1 (or the current directory) looking for a Spec Kit / Git marker.
sk_find_project_root() {
    local dir="${1:-$(pwd)}"
    while [ "$dir" != "/" ]; do
        if [ -d "$dir/.specify" ] || [ -d "$dir/.git" ]; then
            echo "$dir"
            return 0
        fi
        dir="$(dirname "$dir")"
    done
    return 1
}

# True if the git CLI is installed and the current directory is inside a work tree.
sk_has_git() {
    command -v git >/dev/null 2>&1 || return 1
    git rev-parse --is-inside-work-tree >/dev/null 2>&1
}

# Read a top-level "key: value" scalar from a simple YAML file (no nested traversal).
# Strips surrounding quotes and trailing whitespace. Prints nothing if the file or
# key doesn't exist.
sk_yaml_scalar() {
    local file="$1" key="$2"
    [ -f "$file" ] || return 0
    grep -E "^${key}:" "$file" 2>/dev/null \
        | head -n1 \
        | sed -E "s/^${key}:[[:space:]]*//" \
        | sed -E 's/^["'\'']//; s/["'\'']$//; s/[[:space:]]+$//'
}

# Read a top-level string value from a flat JSON file. Prefers jq/python3 when
# available; falls back to a single-line grep/sed for the simple `"key": "value"` case.
sk_json_scalar() {
    local file="$1" key="$2"
    [ -f "$file" ] || return 0
    if command -v jq >/dev/null 2>&1; then
        jq -r --arg k "$key" '.[$k] // empty' "$file" 2>/dev/null
        return 0
    fi
    if command -v python3 >/dev/null 2>&1; then
        python3 -c "
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    print(d.get(sys.argv[2], '') or '')
except Exception:
    pass
" "$file" "$key" 2>/dev/null
        return 0
    fi
    grep -E "\"${key}\"[[:space:]]*:" "$file" 2>/dev/null \
        | head -n1 \
        | sed -E 's/^[^:]*:[[:space:]]*"?([^",}]*)"?.*$/\1/'
}
