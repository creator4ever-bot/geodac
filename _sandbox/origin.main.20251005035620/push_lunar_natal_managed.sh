#!/usr/bin/env bash
set -euo pipefail
exec 9>/tmp/geodac_lunar.lock; flock -n 9 || { echo "[lunar] locked, skip"; exit 0; }

source "$HOME/astroenv/bin/activate"
PY="$HOME/astroenv/bin/python"
CDIR="$HOME/astro"
LOG="$CDIR/logs/lunar_natal.log"
ST="$CDIR/.state"
TZ="${TZ:-Europe/Moscow}"
EPHE="/home/DAC/Zet9 GeoDAC/Swiss"
MIN_EVENTS="${MIN_EVENTS:-10}"

mkdir -p "$CDIR/logs" "$ST"
exec > >(tee -a "$LOG") 2>&1

FROM="$(date -d '-14 days' +%F)"
TO="$(date -d '+14 days' +%F)"
CAL="Astro — Lunar Natal (Managed)"
RAW="$CDIR/lunar_natal.json"
FIX="$CDIR/lunar_natal_for_ics.json"
MERGED="${MERGED:-$CDIR/lunar_natal_merged.json}"

echo "[$(date '+%F %T')] lunar start FROM=$FROM TO=$TO CAL=$CAL"

# Бэкап
$PY - << 'PY'
import os,json,datetime as dt
from google.oauth2.credentials import Credentials; from googleapiclient.discovery import build
  # Lunar angles post-fixes (finalize just before push)
creds=Credentials.from_authorized_user_file(os.path.expanduser('~/astro/.gcal/token.json'),['https://www.googleapis.com/auth/calendar'])
svc=build('calendar','v3',credentials=creds); name="Astro — Lunar Natal (Managed)"
cal=next((it for it in svc.calendarList().list().execute().get('items',[]) if it['summary']==name),None)
if cal:
  now=dt.datetime.utcnow(); tmin=(now-dt.timedelta(days=14)).isoformat()+"Z"; tmax=(now+dt.timedelta(days=14)).isoformat()+"Z"
  ev=[]; page=None
  while True:
    r=svc.events().list(calendarId=cal['id'],timeMin=tmin,timeMax=tmax,singleEvents=True,orderBy='startTime',pageToken=page).execute()
    ev+=r.get('items',[]); page=r.get('nextPageToken')
    if not page: break
  dst=os.path.expanduser('~/astro/backups'); os.makedirs(dst,exist_ok=True)
  p=os.path.join(dst, f"Lunar_{dt.datetime.now().strftime('%Y%m%d-%H%M')}.json"); json.dump({'items':ev}, open(p,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
  print("[backup] saved:", p, "count:", len(ev))
else: print("[backup] calendar not found:", name)
PY

# Расчёт RAW
$PY "$CDIR/transits_slow.py" "$FROM" "$TO" --ephe "$EPHE" --bodies Moon,NNode > "$RAW"
echo "[calc] RAW written: $(wc -c < "$RAW") bytes"

# Рендер → FIX
$PY "$CDIR/render_for_ics.py" "$RAW" "$FIX"

# Guard + push (Rx/S не ставим для Луны)
CNT=$($PY -c 'import json,os; print(len(json.load(open(os.path.expanduser("~/astro/lunar_natal_for_ics.json"),encoding="utf-8"))["events"]))')
echo "[validate] events: $CNT"
  # Lunar angles post-fixes (fill houses.tr for angle events, ensure peak and "(из Hn)")
[ "$CNT" -lt "$MIN_EVENTS" ] && { echo "[abort] too few events ($CNT < $MIN_EVENTS)"; exit 3; }

$PY "$CDIR/lunar_merge_angles.py" "$FIX" "$CDIR/lunar_natal_merged.json"

$PY "$CDIR/push_gcal.py" --json "$MERGED" --tz "$TZ" --calendar "$CAL" --replace

date +%s > "$ST/lunar.last_ok"
echo "[$(date '+%F %T')] lunar done"
