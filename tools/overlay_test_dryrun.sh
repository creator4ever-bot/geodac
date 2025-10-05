#!/bin/sh
set -eu
ENV=~/astro/chatkit/canonical/02_paths.env
[ -f "$ENV" ] || { echo "Missing ENV: $ENV"; exit 1; }
. "$ENV"

BASE="${GD_BASE:-${BASE_PATH:-${BASE_DIR:-$HOME/astro/base}}}"
OVERLAY="${GD_OVERLAY_TEST:-${OVERLAY_TEST_PATH:-${OVERLAY_TEST_DIR:-$HOME/astro/overlay_test}}}"
STAGE="${GD_STAGE:-${STAGE_DIR:-$HOME/astro/stage}}"

echo "DRY-RUN TEST"; printf "BASE=%s\nOVERLAY=%s\nTARGET=%s\n" "$BASE" "$OVERLAY" "$STAGE"
[ -d "$OVERLAY" ] || { echo "Overlay not found: $OVERLAY"; exit 2; }

export BASE OVERLAY STAGE
find "$OVERLAY" -type f -exec sh -c '
  for src do
    rel=${src#"$OVERLAY"/}
    tgt="$STAGE/$rel"; base="$BASE/$rel"
    if [ -e "$tgt" ]; then
      if cmp -s "$src" "$tgt"; then echo "SKIP identical -> $rel"; else echo "REPLACE target -> $rel"; fi
    elif [ -e "$base" ]; then
      if cmp -s "$src" "$base"; then echo "SKIP identical(base) -> $rel"; else echo "ADD over base -> $rel"; fi
    else
      echo "ADD new -> $rel"
    fi
  done
' sh {} +
