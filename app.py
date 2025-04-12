import streamlit as st
import pandas as pd
import plotly.express as px
import base64
from io import BytesIO

# ----------------------------
# Page Setup
# ----------------------------
st.set_page_config(
    page_title="HRC Price Forecast Dashboard",
    layout="wide",
    page_icon="📈"
)

st.markdown("""
    <style>
        .main {background-color: #F5FAFF;}
        h1, h2, h3 {color: #0E539A;}
    </style>
""", unsafe_allow_html=True)

st.title("📈 HRC Price Forecasting Dashboard")
st.markdown("""This dashboard displays HRC price forecasts using VAR, Regression, and LSTM models, along with a calculator for India's landed import price. All forecasts are visualized with macroeconomic drivers for actionable insights.""")

# ----------------------------
# Load Forecast Data
# ----------------------------
@st.cache_data
def load_forecasts():
    var = pd.read_csv("var_forecast.csv", parse_dates=["Date"])
    reg = pd.read_csv("regression_forecast.csv", parse_dates=["Date"])
    lstm = pd.read_csv("lstm_forecast.csv", parse_dates=["Date"])
    return var, reg, lstm

var_df, reg_df, lstm_df = load_forecasts()

# ----------------------------
# User Inputs
# ----------------------------
model_choice = st.selectbox("Select Forecast Model", ["VAR", "Regression", "LSTM"])
time_range = st.slider("Select Time Range", min_value=var_df["Date"].min().date(), max_value=var_df["Date"].max().date(), value=(var_df["Date"].min().date(), var_df["Date"].max().date()))
exchange_rate = st.number_input("INR/USD Exchange Rate", value=82.0)

freight = 50
insurance = 1.5
customs_duty = 7.5

# ----------------------------
# Filter Data
# ----------------------------
def get_model_df():
    if model_choice == "VAR": return var_df
    elif model_choice == "Regression": return reg_df
    else: return lstm_df

model_df = get_model_df()
filtered_df = model_df[(model_df["Date"] >= pd.to_datetime(time_range[0])) & (model_df["Date"] <= pd.to_datetime(time_range[1]))]

# ----------------------------
# Landed Price Calculation
# ----------------------------
for country in ["China", "Japan"]:
    fob_col = f"FOB_{country}"
    cif = filtered_df[fob_col] + freight + (filtered_df[fob_col] * insurance / 100)
    filtered_df[f"Landed_{country}"] = cif * (1 + customs_duty / 100) * exchange_rate

# ----------------------------
# Plot Forecast Chart
# ----------------------------
fig = px.line(filtered_df, x="Date",
              y=["FOB_China", "Landed_China", "FOB_Japan", "Landed_Japan"],
              labels={"value": "USD/t or INR/t", "Date": "Date"},
              title=f"{model_choice} Forecast: HRC Prices & Landed Costs")
fig.update_layout(hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

# ----------------------------
# Download Buttons
# ----------------------------
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

def convert_fig_to_png(fig):
    img_bytes = fig.to_image(format="png")
    return img_bytes

col1, col2 = st.columns(2)
with col1:
    st.download_button(
        label="Download Forecast Data as CSV",
        data=convert_df_to_csv(filtered_df),
        file_name=f"{model_choice.lower()}_forecast.csv",
        mime="text/csv"
    )
with col2:
    png_bytes = convert_fig_to_png(fig)
    st.download_button(
        label="Download Forecast Plot as PNG",
        data=png_bytes,
        file_name=f"{model_choice.lower()}_forecast.png",
        mime="image/png"
    )

# ----------------------------
# Data Table Display
# ----------------------------
st.markdown("### 📄 Forecast Data Table")
st.dataframe(filtered_df.round(2))
