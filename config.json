# app.py

import os
import json
import streamlit as st

from pages import scriptking_page, visualking_page, memoking_page  # 나중에 계속 추가

CONFIG_PATH = "config.json"

# ---------------------------
# config.json load / save
# ---------------------------
def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_config(data: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
