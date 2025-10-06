#!/bin/sh
set -eu
A="$HOME/astro"; PY="/home/DAC/astroenv/bin/python"; LOG="$A/logs"
mkdir -p "$LOG"
# 1) Пересчёт оффлайн (не трогаем HOME, токены не нужны)
NO_API=1 PUSH=0 DRY=1 "$HOME/bin/LUNAR_DRY" >/dev/null 2>&1 || true
# 2) Конвертер JSON -> ICS с окном ±14 дней и клэмпом по орбису
OUT="$LOG/lunar_14d.$(date +%Y%m%d%H%M%S).ics"
"$PY" "$A/scripts/lunar_json_to_ics.py" "$A/lunar_natal_for_ics.json" "$OUT" 14
echo "ICS=$OUT"
grep -c '^BEGIN:VEVENT' "$OUT" | awk '{print "VEVENTS="$1}'
