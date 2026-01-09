"""
Aba Variacao Cambial - Analise de operacoes em moeda estrangeira
Foco em Bancos, Dolar, Natureza, Principal, Juros e Variacao
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from config.theme import get_cores
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero


# Padroes para identificar operacoes cambiais/financeiras
MOEDAS_ESTRANGEIRAS = ['DOLAR COMPRA', 'DOLAR VENDA', 'EURO', 'DOLAR']
NATUREZAS_FINANCEIRAS = [
    'NATUREZA EMPRESTIMOS',
    'EMPRESTIMOS - MUTUOS',
    'EMPRESTIMOS-MUTUOS',
    'JUROS AMORTIZACAO',
    'JUROS',
    'VARIACAO CAMBIAL',
    'LEASING',
    'FINANCIAMENTO'
]


def identificar_operacoes_cambiais(df):
    """Identifica operacoes em moeda estrangeira ou de natureza financeira"""
    mask_moeda = df['MOEDA'].str.upper().isin([m.upper() for m in MOEDAS_ESTRANGEIRAS]) if 'MOEDA' in df.columns else pd.Series([False]*len(df))

    mask_natureza = pd.Series([False]*len(df))
    if 'DESCRICAO' in df.columns:
        for nat in NATUREZAS_FINANCEIRAS:
            mask_natureza |= df['DESCRICAO'].str.upper().str.contains(nat, na=False)

    return df[mask_moeda | mask_natureza].copy()


def classificar_tipo_operacao(row):
    """Classifica o tipo de operacao cambial/financeira"""
    descricao = str(row.get('DESCRICAO', '')).upper()
    moeda = str(row.get('MOEDA', '')).upper()

    if 'JUROS' in descricao:
        return 'Juros'
    elif 'VARIACAO' in descricao:
        return 'Variacao Cambial'
    elif 'EMPRESTIMO' in descricao or 'MUTUO' in descricao:
        return 'Principal (Emprestimo)'
    elif 'LEASING' in descricao:
        return 'Leasing'
    elif 'FINANCIAMENTO' in descricao:
        return 'Financiamento'
    elif moeda in ['DOLAR COMPRA', 'DOLAR VENDA', 'DOLAR', 'EURO']:
        return 'Operacao em Moeda Estrangeira'
    else:
        return 'Outros'


def render_cambio(df_contas):
    """Renderiza a aba de Variacao Cambial"""
    cores = get_cores()
    hoje = datetime.now()

    st.markdown("### Variacao Cambial e Operacoes Financeiras")
    st.caption("Analise de operacoes em moeda estrangeira, emprestimos bancarios, juros e variacao cambial")

    df_cambio = identificar_operacoes_cambiais(df_contas)

    if len(df_cambio) == 0:
        st.warning("Nenhuma operacao cambial ou financeira encontrada no periodo selecionado.")
        return

    df_cambio['TIPO_OPERACAO'] = df_cambio.apply(classificar_tipo_operacao, axis=1)

    # ========== RESUMO GERAL ==========
    st.markdown("#### Resumo Geral")

    total_cambio = df_cambio['VALOR_ORIGINAL'].sum()
    total_geral = df_contas['VALOR_ORIGINAL'].sum()
    pct_cambio = (total_cambio / total_geral * 100) if total_geral > 0 else 0

    saldo_cambio = df_cambio['SALDO'].sum()

    df_principal = df_cambio[df_cambio['TIPO_OPERACAO'].str.contains('Principal|Emprestimo|Financiamento|Leasing', na=False, regex=True)]
    df_juros = df_cambio[df_cambio['TIPO_OPERACAO'] == 'Juros']
    df_variacao = df_cambio[df_cambio['TIPO_OPERACAO'] == 'Variacao Cambial']

    total_principal = df_principal['VALOR_ORIGINAL'].sum()
    total_juros = df_juros['VALOR_ORIGINAL'].sum()
    total_variacao = df_variacao['VALOR_ORIGINAL'].sum()

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Total Operacoes", formatar_moeda(total_cambio), delta=f"{pct_cambio:.1f}% do total geral")
    col2.metric("Principal", formatar_moeda(total_principal), help="Emprestimos, financiamentos e leasing")
    col3.metric("Juros", formatar_moeda(total_juros), delta_color="inverse")
    col4.metric("Variacao Cambial", formatar_moeda(total_variacao))
    col5.metric("Saldo Pendente", formatar_moeda(saldo_cambio), delta_color="inverse" if saldo_cambio > 0 else "normal")

    st.markdown("---")

    # ========== ANALISE POR MOEDA ==========
    st.markdown("#### Analise por Moeda")

    col1, col2 = st.columns(2)

    with col1:
        if 'MOEDA' in df_cambio.columns:
            df_moeda = df_cambio.groupby('MOEDA').agg({
                'VALOR_ORIGINAL': 'sum',
                'SALDO': 'sum',
                'FORNECEDOR': 'count'
            }).reset_index()
            df_moeda.columns = ['Moeda', 'Total', 'Saldo', 'Qtd']
            df_moeda = df_moeda.sort_values('Total', ascending=False)

            cores_moeda = {
                'DOLAR COMPRA': cores['sucesso'],
                'DOLAR VENDA': cores['alerta'],
                'EURO': cores['info'],
                'REAL': cores['primaria']
            }

            fig = go.Figure(data=[go.Pie(
                labels=df_moeda['Moeda'],
                values=df_moeda['Total'],
                hole=0.5,
                marker_colors=[cores_moeda.get(m, cores['info']) for m in df_moeda['Moeda']],
                textinfo='percent+label',
                textfont_size=11
            )])

            fig.update_layout(criar_layout(320), showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)

            df_moeda_exib = pd.DataFrame({
                'Moeda': df_moeda['Moeda'],
                'Total': df_moeda['Total'].apply(lambda x: formatar_moeda(x, completo=True)),
                'Saldo': df_moeda['Saldo'].apply(lambda x: formatar_moeda(x, completo=True)),
                'Qtd Titulos': df_moeda['Qtd']
            })
            st.dataframe(df_moeda_exib, use_container_width=True, hide_index=True)
        else:
            st.info("Coluna MOEDA nao disponivel nos dados.")

    with col2:
        if 'TX_MOEDA' in df_cambio.columns:
            st.markdown("##### Taxa de Cambio")

            df_tx = df_cambio[df_cambio['TX_MOEDA'] > 0].copy()
            if len(df_tx) > 0:
                df_tx['MES_ANO'] = df_tx['EMISSAO'].dt.to_period('M')
                df_tx_mensal = df_tx.groupby('MES_ANO').agg({'TX_MOEDA': 'mean'}).reset_index()
                df_tx_mensal['MES_ANO'] = df_tx_mensal['MES_ANO'].astype(str)
                df_tx_mensal = df_tx_mensal.tail(12)

                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df_tx_mensal['MES_ANO'],
                    y=df_tx_mensal['TX_MOEDA'],
                    mode='lines+markers',
                    line=dict(color=cores['primaria'], width=2),
                    marker=dict(size=8)
                ))
                fig.update_layout(criar_layout(250), xaxis_tickangle=-45, yaxis_title='Taxa (R$)', margin=dict(l=50, r=10, t=10, b=60))
                st.plotly_chart(fig, use_container_width=True)

                tx_atual = df_tx_mensal['TX_MOEDA'].iloc[-1] if len(df_tx_mensal) > 0 else 0
                tx_media = df_tx['TX_MOEDA'].mean()

                col_a, col_b = st.columns(2)
                col_a.metric("Taxa Atual", f"R$ {tx_atual:.4f}")
                col_b.metric("Taxa Media", f"R$ {tx_media:.4f}")
            else:
                st.info("Sem dados de taxa de cambio.")
        else:
            st.info("Coluna TX_MOEDA nao disponivel.")

    st.markdown("---")

    # ========== TABS DETALHADAS ==========
    tab1, tab2, tab3, tab4 = st.tabs(["Por Banco/Fornecedor", "Por Natureza", "Evolucao", "Detalhes"])

    with tab1:
        _render_por_banco(df_cambio, cores)

    with tab2:
        _render_por_natureza(df_cambio, cores)

    with tab3:
        _render_evolucao_cambio(df_cambio, cores)

    with tab4:
        _render_detalhes_cambio(df_cambio, cores, hoje)


def _render_por_banco(df_cambio, cores):
    """Analise por banco/fornecedor"""
    df_banco = df_cambio.groupby('NOME_FORNECEDOR').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'FORNECEDOR': 'count'
    }).reset_index()
    df_banco.columns = ['Banco/Fornecedor', 'Total', 'Saldo', 'Qtd']
    df_banco['Pago'] = df_banco['Total'] - df_banco['Saldo']
    df_banco['% Pago'] = ((df_banco['Pago'] / df_banco['Total']) * 100).fillna(0).round(1)
    df_banco = df_banco.sort_values('Total', ascending=False)

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("##### Top 15 Bancos/Fornecedores")
        df_top = df_banco.head(15)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=df_top['Banco/Fornecedor'].str[:30],
            x=df_top['Pago'],
            orientation='h',
            name='Pago',
            marker_color=cores['primaria'],
            text=[formatar_moeda(v) for v in df_top['Pago']],
            textposition='inside',
            textfont=dict(size=9, color='white')
        ))

        fig.add_trace(go.Bar(
            y=df_top['Banco/Fornecedor'].str[:30],
            x=df_top['Saldo'],
            orientation='h',
            name='Pendente',
            marker_color=cores['alerta'],
            text=[formatar_moeda(v) for v in df_top['Saldo']],
            textposition='inside',
            textfont=dict(size=9, color='white')
        ))

        fig.update_layout(
            criar_layout(450, barmode='stack'),
            yaxis={'autorange': 'reversed'},
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
            margin=dict(l=10, r=10, t=40, b=10)
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("##### Resumo")
        st.metric("Total de Fornecedores", len(df_banco))
        st.metric("Valor Total", formatar_moeda(df_banco['Total'].sum()))
        st.metric("Saldo Pendente", formatar_moeda(df_banco['Saldo'].sum()))

    st.markdown("##### Tabela Completa")
    df_exib = pd.DataFrame({
        'Banco/Fornecedor': df_banco['Banco/Fornecedor'],
        'Total': df_banco['Total'].apply(lambda x: formatar_moeda(x, completo=True)),
        'Pago': df_banco['Pago'].apply(lambda x: formatar_moeda(x, completo=True)),
        'Saldo': df_banco['Saldo'].apply(lambda x: formatar_moeda(x, completo=True)),
        'Qtd': df_banco['Qtd'],
        '% Pago': df_banco['% Pago']
    })
    st.dataframe(df_exib, use_container_width=True, hide_index=True, height=350,
        column_config={'% Pago': st.column_config.ProgressColumn('% Pago', format='%.0f%%', min_value=0, max_value=100)})


def _render_por_natureza(df_cambio, cores):
    """Analise por natureza/categoria"""
    df_tipo = df_cambio.groupby('TIPO_OPERACAO').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'FORNECEDOR': 'count'
    }).reset_index()
    df_tipo.columns = ['Tipo', 'Total', 'Saldo', 'Qtd']
    df_tipo = df_tipo.sort_values('Total', ascending=False)

    col1, col2 = st.columns(2)

    cores_tipo = {
        'Principal (Emprestimo)': cores['primaria'],
        'Juros': cores['perigo'],
        'Variacao Cambial': cores['alerta'],
        'Leasing': cores['info'],
        'Financiamento': cores['sucesso'],
        'Operacao em Moeda Estrangeira': '#9333ea',
        'Outros': cores['texto_secundario']
    }

    with col1:
        st.markdown("##### Por Tipo de Operacao")
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_tipo['Tipo'],
            y=df_tipo['Total'],
            marker_color=[cores_tipo.get(t, cores['info']) for t in df_tipo['Tipo']],
            text=[formatar_moeda(v) for v in df_tipo['Total']],
            textposition='outside',
            textfont=dict(size=9)
        ))
        fig.update_layout(criar_layout(320), xaxis_tickangle=-30, margin=dict(l=10, r=10, t=10, b=80))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("##### Distribuicao")
        fig = go.Figure(data=[go.Pie(
            labels=df_tipo['Tipo'],
            values=df_tipo['Total'],
            hole=0.5,
            marker_colors=[cores_tipo.get(t, cores['info']) for t in df_tipo['Tipo']],
            textinfo='percent',
            textfont_size=11
        )])
        fig.update_layout(criar_layout(320), showlegend=True,
            legend=dict(orientation='h', yanchor='top', y=-0.1, xanchor='center', x=0.5, font=dict(size=9)),
            margin=dict(l=10, r=10, t=10, b=60))
        st.plotly_chart(fig, use_container_width=True)

    if 'DESCRICAO' in df_cambio.columns:
        st.markdown("##### Por Categoria (DESCRICAO)")
        df_cat = df_cambio.groupby('DESCRICAO').agg({
            'VALOR_ORIGINAL': 'sum',
            'SALDO': 'sum',
            'FORNECEDOR': 'count'
        }).reset_index()
        df_cat.columns = ['Categoria', 'Total', 'Saldo', 'Qtd']
        df_cat = df_cat.sort_values('Total', ascending=False).head(10)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=df_cat['Categoria'].str[:35],
            x=df_cat['Total'],
            orientation='h',
            marker_color=cores['primaria'],
            text=[formatar_moeda(v) for v in df_cat['Total']],
            textposition='outside',
            textfont=dict(size=9)
        ))
        fig.update_layout(criar_layout(350), yaxis={'autorange': 'reversed'}, margin=dict(l=10, r=70, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)


def _render_evolucao_cambio(df_cambio, cores):
    """Evolucao temporal das operacoes cambiais"""
    df_temp = df_cambio.copy()
    df_temp['MES_ANO'] = df_temp['EMISSAO'].dt.to_period('M')

    df_mensal = df_temp.groupby('MES_ANO').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'FORNECEDOR': 'count'
    }).reset_index()
    df_mensal['MES_ANO'] = df_mensal['MES_ANO'].astype(str)
    df_mensal.columns = ['Periodo', 'Total', 'Saldo', 'Qtd']
    df_mensal = df_mensal.tail(12)

    st.markdown("##### Evolucao Mensal")

    col1, col2 = st.columns(2)

    with col1:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_mensal['Periodo'],
            y=df_mensal['Total'],
            marker_color=cores['primaria'],
            text=[formatar_moeda(v) for v in df_mensal['Total']],
            textposition='outside',
            textfont=dict(size=8)
        ))
        fig.update_layout(criar_layout(300), xaxis_tickangle=-45, margin=dict(l=10, r=10, t=10, b=60))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        df_tipo_mensal = df_temp.groupby(['MES_ANO', 'TIPO_OPERACAO'])['VALOR_ORIGINAL'].sum().reset_index()
        df_tipo_mensal['MES_ANO'] = df_tipo_mensal['MES_ANO'].astype(str)
        meses_unicos = sorted(df_tipo_mensal['MES_ANO'].unique())[-12:]
        df_tipo_mensal = df_tipo_mensal[df_tipo_mensal['MES_ANO'].isin(meses_unicos)]

        fig = go.Figure()
        for tipo in df_tipo_mensal['TIPO_OPERACAO'].unique():
            df_t = df_tipo_mensal[df_tipo_mensal['TIPO_OPERACAO'] == tipo]
            fig.add_trace(go.Scatter(x=df_t['MES_ANO'], y=df_t['VALOR_ORIGINAL'], mode='lines+markers', name=tipo[:20], line=dict(width=2)))
        fig.update_layout(criar_layout(300), xaxis_tickangle=-45,
            legend=dict(orientation='h', yanchor='top', y=-0.2, xanchor='center', x=0.5, font=dict(size=8)),
            margin=dict(l=10, r=10, t=10, b=80))
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("##### Resumo por Ano")
    df_ano = df_temp.groupby(df_temp['EMISSAO'].dt.year).agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'FORNECEDOR': 'count'
    }).reset_index()
    df_ano.columns = ['Ano', 'Total', 'Saldo', 'Qtd']
    df_ano['Pago'] = df_ano['Total'] - df_ano['Saldo']

    df_ano_exib = pd.DataFrame({
        'Ano': df_ano['Ano'].astype(int),
        'Total': df_ano['Total'].apply(lambda x: formatar_moeda(x, completo=True)),
        'Pago': df_ano['Pago'].apply(lambda x: formatar_moeda(x, completo=True)),
        'Saldo': df_ano['Saldo'].apply(lambda x: formatar_moeda(x, completo=True)),
        'Qtd Titulos': df_ano['Qtd']
    })
    st.dataframe(df_ano_exib, use_container_width=True, hide_index=True)


def _render_detalhes_cambio(df_cambio, cores, hoje):
    """Detalhes das operacoes cambiais"""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        tipos = ['Todos'] + sorted(df_cambio['TIPO_OPERACAO'].unique().tolist())
        filtro_tipo = st.selectbox("Tipo Operacao", tipos, key="cambio_tipo")

    with col2:
        if 'MOEDA' in df_cambio.columns:
            moedas = ['Todas'] + sorted(df_cambio['MOEDA'].dropna().unique().tolist())
            filtro_moeda = st.selectbox("Moeda", moedas, key="cambio_moeda")
        else:
            filtro_moeda = 'Todas'

    with col3:
        filtro_status = st.selectbox("Status", ['Todos', 'Pendente', 'Pago', 'Vencido'], key="cambio_status")

    with col4:
        ordem = st.selectbox("Ordenar", ["Maior Valor", "Mais Recente", "Fornecedor A-Z"], key="cambio_ordem")

    df_show = df_cambio.copy()

    if filtro_tipo != 'Todos':
        df_show = df_show[df_show['TIPO_OPERACAO'] == filtro_tipo]

    if filtro_moeda != 'Todas' and 'MOEDA' in df_show.columns:
        df_show = df_show[df_show['MOEDA'] == filtro_moeda]

    if filtro_status == 'Pendente':
        df_show = df_show[df_show['SALDO'] > 0]
    elif filtro_status == 'Pago':
        df_show = df_show[df_show['SALDO'] == 0]
    elif filtro_status == 'Vencido':
        df_show = df_show[df_show['STATUS'] == 'Vencido']

    if ordem == "Maior Valor":
        df_show = df_show.sort_values('VALOR_ORIGINAL', ascending=False)
    elif ordem == "Mais Recente":
        df_show = df_show.sort_values('EMISSAO', ascending=False)
    else:
        df_show = df_show.sort_values('NOME_FORNECEDOR')

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Titulos", formatar_numero(len(df_show)))
    col2.metric("Total", formatar_moeda(df_show['VALOR_ORIGINAL'].sum()))
    col3.metric("Saldo", formatar_moeda(df_show['SALDO'].sum()))
    col4.metric("Vencidos", formatar_numero(len(df_show[df_show['STATUS'] == 'Vencido'])))

    st.markdown("---")

    colunas_base = ['NOME_FILIAL', 'NOME_FORNECEDOR', 'TIPO_OPERACAO', 'EMISSAO', 'VENCIMENTO', 'VALOR_ORIGINAL', 'SALDO', 'STATUS']
    colunas_extra = []
    if 'MOEDA' in df_show.columns:
        colunas_extra.append('MOEDA')
    if 'TX_MOEDA' in df_show.columns:
        colunas_extra.append('TX_MOEDA')

    colunas = [c for c in colunas_base + colunas_extra if c in df_show.columns]
    df_exib = df_show[colunas].head(100).copy()

    if 'EMISSAO' in df_exib.columns:
        df_exib['EMISSAO'] = pd.to_datetime(df_exib['EMISSAO']).dt.strftime('%d/%m/%Y')
    if 'VENCIMENTO' in df_exib.columns:
        df_exib['VENCIMENTO'] = pd.to_datetime(df_exib['VENCIMENTO']).dt.strftime('%d/%m/%Y')
    if 'VALOR_ORIGINAL' in df_exib.columns:
        df_exib['VALOR_ORIGINAL'] = df_exib['VALOR_ORIGINAL'].apply(lambda x: formatar_moeda(x, completo=True))
    if 'SALDO' in df_exib.columns:
        df_exib['SALDO'] = df_exib['SALDO'].apply(lambda x: formatar_moeda(x, completo=True))
    if 'TX_MOEDA' in df_exib.columns:
        df_exib['TX_MOEDA'] = df_exib['TX_MOEDA'].apply(lambda x: f"R$ {x:.4f}" if pd.notna(x) and x > 0 else '-')

    rename_map = {
        'NOME_FILIAL': 'Filial',
        'NOME_FORNECEDOR': 'Banco/Fornecedor',
        'TIPO_OPERACAO': 'Tipo',
        'EMISSAO': 'Emissao',
        'VENCIMENTO': 'Vencimento',
        'VALOR_ORIGINAL': 'Valor',
        'SALDO': 'Saldo',
        'STATUS': 'Status',
        'MOEDA': 'Moeda',
        'TX_MOEDA': 'Taxa'
    }
    df_exib = df_exib.rename(columns=rename_map)

    st.dataframe(df_exib, use_container_width=True, hide_index=True, height=450)
    st.caption(f"Exibindo {len(df_exib)} de {len(df_show)} registros")
