
import os
import datetime
import json
import base64
import gzip
import urllib.parse

import numpy as np
import pandas as pd
import plotly.graph_objects as go
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
except Exception:
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


language = st.session_state.language


# ─── Language Dictionaries ────────────────────────────────────────
page_labels = {
    "English": {"Calculator": "Calculator", "Instructions": "Instructions"},
    "Italiano": {"Calculator": "Calcolatore", "Instructions": "Istruzioni"},
}


def format_vlamax(value: float) -> str:
    return f"{value:.2f} mmol·L⁻¹·s⁻¹"


def snapshot_compress(data: dict) -> str:
    raw = json.dumps(data)
    compressed = gzip.compress(raw.encode("utf-8"))
    return "gz:" + base64.b64encode(compressed).decode("utf-8")


def snapshot_decompress(encoded: str) -> dict:
    decoded = urllib.parse.unquote(encoded)
    if decoded.startswith("gz:"):
        compressed = base64.b64decode(decoded[3:])
        raw = gzip.decompress(compressed).decode("utf-8")
    else:
        raw = base64.b64decode(decoded).decode("utf-8")
    return json.loads(raw)


def make_default_rider(name: str) -> dict:
    return {
        "name": name,
        "bl_pre": 1.0,
        "t_test": 10.0,
        "t_alac": 3.0,
        "post_lactate": {str(i): None for i in range(11)},
        "post_points": [{"time_s": i * 60, "lactate": None} for i in range(11)],
        "result": None,
    }


def init_riders_state():
    # Single-rider app state.
    if "rider" not in st.session_state and "riders" in st.session_state:
        # One-time migration from legacy multi-rider session state.
        legacy_riders = st.session_state.get("riders", {})
        legacy_active = st.session_state.get("active_rider_id")
        if isinstance(legacy_riders, dict) and legacy_riders:
            if legacy_active in legacy_riders:
                st.session_state.rider = legacy_riders[legacy_active]
            else:
                st.session_state.rider = next(iter(legacy_riders.values()))

    if "rider" not in st.session_state:
        st.session_state.rider = make_default_rider("Rider")
    if "snapshot_loaded" not in st.session_state:
        st.session_state.snapshot_loaded = False


def rider_post_df(rider: dict) -> pd.DataFrame:
    points = rider.get("post_points")
    if isinstance(points, list) and len(points) > 0:
        df = pd.DataFrame(points)
        if "time_s" not in df.columns:
            df["time_s"] = np.nan
        if "lactate" not in df.columns:
            df["lactate"] = np.nan
        df["time_s"] = pd.to_numeric(df["time_s"], errors="coerce")
        df["lactate"] = pd.to_numeric(df["lactate"], errors="coerce")
        df = df.sort_values("time_s", na_position="last").reset_index(drop=True)
        return df[["time_s", "lactate"]]

    # Legacy fallback: rebuild default time grid from old minute-binned dict.
    values = rider.get("post_lactate", {})
    return pd.DataFrame({"time_s": [i * 60 for i in range(11)], "lactate": [values.get(str(i), None) for i in range(11)]})


def post_df_to_points(df: pd.DataFrame) -> list:
    tmp = df.copy()
    tmp["time_s"] = pd.to_numeric(tmp["time_s"], errors="coerce")
    tmp["lactate"] = pd.to_numeric(tmp["lactate"], errors="coerce")
    tmp = tmp.dropna(subset=["time_s"]).sort_values("time_s").reset_index(drop=True)
    out = []
    for _, row in tmp.iterrows():
        out.append(
            {
                "time_s": float(row["time_s"]),
                "lactate": None if pd.isna(row["lactate"]) else float(row["lactate"]),
            }
        )
    return out


def post_df_to_dict(df: pd.DataFrame) -> dict:
    result = {str(i): None for i in range(11)}
    tmp = df.copy()
    tmp["time_s"] = pd.to_numeric(tmp["time_s"], errors="coerce")
    tmp["lactate"] = pd.to_numeric(tmp["lactate"], errors="coerce")
    for _, row in tmp.dropna(subset=["time_s"]).iterrows():
        m = int(round(float(row["time_s"]) / 60.0))
        if 0 <= m <= 10:
            result[str(m)] = float(row["lactate"]) if pd.notna(row["lactate"]) else None
    return result


