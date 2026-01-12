"""
Aba Visao Geral - Overview Executivo - Contas a Receber
Design limpo e moderno
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

from config.theme import get_cores
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero


def render_visao_geral_receber(df):
    """Renderiza a aba Visao Geral com design moderno"""
    cores = get_cores()

    if len(df) == 0:
        st.warning("Nenhum dado disponivel.")
        return

    # Calcular metricas
    df_pendentes = df[df['SALDO'] > 0]
    df_vencidos = df[df['STATUS'] == 'Vencido']
    df_recebidos = df[df['SALDO'] == 0]

    total = df['VALOR_ORIGINAL'].sum()
    recebido = total - df['SALDO'].sum()
    pendente = df['SALDO'].sum()
    vencido = df_vencidos['SALDO'].sum()
    pct_recebido = (recebido / total * 100) if total > 0 else 0
    pct_vencido = (vencido / pendente * 100) if pendente > 0 else 0

    # Métricas de performance (DSO e Pontualidade)
    dso_medio = 0
    taxa_pontual = 0
    taxa_renegociacao = 0

    if 'DSO' in df_recebidos.columns:
        df_dso_valid = df_recebidos[df_recebidos['DSO'].notna() & (df_recebidos['DSO'] > 0)]
        dso_medio = df_dso_valid['DSO'].mean() if len(df_dso_valid) > 0 else 0

    if 'PONTUAL' in df_recebidos.columns:
        df_pont_valid = df_recebidos[df_recebidos['PONTUAL'].notna()]
        taxa_pontual = (df_pont_valid['PONTUAL'].sum() / len(df_pont_valid) * 100) if len(df_pont_valid) > 0 else 0

    if 'RENEGOCIADO' in df.columns:
        taxa_renegociacao = (df['RENEGOCIADO'].sum() / len(df) * 100) if len(df) > 0 else 0

    # ========== CARDS PRINCIPAIS ==========
    st.markdown(f"""
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1.5rem;">
        <div style="background: linear-gradient(135deg, {cores['sucesso']}20 0%, {cores['sucesso']}10 100%);
                    border: 1px solid {cores['sucesso']}40; border-radius: 12px; padding: 1.25rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0 0 0.5rem 0;">Total Emitido</p>
            <p style="color: {cores['texto']}; font-size: 1.5rem; font-weight: 700; margin: 0;">{formatar_moeda(total)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0.25rem 0 0 0;">{formatar_numero(len(df))} titulos</p>
        </div>
        <div style="background: linear-gradient(135deg, {cores['info']}20 0%, {cores['info']}10 100%);
                    border: 1px solid {cores['info']}40; border-radius: 12px; padding: 1.25rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0 0 0.5rem 0;">Recebido</p>
            <p style="color: {cores['sucesso']}; font-size: 1.5rem; font-weight: 700; margin: 0;">{formatar_moeda(recebido)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0.25rem 0 0 0;">{pct_recebido:.1f}% do total</p>
        </div>
        <div style="background: linear-gradient(135deg, {cores['alerta']}20 0%, {cores['alerta']}10 100%);
                    border: 1px solid {cores['alerta']}40; border-radius: 12px; padding: 1.25rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0 0 0.5rem 0;">A Receber</p>
            <p style="color: {cores['alerta']}; font-size: 1.5rem; font-weight: 700; margin: 0;">{formatar_moeda(pendente)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0.25rem 0 0 0;">{formatar_numero(len(df_pendentes))} titulos pendentes</p>
        </div>
        <div style="background: linear-gradient(135deg, {cores['perigo']}20 0%, {cores['perigo']}10 100%);
                    border: 1px solid {cores['perigo']}40; border-radius: 12px; padding: 1.25rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0 0 0.5rem 0;">Vencido</p>
            <p style="color: {cores['perigo']}; font-size: 1.5rem; font-weight: 700; margin: 0;">{formatar_moeda(vencido)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0.25rem 0 0 0;">{pct_vencido:.1f}% do pendente</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ========== CARDS DE PERFORMANCE ==========
    cor_dso = cores['sucesso'] if dso_medio <= 30 else (cores['alerta'] if dso_medio <= 60 else cores['perigo'])
    cor_pont = cores['sucesso'] if taxa_pontual >= 80 else (cores['alerta'] if taxa_pontual >= 60 else cores['perigo'])
    cor_reneg = cores['sucesso'] if taxa_renegociacao <= 10 else (cores['alerta'] if taxa_renegociacao <= 25 else cores['perigo'])

    st.markdown(f"""
    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-bottom: 1.5rem;">
        <div style="background: {cores['card']}; border: 1px solid {cores['borda']}; border-left: 4px solid {cor_dso};
                    border-radius: 0 12px 12px 0; padding: 1rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0;">DSO Medio</p>
            <p style="color: {cor_dso}; font-size: 1.75rem; font-weight: 700; margin: 0;">{dso_medio:.0f} dias</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">Prazo medio de recebimento</p>
        </div>
        <div style="background: {cores['card']}; border: 1px solid {cores['borda']}; border-left: 4px solid {cor_pont};
                    border-radius: 0 12px 12px 0; padding: 1rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0;">Taxa Pontualidade</p>
            <p style="color: {cor_pont}; font-size: 1.75rem; font-weight: 700; margin: 0;">{taxa_pontual:.1f}%</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">Recebido no prazo</p>
        </div>
        <div style="background: {cores['card']}; border: 1px solid {cores['borda']}; border-left: 4px solid {cor_reneg};
                    border-radius: 0 12px 12px 0; padding: 1rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0;">Taxa Renegociacao</p>
            <p style="color: {cor_reneg}; font-size: 1.75rem; font-weight: 700; margin: 0;">{taxa_renegociacao:.1f}%</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">Titulos prorrogados</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ========== BARRA DE PROGRESSO ==========
    st.markdown(f"""
    <div style="background: {cores['card']}; border: 1px solid {cores['borda']}; border-radius: 12px; padding: 1rem; margin-bottom: 1.5rem;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
            <span style="color: {cores['texto']}; font-weight: 600;">Taxa de Recebimento</span>
            <span style="color: {cores['sucesso']}; font-weight: 700;">{pct_recebido:.1f}%</span>
        </div>
        <div style="background: {cores['borda']}; border-radius: 8px; height: 12px; overflow: hidden;">
            <div style="background: linear-gradient(90deg, {cores['sucesso']} 0%, {cores['primaria']} 100%);
                        width: {min(pct_recebido, 100):.1f}%; height: 100%; border-radius: 8px;"></div>
        </div>
        <div style="display: flex; justify-content: space-between; margin-top: 0.5rem;">
            <span style="color: {cores['texto_secundario']}; font-size: 0.75rem;">Recebido: {formatar_moeda(recebido)}</span>
            <span style="color: {cores['texto_secundario']}; font-size: 0.75rem;">Meta: {formatar_moeda(total)}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ========== AGING CARDS ==========
    _render_aging_cards(df_pendentes, cores)

    st.divider()

    # ========== GRAFICOS ==========
    col1, col2 = st.columns(2)

    with col1:
        _render_donut_status(df, cores)

    with col2:
        _render_top_clientes(df_pendentes, cores)

    st.divider()

    # ========== EVOLUCAO ==========
    _render_evolucao_mensal(df, cores)


def _render_aging_cards(df_pendentes, cores):
    """Cards de aging com design limpo"""

    # Calcular valores por faixa
    vencido = df_pendentes[df_pendentes['STATUS'] == 'Vencido']['SALDO'].sum()
    qtd_vencido = len(df_pendentes[df_pendentes['STATUS'] == 'Vencido'])

    vence_7d = df_pendentes[df_pendentes['STATUS'] == 'Vence em 7 dias']['SALDO'].sum()
    qtd_7d = len(df_pendentes[df_pendentes['STATUS'] == 'Vence em 7 dias'])

    vence_15d = df_pendentes[df_pendentes['STATUS'] == 'Vence em 15 dias']['SALDO'].sum()
    qtd_15d = len(df_pendentes[df_pendentes['STATUS'] == 'Vence em 15 dias'])

    vence_30d = df_pendentes[df_pendentes['STATUS'] == 'Vence em 30 dias']['SALDO'].sum()
    qtd_30d = len(df_pendentes[df_pendentes['STATUS'] == 'Vence em 30 dias'])

    st.markdown(f"""
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.75rem;">
        <div style="background: {cores['card']}; border-left: 4px solid {cores['perigo']};
                    border-radius: 0 8px 8px 0; padding: 1rem;">
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                <div style="width: 8px; height: 8px; background: {cores['perigo']}; border-radius: 50%;"></div>
                <span style="color: {cores['texto_secundario']}; font-size: 0.75rem; text-transform: uppercase;">Vencido</span>
            </div>
            <p style="color: {cores['perigo']}; font-size: 1.25rem; font-weight: 700; margin: 0;">{formatar_moeda(vencido)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0.25rem 0 0 0;">{formatar_numero(qtd_vencido)} titulos</p>
        </div>
        <div style="background: {cores['card']}; border-left: 4px solid {cores['alerta']};
                    border-radius: 0 8px 8px 0; padding: 1rem;">
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                <div style="width: 8px; height: 8px; background: {cores['alerta']}; border-radius: 50%;"></div>
                <span style="color: {cores['texto_secundario']}; font-size: 0.75rem; text-transform: uppercase;">Vence em 7 dias</span>
            </div>
            <p style="color: {cores['alerta']}; font-size: 1.25rem; font-weight: 700; margin: 0;">{formatar_moeda(vence_7d)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0.25rem 0 0 0;">{formatar_numero(qtd_7d)} titulos</p>
        </div>
        <div style="background: {cores['card']}; border-left: 4px solid {cores['info']};
                    border-radius: 0 8px 8px 0; padding: 1rem;">
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                <div style="width: 8px; height: 8px; background: {cores['info']}; border-radius: 50%;"></div>
                <span style="color: {cores['texto_secundario']}; font-size: 0.75rem; text-transform: uppercase;">Vence em 15 dias</span>
            </div>
            <p style="color: {cores['info']}; font-size: 1.25rem; font-weight: 700; margin: 0;">{formatar_moeda(vence_15d)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0.25rem 0 0 0;">{formatar_numero(qtd_15d)} titulos</p>
        </div>
        <div style="background: {cores['card']}; border-left: 4px solid {cores['sucesso']};
                    border-radius: 0 8px 8px 0; padding: 1rem;">
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                <div style="width: 8px; height: 8px; background: {cores['sucesso']}; border-radius: 50%;"></div>
                <span style="color: {cores['texto_secundario']}; font-size: 0.75rem; text-transform: uppercase;">Vence em 30 dias</span>
            </div>
            <p style="color: {cores['sucesso']}; font-size: 1.25rem; font-weight: 700; margin: 0;">{formatar_moeda(vence_30d)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0.25rem 0 0 0;">{formatar_numero(qtd_30d)} titulos</p>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _render_donut_status(df, cores):
    """Donut chart de status"""

    st.markdown("##### Composicao por Status")

    # Agrupar por status
    df_status = df.groupby('STATUS').agg({
        'SALDO': 'sum',
        'VALOR_ORIGINAL': 'count'
    }).reset_index()
    df_status.columns = ['Status', 'Valor', 'Qtd']
    df_status = df_status[df_status['Valor'] > 0].sort_values('Valor', ascending=False)

    cores_status = {
        'Recebido': cores['sucesso'],
        'Vencido': cores['perigo'],
        'Vence em 7 dias': cores['alerta'],
        'Vence em 15 dias': '#f59e0b',
        'Vence em 30 dias': cores['info'],
        'Vence em 60 dias': '#8b5cf6',
        'Vence em +60 dias': cores['texto_secundario']
    }

    fig = go.Figure(go.Pie(
        labels=df_status['Status'],
        values=df_status['Valor'],
        hole=0.6,
        marker=dict(colors=[cores_status.get(s, cores['info']) for s in df_status['Status']]),
        textinfo='percent',
        textfont=dict(size=11, color='white'),
        hovertemplate='<b>%{label}</b><br>%{value:,.2f}<br>%{percent}<extra></extra>'
    ))

    # Valor central
    total_pendente = df['SALDO'].sum()
    fig.add_annotation(
        text=f"<b>Saldo</b><br>{formatar_moeda(total_pendente)}",
        x=0.5, y=0.5,
        font=dict(size=14, color=cores['texto']),
        showarrow=False
    )

    fig.update_layout(
        criar_layout(320),
        showlegend=True,
        legend=dict(orientation="h", yanchor="top", y=-0.05, xanchor="center", x=0.5, font=dict(size=10)),
        margin=dict(l=20, r=20, t=20, b=60)
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_top_clientes(df_pendentes, cores):
    """Top 5 clientes devedores"""

    st.markdown("##### Top 5 Clientes - Maior Saldo")

    col_cliente = 'NOME_CLIENTE' if 'NOME_CLIENTE' in df_pendentes.columns else 'NOME_FORNECEDOR'

    df_top = df_pendentes.groupby(col_cliente)['SALDO'].sum().nlargest(5).reset_index()
    df_top.columns = ['Cliente', 'Saldo']

    if len(df_top) == 0:
        st.info("Sem dados")
        return

    total = df_top['Saldo'].sum()

    fig = go.Figure(go.Bar(
        y=df_top['Cliente'].str[:25],
        x=df_top['Saldo'],
        orientation='h',
        marker=dict(
            color=df_top['Saldo'],
            colorscale=[[0, cores['info']], [1, cores['sucesso']]],
            showscale=False
        ),
        text=[f"{formatar_moeda(v)} ({v/total*100:.1f}%)" for v in df_top['Saldo']],
        textposition='outside',
        textfont=dict(size=10)
    ))

    fig.update_layout(
        criar_layout(320),
        yaxis={'autorange': 'reversed'},
        margin=dict(l=10, r=120, t=20, b=20)
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_evolucao_mensal(df, cores):
    """Evolucao mensal de emissao e recebimento"""

    st.markdown("##### Evolucao Mensal")

    df_temp = df.copy()
    df_temp['MES'] = df_temp['EMISSAO'].dt.to_period('M')

    df_mes = df_temp.groupby('MES').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum'
    }).reset_index()

    df_mes['MES'] = df_mes['MES'].astype(str)
    df_mes['Recebido'] = df_mes['VALOR_ORIGINAL'] - df_mes['SALDO']
    df_mes['Taxa'] = (df_mes['Recebido'] / df_mes['VALOR_ORIGINAL'] * 100).fillna(0)
    df_mes = df_mes.tail(12)

    if len(df_mes) < 2:
        st.info("Dados insuficientes para evolucao")
        return

    fig = go.Figure()

    # Barras empilhadas
    fig.add_trace(go.Bar(
        x=df_mes['MES'],
        y=df_mes['Recebido'],
        name='Recebido',
        marker_color=cores['sucesso']
    ))

    fig.add_trace(go.Bar(
        x=df_mes['MES'],
        y=df_mes['SALDO'],
        name='Pendente',
        marker_color=cores['alerta']
    ))

    # Linha de taxa
    fig.add_trace(go.Scatter(
        x=df_mes['MES'],
        y=df_mes['Taxa'],
        mode='lines+markers',
        name='% Recebido',
        yaxis='y2',
        line=dict(color=cores['texto'], width=2),
        marker=dict(size=6)
    ))

    fig.update_layout(
        criar_layout(300, barmode='stack'),
        yaxis=dict(title='Valor (R$)'),
        yaxis2=dict(title='% Recebido', overlaying='y', side='right', showgrid=False, range=[0, 105]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)),
        margin=dict(l=10, r=50, t=40, b=40),
        xaxis_tickangle=-45
    )

    st.plotly_chart(fig, use_container_width=True)
