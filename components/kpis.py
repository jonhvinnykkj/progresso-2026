"""
Componente de KPIs/Métricas
"""
import streamlit as st
from config.theme import get_cores
from utils.formatters import formatar_moeda, formatar_numero, formatar_delta, calcular_variacao
from datetime import datetime


def render_kpis(df, df_vencidos, df_contas, metricas):
    """Renderiza os KPIs principais do dashboard com destaque para vencidos"""
    cores = get_cores()

    # Layout: 4 KPIs normais + 1 KPI destacado (vencido)
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total", formatar_moeda(metricas['total']), f"{formatar_numero(metricas['qtd_total'])} titulos")

    with col2:
        st.metric("Pago", formatar_moeda(metricas['pago']), f"{metricas['pct_pago']:.1f}%")

    with col3:
        st.metric("Pendente", formatar_moeda(metricas['pendente']))

    with col4:
        st.metric("Atraso Medio", f"{metricas['dias_atraso']:.0f} dias")

    # Card destacado para VENCIDOS (crítico)
    if metricas['vencido'] > 0:
        pct_vencido = (metricas['vencido'] / metricas['pendente'] * 100) if metricas['pendente'] > 0 else 0
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
                    border-radius: 12px; padding: 1rem 1.5rem; margin: 1rem 0;
                    box-shadow: 0 4px 15px rgba(220, 53, 69, 0.3);">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <p style="color: rgba(255,255,255,0.8); font-size: 0.75rem; margin: 0;
                              text-transform: uppercase; letter-spacing: 1px;">VENCIDO - ATENCAO</p>
                    <p style="color: white; font-size: 2rem; font-weight: 700; margin: 0.25rem 0;">
                        {formatar_moeda(metricas['vencido'])}
                    </p>
                </div>
                <div style="text-align: right;">
                    <p style="color: white; font-size: 1.5rem; font-weight: 600; margin: 0;">
                        {formatar_numero(metricas['qtd_vencidos'])} titulos
                    </p>
                    <p style="color: rgba(255,255,255,0.8); font-size: 0.85rem; margin: 0;">
                        {pct_vencido:.1f}% do pendente
                    </p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


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
