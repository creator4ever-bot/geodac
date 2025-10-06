#!/bin/sh
set -eu
A="$HOME/astro"; PY="/home/DAC/astroenv/bin/python"; LOG="$A/logs"; mkdir -p "$LOG"
# whitelist: Sun..Pluto + ASC/MC/DSC/IC
OUTY="$LOG/natal.pa.$(date +%Y%m%d%H%M%S).yaml"
$PY - <<'PY' > "$OUTY"
import os,yaml
allow=set("Sun Mercury Venus Mars Jupiter Saturn Uranus Neptune Pluto ASC MC DSC IC".split())
y=yaml.safe_load(open(os.path.expanduser('~/astro/config/natal_positions.yaml')))
print(yaml.safe_dump({k:v for k,v in y.items() if k in allow}, allow_unicode=True, sort_keys=True))
PY
NO_API=1 PUSH=0 DRY=1 "$HOME/bin/LUNAR_DRY" >/dev/null 2>&1 || true
"$PY" "$A/scripts/lunar_refine_peaks.py" "$A/lunar_natal_for_ics.json" "$OUTY" "$A/config/orbs_moon.yaml" >>"$LOG/lunar_refine.log" 2>&1 || true
SRC="$A/lunar_natal_for_ics.refined.json"
ICS="$LOG/lunar_14d.pa.$(date +%Y%m%d%H%M%S).ics"
"$PY" "$A/scripts/lunar_json_to_ics.py" "$SRC" "$ICS" 14
echo "ICS=$ICS"; grep -c '^BEGIN:VEVENT' "$ICS" | awk '{print "VEVENTS="$1}'
