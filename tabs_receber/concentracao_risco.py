"""
Aba Concentracao de Risco - Analise de exposicao por cliente
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

from config.theme import get_cores
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero


def render_concentracao_risco(df):
    """Renderiza a aba de Concentracao de Risco"""
    cores = get_cores()

    if len(df) == 0:
        st.warning("Nenhum dado disponivel.")
        return

    col_cliente = 'NOME_CLIENTE' if 'NOME_CLIENTE' in df.columns else 'NOME_FORNECEDOR'
    df = df.copy()

    # ========== FILTRO POR FILIAL ==========
    if 'NOME_FILIAL' in df.columns:
        filiais = ['Todas as Filiais'] + sorted(df['NOME_FILIAL'].dropna().unique().tolist())

        col_filtro1, col_filtro2, col_spacer = st.columns([2, 2, 4])

        with col_filtro1:
            filtro_filial = st.selectbox(
                "Filtrar por Filial",
                filiais,
                key="conc_filtro_filial"
            )

        if filtro_filial != 'Todas as Filiais':
            df = df[df['NOME_FILIAL'] == filtro_filial].copy()

            with col_filtro2:
                st.info(f"Filtrando: {filtro_filial}")

        st.markdown("---")

    # ========== METRICAS DE CONCENTRACAO ==========
    st.markdown(f"""
    <div style="background: {cores['card']}; border-left: 4px solid {cores['alerta']};
                padding: 0.75rem 1rem; border-radius: 0 8px 8px 0; margin-bottom: 1rem;">
        <h4 style="color: {cores['texto']}; margin: 0;">Analise de Concentracao de Risco</h4>
        <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0;">
            Exposicao por cliente e indicadores de risco
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Calcular metricas
    total_clientes = df[col_cliente].nunique()
    total_saldo = df['SALDO'].sum()
    total_valor = df['VALOR_ORIGINAL'].sum()

    # Top 10 clientes
    df_top10 = df.groupby(col_cliente)['SALDO'].sum().nlargest(10)
    concentracao_top10 = df_top10.sum() / total_saldo * 100 if total_saldo > 0 else 0

    # Top 5 clientes
    df_top5 = df.groupby(col_cliente)['SALDO'].sum().nlargest(5)
    concentracao_top5 = df_top5.sum() / total_saldo * 100 if total_saldo > 0 else 0

    # Maior cliente
    maior_cliente = df_top10.index[0] if len(df_top10) > 0 else 'N/A'
    maior_valor = df_top10.iloc[0] if len(df_top10) > 0 else 0
    pct_maior = maior_valor / total_saldo * 100 if total_saldo > 0 else 0

    # HHI (Herfindahl-Hirschman Index) - medida de concentracao
    df_share = df.groupby(col_cliente)['SALDO'].sum() / total_saldo * 100 if total_saldo > 0 else pd.Series([0])
    hhi = (df_share ** 2).sum()

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric(
        "Total Clientes",
        formatar_numero(total_clientes),
        f"Saldo: {formatar_moeda(total_saldo)}"
    )

    col2.metric(
        "Concentracao Top 5",
        f"{concentracao_top5:.1f}%",
        "do saldo total"
    )

    col3.metric(
        "Concentracao Top 10",
        f"{concentracao_top10:.1f}%",
        "do saldo total"
    )

    col4.metric(
        "Maior Cliente",
        f"{pct_maior:.1f}%",
        maior_cliente[:20]
    )

    # Classificar risco HHI
    if hhi < 1500:
        risco_hhi = "Baixo"
        delta_color = "normal"
    elif hhi < 2500:
        risco_hhi = "Moderado"
        delta_color = "off"
    else:
        risco_hhi = "Alto"
        delta_color = "inverse"

    col5.metric(
        "Indice HHI",
        f"{hhi:.0f}",
        f"Risco {risco_hhi}",
        delta_color=delta_color
    )

    # Alerta de concentracao
    if concentracao_top5 > 50:
        st.error(f"ALERTA: Top 5 clientes concentram {concentracao_top5:.1f}% do saldo. Risco elevado de inadimplencia.")
    elif concentracao_top5 > 30:
        st.warning(f"Atencao: Top 5 clientes concentram {concentracao_top5:.1f}% do saldo.")

    st.divider()

    # ========== GRAFICOS ==========
    col1, col2 = st.columns(2)

    with col1:
        _render_top_clientes(df, col_cliente, cores)

    with col2:
        _render_curva_concentracao(df, col_cliente, cores)

    # ========== ANALISE POR FAIXA ==========
    st.divider()
    _render_analise_faixas(df, col_cliente, cores)

    # ========== MATRIZ DE RISCO ==========
    st.divider()
    _render_matriz_risco(df, col_cliente, cores)

    # ========== TABELA DETALHADA ==========
    st.divider()
    _render_tabela_clientes(df, col_cliente, cores)


