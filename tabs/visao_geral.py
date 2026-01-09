"""
Aba Dashboard - Overview Executivo Resumido
Foco: KPIs principais + graficos de status, evolucao e top fornecedores
"""
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

from config.theme import get_cores
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero


def render_visao_geral(df, df_pendentes=None, df_vencidos=None, metricas=None):
    """Renderiza a aba Dashboard - Overview executivo resumido"""
    cores = get_cores()
    hoje = datetime.now()

    if len(df) == 0:
        st.warning("Nenhum dado disponivel.")
        return

    # Se nao recebeu os dados, calcular internamente (compatibilidade)
    if df_pendentes is None:
        df_pendentes = df[df['SALDO'] > 0]
    if df_vencidos is None:
        df_vencidos = df[df['STATUS'] == 'Vencido']
    if metricas is None:
        total = df['VALOR_ORIGINAL'].sum()
        pago = total - df['SALDO'].sum()
        pendente = df['SALDO'].sum()
        vencido = df_vencidos['SALDO'].sum()
        metricas = {
            'total': total,
            'pago': pago,
            'pendente': pendente,
            'vencido': vencido,
            'pct_pago': (pago / total * 100) if total > 0 else 0,
            'dias_atraso': df_vencidos['DIAS_ATRASO'].mean() if len(df_vencidos) > 0 else 0,
            'qtd_total': len(df),
            'qtd_vencidos': len(df_vencidos)
        }

    pct_vencido = (metricas['vencido'] / metricas['pendente'] * 100) if metricas['pendente'] > 0 else 0

    # ========== CARDS PRINCIPAIS ==========
    st.markdown(f"""
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1.5rem;">
        <div style="background: linear-gradient(135deg, {cores['primaria']}20 0%, {cores['primaria']}10 100%);
                    border: 1px solid {cores['primaria']}40; border-radius: 12px; padding: 1.25rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0 0 0.5rem 0;">Total Emitido</p>
            <p style="color: {cores['texto']}; font-size: 1.5rem; font-weight: 700; margin: 0;">{formatar_moeda(metricas['total'])}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0.25rem 0 0 0;">{formatar_numero(metricas['qtd_total'])} titulos</p>
        </div>
        <div style="background: linear-gradient(135deg, {cores['sucesso']}20 0%, {cores['sucesso']}10 100%);
                    border: 1px solid {cores['sucesso']}40; border-radius: 12px; padding: 1.25rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0 0 0.5rem 0;">Pago</p>
            <p style="color: {cores['sucesso']}; font-size: 1.5rem; font-weight: 700; margin: 0;">{formatar_moeda(metricas['pago'])}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0.25rem 0 0 0;">{metricas['pct_pago']:.1f}% do total</p>
        </div>
        <div style="background: linear-gradient(135deg, {cores['alerta']}20 0%, {cores['alerta']}10 100%);
                    border: 1px solid {cores['alerta']}40; border-radius: 12px; padding: 1.25rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0 0 0.5rem 0;">Pendente</p>
            <p style="color: {cores['alerta']}; font-size: 1.5rem; font-weight: 700; margin: 0;">{formatar_moeda(metricas['pendente'])}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0.25rem 0 0 0;">{100 - metricas['pct_pago']:.1f}% do total</p>
        </div>
        <div style="background: linear-gradient(135deg, {cores['perigo']}20 0%, {cores['perigo']}10 100%);
                    border: 1px solid {cores['perigo']}40; border-radius: 12px; padding: 1.25rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0 0 0.5rem 0;">Vencido</p>
            <p style="color: {cores['perigo']}; font-size: 1.5rem; font-weight: 700; margin: 0;">{formatar_moeda(metricas['vencido'])}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0.25rem 0 0 0;">{pct_vencido:.1f}% do pendente</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ========== BARRA DE PROGRESSO ==========
    st.markdown(f"""
    <div style="background: {cores['card']}; border: 1px solid {cores['borda']}; border-radius: 12px; padding: 1rem; margin-bottom: 1.5rem;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
            <span style="color: {cores['texto']}; font-weight: 600;">Taxa de Pagamento</span>
            <span style="color: {cores['sucesso']}; font-weight: 700;">{metricas['pct_pago']:.1f}%</span>
        </div>
        <div style="background: {cores['borda']}; border-radius: 8px; height: 12px; overflow: hidden;">
            <div style="background: linear-gradient(90deg, {cores['sucesso']} 0%, {cores['primaria']} 100%);
                        width: {min(metricas['pct_pago'], 100):.1f}%; height: 100%; border-radius: 8px;"></div>
        </div>
        <div style="display: flex; justify-content: space-between; margin-top: 0.5rem;">
            <span style="color: {cores['texto_secundario']}; font-size: 0.75rem;">Pago: {formatar_moeda(metricas['pago'])}</span>
            <span style="color: {cores['texto_secundario']}; font-size: 0.75rem;">Meta: {formatar_moeda(metricas['total'])}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ========== CARDS DE AGING ==========
    valor_vence_7d = df_pendentes[df_pendentes['STATUS'] == 'Vence em 7 dias']['SALDO'].sum() if len(df_pendentes) > 0 else 0
    qtd_vence_7d = len(df_pendentes[df_pendentes['STATUS'] == 'Vence em 7 dias']) if len(df_pendentes) > 0 else 0

    valor_vence_15d = df_pendentes[df_pendentes['STATUS'] == 'Vence em 15 dias']['SALDO'].sum() if len(df_pendentes) > 0 else 0
    qtd_vence_15d = len(df_pendentes[df_pendentes['STATUS'] == 'Vence em 15 dias']) if len(df_pendentes) > 0 else 0

    valor_vence_30d = df_pendentes[df_pendentes['STATUS'] == 'Vence em 30 dias']['SALDO'].sum() if len(df_pendentes) > 0 else 0
    qtd_vence_30d = len(df_pendentes[df_pendentes['STATUS'] == 'Vence em 30 dias']) if len(df_pendentes) > 0 else 0

    st.markdown(f"""
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.75rem; margin-bottom: 1.5rem;">
        <div style="background: {cores['card']}; border-left: 4px solid {cores['perigo']};
                    border-radius: 0 10px 10px 0; padding: 1rem;">
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                <div style="width: 10px; height: 10px; background: {cores['perigo']}; border-radius: 50%;"></div>
                <span style="color: {cores['texto_secundario']}; font-size: 0.75rem; text-transform: uppercase; font-weight: 600;">Vencido</span>
            </div>
            <p style="color: {cores['perigo']}; font-size: 1.3rem; font-weight: 700; margin: 0;">{formatar_moeda(metricas['vencido'])}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0.25rem 0 0 0;">{formatar_numero(metricas['qtd_vencidos'])} titulos | {metricas['dias_atraso']:.0f}d medio</p>
        </div>
        <div style="background: {cores['card']}; border-left: 4px solid {cores['alerta']};
                    border-radius: 0 10px 10px 0; padding: 1rem;">
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                <div style="width: 10px; height: 10px; background: {cores['alerta']}; border-radius: 50%;"></div>
                <span style="color: {cores['texto_secundario']}; font-size: 0.75rem; text-transform: uppercase; font-weight: 600;">7 dias</span>
            </div>
            <p style="color: {cores['alerta']}; font-size: 1.3rem; font-weight: 700; margin: 0;">{formatar_moeda(valor_vence_7d)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0.25rem 0 0 0;">{formatar_numero(qtd_vence_7d)} titulos</p>
        </div>
        <div style="background: {cores['card']}; border-left: 4px solid {cores['info']};
                    border-radius: 0 10px 10px 0; padding: 1rem;">
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                <div style="width: 10px; height: 10px; background: {cores['info']}; border-radius: 50%;"></div>
                <span style="color: {cores['texto_secundario']}; font-size: 0.75rem; text-transform: uppercase; font-weight: 600;">15 dias</span>
            </div>
            <p style="color: {cores['info']}; font-size: 1.3rem; font-weight: 700; margin: 0;">{formatar_moeda(valor_vence_15d)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0.25rem 0 0 0;">{formatar_numero(qtd_vence_15d)} titulos</p>
        </div>
        <div style="background: {cores['card']}; border-left: 4px solid {cores['sucesso']};
                    border-radius: 0 10px 10px 0; padding: 1rem;">
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                <div style="width: 10px; height: 10px; background: {cores['sucesso']}; border-radius: 50%;"></div>
                <span style="color: {cores['texto_secundario']}; font-size: 0.75rem; text-transform: uppercase; font-weight: 600;">30 dias</span>
            </div>
            <p style="color: {cores['sucesso']}; font-size: 1.3rem; font-weight: 700; margin: 0;">{formatar_moeda(valor_vence_30d)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0.25rem 0 0 0;">{formatar_numero(qtd_vence_30d)} titulos</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ========== GRAFICOS ==========
    # Linha 1: Graficos principais
    col1, col2 = st.columns(2)

    with col1:
        _render_donut_status(df, cores)

    with col2:
        _render_evolucao_ultimos_meses(df, cores)

    # Linha 2: Proximos vencimentos + Top fornecedores
    col1, col2 = st.columns(2)

    with col1:
        _render_proximos_vencimentos(df_pendentes, cores, hoje)

    with col2:
        _render_top_fornecedores(df_pendentes, cores)


def _render_donut_status(df, cores):
    """Donut chart de distribuicao por status de pagamento"""

    st.markdown("##### Distribuicao por Status")

    # Agrupar por status simplificado
    df_status = df.copy()
    df_status['STATUS_SIMPLES'] = df_status.apply(
        lambda r: 'Pago' if r['SALDO'] <= 0 else ('Vencido' if r['STATUS'] == 'Vencido' else 'Pendente'),
        axis=1
    )

    df_grp = df_status.groupby('STATUS_SIMPLES')['VALOR_ORIGINAL'].sum().reset_index()

    cores_status = {
        'Pago': cores['sucesso'],
        'Pendente': cores['alerta'],
        'Vencido': cores['perigo']
    }

    fig = go.Figure(go.Pie(
        labels=df_grp['STATUS_SIMPLES'],
        values=df_grp['VALOR_ORIGINAL'],
        hole=0.65,
        marker=dict(colors=[cores_status.get(s, cores['info']) for s in df_grp['STATUS_SIMPLES']]),
        textinfo='percent',
        textfont=dict(size=12, color='white'),
        hovertemplate='<b>%{label}</b><br>R$ %{value:,.2f}<br>%{percent}<extra></extra>'
    ))

    # Texto central
    total = df['VALOR_ORIGINAL'].sum()
    fig.add_annotation(
        text=f"<b>{formatar_moeda(total)}</b>",
        x=0.5, y=0.5,
        font=dict(size=16, color=cores['texto']),
        showarrow=False
    )

    fig.update_layout(
        criar_layout(300),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
        margin=dict(l=20, r=20, t=20, b=40)
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_evolucao_ultimos_meses(df, cores):
    """Evolucao dos ultimos 6 meses"""

    st.markdown("##### Evolucao - Ultimos 6 Meses")

    df_tempo = df.copy()
    df_tempo['MES'] = df_tempo['EMISSAO'].dt.to_period('M')

    df_grp = df_tempo.groupby('MES').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum'
    }).reset_index()
    df_grp['MES'] = df_grp['MES'].astype(str)
    df_grp['PAGO'] = df_grp['VALOR_ORIGINAL'] - df_grp['SALDO']
    df_grp = df_grp.tail(6)

    if len(df_grp) > 0:
        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=df_grp['MES'],
            y=df_grp['PAGO'],
            name='Pago',
            marker_color=cores['sucesso']
        ))

        fig.add_trace(go.Bar(
            x=df_grp['MES'],
            y=df_grp['SALDO'],
            name='Pendente',
            marker_color=cores['alerta']
        ))

        fig.update_layout(
            criar_layout(300, barmode='stack'),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=10, r=10, t=30, b=30)
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados suficientes")


def _render_proximos_vencimentos(df_pendentes, cores, hoje):
    """Renderiza proximos vencimentos (30 dias)"""

    st.markdown("##### Proximos Vencimentos (30 dias)")

    if len(df_pendentes) == 0:
        st.info("Sem vencimentos pendentes")
        return

    # Filtrar proximos 30 dias (apenas futuros, nao vencidos)
    df_prox = df_pendentes[
        (df_pendentes['VENCIMENTO'] >= hoje) &
        (df_pendentes['VENCIMENTO'] <= hoje + timedelta(days=30))
    ].copy()

    if len(df_prox) == 0:
        st.success("Nenhum vencimento nos proximos 30 dias")
        return

    # Agrupar por semana de forma clara
    def semana_label(dias):
        if dias <= 7:
            return "Semana 1"
        elif dias <= 14:
            return "Semana 2"
        elif dias <= 21:
            return "Semana 3"
        else:
            return "Semana 4"

    df_prox['PERIODO'] = df_prox['DIAS_VENC'].apply(semana_label)

    ordem = ["Semana 1", "Semana 2", "Semana 3", "Semana 4"]
    df_grp = df_prox.groupby('PERIODO').agg({
        'SALDO': 'sum',
        'FORNECEDOR': 'count'
    }).reindex(ordem, fill_value=0).reset_index()
    df_grp.columns = ['Periodo', 'Valor', 'Qtd']

    # Cores: mais urgente = mais vermelho, menos urgente = mais verde
    cores_periodo = [cores['perigo'], cores['alerta'], '#84cc16', cores['sucesso']]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_grp['Periodo'],
        y=df_grp['Valor'],
        marker_color=cores_periodo,
        text=[f"{formatar_moeda(v)}<br>({int(q)} tit)" for v, q in zip(df_grp['Valor'], df_grp['Qtd'])],
        textposition='outside',
        textfont=dict(size=9)
    ))

    fig.update_layout(
        criar_layout(250),
        margin=dict(l=10, r=10, t=10, b=30),
        xaxis_title=None,
        yaxis_title=None
    )

    st.plotly_chart(fig, use_container_width=True)

    # Legenda explicativa
    st.caption(f"""
    **Semana 1**: Hoje ate {(hoje + timedelta(days=7)).strftime('%d/%m')} |
    **Semana 2**: {(hoje + timedelta(days=8)).strftime('%d/%m')} a {(hoje + timedelta(days=14)).strftime('%d/%m')} |
    **Semana 3**: {(hoje + timedelta(days=15)).strftime('%d/%m')} a {(hoje + timedelta(days=21)).strftime('%d/%m')} |
    **Semana 4**: {(hoje + timedelta(days=22)).strftime('%d/%m')} a {(hoje + timedelta(days=30)).strftime('%d/%m')}
    """)


def _render_top_fornecedores(df_pendentes, cores):
    """Renderiza top fornecedores com saldo pendente"""

    st.markdown("##### Top Fornecedores (Saldo Pendente)")

    if len(df_pendentes) == 0:
        st.info("Sem saldo pendente")
        return

    df_forn = df_pendentes.groupby('NOME_FORNECEDOR')['SALDO'].sum().nlargest(8).reset_index()

    if len(df_forn) == 0:
        st.info("Sem dados")
        return

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=df_forn['NOME_FORNECEDOR'].str[:20],
        x=df_forn['SALDO'],
        orientation='h',
        marker_color=cores['primaria'],
        text=[formatar_moeda(v) for v in df_forn['SALDO']],
        textposition='outside',
        textfont=dict(size=9)
    ))

    fig.update_layout(
        criar_layout(250),
        yaxis={'autorange': 'reversed'},
        margin=dict(l=10, r=60, t=10, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)
