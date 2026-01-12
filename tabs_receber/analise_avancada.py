"""
Aba Estatisticas - Analises estatisticas e de risco - Contas a Receber
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

from config.theme import get_cores
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero


def get_df_vencidos(df):
    return df[df['STATUS'] == 'Vencido']


def render_analise_avancada_receber(df):
    """Renderiza a aba de Estatisticas"""
    cores = get_cores()
    hoje = datetime.now()

    if len(df) == 0:
        st.warning("Nenhum dado disponivel para analise.")
        return

    st.markdown("### Estatisticas e Risco")

    tab1, tab2, tab3 = st.tabs([
        "Curva ABC",
        "Risco",
        "Estatisticas"
    ])

    with tab1:
        _render_curva_abc(df, cores)

    with tab2:
        _render_risco(df, cores, hoje)

    with tab3:
        _render_estatisticas(df, cores)


def _render_curva_abc(df, cores):
    """Renderiza analise de Curva ABC - Apenas Clientes"""

    st.markdown("#### Analise ABC de Clientes")

    df_cli = df.groupby('NOME_CLIENTE').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum'
    }).sort_values('VALOR_ORIGINAL', ascending=False).reset_index()

    total = df_cli['VALOR_ORIGINAL'].sum()
    df_cli['%'] = df_cli['VALOR_ORIGINAL'] / total * 100
    df_cli['Acum'] = df_cli['%'].cumsum()
    df_cli['Classe'] = df_cli['Acum'].apply(lambda x: 'A' if x <= 80 else ('B' if x <= 95 else 'C'))

    qtd_a = len(df_cli[df_cli['Classe'] == 'A'])
    qtd_b = len(df_cli[df_cli['Classe'] == 'B'])
    qtd_c = len(df_cli[df_cli['Classe'] == 'C'])
    valor_a = df_cli[df_cli['Classe'] == 'A']['VALOR_ORIGINAL'].sum()
    valor_b = df_cli[df_cli['Classe'] == 'B']['VALOR_ORIGINAL'].sum()
    valor_c = df_cli[df_cli['Classe'] == 'C']['VALOR_ORIGINAL'].sum()

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Clientes", formatar_numero(len(df_cli)))
    col2.metric("Classe A", f"{qtd_a} ({qtd_a/len(df_cli)*100:.0f}%)")
    col3.metric("Classe B", f"{qtd_b} ({qtd_b/len(df_cli)*100:.0f}%)")
    col4.metric("Classe C", f"{qtd_c} ({qtd_c/len(df_cli)*100:.0f}%)")
    col5.metric("Concentracao", f"{df_cli.head(10)['%'].sum():.1f}%", help="Top 10 clientes")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("##### Top 10 Clientes")
        df_top = df_cli.head(10)
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=df_top['NOME_CLIENTE'].str[:25],
            x=df_top['VALOR_ORIGINAL'],
            orientation='h',
            marker_color=[cores['primaria'] if c == 'A' else cores['alerta'] if c == 'B' else cores['info'] for c in df_top['Classe']],
            text=[formatar_moeda(v) for v in df_top['VALOR_ORIGINAL']],
            textposition='outside',
            textfont=dict(size=9)
        ))
        fig.update_layout(
            criar_layout(320),
            yaxis={'autorange': 'reversed'},
            margin=dict(l=10, r=70, t=10, b=10)
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("##### Distribuicao ABC")
        fig = go.Figure(data=[go.Pie(
            labels=['Classe A', 'Classe B', 'Classe C'],
            values=[valor_a, valor_b, valor_c],
            hole=0.5,
            marker_colors=[cores['primaria'], cores['alerta'], cores['info']],
            textinfo='percent+label',
            textfont_size=11
        )])
        fig.update_layout(criar_layout(320), showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("Ver tabela completa de clientes"):
        df_show = df_cli.head(20).copy()
        df_show['Cliente'] = df_show['NOME_CLIENTE'].str[:35]
        df_show['Valor'] = df_show['VALOR_ORIGINAL'].apply(lambda x: formatar_moeda(x, completo=True))
        df_show['Saldo'] = df_show['SALDO'].apply(lambda x: formatar_moeda(x, completo=True))
        df_show['%'] = df_show['%'].apply(lambda x: f"{x:.2f}%")
        df_show['Acum.'] = df_show['Acum'].apply(lambda x: f"{x:.1f}%")
        st.dataframe(df_show[['Cliente', 'Valor', 'Saldo', '%', 'Acum.', 'Classe']], use_container_width=True, hide_index=True)


def _render_risco(df, cores, hoje):
    """Renderiza analise de risco e aging"""

    df_vencidos = get_df_vencidos(df)
    total_saldo = df['SALDO'].sum()
    total_vencido = df_vencidos['SALDO'].sum()
    inadimplencia = (total_vencido / total_saldo * 100) if total_saldo > 0 else 0
    aging_medio = df_vencidos['DIAS_ATRASO'].mean() if len(df_vencidos) > 0 else 0

    participacoes = df.groupby('NOME_CLIENTE')['VALOR_ORIGINAL'].sum() / df['VALOR_ORIGINAL'].sum()
    hhi = (participacoes ** 2).sum() * 10000

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Saldo Vencido", formatar_moeda(total_vencido))
    col2.metric(
        "Taxa Inadimplencia",
        f"{inadimplencia:.1f}%",
        delta="Critico" if inadimplencia > 25 else "Alto" if inadimplencia > 15 else "Normal",
        delta_color="inverse" if inadimplencia > 15 else "off"
    )
    col3.metric("Aging Medio", f"{aging_medio:.0f} dias")
    col4.metric("Titulos Vencidos", formatar_numero(len(df_vencidos)))
    col5.metric("Indice HHI", f"{hhi:.0f}", help="<1500: Baixa, 1500-2500: Media, >2500: Alta concentracao")

    st.markdown("---")

    st.markdown("##### Aging por Faixa de Atraso")

    def faixa_atraso(dias):
        if pd.isna(dias) or dias <= 0:
            return 'Em dia'
        elif dias <= 30:
            return '1-30 dias'
        elif dias <= 60:
            return '31-60 dias'
        elif dias <= 90:
            return '61-90 dias'
        return '90+ dias'

    df_r = df.copy()
    df_r['Faixa'] = df_r['DIAS_ATRASO'].apply(faixa_atraso)

    ordem = ['Em dia', '1-30 dias', '31-60 dias', '61-90 dias', '90+ dias']
    df_aging = df_r.groupby('Faixa').agg({
        'SALDO': 'sum',
        'VALOR_ORIGINAL': 'count'
    }).reindex(ordem, fill_value=0).reset_index()
    df_aging.columns = ['Faixa', 'Valor', 'Qtd']

    cores_faixas = [cores['sucesso'], cores['info'], cores['alerta'], '#ff6b35', cores['perigo']]

    col1, col2 = st.columns(2)

    with col1:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_aging['Faixa'],
            y=df_aging['Valor'],
            marker_color=cores_faixas,
            text=[formatar_moeda(v) for v in df_aging['Valor']],
            textposition='outside',
            textfont=dict(size=9)
        ))
        fig.update_layout(criar_layout(300), margin=dict(l=10, r=10, t=10, b=50))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        df_aging_exib = df_aging.copy()
        df_aging_exib['Valor'] = df_aging_exib['Valor'].apply(lambda x: formatar_moeda(x, completo=True))
        df_aging_exib['%'] = (df_r.groupby('Faixa')['SALDO'].sum() / total_saldo * 100).reindex(ordem, fill_value=0).apply(lambda x: f"{x:.1f}%").values
        st.dataframe(df_aging_exib, use_container_width=True, hide_index=True)

    st.markdown("---")

    st.markdown("##### Top 10 Clientes de Maior Risco")

    if len(df_vencidos) > 0:
        df_crit = df_vencidos.groupby('NOME_CLIENTE').agg({
            'SALDO': 'sum',
            'VALOR_ORIGINAL': 'count',
            'DIAS_ATRASO': ['mean', 'max']
        }).reset_index()
        df_crit.columns = ['Cliente', 'Saldo Vencido', 'Qtd', 'Atraso Medio', 'Atraso Max']
        df_crit = df_crit.sort_values('Saldo Vencido', ascending=False).head(10)

        max_saldo = df_crit['Saldo Vencido'].max() if df_crit['Saldo Vencido'].max() > 0 else 1
        max_atraso = df_crit['Atraso Max'].max() if df_crit['Atraso Max'].max() > 0 else 1
        df_crit['Score'] = (
            (df_crit['Saldo Vencido'] / max_saldo * 50) +
            (df_crit['Atraso Max'] / max_atraso * 50)
        ).round(0).astype(int)

        def get_nivel(score):
            if score >= 70:
                return 'Critico'
            elif score >= 40:
                return 'Alto'
            else:
                return 'Medio'

        df_crit['Risco'] = df_crit['Score'].apply(get_nivel)

        df_exib = df_crit.copy()
        df_exib['Cliente'] = df_exib['Cliente'].str[:30]
        df_exib['Saldo Vencido'] = df_exib['Saldo Vencido'].apply(lambda x: formatar_moeda(x, completo=True))
        df_exib['Atraso Medio'] = df_exib['Atraso Medio'].apply(lambda x: f"{x:.0f}d")
        df_exib['Atraso Max'] = df_exib['Atraso Max'].apply(lambda x: f"{x:.0f}d")

        st.dataframe(
            df_exib[['Cliente', 'Saldo Vencido', 'Qtd', 'Atraso Medio', 'Atraso Max', 'Score', 'Risco']],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.success("Nenhum titulo vencido!")


def _render_estatisticas(df, cores):
    """Renderiza estatisticas descritivas"""

    st.markdown("#### Estatisticas Descritivas")

    stats = df['VALOR_ORIGINAL'].describe()

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Minimo", formatar_moeda(stats['min']))
    col2.metric("Maximo", formatar_moeda(stats['max']))
    col3.metric("Media", formatar_moeda(stats['mean']))
    col4.metric("Mediana", formatar_moeda(stats['50%']))
    col5.metric("Desvio Padrao", formatar_moeda(stats['std']))

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Distribuicao de Valores")
        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=df['VALOR_ORIGINAL'],
            nbinsx=30,
            marker_color=cores['primaria'],
            opacity=0.8
        ))
        fig.add_vline(x=stats['mean'], line_dash="dash", line_color=cores['alerta'],
                      annotation_text=f"Media: {formatar_moeda(stats['mean'])}")
        fig.update_layout(
            criar_layout(300),
            xaxis_title='Valor (R$)',
            yaxis_title='Frequencia',
            margin=dict(l=50, r=10, t=10, b=40)
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("##### Box Plot por Status")
        fig = go.Figure()
        for status in df['STATUS'].dropna().unique():
            df_st = df[df['STATUS'] == status]
            fig.add_trace(go.Box(
                y=df_st['VALOR_ORIGINAL'],
                name=status[:12],
                boxpoints='outliers'
            ))
        fig.update_layout(
            criar_layout(300),
            showlegend=False,
            yaxis_title='Valor (R$)',
            margin=dict(l=50, r=10, t=10, b=30)
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    st.markdown("##### Distribuicao por Faixa de Valor")

    def faixa_valor(v):
        if v <= 1000:
            return 'Ate R$ 1K'
        elif v <= 5000:
            return 'R$ 1K - 5K'
        elif v <= 10000:
            return 'R$ 5K - 10K'
        elif v <= 50000:
            return 'R$ 10K - 50K'
        elif v <= 100000:
            return 'R$ 50K - 100K'
        return 'Acima de R$ 100K'

    df_fx = df.copy()
    df_fx['Faixa'] = df_fx['VALOR_ORIGINAL'].apply(faixa_valor)

    ordem = ['Ate R$ 1K', 'R$ 1K - 5K', 'R$ 5K - 10K', 'R$ 10K - 50K', 'R$ 50K - 100K', 'Acima de R$ 100K']
    df_faixas = df_fx.groupby('Faixa').agg({
        'VALOR_ORIGINAL': ['count', 'sum']
    }).reindex(ordem).reset_index()
    df_faixas.columns = ['Faixa', 'Qtd', 'Total']
    df_faixas = df_faixas.dropna()

    col1, col2 = st.columns(2)

    with col1:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_faixas['Faixa'],
            y=df_faixas['Qtd'],
            marker_color=cores['info'],
            text=df_faixas['Qtd'],
            textposition='outside'
        ))
        fig.update_layout(criar_layout(280), xaxis_tickangle=-30, margin=dict(l=10, r=10, t=10, b=80))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_faixas['Faixa'],
            y=df_faixas['Total'],
            marker_color=cores['alerta'],
            text=[formatar_moeda(v) for v in df_faixas['Total']],
            textposition='outside',
            textfont=dict(size=9)
        ))
        fig.update_layout(criar_layout(280), xaxis_tickangle=-30, margin=dict(l=10, r=10, t=10, b=80))
        st.plotly_chart(fig, use_container_width=True)

    df_faixas_exib = df_faixas.copy()
    df_faixas_exib['Total'] = df_faixas_exib['Total'].apply(lambda x: formatar_moeda(x, completo=True))
    df_faixas_exib['%'] = (df_fx.groupby('Faixa')['VALOR_ORIGINAL'].count().reindex(ordem) / len(df) * 100).apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "0%").values
    st.dataframe(df_faixas_exib, use_container_width=True, hide_index=True)
