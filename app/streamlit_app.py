import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import shap
import base64

from src.inference import fetch_current_features, fetch_display_history, load_latest_model, predict_forecast

st.set_page_config(page_title="RuFus · Pearls AQI Predictor", page_icon="🍃", layout="wide")

# --- Theme constants (single source of truth — every color below pulls from here) ---
TEXT = "#F4F7FB"
TEXT_SOFT = "#C9D1E3"
ACCENT = "#F7B955"
ACCENT_2 = "#68D7C6"
BG = "#07101D"
CARD_BG = "rgba(12, 20, 35, 0.80)"
CARD_BG_2 = "rgba(18, 28, 48, 0.88)"
BORDER = "rgba(147, 168, 203, 0.18)"
MUTED = "#93A0B8"
GOOD_FG, GOOD_BG = "#52E0C4", "rgba(22, 78, 67, 0.78)"
BAD_FG, BAD_BG = "#FF8A8A", "rgba(92, 28, 41, 0.78)"
SURFACE_SHADOW = "0 24px 80px rgba(2, 6, 23, 0.40)"


def get_background_svg():
    svg = """<svg width="1600" height="1200" viewBox="0 0 1600 1200" xmlns="http://www.w3.org/2000/svg">
      <g stroke="#F59E0B" stroke-width="1.4" fill="none" opacity="0.12">
        <path d="M -50 150 C 300 50, 500 250, 850 150 S 1400 50, 1700 180"/>
        <path d="M -50 350 C 250 450, 550 250, 900 380 S 1450 480, 1700 380"/>
        <path d="M -50 550 C 350 650, 600 400, 950 550 S 1500 650, 1700 550"/>
        <path d="M -50 750 C 300 650, 650 900, 1000 750 S 1400 650, 1700 780"/>
        <path d="M -50 950 C 350 1050, 600 800, 950 950 S 1500 1050, 1700 950"/>
      </g>
      <g stroke="#2DD4BF" stroke-width="1" fill="none" opacity="0.08">
        <path d="M -50 250 C 300 150, 600 350, 950 250 S 1450 150, 1700 280"/>
        <path d="M -50 650 C 300 550, 650 750, 1000 650 S 1450 550, 1700 680"/>
      </g>
      <g fill="#F59E0B" opacity="0.05">
        <ellipse cx="250" cy="200" rx="220" ry="160"/>
        <ellipse cx="1300" cy="850" rx="260" ry="180"/>
        <ellipse cx="900" cy="500" rx="180" ry="130"/>
      </g>
    </svg>"""
    encoded = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
    return f"data:image/svg+xml;base64,{encoded}"


BG_SVG = get_background_svg()

st.markdown(
    f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600;700&display=swap');
:root {{ color-scheme: dark; }}
html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; color: {TEXT}; }}
h1, h2, h3, .hero-title, .section-title {{ font-family: 'Space Grotesk', sans-serif; }}

html, body {{ background: {BG}; }}
body::before {{
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    background:
        radial-gradient(circle at 12% 20%, rgba(247, 185, 85, 0.14), transparent 26%),
        radial-gradient(circle at 82% 14%, rgba(104, 215, 198, 0.12), transparent 24%),
        radial-gradient(circle at 72% 82%, rgba(109, 140, 255, 0.08), transparent 28%),
        linear-gradient(180deg, rgba(255, 255, 255, 0.03), transparent 28%);
    z-index: 0;
}}

.stApp {{
    background-color: {BG};
    background-image: url("{BG_SVG}");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}}

[data-testid="stHeader"], [data-testid="stToolbar"], footer {{ visibility: hidden; height: 0; }}
.block-container {{
    max-width: 1360px;
    padding-top: 2.1rem;
    padding-bottom: 2.5rem;
}}

.eyebrow {{
    display: inline-flex;
    align-items: center;
    gap: 0.55rem;
    padding: 0.45rem 0.9rem;
    border-radius: 999px;
    border: 1px solid {BORDER};
    background: rgba(255, 255, 255, 0.03);
    color: {TEXT_SOFT};
    font-size: 0.82rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}}

.title-wrap {{ margin-top: 0.95rem; }}
.hero-title {{ font-size: clamp(2.4rem, 4vw, 4.1rem); font-weight: 700; color: {TEXT}; margin: 0; line-height: 1.02; }}
.hero-subtitle {{ color: {TEXT_SOFT}; font-size: 1.02rem; max-width: 54rem; margin-top: 0.85rem; line-height: 1.6; }}

