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

from datetime import datetime

from config.theme import get_cores, get_css
from config.settings import INTERCOMPANY_PATTERNS
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
from tabs_receber.tipo_documento import render_tipo_documento
from tabs_receber.concentracao_risco import render_concentracao_risco
from tabs_receber.inadimplencia import render_inadimplencia
from tabs_receber.adiantamentos import render_adiantamentos_receber
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
def fragment_concentracao_risco(df):
    render_concentracao_risco(df)

@st.fragment
def fragment_inadimplencia(df):
    render_inadimplencia(df)

@st.fragment
def fragment_detalhes(df):
    render_detalhes_receber(df)


def main():
    # Tema
    if 'tema_escuro' not in st.session_state:
        st.session_state.tema_escuro = True

    cores = get_cores()
    st.markdown(get_css(), unsafe_allow_html=True)

    # Navbar com filtros de tempo
    datas_navbar = render_navbar(pagina_atual='receber', mostrar_filtro_tempo=True)

    # Carregar dados
    df_contas_raw, df_adiant, df_baixas = carregar_dados_receber()

    # Excluir clientes Intercompany dos dados principais (igual ao Contas a Pagar)
    mask_intercompany = df_contas_raw['NOME_CLIENTE'].str.upper().str.contains(
        '|'.join(INTERCOMPANY_PATTERNS), na=False, regex=True
    )
    df_contas = df_contas_raw[~mask_intercompany].copy()

    filiais_opcoes, categorias_opcoes = get_opcoes_filtros_receber(df_contas)

    hoje = datetime.now()

    # Datas do filtro da navbar
    data_inicio, data_fim = datas_navbar if datas_navbar else (datetime(2000, 1, 1).date(), hoje.date())

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

        # Filtros
        st.markdown(f"<p style='color: {cores['texto']}; font-size: 0.8rem; font-weight: 600; margin-bottom: 0.5rem;'>Filtros</p>", unsafe_allow_html=True)

        filtro_filial = st.selectbox("Filial", filiais_opcoes, key="rec_filial")

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
        filtro_filial, filtro_status, filtro_categoria, busca_cliente, filtro_tipo_doc
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

    # Tabs (9 tabs) - Estrutura otimizada para dados de Receber
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
        "Visao Geral", "Vencimentos", "Clientes", "Categorias",
        "Tipo Documento", "Concentracao", "Inadimplencia", "Adiantamentos", "Detalhes"
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
        fragment_concentracao_risco(df)

    with tab7:
        fragment_inadimplencia(df)

    with tab8:
        render_adiantamentos_receber(df_adiant, df_baixas)

    with tab9:
        fragment_detalhes(df)

    # Footer
    st.divider()
    st.caption(f"Grupo Progresso - Dashboard Financeiro | Atualizado em {hoje.strftime('%d/%m/%Y %H:%M')}")


if __name__ == "__main__":
    main()
