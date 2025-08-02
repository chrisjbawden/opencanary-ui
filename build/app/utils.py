import os
import json
import subprocess
import time
from typing import Any, Optional

CONFIG_PATH    = "/etc/opencanaryd/opencanary.conf"
LOG_PATH       = "/var/tmp/opencanary.log"
BACKUP_DIR     = "/app/backups"
SETTINGS_FILE  = "/app/settings.conf"

def read_text(path: str) -> str:
    if not os.path.exists(path):
        return ""
    b = open(path, "rb").read()
    for enc in ("utf-8", "cp1252"):
        try:
            return b.decode(enc)
        except:
            pass
    return b.decode("utf-8", "ignore")

def load_json(path: str) -> dict:
    txt = read_text(path)
    if not txt.strip():
        return {}
    try:
        return json.loads(txt)
    except json.JSONDecodeError:
        return {}

def save_json(path: str, data: dict):
    # Atomic write for safety
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_path, path)

def restart_opencanary():
    subprocess.run(["pkill", "-f", "opencanaryd"], check=False)
    subprocess.Popen(["opencanaryd", "--start", "-f"])
    time.sleep(1)

# ——— Settings helpers —————————————————————————————

def load_settings() -> dict:
    return load_json(SETTINGS_FILE)

def save_settings(settings: dict):
    save_json(SETTINGS_FILE, settings)

# ——— New: Get, Set, and Delete helper functions for settings ———

def get_setting(key_path: str, default: Any = None) -> Any:
    """
    Retrieve a setting from settings.conf using dot notation (e.g., 'config.alert_method')
    """
    settings = load_settings()
    keys = key_path.split(".")
    current = settings
    for k in keys:
        if isinstance(current, dict) and k in current:
            current = current[k]
        else:
            return default
    return current

def set_setting(key_path: str, value: Any) -> None:
    """
    Set a value in settings.conf using dot notation (e.g., 'config.alert_method')
    """
    settings = load_settings()
    keys = key_path.split(".")
    current = settings
    for k in keys[:-1]:
        if k not in current or not isinstance(current[k], dict):
            current[k] = {}
        current = current[k]
    current[keys[-1]] = value
    save_settings(settings)

def delete_setting(key_path: str) -> None:
    """
    Delete a key from settings.conf using dot notation.
    """
    settings = load_settings()
    keys = key_path.split(".")
    current = settings
    for k in keys[:-1]:
        if k not in current or not isinstance(current[k], dict):
            return  # Key path doesn't exist
        current = current[k]
    current.pop(keys[-1], None)
    save_settings(settings)

# ——— Example usage ———
# set_setting('config.alert_method', 'webhook')
# alert_method = get_setting('config.alert_method', 'webhook')
# delete_setting('config.alert_method')