def _render_top_clientes(df, col_cliente, cores):
    """Top clientes por saldo"""
    st.markdown("##### Top 15 Clientes por Saldo")

    df_grp = df.groupby(col_cliente).agg({
        'SALDO': 'sum',
        'VALOR_ORIGINAL': 'sum'
    }).nlargest(15, 'SALDO').reset_index()

    total_saldo = df['SALDO'].sum()
    df_grp['Pct'] = df_grp['SALDO'] / total_saldo * 100

    fig = go.Figure(go.Bar(
        y=df_grp[col_cliente].str[:25],
        x=df_grp['SALDO'],
        orientation='h',
        marker_color=cores['sucesso'],
        text=[f"{formatar_moeda(v)} ({p:.1f}%)" for v, p in zip(df_grp['SALDO'], df_grp['Pct'])],
        textposition='outside',
        textfont=dict(size=8)
    ))

    fig.update_layout(
        criar_layout(400),
        yaxis={'autorange': 'reversed'},
        margin=dict(l=10, r=120, t=10, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_curva_concentracao(df, col_cliente, cores):
    """Curva de Lorenz - concentracao"""
    st.markdown("##### Curva de Concentracao (Lorenz)")

    # Calcular curva de Lorenz
    df_grp = df.groupby(col_cliente)['SALDO'].sum().sort_values(ascending=False)
    total = df_grp.sum()

    if total == 0:
        st.info("Sem dados para curva de concentracao")
        return

    # Calcular percentuais acumulados
    n = len(df_grp)
    pct_clientes = [(i + 1) / n * 100 for i in range(n)]
    pct_valor_acum = (df_grp.cumsum() / total * 100).tolist()

    fig = go.Figure()

    # Linha de igualdade perfeita
    fig.add_trace(go.Scatter(
        x=[0, 100],
        y=[0, 100],
        mode='lines',
        name='Igualdade Perfeita',
        line=dict(color=cores['texto_secundario'], dash='dash', width=1)
    ))

    # Curva de Lorenz
    fig.add_trace(go.Scatter(
        x=[0] + pct_clientes,
        y=[0] + pct_valor_acum,
        mode='lines',
        name='Concentracao Real',
        fill='tozeroy',
        line=dict(color=cores['sucesso'], width=2),
        fillcolor='rgba(34, 197, 94, 0.2)'  # cores['sucesso'] com transparencia
    ))

    # Marcar pontos importantes
    # Top 20%
    idx_20 = int(n * 0.2)
    if idx_20 > 0:
        fig.add_annotation(
            x=20,
            y=pct_valor_acum[idx_20-1],
            text=f"Top 20%: {pct_valor_acum[idx_20-1]:.0f}%",
            showarrow=True,
            arrowhead=2,
            font=dict(size=9, color=cores['texto'])
        )

    fig.update_layout(
        criar_layout(400),
        xaxis_title='% Clientes',
        yaxis_title='% Saldo Acumulado',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=40, b=40)
    )

    st.plotly_chart(fig, use_container_width=True)

    # Calcular Gini
    area_sob_curva = sum(pct_valor_acum) / len(pct_valor_acum) / 100
    gini = (0.5 - area_sob_curva) / 0.5
    st.caption(f"Indice Gini: {gini:.3f} (0 = igualdade perfeita, 1 = concentracao maxima)")


def _render_analise_faixas(df, col_cliente, cores):
    """Analise por faixas de valor"""
    st.markdown("##### Distribuicao por Faixa de Saldo")

    # Agrupar clientes por saldo total
    df_cliente = df.groupby(col_cliente)['SALDO'].sum().reset_index()

    # Definir faixas
    faixas = [
        (0, 1000, 'Ate R$ 1 mil'),
        (1000, 10000, 'R$ 1 mil - R$ 10 mil'),
        (10000, 50000, 'R$ 10 mil - R$ 50 mil'),
        (50000, 100000, 'R$ 50 mil - R$ 100 mil'),
        (100000, 500000, 'R$ 100 mil - R$ 500 mil'),
        (500000, 1000000, 'R$ 500 mil - R$ 1 mi'),
        (1000000, float('inf'), 'Acima de R$ 1 mi')
    ]

    dados_faixas = []
    for min_val, max_val, nome in faixas:
        mask = (df_cliente['SALDO'] >= min_val) & (df_cliente['SALDO'] < max_val)
        qtd = mask.sum()
        valor = df_cliente.loc[mask, 'SALDO'].sum()
        dados_faixas.append({
            'Faixa': nome,
            'Clientes': qtd,
            'Saldo': valor
        })

    df_faixas = pd.DataFrame(dados_faixas)
    df_faixas = df_faixas[df_faixas['Clientes'] > 0]  # Remover faixas vazias

    col1, col2 = st.columns(2)

    with col1:
        fig = go.Figure(go.Bar(
            x=df_faixas['Faixa'],
            y=df_faixas['Clientes'],
            marker_color=cores['info'],
            text=df_faixas['Clientes'],
            textposition='outside'
        ))

        fig.update_layout(
            criar_layout(250),
            xaxis_tickangle=-45,
            margin=dict(l=10, r=10, t=10, b=100),
            yaxis_title='Qtd Clientes'
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = go.Figure(go.Bar(
            x=df_faixas['Faixa'],
            y=df_faixas['Saldo'],
            marker_color=cores['sucesso'],
            text=[formatar_moeda(v) for v in df_faixas['Saldo']],
            textposition='outside',
            textfont=dict(size=8)
        ))

        fig.update_layout(
            criar_layout(250),
            xaxis_tickangle=-45,
            margin=dict(l=10, r=10, t=10, b=100),
            yaxis_title='Saldo Total'
        )

        st.plotly_chart(fig, use_container_width=True)


def _render_matriz_risco(df, col_cliente, cores):
    """Matriz de risco: valor vs atraso"""
    st.markdown("##### Matriz de Risco: Valor x Atraso")

    # Agregar por cliente
    df_cliente = df.groupby(col_cliente).agg({
        'SALDO': 'sum',
        'DIAS_ATRASO': 'max',
        'VALOR_ORIGINAL': 'count'
    }).reset_index()
    df_cliente.columns = [col_cliente, 'Saldo', 'Dias_Atraso', 'Qtd_Titulos']

    # Filtrar apenas com saldo > 0 e atraso >= 0
    df_cliente = df_cliente[(df_cliente['Saldo'] > 0) & (df_cliente['Dias_Atraso'] >= 0)]

    if len(df_cliente) == 0:
        st.info("Sem dados para matriz de risco")
        return

    # Classificar risco
    def classificar_risco(row):
        if row['Dias_Atraso'] > 90 and row['Saldo'] > 100000:
            return 'Critico'
        elif row['Dias_Atraso'] > 60 or row['Saldo'] > 500000:
            return 'Alto'
        elif row['Dias_Atraso'] > 30 or row['Saldo'] > 100000:
            return 'Medio'
        else:
            return 'Baixo'

    df_cliente['Risco'] = df_cliente.apply(classificar_risco, axis=1)

    # Cores por risco
    cores_risco = {
        'Critico': cores['perigo'],
        'Alto': cores['alerta'],
        'Medio': cores['info'],
        'Baixo': cores['sucesso']
    }

    fig = go.Figure()

    for risco in ['Baixo', 'Medio', 'Alto', 'Critico']:
        df_r = df_cliente[df_cliente['Risco'] == risco]
        if len(df_r) > 0:
            fig.add_trace(go.Scatter(
                x=df_r['Dias_Atraso'],
                y=df_r['Saldo'],
                mode='markers',
                name=risco,
                marker=dict(
                    color=cores_risco[risco],
                    size=8,
                    opacity=0.7
                ),
                text=df_r[col_cliente],
                hovertemplate='<b>%{text}</b><br>Atraso: %{x} dias<br>Saldo: R$ %{y:,.2f}<extra></extra>'
            ))

    fig.update_layout(
        criar_layout(350),
        xaxis_title='Dias de Atraso',
        yaxis_title='Saldo (R$)',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=40, b=40)
    )

    st.plotly_chart(fig, use_container_width=True)

    # Resumo por risco
    col1, col2, col3, col4 = st.columns(4)

    for col, risco in zip([col1, col2, col3, col4], ['Critico', 'Alto', 'Medio', 'Baixo']):
        df_r = df_cliente[df_cliente['Risco'] == risco]
        qtd = len(df_r)
        valor = df_r['Saldo'].sum()
        col.metric(
            f"Risco {risco}",
            formatar_numero(qtd) + " clientes",
            formatar_moeda(valor)
        )


def _render_tabela_clientes(df, col_cliente, cores):
    """Tabela detalhada de clientes"""
    st.markdown("##### Detalhamento por Cliente")

    # Filtros
    col1, col2 = st.columns(2)

    with col1:
        ordenar = st.selectbox(
            "Ordenar por",
            ['Maior Saldo', 'Maior Atraso', 'Mais Titulos'],
            key="cr_ordem"
        )

    with col2:
        qtd = st.selectbox("Exibir", [20, 50, 100], key="cr_qtd")

    # Agregar
    df_cliente = df.groupby(col_cliente).agg({
        'SALDO': 'sum',
        'VALOR_ORIGINAL': ['sum', 'count'],
        'DIAS_ATRASO': 'max'
    }).reset_index()
    df_cliente.columns = [col_cliente, 'Saldo', 'Total', 'Qtd', 'Dias_Atraso']

    # Calcular vencidos
    df_venc = df[df['STATUS'] == 'Vencido'].groupby(col_cliente)['SALDO'].sum().reset_index()
    df_venc.columns = [col_cliente, 'Vencido']
    df_cliente = df_cliente.merge(df_venc, on=col_cliente, how='left')
    df_cliente['Vencido'] = df_cliente['Vencido'].fillna(0)

    # Taxa de recebimento
    df_cliente['Taxa_Receb'] = ((df_cliente['Total'] - df_cliente['Saldo']) / df_cliente['Total'] * 100).round(1)

    # Ordenar
    if ordenar == 'Maior Saldo':
        df_cliente = df_cliente.nlargest(qtd, 'Saldo')
    elif ordenar == 'Maior Atraso':
        df_cliente = df_cliente.nlargest(qtd, 'Dias_Atraso')
    else:
        df_cliente = df_cliente.nlargest(qtd, 'Qtd')

    # Formatar
    df_show = df_cliente.copy()
    df_show['Total'] = df_show['Total'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Saldo'] = df_show['Saldo'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Vencido'] = df_show['Vencido'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Taxa_Receb'] = df_show['Taxa_Receb'].apply(lambda x: f"{x:.1f}%")

    df_show.columns = ['Cliente', 'Saldo Pendente', 'Valor Total', 'Qtd Titulos', 'Dias Atraso', 'Valor Vencido', '% Recebido']

    st.dataframe(
        df_show,
        use_container_width=True,
        hide_index=True,
        height=400
    )

    st.caption(f"Exibindo {len(df_show)} clientes")
