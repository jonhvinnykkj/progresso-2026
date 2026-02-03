"""
Modulo de autenticacao
Dashboard Financeiro - Grupo Progresso
"""
import streamlit as st
from auth.login import render_login


def verificar_autenticacao() -> bool:
    """
    Verifica se o usuario esta autenticado.
    Se nao estiver, renderiza a tela de login.

    Usar em todas as paginas:
        from auth import verificar_autenticacao
        if not verificar_autenticacao():
            st.stop()
    """
    if st.session_state.get('autenticado'):
        return True
    return render_login()


def is_admin() -> bool:
    """Verifica se o usuario logado e admin."""
    usuario = st.session_state.get('usuario')
    if not usuario:
        return False
    return usuario.get('perfil') == 'admin'
