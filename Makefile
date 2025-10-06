SHELL=/bin/sh
NOG=$(HOME)/bin/nogoogle
TZ?=Europe/Moscow

# Подхватить ID из файла (вы уже сохранили config/cals.env)
-include $(HOME)/astro/config/cals.env

CAL_LUNAR?=Astro - Lunar Natal (TEST Clean)
CAL_LUNAR_PROD?=Astro - Lunar Natal (PROD)

.PHONY: help lunar-ics overlay-ics mundane-json \
        push-lunar-test push-lunar-prod wipe-lunar-prod

help:
	@echo "make lunar-ics | overlay-ics | mundane-json"
	@echo "make push-lunar-test ALLOW=1"
	@echo "make wipe-lunar-prod ALLOW=1 | push-lunar-prod ALLOW=1"

lunar-ics:
	@$(HOME)/astro/tools/mk_lunar_ics.sh

overlay-ics:
	@$(HOME)/astro/tools/mk_ics_28d.sh || true
	@ls -1t $(HOME)/astro/logs/clean_28d.*.ics 2>/dev/null | head -n1 | sed "s/^/LAST: /"

mundane-json:
	@$(NOG) $(HOME)/bin/mundane-normalize >/dev/null 2>&1 || true
	@$(NOG) $(HOME)/bin/mundane-enrich   >/dev/null 2>&1 || true
	@ls -1t $(HOME)/astro/mundane_forpush.*.json 2>/dev/null | head -n 4

push-lunar-test:
	@[ "$(ALLOW)" = "1" ] || (echo "BLOCKED: set ALLOW=1"; exit 1)
	@cal=$${CAL_LUNAR_TEST_ID:-"$(CAL_LUNAR)"}; \
	gc-push --cal "$$cal" --json "$(HOME)/astro/lunar_natal_forpush.json" --tz "$(TZ)" --replace

wipe-lunar-prod:
	@[ "$(ALLOW)" = "1" ] || (echo "BLOCKED: set ALLOW=1"; exit 1)
	@echo '{"events":[]}' > $(HOME)/astro/empty.events.json
	@cal=$${CAL_LUNAR_PROD_ID:-"$(CAL_LUNAR_PROD)"}; \
	gc-push --cal "$$cal" --json "$(HOME)/astro/empty.events.json" --tz "$(TZ)" --replace

push-lunar-prod:
	@[ "$(ALLOW)" = "1" ] || (echo "BLOCKED: set ALLOW=1"; exit 1)
	@cal=$${CAL_LUNAR_PROD_ID:-"$(CAL_LUNAR_PROD)"}; \
	gc-push --cal "$$cal" --json "$(HOME)/astro/lunar_natal_forpush.json" --tz "$(TZ)" --replace

PY=/home/DAC/astroenv/bin/python
count-lunar-prod:
	@cal=$${CAL_LUNAR_PROD_ID:-"Astro - Lunar Natal (PROD)"}; \
	$(PY) $(HOME)/astro/tools/gc_wipe_all.py --cal "$$cal"

wipe-lunar-prod-hard:
	@[ "$(ALLOW)" = "1" ] || (echo "BLOCKED: set ALLOW=1"; exit 1)
	@cal=$${CAL_LUNAR_PROD_ID:-"Astro - Lunar Natal (PROD)"}; \
	$(PY) $(HOME)/astro/tools/gc_wipe_all.py --cal "$$cal" --do

# Lunar: PA (Sun..Pluto + ASC/MC/DSC/IC) по умолчанию
lunar-ics:
	@$(HOME)/astro/tools/mk_lunar_ics_pa.sh

lunar-ics-planets:
	@$(HOME)/astro/tools/mk_lunar_ics_planets.sh

CAL_LUNAR_PROD?=Astro - Lunar Natal (PROD)
push-lunar-ics-prod:
	@[ "$(ALLOW)" = "1" ] || (echo "BLOCKED: set ALLOW=1"; exit 1)
	@ics=$$(ls -1t $(HOME)/astro/logs/lunar_14d.pa.*.ics $(HOME)/astro/logs/lunar_14d.planets.*.ics 2>/dev/null | head -n1); \
	test -n "$$ics" || (echo "no lunar .ics found"; exit 2); \
	$(HOME)/astro/tools/ics_to_events_json.py < "$$ics" > $(HOME)/astro/logs/lunar_planets.events.json; \
	gc-push --cal "$(CAL_LUNAR_PROD)" --json $(HOME)/astro/logs/lunar_planets.events.json --tz Europe/Moscow --replace
