"""
Pagina Contas a Receber
Dashboard Financeiro - Grupo Progresso
"""
import streamlit as st
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(
    page_title="Contas a Receber | Grupo Progresso",
    page_icon="GP",
    layout="wide",
    initial_sidebar_state="expanded"
)

from auth import verificar_autenticacao
if not verificar_autenticacao():
    st.stop()

from datetime import datetime
import pandas as pd

from config.theme import get_cores, get_css
from config.settings import INTERCOMPANY_PATTERNS, TIPOS_EXCLUIDOS, CACHE_TTL
from components.navbar import render_navbar, render_page_header
from utils.formatters import formatar_moeda, formatar_numero, to_excel, to_csv

# Importar funcoes do loader de receber
from data.loader_receber import (
    carregar_dados_receber,
    aplicar_filtros_receber,
    get_opcoes_filtros_receber,
    get_dados_filtrados_receber,
    calcular_metricas_receber
)

# Importar tabs de receber
from tabs_receber.visao_geral import render_visao_geral_receber
from tabs_receber.vencimentos import render_vencimentos_receber
from tabs_receber.clientes import render_clientes
from tabs_receber.categorias import render_categorias_receber
from tabs_receber.adiantamentos import render_adiantamentos_receber
from tabs_receber.tipo_documento import render_tipo_documento
from tabs_receber.detalhes import render_detalhes_receber


# Fragments para evitar rerun completo
@st.fragment
def fragment_vencimentos(df):
    render_vencimentos_receber(df)

@st.fragment
def fragment_clientes(df):
    render_clientes(df)

@st.fragment
def fragment_categorias(df):
    render_categorias_receber(df)

@st.fragment
def fragment_tipo_documento(df):
    render_tipo_documento(df)

@st.fragment
def fragment_detalhes(df):
    render_detalhes_receber(df)


@st.cache_data(ttl=CACHE_TTL)
def _preparar_dados_receber(_df_contas_raw, _df_baixas_raw):
    """Pre-processa dados de receber: remove intercompany, extrai adiantamentos"""
    # Excluir clientes Intercompany
    mask_cliente_ic = _df_contas_raw['NOME_CLIENTE'].str.upper().str.contains(
        '|'.join(INTERCOMPANY_PATTERNS), na=False, regex=True
    )
    df_sem_ic = _df_contas_raw[~mask_cliente_ic]

    # Excluir tipos que duplicam valores (FAT, etc.)
    if 'TIPO' in df_sem_ic.columns and TIPOS_EXCLUIDOS:
        df_sem_ic = df_sem_ic[~df_sem_ic['TIPO'].str.strip().isin(TIPOS_EXCLUIDOS)]

    # Baixas: filtrar intercompany por NOME_CLIENTE
    df_baixas = _df_baixas_raw
    if len(df_baixas) > 0 and 'NOME_CLIENTE' in df_baixas.columns:
        mask_ic_baixas = df_baixas['NOME_CLIENTE'].str.upper().str.contains(
            '|'.join(INTERCOMPANY_PATTERNS), na=False, regex=True
        )
        df_baixas = df_baixas[~mask_ic_baixas]

    # Extrair adiantamentos do proprio Contas a Receber (evita duplicacao com arquivo separado)
    tipos_adiantamento = ['RA', 'PA', 'AD', 'ADTO']
    mask_tipo_adto = df_sem_ic['TIPO'].isin(tipos_adiantamento)
    mask_desc_adto = df_sem_ic['DESCRICAO'].str.upper().str.contains('ADIANTAMENTO|ADT |ADTO', na=False, regex=True)
    mask_adiantamento = mask_tipo_adto | mask_desc_adto
    df_adiant = df_sem_ic[mask_adiantamento]
    df_contas = df_sem_ic[~mask_adiantamento]

    return df_contas, df_adiant, df_baixas


