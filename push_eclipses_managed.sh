#!/usr/bin/env bash
set -euo pipefail

# lock
exec 9>/tmp/geodac_eclipses.lock; flock -n 9 || { echo "[eclipses] locked, skip"; exit 0; }

# env
source "$HOME/astroenv/bin/activate"
PY="$HOME/astroenv/bin/python"
CDIR="$HOME/astro"
LOG="$CDIR/logs/eclipses.log"
ST="$CDIR/.state"
TZ="${TZ:-Europe/Moscow}"
CAL="GeoDAC • Eclipses"

mkdir -p "$CDIR/logs" "$ST"
exec > >(tee -a "$LOG") 2>&1

FROM="$(date -d '-200 days' +%F)"
TO="$(date -d '+400 days' +%F)"
echo "[$(date '+%F %T')] eclipses FROM=$FROM TO=$TO CAL=$CAL"

# 1) Выбираем источник (предпочтение — composed)
SRC=""
[[ -f "$CDIR/eclipse_triggers_forpush.composed.json" ]] && SRC="$CDIR/eclipse_triggers_forpush.composed.json"
[[ -z "$SRC" && -f "$CDIR/eclipse_triggers_forpush.json" ]] && SRC="$CDIR/eclipse_triggers_forpush.json"
[[ -z "$SRC" && -f "$CDIR/eclipse_triggers_window.json" ]] && SRC="$CDIR/eclipse_triggers_window.json"

if [[ -z "$SRC" ]]; then
  echo "[eclipses] no triggers JSON found -> abort"
  exit 4
fi

# 2) Валидация и подсчёт (аргумент надо передать ДО heredoc)
CNT=$("$PY" - "$SRC" <<'PY'
import json,sys
p=sys.argv[1]
with open(p,encoding='utf-8') as f:
    d=json.load(f)
ev=d.get('events', d)
print(len(ev) if isinstance(ev,list) else 0)
PY
)
echo "OK triggers: $CNT -> $SRC"

# 3) Push в GCal
"$PY" "$CDIR/push_gcal.py" --json "$SRC" --tz "$TZ" --calendar "$CAL" --replace

date +%s > "$ST/eclipses.last_ok"
echo "[$(date '+%F %T')] eclipses done"
