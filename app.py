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
def build_combined_forecast(months_ahead, up_adj, down_adj):
    start_date = pd.to_datetime("2024-11-01")
    end_date = start_date + pd.DateOffset(months=months_ahead - 1)

    # China Historical
    china_hist = china_actual[china_actual.index < start_date].to_frame(name="China HRC (FOB, $/t) Historical")

    # Upside forecast (VAR-based with adjustments)
    china_up = china_var_forecast[(china_var_forecast.index >= start_date) & (china_var_forecast.index <= end_date)]
    for key, pct in up_adj.items():
        if pct > 0:
            china_up *= (1 + pct / 100)
    china_up = china_up.to_frame(name="China Upside/Downside")

    # Downside forecast (MLR-based with adjustments)
    china_down = china_mlr_forecast[(china_mlr_forecast.index >= start_date) & (china_mlr_forecast.index <= end_date)]
    for key, pct in down_adj.items():
        if pct > 0:
            china_down *= (1 - pct / 100)
    china_down = china_down.to_frame(name="China Downside")

    # Japan forecast adjusted by Iron Ore only
    japan_forecast = df_japan["Japan_HRC_f"]
    japan_hist = df_base["Japan HRC FOB"] if "Japan HRC FOB" in df_base.columns else None
    japan_up = japan_forecast[(japan_forecast.index >= start_date) & (japan_forecast.index <= end_date)]
    japan_up = japan_up * (1 + up_adj.get("Iron Ore", 0) / 100)
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

months = st.sidebar.slider("Months ahead (Started in 2025-02-01)", min_value=3, max_value=18, value=12)

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
st.title("Forecasting HRC Prices")
st.markdown("### with Historical Data + Upside/Downside")

# --- Load and Transform Data ---
combined_df = build_combined_forecast(months, upside_adjustments, downside_adjustments)

# Rename for clarity in chart
combined_df.rename(columns={
    "China Upside/Downside": "China HRC (FOB, $/t) Forecast",
    "China Downside": "China Upside/Downside",
    "Japan Upside/Downside": "Japan HRC (FOB, $/t) Forecast"
}, inplace=True)

melted = combined_df.melt("Date", var_name="Series", value_name="USD/ton")

chart = alt.Chart(melted).mark_line().encode(
    x='Date:T',
    y=alt.Y('USD/ton:Q', title='Price (USD per ton)'),
    color='Series:N',
    strokeDash='Series:N',
    tooltip=[
        alt.Tooltip('Date:T', title='Date'),
        alt.Tooltip('USD/ton:Q', title='Price (USD/t)')
    ]
).properties(width=900, height=450).interactive()


st.altair_chart(chart, use_container_width=True)

# --- India Landed Price Calculator ---
st.subheader("🇮🇳 India Landed Price Calculator")

st.markdown("**China Table**")
fob_china = st.number_input("HRC FOB China ($/t)", value=500.0)
freight = st.number_input("Sea Freight ($/t)", value=30.0)
customs_pct = st.number_input("Basic Customs Duty (%)", value=7.5)
sgd = st.number_input("Applicable SGD ($/t)", value=0.0)
lc_charges = st.number_input("LC charges & Port charges ($/t)", value=10.0)
mip = st.number_input("Minimum Import Price ($/t)", value=0.0)
exchange_rate = st.number_input("Exchange Rate (Rs/USD)", value=86.0)
freight_to_city = st.number_input("Freight (Port to City) (Rs/t)", value=500.0)

cfr = fob_china + freight
insurance = 0.01 * cfr
cif = cfr + insurance
customs_absolute = cif * customs_pct / 100
sws = customs_absolute * 0.10
landed_value = cif + customs_absolute + sws
safeguard_duty_pct = st.number_input("Safeguard Duty (%)", value=0.0)
safeguard_duty_abs = landed_value * safeguard_duty_pct / 100
port_price = landed_value + sgd + mip + safeguard_duty_abs
mumbai_port_rs = port_price * exchange_rate
mumbai_market_rs = mumbai_port_rs + freight_to_city

st.markdown(f"<span style='color:#0E539A; font-weight:bold;'>China landed price is: ₹ {mumbai_market_rs:.2f}/t</span>", unsafe_allow_html=True)


# --- Japan/Korea Landed Price Calculator ---
st.markdown("**Japan Table**")
fob_japan = st.number_input("HRC FOB Japan ($/t)", value=600.0)
freight_jp = st.number_input("Sea Freight (Japan) ($/t)", value=30.0)
customs_pct_jp = st.number_input("Basic Customs Duty (Japan) (%)", value=0.0)
sgd_jp = st.number_input("Applicable SGD (Japan) ($/t)", value=0.0)
lc_charges_jp = st.number_input("LC charges & Port charges (Japan) ($/t)", value=10.0)
mip_jp = st.number_input("Minimum Import Price (Japan) ($/t)", value=0.0)
exchange_rate_jp = st.number_input("Exchange Rate (Japan Rs/USD)", value=86.0)
freight_to_city_jp = st.number_input("Freight (Port to City - Japan) (Rs/t)", value=500.0)

cfr_jp = fob_japan + freight_jp
insurance_jp = 0.01 * cfr_jp
cif_jp = cfr_jp + insurance_jp
customs_absolute_jp = cif_jp * customs_pct_jp / 100
sws_jp = customs_absolute_jp * 0.10
landed_value_jp = cif_jp + customs_absolute_jp + sws_jp
safeguard_duty_pct_jp = st.number_input("Safeguard Duty (Japan) (%)", value=0.0)
safeguard_duty_abs_jp = landed_value_jp * safeguard_duty_pct_jp / 100
port_price_jp = landed_value_jp + sgd_jp + mip_jp + safeguard_duty_abs_jp
mumbai_port_rs_jp = port_price_jp * exchange_rate_jp
mumbai_market_rs_jp = mumbai_port_rs_jp + freight_to_city_jp

st.markdown(f"<span style='color:red; font-weight:bold;'>Japan landed price is: ₹ {mumbai_market_rs_jp:.2f}/t</span>", unsafe_allow_html=True)
