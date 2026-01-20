"""
Dashboard Financeiro - Grupo Progresso
Contas a Receber

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
from data.loader_receber import (
    carregar_dados_receber,
    aplicar_filtros_receber,
    get_opcoes_filtros_receber,
    get_dados_filtrados_receber,
    calcular_metricas_receber
)
from components.header_receber import render_header_receber
from components.sidebar_receber import render_sidebar_receber
from components.kpis import render_kpis
from components.alerts import render_alerts, render_alert_cards

from tabs_receber.visao_geral import render_visao_geral_receber
from tabs_receber.vencimentos import render_vencimentos_receber
from tabs_receber.clientes import render_clientes
from tabs_receber.categorias import render_categorias_receber
from tabs_receber.evolucao import render_evolucao_receber
from tabs_receber.adiantamentos import render_adiantamentos_receber
from tabs_receber.detalhes import render_detalhes_receber
from tabs_receber.analise_avancada import render_analise_avancada_receber


# Funções com @st.fragment para evitar rerun completo da página
@st.fragment
def fragment_vencimentos(df):
    render_vencimentos_receber(df)

@st.fragment
def fragment_clientes(df):
    render_clientes(df)

@st.fragment
def fragment_categorias(df):
    render_categorias_receber(df)

@st.fragment
def fragment_evolucao(df):
    render_evolucao_receber(df)

@st.fragment
def fragment_detalhes(df):
    render_detalhes_receber(df)

@st.fragment
def fragment_analise_avancada(df):
    render_analise_avancada_receber(df)


def main():
    """Função principal do dashboard"""

    # Inicializar tema
    if 'tema_escuro' not in st.session_state:
        st.session_state.tema_escuro = True

    # Aplicar CSS
    st.markdown(get_css(), unsafe_allow_html=True)

    # Carregar dados
    df_contas, df_adiant, df_baixas = carregar_dados_receber()
    filiais_opcoes, categorias_opcoes = get_opcoes_filtros_receber(df_contas)

    # Renderizar sidebar e obter filtros
    data_inicio, data_fim, filtro_filial, filtro_status, filtro_categoria, busca_cliente, filtro_tipo_doc = render_sidebar_receber(
        df_contas, filiais_opcoes, categorias_opcoes
    )

    # Aplicar filtros
    df = aplicar_filtros_receber(
        df_contas, data_inicio, data_fim,
        filtro_filial, filtro_status, filtro_categoria, busca_cliente, filtro_tipo_doc
    )
    df_pendentes, df_vencidos = get_dados_filtrados_receber(df, df_contas)

    # Calcular métricas
    metricas = calcular_metricas_receber(df, df_vencidos)

    # Header
    render_header_receber(metricas['qtd_total'], data_inicio, data_fim)

    # KPIs adaptados para Receber
    _render_kpis_receber(df, df_vencidos, df_contas, metricas)

    st.markdown("<br>", unsafe_allow_html=True)

    # Alertas adaptados
    _render_alerts_receber(df_pendentes, df_vencidos, metricas)

    st.markdown("<br>", unsafe_allow_html=True)

    # Tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "Visão Geral", "Vencimentos", "Clientes", "Categorias",
        "Evolução", "Adiantamentos", "Detalhes", "Análise Avançada"
    ])

    with tab1:
        render_visao_geral_receber(df)

    with tab2:
        fragment_vencimentos(df)

    with tab3:
        fragment_clientes(df)

    with tab4:
        fragment_categorias(df)

    with tab5:
        fragment_evolucao(df)

    with tab6:
        render_adiantamentos_receber(df_adiant, df_baixas)

    with tab7:
        fragment_detalhes(df)

    with tab8:
        fragment_analise_avancada(df)

    # Footer
    hoje = datetime.now()
    st.divider()
    st.caption(f"Grupo Progresso - Dashboard Financeiro | Atualizado em {hoje.strftime('%d/%m/%Y %H:%M')}")


def _render_kpis_receber(df, df_vencidos, df_contas, metricas):
    """Renderiza KPIs específicos para Contas a Receber"""
    from utils.formatters import formatar_moeda, formatar_numero
    from config.theme import get_cores

    cores = get_cores()

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Total a Receber</div>
            <div class="kpi-value">{formatar_moeda(metricas['total'])}</div>
            <div class="kpi-delta">{formatar_numero(metricas['qtd_total'])} títulos</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Recebido</div>
            <div class="kpi-value" style="color: {cores['sucesso']};">{formatar_moeda(metricas['recebido'])}</div>
            <div class="kpi-delta">{metricas['pct_recebido']:.1f}% do total</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Pendente</div>
            <div class="kpi-value" style="color: {cores['alerta']};">{formatar_moeda(metricas['pendente'])}</div>
            <div class="kpi-delta">A receber</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Vencido</div>
            <div class="kpi-value" style="color: {cores['perigo']};">{formatar_moeda(metricas['vencido'])}</div>
            <div class="kpi-delta">{formatar_numero(metricas['qtd_vencidos'])} títulos</div>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        dias = int(metricas['dias_atraso']) if metricas['dias_atraso'] > 0 else 0
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Atraso Médio</div>
            <div class="kpi-value">{dias} dias</div>
            <div class="kpi-delta">Títulos vencidos</div>
        </div>
        """, unsafe_allow_html=True)


def _render_alerts_receber(df_pendentes, df_vencidos, metricas):
    """Renderiza alertas específicos para Contas a Receber"""
    from utils.formatters import formatar_moeda, formatar_numero

    # Alertas de vencimento
    vence_7d = df_pendentes[df_pendentes['STATUS'] == 'Vence em 7 dias']['SALDO'].sum()
    qtd_7d = len(df_pendentes[df_pendentes['STATUS'] == 'Vence em 7 dias'])

    col1, col2, col3 = st.columns(3)

    with col1:
        if metricas['vencido'] > 0:
            st.error(f"**{formatar_numero(metricas['qtd_vencidos'])}** títulos vencidos totalizando **{formatar_moeda(metricas['vencido'])}**")
        else:
            st.success("Nenhum título vencido!")

    with col2:
        if vence_7d > 0:
            st.warning(f"**{formatar_numero(qtd_7d)}** títulos vencem em 7 dias: **{formatar_moeda(vence_7d)}**")
        else:
            st.info("Nenhum vencimento crítico nos próximos 7 dias")

    with col3:
        pct_receb = metricas['pct_recebido']
        if pct_receb >= 80:
            st.success(f"Taxa de recebimento: **{pct_receb:.1f}%** - Excelente!")
        elif pct_receb >= 50:
            st.info(f"Taxa de recebimento: **{pct_receb:.1f}%** - Bom")
        else:
            st.warning(f"Taxa de recebimento: **{pct_receb:.1f}%** - Atenção")


if __name__ == "__main__":
    main()