def compute_peak_post(post_data):
    # New format: explicit time points with time_s.
    if isinstance(post_data, list):
        times = []
        vals = []
        for row in post_data:
            if not isinstance(row, dict):
                continue
            t = row.get("time_s", None)
            v = row.get("lactate", None)
            try:
                tf = float(t)
                vf = float(v)
            except Exception:
                continue
            if np.isfinite(tf) and np.isfinite(vf):
                times.append(tf)
                vals.append(vf)
        if not vals:
            return np.nan, np.nan
        idx = int(np.nanargmax(np.array(vals, dtype=float)))
        return float(vals[idx]), float(times[idx])




def generate_post_lactate_values(bl_pre: float) -> dict:
    """Create plausible post-test lactate samples from minute 0 to 10.

    Shape constraints:
    - rapid rise from baseline
    - early peak around 1-4 min
    - slow decline ending near 60-80% of peak by minute 10
    """
    base = max(float(bl_pre), 0.6)
    minutes = np.arange(11, dtype=float)

    peak_minute = np.random.randint(1, 5)  # 1..4 min
    peak_val = base + np.random.uniform(6.0, 10.0)
    end_frac = np.random.uniform(0.60, 0.80)
    end_val = max(base, peak_val * end_frac)

    values = np.zeros_like(minutes, dtype=float)

    # Fast rise to peak using normalized exponential kinetics.
    k_rise = np.random.uniform(1.4, 2.1)
    denom = 1.0 - np.exp(-k_rise * max(peak_minute, 1e-6))
    for i, t in enumerate(minutes):
        if t <= peak_minute:
            rise_frac = (1.0 - np.exp(-k_rise * t)) / max(denom, 1e-9)
            values[i] = base + (peak_val - base) * rise_frac
        else:
            # Very gradual post-peak decline, forced to end around 60-80% of peak.
            frac = (t - peak_minute) / max(10.0 - peak_minute, 1e-9)
            values[i] = peak_val - (peak_val - end_val) * (frac ** 1.5)

    # Small noise, then enforce non-increasing recovery after peak.
    values += np.random.normal(0, 0.08, size=values.size)
    peak_idx = int(peak_minute)
    tail = values[peak_idx:]
    values[peak_idx:] = np.minimum.accumulate(tail)
    values = np.clip(values, base, None)

    return {str(i): float(np.round(v, 2)) for i, v in enumerate(values)}


