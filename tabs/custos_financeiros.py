"""
Aba Custos Financeiros - Analise de Juros, Multas e Variacao Cambial
Foco em Bancos e operacoes em Dolar
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

from config.theme import get_cores
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero


# Padroes para identificar categorias de Bancos
PADROES_BANCOS = [
    'BANCO', 'BRADESCO', 'ITAU', 'SANTANDER', 'BB ', 'CAIXA', 'BTG',
    'SAFRA', 'SICREDI', 'SICOOB', 'INTER', 'NUBANK', 'C6', 'ORIGINAL',
    'FINANC', 'EMPREST', 'LEASING', 'CDC', 'CCB', 'FINAME', 'BNDES',
    'CREDITO', 'CAPITAL DE GIRO', 'DESCONTO', 'ANTECIPACAO', 'FIDC'
]


def render_custos_financeiros(df):
    """Renderiza a aba de Custos Financeiros"""
    cores = get_cores()

    if len(df) == 0:
        st.warning("Nenhum dado disponivel.")
        return

    # Preparar dados
    df_custos = _preparar_dados_custos(df)

    # ========== KPIs PRINCIPAIS ==========
    _render_kpis_custos(df_custos, cores)

    st.divider()

    # ========== SECAO BANCOS ==========
    st.markdown(f"""
    <div style="background: {cores['card']}; border-left: 4px solid {cores['info']};
                padding: 0.75rem 1rem; border-radius: 0 8px 8px 0; margin-bottom: 1rem;">
        <h4 style="color: {cores['texto']}; margin: 0;">Operacoes Bancarias</h4>
        <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0;">
            Principal + Juros + Variacao Cambial
        </p>
    </div>
    """, unsafe_allow_html=True)

    _render_secao_bancos(df_custos, cores)

    st.divider()

    # ========== SECAO DOLAR ==========
    st.markdown(f"""
    <div style="background: {cores['card']}; border-left: 4px solid {cores['sucesso']};
                padding: 0.75rem 1rem; border-radius: 0 8px 8px 0; margin-bottom: 1rem;">
        <h4 style="color: {cores['texto']}; margin: 0;">Operacoes em Dolar (USD)</h4>
        <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0;">
            Pagamentos com variacao cambial
        </p>
    </div>
    """, unsafe_allow_html=True)

    _render_secao_dolar(df_custos, cores)

    st.divider()

    # ========== ANALISE POR NATUREZA ==========
    st.markdown(f"""
    <div style="background: {cores['card']}; border-left: 4px solid {cores['alerta']};
                padding: 0.75rem 1rem; border-radius: 0 8px 8px 0; margin-bottom: 1rem;">
        <h4 style="color: {cores['texto']}; margin: 0;">Custos por Natureza</h4>
        <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0;">
            Segregacao por categoria de despesa
        </p>
    </div>
    """, unsafe_allow_html=True)

    _render_custos_por_natureza(df_custos, cores)

    st.divider()

    # ========== EVOLUCAO TEMPORAL ==========
    _render_evolucao_custos(df_custos, cores)

    st.divider()

    # ========== DETALHAMENTO ==========
    _render_detalhes_custos(df_custos, cores)


def _preparar_dados_custos(df):
    """Prepara dados com custos financeiros"""
    df_custos = df.copy()

    # Garantir colunas de custos
    colunas_custos = ['VALOR_JUROS', 'VALOR_MULTA', 'VALOR_CORRECAO', 'VALOR_ACRESCIMO', 'VLR_DESCONTO', 'TX_MOEDA']
    for col in colunas_custos:
        if col not in df_custos.columns:
            df_custos[col] = 0
        else:
            df_custos[col] = pd.to_numeric(df_custos[col], errors='coerce').fillna(0)

    # Total de custos financeiros
    df_custos['CUSTO_FINANCEIRO'] = (
        df_custos['VALOR_JUROS'] +
        df_custos['VALOR_MULTA'] +
        df_custos['VALOR_CORRECAO'] +
        df_custos['VALOR_ACRESCIMO']
    )

    # Identificar operacoes em dolar (TX_MOEDA > 1 indica conversao)
    df_custos['IS_DOLAR'] = df_custos['TX_MOEDA'] > 1

    # Variacao cambial
    df_custos['VARIACAO_CAMBIAL'] = df_custos.apply(
        lambda x: x['VALOR_CORRECAO'] if x['IS_DOLAR'] else 0, axis=1
    )

    # Identificar se e Banco (na categoria ou fornecedor)
    df_custos['IS_BANCO'] = df_custos['DESCRICAO'].str.upper().str.contains(
        '|'.join(PADROES_BANCOS), na=False, regex=True
    ) | df_custos['NOME_FORNECEDOR'].str.upper().str.contains(
        '|'.join(PADROES_BANCOS), na=False, regex=True
    )

    return df_custos


def _render_kpis_custos(df, cores):
    """KPIs principais de custos financeiros"""

    total_juros = df['VALOR_JUROS'].sum()
    total_multa = df['VALOR_MULTA'].sum()
    total_correcao = df['VALOR_CORRECAO'].sum()
    total_desconto = df['VLR_DESCONTO'].sum() if 'VLR_DESCONTO' in df.columns else 0
    total_custos = df['CUSTO_FINANCEIRO'].sum()
    total_principal = df['VALOR_ORIGINAL'].sum()

    # Percentual sobre principal
    pct_custos = (total_custos / total_principal * 100) if total_principal > 0 else 0

    # Custos em bancos
    df_bancos = df[df['IS_BANCO']]
    custos_bancos = df_bancos['CUSTO_FINANCEIRO'].sum() if len(df_bancos) > 0 else 0
    principal_bancos = df_bancos['VALOR_ORIGINAL'].sum() if len(df_bancos) > 0 else 0

    # Custos em dolar
    df_dolar = df[df['IS_DOLAR']]
    custos_dolar = df_dolar['VARIACAO_CAMBIAL'].sum() if len(df_dolar) > 0 else 0
    principal_dolar = df_dolar['VALOR_ORIGINAL'].sum() if len(df_dolar) > 0 else 0

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            label="Total Custos Financ.",
            value=formatar_moeda(total_custos),
            delta=f"{pct_custos:.2f}% do principal",
            delta_color="inverse"
        )

    with col2:
        st.metric(
            label="Juros",
            value=formatar_moeda(total_juros),
            delta=f"{len(df[df['VALOR_JUROS'] > 0])} titulos",
            delta_color="off"
        )

    with col3:
        st.metric(
            label="Multas",
            value=formatar_moeda(total_multa),
            delta=f"{len(df[df['VALOR_MULTA'] > 0])} titulos",
            delta_color="off"
        )

    with col4:
        st.metric(
            label="Custos Bancos",
            value=formatar_moeda(custos_bancos),
            delta=f"{len(df_bancos)} operacoes",
            delta_color="off"
        )

    with col5:
        st.metric(
            label="Var. Cambial USD",
            value=formatar_moeda(custos_dolar),
            delta=f"{len(df_dolar)} operacoes",
            delta_color="off"
        )

    # Linha de alerta
    if pct_custos > 3:
        st.error(f"Custos financeiros acima de 3% do principal ({pct_custos:.2f}%)")
    elif pct_custos > 1:
        st.warning(f"Custos financeiros de {pct_custos:.2f}% - monitorar")


def _render_secao_bancos(df, cores):
    """Secao de analise de Bancos"""

    df_bancos = df[df['IS_BANCO']].copy()

    if len(df_bancos) == 0:
        st.info("Nenhuma operacao bancaria identificada no periodo.")
        st.caption(f"Padroes buscados: {', '.join(PADROES_BANCOS[:10])}...")
        return

    col1, col2 = st.columns(2)

    with col1:
        # Resumo por fornecedor (Banco)
        st.markdown("##### Por Instituicao Financeira")

        df_banco_agg = df_bancos.groupby('NOME_FORNECEDOR').agg({
            'VALOR_ORIGINAL': 'sum',
            'VALOR_JUROS': 'sum',
            'VALOR_CORRECAO': 'sum',
            'CUSTO_FINANCEIRO': 'sum',
            'SALDO': 'sum'
        }).reset_index()
        df_banco_agg.columns = ['Banco', 'Principal', 'Juros', 'Variacao', 'Custo_Total', 'Saldo']
        df_banco_agg = df_banco_agg.sort_values('Principal', ascending=False).head(10)

        fig = go.Figure()

        fig.add_trace(go.Bar(
            y=df_banco_agg['Banco'].str[:25],
            x=df_banco_agg['Principal'],
            orientation='h',
            name='Principal',
            marker_color=cores['info'],
            text=[formatar_moeda(v) for v in df_banco_agg['Principal']],
            textposition='inside',
            textfont=dict(size=9, color='white')
        ))

        fig.add_trace(go.Bar(
            y=df_banco_agg['Banco'].str[:25],
            x=df_banco_agg['Juros'],
            orientation='h',
            name='Juros',
            marker_color=cores['alerta'],
            text=[formatar_moeda(v) if v > 0 else '' for v in df_banco_agg['Juros']],
            textposition='inside',
            textfont=dict(size=9, color='white')
        ))

        fig.add_trace(go.Bar(
            y=df_banco_agg['Banco'].str[:25],
            x=df_banco_agg['Variacao'],
            orientation='h',
            name='Variacao',
            marker_color=cores['perigo'],
            text=[formatar_moeda(v) if v > 0 else '' for v in df_banco_agg['Variacao']],
            textposition='inside',
            textfont=dict(size=9, color='white')
        ))

        fig.update_layout(
            criar_layout(350, barmode='stack'),
            yaxis={'autorange': 'reversed'},
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=10, r=10, t=30, b=10)
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Tabela resumo bancos
        st.markdown("##### Detalhamento Bancos")

        df_tab = df_banco_agg.copy()
        df_tab['Taxa_Custo'] = (df_tab['Custo_Total'] / df_tab['Principal'] * 100).round(2)
        df_tab['Principal'] = df_tab['Principal'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab['Juros'] = df_tab['Juros'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab['Variacao'] = df_tab['Variacao'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab['Custo_Total'] = df_tab['Custo_Total'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab['Saldo'] = df_tab['Saldo'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab['Taxa_Custo'] = df_tab['Taxa_Custo'].apply(lambda x: f"{x:.2f}%")

        df_tab.columns = ['Banco', 'Principal', 'Juros', 'Variacao', 'Custo Total', 'Saldo', '% Custo']

        st.dataframe(df_tab, use_container_width=True, hide_index=True, height=350)

    # KPIs de bancos
    st.markdown("##### Resumo Operacoes Bancarias")
    col1, col2, col3, col4 = st.columns(4)

    total_principal = df_bancos['VALOR_ORIGINAL'].sum()
    total_juros = df_bancos['VALOR_JUROS'].sum()
    total_saldo = df_bancos['SALDO'].sum()
    taxa_media = (total_juros / total_principal * 100) if total_principal > 0 else 0

    col1.metric("Principal Total", formatar_moeda(total_principal))
    col2.metric("Juros Total", formatar_moeda(total_juros))
    col3.metric("Saldo Devedor", formatar_moeda(total_saldo))
    col4.metric("Taxa Media Juros", f"{taxa_media:.2f}%")


def _render_secao_dolar(df, cores):
    """Secao de analise de operacoes em Dolar"""

    df_dolar = df[df['IS_DOLAR']].copy()

    if len(df_dolar) == 0:
        st.info("Nenhuma operacao em dolar identificada no periodo.")
        st.caption("Operacoes em dolar sao identificadas pela taxa de moeda (TX_MOEDA > 1)")
        return

    col1, col2 = st.columns(2)

    with col1:
        # KPIs Dolar
        st.markdown("##### Resumo Operacoes USD")

        total_valor = df_dolar['VALOR_ORIGINAL'].sum()
        total_variacao = df_dolar['VARIACAO_CAMBIAL'].sum()
        taxa_media = df_dolar['TX_MOEDA'].mean()
        taxa_max = df_dolar['TX_MOEDA'].max()
        taxa_min = df_dolar['TX_MOEDA'].min()

        col_a, col_b = st.columns(2)

        with col_a:
            st.metric("Valor Total BRL", formatar_moeda(total_valor))
            st.metric("Taxa Media", f"R$ {taxa_media:.4f}")

        with col_b:
            st.metric("Variacao Cambial", formatar_moeda(total_variacao))
            st.metric("Taxa Min/Max", f"{taxa_min:.2f} / {taxa_max:.2f}")

        # Por fornecedor em dolar
        st.markdown("##### Top Fornecedores USD")

        df_dolar_forn = df_dolar.groupby('NOME_FORNECEDOR').agg({
            'VALOR_ORIGINAL': 'sum',
            'TX_MOEDA': 'mean',
            'VARIACAO_CAMBIAL': 'sum'
        }).nlargest(8, 'VALOR_ORIGINAL').reset_index()

        fig = go.Figure(go.Bar(
            y=df_dolar_forn['NOME_FORNECEDOR'].str[:20],
            x=df_dolar_forn['VALOR_ORIGINAL'],
            orientation='h',
            marker_color=cores['sucesso'],
            text=[f"{formatar_moeda(v)}" for v in df_dolar_forn['VALOR_ORIGINAL']],
            textposition='outside',
            textfont=dict(size=9)
        ))

        fig.update_layout(
            criar_layout(200),
            yaxis={'autorange': 'reversed'},
            margin=dict(l=10, r=80, t=10, b=10)
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Evolucao taxa
        st.markdown("##### Evolucao Taxa Cambio")

        df_dolar['MES'] = df_dolar['EMISSAO'].dt.to_period('M')
        df_taxa_mes = df_dolar.groupby('MES').agg({
            'TX_MOEDA': 'mean',
            'VALOR_ORIGINAL': 'sum',
            'VARIACAO_CAMBIAL': 'sum'
        }).reset_index()
        df_taxa_mes['MES'] = df_taxa_mes['MES'].astype(str)

        if len(df_taxa_mes) > 1:
            fig = go.Figure()

            fig.add_trace(go.Scatter(
                x=df_taxa_mes['MES'],
                y=df_taxa_mes['TX_MOEDA'],
                mode='lines+markers',
                name='Taxa Media',
                line=dict(color=cores['sucesso'], width=2),
                marker=dict(size=8)
            ))

            fig.update_layout(
                criar_layout(200),
                xaxis_title='Periodo',
                yaxis_title='Taxa R$/USD',
                margin=dict(l=10, r=10, t=10, b=30)
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Dados insuficientes para grafico de evolucao")

        # Tabela operacoes dolar
        st.markdown("##### Operacoes em USD")

        colunas = ['NOME_FORNECEDOR', 'EMISSAO', 'VALOR_ORIGINAL', 'TX_MOEDA', 'VARIACAO_CAMBIAL', 'STATUS']
        colunas_disp = [c for c in colunas if c in df_dolar.columns]
        df_tab = df_dolar[colunas_disp].nlargest(10, 'VALOR_ORIGINAL').copy()

        df_tab['EMISSAO'] = pd.to_datetime(df_tab['EMISSAO']).dt.strftime('%d/%m/%Y')
        df_tab['VALOR_ORIGINAL'] = df_tab['VALOR_ORIGINAL'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab['TX_MOEDA'] = df_tab['TX_MOEDA'].apply(lambda x: f"{x:.4f}")
        df_tab['VARIACAO_CAMBIAL'] = df_tab['VARIACAO_CAMBIAL'].apply(lambda x: formatar_moeda(x, completo=True))

        df_tab.columns = ['Fornecedor', 'Emissao', 'Valor', 'Taxa', 'Var. Cambial', 'Status']

        st.dataframe(df_tab, use_container_width=True, hide_index=True, height=200)


def _render_custos_por_natureza(df, cores):
    """Analise de custos por natureza/categoria"""

    # Filtrar apenas registros com custos
    df_com_custos = df[df['CUSTO_FINANCEIRO'] > 0].copy()

    if len(df_com_custos) == 0:
        st.info("Nenhum registro com custos financeiros no periodo.")
        return

    col1, col2 = st.columns(2)

    with col1:
        # Por categoria
        st.markdown("##### Custos por Categoria")

        df_cat = df_com_custos.groupby('DESCRICAO').agg({
            'VALOR_ORIGINAL': 'sum',
            'VALOR_JUROS': 'sum',
            'VALOR_MULTA': 'sum',
            'CUSTO_FINANCEIRO': 'sum'
        }).nlargest(10, 'CUSTO_FINANCEIRO').reset_index()

        fig = go.Figure()

        fig.add_trace(go.Bar(
            y=df_cat['DESCRICAO'].str[:25],
            x=df_cat['VALOR_JUROS'],
            orientation='h',
            name='Juros',
            marker_color=cores['alerta']
        ))

        fig.add_trace(go.Bar(
            y=df_cat['DESCRICAO'].str[:25],
            x=df_cat['VALOR_MULTA'],
            orientation='h',
            name='Multas',
            marker_color=cores['perigo']
        ))

        fig.update_layout(
            criar_layout(300, barmode='stack'),
            yaxis={'autorange': 'reversed'},
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=10, r=10, t=30, b=10)
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Taxa de custo por categoria
        st.markdown("##### Taxa de Custo por Categoria")

        df_cat['Taxa'] = (df_cat['CUSTO_FINANCEIRO'] / df_cat['VALOR_ORIGINAL'] * 100).round(2)
        df_cat_sorted = df_cat.nlargest(10, 'Taxa')

        def cor_taxa(t):
            if t < 1:
                return cores['sucesso']
            elif t < 3:
                return cores['info']
            elif t < 5:
                return cores['alerta']
            return cores['perigo']

        bar_colors = [cor_taxa(t) for t in df_cat_sorted['Taxa']]

        fig = go.Figure(go.Bar(
            y=df_cat_sorted['DESCRICAO'].str[:25],
            x=df_cat_sorted['Taxa'],
            orientation='h',
            marker_color=bar_colors,
            text=[f"{t:.2f}%" for t in df_cat_sorted['Taxa']],
            textposition='outside',
            textfont=dict(size=9)
        ))

        fig.update_layout(
            criar_layout(300),
            yaxis={'autorange': 'reversed'},
            xaxis_title='% Custo sobre Principal',
            margin=dict(l=10, r=50, t=10, b=10)
        )

        st.plotly_chart(fig, use_container_width=True)
        st.caption("Verde < 1% | Azul < 3% | Amarelo < 5% | Vermelho >= 5%")


def _render_evolucao_custos(df, cores):
    """Evolucao temporal dos custos"""

    st.markdown("##### Evolucao Mensal de Custos Financeiros")

    df_temp = df.copy()
    df_temp['MES'] = df_temp['EMISSAO'].dt.to_period('M')

    df_mes = df_temp.groupby('MES').agg({
        'VALOR_JUROS': 'sum',
        'VALOR_MULTA': 'sum',
        'VALOR_CORRECAO': 'sum',
        'CUSTO_FINANCEIRO': 'sum',
        'VALOR_ORIGINAL': 'sum'
    }).reset_index()

    df_mes['MES'] = df_mes['MES'].astype(str)
    df_mes['Taxa'] = (df_mes['CUSTO_FINANCEIRO'] / df_mes['VALOR_ORIGINAL'] * 100).fillna(0)

    if len(df_mes) < 2:
        st.info("Dados insuficientes para grafico de evolucao")
        return

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df_mes['MES'],
        y=df_mes['VALOR_JUROS'],
        name='Juros',
        marker_color=cores['alerta']
    ))

    fig.add_trace(go.Bar(
        x=df_mes['MES'],
        y=df_mes['VALOR_MULTA'],
        name='Multas',
        marker_color=cores['perigo']
    ))

    fig.add_trace(go.Bar(
        x=df_mes['MES'],
        y=df_mes['VALOR_CORRECAO'],
        name='Correcao/Variacao',
        marker_color=cores['info']
    ))

    # Linha de taxa
    fig.add_trace(go.Scatter(
        x=df_mes['MES'],
        y=df_mes['Taxa'],
        mode='lines+markers',
        name='% Custo',
        yaxis='y2',
        line=dict(color=cores['texto'], width=2),
        marker=dict(size=6)
    ))

    fig.update_layout(
        criar_layout(300, barmode='stack'),
        yaxis=dict(title='Valor (R$)'),
        yaxis2=dict(title='% Custo', overlaying='y', side='right', showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=50, t=30, b=30),
        xaxis_tickangle=-45
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_detalhes_custos(df, cores):
    """Detalhamento dos custos"""

    st.markdown("##### Detalhamento de Custos")

    # Filtros
    col1, col2, col3 = st.columns(3)

    with col1:
        tipo_filtro = st.selectbox(
            "Tipo",
            ['Todos', 'Apenas Bancos', 'Apenas Dolar', 'Com Juros', 'Com Multa'],
            key="cf_tipo"
        )

    with col2:
        ordenar = st.selectbox(
            "Ordenar por",
            ['Maior Custo', 'Maior Principal', 'Maior Taxa'],
            key="cf_ordem"
        )

    with col3:
        qtd = st.selectbox("Exibir", [20, 50, 100], key="cf_qtd")

    # Aplicar filtros
    df_filtrado = df.copy()

    if tipo_filtro == 'Apenas Bancos':
        df_filtrado = df_filtrado[df_filtrado['IS_BANCO']]
    elif tipo_filtro == 'Apenas Dolar':
        df_filtrado = df_filtrado[df_filtrado['IS_DOLAR']]
    elif tipo_filtro == 'Com Juros':
        df_filtrado = df_filtrado[df_filtrado['VALOR_JUROS'] > 0]
    elif tipo_filtro == 'Com Multa':
        df_filtrado = df_filtrado[df_filtrado['VALOR_MULTA'] > 0]

    # Ordenar
    if ordenar == 'Maior Custo':
        df_filtrado = df_filtrado.nlargest(qtd, 'CUSTO_FINANCEIRO')
    elif ordenar == 'Maior Principal':
        df_filtrado = df_filtrado.nlargest(qtd, 'VALOR_ORIGINAL')
    else:
        df_filtrado['TAXA_CUSTO'] = (df_filtrado['CUSTO_FINANCEIRO'] / df_filtrado['VALOR_ORIGINAL'] * 100).fillna(0)
        df_filtrado = df_filtrado.nlargest(qtd, 'TAXA_CUSTO')

    if len(df_filtrado) == 0:
        st.info("Nenhum registro encontrado com os filtros selecionados.")
        return

    # Preparar tabela
    colunas = ['NOME_FILIAL', 'NOME_FORNECEDOR', 'DESCRICAO', 'EMISSAO', 'VALOR_ORIGINAL',
               'VALOR_JUROS', 'VALOR_MULTA', 'CUSTO_FINANCEIRO', 'TX_MOEDA', 'STATUS']
    colunas_disp = [c for c in colunas if c in df_filtrado.columns]
    df_tab = df_filtrado[colunas_disp].copy()

    # Formatar
    df_tab['EMISSAO'] = pd.to_datetime(df_tab['EMISSAO']).dt.strftime('%d/%m/%Y')
    for col in ['VALOR_ORIGINAL', 'VALOR_JUROS', 'VALOR_MULTA', 'CUSTO_FINANCEIRO']:
        if col in df_tab.columns:
            df_tab[col] = df_tab[col].apply(lambda x: formatar_moeda(x, completo=True))

    if 'TX_MOEDA' in df_tab.columns:
        df_tab['TX_MOEDA'] = df_tab['TX_MOEDA'].apply(lambda x: f"{x:.4f}" if x > 1 else '-')

    nomes = {
        'NOME_FILIAL': 'Filial',
        'NOME_FORNECEDOR': 'Fornecedor',
        'DESCRICAO': 'Categoria',
        'EMISSAO': 'Emissao',
        'VALOR_ORIGINAL': 'Principal',
        'VALOR_JUROS': 'Juros',
        'VALOR_MULTA': 'Multa',
        'CUSTO_FINANCEIRO': 'Custo Total',
        'TX_MOEDA': 'Taxa USD',
        'STATUS': 'Status'
    }
    df_tab.columns = [nomes.get(c, c) for c in df_tab.columns]

    st.dataframe(df_tab, use_container_width=True, hide_index=True, height=400)
    st.caption(f"Exibindo {len(df_tab)} registros")
