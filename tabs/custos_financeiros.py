"""
Aba Custos Financeiros - Análise de Juros, Multas, Descontos e Correção
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

from config.theme import get_cores, get_sequencia_cores
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero


def render_custos_financeiros(df):
    """Renderiza a aba de Custos Financeiros"""
    cores = get_cores()
    seq_cores = get_sequencia_cores()

    st.markdown("### Custos Financeiros")
    st.caption("Análise detalhada de juros, multas, descontos e correção monetária")

    # Verificar se as colunas existem
    colunas_necessarias = ['VALOR_JUROS', 'VALOR_MULTA', 'VLR_DESCONTO', 'VALOR_CORRECAO']
    colunas_disponiveis = [col for col in colunas_necessarias if col in df.columns]

    if len(colunas_disponiveis) == 0:
        st.warning("Dados de custos financeiros não disponíveis.")
        return

    # ========== SEÇÃO 1: RESUMO GERAL ==========
    _render_resumo_custos(df, cores)

    st.divider()

    # ========== SEÇÃO 2: ANÁLISES DETALHADAS ==========
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Evolução Temporal",
        "🏢 Por Fornecedor",
        "📁 Por Categoria",
        "📋 Detalhamento"
    ])

    with tab1:
        _render_evolucao_temporal(df, cores)

    with tab2:
        _render_por_fornecedor(df, cores)

    with tab3:
        _render_por_categoria(df, cores)

    with tab4:
        _render_detalhamento(df, cores)


def _render_resumo_custos(df, cores):
    """Resumo geral dos custos financeiros"""

    # Calcular totais
    total_juros = df['VALOR_JUROS'].sum() if 'VALOR_JUROS' in df.columns else 0
    total_multas = df['VALOR_MULTA'].sum() if 'VALOR_MULTA' in df.columns else 0
    total_descontos = df['VLR_DESCONTO'].sum() if 'VLR_DESCONTO' in df.columns else 0
    total_correcao = df['VALOR_CORRECAO'].sum() if 'VALOR_CORRECAO' in df.columns else 0
    total_acrescimo = df['VALOR_ACRESCIMO'].sum() if 'VALOR_ACRESCIMO' in df.columns else 0
    total_decrescimo = df['VALOR_DECRESCIMO'].sum() if 'VALOR_DECRESCIMO' in df.columns else 0

    # Custo líquido (juros + multas - descontos)
    custo_bruto = total_juros + total_multas
    custo_liquido = custo_bruto - total_descontos

    # Contagens
    titulos_com_juros = len(df[df['VALOR_JUROS'] > 0]) if 'VALOR_JUROS' in df.columns else 0
    titulos_com_multa = len(df[df['VALOR_MULTA'] > 0]) if 'VALOR_MULTA' in df.columns else 0
    titulos_com_desconto = len(df[df['VLR_DESCONTO'] > 0]) if 'VLR_DESCONTO' in df.columns else 0
    total_titulos = len(df)

    pct_com_juros = (titulos_com_juros / total_titulos * 100) if total_titulos > 0 else 0
    pct_com_multa = (titulos_com_multa / total_titulos * 100) if total_titulos > 0 else 0
    pct_com_desconto = (titulos_com_desconto / total_titulos * 100) if total_titulos > 0 else 0

    st.markdown("#### Resumo Geral")

    # Linha 1: KPIs principais
    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric(
        "Total Juros",
        formatar_moeda(total_juros),
        delta=f"{titulos_com_juros} títulos ({pct_com_juros:.1f}%)",
        delta_color="inverse"
    )

    col2.metric(
        "Total Multas",
        formatar_moeda(total_multas),
        delta=f"{titulos_com_multa} títulos ({pct_com_multa:.1f}%)",
        delta_color="inverse"
    )

    col3.metric(
        "Total Descontos",
        formatar_moeda(total_descontos),
        delta=f"{titulos_com_desconto} títulos ({pct_com_desconto:.1f}%)",
        delta_color="normal"
    )

    col4.metric(
        "Correção Monetária",
        formatar_moeda(abs(total_correcao)),
        delta="Ganho" if total_correcao < 0 else "Perda",
        delta_color="normal" if total_correcao < 0 else "inverse"
    )

    col5.metric(
        "Custo Líquido",
        formatar_moeda(custo_liquido),
        delta=f"Juros + Multas - Descontos",
        delta_color="off"
    )

    # Linha 2: Indicadores adicionais
    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)

    # Ticket médio de juros
    ticket_medio_juros = total_juros / titulos_com_juros if titulos_com_juros > 0 else 0
    col1.metric(
        "Juros Médio por Título",
        formatar_moeda(ticket_medio_juros),
        help="Valor médio de juros nos títulos que tiveram juros"
    )

    # Ticket médio de multa
    ticket_medio_multa = total_multas / titulos_com_multa if titulos_com_multa > 0 else 0
    col2.metric(
        "Multa Média por Título",
        formatar_moeda(ticket_medio_multa),
        help="Valor médio de multa nos títulos que tiveram multa"
    )

    # Economia com descontos
    col3.metric(
        "Economia com Descontos",
        formatar_moeda(total_descontos),
        delta=f"{(total_descontos/custo_bruto*100):.1f}% do custo bruto" if custo_bruto > 0 else "0%",
        delta_color="normal"
    )

    # Impacto no valor total
    valor_total = df['VALOR_ORIGINAL'].sum()
    impacto_pct = (custo_liquido / valor_total * 100) if valor_total > 0 else 0
    col4.metric(
        "Impacto no Total",
        f"{impacto_pct:.2f}%",
        delta=f"Sobre {formatar_moeda(valor_total)}",
        delta_color="off"
    )

    # Alerta visual
    if custo_liquido > 0:
        if impacto_pct > 5:
            st.error(f"⚠️ **Atenção:** Custos financeiros representam {impacto_pct:.2f}% do valor total - acima do aceitável!")
        elif impacto_pct > 2:
            st.warning(f"⚡ **Alerta:** Custos financeiros de {impacto_pct:.2f}% - monitorar de perto.")
        else:
            st.success(f"✅ Custos financeiros controlados: {impacto_pct:.2f}% do valor total.")


def _render_evolucao_temporal(df, cores):
    """Evolução temporal dos custos financeiros"""

    st.markdown("##### Evolução Mensal")

    df_temp = df.copy()
    df_temp['MES_ANO'] = df_temp['EMISSAO'].dt.to_period('M')

    df_mensal = df_temp.groupby('MES_ANO').agg({
        'VALOR_JUROS': 'sum',
        'VALOR_MULTA': 'sum',
        'VLR_DESCONTO': 'sum',
        'VALOR_CORRECAO': 'sum',
        'VALOR_ORIGINAL': 'count'
    }).reset_index()
    df_mensal.columns = ['Período', 'Juros', 'Multas', 'Descontos', 'Correção', 'Qtd_Títulos']
    df_mensal['Período'] = df_mensal['Período'].astype(str)
    df_mensal = df_mensal.tail(12)  # Últimos 12 meses

    col1, col2 = st.columns(2)

    with col1:
        # Gráfico de barras empilhadas
        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=df_mensal['Período'],
            y=df_mensal['Juros'],
            name='Juros',
            marker_color=cores['perigo'],
            text=[formatar_moeda(v) for v in df_mensal['Juros']],
            textposition='inside',
            textfont=dict(size=9)
        ))

        fig.add_trace(go.Bar(
            x=df_mensal['Período'],
            y=df_mensal['Multas'],
            name='Multas',
            marker_color=cores['alerta'],
            text=[formatar_moeda(v) for v in df_mensal['Multas']],
            textposition='inside',
            textfont=dict(size=9)
        ))

        fig.update_layout(
            criar_layout(350, barmode='stack'),
            xaxis_tickangle=-45,
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
            margin=dict(l=10, r=10, t=40, b=60)
        )

        st.plotly_chart(fig, use_container_width=True)
        st.caption("Juros e Multas por mês")

    with col2:
        # Gráfico de descontos
        fig2 = go.Figure()

        fig2.add_trace(go.Bar(
            x=df_mensal['Período'],
            y=df_mensal['Descontos'],
            name='Descontos Obtidos',
            marker_color=cores['sucesso'],
            text=[formatar_moeda(v) for v in df_mensal['Descontos']],
            textposition='outside',
            textfont=dict(size=9)
        ))

        fig2.update_layout(
            criar_layout(350),
            xaxis_tickangle=-45,
            margin=dict(l=10, r=10, t=40, b=60)
        )

        st.plotly_chart(fig2, use_container_width=True)
        st.caption("Descontos obtidos por mês")

    # Linha de tendência - Custo Líquido
    st.markdown("##### Tendência do Custo Líquido")

    df_mensal['Custo_Liquido'] = df_mensal['Juros'] + df_mensal['Multas'] - df_mensal['Descontos']

    fig3 = go.Figure()

    fig3.add_trace(go.Scatter(
        x=df_mensal['Período'],
        y=df_mensal['Custo_Liquido'],
        mode='lines+markers+text',
        name='Custo Líquido',
        line=dict(color=cores['info'], width=3),
        marker=dict(size=10),
        text=[formatar_moeda(v) for v in df_mensal['Custo_Liquido']],
        textposition='top center',
        textfont=dict(size=9)
    ))

    # Linha de média
    media = df_mensal['Custo_Liquido'].mean()
    fig3.add_hline(y=media, line_dash="dash", line_color=cores['alerta'],
                   annotation_text=f"Média: {formatar_moeda(media)}")

    fig3.update_layout(
        criar_layout(300),
        xaxis_tickangle=-45,
        margin=dict(l=10, r=10, t=30, b=60)
    )

    st.plotly_chart(fig3, use_container_width=True)


def _render_por_fornecedor(df, cores):
    """Análise de custos financeiros por fornecedor"""

    st.markdown("##### Fornecedores com Maiores Custos Financeiros")

    # Agrupar por fornecedor
    df_forn = df.groupby('NOME_FORNECEDOR').agg({
        'VALOR_JUROS': 'sum',
        'VALOR_MULTA': 'sum',
        'VLR_DESCONTO': 'sum',
        'VALOR_ORIGINAL': ['sum', 'count']
    }).reset_index()
    df_forn.columns = ['Fornecedor', 'Juros', 'Multas', 'Descontos', 'Valor_Total', 'Qtd_Títulos']
    df_forn['Custo_Total'] = df_forn['Juros'] + df_forn['Multas']
    df_forn['Custo_Liquido'] = df_forn['Custo_Total'] - df_forn['Descontos']
    df_forn['Pct_Custo'] = (df_forn['Custo_Total'] / df_forn['Valor_Total'] * 100).round(2)
    df_forn = df_forn.sort_values('Custo_Total', ascending=False)

    col1, col2 = st.columns([2, 1])

    with col1:
        # Top 15 fornecedores com mais custos
        df_top = df_forn.head(15)

        fig = go.Figure()

        fig.add_trace(go.Bar(
            y=df_top['Fornecedor'].str[:30],
            x=df_top['Juros'],
            orientation='h',
            name='Juros',
            marker_color=cores['perigo'],
            text=[formatar_moeda(v) for v in df_top['Juros']],
            textposition='inside',
            textfont=dict(size=9)
        ))

        fig.add_trace(go.Bar(
            y=df_top['Fornecedor'].str[:30],
            x=df_top['Multas'],
            orientation='h',
            name='Multas',
            marker_color=cores['alerta'],
            text=[formatar_moeda(v) for v in df_top['Multas']],
            textposition='inside',
            textfont=dict(size=9)
        ))

        fig.update_layout(
            criar_layout(500, barmode='stack'),
            yaxis={'autorange': 'reversed'},
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
            margin=dict(l=10, r=10, t=40, b=10)
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("**Maiores Impactos:**")

        for _, row in df_forn.head(10).iterrows():
            nome = row['Fornecedor'][:25]
            custo = row['Custo_Total']
            pct = row['Pct_Custo']

            if pct > 5:
                icone = "🔴"
            elif pct > 2:
                icone = "🟡"
            else:
                icone = "🟢"

            st.markdown(f"{icone} **{nome}**")
            st.caption(f"Custo: {formatar_moeda(custo)} ({pct:.1f}% do valor)")

    # Tabela completa
    st.markdown("##### Tabela Detalhada por Fornecedor")

    df_exibir = df_forn.copy()
    df_exibir = df_exibir[df_exibir['Custo_Total'] > 0]  # Apenas com custos

    df_exibir['Juros'] = df_exibir['Juros'].apply(lambda x: formatar_moeda(x, completo=True))
    df_exibir['Multas'] = df_exibir['Multas'].apply(lambda x: formatar_moeda(x, completo=True))
    df_exibir['Descontos'] = df_exibir['Descontos'].apply(lambda x: formatar_moeda(x, completo=True))
    df_exibir['Custo_Total'] = df_exibir['Custo_Total'].apply(lambda x: formatar_moeda(x, completo=True))
    df_exibir['Valor_Total'] = df_exibir['Valor_Total'].apply(lambda x: formatar_moeda(x, completo=True))

    st.dataframe(
        df_exibir[['Fornecedor', 'Juros', 'Multas', 'Descontos', 'Custo_Total', 'Valor_Total', 'Qtd_Títulos', 'Pct_Custo']],
        use_container_width=True,
        hide_index=True,
        height=400,
        column_config={
            'Pct_Custo': st.column_config.ProgressColumn(
                '% Custo/Valor',
                format='%.1f%%',
                min_value=0,
                max_value=10
            )
        }
    )


def _render_por_categoria(df, cores):
    """Análise de custos financeiros por categoria"""

    st.markdown("##### Custos Financeiros por Categoria")

    # Agrupar por categoria
    df_cat = df.groupby('DESCRICAO').agg({
        'VALOR_JUROS': 'sum',
        'VALOR_MULTA': 'sum',
        'VLR_DESCONTO': 'sum',
        'VALOR_ORIGINAL': 'sum'
    }).reset_index()
    df_cat.columns = ['Categoria', 'Juros', 'Multas', 'Descontos', 'Valor_Total']
    df_cat['Custo_Total'] = df_cat['Juros'] + df_cat['Multas']
    df_cat['Pct_Custo'] = (df_cat['Custo_Total'] / df_cat['Valor_Total'] * 100).round(2)
    df_cat = df_cat.sort_values('Custo_Total', ascending=False)

    col1, col2 = st.columns(2)

    with col1:
        # Top 10 categorias
        df_top = df_cat.head(10)

        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=df_top['Categoria'].str[:25],
            y=df_top['Juros'],
            name='Juros',
            marker_color=cores['perigo']
        ))

        fig.add_trace(go.Bar(
            x=df_top['Categoria'].str[:25],
            y=df_top['Multas'],
            name='Multas',
            marker_color=cores['alerta']
        ))

        fig.update_layout(
            criar_layout(350, barmode='group'),
            xaxis_tickangle=-45,
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
            margin=dict(l=10, r=10, t=40, b=100)
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Descontos por categoria
        df_desc = df_cat[df_cat['Descontos'] > 0].sort_values('Descontos', ascending=False).head(10)

        fig2 = go.Figure()

        fig2.add_trace(go.Bar(
            x=df_desc['Categoria'].str[:25],
            y=df_desc['Descontos'],
            marker_color=cores['sucesso'],
            text=[formatar_moeda(v) for v in df_desc['Descontos']],
            textposition='outside',
            textfont=dict(size=9)
        ))

        fig2.update_layout(
            criar_layout(350),
            xaxis_tickangle=-45,
            margin=dict(l=10, r=10, t=40, b=100)
        )

        st.plotly_chart(fig2, use_container_width=True)
        st.caption("Top 10 categorias com descontos")


def _render_detalhamento(df, cores):
    """Tabela detalhada de títulos com custos financeiros"""

    st.markdown("##### Títulos com Custos Financeiros")

    # Filtrar apenas títulos com algum custo
    df_custos = df[
        (df['VALOR_JUROS'] > 0) |
        (df['VALOR_MULTA'] > 0) |
        (df['VLR_DESCONTO'] > 0)
    ].copy()

    if len(df_custos) == 0:
        st.info("Nenhum título com custos financeiros encontrado.")
        return

    # Filtros
    col1, col2, col3 = st.columns(3)

    with col1:
        tipo_custo = st.selectbox(
            "Tipo de Custo",
            ["Todos", "Com Juros", "Com Multas", "Com Descontos"],
            key="tipo_custo_filter"
        )

    with col2:
        ordenar = st.selectbox(
            "Ordenar por",
            ["Maior Juros", "Maior Multa", "Maior Desconto", "Mais Recente"],
            key="ordenar_custos"
        )

    with col3:
        limite = st.selectbox(
            "Exibir",
            ["50 primeiros", "100 primeiros", "Todos"],
            key="limite_custos"
        )

    # Aplicar filtros
    if tipo_custo == "Com Juros":
        df_custos = df_custos[df_custos['VALOR_JUROS'] > 0]
    elif tipo_custo == "Com Multas":
        df_custos = df_custos[df_custos['VALOR_MULTA'] > 0]
    elif tipo_custo == "Com Descontos":
        df_custos = df_custos[df_custos['VLR_DESCONTO'] > 0]

    # Ordenar
    if ordenar == "Maior Juros":
        df_custos = df_custos.sort_values('VALOR_JUROS', ascending=False)
    elif ordenar == "Maior Multa":
        df_custos = df_custos.sort_values('VALOR_MULTA', ascending=False)
    elif ordenar == "Maior Desconto":
        df_custos = df_custos.sort_values('VLR_DESCONTO', ascending=False)
    else:
        df_custos = df_custos.sort_values('EMISSAO', ascending=False)

    # Limitar
    if limite == "50 primeiros":
        df_custos = df_custos.head(50)
    elif limite == "100 primeiros":
        df_custos = df_custos.head(100)

    # Preparar exibição
    colunas = ['NOME_FORNECEDOR', 'DESCRICAO', 'EMISSAO', 'VENCIMENTO', 'VALOR_ORIGINAL',
               'VALOR_JUROS', 'VALOR_MULTA', 'VLR_DESCONTO']

    df_exibir = df_custos[colunas].copy()
    df_exibir = df_exibir.rename(columns={
        'NOME_FORNECEDOR': 'Fornecedor',
        'DESCRICAO': 'Categoria',
        'EMISSAO': 'Emissão',
        'VENCIMENTO': 'Vencimento',
        'VALOR_ORIGINAL': 'Valor Original',
        'VALOR_JUROS': 'Juros',
        'VALOR_MULTA': 'Multa',
        'VLR_DESCONTO': 'Desconto'
    })

    # Formatar datas
    df_exibir['Emissão'] = pd.to_datetime(df_exibir['Emissão']).dt.strftime('%d/%m/%Y')
    df_exibir['Vencimento'] = pd.to_datetime(df_exibir['Vencimento']).dt.strftime('%d/%m/%Y')

    # Formatar valores
    for col in ['Valor Original', 'Juros', 'Multa', 'Desconto']:
        df_exibir[col] = df_exibir[col].apply(lambda x: formatar_moeda(x, completo=True))

    st.dataframe(df_exibir, use_container_width=True, hide_index=True, height=500)
    st.caption(f"Exibindo {len(df_exibir)} títulos com custos financeiros")
