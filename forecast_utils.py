# forecast_utils.py
from statsmodels.tsa.api import VAR
import pandas as pd

def generate_forecast(df, iron_ore_up, hcc_up, scrap_up, export_perc_up, fai_up,
                      iron_ore_down, hcc_down, scrap_down, export_perc_down, fai_down, months_ahead):
    df.set_index('Date', inplace=True)
    df.index = pd.to_datetime(df.index)

    list_of_variables = ['Iron Ore (CFR, $/t)', 'HCC (Aus FOB, $/t)', 'Domestic Scrap (DDP Jiangsu incl. VAT $/t)', 
                         'Monthly Export of Semis & Finished Steel as % of Production', 
                         'FAI in urban real estate development (y-o-y) Growth',
                         'Automobile Production (y-o-y)', 'Civil Metal-Vessels/Steel Ships (y-o-y)', 
                         'Household Fridges (y-o-y)', 'Air Conditioner (y-o-y)']
    hrc = ['HRC (FOB, $/t)']
    final_cols = hrc + list_of_variables
    final_df = df.copy()[final_cols]
    final_df_differenced = final_df.diff().dropna()

    var_model = VAR(final_df_differenced)
    model_fitted = var_model.fit(4)
    lag_order = model_fitted.k_ar

    forecast_input = final_df_differenced.values[-lag_order:]
    forecast_result = model_fitted.forecast(y=forecast_input, steps=months_ahead)

    forecast_df = pd.DataFrame(forecast_result, columns=final_df_differenced.columns)
    forecast_df = forecast_df.cumsum()
    last_values = final_df.iloc[-1]
    forecast_df = forecast_df.add(last_values)

    return forecast_df
