import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime

# Set page config
st.set_page_config(page_title="HRC Price Forecast Dashboard", layout="wide")

# --- Load Data ---
df_base = pd.read_csv("wo_na.csv", parse_dates=["Date"])
df_base.set_index("Date", inplace=True)

df_mlr = pd.read_csv("multireg_forecast.csv", parse_dates=["Date"])
df_var = pd.read_csv("var_forecast_actual.csv", parse_dates=["Date"])
df_japan = pd.read_csv("JP_forecast.csv", header=0, names=["Date", "Japan_HRC_f"], parse_dates=["Date"])
df_japan.set_index("Date", inplace=True)

china_mlr_forecast = df_mlr.set_index("Date")["HRC (FOB, $/t)_f"]
china_var_forecast = df_var.set_index("Date")["HRC (FOB, $/t)_forecast"]
china_actual = df_base["HRC (FOB, $/t)"]

# --- Build Combined Data ---
def build_combined_forecast_with_bounds(months_ahead, up_pct, down_pct):
    start_date = pd.to_datetime("2024-11-01")
    end_date = start_date + pd.DateOffset(months=months_ahead - 1)

    china_hist = china_actual[china_actual.index < start_date].to_frame(name="China Historical")
    china_forecast = china_var_forecast[(china_var_forecast.index >= start_date) & (china_var_forecast.index <= end_date)]
    china_center = china_forecast.to_frame(name="China Forecast")
    china_center["China Upper"] = china_center["China Forecast"] * (1 + up_pct / 100)
    china_center["China Lower"] = china_center["China Forecast"] * (1 - down_pct / 100)

    japan_forecast = df_japan["Japan_HRC_f"]
    japan_hist = df_base["Japan HRC FOB"] if "Japan HRC FOB" in df_base.columns else None
    japan_future = japan_forecast[(japan_forecast.index >= start_date) & (japan_forecast.index <= end_date)]
    japan_center = japan_future.to_frame(name="Japan Forecast")
    japan_center["Japan Upper"] = japan_center["Japan Forecast"] * (1 + up_pct / 100)
    japan_center["Japan Lower"] = japan_center["Japan Forecast"] * (1 - down_pct / 100)

    df_plot = pd.concat([
        china_hist,
        china_center,
        japan_center,
        japan_hist.to_frame(name="Japan Historical") if japan_hist is not None else None
    ], axis=1)
    df_plot.reset_index(inplace=True)
    return df_plot

# --- Sidebar ---
st.sidebar.header("Forecast Adjustment Settings")
up_pct = st.sidebar.slider("Upside (%)", min_value=0, max_value=30, value=10)
down_pct = st.sidebar.slider("Downside (%)", min_value=0, max_value=30, value=10)
months = st.sidebar.slider("Forecast Horizon (months)", min_value=3, max_value=18, value=12)

# --- Title ---
st.title("Forecasting HRC Prices")
st.markdown("### Historical + Forecast + Upside/Downside Ranges")

# --- Forecast and Visual ---
df_plot = build_combined_forecast_with_bounds(months, up_pct, down_pct)

base = alt.Chart(df_plot).encode(x='Date:T')

area_china = base.mark_area(opacity=0.3, color='lightgreen').encode(
    y='China Lower:Q',
    y2='China Upper:Q'
)
line_china = base.mark_line(strokeDash=[4,2], color='green').encode(y='China Forecast:Q')
hist_china = base.mark_line(color='black').encode(y='China Historical:Q')

area_japan = base.mark_area(opacity=0.3, color='lightcoral').encode(
    y='Japan Lower:Q',
    y2='Japan Upper:Q'
)
line_japan = base.mark_line(strokeDash=[4,2], color='red').encode(y='Japan Forecast:Q')
hist_japan = base.mark_line(color='gray').encode(y='Japan Historical:Q')

chart = (area_china + line_china + hist_china + area_japan + line_japan + hist_japan).properties(
    width=900, height=450
)
st.altair_chart(chart, use_container_width=True)

# --- Footer ---
st.markdown("---")
st.markdown("Built by Ye Tian for TATA Steel, 2025.")
