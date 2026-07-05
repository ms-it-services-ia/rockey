#!/usr/bin/env bash
# Agent-context extension: update-agent-context.sh
# Refreshes the managed Spec Kit section inside the active coding agent's context
# file (e.g. CLAUDE.md) so it points at the most recently created feature's plan.md.
#
# Usage: update-agent-context.sh [plan_path]
#   plan_path   Optional. Defaults to the most recently modified specs/*/plan.md.

set -e

PLAN_PATH_ARG="${1:-}"

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

_find_project_root() {
    local dir="$1"
    while [ "$dir" != "/" ]; do
        [ -d "$dir/.specify" ] && { echo "$dir"; return 0; }
        dir="$(dirname "$dir")"
    done
    return 1
}

REPO_ROOT="$(_find_project_root "$SCRIPT_DIR")" || REPO_ROOT="$(pwd)"
cd "$REPO_ROOT"

CONFIG_FILE="$REPO_ROOT/.specify/extensions/agent-context/agent-context-config.yml"
CONTEXT_FILE=""
MARKER_START="<!-- SPECKIT START -->"
MARKER_END="<!-- SPECKIT END -->"

if [ -f "$CONFIG_FILE" ]; then
    CONTEXT_FILE=$(grep -E '^context_file:' "$CONFIG_FILE" | head -n1 | sed -E 's/^context_file:[[:space:]]*//')
    _start=$(grep -E '^[[:space:]]+start:' "$CONFIG_FILE" | head -n1 | sed -E 's/^[[:space:]]+start:[[:space:]]*//')
    _end=$(grep -E '^[[:space:]]+end:' "$CONFIG_FILE" | head -n1 | sed -E 's/^[[:space:]]+end:[[:space:]]*//')
    [ -n "$_start" ] && MARKER_START="$_start"
    [ -n "$_end" ] && MARKER_END="$_end"
fi

if [ -z "$CONTEXT_FILE" ]; then
    echo "[specify] No context_file configured; nothing to do" >&2
    exit 0
fi

CONTEXT_PATH="$REPO_ROOT/$CONTEXT_FILE"
if [ ! -f "$CONTEXT_PATH" ]; then
    echo "[specify] Context file '$CONTEXT_FILE' not found; nothing to do" >&2
    exit 0
fi

if [ -z "$PLAN_PATH_ARG" ]; then
    PLAN_PATH_ARG=$(ls -t "$REPO_ROOT"/specs/*/plan.md 2>/dev/null | head -n1 || true)
fi

if [ -z "$PLAN_PATH_ARG" ]; then
    echo "[specify] No plan.md found under specs/; nothing to do" >&2
    exit 0
fi

PLAN_REL="${PLAN_PATH_ARG#"$REPO_ROOT"/}"

BLOCK="${MARKER_START}
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:
${PLAN_REL}
${MARKER_END}"

if grep -qF "$MARKER_START" "$CONTEXT_PATH" 2>/dev/null; then
    # The replacement block is multi-line, and BSD awk (macOS's default /usr/bin/awk)
    # rejects a multi-line value passed via -v ("newline in string"). Feed it as a
    # second file argument instead, read via FNR==NR, so no -v variable ever holds
    # an embedded newline.
    BLOCK_FILE=$(mktemp)
    trap 'rm -f "$BLOCK_FILE"' EXIT
    printf '%s\n' "$BLOCK" > "$BLOCK_FILE"
    awk -v start="$MARKER_START" -v end="$MARKER_END" '
        FNR == NR { block[NR] = $0; blocklines = NR; next }
        $0 == start { for (i = 1; i <= blocklines; i++) print block[i]; skip = 1; next }
        skip && $0 == end { skip = 0; next }
        skip { next }
        { print }
    ' "$BLOCK_FILE" "$CONTEXT_PATH" > "$CONTEXT_PATH.tmp"
    mv "$CONTEXT_PATH.tmp" "$CONTEXT_PATH"
    rm -f "$BLOCK_FILE"
    trap - EXIT
else
    {
        [ -s "$CONTEXT_PATH" ] && echo ""
        printf '%s\n' "$BLOCK"
    } >> "$CONTEXT_PATH"
fi

echo "[OK] Agent context updated: $CONTEXT_FILE -> $PLAN_REL" >&2
