"""
Aba Análise Cambial - Exposição e variação cambial (USD, EUR)
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

from config.theme import get_cores, get_sequencia_cores
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero


def render_cambio(df):
    """Renderiza a aba de Análise Cambial"""
    cores = get_cores()
    seq_cores = get_sequencia_cores()

    st.markdown("### Análise Cambial")
    st.caption("Exposição a moedas estrangeiras e variação cambial")

    # Verificar se as colunas existem
    if 'MOEDA' not in df.columns:
        st.warning("Dados de moeda não disponíveis.")
        return

    # Separar por moeda
    df_brl = df[df['MOEDA'] == 'REAL']
    df_usd = df[df['MOEDA'].isin(['DOLAR COMPRA', 'DOLAR VENDA', 'USD', 'DÓLAR'])]
    df_eur = df[df['MOEDA'].isin(['EURO', 'EUR'])]
    df_outras = df[~df['MOEDA'].isin(['REAL', 'DOLAR COMPRA', 'DOLAR VENDA', 'USD', 'DÓLAR', 'EURO', 'EUR'])]

    total_moeda_estrangeira = len(df_usd) + len(df_eur) + len(df_outras)

    if total_moeda_estrangeira == 0:
        st.info("Não há títulos em moeda estrangeira no período selecionado.")
        return

    # ========== SEÇÃO 1: RESUMO GERAL ==========
    _render_resumo_cambial(df, df_brl, df_usd, df_eur, cores)

    st.divider()

    # ========== SEÇÃO 2: ANÁLISES DETALHADAS ==========
    tab1, tab2, tab3 = st.tabs([
        "📊 Exposição por Moeda",
        "📈 Evolução Temporal",
        "📋 Detalhamento"
    ])

    with tab1:
        _render_exposicao(df, df_usd, df_eur, cores, seq_cores)

    with tab2:
        _render_evolucao_cambial(df, df_usd, df_eur, cores)

    with tab3:
        _render_detalhes_cambio(df, df_usd, df_eur, cores)


def _render_resumo_cambial(df, df_brl, df_usd, df_eur, cores):
    """Resumo geral da exposição cambial"""

    st.markdown("#### Exposição Cambial")

    # Calcular totais
    total_brl = df_brl['VALOR_ORIGINAL'].sum() if len(df_brl) > 0 else 0
    total_usd = df_usd['VALOR_ORIGINAL'].sum() if len(df_usd) > 0 else 0
    total_usd_real = df_usd['VALOR_REAL'].sum() if len(df_usd) > 0 and 'VALOR_REAL' in df_usd.columns else total_usd
    total_eur = df_eur['VALOR_ORIGINAL'].sum() if len(df_eur) > 0 else 0
    total_eur_real = df_eur['VALOR_REAL'].sum() if len(df_eur) > 0 and 'VALOR_REAL' in df_eur.columns else total_eur

    total_geral = df['VALOR_ORIGINAL'].sum()
    exposicao_cambial = total_usd + total_eur
    pct_exposicao = (exposicao_cambial / total_geral * 100) if total_geral > 0 else 0

    # Taxa média USD
    if len(df_usd) > 0 and 'TX_MOEDA' in df_usd.columns:
        df_usd_valido = df_usd[df_usd['TX_MOEDA'] > 0]
        taxa_media_usd = df_usd_valido['TX_MOEDA'].mean() if len(df_usd_valido) > 0 else 0
    else:
        taxa_media_usd = 0

    # Variação cambial
    variacao_usd = df_usd['VALOR_CORRECAO'].sum() if len(df_usd) > 0 and 'VALOR_CORRECAO' in df_usd.columns else 0
    variacao_eur = df_eur['VALOR_CORRECAO'].sum() if len(df_eur) > 0 and 'VALOR_CORRECAO' in df_eur.columns else 0
    variacao_total = variacao_usd + variacao_eur

    # KPIs
    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric(
        "Total em Real (BRL)",
        formatar_moeda(total_brl),
        delta=f"{len(df_brl)} títulos",
        delta_color="off"
    )

    col2.metric(
        "Total em Dólar (USD)",
        formatar_moeda(total_usd),
        delta=f"{len(df_usd)} títulos",
        delta_color="off"
    )

    col3.metric(
        "Total em Euro (EUR)",
        formatar_moeda(total_eur),
        delta=f"{len(df_eur)} títulos",
        delta_color="off"
    )

    col4.metric(
        "Exposição Cambial",
        f"{pct_exposicao:.1f}%",
        delta=formatar_moeda(exposicao_cambial),
        delta_color="off"
    )

    col5.metric(
        "Variação Cambial",
        formatar_moeda(abs(variacao_total)),
        delta="Ganho" if variacao_total < 0 else "Perda",
        delta_color="normal" if variacao_total < 0 else "inverse"
    )

    # Segunda linha de KPIs
    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Taxa Média USD",
        f"R$ {taxa_media_usd:.4f}" if taxa_media_usd > 0 else "N/A",
        help="Taxa média de conversão USD/BRL"
    )

    col2.metric(
        "USD em Reais",
        formatar_moeda(total_usd_real),
        help="Valor em Reais dos títulos em dólar"
    )

    col3.metric(
        "EUR em Reais",
        formatar_moeda(total_eur_real),
        help="Valor em Reais dos títulos em euro"
    )

    # Alerta de exposição
    if pct_exposicao > 20:
        col4.error(f"⚠️ Alta exposição cambial!")
    elif pct_exposicao > 10:
        col4.warning(f"⚡ Exposição moderada")
    else:
        col4.success(f"✅ Exposição controlada")


def _render_exposicao(df, df_usd, df_eur, cores, seq_cores):
    """Gráficos de exposição por moeda"""

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Distribuição por Moeda")

        # Agrupar por moeda
        df_moedas = df.groupby('MOEDA').agg({
            'VALOR_ORIGINAL': 'sum',
            'FORNECEDOR': 'count'
        }).reset_index()
        df_moedas.columns = ['Moeda', 'Valor', 'Qtd']
        df_moedas = df_moedas.sort_values('Valor', ascending=False)

        cores_moedas = {
            'REAL': cores['primaria'],
            'DOLAR COMPRA': cores['info'],
            'DOLAR VENDA': '#3b82f6',
            'EURO': cores['alerta']
        }

        fig = go.Figure(go.Pie(
            labels=df_moedas['Moeda'],
            values=df_moedas['Valor'],
            hole=0.5,
            marker=dict(colors=[cores_moedas.get(m, cores['texto_secundario']) for m in df_moedas['Moeda']]),
            textinfo='percent+label',
            textposition='outside',
            textfont=dict(size=10),
            hovertemplate='<b>%{label}</b><br>Valor: R$ %{value:,.2f}<br>%{percent}<extra></extra>'
        ))

        fig.update_layout(
            criar_layout(350),
            showlegend=False,
            margin=dict(l=20, r=20, t=20, b=20)
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("##### Quantidade de Títulos por Moeda")

        fig2 = go.Figure()

        fig2.add_trace(go.Bar(
            y=df_moedas['Moeda'],
            x=df_moedas['Qtd'],
            orientation='h',
            marker_color=[cores_moedas.get(m, cores['texto_secundario']) for m in df_moedas['Moeda']],
            text=[f"{q:,}" for q in df_moedas['Qtd']],
            textposition='outside'
        ))

        fig2.update_layout(
            criar_layout(350),
            yaxis={'autorange': 'reversed'},
            margin=dict(l=10, r=10, t=20, b=30)
        )

        st.plotly_chart(fig2, use_container_width=True)

    # Top fornecedores em moeda estrangeira
    if len(df_usd) > 0:
        st.markdown("##### Top Fornecedores em Dólar (USD)")

        df_forn_usd = df_usd.groupby('NOME_FORNECEDOR').agg({
            'VALOR_ORIGINAL': 'sum',
            'VALOR_REAL': 'sum',
            'FORNECEDOR': 'count'
        }).reset_index()
        df_forn_usd.columns = ['Fornecedor', 'Valor_USD', 'Valor_BRL', 'Qtd']
        df_forn_usd = df_forn_usd.sort_values('Valor_USD', ascending=False).head(10)

        fig3 = go.Figure()

        fig3.add_trace(go.Bar(
            y=df_forn_usd['Fornecedor'].str[:30],
            x=df_forn_usd['Valor_USD'],
            orientation='h',
            name='Valor Original',
            marker_color=cores['info'],
            text=[formatar_moeda(v) for v in df_forn_usd['Valor_USD']],
            textposition='outside',
            textfont=dict(size=9)
        ))

        fig3.update_layout(
            criar_layout(350),
            yaxis={'autorange': 'reversed'},
            margin=dict(l=10, r=10, t=20, b=10)
        )

        st.plotly_chart(fig3, use_container_width=True)


def _render_evolucao_cambial(df, df_usd, df_eur, cores):
    """Evolução temporal da exposição cambial"""

    st.markdown("##### Evolução Mensal por Moeda")

    df_temp = df.copy()
    df_temp['MES_ANO'] = df_temp['EMISSAO'].dt.to_period('M')

    df_mensal = df_temp.groupby(['MES_ANO', 'MOEDA']).agg({
        'VALOR_ORIGINAL': 'sum',
        'TX_MOEDA': 'mean'
    }).reset_index()
    df_mensal.columns = ['Período', 'Moeda', 'Valor', 'Taxa_Media']
    df_mensal['Período'] = df_mensal['Período'].astype(str)
    df_mensal = df_mensal[df_mensal['Período'].isin(df_mensal['Período'].unique()[-12:])]

    # Gráfico de evolução
    fig = go.Figure()

    cores_moedas = {
        'REAL': cores['primaria'],
        'DOLAR COMPRA': cores['info'],
        'DOLAR VENDA': '#60a5fa',
        'EURO': cores['alerta']
    }

    for moeda in df_mensal['Moeda'].unique():
        df_moeda = df_mensal[df_mensal['Moeda'] == moeda]
        fig.add_trace(go.Scatter(
            x=df_moeda['Período'],
            y=df_moeda['Valor'],
            mode='lines+markers',
            name=moeda,
            line=dict(width=2, color=cores_moedas.get(moeda, cores['texto_secundario'])),
            marker=dict(size=6)
        ))

    fig.update_layout(
        criar_layout(400),
        xaxis_tickangle=-45,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
        margin=dict(l=10, r=10, t=50, b=60)
    )

    st.plotly_chart(fig, use_container_width=True)

    # Evolução da taxa de câmbio USD
    if len(df_usd) > 0 and 'TX_MOEDA' in df_usd.columns:
        st.markdown("##### Evolução da Taxa de Câmbio USD")

        df_taxa = df_mensal[(df_mensal['Moeda'].isin(['DOLAR COMPRA', 'DOLAR VENDA'])) & (df_mensal['Taxa_Media'] > 0)]

        if len(df_taxa) > 0:
            fig2 = go.Figure()

            for moeda in df_taxa['Moeda'].unique():
                df_m = df_taxa[df_taxa['Moeda'] == moeda]
                fig2.add_trace(go.Scatter(
                    x=df_m['Período'],
                    y=df_m['Taxa_Media'],
                    mode='lines+markers+text',
                    name=moeda,
                    line=dict(width=2),
                    text=[f"R$ {t:.2f}" for t in df_m['Taxa_Media']],
                    textposition='top center',
                    textfont=dict(size=9)
                ))

            fig2.update_layout(
                criar_layout(300),
                xaxis_tickangle=-45,
                yaxis_title='Taxa R$/USD',
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
                margin=dict(l=10, r=10, t=50, b=60)
            )

            st.plotly_chart(fig2, use_container_width=True)


def _render_detalhes_cambio(df, df_usd, df_eur, cores):
    """Tabela detalhada de títulos em moeda estrangeira"""

    st.markdown("##### Títulos em Moeda Estrangeira")

    # Filtrar apenas moeda estrangeira
    df_estrang = df[~df['MOEDA'].isin(['REAL', 'BRL'])]

    if len(df_estrang) == 0:
        st.info("Nenhum título em moeda estrangeira.")
        return

    # Filtros
    col1, col2, col3 = st.columns(3)

    with col1:
        moedas = ['Todas'] + sorted(df_estrang['MOEDA'].unique().tolist())
        moeda_sel = st.selectbox("Moeda:", moedas, key="moeda_filter")

    with col2:
        ordenar = st.selectbox(
            "Ordenar por:",
            ["Maior Valor", "Mais Recente", "Fornecedor A-Z"],
            key="ordenar_cambio"
        )

    with col3:
        limite = st.selectbox(
            "Exibir:",
            ["50 primeiros", "100 primeiros", "Todos"],
            key="limite_cambio"
        )

    # Aplicar filtros
    df_filtrado = df_estrang.copy()

    if moeda_sel != 'Todas':
        df_filtrado = df_filtrado[df_filtrado['MOEDA'] == moeda_sel]

    # Ordenar
    if ordenar == "Maior Valor":
        df_filtrado = df_filtrado.sort_values('VALOR_ORIGINAL', ascending=False)
    elif ordenar == "Mais Recente":
        df_filtrado = df_filtrado.sort_values('EMISSAO', ascending=False)
    else:
        df_filtrado = df_filtrado.sort_values('NOME_FORNECEDOR')

    # Limitar
    if limite == "50 primeiros":
        df_filtrado = df_filtrado.head(50)
    elif limite == "100 primeiros":
        df_filtrado = df_filtrado.head(100)

    # Preparar exibição
    colunas = ['NOME_FORNECEDOR', 'MOEDA', 'TX_MOEDA', 'EMISSAO', 'VENCIMENTO',
               'VALOR_ORIGINAL', 'VALOR_REAL', 'VALOR_CORRECAO', 'SALDO']

    colunas_disp = [c for c in colunas if c in df_filtrado.columns]
    df_exibir = df_filtrado[colunas_disp].copy()

    # Renomear
    rename_map = {
        'NOME_FORNECEDOR': 'Fornecedor',
        'MOEDA': 'Moeda',
        'TX_MOEDA': 'Taxa Câmbio',
        'EMISSAO': 'Emissão',
        'VENCIMENTO': 'Vencimento',
        'VALOR_ORIGINAL': 'Valor Original',
        'VALOR_REAL': 'Valor em Reais',
        'VALOR_CORRECAO': 'Variação Cambial',
        'SALDO': 'Saldo'
    }
    df_exibir = df_exibir.rename(columns=rename_map)

    # Formatar datas
    if 'Emissão' in df_exibir.columns:
        df_exibir['Emissão'] = pd.to_datetime(df_exibir['Emissão']).dt.strftime('%d/%m/%Y')
    if 'Vencimento' in df_exibir.columns:
        df_exibir['Vencimento'] = pd.to_datetime(df_exibir['Vencimento']).dt.strftime('%d/%m/%Y')

    # Formatar valores
    for col in ['Valor Original', 'Valor em Reais', 'Variação Cambial', 'Saldo']:
        if col in df_exibir.columns:
            df_exibir[col] = df_exibir[col].apply(lambda x: formatar_moeda(x, completo=True) if pd.notna(x) else 'R$ 0,00')

    if 'Taxa Câmbio' in df_exibir.columns:
        df_exibir['Taxa Câmbio'] = df_exibir['Taxa Câmbio'].apply(lambda x: f"R$ {x:.4f}" if pd.notna(x) and x > 0 else '-')

    st.dataframe(df_exibir, use_container_width=True, hide_index=True, height=500)
    st.caption(f"Exibindo {len(df_exibir)} títulos em moeda estrangeira")
