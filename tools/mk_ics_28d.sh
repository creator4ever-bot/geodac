#!/bin/sh
set -eu
A="$HOME/astro"; LOG="$A/logs"; PY="/home/DAC/astroenv/bin/python"
mkdir -p "$LOG" "$A/_offline_home"
nog(){ HOME="$A/_offline_home" NO_API=1 PUSH=0 DRY=1 "$@"; }
SRC="${1:-}"; TMP="$LOG/tmp_src.$(date +%Y%m%d%H%M%S).ics"; OUT="$LOG/clean_28d.$(date +%Y%m%d%H%M%S).ics"
if [ -z "$SRC" ]; then
  P="$A/scripts/render_for_ics.py"; [ -f "$P" ] || P="$A/render_for_ics.py"
  nog "$HOME/bin/overlay-build-pw"   >>"$LOG/overlay_build.log" 2>&1 || true
  nog "$HOME/bin/overlay-pw-compact" >>"$LOG/overlay_compact.log" 2>&1 || true
  "$PY" "$P" "$A/overlay_houses_forpush.pw_compact.json" > "$TMP"
else
  cp -f -- "$SRC" "$TMP"
fi
"$PY" "$A/scripts/ics_window_clamp.py" "$TMP" "$OUT" 28
echo "ICS=$OUT"
grep -c '^BEGIN:VEVENT' "$OUT" | awk '{print "VEVENTS="$1}'
