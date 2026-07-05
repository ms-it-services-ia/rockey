---
name: speckit-git-validate
description: Validate current branch follows feature branch naming conventions
compatibility: Requires spec-kit project structure with .specify/ directory
metadata:
  author: github-spec-kit
  source: git:commands/speckit.git.validate.md
---

# Validate Feature Branch

Check that the current Git branch follows Spec Kit's feature branch naming convention, and warn (without blocking) if it doesn't.

## Behavior

1. Skip entirely if Git is not available or the current directory is not a Git repository.
2. Read the current branch: `git rev-parse --abbrev-ref HEAD`.
3. Strip a single optional gitflow-style prefix (e.g. `feat/004-name` -> `004-name`) before validating.
4. Accept the branch as valid if it matches either:
   - Sequential: `^[0-9]{3,}-` (e.g. `003-user-auth`)
   - Timestamp: `^[0-9]{8}-[0-9]{6}-` (e.g. `20260319-143022-user-auth`)
5. If neither pattern matches, report which branch is checked out and that it doesn't follow the convention — do not rename or check out branches automatically.

## Execution

```bash
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "[specify] Not a Git repository; skipped validation"; exit 0; }
BRANCH=$(git rev-parse --abbrev-ref HEAD)
EFFECTIVE=$(printf '%s' "$BRANCH" | sed -E 's#^[^/]+/(.+)$#\1#')
if [[ "$EFFECTIVE" =~ ^[0-9]{8}-[0-9]{6}- ]] || [[ "$EFFECTIVE" =~ ^[0-9]{3,}- ]]; then
    echo "[OK] Branch '$BRANCH' follows the feature branch naming convention"
else
    echo "[specify] Warning: branch '$BRANCH' does not look like a feature branch (expected NNN-slug or YYYYMMDD-HHMMSS-slug)"
fi
```

## When to Use

Run this manually before `/speckit-plan` or `/speckit-tasks` if you're unsure whether you're on the right branch — it is not wired into any automatic hook.

## Graceful Degradation

- Not a Git repository: skip with a message, exit successfully
- Branch name doesn't match: warn only, never fails the command or renames anything
