GeoDAC — Самая Правильная Инструкция (кратко)

Контракт (чтобы чат не «чинил по-своему»)
- Никаких установок пакетов и правок путей без явного OK.
- Offline-first (.ics). API Google — только по запросу.
- Длинные логи/JSON — только ссылками. Ответы <= 1500 символов, при большем объеме — CHUNK 1/N и ждать "CONTINUE".
- Любое удаление/замена — только после подтверждения. Сначала TEST/dry-run, потом PROD.

Ритуал старта сессии
1) ops (или ops-start), затем: ops_note "start"
2) geodacctx  (быстрый контекст)
3) gdaudit    (диагностика; если diagnose_luna_vs_overlay ACC < 100% — ничего не пушим)
4) SAVE_JSONS — в конце сессии; SUMMARY_NOW — короткая сводка; session-close — отчёт + бэкапы

Overlay (только TEST -> PROD одним и тем же файлом)
1) overlay-build-pw
2) overlay-pw-compact -> ~/astro/overlay_houses_forpush.pw_compact.json
3) overlay-push-test
4) Визуальная проверка TEST
5) overlay-push-prod — тем же файлом, без пересборки между шагами

Mundane (публикация из бэкапа + толковки ингрессий)
1) mundane-normalize -> ~/astro/mundane_forpush.normalized.json
2) mundane-enrich    -> ~/astro/mundane_forpush.enriched.json
3) mundane-push-test / mundane-push-prod

Lunar (28 дней)
- Dry-run: LUNAR_DRY  (эквивалент with_markers LUNAR_DRY env PUSH=0 ...)
- PROD: lunar-push-prod
- Пайплайн: build -> merge -> dedup -> enrich -> push

Dreams
- dream-log "YYYY-MM-DD HH:MM" "YYYY-MM-DD HH:MM" "note"
- dream-log-last [минут] "note"  (по умолчанию 60)
- dreams-push-2d-test

Календарь и дубли (без API, оффлайн)
- Экспорт .ics из Google Calendar -> tools/ics_dedup_medium.py -> импорт в новый календарь "Medium (Clean)".
- PROD-токены ~/.gcal/{credentials.json, token.json}. Реавторизация — только вручную и по запросу.

Работа с чатом (чтобы не «умирал»)
- Использовать обычную вкладку браузера (не «как приложение»). Shields off.
- В DevTools заблокировать шум: surveys, posthog, /ingest/, /decide/, /collect.
- Перед длинным сообщением — короткий ping, дождаться ответа, потом кусками.
- Новый чат каждые 6–12 часов. Для старта: chatkit/canonical/05_seed_mini.txt.

Восстановление чата за 10 секунд
1) Открыть Desktop/GeoDAC_Самая_Правильная_Инструкция_v1.md (эта инструкция).
2) В новом чате вставить текст из chatkit/canonical/05_seed_mini.txt.
3) Ответить: AUTH = N (если не нужен), PIPELINE = TEST.
4) Дальше — работать по этой инструкции и шпаргалке 06_session_cheatsheet.md.

Полезные пути и файлы
- Репозиторий: ~/astro
- Логи: ~/astro/logs
- Инструменты: ~/astro/tools
- Натальная БД: ~/astro/.state/charts.db
- Индекс ZET: ~/astro/.state/zet_index.json
- GCAL токен/креды: ~/.gcal/{token.json,credentials.json}
- Обёртки: ~/bin (overlay-*, mundane-*, ops*, gdaudit, SAVE_JSONS, SUMMARY_NOW, LUNAR_DRY, dreams-*)
- Канон: ~/astro/chatkit/canonical (контракт, пути, runbook, паспорт, шпаргалки, seed)

Тревожные сигналы — стоп пуш
- diagnose_luna_vs_overlay ACC < 100%
- overlay_houses.log или medium.log с повторяющимися ошибками
- invalid_grant в любых GCal шагах (значит оффлайн или TEST без PUSH)
- В чате «вечный generating» — не реанимируем тред, создаем новый по seed

VENV: используем $HOME/astroenv (см. 02_paths.env). Если недоступен — фоллбек на системный python3.