def build_lactate_time_plot(rider: dict, language: str):
    # Prefer explicit user-edited post points (time_s), fallback to legacy minute-binned dict.
    seconds = []
    lactates = []
    points = rider.get("post_points")
    if isinstance(points, list) and len(points) > 0:
        for row in points:
            if not isinstance(row, dict):
                continue
            t = row.get("time_s", None)
            v = row.get("lactate", None)
            try:
                tf = float(t)
                vf = float(v)
            except Exception:
                continue
            if np.isfinite(tf) and np.isfinite(vf):
                seconds.append(tf)
                lactates.append(vf)


    if seconds:
        order = np.argsort(np.array(seconds, dtype=float))
        seconds = [seconds[i] for i in order]
        lactates = [lactates[i] for i in order]

    fig = go.Figure()
    title_size = 16
    tick_size = 12
    legend_size = 12
    annotation_size = 12

    # Optional pre-test point shown slightly before time zero.
    pre_val = rider.get("bl_pre", None)
    if pre_val is not None:
        try:
            pre_val = float(pre_val)
            if np.isfinite(pre_val):
                fig.add_trace(
                    go.Scatter(
                        x=[-10.0],
                        y=[pre_val],
                        mode="markers",
                        name="Pre-test" if language == "English" else "Pre-test",
                        marker=dict(color="#111827", size=9, symbol="circle"),
                        hovertemplate=(
                            "Time: pre<br>Lactate: %{y:.2f} mmol/L<extra></extra>"
                            if language == "English"
                            else "Tempo: pre<br>Lattato: %{y:.2f} mmol/L<extra></extra>"
                        ),
                    )
                )
        except Exception:
            pass

    if seconds:
        x_arr = np.array(seconds, dtype=float)
        y_arr = np.array(lactates, dtype=float)

        # Use a spline-shaped line through measured points (better local fit than polynomial).
        if len(x_arr) >= 2 and np.unique(x_arr).size >= 2:
            fig.add_trace(
                go.Scatter(
                    x=x_arr,
                    y=y_arr,
                    mode="lines",
                    name="Smoothed curve" if language == "English" else "Curva smussata",
                    line=dict(color="#B2BEB5", width=2.5, shape="spline", smoothing=1.1, dash="dash"),
                    opacity=.5,
                    hovertemplate=(
                        "Time: %{x:.0f} s<br>Lactate: %{y:.2f} mmol/L<extra></extra>"
                        if language == "English"
                        else "Tempo: %{x:.0f} s<br>Lattato: %{y:.2f} mmol/L<extra></extra>"
                    ),
                )
            )

        fig.add_trace(
            go.Scatter(
                x=seconds,
                y=lactates,
                mode="markers",
                name="Post-test samples" if language == "English" else "Campioni post-test",
                marker=dict(color="#2563eb", size=8),
                hovertemplate=(
                    "Time: %{x:.0f} s<br>Lactate: %{y:.2f} mmol/L<extra></extra>"
                    if language == "English"
                    else "Tempo: %{x:.0f} s<br>Lattato: %{y:.2f} mmol/L<extra></extra>"
                ),
            )
        )

    # Exercise timepoint marker at immediate post (minute 0).
    fig.add_vline(
        x=0,
        line=dict(color="#ef4444", dash="dash", width=3),
        opacity=0.7,
        annotation_text=("Exercise end" if language == "English" else "Fine esercizio"),
        annotation_position="top left",
        annotation_font=dict(size=annotation_size),
    )

    if rider.get("result") and np.isfinite(rider["result"].get("bl_post_peak", np.nan)):
        fig.add_trace(
            go.Scatter(
                x=[float(rider["result"].get("peak_time_s", rider["result"].get("peak_minute", np.nan) * 60.0))],
                y=[float(rider["result"].get("bl_post_peak", np.nan))],
                mode="markers",
                name="Peak" if language == "English" else "Picco",
                marker=dict(color="#f59e0b", size=11, symbol="diamond"),
                hovertemplate=(
                    "Peak time: %{x:.0f} s<br>Lactate: %{y:.2f} mmol/L<extra></extra>"
                    if language == "English"
                    else "Tempo di picco: %{x:.0f} s<br>Lattato: %{y:.2f} mmol/L<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        template="plotly_white",
        margin=dict(t=40, b=40, l=60, r=20),
        xaxis=dict(
            title=("Time (s, post-test)" if language == "English" else "Tempo (s, post-test)"),
            range=[-30, 630],
            tickmode="array",
            tickvals=[0, 60, 120, 180, 240, 300, 360, 420, 480, 540, 600],
            ticktext=["0", "60", "120", "180", "240", "300", "360", "420", "480", "540", "600"],
            title_font=dict(size=title_size),
            tickfont=dict(size=tick_size),
        ),
        yaxis=dict(
            title=("Lactate (mmol/L)" if language == "English" else "Lattato (mmol/L)"),
            title_font=dict(size=title_size),
            tickfont=dict(size=tick_size),
        ),
        hovermode="closest",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=legend_size)),
    )
    return fig


init_riders_state()

