#!/usr/bin/env bash
set -euo pipefail

# lock
exec 9>/tmp/geodac_overlay_houses.lock; flock -n 9 || { echo "[overlay] locked, skip"; exit 0; }

# env
[ -f "$HOME/astroenv/bin/activate" ] && source "$HOME/astroenv/bin/activate" || true
PY="${PY:-$HOME/astroenv/bin/python}"
command -v "$PY" >/dev/null 2>&1 || PY="$(command -v python3 || true)"

CDIR="$HOME/astro"
LOG="$CDIR/logs/overlay_houses.log"
ST="$CDIR/.state"
TZ="${TZ:-Europe/Moscow}"
CAL="${CAL:-Astro — Overlay Houses (Managed)}"

mkdir -p "$CDIR/logs" "$ST"
exec > >(tee -a "$LOG") 2>&1

echo "[$(date '+%F %T')] overlay start CAL=$CAL TZ=$TZ"

# choose source
SRC=""
for p in \
  "$CDIR/overlay_houses_forpush.pw_compact.json" \
  "$CDIR/overlay_houses_forpush.pw.json" \
  "$CDIR/overlay_houses_forpush.json" \
  "$CDIR/overlay_houses_forpush.normalized.json" \
  "$CDIR/overlay_houses_forpush.di.json"
do
  [ -f "$p" ] && SRC="$p" && break
done

if [ -z "$SRC" ]; then
  echo "[overlay] no overlay_houses_forpush*.json found -> abort"
  exit 4
fi

# count events
CNT=$("$PY" - "$SRC" <<'PY'
import json, sys
p=sys.argv[1]
with open(p, encoding='utf-8') as f:
    d=json.load(f)
ev=d.get('events', d) if isinstance(d, dict) else (d if isinstance(d, list) else [])
print(len(ev) if isinstance(ev, list) else 0)
PY
)
echo "OK overlay events: $CNT -> $SRC"

# respect PUSH
if [ "${PUSH:-1}" != "1" ]; then
  echo "[gcal] skip push (PUSH=0)"
  exit 0
fi

# optional re-auth
if [ "${AUTH:-0}" = "1" ]; then
  echo "[gcal] AUTH=1 -> removing token to re-auth"
  rm -f "$HOME/.gcal/token.json" "$CDIR/.gcal/token.json" 2>/dev/null || true
fi

# push
[ -n "$PY" ] || { echo "[overlay] no python runtime"; exit 5; }
"$PY" "$CDIR/push_gcal.py" --json "$SRC" --tz "$TZ" --calendar "$CAL" --replace

date +%s > "$ST/overlay_houses.last_ok"
echo "[$(date '+%F %T')] overlay done"
