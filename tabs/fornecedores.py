"""
Aba Fornecedores - Análise completa por fornecedor
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

from config.theme import get_cores
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero
from utils.data_helpers import get_df_pendentes


def render_fornecedores(df):
    """Renderiza a aba de Fornecedores"""
    cores = get_cores()

    if len(df) == 0:
        st.warning("Nenhum dado disponivel para o periodo selecionado.")
        return

    # Calcular internamente
    df_pendentes = get_df_pendentes(df)

    # KPIs de resumo
    _render_kpis_fornecedores(df, df_pendentes, cores)

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
        _render_scatter_fornecedores(df, cores)

    st.divider()

    # Busca e detalhes de fornecedor
    _render_busca_fornecedor(df, df_pendentes, cores)

    st.divider()

    # Ranking completo
    _render_ranking_completo(df, df_pendentes, cores)


def _render_kpis_fornecedores(df, df_pendentes, cores):
    """KPIs de resumo de fornecedores"""

    total_fornecedores = df['NOME_FORNECEDOR'].nunique()
    total_valor = df['VALOR_ORIGINAL'].sum()
    total_pendente = df_pendentes['SALDO'].sum() if len(df_pendentes) > 0 else 0

    # Top fornecedor - com verificação de segurança
    df_forn_sum = df.groupby('NOME_FORNECEDOR')['VALOR_ORIGINAL'].sum()
    if len(df_forn_sum) > 0:
        top_forn = df_forn_sum.idxmax()
        top_forn_valor = df_forn_sum.max()
        pct_top = (top_forn_valor / total_valor * 100) if total_valor > 0 else 0
    else:
        top_forn = "N/A"
        top_forn_valor = 0
        pct_top = 0

    # Concentração - quantos representam 80%
    if len(df_forn_sum) > 0:
        df_conc = df_forn_sum.sort_values(ascending=False)
        df_conc_cum = df_conc.cumsum() / df_conc.sum() * 100
        forn_80 = (df_conc_cum <= 80).sum()
    else:
        forn_80 = 0

    # Ticket médio
    ticket_medio = total_valor / len(df) if len(df) > 0 else 0

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            label="🏢 Total Fornecedores",
            value=formatar_numero(total_fornecedores),
            delta=f"{formatar_numero(len(df))} títulos",
            delta_color="off"
        )

    with col2:
        st.metric(
            label="💰 Valor Total",
            value=formatar_moeda(total_valor),
            delta=f"Pendente: {formatar_moeda(total_pendente)}",
            delta_color="off"
        )

    with col3:
        top_forn_display = top_forn[:20] + "..." if len(str(top_forn)) > 20 else top_forn
        st.metric(
            label="🏆 Maior Fornecedor",
            value=top_forn_display,
            delta=f"{pct_top:.1f}% do total",
            delta_color="off"
        )

    with col4:
        pct_forn = (forn_80/total_fornecedores*100) if total_fornecedores > 0 else 0
        st.metric(
            label="📊 Concentração 80%",
            value=f"{forn_80} fornecedores",
            delta=f"{pct_forn:.1f}% do total",
            delta_color="off"
        )

    with col5:
        st.metric(
            label="🎫 Ticket Médio",
            value=formatar_moeda(ticket_medio),
            delta="Por título",
            delta_color="off"
        )


def _render_top_valor_total(df, cores):
    """Top 10 fornecedores por valor total"""

    st.markdown("##### 💰 Top 10 - Valor Total")

    df_forn = df.groupby('NOME_FORNECEDOR').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'FORNECEDOR': 'count'
    }).nlargest(10, 'VALOR_ORIGINAL').reset_index()

    df_forn['PAGO'] = df_forn['VALOR_ORIGINAL'] - df_forn['SALDO']

    fig = go.Figure()

    # Barras empilhadas: Pago + Pendente
    fig.add_trace(go.Bar(
        y=df_forn['NOME_FORNECEDOR'].str[:25],
        x=df_forn['PAGO'],
        orientation='h',
        name='Pago',
        marker_color=cores['sucesso'],
        text=[formatar_moeda(v) for v in df_forn['PAGO']],
        textposition='inside',
        textfont=dict(size=9, color='white')
    ))

    fig.add_trace(go.Bar(
        y=df_forn['NOME_FORNECEDOR'].str[:25],
        x=df_forn['SALDO'],
        orientation='h',
        name='Pendente',
        marker_color=cores['alerta'],
        text=[formatar_moeda(v) for v in df_forn['SALDO']],
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
    """Top 10 fornecedores com mais pendente"""

    st.markdown("##### ⚠️ Top 10 - Saldo Pendente")

    df_pend = df_pendentes.groupby('NOME_FORNECEDOR').agg({
        'SALDO': 'sum',
        'DIAS_ATRASO': 'max',
        'FORNECEDOR': 'count'
    }).nlargest(10, 'SALDO').reset_index()

    # Cor baseada no atraso máximo
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
        y=df_pend['NOME_FORNECEDOR'].str[:25],
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

    st.caption("Cores: 🟢 Em dia | 🟡 1-15d | 🟠 16-30d | 🔴 +30d atraso")


def _render_concentracao_abc(df, cores):
    """Análise ABC de fornecedores"""

    st.markdown("##### 📊 Curva ABC - Concentração")

    df_abc = df.groupby('NOME_FORNECEDOR')['VALOR_ORIGINAL'].sum().sort_values(ascending=False).reset_index()
    total = df_abc['VALOR_ORIGINAL'].sum()
    df_abc['PCT'] = df_abc['VALOR_ORIGINAL'] / total * 100
    df_abc['PCT_ACUM'] = df_abc['PCT'].cumsum()
    df_abc['RANK'] = range(1, len(df_abc) + 1)

    # Classificar ABC
    df_abc['CLASSE'] = df_abc['PCT_ACUM'].apply(
        lambda x: 'A' if x <= 80 else ('B' if x <= 95 else 'C')
    )

    # Gráfico de Pareto
    fig = go.Figure()

    # Barras de valor
    cores_abc = {'A': cores['primaria'], 'B': cores['alerta'], 'C': cores['info']}
    fig.add_trace(go.Bar(
        x=df_abc['RANK'][:30],
        y=df_abc['VALOR_ORIGINAL'][:30],
        name='Valor',
        marker_color=[cores_abc[c] for c in df_abc['CLASSE'][:30]]
    ))

    # Linha acumulada
    fig.add_trace(go.Scatter(
        x=df_abc['RANK'][:30],
        y=df_abc['PCT_ACUM'][:30],
        name='% Acumulado',
        mode='lines+markers',
        line=dict(color=cores['texto'], width=2),
        yaxis='y2'
    ))

    # Linhas de referência
    fig.add_hline(y=80, line_dash="dash", line_color=cores['sucesso'], yref='y2')
    fig.add_hline(y=95, line_dash="dash", line_color=cores['alerta'], yref='y2')

    fig.update_layout(
        criar_layout(300),
        yaxis2=dict(overlaying='y', side='right', range=[0, 105], showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=40, t=30, b=30),
        xaxis_title="Rank Fornecedor"
    )

    st.plotly_chart(fig, use_container_width=True)

    # Resumo ABC
    col1, col2, col3 = st.columns(3)
    with col1:
        qtd_a = len(df_abc[df_abc['CLASSE'] == 'A'])
        st.success(f"**A**: {qtd_a} forn. (80% valor)")
    with col2:
        qtd_b = len(df_abc[df_abc['CLASSE'] == 'B'])
        st.warning(f"**B**: {qtd_b} forn. (15% valor)")
    with col3:
        qtd_c = len(df_abc[df_abc['CLASSE'] == 'C'])
        st.info(f"**C**: {qtd_c} forn. (5% valor)")


def _render_scatter_fornecedores(df, cores):
    """Scatter plot: Valor Total vs % Pendente"""

    st.markdown("##### 🔍 Análise: Valor vs Pendência")

    df_scatter = df.groupby('NOME_FORNECEDOR').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'FORNECEDOR': 'count'
    }).reset_index()

    df_scatter['PCT_PENDENTE'] = (df_scatter['SALDO'] / df_scatter['VALOR_ORIGINAL'] * 100).fillna(0)
    df_scatter = df_scatter.nlargest(50, 'VALOR_ORIGINAL')

    fig = px.scatter(
        df_scatter,
        x='VALOR_ORIGINAL',
        y='PCT_PENDENTE',
        size='FORNECEDOR',
        hover_name='NOME_FORNECEDOR',
        color='PCT_PENDENTE',
        color_continuous_scale=['#10b981', '#fbbf24', '#ef4444'],
        labels={
            'VALOR_ORIGINAL': 'Valor Total (R$)',
            'PCT_PENDENTE': '% Pendente',
            'FORNECEDOR': 'Qtd Títulos'
        }
    )

    fig.update_layout(
        criar_layout(300),
        coloraxis_colorbar=dict(title="% Pend."),
        margin=dict(l=10, r=10, t=10, b=40)
    )

    # Linha de referência 50%
    fig.add_hline(y=50, line_dash="dash", line_color=cores['alerta'],
                  annotation_text="50%", annotation_position="right")

    st.plotly_chart(fig, use_container_width=True)

    st.caption("Tamanho = Qtd títulos | Cor = % Pendente")


def _render_busca_fornecedor(df, df_pendentes, cores):
    """Busca e detalhes de fornecedor específico"""

    st.markdown("##### 🔎 Consultar Fornecedor")

    # Lista de fornecedores únicos
    fornecedores = sorted(df['NOME_FORNECEDOR'].unique().tolist())

    col1, col2 = st.columns([3, 1])
    with col1:
        fornecedor_selecionado = st.selectbox(
            "Selecione um fornecedor",
            options=[""] + fornecedores,
            key="busca_fornecedor"
        )

    if fornecedor_selecionado:
        df_forn = df[df['NOME_FORNECEDOR'] == fornecedor_selecionado]
        df_pend_forn = df_pendentes[df_pendentes['NOME_FORNECEDOR'] == fornecedor_selecionado]

        # Métricas do fornecedor
        total_valor = df_forn['VALOR_ORIGINAL'].sum()
        total_pago = total_valor - df_forn['SALDO'].sum()
        total_pendente = df_forn['SALDO'].sum()
        qtd_titulos = len(df_forn)
        pct_pago = (total_pago / total_valor * 100) if total_valor > 0 else 0

        # Vencidos
        vencidos = df_pend_forn[df_pend_forn['STATUS'] == 'Vencido']
        total_vencido = vencidos['SALDO'].sum() if len(vencidos) > 0 else 0
        dias_atraso_max = vencidos['DIAS_ATRASO'].max() if len(vencidos) > 0 else 0

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric("Total", formatar_moeda(total_valor), f"{qtd_titulos} títulos", delta_color="off")
        with col2:
            st.metric("Pago", formatar_moeda(total_pago), f"{pct_pago:.1f}%", delta_color="off")
        with col3:
            st.metric("Pendente", formatar_moeda(total_pendente), delta_color="off")
        with col4:
            st.metric("Vencido", formatar_moeda(total_vencido), delta_color="off")
        with col5:
            if dias_atraso_max > 0:
                st.metric("Maior Atraso", f"{int(dias_atraso_max)} dias", delta_color="off")
            else:
                st.metric("Maior Atraso", "Em dia", delta_color="off")

        # Evolução do fornecedor
        st.markdown("###### 📈 Histórico de Compras")

        df_hist = df_forn.copy()
        df_hist['MES'] = df_hist['EMISSAO'].dt.to_period('M').astype(str)
        df_hist_grp = df_hist.groupby('MES').agg({
            'VALOR_ORIGINAL': 'sum',
            'SALDO': 'sum'
        }).reset_index()
        df_hist_grp['PAGO'] = df_hist_grp['VALOR_ORIGINAL'] - df_hist_grp['SALDO']

        if len(df_hist_grp) > 1:
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df_hist_grp['MES'], y=df_hist_grp['PAGO'], name='Pago', marker_color=cores['sucesso']))
            fig.add_trace(go.Bar(x=df_hist_grp['MES'], y=df_hist_grp['SALDO'], name='Pendente', marker_color=cores['alerta']))
            fig.update_layout(criar_layout(200, barmode='stack'), margin=dict(l=10, r=10, t=10, b=30))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Histórico insuficiente para gráfico")

        # Títulos do fornecedor
        with st.expander("📋 Ver títulos do fornecedor"):
            df_titulos = df_forn[['NOME_FILIAL', 'DESCRICAO', 'EMISSAO', 'VENCIMENTO', 'VALOR_ORIGINAL', 'SALDO', 'STATUS']].copy()
            df_titulos['EMISSAO'] = df_titulos['EMISSAO'].dt.strftime('%d/%m/%Y')
            df_titulos['VENCIMENTO'] = df_titulos['VENCIMENTO'].dt.strftime('%d/%m/%Y')
            df_titulos['VALOR_ORIGINAL'] = df_titulos['VALOR_ORIGINAL'].apply(lambda x: formatar_moeda(x, completo=True))
            df_titulos['SALDO'] = df_titulos['SALDO'].apply(lambda x: formatar_moeda(x, completo=True))
            df_titulos.columns = ['Filial', 'Categoria', 'Emissão', 'Vencimento', 'Valor', 'Saldo', 'Status']
            st.dataframe(df_titulos, use_container_width=True, hide_index=True, height=300)


def _render_ranking_completo(df, df_pendentes, cores):
    """Ranking completo com filtros"""

    st.markdown("##### 🏆 Ranking de Fornecedores")

    # Filtros
    col1, col2, col3 = st.columns(3)
    with col1:
        ordenar = st.selectbox("Ordenar por", ["Valor Total", "Saldo Pendente", "Qtd Títulos", "% Pendente"], key="ord_rank")
    with col2:
        qtd_exibir = st.selectbox("Exibir", [20, 50, 100, "Todos"], key="qtd_rank")
    with col3:
        filtro_status = st.selectbox("Status", ["Todos", "Com Pendência", "Quitados"], key="status_rank")

    # Preparar dados
    df_rank = df.groupby('NOME_FORNECEDOR').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'FORNECEDOR': 'count'
    }).reset_index()

    df_rank.columns = ['Fornecedor', 'Total', 'Pendente', 'Títulos']
    df_rank['% Pago'] = ((df_rank['Total'] - df_rank['Pendente']) / df_rank['Total'] * 100).round(1)
    df_rank['% Pendente'] = (100 - df_rank['% Pago']).round(1)

    # Filtrar por status
    if filtro_status == "Com Pendência":
        df_rank = df_rank[df_rank['Pendente'] > 0]
    elif filtro_status == "Quitados":
        df_rank = df_rank[df_rank['Pendente'] <= 0]

    # Ordenar
    if ordenar == "Valor Total":
        df_rank = df_rank.sort_values('Total', ascending=False)
    elif ordenar == "Saldo Pendente":
        df_rank = df_rank.sort_values('Pendente', ascending=False)
    elif ordenar == "Qtd Títulos":
        df_rank = df_rank.sort_values('Títulos', ascending=False)
    else:
        df_rank = df_rank.sort_values('% Pendente', ascending=False)

    # Limitar quantidade
    if qtd_exibir != "Todos":
        df_rank = df_rank.head(qtd_exibir)

    # Formatar valores
    df_show = df_rank.copy()
    df_show['Total'] = df_show['Total'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Pendente'] = df_show['Pendente'].apply(lambda x: formatar_moeda(x, completo=True))

    st.dataframe(
        df_show,
        use_container_width=True,
        hide_index=True,
        height=400,
        column_config={
            "% Pago": st.column_config.ProgressColumn(
                "% Pago",
                help="Percentual pago",
                format="%.1f%%",
                min_value=0,
                max_value=100,
            ),
        }
    )

    st.caption(f"Exibindo {len(df_show)} fornecedores | Total geral: {formatar_moeda(df['VALOR_ORIGINAL'].sum(), completo=True)}")
