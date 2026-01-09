"""
Aba Formas de Pagamento - Analise por forma de pagamento
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from config.theme import get_cores
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero


def render_formas_pagamento(df):
    """Renderiza a aba de Formas de Pagamento"""
    cores = get_cores()
    hoje = datetime.now()

    if len(df) == 0:
        st.warning("Nenhum dado disponivel.")
        return

    # Verificar se coluna existe
    if 'DESCRICAO_FORMA_PAGAMENTO' not in df.columns:
        st.warning("Coluna de forma de pagamento nao encontrada.")
        return

    # Tratar valores vazios/nulos na forma de pagamento - INCLUIR como "Nao Informado"
    df = df.copy()
    df['DESCRICAO_FORMA_PAGAMENTO'] = df['DESCRICAO_FORMA_PAGAMENTO'].fillna('').astype(str).str.strip()
    df.loc[df['DESCRICAO_FORMA_PAGAMENTO'] == '', 'DESCRICAO_FORMA_PAGAMENTO'] = 'Nao Informado'

    # Contar registros sem forma original para mostrar cobertura
    qtd_nao_informado = len(df[df['DESCRICAO_FORMA_PAGAMENTO'] == 'Nao Informado'])

    # ========== RESUMO DE COBERTURA ==========
    if qtd_nao_informado > 0:
        total_titulos = len(df)
        pct_nao_info = qtd_nao_informado / total_titulos * 100
        qtd_informado = total_titulos - qtd_nao_informado

        st.markdown("##### Cobertura de Dados")

        col1, col2 = st.columns(2)

        col1.metric(
            "Com Forma Informada",
            formatar_numero(qtd_informado),
            f"{100-pct_nao_info:.1f}% dos titulos"
        )

        col2.metric(
            "Nao Informado",
            formatar_numero(qtd_nao_informado),
            f"{pct_nao_info:.1f}% (incluido na analise)"
        )

        st.divider()

    # Preparar dados
    df_pagos = df[df['SALDO'] == 0].copy()
    df_pendentes = df[df['SALDO'] > 0].copy()
    df_vencidos = df[df['STATUS'] == 'Vencido'].copy()

    # ========== KPIs ==========
    total_formas = df['DESCRICAO_FORMA_PAGAMENTO'].nunique()
    total_valor = df['VALOR_ORIGINAL'].sum()
    total_pendente = df_pendentes['SALDO'].sum()

    # Forma mais usada
    forma_mais_usada = df.groupby('DESCRICAO_FORMA_PAGAMENTO')['VALOR_ORIGINAL'].sum().idxmax() if len(df) > 0 else 'N/A'
    pct_forma_top = (df[df['DESCRICAO_FORMA_PAGAMENTO'] == forma_mais_usada]['VALOR_ORIGINAL'].sum() / total_valor * 100) if total_valor > 0 else 0

    # Pontualidade geral
    taxa_pontual = 0
    if len(df_pagos) > 0 and 'DIAS_ATRASO_PGTO' in df_pagos.columns:
        atraso = df_pagos['DIAS_ATRASO_PGTO'].dropna()
        if len(atraso) > 0:
            taxa_pontual = (atraso <= 0).sum() / len(atraso) * 100

    # Prazo medio
    prazo_medio = 0
    if len(df_pagos) > 0 and 'DIAS_PARA_PAGAR' in df_pagos.columns:
        prazo = df_pagos['DIAS_PARA_PAGAR'].dropna()
        if len(prazo) > 0:
            prazo_medio = prazo.mean()

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Formas de Pagto", total_formas)
    col2.metric("Valor Total", formatar_moeda(total_valor))
    col3.metric("Pendente", formatar_moeda(total_pendente))
    col4.metric("Taxa Pontualidade", f"{taxa_pontual:.1f}%")
    col5.metric("Prazo Medio", f"{prazo_medio:.0f} dias")

    st.divider()

    # ========== GRAFICOS LINHA 1 ==========
    col1, col2 = st.columns(2)

    with col1:
        _render_distribuicao_valor(df, cores)

    with col2:
        _render_distribuicao_quantidade(df, cores)

    # ========== GRAFICOS LINHA 2 ==========
    col1, col2 = st.columns(2)

    with col1:
        _render_prazo_por_forma(df_pagos, cores)

    with col2:
        _render_pontualidade_por_forma(df_pagos, cores)

    # ========== GRAFICOS LINHA 3 ==========
    col1, col2 = st.columns(2)

    with col1:
        _render_pendente_por_forma(df_pendentes, cores)

    with col2:
        _render_vencido_por_forma(df_vencidos, cores)

    st.divider()

    # ========== TABELA RANKING ==========
    _render_ranking_formas(df, df_pagos, df_pendentes, df_vencidos, cores)


def _render_distribuicao_valor(df, cores):
    """Distribuicao por valor"""

    st.markdown("##### Distribuicao por Valor")

    df_grp = df.groupby('DESCRICAO_FORMA_PAGAMENTO')['VALOR_ORIGINAL'].sum().sort_values(ascending=False).head(10).reset_index()
    df_grp.columns = ['Forma', 'Valor']

    fig = go.Figure(go.Pie(
        labels=df_grp['Forma'],
        values=df_grp['Valor'],
        hole=0.5,
        marker=dict(colors=[cores['primaria'], cores['info'], cores['sucesso'], cores['alerta'], '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1']),
        textinfo='percent',
        textfont=dict(size=10),
        hovertemplate='<b>%{label}</b><br>%{value:,.2f}<br>%{percent}<extra></extra>'
    ))

    fig.update_layout(
        criar_layout(280),
        showlegend=True,
        legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02, font=dict(size=9)),
        margin=dict(l=10, r=120, t=10, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_distribuicao_quantidade(df, cores):
    """Distribuicao por quantidade"""

    st.markdown("##### Distribuicao por Quantidade")

    df_grp = df.groupby('DESCRICAO_FORMA_PAGAMENTO').size().sort_values(ascending=False).head(10).reset_index()
    df_grp.columns = ['Forma', 'Qtd']

    fig = go.Figure(go.Bar(
        x=df_grp['Forma'].str[:15],
        y=df_grp['Qtd'],
        marker_color=cores['info'],
        text=df_grp['Qtd'],
        textposition='outside',
        textfont=dict(size=9)
    ))

    fig.update_layout(
        criar_layout(280),
        xaxis_tickangle=-45,
        margin=dict(l=10, r=10, t=10, b=80)
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_prazo_por_forma(df_pagos, cores):
    """Prazo medio de pagamento por forma"""

    st.markdown("##### Prazo Medio por Forma")

    if len(df_pagos) == 0 or 'DIAS_PARA_PAGAR' not in df_pagos.columns:
        st.info("Sem dados de pagamento")
        return

    df_grp = df_pagos.groupby('DESCRICAO_FORMA_PAGAMENTO').agg({
        'DIAS_PARA_PAGAR': 'mean',
        'VALOR_ORIGINAL': 'count'
    }).reset_index()
    df_grp.columns = ['Forma', 'Prazo', 'Qtd']

    # Filtrar formas com pelo menos 5 pagamentos
    df_grp = df_grp[df_grp['Qtd'] >= 5].sort_values('Prazo', ascending=True).head(10)

    if len(df_grp) == 0:
        st.info("Sem dados suficientes (min. 5 pagamentos)")
        return

    fig = go.Figure(go.Bar(
        y=df_grp['Forma'].str[:20],
        x=df_grp['Prazo'],
        orientation='h',
        marker_color=cores['primaria'],
        text=[f"{p:.0f}d" for p in df_grp['Prazo']],
        textposition='outside',
        textfont=dict(size=9)
    ))

    fig.update_layout(
        criar_layout(280),
        yaxis={'autorange': 'reversed'},
        margin=dict(l=10, r=50, t=10, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_pontualidade_por_forma(df_pagos, cores):
    """Pontualidade por forma de pagamento"""

    st.markdown("##### Pontualidade por Forma")

    if len(df_pagos) == 0 or 'DIAS_ATRASO_PGTO' not in df_pagos.columns:
        st.info("Sem dados de pagamento")
        return

    # Calcular pontualidade por forma
    def calc_pontualidade(group):
        atraso = group['DIAS_ATRASO_PGTO'].dropna()
        if len(atraso) < 5:
            return None
        return (atraso <= 0).sum() / len(atraso) * 100

    df_pont = df_pagos.groupby('DESCRICAO_FORMA_PAGAMENTO').apply(calc_pontualidade).dropna().sort_values(ascending=False).head(10).reset_index()
    df_pont.columns = ['Forma', 'Pontualidade']

    if len(df_pont) == 0:
        st.info("Sem dados suficientes (min. 5 pagamentos)")
        return

    # Cores baseadas na pontualidade
    def cor_pont(p):
        if p >= 70:
            return cores['sucesso']
        elif p >= 50:
            return cores['alerta']
        return cores['perigo']

    fig = go.Figure(go.Bar(
        y=df_pont['Forma'].str[:20],
        x=df_pont['Pontualidade'],
        orientation='h',
        marker_color=[cor_pont(p) for p in df_pont['Pontualidade']],
        text=[f"{p:.0f}%" for p in df_pont['Pontualidade']],
        textposition='outside',
        textfont=dict(size=9)
    ))

    fig.update_layout(
        criar_layout(280),
        yaxis={'autorange': 'reversed'},
        xaxis=dict(range=[0, 105]),
        margin=dict(l=10, r=40, t=10, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_pendente_por_forma(df_pendentes, cores):
    """Valor pendente por forma"""

    st.markdown("##### Valor Pendente por Forma")

    if len(df_pendentes) == 0:
        st.success("Sem pendencias!")
        return

    df_grp = df_pendentes.groupby('DESCRICAO_FORMA_PAGAMENTO')['SALDO'].sum().sort_values(ascending=False).head(8).reset_index()
    df_grp.columns = ['Forma', 'Valor']

    fig = go.Figure(go.Bar(
        y=df_grp['Forma'].str[:20],
        x=df_grp['Valor'],
        orientation='h',
        marker_color=cores['alerta'],
        text=[formatar_moeda(v) for v in df_grp['Valor']],
        textposition='outside',
        textfont=dict(size=9)
    ))

    fig.update_layout(
        criar_layout(250),
        yaxis={'autorange': 'reversed'},
        margin=dict(l=10, r=80, t=10, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_vencido_por_forma(df_vencidos, cores):
    """Valor vencido por forma"""

    st.markdown("##### Valor Vencido por Forma")

    if len(df_vencidos) == 0:
        st.success("Sem vencidos!")
        return

    df_grp = df_vencidos.groupby('DESCRICAO_FORMA_PAGAMENTO')['SALDO'].sum().sort_values(ascending=False).head(8).reset_index()
    df_grp.columns = ['Forma', 'Valor']

    fig = go.Figure(go.Bar(
        y=df_grp['Forma'].str[:20],
        x=df_grp['Valor'],
        orientation='h',
        marker_color=cores['perigo'],
        text=[formatar_moeda(v) for v in df_grp['Valor']],
        textposition='outside',
        textfont=dict(size=9)
    ))

    fig.update_layout(
        criar_layout(250),
        yaxis={'autorange': 'reversed'},
        margin=dict(l=10, r=80, t=10, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_ranking_formas(df, df_pagos, df_pendentes, df_vencidos, cores):
    """Tabela ranking de formas de pagamento"""

    st.markdown("##### Ranking - Formas de Pagamento")

    # Agrupar dados
    df_grp = df.groupby('DESCRICAO_FORMA_PAGAMENTO').agg({
        'VALOR_ORIGINAL': ['count', 'sum'],
        'SALDO': 'sum'
    }).reset_index()
    df_grp.columns = ['Forma', 'Qtd', 'Total', 'Saldo']

    # Calcular pontualidade
    if len(df_pagos) > 0 and 'DIAS_ATRASO_PGTO' in df_pagos.columns:
        def calc_pont(forma):
            subset = df_pagos[df_pagos['DESCRICAO_FORMA_PAGAMENTO'] == forma]['DIAS_ATRASO_PGTO'].dropna()
            if len(subset) < 5:
                return None
            return (subset <= 0).sum() / len(subset) * 100

        df_grp['Pontualidade'] = df_grp['Forma'].apply(calc_pont)
    else:
        df_grp['Pontualidade'] = None

    # Calcular prazo medio
    if len(df_pagos) > 0 and 'DIAS_PARA_PAGAR' in df_pagos.columns:
        def calc_prazo(forma):
            subset = df_pagos[df_pagos['DESCRICAO_FORMA_PAGAMENTO'] == forma]['DIAS_PARA_PAGAR'].dropna()
            if len(subset) < 5:
                return None
            return subset.mean()

        df_grp['Prazo'] = df_grp['Forma'].apply(calc_prazo)
    else:
        df_grp['Prazo'] = None

    # Calcular vencido
    df_venc_grp = df_vencidos.groupby('DESCRICAO_FORMA_PAGAMENTO')['SALDO'].sum().reset_index()
    df_venc_grp.columns = ['Forma', 'Vencido']
    df_grp = df_grp.merge(df_venc_grp, on='Forma', how='left')
    df_grp['Vencido'] = df_grp['Vencido'].fillna(0)

    # Ordenar
    df_grp = df_grp.sort_values('Total', ascending=False)

    # Formatar
    df_show = df_grp.copy()
    df_show['Total'] = df_show['Total'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Saldo'] = df_show['Saldo'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Vencido'] = df_show['Vencido'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Pontualidade'] = df_show['Pontualidade'].apply(lambda x: f"{x:.0f}%" if pd.notna(x) else '-')
    df_show['Prazo'] = df_show['Prazo'].apply(lambda x: f"{x:.0f}d" if pd.notna(x) else '-')

    # Renomear
    df_show.columns = ['Forma de Pagamento', 'Qtd Titulos', 'Valor Total', 'Saldo Pendente', 'Pontualidade', 'Prazo Medio', 'Valor Vencido']

    st.dataframe(
        df_show,
        use_container_width=True,
        hide_index=True,
        height=400
    )

    st.caption(f"Total: {len(df_show)} formas de pagamento")
