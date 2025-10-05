[GeoDAC/Continue/part3]
Режим: проф. астролог; линейно; окружение не восстанавливать; правки точечные; валидность > формальная ровность.

Старт каждой сессии:
- ops; geodacctx; если ACC<100% — не пушить.

Инварианты:
- Lunar по натальной сетке (без dynamic cusps на пике).
- transits_slow.py: нет normalize_cusps_to_asc; нет cusps_peak/houses(jd_peak).
- push_lunar_natal_managed.sh вызывает:
  /home/DAC/astroenv/bin/python ~/astro/lunar_angles_postfix.py
  /home/DAC/astroenv/bin/python ~/astro/lunar_angles_rehouse.py
- Swisseph-скрипты запускать через /home/DAC/astroenv/bin/python.

Что присылать ассистенту:
- geodacctx (~200 строк).
- При ACC<100% — MISM из diagnose + 1–2 события из lunar_natal_for_ics.json.

Готовые ручные пуски:
- lunar_natal/eclipses/overlay_houses/mundane/medium/long (см. part2).
