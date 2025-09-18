#!/usr/bin/env bash
set -euo pipefail
echo "=== GeoDAC Quick Context $(date -Is) ==="
echo "User: $USER  Host: $(hostname)"
echo "Origin (clean repo): $(cat "$HOME/astro/.state/remote.origin.url" 2>/dev/null || echo 'not set')"
echo "TZ: ${TZ:-$(cat /etc/timezone 2>/dev/null || echo '-')}"
echo
cd "$HOME/astro" || exit 0
echo "— git HEAD (last 3) —"
git --no-pager log -3 --oneline --decorate --stat || true
echo
echo "— state freshness (.last_ok) —"
for f in "$HOME/astro/.state/"*.last_ok; do
  [ -f "$f" ] && { ts=$(cat "$f"); when=$(date -d @"$ts" 2>/dev/null || echo "$ts"); echo "$(basename "$f") = $when"; }
done
echo
echo "— lunar invariants —"
grep -n 'normalize_cusps_to_asc' "$HOME/astro/transits_slow.py" || echo "OK: no normalize_cusps_to_asc"
grep -nE 'cusps_peak|housesKATEX_INLINE_OPENjd_peak' "$HOME/astro/transits_slow.py" || echo "OK: no dynamic cusps on peak"
grep -n 'lunar_angles_.*\.py' "$HOME/astro/push_lunar_natal_managed.sh" || echo "WARN: no lunar_angles_* post-fixes in push script"
echo
echo "— python (astroenv) —"
/home/DAC/astroenv/bin/python -V || true
echo "— diagnose lunar vs overlay —"
/home/DAC/astroenv/bin/python "$HOME/astro/diagnose_luna_vs_overlay.py" || true
echo
echo "— logs (tails) —"
for log in mundane medium long lunar_natal eclipses overlay_houses; do
  p="$HOME/astro/logs/${log}.log"; [ -f "$p" ] && { echo "[${log}.log]"; tail -n 40 "$p"; echo; }
done
echo "— cron —"
crontab -l | grep -E 'push_eclipses|push_overlay_houses' || echo "Cron: eclipses/overlay entries not found"
echo "=== end of context ==="
