---
name: speckit-git-remote
description: Detect Git remote URL for GitHub integration
compatibility: Requires spec-kit project structure with .specify/ directory
metadata:
  author: github-spec-kit
  source: git:commands/speckit.git.remote.md
---

# Detect Git Remote

Detect the `origin` remote and, if it points at GitHub, extract the `owner/repo` so other commands (e.g. `/speckit-taskstoissues`, PR creation) can target the right repository.

## Behavior

1. Read the remote URL: `git config --get remote.origin.url`.
2. If no `origin` remote is configured, report that clearly — do not guess or add one.
3. Parse both URL forms:
   - SSH: `git@github.com:owner/repo.git`
   - HTTPS: `https://github.com/owner/repo.git` (`.git` suffix optional)
4. Report `owner`, `repo`, and whether the remote is GitHub (vs. some other host, e.g. GitLab/Bitbucket, which GitHub-specific commands like `/speckit-taskstoissues` cannot use).

## Execution

```bash
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "[specify] Not a Git repository; skipped remote detection"; exit 0; }
URL=$(git config --get remote.origin.url 2>/dev/null)
if [ -z "$URL" ]; then
    echo "[specify] No 'origin' remote configured"
    exit 0
fi
if [[ "$URL" =~ github\.com[:/]([^/]+)/(.+)$ ]]; then
    OWNER="${BASH_REMATCH[1]}"
    REPO="${BASH_REMATCH[2]%.git}"
    echo "{\"host\":\"github\",\"owner\":\"$OWNER\",\"repo\":\"$REPO\"}"
else
    echo "{\"host\":\"other\",\"url\":\"$URL\"}"
fi
```

## Graceful Degradation

- No Git repository or no `origin` remote: report the gap, exit successfully (no error)
- Non-GitHub remote: report the raw URL and `host: "other"` so callers know GitHub-specific features (like `/speckit-taskstoissues`) won't work
