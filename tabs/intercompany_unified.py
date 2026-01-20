"""
Intercompany Unificado - Conciliacao entre Filiais
Dashboard Financeiro - Grupo Progresso

REGRA: Intercompany = operacoes entre FILIAIS do grupo
Se FILIAL X paga para FILIAL Y, entao FILIAL Y deve ter a receber de FILIAL X
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from config.theme import get_cores
from config.settings import INTERCOMPANY_PATTERNS, INTERCOMPANY_PADRONIZACAO
from data.loader import carregar_dados
from data.loader_receber import carregar_dados_receber
from utils.formatters import formatar_moeda, formatar_numero


# Mapeamento de filiais para padronizacao (usando settings como fonte unica)
# IMPORTANTE: Ordem importa - padroes mais especificos primeiro
FILIAIS_PADRAO = {
    'PROGRESSO AGROINDUSTRIAL': ['PROGRESSO AGROINDUST', 'PROGRESSO MATRIZ'],
    'PROGRESSO AGRICOLA': ['PROGRESSO AGRICOLA'],  # Filial separada
    'PENINSULA': ['PENINSULA', 'FAZENDA PENINSULA'],
    'OURO BRANCO': ['PROGRESSO FBO', 'OURO BRANCO', 'FAZENDA OURO BRANCO', 'SEMENTES OURO BRANCO', 'OURO BRANCO INSUMOS'],  # FBO = Fazenda Ouro Branco
    'TROPICAL': ['TROPICAL', 'FAZENDA TROPICAL', 'HOTEL TROPICAL', 'POUSADA TROPICAL', 'TROPICAL AGROPART'],
    'BRASIL AGRICOLA': ['BRASIL AGRICOLA'],
    'AG3 AGRO': ['AG3 AGRO'],
    'CG3 AGRO': ['CG3 AGRO'],
    'RAINHA DA SERRA': ['RAINHA DA SERRA'],
    'SDS PARTICIPACOES': ['SDS PARTICIPACOES'],
    'IMPERIAL': ['IMPERIAL'],
    'FAMILIA SANDERS': ['CORNELIO', 'GREICY', 'GREGORY SANDERS', 'GUEBERSON SANDERS'],
}


def identificar_filial(nome):
    """Identifica a qual filial padrao o nome pertence"""
    if pd.isna(nome):
        return None
    nome_upper = str(nome).upper()
    for filial, padroes in FILIAIS_PADRAO.items():
        for padrao in padroes:
            if padrao in nome_upper:
                return filial
    return None


def carregar_dados_intercompany():
    """Carrega e processa dados intercompany de ambas as bases"""

    # Carregar dados brutos
    df_pagar_raw, _, _ = carregar_dados()
    df_receber_raw, _, _ = carregar_dados_receber()

    # Identificar filiais
    df_pagar_raw['FILIAL_ORIGEM'] = df_pagar_raw['NOME_FILIAL'].apply(identificar_filial)
    df_pagar_raw['FILIAL_DESTINO'] = df_pagar_raw['NOME_FORNECEDOR'].apply(identificar_filial)

    df_receber_raw['FILIAL_ORIGEM'] = df_receber_raw['NOME_FILIAL'].apply(identificar_filial)
    df_receber_raw['FILIAL_DESTINO'] = df_receber_raw['NOME_CLIENTE'].apply(identificar_filial)

    # Filtrar apenas intercompany (onde FORNECEDOR/CLIENTE é uma filial do grupo)
    df_pagar = df_pagar_raw[df_pagar_raw['FILIAL_DESTINO'].notna()].copy()
    df_receber = df_receber_raw[df_receber_raw['FILIAL_DESTINO'].notna()].copy()

    return df_pagar, df_receber


def calcular_conciliacao(df_pagar, df_receber):
    """Calcula a conciliacao entre o que uma filial paga e outra recebe"""

    # A PAGAR: FILIAL_ORIGEM paga para FILIAL_DESTINO
    pagar_resumo = df_pagar.groupby(['FILIAL_ORIGEM', 'FILIAL_DESTINO']).agg({
        'SALDO': 'sum',
        'VALOR_ORIGINAL': 'sum',
        'NUMERO': 'count'
    }).reset_index()
    pagar_resumo.columns = ['DE', 'PARA', 'SALDO_PAGAR', 'VALOR_PAGAR', 'QTD_PAGAR']

    # A RECEBER: FILIAL_ORIGEM recebe de FILIAL_DESTINO
    # Invertendo a logica: se FILIAL X recebe de CLIENTE Y, entao Y paga para X
    receber_resumo = df_receber.groupby(['FILIAL_DESTINO', 'FILIAL_ORIGEM']).agg({
        'SALDO': 'sum',
        'VALOR_ORIGINAL': 'sum',
        'NUMERO': 'count'
    }).reset_index()
    receber_resumo.columns = ['DE', 'PARA', 'SALDO_RECEBER', 'VALOR_RECEBER', 'QTD_RECEBER']

    # Merge para comparar
    conciliacao = pd.merge(pagar_resumo, receber_resumo, on=['DE', 'PARA'], how='outer').fillna(0)
    conciliacao['DIFERENCA'] = conciliacao['SALDO_PAGAR'] - conciliacao['SALDO_RECEBER']
    conciliacao['DIFERENCA_ABS'] = conciliacao['DIFERENCA'].abs()

    return conciliacao


def render_intercompany_unificado(data_inicio=None, data_fim=None):
    """Renderiza a pagina unificada de Intercompany"""

    cores = get_cores()

    # Carregar dados
    df_pagar, df_receber = carregar_dados_intercompany()

    # Aplicar filtro de data se fornecido
    if data_inicio is not None and data_fim is not None:
        if 'EMISSAO' in df_pagar.columns:
            df_pagar = df_pagar[(df_pagar['EMISSAO'].dt.date >= data_inicio) & (df_pagar['EMISSAO'].dt.date <= data_fim)]
        if 'EMISSAO' in df_receber.columns:
            df_receber = df_receber[(df_receber['EMISSAO'].dt.date >= data_inicio) & (df_receber['EMISSAO'].dt.date <= data_fim)]

    # Calcular conciliacao
    conciliacao = calcular_conciliacao(df_pagar, df_receber)

    # ========== METRICAS PRINCIPAIS ==========
    total_pagar = df_pagar['SALDO'].sum()
    total_receber = df_receber['SALDO'].sum()
    diferenca_total = conciliacao['DIFERENCA'].sum()
    diferenca_abs = conciliacao['DIFERENCA_ABS'].sum()

    # Pares conciliados (diferenca < 1000)
    pares_ok = len(conciliacao[conciliacao['DIFERENCA_ABS'] < 1000])
    pares_total = len(conciliacao[conciliacao['DIFERENCA_ABS'] > 0])
    pct_conciliado = (pares_ok / pares_total * 100) if pares_total > 0 else 100

    # Header principal
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, {cores['primaria']}15, {cores['card']});
                border: 2px solid {cores['primaria']}; border-radius: 16px;
                padding: 1.5rem; margin-bottom: 1.25rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
            <div>
                <p style="color: {cores['primaria']}; font-size: 0.9rem; font-weight: 600; margin: 0;">
                    CONCILIACAO INTERCOMPANY</p>
                <p style="color: {cores['texto']}; font-size: 2rem; font-weight: 700; margin: 0.25rem 0;">
                    Operacoes entre Filiais do Grupo</p>
                <p style="color: {cores['texto_secundario']}; font-size: 0.85rem; margin: 0;">
                    Comparativo: A Pagar vs A Receber entre filiais</p>
            </div>
            <div style="display: flex; gap: 1.5rem; flex-wrap: wrap;">
                <div style="text-align: center; padding: 1rem; background: {cores['perigo']}15; border-radius: 10px; min-width: 130px;">
                    <p style="color: {cores['perigo']}; font-size: 0.7rem; font-weight: 600; margin: 0;">A PAGAR</p>
                    <p style="color: {cores['perigo']}; font-size: 1.3rem; font-weight: 700; margin: 0.2rem 0;">
                        {formatar_moeda(total_pagar)}</p>
                    <p style="color: {cores['texto_secundario']}; font-size: 0.65rem; margin: 0;">
                        {len(df_pagar)} titulos</p>
                </div>
                <div style="text-align: center; padding: 1rem; background: {cores['sucesso']}15; border-radius: 10px; min-width: 130px;">
                    <p style="color: {cores['sucesso']}; font-size: 0.7rem; font-weight: 600; margin: 0;">A RECEBER</p>
                    <p style="color: {cores['sucesso']}; font-size: 1.3rem; font-weight: 700; margin: 0.2rem 0;">
                        {formatar_moeda(total_receber)}</p>
                    <p style="color: {cores['texto_secundario']}; font-size: 0.65rem; margin: 0;">
                        {len(df_receber)} titulos</p>
                </div>
                <div style="text-align: center; padding: 1rem; background: {cores['alerta']}15; border-radius: 10px; min-width: 130px;">
                    <p style="color: {cores['alerta']}; font-size: 0.7rem; font-weight: 600; margin: 0;">DIFERENCA</p>
                    <p style="color: {cores['alerta']}; font-size: 1.3rem; font-weight: 700; margin: 0.2rem 0;">
                        {formatar_moeda(diferenca_abs)}</p>
                    <p style="color: {cores['texto_secundario']}; font-size: 0.65rem; margin: 0;">
                        a conciliar</p>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ========== TABS ==========
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Conciliacao", "Matriz", "Por Filial", "Detalhes A Pagar", "Detalhes A Receber"
    ])

    with tab1:
        _render_conciliacao(conciliacao, cores)

    with tab2:
        _render_matriz(df_pagar, df_receber, cores)

    with tab3:
        _render_por_filial(df_pagar, df_receber, conciliacao, cores)

    with tab4:
        _render_detalhes_pagar(df_pagar, cores)

    with tab5:
        _render_detalhes_receber(df_receber, cores)


def _render_conciliacao(conciliacao, cores):
    """Renderiza a aba de conciliacao"""

    st.markdown("##### Analise de Conciliacao: A Pagar vs A Receber")
    st.caption("Se FILIAL X paga para FILIAL Y, entao Y deve ter a receber de X. A diferenca indica valores nao conciliados.")

    # KPIs
    col1, col2, col3, col4 = st.columns(4)

    total_pagar = conciliacao['SALDO_PAGAR'].sum()
    total_receber = conciliacao['SALDO_RECEBER'].sum()
    diferenca = conciliacao['DIFERENCA'].sum()

    with col1:
        st.metric("Total A Pagar IC", formatar_moeda(total_pagar))
    with col2:
        st.metric("Total A Receber IC", formatar_moeda(total_receber))
    with col3:
        cor_dif = "inverse" if diferenca > 0 else "normal"
        st.metric("Diferenca Liquida", formatar_moeda(diferenca), delta_color=cor_dif)
    with col4:
        pares_divergentes = len(conciliacao[conciliacao['DIFERENCA_ABS'] >= 1000])
        st.metric("Pares Divergentes", pares_divergentes)

    st.divider()

    # Grafico de divergencias
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("##### Maiores Divergencias")

        # Top divergencias
        top_div = conciliacao[conciliacao['DIFERENCA_ABS'] >= 1000].nlargest(15, 'DIFERENCA_ABS').copy()
        top_div['PAR'] = top_div['DE'] + ' -> ' + top_div['PARA']

        if len(top_div) > 0:
            colors = [cores['perigo'] if x > 0 else cores['sucesso'] for x in top_div['DIFERENCA']]

            fig = go.Figure()
            fig.add_trace(go.Bar(
                y=top_div['PAR'],
                x=top_div['DIFERENCA'],
                orientation='h',
                marker_color=colors,
                text=[formatar_moeda(x) for x in top_div['DIFERENCA']],
                textposition='outside',
                textfont=dict(size=9, color=cores['texto'])
            ))

            fig.add_vline(x=0, line_dash="dash", line_color=cores['texto_secundario'], line_width=1)

            fig.update_layout(
                height=400,
                margin=dict(l=10, r=100, t=10, b=10),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showticklabels=False, showgrid=True, gridcolor=cores['borda'], zeroline=False),
                yaxis=dict(tickfont=dict(color=cores['texto'], size=9))
            )

            st.plotly_chart(fig, use_container_width=True)
            st.caption("Vermelho = Pagar > Receber (falta lancamento no Receber) | Verde = Receber > Pagar (falta lancamento no Pagar)")
        else:
            st.success("Todas as operacoes estao conciliadas!")

    with col2:
        st.markdown("##### Legenda")
        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['borda']};
                    border-radius: 10px; padding: 1rem; font-size: 0.8rem;">
            <p style="color: {cores['texto']}; margin-bottom: 0.75rem;"><b>Como interpretar:</b></p>
            <p style="color: {cores['perigo']}; margin: 0.5rem 0;">
                <b>Diferenca Positiva:</b><br>
                A Pagar > A Receber<br>
                <i>Falta lancamento no Contas a Receber da filial destino</i>
            </p>
            <p style="color: {cores['sucesso']}; margin: 0.5rem 0;">
                <b>Diferenca Negativa:</b><br>
                A Receber > A Pagar<br>
                <i>Falta lancamento no Contas a Pagar da filial origem</i>
            </p>
            <p style="color: {cores['texto_secundario']}; margin: 0.5rem 0;">
                <b>Diferenca Zero:</b><br>
                Operacao conciliada
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # Tabela completa
    st.markdown("##### Tabela de Conciliacao Completa")

    # Filtros
    col1, col2, col3 = st.columns(3)
    with col1:
        filtro_status = st.selectbox("Status", ["Todos", "Divergentes", "Conciliados"], key="conc_status")
    with col2:
        filiais = ['Todas'] + sorted(list(set(conciliacao['DE'].tolist() + conciliacao['PARA'].tolist())))
        filtro_filial = st.selectbox("Filial", filiais, key="conc_filial")
    with col3:
        ordenar = st.selectbox("Ordenar por", ["Maior Divergencia", "Maior Valor Pagar", "Maior Valor Receber"], key="conc_ordem")

    df_show = conciliacao.copy()

    if filtro_status == "Divergentes":
        df_show = df_show[df_show['DIFERENCA_ABS'] >= 1000]
    elif filtro_status == "Conciliados":
        df_show = df_show[df_show['DIFERENCA_ABS'] < 1000]

    if filtro_filial != 'Todas':
        df_show = df_show[(df_show['DE'] == filtro_filial) | (df_show['PARA'] == filtro_filial)]

    if ordenar == "Maior Divergencia":
        df_show = df_show.sort_values('DIFERENCA_ABS', ascending=False)
    elif ordenar == "Maior Valor Pagar":
        df_show = df_show.sort_values('SALDO_PAGAR', ascending=False)
    else:
        df_show = df_show.sort_values('SALDO_RECEBER', ascending=False)

    # Preparar tabela
    df_tab = df_show[['DE', 'PARA', 'QTD_PAGAR', 'SALDO_PAGAR', 'QTD_RECEBER', 'SALDO_RECEBER', 'DIFERENCA']].copy()
    df_tab['QTD_PAGAR'] = df_tab['QTD_PAGAR'].astype(int)
    df_tab['QTD_RECEBER'] = df_tab['QTD_RECEBER'].astype(int)
    df_tab['SALDO_PAGAR'] = df_tab['SALDO_PAGAR'].apply(lambda x: formatar_moeda(x, completo=True))
    df_tab['SALDO_RECEBER'] = df_tab['SALDO_RECEBER'].apply(lambda x: formatar_moeda(x, completo=True))
    df_tab['DIFERENCA'] = df_tab['DIFERENCA'].apply(lambda x: formatar_moeda(x, completo=True))

    df_tab.columns = ['De', 'Para', 'Qtd Pagar', 'Saldo Pagar', 'Qtd Receber', 'Saldo Receber', 'Diferenca']

    st.dataframe(df_tab, use_container_width=True, hide_index=True, height=400)


def _render_matriz(df_pagar, df_receber, cores):
    """Renderiza a matriz de operacoes entre filiais"""

    st.markdown("##### Matriz de Operacoes Intercompany")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"<p style='color: {cores['perigo']}; font-weight: 600;'>A PAGAR: Quem paga para quem</p>", unsafe_allow_html=True)

        matriz_pagar = df_pagar.pivot_table(
            index='FILIAL_ORIGEM',
            columns='FILIAL_DESTINO',
            values='SALDO',
            aggfunc='sum',
            fill_value=0
        )

        # Formatar
        matriz_pagar_fmt = matriz_pagar.copy()
        for col in matriz_pagar_fmt.columns:
            matriz_pagar_fmt[col] = matriz_pagar_fmt[col].apply(lambda x: formatar_moeda(x) if x > 0 else '-')

        st.dataframe(matriz_pagar_fmt, use_container_width=True, height=350)
        st.caption("Linha = Quem paga | Coluna = Para quem")

    with col2:
        st.markdown(f"<p style='color: {cores['sucesso']}; font-weight: 600;'>A RECEBER: Quem recebe de quem</p>", unsafe_allow_html=True)

        matriz_receber = df_receber.pivot_table(
            index='FILIAL_ORIGEM',
            columns='FILIAL_DESTINO',
            values='SALDO',
            aggfunc='sum',
            fill_value=0
        )

        # Formatar
        matriz_receber_fmt = matriz_receber.copy()
        for col in matriz_receber_fmt.columns:
            matriz_receber_fmt[col] = matriz_receber_fmt[col].apply(lambda x: formatar_moeda(x) if x > 0 else '-')

        st.dataframe(matriz_receber_fmt, use_container_width=True, height=350)
        st.caption("Linha = Quem recebe | Coluna = De quem")

    st.divider()

    # Grafico de barras comparativo
    st.markdown("##### Comparativo por Filial")

    # Totais por filial
    pagar_origem = df_pagar.groupby('FILIAL_ORIGEM')['SALDO'].sum().reset_index()
    pagar_origem.columns = ['Filial', 'Paga']

    receber_origem = df_receber.groupby('FILIAL_ORIGEM')['SALDO'].sum().reset_index()
    receber_origem.columns = ['Filial', 'Recebe']

    df_comp = pd.merge(pagar_origem, receber_origem, on='Filial', how='outer').fillna(0)
    df_comp['Saldo'] = df_comp['Recebe'] - df_comp['Paga']
    df_comp = df_comp.sort_values('Saldo')

    fig = go.Figure()

    fig.add_trace(go.Bar(
        name='A Pagar',
        y=df_comp['Filial'],
        x=-df_comp['Paga'],  # Negativo para mostrar a esquerda
        orientation='h',
        marker_color=cores['perigo'],
        text=[formatar_moeda(x) for x in df_comp['Paga']],
        textposition='inside',
        textfont=dict(size=9, color='white')
    ))

    fig.add_trace(go.Bar(
        name='A Receber',
        y=df_comp['Filial'],
        x=df_comp['Recebe'],
        orientation='h',
        marker_color=cores['sucesso'],
        text=[formatar_moeda(x) for x in df_comp['Recebe']],
        textposition='inside',
        textfont=dict(size=9, color='white')
    ))

    fig.add_vline(x=0, line_color=cores['texto'], line_width=2)

    fig.update_layout(
        barmode='relative',
        height=350,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showticklabels=False, showgrid=False),
        yaxis=dict(tickfont=dict(color=cores['texto'], size=10)),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5,
                   font=dict(color=cores['texto'], size=10))
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_por_filial(df_pagar, df_receber, conciliacao, cores):
    """Analise detalhada por filial"""

    st.markdown("##### Selecione uma Filial para Analise Detalhada")

    filiais = sorted(list(set(
        df_pagar['FILIAL_ORIGEM'].dropna().unique().tolist() +
        df_receber['FILIAL_ORIGEM'].dropna().unique().tolist()
    )))

    filial_sel = st.selectbox("Filial", filiais, key="filial_det")

    if not filial_sel:
        return

    st.divider()

    # Dados da filial
    pagar_filial = df_pagar[df_pagar['FILIAL_ORIGEM'] == filial_sel]
    receber_filial = df_receber[df_receber['FILIAL_ORIGEM'] == filial_sel]

    total_pagar = pagar_filial['SALDO'].sum()
    total_receber = receber_filial['SALDO'].sum()
    saldo = total_receber - total_pagar

    # KPIs da filial
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(f"{filial_sel} - A Pagar", formatar_moeda(total_pagar), f"{len(pagar_filial)} titulos")
    with col2:
        st.metric(f"{filial_sel} - A Receber", formatar_moeda(total_receber), f"{len(receber_filial)} titulos")
    with col3:
        cor = "normal" if saldo >= 0 else "inverse"
        st.metric("Saldo Liquido", formatar_moeda(saldo), "Credor" if saldo >= 0 else "Devedor", delta_color=cor)
    with col4:
        conc_filial = conciliacao[(conciliacao['DE'] == filial_sel) | (conciliacao['PARA'] == filial_sel)]
        div_filial = len(conc_filial[conc_filial['DIFERENCA_ABS'] >= 1000])
        st.metric("Divergencias", div_filial)

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"##### {filial_sel} PAGA para:")

        pagar_dest = pagar_filial.groupby('FILIAL_DESTINO').agg({
            'SALDO': 'sum',
            'NUMERO': 'count'
        }).reset_index()
        pagar_dest.columns = ['Para', 'Saldo', 'Qtd']
        pagar_dest = pagar_dest.sort_values('Saldo', ascending=False)

        if len(pagar_dest) > 0:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=pagar_dest['Para'],
                y=pagar_dest['Saldo'],
                marker_color=cores['perigo'],
                text=[formatar_moeda(x) for x in pagar_dest['Saldo']],
                textposition='outside',
                textfont=dict(size=9, color=cores['texto'])
            ))

            fig.update_layout(
                height=300,
                margin=dict(l=10, r=10, t=10, b=50),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(tickfont=dict(color=cores['texto'], size=9), tickangle=-30),
                yaxis=dict(showticklabels=False, showgrid=False)
            )

            st.plotly_chart(fig, use_container_width=True)

            # Tabela
            pagar_dest['Saldo'] = pagar_dest['Saldo'].apply(lambda x: formatar_moeda(x, completo=True))
            st.dataframe(pagar_dest, use_container_width=True, hide_index=True)
        else:
            st.info(f"{filial_sel} nao tem contas a pagar intercompany")

    with col2:
        st.markdown(f"##### {filial_sel} RECEBE de:")

        receber_orig = receber_filial.groupby('FILIAL_DESTINO').agg({
            'SALDO': 'sum',
            'NUMERO': 'count'
        }).reset_index()
        receber_orig.columns = ['De', 'Saldo', 'Qtd']
        receber_orig = receber_orig.sort_values('Saldo', ascending=False)

        if len(receber_orig) > 0:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=receber_orig['De'],
                y=receber_orig['Saldo'],
                marker_color=cores['sucesso'],
                text=[formatar_moeda(x) for x in receber_orig['Saldo']],
                textposition='outside',
                textfont=dict(size=9, color=cores['texto'])
            ))

            fig.update_layout(
                height=300,
                margin=dict(l=10, r=10, t=10, b=50),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(tickfont=dict(color=cores['texto'], size=9), tickangle=-30),
                yaxis=dict(showticklabels=False, showgrid=False)
            )

            st.plotly_chart(fig, use_container_width=True)

            # Tabela
            receber_orig['Saldo'] = receber_orig['Saldo'].apply(lambda x: formatar_moeda(x, completo=True))
            st.dataframe(receber_orig, use_container_width=True, hide_index=True)
        else:
            st.info(f"{filial_sel} nao tem contas a receber intercompany")


def _render_detalhes_pagar(df_pagar, cores):
    """Detalhes dos titulos a pagar intercompany"""

    st.markdown("##### Titulos A Pagar - Intercompany")

    # Filtros
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        filiais_origem = ['Todas'] + sorted(df_pagar['FILIAL_ORIGEM'].dropna().unique().tolist())
        filtro_origem = st.selectbox("Filial Origem", filiais_origem, key="pagar_origem")

    with col2:
        filiais_destino = ['Todas'] + sorted(df_pagar['FILIAL_DESTINO'].dropna().unique().tolist())
        filtro_destino = st.selectbox("Paga Para", filiais_destino, key="pagar_destino")

    with col3:
        status_opcoes = ['Todos', 'Pendente', 'Vencido']
        filtro_status = st.selectbox("Status", status_opcoes, key="pagar_status")

    with col4:
        ordenar = st.selectbox("Ordenar", ["Maior Saldo", "Mais Recente", "Mais Antigo"], key="pagar_ordem")

    df_show = df_pagar.copy()

    if filtro_origem != 'Todas':
        df_show = df_show[df_show['FILIAL_ORIGEM'] == filtro_origem]

    if filtro_destino != 'Todas':
        df_show = df_show[df_show['FILIAL_DESTINO'] == filtro_destino]

    if filtro_status == 'Pendente':
        df_show = df_show[df_show['SALDO'] > 0]
    elif filtro_status == 'Vencido':
        df_show = df_show[(df_show['SALDO'] > 0) & (df_show['DIAS_VENC'] < 0)]

    if ordenar == "Maior Saldo":
        df_show = df_show.sort_values('SALDO', ascending=False)
    elif ordenar == "Mais Recente":
        df_show = df_show.sort_values('EMISSAO', ascending=False)
    else:
        df_show = df_show.sort_values('EMISSAO', ascending=True)

    # Metricas
    col1, col2, col3 = st.columns(3)
    col1.metric("Titulos", formatar_numero(len(df_show)))
    col2.metric("Saldo Total", formatar_moeda(df_show['SALDO'].sum()))
    col3.metric("Vencidos", formatar_numero(len(df_show[(df_show['SALDO'] > 0) & (df_show['DIAS_VENC'] < 0)])))

    st.divider()

    # Tabela
    colunas = ['NOME_FILIAL', 'NOME_FORNECEDOR', 'FILIAL_DESTINO', 'EMISSAO', 'VENCIMENTO', 'VALOR_ORIGINAL', 'SALDO', 'STATUS']
    colunas_disp = [c for c in colunas if c in df_show.columns]
    df_tab = df_show[colunas_disp].head(200).copy()

    for col in ['EMISSAO', 'VENCIMENTO']:
        if col in df_tab.columns:
            df_tab[col] = pd.to_datetime(df_tab[col], errors='coerce').dt.strftime('%d/%m/%Y')

    for col in ['VALOR_ORIGINAL', 'SALDO']:
        if col in df_tab.columns:
            df_tab[col] = df_tab[col].apply(lambda x: formatar_moeda(x, completo=True))

    nomes = {
        'NOME_FILIAL': 'Filial Origem',
        'NOME_FORNECEDOR': 'Fornecedor',
        'FILIAL_DESTINO': 'Paga Para',
        'EMISSAO': 'Emissao',
        'VENCIMENTO': 'Vencimento',
        'VALOR_ORIGINAL': 'Valor',
        'SALDO': 'Saldo',
        'STATUS': 'Status'
    }
    df_tab.columns = [nomes.get(c, c) for c in df_tab.columns]

    st.dataframe(df_tab, use_container_width=True, hide_index=True, height=450)
    st.caption(f"Exibindo {len(df_tab)} de {len(df_show)} registros")


def _render_detalhes_receber(df_receber, cores):
    """Detalhes dos titulos a receber intercompany"""

    st.markdown("##### Titulos A Receber - Intercompany")

    # Filtros
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        filiais_origem = ['Todas'] + sorted(df_receber['FILIAL_ORIGEM'].dropna().unique().tolist())
        filtro_origem = st.selectbox("Filial Origem", filiais_origem, key="receber_origem")

    with col2:
        filiais_destino = ['Todas'] + sorted(df_receber['FILIAL_DESTINO'].dropna().unique().tolist())
        filtro_destino = st.selectbox("Recebe De", filiais_destino, key="receber_destino")

    with col3:
        status_opcoes = ['Todos', 'Pendente', 'Vencido']
        filtro_status = st.selectbox("Status", status_opcoes, key="receber_status")

    with col4:
        ordenar = st.selectbox("Ordenar", ["Maior Saldo", "Mais Recente", "Mais Antigo"], key="receber_ordem")

    df_show = df_receber.copy()

    if filtro_origem != 'Todas':
        df_show = df_show[df_show['FILIAL_ORIGEM'] == filtro_origem]

    if filtro_destino != 'Todas':
        df_show = df_show[df_show['FILIAL_DESTINO'] == filtro_destino]

    if filtro_status == 'Pendente':
        df_show = df_show[df_show['SALDO'] > 0]
    elif filtro_status == 'Vencido':
        df_show = df_show[(df_show['SALDO'] > 0) & (df_show['DIAS_VENC'] < 0)]

    if ordenar == "Maior Saldo":
        df_show = df_show.sort_values('SALDO', ascending=False)
    elif ordenar == "Mais Recente":
        df_show = df_show.sort_values('EMISSAO', ascending=False)
    else:
        df_show = df_show.sort_values('EMISSAO', ascending=True)

    # Metricas
    col1, col2, col3 = st.columns(3)
    col1.metric("Titulos", formatar_numero(len(df_show)))
    col2.metric("Saldo Total", formatar_moeda(df_show['SALDO'].sum()))
    col3.metric("Vencidos", formatar_numero(len(df_show[(df_show['SALDO'] > 0) & (df_show['DIAS_VENC'] < 0)])))

    st.divider()

    # Tabela
    colunas = ['NOME_FILIAL', 'NOME_CLIENTE', 'FILIAL_DESTINO', 'EMISSAO', 'VENCIMENTO', 'VALOR_ORIGINAL', 'SALDO', 'STATUS']
    colunas_disp = [c for c in colunas if c in df_show.columns]
    df_tab = df_show[colunas_disp].head(200).copy()

    for col in ['EMISSAO', 'VENCIMENTO']:
        if col in df_tab.columns:
            df_tab[col] = pd.to_datetime(df_tab[col], errors='coerce').dt.strftime('%d/%m/%Y')

    for col in ['VALOR_ORIGINAL', 'SALDO']:
        if col in df_tab.columns:
            df_tab[col] = df_tab[col].apply(lambda x: formatar_moeda(x, completo=True))

    nomes = {
        'NOME_FILIAL': 'Filial Origem',
        'NOME_CLIENTE': 'Cliente',
        'FILIAL_DESTINO': 'Recebe De',
        'EMISSAO': 'Emissao',
        'VENCIMENTO': 'Vencimento',
        'VALOR_ORIGINAL': 'Valor',
        'SALDO': 'Saldo',
        'STATUS': 'Status'
    }
    df_tab.columns = [nomes.get(c, c) for c in df_tab.columns]

    st.dataframe(df_tab, use_container_width=True, hide_index=True, height=450)
    st.caption(f"Exibindo {len(df_tab)} de {len(df_show)} registros")
