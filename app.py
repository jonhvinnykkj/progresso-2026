"""
Dashboard Financeiro - Grupo Progresso
Contas a Pagar (Nao-Intercompany)

Autor: Grupo Progresso
Versao: 3.0 (Multi-page)
"""
import streamlit as st
import warnings
warnings.filterwarnings('ignore')

# Configuracao da pagina (deve ser a primeira chamada Streamlit)
from config.settings import PAGE_CONFIG, INTERCOMPANY_PATTERNS, TIPOS_EXCLUIDOS, CACHE_TTL
st.set_page_config(**PAGE_CONFIG)

from auth import verificar_autenticacao
if not verificar_autenticacao():
    st.stop()

# Imports apos configuracao
from datetime import datetime

from config.theme import get_cores, get_css
from data.loader import carregar_dados, aplicar_filtros, get_opcoes_filtros, get_dados_filtrados, calcular_metricas
from components.navbar import render_navbar, render_page_header
from components.sidebar import render_sidebar
from utils.formatters import formatar_numero

from tabs.visao_geral import render_visao_geral
from tabs.vencimentos import render_vencimentos
from tabs.fornecedores import render_fornecedores
from tabs.categorias import render_categorias
from tabs.formas_pagamento import render_formas_pagamento
from tabs.tipo_documento import render_tipo_documento
from tabs.adiantamentos import render_adiantamentos
from tabs.bancos import render_bancos
from tabs.juros_cambio import render_juros_cambio
from tabs.detalhes import render_detalhes


# Funções com @st.fragment para evitar rerun completo da página
@st.fragment
def fragment_vencimentos(df):
    render_vencimentos(df)

@st.fragment
def fragment_fornecedores(df):
    render_fornecedores(df)

@st.fragment
def fragment_categorias(df):
    render_categorias(df)

@st.fragment
def fragment_formas_pagamento(df):
    render_formas_pagamento(df)

@st.fragment
def fragment_tipo_documento(df):
    render_tipo_documento(df)

@st.fragment
def fragment_detalhes(df):
    render_detalhes(df)


PADROES_CUSTOS_FINANCEIROS = ['TAXA', 'JUROS', 'BANC', 'EMPRESTIMO', 'MULTA CONTRATUAL', 'IOF', 'ENCARGO']


@st.cache_data(ttl=CACHE_TTL)
def _preparar_dados_pagar(_df_contas):
    """Pre-processa dados: remove intercompany, extrai adiantamentos e custos financeiros"""
    # Excluir fornecedores Intercompany dos dados principais
    mask_intercompany = _df_contas['NOME_FORNECEDOR'].str.upper().str.contains(
        '|'.join(INTERCOMPANY_PATTERNS), na=False, regex=True
    )
    df_sem_ic = _df_contas[~mask_intercompany]

    # Excluir tipos que duplicam valores (FAT, etc.)
    if 'TIPO' in df_sem_ic.columns and TIPOS_EXCLUIDOS:
        df_sem_ic = df_sem_ic[~df_sem_ic['TIPO'].str.strip().isin(TIPOS_EXCLUIDOS)]

    # Extrair adiantamentos (TIPO=PA ou DESCRICAO contendo ADTO/ADIANT)
    mask_tipo_adto = df_sem_ic['TIPO'].isin(['PA', 'ADI'])
    mask_desc_adto = df_sem_ic['DESCRICAO'].str.upper().str.contains('ADTO|ADIANT', na=False, regex=True)
    mask_adiantamento = mask_tipo_adto | mask_desc_adto
    df_adiantamentos = df_sem_ic[mask_adiantamento]
    df_sem_adto = df_sem_ic[~mask_adiantamento]

    # Separar custos financeiros/bancos
    mask_custos_fin = df_sem_adto['DESCRICAO'].str.upper().str.contains(
        '|'.join(PADROES_CUSTOS_FINANCEIROS), na=False, regex=True
    )
    df_custos_financeiros = df_sem_adto[mask_custos_fin]
    df_contas_sem_ic = df_sem_adto[~mask_custos_fin]

    return df_contas_sem_ic, df_custos_financeiros, df_adiantamentos


