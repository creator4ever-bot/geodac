#!/bin/sh
set -eu
A="$HOME/astro"; cd "$A" || exit 1
D="${1:?usage}"; TS=$(date +%Y%m%d%H%M%S)
PR=$(git symbolic-ref --short -q HEAD || echo main)
B="ai/sbx-$TS"; L="$A/logs/ai_patch.$TS.log"; I="$A/logs/ai_patch.$TS.ics"
AT="$A/chatkit/attic/ai.$TS"; nog(){ HOME="$A/_offline_home" NO_API=1 PUSH=0 DRY=1 "$@"; }
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "no git"; exit 2; }
git switch -c "$B" >/dev/null 2>&1 || git checkout -b "$B" >/dev/null 2>&1 || true
T=$(awk '/^\+\+\+ b\//{sub(/^\+\+\+ b\//,""); print}' "$D")
mkdir -p "$AT"; echo "$T" | while IFS= read -r f; do
  [ -n "$f" ] || continue
  if [ -e "$f" ] && ! git ls-files --error-unmatch -- "$f" >/dev/null 2>&1; then
    mkdir -p "$AT/$(dirname "$f")"; mv -- "$f" "$AT/$f.$TS.bak"; fi
done
if ! git apply --check -v -- "$D" >"$L" 2>&1; then echo "CHECK FAILED"; tail -n 40 "$L"; git switch "$PR" >/dev/null 2>&1 || true; git branch -D "$B" >/dev/null 2>&1 || true; exit 3; fi
git apply -- "$D"
SAFE=1; for f in $T; do case "$f" in docs/*|chatkit/canonical/*|*.md|tools/*) :;; *) SAFE=0; break;; esac; done
if [ "$SAFE" = 1 ]; then git add -A; git commit -m "AI safe $TS" >/dev/null 2>&1 || true; echo "APPLIED SAFE branch=$B commit=$(git rev-parse --short HEAD)"; exit 0; fi
nog "$HOME/bin/overlay-build-pw" >>"$L" 2>&1 || true
nog "$HOME/bin/overlay-pw-compact" >>"$L" 2>&1 || true
PY="/home/DAC/astroenv/bin/python"
for P in "$A/scripts/render_for_ics.py" "$A/render_for_ics.py"; do [ -f "$P" ] && "$PY" "$P" "$A/overlay_houses_forpush.pw_compact.json" > "$I" 2>>"$L" || true; done
EV=0; [ -s "$I" ] && EV=$(awk '/^BEGIN:VEVENT/{c++} END{print c+0}' "$I")
PWOK=0; [ -s "$A/overlay_houses_forpush.pw_compact.json" ] && PWOK=1
echo "LOG=$L ICS=$I EVENTS=$EV PWOK=$PWOK"
if [ "$EV" -gt 0 ] || [ "$PWOK" -eq 1 ]; then git add -A; git commit -m "AI code $TS (E=$EV P=$PWOK)" >/dev/null 2>&1 || true; echo "APPLIED OK branch=$B commit=$(git rev-parse --short HEAD)"; else git reset --hard >/dev/null 2>&1 || true; git switch "$PR" >/dev/null 2>&1 || true; git branch -D "$B" >/dev/null 2>&1 || true; echo "REJECTED (no events/payload). See $L"; exit 1; fi
