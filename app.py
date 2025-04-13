import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
from forecast_utils import generate_forecast


# Set page config
st.set_page_config(page_title="HRC Price Forecast Dashboard", layout="wide")

# --- Custom Dashboard Title ---
st.markdown("""
    <div style='text-align: center; padding: 1rem 0; background-color: #0E539A; color: white; border-radius: 8px;'>
        <h1 style='margin-bottom: 0.3rem;'>HRC Price Predict Model Dashboard</h1>
        <p style='font-size: 18px;'>For TATA Steel | Forecasting & Landed Cost Analytics</p>
    </div>
""", unsafe_allow_html=True)


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
from forecast_utils import generate_forecast

def build_combined_forecast(months_ahead, up_adj, down_adj):
    start_date = pd.to_datetime("2024-11-01")
    end_date = start_date + pd.DateOffset(months=months_ahead - 1)

    china_hist = china_actual[china_actual.index < start_date].to_frame(name="China HRC (FOB, $/t) Historical")

    df_input = pd.read_csv("wo_na.csv", parse_dates=["Date"])  
    forecast_df = generate_forecast(
        df_input,
        iron_ore_up=up_adj["Iron Ore"],
        hcc_up=up_adj["HCC"],
        scrap_up=up_adj["Scrap"],
        export_perc_up=up_adj["Export"],
        fai_up=up_adj["FAI"],
        iron_ore_down=down_adj["Iron Ore"],
        hcc_down=down_adj["HCC"],
        scrap_down=down_adj["Scrap"],
        export_perc_down=down_adj["Export"],
        fai_down=down_adj["FAI"],
        months_ahead=months_ahead
    )

    china_forecast = forecast_df["HRC (FOB, $/t)"].copy()
    china_forecast.index = pd.date_range(start=start_date, periods=months_ahead, freq="MS")
    china_forecast = china_forecast.to_frame(name="China HRC (FOB, $/t) Forecast")

    china_downside = china_forecast * (1 - max(down_adj.values()) / 100)
    china_downside.columns = ["China Upside/Downside"]

    japan_forecast = df_japan["Japan_HRC_f"]
    japan_hist = df_base["Japan HRC FOB"] if "Japan HRC FOB" in df_base.columns else None
    japan_forecast = japan_forecast[(japan_forecast.index >= start_date) & (japan_forecast.index <= end_date)]
    japan_forecast = japan_forecast * (1 + up_adj.get("Iron Ore", 0) / 100)
    japan_forecast = japan_forecast.to_frame(name="Japan HRC (FOB, $/t) Forecast")


    combined = pd.concat([
        china_hist,
        china_forecast,
        china_downside,
        japan_forecast
    ], axis=1)

    if japan_hist is not None:
        japan_hist = japan_hist[japan_hist.index < start_date]
        combined = combined.join(japan_hist.to_frame(name="Japan HRC (FOB, $/t) Historical"), how="left")

    combined.reset_index(inplace=True)
    combined.rename(columns={"index": "Date"}, inplace=True)
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

st.sidebar.markdown("**Country Selection**")
selected_countries = st.sidebar.multiselect(
    "Select country to view:",
    options=["China", "Japan"],
    default=["China", "Japan"]
)

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

forecast_only = combined_df[combined_df["Date"] >= "2024-11-01"]

export_df = forecast_only[["Date", "China HRC (FOB, $/t) Forecast", "Japan HRC (FOB, $/t) Forecast"]].copy()
export_df.rename(columns={
    "Date": "Month",
    "China HRC (FOB, $/t) Forecast": "China HRC Price",
    "Japan HRC (FOB, $/t) Forecast": "Japan HRC Price"
}, inplace=True)

csv_bytes = export_df.to_csv(index=False).encode("utf-8")


melted = combined_df.melt("Date", var_name="Series", value_name="USD/ton")

filter_terms = []
filter_terms = []
if "China" in selected_countries:
    filter_terms += ["China HRC (FOB, $/t) Historical", "China HRC (FOB, $/t) Forecast", "China Upside/Downside"]
if "Japan" in selected_countries:
    filter_terms += ["Japan HRC (FOB, $/t) Historical", "Japan HRC (FOB, $/t) Forecast"]  
    filter_terms += ["Japan HRC (FOB, $/t) Historical"]  


melted = melted[melted["Series"].isin(filter_terms)]


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

st.download_button(
    label="📥 Download Forecast Values as CSV",
    data=csv_bytes,
    file_name="hrc_forecast.csv",
    mime="text/csv"
)

available_months = combined_df[combined_df["Date"] >= "2024-11-01"]["Date"].dt.strftime("%Y-%m").unique().tolist()

selected_month_str = st.selectbox("📅 Select Month for Landed Price Calculation", available_months, index=0)
selected_month = pd.to_datetime(selected_month_str + "-01")
selected_row = combined_df[combined_df["Date"] == selected_month]
selected_china_fob = selected_row["China HRC (FOB, $/t) Forecast"].values[0] if not selected_row.empty else 0.0
selected_japan_fob = selected_row["Japan HRC (FOB, $/t) Forecast"].values[0] if not selected_row.empty else 0.0


# --- India Landed Price Calculator ---
st.subheader("🇮🇳 India Landed Price Calculator")

st.markdown("**China Table**")
selected_china_fob = selected_row["China HRC (FOB, $/t) Forecast"].values[0] if not selected_row.empty and not pd.isna(selected_row["China HRC (FOB, $/t) Forecast"].values[0]) else 0.0
selected_japan_fob = selected_row["Japan HRC (FOB, $/t) Forecast"].values[0] if not selected_row.empty and not pd.isna(selected_row["Japan HRC (FOB, $/t) Forecast"].values[0]) else 0.0
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
fob_japan = st.number_input("HRC FOB Japan ($/t)", value=float(round(selected_japan_fob, 2)))
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
