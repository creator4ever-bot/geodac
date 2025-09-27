#!/usr/bin/env bash
set -euo pipefail
exec 9>/tmp/geodac_medium.lock; flock -n 9 || { echo "[medium] locked, skip"; exit 0; }

source "$HOME/astroenv/bin/activate"
PY="$HOME/astroenv/bin/python"
CDIR="$HOME/astro"
LOG="$CDIR/logs/medium.log"
ST="$CDIR/.state"
TZ="${TZ:-Europe/Moscow}"
CAL="Astro — Medium (Managed)"
MIN_EVENTS="${MIN_EVENTS:-40}"
EPHE="/home/DAC/Zet9 GeoDAC/Swiss"
USE_TOPO="${USE_TOPO:-1}"
NATAL_STATE_DIR="${NATAL_STATE_DIR:-$ST}"

mkdir -p "$CDIR/logs" "$ST"
exec > >(tee -a "$LOG") 2>&1

FROM="$(date -d '-30 days' +%F)"
TO="$(date -d '+30 days' +%F)"
echo "[$(date '+%F %T')] medium FROM=$FROM TO=$TO CAL=$CAL"

RAW="$CDIR/transits_medium.json"
FIX="$CDIR/transits_medium_for_ics.json"

# расчёт только Sun..Mars
USE_TOPO="$USE_TOPO" NATAL_STATE_DIR="$NATAL_STATE_DIR" \
"$PY" "$CDIR/transits_slow.py" "$FROM" "$TO" --ephe "$EPHE" --bodies "Sun,Mercury,Venus,Mars"

# guard

# post-calc filter: оставляем только Sun..Mars
"$PY" - <<"PY"
import os,json
CD=os.path.expanduser("~/astro")
p=os.path.join(CD, "transits_medium.json")
d=json.load(open(p,encoding="utf-8"))
ev=d.get("events", d)
keep=("Sun","Mercury","Venus","Mars")
flt=[e for e in ev if str(e.get("transit","")) in keep]
out={"meta": d.get("meta",{}), "events": flt} if isinstance(d,dict) else {"events": flt}
json.dump(out, open(p,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"[filter] medium Sun..Mars: {len(flt)} events")
PY

[[ ! -s "$RAW" ]] && { echo "[error] RAW is empty or missing: $RAW — abort"; exit 4; }

# рендер
[ -f "$HOME/astro/tools/houses_tr_start_fix.py" ] && "$PY" "$HOME/astro/tools/houses_tr_start_fix.py" "$FIX" || echo "[houses-tr-fix] skip (missing)"
[ -f "$HOME/astro/tools/axis_unify_postfix.py" ] && "$PY" "$HOME/astro/tools/axis_unify_postfix.py" "$FIX" || echo "[axis-unify] skip (missing)"
"$PY" "$CDIR/render_for_ics.py" "$RAW" "$FIX"

# валидация
CNT=$("$PY" -c 'import json,os; d=json.load(open(os.path.expanduser("~/astro/transits_medium_for_ics.json"),encoding="utf-8")); ev=d.get("events",d); print(len(ev))')
echo "[validate] events: $CNT"
[ "$CNT" -lt "$MIN_EVENTS" ] && { echo "[abort] few events"; exit 3; }

# пуш (по умолчанию включён, можно временно PUSH=0)
if [[ "${PUSH:-1}" != "1" ]]; then
  echo "[gcal] skip push (PUSH=${PUSH:-0})"
  echo "[$(date '+%F %T')] medium done"; exit 0
fi

"$PY" "$CDIR/push_gcal.py" --json "$FIX" --tz "$TZ" --calendar "$CAL" --replace
echo "[$(date '+%F %T')] medium done"
