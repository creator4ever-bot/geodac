# GeoDAC session — Stations naming + UI-склейка + публикация

Дата/время: 2025-09-15T06:45:44+03:00
Окно: PAST=200, FUTURE=200, TZ=Europe/Moscow

Что сделано
- Переименование станций: «остановка и разворот назад/вперёд».
- Стык S↓→℞: «остановка и разворот назад» заканчивается ровно в момент старта ретрофазы (стык по станции).
- S↑: «остановка и разворот вперёд» — единое событие (без отдельного «директный») с ремаркой «далее — планета работает в штатном режиме».
- UI-склейка (флаг STATION_UI_COLLAPSE_DAY=1): стационар назад обрезается до локальной полуночи дня разворота (в месячном виде в день S↓ остаётся одна «полоса» — ретро).
- push_gcal: исправлен формат дат, добавлен прогресс-лог, введён gd_hash (skip неизменившихся), режим upsert-only.

Проверки и публикации
- station enhance: stitched=10, collapsed=7 (на текущем окне).
- Тест-календарь “Astro — Mundane v2 (Managed)”: Upsert done: inserted=47, updated=312, skipped=0; Replace deleted=96.
- Основной “Astro — Mundane (Managed)” (с UI-склейкой): Upsert done: inserted=20, updated=0, skipped=339; Replace deleted=20.

Коммиты
- 7c1ef1d mundane: станции → «остановка и разворот …»; SB→RX стык; UI-склейка SB до полуночи дня разворота (флаг STATION_UI_COLLAPSE_DAY) (2025-09-15)
- 2f5e3e2 push_gcal: прогресс-лог, контент-хеш gd_hash (skip неизменившихся), устойчивый парсинг дат (2025-09-15)
- 7fe5a34 mundane: stitch SB→RX (встык); S↑: ремарка «…работает в штатном режиме»; скрыт «директный»; dedup/сортировка сохранены (2025-09-15)

Next
- Eclipses: вынести триггеры в отдельный Managed-календарь “GeoDAC • Eclipses” (параметры orb_deg/fresh_days из конфига), завести крон при необходимости.
- Далее по плану: packs (composer.active_pack, тона/домены), UI-стабилизация отдельной сессией.

Коммиты (факт):
- 7c1ef1d mundane: станции → «остановка и разворот …»; SB→RX стык; UI-склейка SB до полуночи дня разворота (флаг STATION_UI_COLLAPSE_DAY) (2025-09-15)
- 2f5e3e2 push_gcal: прогресс-лог, контент-хеш gd_hash (skip неизменившихся), устойчивый парсинг дат (2025-09-15)
- 7fe5a34 mundane: stitch SB→RX (встык); S↑: ремарка «…работает в штатном режиме»; скрыт «директный»; dedup/сортировка сохранены (2025-09-15)
- 42b2b57 UI: dark toggle + no auto-open; Brave shortcuts (dark content, proxy support); start wrapper (2025-09-14)
- c6dd302 UI: ZET DBase recursive toggle; Brave .desktop shortcuts; stabilize UI files (2025-09-14)