#!/usr/bin/env bash
set -Eeuo pipefail
STATE="$HOME/astro/.state"; mkdir -p "$STATE"
LAST="$STATE/dreams_test.last_ok"
# если не обновлялись > 6 часов — догоним
now=$(date +%s); last=$( [ -f "$LAST" ] && cat "$LAST" || echo 0)
if [ $(( now - last )) -gt $((6*3600)) ]; then
  CAL="${CAL:-GeoDAC • Dreams (TEST)}" bash -lc "$HOME/astro/scripts/dreams_update_test.sh >> $HOME/astro/logs/dreams.log 2>&1" || true
else
  echo "[dreams] catchup: fresh enough ($(date -d @$last -Is))"
fi
