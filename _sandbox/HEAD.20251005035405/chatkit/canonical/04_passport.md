Goal: medium/overlay/lunar/mundane -> GCal; light ops.
Repo: $HOME/astro; Logs: $HOME/astro/logs; Backups: $HOME/astro/backups
ZET index: $HOME/astro/.state/zet_index.json; Natal DB: $HOME/astro/.state/charts.db
Risks: platform TTL/spinner; avoid long dumps; API only on demand.
Active: verify overlay in TEST (dry-run); fix dupes offline if needed.

Desktop archive resumed: 2025-09-30T02:58:18+03:00
Folder: /home/DAC/Desktop/GeoDAC_Desk_Archive_20250930_0254

STATUS @ 2025-09-30T05:05:16+03:00
- Medium PROD по ID работает; переименование в UI частично (описание событий ещё содержит ID — отложено).
- overlay: ок; medium: ок (newstyle через апгрейдер). long/lunar: предстоит привести к «новому» стилю.

Runtime:
- scheduler: cron (systemd: OFF)
- auto_updates: paused (see crontab [PAUSE] entries)

STATUS — Lunar @ 2025-10-04T07:22:43+03:00
- LUNAR PROD updated: newstyle, 92 events, month window, QA PASS.
- CAL_LUNAR_ID recorded in 02_paths.env.
