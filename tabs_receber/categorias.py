"""
Aba Categorias - Análise completa por categoria - Contas a Receber
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from config.theme import get_cores
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero
from config.settings import GRUPOS_FILIAIS, get_grupo_filial


def render_categorias_receber(df):
    """Renderiza a aba de Categorias"""
    cores = get_cores()

    if len(df) == 0:
        st.warning("Nenhum dado disponível para o período selecionado.")
        return

    # Usar NOME_CLIENTE para contagem (CLIENTE pode nao existir)
    col_count = 'CLIENTE' if 'CLIENTE' in df.columns else 'NOME_CLIENTE'

    df_cat = df.groupby('DESCRICAO').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'NOME_CLIENTE': ['count', 'nunique'],
        'NOME_FILIAL': 'nunique'
    }).reset_index()

    df_cat.columns = ['Categoria', 'Total', 'Pendente', 'Qtd', 'Clientes', 'Filiais']
    df_cat['Recebido'] = df_cat['Total'] - df_cat['Pendente']
    df_cat['Pct_Recebido'] = (df_cat['Recebido'] / df_cat['Total'] * 100).fillna(0).round(1)
    df_cat = df_cat.sort_values('Total', ascending=False)

    # KPIs
    _render_kpis_categorias(df_cat, df, cores)

    st.divider()

    # NOVO: Prazo médio por categoria (Emissão x Vencimento)
    _render_prazo_por_categoria(df, cores)

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

    # NOVO: Aging por Categoria + Categorias Críticas
    col1, col2 = st.columns(2)

    with col1:
        _render_aging_por_categoria(df, cores)

    with col2:
        _render_categorias_criticas(df, cores)

    st.divider()

    # NOVO: Heatmap Categoria x Filial + Sazonalidade
    col1, col2 = st.columns(2)

    with col1:
        _render_heatmap_categoria_filial(df, cores)

    with col2:
        _render_sazonalidade_categorias(df, cores)

    st.divider()

    # Consulta de categoria específica
    _render_detalhe_categoria(df, df_cat, cores)

    st.divider()

    # Ranking completo
    _render_ranking_categorias(df_cat, cores)


def _render_prazo_por_categoria(df, cores):
    """Prazo médio por categoria - dias entre emissão e vencimento - com detalhamento por cliente"""

    st.markdown("##### Prazo Médio por Categoria (Emissão → Vencimento)")

    # Calcular prazo (dias entre emissão e vencimento)
    df_prazo = df.copy()
    df_prazo['PRAZO_DIAS'] = (df_prazo['VENCIMENTO'] - df_prazo['EMISSAO']).dt.days

    # Remover valores inválidos (negativos ou muito altos)
    df_prazo = df_prazo[(df_prazo['PRAZO_DIAS'] >= 0) & (df_prazo['PRAZO_DIAS'] <= 365)]

    if len(df_prazo) == 0:
        st.warning("Sem dados válidos para calcular prazo médio.")
        return

    # Agrupar por categoria
    df_cat_prazo = df_prazo.groupby('DESCRICAO').agg({
        'PRAZO_DIAS': ['mean', 'median', 'min', 'max', 'std'],
        'VALOR_ORIGINAL': 'sum',
        'NOME_CLIENTE': 'nunique'
    }).reset_index()

    df_cat_prazo.columns = ['Categoria', 'Prazo_Medio', 'Prazo_Mediana', 'Prazo_Min', 'Prazo_Max', 'Prazo_Desvio', 'Valor_Total', 'Clientes']
    df_cat_prazo = df_cat_prazo.sort_values('Valor_Total', ascending=False)

    # Estatísticas gerais no topo
    prazo_geral = df_prazo['PRAZO_DIAS'].mean()
    prazo_mediana_geral = df_prazo['PRAZO_DIAS'].median()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Prazo Médio Geral", f"{prazo_geral:.0f} dias")
    with col2:
        st.metric("Mediana Geral", f"{prazo_mediana_geral:.0f} dias")
    with col3:
        idx_maior = df_cat_prazo['Prazo_Medio'].idxmax()
        cat_maior_prazo = df_cat_prazo.loc[idx_maior, 'Categoria'] if len(df_cat_prazo) > 0 else "N/A"
        maior_prazo = df_cat_prazo['Prazo_Medio'].max()
        st.metric("Maior Prazo", f"{cat_maior_prazo[:18]}...", f"{maior_prazo:.0f} dias", delta_color="off")
    with col4:
        idx_menor = df_cat_prazo['Prazo_Medio'].idxmin()
        cat_menor_prazo = df_cat_prazo.loc[idx_menor, 'Categoria'] if len(df_cat_prazo) > 0 else "N/A"
        menor_prazo = df_cat_prazo['Prazo_Medio'].min()
        st.metric("Menor Prazo", f"{cat_menor_prazo[:18]}...", f"{menor_prazo:.0f} dias", delta_color="off")

    st.markdown("")

    # Exibir em duas colunas: gráfico de barras e tabela
    col1, col2 = st.columns([3, 2])

    with col1:
        # Top 15 categorias por valor - mostrar prazo médio
        df_top = df_cat_prazo.head(15).copy()
        df_top = df_top.sort_values('Prazo_Medio', ascending=True)

        # Cor baseada no prazo (verde = curto, vermelho = longo)
        cores_barras = []
        for prazo in df_top['Prazo_Medio']:
            if prazo <= 15:
                cores_barras.append(cores['sucesso'])
            elif prazo <= 30:
                cores_barras.append(cores['primaria'])
            elif prazo <= 45:
                cores_barras.append(cores['alerta'])
            elif prazo <= 60:
                cores_barras.append('#f97316')
            else:
                cores_barras.append(cores['perigo'])

        fig = go.Figure(go.Bar(
            y=df_top['Categoria'].str[:25],
            x=df_top['Prazo_Medio'],
            orientation='h',
            marker_color=cores_barras,
            text=[f"{int(p)} dias" for p in df_top['Prazo_Medio']],
            textposition='outside',
            textfont=dict(size=9),
            hovertemplate="<b>%{y}</b><br>Prazo Médio: %{x:.0f} dias<extra></extra>"
        ))

        fig.update_layout(
            criar_layout(320),
            xaxis_title="Prazo Médio (dias)",
            margin=dict(l=10, r=50, t=10, b=30)
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Tabela resumo
        df_tabela = df_cat_prazo.head(15).copy()
        df_tabela['Prazo_Medio'] = df_tabela['Prazo_Medio'].round(0).astype(int)
        df_tabela['Prazo_Mediana'] = df_tabela['Prazo_Mediana'].round(0).astype(int)
        df_tabela['Valor_Total'] = df_tabela['Valor_Total'].apply(lambda x: formatar_moeda(x, completo=True))

        df_show = df_tabela[['Categoria', 'Prazo_Medio', 'Prazo_Mediana', 'Valor_Total', 'Clientes']].copy()
        df_show.columns = ['Categoria', 'Média (dias)', 'Mediana', 'Valor Total', 'Clientes']

        st.dataframe(
            df_show,
            use_container_width=True,
            hide_index=True,
            height=320
        )

    # ========== DETALHAMENTO POR CLIENTE ==========
    st.markdown("---")
    st.markdown("###### Detalhamento por Cliente")

    # Filtros
    col_filtro1, col_filtro2, col_filtro3 = st.columns([2, 2, 1])

    with col_filtro1:
        categorias_lista = ['Todas as Categorias'] + df_cat_prazo['Categoria'].tolist()
        categoria_selecionada = st.selectbox(
            "Filtrar por Categoria",
            categorias_lista,
            key="prazo_cat_filter"
        )

    with col_filtro2:
        faixas_prazo = ['Todos os Prazos', 'Até 15 dias', '16-30 dias', '31-45 dias', '46-60 dias', 'Acima de 60 dias']
        faixa_selecionada = st.selectbox(
            "Filtrar por Faixa de Prazo",
            faixas_prazo,
            key="prazo_faixa_filter"
        )

    with col_filtro3:
        ordenar_por = st.selectbox(
            "Ordenar por",
            ['Valor Total', 'Prazo Médio', 'Qtd Títulos'],
            key="prazo_ordenar"
        )

    # Aplicar filtros
    df_filtrado = df_prazo.copy()

    if categoria_selecionada != 'Todas as Categorias':
        df_filtrado = df_filtrado[df_filtrado['DESCRICAO'] == categoria_selecionada]

    # Agrupar por cliente (dentro da categoria se filtrada)
    if categoria_selecionada != 'Todas as Categorias':
        # Quando uma categoria está selecionada, mostrar clientes dessa categoria
        df_clientes = df_filtrado.groupby('NOME_CLIENTE').agg({
            'PRAZO_DIAS': ['mean', 'median', 'min', 'max', 'count'],
            'VALOR_ORIGINAL': 'sum',
            'SALDO': 'sum'
        }).reset_index()
        df_clientes.columns = ['Cliente', 'Prazo_Medio', 'Prazo_Mediana', 'Prazo_Min', 'Prazo_Max', 'Qtd_Titulos', 'Valor_Total', 'Saldo']
    else:
        # Quando todas categorias, mostrar cliente + categoria
        df_clientes = df_filtrado.groupby(['NOME_CLIENTE', 'DESCRICAO']).agg({
            'PRAZO_DIAS': ['mean', 'median', 'min', 'max', 'count'],
            'VALOR_ORIGINAL': 'sum',
            'SALDO': 'sum'
        }).reset_index()
        df_clientes.columns = ['Cliente', 'Categoria', 'Prazo_Medio', 'Prazo_Mediana', 'Prazo_Min', 'Prazo_Max', 'Qtd_Titulos', 'Valor_Total', 'Saldo']

    # Filtrar por faixa de prazo
    if faixa_selecionada == 'Até 15 dias':
        df_clientes = df_clientes[df_clientes['Prazo_Medio'] <= 15]
    elif faixa_selecionada == '16-30 dias':
        df_clientes = df_clientes[(df_clientes['Prazo_Medio'] > 15) & (df_clientes['Prazo_Medio'] <= 30)]
    elif faixa_selecionada == '31-45 dias':
        df_clientes = df_clientes[(df_clientes['Prazo_Medio'] > 30) & (df_clientes['Prazo_Medio'] <= 45)]
    elif faixa_selecionada == '46-60 dias':
        df_clientes = df_clientes[(df_clientes['Prazo_Medio'] > 45) & (df_clientes['Prazo_Medio'] <= 60)]
    elif faixa_selecionada == 'Acima de 60 dias':
        df_clientes = df_clientes[df_clientes['Prazo_Medio'] > 60]

    # Ordenar
    if ordenar_por == 'Valor Total':
        df_clientes = df_clientes.sort_values('Valor_Total', ascending=False)
    elif ordenar_por == 'Prazo Médio':
        df_clientes = df_clientes.sort_values('Prazo_Medio', ascending=False)
    else:
        df_clientes = df_clientes.sort_values('Qtd_Titulos', ascending=False)

    if len(df_clientes) == 0:
        st.info("Nenhum cliente encontrado com os filtros selecionados.")
        return

    # Layout: Gráfico + Tabela
    col_graf, col_tab = st.columns([1, 1])

    with col_graf:
        # Gráfico dos top 10 clientes
        df_plot = df_clientes.head(10).copy()

        # Definir cor baseada no prazo
        def get_cor_prazo(prazo):
            if prazo <= 15:
                return cores['sucesso']
            elif prazo <= 30:
                return cores['primaria']
            elif prazo <= 45:
                return cores['alerta']
            elif prazo <= 60:
                return '#f97316'
            else:
                return cores['perigo']

        cores_graf = [get_cor_prazo(p) for p in df_plot['Prazo_Medio']]

        fig = go.Figure()

        fig.add_trace(go.Bar(
            y=df_plot['Cliente'].str[:30],
            x=df_plot['Prazo_Medio'],
            orientation='h',
            marker_color=cores_graf,
            text=[f"{int(p)}d | {formatar_moeda(v)}" for p, v in zip(df_plot['Prazo_Medio'], df_plot['Valor_Total'])],
            textposition='outside',
            textfont=dict(size=8),
            hovertemplate="<b>%{y}</b><br>Prazo: %{x:.0f} dias<extra></extra>"
        ))

        fig.update_layout(
            criar_layout(350),
            xaxis_title="Prazo Médio (dias)",
            yaxis={'autorange': 'reversed'},
            margin=dict(l=10, r=100, t=10, b=30)
        )

        st.plotly_chart(fig, use_container_width=True)

    with col_tab:
        # Tabela detalhada
        df_tabela_cli = df_clientes.head(50).copy()
        df_tabela_cli['Prazo_Medio'] = df_tabela_cli['Prazo_Medio'].round(0).astype(int)
        df_tabela_cli['Valor_Fmt'] = df_tabela_cli['Valor_Total'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tabela_cli['Saldo_Fmt'] = df_tabela_cli['Saldo'].apply(lambda x: formatar_moeda(x, completo=True))

        if categoria_selecionada != 'Todas as Categorias':
            df_show_cli = df_tabela_cli[['Cliente', 'Prazo_Medio', 'Qtd_Titulos', 'Valor_Fmt', 'Saldo_Fmt']].copy()
            df_show_cli.columns = ['Cliente', 'Prazo (dias)', 'Títulos', 'Valor Total', 'Saldo']
        else:
            df_show_cli = df_tabela_cli[['Cliente', 'Categoria', 'Prazo_Medio', 'Qtd_Titulos', 'Valor_Fmt']].copy()
            df_show_cli.columns = ['Cliente', 'Categoria', 'Prazo (dias)', 'Títulos', 'Valor Total']

        st.dataframe(
            df_show_cli,
            use_container_width=True,
            hide_index=True,
            height=350
        )

    # Resumo do filtro
    total_clientes = len(df_clientes)
    total_valor = df_clientes['Valor_Total'].sum()
    prazo_medio_filtro = df_clientes['Prazo_Medio'].mean() if len(df_clientes) > 0 else 0

    st.markdown(f"""
    <div style="background: {cores['card']}; border: 1px solid {cores['borda']}; border-radius: 8px;
                padding: 0.75rem; margin-top: 0.5rem;">
        <div style="display: flex; justify-content: space-around; text-align: center;">
            <div>
                <span style="color: {cores['texto_secundario']}; font-size: 0.75rem;">Clientes</span><br>
                <span style="color: {cores['texto']}; font-weight: 700;">{total_clientes}</span>
            </div>
            <div>
                <span style="color: {cores['texto_secundario']}; font-size: 0.75rem;">Valor Total</span><br>
                <span style="color: {cores['sucesso']}; font-weight: 700;">{formatar_moeda(total_valor)}</span>
            </div>
            <div>
                <span style="color: {cores['texto_secundario']}; font-size: 0.75rem;">Prazo Médio</span><br>
                <span style="color: {cores['primaria']}; font-weight: 700;">{prazo_medio_filtro:.0f} dias</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Expander com títulos detalhados
    if categoria_selecionada != 'Todas as Categorias':
        with st.expander(f"Ver títulos da categoria: {categoria_selecionada}"):
            df_titulos = df_filtrado[['NOME_FILIAL', 'NOME_CLIENTE', 'EMISSAO', 'VENCIMENTO', 'PRAZO_DIAS', 'VALOR_ORIGINAL', 'SALDO', 'STATUS']].copy()
            df_titulos = df_titulos.sort_values('VALOR_ORIGINAL', ascending=False).head(100)
            df_titulos['EMISSAO'] = df_titulos['EMISSAO'].dt.strftime('%d/%m/%Y')
            df_titulos['VENCIMENTO'] = df_titulos['VENCIMENTO'].dt.strftime('%d/%m/%Y')
            df_titulos['VALOR_ORIGINAL'] = df_titulos['VALOR_ORIGINAL'].apply(lambda x: formatar_moeda(x, completo=True))
            df_titulos['SALDO'] = df_titulos['SALDO'].apply(lambda x: formatar_moeda(x, completo=True))
            df_titulos.columns = ['Filial', 'Cliente', 'Emissão', 'Vencimento', 'Prazo (dias)', 'Valor', 'Saldo', 'Status']
            st.dataframe(df_titulos, use_container_width=True, hide_index=True, height=400)


