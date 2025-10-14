import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import os 
import plotly

st.set_page_config(layout="wide")
st.title("National Fallout")

# --- Variáveis de Configuração ---
DATA_FILE = 'Treemap Recrutamento.csv' 
VALUE_COL = 'Panelists'
ALL_HIERARCHY_COLS = ['Region', 'Age', 'Gender'] 
FILTER_COL_1 = 'Country'
FILTER_COL_2 = 'Recruit_Source'


# --- 1. CARREGAMENTO E AGRUPAMENTO DE DADOS (USANDO CACHE) ---

@st.cache_data
def load_and_group_data(file_name):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, file_name)
    
    df_seus_dados = pd.DataFrame() 

    if not os.path.exists(file_path):
        st.warning(f"AVISO: O arquivo '{file_name}' não foi encontrado. Gerando dados de demonstração.")
        np.random.seed(42)
        num_rows = 5000
        df_seus_dados = pd.DataFrame({
            FILTER_COL_1: np.random.choice(['Brazil', 'Mexico', 'Argentina'], size=num_rows),
            FILTER_COL_2: np.random.choice(['Social Media', 'Referral', 'Paid Search', 'Other'], size=num_rows),
            'Region': np.random.choice(['North', 'South', 'East', 'West'], size=num_rows),
            'Age': np.random.choice(['18-25', '26-40', '41-55', '55+'], size=num_rows),
            'Gender': np.random.choice(['Male', 'Female'], size=num_rows),
            VALUE_COL: np.random.randint(1, 20, size=num_rows)
        })
    else:
        try:
            df_seus_dados = pd.read_csv(file_path, sep=',')
        except Exception as e:
            st.error(f"Erro ao ler o arquivo CSV. Detalhe: {e}")
            return pd.DataFrame()

    required_cols = [FILTER_COL_1, FILTER_COL_2] + ALL_HIERARCHY_COLS + [VALUE_COL]
    if not all(col in df_seus_dados.columns for col in required_cols):
        st.error(f"Erro: O arquivo deve conter as colunas: {', '.join(required_cols)}")
        return pd.DataFrame()

    group_cols = [FILTER_COL_1, FILTER_COL_2] + ALL_HIERARCHY_COLS
    df_agg = (
        df_seus_dados.groupby(group_cols)[VALUE_COL]
        .sum()
        .reset_index()
        .rename(columns={VALUE_COL: 'Total_Values'})
    )
    return df_agg

df_agg = load_and_group_data(DATA_FILE)

if df_agg.empty:
    st.stop()


# --- 2. WIDGETS DE FILTRO ---

country_list = sorted(df_agg[FILTER_COL_1].unique().tolist())
selected_country = st.sidebar.selectbox(
    f'1. Selecione o {FILTER_COL_1}:',
    options=country_list
)

source_options = sorted(df_agg[FILTER_COL_2].unique().tolist())
selected_sources = st.sidebar.multiselect(
    f'2. Selecione a {FILTER_COL_2}:',
    options=source_options,
    default=source_options 
)

selected_hierarchy = st.sidebar.multiselect(
    '3. Escolha os Níveis do Treemap (Ordem Importa!):',
    options=ALL_HIERARCHY_COLS,
    default=ALL_HIERARCHY_COLS
)


# --- 3. LÓGICA DE FILTRAGEM E PLOTAGEM ---

if selected_country and selected_sources and selected_hierarchy:
    
    df_filtered = df_agg[df_agg[FILTER_COL_1] == selected_country].copy()
    df_filtered = df_filtered[df_filtered[FILTER_COL_2].isin(selected_sources)].copy()

    source_title = 'Geral' if len(selected_sources) == len(source_options) else ', '.join(selected_sources)

    if df_filtered.empty:
        st.warning(f"Não há dados para a combinação: País='{selected_country}' e Fonte(s)='{source_title}'.")
    else:
        df_plot = df_filtered.groupby(selected_hierarchy)['Total_Values'].sum().reset_index()
        
        fig = px.treemap(
            df_plot,
            path=selected_hierarchy, 
            values='Total_Values',
            title=f'Distribuição de {VALUE_COL} em {selected_country} (Fonte: {source_title})',
            color='Total_Values',
            color_continuous_scale='Blues'
        )
        
        # AQUI ESTÁ A MUDANÇA: .2f para formatar em 2 casas decimais
        fig.update_traces(
            textinfo='label+percent parent+percent root',
            hovertemplate=f'{VALUE_COL}: %{{value}}<br>Percentual Pai: %{{percentParent:.2f}}<br>Percentual Total: %{{percentRoot:.2f}}<extra></extra>',
        )

        fig.update_layout(margin = dict(t=50, l=25, r=25, b=25))
        
        st.plotly_chart(fig, use_container_width=True)

elif not selected_hierarchy:
    st.warning("Selecione pelo menos uma categoria (Região, Idade ou Gênero) para montar o Treemap.")
