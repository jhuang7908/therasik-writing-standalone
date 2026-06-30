#!/usr/bin/env bash
# Safe git push for journal pipeline bots — merge remote instead of rebase conflicts.
set -euo pipefail

MSG="${1:?commit message required}"
PATHS="${2:-assets/journal_requirements/}"

git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"

git add $PATHS
if git diff --cached --quiet; then
  echo "No changes to commit"
  exit 0
fi

git commit -m "$MSG"

for attempt in 1 2 3; do
  git fetch origin main
  if git merge origin/main --no-edit -m "chore: merge main before push [skip ci]"; then
    :
  else
    # Prefer our journal JSON changes; regenerate index from ours on conflict
    git checkout --ours assets/journal_requirements/_index.json 2>/dev/null || true
    git add assets/journal_requirements/_index.json 2>/dev/null || true
    git commit --no-edit || true
  fi
  if git push origin HEAD:main; then
    echo "Push succeeded on attempt $attempt"
    exit 0
  fi
  echo "Push failed attempt $attempt, retrying..."
  sleep $((attempt * 5))
done

echo "Push failed after 3 attempts" >&2
exit 1
