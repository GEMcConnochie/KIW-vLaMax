import os
import json
import base64
import gzip
import urllib.parse
from io import StringIO

from lactate_thresholds.process import clean_data
from lactate_thresholds.methods import interpolate
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

import lactate_thresholds.zones as zones
import logging

from lactate_thresholds.utils import get_lactate_interpolated, get_heart_rate_interpolated, get_intensity_interpolated

from lactate_thresholds.types import LogLog, BaseLinePlus, LactateThresholdResults

st.set_page_config(
    page_title="VO2 Max Estimation",
    layout="wide",
    initial_sidebar_state="auto",
)

# ─── Auth / secrets ───────────────────────────────────────────────
try:
    SHARED_PASSWORD = os.getenv("SHARED_PASSWORD", "")
    running_locally = False
except Exception:
    running_locally = True

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    SHARED_PASSWORD = os.getenv("SHARED_PASSWORD", "")




# ─── Language ─────────────────────────────────────────────────────
if "language" not in st.session_state:
    st.session_state.language = "English"
language = st.session_state.language

# ─── Authentication ───────────────────────────────────────────────
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False


page_labels = {
    "English": {"Calculator": "Calculator", "Instructions": "Instructions"},
    "Italiano": {"Calculator": "Calcolatore", "Instructions": "Istruzioni"},
}



# ─── Instruction page ─────────────────────────────────────────────

def instruct_pg():
    if language == "English":
        with st.expander("**About This Calculator**", expanded=True):
            st.markdown("""
                        """)

        with st.expander("**How to Perform Your Test**"):
            st.markdown("""
                       """)



        with st.expander("**References**"):
            st.markdown("""
            																   
																						
            """)

    else:
        with st.expander("**Informazioni sul Calcolatore**", expanded=True):
            st.markdown("""
            """)
        with st.expander("**Come Eseguire il Test**"):
            st.markdown("""
                    """)



        with st.expander("**Riferimenti**"):
            st.markdown("""
                        """)



# Auth gate
if not st.session_state.authenticated:
    pw = st.text_input(
        "Enter KIW subscriber password to edit input data:" if language == "English"
        else "Inserisci la password ricevuta per utilizzare questa app:",
        type="password", key="pw_input"
    )
    if pw == SHARED_PASSWORD:
        st.session_state.authenticated = True
        st.success("✅ Access granted" if language == "English" else "✅ Accesso consentito")
        st.rerun()
    elif pw:
        st.error("❌ Incorrect password" if language == "English" else "❌ Password errata")
# ─── Main layout ──────────────────────────────────────────────────
# Header row
hc1, hc2 = st.columns([1, 7])
with hc1:
    try:
        st.markdown(
            """
            <style>
              .logo-wrap {
                height: 180px;
                display: flex;
                align-items: center;
                justify-content: center;
              }
            </style>
            """,
            unsafe_allow_html=True,
        )
        st.image("logogreysq.png")
    except Exception:
        st.markdown("🩸")

with hc2:
    ca, cb = st.columns([3, 1])
    with ca:
        title = "VO2 max Calculator" if language == "English" else "Calcolatore VO2 max"
        st.markdown(
            f"""
            <style>
              @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&display=swap');
              .title-wrap {{
                height: 180px;
                display: flex;
                align-items: center;
                justify-content: left;
                padding-top: 20px;
              }}
              .app-title {{
                margin: 0;
                font-family: "Bebas Neue" !important;
                font-weight: 400;
                font-size:60px !important;
                letter-spacing: 0.05rem;
                line-height: 1;
                text-align: left;
              }}
            </style>
            <div class="title-wrap">
              <h1 class="app-title">{title}</h1>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with cb:
        lang_choice = st.radio("Language / Lingua", ("English", "Italiano"), horizontal=True)
        if lang_choice != st.session_state.language:
            st.session_state.language = lang_choice
            # Translate current internal page/sport to new language labels instead of deleting
            new_labels = MODE_LABELS[lang_choice]
            st.session_state.sport_radio = new_labels[st.session_state.sport_mode_internal]
            page_new_labels = page_labels[lang_choice]
            st.session_state.page_radio = page_new_labels[st.session_state.page_internal]
            # Preserve number inputs
            st.session_state.stg_len = st.session_state.get("stg_len", 3.0)
            st.session_state.start_intensity = st.session_state.get("start_intensity",
                                                                    MODE_DEFAULTS[st.session_state.sport_mode_internal][
                                                                        "start"])
            st.session_state.intensity_increment = st.session_state.get("intensity_increment", MODE_DEFAULTS[
                st.session_state.sport_mode_internal]["inc"])
            st.rerun()















# ─── Page toggle ──────────────────────────────────────────────────



page_options = [page_labels[language]["Calculator"], page_labels[language]["Instructions"]]
current_page_display = page_labels[language][st.session_state.page_internal]

# Ensure keyed widget value is valid for current language/options
if "page_radio" not in st.session_state or st.session_state.page_radio not in page_options:
    st.session_state.page_radio = current_page_display

page_display = st.radio(
    "",
    page_options,
    horizontal=True,
    key="page_radio",
)

page_reverse = {v: k for k, v in page_labels[language].items()}
st.session_state.page_internal = page_reverse[page_display]

if st.session_state.page_internal == "Instructions":
    instruct_pg()
    st.stop()


# ─── Footer ───────────────────────────────────────────────────────
import datetime
year = datetime.datetime.now().year
st.markdown("---")
fc1, fc2, fc3 = st.columns([4, 8, 3])
with fc1:
    try:
        st.image("logo_size_invert.jpg")
    except Exception:
        pass
    st.markdown(
        f"""<div style="text-align: center;">
        © {year} <b>Knowledge is Watt</b><br>
        {"All rights reserved." if language == "English" else "Tutti i diritti riservati."}
        </div>""",
        unsafe_allow_html=True
    )
with fc3:
    st.markdown(
        f"""<div style="text-align: center;">
        {"Developed by:" if language == "English" else "Sviluppato da:"}<br>
        <b>Dr. Grace McConnochie</b><br>
        <b>Dr. Gabriele Gallo</b><br>
        {"Questions/Issues?" if language == "English" else "Domande?"}
        <a href="mailto:contact@knowledgeiswatt.com">✉️</a>
        </div>""",
        unsafe_allow_html=True
    )
