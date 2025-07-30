#!/bin/bash

RSYSLOG_CONF="/app/rsyslog-opencanary.conf"
INSTALLED_CONF="/etc/rsyslog.d/opencanary.conf"

start_rsyslog() {
    echo "[watcher] Starting rsyslogd"
    cp "$RSYSLOG_CONF" "$INSTALLED_CONF"
    rsyslogd -n &
}

stop_rsyslog() {
    echo "[watcher] Stopping rsyslogd"
    pkill -TERM -x rsyslogd
    rm -f "$INSTALLED_CONF"
}

while true; do
    if [ -f "$RSYSLOG_CONF" ]; then
        if ! pgrep -x rsyslogd > /dev/null; then
            start_rsyslog
        fi
    else
        if pgrep -x rsyslogd > /dev/null; then
            stop_rsyslog
        fi
    fi
    sleep 10
done
