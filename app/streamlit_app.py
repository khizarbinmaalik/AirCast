import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_extras.stylable_container import stylable_container
from streamlit_extras.metric_cards import style_metric_cards

from src.inference import fetch_current_features, load_latest_model, predict_forecast

st.set_page_config(page_title="AQI Predictor", page_icon="🌫️", layout="wide")

# --- Global theme ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.main { background: linear-gradient(180deg, #0f1419 0%, #1a1f2e 100%); }

.hero-title {
    font-size: 2.2rem; font-weight: 800; color: #ffffff;
    margin-bottom: 0; letter-spacing: -0.5px;
}
.hero-subtitle { color: #8b93a7; font-size: 0.95rem; margin-top: 4px; }
.data-timestamp {
    color: #6b7280; font-size: 0.8rem; margin-top: 8px;
}
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_model():
    return load_latest_model()


@st.cache_data(ttl=3600)
def get_current_features():
    return fetch_current_features()


AQI_ZONES = [
    (0, 50, "Good", "#22c55e"),
    (50, 100, "Moderate", "#eab308"),
    (100, 150, "Unhealthy for Sensitive Groups", "#f97316"),
    (150, 200, "Unhealthy", "#ef4444"),
    (200, 300, "Very Unhealthy", "#a855f7"),
    (300, 500, "Hazardous", "#7f1d1d"),
]


def aqi_category(aqi):
    for low, high, label, color in AQI_ZONES:
        if low <= aqi < high:
            return label, color
    return "Hazardous", AQI_ZONES[-1][3]


def hex_to_rgba(hex_color, alpha=0.2):
    """Converts a 6-digit hex color to an rgba() string Plotly accepts —
    Plotly's color validator rejects 8-digit hex-with-alpha shorthand."""
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def render_gauge(aqi_value):
    label, color = aqi_category(aqi_value)
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=aqi_value,
        number={"font": {"size": 48, "color": "#ffffff"}, "suffix": ""},
        gauge={
            "axis": {"range": [0, 300], "tickcolor": "#8b93a7", "tickfont": {"color": "#8b93a7"}},
            "bar": {"color": color, "thickness": 0.3},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [{"range": [low, high], "color": hex_to_rgba(c, 0.2)} for low, high, _, c in AQI_ZONES],
        },
    ))
    fig.update_layout(
        height=280, margin=dict(l=20, r=20, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)", font={"color": "#ffffff"},
    )
    return fig

def render_trend_chart(forecast):
    days = ["Today", "Day 1", "Day 2", "Day 3"]
    values = [forecast["current_aqi"], forecast["day1"], forecast["day2"], forecast["day3"]]

    fig = go.Figure()

    # Colored AQI zone bands behind the line, for immediate visual context
    for low, high, label, color in AQI_ZONES:
        if low > max(values) + 30:
            continue
        fig.add_hrect(y0=low, y1=high, fillcolor=color, opacity=0.08, line_width=0)

    fig.add_trace(go.Scatter(
        x=days, y=values, mode="lines+markers",
        line=dict(width=4, color="#38bdf8", shape="spline"),
        marker=dict(size=12, color="#38bdf8", line=dict(width=2, color="#ffffff")),
        fill="tozeroy", fillcolor="rgba(56, 189, 248, 0.12)",
    ))

    fig.update_layout(
        height=380, margin=dict(l=10, r=10, t=20, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#8b93a7"},
        yaxis=dict(title="US AQI", gridcolor="#2a3040", range=[0, max(values) + 40]),
        xaxis=dict(gridcolor="rgba(0,0,0,0)"),
        showlegend=False,
    )
    return fig


# --- Header ---
st.markdown('<p class="hero-title">🌫️ Sukkur AQI Predictor</p>', unsafe_allow_html=True)
st.markdown('<p class="hero-subtitle">3-day forecast — XGBoost delta model · Open-Meteo · NASA FIRMS</p>', unsafe_allow_html=True)

with st.spinner("Fetching latest conditions and generating forecast..."):
    models, feature_cols = get_model()
    feature_row = get_current_features()
    forecast = predict_forecast(feature_row, models, feature_cols)

st.markdown(f'<p class="data-timestamp">📡 Latest data: {feature_row["time"].iloc[0]}</p>', unsafe_allow_html=True)
st.write("")

# --- Alert banner ---
max_forecast_aqi = max(forecast["day1"], forecast["day2"], forecast["day3"])
if max_forecast_aqi > 200:
    worst_day = max(["day1", "day2", "day3"], key=lambda d: forecast[d])
    st.error(f"⚠️ **Hazardous air quality expected** — {worst_day.replace('day', 'Day ')}: "
             f"AQI {forecast[worst_day]:.0f}. Limit outdoor activity.")
elif max_forecast_aqi > 150:
    st.warning("⚠️ Unhealthy air quality expected in the next 3 days. Sensitive groups should take precautions.")

st.write("")

# --- Current AQI gauge + forecast cards, side by side ---
col_gauge, col_cards = st.columns([1, 1.4])

with col_gauge:
    st.plotly_chart(render_gauge(forecast["current_aqi"]), use_container_width=True)
    label, color = aqi_category(forecast["current_aqi"])
    st.markdown(f'<p style="text-align:center; color:{color}; font-weight:700; font-size:1.1rem;">{label}</p>', unsafe_allow_html=True)

with col_cards:
    st.write("")
    day_cols = st.columns(3)
    for i, horizon in enumerate(["day1", "day2", "day3"]):
        label, color = aqi_category(forecast[horizon])
        delta = forecast[horizon] - forecast["current_aqi"]
        arrow = "↑" if delta > 0 else "↓" if delta < 0 else "→"

        with day_cols[i]:
            with stylable_container(
                key=f"card_{horizon}",
                css_styles=f"""
                {{
                    background: linear-gradient(145deg, #1a1f2e, #212838);
                    border: 1px solid {color}44;
                    border-radius: 16px;
                    padding: 18px 12px;
                    text-align: center;
                }}
                """,
            ):
                st.markdown(f'<p style="color:#8b93a7; font-size:0.85rem; margin:0;">Day {i+1}</p>', unsafe_allow_html=True)
                st.markdown(f'<p style="color:#ffffff; font-size:2rem; font-weight:800; margin:4px 0;">{forecast[horizon]:.0f}</p>', unsafe_allow_html=True)
                st.markdown(f'<p style="color:{color}; font-size:0.8rem; font-weight:600; margin:0;">{label}</p>', unsafe_allow_html=True)
                st.markdown(f'<p style="color:#8b93a7; font-size:0.8rem; margin-top:6px;">{arrow} {delta:+.0f} vs today</p>', unsafe_allow_html=True)

st.write("")
st.subheader("Forecast Trend")
st.plotly_chart(render_trend_chart(forecast), use_container_width=True)