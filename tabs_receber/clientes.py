"""
Aba Clientes - Análise completa por cliente - Contas a Receber
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

from config.theme import get_cores
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero


def get_df_pendentes(df):
    return df[df['SALDO'] > 0]


def render_clientes(df):
    """Renderiza a aba de Clientes"""
    cores = get_cores()

    if len(df) == 0:
        st.warning("Nenhum dado disponivel para o periodo selecionado.")
        return

    df_pendentes = get_df_pendentes(df)

    # KPIs de resumo
    _render_kpis_clientes(df, df_pendentes, cores)

    st.divider()

    # Linha 1: Top Valor + Top Pendente
    col1, col2 = st.columns(2)

    with col1:
        _render_top_valor_total(df, cores)

    with col2:
        _render_top_saldo_pendente(df_pendentes, cores)

    st.divider()

    # Linha 2: Concentração ABC + Dispersão
    col1, col2 = st.columns(2)

    with col1:
        _render_concentracao_abc(df, cores)

    with col2:
        _render_scatter_clientes(df, cores)

    st.divider()

    # NOVO: Aging por Cliente + Clientes Críticos
    col1, col2 = st.columns(2)

    with col1:
        _render_aging_por_cliente(df_pendentes, cores)

    with col2:
        _render_clientes_criticos(df, df_pendentes, cores)

    st.divider()

    # NOVO: Heatmap Cliente x Mês + Top por Filial
    col1, col2 = st.columns(2)

    with col1:
        _render_heatmap_cliente_mes(df, cores)

    with col2:
        _render_top_clientes_por_filial(df, cores)

    st.divider()

    # Performance de Recebimento por Cliente
    _render_performance_clientes(df, cores)

    st.divider()

    # Busca e detalhes de cliente
    _render_busca_cliente(df, df_pendentes, cores)

    st.divider()

    # Ranking completo
    _render_ranking_completo(df, df_pendentes, cores)


def _render_kpis_clientes(df, df_pendentes, cores):
    """KPIs de resumo de clientes"""

    total_clientes = df['NOME_CLIENTE'].nunique()
    total_valor = df['VALOR_ORIGINAL'].sum()
    total_pendente = df_pendentes['SALDO'].sum() if len(df_pendentes) > 0 else 0

    df_cli_sum = df.groupby('NOME_CLIENTE')['VALOR_ORIGINAL'].sum()
    if len(df_cli_sum) > 0:
        top_cli = df_cli_sum.idxmax()
        top_cli_valor = df_cli_sum.max()
        pct_top = (top_cli_valor / total_valor * 100) if total_valor > 0 else 0
    else:
        top_cli = "N/A"
        top_cli_valor = 0
        pct_top = 0

    if len(df_cli_sum) > 0:
        df_conc = df_cli_sum.sort_values(ascending=False)
        df_conc_cum = df_conc.cumsum() / df_conc.sum() * 100
        cli_80 = (df_conc_cum <= 80).sum()
    else:
        cli_80 = 0

    ticket_medio = total_valor / len(df) if len(df) > 0 else 0

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            label="Total Clientes",
            value=formatar_numero(total_clientes),
            delta=f"{formatar_numero(len(df))} títulos",
            delta_color="off"
        )

    with col2:
        st.metric(
            label="Valor Total",
            value=formatar_moeda(total_valor),
            delta=f"Pendente: {formatar_moeda(total_pendente)}",
            delta_color="off"
        )

    with col3:
        top_cli_display = top_cli[:20] + "..." if len(str(top_cli)) > 20 else top_cli
        st.metric(
            label="Maior Cliente",
            value=top_cli_display,
            delta=f"{pct_top:.1f}% do total",
            delta_color="off"
        )

    with col4:
        pct_cli = (cli_80/total_clientes*100) if total_clientes > 0 else 0
        st.metric(
            label="Concentração 80%",
            value=f"{cli_80} clientes",
            delta=f"{pct_cli:.1f}% do total",
            delta_color="off"
        )

    with col5:
        st.metric(
            label="Ticket Médio",
            value=formatar_moeda(ticket_medio),
            delta="Por título",
            delta_color="off"
        )


def _render_top_valor_total(df, cores):
    """Top 10 clientes por valor total"""

    st.markdown("##### Top 10 - Valor Total")

    df_cli = df.groupby('NOME_CLIENTE').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'CLIENTE': 'count'
    }).nlargest(10, 'VALOR_ORIGINAL').reset_index()

    df_cli['RECEBIDO'] = df_cli['VALOR_ORIGINAL'] - df_cli['SALDO']

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=df_cli['NOME_CLIENTE'].str[:25],
        x=df_cli['RECEBIDO'],
        orientation='h',
        name='Recebido',
        marker_color=cores['sucesso'],
        text=[formatar_moeda(v) for v in df_cli['RECEBIDO']],
        textposition='inside',
        textfont=dict(size=9, color='white')
    ))

    fig.add_trace(go.Bar(
        y=df_cli['NOME_CLIENTE'].str[:25],
        x=df_cli['SALDO'],
        orientation='h',
        name='Pendente',
        marker_color=cores['alerta'],
        text=[formatar_moeda(v) for v in df_cli['SALDO']],
        textposition='inside',
        textfont=dict(size=9, color='white')
    ))

    fig.update_layout(
        criar_layout(300, barmode='stack'),
        yaxis={'autorange': 'reversed'},
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=30, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_top_saldo_pendente(df_pendentes, cores):
    """Top 10 clientes com mais pendente"""

    st.markdown("##### Top 10 - Saldo Pendente")

    df_pend = df_pendentes.groupby('NOME_CLIENTE').agg({
        'SALDO': 'sum',
        'DIAS_ATRASO': 'max',
        'CLIENTE': 'count'
    }).nlargest(10, 'SALDO').reset_index()

    def get_color(dias):
        if dias > 30:
            return cores['perigo']
        elif dias > 15:
            return cores['alerta']
        elif dias > 0:
            return '#fbbf24'
        else:
            return cores['primaria']

    colors = [get_color(d) for d in df_pend['DIAS_ATRASO']]

    fig = go.Figure(go.Bar(
        y=df_pend['NOME_CLIENTE'].str[:25],
        x=df_pend['SALDO'],
        orientation='h',
        marker_color=colors,
        text=[f"{formatar_moeda(v)} ({int(d)}d)" for v, d in zip(df_pend['SALDO'], df_pend['DIAS_ATRASO'])],
        textposition='outside',
        textfont=dict(size=9)
    ))

    fig.update_layout(
        criar_layout(300),
        yaxis={'autorange': 'reversed'},
        margin=dict(l=10, r=80, t=10, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)

    st.caption("Cores: Em dia | 1-15d | 16-30d | +30d atraso")


def _render_concentracao_abc(df, cores):
    """Análise ABC de clientes"""

    st.markdown("##### Curva ABC - Concentração")

    df_abc = df.groupby('NOME_CLIENTE')['VALOR_ORIGINAL'].sum().sort_values(ascending=False).reset_index()
    total = df_abc['VALOR_ORIGINAL'].sum()
    df_abc['PCT'] = df_abc['VALOR_ORIGINAL'] / total * 100
    df_abc['PCT_ACUM'] = df_abc['PCT'].cumsum()
    df_abc['RANK'] = range(1, len(df_abc) + 1)

    df_abc['CLASSE'] = df_abc['PCT_ACUM'].apply(
        lambda x: 'A' if x <= 80 else ('B' if x <= 95 else 'C')
    )

    fig = go.Figure()

    cores_abc = {'A': cores['primaria'], 'B': cores['alerta'], 'C': cores['info']}
    fig.add_trace(go.Bar(
        x=df_abc['RANK'][:30],
        y=df_abc['VALOR_ORIGINAL'][:30],
        name='Valor',
        marker_color=[cores_abc[c] for c in df_abc['CLASSE'][:30]]
    ))

    fig.add_trace(go.Scatter(
        x=df_abc['RANK'][:30],
        y=df_abc['PCT_ACUM'][:30],
        name='% Acumulado',
        mode='lines+markers',
        line=dict(color=cores['texto'], width=2),
        yaxis='y2'
    ))

    fig.add_hline(y=80, line_dash="dash", line_color=cores['sucesso'], yref='y2')
    fig.add_hline(y=95, line_dash="dash", line_color=cores['alerta'], yref='y2')

    fig.update_layout(
        criar_layout(300),
        yaxis2=dict(overlaying='y', side='right', range=[0, 105], showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=40, t=30, b=30),
        xaxis_title="Rank Cliente"
    )

    st.plotly_chart(fig, use_container_width=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        qtd_a = len(df_abc[df_abc['CLASSE'] == 'A'])
        st.success(f"**A**: {qtd_a} cli. (80% valor)")
    with col2:
        qtd_b = len(df_abc[df_abc['CLASSE'] == 'B'])
        st.warning(f"**B**: {qtd_b} cli. (15% valor)")
    with col3:
        qtd_c = len(df_abc[df_abc['CLASSE'] == 'C'])
        st.info(f"**C**: {qtd_c} cli. (5% valor)")


def _render_aging_por_cliente(df_pendentes, cores):
    """Aging por cliente - faixas de vencimento"""

    st.markdown("##### Aging por Cliente (Top 15)")

    if len(df_pendentes) == 0:
        st.info("Sem titulos pendentes")
        return

    # Calcular faixas de aging
    df_aging = df_pendentes.copy()
    df_aging['FAIXA'] = pd.cut(
        df_aging['DIAS_ATRASO'],
        bins=[-float('inf'), 0, 30, 60, 90, float('inf')],
        labels=['A Vencer', '1-30d', '31-60d', '61-90d', '+90d']
    )

    # Agrupar por cliente e faixa
    df_pivot = df_aging.groupby(['NOME_CLIENTE', 'FAIXA'])['SALDO'].sum().unstack(fill_value=0)

    # Top 15 por saldo total
    df_pivot['TOTAL'] = df_pivot.sum(axis=1)
    df_pivot = df_pivot.nlargest(15, 'TOTAL')
    df_pivot = df_pivot.drop(columns=['TOTAL'])

    # Criar grafico de barras empilhadas
    fig = go.Figure()

    cores_faixas = {
        'A Vencer': cores['primaria'],
        '1-30d': cores['alerta'],
        '31-60d': '#f97316',
        '61-90d': cores['perigo'],
        '+90d': '#7f1d1d'
    }

    for faixa in ['A Vencer', '1-30d', '31-60d', '61-90d', '+90d']:
        if faixa in df_pivot.columns:
            fig.add_trace(go.Bar(
                y=df_pivot.index.str[:20],
                x=df_pivot[faixa],
                orientation='h',
                name=faixa,
                marker_color=cores_faixas.get(faixa, cores['info']),
                text=[formatar_moeda(v) if v > 0 else '' for v in df_pivot[faixa]],
                textposition='inside',
                textfont=dict(size=8, color='white')
            ))

    fig.update_layout(
        criar_layout(350, barmode='stack'),
        yaxis={'autorange': 'reversed'},
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=40, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_clientes_criticos(df, df_pendentes, cores):
    """Clientes críticos - alto valor + alto % vencido"""

    st.markdown("##### Clientes Críticos (Risco)")

    if len(df_pendentes) == 0:
        st.info("Sem titulos pendentes")
        return

    # Calcular métricas por cliente
    df_cli = df.groupby('NOME_CLIENTE').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum'
    }).reset_index()

    df_vencido = df_pendentes[df_pendentes['DIAS_ATRASO'] > 0].groupby('NOME_CLIENTE').agg({
        'SALDO': 'sum',
        'DIAS_ATRASO': 'max'
    }).reset_index()
    df_vencido.columns = ['NOME_CLIENTE', 'VENCIDO', 'DIAS_MAX']

    df_cli = df_cli.merge(df_vencido, on='NOME_CLIENTE', how='left')
    df_cli['VENCIDO'] = df_cli['VENCIDO'].fillna(0)
    df_cli['DIAS_MAX'] = df_cli['DIAS_MAX'].fillna(0)
    df_cli['PCT_VENCIDO'] = (df_cli['VENCIDO'] / df_cli['SALDO'] * 100).fillna(0)

    # Score de risco: Valor vencido * (dias atraso / 30)
    df_cli['SCORE_RISCO'] = df_cli['VENCIDO'] * (1 + df_cli['DIAS_MAX'] / 30)

    # Top 10 críticos
    df_criticos = df_cli[df_cli['VENCIDO'] > 0].nlargest(10, 'SCORE_RISCO')

    if len(df_criticos) == 0:
        st.success("Nenhum cliente com titulos vencidos!")
        return

    fig = go.Figure()

    # Barra de vencido
    fig.add_trace(go.Bar(
        y=df_criticos['NOME_CLIENTE'].str[:20],
        x=df_criticos['VENCIDO'],
        orientation='h',
        marker_color=cores['perigo'],
        text=[f"{formatar_moeda(v)} | {int(d)}d" for v, d in zip(df_criticos['VENCIDO'], df_criticos['DIAS_MAX'])],
        textposition='outside',
        textfont=dict(size=9)
    ))

    fig.update_layout(
        criar_layout(350),
        yaxis={'autorange': 'reversed'},
        margin=dict(l=10, r=100, t=10, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)

    # Resumo
    total_critico = df_criticos['VENCIDO'].sum()
    st.error(f"**Total em Risco:** {formatar_moeda(total_critico)} | **{len(df_criticos)} clientes**")


def _render_heatmap_cliente_mes(df, cores):
    """Heatmap de valores por cliente x mês"""

    st.markdown("##### Heatmap: Cliente x Mês")

    df_heat = df.copy()
    df_heat['MES'] = df_heat['EMISSAO'].dt.to_period('M').astype(str)

    # Top 12 clientes por valor
    top_clientes = df_heat.groupby('NOME_CLIENTE')['VALOR_ORIGINAL'].sum().nlargest(12).index.tolist()
    df_heat = df_heat[df_heat['NOME_CLIENTE'].isin(top_clientes)]

    # Pivot
    df_pivot = df_heat.groupby(['NOME_CLIENTE', 'MES'])['VALOR_ORIGINAL'].sum().unstack(fill_value=0)

    # Ultimos 6 meses
    if len(df_pivot.columns) > 6:
        df_pivot = df_pivot[df_pivot.columns[-6:]]

    if len(df_pivot) == 0 or len(df_pivot.columns) == 0:
        st.info("Dados insuficientes para heatmap")
        return

    # Formatar nomes dos meses
    meses_formatados = [m[-5:] for m in df_pivot.columns]

    fig = go.Figure(data=go.Heatmap(
        z=df_pivot.values,
        x=meses_formatados,
        y=df_pivot.index.str[:18],
        colorscale=[
            [0, cores['card']],
            [0.5, cores['primaria']],
            [1, cores['sucesso']]
        ],
        text=[[formatar_moeda(v) for v in row] for row in df_pivot.values],
        texttemplate="%{text}",
        textfont=dict(size=8),
        hovertemplate="Cliente: %{y}<br>Mês: %{x}<br>Valor: %{text}<extra></extra>"
    ))

    fig.update_layout(
        criar_layout(350),
        xaxis_title="Mês",
        margin=dict(l=10, r=10, t=10, b=40)
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_top_clientes_por_filial(df, cores):
    """Top clientes por filial"""

    st.markdown("##### Top Clientes por Filial")

    if 'NOME_FILIAL' not in df.columns:
        st.info("Coluna NOME_FILIAL nao disponivel")
        return

    # Selecionar filial
    filiais = sorted(df['NOME_FILIAL'].dropna().unique().tolist())
    if len(filiais) == 0:
        st.info("Sem dados de filiais")
        return

    filial_sel = st.selectbox("Filial", filiais, key="filial_top_cli")

    df_filial = df[df['NOME_FILIAL'] == filial_sel]

    # Top 10 por valor
    df_top = df_filial.groupby('NOME_CLIENTE').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'CLIENTE': 'count'
    }).nlargest(10, 'VALOR_ORIGINAL').reset_index()

    df_top['RECEBIDO'] = df_top['VALOR_ORIGINAL'] - df_top['SALDO']

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=df_top['NOME_CLIENTE'].str[:20],
        x=df_top['RECEBIDO'],
        orientation='h',
        name='Recebido',
        marker_color=cores['sucesso'],
        text=[formatar_moeda(v) for v in df_top['RECEBIDO']],
        textposition='inside',
        textfont=dict(size=8, color='white')
    ))

    fig.add_trace(go.Bar(
        y=df_top['NOME_CLIENTE'].str[:20],
        x=df_top['SALDO'],
        orientation='h',
        name='Pendente',
        marker_color=cores['alerta'],
        text=[formatar_moeda(v) for v in df_top['SALDO']],
        textposition='inside',
        textfont=dict(size=8, color='white')
    ))

    fig.update_layout(
        criar_layout(280, barmode='stack'),
        yaxis={'autorange': 'reversed'},
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=30, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)

    # Resumo da filial
    total_filial = df_filial['VALOR_ORIGINAL'].sum()
    total_pend = df_filial['SALDO'].sum()
    st.caption(f"Total Filial: {formatar_moeda(total_filial)} | Pendente: {formatar_moeda(total_pend)}")


def _render_scatter_clientes(df, cores):
    """Scatter plot: Valor Total vs % Pendente"""

    st.markdown("##### Análise: Valor vs Pendência")

    df_scatter = df.groupby('NOME_CLIENTE').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'CLIENTE': 'count'
    }).reset_index()

    df_scatter['PCT_PENDENTE'] = (df_scatter['SALDO'] / df_scatter['VALOR_ORIGINAL'] * 100).fillna(0)
    df_scatter = df_scatter.nlargest(50, 'VALOR_ORIGINAL')

    fig = px.scatter(
        df_scatter,
        x='VALOR_ORIGINAL',
        y='PCT_PENDENTE',
        size='CLIENTE',
        hover_name='NOME_CLIENTE',
        color='PCT_PENDENTE',
        color_continuous_scale=['#10b981', '#fbbf24', '#ef4444'],
        labels={
            'VALOR_ORIGINAL': 'Valor Total (R$)',
            'PCT_PENDENTE': '% Pendente',
            'CLIENTE': 'Qtd Títulos'
        }
    )

    fig.update_layout(
        criar_layout(300),
        coloraxis_colorbar=dict(title="% Pend."),
        margin=dict(l=10, r=10, t=10, b=40)
    )

    fig.add_hline(y=50, line_dash="dash", line_color=cores['alerta'],
                  annotation_text="50%", annotation_position="right")

    st.plotly_chart(fig, use_container_width=True)

    st.caption("Tamanho = Qtd títulos | Cor = % Pendente")


def _render_performance_clientes(df, cores):
    """Análise de Emissão x Vencimento por cliente"""

    st.markdown("##### Emissão x Vencimento por Cliente")

    if len(df) == 0:
        st.info("Sem dados disponiveis")
        return

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("###### Volume por Mês de Emissão")

        # Agrupar por mês de emissão
        df_emissao = df.copy()
        df_emissao['MES_EMISSAO'] = df_emissao['EMISSAO'].dt.to_period('M').astype(str)

        df_mes_emissao = df_emissao.groupby('MES_EMISSAO').agg({
            'VALOR_ORIGINAL': 'sum',
            'CLIENTE': 'count'
        }).reset_index()
        df_mes_emissao.columns = ['Mês', 'Valor', 'Qtd']

        # Últimos 12 meses
        if len(df_mes_emissao) > 12:
            df_mes_emissao = df_mes_emissao.tail(12)

        if len(df_mes_emissao) > 0:
            fig = go.Figure()

            fig.add_trace(go.Bar(
                x=df_mes_emissao['Mês'],
                y=df_mes_emissao['Valor'],
                marker_color=cores['primaria'],
                text=[formatar_moeda(v) for v in df_mes_emissao['Valor']],
                textposition='outside',
                textfont=dict(size=8)
            ))

            fig.update_layout(
                criar_layout(280),
                xaxis_title='Mês Emissão',
                margin=dict(l=10, r=10, t=10, b=50),
                xaxis=dict(tickangle=-45)
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados de emissão")

    with col2:
        st.markdown("###### Volume por Mês de Vencimento")

        # Agrupar por mês de vencimento
        df_vencimento = df.copy()
        df_vencimento = df_vencimento[df_vencimento['VENCIMENTO'].notna()]
        df_vencimento['MES_VENCIMENTO'] = df_vencimento['VENCIMENTO'].dt.to_period('M').astype(str)

        df_mes_venc = df_vencimento.groupby('MES_VENCIMENTO').agg({
            'VALOR_ORIGINAL': 'sum',
            'SALDO': 'sum',
            'CLIENTE': 'count'
        }).reset_index()
        df_mes_venc.columns = ['Mês', 'Valor', 'Saldo', 'Qtd']

        # Últimos 12 meses
        if len(df_mes_venc) > 12:
            df_mes_venc = df_mes_venc.tail(12)

        if len(df_mes_venc) > 0:
            fig = go.Figure()

            # Valor recebido
            df_mes_venc['Recebido'] = df_mes_venc['Valor'] - df_mes_venc['Saldo']

            fig.add_trace(go.Bar(
                x=df_mes_venc['Mês'],
                y=df_mes_venc['Recebido'],
                name='Recebido',
                marker_color=cores['sucesso']
            ))

            fig.add_trace(go.Bar(
                x=df_mes_venc['Mês'],
                y=df_mes_venc['Saldo'],
                name='Pendente',
                marker_color=cores['alerta']
            ))

            fig.update_layout(
                criar_layout(280, barmode='stack'),
                xaxis_title='Mês Vencimento',
                margin=dict(l=10, r=10, t=10, b=50),
                xaxis=dict(tickangle=-45),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados de vencimento")

    # Tabela comparativa Emissão x Vencimento
    with st.expander("Ver detalhes Emissão x Vencimento", expanded=False):
        df_comp = df.copy()
        df_comp = df_comp[df_comp['EMISSAO'].notna() & df_comp['VENCIMENTO'].notna()]

        # Calcular prazo médio (dias entre emissão e vencimento)
        df_comp['PRAZO'] = (df_comp['VENCIMENTO'] - df_comp['EMISSAO']).dt.days

        df_resumo = df_comp.groupby('NOME_CLIENTE').agg({
            'VALOR_ORIGINAL': 'sum',
            'SALDO': 'sum',
            'PRAZO': 'mean',
            'CLIENTE': 'count'
        }).reset_index()

        df_resumo.columns = ['Cliente', 'Valor Total', 'Saldo', 'Prazo Médio (dias)', 'Qtd Títulos']
        df_resumo['Prazo Médio (dias)'] = df_resumo['Prazo Médio (dias)'].round(0).astype(int)
        df_resumo = df_resumo.sort_values('Valor Total', ascending=False)

        df_resumo['Valor Total'] = df_resumo['Valor Total'].apply(lambda x: formatar_moeda(x, completo=True))
        df_resumo['Saldo'] = df_resumo['Saldo'].apply(lambda x: formatar_moeda(x, completo=True))

        st.dataframe(df_resumo.head(50), use_container_width=True, hide_index=True, height=350)


def _render_busca_cliente(df, df_pendentes, cores):
    """Busca e detalhes de cliente específico"""

    st.markdown("##### Consultar Cliente")

    clientes = sorted([str(c) for c in df['NOME_CLIENTE'].dropna().unique().tolist()])

    col1, col2 = st.columns([3, 1])
    with col1:
        cliente_selecionado = st.selectbox(
            "Selecione um cliente",
            options=[""] + clientes,
            key="busca_cliente_rec"
        )

    if cliente_selecionado:
        df_cli = df[df['NOME_CLIENTE'] == cliente_selecionado]
        df_pend_cli = df_pendentes[df_pendentes['NOME_CLIENTE'] == cliente_selecionado]

        total_valor = df_cli['VALOR_ORIGINAL'].sum()
        total_recebido = total_valor - df_cli['SALDO'].sum()
        total_pendente = df_cli['SALDO'].sum()
        qtd_titulos = len(df_cli)
        pct_recebido = (total_recebido / total_valor * 100) if total_valor > 0 else 0

        vencidos = df_pend_cli[df_pend_cli['STATUS'] == 'Vencido']
        total_vencido = vencidos['SALDO'].sum() if len(vencidos) > 0 else 0
        dias_atraso_max = vencidos['DIAS_ATRASO'].max() if len(vencidos) > 0 else 0

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric("Total", formatar_moeda(total_valor), f"{qtd_titulos} títulos", delta_color="off")
        with col2:
            st.metric("Recebido", formatar_moeda(total_recebido), f"{pct_recebido:.1f}%", delta_color="off")
        with col3:
            st.metric("Pendente", formatar_moeda(total_pendente), delta_color="off")
        with col4:
            st.metric("Vencido", formatar_moeda(total_vencido), delta_color="off")
        with col5:
            if dias_atraso_max > 0:
                st.metric("Maior Atraso", f"{int(dias_atraso_max)} dias", delta_color="off")
            else:
                st.metric("Maior Atraso", "Em dia", delta_color="off")

        st.markdown("###### Histórico de Vendas")

        df_hist = df_cli.copy()
        df_hist['MES'] = df_hist['EMISSAO'].dt.to_period('M').astype(str)
        df_hist_grp = df_hist.groupby('MES').agg({
            'VALOR_ORIGINAL': 'sum',
            'SALDO': 'sum'
        }).reset_index()
        df_hist_grp['RECEBIDO'] = df_hist_grp['VALOR_ORIGINAL'] - df_hist_grp['SALDO']

        if len(df_hist_grp) > 1:
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df_hist_grp['MES'], y=df_hist_grp['RECEBIDO'], name='Recebido', marker_color=cores['sucesso']))
            fig.add_trace(go.Bar(x=df_hist_grp['MES'], y=df_hist_grp['SALDO'], name='Pendente', marker_color=cores['alerta']))
            fig.update_layout(criar_layout(200, barmode='stack'), margin=dict(l=10, r=10, t=10, b=30))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Histórico insuficiente para gráfico")

        with st.expander("Ver títulos do cliente"):
            df_titulos = df_cli[['NOME_FILIAL', 'DESCRICAO', 'EMISSAO', 'VENCIMENTO', 'VALOR_ORIGINAL', 'SALDO', 'STATUS']].copy()
            df_titulos['EMISSAO'] = df_titulos['EMISSAO'].dt.strftime('%d/%m/%Y')
            df_titulos['VENCIMENTO'] = df_titulos['VENCIMENTO'].dt.strftime('%d/%m/%Y')
            df_titulos['VALOR_ORIGINAL'] = df_titulos['VALOR_ORIGINAL'].apply(lambda x: formatar_moeda(x, completo=True))
            df_titulos['SALDO'] = df_titulos['SALDO'].apply(lambda x: formatar_moeda(x, completo=True))
            df_titulos.columns = ['Filial', 'Categoria', 'Emissão', 'Vencimento', 'Valor', 'Saldo', 'Status']
            st.dataframe(df_titulos, use_container_width=True, hide_index=True, height=300)


def _render_ranking_completo(df, df_pendentes, cores):
    """Ranking completo com filtros"""

    st.markdown("##### Ranking de Clientes")

    col1, col2, col3 = st.columns(3)
    with col1:
        ordenar = st.selectbox("Ordenar por", ["Valor Total", "Saldo Pendente", "Qtd Títulos", "% Pendente"], key="ord_rank_cli")
    with col2:
        qtd_exibir = st.selectbox("Exibir", [20, 50, 100, "Todos"], key="qtd_rank_cli")
    with col3:
        filtro_status = st.selectbox("Status", ["Todos", "Com Pendência", "Quitados"], key="status_rank_cli")

    df_rank = df.groupby('NOME_CLIENTE').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'CLIENTE': 'count'
    }).reset_index()

    df_rank.columns = ['Cliente', 'Total', 'Pendente', 'Títulos']
    df_rank['% Recebido'] = ((df_rank['Total'] - df_rank['Pendente']) / df_rank['Total'] * 100).round(1)
    df_rank['% Pendente'] = (100 - df_rank['% Recebido']).round(1)

    if filtro_status == "Com Pendência":
        df_rank = df_rank[df_rank['Pendente'] > 0]
    elif filtro_status == "Quitados":
        df_rank = df_rank[df_rank['Pendente'] <= 0]

    if ordenar == "Valor Total":
        df_rank = df_rank.sort_values('Total', ascending=False)
    elif ordenar == "Saldo Pendente":
        df_rank = df_rank.sort_values('Pendente', ascending=False)
    elif ordenar == "Qtd Títulos":
        df_rank = df_rank.sort_values('Títulos', ascending=False)
    else:
        df_rank = df_rank.sort_values('% Pendente', ascending=False)

    if qtd_exibir != "Todos":
        df_rank = df_rank.head(qtd_exibir)

    df_show = df_rank.copy()
    df_show['Total'] = df_show['Total'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Pendente'] = df_show['Pendente'].apply(lambda x: formatar_moeda(x, completo=True))

    st.dataframe(
        df_show,
        use_container_width=True,
        hide_index=True,
        height=400,
        column_config={
            "% Recebido": st.column_config.ProgressColumn(
                "% Recebido",
                help="Percentual recebido",
                format="%.1f%%",
                min_value=0,
                max_value=100,
            ),
        }
    )

    st.caption(f"Exibindo {len(df_show)} clientes | Total geral: {formatar_moeda(df['VALOR_ORIGINAL'].sum(), completo=True)}")
