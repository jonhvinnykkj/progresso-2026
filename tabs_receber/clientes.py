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
    """Análise de performance de recebimento por cliente usando DT_BAIXA e VENCTO_REAL"""

    st.markdown("##### Performance de Recebimento por Cliente")

    # Verificar se temos as colunas necessárias
    tem_dso = 'DSO' in df.columns
    tem_pontual = 'PONTUAL' in df.columns
    tem_reneg = 'RENEGOCIADO' in df.columns

    if not tem_dso and not tem_pontual and not tem_reneg:
        st.info("Dados de performance nao disponiveis (colunas DT_BAIXA/VENCTO_REAL)")
        return

    col1, col2 = st.columns(2)

    with col1:
        if tem_dso:
            st.markdown("###### Melhores Pagadores (Menor DSO)")

            # Filtrar apenas recebidos com DSO válido
            df_receb = df[(df['SALDO'] == 0) & df['DSO'].notna() & (df['DSO'] > 0)]

            if len(df_receb) > 0:
                df_dso = df_receb.groupby('NOME_CLIENTE').agg({
                    'DSO': 'mean',
                    'VALOR_ORIGINAL': 'sum',
                    'CLIENTE': 'count'
                }).reset_index()

                # Filtrar clientes com pelo menos 3 títulos
                df_dso = df_dso[df_dso['CLIENTE'] >= 3]

                # Top 10 menores DSO
                df_melhores = df_dso.nsmallest(10, 'DSO')

                if len(df_melhores) > 0:
                    fig = go.Figure(go.Bar(
                        y=df_melhores['NOME_CLIENTE'].str[:22],
                        x=df_melhores['DSO'],
                        orientation='h',
                        marker_color=cores['sucesso'],
                        text=[f"{d:.0f}d | {formatar_moeda(v)}" for d, v in zip(df_melhores['DSO'], df_melhores['VALOR_ORIGINAL'])],
                        textposition='outside',
                        textfont=dict(size=9)
                    ))

                    fig.update_layout(
                        criar_layout(280),
                        yaxis={'autorange': 'reversed'},
                        xaxis_title='DSO (dias)',
                        margin=dict(l=10, r=100, t=10, b=30)
                    )

                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Poucos dados para analise")
            else:
                st.info("Sem dados de recebimento")

    with col2:
        if tem_dso:
            st.markdown("###### Piores Pagadores (Maior DSO)")

            df_receb = df[(df['SALDO'] == 0) & df['DSO'].notna() & (df['DSO'] > 0)]

            if len(df_receb) > 0:
                df_dso = df_receb.groupby('NOME_CLIENTE').agg({
                    'DSO': 'mean',
                    'VALOR_ORIGINAL': 'sum',
                    'CLIENTE': 'count'
                }).reset_index()

                df_dso = df_dso[df_dso['CLIENTE'] >= 3]
                df_piores = df_dso.nlargest(10, 'DSO')

                if len(df_piores) > 0:
                    fig = go.Figure(go.Bar(
                        y=df_piores['NOME_CLIENTE'].str[:22],
                        x=df_piores['DSO'],
                        orientation='h',
                        marker_color=cores['perigo'],
                        text=[f"{d:.0f}d | {formatar_moeda(v)}" for d, v in zip(df_piores['DSO'], df_piores['VALOR_ORIGINAL'])],
                        textposition='outside',
                        textfont=dict(size=9)
                    ))

                    fig.update_layout(
                        criar_layout(280),
                        yaxis={'autorange': 'reversed'},
                        xaxis_title='DSO (dias)',
                        margin=dict(l=10, r=100, t=10, b=30)
                    )

                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Poucos dados para analise")
            else:
                st.info("Sem dados de recebimento")

    # Tabela de performance
    if tem_dso or tem_pontual or tem_reneg:
        with st.expander("Ver ranking completo de performance", expanded=False):
            df_receb = df[df['SALDO'] == 0].copy() if tem_dso else df.copy()

            agg_dict = {'VALOR_ORIGINAL': 'sum', 'CLIENTE': 'count'}
            if tem_dso:
                agg_dict['DSO'] = 'mean'
            if tem_pontual:
                agg_dict['PONTUAL'] = 'mean'
            if tem_reneg:
                agg_dict['RENEGOCIADO'] = 'mean'

            df_perf = df_receb.groupby('NOME_CLIENTE').agg(agg_dict).reset_index()
            df_perf = df_perf[df_perf['CLIENTE'] >= 2]

            # Renomear colunas
            col_names = {'NOME_CLIENTE': 'Cliente', 'VALOR_ORIGINAL': 'Valor', 'CLIENTE': 'Titulos'}
            if tem_dso:
                col_names['DSO'] = 'DSO Medio'
            if tem_pontual:
                col_names['PONTUAL'] = '% Pontual'
                df_perf['PONTUAL'] = df_perf['PONTUAL'] * 100
            if tem_reneg:
                col_names['RENEGOCIADO'] = '% Reneg'
                df_perf['RENEGOCIADO'] = df_perf['RENEGOCIADO'] * 100

            df_perf = df_perf.rename(columns=col_names)

            # Ordenar por DSO se disponível
            if 'DSO Medio' in df_perf.columns:
                df_perf = df_perf.sort_values('DSO Medio', ascending=True)

            df_perf['Valor'] = df_perf['Valor'].apply(lambda x: formatar_moeda(x, completo=True))

            st.dataframe(df_perf.head(50), use_container_width=True, hide_index=True, height=350)


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
