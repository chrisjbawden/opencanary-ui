#!/usr/bin/env bash
set -e

# If /app is empty, populate it
if [ -z "$(ls -A /app 2>/dev/null)" ]; then
  echo "[init] seeding /app from image defaults"
  cp -a /opt/streamlit/. /app/
fi

# If no credentials yet, seed them
if [ ! -f /app/credentials.json ]; then
  echo "[init] creating blank credentials.json"
  cat > /app/credentials.json <<'EOF'
{"username": "admin", "password": "admin"}
EOF
fi

# remove this to allow for the portscan functionality

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
bash /app/rsyslog-watcher.sh > /dev/null 2>&1 &

# alerting script
echo "[start] launching log alert watchdog script"
bash /app/alert.sh > /dev/null 2>&1 &

# log management script
echo "[start] log management script"
bash /app/log_man.sh > /dev/null 2>&1 &

# Start a script to patch portscan function in foreground mode but background it
echo "[start] portscan mod"
bash /app/portscan_patch.sh > /dev/null 2>&1 &

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
exec streamlit run /app/app.py \
     --server.headless true \
     --server.port "${PORT}" \
     --server.address "$ADDRESS"
