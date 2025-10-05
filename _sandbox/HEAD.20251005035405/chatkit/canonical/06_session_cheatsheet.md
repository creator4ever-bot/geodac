GeoDAC — Шпаргалка сессии (MX Linux, Geany, markers)

Старт (ничего не ломает)
- ops (или ops-start), затем: ops_note "start"
- geodacctx
- gdaudit
  Если ACC<100% в diagnose_luna_vs_overlay — ничего не пушим.

Overlay (только через TEST → затем PROD тем же файлом)
1) Сборка PW:
   overlay-build-pw
   → $HOME/astro/overlay_houses_forpush.pw.json
2) Day-compact (убрать день ингресса):
   overlay-pw-compact
   → $HOME/astro/overlay_houses_forpush.pw_compact.json
3) Push TEST:
   overlay-push-test
4) Визуальная проверка (TEST)
5) Push PROD (тем же файлом):
   overlay-push-prod

Mundane (публикация из бэкапа + толковки ингрессий)
1) Нормализовать бэкап в forpush:
   mundane-normalize                 # берёт последний *Mundane*.json из backups
   → $HOME/astro/mundane_forpush.normalized.json
2) Толковки для ингрессий (composer):
   mundane-enrich
   → $HOME/astro/mundane_forpush.enriched.json
3) Push (TEST или PROD):
   mundane-push-test   |   mundane-push-prod

Доступ тестировщикам к календарям
- В UI Google Calendar → Настройки → (календарь) → Доступ для пользователей → добавить e‑mail → права “Просматривать все сведения о событиях”.
- Если нет Google‑аккаунта: Интеграция → Secret address in iCal format → отдать ссылку (read-only).

GCAL креды (обязательно)
- Храним здесь: ~/.gcal/{credentials.json,token.json}
- Обновить токен:
  $HOME/astroenv/bin/python - <<PY
from google_auth_oauthlib.flow import InstalledAppFlow; from pathlib import Path
scopes=["https://www.googleapis.com/auth/calendar"]; d=Path.home()/".gcal"
creds=InstalledAppFlow.from_client_secrets_file(str(d/"credentials.json"), scopes).run_local_server(port=0, prompt="consent")
(d/"token.json").write_text(creds.to_json()); print("Token saved:", d/"token.json")
PY

CLI wrappers (короткие команды)
- overlay-build-pw        — собрать Overlay PW
- overlay-pw-compact      — сделать day-compact
- overlay-push-test/prod  — push Overlay в TEST/PROD
- mundane-normalize [bak] — бэкап -> normalized forpush
- mundane-enrich          — добавить толковки ингрессий (packs/mundane_ingress.yaml)
- mundane-push-test/prod  — push Mundane в TEST/PROD
- gcal-list               — список календарей (read-only)
- gcal-share --cal "Name" email1 [email2 ...] — выдать доступ (read-only)
Справка: geodac-help

Закрытие сессии
- session-close — бэкап итоговых JSON + summary + end в оперлог
- SAVE_JSONS (бэкап JSON)
- SUMMARY_NOW (короткая сводка)
- ops_note "end"

Lunar (чистый конвейер, 28 дней)
1) Dry-run: with_markers LUNAR_DRY env PUSH=0 ...
2) PROD: lunar-push-prod
Пайплайн: build → merge → dedup → enrich → push

Dreams (календарь снов, без привязки ко времени суток)
- dream-log "YYYY-MM-DD HH:MM" "YYYY-MM-DD HH:MM" "note"   (CAL=... для целевого календ.)
- dream-log-last [минут] "note"        (по умолчанию 60 мин, CAL=...)
- dreams-push-2d-test                   (±2 суток, по 2 окна в день в TEST)
