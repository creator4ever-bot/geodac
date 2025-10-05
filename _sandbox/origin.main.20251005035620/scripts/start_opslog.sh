#!/usr/bin/env bash
export OPS_LOG="$HOME/astro/chatlog/OPS_$(date +%F_%H%M%S).log"
mkdir -p "$HOME/astro/chatlog"
{
  echo "=== GeoDAC Ops session start $(date -Is) ==="
  echo "User: $USER  Host: $(hostname)"
  echo "Repo: ~/astro"
  echo "Python3: $(command -v python3 || echo 'not found')  $([ -x "$(command -v python3)" ] && python3 -V)"
} | tee -a "$OPS_LOG"
export PS4='+ [$(date "+%F %T")] '
exec > >(tee -a "$OPS_LOG") 2>&1
set -x
ops_note() { printf "\n### NOTE %s — %s\n\n" "$(date -Is)" "$*"; }
export -f ops_note
ops_note "opslog started"
echo "OPS_LOG=$OPS_LOG"
