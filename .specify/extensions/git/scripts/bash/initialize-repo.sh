#!/usr/bin/env bash
# Git extension: initialize-repo.sh
# Initializes a Git repository for a brand-new Spec Kit project, before the
# constitution is written (before_constitution hook). Safe to run on an existing
# repository — it no-ops rather than re-initializing.
#
# Usage: initialize-repo.sh

set -e

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./git-common.sh
source "$SCRIPT_DIR/git-common.sh"

REPO_ROOT="$(sk_find_project_root "$SCRIPT_DIR")" || REPO_ROOT="$(pwd)"
cd "$REPO_ROOT"

if ! command -v git >/dev/null 2>&1; then
    echo "[specify] Warning: Git not found; skipped repository initialization" >&2
    exit 0
fi

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "[specify] Already inside a Git repository; skipped initialization" >&2
    exit 0
fi

CONFIG_FILE="$REPO_ROOT/.specify/extensions/git/git-config.yml"
COMMIT_MESSAGE="$(sk_yaml_scalar "$CONFIG_FILE" "init_commit_message")"
[ -z "$COMMIT_MESSAGE" ] && COMMIT_MESSAGE="[Spec Kit] Initial commit"

_git_out=$(git init 2>&1) || { echo "[specify] Error: git init failed: $_git_out" >&2; exit 1; }
_git_out=$(git add . 2>&1) || { echo "[specify] Error: git add failed: $_git_out" >&2; exit 1; }
_git_out=$(git commit -q -m "$COMMIT_MESSAGE" 2>&1) || { echo "[specify] Error: git commit failed: $_git_out" >&2; exit 1; }

echo "[OK] Git repository initialized" >&2
