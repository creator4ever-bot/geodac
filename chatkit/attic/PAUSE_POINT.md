GeoDAC — PAUSE POINT (2025-09-19)

Статус:
- Invariants:
  - Домификация: Topocentric (T) — ok
  - Планеты: топоцентрические (USE_TOPO=1) — ok
  - Дом транзитной планеты: по старту окна (houses_tr_ref=start) — ok (Medium/Long)
  - Лунные: Moon rehouse считает дом по натальной сетке; Moon ☍ Venus = «из H7 к H1» — ok
- Источники натала:
  - natal_frame.json синхронизирован с куспидами/осями — ok
  - поддержка NATAL_STATE_DIR — ok (можно переключать каталоги)
  - override (natal_override.json) поддерживается в transits_slow — готово (можно «прибить» долготы)
- Скрипты:
  - push_lunar_natal_managed.sh — ok (postfix stub + rehouse)
  - push_overlay_houses.sh — ok (digest+push)
  - push_eclipses_managed.sh — ok
  - push_medium_managed.sh — создан, с гвардом RAW — ok
- Исправления:
  - transits_slow.py: close_win переписан; set_topo глобально; main с печатью — ok
  - render_for_ics.py: защита от events=None — ok

Дальше:
1) Пересчитать Medium (см. push_medium...), проверить «☉ △ ♂ (из H7 к H12)».
2) По желанию: добавить natal_override.json с точными долготами/узлами (True/Mean), затем пересчитать.
3) Опционально: унифицировать Луну на «дом по старту окна» (сейчас середина окна) — обсудить.

Стартовые операции:
- ops
- geodacctx
- ~/astro/scripts/geodac_healthcheck.sh
