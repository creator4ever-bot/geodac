#!/usr/bin/env bash
set -Eeuo pipefail
AST="$HOME/astro"

echo "=== GeoDAC Quick Context $(date -Is) ==="
echo "User: $(whoami)  Host: $(hostname)"
echo "Repo: $AST"
echo "TZ: ${TZ:-$(cat /etc/timezone 2>/dev/null || echo "-")}"

echo; echo "— git HEAD (last 3) —"
git -C "$AST" --no-pager log --oneline --decorate -n 3 2>/dev/null || true

echo; echo "— state freshness (.last_ok) —"
for f in "$AST"/.state/*.last_ok; do [ -f "$f" ] && echo "$(basename "$f") = $(date -d @$(cat "$f") 2>/dev/null)"; done

echo; echo "— logs (tails) —"
for n in mundane medium long lunar_natal eclipses overlay_houses; do
  echo "[$n.log]"; tail -n 40 "$AST/logs/$n.log" 2>/dev/null || true; echo
done
echo "=== end of context ==="
