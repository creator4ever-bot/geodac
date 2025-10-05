#!/bin/sh
set -eu
A="$HOME/astro"; cd "$A" || exit 1
DIFF="${1:?usage: ai_patch.sh <patch.diff>}"
TS=$(date +%Y%m%d%H%M%S)
PREV=$(git symbolic-ref --short -q HEAD || echo main)
BR="ai/sandbox-$TS"; LOG="$A/logs/ai_patch.$TS.log"; ICS="$A/logs/ai_patch.$TS.ics"
ATT="$A/chatkit/attic/ai_patch.$TS"
nog(){ HOME="$A/_offline_home" NO_API=1 PUSH=0 DRY=1 "$@"; }

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "Not a git repo"; exit 2; }
git switch -c "$BR" >/dev/null 2>&1 || git checkout -b "$BR" >/dev/null 2>&1 || true

# Цели патча (без sed/\\1)
TARGETS=$(awk '/^\+\+\+ b\//{sub(/^\+\+\+ b\//,""); print}' "$DIFF")

# Автопарковка существующих неотслеживаемых файлов
mkdir -p "$ATT"
echo "$TARGETS" | while IFS= read -r f; do
  [ -n "$f" ] || continue
  if [ -e "$f" ] && ! git ls-files --error-unmatch -- "$f" >/dev/null 2>&1; then
    mkdir -p "$ATT/$(dirname "$f")"
    mv -- "$f" "$ATT/$f.$TS.bak"
  fi
done

# Проверка/применение
if ! git apply --check -v -- "$DIFF" >"$LOG" 2>&1; then
  echo "CHECK FAILED"; tail -n 60 "$LOG"
  git switch "$PREV" >/dev/null 2>&1 || true; git branch -D "$BR" >/dev/null 2>&1 || true
  exit 3
fi
git apply -- "$DIFF"

# Doc-only? (docs/, chatkit/canonical/, README/LICENSE, *.md)
DOCONLY=1
for f in $TARGETS; do
  case "$f" in docs/*|chatkit/canonical/*|README*|LICENSE*|*.md) : ;; *) DOCONLY=0; break;; esac
done
if [ "$DOCONLY" = 1 ]; then
  git add -A; git commit -m "AI doc patch $TS" >/dev/null 2>&1 || true
  echo "APPLIED DOC-ONLY branch=$BR commit=$(git rev-parse --short HEAD)"; exit 0
fi

# Кодовые патчи — оффлайн прогон
nog "$HOME/bin/overlay-build-pw"   >>"$LOG" 2>&1 || true
nog "$HOME/bin/overlay-pw-compact" >>"$LOG" 2>&1 || true
PY="/home/DAC/astroenv/bin/python"
for P in "$A/scripts/render_for_ics.py" "$A/render_for_ics.py"; do
  [ -f "$P" ] && "$PY" "$P" "$A/overlay_houses_forpush.pw_compact.json" > "$ICS" 2>>"$LOG" || true
done
EV=0; [ -s "$ICS" ] && EV=$(awk '/^BEGIN:VEVENT/{c++} END{print c+0}' "$ICS")
echo "LOG=$LOG ICS=$ICS EVENTS=$EV"
if [ "$EV" -gt 0 ]; then
  git add -A; git commit -m "AI patch $TS (events=$EV)" >/dev/null 2>&1 || true
  echo "APPLIED OK branch=$BR commit=$(git rev-parse --short HEAD)"
else
  git reset --hard >/dev/null 2>&1 || true
  git switch "$PREV" >/dev/null 2>&1 || true
  git branch -D "$BR" >/dev/null 2>&1 || true
  echo "REJECTED (no events). See $LOG"; exit 1
fi
