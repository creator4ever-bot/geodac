# GeoDAC CLI wrappers

Короткие команды (в $HOME/bin):
- overlay-build-pw        — собрать Overlay PW
- overlay-pw-compact      — PW -> PW compact (убирает день ингресса)
- overlay-push-test/prod  — push Overlay в TEST/PROD
- mundane-normalize [bak] — бэкап Mundane -> normalized forpush
- mundane-enrich          — толковки для ингрессий (исп. packs/mundane_ingress.yaml)
- mundane-push-test/prod  — push Mundane в TEST/PROD
- gcal-list               — вывести список календарей (read-only)
- gcal-share --cal "Name" email1 [email2 ...] — выдать доступ (read-only)

Примеры:
- Overlay:  
  overlay-build-pw && overlay-pw-compact && overlay-push-test  
  (после визуальной проверки) overlay-push-prod
- Mundane:  
  mundane-normalize && mundane-enrich && mundane-push-prod

Замечания:
- PROD трогаем только после OK в TEST (для Overlay, при наличии TEST).
- Креды GCAL: ~/.gcal/{credentials.json,token.json}
