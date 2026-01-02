"""
Componente de Header do Dashboard
"""
import streamlit as st
from config.theme import get_cores
from utils.formatters import formatar_numero


def render_header(qtd_titulos: int, data_inicio, data_fim):
    """Renderiza o header principal do dashboard"""
    cores = get_cores()

    st.markdown(f"""
    <div class="header-gp">
        <div class="logo">GP</div>
        <div>
            <p class="titulo">Contas a Pagar</p>
            <p class="subtitulo">{formatar_numero(qtd_titulos)} títulos selecionados | {data_inicio.strftime('%d/%m/%Y')} - {data_fim.strftime('%d/%m/%Y')}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
