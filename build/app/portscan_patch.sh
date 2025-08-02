#!/usr/bin/env bash

CONF_PATH="/etc/opencanaryd/opencanary.conf"
PYTHON_SCRIPT="/app/portscanmod.py"

check_portscan_enabled() {
    grep -q '"portscan"[[:space:]]*:[[:space:]]*true' "$CONF_PATH"
}

is_python_running() {
    pgrep -f "$PYTHON_SCRIPT" > /dev/null 2>&1
}

start_python() {
    nohup python3 "$PYTHON_SCRIPT" > /dev/null 2>&1 &
    echo "[monitor_portscan.sh] Started portscan watcher"
}

stop_python() {
    pkill -f "$PYTHON_SCRIPT"
    echo "[monitor_portscan.sh] Stopped portscan watcher"
}

while true; do
    if check_portscan_enabled; then
        if ! is_python_running; then
            start_python
        fi
    else
        if is_python_running; then
            stop_python
        fi
    fi
    sleep 60
done
