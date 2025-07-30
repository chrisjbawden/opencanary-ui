# settings.py
import time
import os
import shutil
import zipfile
import datetime
import streamlit as st
from utils import load_settings, save_settings, BACKUP_DIR, CONFIG_PATH, restart_opencanary

def render_settings():
    settings = load_settings()
    creds = settings.get("credentials", {
        "username": "admin",
        "password": "admin",
        "capture_login": True
    })

    if st.session_state.get("layout") == "wide":
        st.session_state.layout = "centered"
        st.rerun()

    # ─── Capture login toggle (auto‑save) ────────────────────────────────────
    current = creds.get("capture_login", False)
    capture = st.checkbox(
        "Capture login in OpenCanary log",
        value=current,
        key="capture_login"
    )
    if capture != current:
        creds["capture_login"] = capture
        settings["credentials"] = creds
        save_settings(settings)
        st.toast(f"capture_login set to {capture}")
        st.rerun()

    st.write("---")

    # ─── Password (in a form) ────────────────────────────────────────────────
    with st.form("password_form"):
        p1 = st.text_input("New password", type="password", key="p1")
        p2 = st.text_input("Confirm password", type="password", key="p2")
        col1, col2 = st.columns([3,1])
        with col2:
            submitted = st.form_submit_button("Update Password")
            if submitted:
                if p1 and p1 == p2:
                    creds["password"] = p1
                    settings["credentials"] = creds
                    save_settings(settings)
                    st.success("Password updated.")
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("Passwords must match")

    # ─── Backup management ─────────────────────────────────────────────────────
    os.makedirs(BACKUP_DIR, exist_ok=True)

    APP_DIR_TARGET_FILES = {"settings.conf", "rsyslog-opencanary.conf"}

    col1, col2 = st.columns([3,1])
    with col2:
        if st.button("Backup", use_container_width=True):
            ts = datetime.datetime.now().strftime("%Y%m%d-%H%M")
            backup_name = f"backup-{ts}.zip"
            backup_path = os.path.join(BACKUP_DIR, backup_name)
            with zipfile.ZipFile(backup_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                # add only the two target files under "app/"
                for root, dirs, files in os.walk("/app"):
                    if BACKUP_DIR in root:
                        continue
                    dirs[:] = [d for d in dirs if d not in ("__pycache__",) and not d.startswith(".")]
                    for f in files:
                        if f.startswith(".") or f not in APP_DIR_TARGET_FILES:
                            continue
                        full = os.path.join(root, f)
                        rel  = os.path.relpath(full, "/app")
                        arc  = os.path.join("app", rel)
                        zf.write(full, arc)

                # add opencanary config under "config/"
                zf.write(CONFIG_PATH, os.path.join("config", os.path.basename(CONFIG_PATH)))

                # add skins directory under "skins/"
                skin_dir = "/usr/local/lib/python3.10/dist-packages/opencanary/modules/data/http/skin"
                for root, dirs, files in os.walk(skin_dir):
                    dirs[:] = [d for d in dirs if d != "__pycache__"]
                    for f in files:
                        full = os.path.join(root, f)
                        rel  = os.path.relpath(full, skin_dir)
                        arc  = os.path.join("skins", rel)
                        zf.write(full, arc)

            st.success(f"Created backup: {backup_name}")
            time.sleep(2)
            st.rerun()

    with st.expander("Manage backups", expanded=False):
        backups = sorted(
            [f for f in os.listdir(BACKUP_DIR) if f.endswith(".zip")],
            reverse=True
        )
        for name in backups:
            col_name, col_dl, col_rs, col_del = st.columns([5,1,1,1])
            path = os.path.join(BACKUP_DIR, name)
            with col_name:
                st.write(name)
            # Download
            with col_dl:
                with open(path, "rb") as f:
                    st.download_button(
                        label="⬇️",
                        data=f,
                        file_name=name,
                        mime="application/zip",
                        key=f"dl_{name}"
                    )
            # Restore
            with col_rs:
                if st.button("⟳", key=f"rs_{name}", help=f"Restore backup '{name}'"):
                    with zipfile.ZipFile(path, "r") as zf:
                        for member in zf.namelist():
                            if member.startswith("backups/"):
                                continue
                            data = zf.read(member)
                            # map to correct target
                            if member.startswith("config/"):
                                dest = CONFIG_PATH
                            elif member.startswith("skins/"):
                                rel = member[len("skins/"):]
                                dest = os.path.join(
                                    "/usr/local/lib/python3.10/dist-packages/opencanary/modules/data/http/skin",
                                    rel
                                )
                            elif member.startswith("app/"):
                                rel = member[len("app/"):]
                                dest = os.path.join("/app", rel)
                            else:
                                continue
                            os.makedirs(os.path.dirname(dest), exist_ok=True)
                            with open(dest, "wb") as out:
                                out.write(data)
                    restart_opencanary()
                    st.success(f"Restored from {name}")
                    time.sleep(2)
                    st.rerun()
            # Delete
            with col_del:
                if st.button("❌", key=f"del_{name}", help=f"Delete backup '{name}'"):
                    os.remove(path)
                    st.success(f"Deleted backup: {name}")
                    time.sleep(2)
                    st.rerun()

        st.write("---")

        # Upload existing backup
        upload_col1, upload_col2 = st.columns([3,1])
        with upload_col1:
            up = st.file_uploader("Upload backup (.zip)", type="zip", key="upload_backup")
        with upload_col2:
            st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)
            if st.button("Upload", key="upload_backup_btn", use_container_width=True):
                if not up:
                    st.error("No file selected")
                else:
                    save_path = os.path.join(BACKUP_DIR, up.name)
                    with open(save_path, "wb") as f:
                        f.write(up.getbuffer())
                    st.success(f"Uploaded backup: {up.name}")
                    time.sleep(2)
                    st.rerun()

    # ─── Log file viewer/editor ─────────────────────────────────────────────────────

    st.write("---")

    LOG_PATH = "/var/tmp/opencanary.log"

    with st.expander("Opencanary log file", expanded=False):
        try:
            with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
                log_content = f.read()
        except FileNotFoundError:
            log_content = ""
            st.warning("Log file not found.")

        log_new = st.text_area(
            "Log file content",
            value=log_content,
            height=350,
            key="log_file_edit"
        )
        col1, col2 = st.columns([2, 1])
        with col2:
            if st.button("Save Log File", key="save_log_file", use_container_width=True):
                try:
                    with open(LOG_PATH, "w", encoding="utf-8") as f:
                        f.write(log_new)
                    st.success("Log file saved.")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to save log file: {e}")

    # ─── Footer ───────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; padding-top: 20px;">
        <p> Opencanary UI Project </p>
          <a href="https://github.com/chrisjbawden/opencanary-ui" target="_blank">
            <img src="https://cdn.jsdelivr.net/npm/@mdi/svg@6.9.96/svg/bird.svg" width="40"
                 style="filter: invert(29%) sepia(88%) saturate(6551%) hue-rotate(196deg)
                        brightness(92%) contrast(96%); display: block; margin: 0 auto 8px auto;"
                 alt="Bird icon"/>
            <div style="font-size: 0.9em;">View on GitHub</div>
          </a>
          <p>V1.0.1</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
