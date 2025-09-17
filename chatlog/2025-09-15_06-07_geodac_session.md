# GeoDAC session — Stations + GCal upsert (hash+progress)

Дата/время: $(date -Is)
Окно: PAST=200, FUTURE=200, TZ=Europe/Moscow

Сделано:
- Станции: «разворот назад» → «ретроградный» — встык, без наложений.
- «Разворот вперёд»: одно событие (℞→D) с ремаркой «…далее — планета работает в штатном режиме».
- GCal push: починен формат дат; добавлен прогресс‑лог.
- Upsert only changes: gd_hash → неизменившиеся пропускаются (skip).

Проверки:
- SB→RX delta: 0 сек (логика верная; источники местами дают локальное время для RX).
- S↑: ремарка добавлена (mundane_fill_post_desc.py).
- Пуш в GCal: Upsert done, Replace OK.

Commits:
- mundane_station_enhance.py — stitch SB→RX
- mundane_fill_post_desc.py — ремарка для S↑
- push_gcal.py — прогресс, gd_hash, устойчивый парсинг дат

Next:
- Eclipses: вынести триггеры в отдельный Managed‑календарь “GeoDAC • Eclipses”, orb_deg/fresh_days из конфига.
- (Опционально) Packs composer: активный pack и тона.
