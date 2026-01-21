"""
Aba Bancos - Emprestimos, Financiamentos, Operacoes Bancarias
Com analise de parcelas pagas e pendentes
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from config.theme import get_cores
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero


def render_bancos(df):
    """Renderiza a aba de Bancos (Emprestimos, Financiamentos) com analise de parcelas"""
    cores = get_cores()

    if len(df) == 0:
        st.info("Nenhum registro de operacoes bancarias no periodo.")
        return

    # Preparar dados
    df_bancos = df.copy()

    # Garantir colunas necessarias
    colunas_necessarias = ['VALOR_JUROS', 'VALOR_MULTA', 'VALOR_CORRECAO', 'VALOR_ACRESCIMO', 'VLR_DESCONTO', 'TX_MOEDA', 'PARCELA']
    for col in colunas_necessarias:
        if col not in df_bancos.columns:
            df_bancos[col] = 0
        else:
            df_bancos[col] = pd.to_numeric(df_bancos[col], errors='coerce').fillna(0)

    # Total de custos financeiros adicionais
    df_bancos['CUSTO_ADICIONAL'] = (
        df_bancos['VALOR_JUROS'] +
        df_bancos['VALOR_MULTA'] +
        df_bancos['VALOR_CORRECAO'] +
        df_bancos['VALOR_ACRESCIMO']
    )

    # ========== FILTROS ==========
    st.markdown("##### Filtros")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        # Filtro de banco/fornecedor
        bancos = ['Todos'] + sorted(df_bancos['NOME_FORNECEDOR'].dropna().unique().tolist())
        filtro_banco = st.selectbox("Banco/Instituicao", bancos, key="banco_filtro")

    with col2:
        # Filtro de tipo de operacao
        tipos = ['Todas'] + sorted(df_bancos['DESCRICAO'].dropna().unique().tolist())
        filtro_tipo = st.selectbox("Tipo de Operacao", tipos, key="banco_tipo")

    with col3:
        # Filtro de filial
        filiais = ['Todas'] + sorted(df_bancos['NOME_FILIAL'].dropna().unique().tolist())
        filtro_filial = st.selectbox("Filial", filiais, key="banco_filial")

    with col4:
        # Filtro de status
        filtro_status = st.selectbox("Status Parcela", ["Todas", "Pagas", "Pendentes", "Vencidas"], key="banco_status")

    # Aplicar filtros
    df_filtrado = df_bancos.copy()

    if filtro_banco != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['NOME_FORNECEDOR'] == filtro_banco]

    if filtro_tipo != 'Todas':
        df_filtrado = df_filtrado[df_filtrado['DESCRICAO'] == filtro_tipo]

    if filtro_filial != 'Todas':
        df_filtrado = df_filtrado[df_filtrado['NOME_FILIAL'] == filtro_filial]

    if filtro_status == 'Pagas':
        df_filtrado = df_filtrado[df_filtrado['SALDO'] == 0]
    elif filtro_status == 'Pendentes':
        df_filtrado = df_filtrado[df_filtrado['SALDO'] > 0]
    elif filtro_status == 'Vencidas':
        df_filtrado = df_filtrado[df_filtrado['STATUS'] == 'Vencido']

    st.divider()

    # ========== KPIs PRINCIPAIS ==========
    _render_kpis(df_filtrado, cores)

    st.divider()

    # ========== ANALISE DE PARCELAS ==========
    _render_analise_parcelas(df_filtrado, cores)

    st.divider()

    # ========== POR BANCO ==========
    _render_por_banco(df_filtrado, cores)

    st.divider()

    # ========== POR TIPO DE OPERACAO ==========
    _render_por_tipo(df_filtrado, cores)

    st.divider()

    # ========== CRONOGRAMA DE VENCIMENTOS ==========
    _render_cronograma(df_filtrado, cores)

    st.divider()

    # ========== DETALHES ==========
    _render_detalhes(df_filtrado, cores)


def _render_kpis(df, cores):
    """KPIs principais com foco em parcelas"""

    total_principal = df['VALOR_ORIGINAL'].sum()
    total_saldo = df['SALDO'].sum()
    total_pago = total_principal - total_saldo
    total_juros = df['VALOR_JUROS'].sum()
    total_custos = df['CUSTO_ADICIONAL'].sum()

    # Parcelas
    total_parcelas = len(df)
    parcelas_pagas = len(df[df['SALDO'] == 0])
    parcelas_pendentes = len(df[df['SALDO'] > 0])
    parcelas_vencidas = len(df[df['STATUS'] == 'Vencido'])

    pct_parcelas_pagas = (parcelas_pagas / total_parcelas * 100) if total_parcelas > 0 else 0
    pct_valor_pago = (total_pago / total_principal * 100) if total_principal > 0 else 0

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    col1.metric(
        "Total Parcelas",
        formatar_numero(total_parcelas),
        f"Principal: {formatar_moeda(total_principal)}"
    )

    col2.metric(
        "Parcelas Pagas",
        formatar_numero(parcelas_pagas),
        f"{pct_parcelas_pagas:.1f}% do total"
    )

    col3.metric(
        "Parcelas Pendentes",
        formatar_numero(parcelas_pendentes),
        f"Saldo: {formatar_moeda(total_saldo)}"
    )

    col4.metric(
        "Parcelas Vencidas",
        formatar_numero(parcelas_vencidas),
        f"{(parcelas_vencidas/total_parcelas*100) if total_parcelas > 0 else 0:.1f}% do total"
    )

    col5.metric(
        "Valor Pago",
        formatar_moeda(total_pago),
        f"{pct_valor_pago:.1f}% quitado"
    )

    col6.metric(
        "Juros Pagos",
        formatar_moeda(total_juros),
        f"{(total_juros/total_principal*100) if total_principal > 0 else 0:.2f}% do principal"
    )


def _render_analise_parcelas(df, cores):
    """Analise detalhada de parcelas por contrato/operacao"""

    st.markdown("##### Analise de Parcelas por Contrato")

    # Agrupar por NUMERO (identificador do contrato/emprestimo)
    df_contratos = df.groupby(['NOME_FORNECEDOR', 'NUMERO']).agg({
        'PARCELA': 'max',  # Total de parcelas do contrato
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'VALOR_JUROS': 'sum',
        'DESCRICAO': 'first',
        'EMISSAO': 'min',
        'VENCIMENTO': 'max'
    }).reset_index()

    # Contar parcelas pagas e pendentes por contrato
    df_parc_status = df.groupby(['NOME_FORNECEDOR', 'NUMERO']).apply(
        lambda x: pd.Series({
            'Parcelas_Pagas': len(x[x['SALDO'] == 0]),
            'Parcelas_Pendentes': len(x[x['SALDO'] > 0]),
            'Parcelas_Vencidas': len(x[x['STATUS'] == 'Vencido'])
        })
    ).reset_index()

    df_contratos = df_contratos.merge(df_parc_status, on=['NOME_FORNECEDOR', 'NUMERO'])
    df_contratos['Total_Parcelas'] = df_contratos['Parcelas_Pagas'] + df_contratos['Parcelas_Pendentes']
    df_contratos['Pago'] = df_contratos['VALOR_ORIGINAL'] - df_contratos['SALDO']
    df_contratos['% Quitado'] = (df_contratos['Pago'] / df_contratos['VALOR_ORIGINAL'] * 100).round(1)
    df_contratos = df_contratos.sort_values('VALOR_ORIGINAL', ascending=False)

    col1, col2 = st.columns(2)

    with col1:
        # Grafico de parcelas pagas vs pendentes por banco
        st.markdown("###### Parcelas por Banco")

        df_banco_parc = df.groupby('NOME_FORNECEDOR').apply(
            lambda x: pd.Series({
                'Pagas': len(x[x['SALDO'] == 0]),
                'Pendentes': len(x[x['SALDO'] > 0]),
                'Vencidas': len(x[x['STATUS'] == 'Vencido'])
            })
        ).reset_index()
        df_banco_parc = df_banco_parc.sort_values('Pagas', ascending=False).head(10)

        fig = go.Figure()

        fig.add_trace(go.Bar(
            y=df_banco_parc['NOME_FORNECEDOR'].str[:25],
            x=df_banco_parc['Pagas'],
            orientation='h',
            name='Pagas',
            marker_color=cores['sucesso']
        ))

        fig.add_trace(go.Bar(
            y=df_banco_parc['NOME_FORNECEDOR'].str[:25],
            x=df_banco_parc['Pendentes'],
            orientation='h',
            name='Pendentes',
            marker_color=cores['alerta']
        ))

        fig.add_trace(go.Bar(
            y=df_banco_parc['NOME_FORNECEDOR'].str[:25],
            x=df_banco_parc['Vencidas'],
            orientation='h',
            name='Vencidas',
            marker_color=cores['perigo']
        ))

        fig.update_layout(
            criar_layout(350, barmode='stack'),
            yaxis={'autorange': 'reversed'},
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
            margin=dict(l=10, r=10, t=30, b=10)
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Resumo geral de parcelas
        st.markdown("###### Resumo de Parcelas")

        total_parcelas = len(df)
        pagas = len(df[df['SALDO'] == 0])
        pendentes = len(df[df['SALDO'] > 0])
        vencidas = len(df[df['STATUS'] == 'Vencido'])

        fig = go.Figure(go.Pie(
            labels=['Pagas', 'Pendentes (em dia)', 'Vencidas'],
            values=[pagas, pendentes - vencidas, vencidas],
            hole=0.5,
            marker=dict(colors=[cores['sucesso'], cores['alerta'], cores['perigo']]),
            textinfo='percent+value',
            textfont=dict(size=11),
            hovertemplate='<b>%{label}</b><br>%{value} parcelas<br>%{percent}<extra></extra>'
        ))

        fig.update_layout(
            criar_layout(350),
            showlegend=True,
            legend=dict(orientation='h', yanchor='bottom', y=-0.2, xanchor='center', x=0.5),
            margin=dict(l=10, r=10, t=10, b=50)
        )

        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Tabela de contratos
    st.markdown("###### Detalhamento por Contrato")

    df_show = df_contratos.head(20).copy()
    df_show['VALOR_ORIGINAL'] = df_show['VALOR_ORIGINAL'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Pago'] = df_show['Pago'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['SALDO'] = df_show['SALDO'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['VALOR_JUROS'] = df_show['VALOR_JUROS'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['% Quitado'] = df_show['% Quitado'].apply(lambda x: f"{x:.1f}%")
    df_show['EMISSAO'] = pd.to_datetime(df_show['EMISSAO']).dt.strftime('%d/%m/%Y')
    df_show['VENCIMENTO'] = pd.to_datetime(df_show['VENCIMENTO']).dt.strftime('%d/%m/%Y')

    df_show = df_show.rename(columns={
        'NOME_FORNECEDOR': 'Banco',
        'NUMERO': 'Contrato',
        'DESCRICAO': 'Tipo',
        'Total_Parcelas': 'Total',
        'Parcelas_Pagas': 'Pagas',
        'Parcelas_Pendentes': 'Pendentes',
        'Parcelas_Vencidas': 'Vencidas',
        'VALOR_ORIGINAL': 'Principal',
        'SALDO': 'Saldo',
        'VALOR_JUROS': 'Juros',
        'EMISSAO': 'Inicio',
        'VENCIMENTO': 'Fim'
    })

    st.dataframe(
        df_show[['Banco', 'Contrato', 'Tipo', 'Total', 'Pagas', 'Pendentes', 'Vencidas', 'Principal', 'Pago', 'Saldo', '% Quitado']],
        use_container_width=True,
        hide_index=True,
        height=350
    )


def _render_por_banco(df, cores):
    """Analise por banco/instituicao"""

    st.markdown("##### Por Banco/Instituicao")

    df_banco = df.groupby('NOME_FORNECEDOR').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'VALOR_JUROS': 'sum',
        'NUMERO': 'nunique',  # Quantidade de contratos
        'PARCELA': 'count'  # Quantidade de parcelas
    }).reset_index()
    df_banco.columns = ['Banco', 'Principal', 'Saldo', 'Juros', 'Contratos', 'Parcelas']
    df_banco['Pago'] = df_banco['Principal'] - df_banco['Saldo']
    df_banco['% Pago'] = (df_banco['Pago'] / df_banco['Principal'] * 100).round(1)
    df_banco = df_banco.sort_values('Principal', ascending=False)

    col1, col2 = st.columns(2)

    with col1:
        # Grafico
        df_top = df_banco.head(10)

        fig = go.Figure()

        fig.add_trace(go.Bar(
            y=df_top['Banco'].str[:25],
            x=df_top['Pago'],
            orientation='h',
            name='Pago',
            marker_color=cores['sucesso']
        ))

        fig.add_trace(go.Bar(
            y=df_top['Banco'].str[:25],
            x=df_top['Saldo'],
            orientation='h',
            name='Saldo Pendente',
            marker_color=cores['alerta']
        ))

        fig.update_layout(
            criar_layout(400, barmode='stack'),
            yaxis={'autorange': 'reversed'},
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
            margin=dict(l=10, r=10, t=30, b=10)
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Tabela
        df_tab = df_banco.copy()
        df_tab['Principal'] = df_tab['Principal'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab['Pago'] = df_tab['Pago'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab['Saldo'] = df_tab['Saldo'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab['Juros'] = df_tab['Juros'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab['% Pago'] = df_tab['% Pago'].apply(lambda x: f"{x:.1f}%")

        st.dataframe(df_tab, use_container_width=True, hide_index=True, height=400)


def _render_por_tipo(df, cores):
    """Analise por tipo de operacao"""

    st.markdown("##### Por Tipo de Operacao")

    df_tipo = df.groupby('DESCRICAO').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'VALOR_JUROS': 'sum',
        'NUMERO': 'nunique',
        'PARCELA': 'count'
    }).reset_index()
    df_tipo.columns = ['Tipo', 'Principal', 'Saldo', 'Juros', 'Contratos', 'Parcelas']
    df_tipo['Pago'] = df_tipo['Principal'] - df_tipo['Saldo']
    df_tipo['% Pago'] = (df_tipo['Pago'] / df_tipo['Principal'] * 100).round(1)

    # Parcelas pagas/pendentes por tipo
    df_tipo_parc = df.groupby('DESCRICAO').apply(
        lambda x: pd.Series({
            'Parc_Pagas': len(x[x['SALDO'] == 0]),
            'Parc_Pendentes': len(x[x['SALDO'] > 0])
        })
    ).reset_index()
    df_tipo = df_tipo.merge(df_tipo_parc, left_on='Tipo', right_on='DESCRICAO').drop('DESCRICAO', axis=1)
    df_tipo = df_tipo.sort_values('Principal', ascending=False)

    col1, col2 = st.columns(2)

    with col1:
        # Pizza por tipo
        fig = go.Figure(go.Pie(
            labels=df_tipo['Tipo'].str[:20],
            values=df_tipo['Principal'],
            hole=0.4,
            textinfo='percent',
            textfont=dict(size=9),
            hovertemplate='<b>%{label}</b><br>R$ %{value:,.2f}<br>%{percent}<extra></extra>'
        ))

        fig.update_layout(
            criar_layout(350),
            showlegend=True,
            legend=dict(orientation='v', yanchor='middle', y=0.5, xanchor='left', x=1.02, font=dict(size=8)),
            margin=dict(l=10, r=120, t=10, b=10)
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Tabela
        df_tab = df_tipo.copy()
        df_tab['Principal'] = df_tab['Principal'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab['Pago'] = df_tab['Pago'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab['Saldo'] = df_tab['Saldo'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab['Juros'] = df_tab['Juros'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab['% Pago'] = df_tab['% Pago'].apply(lambda x: f"{x:.1f}%")

        st.dataframe(
            df_tab[['Tipo', 'Contratos', 'Parcelas', 'Parc_Pagas', 'Parc_Pendentes', 'Principal', 'Pago', 'Saldo', '% Pago']],
            use_container_width=True,
            hide_index=True,
            height=350
        )


def _render_cronograma(df, cores):
    """Cronograma de vencimentos futuros"""

    st.markdown("##### Cronograma de Vencimentos")

    # Filtrar apenas pendentes
    df_pend = df[df['SALDO'] > 0].copy()

    if len(df_pend) == 0:
        st.success("Nenhuma parcela pendente!")
        return

    # Agrupar por mes de vencimento
    df_pend['MES_VENC'] = df_pend['VENCIMENTO'].dt.to_period('M')

    df_crono = df_pend.groupby('MES_VENC').agg({
        'SALDO': 'sum',
        'NUMERO': 'count'
    }).reset_index()
    df_crono.columns = ['Mes', 'Valor', 'Parcelas']
    df_crono['Mes'] = df_crono['Mes'].astype(str)

    col1, col2 = st.columns([2, 1])

    with col1:
        # Grafico de barras do cronograma
        fig = go.Figure(go.Bar(
            x=df_crono['Mes'],
            y=df_crono['Valor'],
            marker_color=cores['info'],
            text=[formatar_moeda(v) for v in df_crono['Valor']],
            textposition='outside',
            textfont=dict(size=9)
        ))

        fig.update_layout(
            criar_layout(300),
            xaxis_title='Mes de Vencimento',
            yaxis_title='Valor (R$)',
            margin=dict(l=10, r=10, t=10, b=50),
            xaxis_tickangle=-45
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Resumo
        st.markdown("###### Resumo")

        hoje = datetime.now()
        df_pend['DIAS_VENC'] = (df_pend['VENCIMENTO'] - pd.Timestamp(hoje)).dt.days

        vence_7d = df_pend[df_pend['DIAS_VENC'].between(0, 7)]['SALDO'].sum()
        vence_30d = df_pend[df_pend['DIAS_VENC'].between(0, 30)]['SALDO'].sum()
        vence_60d = df_pend[df_pend['DIAS_VENC'].between(0, 60)]['SALDO'].sum()
        vencido = df_pend[df_pend['DIAS_VENC'] < 0]['SALDO'].sum()

        st.metric("Vencido", formatar_moeda(vencido), delta=f"{len(df_pend[df_pend['DIAS_VENC'] < 0])} parcelas", delta_color="inverse")
        st.metric("Vence em 7 dias", formatar_moeda(vence_7d), f"{len(df_pend[df_pend['DIAS_VENC'].between(0, 7)])} parcelas")
        st.metric("Vence em 30 dias", formatar_moeda(vence_30d), f"{len(df_pend[df_pend['DIAS_VENC'].between(0, 30)])} parcelas")
        st.metric("Vence em 60 dias", formatar_moeda(vence_60d), f"{len(df_pend[df_pend['DIAS_VENC'].between(0, 60)])} parcelas")


def _render_detalhes(df, cores):
    """Tabela de detalhes das parcelas"""

    st.markdown("##### Detalhamento de Parcelas")

    # Filtros adicionais
    col1, col2, col3 = st.columns(3)

    with col1:
        ordenar = st.selectbox("Ordenar por", ["Vencimento", "Maior valor", "Maior saldo", "Banco"], key="banco_ordem_det")

    with col2:
        limite = st.selectbox("Exibir", [50, 100, 200, 500], key="banco_limite")

    with col3:
        mostrar = st.radio("Mostrar", ["Todas", "Apenas pendentes", "Apenas vencidas"], horizontal=True, key="banco_mostrar")

    # Aplicar filtros
    df_show = df.copy()

    if mostrar == "Apenas pendentes":
        df_show = df_show[df_show['SALDO'] > 0]
    elif mostrar == "Apenas vencidas":
        df_show = df_show[df_show['STATUS'] == 'Vencido']

    # Ordenar
    if ordenar == "Vencimento":
        df_show = df_show.sort_values('VENCIMENTO')
    elif ordenar == "Maior valor":
        df_show = df_show.sort_values('VALOR_ORIGINAL', ascending=False)
    elif ordenar == "Maior saldo":
        df_show = df_show.sort_values('SALDO', ascending=False)
    else:
        df_show = df_show.sort_values('NOME_FORNECEDOR')

    df_show = df_show.head(limite)

    if len(df_show) == 0:
        st.info("Nenhum registro encontrado.")
        return

    # Preparar tabela
    colunas = ['NOME_FILIAL', 'NOME_FORNECEDOR', 'NUMERO', 'PARCELA', 'DESCRICAO', 'EMISSAO', 'VENCIMENTO',
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
        'NOME_FORNECEDOR': 'Banco',
        'NUMERO': 'Contrato',
        'PARCELA': 'Parcela',
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
    st.caption(f"Exibindo {len(df_tab)} parcelas")