if not st.session_state.snapshot_loaded:
    snap_param = st.query_params.get("snapshot")
    if snap_param:
        try:
            payload = snapshot_decompress(snap_param)
            # Backward compatibility: accept either direct rider payload or wrapped measurements payload.
            if "measurements" in payload:
                payload = json.loads(payload.get("measurements", "{}"))

            # New single-rider snapshot format.
            if isinstance(payload.get("rider"), dict):
                st.session_state.rider = payload["rider"]
            else:
                # Legacy multi-rider snapshot format: pick active rider if present, else first.
                loaded_riders = payload.get("riders", {})
                if isinstance(loaded_riders, dict) and loaded_riders:
                    active = payload.get("active_rider_id")
                    if active in loaded_riders:
                        st.session_state.rider = loaded_riders[active]
                    else:
                        st.session_state.rider = next(iter(loaded_riders.values()))
        except Exception as e:
            st.warning(f"Could not load snapshot: {e}")
    st.session_state.snapshot_loaded = True


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
                - **talac** = alactic time span - a fixed alactic time span of 3 seconds is recommended with a 8–12 s test duration.
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
                3. Ideally, use a **laboratory-grade lactate analyser**.
                4. Aim for **pre-test lactate ≤ 1.5 mmol/L**.
                5. Sample lactate every minute after the test to capture the peak.
                6. Use a **fixed cadence / isokinetic mode** when testing on an ergometer.
                7. Use **passive recovery** after the sprint.
                8. Include at least one **familiarization** trial.
                9. Ensure a **true maximal effort** with strong motivation.
                10. Consume suitable **nutrition and hydration** before testing.
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
                - **talac** = fase alattacida - si raccomanda un intervallo di tempo alattacido fisso di 3 secondi con una durata del test di 8-12 secondi.
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
                10. Prima del test, assicurarsi di assumere un'alimentazione e un'idratazione adeguate.
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

rider = st.session_state.rider

