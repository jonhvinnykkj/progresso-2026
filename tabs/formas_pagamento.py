"""
Aba Formas de Pagamento - Análise por modalidade de pagamento
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

from config.theme import get_cores, get_sequencia_cores
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero


def render_formas_pagamento(df):
    """Renderiza a aba de Formas de Pagamento"""
    cores = get_cores()
    seq_cores = get_sequencia_cores()

    st.markdown("### Formas de Pagamento")
    st.caption("Análise detalhada por modalidade de pagamento (PIX, TED, Boleto, etc.)")

    # Verificar se as colunas existem
    if 'FORMA_PAGTO' not in df.columns and 'DESCRICAO_FORMA_PAGAMENTO' not in df.columns:
        st.warning("Dados de formas de pagamento não disponíveis.")
        return

    # Preparar dados - usar DESCRICAO_FORMA_PAGAMENTO se disponível
    df_prep = df.copy()
    if 'DESCRICAO_FORMA_PAGAMENTO' in df_prep.columns:
        df_prep['FORMA'] = df_prep['DESCRICAO_FORMA_PAGAMENTO'].fillna('Não informado')
    else:
        df_prep['FORMA'] = df_prep['FORMA_PAGTO'].fillna('Não informado')

    # Simplificar nomes de formas de pagamento
    df_prep['FORMA'] = df_prep['FORMA'].apply(_normalizar_forma_pagamento)

    # ========== SEÇÃO 1: RESUMO GERAL ==========
    _render_resumo_formas(df_prep, cores)

    st.divider()

    # ========== SEÇÃO 2: ANÁLISES DETALHADAS ==========
    tab1, tab2, tab3 = st.tabs([
        "📊 Distribuição",
        "📈 Evolução Temporal",
        "📋 Detalhamento"
    ])

    with tab1:
        _render_distribuicao(df_prep, cores, seq_cores)

    with tab2:
        _render_evolucao(df_prep, cores)

    with tab3:
        _render_detalhes(df_prep, cores)


def _normalizar_forma_pagamento(forma):
    """Normaliza os nomes das formas de pagamento"""
    if pd.isna(forma) or forma == '' or str(forma).strip() == '':
        return 'Não Informado'

    forma_upper = str(forma).upper().strip()

    if 'PIX' in forma_upper:
        if 'QR' in forma_upper:
            return 'PIX QR Code'
        return 'PIX Transferência'
    elif 'TED' in forma_upper:
        if 'MESMO' in forma_upper:
            return 'TED Mesmo Titular'
        elif 'OUTRO' in forma_upper:
            return 'TED Outro Titular'
        return 'TED'
    elif 'BOLETO' in forma_upper or 'TITULO' in forma_upper:
        return 'Boleto'
    elif 'COMPENSACAO' in forma_upper or 'COMPENSAÇÃO' in forma_upper:
        return 'Compensação'
    elif 'CHEQUE' in forma_upper:
        return 'Cheque'
    elif 'DINHEIRO' in forma_upper:
        return 'Dinheiro'
    elif 'SEM PAGAMENTO' in forma_upper:
        return 'Sem Pagamento Financeiro'
    elif 'LIQUIDACAO' in forma_upper or 'LIQUIDAÇÃO' in forma_upper:
        return 'Liquidação Bancária'

    return forma[:30] if len(forma) > 30 else forma


def _render_resumo_formas(df, cores):
    """Resumo geral das formas de pagamento"""

    # Calcular totais por forma
    df_formas = df.groupby('FORMA').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'FORNECEDOR': 'count'
    }).reset_index()
    df_formas.columns = ['Forma', 'Valor_Total', 'Saldo', 'Qtd_Títulos']
    df_formas = df_formas.sort_values('Valor_Total', ascending=False)

    # Top 3 formas
    top3 = df_formas.head(3)

    st.markdown("#### Resumo Geral")

    # KPIs das top 3 formas
    cols = st.columns(len(top3) + 2)

    for i, (_, row) in enumerate(top3.iterrows()):
        with cols[i]:
            pct = row['Valor_Total'] / df['VALOR_ORIGINAL'].sum() * 100
            st.metric(
                row['Forma'][:20],
                formatar_moeda(row['Valor_Total']),
                delta=f"{row['Qtd_Títulos']} títulos ({pct:.1f}%)",
                delta_color="off"
            )

    # Total de formas e concentração
    with cols[-2]:
        total_formas = len(df_formas)
        st.metric(
            "Formas Utilizadas",
            f"{total_formas}",
            delta="modalidades diferentes",
            delta_color="off"
        )

    # Concentração
    with cols[-1]:
        top3_pct = top3['Valor_Total'].sum() / df['VALOR_ORIGINAL'].sum() * 100
        st.metric(
            "Concentração Top 3",
            f"{top3_pct:.1f}%",
            delta="do valor total",
            delta_color="off"
        )


def _render_distribuicao(df, cores, seq_cores):
    """Distribuição por forma de pagamento"""

    col1, col2 = st.columns(2)

    # Agrupar por forma
    df_formas = df.groupby('FORMA').agg({
        'VALOR_ORIGINAL': 'sum',
        'FORNECEDOR': 'count'
    }).reset_index()
    df_formas.columns = ['Forma', 'Valor', 'Qtd']
    df_formas = df_formas.sort_values('Valor', ascending=False)
    total = df_formas['Valor'].sum()
    df_formas['Pct'] = (df_formas['Valor'] / total * 100).round(1)

    with col1:
        st.markdown("##### Distribuição por Valor")

        fig = go.Figure(go.Pie(
            labels=df_formas['Forma'],
            values=df_formas['Valor'],
            hole=0.5,
            marker=dict(colors=seq_cores),
            textinfo='percent+label',
            textposition='outside',
            textfont=dict(size=10),
            hovertemplate='<b>%{label}</b><br>Valor: R$ %{value:,.2f}<br>%{percent}<extra></extra>'
        ))

        # Texto central
        fig.add_annotation(
            text=f"<b>{formatar_moeda(total)}</b><br>Total",
            x=0.5, y=0.5,
            font=dict(size=14, color=cores['texto']),
            showarrow=False
        )

        fig.update_layout(
            criar_layout(400),
            showlegend=False,
            margin=dict(l=20, r=20, t=20, b=20)
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("##### Distribuição por Quantidade")

        fig2 = go.Figure()

        fig2.add_trace(go.Bar(
            y=df_formas['Forma'],
            x=df_formas['Qtd'],
            orientation='h',
            marker_color=cores['primaria'],
            text=[f"{q:,}" for q in df_formas['Qtd']],
            textposition='outside',
            textfont=dict(size=10)
        ))

        fig2.update_layout(
            criar_layout(400),
            yaxis={'autorange': 'reversed'},
            xaxis_title='Quantidade de Títulos',
            margin=dict(l=10, r=10, t=20, b=30)
        )

        st.plotly_chart(fig2, use_container_width=True)

    # Tabela resumo
    st.markdown("##### Resumo por Forma de Pagamento")

    df_exibir = df_formas.copy()
    df_exibir['Ticket_Médio'] = df_exibir['Valor'] / df_exibir['Qtd']
    df_exibir['Valor'] = df_exibir['Valor'].apply(lambda x: formatar_moeda(x, completo=True))
    df_exibir['Ticket_Médio'] = df_exibir['Ticket_Médio'].apply(lambda x: formatar_moeda(x, completo=True))
    df_exibir = df_exibir.rename(columns={
        'Forma': 'Forma de Pagamento',
        'Valor': 'Valor Total',
        'Qtd': 'Qtd Títulos',
        'Pct': '% do Total',
        'Ticket_Médio': 'Ticket Médio'
    })

    st.dataframe(
        df_exibir,
        use_container_width=True,
        hide_index=True,
        column_config={
            '% do Total': st.column_config.ProgressColumn(
                '% do Total',
                format='%.1f%%',
                min_value=0,
                max_value=100
            )
        }
    )


def _render_evolucao(df, cores):
    """Evolução temporal por forma de pagamento"""

    st.markdown("##### Evolução Mensal por Forma de Pagamento")

    df_temp = df.copy()
    df_temp['MES_ANO'] = df_temp['EMISSAO'].dt.to_period('M')

    # Pegar top 5 formas
    top_formas = df.groupby('FORMA')['VALOR_ORIGINAL'].sum().nlargest(5).index.tolist()

    df_mensal = df_temp[df_temp['FORMA'].isin(top_formas)].groupby(['MES_ANO', 'FORMA']).agg({
        'VALOR_ORIGINAL': 'sum'
    }).reset_index()
    df_mensal.columns = ['Período', 'Forma', 'Valor']
    df_mensal['Período'] = df_mensal['Período'].astype(str)

    # Últimos 12 meses
    ultimos_periodos = df_mensal['Período'].unique()[-12:]
    df_mensal = df_mensal[df_mensal['Período'].isin(ultimos_periodos)]

    fig = go.Figure()

    cores_formas = {
        'PIX Transferência': cores['primaria'],
        'Boleto': cores['info'],
        'TED Outro Titular': cores['alerta'],
        'TED Mesmo Titular': '#8b5cf6',
        'Compensação': '#ec4899'
    }

    for forma in top_formas:
        df_forma = df_mensal[df_mensal['Forma'] == forma]
        fig.add_trace(go.Scatter(
            x=df_forma['Período'],
            y=df_forma['Valor'],
            mode='lines+markers',
            name=forma[:20],
            line=dict(width=2, color=cores_formas.get(forma, cores['texto_secundario'])),
            marker=dict(size=6)
        ))

    fig.update_layout(
        criar_layout(400),
        xaxis_tickangle=-45,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
        margin=dict(l=10, r=10, t=50, b=60)
    )

    st.plotly_chart(fig, use_container_width=True)

    # Comparativo mensal em barras empilhadas
    st.markdown("##### Composição Mensal")

    df_pivot = df_mensal.pivot(index='Período', columns='Forma', values='Valor').fillna(0)

    fig2 = go.Figure()

    for forma in df_pivot.columns:
        fig2.add_trace(go.Bar(
            x=df_pivot.index,
            y=df_pivot[forma],
            name=forma[:15],
            marker_color=cores_formas.get(forma, cores['texto_secundario'])
        ))

    fig2.update_layout(
        criar_layout(350, barmode='stack'),
        xaxis_tickangle=-45,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
        margin=dict(l=10, r=10, t=50, b=60)
    )

    st.plotly_chart(fig2, use_container_width=True)


def _render_detalhes(df, cores):
    """Detalhamento por forma de pagamento"""

    st.markdown("##### Análise por Forma de Pagamento")

    # Seletor de forma
    formas_disponiveis = ['Todas'] + sorted(df['FORMA'].unique().tolist())
    forma_selecionada = st.selectbox("Selecione a forma de pagamento:", formas_disponiveis)

    if forma_selecionada != 'Todas':
        df_filtrado = df[df['FORMA'] == forma_selecionada]
    else:
        df_filtrado = df

    # Métricas
    col1, col2, col3, col4 = st.columns(4)

    total_valor = df_filtrado['VALOR_ORIGINAL'].sum()
    total_titulos = len(df_filtrado)
    ticket_medio = total_valor / total_titulos if total_titulos > 0 else 0
    fornecedores = df_filtrado['NOME_FORNECEDOR'].nunique()

    col1.metric("Valor Total", formatar_moeda(total_valor))
    col2.metric("Qtd Títulos", formatar_numero(total_titulos))
    col3.metric("Ticket Médio", formatar_moeda(ticket_medio))
    col4.metric("Fornecedores", formatar_numero(fornecedores))

    # Top fornecedores para a forma selecionada
    st.markdown("##### Top 10 Fornecedores")

    df_forn = df_filtrado.groupby('NOME_FORNECEDOR').agg({
        'VALOR_ORIGINAL': 'sum',
        'FORNECEDOR': 'count'
    }).reset_index()
    df_forn.columns = ['Fornecedor', 'Valor', 'Qtd']
    df_forn = df_forn.sort_values('Valor', ascending=False).head(10)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=df_forn['Fornecedor'].str[:30],
        x=df_forn['Valor'],
        orientation='h',
        marker_color=cores['primaria'],
        text=[formatar_moeda(v) for v in df_forn['Valor']],
        textposition='outside',
        textfont=dict(size=9)
    ))

    fig.update_layout(
        criar_layout(350),
        yaxis={'autorange': 'reversed'},
        margin=dict(l=10, r=10, t=10, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)
