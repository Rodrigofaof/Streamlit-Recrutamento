import pandas as pd
import numpy as np
from spend_model import run_spend_model
from pandas.tseries.offsets import BDay

def main():
    # Treina o modelo e obtém os dados de treino
    model, df_train = run_spend_model()
    print("Modelo treinado com sucesso. Exemplo de treino:")
    print(df_train.head())

    # ===============================
    # 1. Calcular média de gasto dos últimos 3 dias úteis
    # ===============================
    last_date = df_train['date'].max()
    mask = (df_train['date'] > last_date - BDay(3)) & (df_train['date'] <= last_date)
    df_last3 = df_train.loc[mask]

    mean_spend = (
        df_last3.groupby(['country', 'Source'], as_index=False)['spend']
        .mean()
        .rename(columns={'spend': 'avg_spend'})
    )

    mean_spend['log_spend'] = np.log(mean_spend['avg_spend'])

    print("\nMédia de gasto dos últimos 3 dias úteis:")
    print(mean_spend.head())

    # ===============================
    # 2. Fazer previsão com base na média calculada
    # ===============================
    preds = model.predict(mean_spend)
    mean_spend['predicted_panelists'] = preds

    print("\nPrevisão com base nos 3 dias úteis mais recentes:")
    print(mean_spend[['country', 'Source', 'avg_spend', 'predicted_panelists']].head())

    # === Soma por país ===
    spend_by_country = (
        mean_spend.groupby('country', as_index=False)
        .agg({'avg_spend': 'sum', 'predicted_panelists': 'sum'})
    )
    print("\nTotais por país:")
    print(spend_by_country)

if __name__ == "__main__":
    main()
