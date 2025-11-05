import re
import pandas as pd
from utils.file_handler import criar_dataframe

PADRAO_REGEX_VALORES = (
    r'Sel:\s*(.*?)\n'
    r'Completes Necessary:\s*(.*?)\n'
    r'Region:\s*(.*)'
)

def parse_comments_and_transform(recruitments_df):
    df_new_cols = recruitments_df['Comments'].str.extract(PADRAO_REGEX_VALORES)
    df_new_cols.columns = ['Sel', 'Completes Necessary', 'Region']
    transformed = pd.concat([recruitments_df.drop('Comments', axis=1), df_new_cols], axis=1)
    transformed['Completes Necessary'] = pd.to_numeric(transformed['Completes Necessary'], errors='coerce')
    return transformed

def merge_specs_and_compute(recruitments_df, specs_df):
    specs_df['Initial_Launch_Date'] = pd.to_datetime(specs_df['Initial_Launch_Date'])
    specs_df['Periodo_Dias'] = pd.to_timedelta(specs_df['Days_in_Field'], unit='D')
    specs_df['Expected_End_Date'] = specs_df['Initial_Launch_Date'] + specs_df['Periodo_Dias']
    specs_df = specs_df.drop(columns=['Periodo_Dias'])

    merged = recruitments_df.merge(
    right=specs_df,
    how='inner',
    on=['Country', 'Project_ID']
    )

    # Garante que o Project_ID continue disponível nas próximas etapas
    if 'Project_ID' not in merged.columns and 'Project_ID' in recruitments_df.columns:
        merged['Project_ID'] = recruitments_df['Project_ID']

    # Remove apenas colunas realmente redundantes
    cols_to_drop = [c for c in ['Country', 'code', 'Days_in_Field', 'Initial_Launch_Date'] if c in merged.columns]
    merged = merged.drop(columns=cols_to_drop)

    return merged


def attach_completes_and_filter(merged_df, completes_df):
    out = merged_df.merge(how='left', right=completes_df, on=['Project_ID', 'Code'])
    out['Completes'] = out['Completes'].fillna(0)
    out['Final Completes'] = out['Completes Necessary'] - out['Completes']
    out = out[out['Final Completes'] > 0].copy()
    return out