def main():
    """Funcao principal do dashboard"""

    # Inicializar tema
    if 'tema_escuro' not in st.session_state:
        st.session_state.tema_escuro = True

    cores = get_cores()

    # Aplicar CSS
    st.markdown(get_css(), unsafe_allow_html=True)

    # Carregar dados PRIMEIRO para obter opcoes de filiais
    df_contas, df_baixas = carregar_dados()

    # Pre-processar dados (cacheado) - extrai adiantamentos do proprio Contas a Pagar
    df_contas_sem_ic, df_custos_financeiros, df_adiant = _preparar_dados_pagar(df_contas)

    # Obter opcoes de filtros (SEM intercompany e SEM adiantamentos)
    filiais_por_grupo, categorias_opcoes = get_opcoes_filtros(df_contas_sem_ic)

    # NavBar com filtros rapidos de tempo E FILIAL
    navbar_result = render_navbar(pagina_atual='pagar', mostrar_filtro_tempo=True, filiais_por_grupo=filiais_por_grupo)
    data_inicio, data_fim, filtro_filiais = navbar_result if navbar_result else (datetime(2000, 1, 1).date(), datetime.now().date(), None)

    # Apenas ajustar data_inicio ao minimo dos dados (nao limitar data_fim)
    data_min = df_contas_sem_ic['EMISSAO'].min().date()
    data_inicio = max(data_inicio, data_min)

    # Renderizar sidebar e obter filtros (SEM intercompany)
    _, filtro_status, filtro_categoria, busca_fornecedor, filtro_tipo_doc, filtro_forma_pagto = render_sidebar(
        df_contas_sem_ic, filiais_por_grupo, categorias_opcoes
    )

    # Aplicar filtros (sem intercompany)
    df = aplicar_filtros(
        df_contas_sem_ic, data_inicio, data_fim,
        filtro_filiais, filtro_status, filtro_categoria, busca_fornecedor,
        filtro_tipo_doc, filtro_forma_pagto
    )
    df_pendentes, df_vencidos = get_dados_filtrados(df, df_contas_sem_ic)

    # Calcular metricas
    metricas = calcular_metricas(df, df_vencidos)

    # Page Header
    render_page_header(
        titulo="Contas a Pagar",
        subtitulo=f"{formatar_numero(metricas['qtd_total'])} titulos | {data_inicio.strftime('%d/%m/%Y')} - {data_fim.strftime('%d/%m/%Y')}",
        icone="CP",
        cor=cores['primaria']
    )

    # Tabs (10 tabs)
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
        "Visao Geral", "Vencimentos", "Fornecedores", "Categorias",
        "Tipo Documento", "Formas Pagto", "Bancos", "Juros e Cambio", "Adiantamentos", "Detalhes"
    ])

    with tab1:
        # KPIs e alertas apenas na Visao Geral
        render_visao_geral(df, df_pendentes, df_vencidos, metricas)

    with tab2:
        fragment_vencimentos(df)

    with tab3:
        fragment_fornecedores(df)

    with tab4:
        fragment_categorias(df)

    with tab5:
        fragment_tipo_documento(df)

    with tab6:
        fragment_formas_pagamento(df)

    with tab7:
        # Aplicar filtro de filial nos bancos (custos financeiros)
        df_bancos_filtrado = df_custos_financeiros
        if filtro_filiais is not None and 'FILIAL' in df_bancos_filtrado.columns:
            df_bancos_filtrado = df_bancos_filtrado[df_bancos_filtrado['FILIAL'].isin(filtro_filiais)]
        render_bancos(df_bancos_filtrado)

    with tab8:
        # Juros e Cambio - usa df filtrado (todas as contas, nao apenas bancos)
        render_juros_cambio(df)

    with tab9:
        # Aplicar filtro de filial nos adiantamentos e baixas
        df_adiant_filtrado = df_adiant
        df_baixas_filtrado = df_baixas
        if filtro_filiais is not None:
            if 'FILIAL' in df_adiant_filtrado.columns:
                df_adiant_filtrado = df_adiant_filtrado[df_adiant_filtrado['FILIAL'].isin(filtro_filiais)]
            if 'FILIAL' in df_baixas_filtrado.columns:
                df_baixas_filtrado = df_baixas_filtrado[df_baixas_filtrado['FILIAL'].isin(filtro_filiais)]
        render_adiantamentos(df_adiant_filtrado, df_baixas_filtrado)

    with tab10:
        fragment_detalhes(df)

    # Footer
    hoje = datetime.now()
    st.divider()
    st.caption(f"Grupo Progresso - Dashboard Financeiro | Atualizado em {hoje.strftime('%d/%m/%Y %H:%M')}")


if __name__ == "__main__":
    main()
