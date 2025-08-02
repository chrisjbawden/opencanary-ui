#!/usr/bin/env python3
import subprocess
import time
import re
import os
import random
import socket
import signal
import sys

def get_default_interface():
    try:
        with open("/proc/net/route") as f:
            for line in f.readlines():
                fields = line.strip().split()
                if fields[1] == '00000000' and int(fields[3], 16) & 2:
                    return fields[0]
    except Exception:
        pass
    return "eth0"  # Fallback

def get_host_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def is_broadcast_address(ip):
    if ip == "255.255.255.255":
        return True
    if ip.endswith('.255'):
        return True
    return False

INTERFACE = get_default_interface()
HOST_IP = get_host_ip()
KERNLOG_PATH = "/var/log/kern.log"
HOSTNAME = socket.gethostname()
TCPDUMP_CMD = [
    "tcpdump", "-nnl", "-tt", "-i", INTERFACE,
    f"(tcp[tcpflags] & tcp-syn != 0 and tcp[tcpflags] & tcp-ack == 0 or udp) and dst host {HOST_IP}"
]
RE_TCP = re.compile(r"(\d+\.\d+\.\d+\.\d+)\.(\d+) > (\d+\.\d+\.\d+\.\d+)\.(\d+): Flags \[S\]")
RE_UDP = re.compile(r"(\d+\.\d+\.\d+\.\d+)\.(\d+) > (\d+\.\d+\.\d+\.\d+)\.(\d+): UDP")
terminate = False

def handler(signum, frame):
    global terminate
    print("[*] Received signal to terminate. Exiting cleanly...")
    terminate = True

def fake_mac():
    return ":".join(f"{random.randint(0, 255):02x}" for _ in range(6))

def write_iptables_log(line):
    with open(KERNLOG_PATH, "a") as logf:
        logf.write(line + "\n")
        logf.flush()

def main():
    print(f"[*] Using detected interface: {INTERFACE}")
    print(f"[*] Detected host IP: {HOST_IP}")
    print(f"[*] Starting tcpdump... Simulating iptables logs to {KERNLOG_PATH}")

    while not terminate:
        try:
            with subprocess.Popen(
                TCPDUMP_CMD, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
            ) as proc:
                for rawline in proc.stdout:
                    if terminate:
                        proc.terminate()
                        break
                    line = rawline.strip()
                    now = time.localtime()
                    timestamp = time.strftime("%b %e %H:%M:%S", now)

                    match = RE_TCP.search(line)
                    if match:
                        src_ip, src_port, dst_ip, dst_port = match.groups()
                        # Confirm dst_ip matches our IP
                        if dst_ip != HOST_IP:
                            continue
                        mac = fake_mac()
                        logline = (
                            f"{timestamp} {HOSTNAME} kernel: canaryfw: "
                            f"IN={INTERFACE} OUT= MAC={mac} "
                            f"SRC={src_ip} DST={dst_ip} LEN=60 TOS=0x00 PREC=0x00 TTL=64 "
                            f"ID={random.randint(10000,99999)} DF PROTO=TCP SPT={src_port} DPT={dst_port} WINDOW=29200 RES=0x00 SYN URGP=0"
                        )
                        write_iptables_log(logline)
                        print(f"[TCP->LOG] {src_ip}:{src_port} -> {dst_ip}:{dst_port}")
                        continue

                    match = RE_UDP.search(line)
                    if match:
                        src_ip, src_port, dst_ip, dst_port = match.groups()
                        # Confirm dst_ip matches our IP
                        if dst_ip != HOST_IP:
                            continue
                        if is_broadcast_address(dst_ip):
                            continue  # skip broadcast UDP events
                        mac = fake_mac()
                        logline = (
                            f"{timestamp} {HOSTNAME} kernel: IPTables-Dropped: "
                            f"IN={INTERFACE} OUT= MAC={mac} "
                            f"SRC={src_ip} DST={dst_ip} LEN=60 TOS=0x00 PREC=0x00 TTL=64 "
                            f"ID={random.randint(10000,99999)} DF PROTO=UDP SPT={src_port} DPT={dst_port} LEN=42"
                        )
                        write_iptables_log(logline)
                        print(f"[UDP->LOG] {src_ip}:{src_port} -> {dst_ip}:{dst_port}")
                        continue
        except Exception as e:
            print(f"[!] Exception in tcpdump loop: {e}. Restarting in 3s...")
            time.sleep(3)

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)
    try:
        main()
    except Exception as e:
        print(f"[!] Unhandled exception: {e}")
