GeoDAC: Lunar Natal оффлайн
1) Орбисы: правьте config/orbs_moon.yaml
2) Генерация: tools/mk_lunar_ics.sh → logs/lunar_14d*.ics
3) Импорт: Settings → Import → выбрать .ics → календарь TEST Clean
4) PROD: только после проверки (make push-lunar-prod ALLOW=1)