def _render_kpis_categorias(df_cat, df, cores):
    """KPIs de resumo de categorias"""

    total_categorias = len(df_cat)
    total_valor = df_cat['Total'].sum()
    total_pendente = df_cat['Pendente'].sum()

    top_cat = df_cat.iloc[0]['Categoria'] if len(df_cat) > 0 else "N/A"
    top_cat_valor = df_cat.iloc[0]['Total'] if len(df_cat) > 0 else 0
    pct_top = (top_cat_valor / total_valor * 100) if total_valor > 0 else 0

    df_cat_sorted = df_cat.sort_values('Total', ascending=False)
    df_cat_sorted['PCT_ACUM'] = df_cat_sorted['Total'].cumsum() / total_valor * 100
    cat_80 = (df_cat_sorted['PCT_ACUM'] <= 80).sum()

    ticket_medio = total_valor / df_cat['Qtd'].sum() if df_cat['Qtd'].sum() > 0 else 0

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            label="Total Categorias",
            value=formatar_numero(total_categorias),
            delta=f"{formatar_numero(df_cat['Qtd'].sum())} títulos",
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
            label="Maior Categoria",
            value=top_cat[:18] + "..." if len(top_cat) > 18 else top_cat,
            delta=f"{pct_top:.1f}% do total",
            delta_color="off"
        )

    with col4:
        st.metric(
            label="Concentração 80%",
            value=f"{cat_80} categorias",
            delta=f"{cat_80/total_categorias*100:.1f}% do total",
            delta_color="off"
        )

    with col5:
        st.metric(
            label="Ticket Médio",
            value=formatar_moeda(ticket_medio),
            delta="Por título",
            delta_color="off"
        )


