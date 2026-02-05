"""
Aba Tipo Documento - Analise por tipo de documento (NF, RA, NCC, etc.)
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

from config.theme import get_cores
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero


# Descricao dos tipos de documento
TIPOS_DESC = {
    'NF': 'Nota Fiscal',
    'NFE': 'Nota Fiscal Eletronica',
    'NFSE': 'NF de Servico',
    'RA': 'Recibo de Adiantamento',
    'NCC': 'Nota de Credito ao Cliente',
    'RC': 'Recibo',
    'FT': 'Fatura',
    'FAT': 'Faturamento (excluido)',
    'PR': 'Provisao',
    'OP': 'Ordem de Pagamento',
    'NCF': 'Nota de Credito Fornecedor',
    'TX': 'Taxa',
    'CF-': 'COFINS',
    'CS-': 'CSLL',
    'IR-': 'Imposto de Renda',
    'PI-': 'PIS',
    'PIS': 'PIS',
    'COF': 'COFINS'
}


def render_tipo_documento(df):
    """Renderiza a aba de Tipo de Documento"""
    cores = get_cores()

    if len(df) == 0:
        st.warning("Nenhum dado disponivel.")
        return

    if 'TIPO' not in df.columns:
        st.warning("Coluna TIPO nao encontrada.")
        return

    df = df.copy()

    # Preparar dados
    df_pendentes = df[df['SALDO'] > 0]
    df_recebidos = df[df['SALDO'] == 0]
    df_vencidos = df[df['STATUS'] == 'Vencido']

    # ========== KPIs ==========
    total_tipos = df['TIPO'].nunique()
    tipo_mais_comum = df['TIPO'].value_counts().idxmax()
    pct_tipo_top = df['TIPO'].value_counts().iloc[0] / len(df) * 100
    total_valor = df['VALOR_ORIGINAL'].sum()
    total_pendente = df_pendentes['SALDO'].sum()

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Tipos de Documento", total_tipos)
    col2.metric("Tipo Mais Comum", tipo_mais_comum, f"{pct_tipo_top:.1f}%")
    col3.metric("Valor Total", formatar_moeda(total_valor))
    col4.metric("Pendente", formatar_moeda(total_pendente))
    col5.metric("Titulos Vencidos", formatar_numero(len(df_vencidos)))

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
        _render_status_por_tipo(df, cores)

    with col2:
        _render_vencidos_por_tipo(df_vencidos, cores)

    st.divider()

    # ========== CATEGORIAS POR TIPO ==========
    _render_categorias_por_tipo(df, cores)

    st.divider()

    # ========== TABELA DETALHADA ==========
    _render_tabela_tipos(df, df_pendentes, df_vencidos, cores)


def _render_distribuicao_valor(df, cores):
    """Distribuicao por valor"""
    st.markdown("##### Distribuicao por Valor")

    df_grp = df.groupby('TIPO').agg({
        'VALOR_ORIGINAL': 'sum'
    }).sort_values('VALOR_ORIGINAL', ascending=False).reset_index()

    # Adicionar descricao
    df_grp['DESC'] = df_grp['TIPO'].map(lambda x: f"{x} - {TIPOS_DESC.get(x, x)}")

    cores_grafico = [cores['sucesso'], cores['info'], cores['primaria'], cores['alerta'],
                    '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1']

    fig = go.Figure(go.Pie(
        labels=df_grp['DESC'],
        values=df_grp['VALOR_ORIGINAL'],
        hole=0.5,
        marker=dict(colors=cores_grafico[:len(df_grp)]),
        textinfo='percent',
        textfont=dict(size=10),
        hovertemplate='<b>%{label}</b><br>R$ %{value:,.2f}<br>%{percent}<extra></extra>'
    ))

    fig.update_layout(
        criar_layout(300),
        showlegend=True,
        legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02, font=dict(size=9)),
        margin=dict(l=10, r=150, t=10, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_distribuicao_quantidade(df, cores):
    """Distribuicao por quantidade"""
    st.markdown("##### Distribuicao por Quantidade")

    df_grp = df.groupby('TIPO').size().sort_values(ascending=False).reset_index()
    df_grp.columns = ['Tipo', 'Qtd']

    # Adicionar descricao
    df_grp['Label'] = df_grp['Tipo'].map(lambda x: f"{x}")

    fig = go.Figure(go.Bar(
        x=df_grp['Label'],
        y=df_grp['Qtd'],
        marker_color=cores['sucesso'],
        text=df_grp['Qtd'],
        textposition='outside',
        textfont=dict(size=9),
        hovertemplate='<b>%{x}</b><br>Quantidade: %{y}<extra></extra>'
    ))

    fig.update_layout(
        criar_layout(300),
        xaxis_tickangle=-45,
        margin=dict(l=10, r=10, t=10, b=80)
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_status_por_tipo(df, cores):
    """Status por tipo de documento - barras horizontais proporcionais"""
    st.markdown("##### Status por Tipo")

    # Top 8 tipos por valor
    tipos = df.groupby('TIPO')['VALOR_ORIGINAL'].sum().nlargest(8).index.tolist()
    df_filtrado = df[df['TIPO'].isin(tipos)]

    if len(df_filtrado) == 0:
        st.info("Sem dados")
        return

    # Simplificar status para 3 grupos
    def agrupar_status(s):
        if s == 'Recebido':
            return 'Recebido'
        elif s == 'Vencido':
            return 'Vencido'
        return 'A Vencer'

    df_filtrado = df_filtrado.copy()
    df_filtrado['STATUS_GRUPO'] = df_filtrado['STATUS'].apply(agrupar_status)

    # Pivot: tipo x status_grupo
    pivot = df_filtrado.pivot_table(
        values='VALOR_ORIGINAL', index='TIPO', columns='STATUS_GRUPO',
        aggfunc='sum', fill_value=0
    )

    # Ordenar por total
    pivot['_total'] = pivot.sum(axis=1)
    pivot = pivot.sort_values('_total', ascending=True)
    pivot = pivot.drop(columns='_total')

    # Calcular percentuais
    totais = pivot.sum(axis=1)
    pivot_pct = pivot.div(totais, axis=0) * 100

    ordem_status = ['Recebido', 'A Vencer', 'Vencido']
    cores_status = {
        'Recebido': cores['sucesso'],
        'A Vencer': cores['info'],
        'Vencido': cores['perigo']
    }

    fig = go.Figure()

    for status in ordem_status:
        if status not in pivot_pct.columns:
            continue
        fig.add_trace(go.Bar(
            y=pivot.index,
            x=pivot_pct[status],
            orientation='h',
            name=status,
            marker_color=cores_status[status],
            text=[f"{p:.0f}%" if p >= 8 else '' for p in pivot_pct[status]],
            textposition='inside',
            textfont=dict(size=10, color='white'),
            customdata=[formatar_moeda(v) for v in pivot[status]],
            hovertemplate='<b>%{y}</b> - ' + status + '<br>%{customdata} (%{x:.1f}%)<extra></extra>'
        ))

    fig.update_layout(
        criar_layout(300, barmode='stack'),
        xaxis=dict(showticklabels=False, showgrid=False, range=[0, 100]),
        yaxis=dict(tickfont=dict(size=10, color=cores['texto'])),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
                    font=dict(size=10, color=cores['texto'])),
        margin=dict(l=10, r=10, t=35, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_vencidos_por_tipo(df_vencidos, cores):
    """Vencidos por tipo"""
    st.markdown("##### Valor Vencido por Tipo")

    if len(df_vencidos) == 0:
        st.success("Sem titulos vencidos!")
        return

    df_grp = df_vencidos.groupby('TIPO').agg({
        'SALDO': 'sum',
        'VALOR_ORIGINAL': 'count'
    }).sort_values('SALDO', ascending=False).head(8).reset_index()
    df_grp.columns = ['Tipo', 'Saldo', 'Qtd']

    fig = go.Figure(go.Bar(
        y=df_grp['Tipo'],
        x=df_grp['Saldo'],
        orientation='h',
        marker_color=cores['perigo'],
        text=[f"{formatar_moeda(v)} ({q})" for v, q in zip(df_grp['Saldo'], df_grp['Qtd'])],
        textposition='outside',
        textfont=dict(size=9)
    ))

    fig.update_layout(
        criar_layout(300),
        yaxis={'autorange': 'reversed'},
        margin=dict(l=10, r=100, t=10, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_categorias_por_tipo(df, cores):
    """Quantidade de documentos por categoria para cada tipo"""
    st.markdown("##### Categorias por Tipo de Documento")

    if 'DESCRICAO' not in df.columns:
        st.info("Coluna de categoria nao disponivel.")
        return

    tipos_disp = df['TIPO'].value_counts().index.tolist()
    tipo_sel = st.selectbox("Selecione o tipo de documento", tipos_disp, key='tipo_doc_rec_cat')

    df_tipo = df[df['TIPO'] == tipo_sel]

    if len(df_tipo) == 0:
        st.info(f"Nenhum titulo do tipo {tipo_sel}.")
        return

    # Agrupar por categoria
    df_cat = df_tipo.groupby('DESCRICAO').agg({
        'VALOR_ORIGINAL': ['count', 'sum'],
        'SALDO': 'sum'
    }).reset_index()
    df_cat.columns = ['Categoria', 'Qtd', 'Valor Total', 'Pendente']
    df_cat['Recebido'] = (df_cat['Valor Total'] - df_cat['Pendente']).clip(lower=0)
    df_cat = df_cat.sort_values('Qtd', ascending=False)

    col1, col2 = st.columns(2)

    with col1:
        # Grafico top 10 por quantidade
        df_top = df_cat.head(10).sort_values('Qtd', ascending=True)

        fig = go.Figure(go.Bar(
            y=df_top['Categoria'].str[:25],
            x=df_top['Qtd'],
            orientation='h',
            marker_color=cores['sucesso'],
            text=df_top['Qtd'],
            textposition='outside',
            textfont=dict(size=9, color=cores['texto'])
        ))

        fig.update_layout(
            criar_layout(320),
            margin=dict(l=10, r=40, t=10, b=10),
            xaxis=dict(showticklabels=False, showgrid=False),
            yaxis=dict(tickfont=dict(size=9, color=cores['texto'])),
            showlegend=False
        )

        st.markdown(f"###### Top 10 Categorias - {tipo_sel} (por quantidade)")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Tabela completa
        st.markdown(f"###### Todas as Categorias - {tipo_sel}")
        df_show = df_cat.copy()
        df_show['Valor Total'] = df_show['Valor Total'].apply(lambda x: formatar_moeda(x, completo=True))
        df_show['Recebido'] = df_show['Recebido'].apply(lambda x: formatar_moeda(x, completo=True))
        df_show['Pendente'] = df_show['Pendente'].apply(lambda x: formatar_moeda(x, completo=True))

        st.dataframe(df_show, use_container_width=True, hide_index=True, height=320)
        st.caption(f"{len(df_cat)} categorias no tipo {tipo_sel} | {formatar_numero(len(df_tipo))} titulos")


def _render_tabela_tipos(df, df_pendentes, df_vencidos, cores):
    """Tabela resumo por tipo de documento"""
    st.markdown("##### Resumo por Tipo de Documento")

    # Agrupar dados
    df_grp = df.groupby('TIPO').agg({
        'VALOR_ORIGINAL': ['count', 'sum'],
        'SALDO': 'sum'
    }).reset_index()
    df_grp.columns = ['Tipo', 'Qtd', 'Total', 'Saldo']

    # Calcular vencidos
    df_venc_grp = df_vencidos.groupby('TIPO')['SALDO'].sum().reset_index()
    df_venc_grp.columns = ['Tipo', 'Vencido']
    df_grp = df_grp.merge(df_venc_grp, on='Tipo', how='left')
    df_grp['Vencido'] = df_grp['Vencido'].fillna(0)

    # Calcular recebidos
    df_rec = df[df['SALDO'] == 0].groupby('TIPO')['VALOR_ORIGINAL'].sum().reset_index()
    df_rec.columns = ['Tipo', 'Recebido']
    df_grp = df_grp.merge(df_rec, on='Tipo', how='left')
    df_grp['Recebido'] = df_grp['Recebido'].fillna(0)

    # Taxa de recebimento
    df_grp['Taxa_Receb'] = (df_grp['Recebido'] / df_grp['Total'] * 100).round(1)

    # Ordenar
    df_grp = df_grp.sort_values('Total', ascending=False)

    # Adicionar descricao
    df_grp['Descricao'] = df_grp['Tipo'].map(lambda x: TIPOS_DESC.get(x, '-'))

    # Formatar
    df_show = df_grp.copy()
    df_show['Total'] = df_show['Total'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Saldo'] = df_show['Saldo'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Vencido'] = df_show['Vencido'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Recebido'] = df_show['Recebido'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Taxa_Receb'] = df_show['Taxa_Receb'].apply(lambda x: f"{x:.1f}%")

    # Renomear
    df_show = df_show[['Tipo', 'Descricao', 'Qtd', 'Total', 'Recebido', 'Saldo', 'Vencido', 'Taxa_Receb']]
    df_show.columns = ['Tipo', 'Descricao', 'Qtd', 'Valor Total', 'Recebido', 'Saldo Pendente', 'Valor Vencido', '% Recebido']

    st.dataframe(
        df_show,
        use_container_width=True,
        hide_index=True,
        height=400
    )

    st.caption(f"Total: {len(df_show)} tipos de documento")
