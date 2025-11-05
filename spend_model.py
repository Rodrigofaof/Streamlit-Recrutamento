import pandas as pd
import numpy as np
import statsmodels.api as sm
from database_handler import connect_db, query_spend_last4months, query_panelists_last4months
from utils.file_handler import criar_dataframe

def run_spend_model():
    """Executa consultas, prepara dados e ajusta modelo NB de Spend vs Panelists."""

    conn = connect_db()
    cursor = conn.cursor()

    # ===== CONSULTAS =====
    cost_raw = query_spend_last4months(cursor)
    Cost = criar_dataframe(cost_raw, cursor)

    panel_raw = query_panelists_last4months(cursor)
    Panelists = criar_dataframe(panel_raw, cursor)

    # ===== MERGE =====
    df_merged = Panelists.merge(right=Cost, on=['country','recruit_source','date'], how='inner')

    Source = pd.read_excel('Recruit_source.xlsx')
    df_merged = df_merged.merge(right=Source, how='inner', on='recruit_source')
    df_merged = df_merged.drop(columns='recruit_source')

    df = df_merged.copy()
    df['date'] = pd.to_datetime(df['date'])

    # ===== FILTRO (últimos 4 meses) =====
    latest_data_date = df['date'].max()
    start_date_filter = latest_data_date - pd.DateOffset(months=4)

    df_train = df[
        (df['date'] >= start_date_filter) &
        (df['date'] <= latest_data_date) &
        (df['spend'] > 0)
    ].copy()

    df_train['log_spend'] = np.log(df_train['spend'])

    # ===== MODELO NB =====
    formula = "Panelists ~ log_spend * C(Source) + log_spend * C(country)"
    model_final = sm.NegativeBinomial.from_formula(formula, data=df_train).fit(maxiter=100)

    cursor.close()
    conn.close()

    return model_final, df_train

