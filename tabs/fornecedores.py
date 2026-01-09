"""
Aba Fornecedores - Analise completa por fornecedor com comportamento de pagamento
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

from config.theme import get_cores
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero
from utils.data_helpers import get_df_pendentes, get_df_vencidos


def render_fornecedores(df):
    """Renderiza a aba de Fornecedores"""
    cores = get_cores()

    if len(df) == 0:
        st.warning("Nenhum dado disponivel.")
        return

    # Calcular dataframes
    df_pendentes = get_df_pendentes(df)
    df_vencidos = get_df_vencidos(df)
    df_pagos = df[df['SALDO'] == 0].copy()

    # ========== KPIs ==========
    _render_kpis(df, df_pendentes, df_pagos, cores)

    st.divider()

    # ========== LINHA 1: Valor e Pendencia ==========
    col1, col2 = st.columns(2)

    with col1:
        _render_top_valor(df, cores)

    with col2:
        _render_top_pendente(df_pendentes, cores)

    st.divider()

    # ========== LINHA 2: Prazo Concedido pelo Fornecedor ==========
    col1, col2 = st.columns(2)

    with col1:
        _render_prazo_concedido(df, cores)

    with col2:
        _render_comparativo_prazos(df, df_pagos, cores)

    st.divider()

    # ========== LINHA 3: Comportamento de Pagamento ==========
    col1, col2 = st.columns(2)

    with col1:
        _render_prazo_por_fornecedor(df_pagos, cores)

    with col2:
        _render_pontualidade_por_fornecedor(df_pagos, cores)

    st.divider()

    # ========== LINHA 4: Analise de Risco e ABC ==========
    col1, col2 = st.columns(2)

    with col1:
        _render_matriz_risco(df, df_vencidos, cores)

    with col2:
        _render_curva_abc(df, cores)

    st.divider()

    # ========== BUSCA FORNECEDOR ==========
    _render_busca_fornecedor(df, df_pendentes, df_pagos, cores)

    st.divider()

    # ========== RANKING ==========
    _render_ranking(df, df_pagos, cores)


def _render_kpis(df, df_pendentes, df_pagos, cores):
    """KPIs principais"""

    total_fornecedores = df['NOME_FORNECEDOR'].nunique()
    total_valor = df['VALOR_ORIGINAL'].sum()
    total_pendente = df_pendentes['SALDO'].sum() if len(df_pendentes) > 0 else 0

    # Taxa pontualidade geral
    taxa_pontual = 0
    if len(df_pagos) > 0 and 'DIAS_ATRASO_PGTO' in df_pagos.columns:
        atraso = df_pagos['DIAS_ATRASO_PGTO'].dropna()
        if len(atraso) > 0:
            taxa_pontual = (atraso <= 0).sum() / len(atraso) * 100

    # Tempo medio para pagar (da emissao ate o pagamento)
    tempo_medio_pgto = 0
    if len(df_pagos) > 0 and 'DIAS_PARA_PAGAR' in df_pagos.columns:
        dias = df_pagos['DIAS_PARA_PAGAR'].dropna()
        # Filtrar apenas valores positivos (emissao antes do pagamento)
        dias_validos = dias[dias > 0]
        if len(dias_validos) > 0:
            tempo_medio_pgto = dias_validos.mean()

    # Fornecedores com atraso
    forn_com_atraso = df_pendentes[df_pendentes['STATUS'] == 'Vencido']['NOME_FORNECEDOR'].nunique() if len(df_pendentes) > 0 else 0

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            label="Total Fornecedores",
            value=formatar_numero(total_fornecedores),
            delta=f"{formatar_numero(len(df))} titulos",
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
        st.metric(
            label="Taxa Pontualidade",
            value=f"{taxa_pontual:.1f}%",
            delta="pagos no prazo",
            delta_color="off"
        )

    with col4:
        st.metric(
            label="Tempo Medio p/ Pagar",
            value=f"{tempo_medio_pgto:.0f} dias",
            delta="da NF ate o pagamento",
            delta_color="off"
        )

    with col5:
        pct_atraso = (forn_com_atraso / total_fornecedores * 100) if total_fornecedores > 0 else 0
        st.metric(
            label="Forn. com Atraso",
            value=formatar_numero(forn_com_atraso),
            delta=f"{pct_atraso:.1f}% do total",
            delta_color="off"
        )


def _render_top_valor(df, cores):
    """Top 10 por valor total"""

    st.markdown("##### Top 10 - Valor Total")

    df_forn = df.groupby('NOME_FORNECEDOR').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'FORNECEDOR': 'count'
    }).nlargest(10, 'VALOR_ORIGINAL').reset_index()

    df_forn['PAGO'] = df_forn['VALOR_ORIGINAL'] - df_forn['SALDO']

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=df_forn['NOME_FORNECEDOR'].str[:25],
        x=df_forn['PAGO'],
        orientation='h',
        name='Pago',
        marker_color=cores['sucesso'],
        text=[formatar_moeda(v) for v in df_forn['PAGO']],
        textposition='inside',
        textfont=dict(size=9, color='white')
    ))

    fig.add_trace(go.Bar(
        y=df_forn['NOME_FORNECEDOR'].str[:25],
        x=df_forn['SALDO'],
        orientation='h',
        name='Pendente',
        marker_color=cores['alerta'],
        text=[formatar_moeda(v) for v in df_forn['SALDO']],
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


def _render_top_pendente(df_pendentes, cores):
    """Top 10 com mais saldo pendente"""

    st.markdown("##### Top 10 - Saldo Pendente")

    if len(df_pendentes) == 0:
        st.info("Sem saldo pendente")
        return

    df_pend = df_pendentes.groupby('NOME_FORNECEDOR').agg({
        'SALDO': 'sum',
        'DIAS_ATRASO': 'max',
        'FORNECEDOR': 'count'
    }).nlargest(10, 'SALDO').reset_index()

    def cor_atraso(dias):
        if dias > 30:
            return cores['perigo']
        elif dias > 15:
            return '#f97316'
        elif dias > 0:
            return cores['alerta']
        return cores['primaria']

    bar_colors = [cor_atraso(d) for d in df_pend['DIAS_ATRASO']]

    fig = go.Figure(go.Bar(
        y=df_pend['NOME_FORNECEDOR'].str[:25],
        x=df_pend['SALDO'],
        orientation='h',
        marker_color=bar_colors,
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
    st.caption("Cor: Em dia | 1-15d | 16-30d | 30+d atraso")


def _render_prazo_concedido(df, cores):
    """Prazo concedido pelo fornecedor (Emissao -> Vencimento)"""

    st.markdown("##### Prazo Concedido pelo Fornecedor")
    st.caption("Dias entre Emissao da NF e Vencimento")

    # Calcular prazo concedido (vencimento - emissao)
    df_calc = df.copy()
    df_calc['PRAZO_CONCEDIDO'] = (df_calc['VENCIMENTO'] - df_calc['EMISSAO']).dt.days

    # Remover valores invalidos
    df_calc = df_calc[df_calc['PRAZO_CONCEDIDO'].notna() & (df_calc['PRAZO_CONCEDIDO'] >= 0)]

    if len(df_calc) == 0:
        st.info("Sem dados para calcular prazo concedido")
        return

    # Agrupar por fornecedor
    df_prazo = df_calc.groupby('NOME_FORNECEDOR').agg({
        'PRAZO_CONCEDIDO': 'mean',
        'VALOR_ORIGINAL': ['sum', 'count']
    }).reset_index()
    df_prazo.columns = ['Fornecedor', 'Prazo_Medio', 'Valor', 'Qtd']

    # Top 10 fornecedores com maior prazo (melhores para nosso fluxo de caixa)
    df_top = df_prazo.nlargest(10, 'Prazo_Medio')

    def cor_prazo(p):
        if p >= 60:
            return cores['sucesso']  # Excelente
        elif p >= 45:
            return '#84cc16'  # Muito bom
        elif p >= 30:
            return cores['info']  # Bom
        elif p >= 15:
            return cores['alerta']  # Regular
        return cores['perigo']  # Ruim

    bar_colors = [cor_prazo(p) for p in df_top['Prazo_Medio']]

    fig = go.Figure(go.Bar(
        y=df_top['Fornecedor'].str[:25],
        x=df_top['Prazo_Medio'],
        orientation='h',
        marker_color=bar_colors,
        text=[f"{p:.0f}d" for p in df_top['Prazo_Medio']],
        textposition='outside',
        textfont=dict(size=10)
    ))

    fig.update_layout(
        criar_layout(280),
        yaxis={'autorange': 'reversed'},
        margin=dict(l=10, r=50, t=10, b=10),
        xaxis_title='Dias'
    )

    st.plotly_chart(fig, use_container_width=True)

    # Metricas resumidas
    col1, col2, col3 = st.columns(3)
    prazo_geral = df_calc['PRAZO_CONCEDIDO'].mean()
    col1.metric("Prazo Medio Geral", f"{prazo_geral:.0f} dias")

    forn_30plus = len(df_prazo[df_prazo['Prazo_Medio'] >= 30])
    col2.metric("Forn. 30+ dias", formatar_numero(forn_30plus))

    forn_60plus = len(df_prazo[df_prazo['Prazo_Medio'] >= 60])
    col3.metric("Forn. 60+ dias", formatar_numero(forn_60plus))


def _render_comparativo_prazos(df, df_pagos, cores):
    """Comparativo: Prazo concedido vs Prazo real de pagamento"""

    st.markdown("##### Prazo Concedido vs Prazo Real")
    st.caption("Comparacao entre prazo do fornecedor e tempo real de pagamento")

    if len(df_pagos) == 0 or 'DIAS_PARA_PAGAR' not in df_pagos.columns:
        st.info("Sem dados de pagamentos realizados")
        return

    # Calcular prazo concedido nos pagos
    df_calc = df_pagos.copy()
    df_calc['PRAZO_CONCEDIDO'] = (df_calc['VENCIMENTO'] - df_calc['EMISSAO']).dt.days

    # Filtrar dados validos
    df_calc = df_calc[
        df_calc['PRAZO_CONCEDIDO'].notna() &
        df_calc['DIAS_PARA_PAGAR'].notna() &
        (df_calc['PRAZO_CONCEDIDO'] >= 0)
    ]

    if len(df_calc) == 0:
        st.info("Sem dados para comparacao")
        return

    # Agrupar por fornecedor
    df_comp = df_calc.groupby('NOME_FORNECEDOR').agg({
        'PRAZO_CONCEDIDO': 'mean',
        'DIAS_PARA_PAGAR': 'mean',
        'VALOR_ORIGINAL': 'sum'
    }).reset_index()
    df_comp.columns = ['Fornecedor', 'Prazo_Concedido', 'Prazo_Real', 'Valor']

    # Calcular diferenca (positivo = pagamos antes do prazo)
    df_comp['Diferenca'] = df_comp['Prazo_Concedido'] - df_comp['Prazo_Real']

    # Filtrar top 15 por valor
    df_top = df_comp.nlargest(15, 'Valor')

    fig = go.Figure()

    # Barras do prazo concedido
    fig.add_trace(go.Bar(
        y=df_top['Fornecedor'].str[:20],
        x=df_top['Prazo_Concedido'],
        orientation='h',
        name='Prazo Concedido',
        marker_color=cores['info'],
        opacity=0.7
    ))

    # Barras do prazo real
    fig.add_trace(go.Bar(
        y=df_top['Fornecedor'].str[:20],
        x=df_top['Prazo_Real'],
        orientation='h',
        name='Prazo Real',
        marker_color=cores['primaria']
    ))

    fig.update_layout(
        criar_layout(300, barmode='group'),
        yaxis={'autorange': 'reversed'},
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis_title='Dias'
    )

    st.plotly_chart(fig, use_container_width=True)

    # Metricas
    col1, col2, col3 = st.columns(3)

    prazo_conc_medio = df_comp['Prazo_Concedido'].mean()
    prazo_real_medio = df_comp['Prazo_Real'].mean()
    diferenca_media = prazo_conc_medio - prazo_real_medio

    col1.metric("Prazo Medio Concedido", f"{prazo_conc_medio:.0f} dias")
    col2.metric("Prazo Real Medio", f"{prazo_real_medio:.0f} dias")

    if diferenca_media > 0:
        col3.metric("Margem de Folga", f"{diferenca_media:.0f} dias", "pagamos antes")
    else:
        col3.metric("Atraso Medio", f"{abs(diferenca_media):.0f} dias", "alem do prazo", delta_color="inverse")


def _render_prazo_por_fornecedor(df_pagos, cores):
    """Tempo real de pagamento por fornecedor (Emissao -> Baixa)"""

    st.markdown("##### Tempo Real de Pagamento")
    st.caption("Dias entre Emissao da NF e Data da Baixa (pagamento)")

    if len(df_pagos) == 0 or 'DIAS_PARA_PAGAR' not in df_pagos.columns:
        st.info("Sem dados de pagamento")
        return

    df_prazo = df_pagos.groupby('NOME_FORNECEDOR').agg({
        'DIAS_PARA_PAGAR': 'mean',
        'VALOR_ORIGINAL': ['sum', 'count']
    }).reset_index()
    df_prazo.columns = ['Fornecedor', 'Prazo', 'Valor', 'Qtd']
    df_prazo = df_prazo.dropna(subset=['Prazo'])

    # Top 10 com maior tempo para pagar (mais lento)
    df_top = df_prazo.nlargest(10, 'Prazo')

    def cor_prazo(p):
        if p <= 30:
            return cores['sucesso']
        elif p <= 45:
            return cores['info']
        elif p <= 60:
            return cores['alerta']
        return cores['perigo']

    bar_colors = [cor_prazo(p) for p in df_top['Prazo']]

    fig = go.Figure(go.Bar(
        y=df_top['Fornecedor'].str[:25],
        x=df_top['Prazo'],
        orientation='h',
        marker_color=bar_colors,
        text=[f"{p:.0f}d" for p in df_top['Prazo']],
        textposition='outside',
        textfont=dict(size=10)
    ))

    fig.update_layout(
        criar_layout(300),
        yaxis={'autorange': 'reversed'},
        margin=dict(l=10, r=50, t=10, b=10),
        xaxis_title='Dias'
    )

    st.plotly_chart(fig, use_container_width=True)
    st.caption("Top 10 fornecedores onde levamos mais tempo para pagar (Emissao → Baixa)")


def _render_pontualidade_por_fornecedor(df_pagos, cores):
    """Distribuicao de pontualidade de pagamento"""

    st.markdown("##### Comportamento de Pagamento")

    if len(df_pagos) == 0 or 'DIAS_ATRASO_PGTO' not in df_pagos.columns:
        st.info("Sem dados de pagamento")
        return

    # Verificar se tem dados de atraso
    atraso_geral = df_pagos['DIAS_ATRASO_PGTO'].dropna()
    if len(atraso_geral) == 0:
        st.warning("Nenhum titulo com data de baixa preenchida")
        return

    # Calcular estatisticas gerais
    total_pagamentos = len(atraso_geral)
    pagos_no_prazo = (atraso_geral <= 0).sum()
    pagos_atrasados = (atraso_geral > 0).sum()
    taxa_pontualidade = pagos_no_prazo / total_pagamentos * 100
    atraso_medio = atraso_geral[atraso_geral > 0].mean() if pagos_atrasados > 0 else 0

    # Cards de resumo
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Pagamentos", formatar_numero(total_pagamentos))
    col2.metric("No Prazo", formatar_numero(pagos_no_prazo), f"{taxa_pontualidade:.1f}%")
    col3.metric("Com Atraso", formatar_numero(pagos_atrasados), f"{100-taxa_pontualidade:.1f}%")
    col4.metric("Atraso Medio", f"{atraso_medio:.0f} dias" if atraso_medio > 0 else "-")

    # Distribuicao por faixa de atraso
    def classificar_atraso(dias):
        if dias <= -7:
            return "Antecipado (7+ dias)"
        elif dias < 0:
            return "Antecipado (1-7 dias)"
        elif dias == 0:
            return "No vencimento"
        elif dias <= 7:
            return "Atraso 1-7 dias"
        elif dias <= 15:
            return "Atraso 8-15 dias"
        elif dias <= 30:
            return "Atraso 16-30 dias"
        else:
            return "Atraso 30+ dias"

    df_dist = pd.DataFrame({'ATRASO': atraso_geral})
    df_dist['FAIXA'] = df_dist['ATRASO'].apply(classificar_atraso)

    ordem = ["Antecipado (7+ dias)", "Antecipado (1-7 dias)", "No vencimento",
             "Atraso 1-7 dias", "Atraso 8-15 dias", "Atraso 16-30 dias", "Atraso 30+ dias"]

    df_grp = df_dist.groupby('FAIXA').size().reindex(ordem, fill_value=0).reset_index()
    df_grp.columns = ['Faixa', 'Qtd']
    df_grp['Pct'] = df_grp['Qtd'] / total_pagamentos * 100

    # Cores: verde para antecipado/no prazo, amarelo/vermelho para atraso
    cores_faixas = [
        cores['sucesso'],      # Antecipado 7+
        '#84cc16',             # Antecipado 1-7
        cores['primaria'],     # No vencimento
        cores['alerta'],       # Atraso 1-7
        '#f59e0b',             # Atraso 8-15
        '#f97316',             # Atraso 16-30
        cores['perigo']        # Atraso 30+
    ]

    fig = go.Figure(go.Bar(
        x=df_grp['Faixa'],
        y=df_grp['Qtd'],
        marker_color=cores_faixas,
        text=[f"{int(q)}<br>({p:.1f}%)" for q, p in zip(df_grp['Qtd'], df_grp['Pct'])],
        textposition='outside',
        textfont=dict(size=9)
    ))

    fig.update_layout(
        criar_layout(280),
        margin=dict(l=10, r=10, t=10, b=80),
        xaxis_tickangle=-30
    )

    st.plotly_chart(fig, use_container_width=True)
    st.caption("Distribuicao de pagamentos por faixa de atraso (DT_BAIXA vs VENCIMENTO)")


def _render_matriz_risco(df, df_vencidos, cores):
    """Matriz de risco: Valor x Atraso"""

    st.markdown("##### Matriz de Risco")

    if len(df_vencidos) == 0:
        st.success("Nenhum fornecedor com titulos vencidos!")
        return

    df_risco = df_vencidos.groupby('NOME_FORNECEDOR').agg({
        'SALDO': 'sum',
        'DIAS_ATRASO': 'max',
        'VALOR_ORIGINAL': 'count'
    }).reset_index()
    df_risco.columns = ['Fornecedor', 'Valor_Vencido', 'Dias_Atraso', 'Qtd']

    # Classificar risco
    def classificar_risco(row):
        if row['Valor_Vencido'] > 100000 and row['Dias_Atraso'] > 30:
            return 'Critico'
        elif row['Valor_Vencido'] > 50000 or row['Dias_Atraso'] > 30:
            return 'Alto'
        elif row['Dias_Atraso'] > 15:
            return 'Medio'
        return 'Baixo'

    df_risco['Risco'] = df_risco.apply(classificar_risco, axis=1)

    cores_risco = {
        'Critico': cores['perigo'],
        'Alto': '#f97316',
        'Medio': cores['alerta'],
        'Baixo': cores['info']
    }

    fig = px.scatter(
        df_risco,
        x='Dias_Atraso',
        y='Valor_Vencido',
        size='Qtd',
        color='Risco',
        hover_name='Fornecedor',
        color_discrete_map=cores_risco,
        labels={
            'Dias_Atraso': 'Dias em Atraso',
            'Valor_Vencido': 'Valor Vencido (R$)',
            'Qtd': 'Qtd Titulos'
        }
    )

    # Linhas de referencia
    fig.add_hline(y=50000, line_dash="dash", line_color=cores['alerta'], opacity=0.5)
    fig.add_vline(x=30, line_dash="dash", line_color=cores['alerta'], opacity=0.5)

    fig.update_layout(
        criar_layout(300),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        margin=dict(l=10, r=10, t=30, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)

    # Resumo
    col1, col2, col3, col4 = st.columns(4)
    for i, (risco, col) in enumerate(zip(['Critico', 'Alto', 'Medio', 'Baixo'], [col1, col2, col3, col4])):
        qtd = len(df_risco[df_risco['Risco'] == risco])
        col.metric(risco, qtd)


def _render_curva_abc(df, cores):
    """Curva ABC de fornecedores"""

    st.markdown("##### Curva ABC")

    df_abc = df.groupby('NOME_FORNECEDOR')['VALOR_ORIGINAL'].sum().sort_values(ascending=False).reset_index()
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
        xaxis_title="Rank"
    )

    st.plotly_chart(fig, use_container_width=True)

    # Resumo
    col1, col2, col3 = st.columns(3)
    qtd_a = len(df_abc[df_abc['CLASSE'] == 'A'])
    qtd_b = len(df_abc[df_abc['CLASSE'] == 'B'])
    qtd_c = len(df_abc[df_abc['CLASSE'] == 'C'])
    col1.success(f"**A**: {qtd_a} (80%)")
    col2.warning(f"**B**: {qtd_b} (15%)")
    col3.info(f"**C**: {qtd_c} (5%)")


def _render_busca_fornecedor(df, df_pendentes, df_pagos, cores):
    """Busca e detalhes de fornecedor"""

    st.markdown("##### Consultar Fornecedor")

    fornecedores = sorted(df['NOME_FORNECEDOR'].unique().tolist())

    fornecedor_selecionado = st.selectbox(
        "Selecione um fornecedor",
        options=[""] + fornecedores,
        key="busca_forn"
    )

    if not fornecedor_selecionado:
        return

    df_forn = df[df['NOME_FORNECEDOR'] == fornecedor_selecionado]
    df_pend_forn = df_pendentes[df_pendentes['NOME_FORNECEDOR'] == fornecedor_selecionado]
    df_pago_forn = df_pagos[df_pagos['NOME_FORNECEDOR'] == fornecedor_selecionado]

    # Calcular metricas
    total_valor = df_forn['VALOR_ORIGINAL'].sum()
    total_pendente = df_forn['SALDO'].sum()
    total_pago = total_valor - total_pendente
    qtd_titulos = len(df_forn)

    # Vencidos
    vencidos = df_pend_forn[df_pend_forn['STATUS'] == 'Vencido']
    total_vencido = vencidos['SALDO'].sum() if len(vencidos) > 0 else 0
    dias_atraso_max = vencidos['DIAS_ATRASO'].max() if len(vencidos) > 0 else 0

    # Prazo e pontualidade
    prazo_medio = 0
    taxa_pontual = 0
    if len(df_pago_forn) > 0:
        if 'DIAS_PARA_PAGAR' in df_pago_forn.columns:
            prazo = df_pago_forn['DIAS_PARA_PAGAR'].dropna()
            if len(prazo) > 0:
                prazo_medio = prazo.mean()

        if 'DIAS_ATRASO_PGTO' in df_pago_forn.columns:
            atraso = df_pago_forn['DIAS_ATRASO_PGTO'].dropna()
            if len(atraso) > 0:
                taxa_pontual = (atraso <= 0).sum() / len(atraso) * 100

    # Linha 1: Metricas financeiras
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Valor Total", formatar_moeda(total_valor), f"{qtd_titulos} titulos")
    col2.metric("Pago", formatar_moeda(total_pago))
    col3.metric("Pendente", formatar_moeda(total_pendente))
    col4.metric("Vencido", formatar_moeda(total_vencido), f"{int(dias_atraso_max)}d atraso" if dias_atraso_max > 0 else "Em dia")

    # Linha 2: Metricas de comportamento
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Prazo Medio Pgto", f"{prazo_medio:.0f} dias")
    col2.metric("Taxa Pontualidade", f"{taxa_pontual:.1f}%")

    pct_pago = (total_pago / total_valor * 100) if total_valor > 0 else 0
    col3.metric("% Pago", f"{pct_pago:.1f}%")

    # Classificar fornecedor
    if taxa_pontual >= 80 and prazo_medio <= 45:
        status = "Excelente"
        cor_status = "success"
    elif taxa_pontual >= 60:
        status = "Bom"
        cor_status = "info"
    elif taxa_pontual >= 40:
        status = "Regular"
        cor_status = "warning"
    else:
        status = "Atencao"
        cor_status = "error"

    with col4:
        if cor_status == "success":
            st.success(f"**{status}**")
        elif cor_status == "info":
            st.info(f"**{status}**")
        elif cor_status == "warning":
            st.warning(f"**{status}**")
        else:
            st.error(f"**{status}**")

    # Tabs de detalhes
    tab1, tab2 = st.tabs(["Historico", "Titulos"])

    with tab1:
        # Grafico de evolucao
        df_hist = df_forn.copy()
        df_hist['MES'] = df_hist['EMISSAO'].dt.to_period('M').astype(str)
        df_hist_grp = df_hist.groupby('MES').agg({
            'VALOR_ORIGINAL': 'sum',
            'SALDO': 'sum'
        }).reset_index()
        df_hist_grp['PAGO'] = df_hist_grp['VALOR_ORIGINAL'] - df_hist_grp['SALDO']

        if len(df_hist_grp) > 1:
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df_hist_grp['MES'], y=df_hist_grp['PAGO'], name='Pago', marker_color=cores['sucesso']))
            fig.add_trace(go.Bar(x=df_hist_grp['MES'], y=df_hist_grp['SALDO'], name='Pendente', marker_color=cores['alerta']))
            fig.update_layout(criar_layout(200, barmode='stack'), margin=dict(l=10, r=10, t=10, b=30))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Historico insuficiente")

    with tab2:
        # Tabela de titulos
        colunas = ['NOME_FILIAL', 'EMISSAO', 'VENCIMENTO', 'DT_BAIXA', 'DIAS_PARA_PAGAR', 'DIAS_ATRASO_PGTO', 'VALOR_ORIGINAL', 'SALDO', 'STATUS']
        colunas_disp = [c for c in colunas if c in df_forn.columns]
        df_tab = df_forn[colunas_disp].copy()

        for col in ['EMISSAO', 'VENCIMENTO', 'DT_BAIXA']:
            if col in df_tab.columns:
                df_tab[col] = pd.to_datetime(df_tab[col], errors='coerce').dt.strftime('%d/%m/%Y')
                df_tab[col] = df_tab[col].fillna('-')

        df_tab['VALOR_ORIGINAL'] = df_tab['VALOR_ORIGINAL'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab['SALDO'] = df_tab['SALDO'].apply(lambda x: formatar_moeda(x, completo=True))

        if 'DIAS_PARA_PAGAR' in df_tab.columns:
            df_tab['DIAS_PARA_PAGAR'] = df_tab['DIAS_PARA_PAGAR'].apply(lambda x: f"{int(x)}d" if pd.notna(x) else '-')

        if 'DIAS_ATRASO_PGTO' in df_tab.columns:
            def fmt_atraso(d):
                if pd.isna(d):
                    return '-'
                d = int(d)
                if d < 0:
                    return f"{abs(d)}d antec."
                elif d == 0:
                    return "No prazo"
                return f"{d}d atras."
            df_tab['DIAS_ATRASO_PGTO'] = df_tab['DIAS_ATRASO_PGTO'].apply(fmt_atraso)

        nomes = {
            'NOME_FILIAL': 'Filial',
            'EMISSAO': 'Emissao',
            'VENCIMENTO': 'Vencimento',
            'DT_BAIXA': 'Dt Pagto',
            'DIAS_PARA_PAGAR': 'Dias p/ Pagar',
            'DIAS_ATRASO_PGTO': 'Pgto vs Venc',
            'VALOR_ORIGINAL': 'Valor',
            'SALDO': 'Saldo',
            'STATUS': 'Status'
        }
        df_tab.columns = [nomes.get(c, c) for c in df_tab.columns]

        st.dataframe(df_tab, use_container_width=True, hide_index=True, height=300)


def _render_ranking(df, df_pagos, cores):
    """Ranking completo de fornecedores"""

    st.markdown("##### Ranking de Fornecedores")

    # Filtros
    col1, col2, col3 = st.columns(3)
    with col1:
        ordenar = st.selectbox(
            "Ordenar por",
            ["Valor Total", "Saldo Pendente", "Prazo Medio", "Pontualidade"],
            key="rank_ordem"
        )
    with col2:
        qtd_exibir = st.selectbox("Exibir", [20, 50, 100], key="rank_qtd")
    with col3:
        filtro = st.selectbox("Filtrar", ["Todos", "Com Pendencia", "Quitados"], key="rank_filtro")

    # Preparar dados base
    df_rank = df.groupby('NOME_FORNECEDOR').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'FORNECEDOR': 'count'
    }).reset_index()
    df_rank.columns = ['Fornecedor', 'Total', 'Pendente', 'Titulos']

    # Adicionar metricas de pagamento
    if len(df_pagos) > 0:
        def calc_metricas(forn):
            df_f = df_pagos[df_pagos['NOME_FORNECEDOR'] == forn]
            if len(df_f) == 0:
                return pd.Series({'Prazo': None, 'Pontualidade': None})

            prazo = None
            pont = None

            if 'DIAS_PARA_PAGAR' in df_f.columns:
                p = df_f['DIAS_PARA_PAGAR'].dropna()
                if len(p) > 0:
                    prazo = p.mean()

            if 'DIAS_ATRASO_PGTO' in df_f.columns:
                a = df_f['DIAS_ATRASO_PGTO'].dropna()
                if len(a) > 0:
                    pont = (a <= 0).sum() / len(a) * 100

            return pd.Series({'Prazo': prazo, 'Pontualidade': pont})

        metricas = df_rank['Fornecedor'].apply(calc_metricas)
        df_rank = pd.concat([df_rank, metricas], axis=1)
    else:
        df_rank['Prazo'] = None
        df_rank['Pontualidade'] = None

    df_rank['% Pago'] = ((df_rank['Total'] - df_rank['Pendente']) / df_rank['Total'] * 100).round(1)

    # Filtrar
    if filtro == "Com Pendencia":
        df_rank = df_rank[df_rank['Pendente'] > 0]
    elif filtro == "Quitados":
        df_rank = df_rank[df_rank['Pendente'] <= 0]

    # Ordenar
    if ordenar == "Valor Total":
        df_rank = df_rank.sort_values('Total', ascending=False)
    elif ordenar == "Saldo Pendente":
        df_rank = df_rank.sort_values('Pendente', ascending=False)
    elif ordenar == "Prazo Medio":
        df_rank = df_rank.sort_values('Prazo', ascending=False, na_position='last')
    else:
        df_rank = df_rank.sort_values('Pontualidade', ascending=True, na_position='last')

    df_rank = df_rank.head(qtd_exibir)

    # Formatar para exibicao
    df_show = df_rank.copy()
    df_show['Total'] = df_show['Total'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Pendente'] = df_show['Pendente'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Prazo'] = df_show['Prazo'].apply(lambda x: f"{x:.0f}d" if pd.notna(x) else '-')
    df_show['Pontualidade'] = df_show['Pontualidade'].apply(lambda x: f"{x:.0f}%" if pd.notna(x) else '-')

    st.dataframe(
        df_show,
        use_container_width=True,
        hide_index=True,
        height=400,
        column_config={
            "% Pago": st.column_config.ProgressColumn(
                "% Pago",
                format="%.1f%%",
                min_value=0,
                max_value=100
            )
        }
    )

    st.caption(f"Exibindo {len(df_show)} fornecedores")
