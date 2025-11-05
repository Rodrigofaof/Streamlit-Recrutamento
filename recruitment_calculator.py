import numpy as np
import pandas as pd
from datetime import datetime

AGES = list(range(18, 100))  # 18..99

def calcular_days_left(df, date_col="Expected_End_Date"):
    today = pd.Timestamp(datetime.now().date())
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df["Days_Left"] = (df[date_col] - today).dt.days
    df["Days_Left"] = df["Days_Left"].apply(lambda x: x if x > 0 else 1)
    return df

def compute_no_match(rapid_df):
    cols = ['min_age', 'max_age', 'Gender', 'Final Completes', 'Region', 'Expected_End_Date', 'Code']
    if 'Project_ID' in rapid_df.columns:
        cols.insert(0, 'Project_ID')

    NoMatch = rapid_df[rapid_df['match_method'] == 'no_match'][cols].copy()
    NoMatch = calcular_days_left(NoMatch, "Expected_End_Date")
    NoMatch["Completes_Per_Day"] = (NoMatch["Final Completes"] / NoMatch["Days_Left"]).round().astype(int)

    # Ajusta nomes e mantém apenas as colunas desejadas
    NoMatch = NoMatch.rename(columns={
        'Completes_Per_Day': 'Completes',
        'Code': 'Country'
    })

    # Reordena e remove o que não é necessário
    colunas_finais = ['Project_ID', 'Country', 'Completes', 'min_age', 'max_age', 'Gender', 'Region']
    NoMatch = NoMatch[[c for c in colunas_finais if c in NoMatch.columns]]

    NoMatch = NoMatch.sort_values(by='Country').reset_index(drop=True)
    return NoMatch


def redistribute_completes_integer(row):
    """Distribui completas inteiras entre as idades do intervalo."""
    min_age, max_age, completes = int(row["min_age"]), int(row["max_age"]), int(row["Final Completes"])
    min_age = max(min_age, 18)
    max_age = min(max_age, 99)
    ages_range = list(range(min_age, max_age + 1))
    if len(ages_range) == 0 or completes <= 0:
        return pd.Series({age: 0 for age in AGES})

    counts = np.zeros(len(ages_range), dtype=int)
    chosen_indices = np.random.default_rng(seed=42).choice(range(len(ages_range)), completes, replace=True)
    for i in chosen_indices:
        counts[i] += 1

    data = {age: 0 for age in AGES}
    for idx, age in enumerate(ages_range):
        data[age] = counts[idx]
    return pd.Series(data)

def assign_agegroup(row):
    # “Any” se pedido 18-99; senão 18-45 e 45+
    if int(row["min_age"]) == 18 and int(row["max_age"]) == 99:
        return "Any"
    elif int(row["Age"]) <= 45:
        return "18to45"
    else:
        return "45+"

def compute_final_match(Match):
    FinalMatch = Match[['min_age','max_age','Gender','Final Completes','matched_region','Expected_End_Date','Code','regions_count','cpi']].copy()
    # Expande por idade (inteira e reprodutível)
    age_expanded = FinalMatch.apply(redistribute_completes_integer, axis=1)
    age_expanded["Code"] = FinalMatch["Code"].values
    age_expanded["matched_region"] = FinalMatch["matched_region"].values
    age_expanded["index_original"] = FinalMatch.index
    age_expanded["min_age"] = FinalMatch["min_age"].values
    age_expanded["max_age"] = FinalMatch["max_age"].values
    age_expanded

    age_melted = age_expanded.melt(
    id_vars=["Code", "matched_region", "index_original", "min_age", "max_age"],
    var_name="Age",
    value_name="Completes"
    )

    age_melted["Age"] = age_melted["Age"].astype(int)
    age_melted["AgeGroup"] = age_melted.apply(assign_agegroup, axis=1)
    age_grouped = (
    age_melted.groupby(["index_original", "Code", "matched_region", "AgeGroup"], as_index=False)["Completes"]
    .sum()
    .astype({"Completes": int})
    )

    FinalMatch2 = FinalMatch.merge(age_grouped, left_index=True, right_on="index_original", how="left", suffixes=("", "_dup"))
    FinalMatch2 = FinalMatch2.drop(columns=["index_original"])
    for col in ["Code", "matched_region"]:
        dup = f"{col}_dup"
    if dup in FinalMatch2.columns:
        FinalMatch2[col] = FinalMatch2[dup]
        FinalMatch2.drop(columns=[dup], inplace=True)

        # KPI por dia
    FinalMatch2 = calcular_days_left(FinalMatch2, "Expected_End_Date")
    FinalMatch2["Completes_Per_Day"] = (FinalMatch2["Completes"] / FinalMatch2["Days_Left"]).round().astype(int)
    FinalMatch2 = FinalMatch2[FinalMatch2["Completes_Per_Day"] > 0].reset_index(drop=True)

    # Desnormaliza matched_region (se múltiplas, dividir proporcionalmente)
    df = FinalMatch2.copy()
    df["matched_region"] = df["matched_region"].astype(str)
    df["region_list"] = df["matched_region"].str.split(",")
    df = df.explode("region_list").reset_index(drop=True)
    df["region_list"] = df["region_list"].str.strip()

        # Conta quantas regiões cada linha tinha (por chave original)
        # Como explodimos e perdemos o índice original, aproximamos dividindo por contagem por (Code, Gender, AgeGroup, Expected_End_Date)
        # (Para fidelidade máxima, o método original usava index_original; aqui mantemos consistência prática)
        # Para manter 1:1 com seu script, vamos fazer por linha pós-explosão:
    df["region_split_count"] = df.groupby(df.index)["region_list"].transform("count")

    df["Completes"] = (df["Completes"] / df["region_split_count"]).round().astype(int)
    df["Completes_Per_Day"] = (df["Completes_Per_Day"] / df["region_split_count"]).round().astype(int)
    df = df[df["Completes"] > 0].reset_index(drop=True)
    df["matched_region"] = df["region_list"]
    FinalMatch3 = df.drop(columns=["region_list", "region_split_count"])

    # Agrega final para o layout do e-mail
    FinalMatch3 = (
        FinalMatch3[['Gender','matched_region','Code','AgeGroup','Completes_Per_Day','cpi']]
        .groupby(['Gender','matched_region','Code','AgeGroup'], as_index=False)
        .agg({'Completes_Per_Day':'sum', 'cpi':'mean'})  # soma completes, média de CPI
        .rename(columns={'matched_region':'region','Completes_Per_Day':'Completes','cpi':'CPI'})
    )

    FinalMatch3['region'] = FinalMatch3['region'].replace('Nacional','National')

    return FinalMatch3