def _render_treemap(df_cat, cores):
    """Treemap de categorias"""

    st.markdown("##### Treemap - Distribuição")

    df_tree = df_cat.head(15).copy()

    if len(df_tree) > 0:
        fig = px.treemap(
            df_tree,
            path=['Categoria'],
            values='Total',
            color='Pct_Recebido',
            color_continuous_scale='RdYlGn',
            hover_data={'Total': ':,.2f', 'Pendente': ':,.2f', 'Pct_Recebido': ':.1f'}
        )
        fig.update_layout(
            criar_layout(300),
            coloraxis_colorbar=dict(title="% Recebido", len=0.6),
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

    st.markdown("##### Top 8 Categorias")

    df_top = df_cat.head(8).copy()
    outros = df_cat.iloc[8:]['Total'].sum() if len(df_cat) > 8 else 0

    if outros > 0:
        df_top = pd.concat([df_top, pd.DataFrame([{
            'Categoria': 'Outros',
            'Total': outros,
            'Pendente': df_cat.iloc[8:]['Pendente'].sum(),
            'Recebido': df_cat.iloc[8:]['Recebido'].sum(),
            'Pct_Recebido': 0
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

    st.markdown("##### Top 10 - Recebido vs Pendente")

    df_top = df_cat.head(10)

    if len(df_top) > 0:
        fig = go.Figure()

        fig.add_trace(go.Bar(
            y=df_top['Categoria'].str[:25],
            x=df_top['Recebido'],
            orientation='h',
            name='Recebido',
            marker_color=cores['sucesso'],
            text=[formatar_moeda(v) for v in df_top['Recebido']],
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


def _render_aging_por_categoria(df, cores):
    """Aging por categoria - mostra quanto está vencido vs a vencer por categoria"""

    st.markdown("##### Situação de Vencimento por Categoria")
    st.caption("Quanto de cada categoria está vencido vs a vencer")

    df_pendentes = df[df['SALDO'] > 0].copy()

    if len(df_pendentes) == 0:
        st.info("Sem títulos pendentes")
        return

    # Classificar: Vencido vs A Vencer
    df_pendentes['SITUACAO'] = df_pendentes['STATUS'].apply(
        lambda x: 'Vencido' if x == 'Vencido' else 'A Vencer'
    )

    # Agrupar por categoria
    df_cat = df_pendentes.groupby('DESCRICAO').agg({
        'SALDO': 'sum',
        'VALOR_ORIGINAL': 'count'
    }).reset_index()
    df_cat.columns = ['Categoria', 'Saldo_Total', 'Qtd']

    # Calcular vencido por categoria
    df_vencido = df_pendentes[df_pendentes['SITUACAO'] == 'Vencido'].groupby('DESCRICAO')['SALDO'].sum().reset_index()
    df_vencido.columns = ['Categoria', 'Vencido']

    # Merge
    df_cat = df_cat.merge(df_vencido, on='Categoria', how='left')
    df_cat['Vencido'] = df_cat['Vencido'].fillna(0)
    df_cat['A_Vencer'] = df_cat['Saldo_Total'] - df_cat['Vencido']
    df_cat['Pct_Vencido'] = (df_cat['Vencido'] / df_cat['Saldo_Total'] * 100).round(1)

    # Top 10 por saldo
    df_cat = df_cat.sort_values('Saldo_Total', ascending=False).head(10)

    # Gráfico de barras empilhadas (horizontal)
    fig = go.Figure()

    # Barra "A Vencer" (verde)
    fig.add_trace(go.Bar(
        y=df_cat['Categoria'].str[:22],
        x=df_cat['A_Vencer'],
        orientation='h',
        name='A Vencer',
        marker_color=cores['sucesso'],
        text=[formatar_moeda(v) for v in df_cat['A_Vencer']],
        textposition='inside',
        textfont=dict(size=8, color='white'),
        hovertemplate="<b>%{y}</b><br>A Vencer: R$ %{x:,.2f}<extra></extra>"
    ))

    # Barra "Vencido" (vermelho)
    fig.add_trace(go.Bar(
        y=df_cat['Categoria'].str[:22],
        x=df_cat['Vencido'],
        orientation='h',
        name='Vencido',
        marker_color=cores['perigo'],
        text=[f"{formatar_moeda(v)} ({p:.0f}%)" if v > 0 else '' for v, p in zip(df_cat['Vencido'], df_cat['Pct_Vencido'])],
        textposition='inside',
        textfont=dict(size=8, color='white'),
        hovertemplate="<b>%{y}</b><br>Vencido: R$ %{x:,.2f}<extra></extra>"
    ))

    fig.update_layout(
        criar_layout(320, barmode='stack'),
        yaxis={'autorange': 'reversed'},
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)),
        margin=dict(l=10, r=10, t=40, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)

    # Resumo
    total_vencido = df_cat['Vencido'].sum()
    total_a_vencer = df_cat['A_Vencer'].sum()
    pct_vencido_geral = (total_vencido / (total_vencido + total_a_vencer) * 100) if (total_vencido + total_a_vencer) > 0 else 0

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("A Vencer", formatar_moeda(total_a_vencer))
    with col2:
        st.metric("Vencido", formatar_moeda(total_vencido))
    with col3:
        st.metric("% Vencido", f"{pct_vencido_geral:.1f}%")


def _render_categorias_criticas(df, cores):
    """Categorias críticas - alto valor vencido"""

    st.markdown("##### Categorias Críticas")

    df_pendentes = df[df['SALDO'] > 0].copy()

    if len(df_pendentes) == 0:
        st.info("Sem titulos pendentes")
        return

    # Filtrar vencidos
    df_vencido = df_pendentes[df_pendentes['DIAS_ATRASO'] > 0]

    if len(df_vencido) == 0:
        st.success("Nenhuma categoria com titulos vencidos!")
        return

    # Agrupar por categoria
    df_crit = df_vencido.groupby('DESCRICAO').agg({
        'SALDO': 'sum',
        'DIAS_ATRASO': 'max',
        'NOME_CLIENTE': 'nunique'
    }).reset_index()
    df_crit.columns = ['Categoria', 'Vencido', 'Dias_Max', 'Clientes']

    # Score de risco
    df_crit['SCORE'] = df_crit['Vencido'] * (1 + df_crit['Dias_Max'] / 30)
    df_crit = df_crit.nlargest(10, 'SCORE')

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=df_crit['Categoria'].str[:22],
        x=df_crit['Vencido'],
        orientation='h',
        marker_color=cores['perigo'],
        text=[f"{formatar_moeda(v)} | {int(d)}d | {c} cli" for v, d, c in zip(df_crit['Vencido'], df_crit['Dias_Max'], df_crit['Clientes'])],
        textposition='outside',
        textfont=dict(size=8)
    ))

    fig.update_layout(
        criar_layout(320),
        yaxis={'autorange': 'reversed'},
        margin=dict(l=10, r=120, t=10, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)

    total_critico = df_crit['Vencido'].sum()
    st.error(f"**Total Vencido:** {formatar_moeda(total_critico)}")


def _get_nome_grupo(cod_filial):
    """Retorna o nome do grupo a partir do codigo da filial"""
    grupo_id = get_grupo_filial(int(cod_filial))
    return GRUPOS_FILIAIS.get(grupo_id, f"Grupo {grupo_id}")


def _detectar_multiplos_grupos(df):
    """Detecta se o dataframe contem filiais de multiplos grupos"""
    if 'FILIAL' not in df.columns or len(df) == 0:
        return False
    grupos = df['FILIAL'].dropna().apply(lambda x: get_grupo_filial(int(x))).nunique()
    return grupos > 1


def _get_label_filial(row):
    """Retorna label curta da filial: codigo + sufixo do nome"""
    cod = str(int(row['FILIAL'])) if pd.notna(row.get('FILIAL')) else ''
    nome = str(row.get('NOME_FILIAL', ''))
    partes = nome.split(' - ')
    sufixo = partes[-1].strip() if len(partes) > 1 else nome.strip()
    return f"{cod} - {sufixo}" if cod else sufixo


def _render_heatmap_categoria_filial(df, cores):
    """Heatmap de valores por categoria x filial/grupo"""

    if 'NOME_FILIAL' not in df.columns:
        st.info("Coluna NOME_FILIAL nao disponivel")
        return

    multiplos_grupos = _detectar_multiplos_grupos(df)

    # Top 8 categorias
    top_cats = df.groupby('DESCRICAO')['VALOR_ORIGINAL'].sum().nlargest(8).index.tolist()
    df_heat = df[df['DESCRICAO'].isin(top_cats)].copy()

    if multiplos_grupos:
        st.markdown("##### Categoria x Grupo")
        df_heat['GRUPO'] = df_heat['FILIAL'].apply(lambda x: _get_nome_grupo(x))
        col_agrup = 'GRUPO'
    else:
        st.markdown("##### Categoria x Filial")
        df_heat['FILIAL_LABEL'] = df_heat.apply(_get_label_filial, axis=1)
        col_agrup = 'FILIAL_LABEL'

    # Pivot
    df_pivot = df_heat.groupby(['DESCRICAO', col_agrup])['VALOR_ORIGINAL'].sum().unstack(fill_value=0)

    if len(df_pivot) == 0 or len(df_pivot.columns) == 0:
        st.info("Dados insuficientes para heatmap")
        return

    fig = go.Figure(data=go.Heatmap(
        z=df_pivot.values,
        x=[str(c)[:20] for c in df_pivot.columns],
        y=df_pivot.index.str[:20],
        colorscale=[
            [0, cores['card']],
            [0.5, cores['primaria']],
            [1, cores['sucesso']]
        ],
        text=[[formatar_moeda(v) for v in row] for row in df_pivot.values],
        texttemplate="%{text}",
        textfont=dict(size=8),
        hovertemplate="Categoria: %{y}<br>" + ("Grupo" if multiplos_grupos else "Filial") + ": %{x}<br>Valor: %{text}<extra></extra>"
    ))

    fig.update_layout(
        criar_layout(320),
        margin=dict(l=10, r=10, t=10, b=60),
        xaxis_tickangle=-45
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_sazonalidade_categorias(df, cores):
    """Sazonalidade - padrão mensal por categoria"""

    st.markdown("##### Sazonalidade (Mês do Ano)")

    # Top 5 categorias
    top_cats = df.groupby('DESCRICAO')['VALOR_ORIGINAL'].sum().nlargest(5).index.tolist()
    df_saz = df[df['DESCRICAO'].isin(top_cats)].copy()

    df_saz['MES_NUM'] = df_saz['EMISSAO'].dt.month
    df_saz['MES_NOME'] = df_saz['EMISSAO'].dt.strftime('%b')

    # Agrupar por mês e categoria
    df_pivot = df_saz.groupby(['MES_NUM', 'MES_NOME', 'DESCRICAO'])['VALOR_ORIGINAL'].sum().reset_index()

    if len(df_pivot) == 0:
        st.info("Dados insuficientes")
        return

    # Ordenar por mês
    df_pivot = df_pivot.sort_values('MES_NUM')

    fig = px.bar(
        df_pivot,
        x='MES_NOME',
        y='VALOR_ORIGINAL',
        color='DESCRICAO',
        barmode='group',
        labels={'VALOR_ORIGINAL': 'Valor (R$)', 'MES_NOME': 'Mês', 'DESCRICAO': 'Categoria'}
    )

    fig.update_layout(
        criar_layout(320),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.4,
            xanchor="center",
            x=0.5,
            font=dict(size=7)
        ),
        margin=dict(l=10, r=10, t=10, b=90),
        xaxis={'categoryorder': 'array', 'categoryarray': ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']}
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_evolucao_categorias(df, cores):
    """Evolução mensal das top 5 categorias"""

    st.markdown("##### Evolução Mensal - Top 5")

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

    st.markdown("##### Consultar Categoria")

    categorias = df_cat['Categoria'].tolist()

    col1, col2 = st.columns([3, 1])
    with col1:
        categoria_selecionada = st.selectbox(
            "Selecione uma categoria",
            options=[""] + categorias,
            key="busca_categoria_rec"
        )

    if categoria_selecionada:
        df_sel = df[df['DESCRICAO'] == categoria_selecionada]

        total_valor = df_sel['VALOR_ORIGINAL'].sum()
        total_recebido = total_valor - df_sel['SALDO'].sum()
        total_pendente = df_sel['SALDO'].sum()
        qtd_titulos = len(df_sel)
        qtd_clientes = df_sel['NOME_CLIENTE'].nunique()
        pct_recebido = (total_recebido / total_valor * 100) if total_valor > 0 else 0

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric("Total", formatar_moeda(total_valor), f"{qtd_titulos} títulos", delta_color="off")
        with col2:
            st.metric("Recebido", formatar_moeda(total_recebido), f"{pct_recebido:.1f}%", delta_color="off")
        with col3:
            st.metric("Pendente", formatar_moeda(total_pendente), delta_color="off")
        with col4:
            st.metric("Clientes", qtd_clientes, delta_color="off")
        with col5:
            filiais = df_sel['NOME_FILIAL'].nunique()
            st.metric("Filiais", filiais, delta_color="off")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("###### Top Clientes")
            df_cli = df_sel.groupby('NOME_CLIENTE')['VALOR_ORIGINAL'].sum().nlargest(5).reset_index()

            if len(df_cli) > 0:
                fig = go.Figure(go.Bar(
                    y=df_cli['NOME_CLIENTE'].str[:20],
                    x=df_cli['VALOR_ORIGINAL'],
                    orientation='h',
                    marker_color=cores['primaria'],
                    text=[formatar_moeda(v) for v in df_cli['VALOR_ORIGINAL']],
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
            st.markdown("###### Distribuição por Filial")
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

        with st.expander("Ver títulos da categoria"):
            df_titulos = df_sel[['NOME_FILIAL', 'NOME_CLIENTE', 'EMISSAO', 'VENCIMENTO', 'VALOR_ORIGINAL', 'SALDO', 'STATUS']].copy()
            df_titulos = df_titulos.sort_values('VALOR_ORIGINAL', ascending=False).head(50)
            df_titulos['EMISSAO'] = df_titulos['EMISSAO'].dt.strftime('%d/%m/%Y')
            df_titulos['VENCIMENTO'] = df_titulos['VENCIMENTO'].dt.strftime('%d/%m/%Y')
            df_titulos['VALOR_ORIGINAL'] = df_titulos['VALOR_ORIGINAL'].apply(lambda x: formatar_moeda(x, completo=True))
            df_titulos['SALDO'] = df_titulos['SALDO'].apply(lambda x: formatar_moeda(x, completo=True))
            df_titulos.columns = ['Filial', 'Cliente', 'Emissão', 'Vencimento', 'Valor', 'Saldo', 'Status']
            st.dataframe(df_titulos, use_container_width=True, hide_index=True, height=300)


def _render_ranking_categorias(df_cat, cores):
    """Ranking completo com filtros"""

    st.markdown("##### Ranking de Categorias")

    col1, col2, col3 = st.columns(3)
    with col1:
        ordenar = st.selectbox(
            "Ordenar por",
            ["Valor Total", "Saldo Pendente", "Qtd Títulos", "% Pendente"],
            key="ord_cat_rec"
        )
    with col2:
        qtd_exibir = st.selectbox("Exibir", [15, 30, 50, "Todas"], key="qtd_cat_rec")
    with col3:
        filtro_status = st.selectbox("Status", ["Todas", "Com Pendência", "Quitadas"], key="status_cat_rec")

    df_rank = df_cat.copy()
    df_rank['% Pendente'] = (100 - df_rank['Pct_Recebido']).round(1)

    if filtro_status == "Com Pendência":
        df_rank = df_rank[df_rank['Pendente'] > 0]
    elif filtro_status == "Quitadas":
        df_rank = df_rank[df_rank['Pendente'] <= 0]

    if ordenar == "Valor Total":
        df_rank = df_rank.sort_values('Total', ascending=False)
    elif ordenar == "Saldo Pendente":
        df_rank = df_rank.sort_values('Pendente', ascending=False)
    elif ordenar == "Qtd Títulos":
        df_rank = df_rank.sort_values('Qtd', ascending=False)
    else:
        df_rank = df_rank.sort_values('% Pendente', ascending=False)

    if qtd_exibir != "Todas":
        df_rank = df_rank.head(qtd_exibir)

    df_show = df_rank[['Categoria', 'Total', 'Pendente', 'Qtd', 'Clientes', 'Pct_Recebido']].copy()
    df_show['Total'] = df_show['Total'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Pendente'] = df_show['Pendente'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show.columns = ['Categoria', 'Total', 'Pendente', 'Títulos', 'Clientes', '% Recebido']

    st.dataframe(
        df_show,
        use_container_width=True,
        hide_index=True,
        height=400,
        column_config={
            "% Recebido": st.column_config.ProgressColumn(
                "% Recebido",
                help="Percentual recebido",
                format="%.1f%%",
                min_value=0,
                max_value=100,
            ),
        }
    )

    st.caption(f"Exibindo {len(df_show)} categorias | Total geral: {formatar_moeda(df_cat['Total'].sum(), completo=True)}")
