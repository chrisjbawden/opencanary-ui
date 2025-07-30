#!/usr/bin/env bash
#
# prune-log-entries.sh
# Prune log lines older than N days (from settings.conf) on a 6‑hour loop.
#

set -euo pipefail

# ─── CONFIG ──────────────────────────────────────────────────────────────────

LOGFILE="/var/tmp/opencanary.log"
SETTINGS_CONF="/app/settings.conf"

# ─── FUNCTIONS ────────────────────────────────────────────────────────────────

parse_date() {
  local line="$1" datestr ts

  # ISO 8601: 2025‑07‑30T14:08:23
  if [[ $line =~ ^([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}) ]]; then
    datestr="${BASH_REMATCH[1]}"
    date -d "$datestr" +%s 2>/dev/null && return
  fi

  # syslog style: Jul 30 14:08:23 (assume current year)
  if [[ $line =~ ^([A-Za-z]{3}\ +[0-9]{1,2}\ [0-9]{2}:[0-9]{2}:[0-9]{2}) ]]; then
    datestr="$(date +%Y) ${BASH_REMATCH[1]}"
    date -d "$datestr" +%s 2>/dev/null && return
  fi

  # Unrecognised → no timestamp
  echo ""
}

# ─── MAIN LOOP ────────────────────────────────────────────────────────────────

while true; do
  # 1) Attempt to read log_expiry (days) from settings.conf
  if [[ -r "$SETTINGS_CONF" ]]; then
    # pull from .config.log_expiry; //empty makes missing → empty string
    LOG_EXPIRY=$(jq -r '.config.log_expiry // ""' "$SETTINGS_CONF")
  else
    echo "[WARN] Cannot read $SETTINGS_CONF; skipping prune." >&2
    sleep 6h
    continue
  fi

  # 2) If no expiry set, skip pruning
  if [[ -z "$LOG_EXPIRY" ]]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] log_expiry not set; skipping prune." >&2
    sleep 6h
    continue
  fi

  # 3) Compute cutoff epoch
  if ! cutoff_epoch=$(date -d "${LOG_EXPIRY} days ago" +%s 2>/dev/null); then
    echo "[ERROR] Invalid log_expiry value: '$LOG_EXPIRY'; skipping prune." >&2
    sleep 6h
    continue
  fi

  # 4) Prune into temp file
  tmpfile="$(mktemp)"
  while IFS= read -r line; do
    ts=$(parse_date "$line")
    if [[ -z $ts ]] || (( ts >= cutoff_epoch )); then
      echo "$line" >> "$tmpfile"
    fi
    # else: drop older lines
  done < "$LOGFILE"

  # 5) Atomically replace original
  mv "$tmpfile" "$LOGFILE"
  chmod --reference="$LOGFILE" "$LOGFILE" || true

  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Pruned logs older than $LOG_EXPIRY days." >&2

  # 6) Wait 6 hours
  sleep 6h
done
