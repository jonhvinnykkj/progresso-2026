"""
Dashboard Financeiro - Grupo Progresso
Contas a Pagar

Autor: Grupo Progresso
Versão: 2.0 (Refatorado)
"""
import streamlit as st
import warnings
warnings.filterwarnings('ignore')

# Configuração da página (deve ser a primeira chamada Streamlit)
from config.settings import PAGE_CONFIG
st.set_page_config(**PAGE_CONFIG)

# Imports após configuração
from datetime import datetime

from config.theme import get_cores, get_css
from data.loader import carregar_dados, aplicar_filtros, get_opcoes_filtros, get_dados_filtrados, calcular_metricas
from components.header import render_header
from components.sidebar import render_sidebar
from components.kpis import render_kpis
from components.alerts import render_alerts, render_alert_cards

from tabs.visao_geral import render_visao_geral
from tabs.vencimentos import render_vencimentos
from tabs.fornecedores import render_fornecedores
from tabs.categorias import render_categorias
from tabs.evolucao import render_evolucao
from tabs.adiantamentos import render_adiantamentos
from tabs.detalhes import render_detalhes
from tabs.analise_avancada import render_analise_avancada


# Funções com @st.fragment para evitar rerun completo da página
@st.fragment
def fragment_vencimentos(df, df_pendentes, df_vencidos):
    render_vencimentos(df, df_pendentes, df_vencidos)

@st.fragment
def fragment_fornecedores(df, df_pendentes):
    render_fornecedores(df, df_pendentes)

@st.fragment
def fragment_categorias(df):
    render_categorias(df)

@st.fragment
def fragment_evolucao(df, df_contas, df_pendentes):
    render_evolucao(df, df_contas, df_pendentes)

@st.fragment
def fragment_detalhes(df, df_contas):
    render_detalhes(df, df_contas)

@st.fragment
def fragment_analise_avancada(df, df_contas):
    render_analise_avancada(df, df_contas)


def main():
    """Função principal do dashboard"""

    # Inicializar tema
    if 'tema_escuro' not in st.session_state:
        st.session_state.tema_escuro = True

    # Aplicar CSS
    st.markdown(get_css(), unsafe_allow_html=True)

    # Carregar dados
    df_contas, df_adiant, df_baixas = carregar_dados()
    filiais_opcoes, categorias_opcoes = get_opcoes_filtros(df_contas)

    # Renderizar sidebar e obter filtros
    data_inicio, data_fim, filtro_filial, filtro_status, filtro_categoria, busca_fornecedor = render_sidebar(
        df_contas, filiais_opcoes, categorias_opcoes
    )

    # Aplicar filtros
    df = aplicar_filtros(
        df_contas, data_inicio, data_fim,
        filtro_filial, filtro_status, filtro_categoria, busca_fornecedor
    )
    df_pendentes, df_vencidos = get_dados_filtrados(df, df_contas)

    # Calcular métricas
    metricas = calcular_metricas(df, df_vencidos)

    # Header
    render_header(metricas['qtd_total'], data_inicio, data_fim)

    # KPIs
    render_kpis(df, df_vencidos, df_contas, metricas)

    st.markdown("<br>", unsafe_allow_html=True)

    # Alertas
    render_alerts(df_pendentes, df_vencidos, metricas)

    # Cards de alerta
    render_alert_cards(df_pendentes)

    st.markdown("<br>", unsafe_allow_html=True)

    # Tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "Visão Geral", "Vencimentos", "Fornecedores", "Categorias",
        "Evolução", "Adiantamentos", "Detalhes", "Análise Avançada"
    ])

    with tab1:
        render_visao_geral(df, df_pendentes, df_vencidos, metricas)

    with tab2:
        fragment_vencimentos(df, df_pendentes, df_vencidos)

    with tab3:
        fragment_fornecedores(df, df_pendentes)

    with tab4:
        fragment_categorias(df)

    with tab5:
        fragment_evolucao(df, df_contas, df_pendentes)

    with tab6:
        render_adiantamentos(df_adiant, df_baixas)

    with tab7:
        fragment_detalhes(df, df_contas)

    with tab8:
        fragment_analise_avancada(df, df_contas)

    # Footer
    hoje = datetime.now()
    st.divider()
    st.caption(f"Grupo Progresso - Dashboard Financeiro | Atualizado em {hoje.strftime('%d/%m/%Y %H:%M')}")


if __name__ == "__main__":
    main()