.card {{
    background: linear-gradient(180deg, {CARD_BG}, {CARD_BG_2});
    border: 1px solid {BORDER};
    border-radius: 22px;
    padding: 20px;
    height: 100%;
    box-shadow: {SURFACE_SHADOW};
    backdrop-filter: blur(18px);
    -webkit-backdrop-filter: blur(18px);
}}

.soft-panel {{
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.035), rgba(255, 255, 255, 0.018));
    border: 1px solid {BORDER};
    border-radius: 22px;
    padding: 22px;
    box-shadow: {SURFACE_SHADOW};
    backdrop-filter: blur(18px);
    -webkit-backdrop-filter: blur(18px);
}}

.pill {{
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.42rem 0.9rem;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 700;
    letter-spacing: 0.02em;
    border: 1px solid rgba(255, 255, 255, 0.10);
}}

.section-title {{ font-weight: 700; color: {TEXT}; font-size: 1.25rem; margin: 0 0 0.7rem; letter-spacing: -0.01em; }}
.section-kicker {{ color: {MUTED}; font-size: 0.83rem; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.35rem; }}
.big-number {{ font-size: clamp(2.4rem, 4vw, 3.5rem); font-weight: 700; color: {ACCENT}; line-height: 1; letter-spacing: -0.04em; }}
.label-muted {{ color: {MUTED}; font-size: 0.84rem; }}
.value-large {{ font-size: 1.55rem; font-weight: 700; color: {TEXT}; letter-spacing: -0.02em; }}
.metric-value {{ font-size: 1.6rem; font-weight: 700; color: {TEXT}; line-height: 1.05; }}
.metric-label {{ color: {TEXT_SOFT}; font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.08em; }}
.metric-meta {{ color: {MUTED}; font-size: 0.82rem; margin-top: 0.3rem; }}
.chart-card {{ padding: 18px 18px 8px; }}
</style>
""",
    unsafe_allow_html=True,
)

AQI_ZONES = [
    (0, 50, "Good", "#2DD4BF", "#0F3D38"),
    (50, 100, "Moderate", "#FBBF24", "#3D2E0A"),
    (100, 150, "Unhealthy for Sensitive Groups", "#FB923C", "#3D230A"),
    (150, 200, "Unhealthy", "#F87171", "#3D1414"),
    (200, 300, "Very Unhealthy", "#C084FC", "#2E1440"),
    (300, 500, "Hazardous", "#EF4444", "#3D0F13"),
]

def aqi_category(aqi):
    for low, high, label, fg, bg in AQI_ZONES:
        if low <= aqi < high:
            return label, fg, bg
    return AQI_ZONES[-1][2], AQI_ZONES[-1][3], AQI_ZONES[-1][4]

def pill(label, fg, bg):
    return f'<span class="pill" style="color:{fg}; background:{bg};">{label}</span>'


def style_chart(fig, height):
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": MUTED},
        showlegend=False,
        yaxis=dict(gridcolor=BORDER, zeroline=False),
        xaxis=dict(gridcolor="rgba(0,0,0,0)", showgrid=False),
    )
    return fig


@st.cache_resource
def get_model():
    return load_latest_model()

@st.cache_data(ttl=3600)
def get_current_features():
    return fetch_current_features()

@st.cache_data(ttl=3600)
def get_history():
    return fetch_display_history()

@st.cache_resource
def get_explainers(_models):
    return {h: shap.TreeExplainer(_models[h]) for h in ["day1", "day2", "day3"]}


# --- Header ---
header_left, header_right = st.columns([3.2, 1.1])
with header_left:
    st.markdown('<div class="eyebrow">Live AQI intelligence</div>', unsafe_allow_html=True)
    st.markdown(
        '''
        <div class="title-wrap">
            <div class="hero-title">Rufus</div>
            <div class="hero-subtitle">A modern forecast dashboard for Sukkur air quality, combining live conditions, 3-day predictions, and model explanations in one calm, readable view.</div>
        </div>
        ''',
        unsafe_allow_html=True,
    )
with header_right:
    st.markdown(
        f'''
        <div class="soft-panel" style="text-align:right;">
            <div class="metric-label">Last refresh</div>
            <div class="metric-value" style="font-size:1.1rem;">{pd.Timestamp.now().strftime("%b %d, %Y")}</div>
            <div class="metric-meta">{pd.Timestamp.now().strftime("%I:%M %p")}</div>
        </div>
        ''',
        unsafe_allow_html=True,
    )

st.write("")

with st.spinner("Fetching latest conditions..."):
    models, feature_cols, metrics, model_version = get_model()
    feature_row = get_current_features()
    history_df = get_history()
    forecast = predict_forecast(feature_row, models, feature_cols)
    explainers = get_explainers(models)

# --- Alerts ---
max_forecast = max(forecast["day1"], forecast["day2"], forecast["day3"])
if max_forecast > 200:
    st.error("⚠️ Hazardous air quality expected in the next 3 days.")
elif max_forecast > 150:
    st.warning("⚠️ Unhealthy air quality expected in the next 3 days.")

# --- Hero: gauge + current AQI ---
st.markdown('<div class="section-kicker">Overview</div><div class="section-title">Sukkur Air Quality</div>', unsafe_allow_html=True)

current_aqi = forecast["current_aqi"]
label, fg, bg = aqi_category(current_aqi)
aqi_24h_ago = history_df.iloc[0]["us_aqi"] if len(history_df) > 24 else current_aqi
delta = current_aqi - aqi_24h_ago
delta_color = GOOD_FG if delta < 0 else BAD_FG
delta_arrow = "▼" if delta < 0 else "▲"
trend_meta = "Improving" if delta < 0 else "Worsening"

with st.container():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    gauge_col, status_col = st.columns([1.15, 0.85])
    with gauge_col:
        fig = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=current_aqi,
                number={"font": {"size": 54, "color": ACCENT}},
                gauge={
                    "axis": {"range": [0, 300], "tickcolor": MUTED, "tickwidth": 1.2},
                    "bar": {"color": ACCENT, "thickness": 0.34},
                    "bgcolor": "rgba(0,0,0,0)",
                    "borderwidth": 0,
                    "steps": [
                        {"range": [0, 50], "color": "rgba(82, 224, 196, 0.16)"},
                        {"range": [50, 100], "color": "rgba(247, 185, 85, 0.16)"},
                        {"range": [100, 150], "color": "rgba(255, 153, 102, 0.16)"},
                        {"range": [150, 200], "color": "rgba(255, 138, 138, 0.16)"},
                        {"range": [200, 300], "color": "rgba(193, 108, 255, 0.16)"},
                    ],
                },
            )
        )
        fig.update_layout(
            height=300,
            margin=dict(l=10, r=10, t=18, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={"color": TEXT},
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)
    with status_col:
        st.markdown('<div class="section-kicker">Current state</div><div class="section-title">Current Air Quality</div>', unsafe_allow_html=True)
        st.markdown(pill(label, fg, bg), unsafe_allow_html=True)
        st.write("")
        st.markdown(
            f'''
            <div class="metric-value" style="color:{delta_color}; font-size:1.45rem; margin-top:0.2rem;">{delta_arrow} {abs(delta):.0f} vs 24h ago</div>
            <div class="metric-meta">{trend_meta} since yesterday</div>
            ''',
            unsafe_allow_html=True,
        )
        st.markdown(f'<div class="metric-meta">Updated {feature_row["time"].iloc[0]}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.write("")

# --- Current Pollutants ---
st.markdown('<div class="section-kicker">Live readings</div><div class="section-title">Current Pollutants</div>', unsafe_allow_html=True)
pollutants = [("PM2.5", "pm2_5"), ("PM10", "pm10"), ("O3", "ozone"),
              ("NO2", "nitrogen_dioxide"), ("SO2", "sulphur_dioxide"), ("CO", "carbon_monoxide")]
cols = st.columns(6)
for index, (pollutant_label, column_name) in enumerate(pollutants):
    with cols[index]:
        st.markdown(f'<div class="card"><div class="metric-label">{pollutant_label}</div><div class="metric-value">{feature_row[column_name].iloc[0]:.1f}</div></div>', unsafe_allow_html=True)

st.write("")

# --- 24h trend + current conditions ---
tcol, ccol = st.columns([2, 1])
with tcol:
    st.markdown('<div class="section-kicker">History</div><div class="section-title">24-Hour AQI Trend</div>', unsafe_allow_html=True)
    recent = history_df.tail(24)
    fig = go.Figure(go.Scatter(
        x=recent["time"], y=recent["us_aqi"], mode="lines",
        line=dict(color=ACCENT, width=3, shape="spline"), fill="tozeroy", fillcolor="rgba(247, 185, 85, 0.10)",
    ))
    st.plotly_chart(style_chart(fig, 330), use_container_width=True)

with ccol:
    st.markdown('<div class="section-kicker">Weather context</div><div class="section-title">Current Conditions</div>', unsafe_allow_html=True)
    conditions = [("Temperature", f'{feature_row["temperature_2m"].iloc[0]:.1f} °C'),
                  ("Humidity", f'{feature_row["relative_humidity_2m"].iloc[0]:.0f}%'),
                  ("Pressure", f'{feature_row["surface_pressure"].iloc[0]:.1f} hPa')]
    for condition_label, condition_value in conditions:
        st.markdown(f'<div class="card" style="margin-bottom:12px;"><div class="metric-label">{condition_label}</div><div class="metric-value">{condition_value}</div></div>', unsafe_allow_html=True)

st.write("")

# --- 3-Day Forecast ---
st.markdown('<div class="section-kicker">Forecast</div><div class="section-title">3-Day Forecast</div>', unsafe_allow_html=True)
cols = st.columns(3)
for index, horizon in enumerate(["day1", "day2", "day3"]):
    label, fg, bg = aqi_category(forecast[horizon])
    rmse = metrics.get(f"{horizon}_rmse", None)
    rmse_text = f"± {rmse:.2f}" if isinstance(rmse, (int, float)) else "n/a"
    with cols[index]:
        st.markdown(f"""
        <div class="card">
            <div class="metric-label">+{index + 1} day</div>
            {pill(label, fg, bg)}
            <div style="height: 0.8rem;"></div>
            <div class="big-number">{forecast[horizon]:.1f}</div>
            <div class="metric-meta" style="margin-top:0.55rem;">Model RMSE: {rmse_text}</div>
        </div>
        """, unsafe_allow_html=True)

st.write("")
st.markdown('<div class="section-kicker">Trajectory</div><div class="section-title">Predicted AQI Trend</div>', unsafe_allow_html=True)
days = ["Today", "+1 day", "+2 days", "+3 days"]
values = [current_aqi, forecast["day1"], forecast["day2"], forecast["day3"]]
fig = go.Figure(go.Scatter(x=days, y=values, mode="lines+markers", line=dict(color=ACCENT, width=2.5), marker=dict(size=8, color=ACCENT)))
st.plotly_chart(style_chart(fig, 310), use_container_width=True)

st.write("")

# --- Why This Prediction (live SHAP) ---
st.markdown('<div class="section-kicker">Explainability</div><div class="section-title">Why This Prediction</div>', unsafe_allow_html=True)
horizon_label = st.segmented_control("Horizon", options=["+1 day", "+2 days", "+3 days"], default="+1 day", label_visibility="collapsed")
horizon_map = {"+1 day": "day1", "+2 days": "day2", "+3 days": "day3"}
selected = horizon_map[horizon_label]

X_current = feature_row[feature_cols]
sv = explainers[selected](X_current)
contributions = pd.Series(sv.values[0], index=feature_cols)
top_increase = contributions.idxmax()
top_decrease = contributions.idxmin()

c1, c2 = st.columns(2)
with c1:
    st.markdown(f"""<div class="card"><div class="metric-label">Top increase</div>
    <div class="metric-value">{top_increase}</div>
    <span class="pill" style="color:{BAD_FG}; background:{BAD_BG};">↑ +{contributions[top_increase]:.2f}</span></div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""<div class="card"><div class="metric-label">Top decrease</div>
    <div class="metric-value">{top_decrease}</div>
    <span class="pill" style="color:{GOOD_FG}; background:{GOOD_BG};">↓ {contributions[top_decrease]:.2f}</span></div>""", unsafe_allow_html=True)

st.write("")
top_features = contributions.abs().sort_values(ascending=True).tail(15)
fig = go.Figure(go.Bar(x=top_features.values, y=top_features.index, orientation="h", marker_color=ACCENT))
fig.update_layout(
    height=450,
    margin=dict(l=10, r=10, t=10, b=10),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font={"color": MUTED},
    xaxis=dict(gridcolor=BORDER, zeroline=False),
    yaxis=dict(autorange="reversed"),
)
st.markdown('<div class="card chart-card">', unsafe_allow_html=True)
st.plotly_chart(fig, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)