with st.form("vlamax_input_form", clear_on_submit=False):
        rider_name_entry = st.text_input(
            "Rider name" if language == "English" else "Nome atleta",
            value=rider.get("name", ""),
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            bl_pre = st.number_input(
                "Pre-test lactate (mmol/L)" if language == "English" else "Lattato pre-test (mmol/L)",
                min_value=0.0,
                max_value=25.0,
                value=float(rider.get("bl_pre", 1.0)),
                step=0.1,
                disabled=not st.session_state.authenticated,
            )
        with col2:
            t_test = st.number_input(
                "Total test duration (s)" if language == "English" else "Durata totale test (s)",
                min_value=1.0,
                max_value=60.0,
                value=float(rider.get("t_test", 10.0)),
                step=0.5,
                disabled=not st.session_state.authenticated,
            )
        with col3:
            t_alac = st.number_input(
                "Alactic time (s)" if language == "English" else "Tempo alattacido (s)",
                min_value=0.0,
                max_value=10.0,
                value=float(rider.get("t_alac", 3.0)),
                step=0.5,
                disabled=not st.session_state.authenticated,
            )

        st.markdown(
            "**Post-test lactate samples (immediately post + every minute to 10 min)**"
            if language == "English"
            else "**Campioni lattato post-test (immediato post + ogni minuto fino a 10 min)**"
        )
        post_df = rider_post_df(rider)
        edited_post_df = st.data_editor(
            post_df.reset_index(drop=True),
            num_rows="fixed",
            hide_index=False,
            use_container_width=True,
            disabled=not  st.session_state.authenticated,
            column_config={
                "time_s": st.column_config.NumberColumn(
                    "Seconds" if language == "English" else "Secondi",
                    step=60,
                    format="%d",
                ),
                "lactate": st.column_config.NumberColumn(
                    "Lactate (mmol/L)" if language == "English" else "Lattato (mmol/L)",
                    step=0.1,
                    format="%.2f",
                ),
            },
        )

        b1, b2 = st.columns(2)
        with b1:
            generate_pressed = st.form_submit_button(
                "Generate lactate values" if language == "English" else "Genera valori lattato",
                use_container_width=True,
                disabled=not st.session_state.authenticated,
            )
        with b2:
            calculate_pressed = st.form_submit_button(
                "Calculate" if language == "English" else "Calcola",
                use_container_width=True,
                disabled=not st.session_state.authenticated,
            )

if generate_pressed:
    rider_name = rider_name_entry.strip() or "Rider"
    rider["name"] = rider_name
    rider["bl_pre"] = float(bl_pre)
    rider["t_test"] = float(t_test)
    rider["t_alac"] = float(t_alac)
    rider["post_lactate"] = generate_post_lactate_values(float(bl_pre))
    rider["post_points"] = [{"time_s": i * 60, "lactate": rider["post_lactate"].get(str(i), None)} for i in range(11)]
    rider["result"] = None
    st.rerun()

if calculate_pressed:
    rider_name = rider_name_entry.strip() or "Rider"

    rider["name"] = rider_name
    rider["bl_pre"] = float(bl_pre)
    rider["t_test"] = float(t_test)
    rider["t_alac"] = float(t_alac)
    rider["post_lactate"] = post_df_to_dict(edited_post_df)
    rider["post_points"] = post_df_to_points(edited_post_df)

    peak_post, peak_time_s = compute_peak_post(rider.get("post_points", rider["post_lactate"]))
    if rider["t_test"] <= rider["t_alac"]:
        rider["result"] = None
        st.error(
            "Total test duration must be greater than alactic time." if language == "English"
            else "La durata totale del test deve essere maggiore del tempo alattacido."
        )
    elif not np.isfinite(peak_post):
        rider["result"] = None
        st.error(
            "Enter at least one valid post-test lactate value." if language == "English"
            else "Inserisci almeno un valore valido di lattato post-test."
        )
    elif peak_post < rider["bl_pre"]:
        rider["result"] = None
        st.error(
            "Peak post-test lactate should be greater than or equal to pre-test lactate." if language == "English"
            else "Il picco di lattato post-test deve essere maggiore o uguale al lattato pre-test."
        )
    else:
        vlamax = (peak_post - rider["bl_pre"]) / (rider["t_test"] - rider["t_alac"])
        rider["result"] = {
            "vlamax": float(vlamax),
            "bl_pre": float(rider["bl_pre"]),
            "bl_post_peak": float(peak_post),
            "peak_time_s": float(peak_time_s),
            "peak_minute": int(round(float(peak_time_s) / 60.0)),
            "t_test": float(rider["t_test"]),
            "t_alac": float(rider["t_alac"]),
        }


# ─── Results Display ──────────────────────────────────────────────
if rider.get("result"):
    result = rider["result"]
    st.markdown("---")
    st.markdown("## " + ("Result" if language == "English" else "Risultato"))

    rc1, rc2, rc3 = st.columns(3)
    with rc1:
        st.metric("vLaMax", format_vlamax(result["vlamax"]))
    with rc2:
        st.metric(
            "Peak post-test lactate" if language == "English" else "Picco lattato post-test",
            f"{result['bl_post_peak']:.2f} mmol/L",
        )
    with rc3:
        st.metric(
            "Peak time" if language == "English" else "Tempo di picco",
            f"{int(result.get('peak_time_s', result.get('peak_minute', 0) * 60))} s",
        )

st.markdown("### " + ("Lactate Curve" if language == "English" else "Curva del lattato"))
fig_time = build_lactate_time_plot(rider, language)
st.plotly_chart(fig_time, use_container_width=True)

st.markdown("---")
with st.expander("🔗 " + (" Save data" if language == "English" else "Salva data")):
    try:

        try:
            base_url = st.context.url.split("?")[0].rstrip("/")


        except Exception:
            base_url = "https://kiw-vlamax-calculator.up.railway.app/"

        snap_data = {
            "measurements": json.dumps(
                {
                    "rider": st.session_state.rider,
                }
            ),
            #   "lt1": lt1_val,
            #  "lt2": lt2_val,
            #  "zone_type": st.session_state.zone_type,
        }
        encoded = urllib.parse.quote(snapshot_compress(snap_data))
        snap_url = f"{base_url}/?snapshot={encoded}"
        st.code(snap_url)
        st.caption("Copy this URL to share your test results." if language == "English"
                   else "Copia questo URL per condividere i tuoi risultati.")
    except Exception as e:
        st.warning(f"Could not generate snapshot URL: {e}")


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
