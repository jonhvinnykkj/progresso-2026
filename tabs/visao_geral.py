"""
Aba Dashboard - Overview Executivo Resumido
Foco: KPIs principais + 2 graficos (status e evolucao)
"""
import streamlit as st
import plotly.graph_objects as go

from config.theme import get_cores
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero
from utils.data_helpers import get_df_pendentes, get_df_vencidos, calcular_metricas_basicas


def render_visao_geral(df):
    """Renderiza a aba Dashboard - Overview executivo resumido"""
    cores = get_cores()

    # Calcular dados internamente
    df_pendentes = get_df_pendentes(df)
    df_vencidos = get_df_vencidos(df)
    metricas = calcular_metricas_basicas(df)

    # Resumo Executivo com KPIs
    _render_resumo_executivo(df, df_pendentes, metricas, cores)

    st.divider()

    # Dois graficos principais lado a lado
    col1, col2 = st.columns(2)

    with col1:
        _render_donut_status(df, cores)

    with col2:
        _render_evolucao_ultimos_meses(df, cores)


def _render_resumo_executivo(df, df_pendentes, metricas, cores):
    """Resumo executivo com KPIs e insights"""

    total = metricas['total']
    pago = metricas['pago']
    pendente = metricas['pendente']
    vencido = metricas['vencido']
    pct_pago = metricas['pct_pago']

    # Calcular insights
    valor_7d = df_pendentes[df_pendentes['STATUS'] == 'Vence em 7 dias']['SALDO'].sum()

    # Top categoria
    if len(df) > 0:
        top_cat = df.groupby('DESCRICAO')['VALOR_ORIGINAL'].sum().idxmax()
        pct_top_cat = df.groupby('DESCRICAO')['VALOR_ORIGINAL'].sum().max() / total * 100
    else:
        top_cat = "N/A"
        pct_top_cat = 0

    # Definir status geral
    if vencido > pendente * 0.3:
        status_geral = "Critico"
        delta_status = "Alto risco"
        delta_color = "inverse"
    elif vencido > pendente * 0.1:
        status_geral = "Atencao"
        delta_status = "Moderado"
        delta_color = "off"
    else:
        status_geral = "Saudavel"
        delta_status = "Baixo risco"
        delta_color = "normal"

    # KPIs em colunas
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            label="Status Financeiro",
            value=status_geral,
            delta=delta_status,
            delta_color=delta_color
        )

    with col2:
        st.metric(
            label="Total Periodo",
            value=formatar_moeda(total),
            delta=f"{formatar_numero(metricas['qtd_total'])} titulos",
            delta_color="off"
        )

    with col3:
        st.metric(
            label="Pago",
            value=formatar_moeda(pago),
            delta=f"{pct_pago:.1f}% do total",
            delta_color="off"
        )

    with col4:
        st.metric(
            label="Pendente",
            value=formatar_moeda(pendente),
            delta="A pagar",
            delta_color="off"
        )

    with col5:
        st.metric(
            label="Vencido",
            value=formatar_moeda(vencido),
            delta=f"{formatar_numero(metricas['qtd_vencidos'])} titulos",
            delta_color="off"
        )

    # Insights
    if valor_7d > 0:
        insight_7d = f"Proximos 7 dias: **{formatar_moeda(valor_7d)}** a vencer."
    else:
        insight_7d = "Sem vencimentos criticos nos proximos 7 dias."

    st.info(f"Principal categoria: **{top_cat}** ({pct_top_cat:.1f}% do valor). {insight_7d}")


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
