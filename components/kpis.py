"""
Componente de KPIs/Métricas
"""
import streamlit as st
from config.theme import get_cores
from utils.formatters import formatar_moeda, formatar_numero, formatar_delta, calcular_variacao
from datetime import datetime


def render_kpis(df, df_vencidos, df_contas, metricas):
    """Renderiza os KPIs principais do dashboard"""
    cores = get_cores()
    hoje = datetime.now()

    # Calcular variação vs mês anterior
    mes_atual = hoje.month
    ano_atual = hoje.year
    mes_anterior = mes_atual - 1 if mes_atual > 1 else 12
    ano_mes_anterior = ano_atual if mes_atual > 1 else ano_atual - 1

    df_mes_atual = df_contas[(df_contas['EMISSAO'].dt.month == mes_atual) & (df_contas['EMISSAO'].dt.year == ano_atual)]
    df_mes_anterior = df_contas[(df_contas['EMISSAO'].dt.month == mes_anterior) & (df_contas['EMISSAO'].dt.year == ano_mes_anterior)]

    pendente_mes_atual = df_mes_atual['SALDO'].sum()
    pendente_mes_anterior = df_mes_anterior['SALDO'].sum()
    var_pendente = calcular_variacao(pendente_mes_atual, pendente_mes_anterior)

    # Renderizar KPIs
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total", formatar_moeda(metricas['total']), f"{formatar_numero(metricas['qtd_total'])} títulos")
    col2.metric("Pago", formatar_moeda(metricas['pago']), f"{metricas['pct_pago']:.1f}%")
    col3.metric("Pendente", formatar_moeda(metricas['pendente']), formatar_delta(var_pendente), delta_color="inverse")
    col4.metric("Vencido", formatar_moeda(metricas['vencido']), f"{formatar_numero(metricas['qtd_vencidos'])} títulos", delta_color="inverse")
    col5.metric("Atraso Médio", f"{metricas['dias_atraso']:.0f} dias")


def render_kpis_detalhados(metricas, cores=None):
    """Renderiza KPIs com visual mais detalhado"""
    if cores is None:
        cores = get_cores()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="resumo-card">
            <div class="titulo">Total Geral</div>
            <div class="valor" style="color: {cores['primaria']}">{formatar_moeda(metricas['total'])}</div>
            <div class="subtitulo">{formatar_numero(metricas['qtd_total'])} títulos</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="resumo-card">
            <div class="titulo">Valor Pago</div>
            <div class="valor" style="color: {cores['sucesso']}">{formatar_moeda(metricas['pago'])}</div>
            <div class="subtitulo">{metricas['pct_pago']:.1f}% do total</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="resumo-card">
            <div class="titulo">Pendente</div>
            <div class="valor" style="color: {cores['alerta']}">{formatar_moeda(metricas['pendente'])}</div>
            <div class="subtitulo">A pagar</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="resumo-card">
            <div class="titulo">Vencido</div>
            <div class="valor" style="color: {cores['perigo']}">{formatar_moeda(metricas['vencido'])}</div>
            <div class="subtitulo">{formatar_numero(metricas['qtd_vencidos'])} títulos | {metricas['dias_atraso']:.0f} dias médio</div>
        </div>
        """, unsafe_allow_html=True)
