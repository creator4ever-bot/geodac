#!/usr/bin/env bash
set -euo pipefail
CLEAN="$HOME/geodac_public_clean"
ORIGIN_URL="${1:-$(cat "$HOME/astro/.state/remote.origin.url" 2>/dev/null || echo 'https://github.com/creator4ever-bot/geodac.git')}"

mkdir -p "$CLEAN"
rsync -a --delete \
  --exclude='.git' \
  --exclude='.gcal' --exclude='.state' \
  --exclude='logs'  --exclude='backups' --exclude='chatlog' \
  --exclude='__pycache__' --exclude='*.pyc' --exclude='*.pyo' --exclude='*.pyd' \
  --exclude='*.bak.*' \
  --exclude='lunar_*.json' --exclude='transits_*.json' --exclude='overlay_*.json' \
  --exclude='overlay_ingresses.json' --exclude='overlay_spans.json' --exclude='overlay_houses_forpush.json' \
  --exclude='eclipse_triggers_window.json' --exclude='eclipse_triggers_forpush.json' --exclude='eclipse_triggers_forpush.composed.json' \
  "$HOME/astro/" "$CLEAN/"

# .gitignore в чистой копии (на всякий)
cat > "$CLEAN/.gitignore" <<'EOF'
.gcal/
.state/
logs/
backups/
chatlog/
__pycache__/
*.pyc
*.pyo
*.pyd
*.bak.*
lunar_*.json
transits_*.json
overlay_*.json
overlay_ingresses.json
overlay_spans.json
overlay_houses_forpush.json
eclipse_triggers_window.json
eclipse_triggers_forpush.json
eclipse_triggers_forpush.composed.json
EOF

cd "$CLEAN"
if [ ! -d .git ]; then
  git init -b main
  git remote add origin "$ORIGIN_URL"
fi

git add -A
if git diff --cached --quiet; then
  echo "[publish] no changes"
else
  msg="publish: $(date -Is) sync from ~/astro"
  git commit -m "$msg"
  git push -u origin main
  echo "[publish] pushed main"
fi
