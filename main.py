# main.py (trechos)
from config import EMAIL, PATHS
from database_handler import connect_db, query_recruitments, query_specs, query_completes
from utils.file_handler import criar_dataframe
from data_preprocessing import parse_comments_and_transform, merge_specs_and_compute, attach_completes_and_filter
from region_matcher import build_country_groups, generate_rapidfuzzRecruitments
from recruitment_calculator import compute_no_match, compute_final_match
from email_builder import build_email_html, send_email, sort_with_nacional_first
from currency_handler import fetch_usd_quotes, adjust_cpi_to_usd  
from conversion_rate_handler import build_conversion_rate, merge_with_conversion


import pandas as pd
from datetime import datetime

def main():
    conn = connect_db()
    cursor = conn.cursor()

    # 2) Recruitments
    rec_raw = query_recruitments(cursor)
    Recruitments = criar_dataframe(rec_raw, cursor)
    requests_by_country = (
        Recruitments.groupby("code")["Project_ID"].nunique()
        .reset_index().rename(columns={"Project_ID": "Requests"})
    )

    # 3) Parse comments
    Recruitments = parse_comments_and_transform(Recruitments)

    # 4) Specs
    RecruitmentList = (Recruitments['Project_ID'].astype(str)+' '+Recruitments['Country'].astype(str)).unique().tolist()
    sql_list = ', '.join([f"'{item}'" for item in RecruitmentList])
    Specs = criar_dataframe(query_specs(cursor, sql_list), cursor)
    merged = merge_specs_and_compute(Recruitments, Specs)

    # 5) Completes atuais
    project_ids = ', '.join([f"{item}" for item in merged['Project_ID'].unique().tolist()])
    pp = criar_dataframe(query_completes(cursor, project_ids), cursor)

    # 6) Final Completes > 0
    merged2 = attach_completes_and_filter(merged, pp)

    # >>> NOVO BLOCO DE MOEDAS <<<
    # Se você usa um CSV auxiliar para mapear invoice_currency -> Currency usada no CPI:
    try:
        CurrencyMap = pd.read_csv('Currencies.csv')  # deve ter colunas como ['invoice_currency','Currency']
        merged2 = merged2.merge(CurrencyMap, on='invoice_currency', how='left')
    except FileNotFoundError:
        pass  # segue sem o CSV se não existir

    # Busca cotações USD->alvos e converte CPI para USD
    quotes = fetch_usd_quotes()
    merged2 = adjust_cpi_to_usd(merged2, quotes, left_currency_col="Currency")

    # 7) Locals.csv → grupos por país
    df_ref = pd.read_csv(PATHS["locals_csv"])
    country_groups, df_ref_norm = build_country_groups(df_ref)

    # 8) Fuzzy
    rapidfuzzRecruitments = generate_rapidfuzzRecruitments(merged2, df_ref_norm, country_groups)

    # 9) NoMatch
    NoMatch = compute_no_match(rapidfuzzRecruitments)

        # 10) Match e agregação final
    Match = rapidfuzzRecruitments[rapidfuzzRecruitments['match_method'] != 'no_match'].copy()
    FinalMatch = compute_final_match(Match)

    # >>> NOVA ETAPA: Conversion Rate + Panelists <<<
    conversion_df = build_conversion_rate(cursor)
    FinalMatch = merge_with_conversion(FinalMatch, conversion_df)

    # 11) Ordenação com National primeiro
    colunas = ["Code", "region", "AgeGroup", "Gender", "Completes", "CPI", "Panelists"]
    FinalMatch_display = FinalMatch[colunas].sort_values(["Code", "region", "AgeGroup", "Gender"])
    FinalMatch_display = FinalMatch_display.groupby("Code", group_keys=False).apply(sort_with_nacional_first)

    # 12) Excel
    timestamp = datetime.now().strftime("%Y-%m-%d_%Hh%M")
    file_name = f"Recruitment_{timestamp}.xlsx"
    FinalMatch.sort_values(by=['Code', 'region']).to_excel(file_name, index=False)

    # 13) E-mail
    email_html = build_email_html(FinalMatch_display, NoMatch, requests_by_country)
    send_email(
        sender=EMAIL["sender"],
        password=EMAIL["password"],
        recipients=EMAIL["to"],
        subject=EMAIL["subject"],
        html_body=email_html,
        attachment_path=file_name,
        cc=EMAIL["cc"],
        bcc=EMAIL["bcc"],
    )

if __name__ == "__main__":
    main()
