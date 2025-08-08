#!/usr/bin/env bash
set -e

# If /app/settings.conf is missing, populate it with only settings.conf
if [ ! -f /app/settings.conf ]; then
  echo "[init] seeding /app/settings.conf from image defaults"
  mkdir -p /app
  cp /opt/streamlit/settings.conf /app/
fi

# to allow for the portscan functionality within container

if [ -f "/.dockerenv" ]; then
    rm -f "/.dockerenv"
fi

# If no opencanary config yet, then create it
if [ ! -f /etc/opencanaryd/opencanary.conf ]; then
  echo "[init] generating default opencanary.conf via opencanaryd"
  opencanaryd --copyconfig
  #mkdir -p /etc/opencanaryd
  #cp opencanary.conf /etc/opencanaryd/opencanary.conf
  jq '.["vnc.port"] = 11111' /etc/opencanaryd/opencanary.conf > tmpconf
  mv tmpconf /etc/opencanaryd/opencanary.conf
fi

# rsyslog config: if user‐provided exists, install & restart; else stop rsyslog
if [ -f /app/rsyslog-opencanary.conf ]; then
  echo "[init] custom rsyslog config found, installing"
  cp /app/rsyslog-opencanary.conf /etc/rsyslog.d/opencanary.conf

  echo "[init] starting rsyslog"
  if command -v systemctl >/dev/null; then
    systemctl restart rsyslog
  elif command -v service >/dev/null; then
    service rsyslog restart
  else
    rsyslogd
  fi
fi

#  rsyslog watchdog script
echo "[start] launching rsyslog watchdog script"
bash /opt/streamlit/rsyslog-watcher.sh > /dev/null 2>&1 &

# alerting script
echo "[start] launching log alert watchdog script"
bash /opt/streamlit/alert.sh > /dev/null 2>&1 &

# log management script
echo "[start] log management script"
bash /opt/streamlit/log_man.sh > /dev/null 2>&1 &

# Start a script to patch portscan function in foreground mode but background it
echo "[start] portscan mod"
bash /opt/streamlit/portscan_patch.sh > /dev/null 2>&1 &

# Start OpenCanary in foreground mode but background it
echo "[start] launching OpenCanary daemon"
opencanaryd --start -f > /dev/null 2>&1 &

# Determine port from env or default to 8501
PORT="${MA_PORT:-8501}"

# Pick bind address: use BIND_ADDR if provided, else 0.0.0.0
ADDRESS="${BIND_ADDR:-0.0.0.0}"
echo "[entrypoint] Binding Streamlit to: $ADDRESS"

# Start Streamlit in foreground so Docker stays alive
echo "[start] launching Streamlit app on port ${PORT}"
exec streamlit run /opt/streamlit/app.py \
     --server.headless true \
     --server.port "${PORT}" \
     --server.address "$ADDRESS"
