#!/usr/bin/env bash
set -Eeuo pipefail

# ── Seed /app/settings.conf if missing ───────────────────────────────────────
if [ ! -f /app/settings.conf ]; then
  echo "[init] seeding /app/settings.conf from image defaults"
  mkdir -p /app
  cp /opt/streamlit/settings.conf /app/
fi

# ── Allow portscan logic (you had this quirk) ────────────────────────────────
if [ -f "/.dockerenv" ]; then
  rm -f "/.dockerenv"
fi

# ── Ensure OpenCanary config exists ──────────────────────────────────────────
if [ ! -f /etc/opencanaryd/opencanary.conf ]; then
  echo "[init] generating default opencanary.conf via opencanaryd"
  opencanaryd --copyconfig
  jq '.["vnc.port"] = 11111' /etc/opencanaryd/opencanary.conf > /tmp/tmpconf
  mv /tmp/tmpconf /etc/opencanaryd/opencanary.conf
fi

# ── Optional custom rsyslog config ───────────────────────────────────────────
if [ -f /app/rsyslog-opencanary.conf ]; then
  echo "[init] custom rsyslog config found, installing"
  cp /app/rsyslog-opencanary.conf /etc/rsyslog.d/opencanary.conf
  echo "[init] starting rsyslog"
  if command -v systemctl >/dev/null; then
    systemctl restart rsyslog || true
  elif command -v service >/dev/null; then
    service rsyslog restart || true
  else
    rsyslogd || true
  fi
fi

# ── Start helper scripts in background (tini will reap) ──────────────────────
[ -x /opt/streamlit/rsyslog-watcher.sh ] && /opt/streamlit/rsyslog-watcher.sh >/dev/null 2>&1 &
[ -x /opt/streamlit/alert.sh ]           && /opt/streamlit/alert.sh           >/dev/null 2>&1 &
[ -x /opt/streamlit/log_man.sh ]         && /opt/streamlit/log_man.sh         >/dev/null 2>&1 &
[ -x /opt/streamlit/portscan_patch.sh ]  && /opt/streamlit/portscan_patch.sh  >/dev/null 2>&1 &

# ── Start OpenCanary in background ───────────────────────────────────────────
opencanaryd --start -f >/dev/null 2>&1 &

# ── Streamlit in foreground (container stays alive) ──────────────────────────
PORT="${MA_PORT:-8501}"
ADDRESS="${BIND_ADDR:-0.0.0.0}"
echo "[entrypoint] Binding Streamlit to: ${ADDRESS}, port ${PORT}"

exec streamlit run /opt/streamlit/app.py \
  --server.headless true \
  --server.port "${PORT}" \
  --server.address "${ADDRESS}"
