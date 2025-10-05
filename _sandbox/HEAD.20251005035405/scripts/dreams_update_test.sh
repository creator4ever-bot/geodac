#!/usr/bin/env bash
set -Eeuo pipefail
exec 9>"$HOME/astro/.state/dreams.lock"; flock -n 9 || { echo "[dreams] locked, skip"; exit 0; }

CAL="${CAL:-GeoDAC • Dreams (TEST)}"
PY="$HOME/astroenv/bin/python"
LOG="$HOME/astro/tools/dreams_log.py"
STATE="$HOME/astro/.state"
mkdir -p "$STATE" "$HOME/astro/logs"

# сеть (до 15 попыток)
for i in {1..15}; do
  "$PY" - <<PY >/dev/null 2>&1 && break || sleep 4
import socket; socket.gethostbyname("www.googleapis.com")
PY
done

# окна (-1, 0, +1 сутки; два окна в день)
for o in -1 0 1; do
  D=$(date -d "$o day" +%F)
  "$PY" "$LOG" --start "$D 00:00" --end "$D 11:59" --note "auto: 00–12" --cal "$CAL" || true
  "$PY" "$LOG" --start "$D 12:00" --end "$D 23:59" --note "auto: 12–24" --cal "$CAL" || true
done

date +%s > "$STATE/dreams_test.last_ok"
echo "[dreams] update test OK @ $(date -Is)"
