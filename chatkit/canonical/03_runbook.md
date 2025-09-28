Open: ops/start -> geodacctx -> gdaudit; if diagnose_luna_vs_overlay ACC<100% — no PUSH.
Overlay: build -> day-compact -> push TEST -> visual check -> push PROD (same file).
Mundane: normalize backup -> enrich -> push TEST/PROD.
Lunar: build -> merge -> dedup -> enrich -> push; PROD only if dry-run OK.
Close: session-close -> SAVE_JSONS -> SUMMARY_NOW -> ops_note "end".
