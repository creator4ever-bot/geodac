#!/bin/sh
cd "$HOME/astro" || { echo "NO_ASTRO"; exit 1; }
TS=$(date +%Y%m%d%H%M%S); RDIR="$HOME/astro/logs/recovery.$TS"; mkdir -p "$RDIR"
echo "--- SUMMARY ---"
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "GIT=YES"
  BR=$(git branch --show-current 2>/dev/null); echo "BRANCH=${BR:-'-'}"
  git log -1 --format='HEAD=%h %ct %cI %s' 2>/dev/null || true
  if git remote get-url origin >/dev/null 2>&1; then
    echo "ORIGIN=YES"
    git fetch origin --prune >/dev/null 2>&1 || true
    DEF=$(git remote show origin 2>/dev/null | awk '/HEAD branch/ {print $NF}')
    [ -n "$DEF" ] && echo "ORIGIN_DEF=$DEF" || echo "ORIGIN_DEF=-"
    [ -n "$DEF" ] && git log -1 --format='ORIGIN=%h %ct %cI %s' origin/$DEF 2>/dev/null || true
  else echo "ORIGIN=NO"; fi
else
  echo "GIT=NO"
fi
. "$HOME/astro/chatkit/canonical/02_paths.env" 2>/dev/null || true
BASE=${GD_BASE:-$HOME/astro/base}; OVER=${GD_OVERLAY_TEST:-$HOME/astro/overlay_test}; STAGE=${GD_STAGE:-$HOME/astro/stage}
count(){ [ -d "$1" ] && find "$1" -type f | wc -l | tr -d ' ' || echo 0; }
echo "BASE=$BASE exists=$( [ -d "$BASE" ] && echo yes || echo no ) files=$(count "$BASE")"
echo "OVERLAY=$OVER exists=$( [ -d "$OVER" ] && echo yes || echo no ) files=$(count "$OVER")"
echo "STAGE=$STAGE exists=$( [ -d "$STAGE" ] && echo yes || echo no ) files=$(count "$STAGE")"
echo "--- SUMMARY ---"; echo "$RDIR"
