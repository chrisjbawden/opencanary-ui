#!/usr/bin/env bash
set -euo pipefail

PYTHON_SCRIPT="/app/portscanmod.py"
CONF_FILE="/etc/opencanaryd/opencanary.conf"
LOG_FILE="/tmp/portscanmod.log"

check_portscan_enabled() {
    grep -q '"portscan.enabled"[[:space:]]*:[[:space:]]*true' /etc/opencanaryd/opencanary.conf
}

is_python_running() {
    if pgrep -f portscanmod.py; then
        return 0
    else
        return 1
    fi
}

start_python() {
    nohup python3 "$PYTHON_SCRIPT" > "$LOG_FILE" 2>&1 &
    echo "[monitor_portscan.sh] Started portscan watcher"
}

stop_python() {
    pkill -9 -f "python3 $PYTHON_SCRIPT" || true
    echo "[monitor_portscan.sh] Stopped portscan watcher"
}

cleanup() {
    stop_python
    exit 0
}

trap cleanup SIGINT SIGTERM

while true; do
    if check_portscan_enabled; then
        if ! is_python_running; then
            echo "[monitor_portscan.sh] portscan enabled, starting watcher"
            start_python
        fi
    else
        if is_python_running; then
            echo "[monitor_portscan.sh] portscan disabled, stopping watcher"
            stop_python
        fi
    fi
    echo sleeping ...
    sleep 10
done
