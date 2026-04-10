import os
import datetime
import numpy as np
import pandas as pd
import streamlit as st

# ─── Page Configuration ────────────────────────────────────────────
st.set_page_config(
    page_title="VO2 Max Calculator",
    layout="wide",
    initial_sidebar_state="auto",
)

# ─── Auth / Secrets ────────────────────────────────────────────────
try:
    SHARED_PASSWORD = st.secrets["SHARED_PASSWORD"]
    running_locally = False
except Exception:
    running_locally = True
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass
    SHARED_PASSWORD = os.getenv("SHARED_PASSWORD", "")

# ─── Session State Initialization ──────────────────────────────────
if "language" not in st.session_state:
    st.session_state.language = "English"

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "power_input" not in st.session_state:
    st.session_state.power_input = 5.0

if "calculated_vo2max" not in st.session_state:
    st.session_state.calculated_vo2max = None

if "page_internal" not in st.session_state:
    st.session_state.page_internal = "Calculator"

language = st.session_state.language

# ─── Language Dictionaries ────────────────────────────────────────
page_labels = {
    "English": {"Calculator": "Calculator", "Instructions": "Instructions"},
    "Italiano": {"Calculator": "Calcolatore", "Instructions": "Istruzioni"},
}


# ─── Instructions Page ─────────────────────────────────────────────
def instruct_pg():
    if language == "English":
        with st.expander("**About This Calculator**", expanded=True):
            st.markdown("""
            This calculator estimates your **VO2max** (maximum oxygen consumption) using the **Sitko et al. (2022)** equation:

            ```
            VO2max (ml/min/kg) = 16.61 + 8.87 × 5-minute power output (W/kg)
            ```

            This equation was validated in a study of **46 road cyclists** (11 professionals) with VO2max ranging from ~45 to ~80 ml/min/kg.

            **Accuracy:** The equation can estimate VO2max within a **±3% error 95% of the time**.

            For example, if your 5-minute power is 6.8 W/kg:
            - VO2max = 16.61 + (8.87 × 6.8) = **76.9 ml/min/kg**
            - 95% Confidence Interval: **74.6 – 79.2 ml/min/kg**
            """)

        with st.expander("**How to Perform Your Test**"):
            st.markdown("""
            ### 5-Minute All-Out Power Test

            **Requirements:**
            - Calibrated power meter
            - Stationary bike or indoor trainer
            - 72 hours recovery from previous intense training

            **Protocol:**
            After a sufficient warm-up, perform a **5-minute all-out effort** and record the **average power (Watts)** for the full 5 minutes.


            """)

        with st.expander("**References**"):
            st.markdown("""
            **Primary Reference:**

            Sitko, S., Cirer-Sastre, R., Corbi, F., & López-Laval, I. (2022). 
            Five-Minute Power-Based Test to Predict Maximal Oxygen Consumption in Road Cycling. 
            *International Journal of Sports Physiology and Performance*, 17(1), 9–15.
            https://doi.org/10.1123/ijspp.2020-0923
            """)

    else:  # Italiano
        with st.expander("**Informazioni sul Calcolatore**", expanded=True):
            st.markdown("""
            Questo calcolatore stima il tuo **VO2max** (consumo massimo di ossigeno) utilizzando l'equazione **Sitko et al. (2022)**:

            ```
            VO2max (ml/min/kg) = 16.61 + 8.87 × potenza 5 minuti (W/kg)
            ```

            Questa equazione è stata validata su uno studio di **46 ciclisti su strada** (11 professionisti) con VO2max compresi tra ~45 e ~80 ml/min/kg.

            **Accuratezza:** L'equazione può stimare il VO2max con un errore di **±3% nel 95% dei casi**.

            Ad esempio, se la tua potenza di 5 minuti è 6.8 W/kg:
            - VO2max = 16.61 + (8.87 × 6.8) = **76.9 ml/min/kg**
            - Intervallo di confidenza al 95%: **74.6 – 79.2 ml/min/kg**
            """)

        with st.expander("**Come Eseguire il Test**"):
            st.markdown("""
            ### Test di Potenza di 5 Minuti

            **Requisiti:**
            - Misuratore di potenza calibrato
            - Bicicletta stazionaria o rulli da ciclismo
            - 72 ore di recupero da allenamenti intensi precedenti

            **Protocollo:**
            Dopo un riscaldamento sufficiente, esegui uno **sforzo massimale di 5 minuti** e registra la **potenza media (Watt)** per l'intera durata.


            """)

        with st.expander("**Riferimenti**"):
            st.markdown("""
            **Riferimento Principale:**

            Sitko, S., Cirer-Sastre, R., Corbi, F., & López-Laval, I. (2022). 
            Five-Minute Power-Based Test to Predict Maximal Oxygen Consumption in Road Cycling. 
            *International Journal of Sports Physiology and Performance*, 17(1), 9–15.
            https://doi.org/10.1123/ijspp.2020-0923
            """)


# ─── Authentication Gate ───────────────────────────────────────────
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
    st.stop()

