"""
Aba Categorias - Análise completa por categoria de despesa
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from config.theme import get_cores
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero


def render_categorias(df):
    """Renderiza a aba de Categorias"""
    cores = get_cores()

    if len(df) == 0:
        st.warning("Nenhum dado disponível para o período selecionado.")
        return

    # Preparar dados base
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

    # KPIs
    _render_kpis_categorias(df_cat, df, cores)

    st.divider()

    # Linha 1: Treemap + Donut
    col1, col2 = st.columns(2)

    with col1:
        _render_treemap(df_cat, cores)

    with col2:
        _render_donut_categorias(df_cat, cores)

    st.divider()

    # Linha 2: Top Categorias + Evolução
    col1, col2 = st.columns(2)

    with col1:
        _render_top_categorias(df_cat, cores)

    with col2:
        _render_evolucao_categorias(df, cores)

    st.divider()

    # Consulta de categoria específica
    _render_detalhe_categoria(df, df_cat, cores)

    st.divider()

    # Ranking completo
    _render_ranking_categorias(df_cat, cores)


def _render_kpis_categorias(df_cat, df, cores):
    """KPIs de resumo de categorias"""

    total_categorias = len(df_cat)
    total_valor = df_cat['Total'].sum()
    total_pendente = df_cat['Pendente'].sum()

    # Top categoria
    top_cat = df_cat.iloc[0]['Categoria'] if len(df_cat) > 0 else "N/A"
    top_cat_valor = df_cat.iloc[0]['Total'] if len(df_cat) > 0 else 0
    pct_top = (top_cat_valor / total_valor * 100) if total_valor > 0 else 0

    # Concentração - quantas representam 80%
    df_cat_sorted = df_cat.sort_values('Total', ascending=False)
    df_cat_sorted['PCT_ACUM'] = df_cat_sorted['Total'].cumsum() / total_valor * 100
    cat_80 = (df_cat_sorted['PCT_ACUM'] <= 80).sum()

    # Ticket médio por categoria
    ticket_medio = total_valor / df_cat['Qtd'].sum() if df_cat['Qtd'].sum() > 0 else 0

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            label="🏷️ Total Categorias",
            value=formatar_numero(total_categorias),
            delta=f"{formatar_numero(df_cat['Qtd'].sum())} títulos",
            delta_color="off"
        )

    with col2:
        st.metric(
            label="💰 Valor Total",
            value=formatar_moeda(total_valor),
            delta=f"Pendente: {formatar_moeda(total_pendente)}",
            delta_color="off"
        )

    with col3:
        st.metric(
            label="🏆 Maior Categoria",
            value=top_cat[:18] + "..." if len(top_cat) > 18 else top_cat,
            delta=f"{pct_top:.1f}% do total",
            delta_color="off"
        )

    with col4:
        st.metric(
            label="📊 Concentração 80%",
            value=f"{cat_80} categorias",
            delta=f"{cat_80/total_categorias*100:.1f}% do total",
            delta_color="off"
        )

    with col5:
        st.metric(
            label="🎫 Ticket Médio",
            value=formatar_moeda(ticket_medio),
            delta="Por título",
            delta_color="off"
        )


def _render_treemap(df_cat, cores):
    """Treemap de categorias"""

    st.markdown("##### 🗺️ Treemap - Distribuição")

    df_tree = df_cat.head(15).copy()

    if len(df_tree) > 0:
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
    else:
        st.info("Sem dados para exibir treemap.")


def _render_donut_categorias(df_cat, cores):
    """Donut chart das top 8 categorias"""

    st.markdown("##### 🍩 Top 8 Categorias")

    df_top = df_cat.head(8).copy()
    outros = df_cat.iloc[8:]['Total'].sum() if len(df_cat) > 8 else 0

    if outros > 0:
        df_top = pd.concat([df_top, pd.DataFrame([{
            'Categoria': 'Outros',
            'Total': outros,
            'Pendente': df_cat.iloc[8:]['Pendente'].sum(),
            'Pago': df_cat.iloc[8:]['Pago'].sum(),
            'Pct_Pago': 0
        }])], ignore_index=True)

    if len(df_top) > 0:
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
            legend=dict(
                orientation="v",
                yanchor="middle",
                y=0.5,
                xanchor="left",
                x=1.02,
                font=dict(size=9)
            ),
            margin=dict(l=10, r=100, t=10, b=10)
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados para exibir gráfico.")


def _render_top_categorias(df_cat, cores):
    """Top 10 categorias - barras horizontais"""

    st.markdown("##### 📊 Top 10 - Pago vs Pendente")

    df_top = df_cat.head(10)

    if len(df_top) > 0:
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
    else:
        st.info("Sem dados para exibir gráfico.")


def _render_evolucao_categorias(df, cores):
    """Evolução mensal das top 5 categorias"""

    st.markdown("##### 📈 Evolução Mensal - Top 5")

    # Top 5 categorias
    top5 = df.groupby('DESCRICAO')['VALOR_ORIGINAL'].sum().nlargest(5).index.tolist()

    df_top5 = df[df['DESCRICAO'].isin(top5)].copy()
    df_top5['MES'] = df_top5['EMISSAO'].dt.to_period('M').astype(str)

    df_evol = df_top5.groupby(['MES', 'DESCRICAO'])['VALOR_ORIGINAL'].sum().reset_index()

    if len(df_evol) > 0:
        fig = px.line(
            df_evol,
            x='MES',
            y='VALOR_ORIGINAL',
            color='DESCRICAO',
            markers=True,
            labels={'VALOR_ORIGINAL': 'Valor (R$)', 'MES': 'Mês', 'DESCRICAO': 'Categoria'}
        )

        fig.update_layout(
            criar_layout(300),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.35,
                xanchor="center",
                x=0.5,
                font=dict(size=8)
            ),
            margin=dict(l=10, r=10, t=10, b=80),
            xaxis_tickangle=-45
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados suficientes para evolução.")


def _render_detalhe_categoria(df, df_cat, cores):
    """Detalhes de categoria selecionada"""

    st.markdown("##### 🔎 Consultar Categoria")

    categorias = df_cat['Categoria'].tolist()

    col1, col2 = st.columns([3, 1])
    with col1:
        categoria_selecionada = st.selectbox(
            "Selecione uma categoria",
            options=[""] + categorias,
            key="busca_categoria"
        )

    if categoria_selecionada:
        df_sel = df[df['DESCRICAO'] == categoria_selecionada]

        # Métricas
        total_valor = df_sel['VALOR_ORIGINAL'].sum()
        total_pago = total_valor - df_sel['SALDO'].sum()
        total_pendente = df_sel['SALDO'].sum()
        qtd_titulos = len(df_sel)
        qtd_fornecedores = df_sel['NOME_FORNECEDOR'].nunique()
        pct_pago = (total_pago / total_valor * 100) if total_valor > 0 else 0

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric("Total", formatar_moeda(total_valor), f"{qtd_titulos} títulos", delta_color="off")
        with col2:
            st.metric("Pago", formatar_moeda(total_pago), f"{pct_pago:.1f}%", delta_color="off")
        with col3:
            st.metric("Pendente", formatar_moeda(total_pendente), delta_color="off")
        with col4:
            st.metric("Fornecedores", qtd_fornecedores, delta_color="off")
        with col5:
            filiais = df_sel['NOME_FILIAL'].nunique()
            st.metric("Filiais", filiais, delta_color="off")

        # Gráficos lado a lado
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("###### 🏢 Top Fornecedores")
            df_forn = df_sel.groupby('NOME_FORNECEDOR')['VALOR_ORIGINAL'].sum().nlargest(5).reset_index()

            if len(df_forn) > 0:
                fig = go.Figure(go.Bar(
                    y=df_forn['NOME_FORNECEDOR'].str[:20],
                    x=df_forn['VALOR_ORIGINAL'],
                    orientation='h',
                    marker_color=cores['primaria'],
                    text=[formatar_moeda(v) for v in df_forn['VALOR_ORIGINAL']],
                    textposition='outside',
                    textfont=dict(size=9)
                ))
                fig.update_layout(
                    criar_layout(200),
                    yaxis={'autorange': 'reversed'},
                    margin=dict(l=10, r=60, t=10, b=10)
                )
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("###### 🏭 Distribuição por Filial")
            df_fil = df_sel.groupby('NOME_FILIAL')['VALOR_ORIGINAL'].sum().reset_index()

            if len(df_fil) > 0:
                fig = go.Figure(go.Pie(
                    labels=df_fil['NOME_FILIAL'].str[:15],
                    values=df_fil['VALOR_ORIGINAL'],
                    hole=0.4,
                    textinfo='percent',
                    textfont=dict(size=9)
                ))
                fig.update_layout(
                    criar_layout(200),
                    showlegend=True,
                    legend=dict(font=dict(size=8)),
                    margin=dict(l=10, r=10, t=10, b=10)
                )
                st.plotly_chart(fig, use_container_width=True)

        # Tabela de títulos
        with st.expander("📋 Ver títulos da categoria"):
            df_titulos = df_sel[['NOME_FILIAL', 'NOME_FORNECEDOR', 'EMISSAO', 'VENCIMENTO', 'VALOR_ORIGINAL', 'SALDO', 'STATUS']].copy()
            df_titulos = df_titulos.sort_values('VALOR_ORIGINAL', ascending=False).head(50)
            df_titulos['EMISSAO'] = df_titulos['EMISSAO'].dt.strftime('%d/%m/%Y')
            df_titulos['VENCIMENTO'] = df_titulos['VENCIMENTO'].dt.strftime('%d/%m/%Y')
            df_titulos['VALOR_ORIGINAL'] = df_titulos['VALOR_ORIGINAL'].apply(lambda x: formatar_moeda(x, completo=True))
            df_titulos['SALDO'] = df_titulos['SALDO'].apply(lambda x: formatar_moeda(x, completo=True))
            df_titulos.columns = ['Filial', 'Fornecedor', 'Emissão', 'Vencimento', 'Valor', 'Saldo', 'Status']
            st.dataframe(df_titulos, use_container_width=True, hide_index=True, height=300)


def _render_ranking_categorias(df_cat, cores):
    """Ranking completo com filtros"""

    st.markdown("##### 🏆 Ranking de Categorias")

    # Filtros
    col1, col2, col3 = st.columns(3)
    with col1:
        ordenar = st.selectbox(
            "Ordenar por",
            ["Valor Total", "Saldo Pendente", "Qtd Títulos", "% Pendente"],
            key="ord_cat"
        )
    with col2:
        qtd_exibir = st.selectbox("Exibir", [15, 30, 50, "Todas"], key="qtd_cat")
    with col3:
        filtro_status = st.selectbox("Status", ["Todas", "Com Pendência", "Quitadas"], key="status_cat")

    df_rank = df_cat.copy()
    df_rank['% Pendente'] = (100 - df_rank['Pct_Pago']).round(1)

    # Filtrar
    if filtro_status == "Com Pendência":
        df_rank = df_rank[df_rank['Pendente'] > 0]
    elif filtro_status == "Quitadas":
        df_rank = df_rank[df_rank['Pendente'] <= 0]

    # Ordenar
    if ordenar == "Valor Total":
        df_rank = df_rank.sort_values('Total', ascending=False)
    elif ordenar == "Saldo Pendente":
        df_rank = df_rank.sort_values('Pendente', ascending=False)
    elif ordenar == "Qtd Títulos":
        df_rank = df_rank.sort_values('Qtd', ascending=False)
    else:
        df_rank = df_rank.sort_values('% Pendente', ascending=False)

    # Limitar
    if qtd_exibir != "Todas":
        df_rank = df_rank.head(qtd_exibir)

    # Formatar
    df_show = df_rank[['Categoria', 'Total', 'Pendente', 'Qtd', 'Fornecedores', 'Pct_Pago']].copy()
    df_show['Total'] = df_show['Total'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Pendente'] = df_show['Pendente'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show.columns = ['Categoria', 'Total', 'Pendente', 'Títulos', 'Fornecedores', '% Pago']

    st.dataframe(
        df_show,
        use_container_width=True,
        hide_index=True,
        height=400,
        column_config={
            "% Pago": st.column_config.ProgressColumn(
                "% Pago",
                help="Percentual pago",
                format="%.1f%%",
                min_value=0,
                max_value=100,
            ),
        }
    )

    st.caption(f"Exibindo {len(df_show)} categorias | Total geral: {formatar_moeda(df_cat['Total'].sum(), completo=True)}")
