import os
import subprocess
import shutil
import streamlit as st
import json
import zipfile
import io
import uuid 
import time

from utils import (
    load_json, save_json, restart_opencanary,
    CONFIG_PATH, LOG_PATH,
    load_settings, save_settings,
    get_setting, set_setting, delete_setting
)

SKIN_DIR = "/usr/local/lib/python3.10/dist-packages/opencanary/modules/data/http/skin"
FTP_BANNERS = [
    "FileZilla Server 0.9",
    "Disk Station FTP server at DiskStation ready.",
    "Microsoft FTP Service",
    "(vsFTPd 3.0.3)"
]
SSH_VERSIONS = [
    "SSH-2.0-OpenSSH_5.1p1 Debian-4",
    "SSH-2.0-OpenSSH_7.4",
    "SSH-2.0-OpenSSH_8.0",
    "SSH-2.0-OpenSSH_6.8p1-hpn14v6"
]

def render_config():
    cfg = load_json(CONFIG_PATH)

    if st.session_state.get("layout") == "wide":
        st.session_state.layout = "centered"
        st.rerun()

    raw_mode = st.toggle("raw JSON config", value=False, key="cfg_raw_mode")

    if raw_mode:
        st.text_area(
            "Raw JSON Configuration",
            value=json.dumps(cfg, indent=2),
            height=500,
            key="cfg_raw_json",
        )
        if st.button("Save Raw Config"):
            try:
                new_cfg = json.loads(st.session_state.cfg_raw_json)
                save_json(CONFIG_PATH, new_cfg)
                restart_opencanary()
                st.success("Raw configuration saved & service restarted.")
                time.sleep(2)
                st.rerun()
            except json.JSONDecodeError as e:
                st.error(f"Invalid JSON: {e}")
    else:
        handlers = (
            cfg.setdefault("logger", {})
               .setdefault("kwargs", {})
               .setdefault("handlers", {})
        )
        for h in ("console", "file"):
            if h in handlers:
                handlers[h].setdefault("formatter", "plain")

        initial = {
            "http.enabled":              cfg.get("http.enabled", False),
            "http.skin":                 cfg.get("http.skin", "default"),
            "http.port":                 cfg.get("http.port", 80),
            "https.port":                cfg.get("https.port", 443),
            "portscan.enabled":          cfg.get("portscan.enabled", False),
            "portscan.ignore_localhost": cfg.get("portscan.ignore_localhost", False),
            "ftp.port":                  cfg.get("ftp.port", None),
            "ftp.banner":                cfg.get("ftp.banner", FTP_BANNERS[0]),
            "ssh.enabled":               cfg.get("ssh.enabled", False),
            "ssh.port":                  cfg.get("ssh.port", 22),
            "ssh.version":               cfg.get("ssh.version", SSH_VERSIONS[0]),
            "rdp.enabled":               cfg.get("rdp.enabled", False)
        }

        # ─── Device Node ID ──────────────────────────────────────────────────────
        device_node_id = cfg.get("device.node_id", "opencanary-1")
        new_node_id = st.text_input("Device Node ID", value=device_node_id, key="cfg_node_id")

        # ─── IP Ignorelist ───────────────────────────────────────────────────────

        st.markdown("**IP Ignorelist**")

        def as_dict_list(lst):
            if lst and isinstance(lst[0], dict):
                return lst
            return [{"id": str(uuid.uuid4()), "ip": ip} for ip in lst]

        # Only initialise from config if not in session_state
        if "ip_ignorelist_edit" not in st.session_state:
            st.session_state.ip_ignorelist_edit = as_dict_list(cfg.get("ip.ignorelist", []))

        ip_ignorelist_edit = st.session_state.ip_ignorelist_edit

        indices_to_remove = []
        for idx, entry in enumerate(ip_ignorelist_edit):
            col1, col2 = st.columns([8, 1])
            ip_value = col1.text_input("", value=entry["ip"], key=f"ip_ignore_edit_{entry['id']}")
            if ip_value != entry["ip"]:
                ip_ignorelist_edit[idx]["ip"] = ip_value
            with col2:
                st.markdown('<div style="margin-top: 27px;"></div>', unsafe_allow_html=True)
                if st.button("❌", key=f"del_ip_ignore_{entry['id']}", help="Remove this IP"):
                    indices_to_remove.append(idx)
                    
        for idx in reversed(indices_to_remove):
            ip_ignorelist_edit.pop(idx)
            st.rerun()

        if st.button("➕", key="add_ip_ignore_btn"):
            ip_ignorelist_edit.append({"id": str(uuid.uuid4()), "ip": ""})
            st.rerun()

        # ─── HTTP/S ────────────────────────────────────────────────────────────────
        http_enabled = st.checkbox("Enable HTTP/S", value=initial["http.enabled"], key="cfg_http_en")
        if http_enabled:
            templates = sorted(
                d for d in os.listdir(SKIN_DIR)
                if os.path.isdir(os.path.join(SKIN_DIR, d))
            )
            st.selectbox(
                "HTTP skin",
                options=templates,
                index=templates.index(initial["http.skin"]) if initial["http.skin"] in templates else 0,
                key="cfg_http_skin"
            )
            col_http, col_https = st.columns(2)
            with col_http:
                http_port = st.number_input(
                    "HTTP port",
                    min_value=1, max_value=65535,
                    value=initial["http.port"],
                    key="cfg_http_port"
                )
            with col_https:
                https_port = st.number_input(
                    "HTTPS port",
                    min_value=1, max_value=65535,
                    value=initial["https.port"],
                    key="cfg_https_port"
                )
        else:
            http_port = initial["http.port"]
            https_port = initial["https.port"]

        cfg["http.port"] = http_port
        cfg["https.port"] = https_port

        # ─── Portscan ──────────────────────────────────────────────────────────────
        ps_enabled = st.checkbox("Enable portscan", value=initial["portscan.enabled"], key="cfg_ps_en")
        if ps_enabled:
            ignore_local = st.checkbox(
                "Ignore localhost",
                value=initial["portscan.ignore_localhost"],
                key="cfg_ps_ignore"
            )
        else:
            ignore_local = initial["portscan.ignore_localhost"]

        # ─── FTP ──────────────────────────────────────────────────────────────────
        ftp_enabled = st.checkbox("Enable FTP honeypot", value=initial["ftp.port"] is not None, key="cfg_ftp_en")
        if ftp_enabled:
            ftp_port = st.number_input(
                "FTP Port",
                min_value=1, max_value=65535,
                value=initial["ftp.port"] or 21,
                key="cfg_ftp_port"
            )
            banner_default = initial["ftp.banner"] if initial["ftp.banner"] in FTP_BANNERS else FTP_BANNERS[0]
            ftp_banner = st.selectbox(
                "FTP Banner",
                options=FTP_BANNERS,
                index=FTP_BANNERS.index(banner_default),
                key="cfg_ftp_banner"
            )

        # ─── SSH ──────────────────────────────────────────────────────────────────
        ssh_enabled = st.checkbox("Enable SSH honeypot", value=initial["ssh.enabled"], key="cfg_ssh_en")
        if ssh_enabled:
            ssh_port = st.number_input(
                "SSH Port",
                min_value=1, max_value=65535,
                value=initial["ssh.port"],
                key="cfg_ssh_port"
            )
            ssh_version = st.selectbox(
                "SSH Version",
                options=SSH_VERSIONS,
                index=SSH_VERSIONS.index(initial["ssh.version"]),
                key="cfg_ssh_ver"
            )

        # ─── RDP ──────────────────────────────────────────────────────────────────
        rdp_enabled = st.checkbox("Enable RDP honeypot", value=initial["rdp.enabled"], key="cfg_rdp_en")

        # ─── Save & Restart ───────────────────────────────────────────────────────
        if st.button("Save & Restart", use_container_width=True):
            # Device node_id
            cfg["device.node_id"] = st.session_state.cfg_node_id

            # Save the current IP ignorelist from session_state
            cfg["ip.ignorelist"] = [
                entry["ip"].strip() for entry in st.session_state.ip_ignorelist_edit if entry["ip"].strip()
            ]

            # IP ignorelist is already managed above

            if http_enabled:
                cfg["http.enabled"]  = True
                cfg["https.enabled"] = True
                cfg["http.skin"]     = st.session_state.cfg_http_skin
                cfg["https.skin"]    = st.session_state.cfg_http_skin
                cfg["http.port"]     = st.session_state.cfg_http_port
                cfg["https.port"]    = st.session_state.cfg_https_port
            else:
                cfg["http.enabled"]  = False
                cfg["https.enabled"] = False
                cfg.pop("http.skin", None)
                cfg.pop("https.skin", None)
                cfg.pop("http.port", None)
                cfg.pop("https.port", None)

            cfg["portscan.enabled"]          = ps_enabled
            cfg["portscan.ignore_localhost"] = ignore_local

            if ftp_enabled:
                cfg["ftp.port"]   = st.session_state.cfg_ftp_port
                cfg["ftp.banner"] = st.session_state.cfg_ftp_banner
            else:
                cfg.pop("ftp.port", None)
                cfg.pop("ftp.banner", None)

            if ssh_enabled:
                cfg["ssh.enabled"] = True
                cfg["ssh.port"]    = st.session_state.cfg_ssh_port
                cfg["ssh.version"] = st.session_state.cfg_ssh_ver
            else:
                cfg["ssh.enabled"] = False
                cfg.pop("ssh.port", None)
                cfg.pop("ssh.version", None)

            cfg["rdp.enabled"] = bool(rdp_enabled)

            save_json(CONFIG_PATH, cfg)
            restart_opencanary()
            st.success("Configuration saved & services restarted.")
            time.sleep(2)
            st.rerun()

    # ─── Remote Syslog (unchanged) ──────────────────────────────────────────────
    st.markdown("---")
    syslog_conf_path = "/app/rsyslog-opencanary.conf"
    if "cfg_syslog_en" not in st.session_state:
        st.session_state["cfg_syslog_en"] = os.path.exists(syslog_conf_path)
    file_exists_now = os.path.exists(syslog_conf_path)
    syslog_enabled = st.checkbox("Enable remote syslog", key="cfg_syslog_en")
    just_unticked = file_exists_now and not syslog_enabled

    syslog_ip = ""
    syslog_port = 514
    syslog_proto = "udp"
    if syslog_enabled and file_exists_now:
        try:
            with open(syslog_conf_path) as f:
                for line in f:
                    if 'target="' in line:
                        syslog_ip = line.split('target="')[1].split('"')[0]
                    if 'port="' in line:
                        syslog_port = int(line.split('port="')[1].split('"')[0])
                    if 'type="om' in line:
                        proto_raw = line.split('type="om')[1].split('"')[0]
                        if proto_raw in ("udp", "tcp"):
                            syslog_proto = proto_raw
        except Exception as e:
            st.warning(f"Could not parse existing syslog config: {e}")

    if syslog_enabled:
        syslog_ip = st.text_input("Syslog server IP", value=syslog_ip, key="cfg_syslog_ip")
        syslog_port = st.number_input(
            "Syslog port",
            min_value=1, max_value=65535,
            value=syslog_port,
            key="cfg_syslog_port"
        )
        syslog_proto = st.selectbox(
            "Syslog protocol",
            ["udp", "tcp"],
            index=["udp", "tcp"].index(syslog_proto),
            key="cfg_syslog_proto"
        )
        if st.button("Save Syslog Settings", key="btn_save_syslog", use_container_width=True):
            rsyslog_conf = f'''
module(load="om{syslog_proto}")
*.* action(type="om{syslog_proto}" target="{syslog_ip}" port="{syslog_port}")
'''.strip()
            try:
                with open(syslog_conf_path, "w") as f:
                    f.write(rsyslog_conf)
                st.success("Syslog settings saved.")
                time.sleep(2)
                st.rerun()
            except Exception as e:
                st.error(f"Failed to save syslog config: {e}")

    elif just_unticked:
        if st.button("Disable", type="primary", use_container_width=True):
            try:
                os.remove(syslog_conf_path)
                st.info("Syslog config removed.")
            except FileNotFoundError:
                st.info("Syslog config was already removed.")
            except Exception as e:
                st.error(f"Error disabling syslog: {e}")
            time.sleep(2)
            st.rerun()

    st.write("---")

    # ─── Alerting settings via helpers ───────────────────────────────────────────
    DEFAULT_CFG = {
        "alert": False,
        "alert_strings": [],
        "alert_method": "webhook",
        "webhook_url": "",
        "alert_message": ""
    }
    cfg_alert = get_setting("config", DEFAULT_CFG)
    initial_alert = cfg_alert.get("alert", False)

    alert_on = st.checkbox("Enable alerting", value=initial_alert, key="cfg_alert_en")
    if alert_on:
        raw = st.text_area(
            "Search strings (comma‑separated)",
            value=",".join(cfg_alert.get("alert_strings", [])),
            help="e.g. fire,login,unauthorised",
            key="cfg_alert_raw"
        )
        method = st.selectbox(
            "Alert method",
            options=["webhook", "ntfy"],
            index=["webhook", "ntfy"].index(cfg_alert.get("alert_method", "webhook")),
            key="cfg_alert_method"
        )
        url = st.text_input(
            "Endpoint URL",
            value=cfg_alert.get("webhook_url", ""),
            placeholder="https://example.com/your/webhook",
            key="cfg_alert_url"
        )
        message = st.text_input(
            "Alert message",
            value=cfg_alert.get("alert_message", ""),
            placeholder="E.g. Alert! system one has a warning",
            key="cfg_alert_msg"
        )

        if st.button("Save", key="alert_save_button", use_container_width=True):
            set_setting("config", {
                "alert": True,
                "alert_strings": [s.strip() for s in raw.split(",") if s.strip()],
                "alert_method": method,
                "webhook_url": url.strip(),
                "alert_message": message.strip()
            })
            st.success("Alert configuration saved.")
            time.sleep(2)
            st.rerun()

    elif not alert_on and initial_alert:
        if st.button("Disable alerting", use_container_width=True):
            set_setting("config", DEFAULT_CFG.copy())
            st.success("Alerting disabled.")
            time.sleep(2)
            st.rerun()

    st.write("---")

    # ─── Log expiry setting (use helpers) ───────────────────────────────────────
    log_expiry = get_setting("logman.log_expiry", 90)
    col1, col2 = st.columns([2, 1])
    with col1:
        new_value = st.number_input(
            label="Log expiry (days)",
            min_value=1,
            value=log_expiry,
            step=1,
            key="cfg_log_expiry",
            help="Lines older than this (in days) will be pruned."
        )
    with col2:
        st.markdown("<div style='height:27px;'></div>", unsafe_allow_html=True)
        if st.button("Save log expiry", key="log_expiry_save", use_container_width=True):
            set_setting("logman.log_expiry", int(new_value))
            st.success(f"Saved log_expiry = {new_value} days")
            time.sleep(2)
            st.rerun()

    st.write("---")

    # ─── Manage HTTP/S Skins (unchanged) ───────────────────────────────────────
    with st.expander("Manage HTTP/S Skins", expanded=False):
        skins = [
            d for d in os.listdir(SKIN_DIR)
            if os.path.isdir(os.path.join(SKIN_DIR, d))
        ]
        for name in skins:
            col_name, col_dl, col_del = st.columns([6,1,1])
            with col_name:
                st.write(name)
            mem_zip = io.BytesIO()
            with zipfile.ZipFile(mem_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for root, _, files in os.walk(os.path.join(SKIN_DIR, name)):
                    for file in files:
                        full = os.path.join(root, file)
                        arc = os.path.relpath(full, os.path.join(SKIN_DIR, name))
                        zf.write(full, arc)
            mem_zip.seek(0)
            with col_dl:
                st.download_button(
                    label="⬇️",
                    data=mem_zip,
                    file_name=f"{name}.zip",
                    mime="application/zip",
                    key=f"dl_{name}"
                )
            with col_del:
                if st.button("❌", key=f"del_{name}", help=f"Delete '{name}'"):
                    shutil.rmtree(os.path.join(SKIN_DIR, name))
                    st.success(f"Deleted skin: {name}")
                    st.rerun()

        st.write("---")
        upload_col1, upload_col2 = st.columns([3, 1])
        with upload_col1:
            uploaded = st.file_uploader("Select a .zip file", type="zip", key="skin_zip")
        with upload_col2:
            st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)
            if st.button("Upload", key="upload_skin", use_container_width=True):
                if not uploaded:
                    st.error("No file selected")
                else:
                    z = zipfile.ZipFile(io.BytesIO(uploaded.read()))
                    folder = os.path.splitext(uploaded.name)[0]
                    target = os.path.join(SKIN_DIR, folder)
                    if os.path.exists(target):
                        shutil.rmtree(target)
                    z.extractall(target)
                    st.success(f"Extracted skin to '{folder}'")
                    time.sleep(2)
                    st.rerun()
