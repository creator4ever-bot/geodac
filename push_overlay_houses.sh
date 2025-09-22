#!/usr/bin/env bash
set -euo pipefail

# lock to prevent concurrency
exec 9>/tmp/geodac_overlay.lock; flock -n 9 || { echo "[overlay] locked, skip"; exit 0; }

# activate env
source "$HOME/astroenv/bin/activate"
PY="$HOME/astroenv/bin/python"
CDIR="$HOME/astro"
LOG="$CDIR/logs/overlay_houses.log"; mkdir -p "$CDIR/logs" "$CDIR/.state"

# safe tee: если есть bash — дублируем в лог, иначе просто в лог
if [[ -n ${BASH_VERSION:-} ]]; then
  exec > >(tee -a "$LOG") 2>&1
else
  exec >> "$LOG" 2>&1
fi

TZ="${TZ:-Europe/Moscow}"
CAL="GeoDAC • Overlay Houses"

# снимок окружения в лог
env

echo "[$(date '+%F %T')] overlay houses build timeline"
"$HOME/astro/tools/overlay_houses_timeline.py"

# Если пушить нельзя — выходим после сборки
if [[ "${PUSH:-0}" != "1" ]]; then
  echo "[gcal] skip push (PUSH=${PUSH:-0})"
  date +%s > "$CDIR/.state/overlay_houses.last_ok"
  echo "[$(date '+%F %T')] overlay houses done"
  exit 0
fi

# Пуш в календарь (замена)
"$PY" "$CDIR/push_gcal.py" \
  --json "$CDIR/overlay_houses_forpush.json" \
  --tz "$TZ" --calendar "$CAL" --replace
date +%s > "$CDIR/.state/overlay_houses.last_ok"
echo "[$(date '+%F %T')] overlay houses done"
