GeoDAC — Natal Transits Canon (v1)

1) Область и календари
- Medium: транзиты Sun..Mars к наталу.
- Long: Jupiter..Pluto к наталу.
- Lunar: отдельный конвейер, та же схема домов.
- Единый генератор/формат событий.

2) Время
- start/peak/end (UTC в данных; локаль — в UI).
- peak = точный аспект; точность до минут.

3) Координаты/дома
- ТОПО: транзиты и натал (USE_TOPO=1).
- Дома транзитов по натальной сетке (без dynamic cusps).
- Система: Topocentric (Polich-Page).

4) Цели/точки натала
- Планеты: Sun..Pluto; оси: ASC/MC/DSC/IC; узлы: Node/anti-Node (как пара).
- Доп. точки — только по явному включению.

5) Аспекты и орбы
- 0/60/90/120/180; ⚹ трактовать как sextile.
- Орбы (по умолчанию): Medium: 1.5 (быстрые), Sun: 1.0; Long: 1.0; Axis/Nodes: 1.5.

6) Компоновка (complex)
- MC/IC и ASC/DSC — объединять в одно событие.
- Узлы — как оппозиционная пара, объединять.
- Конфигурации: coalesce в окне T_coalesce (±6ч medium / ±24ч long).
- Домовой переход: фиксировать “Hn→Hm”.

7) Формат события (JSON)
- transit, target(s), aspect, aspect_deg, orb_peak_deg=0.0
- start/peak/end (ISO UTC)
- houses: {tr, nat?}; signs: {tr, nat?}
- style: medium|long|lunar
- id: детерминированный ключ (см. 8)

8) Ключ (deterministic id)
- id = sha1(f"{style}|{transit}|{sorted(targets)}|{aspect_deg}|{start_utc}|{end_utc}").

9) Summary/Description
- Summary: emoji + кратко, например “♂ □ ☉ (H8→H12)” или “♂ □ MC/IC (H9→H10)”.
- Description: проф. разбор аспекта/планет; Houses/Signs; метки start/peak/end; 1–3 рекомендации.

10) Календарные пары
- Astro — Medium/Long/Lunar (Managed). TEST/PROD — по calendars_map.md.

11) Выходы
- medium: transits_medium_for_ics.json (+ .ics по запросу)
- long: transits_long_for_ics.json; lunar — отдельный канал.
- Бэкапы: ~/astro/backups/session_YYYYMMDD_HHMM/

12) Ограничения
- Не использовать dynamic cusps на пике.
- Не смешивать geo/topo.
- Не раскалывать complex по осевым/узловым парам.
- Не менять id при одинаковых интервалах.

13) Параметры по умолчанию (env)
- USE_TOPO=1; STYLE=medium|long|lunar
- T_coalesce_h: 6 (medium) / 24 (long)
- ORB_MEDIUM_FAST=1.5; ORB_MEDIUM_SUN=1.0; ORB_LONG=1.0; ORB_AXIS=1.5

Примечание об изменениях
- Файл редактируемый: дополняйте/корректируйте по мере расширения функционала (v1 → v2 и т.д.).

14) QA-проверки (обязательны перед push)
- Format gate (newstyle): emoji в summary; «Профессиональный разбор» в description; без дублей; без хвостов ID.
- Angle-coverage (офлайн): для каждого target×aspect в окне считаем minΔ(Луна−target−aspect); если minΔ ≤ орб — событие обязано быть в forpush.json; иначе FAIL.
- Только при PASS обоих гейтов допускается replace в PROD (ID-only).
