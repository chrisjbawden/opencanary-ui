import streamlit as st
import datetime
import streamlit.components.v1 as components
from utils import load_settings, LOG_PATH
from dashboard import render_dashboard
from config import render_config
from settings import render_settings
import socket
import json

# ─── Initialize session state ────────────────────────────────────────────────
if "page" not in st.session_state:
    st.session_state.page = "Dashboard"
if "auth" not in st.session_state:
    st.session_state.auth = False

# ─── Determine layout per-page/auth ─────────────────────────────────────────
auth = st.session_state.auth
page = st.session_state.page
layout = "centered" if (not auth or page == "Settings" or page == "OpenCanary Config") else "wide"

st.set_page_config(
    page_title="Portal",
    page_icon="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAAB"
              "CAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+khyoAAAAASUVORK5CYII=",
    layout=layout,
    initial_sidebar_state="expanded",
)

# ─── Inject CSS to hide toolbar and main menu ────────────────────────────────
components.html(
    """
    <style>
      .stToolbarActions { display: none !important; }
      #MainMenu { display: none !important; }
    </style>
    """,
    height=1,
)

# ─── Auto-refresh on 5 min inactivity (JS) ───────────────────────────────────
components.html(
    """
    <script>
    (function() {
        let timeout;
        function resetTimer() {
            clearTimeout(timeout);
            timeout = setTimeout(function() {
                window.location.reload();
            }, 5 * 60 * 1000);
        }
        window.onload = resetTimer;
        document.onmousemove = resetTimer;
        document.onmousedown = resetTimer;
        document.onclick = resetTimer;
        document.onscroll = resetTimer;
        document.onkeypress = resetTimer;

        setTimeout(function() {
            window.location.reload();
        }, 60 * 60 * 1000);
        
    })();
    </script>
    """,
    height=1,
)

# ─── Credentials & Login ─────────────────────────────────────────────────────
settings = load_settings()
creds = settings.get("credentials", {"username": "admin", "password": "admin", "capture_login": False})

if not st.session_state.auth:
    with st.form("login_form"):
        st.title("🔒 Login")
        user = st.text_input("Username", key="login_user")
        pwd = st.text_input("Password", type="password", key="login_pwd")
        if st.form_submit_button("Login"):
            success = (user == creds.get("username") and pwd == creds.get("password"))
            if creds.get("capture_login", False):
                local_dt = datetime.datetime.now()
                ts_local = local_dt.strftime("%Y-%m-%d %H:%M:%S.%f")
                status = "SUCCESS" if success else "FAILURE"
                entry = {
                    "local_time_adjusted": ts_local,
                    "logdata": {
                        "msg": {
                            "logdata": f"{status}: {user}"
                        }
                    },
                    "logtype": 888,
                    "node_id": socket.gethostname(),
                }
                with open(LOG_PATH, "a") as f:
                    f.write(json.dumps(entry) + "\n")

            if success:
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Invalid credentials")
    st.stop()

# ─── Sidebar Navigation ───────────────────────────────────────────────────────
icon_url = "https://cdn.jsdelivr.net/npm/@mdi/svg@6.9.96/svg/bird.svg"
st.sidebar.markdown(
    f'''
    <div style="text-align:center; margin-bottom:40px; padding-bottom:10px;">
    <p> O-UI </p>
      <img src="{icon_url}" width="60"
           style="filter: invert(29%) sepia(88%) saturate(6551%) hue-rotate(196deg)
                  brightness(92%) contrast(96%);" alt="Bird icon"/>
    </div>
    ''',
    unsafe_allow_html=True,
)

if st.sidebar.button("Dashboard", use_container_width=True, key="nav_dashboard"):
    st.session_state.page = "Dashboard"
if st.sidebar.button("OpenCanary Config", use_container_width=True, key="nav_config"):
    st.session_state.page = "OpenCanary Config"

st.sidebar.write("---")
if st.sidebar.button("Settings", use_container_width=True, key="nav_settings"):
    st.session_state.page = "Settings"

st.session_state.layout = layout

# ─── Render selected page ─────────────────────────────────────────────────────
if st.session_state.page == "Dashboard":
    render_dashboard()
elif st.session_state.page == "OpenCanary Config":
    render_config()
else:
    render_settings()
