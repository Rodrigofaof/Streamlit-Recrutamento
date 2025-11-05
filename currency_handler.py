# currency_handler.py
import requests
import pandas as pd
from config import CURRENCY

def fetch_usd_quotes(targets=("EUR","CLP","PEN","ARS","MXN","BRL","COP")) -> pd.DataFrame:
    """Retorna DataFrame com colunas [Source, Target, Rate] a partir do apilayer (USD como base)."""
    params = {
        "access_key": CURRENCY["api_key"],
        "currencies": ",".join(targets),
        "source": "USD",
        "format": 1,
    }
    url = CURRENCY["base_url"]
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    if not data.get("success"):
        err = data.get("error", {})
        raise RuntimeError(f"Currency API error: {err}")
    quotes = data["quotes"]  # ex.: {"USDBRL": 5.62, ...}
    df = pd.DataFrame(list(quotes.items()), columns=["Pair", "Rate"])
    df["Source"] = df["Pair"].str[:3]   # "USD"
    df["Target"] = df["Pair"].str[3:]   # "BRL", ...
    return df[["Source","Target","Rate"]]

def adjust_cpi_to_usd(df: pd.DataFrame, currency_map: pd.DataFrame,
                      left_currency_col="Currency", keep_cols_drop=("Source","Target","Rate","invoice_currency")) -> pd.DataFrame:
    """
    Converte df['cpi'] da moeda local para USD.
    currency_map: DF com [Source='USD', Target='BRL', Rate]
    Se CPI estiver na moeda do 'Target', então CPI_USD = CPI_local / Rate.
    """
    out = df.merge(currency_map, left_on=left_currency_col, right_on="Target", how="left")
    # se não houver cotação, não altera
    out["Rate"] = out["Rate"].fillna(1.0)
    out["cpi"] = out["cpi"] / out["Rate"]
    drop_cols = [c for c in keep_cols_drop if c in out.columns]
    out = out.drop(columns=drop_cols)
    return out
