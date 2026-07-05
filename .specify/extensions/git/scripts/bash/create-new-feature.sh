#!/usr/bin/env bash
# Git extension: create-new-feature.sh
# Creates and checks out a git branch for a new Spec Kit feature (branch creation
# only — the spec directory/files are created separately by the core
# /speckit-specify workflow).
#
# Usage: create-new-feature.sh [--json] [--timestamp] --short-name <name> <feature description>
#
# Honors the GIT_BRANCH_NAME environment variable: when set, it is used verbatim
# as the branch name and all prefix/short-name generation is skipped.

set -e

JSON_MODE=false
USE_TIMESTAMP=false
SHORT_NAME=""
ARGS=()

while [ $# -gt 0 ]; do
    case "$1" in
        --json) JSON_MODE=true ;;
        --timestamp) USE_TIMESTAMP=true ;;
        --short-name)
            [ $# -ge 2 ] || { echo "Error: --short-name requires a value" >&2; exit 1; }
            SHORT_NAME="$2"
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [--json] [--timestamp] --short-name <name> <feature_description>"
            exit 0
            ;;
        *) ARGS+=("$1") ;;
    esac
    shift
done

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./git-common.sh
source "$SCRIPT_DIR/git-common.sh"

REPO_ROOT="$(sk_find_project_root "$SCRIPT_DIR")" || REPO_ROOT="$(pwd)"
cd "$REPO_ROOT"

CONFIG_FILE="$REPO_ROOT/.specify/extensions/git/git-config.yml"
INIT_OPTIONS_FILE="$REPO_ROOT/.specify/init-options.json"

if [ -n "${GIT_BRANCH_NAME:-}" ]; then
    BRANCH_NAME="$GIT_BRANCH_NAME"
    if [[ "$BRANCH_NAME" =~ ^([0-9]+) ]]; then
        FEATURE_NUM="${BASH_REMATCH[1]}"
    else
        FEATURE_NUM="$BRANCH_NAME"
    fi
else
    if [ -z "$SHORT_NAME" ]; then
        echo "Error: --short-name is required unless GIT_BRANCH_NAME is set" >&2
        exit 1
    fi

    # Slugify: lowercase, spaces/underscores -> hyphens, strip anything not [a-z0-9-]
    SLUG=$(printf '%s' "$SHORT_NAME" | tr '[:upper:]' '[:lower:]' | tr ' _' '-' | tr -cd 'a-z0-9-' | sed -E 's/-+/-/g; s/^-|-$//g')

    NUMBERING_MODE=$(sk_yaml_scalar "$CONFIG_FILE" "branch_numbering")
    if [ -z "$NUMBERING_MODE" ]; then
        NUMBERING_MODE=$(sk_json_scalar "$INIT_OPTIONS_FILE" "branch_numbering")
    fi
    [ -z "$NUMBERING_MODE" ] && NUMBERING_MODE="sequential"
    [ "$USE_TIMESTAMP" = true ] && NUMBERING_MODE="timestamp"

    if [ "$NUMBERING_MODE" = "timestamp" ]; then
        PREFIX="$(date +%Y%m%d-%H%M%S)"
        FEATURE_NUM="$PREFIX"
    else
        HIGHEST=0
        if [ -d "$REPO_ROOT/specs" ]; then
            for dir in "$REPO_ROOT"/specs/*/; do
                [ -d "$dir" ] || continue
                name=$(basename "$dir")
                # Sequential prefixes only (>=3 digits) — exclude timestamp dirs
                # (8-digit date + 6-digit time), which also match ^[0-9]{3,}-.
                if [[ "$name" =~ ^[0-9]{3,}- ]] && [[ ! "$name" =~ ^[0-9]{8}-[0-9]{6}- ]]; then
                    n=$((10#$(printf '%s' "$name" | grep -Eo '^[0-9]+')))
                    [ "$n" -gt "$HIGHEST" ] && HIGHEST=$n
                fi
            done
        fi
        if sk_has_git; then
            while IFS= read -r name; do
                [ -z "$name" ] && continue
                if [[ "$name" =~ ^[0-9]{3,}- ]] && [[ ! "$name" =~ ^[0-9]{8}-[0-9]{6}- ]]; then
                    n=$((10#$(printf '%s' "$name" | grep -Eo '^[0-9]+')))
                    [ "$n" -gt "$HIGHEST" ] && HIGHEST=$n
                fi
            done < <(git branch -a 2>/dev/null | sed 's/^[* ]*//; s|^remotes/[^/]*/||')
        fi
        PREFIX=$(printf '%03d' "$((HIGHEST + 1))")
        FEATURE_NUM="$PREFIX"
    fi

    BRANCH_NAME="${PREFIX}-${SLUG}"
fi

if sk_has_git; then
    if git rev-parse --verify "$BRANCH_NAME" >/dev/null 2>&1; then
        git checkout "$BRANCH_NAME" >/dev/null
    else
        git checkout -b "$BRANCH_NAME" >/dev/null
    fi
else
    echo "[specify] Warning: Git repository not detected; skipped branch creation" >&2
fi

if [ "$JSON_MODE" = true ]; then
    printf '{"BRANCH_NAME":"%s","FEATURE_NUM":"%s"}\n' "$BRANCH_NAME" "$FEATURE_NUM"
else
    printf 'BRANCH_NAME=%s\n' "$BRANCH_NAME"
    printf 'FEATURE_NUM=%s\n' "$FEATURE_NUM"
fi
