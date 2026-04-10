
import os
import datetime
import streamlit as st

# ─── Page Configuration ────────────────────────────────────────────
st.set_page_config(
    page_title="vLaMax Calculator",
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

if "page_internal" not in st.session_state:
    st.session_state.page_internal = "Calculator"

if "calculated_vlamax" not in st.session_state:
    st.session_state.calculated_vlamax = None

language = st.session_state.language


# ─── Language Dictionaries ────────────────────────────────────────
page_labels = {
    "English": {"Calculator": "Calculator", "Instructions": "Instructions"},
    "Italiano": {"Calculator": "Calcolatore", "Instructions": "Istruzioni"},
}


def format_vlamax(value: float) -> str:
    return f"{value:.2f} mmol·L⁻¹·s⁻¹"


# ─── Instructions Page ─────────────────────────────────────────────
def instruct_pg():
    if language == "English":
        with st.expander("**About This Calculator**", expanded=True):
            st.markdown(
                """
                This app estimates **vLaMax** — the maximum rate of blood lactate accumulation — using a simple pre/post lactate approach.

                **Formula:**
                ```
                vLaMax = (BLamaxpost - BLapre) / (ttest - talac)
                ```

                where:
                - **BLamaxpost** = highest blood lactate concentration after the test
                - **BLapre** = blood lactate concentration before the test
                - **ttest** = total test duration
                - **talac** = alactic time span
                """
            )

        with st.expander("**How to Perform Your Test**"):
            st.markdown(
                """
                After a sufficient warm-up, perform an **8–12 second all-out sprint** under standardized conditions.

                Collect blood lactate before the effort and then sample repeatedly after the test to identify the **highest post-test lactate value**.
                """
            )

        with st.expander("**10 Practical Recommendations**"):
            st.markdown(
                """
                1. Use an **8–12 s** all-out test.
                2. Keep the **alactic time** fixed at **3 s** when possible.
                3. Prefer a **laboratory-grade lactate analyser**.
                4. Aim for **pre-test lactate ≤ 1.5 mmol/L**.
                5. Sample lactate every minute after the test and capture the peak.
                6. Use a **fixed cadence / isokinetic mode** when testing on an ergometer.
                7. Use **passive recovery** after the sprint.
                8. Include at least one **familiarization** trial.
                9. Ensure a **true maximal effort** with strong motivation.
                10. Standardize **nutrition and hydration** before testing.
                """
            )

        with st.expander("**Reference**"):
            st.markdown(
                """
                Langley, J., Haase, R., Nitzsche, N., & Porter, M. (2025). *Methodological Approaches in Testing Maximal Lactate Accumulation Rate - νLamax: A Systematic Review*. Journal of Science and Cycling, 14(1), 9.
                https://doi.org/10.28985/1425.jsc.09
                """
            )
    else:
        with st.expander("**Informazioni sul Calcolatore**", expanded=True):
            st.markdown(
                """
                Questa app stima la **vLaMax** — la massima velocità di accumulo del lattato nel sangue — usando un approccio semplice pre/post-test.

                **Formula:**
                ```
                vLaMax = (BLamaxpost - BLapre) / (ttest - talac)
                ```

                dove:
                - **BLamaxpost** = massimo lattato ematico dopo il test
                - **BLapre** = lattato ematico prima del test
                - **ttest** = durata totale del test
                - **talac** = fase alattacida
                """
            )

        with st.expander("**Come Eseguire il Test**"):
            st.markdown(
                """
                Dopo un riscaldamento sufficiente, esegui uno **sprint massimale di 8–12 secondi** in condizioni standardizzate.

                Rileva il lattato prima dello sforzo e poi campiona più volte dopo il test per individuare il **valore massimo di lattato post-test**.
                """
            )

        with st.expander("**10 Raccomandazioni Pratiche**"):
            st.markdown(
                """
                1. Usa un test massimale di **8–12 s**.
                2. Mantieni il **tempo alattacido** fisso a **3 s** quando possibile.
                3. Preferisci un **analizzatore del lattato di laboratorio**.
                4. Punta a un **lattato pre-test ≤ 1.5 mmol/L**.
                5. Campiona il lattato ogni minuto dopo il test per cogliere il picco.
                6. Usa una **cadenza fissa / modalità isocinetica** su ergometro.
                7. Usa **recupero passivo** dopo lo sprint.
                8. Prevedi almeno una prova di **familiarizzazione**.
                9. Richiedi uno **sforzo davvero massimale**.
                10. Standardizza **nutrizione e idratazione** prima del test.
                """
            )

        with st.expander("**Riferimento**"):
            st.markdown(
                """
                Langley, J., Haase, R., Nitzsche, N., & Porter, M. (2025). *Methodological Approaches in Testing Maximal Lactate Accumulation Rate - νLamax: A Systematic Review*. Journal of Science and Cycling, 14(1), 9.
                https://doi.org/10.28985/1425.jsc.09
                """
            )


# ─── Authentication Gate ───────────────────────────────────────────
if not st.session_state.authenticated:
    pw = st.text_input(
        "Enter KIW subscriber password to edit input data:" if language == "English"
        else "Inserisci la password ricevuta per utilizzare questa app:",
        type="password",
        key="pw_input",
    )
    if pw == SHARED_PASSWORD:
        st.session_state.authenticated = True
        st.success("✅ Access granted" if language == "English" else "✅ Accesso consentito")
        st.rerun()
    elif pw:
        st.error("❌ Incorrect password" if language == "English" else "❌ Password errata")
    st.stop()


# ─── Main Layout ──────────────────────────────────────────────────
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
        title = "vLaMax Calculator" if language == "English" else "Calcolatore vLaMax"
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
page_options = [page_labels[language]["Calculator"], page_labels[language]["Instructions"]]
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
st.markdown("## " + ("vLaMax Calculator" if language == "English" else "Calcolatore vLaMax"))

st.caption(
    "Estimate vLaMax from pre/post lactate values and test timing." if language == "English"
    else "Stima la vLaMax dai valori di lattato pre/post test e dai tempi del test."
)

col1, col2, col3, col4 = st.columns(4)

with col1:
    bl_pre = st.number_input(
        "Pre-test lactate (mmol/L)" if language == "English" else "Lattato pre-test (mmol/L)",
        min_value=0.0,
        max_value=25.0,
        value=float(st.session_state.get("bl_pre", 1.0)),
        step=0.1,
        disabled=not st.session_state.authenticated,
    )
    st.session_state.bl_pre = bl_pre

with col2:
    bl_post = st.number_input(
        "Peak post-test lactate (mmol/L)" if language == "English" else "Picco lattato post-test (mmol/L)",
        min_value=0.0,
        max_value=30.0,
        value=float(st.session_state.get("bl_post", 12.0)),
        step=0.1,
        disabled=not st.session_state.authenticated,
    )
    st.session_state.bl_post = bl_post

with col3:
    t_test = st.number_input(
        "Total test duration (s)" if language == "English" else "Durata totale test (s)",
        min_value=1.0,
        max_value=60.0,
        value=float(st.session_state.get("t_test", 10.0)),
        step=0.5,
        disabled=not st.session_state.authenticated,
    )
    st.session_state.t_test = t_test

with col4:
    t_alac = st.number_input(
        "Alactic time (s)" if language == "English" else "Tempo alattacido (s)",
        min_value=0.0,
        max_value=10.0,
        value=float(st.session_state.get("t_alac", 3.0)),
        step=0.5,
        disabled=not st.session_state.authenticated,
    )
    st.session_state.t_alac = t_alac

calc_col, note_col = st.columns([1, 3])
with calc_col:
    calculate_pressed = st.button(
        "Calculate" if language == "English" else "Calcola",
        use_container_width=True,
        disabled=not st.session_state.authenticated,
    )

if calculate_pressed:
    if t_test <= t_alac:
        st.session_state.calculated_vlamax = None
        st.error(
            "Total test duration must be greater than alactic time." if language == "English"
            else "La durata totale del test deve essere maggiore del tempo alattacido."
        )
    elif bl_post < bl_pre:
        st.session_state.calculated_vlamax = None
        st.error(
            "Post-test lactate should be greater than or equal to pre-test lactate." if language == "English"
            else "Il lattato post-test deve essere maggiore o uguale al lattato pre-test."
        )
    else:
        vlamax = (bl_post - bl_pre) / (t_test - t_alac)
        st.session_state.calculated_vlamax = {
            "vlamax": vlamax,
            "bl_pre": bl_pre,
            "bl_post": bl_post,
            "t_test": t_test,
            "t_alac": t_alac,
        }


# ─── Results Display ──────────────────────────────────────────────
if st.session_state.calculated_vlamax:
    result = st.session_state.calculated_vlamax
    vlamax = result["vlamax"]

    st.markdown("---")
    st.markdown("## " + ("Result" if language == "English" else "Risultato"))

    # st.markdown(
    #     f"""
    #     <div style="
    #         background: #f8fafc;
    #         border: 1px solid rgba(15, 23, 42, 0.10);
    #         border-radius: 16px;
    #         padding: 18px 20px;
    #         margin-bottom: 14px;
    #     ">
    #         <div style="color: #64748b; font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em;">
    #             {'Formula' if language == 'English' else 'Formula'}
    #         </div>
    #         <div style="margin-top: 8px; font-size: 1.05rem; color: #0f172a;">
    #             ( {result['bl_post']:.1f} - {result['bl_pre']:.1f} ) / ( {result['t_test']:.1f} - {result['t_alac']:.1f} )
    #         </div>
    #     </div>
    #     """,
    #     unsafe_allow_html=True,
    # )

    c1, c2 = st.columns([1.3, 2])
    with c1:
        st.markdown(
            f"""
            <div style="
                background: #ffffff;
                border: 1px solid rgba(15, 23, 42, 0.10);
                border-radius: 18px;
                padding: 18px 20px;
                box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05);
            ">
                <div style="color:#64748b;font-size:0.85rem;font-weight:600;text-transform:uppercase;letter-spacing:0.04em;">
                    {'vLaMax' if language == 'English' else 'vLaMax'}
                </div>
                <div style="margin-top:10px;font-size:2.3rem;font-weight:700;color:#0f172a;line-height:1;">
                    {format_vlamax(vlamax)}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # with c2:
    #     st.markdown(
    #         f"""
    #         <div style="
    #             background: #ffffff;
    #             border: 1px solid rgba(15, 23, 42, 0.10);
    #             border-radius: 18px;
    #             padding: 18px 20px;
    #             box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05);
    #         ">
    #             <div style="color:#64748b;font-size:0.85rem;font-weight:600;text-transform:uppercase;letter-spacing:0.04em;">
    #                 {'Inputs used' if language == 'English' else 'Valori usati'}
    #             </div>
    #             <div style="margin-top:10px;color:#0f172a;font-size:0.98rem;line-height:1.8;">
    #                 BLapre = {result['bl_pre']:.1f} mmol/L<br>
    #                 BLamaxpost = {result['bl_post']:.1f} mmol/L<br>
    #                 ttest = {result['t_test']:.1f} s<br>
    #                 talac = {result['t_alac']:.1f} s
    #             </div>
    #         </div>
    #         """,
    #         unsafe_allow_html=True,
    #     )


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
        unsafe_allow_html=True,
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
        unsafe_allow_html=True,
    )
