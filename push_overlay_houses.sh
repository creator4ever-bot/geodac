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

echo "[$(date '+%F %T')] overlay houses using ingress + digest"

# 1) Сформируем forpush из overlay_ingresses.json (только ингрессии)
CDIR="$CDIR" "$PY" - <<'PY'
import json, os
cdir = os.environ['CDIR']
ing = os.path.join(cdir, 'overlay_ingresses.json')
out = os.path.join(cdir, 'overlay_houses_forpush.json')
with open(ing, encoding='utf-8') as f:
    data = json.load(f)
evs = data.get('events', data)
with open(out, 'w', encoding='utf-8') as f:
    json.dump({"events": evs}, f, ensure_ascii=False, indent=2)
print(f"[overlay] prepared from ingress: {len(evs)} -> {out}")
PY

# 2) Добавим сводку по домам (сегодня)
if [[ -f "$CDIR/overlay_houses_digest.py" ]]; then
  "$PY" "$CDIR/overlay_houses_digest.py"
else
  echo "[digest] overlay_houses_digest.py not found; skipping"
fi

# 3) Push в GCal
"$PY" "$CDIR/push_gcal.py" \
  --json "$CDIR/overlay_houses_forpush.json" \
  --tz "$TZ" --calendar "$CAL" --replace

date +%s > "$CDIR/.state/overlay_houses.last_ok"
echo "[$(date '+%F %T')] overlay houses done"
