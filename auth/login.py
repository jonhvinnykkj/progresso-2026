"""
Tela de Login (sem auto-cadastro)
Dashboard Financeiro - Grupo Progresso
"""
import streamlit as st
from auth.database import autenticar_usuario


def _css_login():
    """CSS para a tela de login - tema escuro"""
    return """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        /* Esconder sidebar e header na tela de login */
        [data-testid="stSidebar"],
        [data-testid="collapsedControl"],
        header[data-testid="stHeader"] {
            display: none !important;
        }

        .stApp {
            background-color: #0f172a !important;
        }

        .main .block-container {
            max-width: 380px;
            padding-top: 1rem;
        }

        .login-card {
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 1.2rem 1.5rem 1rem 1.5rem;
            margin-top: 0.5rem;
        }

        .login-title {
            color: #f1f5f9;
            font-family: 'Inter', sans-serif;
            font-size: 1.1rem;
            font-weight: 700;
            text-align: center;
            margin-bottom: 0.1rem;
        }

        .login-subtitle {
            color: #94a3b8;
            font-family: 'Inter', sans-serif;
            font-size: 0.75rem;
            text-align: center;
            margin-bottom: 0.8rem;
        }

        .login-footer {
            color: #64748b;
            font-family: 'Inter', sans-serif;
            font-size: 0.65rem;
            text-align: center;
            margin-top: 0.8rem;
        }

        /* Reduzir espaco entre inputs */
        .stTextInput {
            margin-bottom: -0.5rem !important;
        }

        /* Estilizar inputs dentro do form */
        .stTextInput > div > div {
            background: #0f172a !important;
            border: 1px solid #334155 !important;
            border-radius: 8px !important;
        }
        .stTextInput input {
            color: #f1f5f9 !important;
            font-family: 'Inter', sans-serif !important;
        }
        .stTextInput label {
            color: #94a3b8 !important;
            font-family: 'Inter', sans-serif !important;
            font-size: 0.85rem !important;
        }

        /* Botao primario verde */
        .stFormSubmitButton > button {
            background: #00873D !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            font-family: 'Inter', sans-serif !important;
            padding: 0.6rem 1rem !important;
            width: 100% !important;
            font-size: 0.95rem !important;
        }
        .stFormSubmitButton > button:hover {
            background: #005A28 !important;
        }
    </style>
    """


def render_login():
    """Renderiza a tela de login. Retorna True se autenticado."""

    if st.session_state.get('autenticado'):
        return True

    # Aplicar CSS
    st.markdown(_css_login(), unsafe_allow_html=True)

    # Logo centralizada (compacta)
    col1, col2, col3 = st.columns([1.2, 1, 1.2])
    with col2:
        st.image("logos/VERTICAL BRANCO.png", use_container_width=True)

    # Card de login
    st.markdown('<div class="login-card">', unsafe_allow_html=True)

    st.markdown('<p class="login-title">Bem-vindo</p>', unsafe_allow_html=True)
    st.markdown('<p class="login-subtitle">Acesse o Dashboard Financeiro</p>', unsafe_allow_html=True)

    with st.form("form_login", clear_on_submit=False):
        email = st.text_input("Email", placeholder="seu@email.com")
        senha = st.text_input("Senha", type="password", placeholder="Sua senha")
        submit = st.form_submit_button("Entrar", use_container_width=True)

        if submit:
            if not email or not senha:
                st.error("Preencha todos os campos.")
            else:
                resultado = autenticar_usuario(email, senha)
                if resultado["sucesso"]:
                    st.session_state.autenticado = True
                    st.session_state.usuario = resultado["usuario"]
                    st.rerun()
                else:
                    st.error(resultado["mensagem"])

    st.markdown('</div>', unsafe_allow_html=True)

    # Footer
    st.markdown('<p class="login-footer">Grupo Progresso - Dashboard Financeiro</p>', unsafe_allow_html=True)

    return False
