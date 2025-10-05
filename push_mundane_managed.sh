#!/usr/bin/env bash
set -euo pipefail
exec 9>/tmp/geodac_mundane.lock; flock -n 9 || { echo "[mundane] locked, skip"; exit 0; }
source "$HOME/astroenv/bin/activate"

PY="$HOME/astroenv/bin/python"
CDIR="$HOME/astro"
LOG="$CDIR/logs/mundane.log"; mkdir -p "$CDIR/logs" "$CDIR/.state"
exec > >(tee -a "$LOG") 2>&1

TZ="${TZ:-Europe/Moscow}"
PAST="${PAST:-200}"; FUTURE="${FUTURE:-200}"
FROM="$(date -d "-$PAST days" +%F)"; TO="$(date -d "+$FUTURE days" +%F)"

CAL_OK="Astro — Mundane (Managed)"; CAL_TEST="Astro — Mundane v2 (Managed)"
TARGET="$CAL_OK"; DO_REPLACE=1  # основной по умолчанию
RAW="$CDIR/mundane_feed.raw.json"
FIX="$CDIR/mundane_feed.fixed.json"
GT="$CDIR/grand_trine_span.json"
MERGED="$CDIR/mundane_feed.merged.json"

MIN_EVENTS="${MIN_EVENTS:-100}"     # guard
GT_ORB="${ORB:-2}"                  # орбис тринов
GT_STEP="${STEP_H:-12}"             # шаг по времени (ч)
GT_TRI="${GT_TRI:-Jupiter,Saturn,Neptune; Jupiter,Saturn,Uranus; Saturn,Uranus,Neptune; Jupiter,Neptune,Pluto; Mars,Jupiter,Uranus}"

echo "[$(date '+%F %T')] mundane FROM=$FROM TO=$TO TARGET=$TARGET replace=$DO_REPLACE"

# 1) Бэкап (только если в основной)
if [ "$DO_REPLACE" -eq 1 ]; then
  $PY - << 'PY'
import os,json,datetime as dt
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
dst=os.path.expanduser('~/astro/backups'); os.makedirs(dst,exist_ok=True)
SCOPES=['https://www.googleapis.com/auth/calendar']
creds=Credentials.from_authorized_user_file(os.path.expanduser('~/astro/.gcal/token.json'),SCOPES)
svc=build('calendar','v3',credentials=creds); name="Astro — Mundane (Managed)"
cal=next((it for it in svc.calendarList().list().execute().get('items',[]) if it['summary']==name),None)
if cal:
  now=dt.datetime.utcnow(); tmin=(now-dt.timedelta(days=200)).isoformat()+"Z"; tmax=(now+dt.timedelta(days=200)).isoformat()+"Z"
  ev=[]; page=None
  while True:
    r=svc.events().list(calendarId=cal['id'],timeMin=tmin,timeMax=tmax,singleEvents=True,orderBy='startTime',pageToken=page).execute()
    ev+=r.get('items',[]); page=r.get('nextPageToken'); 
    if not page: break
  p=os.path.join(dst, f"Astro_Mundane_Managed_{dt.datetime.now().strftime('%Y%m%d-%H%M')}.json")
  json.dump({'items':ev}, open(p,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
  print("[backup] saved:", p, "count:", len(ev))
else:
  print("[backup] calendar not found:", name)
PY
fi

# 2) feed -> RAW
$PY "$CDIR/mundane_feed.py" "$FROM" "$TO" > "$RAW"
echo "[feed] RAW size: $(wc -c < "$RAW")"

# 3) postfix -> FIX (фазы/затмения/Лунная вода/станции)
TZ_NAME="$TZ" $PY "$CDIR/mundane_postfix.py" "$RAW" "$FIX"
$PY "$CDIR/mundane_station_enhance.py" "$FIX"
$PY "$CDIR/mundane_fill_post_desc.py" "$FIX"
FROM="$FROM" TO="$TO" "$CDIR/eclipse_triggers_for_window.sh"
ECL="$HOME/astro/eclipse_triggers_window.json"
$PY "$CDIR/merge_json_events.py" "$FIX" "$ECL" "$FIX"
$PY "$CDIR/mundane_station_enhance.py" "$FIX"
$PY "$CDIR/mundane_fill_post_desc.py" "$FIX"
echo "[postfix] FIX size: $(wc -c < "$FIX")"

# 4) GRAND_TRINE scan на окне (Swiss), может дать 0
ORB="$GT_ORB" STEP_H="$GT_STEP" $PY "$CDIR/mundane_grand_trine_scan.py" "$FROM" "$TO" "$GT" "$GT_TRI" || true

# 5) MERGE GT + FIX
$PY - << 'PY'
import json, os
fix=os.path.expanduser('~/astro/mundane_feed.fixed.json')
gt =os.path.expanduser('~/astro/grand_trine_span.json')
out=os.path.expanduser('~/astro/mundane_feed.merged.json')
def load(p):
    if not os.path.exists(p) or os.path.getsize(p)==0: return []
    d=json.load(open(p,encoding='utf-8')); 
    return d.get('events',[]) if isinstance(d,dict) else d
A=load(fix); B=load(gt)
uniq={}
for e in A+B:
    k=e.get('gd_id') or (e.get('summary',''), e.get('peak',''))
    uniq[k]=e
ev=sorted(uniq.values(), key=lambda x: x.get('peak') or x.get('start') or '')
json.dump({"events":ev}, open(out,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
print("[merge] FIX:", len(A), "GT:", len(B), "=> MERGED:", len(ev))
PY

# 6) Guard и push
CNT=$($PY -c 'import json,os; print(len(json.load(open(os.path.expanduser("~/astro/mundane_feed.merged.json"),encoding="utf-8"))["events"]))')
echo "[validate] MERGED events: $CNT"; [ "$CNT" -lt "$MIN_EVENTS" ] && { echo "[abort] few events ($CNT < $MIN_EVENTS)"; exit 3; }

$PY "$CDIR/push_gcal.py" --json "$MERGED" --tz "$TZ" --calendar "$TARGET" --replace

date +%s > "$CDIR/.state/mundane.last_ok"
echo "[$(date '+%F %T')] mundane done"
