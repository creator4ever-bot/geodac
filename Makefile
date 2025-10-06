SHELL=/bin/sh
NOG=$(HOME)/bin/nogoogle
TZ?=Europe/Moscow
CAL_OVER?=GeoDAC - Overlay Houses (TEST)
CAL_LUNAR?=Astro - Lunar Natal (TEST Clean)

.PHONY: help lunar-ics overlay-ics mundane-json push-overlay-test push-lunar-test
help:
	@echo "make lunar-ics | overlay-ics | mundane-json | push-overlay-test ALLOW=1 CAL=... | push-lunar-test ALLOW=1 CAL=..."

lunar-ics:
	@$(HOME)/astro/tools/mk_lunar_ics.sh

overlay-ics:
	@$(HOME)/astro/tools/mk_ics_28d.sh || true
	@ls -1t $(HOME)/astro/logs/clean_28d.*.ics 2>/dev/null | head -n1 | sed "s/^/LAST: /"

mundane-json:
	@$(NOG) $(HOME)/bin/mundane-normalize >/dev/null 2>&1 || true
	@$(NOG) $(HOME)/bin/mundane-enrich >/dev/null 2>&1 || true
	@ls -1t $(HOME)/astro/mundane_forpush.*.json 2>/dev/null | head -n 4

push-overlay-test:
	@[ "$(ALLOW)" = "1" ] || (echo "BLOCKED: set ALLOW=1"; exit 1)
	@gc-push --cal "$(CAL_OVER)" --json "$(HOME)/astro/overlay_houses_forpush.pw_compact.json" --tz "$(TZ)" --replace

push-lunar-test:
	@[ "$(ALLOW)" = "1" ] || (echo "BLOCKED: set ALLOW=1"; exit 1)
	@gc-push --cal "$(CAL_LUNAR)" --json "$(HOME)/astro/lunar_natal_forpush.json" --tz "$(TZ)" --replace
