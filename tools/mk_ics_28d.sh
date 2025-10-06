#!/bin/sh
set -eu
A="$HOME/astro"; LOG="$A/logs"; PY="/home/DAC/astroenv/bin/python"
mkdir -p "$LOG"
nog(){ NO_API=1 PUSH=0 DRY=1 "$@"; }
P="$A/scripts/render_for_ics.py"; [ -f "$P" ] || P="$A/render_for_ics.py"
nog "$HOME/bin/overlay-build-pw"   >/dev/null 2>&1 || true
nog "$HOME/bin/overlay-pw-compact" >/dev/null 2>&1 || true
RAW="$LOG/raw.$(date +%Y%m%d%H%M%S).ics"; OUT="$LOG/clean_28d.$(date +%Y%m%d%H%M%S).ics"
"$PY" "$P" "$A/overlay_houses_forpush.pw_compact.json" > "$RAW"
"$PY" "$A/scripts/ics_window_clamp.py" "$RAW" "$OUT" 28
echo "ICS=$OUT"; grep -c '^BEGIN:VEVENT' "$OUT" | awk '{print "VEVENTS="$1}'
