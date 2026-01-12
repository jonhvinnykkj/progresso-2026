"""
Aba Custos Financeiros - Analise de Juros, Multas e Variacao Cambial
Foco em valores adicionais recebidos (juros de mora, multas) e operacoes em Dolar
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

from config.theme import get_cores
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero


# Padroes para identificar categorias de Bancos/Financeiras
PADROES_BANCOS = [
    'BANCO', 'BRADESCO', 'ITAU', 'SANTANDER', 'BB ', 'CAIXA', 'BTG',
    'SAFRA', 'SICREDI', 'SICOOB', 'INTER', 'NUBANK', 'C6', 'ORIGINAL',
    'FINANC', 'EMPREST', 'LEASING', 'CDC', 'CCB', 'FINAME', 'BNDES',
    'CREDITO', 'CAPITAL DE GIRO', 'DESCONTO', 'ANTECIPACAO', 'FIDC'
]


def render_custos_financeiros_receber(df):
    """Renderiza a aba de Custos Financeiros para Contas a Receber"""
    cores = get_cores()

    if len(df) == 0:
        st.warning("Nenhum dado disponivel.")
        return

    # Preparar dados
    df_custos = _preparar_dados_custos(df)

    # ========== KPIs PRINCIPAIS ==========
    _render_kpis_custos(df_custos, cores)

    st.divider()

    # ========== SECAO JUROS E MULTAS RECEBIDOS ==========
    st.markdown(f"""
    <div style="background: {cores['card']}; border-left: 4px solid {cores['sucesso']};
                padding: 0.75rem 1rem; border-radius: 0 8px 8px 0; margin-bottom: 1rem;">
        <h4 style="color: {cores['texto']}; margin: 0;">Juros e Multas Recebidos</h4>
        <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0;">
            Valores adicionais cobrados por atraso
        </p>
    </div>
    """, unsafe_allow_html=True)

    _render_secao_juros_recebidos(df_custos, cores)

    st.divider()

    # ========== SECAO DOLAR ==========
    st.markdown(f"""
    <div style="background: {cores['card']}; border-left: 4px solid {cores['info']};
                padding: 0.75rem 1rem; border-radius: 0 8px 8px 0; margin-bottom: 1rem;">
        <h4 style="color: {cores['texto']}; margin: 0;">Operacoes em Dolar (USD)</h4>
        <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0;">
            Recebiveis com variacao cambial
        </p>
    </div>
    """, unsafe_allow_html=True)

    _render_secao_dolar(df_custos, cores)

    st.divider()

    # ========== ANALISE POR NATUREZA ==========
    st.markdown(f"""
    <div style="background: {cores['card']}; border-left: 4px solid {cores['alerta']};
                padding: 0.75rem 1rem; border-radius: 0 8px 8px 0; margin-bottom: 1rem;">
        <h4 style="color: {cores['texto']}; margin: 0;">Receitas por Natureza</h4>
        <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0;">
            Segregacao por categoria
        </p>
    </div>
    """, unsafe_allow_html=True)

    _render_receitas_por_natureza(df_custos, cores)

    st.divider()

    # ========== EVOLUCAO TEMPORAL ==========
    _render_evolucao_receitas(df_custos, cores)

    st.divider()

    # ========== DETALHAMENTO ==========
    _render_detalhes_receitas(df_custos, cores)


def _preparar_dados_custos(df):
    """Prepara dados com custos/receitas financeiras"""
    df_custos = df.copy()

    # Garantir colunas de custos
    colunas_custos = ['VALOR_JUROS', 'VALOR_MULTA', 'VALOR_CORRECAO', 'VALOR_ACRESCIMO', 'VLR_DESCONTO', 'TX_MOEDA']
    for col in colunas_custos:
        if col not in df_custos.columns:
            df_custos[col] = 0
        else:
            df_custos[col] = pd.to_numeric(df_custos[col], errors='coerce').fillna(0)

    # Total de receitas financeiras (juros e multas recebidos)
    df_custos['RECEITA_FINANCEIRA'] = (
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

    # Identificar se e Banco (na categoria ou cliente)
    col_nome = 'NOME_CLIENTE' if 'NOME_CLIENTE' in df_custos.columns else 'NOME_FORNECEDOR'
    df_custos['IS_BANCO'] = df_custos['DESCRICAO'].str.upper().str.contains(
        '|'.join(PADROES_BANCOS), na=False, regex=True
    ) | df_custos[col_nome].str.upper().str.contains(
        '|'.join(PADROES_BANCOS), na=False, regex=True
    )

    return df_custos


def _render_kpis_custos(df, cores):
    """KPIs principais de receitas financeiras"""

    total_juros = df['VALOR_JUROS'].sum()
    total_multa = df['VALOR_MULTA'].sum()
    total_correcao = df['VALOR_CORRECAO'].sum()
    total_desconto = df['VLR_DESCONTO'].sum() if 'VLR_DESCONTO' in df.columns else 0
    total_receitas = df['RECEITA_FINANCEIRA'].sum()
    total_principal = df['VALOR_ORIGINAL'].sum()

    # Percentual sobre principal
    pct_receitas = (total_receitas / total_principal * 100) if total_principal > 0 else 0

    # Operacoes em dolar
    df_dolar = df[df['IS_DOLAR']]
    receitas_dolar = df_dolar['VARIACAO_CAMBIAL'].sum() if len(df_dolar) > 0 else 0
    principal_dolar = df_dolar['VALOR_ORIGINAL'].sum() if len(df_dolar) > 0 else 0

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            label="Total Receita Financ.",
            value=formatar_moeda(total_receitas),
            delta=f"{pct_receitas:.2f}% do principal",
            delta_color="normal"
        )

    with col2:
        st.metric(
            label="Juros Recebidos",
            value=formatar_moeda(total_juros),
            delta=f"{len(df[df['VALOR_JUROS'] > 0])} titulos",
            delta_color="off"
        )

    with col3:
        st.metric(
            label="Multas Recebidas",
            value=formatar_moeda(total_multa),
            delta=f"{len(df[df['VALOR_MULTA'] > 0])} titulos",
            delta_color="off"
        )

    with col4:
        st.metric(
            label="Descontos Concedidos",
            value=formatar_moeda(total_desconto),
            delta=f"{len(df[df['VLR_DESCONTO'] > 0])} titulos",
            delta_color="inverse"
        )

    with col5:
        st.metric(
            label="Var. Cambial USD",
            value=formatar_moeda(receitas_dolar),
            delta=f"{len(df_dolar)} operacoes",
            delta_color="off"
        )


def _render_secao_juros_recebidos(df, cores):
    """Secao de analise de Juros e Multas Recebidos"""

    df_com_juros = df[(df['VALOR_JUROS'] > 0) | (df['VALOR_MULTA'] > 0)].copy()

    if len(df_com_juros) == 0:
        st.info("Nenhum titulo com juros ou multas recebidos no periodo.")
        return

    col1, col2 = st.columns(2)

    with col1:
        # Resumo por cliente
        st.markdown("##### Por Cliente")

        col_nome = 'NOME_CLIENTE' if 'NOME_CLIENTE' in df_com_juros.columns else 'NOME_FORNECEDOR'
        df_cliente_agg = df_com_juros.groupby(col_nome).agg({
            'VALOR_ORIGINAL': 'sum',
            'VALOR_JUROS': 'sum',
            'VALOR_MULTA': 'sum',
            'RECEITA_FINANCEIRA': 'sum',
            'SALDO': 'sum'
        }).reset_index()
        df_cliente_agg.columns = ['Cliente', 'Principal', 'Juros', 'Multa', 'Receita_Total', 'Saldo']
        df_cliente_agg = df_cliente_agg.sort_values('Receita_Total', ascending=False).head(10)

        fig = go.Figure()

        fig.add_trace(go.Bar(
            y=df_cliente_agg['Cliente'].str[:25],
            x=df_cliente_agg['Juros'],
            orientation='h',
            name='Juros',
            marker_color=cores['sucesso'],
            text=[formatar_moeda(v) if v > 0 else '' for v in df_cliente_agg['Juros']],
            textposition='inside',
            textfont=dict(size=9, color='white')
        ))

        fig.add_trace(go.Bar(
            y=df_cliente_agg['Cliente'].str[:25],
            x=df_cliente_agg['Multa'],
            orientation='h',
            name='Multas',
            marker_color=cores['alerta'],
            text=[formatar_moeda(v) if v > 0 else '' for v in df_cliente_agg['Multa']],
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
        # Tabela resumo
        st.markdown("##### Detalhamento por Cliente")

        df_tab = df_cliente_agg.copy()
        df_tab['Taxa_Juros'] = (df_tab['Receita_Total'] / df_tab['Principal'] * 100).round(2)
        df_tab['Principal'] = df_tab['Principal'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab['Juros'] = df_tab['Juros'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab['Multa'] = df_tab['Multa'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab['Receita_Total'] = df_tab['Receita_Total'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab['Saldo'] = df_tab['Saldo'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab['Taxa_Juros'] = df_tab['Taxa_Juros'].apply(lambda x: f"{x:.2f}%")

        df_tab.columns = ['Cliente', 'Principal', 'Juros', 'Multa', 'Receita Total', 'Saldo', '% Receita']

        st.dataframe(df_tab, use_container_width=True, hide_index=True, height=350)

    # KPIs
    st.markdown("##### Resumo Receitas Financeiras")
    col1, col2, col3, col4 = st.columns(4)

    total_principal = df_com_juros['VALOR_ORIGINAL'].sum()
    total_juros = df_com_juros['VALOR_JUROS'].sum()
    total_multas = df_com_juros['VALOR_MULTA'].sum()
    taxa_media = ((total_juros + total_multas) / total_principal * 100) if total_principal > 0 else 0

    col1.metric("Principal Total", formatar_moeda(total_principal))
    col2.metric("Juros Recebidos", formatar_moeda(total_juros))
    col3.metric("Multas Recebidas", formatar_moeda(total_multas))
    col4.metric("Taxa Media", f"{taxa_media:.2f}%")


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

        # Por cliente em dolar
        st.markdown("##### Top Clientes USD")

        col_nome = 'NOME_CLIENTE' if 'NOME_CLIENTE' in df_dolar.columns else 'NOME_FORNECEDOR'
        df_dolar_cli = df_dolar.groupby(col_nome).agg({
            'VALOR_ORIGINAL': 'sum',
            'TX_MOEDA': 'mean',
            'VARIACAO_CAMBIAL': 'sum'
        }).nlargest(8, 'VALOR_ORIGINAL').reset_index()

        fig = go.Figure(go.Bar(
            y=df_dolar_cli[col_nome].str[:20],
            x=df_dolar_cli['VALOR_ORIGINAL'],
            orientation='h',
            marker_color=cores['info'],
            text=[f"{formatar_moeda(v)}" for v in df_dolar_cli['VALOR_ORIGINAL']],
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
                line=dict(color=cores['info'], width=2),
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

        col_nome = 'NOME_CLIENTE' if 'NOME_CLIENTE' in df_dolar.columns else 'NOME_FORNECEDOR'
        colunas = [col_nome, 'EMISSAO', 'VALOR_ORIGINAL', 'TX_MOEDA', 'VARIACAO_CAMBIAL', 'STATUS']
        colunas_disp = [c for c in colunas if c in df_dolar.columns]
        df_tab = df_dolar[colunas_disp].nlargest(10, 'VALOR_ORIGINAL').copy()

        df_tab['EMISSAO'] = pd.to_datetime(df_tab['EMISSAO']).dt.strftime('%d/%m/%Y')
        df_tab['VALOR_ORIGINAL'] = df_tab['VALOR_ORIGINAL'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab['TX_MOEDA'] = df_tab['TX_MOEDA'].apply(lambda x: f"{x:.4f}")
        df_tab['VARIACAO_CAMBIAL'] = df_tab['VARIACAO_CAMBIAL'].apply(lambda x: formatar_moeda(x, completo=True))

        df_tab.columns = ['Cliente', 'Emissao', 'Valor', 'Taxa', 'Var. Cambial', 'Status']

        st.dataframe(df_tab, use_container_width=True, hide_index=True, height=200)


def _render_receitas_por_natureza(df, cores):
    """Analise de receitas por natureza/categoria"""

    # Filtrar apenas registros com receitas financeiras
    df_com_receitas = df[df['RECEITA_FINANCEIRA'] > 0].copy()

    if len(df_com_receitas) == 0:
        st.info("Nenhum registro com receitas financeiras no periodo.")
        return

    col1, col2 = st.columns(2)

    with col1:
        # Por categoria
        st.markdown("##### Receitas por Categoria")

        df_cat = df_com_receitas.groupby('DESCRICAO').agg({
            'VALOR_ORIGINAL': 'sum',
            'VALOR_JUROS': 'sum',
            'VALOR_MULTA': 'sum',
            'RECEITA_FINANCEIRA': 'sum'
        }).nlargest(10, 'RECEITA_FINANCEIRA').reset_index()

        fig = go.Figure()

        fig.add_trace(go.Bar(
            y=df_cat['DESCRICAO'].str[:25],
            x=df_cat['VALOR_JUROS'],
            orientation='h',
            name='Juros',
            marker_color=cores['sucesso']
        ))

        fig.add_trace(go.Bar(
            y=df_cat['DESCRICAO'].str[:25],
            x=df_cat['VALOR_MULTA'],
            orientation='h',
            name='Multas',
            marker_color=cores['alerta']
        ))

        fig.update_layout(
            criar_layout(300, barmode='stack'),
            yaxis={'autorange': 'reversed'},
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=10, r=10, t=30, b=10)
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Taxa de receita por categoria
        st.markdown("##### Taxa de Receita por Categoria")

        df_cat['Taxa'] = (df_cat['RECEITA_FINANCEIRA'] / df_cat['VALOR_ORIGINAL'] * 100).round(2)
        df_cat_sorted = df_cat.nlargest(10, 'Taxa')

        def cor_taxa(t):
            if t >= 5:
                return cores['sucesso']
            elif t >= 2:
                return cores['info']
            elif t >= 1:
                return cores['alerta']
            return cores['texto_secundario']

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
            xaxis_title='% Receita sobre Principal',
            margin=dict(l=10, r=50, t=10, b=10)
        )

        st.plotly_chart(fig, use_container_width=True)
        st.caption("Verde >= 5% | Azul >= 2% | Amarelo >= 1% | Cinza < 1%")


def _render_evolucao_receitas(df, cores):
    """Evolucao temporal das receitas"""

    st.markdown("##### Evolucao Mensal de Receitas Financeiras")

    df_temp = df.copy()
    df_temp['MES'] = df_temp['EMISSAO'].dt.to_period('M')

    df_mes = df_temp.groupby('MES').agg({
        'VALOR_JUROS': 'sum',
        'VALOR_MULTA': 'sum',
        'VALOR_CORRECAO': 'sum',
        'RECEITA_FINANCEIRA': 'sum',
        'VALOR_ORIGINAL': 'sum'
    }).reset_index()

    df_mes['MES'] = df_mes['MES'].astype(str)
    df_mes['Taxa'] = (df_mes['RECEITA_FINANCEIRA'] / df_mes['VALOR_ORIGINAL'] * 100).fillna(0)

    if len(df_mes) < 2:
        st.info("Dados insuficientes para grafico de evolucao")
        return

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df_mes['MES'],
        y=df_mes['VALOR_JUROS'],
        name='Juros',
        marker_color=cores['sucesso']
    ))

    fig.add_trace(go.Bar(
        x=df_mes['MES'],
        y=df_mes['VALOR_MULTA'],
        name='Multas',
        marker_color=cores['alerta']
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
        name='% Receita',
        yaxis='y2',
        line=dict(color=cores['texto'], width=2),
        marker=dict(size=6)
    ))

    fig.update_layout(
        criar_layout(300, barmode='stack'),
        yaxis=dict(title='Valor (R$)'),
        yaxis2=dict(title='% Receita', overlaying='y', side='right', showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=50, t=30, b=30),
        xaxis_tickangle=-45
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_detalhes_receitas(df, cores):
    """Detalhamento das receitas"""

    st.markdown("##### Detalhamento de Receitas Financeiras")

    # Filtros
    col1, col2, col3 = st.columns(3)

    with col1:
        tipo_filtro = st.selectbox(
            "Tipo",
            ['Todos', 'Apenas Dolar', 'Com Juros', 'Com Multa'],
            key="cfr_tipo"
        )

    with col2:
        ordenar = st.selectbox(
            "Ordenar por",
            ['Maior Receita', 'Maior Principal', 'Maior Taxa'],
            key="cfr_ordem"
        )

    with col3:
        qtd = st.selectbox("Exibir", [20, 50, 100], key="cfr_qtd")

    # Aplicar filtros
    df_filtrado = df.copy()

    if tipo_filtro == 'Apenas Dolar':
        df_filtrado = df_filtrado[df_filtrado['IS_DOLAR']]
    elif tipo_filtro == 'Com Juros':
        df_filtrado = df_filtrado[df_filtrado['VALOR_JUROS'] > 0]
    elif tipo_filtro == 'Com Multa':
        df_filtrado = df_filtrado[df_filtrado['VALOR_MULTA'] > 0]

    # Ordenar
    if ordenar == 'Maior Receita':
        df_filtrado = df_filtrado.nlargest(qtd, 'RECEITA_FINANCEIRA')
    elif ordenar == 'Maior Principal':
        df_filtrado = df_filtrado.nlargest(qtd, 'VALOR_ORIGINAL')
    else:
        df_filtrado['TAXA_RECEITA'] = (df_filtrado['RECEITA_FINANCEIRA'] / df_filtrado['VALOR_ORIGINAL'] * 100).fillna(0)
        df_filtrado = df_filtrado.nlargest(qtd, 'TAXA_RECEITA')

    if len(df_filtrado) == 0:
        st.info("Nenhum registro encontrado com os filtros selecionados.")
        return

    # Preparar tabela
    col_nome = 'NOME_CLIENTE' if 'NOME_CLIENTE' in df_filtrado.columns else 'NOME_FORNECEDOR'
    colunas = ['NOME_FILIAL', col_nome, 'DESCRICAO', 'EMISSAO', 'VALOR_ORIGINAL',
               'VALOR_JUROS', 'VALOR_MULTA', 'RECEITA_FINANCEIRA', 'TX_MOEDA', 'STATUS']
    colunas_disp = [c for c in colunas if c in df_filtrado.columns]
    df_tab = df_filtrado[colunas_disp].copy()

    # Formatar
    df_tab['EMISSAO'] = pd.to_datetime(df_tab['EMISSAO']).dt.strftime('%d/%m/%Y')
    for col in ['VALOR_ORIGINAL', 'VALOR_JUROS', 'VALOR_MULTA', 'RECEITA_FINANCEIRA']:
        if col in df_tab.columns:
            df_tab[col] = df_tab[col].apply(lambda x: formatar_moeda(x, completo=True))

    if 'TX_MOEDA' in df_tab.columns:
        df_tab['TX_MOEDA'] = df_tab['TX_MOEDA'].apply(lambda x: f"{x:.4f}" if x > 1 else '-')

    nomes = {
        'NOME_FILIAL': 'Filial',
        'NOME_CLIENTE': 'Cliente',
        'NOME_FORNECEDOR': 'Cliente',
        'DESCRICAO': 'Categoria',
        'EMISSAO': 'Emissao',
        'VALOR_ORIGINAL': 'Principal',
        'VALOR_JUROS': 'Juros',
        'VALOR_MULTA': 'Multa',
        'RECEITA_FINANCEIRA': 'Receita Total',
        'TX_MOEDA': 'Taxa USD',
        'STATUS': 'Status'
    }
    df_tab.columns = [nomes.get(c, c) for c in df_tab.columns]

    st.dataframe(df_tab, use_container_width=True, hide_index=True, height=400)
    st.caption(f"Exibindo {len(df_tab)} registros")
