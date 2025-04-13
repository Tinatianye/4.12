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
def build_combined_forecast(months_ahead, adjustments):
    start_date = pd.to_datetime("2024-11-01")
    end_date = start_date + pd.DateOffset(months=months_ahead - 1)

    # China Historical
    china_hist = china_actual[china_actual.index < start_date].to_frame(name="China HRC (FOB, $/t) Historical")

    # Upside forecast (VAR-based with adjustments)
    china_up = china_var_forecast[(china_var_forecast.index >= start_date) & (china_var_forecast.index <= end_date)]
    china_up = china_up.copy()
    for key, pct in adjustments.items():
        if pct > 0:
            china_up *= (1 + pct / 100)
    china_up = china_up.to_frame(name="China Upside/Downside")

    # Downside forecast (MLR-based with adjustments)
    china_down = china_mlr_forecast[(china_mlr_forecast.index >= start_date) & (china_mlr_forecast.index <= end_date)]
    china_down = china_down.copy()
    for key, pct in adjustments.items():
        if pct > 0:
            china_down *= (1 - pct / 100)
    china_down = china_down.to_frame(name="China Downside")

    # Japan (static forecast adjusted by iron ore only as example)
    japan_forecast = df_japan["Japan_HRC_f"]
    japan_hist = df_base["Japan HRC FOB"] if "Japan HRC FOB" in df_base.columns else None
    japan_up = japan_forecast[(japan_forecast.index >= start_date) & (japan_forecast.index <= end_date)]
    japan_up = japan_up * (1 + adjustments.get("Iron Ore", 0) / 100)
    japan_up = japan_up.to_frame(name="Japan Upside/Downside")

    # Combine
    combined = pd.concat([
        china_hist,
        china_up,
        china_down,
        japan_up
    ], axis=1)

    if japan_hist is not None:
        combined = combined.join(japan_hist.to_frame(name="Japan HRC (FOB, $/t) Historical"), how="left")

    combined.reset_index(inplace=True)
    return combined

# --- Sidebar ---
st.sidebar.header("Model Parameters")
adj_iron_ore = st.sidebar.number_input("Iron Ore (%)", min_value=0, max_value=100, value=5)
adj_hcc = st.sidebar.number_input("HCC (%)", min_value=0, max_value=100, value=5)
adj_scrap = st.sidebar.number_input("Scrap (%)", min_value=0, max_value=100, value=5)
adj_export = st.sidebar.number_input("Export (%)", min_value=0, max_value=100, value=5)
adj_fai = st.sidebar.number_input("FAI (%)", min_value=0, max_value=100, value=5)
months = st.sidebar.slider("Months ahead (Started in 2025-02-01)", min_value=3, max_value=18, value=12)

adjustments = {
    "Iron Ore": adj_iron_ore,
    "HCC": adj_hcc,
    "Scrap": adj_scrap,
    "Export": adj_export,
    "FAI": adj_fai
}

# --- Title ---
st.title("Forecasting HRC Prices")
st.markdown("### with Historical Data + Upside/Downside")

# --- Load and Transform Data ---
combined_df = build_combined_forecast(months, adjustments)

melted = combined_df.melt("Date", var_name="Series", value_name="USD/ton")

chart = alt.Chart(melted).mark_line().encode(
    x='Date:T',
    y=alt.Y('USD/ton:Q', title='Price (USD per ton)'),
    color='Series:N',
    strokeDash='Series:N'
).properties(width=900, height=450)

st.altair_chart(chart, use_container_width=True)

# --- Footer ---
st.markdown("---")
st.markdown("Built by Ye Tian for TATA Steel, 2025.")