# ─── Main Layout ──────────────────────────────────────────────────
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
        title = "VO2 Max Calculator" if language == "English" else "Calcolatore VO2 max"
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
                font-size: 60px !important;
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
            st.rerun()

# ─── Page Navigation ──────────────────────────────────────────────
page_options = [
    page_labels[language]["Calculator"],
    page_labels[language]["Instructions"]
]
current_page_display = page_labels[language][st.session_state.page_internal]

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

# ─── Calculator Page ──────────────────────────────────────────────
st.markdown("---")

st.markdown(
    "## " + ("5-Minute Power Output Test" if language == "English" else "Test di Potenza di 5 Minuti")
)

# Input method toggle
input_method_label = "Input Method" if language == "English" else "Metodo di Input"
input_method_options = (
    ("W/kg", "Watts") if language == "English"
    else ("W/kg", "Watt")
)

col_toggle_a, col_toggle_b = st.columns([1, 3])
with col_toggle_a:
    input_method = st.radio(
        input_method_label,
        input_method_options,
        horizontal=True,
        key="input_method_radio"
    )

# Input fields based on selected method
if input_method == "W/kg" or (language == "Italiano" and input_method == "W/kg"):
    # W/kg input method
    col1, _, col2 = st.columns([1.5,1.5, 1])

    with col1:
        power_input = st.number_input(
            "5-Minute Average Power (W/kg)" if language == "English" else "Potenza Media 5 Minuti (W/kg)",
            min_value=0.1,
            max_value=15.0,
            value=st.session_state.get("power_input_wkg", 5.0),
            step=0.1,
        )
        st.session_state["power_input_wkg"] = power_input
        calculated_wkg = power_input

    with col1:
        if st.button(
                "Calculate" if language == "English" else "Calcola",
                use_container_width=True,
        ):
            vo2max = 16.61 + 8.87 * calculated_wkg
            ci_lower = vo2max * 0.97
            ci_upper = vo2max * 1.03

            st.session_state.calculated_vo2max = {
                "vo2max": vo2max,
                "ci_lower": ci_lower,
                "ci_upper": ci_upper,
            }

else:  # Watts + Weight input method
    col1, col2, col3 = st.columns([1.5, 1.5, 1])

    with col1:
        watts = st.number_input(
            "5-Minute Average Power (Watts)" if language == "English" else "Potenza Media 5 Minuti (Watt)",
            min_value=10,
            max_value=2000,
            value=st.session_state.get("power_input_watts", 400),
            step=10,
        )
        st.session_state["power_input_watts"] = watts

    with col2:
        weight = st.number_input(
            "Body Weight (kg)" if language == "English" else "Peso Corporeo (kg)",
            min_value=30.0,
            max_value=150.0,
            value=st.session_state.get("body_weight", 70.0),
            step=0.1,
        )
        st.session_state["body_weight"] = weight

    with col1:
        if st.button(
                "Calculate" if language == "English" else "Calcola",
                use_container_width=True,
        ):
            calculated_wkg = watts / weight
            vo2max = 16.61 + 8.87 * calculated_wkg
            ci_lower = vo2max * 0.97
            ci_upper = vo2max * 1.03

            st.session_state.calculated_vo2max = {
                "vo2max": vo2max,
                "ci_lower": ci_lower,
                "ci_upper": ci_upper,
                "watts": watts,
                "weight": weight,
                "wkg": calculated_wkg,
            }

# ─── Results Display ──────────────────────────────────────────────
if st.session_state.calculated_vo2max:
    results = st.session_state.calculated_vo2max
    vo2max = results["vo2max"]
    ci_lower = results["ci_lower"]
    ci_upper = results["ci_upper"]

    st.markdown("---")
    st.markdown(
        "## " + ("Results" if language == "English" else "Risultati")
    )

    # Main metrics with enhanced styling
    m2, m1,m3 = st.columns([1, 1.2, 1])


    def metric_card(container, label, value):
        """Clean, professional metric card"""
        container.markdown(
            f"""
            <div style="
                background: #f8f9fa;
                border-left: 4px solid #2c3e50;
                padding: 24px 16px;
                border-radius: 6px;
                text-align: center;
            ">
                <p style="margin: 0; font-size: 12px; color: #666; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;">
                    {label}
                </p>
                <p style="margin: 12px 0 0 0; font-size: 44px; font-weight: 600; color: #1a1a1a; line-height: 1;">
                    {value:.1f}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )


    metrics = [
        ("VO2max (ml/min/kg)" if language == "English" else "VO2max (ml/min/kg)", vo2max),
        ("Lower 95% CI" if language == "English" else "IC Inferiore 95%", ci_lower),
        ("Upper 95% CI" if language == "English" else "IC Superiore 95%", ci_upper)
    ]

    for (container, label, value) in zip([m1, m2, m3], [m[0] for m in metrics], [m[1] for m in metrics]):
        metric_card(container, label, value)

# ─── Footer ───────────────────────────────────────────────────────
st.markdown("---")
year = datetime.datetime.now().year
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
