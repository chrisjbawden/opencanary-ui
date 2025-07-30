#!/usr/bin/env bash
#
# monitor_logs.sh
#
# Continuously checks a JSON config for whether monitoring is enabled,
# then, when enabled, scans your JSON‑line log file every 2 minutes for
# any of the configured alert strings. It will *not* alert on historical
# entries present at first launch—only on new lines seen after startup.
#
# Requirements: jq, curl

SETTINGS_PATH="/app/settings.conf"
LOG_FILE="/var/tmp/opencanary.log"
POLL_OFF=60    # secs between config checks when alerting is off
POLL_ON=60     # secs between log scans when alerting is on

sleep 60

# — Function to provide raw JSON so jq can parse it —
_clean_json() {
  cat "$SETTINGS_PATH"
}

# — Seed LAST_TIME once at startup —
if [[ -f "$LOG_FILE" ]]; then
  LAST_TIME=$(jq -s -r 'map(.local_time) | max // empty' "$LOG_FILE")
  [[ -z "$LAST_TIME" ]] && LAST_TIME=$(date '+%F %T')
else
  LAST_TIME=$(date '+%F %T')
fi
echo "Initial LAST_TIME set to: $LAST_TIME"

while true; do
  # 1) Validate config JSON
  if ! jq . <(_clean_json) &>/dev/null; then
    echo "[WARN ] Invalid JSON in $SETTINGS_PATH; using previous settings" >&2
    sleep $POLL_OFF
    continue
  fi

  # 2) Read settings
  alert_on=$(jq -r '.config.alert'          <(_clean_json))
  readarray -t strings < <(jq -r '.config.alert_strings[]' <(_clean_json))
  method=$(   jq -r '.config.alert_method'   <(_clean_json))
  url=$(      jq -r '.config.webhook_url'    <(_clean_json))
  msg=$(      jq -r '.config.alert_message'  <(_clean_json))

  # 3) Build regex pattern
  if (( ${#strings[@]} )); then
    pat="("
    for s in "${strings[@]}"; do
      esc=$(printf '%s' "$s" | sed -e 's/[][\.*^$/]/\\&/g')
      pat+="$esc|"
    done
    pat=${pat%|}
    pat+=")"
  else
    pat=""
  fi

  # 4) If alerting is off, wait and recheck
  if [[ "$alert_on" != "true" ]]; then
    echo "[$(date '+%F %T')] Monitoring OFF; re‑checking in ${POLL_OFF}s."
    sleep $POLL_OFF
    continue
  fi

  echo "[$(date '+%F %T')] Monitoring ON; scanning for pattern: ${pat}"

  # 5) Extract only new entries newer than LAST_TIME
  new_json=$(jq --arg last "$LAST_TIME" 'select(.local_time > $last)' "$LOG_FILE")
  if [[ -z "$pat" || -z "$new_json" ]]; then
    echo "[$(date '+%F %T')] Nothing new to scan or no patterns defined."
    sleep $POLL_ON
    continue
  fi

  # 6) Filter lines where the pattern appears
  matches=$(printf '%s\n' "$new_json" | grep -E "$pat" || true)
  if [[ -n "$matches" ]]; then
    echo "[$(date '+%F %T')] Found matches:"
    printf '%s\n' "$matches"

    matches_json=$(printf '%s\n' "$matches" | jq -R -s -c 'split("\n")[:-1]')
    payload=$(jq -n \
      --arg ts "$(date -Iseconds)" \
      --arg custom "$msg" \
      --argjson m "$matches_json" \
      '{ timestamp: $ts, message: $custom, matches: $m }'
    )

    case "$method" in
      webhook)
        curl -s -X POST "$url" \
             -H "Content-Type: application/json" \
             -d "$payload"
        ;;
      ntfy)
        curl -s -d "$msg" "$url"
        ;;
      *)
        echo "[WARN] Unknown alert_method: $method"
        ;;
    esac
  else
    echo "[$(date '+%F %T')] No matches this batch."
  fi

  # 7) Advance LAST_TIME
  new_last=$(printf '%s\n' "$new_json" \
    | jq -r '.local_time' \
    | sort \
    | tail -n1)
  LAST_TIME="$new_last"

  sleep $POLL_ON
done