def main():
    # Tema
    if 'tema_escuro' not in st.session_state:
        st.session_state.tema_escuro = True

    cores = get_cores()
    st.markdown(get_css(), unsafe_allow_html=True)

    # Carregar dados PRIMEIRO para obter opcoes de filiais
    df_contas_raw, df_baixas_raw = carregar_dados_receber()

    # Pre-processar dados (cacheado) - extrai adiantamentos do proprio Contas a Receber
    df_contas, df_adiant, df_baixas = _preparar_dados_receber(df_contas_raw, df_baixas_raw)

    filiais_por_grupo, categorias_opcoes = get_opcoes_filtros_receber(df_contas)

    # Navbar com filtros de tempo E FILIAL
    navbar_result = render_navbar(pagina_atual='receber', mostrar_filtro_tempo=True, filiais_por_grupo=filiais_por_grupo)

    hoje = datetime.now()

    # Datas do filtro da navbar (3 valores: data_inicio, data_fim, filtro_filiais)
    if navbar_result:
        data_inicio, data_fim, filtro_filiais = navbar_result
    else:
        data_inicio, data_fim, filtro_filiais = datetime(2000, 1, 1).date(), hoje.date(), None

    # Apenas ajustar data_inicio ao minimo dos dados (nao limitar data_fim)
    data_min = df_contas['EMISSAO'].min().date()
    data_inicio = max(data_inicio, data_min)

    # ========== SIDEBAR ==========
    with st.sidebar:
        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 1rem;">
            <div style="background: {cores['sucesso']}; width: 40px; height: 40px;
                        border-radius: 10px; display: flex; align-items: center;
                        justify-content: center; color: white; font-weight: 700;">CR</div>
            <div>
                <div style="color: {cores['texto']}; font-weight: 600; font-size: 0.95rem;">Grupo Progresso</div>
                <div style="color: {cores['texto_secundario']}; font-size: 0.7rem;">Contas a Receber</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        # Filtros (Filial agora esta na navbar)
        st.markdown(f"<p style='color: {cores['texto']}; font-size: 0.8rem; font-weight: 600; margin-bottom: 0.5rem;'>Filtros</p>", unsafe_allow_html=True)

        status_opcoes = ['Todos os Status', 'Vencido', 'Vence em 7 dias', 'Vence em 15 dias', 'Vence em 30 dias', 'Recebido']
        filtro_status = st.selectbox("Status", status_opcoes, key="rec_status")

        filtro_categoria = st.selectbox("Categoria", categorias_opcoes, key="rec_categoria")
        filtro_tipo_doc = st.selectbox("Tipo Documento", ['Todos', 'Com NF', 'Sem NF'], key="rec_tipo_doc")

        busca_cliente = st.text_input("Cliente", placeholder="Buscar...", key="rec_busca")

        st.divider()

        # Exportar
        st.markdown(f"<p style='color: {cores['texto']}; font-size: 0.8rem; font-weight: 600; margin-bottom: 0.5rem;'>Exportar</p>", unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "Excel",
                data=to_excel(df_contas),
                file_name=f"receber_{hoje.strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        with col2:
            st.download_button(
                "CSV",
                data=to_csv(df_contas),
                file_name=f"receber_{hoje.strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )

        st.divider()

        # Resumo
        st.markdown(f"<p style='color: {cores['texto']}; font-size: 0.8rem; font-weight: 600; margin-bottom: 0.5rem;'>Resumo</p>", unsafe_allow_html=True)

        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['borda']};
                    border-radius: 8px; padding: 0.75rem; font-size: 0.8rem;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.4rem;">
                <span style="color: {cores['texto_secundario']};">Titulos</span>
                <span style="color: {cores['texto']}; font-weight: 600;">{formatar_numero(len(df_contas))}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.4rem;">
                <span style="color: {cores['texto_secundario']};">Valor Total</span>
                <span style="color: {cores['texto']}; font-weight: 600;">{formatar_moeda(df_contas['VALOR_ORIGINAL'].sum())}</span>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <span style="color: {cores['texto_secundario']};">A Receber</span>
                <span style="color: {cores['sucesso']}; font-weight: 600;">{formatar_moeda(df_contas['SALDO'].sum())}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        # Footer
        st.markdown(f"""
        <div style="text-align: center; margin-top: 1.5rem; padding-top: 1rem;
                    border-top: 1px solid {cores['borda']};">
            <p style="color: {cores['texto_secundario']}; font-size: 0.65rem; margin: 0;">
                Atualizado: {hoje.strftime('%d/%m/%Y %H:%M')}</p>
        </div>
        """, unsafe_allow_html=True)

    # ========== APLICAR FILTROS ==========
    df = aplicar_filtros_receber(
        df_contas, data_inicio, data_fim,
        filtro_filiais, filtro_status, filtro_categoria, busca_cliente, filtro_tipo_doc
    )
    df_pendentes, df_vencidos = get_dados_filtrados_receber(df, df_contas)
    metricas = calcular_metricas_receber(df, df_vencidos)

    # ========== CONTEUDO PRINCIPAL ==========
    render_page_header(
        titulo="Contas a Receber",
        subtitulo=f"{formatar_numero(metricas['qtd_total'])} titulos | {data_inicio.strftime('%d/%m/%Y')} - {data_fim.strftime('%d/%m/%Y')}",
        icone="CR",
        cor=cores['sucesso']
    )

    # Tabs (7 tabs) - Estrutura otimizada para dados de Receber
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "Visao Geral", "Vencimentos", "Clientes", "Categorias",
        "Tipos", "Adiantamentos", "Detalhes"
    ])

    with tab1:
        render_visao_geral_receber(df)

    with tab2:
        fragment_vencimentos(df)

    with tab3:
        fragment_clientes(df)

    with tab4:
        fragment_categorias(df)

    with tab5:
        fragment_tipo_documento(df)

    with tab6:
        # Aplicar filtro de filial nos adiantamentos e baixas
        df_adiant_filtrado = df_adiant
        df_baixas_filtrado = df_baixas

        if filtro_filiais is not None:
            if 'FILIAL' in df_adiant_filtrado.columns:
                df_adiant_filtrado = df_adiant_filtrado[df_adiant_filtrado['FILIAL'].isin(filtro_filiais)]
            if 'FILIAL' in df_baixas_filtrado.columns:
                df_baixas_filtrado = df_baixas_filtrado[df_baixas_filtrado['FILIAL'].isin(filtro_filiais)]

        # Aplicar filtro de data (mesmo criterio das outras abas)
        if 'EMISSAO' in df_adiant_filtrado.columns:
            df_adiant_filtrado = df_adiant_filtrado[
                (pd.to_datetime(df_adiant_filtrado['EMISSAO'], errors='coerce').dt.date >= data_inicio) &
                (pd.to_datetime(df_adiant_filtrado['EMISSAO'], errors='coerce').dt.date <= data_fim)
            ]
        if 'DT_BAIXA' in df_baixas_filtrado.columns:
            df_baixas_filtrado = df_baixas_filtrado[
                pd.to_datetime(df_baixas_filtrado['DT_BAIXA'], errors='coerce').dt.date <= data_fim
            ]

        render_adiantamentos_receber(df_adiant_filtrado, df_baixas_filtrado)

    with tab7:
        fragment_detalhes(df)

    # Footer
    st.divider()
    st.caption(f"Grupo Progresso - Dashboard Financeiro | Atualizado em {hoje.strftime('%d/%m/%Y %H:%M')}")


if __name__ == "__main__":
    main()
