#!/usr/bin/env bash
set -Eeuo pipefail
AST="$HOME/astro"
OUT="$AST/chatlog/SESSION_SUMMARY_$(date +%F_%H%M%S).md"
LAST_OPS=$(ls -1t "$AST/chatlog"/OPS_*.log 2>/dev/null | head -n1)
LAST_AUD=$(ls -1t "$AST/logs"/geodac_audit_*.log 2>/dev/null | head -n1)

{
  echo "# GeoDAC — Session Summary @ $(date -Is)"
  echo
  if [ -n "$LAST_OPS" ]; then echo "## OPS tail"; tail -n 80 "$LAST_OPS"; fi
  if [ -n "$LAST_AUD" ]; then echo; echo "## Audit tail"; tail -n 120 "$LAST_AUD"; fi
} > "$OUT"

echo "Summary saved to: $OUT"
