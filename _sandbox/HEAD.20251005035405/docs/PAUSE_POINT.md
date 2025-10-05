# GeoDAC — PAUSE POINT (2025-09-18)

Статус:
- ACC (diagnose_luna_vs_overlay): 100%
- Overlay Houses: ok (ingress + digest), cron ok
- Lunar Natal: ok (merge + postfix[stub] + rehouse), gcal upsert ok
- Eclipses: ok (push_eclipses_managed.sh добавлен), gcal upsert ok

Что сделано сегодня:
- push_overlay_houses.sh: починена синтаксическая ошибка; tee/лог; Python env; formed forpush + digest
- overlay_houses_digest.py: перезаписан, безопасные отступы, optional yaml
- push_lunar_natal_managed.sh: добавлены вызовы lunar_angles_postfix.py и lunar_angles_rehouse.py (astroenv)
- lunar_angles_postfix.py: добавлен безопасный стаб
- render_for_ics.py: устранён KeyError по description (setdefault + get)
- push_eclipses_managed.sh: создан корректный скрипт (heredoc argv, replace-пуш)
- scripts/geodac_healthcheck.sh: добавлен

Резюме-скрипт запуска:
1) ops
2) geodacctx  (если ACC < 100% — ничего не пушим)
3) scripts/geodac_healthcheck.sh
4) Готовые пуши (когда зелёное):
   - Lunar Natal: MIN_EVENTS=10 ~/astro/push_lunar_natal_managed.sh
   - Eclipses: ~/astro/push_eclipses_managed.sh
   - Overlay Houses: ~/astro/push_overlay_houses.sh
   - Mundane: MIN_EVENTS=100 ORB=2 STEP_H=12 ~/astro/push_mundane_managed.sh
   - Medium/Long: MIN_EVENTS=40 ~/astro/push_medium_managed.sh; MIN_EVENTS=10 ~/astro/push_long_managed.sh

Следующие улучшения (не делали сегодня):
- Реализовать реальную логику lunar_angles_postfix.py (вместо стаба)
- Малые утилиты: view_last_* для чтения только последнего прогона из логов
