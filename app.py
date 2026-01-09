"""
Dashboard Financeiro - Grupo Progresso
Contas a Pagar (Nao-Intercompany)

Autor: Grupo Progresso
Versao: 3.0 (Multi-page)
"""
import streamlit as st
import warnings
warnings.filterwarnings('ignore')

# Configuracao da pagina (deve ser a primeira chamada Streamlit)
from config.settings import PAGE_CONFIG, INTERCOMPANY_PATTERNS
st.set_page_config(**PAGE_CONFIG)

# Imports apos configuracao
from datetime import datetime

from config.theme import get_cores, get_css
from data.loader import carregar_dados, aplicar_filtros, get_opcoes_filtros, get_dados_filtrados, calcular_metricas
from components.navbar import render_navbar, render_page_header
from components.sidebar import render_sidebar
from utils.formatters import formatar_numero

from tabs.visao_geral import render_visao_geral
from tabs.vencimentos import render_vencimentos
from tabs.fornecedores import render_fornecedores
from tabs.categorias import render_categorias
from tabs.formas_pagamento import render_formas_pagamento
from tabs.adiantamentos import render_adiantamentos
from tabs.custos_financeiros import render_custos_financeiros
from tabs.detalhes import render_detalhes


# Funções com @st.fragment para evitar rerun completo da página
@st.fragment
def fragment_vencimentos(df):
    render_vencimentos(df)

@st.fragment
def fragment_fornecedores(df):
    render_fornecedores(df)

@st.fragment
def fragment_categorias(df):
    render_categorias(df)

@st.fragment
def fragment_formas_pagamento(df):
    render_formas_pagamento(df)

@st.fragment
def fragment_detalhes(df):
    render_detalhes(df)


def main():
    """Funcao principal do dashboard"""

    # Inicializar tema
    if 'tema_escuro' not in st.session_state:
        st.session_state.tema_escuro = True

    cores = get_cores()

    # Aplicar CSS
    st.markdown(get_css(), unsafe_allow_html=True)

    # NavBar com filtros rapidos de tempo
    datas_navbar = render_navbar(pagina_atual='pagar', mostrar_filtro_tempo=True)

    # Carregar dados
    df_contas, df_adiant, df_baixas = carregar_dados()

    # Excluir fornecedores Intercompany dos dados principais (ANTES de tudo)
    # Padroes importados de config/settings.py (fonte unica)
    mask_intercompany = df_contas['NOME_FORNECEDOR'].str.upper().str.contains('|'.join(INTERCOMPANY_PATTERNS), na=False, regex=True)
    df_contas_sem_ic = df_contas[~mask_intercompany].copy()

    # Obter opcoes de filtros (SEM intercompany)
    filiais_opcoes, categorias_opcoes = get_opcoes_filtros(df_contas_sem_ic)

    # Datas do filtro rapido da navbar
    data_inicio, data_fim = datas_navbar if datas_navbar else (datetime(2000, 1, 1).date(), datetime.now().date())

    # Apenas ajustar data_inicio ao minimo dos dados (nao limitar data_fim)
    data_min = df_contas_sem_ic['EMISSAO'].min().date()
    data_inicio = max(data_inicio, data_min)

    # Renderizar sidebar e obter filtros (SEM intercompany)
    filtro_filial, filtro_status, filtro_categoria, busca_fornecedor, filtro_tipo_doc, filtro_forma_pagto = render_sidebar(
        df_contas_sem_ic, filiais_opcoes, categorias_opcoes
    )

    # Aplicar filtros (sem intercompany)
    df = aplicar_filtros(
        df_contas_sem_ic, data_inicio, data_fim,
        filtro_filial, filtro_status, filtro_categoria, busca_fornecedor,
        filtro_tipo_doc, filtro_forma_pagto
    )
    df_pendentes, df_vencidos = get_dados_filtrados(df, df_contas_sem_ic)

    # Calcular metricas
    metricas = calcular_metricas(df, df_vencidos)

    # Page Header
    render_page_header(
        titulo="Contas a Pagar",
        subtitulo=f"{formatar_numero(metricas['qtd_total'])} titulos | {data_inicio.strftime('%d/%m/%Y')} - {data_fim.strftime('%d/%m/%Y')}",
        icone="CP",
        cor=cores['primaria']
    )

    # Tabs (8 tabs)
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "Visao Geral", "Vencimentos", "Fornecedores", "Categorias",
        "Formas Pagto", "Custos Financ.", "Adiantamentos", "Detalhes"
    ])

    with tab1:
        # KPIs e alertas apenas na Visao Geral
        render_visao_geral(df, df_pendentes, df_vencidos, metricas)

    with tab2:
        fragment_vencimentos(df)

    with tab3:
        fragment_fornecedores(df)

    with tab4:
        fragment_categorias(df)

    with tab5:
        fragment_formas_pagamento(df)

    with tab6:
        render_custos_financeiros(df)

    with tab7:
        render_adiantamentos(df_adiant, df_baixas)

    with tab8:
        fragment_detalhes(df)

    # Footer
    hoje = datetime.now()
    st.divider()
    st.caption(f"Grupo Progresso - Dashboard Financeiro | Atualizado em {hoje.strftime('%d/%m/%Y %H:%M')}")


if __name__ == "__main__":
    main()
