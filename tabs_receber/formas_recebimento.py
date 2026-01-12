"""
Aba Formas de Recebimento - Analise por forma de recebimento
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from config.theme import get_cores
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero


def render_formas_recebimento(df):
    """Renderiza a aba de Formas de Recebimento"""
    cores = get_cores()
    hoje = datetime.now()

    if len(df) == 0:
        st.warning("Nenhum dado disponivel.")
        return

    # Verificar se coluna existe
    if 'DESCRICAO_FORMA_PAGAMENTO' not in df.columns:
        st.warning("Coluna de forma de recebimento nao encontrada.")
        return

    # Tratar valores vazios/nulos na forma de pagamento
    df = df.copy()
    df['DESCRICAO_FORMA_PAGAMENTO'] = df['DESCRICAO_FORMA_PAGAMENTO'].fillna('').astype(str).str.strip()

    # Calcular dados SEM forma de recebimento
    df_sem_forma = df[df['DESCRICAO_FORMA_PAGAMENTO'] == '']
    qtd_sem_forma = len(df_sem_forma)
    valor_sem_forma = df_sem_forma['VALOR_ORIGINAL'].sum()

    # Separar recebidos e pendentes sem forma
    sem_forma_recebidos = df_sem_forma[df_sem_forma['SALDO'] == 0]
    sem_forma_pendentes = df_sem_forma[df_sem_forma['SALDO'] > 0]

    qtd_sem_recebidos = len(sem_forma_recebidos)
    valor_sem_recebidos = sem_forma_recebidos['VALOR_ORIGINAL'].sum()

    qtd_sem_pendentes = len(sem_forma_pendentes)
    valor_sem_pendentes = sem_forma_pendentes['VALOR_ORIGINAL'].sum()
    saldo_sem_pendentes = sem_forma_pendentes['SALDO'].sum()

    # Filtrar apenas com forma de recebimento para analise
    df_com_forma = df[df['DESCRICAO_FORMA_PAGAMENTO'] != '']

    # ========== RESUMO DE COBERTURA ==========
    if qtd_sem_forma > 0:
        total_titulos = len(df)
        pct_sem = qtd_sem_forma / total_titulos * 100

        st.markdown("##### Cobertura de Dados")

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Com Forma Informada",
            formatar_numero(len(df_com_forma)),
            f"{100-pct_sem:.1f}% dos titulos"
        )

        col2.metric(
            "Sem Forma Informada",
            formatar_numero(qtd_sem_forma),
            f"{pct_sem:.1f}% dos titulos"
        )

        col3.metric(
            "Recebidos s/ Forma",
            formatar_numero(qtd_sem_recebidos),
            formatar_moeda(valor_sem_recebidos)
        )

        col4.metric(
            "Pendentes s/ Forma",
            formatar_numero(qtd_sem_pendentes),
            f"Saldo: {formatar_moeda(saldo_sem_pendentes)}"
        )

        st.divider()

    if len(df_com_forma) == 0:
        st.warning("Nenhum registro com forma de recebimento informada.")
        return

    # Usar apenas dados com forma informada para analise
    df = df_com_forma

    # Preparar dados
    df_recebidos = df[df['SALDO'] == 0].copy()
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
    if len(df_recebidos) > 0 and 'DIAS_ATRASO_PGTO' in df_recebidos.columns:
        atraso = df_recebidos['DIAS_ATRASO_PGTO'].dropna()
        if len(atraso) > 0:
            taxa_pontual = (atraso <= 0).sum() / len(atraso) * 100

    # Prazo medio
    prazo_medio = 0
    if len(df_recebidos) > 0 and 'DIAS_PARA_PAGAR' in df_recebidos.columns:
        prazo = df_recebidos['DIAS_PARA_PAGAR'].dropna()
        if len(prazo) > 0:
            prazo_medio = prazo.mean()

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Formas de Recebto", total_formas)
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
        _render_prazo_por_forma(df_recebidos, cores)

    with col2:
        _render_pontualidade_por_forma(df_recebidos, cores)

    # ========== GRAFICOS LINHA 3 ==========
    col1, col2 = st.columns(2)

    with col1:
        _render_pendente_por_forma(df_pendentes, cores)

    with col2:
        _render_vencido_por_forma(df_vencidos, cores)

    st.divider()

    # ========== TABELA RANKING ==========
    _render_ranking_formas(df, df_recebidos, df_pendentes, df_vencidos, cores)


def _render_distribuicao_valor(df, cores):
    """Distribuicao por valor"""

    st.markdown("##### Distribuicao por Valor")

    df_grp = df.groupby('DESCRICAO_FORMA_PAGAMENTO')['VALOR_ORIGINAL'].sum().sort_values(ascending=False).head(10).reset_index()
    df_grp.columns = ['Forma', 'Valor']

    fig = go.Figure(go.Pie(
        labels=df_grp['Forma'],
        values=df_grp['Valor'],
        hole=0.5,
        marker=dict(colors=[cores['sucesso'], cores['info'], cores['primaria'], cores['alerta'], '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1']),
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
        marker_color=cores['sucesso'],
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


def _render_prazo_por_forma(df_recebidos, cores):
    """Prazo medio de recebimento por forma"""

    st.markdown("##### Prazo Medio por Forma")

    if len(df_recebidos) == 0 or 'DIAS_PARA_PAGAR' not in df_recebidos.columns:
        st.info("Sem dados de recebimento")
        return

    df_grp = df_recebidos.groupby('DESCRICAO_FORMA_PAGAMENTO').agg({
        'DIAS_PARA_PAGAR': 'mean',
        'VALOR_ORIGINAL': 'count'
    }).reset_index()
    df_grp.columns = ['Forma', 'Prazo', 'Qtd']

    # Filtrar formas com pelo menos 5 recebimentos
    df_grp = df_grp[df_grp['Qtd'] >= 5].sort_values('Prazo', ascending=True).head(10)

    if len(df_grp) == 0:
        st.info("Sem dados suficientes (min. 5 recebimentos)")
        return

    fig = go.Figure(go.Bar(
        y=df_grp['Forma'].str[:20],
        x=df_grp['Prazo'],
        orientation='h',
        marker_color=cores['sucesso'],
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


def _render_pontualidade_por_forma(df_recebidos, cores):
    """Pontualidade por forma de recebimento"""

    st.markdown("##### Pontualidade por Forma")

    if len(df_recebidos) == 0 or 'DIAS_ATRASO_PGTO' not in df_recebidos.columns:
        st.info("Sem dados de recebimento")
        return

    # Calcular pontualidade por forma
    def calc_pontualidade(group):
        atraso = group['DIAS_ATRASO_PGTO'].dropna()
        if len(atraso) < 5:
            return None
        return (atraso <= 0).sum() / len(atraso) * 100

    df_pont = df_recebidos.groupby('DESCRICAO_FORMA_PAGAMENTO').apply(calc_pontualidade).dropna().sort_values(ascending=False).head(10).reset_index()
    df_pont.columns = ['Forma', 'Pontualidade']

    if len(df_pont) == 0:
        st.info("Sem dados suficientes (min. 5 recebimentos)")
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


def _render_ranking_formas(df, df_recebidos, df_pendentes, df_vencidos, cores):
    """Tabela ranking de formas de recebimento"""

    st.markdown("##### Ranking - Formas de Recebimento")

    # Agrupar dados
    df_grp = df.groupby('DESCRICAO_FORMA_PAGAMENTO').agg({
        'VALOR_ORIGINAL': ['count', 'sum'],
        'SALDO': 'sum'
    }).reset_index()
    df_grp.columns = ['Forma', 'Qtd', 'Total', 'Saldo']

    # Calcular pontualidade
    if len(df_recebidos) > 0 and 'DIAS_ATRASO_PGTO' in df_recebidos.columns:
        def calc_pont(forma):
            subset = df_recebidos[df_recebidos['DESCRICAO_FORMA_PAGAMENTO'] == forma]['DIAS_ATRASO_PGTO'].dropna()
            if len(subset) < 5:
                return None
            return (subset <= 0).sum() / len(subset) * 100

        df_grp['Pontualidade'] = df_grp['Forma'].apply(calc_pont)
    else:
        df_grp['Pontualidade'] = None

    # Calcular prazo medio
    if len(df_recebidos) > 0 and 'DIAS_PARA_PAGAR' in df_recebidos.columns:
        def calc_prazo(forma):
            subset = df_recebidos[df_recebidos['DESCRICAO_FORMA_PAGAMENTO'] == forma]['DIAS_PARA_PAGAR'].dropna()
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
    df_show.columns = ['Forma de Recebimento', 'Qtd Titulos', 'Valor Total', 'Saldo Pendente', 'Pontualidade', 'Prazo Medio', 'Valor Vencido']

    st.dataframe(
        df_show,
        use_container_width=True,
        hide_index=True,
        height=400
    )

    st.caption(f"Total: {len(df_show)} formas de recebimento")
