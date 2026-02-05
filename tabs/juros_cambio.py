"""
Aba Juros e Cambio - Analise de juros pagos e operacoes em dolar/real
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from config.theme import get_cores
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero
from config.settings import GRUPOS_FILIAIS, get_grupo_filial


def _get_nome_grupo(cod_filial):
    grupo_id = get_grupo_filial(int(cod_filial))
    return GRUPOS_FILIAIS.get(grupo_id, f"Grupo {grupo_id}")


def _detectar_multiplos_grupos(df):
    if 'FILIAL' not in df.columns or len(df) == 0:
        return False
    grupos = df['FILIAL'].dropna().apply(lambda x: get_grupo_filial(int(x))).nunique()
    return grupos > 1


def render_juros_cambio(df):
    """Renderiza a aba de Juros e Cambio - separado em duas secoes"""
    cores = get_cores()

    if len(df) == 0:
        st.info("Nenhum dado disponivel.")
        return

    df = df.copy()

    # Garantir colunas necessarias
    colunas_necessarias = ['VALOR_JUROS', 'VALOR_MULTA', 'TX_MOEDA', 'VALOR_REAL']
    for col in colunas_necessarias:
        if col not in df.columns:
            df[col] = 0
        else:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Separar dados
    df_com_juros = df[df['VALOR_JUROS'] > 0]
    df_dolar = df[df['TX_MOEDA'] > 1]  # Operacoes em dolar
    df_real = df[df['TX_MOEDA'] <= 1]  # Operacoes em real

    # ========== DUAS ABAS INTERNAS ==========
    tab_juros, tab_cambio = st.tabs(["Juros e Multas", "Operacoes em Dolar"])

    with tab_juros:
        _render_secao_juros(df, df_com_juros, cores)

    with tab_cambio:
        _render_secao_cambio(df, df_dolar, df_real, cores)


# ============================================================
# SECAO 1: JUROS E MULTAS
# ============================================================

def _render_secao_juros(df, df_com_juros, cores):
    """Secao dedicada a analise de juros e multas - com filtros e analises avancadas"""

    # ========== FILTROS ==========
    st.markdown("##### Filtros")
    col1, col2, col3 = st.columns(3)

    # Listas de filtros baseadas apenas em titulos com juros/multa
    df_base_filtro = df_com_juros if len(df_com_juros) > 0 else df

    with col1:
        categorias = ['Todas'] + sorted([str(x) for x in df_base_filtro['DESCRICAO'].dropna().unique().tolist()])
        filtro_categoria = st.selectbox("Categoria", categorias, key="juros_categoria")

    with col2:
        fornecedores = ['Todos'] + sorted([str(x) for x in df_base_filtro['NOME_FORNECEDOR'].dropna().unique().tolist()])
        filtro_fornecedor = st.selectbox("Fornecedor", fornecedores, key="juros_fornecedor")

    with col3:
        # Filtro de tipo de custo
        tipo_custo = st.selectbox("Tipo de Custo", ["Todos", "Apenas Juros", "Apenas Multas", "Juros + Multas"], key="juros_tipo")

    # Aplicar filtros (partir dos titulos com juros/multa)
    df_filtrado = df_com_juros.copy()

    if filtro_categoria != 'Todas':
        df_filtrado = df_filtrado[df_filtrado['DESCRICAO'] == filtro_categoria]

    if filtro_fornecedor != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['NOME_FORNECEDOR'] == filtro_fornecedor]

    if tipo_custo == "Apenas Juros":
        df_filtrado = df_filtrado[df_filtrado['VALOR_JUROS'] > 0]
    elif tipo_custo == "Apenas Multas":
        df_filtrado = df_filtrado[df_filtrado['VALOR_MULTA'] > 0]

    df_com_custos = df_filtrado

    st.divider()

    # ========== KPIs ==========
    total_juros = df_filtrado['VALOR_JUROS'].sum()
    total_multa = df_filtrado['VALOR_MULTA'].sum()
    total_custos = total_juros + total_multa
    total_principal = df_filtrado['VALOR_ORIGINAL'].sum()

    qtd_com_juros = len(df_filtrado[df_filtrado['VALOR_JUROS'] > 0])
    qtd_com_multa = len(df_filtrado[df_filtrado['VALOR_MULTA'] > 0])
    qtd_total = len(df_filtrado)

    pct_juros = (total_juros / total_principal * 100) if total_principal > 0 else 0
    pct_multa = (total_multa / total_principal * 100) if total_principal > 0 else 0
    pct_titulos_juros = (qtd_com_juros / qtd_total * 100) if qtd_total > 0 else 0

    # Juros medio por titulo
    juros_medio = total_juros / qtd_com_juros if qtd_com_juros > 0 else 0

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    col1.metric(
        "Total de Juros",
        formatar_moeda(total_juros),
        f"{qtd_com_juros} titulos"
    )

    col2.metric(
        "Total de Multas",
        formatar_moeda(total_multa),
        f"{qtd_com_multa} titulos"
    )

    col3.metric(
        "Custo Financeiro Total",
        formatar_moeda(total_custos),
        f"{pct_juros + pct_multa:.2f}% do principal"
    )

    col4.metric(
        "% Juros s/ Principal",
        f"{pct_juros:.2f}%",
        f"de {formatar_moeda(total_principal)}"
    )

    col5.metric(
        "% Titulos c/ Juros",
        f"{pct_titulos_juros:.1f}%",
        f"{qtd_com_juros} de {qtd_total}"
    )

    col6.metric(
        "Juros Medio/Titulo",
        formatar_moeda(juros_medio),
        "por titulo com juros"
    )

    st.divider()

    if len(df_com_custos) == 0:
        st.success("Nenhum titulo com juros ou multas no periodo com os filtros selecionados!")
        return

    # ========== ANALISES ==========

    # Linha 1: Por Fornecedor e Evolucao
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Top Fornecedores com Juros")

        df_forn = df_filtrado.groupby('NOME_FORNECEDOR').agg({
            'VALOR_JUROS': 'sum',
            'VALOR_MULTA': 'sum',
            'VALOR_ORIGINAL': 'sum',
            'NUMERO': 'count'
        }).reset_index()
        df_forn.columns = ['Fornecedor', 'Juros', 'Multa', 'Principal', 'Qtd']
        df_forn['Total'] = df_forn['Juros'] + df_forn['Multa']
        df_forn['% Custo'] = (df_forn['Total'] / df_forn['Principal'] * 100).round(2)
        df_forn = df_forn[df_forn['Total'] > 0].sort_values('Total', ascending=False).head(10)

        if len(df_forn) > 0:
            fig = go.Figure()

            fig.add_trace(go.Bar(
                y=df_forn['Fornecedor'].str[:25],
                x=df_forn['Juros'],
                orientation='h',
                name='Juros',
                marker_color=cores['perigo']
            ))

            fig.add_trace(go.Bar(
                y=df_forn['Fornecedor'].str[:25],
                x=df_forn['Multa'],
                orientation='h',
                name='Multas',
                marker_color=cores['alerta']
            ))

            fig.update_layout(
                criar_layout(350, barmode='stack'),
                yaxis={'autorange': 'reversed'},
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
                margin=dict(l=10, r=10, t=30, b=10)
            )

            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("##### Evolucao Mensal")

        df_temp = df_filtrado.copy()
        df_temp['MES'] = df_temp['EMISSAO'].dt.to_period('M')

        df_mes = df_temp.groupby('MES').agg({
            'VALOR_JUROS': 'sum',
            'VALOR_MULTA': 'sum',
            'VALOR_ORIGINAL': 'sum',
            'NUMERO': 'count'
        }).reset_index()
        df_mes['MES'] = df_mes['MES'].astype(str)
        df_mes['PCT_JUROS'] = (df_mes['VALOR_JUROS'] / df_mes['VALOR_ORIGINAL'] * 100).round(2)

        if len(df_mes) >= 2:
            fig = go.Figure()

            fig.add_trace(go.Bar(
                x=df_mes['MES'],
                y=df_mes['VALOR_JUROS'],
                name='Juros',
                marker_color=cores['perigo']
            ))

            fig.add_trace(go.Bar(
                x=df_mes['MES'],
                y=df_mes['VALOR_MULTA'],
                name='Multas',
                marker_color=cores['alerta']
            ))

            fig.add_trace(go.Scatter(
                x=df_mes['MES'],
                y=df_mes['PCT_JUROS'],
                mode='lines+markers',
                name='% Juros',
                yaxis='y2',
                line=dict(color=cores['info'], width=2),
                marker=dict(size=6)
            ))

            fig.update_layout(
                criar_layout(350, barmode='group'),
                yaxis=dict(title='Valor (R$)'),
                yaxis2=dict(title='% Juros', overlaying='y', side='right', showgrid=False),
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
                margin=dict(l=10, r=50, t=30, b=50),
                xaxis_tickangle=-45
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Dados insuficientes para evolucao mensal")

    st.divider()

    # Linha 2: Por Categoria e Por Filial
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Por Categoria")

        df_cat = df_filtrado.groupby('DESCRICAO').agg({
            'VALOR_JUROS': 'sum',
            'VALOR_MULTA': 'sum',
            'VALOR_ORIGINAL': 'sum',
            'NUMERO': 'count'
        }).reset_index()
        df_cat.columns = ['Categoria', 'Juros', 'Multa', 'Principal', 'Qtd']
        df_cat['Total'] = df_cat['Juros'] + df_cat['Multa']
        df_cat['% Custo'] = (df_cat['Total'] / df_cat['Principal'] * 100).round(2)
        df_cat = df_cat[df_cat['Total'] > 0].sort_values('Total', ascending=False).head(10)

        if len(df_cat) > 0:
            fig = go.Figure(go.Bar(
                y=df_cat['Categoria'].str[:25],
                x=df_cat['Total'],
                orientation='h',
                marker_color=cores['perigo'],
                text=[formatar_moeda(v) for v in df_cat['Total']],
                textposition='outside',
                textfont=dict(size=9)
            ))

            fig.update_layout(
                criar_layout(350),
                yaxis={'autorange': 'reversed'},
                margin=dict(l=10, r=100, t=10, b=10)
            )

            st.plotly_chart(fig, use_container_width=True)

    with col2:
        _usar_grupo_juros = 'FILIAL' in df_filtrado.columns and _detectar_multiplos_grupos(df_filtrado)

        if _usar_grupo_juros:
            st.markdown("##### Por Grupo")
            df_filtrado_grupo = df_filtrado.copy()
            df_filtrado_grupo['GRUPO'] = df_filtrado_grupo['FILIAL'].apply(_get_nome_grupo)
            df_fil = df_filtrado_grupo.groupby('GRUPO').agg({
                'VALOR_JUROS': 'sum',
                'VALOR_MULTA': 'sum',
                'VALOR_ORIGINAL': 'sum',
                'NUMERO': 'count'
            }).reset_index()
            df_fil.columns = ['Filial', 'Juros', 'Multa', 'Principal', 'Qtd']
        else:
            st.markdown("##### Por Filial")
            if 'FILIAL' in df_filtrado.columns and 'NOME_FILIAL' in df_filtrado.columns:
                df_filtrado_fil = df_filtrado.copy()
                df_filtrado_fil['_LABEL'] = df_filtrado_fil['FILIAL'].astype(int).astype(str) + ' - ' + df_filtrado_fil['NOME_FILIAL'].str.split(' - ').str[-1].str.strip()
                df_fil = df_filtrado_fil.groupby('_LABEL').agg({
                    'VALOR_JUROS': 'sum',
                    'VALOR_MULTA': 'sum',
                    'VALOR_ORIGINAL': 'sum',
                    'NUMERO': 'count'
                }).reset_index()
                df_fil.columns = ['Filial', 'Juros', 'Multa', 'Principal', 'Qtd']
            else:
                df_fil = df_filtrado.groupby('NOME_FILIAL').agg({
                    'VALOR_JUROS': 'sum',
                    'VALOR_MULTA': 'sum',
                    'VALOR_ORIGINAL': 'sum',
                    'NUMERO': 'count'
                }).reset_index()
                df_fil.columns = ['Filial', 'Juros', 'Multa', 'Principal', 'Qtd']

        df_fil['Total'] = df_fil['Juros'] + df_fil['Multa']
        df_fil['% Custo'] = (df_fil['Total'] / df_fil['Principal'] * 100).round(2)
        df_fil = df_fil[df_fil['Total'] > 0].sort_values('Total', ascending=False)

        if len(df_fil) > 0:
            fig = go.Figure(go.Pie(
                labels=df_fil['Filial'].str[:20],
                values=df_fil['Total'],
                hole=0.4,
                textinfo='percent',
                textfont=dict(size=9),
                hovertemplate='<b>%{label}</b><br>%{value:,.2f}<br>%{percent}<extra></extra>'
            ))

            fig.update_layout(
                criar_layout(350),
                showlegend=True,
                legend=dict(orientation='v', yanchor='middle', y=0.5, xanchor='left', x=1.02, font=dict(size=8)),
                margin=dict(l=10, r=120, t=10, b=10)
            )

            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Linha 3: Analise de Risco e Distribuicao
    st.markdown("##### Analise de Custos Financeiros")

    col1, col2, col3 = st.columns(3)

    with col1:
        # Distribuicao de juros
        st.markdown("###### Distribuicao dos Juros")

        df_com_juros_filter = df_filtrado[df_filtrado['VALOR_JUROS'] > 0]

        if len(df_com_juros_filter) > 0:
            fig = go.Figure(go.Histogram(
                x=df_com_juros_filter['VALOR_JUROS'],
                nbinsx=20,
                marker_color=cores['perigo'],
                opacity=0.7
            ))

            media_juros = df_com_juros_filter['VALOR_JUROS'].mean()
            fig.add_vline(x=media_juros, line_dash="dash", line_color=cores['info'],
                          annotation_text=f"Media: {formatar_moeda(media_juros)}")

            fig.update_layout(
                criar_layout(250),
                xaxis_title='Valor do Juros',
                yaxis_title='Quantidade',
                margin=dict(l=10, r=10, t=10, b=40)
            )

            st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Maiores juros
        st.markdown("###### Maiores Juros Pagos")

        df_top_juros = df_filtrado.nlargest(5, 'VALOR_JUROS')[['NOME_FORNECEDOR', 'VALOR_JUROS', 'VALOR_ORIGINAL', 'EMISSAO']]
        df_top_juros['% Juros'] = (df_top_juros['VALOR_JUROS'] / df_top_juros['VALOR_ORIGINAL'] * 100).round(2)
        df_top_juros['VALOR_JUROS'] = df_top_juros['VALOR_JUROS'].apply(lambda x: formatar_moeda(x, completo=True))
        df_top_juros['VALOR_ORIGINAL'] = df_top_juros['VALOR_ORIGINAL'].apply(lambda x: formatar_moeda(x, completo=True))
        df_top_juros['EMISSAO'] = pd.to_datetime(df_top_juros['EMISSAO']).dt.strftime('%d/%m/%Y')
        df_top_juros['% Juros'] = df_top_juros['% Juros'].apply(lambda x: f"{x:.2f}%")
        df_top_juros.columns = ['Fornecedor', 'Juros', 'Principal', 'Data', '% Juros']

        st.dataframe(df_top_juros, use_container_width=True, hide_index=True, height=200)

    with col3:
        # Maior % de juros sobre principal
        st.markdown("###### Maior % Juros/Principal")

        df_filtrado_temp = df_filtrado[df_filtrado['VALOR_JUROS'] > 0].copy()
        df_filtrado_temp['PCT_JUROS'] = (df_filtrado_temp['VALOR_JUROS'] / df_filtrado_temp['VALOR_ORIGINAL'] * 100)
        df_top_pct = df_filtrado_temp.nlargest(5, 'PCT_JUROS')[['NOME_FORNECEDOR', 'PCT_JUROS', 'VALOR_JUROS', 'VALOR_ORIGINAL']]
        df_top_pct['PCT_JUROS'] = df_top_pct['PCT_JUROS'].apply(lambda x: f"{x:.2f}%")
        df_top_pct['VALOR_JUROS'] = df_top_pct['VALOR_JUROS'].apply(lambda x: formatar_moeda(x, completo=True))
        df_top_pct['VALOR_ORIGINAL'] = df_top_pct['VALOR_ORIGINAL'].apply(lambda x: formatar_moeda(x, completo=True))
        df_top_pct.columns = ['Fornecedor', '% Juros', 'Juros', 'Principal']

        st.dataframe(df_top_pct, use_container_width=True, hide_index=True, height=200)

    st.divider()

    # Linha 4: Comparativo Juros vs Multas
    st.markdown("##### Comparativo: Juros vs Multas")

    col1, col2 = st.columns(2)

    with col1:
        # Pizza Juros vs Multas
        fig = go.Figure(go.Pie(
            labels=['Juros', 'Multas'],
            values=[total_juros, total_multa],
            hole=0.5,
            marker=dict(colors=[cores['perigo'], cores['alerta']]),
            textinfo='percent+label',
            textfont=dict(size=12),
            hovertemplate='<b>%{label}</b><br>R$ %{value:,.2f}<br>%{percent}<extra></extra>'
        ))

        fig.update_layout(
            criar_layout(280),
            showlegend=False,
            margin=dict(l=10, r=10, t=10, b=10)
        )

        st.plotly_chart(fig, use_container_width=True)

        st.markdown(f"""
        | Tipo | Valor | % do Total |
        |------|-------|------------|
        | Juros | {formatar_moeda(total_juros)} | {(total_juros/total_custos*100) if total_custos > 0 else 0:.1f}% |
        | Multas | {formatar_moeda(total_multa)} | {(total_multa/total_custos*100) if total_custos > 0 else 0:.1f}% |
        | **Total** | **{formatar_moeda(total_custos)}** | **100%** |
        """)

    with col2:
        # Titulos com ambos (juros e multa)
        st.markdown("###### Titulos com Juros E Multas")

        df_ambos = df_filtrado[(df_filtrado['VALOR_JUROS'] > 0) & (df_filtrado['VALOR_MULTA'] > 0)]
        qtd_ambos = len(df_ambos)
        total_ambos = df_ambos['VALOR_JUROS'].sum() + df_ambos['VALOR_MULTA'].sum()

        st.metric("Titulos com Juros + Multa", qtd_ambos, f"Total: {formatar_moeda(total_ambos)}")

        if len(df_ambos) > 0:
            df_ambos_show = df_ambos.nlargest(5, 'VALOR_JUROS')[['NOME_FORNECEDOR', 'VALOR_JUROS', 'VALOR_MULTA', 'VALOR_ORIGINAL']]
            df_ambos_show['Total'] = df_ambos_show['VALOR_JUROS'] + df_ambos_show['VALOR_MULTA']
            df_ambos_show['VALOR_JUROS'] = df_ambos_show['VALOR_JUROS'].apply(lambda x: formatar_moeda(x, completo=True))
            df_ambos_show['VALOR_MULTA'] = df_ambos_show['VALOR_MULTA'].apply(lambda x: formatar_moeda(x, completo=True))
            df_ambos_show['Total'] = df_ambos_show['Total'].apply(lambda x: formatar_moeda(x, completo=True))
            df_ambos_show['VALOR_ORIGINAL'] = df_ambos_show['VALOR_ORIGINAL'].apply(lambda x: formatar_moeda(x, completo=True))
            df_ambos_show.columns = ['Fornecedor', 'Juros', 'Multa', 'Principal', 'Total']

            st.dataframe(df_ambos_show, use_container_width=True, hide_index=True, height=180)

    st.divider()

    # ========== TABELAS DETALHADAS ==========
    st.markdown("##### Tabelas Detalhadas")

    tab_forn, tab_cat, tab_fil, tab_titulos = st.tabs(["Por Fornecedor", "Por Categoria", "Por Filial", "Titulos"])

    with tab_forn:
        df_tab_forn = df_forn.copy()
        df_tab_forn['Juros'] = df_tab_forn['Juros'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab_forn['Multa'] = df_tab_forn['Multa'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab_forn['Total'] = df_tab_forn['Total'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab_forn['Principal'] = df_tab_forn['Principal'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab_forn['% Custo'] = df_tab_forn['% Custo'].apply(lambda x: f"{x:.2f}%")

        st.dataframe(df_tab_forn[['Fornecedor', 'Qtd', 'Principal', 'Juros', 'Multa', 'Total', '% Custo']],
                     use_container_width=True, hide_index=True, height=350)

    with tab_cat:
        df_tab_cat = df_cat.copy()
        df_tab_cat['Juros'] = df_tab_cat['Juros'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab_cat['Multa'] = df_tab_cat['Multa'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab_cat['Total'] = df_tab_cat['Total'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab_cat['Principal'] = df_tab_cat['Principal'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab_cat['% Custo'] = df_tab_cat['% Custo'].apply(lambda x: f"{x:.2f}%")

        st.dataframe(df_tab_cat[['Categoria', 'Qtd', 'Principal', 'Juros', 'Multa', 'Total', '% Custo']],
                     use_container_width=True, hide_index=True, height=350)

    with tab_fil:
        df_tab_fil = df_fil.copy()
        df_tab_fil['Juros'] = df_tab_fil['Juros'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab_fil['Multa'] = df_tab_fil['Multa'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab_fil['Total'] = df_tab_fil['Total'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab_fil['Principal'] = df_tab_fil['Principal'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab_fil['% Custo'] = df_tab_fil['% Custo'].apply(lambda x: f"{x:.2f}%")

        st.dataframe(df_tab_fil[['Filial', 'Qtd', 'Principal', 'Juros', 'Multa', 'Total', '% Custo']],
                     use_container_width=True, hide_index=True, height=350)

    with tab_titulos:
        col1, col2 = st.columns([1, 3])
        with col1:
            ordenar = st.selectbox("Ordenar por", ["Maior juros", "Maior multa", "Maior valor", "Mais recente", "Maior % juros"], key="juros_ordem")

        df_show = df_com_custos.copy()
        df_show['PCT_JUROS'] = (df_show['VALOR_JUROS'] / df_show['VALOR_ORIGINAL'] * 100)

        if ordenar == "Maior juros":
            df_show = df_show.sort_values('VALOR_JUROS', ascending=False)
        elif ordenar == "Maior multa":
            df_show = df_show.sort_values('VALOR_MULTA', ascending=False)
        elif ordenar == "Maior valor":
            df_show = df_show.sort_values('VALOR_ORIGINAL', ascending=False)
        elif ordenar == "Maior % juros":
            df_show = df_show.sort_values('PCT_JUROS', ascending=False)
        else:
            df_show = df_show.sort_values('EMISSAO', ascending=False)

        df_show = df_show.head(100)

        colunas = ['NOME_FILIAL', 'NOME_FORNECEDOR', 'DESCRICAO', 'EMISSAO', 'VENCIMENTO',
                   'VALOR_ORIGINAL', 'VALOR_JUROS', 'VALOR_MULTA', 'PCT_JUROS', 'SALDO', 'STATUS']
        colunas_disp = [c for c in colunas if c in df_show.columns]
        df_tab = df_show[colunas_disp].copy()

        for col in ['EMISSAO', 'VENCIMENTO']:
            if col in df_tab.columns:
                df_tab[col] = pd.to_datetime(df_tab[col], errors='coerce').dt.strftime('%d/%m/%Y')

        for col in ['VALOR_ORIGINAL', 'VALOR_JUROS', 'VALOR_MULTA', 'SALDO']:
            if col in df_tab.columns:
                df_tab[col] = df_tab[col].apply(lambda x: formatar_moeda(x, completo=True))

        if 'PCT_JUROS' in df_tab.columns:
            df_tab['PCT_JUROS'] = df_tab['PCT_JUROS'].apply(lambda x: f"{x:.2f}%")

        nomes = {
            'NOME_FILIAL': 'Filial',
            'NOME_FORNECEDOR': 'Fornecedor',
            'DESCRICAO': 'Categoria',
            'EMISSAO': 'Emissao',
            'VENCIMENTO': 'Vencimento',
            'VALOR_ORIGINAL': 'Principal',
            'VALOR_JUROS': 'Juros',
            'VALOR_MULTA': 'Multa',
            'PCT_JUROS': '% Juros',
            'SALDO': 'Pendente',
            'STATUS': 'Status'
        }
        df_tab.columns = [nomes.get(c, c) for c in df_tab.columns]

        st.dataframe(df_tab, use_container_width=True, hide_index=True, height=350)
        st.caption(f"Exibindo {len(df_tab)} titulos com juros/multas")


# ============================================================
# SECAO 2: OPERACOES EM DOLAR
# ============================================================

def _render_secao_cambio(df, df_dolar, df_real, cores):
    """Secao dedicada a operacoes em moeda estrangeira (dolar) - com filtros e analises"""

    if len(df_dolar) == 0:
        st.info("Nenhuma operacao em dolar no periodo.")
        return

    # ========== FILTROS ==========
    st.markdown("##### Filtros")
    col1, col2, col3 = st.columns(3)

    with col1:
        # Filtro de categoria
        categorias = ['Todas'] + sorted([str(x) for x in df_dolar['DESCRICAO'].dropna().unique().tolist()])
        filtro_categoria = st.selectbox("Categoria", categorias, key="dolar_categoria")

    with col2:
        # Filtro de fornecedor
        fornecedores = ['Todos'] + sorted([str(x) for x in df_dolar['NOME_FORNECEDOR'].dropna().unique().tolist()])
        filtro_fornecedor = st.selectbox("Fornecedor", fornecedores, key="dolar_fornecedor")

    with col3:
        # Filtro de status
        status_opcoes = ['Todos', 'Pendentes', 'Pagos', 'Vencidos']
        filtro_status = st.selectbox("Status", status_opcoes, key="dolar_status")

    # Aplicar filtros
    df_filtrado = df_dolar.copy()

    if filtro_categoria != 'Todas':
        df_filtrado = df_filtrado[df_filtrado['DESCRICAO'] == filtro_categoria]

    if filtro_fornecedor != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['NOME_FORNECEDOR'] == filtro_fornecedor]

    if filtro_status == 'Pendentes':
        df_filtrado = df_filtrado[df_filtrado['SALDO'] > 0]
    elif filtro_status == 'Pagos':
        df_filtrado = df_filtrado[df_filtrado['SALDO'] == 0]
    elif filtro_status == 'Vencidos':
        df_filtrado = df_filtrado[df_filtrado['STATUS'] == 'Vencido']

    st.divider()

    # ========== KPIs (com dados filtrados) ==========
    total_usd = df_filtrado['VALOR_ORIGINAL'].sum()
    total_brl = df_filtrado['VALOR_REAL'].sum()
    total_saldo = df_filtrado['SALDO'].sum()
    total_pago = total_brl - total_saldo

    tx_media = df_filtrado['TX_MOEDA'].mean() if len(df_filtrado) > 0 else 0
    tx_min = df_filtrado['TX_MOEDA'].min() if len(df_filtrado) > 0 else 0
    tx_max = df_filtrado['TX_MOEDA'].max() if len(df_filtrado) > 0 else 0

    # Variacao cambial (diferenca entre taxa max e min)
    variacao = ((tx_max - tx_min) / tx_min * 100) if tx_min > 0 else 0

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    col1.metric(
        "Total em USD",
        f"$ {total_usd:,.2f}",
        f"{len(df_filtrado)} titulos"
    )

    col2.metric(
        "Valor em Reais",
        formatar_moeda(total_brl),
        "convertido"
    )

    col3.metric(
        "Saldo Pendente",
        formatar_moeda(total_saldo),
        f"{len(df_filtrado[df_filtrado['SALDO'] > 0])} pendentes"
    )

    col4.metric(
        "Taxa Media",
        f"R$ {tx_media:.4f}" if tx_media > 0 else "-",
        "USD/BRL"
    )

    col5.metric(
        "Taxa Min / Max",
        f"R$ {tx_min:.2f} - {tx_max:.2f}" if tx_min > 0 else "-",
        f"Variacao: {variacao:.1f}%"
    )

    col6.metric(
        "Ja Pago",
        formatar_moeda(total_pago),
        f"{len(df_filtrado[df_filtrado['SALDO'] == 0])} pagos"
    )

    st.divider()

    # ========== ANALISES ==========

    # Linha 1: Visao geral e evolucao
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Distribuicao por Categoria")

        df_cat = df_filtrado.groupby('DESCRICAO').agg({
            'VALOR_ORIGINAL': 'sum',
            'VALOR_REAL': 'sum',
            'NUMERO': 'count'
        }).reset_index()
        df_cat.columns = ['Categoria', 'USD', 'BRL', 'Qtd']
        df_cat = df_cat.sort_values('USD', ascending=False).head(10)

        if len(df_cat) > 0:
            fig = go.Figure(go.Bar(
                y=df_cat['Categoria'].str[:25],
                x=df_cat['USD'],
                orientation='h',
                marker_color=cores['info'],
                text=[f"$ {v:,.0f}" for v in df_cat['USD']],
                textposition='outside',
                textfont=dict(size=9)
            ))

            fig.update_layout(
                criar_layout(350),
                yaxis={'autorange': 'reversed'},
                margin=dict(l=10, r=80, t=10, b=10)
            )

            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("##### Evolucao Mensal")

        df_temp = df_filtrado.copy()
        df_temp['MES'] = df_temp['EMISSAO'].dt.to_period('M')

        df_mes = df_temp.groupby('MES').agg({
            'VALOR_ORIGINAL': 'sum',
            'VALOR_REAL': 'sum',
            'TX_MOEDA': 'mean',
            'NUMERO': 'count'
        }).reset_index()
        df_mes['MES'] = df_mes['MES'].astype(str)

        if len(df_mes) >= 2:
            fig = go.Figure()

            fig.add_trace(go.Bar(
                x=df_mes['MES'],
                y=df_mes['VALOR_ORIGINAL'],
                name='Valor USD',
                marker_color=cores['info'],
                opacity=0.7
            ))

            fig.add_trace(go.Scatter(
                x=df_mes['MES'],
                y=df_mes['TX_MOEDA'],
                mode='lines+markers',
                name='Taxa USD/BRL',
                yaxis='y2',
                line=dict(color=cores['alerta'], width=3),
                marker=dict(size=8)
            ))

            fig.update_layout(
                criar_layout(350),
                yaxis=dict(title='Valor USD ($)'),
                yaxis2=dict(title='Taxa USD/BRL', overlaying='y', side='right', showgrid=False),
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
                margin=dict(l=10, r=60, t=30, b=50),
                xaxis_tickangle=-45
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Dados insuficientes para evolucao mensal")

    st.divider()

    # Linha 2: Por Fornecedor e Por Filial
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Top Fornecedores em Dolar")

        df_forn = df_filtrado.groupby('NOME_FORNECEDOR').agg({
            'VALOR_ORIGINAL': 'sum',
            'VALOR_REAL': 'sum',
            'TX_MOEDA': 'mean',
            'SALDO': 'sum',
            'NUMERO': 'count'
        }).reset_index()
        df_forn.columns = ['Fornecedor', 'USD', 'BRL', 'Taxa Media', 'Saldo', 'Qtd']
        df_forn['Pago'] = df_forn['BRL'] - df_forn['Saldo']
        df_forn['% Pago'] = (df_forn['Pago'] / df_forn['BRL'] * 100).round(1)
        df_forn = df_forn.sort_values('USD', ascending=False).head(10)

        # Grafico
        fig = go.Figure()

        fig.add_trace(go.Bar(
            y=df_forn['Fornecedor'].str[:25],
            x=df_forn['Pago'],
            orientation='h',
            name='Pago',
            marker_color=cores['sucesso']
        ))

        fig.add_trace(go.Bar(
            y=df_forn['Fornecedor'].str[:25],
            x=df_forn['Saldo'],
            orientation='h',
            name='Saldo Pendente',
            marker_color=cores['alerta']
        ))

        fig.update_layout(
            criar_layout(350, barmode='stack'),
            yaxis={'autorange': 'reversed'},
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
            margin=dict(l=10, r=10, t=30, b=10)
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        _usar_grupo_cambio = 'FILIAL' in df_filtrado.columns and _detectar_multiplos_grupos(df_filtrado)

        if _usar_grupo_cambio:
            st.markdown("##### Por Grupo")
            df_filtrado_grupo = df_filtrado.copy()
            df_filtrado_grupo['GRUPO'] = df_filtrado_grupo['FILIAL'].apply(_get_nome_grupo)
            df_fil = df_filtrado_grupo.groupby('GRUPO').agg({
                'VALOR_ORIGINAL': 'sum',
                'VALOR_REAL': 'sum',
                'TX_MOEDA': 'mean',
                'SALDO': 'sum',
                'NUMERO': 'count'
            }).reset_index()
            df_fil.columns = ['Filial', 'USD', 'BRL', 'Taxa Media', 'Saldo', 'Qtd']
        else:
            st.markdown("##### Por Filial")
            if 'FILIAL' in df_filtrado.columns and 'NOME_FILIAL' in df_filtrado.columns:
                df_filtrado_fil = df_filtrado.copy()
                df_filtrado_fil['_LABEL'] = df_filtrado_fil['FILIAL'].astype(int).astype(str) + ' - ' + df_filtrado_fil['NOME_FILIAL'].str.split(' - ').str[-1].str.strip()
                df_fil = df_filtrado_fil.groupby('_LABEL').agg({
                    'VALOR_ORIGINAL': 'sum',
                    'VALOR_REAL': 'sum',
                    'TX_MOEDA': 'mean',
                    'SALDO': 'sum',
                    'NUMERO': 'count'
                }).reset_index()
                df_fil.columns = ['Filial', 'USD', 'BRL', 'Taxa Media', 'Saldo', 'Qtd']
            else:
                df_fil = df_filtrado.groupby('NOME_FILIAL').agg({
                    'VALOR_ORIGINAL': 'sum',
                    'VALOR_REAL': 'sum',
                    'TX_MOEDA': 'mean',
                    'SALDO': 'sum',
                    'NUMERO': 'count'
                }).reset_index()
                df_fil.columns = ['Filial', 'USD', 'BRL', 'Taxa Media', 'Saldo', 'Qtd']

        df_fil = df_fil.sort_values('USD', ascending=False)

        if len(df_fil) > 0:
            fig = go.Figure(go.Pie(
                labels=df_fil['Filial'].str[:20],
                values=df_fil['USD'],
                hole=0.4,
                textinfo='percent',
                textfont=dict(size=9),
                hovertemplate='<b>%{label}</b><br>$ %{value:,.2f}<br>%{percent}<extra></extra>'
            ))

            fig.update_layout(
                criar_layout(350),
                showlegend=True,
                legend=dict(orientation='v', yanchor='middle', y=0.5, xanchor='left', x=1.02, font=dict(size=8)),
                margin=dict(l=10, r=120, t=10, b=10)
            )

            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Linha 3: Analise de Taxa de Cambio
    st.markdown("##### Analise de Taxa de Cambio")

    col1, col2, col3 = st.columns(3)

    with col1:
        # Distribuicao de taxas
        st.markdown("###### Distribuicao das Taxas")

        fig = go.Figure(go.Histogram(
            x=df_filtrado['TX_MOEDA'],
            nbinsx=20,
            marker_color=cores['info'],
            opacity=0.7
        ))

        fig.add_vline(x=tx_media, line_dash="dash", line_color=cores['perigo'],
                      annotation_text=f"Media: R$ {tx_media:.4f}")

        fig.update_layout(
            criar_layout(250),
            xaxis_title='Taxa USD/BRL',
            yaxis_title='Quantidade',
            margin=dict(l=10, r=10, t=10, b=40)
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Maiores taxas
        st.markdown("###### Maiores Taxas Pagas")

        df_top_taxa = df_filtrado.nlargest(5, 'TX_MOEDA')[['NOME_FORNECEDOR', 'TX_MOEDA', 'VALOR_ORIGINAL', 'EMISSAO']]
        df_top_taxa['TX_MOEDA'] = df_top_taxa['TX_MOEDA'].apply(lambda x: f"R$ {x:.4f}")
        df_top_taxa['VALOR_ORIGINAL'] = df_top_taxa['VALOR_ORIGINAL'].apply(lambda x: f"$ {x:,.2f}")
        df_top_taxa['EMISSAO'] = pd.to_datetime(df_top_taxa['EMISSAO']).dt.strftime('%d/%m/%Y')
        df_top_taxa.columns = ['Fornecedor', 'Taxa', 'USD', 'Data']

        st.dataframe(df_top_taxa, use_container_width=True, hide_index=True, height=200)

    with col3:
        # Menores taxas
        st.markdown("###### Menores Taxas Pagas")

        df_low_taxa = df_filtrado.nsmallest(5, 'TX_MOEDA')[['NOME_FORNECEDOR', 'TX_MOEDA', 'VALOR_ORIGINAL', 'EMISSAO']]
        df_low_taxa['TX_MOEDA'] = df_low_taxa['TX_MOEDA'].apply(lambda x: f"R$ {x:.4f}")
        df_low_taxa['VALOR_ORIGINAL'] = df_low_taxa['VALOR_ORIGINAL'].apply(lambda x: f"$ {x:,.2f}")
        df_low_taxa['EMISSAO'] = pd.to_datetime(df_low_taxa['EMISSAO']).dt.strftime('%d/%m/%Y')
        df_low_taxa.columns = ['Fornecedor', 'Taxa', 'USD', 'Data']

        st.dataframe(df_low_taxa, use_container_width=True, hide_index=True, height=200)

    st.divider()

    # Linha 4: Tabelas detalhadas
    st.markdown("##### Tabelas Detalhadas")

    tab_forn, tab_cat, tab_titulos = st.tabs(["Por Fornecedor", "Por Categoria", "Titulos"])

    with tab_forn:
        df_tab_forn = df_forn.copy()
        df_tab_forn['USD'] = df_tab_forn['USD'].apply(lambda x: f"$ {x:,.2f}")
        df_tab_forn['BRL'] = df_tab_forn['BRL'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab_forn['Saldo'] = df_tab_forn['Saldo'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab_forn['Pago'] = df_tab_forn['Pago'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab_forn['Taxa Media'] = df_tab_forn['Taxa Media'].apply(lambda x: f"R$ {x:.4f}")
        df_tab_forn['% Pago'] = df_tab_forn['% Pago'].apply(lambda x: f"{x:.1f}%")

        st.dataframe(df_tab_forn[['Fornecedor', 'Qtd', 'USD', 'BRL', 'Pago', 'Saldo', 'Taxa Media', '% Pago']],
                     use_container_width=True, hide_index=True, height=350)

    with tab_cat:
        df_tab_cat = df_cat.copy()
        df_tab_cat['USD'] = df_tab_cat['USD'].apply(lambda x: f"$ {x:,.2f}")
        df_tab_cat['BRL'] = df_tab_cat['BRL'].apply(lambda x: formatar_moeda(x, completo=True))

        st.dataframe(df_tab_cat, use_container_width=True, hide_index=True, height=350)

    with tab_titulos:
        col1, col2 = st.columns([1, 3])
        with col1:
            ordenar = st.selectbox("Ordenar por", ["Maior valor USD", "Maior taxa", "Mais recente", "Maior saldo"], key="dolar_ordem")

        df_show = df_filtrado.copy()
        if ordenar == "Maior valor USD":
            df_show = df_show.sort_values('VALOR_ORIGINAL', ascending=False)
        elif ordenar == "Maior taxa":
            df_show = df_show.sort_values('TX_MOEDA', ascending=False)
        elif ordenar == "Maior saldo":
            df_show = df_show.sort_values('SALDO', ascending=False)
        else:
            df_show = df_show.sort_values('EMISSAO', ascending=False)

        df_show = df_show.head(100)

        colunas = ['NOME_FILIAL', 'NOME_FORNECEDOR', 'DESCRICAO', 'EMISSAO', 'VENCIMENTO',
                   'VALOR_ORIGINAL', 'TX_MOEDA', 'VALOR_REAL', 'SALDO', 'STATUS']
        colunas_disp = [c for c in colunas if c in df_show.columns]
        df_tab = df_show[colunas_disp].copy()

        for col in ['EMISSAO', 'VENCIMENTO']:
            if col in df_tab.columns:
                df_tab[col] = pd.to_datetime(df_tab[col], errors='coerce').dt.strftime('%d/%m/%Y')

        if 'VALOR_ORIGINAL' in df_tab.columns:
            df_tab['VALOR_ORIGINAL'] = df_tab['VALOR_ORIGINAL'].apply(lambda x: f"$ {x:,.2f}")

        if 'TX_MOEDA' in df_tab.columns:
            df_tab['TX_MOEDA'] = df_tab['TX_MOEDA'].apply(lambda x: f"R$ {x:.4f}")

        for col in ['VALOR_REAL', 'SALDO']:
            if col in df_tab.columns:
                df_tab[col] = df_tab[col].apply(lambda x: formatar_moeda(x, completo=True))

        nomes = {
            'NOME_FILIAL': 'Filial',
            'NOME_FORNECEDOR': 'Fornecedor',
            'DESCRICAO': 'Categoria',
            'EMISSAO': 'Emissao',
            'VENCIMENTO': 'Vencimento',
            'VALOR_ORIGINAL': 'Valor USD',
            'TX_MOEDA': 'Taxa',
            'VALOR_REAL': 'Valor em R$',
            'SALDO': 'Pendente',
            'STATUS': 'Status'
        }
        df_tab.columns = [nomes.get(c, c) for c in df_tab.columns]

        st.dataframe(df_tab, use_container_width=True, hide_index=True, height=350)
        st.caption(f"Exibindo {len(df_tab)} operacoes em dolar")
