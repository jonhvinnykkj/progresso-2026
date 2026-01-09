"""
Aba Categorias - Analise completa por categoria com comportamento de pagamento
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from config.theme import get_cores
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero
from utils.data_helpers import get_df_pendentes, get_df_vencidos


def render_categorias(df):
    """Renderiza a aba de Categorias"""
    cores = get_cores()

    if len(df) == 0:
        st.warning("Nenhum dado disponivel.")
        return

    # Calcular dataframes
    df_pendentes = get_df_pendentes(df)
    df_vencidos = get_df_vencidos(df)
    df_pagos = df[df['SALDO'] == 0].copy()

    # Dados agregados por categoria
    df_cat = _preparar_dados_categoria(df, df_pagos)

    # ========== KPIs ==========
    _render_kpis(df_cat, df, df_pagos, df_vencidos, cores)

    st.divider()

    # ========== LINHA 1: Distribuicao ==========
    col1, col2 = st.columns(2)

    with col1:
        _render_treemap(df_cat, cores)

    with col2:
        _render_donut(df_cat, cores)

    st.divider()

    # ========== LINHA 2: Comportamento de Pagamento ==========
    col1, col2 = st.columns(2)

    with col1:
        _render_prazo_por_categoria(df_pagos, cores)

    with col2:
        _render_pontualidade_por_categoria(df_pagos, cores)

    st.divider()

    # ========== LINHA 3: Valor e Vencidos ==========
    col1, col2 = st.columns(2)

    with col1:
        _render_top_categorias(df_cat, cores)

    with col2:
        _render_vencidos_por_categoria(df_vencidos, cores)

    st.divider()

    # ========== BUSCA CATEGORIA ==========
    _render_busca_categoria(df, df_pagos, df_vencidos, cores)

    st.divider()

    # ========== RANKING ==========
    _render_ranking(df_cat, df_pagos, cores)


def _preparar_dados_categoria(df, df_pagos):
    """Prepara dados agregados por categoria"""

    df_cat = df.groupby('DESCRICAO').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'FORNECEDOR': 'count',
        'NOME_FORNECEDOR': 'nunique',
        'NOME_FILIAL': 'nunique'
    }).reset_index()

    df_cat.columns = ['Categoria', 'Total', 'Pendente', 'Qtd', 'Fornecedores', 'Filiais']
    df_cat['Pago'] = df_cat['Total'] - df_cat['Pendente']
    df_cat['Pct_Pago'] = (df_cat['Pago'] / df_cat['Total'] * 100).fillna(0).round(1)
    df_cat = df_cat.sort_values('Total', ascending=False)

    return df_cat


def _render_kpis(df_cat, df, df_pagos, df_vencidos, cores):
    """KPIs principais"""

    total_categorias = len(df_cat)
    total_valor = df_cat['Total'].sum()
    total_vencido = df_vencidos['SALDO'].sum() if len(df_vencidos) > 0 else 0

    # Taxa pontualidade geral
    taxa_pontual = 0
    if len(df_pagos) > 0 and 'DIAS_ATRASO_PGTO' in df_pagos.columns:
        atraso = df_pagos['DIAS_ATRASO_PGTO'].dropna()
        if len(atraso) > 0:
            taxa_pontual = (atraso <= 0).sum() / len(atraso) * 100

    # Prazo medio geral
    prazo_medio = 0
    if len(df_pagos) > 0 and 'DIAS_PARA_PAGAR' in df_pagos.columns:
        prazo = df_pagos['DIAS_PARA_PAGAR'].dropna()
        if len(prazo) > 0:
            prazo_medio = prazo.mean()

    # Categorias com vencido
    cat_com_vencido = df_vencidos['DESCRICAO'].nunique() if len(df_vencidos) > 0 else 0

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            label="Total Categorias",
            value=formatar_numero(total_categorias),
            delta=f"{formatar_numero(df_cat['Qtd'].sum())} titulos",
            delta_color="off"
        )

    with col2:
        st.metric(
            label="Valor Total",
            value=formatar_moeda(total_valor),
            delta=f"Vencido: {formatar_moeda(total_vencido)}",
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
            label="Prazo Medio Pgto",
            value=f"{prazo_medio:.0f} dias",
            delta="emissao ate pagamento",
            delta_color="off"
        )

    with col5:
        pct = (cat_com_vencido / total_categorias * 100) if total_categorias > 0 else 0
        st.metric(
            label="Cat. com Vencido",
            value=formatar_numero(cat_com_vencido),
            delta=f"{pct:.0f}% do total",
            delta_color="off"
        )


def _render_treemap(df_cat, cores):
    """Treemap de categorias"""

    st.markdown("##### Treemap - Distribuicao")

    df_tree = df_cat.head(15).copy()

    if len(df_tree) == 0:
        st.info("Sem dados")
        return

    fig = px.treemap(
        df_tree,
        path=['Categoria'],
        values='Total',
        color='Pct_Pago',
        color_continuous_scale='RdYlGn',
        hover_data={'Total': ':,.2f', 'Pendente': ':,.2f', 'Pct_Pago': ':.1f'}
    )

    fig.update_layout(
        criar_layout(300),
        coloraxis_colorbar=dict(title="% Pago", len=0.6),
        margin=dict(l=10, r=10, t=10, b=10)
    )

    fig.update_traces(
        textinfo='label+value',
        texttemplate='%{label}<br>R$ %{value:,.0f}',
        textfont=dict(size=11)
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_donut(df_cat, cores):
    """Donut das top 8 categorias"""

    st.markdown("##### Top 8 Categorias")

    df_top = df_cat.head(8).copy()
    outros = df_cat.iloc[8:]['Total'].sum() if len(df_cat) > 8 else 0

    if outros > 0:
        df_top = pd.concat([df_top, pd.DataFrame([{
            'Categoria': 'Outros',
            'Total': outros
        }])], ignore_index=True)

    if len(df_top) == 0:
        st.info("Sem dados")
        return

    fig = go.Figure(go.Pie(
        labels=df_top['Categoria'].str[:20],
        values=df_top['Total'],
        hole=0.5,
        textinfo='percent',
        textfont=dict(size=10),
        hovertemplate='<b>%{label}</b><br>R$ %{value:,.2f}<br>%{percent}<extra></extra>'
    ))

    total = df_cat['Total'].sum()
    fig.add_annotation(
        text=f"<b>{formatar_moeda(total)}</b>",
        x=0.5, y=0.5,
        font=dict(size=14, color=cores['texto']),
        showarrow=False
    )

    fig.update_layout(
        criar_layout(300),
        showlegend=True,
        legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02, font=dict(size=9)),
        margin=dict(l=10, r=100, t=10, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_prazo_por_categoria(df_pagos, cores):
    """Prazo medio por categoria"""

    st.markdown("##### Prazo Medio por Categoria")

    if len(df_pagos) == 0 or 'DIAS_PARA_PAGAR' not in df_pagos.columns:
        st.info("Sem dados de pagamento")
        return

    df_prazo = df_pagos.groupby('DESCRICAO').agg({
        'DIAS_PARA_PAGAR': 'mean',
        'VALOR_ORIGINAL': 'sum'
    }).reset_index()
    df_prazo.columns = ['Categoria', 'Prazo', 'Valor']
    df_prazo = df_prazo.dropna(subset=['Prazo'])

    # Top 10 com maior prazo
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
        y=df_top['Categoria'].str[:25],
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
    st.caption("Categorias com maior prazo de pagamento")


def _render_pontualidade_por_categoria(df_pagos, cores):
    """Pontualidade por categoria"""

    st.markdown("##### Pontualidade por Categoria")

    if len(df_pagos) == 0 or 'DIAS_ATRASO_PGTO' not in df_pagos.columns:
        st.info("Sem dados de pagamento")
        return

    def calc_pontualidade(group):
        atraso = group['DIAS_ATRASO_PGTO'].dropna()
        if len(atraso) < 5:  # Minimo 5 para ser estatisticamente relevante
            return pd.Series({'Pontualidade': None, 'Qtd': len(atraso)})
        pontual = (atraso <= 0).sum() / len(atraso) * 100
        return pd.Series({'Pontualidade': pontual, 'Qtd': len(atraso)})

    df_pont = df_pagos.groupby('DESCRICAO').apply(calc_pontualidade).reset_index()
    df_pont = df_pont.dropna(subset=['Pontualidade'])

    if len(df_pont) == 0:
        st.info("Dados insuficientes (min. 5 pagamentos)")
        return

    # Top 10 com pior pontualidade
    df_piores = df_pont.nsmallest(10, 'Pontualidade')

    def cor_pont(p):
        if p >= 80:
            return cores['sucesso']
        elif p >= 60:
            return cores['info']
        elif p >= 40:
            return cores['alerta']
        return cores['perigo']

    bar_colors = [cor_pont(p) for p in df_piores['Pontualidade']]

    fig = go.Figure(go.Bar(
        y=df_piores['DESCRICAO'].str[:25],
        x=df_piores['Pontualidade'],
        orientation='h',
        marker_color=bar_colors,
        text=[f"{p:.0f}%" for p in df_piores['Pontualidade']],
        textposition='outside',
        textfont=dict(size=10)
    ))

    fig.update_layout(
        criar_layout(300),
        yaxis={'autorange': 'reversed'},
        margin=dict(l=10, r=50, t=10, b=10),
        xaxis_title='% Pontualidade',
        xaxis=dict(range=[0, 105])
    )

    st.plotly_chart(fig, use_container_width=True)
    st.caption("Categorias com pior pontualidade (min. 5 pagamentos)")


def _render_top_categorias(df_cat, cores):
    """Top 10 categorias - Pago vs Pendente"""

    st.markdown("##### Top 10 - Pago vs Pendente")

    df_top = df_cat.head(10)

    if len(df_top) == 0:
        st.info("Sem dados")
        return

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=df_top['Categoria'].str[:25],
        x=df_top['Pago'],
        orientation='h',
        name='Pago',
        marker_color=cores['sucesso'],
        text=[formatar_moeda(v) for v in df_top['Pago']],
        textposition='inside',
        textfont=dict(size=9, color='white')
    ))

    fig.add_trace(go.Bar(
        y=df_top['Categoria'].str[:25],
        x=df_top['Pendente'],
        orientation='h',
        name='Pendente',
        marker_color=cores['alerta'],
        text=[formatar_moeda(v) for v in df_top['Pendente']],
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


def _render_vencidos_por_categoria(df_vencidos, cores):
    """Vencidos por categoria"""

    st.markdown("##### Vencidos por Categoria")

    if len(df_vencidos) == 0:
        st.success("Nenhum titulo vencido!")
        return

    df_venc = df_vencidos.groupby('DESCRICAO').agg({
        'SALDO': 'sum',
        'DIAS_ATRASO': 'mean',
        'VALOR_ORIGINAL': 'count'
    }).nlargest(10, 'SALDO').reset_index()
    df_venc.columns = ['Categoria', 'Valor', 'Atraso_Medio', 'Qtd']

    def cor_atraso(d):
        if d > 30:
            return cores['perigo']
        elif d > 15:
            return '#f97316'
        return cores['alerta']

    bar_colors = [cor_atraso(d) for d in df_venc['Atraso_Medio']]

    fig = go.Figure(go.Bar(
        y=df_venc['Categoria'].str[:25],
        x=df_venc['Valor'],
        orientation='h',
        marker_color=bar_colors,
        text=[f"{formatar_moeda(v)} ({d:.0f}d)" for v, d in zip(df_venc['Valor'], df_venc['Atraso_Medio'])],
        textposition='outside',
        textfont=dict(size=9)
    ))

    fig.update_layout(
        criar_layout(300),
        yaxis={'autorange': 'reversed'},
        margin=dict(l=10, r=80, t=10, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)
    st.caption("Cor indica atraso medio (amarelo < 15d, laranja < 30d, vermelho > 30d)")


def _render_busca_categoria(df, df_pagos, df_vencidos, cores):
    """Busca e detalhes de categoria"""

    st.markdown("##### Consultar Categoria")

    categorias = sorted(df['DESCRICAO'].unique().tolist())

    categoria_sel = st.selectbox(
        "Selecione uma categoria",
        options=[""] + categorias,
        key="busca_cat"
    )

    if not categoria_sel:
        return

    df_sel = df[df['DESCRICAO'] == categoria_sel]
    df_pago_sel = df_pagos[df_pagos['DESCRICAO'] == categoria_sel]
    df_venc_sel = df_vencidos[df_vencidos['DESCRICAO'] == categoria_sel]

    # Metricas financeiras
    total_valor = df_sel['VALOR_ORIGINAL'].sum()
    total_pendente = df_sel['SALDO'].sum()
    total_pago = total_valor - total_pendente
    total_vencido = df_venc_sel['SALDO'].sum() if len(df_venc_sel) > 0 else 0

    # Metricas de pagamento
    prazo_medio = 0
    taxa_pontual = 0
    if len(df_pago_sel) > 0:
        if 'DIAS_PARA_PAGAR' in df_pago_sel.columns:
            prazo = df_pago_sel['DIAS_PARA_PAGAR'].dropna()
            if len(prazo) > 0:
                prazo_medio = prazo.mean()

        if 'DIAS_ATRASO_PGTO' in df_pago_sel.columns:
            atraso = df_pago_sel['DIAS_ATRASO_PGTO'].dropna()
            if len(atraso) > 0:
                taxa_pontual = (atraso <= 0).sum() / len(atraso) * 100

    # Linha 1: Metricas financeiras
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Valor Total", formatar_moeda(total_valor), f"{len(df_sel)} titulos")
    col2.metric("Pago", formatar_moeda(total_pago))
    col3.metric("Pendente", formatar_moeda(total_pendente))
    col4.metric("Vencido", formatar_moeda(total_vencido))

    # Linha 2: Metricas de comportamento
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Prazo Medio Pgto", f"{prazo_medio:.0f} dias")
    col2.metric("Taxa Pontualidade", f"{taxa_pontual:.1f}%")
    col3.metric("Fornecedores", df_sel['NOME_FORNECEDOR'].nunique())
    col4.metric("Filiais", df_sel['NOME_FILIAL'].nunique())

    # Tabs
    tab1, tab2, tab3 = st.tabs(["Por Fornecedor", "Por Filial", "Titulos"])

    with tab1:
        df_forn = df_sel.groupby('NOME_FORNECEDOR').agg({
            'VALOR_ORIGINAL': 'sum',
            'SALDO': 'sum'
        }).nlargest(10, 'VALOR_ORIGINAL').reset_index()

        if len(df_forn) > 0:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                y=df_forn['NOME_FORNECEDOR'].str[:20],
                x=df_forn['VALOR_ORIGINAL'] - df_forn['SALDO'],
                orientation='h',
                name='Pago',
                marker_color=cores['sucesso']
            ))
            fig.add_trace(go.Bar(
                y=df_forn['NOME_FORNECEDOR'].str[:20],
                x=df_forn['SALDO'],
                orientation='h',
                name='Pendente',
                marker_color=cores['alerta']
            ))
            fig.update_layout(
                criar_layout(250, barmode='stack'),
                yaxis={'autorange': 'reversed'},
                margin=dict(l=10, r=10, t=10, b=10)
            )
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        df_fil = df_sel.groupby('NOME_FILIAL').agg({
            'VALOR_ORIGINAL': 'sum',
            'SALDO': 'sum'
        }).reset_index()

        if len(df_fil) > 0:
            fig = go.Figure(go.Pie(
                labels=df_fil['NOME_FILIAL'],
                values=df_fil['VALOR_ORIGINAL'],
                hole=0.4,
                textinfo='percent+label',
                textfont=dict(size=10)
            ))
            fig.update_layout(
                criar_layout(250),
                showlegend=False,
                margin=dict(l=10, r=10, t=10, b=10)
            )
            st.plotly_chart(fig, use_container_width=True)

    with tab3:
        colunas = ['NOME_FILIAL', 'NOME_FORNECEDOR', 'EMISSAO', 'VENCIMENTO', 'DT_BAIXA', 'DIAS_PARA_PAGAR', 'VALOR_ORIGINAL', 'SALDO', 'STATUS']
        colunas_disp = [c for c in colunas if c in df_sel.columns]
        df_tab = df_sel[colunas_disp].nlargest(50, 'VALOR_ORIGINAL').copy()

        for col in ['EMISSAO', 'VENCIMENTO', 'DT_BAIXA']:
            if col in df_tab.columns:
                df_tab[col] = pd.to_datetime(df_tab[col], errors='coerce').dt.strftime('%d/%m/%Y')
                df_tab[col] = df_tab[col].fillna('-')

        df_tab['VALOR_ORIGINAL'] = df_tab['VALOR_ORIGINAL'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab['SALDO'] = df_tab['SALDO'].apply(lambda x: formatar_moeda(x, completo=True))

        if 'DIAS_PARA_PAGAR' in df_tab.columns:
            df_tab['DIAS_PARA_PAGAR'] = df_tab['DIAS_PARA_PAGAR'].apply(lambda x: f"{int(x)}d" if pd.notna(x) else '-')

        nomes = {
            'NOME_FILIAL': 'Filial',
            'NOME_FORNECEDOR': 'Fornecedor',
            'EMISSAO': 'Emissao',
            'VENCIMENTO': 'Vencimento',
            'DT_BAIXA': 'Dt Pagto',
            'DIAS_PARA_PAGAR': 'Dias p/ Pagar',
            'VALOR_ORIGINAL': 'Valor',
            'SALDO': 'Saldo',
            'STATUS': 'Status'
        }
        df_tab.columns = [nomes.get(c, c) for c in df_tab.columns]

        st.dataframe(df_tab, use_container_width=True, hide_index=True, height=300)


def _render_ranking(df_cat, df_pagos, cores):
    """Ranking completo"""

    st.markdown("##### Ranking de Categorias")

    # Filtros
    col1, col2, col3 = st.columns(3)
    with col1:
        ordenar = st.selectbox(
            "Ordenar por",
            ["Valor Total", "Saldo Pendente", "Prazo Medio", "Pontualidade"],
            key="cat_ordem"
        )
    with col2:
        qtd_exibir = st.selectbox("Exibir", [15, 30, 50], key="cat_qtd")
    with col3:
        filtro = st.selectbox("Filtrar", ["Todas", "Com Pendencia", "Quitadas"], key="cat_filtro")

    # Adicionar metricas de pagamento
    df_rank = df_cat.copy()

    if len(df_pagos) > 0:
        def calc_metricas(cat):
            df_c = df_pagos[df_pagos['DESCRICAO'] == cat]
            if len(df_c) == 0:
                return pd.Series({'Prazo': None, 'Pontualidade': None})

            prazo = None
            pont = None

            if 'DIAS_PARA_PAGAR' in df_c.columns:
                p = df_c['DIAS_PARA_PAGAR'].dropna()
                if len(p) > 0:
                    prazo = p.mean()

            if 'DIAS_ATRASO_PGTO' in df_c.columns:
                a = df_c['DIAS_ATRASO_PGTO'].dropna()
                if len(a) > 0:
                    pont = (a <= 0).sum() / len(a) * 100

            return pd.Series({'Prazo': prazo, 'Pontualidade': pont})

        metricas = df_rank['Categoria'].apply(calc_metricas)
        df_rank = pd.concat([df_rank, metricas], axis=1)
    else:
        df_rank['Prazo'] = None
        df_rank['Pontualidade'] = None

    # Filtrar
    if filtro == "Com Pendencia":
        df_rank = df_rank[df_rank['Pendente'] > 0]
    elif filtro == "Quitadas":
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

    # Formatar
    df_show = df_rank[['Categoria', 'Total', 'Pendente', 'Qtd', 'Fornecedores', 'Prazo', 'Pontualidade', 'Pct_Pago']].copy()
    df_show['Total'] = df_show['Total'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Pendente'] = df_show['Pendente'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Prazo'] = df_show['Prazo'].apply(lambda x: f"{x:.0f}d" if pd.notna(x) else '-')
    df_show['Pontualidade'] = df_show['Pontualidade'].apply(lambda x: f"{x:.0f}%" if pd.notna(x) else '-')
    df_show.columns = ['Categoria', 'Total', 'Pendente', 'Titulos', 'Fornecedores', 'Prazo', 'Pontualidade', '% Pago']

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

    st.caption(f"Exibindo {len(df_show)} categorias")
