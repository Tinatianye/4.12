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
    else:
        forecast_series = df_japan["Japan_HRC_f"]
        label = "Japan HRC FOB"

    forecast_period = forecast_series[(forecast_series.index >= start_date) & (forecast_series.index <= end_date)]
    forecast_df = forecast_period.to_frame(name=label)
    forecast_df.index.name = "Date"
    forecast_df.reset_index(inplace=True)
    return forecast_df

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
forecast_df = create_forecast_region(region, scenario, months)
freight_cost = 50 if region == "China" else 60
forecast_df["Landed (CIF)"] = forecast_df[forecast_df.columns[1]] + freight_cost

melted = forecast_df.melt("Date", value_vars=[forecast_df.columns[1], "Landed (CIF)"], var_name="Price Type", value_name="USD/ton")
chart = alt.Chart(melted).mark_line(point=True).encode(
    x='Date:T',
    y=alt.Y('USD/ton:Q', title='Price (USD per ton)'),
    color='Price Type:N'
).properties(title=f"{region} HRC Export Price Forecast ({scenario} Scenario)")

st.subheader(f"Forecasted HRC Price ({region}) - FOB vs Landed (India)")
st.altair_chart(chart, use_container_width=True)

# --- Footer ---
st.markdown("---")
st.markdown("Built by Ye Tian for TATA Steel, 2025.")
