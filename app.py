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

# --- Forecasting Function ---
def create_forecast_region(region: str, scenario: str, months_ahead: int):
    start_date = pd.to_datetime("2024-11-01")
    end_date = start_date + pd.DateOffset(months=months_ahead - 1)

    if region == "China":
        forecast_series = china_mlr_forecast if scenario == "Downside" else china_var_forecast
        label = "China HRC FOB"
        actual_series = china_actual
    else:
        forecast_series = df_japan["Japan_HRC_f"]
        label = "Japan HRC FOB"
        actual_series = df_base["Japan HRC FOB"] if "Japan HRC FOB" in df_base.columns else None

    forecast_period = forecast_series[(forecast_series.index >= start_date) & (forecast_series.index <= end_date)]
    forecast_df = forecast_period.to_frame(name=label)
    forecast_df.index.name = "Date"

    # Combine with actuals for continuity
    if actual_series is not None:
        actual_part = actual_series[actual_series.index < start_date].to_frame(name=label)
        full_series = pd.concat([actual_part, forecast_df])
    else:
        full_series = forecast_df

    full_series["Landed (CIF)"] = full_series[label] + (50 if region == "China" else 60)
    full_series.reset_index(inplace=True)
    return full_series, label

# --- Sidebar Controls ---
st.sidebar.header("Options")
region = st.sidebar.selectbox("Select Region", ["China", "Japan"])
scenario = st.sidebar.selectbox("Select Scenario", ["Downside", "Upside"])
months = st.sidebar.slider("Months ahead to forecast", min_value=3, max_value=18, value=12)

# --- Title ---
st.title("HRC Price Forecast Dashboard (2025)")
st.markdown(f"**Region:** {region} &nbsp;&nbsp; **Scenario:** {scenario} &nbsp;&nbsp; **Horizon:** {months} months")

# --- Historical Trends ---
st.subheader("Historical Time Series Trends")
options = list(df_base.columns)
default_vars = ["HRC (FOB, $/t)", "Iron Ore (CFR, $/t)"]
selected_vars = st.multiselect("Select variables to plot", options, default=default_vars)
if selected_vars:
    st.line_chart(df_base[selected_vars])

# --- Forecast & Landed Price ---
forecast_df, label = create_forecast_region(region, scenario, months)

melted = forecast_df.melt("Date", value_vars=[label, "Landed (CIF)"], var_name="Price Type", value_name="USD/ton")
chart = alt.Chart(melted).mark_line(point=True).encode(
    x='Date:T',
    y=alt.Y('USD/ton:Q', title='Price (USD per ton)'),
    color='Price Type:N'
).properties(title=f"Forecasting HRC Prices with Historical Data + {scenario} Scenario")

st.subheader(f"Forecasted HRC Price ({region}) - FOB vs Landed (India)")
st.altair_chart(chart, use_container_width=True)

# --- Footer ---
st.markdown("---")
st.markdown("Built by Ye Tian for TATA Steel, 2025.")
