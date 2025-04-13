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
japan_forecast = df_japan["Japan_HRC_f"]

# --- Build Combined Data ---
def build_combined_forecast(months_ahead, up_adj, down_adj):
    start_date = pd.to_datetime("2024-11-01")
    end_date = start_date + pd.DateOffset(months=months_ahead - 1)

    # China Historical
    china_hist = china_actual[china_actual.index < start_date].to_frame(name="China HRC (FOB, $/t) Historical")

    # China Upside (VAR Forecast)
    china_up = china_var_forecast[(china_var_forecast.index >= start_date) & (china_var_forecast.index <= end_date)]
    for key, pct in up_adj.items():
        if pct > 0:
            china_up *= (1 + pct / 100)
    china_up = china_up.to_frame(name="China HRC (FOB, $/t) Forecast")

    # China Downside (MLR Forecast)
    china_down = china_mlr_forecast[(china_mlr_forecast.index >= start_date) & (china_mlr_forecast.index <= end_date)]
    for key, pct in down_adj.items():
        if pct > 0:
            china_down *= (1 - pct / 100)
    china_down = china_down.to_frame(name="China Downside")

    # Japan Forecast (adjusted by Iron Ore)
    japan_up = japan_forecast[(japan_forecast.index >= start_date) & (japan_forecast.index <= end_date)]
    japan_up = japan_up * (1 + up_adj.get("Iron Ore", 0) / 100)
    japan_up = japan_up.to_frame(name="Japan HRC (FOB, $/t) Forecast")

    japan_hist = df_base["Japan HRC FOB"] if "Japan HRC FOB" in df_base.columns else None

    # Combine all
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

# Upside Inputs
st.sidebar.markdown("**Upside (%) Adjustments**")
up_iron_ore = st.sidebar.number_input("Iron Ore (Upside)", min_value=0, max_value=100, value=5)
up_hcc = st.sidebar.number_input("HCC (Upside)", min_value=0, max_value=100, value=5)
up_scrap = st.sidebar.number_input("Scrap (Upside)", min_value=0, max_value=100, value=5)
up_export = st.sidebar.number_input("Export (Upside)", min_value=0, max_value=100, value=5)
up_fai = st.sidebar.number_input("FAI (Upside)", min_value=0, max_value=100, value=5)

# Downside Inputs
st.sidebar.markdown("**Downside (%) Adjustments**")
down_iron_ore = st.sidebar.number_input("Iron Ore (Downside)", min_value=0, max_value=100, value=5)
down_hcc = st.sidebar.number_input("HCC (Downside)", min_value=0, max_value=100, value=5)
down_scrap = st.sidebar.number_input("Scrap (Downside)", min_value=0, max_value=100, value=5)
down_export = st.sidebar.number_input("Export (Downside)", min_value=0, max_value=100, value=5)
down_fai = st.sidebar.number_input("FAI (Downside)", min_value=0, max_value=100, value=5)

months = st.sidebar.slider("Months ahead (Start: 2024-11)", min_value=3, max_value=18, value=12)

upside_adjustments = {
    "Iron Ore": up_iron_ore,
    "HCC": up_hcc,
    "Scrap": up_scrap,
    "Export": up_export,
    "FAI": up_fai
}

downside_adjustments = {
    "Iron Ore": down_iron_ore,
    "HCC": down_hcc,
    "Scrap": down_scrap,
    "Export": down_export,
    "FAI": down_fai
}

# --- Title ---
st.title("📈 Forecasting HRC Prices")
st.markdown("Historical Data + Forecast with Upside/Downside Scenarios")

# --- Load Forecasted Data ---
combined_df = build_combined_forecast(months, upside_adjustments, downside_adjustments)
melted = combined_df.melt("Date", var_name="Series", value_name="USD/ton")

# --- Chart ---
chart = alt.Chart(melted).mark_line().encode(
    x=alt.X('Date:T', title="Date"),
    y=alt.Y('USD/ton:Q', title="Price (USD per ton)"),
    color='Series:N',
    strokeDash=alt.condition(
        alt.datum.Series == "Japan HRC (FOB, $/t) Forecast",
        alt.value([5, 5]),  # Dashed line
        alt.value([0])      # Solid line for others
    ),
    tooltip=['Date:T', 'Series:N', 'USD/ton:Q']
).properties(width=900, height=450)

st.altair_chart(chart, use_container_width=True)
