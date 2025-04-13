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

# --- Build Combined Data for Forecast Chart ---
def build_forecast_plot_data(months_ahead, up_pct, down_pct):
    start_date = pd.to_datetime("2024-11-01")
    end_date = start_date + pd.DateOffset(months=months_ahead - 1)

    df = pd.DataFrame(index=pd.date_range(start=start_date, end=end_date, freq="MS"))

    df["China Forecast"] = china_var_forecast.reindex(df.index)
    df["China Upper"] = df["China Forecast"] * (1 + up_pct / 100)
    df["China Lower"] = df["China Forecast"] * (1 - down_pct / 100)

    df["Japan Forecast"] = df_japan["Japan_HRC_f"].reindex(df.index)
    df["Japan Upper"] = df["Japan Forecast"] * (1 + up_pct / 100)
    df["Japan Lower"] = df["Japan Forecast"] * (1 - down_pct / 100)

    hist_df = pd.DataFrame({
        "China Historical": china_actual,
        "Japan Historical": df_base["Japan HRC FOB"] if "Japan HRC FOB" in df_base.columns else None
    })

    return df, hist_df

# --- Sidebar ---
st.sidebar.header("Forecast Parameters")
up_pct = st.sidebar.slider("Upside (%)", 0, 30, 10)
down_pct = st.sidebar.slider("Downside (%)", 0, 30, 10)
months = st.sidebar.slider("Forecast Horizon (months)", 3, 18, 12)

# --- Title ---
st.title("Forecasting of China's and Japan's HRC Prices")
st.markdown("### with Historical Data, Forecast, and Upside/Downside")

# --- Load Forecast Data ---
df_forecast, df_hist = build_forecast_plot_data(months, up_pct, down_pct)

base = alt.Chart(df_forecast.reset_index().rename(columns={"index": "Date"})).encode(x="Date:T")

# China
area_china = base.mark_area(opacity=0.2, color="#90ee90").encode(
    y="China Lower:Q",
    y2="China Upper:Q"
)
line_china_forecast = base.mark_line(strokeDash=[4, 2], color="red").encode(y="China Forecast:Q")
line_china_hist = alt.Chart(df_hist.reset_index()).mark_line(color="black").encode(x="Date:T", y="China Historical:Q")

# Japan
area_japan = base.mark_area(opacity=0.2, color="#f08080").encode(
    y="Japan Lower:Q",
    y2="Japan Upper:Q"
)
line_japan_forecast = base.mark_line(strokeDash=[4, 2], color="#4682b4").encode(y="Japan Forecast:Q")
line_japan_hist = alt.Chart(df_hist.reset_index()).mark_line(color="#888").encode(x="Date:T", y="Japan Historical:Q")

chart = (line_china_hist + line_china_forecast + area_china + line_japan_hist + line_japan_forecast + area_japan).properties(
    width=900, height=450
)
st.altair_chart(chart, use_container_width=True)

# --- Footer ---
st.markdown("---")
st.markdown("Built by Ye Tian for TATA Steel, 2025.")
