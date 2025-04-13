import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
import matplotlib.pyplot as plt

# Set page config
st.set_page_config(page_title="HRC Price Forecast Dashboard", layout="wide")

# --- Custom Dashboard Title ---
st.markdown("""
    <div style='text-align: center; padding: 1rem 0; background-color: #0E539A; color: white; border-radius: 8px;'>
        <h1 style='margin-bottom: 0.3rem;'>HRC Price Predict Model Dashboard</h1>
        <p style='font-size: 18px;'>For TATA Steel | Forecasting & Landed Cost Analytics</p>
    </div>
""", unsafe_allow_html=True)

# --- Forecasting Function from Notebook ---
def generate_forecast(df, iron_ore_up, hcc_up, scrap_up, export_perc_up, fai_up,
                      iron_ore_down, hcc_down, scrap_down, export_perc_down, fai_down, months_ahead):
    from statsmodels.tsa.api import VAR

    df.set_index('Date', inplace=True)
    df.index = pd.to_datetime(df.index)

    list_of_variables = ['Iron Ore (CFR, $/t)', 'HCC (Aus FOB, $/t)',
        'Domestic Scrap (DDP Jiangsu incl. VAT $/t)',
        'Monthly Export of Semis & Finished Steel as % of Production',
        'FAI in urban real estate development (y-o-y) Growth']
    hrc = ['HRC (FOB, $/t)']
    final_cols = hrc + list_of_variables
    final_df = df[final_cols]
    final_df_differenced = final_df.diff().dropna()

    model = VAR(final_df_differenced)
    results = model.fit(2)
    lag_order = results.k_ar
    forecast_input = final_df_differenced.values[-lag_order:]
    fc = results.forecast(y=forecast_input, steps=months_ahead)
    fc_df = pd.DataFrame(fc, index=pd.date_range(start=final_df_differenced.index[-1]+pd.DateOffset(months=1), periods=months_ahead, freq='MS'), columns=final_df_differenced.columns)

    forecast_result = final_df.iloc[-1] + fc_df.cumsum()
    forecast_result['HRC (FOB, $/t) Upside'] = forecast_result['HRC (FOB, $/t)'] * (1 + (iron_ore_up + hcc_up + scrap_up + export_perc_up + fai_up) / 500)
    forecast_result['HRC (FOB, $/t) Downside'] = forecast_result['HRC (FOB, $/t)'] * (1 - (iron_ore_down + hcc_down + scrap_down + export_perc_down + fai_down) / 500)

    china_hist = df['HRC (FOB, $/t)'].copy()
    japan_hist = df['Japan HRC FOB'].copy() if 'Japan HRC FOB' in df.columns else pd.Series(dtype=float)

    plt.figure(figsize=(10,5))
    plt.plot(china_hist, label='China Historical')
    if not japan_hist.empty:
        plt.plot(japan_hist, label='Japan Historical', linestyle='--')
    plt.plot(forecast_result['HRC (FOB, $/t)'], label='China Forecast', color='red')
    plt.fill_between(forecast_result.index, forecast_result['HRC (FOB, $/t) Upside'], forecast_result['HRC (FOB, $/t) Downside'], color='red', alpha=0.2, label='Upside/Downside')

    plt.title('HRC Price Forecast with Historical Data')
    plt.xlabel('Date')
    plt.ylabel('Price (USD/t)')
    plt.legend()
    plt.grid(True)
    return plt

# --- Sidebar Parameters ---
st.sidebar.header("Model Parameters")
up_iron_ore = st.sidebar.number_input("Iron Ore (Upside)", 0, 100, 5)
up_hcc = st.sidebar.number_input("HCC (Upside)", 0, 100, 5)
up_scrap = st.sidebar.number_input("Scrap (Upside)", 0, 100, 5)
up_export = st.sidebar.number_input("Export (Upside)", 0, 100, 5)
up_fai = st.sidebar.number_input("FAI (Upside)", 0, 100, 5)

down_iron_ore = st.sidebar.number_input("Iron Ore (Downside)", 0, 100, 5)
down_hcc = st.sidebar.number_input("HCC (Downside)", 0, 100, 5)
down_scrap = st.sidebar.number_input("Scrap (Downside)", 0, 100, 5)
down_export = st.sidebar.number_input("Export (Downside)", 0, 100, 5)
down_fai = st.sidebar.number_input("FAI (Downside)", 0, 100, 5)

months = st.sidebar.slider("Forecast Months Ahead", 3, 18, 12)

# --- Forecast Chart (Matplotlib) ---
st.subheader("📈 Forecast Chart (Matplotlib)")
df_full = pd.read_csv("wo_na.csv", parse_dates=["Date"])
fig = generate_forecast(
    df_full,
    up_iron_ore, up_hcc, up_scrap, up_export, up_fai,
    down_iron_ore, down_hcc, down_scrap, down_export, down_fai,
    months
)
st.pyplot(fig)

# --- CSV Download ---
forecast_df = df_full.copy()
forecast_df.set_index("Date", inplace=True)
latest = forecast_df["HRC (FOB, $/t)"].dropna().iloc[-1]
forecast_months = pd.date_range(start=forecast_df.index[-1] + pd.DateOffset(months=1), periods=months, freq="MS")
china_forecast = [latest * (1 + (i / 100)) for i in range(months)]
japan_forecast = [latest * (0.95 + (i / 1000)) for i in range(months)]  # dummy

export_df = pd.DataFrame({
    "Month": forecast_months.strftime("%Y-%m"),
    "China HRC Price": china_forecast,
    "Japan HRC Price": japan_forecast
})

csv_bytes = export_df.to_csv(index=False).encode("utf-8")
st.download_button("📥 Download Forecast Values as CSV", data=csv_bytes, file_name="hrc_forecast.csv", mime="text/csv")

# --- Landed Price Calculator ---
available_months = forecast_months.strftime("%Y-%m").tolist()
selected_month_str = st.selectbox("📅 Select Month for Landed Price Calculation", available_months)
selected_china_fob = export_df[export_df["Month"] == selected_month_str]["China HRC Price"].values[0]
selected_japan_fob = export_df[export_df["Month"] == selected_month_str]["Japan HRC Price"].values[0]

st.subheader("🇮🇳 India Landed Price Calculator")
st.markdown("**China Table**")
fob_china = st.number_input("HRC FOB China ($/t)", value=float(round(selected_china_fob, 2)))
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
