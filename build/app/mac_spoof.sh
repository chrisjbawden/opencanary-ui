#!/usr/bin/env bash
set -euo pipefail

# --- Autodetect the host’s primary uplink interface --------------------------
# Picks the device used for the default route (e.g. enp3s0, eth0, etc.)
HOST_IFACE=$(ip route | awk '/^default/ {print $5; exit}')
if [[ -z "$HOST_IFACE" ]]; then
  echo "[error] Could not detect HOST_IFACE via default route" >&2
  exit 1
fi

# --- Configuration ------------------------------------------------------------

# 1) Vendor OUI (first 3 bytes of the MAC you want to mimic)
#    e.g. Synology’s OUI might be 00:11:32
VENDOR_OUI="00:11:32"

# 2) Name for the macvlan interface
HONEY_INTF="macvlan_hpot"

# --- Generate a random MAC suffix (last 3 bytes) ------------------------------
rand_byte() { printf '%02X' $(( RANDOM % 256 )); }
R1=$(rand_byte); R2=$(rand_byte); R3=$(rand_byte)
HONEYPOT_MAC="${VENDOR_OUI}:${R1}:${R2}:${R3}"

echo "[init] Detected host interface: $HOST_IFACE"
echo "[init] Creating $HONEY_INTF with spoofed MAC $HONEYPOT_MAC"

# --- Create & configure the macvlan ------------------------------------------
ip link add "$HONEY_INTF" link "$HOST_IFACE" type macvlan mode bridge
ip link set dev "$HONEY_INTF" address "$HONEYPOT_MAC"
ip link set dev "$HONEY_INTF" up

# --- Obtain an IP via DHCP ---------------------------------------------------
echo "[init] Requesting DHCP lease on $HONEY_INTF"
dhclient "$HONEY_INTF"

# --- Exec your honeypot process bound to that interface -----------------------
# Replace this with your actual honeypot command, binding to $HONEY_INTF
exec /usr/bin/honeypot --iface "$HONEY_INTF"
