"""
Aba Custos Financeiros - Bancos, Emprestimos, Taxas, Juros
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from config.theme import get_cores
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero


def render_custos_financeiros(df):
    """Renderiza a aba de Custos Financeiros (Bancos)"""
    cores = get_cores()

    if len(df) == 0:
        st.info("Nenhum registro de custos financeiros/bancos no periodo.")
        return

    # Preparar dados
    df_custos = df.copy()

    # Garantir colunas de custos
    colunas_custos = ['VALOR_JUROS', 'VALOR_MULTA', 'VALOR_CORRECAO', 'VALOR_ACRESCIMO', 'VLR_DESCONTO', 'TX_MOEDA']
    for col in colunas_custos:
        if col not in df_custos.columns:
            df_custos[col] = 0
        else:
            df_custos[col] = pd.to_numeric(df_custos[col], errors='coerce').fillna(0)

    # Total de custos financeiros adicionais
    df_custos['CUSTO_ADICIONAL'] = (
        df_custos['VALOR_JUROS'] +
        df_custos['VALOR_MULTA'] +
        df_custos['VALOR_CORRECAO'] +
        df_custos['VALOR_ACRESCIMO']
    )

    # Identificar operacoes em dolar
    df_custos['IS_DOLAR'] = df_custos['TX_MOEDA'] > 1

    # ========== KPIs PRINCIPAIS ==========
    _render_kpis(df_custos, cores)

    st.divider()

    # ========== POR DESCRICAO ==========
    _render_por_descricao(df_custos, cores)

    st.divider()

    # ========== POR FORNECEDOR ==========
    _render_por_fornecedor(df_custos, cores)

    st.divider()

    # ========== EVOLUCAO ==========
    _render_evolucao(df_custos, cores)

    st.divider()

    # ========== DETALHES ==========
    _render_detalhes(df_custos, cores)


def _render_kpis(df, cores):
    """KPIs principais"""

    total_principal = df['VALOR_ORIGINAL'].sum()
    total_saldo = df['SALDO'].sum()
    total_pago = total_principal - total_saldo
    total_juros = df['VALOR_JUROS'].sum()
    total_multa = df['VALOR_MULTA'].sum()
    total_custos = df['CUSTO_ADICIONAL'].sum()

    # Pendentes e pagos
    df_pendentes = df[df['SALDO'] > 0]
    df_pagos = df[df['SALDO'] <= 0]

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    col1.metric(
        "Total Principal",
        formatar_moeda(total_principal),
        f"{len(df)} titulos"
    )

    col2.metric(
        "Saldo Pendente",
        formatar_moeda(total_saldo),
        f"{len(df_pendentes)} pendentes"
    )

    col3.metric(
        "Ja Pago",
        formatar_moeda(total_pago),
        f"{len(df_pagos)} pagos"
    )

    col4.metric(
        "Juros",
        formatar_moeda(total_juros),
        f"{len(df[df['VALOR_JUROS'] > 0])} c/ juros"
    )

    col5.metric(
        "Multas",
        formatar_moeda(total_multa),
        f"{len(df[df['VALOR_MULTA'] > 0])} c/ multa"
    )

    pct_custos = (total_custos / total_principal * 100) if total_principal > 0 else 0
    col6.metric(
        "Custos Adicionais",
        formatar_moeda(total_custos),
        f"{pct_custos:.2f}% do principal"
    )


def _render_por_descricao(df, cores):
    """Analise por descricao/tipo"""

    st.markdown("##### Por Tipo de Operacao")

    col1, col2 = st.columns(2)

    with col1:
        # Grafico por descricao
        df_desc = df.groupby('DESCRICAO').agg({
            'VALOR_ORIGINAL': 'sum',
            'SALDO': 'sum',
            'NUMERO': 'count'
        }).reset_index()
        df_desc.columns = ['Descricao', 'Principal', 'Saldo', 'Qtd']
        df_desc = df_desc.sort_values('Principal', ascending=True)

        fig = go.Figure()

        fig.add_trace(go.Bar(
            y=df_desc['Descricao'],
            x=df_desc['Saldo'],
            orientation='h',
            name='Saldo Pendente',
            marker_color=cores['alerta'],
            text=[formatar_moeda(v) for v in df_desc['Saldo']],
            textposition='inside',
            textfont=dict(size=9, color='white')
        ))

        fig.add_trace(go.Bar(
            y=df_desc['Descricao'],
            x=df_desc['Principal'] - df_desc['Saldo'],
            orientation='h',
            name='Ja Pago',
            marker_color=cores['sucesso'],
            text=[formatar_moeda(v) for v in (df_desc['Principal'] - df_desc['Saldo'])],
            textposition='inside',
            textfont=dict(size=9, color='white')
        ))

        fig.update_layout(
            criar_layout(350, barmode='stack'),
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
            margin=dict(l=10, r=10, t=30, b=10)
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Tabela resumo
        df_tab = df_desc.copy()
        df_tab['Pago'] = df_tab['Principal'] - df_tab['Saldo']
        df_tab['% Pago'] = (df_tab['Pago'] / df_tab['Principal'] * 100).round(1)

        df_tab['Principal'] = df_tab['Principal'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab['Saldo'] = df_tab['Saldo'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab['Pago'] = df_tab['Pago'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab['% Pago'] = df_tab['% Pago'].apply(lambda x: f"{x:.1f}%")

        df_tab = df_tab[['Descricao', 'Qtd', 'Principal', 'Pago', 'Saldo', '% Pago']]

        st.dataframe(df_tab, use_container_width=True, hide_index=True, height=350)


def _render_por_fornecedor(df, cores):
    """Analise por fornecedor/banco"""

    st.markdown("##### Por Fornecedor/Banco")

    col1, col2 = st.columns(2)

    with col1:
        # Top fornecedores
        df_forn = df.groupby('NOME_FORNECEDOR').agg({
            'VALOR_ORIGINAL': 'sum',
            'SALDO': 'sum',
            'VALOR_JUROS': 'sum',
            'NUMERO': 'count'
        }).reset_index()
        df_forn.columns = ['Fornecedor', 'Principal', 'Saldo', 'Juros', 'Qtd']
        df_forn = df_forn.sort_values('Principal', ascending=False).head(15)

        fig = go.Figure()

        fig.add_trace(go.Bar(
            y=df_forn['Fornecedor'].str[:30],
            x=df_forn['Principal'],
            orientation='h',
            name='Principal',
            marker_color=cores['info'],
            text=[formatar_moeda(v) for v in df_forn['Principal']],
            textposition='inside',
            textfont=dict(size=9, color='white')
        ))

        fig.update_layout(
            criar_layout(400),
            yaxis={'autorange': 'reversed'},
            margin=dict(l=10, r=10, t=10, b=10)
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Tabela
        df_tab = df_forn.copy()
        df_tab['Pago'] = df_tab['Principal'] - df_tab['Saldo']

        df_tab['Principal'] = df_tab['Principal'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab['Saldo'] = df_tab['Saldo'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab['Juros'] = df_tab['Juros'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab['Pago'] = df_tab['Pago'].apply(lambda x: formatar_moeda(x, completo=True))

        df_tab = df_tab[['Fornecedor', 'Qtd', 'Principal', 'Pago', 'Saldo', 'Juros']]

        st.dataframe(df_tab, use_container_width=True, hide_index=True, height=400)


def _render_evolucao(df, cores):
    """Evolucao temporal"""

    st.markdown("##### Evolucao Mensal")

    df_temp = df.copy()
    df_temp['MES'] = df_temp['EMISSAO'].dt.to_period('M')

    df_mes = df_temp.groupby('MES').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'VALOR_JUROS': 'sum'
    }).reset_index()

    df_mes['MES'] = df_mes['MES'].astype(str)
    df_mes['PAGO'] = df_mes['VALOR_ORIGINAL'] - df_mes['SALDO']

    if len(df_mes) < 2:
        st.info("Dados insuficientes para grafico de evolucao")
        return

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df_mes['MES'],
        y=df_mes['PAGO'],
        name='Pago',
        marker_color=cores['sucesso']
    ))

    fig.add_trace(go.Bar(
        x=df_mes['MES'],
        y=df_mes['SALDO'],
        name='Saldo Pendente',
        marker_color=cores['alerta']
    ))

    fig.add_trace(go.Scatter(
        x=df_mes['MES'],
        y=df_mes['VALOR_JUROS'],
        mode='lines+markers',
        name='Juros',
        yaxis='y2',
        line=dict(color=cores['perigo'], width=2),
        marker=dict(size=6)
    ))

    fig.update_layout(
        criar_layout(300, barmode='stack'),
        yaxis=dict(title='Principal (R$)'),
        yaxis2=dict(title='Juros (R$)', overlaying='y', side='right', showgrid=False),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
        margin=dict(l=10, r=50, t=30, b=30),
        xaxis_tickangle=-45
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_detalhes(df, cores):
    """Tabela de detalhes"""

    st.markdown("##### Detalhamento")

    # Filtros
    col1, col2, col3 = st.columns(3)

    with col1:
        filtro_status = st.radio("Status", ["Todos", "Pendentes", "Pagos"], horizontal=True, key="cf_status")

    with col2:
        descricoes = ['Todas'] + sorted(df['DESCRICAO'].unique().tolist())
        filtro_desc = st.selectbox("Tipo", descricoes, key="cf_desc")

    with col3:
        ordenar = st.selectbox("Ordenar", ["Maior valor", "Mais recente", "Maior saldo"], key="cf_ordem")

    # Aplicar filtros
    df_show = df.copy()

    if filtro_status == "Pendentes":
        df_show = df_show[df_show['SALDO'] > 0]
    elif filtro_status == "Pagos":
        df_show = df_show[df_show['SALDO'] <= 0]

    if filtro_desc != 'Todas':
        df_show = df_show[df_show['DESCRICAO'] == filtro_desc]

    # Ordenar
    if ordenar == "Maior valor":
        df_show = df_show.sort_values('VALOR_ORIGINAL', ascending=False)
    elif ordenar == "Mais recente":
        df_show = df_show.sort_values('EMISSAO', ascending=False)
    else:
        df_show = df_show.sort_values('SALDO', ascending=False)

    df_show = df_show.head(100)

    if len(df_show) == 0:
        st.info("Nenhum registro encontrado com os filtros selecionados.")
        return

    # Preparar tabela
    colunas = ['NOME_FILIAL', 'NOME_FORNECEDOR', 'DESCRICAO', 'EMISSAO', 'VENCIMENTO',
               'VALOR_ORIGINAL', 'SALDO', 'VALOR_JUROS', 'STATUS']
    colunas_disp = [c for c in colunas if c in df_show.columns]
    df_tab = df_show[colunas_disp].copy()

    # Formatar
    for col in ['EMISSAO', 'VENCIMENTO']:
        if col in df_tab.columns:
            df_tab[col] = pd.to_datetime(df_tab[col], errors='coerce').dt.strftime('%d/%m/%Y')

    for col in ['VALOR_ORIGINAL', 'SALDO', 'VALOR_JUROS']:
        if col in df_tab.columns:
            df_tab[col] = df_tab[col].apply(lambda x: formatar_moeda(x, completo=True))

    nomes = {
        'NOME_FILIAL': 'Filial',
        'NOME_FORNECEDOR': 'Fornecedor',
        'DESCRICAO': 'Tipo',
        'EMISSAO': 'Emissao',
        'VENCIMENTO': 'Vencimento',
        'VALOR_ORIGINAL': 'Principal',
        'SALDO': 'Saldo',
        'VALOR_JUROS': 'Juros',
        'STATUS': 'Status'
    }
    df_tab.columns = [nomes.get(c, c) for c in df_tab.columns]

    st.dataframe(df_tab, use_container_width=True, hide_index=True, height=400)
    st.caption(f"Exibindo {len(df_tab)} registros")
