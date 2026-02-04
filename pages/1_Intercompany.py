"""
Intercompany - Visao Unificada A Pagar + A Receber
Dashboard Financeiro - Grupo Progresso
"""
import streamlit as st
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(
    page_title="Intercompany | Grupo Progresso",
    page_icon="GP",
    layout="wide",
    initial_sidebar_state="expanded"
)

from auth import verificar_autenticacao
if not verificar_autenticacao():
    st.stop()

from datetime import datetime

from config.theme import get_cores, get_css
from components.navbar import render_navbar, render_page_header
from tabs.intercompany_unified import render_intercompany_unificado, carregar_dados_intercompany
from utils.formatters import formatar_moeda, formatar_numero, to_excel


def main():
    # Tema
    if 'tema_escuro' not in st.session_state:
        st.session_state.tema_escuro = True

    cores = get_cores()
    st.markdown(get_css(), unsafe_allow_html=True)

    # Navbar com filtro de tempo (ignora filtro de filial por enquanto)
    navbar_result = render_navbar(pagina_atual='intercompany', mostrar_filtro_tempo=True)

    # Datas do filtro (3 valores: data_inicio, data_fim, filtro_filiais)
    if navbar_result:
        data_inicio, data_fim, _ = navbar_result
    else:
        data_inicio, data_fim = datetime(2000, 1, 1).date(), datetime.now().date()

    # Carregar dados para sidebar
    df_pagar, df_receber = carregar_dados_intercompany()

    # Aplicar filtro de data
    ts_inicio = pd.Timestamp(data_inicio)
    ts_fim = pd.Timestamp(data_fim) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    if 'EMISSAO' in df_pagar.columns:
        df_pagar = df_pagar[(df_pagar['EMISSAO'] >= ts_inicio) & (df_pagar['EMISSAO'] <= ts_fim)]
    if 'EMISSAO' in df_receber.columns:
        df_receber = df_receber[(df_receber['EMISSAO'] >= ts_inicio) & (df_receber['EMISSAO'] <= ts_fim)]

    hoje = datetime.now()

    # ========== SIDEBAR ==========
    with st.sidebar:
        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 1rem;">
            <div style="background: linear-gradient(135deg, {cores['primaria']}, {cores['info']});
                        width: 40px; height: 40px;
                        border-radius: 10px; display: flex; align-items: center;
                        justify-content: center; color: white; font-weight: 700;">IC</div>
            <div>
                <div style="color: {cores['texto']}; font-weight: 600; font-size: 0.95rem;">Grupo Progresso</div>
                <div style="color: {cores['texto_secundario']}; font-size: 0.7rem;">Intercompany Unificado</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        # Resumo rapido
        total_pagar = df_pagar['SALDO'].sum()
        total_receber = df_receber['SALDO'].sum()
        saldo_liquido = total_receber - total_pagar

        cor_saldo = cores['perigo'] if saldo_liquido < 0 else cores['sucesso']
        posicao = "Devedor" if saldo_liquido < 0 else "Credor"

        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cor_saldo};
                    border-radius: 10px; padding: 1rem; margin-bottom: 1rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0; text-align: center;">
                POSICAO NO GRUPO</p>
            <p style="color: {cor_saldo}; font-size: 1.5rem; font-weight: 700; margin: 0.25rem 0; text-align: center;">
                {formatar_moeda(abs(saldo_liquido))}</p>
            <p style="color: {cor_saldo}; font-size: 0.75rem; font-weight: 600; margin: 0; text-align: center;">
                {posicao}</p>
        </div>
        """, unsafe_allow_html=True)

        # Detalhes
        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['borda']};
                    border-radius: 8px; padding: 0.75rem; font-size: 0.8rem;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.4rem;">
                <span style="color: {cores['texto_secundario']};">A Pagar</span>
                <span style="color: {cores['perigo']}; font-weight: 600;">{formatar_moeda(total_pagar)}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.4rem;">
                <span style="color: {cores['texto_secundario']};">A Receber</span>
                <span style="color: {cores['sucesso']}; font-weight: 600;">{formatar_moeda(total_receber)}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.4rem;">
                <span style="color: {cores['texto_secundario']};">Titulos Pagar</span>
                <span style="color: {cores['texto']}; font-weight: 600;">{formatar_numero(len(df_pagar))}</span>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <span style="color: {cores['texto_secundario']};">Titulos Receber</span>
                <span style="color: {cores['texto']}; font-weight: 600;">{formatar_numero(len(df_receber))}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        # Exportar
        st.markdown(f"<p style='color: {cores['texto']}; font-size: 0.8rem; font-weight: 600; margin-bottom: 0.5rem;'>Exportar Dados</p>", unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "A Pagar",
                data=to_excel(df_pagar),
                file_name=f"ic_pagar_{hoje.strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        with col2:
            st.download_button(
                "A Receber",
                data=to_excel(df_receber),
                file_name=f"ic_receber_{hoje.strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        st.divider()

        # Footer
        st.markdown(f"""
        <div style="text-align: center; margin-top: 1rem; padding-top: 0.75rem;
                    border-top: 1px solid {cores['borda']};">
            <p style="color: {cores['texto_secundario']}; font-size: 0.65rem; margin: 0;">
                Atualizado: {hoje.strftime('%d/%m/%Y %H:%M')}</p>
        </div>
        """, unsafe_allow_html=True)

    # ========== CONTEUDO PRINCIPAL ==========
    render_page_header(
        titulo="Intercompany",
        subtitulo=f"Visao Unificada | A Pagar + A Receber | {formatar_numero(len(df_pagar) + len(df_receber))} titulos",
        icone="IC",
        cor=cores['primaria']
    )

    # Renderizar pagina unificada (com datas filtradas)
    render_intercompany_unificado(data_inicio, data_fim)

    # Footer
    st.divider()
    st.caption(f"Grupo Progresso - Dashboard Financeiro | Atualizado em {hoje.strftime('%d/%m/%Y %H:%M')}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        st.error(f"Erro: {str(e)}")
        st.code(traceback.format_exc())
