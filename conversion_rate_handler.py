import pandas as pd
from database_handler import query_conversion_rate, query_latam
from utils.file_handler import criar_dataframe

def build_conversion_rate(cursor) -> pd.DataFrame:
    """Gera tabela final de ConversionRate por região, faixa etária e gênero, preservando capitalização."""
    conv_raw = query_conversion_rate(cursor)
    Conversion_Rate = criar_dataframe(conv_raw, cursor)
    panelist_ids = Conversion_Rate["ID"].unique().tolist()

    latam = criar_dataframe(query_latam(cursor, panelist_ids), cursor)
    latamtranslate = pd.read_csv("Latam.csv")

    latam = latam.merge(Conversion_Rate, on="ID", how="inner")
    latam = latam.merge(
        latamtranslate,
        left_on=["Region ID", "Country"],
        right_on=["Region ID", "Country ID"],
        how="inner"
    )
    latam = latam[["Code", "Gender", "Age", "Starts", "Completes", "Name"]].rename(columns={"Name": "region"})

    df = latam.copy()
    df["AgeGroup"] = df["Age"].apply(lambda x: "18to45" if x <= 45 else "45+")
    df["Gender"] = df["Gender"].map({1: "Male", 2: "Female"})

    def conversion_rate(df_group):
        starts = df_group["Starts"].sum()
        completes = df_group["Completes"].sum()
        return completes / starts if starts > 0 else 0

    # --- Regionais ---
    base = df.groupby(["Code", "region", "AgeGroup", "Gender"]).apply(conversion_rate).reset_index(name="ConversionRate")
    both_age = df.groupby(["Code", "region", "AgeGroup"]).apply(conversion_rate).reset_index(name="ConversionRate")
    both_age["Gender"] = "Both"
    any_age = df.groupby(["Code", "region", "Gender"]).apply(conversion_rate).reset_index(name="ConversionRate")
    any_age["AgeGroup"] = "Any"
    both_any = df.groupby(["Code", "region"]).apply(conversion_rate).reset_index(name="ConversionRate")
    both_any["Gender"], both_any["AgeGroup"] = "Both", "Any"

    regional = pd.concat([base, both_age, any_age, both_any], ignore_index=True)

    # --- Nacionais ---
    national = df.groupby(["Code", "AgeGroup", "Gender"]).apply(conversion_rate).reset_index(name="ConversionRate")
    national["region"] = "National"

    national_both_age = df.groupby(["Code", "AgeGroup"]).apply(conversion_rate).reset_index(name="ConversionRate")
    national_both_age["Gender"], national_both_age["region"] = "Both", "National"

    national_any_gender = df.groupby(["Code", "Gender"]).apply(conversion_rate).reset_index(name="ConversionRate")
    national_any_gender["AgeGroup"], national_any_gender["region"] = "Any", "National"

    national_both_any = df.groupby(["Code"]).apply(conversion_rate).reset_index(name="ConversionRate")
    national_both_any["Gender"], national_both_any["AgeGroup"], national_both_any["region"] = "Both", "Any", "National"

    national_all = pd.concat([national, national_both_age, national_any_gender, national_both_any], ignore_index=True)
    final = pd.concat([regional, national_all], ignore_index=True)

    # --- Normalização leve (sem lowercase) ---
    final["region"] = (
        final["region"].astype(str)
        .str.strip()
        .str.normalize("NFKD")
        .str.encode("ascii", "ignore")
        .str.decode("utf-8")
    )
    final["Code"] = final["Code"].astype(str).str.strip().str.upper()
    return final


def merge_with_conversion(FinalMatch3: pd.DataFrame, conversion_df: pd.DataFrame) -> pd.DataFrame:
    """Faz o merge de FinalMatch3 com ConversionRate e calcula painelistas estimados."""
    FinalMatch3 = FinalMatch3.copy()

    FinalMatch3["region"] = (
        FinalMatch3["region"].astype(str)
        .str.strip()
        .str.normalize("NFKD")
        .str.encode("ascii", "ignore")
        .str.decode("utf-8")
    )
    FinalMatch3["Code"] = FinalMatch3["Code"].astype(str).str.strip().str.upper()
    FinalMatch3["Gender"] = FinalMatch3["Gender"].replace({1: "Male", 2: "Female"})

    merged = FinalMatch3.merge(conversion_df, on=["region", "Code", "Gender", "AgeGroup"], how="left")
    merged["Panelists"] = (merged["Completes"] / merged["ConversionRate"]).replace([float("inf"), pd.NA], 0)
    merged["Panelists"] = merged["Panelists"].fillna(0).astype(float).round().astype(int)
    merged = merged.drop(columns=["ConversionRate"], errors="ignore")
    return merged
