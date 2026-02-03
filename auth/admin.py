"""
Painel de Gestao de Usuarios (Admin)
Dashboard Financeiro - Grupo Progresso
"""
import streamlit as st
from auth import is_admin
from auth.database import (
    criar_usuario,
    listar_usuarios,
    alternar_status_usuario,
    redefinir_senha,
)
from config.theme import get_cores


def render_admin_usuarios():
    """Renderiza o painel de gestao de usuarios. Apenas admins."""
    if not is_admin():
        st.error("Acesso negado. Apenas administradores podem acessar esta pagina.")
        return

    cores = get_cores()

    # CSS do painel admin
    st.markdown(f"""
    <style>
        .admin-header {{
            background: {cores['card']};
            border: 1px solid {cores['borda']};
            border-radius: 12px;
            padding: 1rem 1.5rem;
            margin-bottom: 1rem;
        }}
        .admin-title {{
            color: {cores['texto']};
            font-size: 1.2rem;
            font-weight: 700;
            margin: 0;
        }}
        .admin-subtitle {{
            color: {cores['texto_secundario']};
            font-size: 0.8rem;
            margin: 0;
        }}
        .user-card {{
            background: {cores['card']};
            border: 1px solid {cores['borda']};
            border-radius: 10px;
            padding: 1rem;
            margin-bottom: 0.5rem;
        }}
        .user-name {{
            color: {cores['texto']};
            font-weight: 600;
            font-size: 0.95rem;
        }}
        .user-email {{
            color: {cores['texto_secundario']};
            font-size: 0.8rem;
        }}
        .badge-admin {{
            background: {cores['primaria']}25;
            color: {cores['primaria']};
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: 600;
        }}
        .badge-usuario {{
            background: {cores['info']}25;
            color: {cores['info']};
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: 600;
        }}
        .badge-ativo {{
            background: {cores['sucesso']}25;
            color: {cores['sucesso']};
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: 600;
        }}
        .badge-inativo {{
            background: {cores['perigo']}25;
            color: {cores['perigo']};
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: 600;
        }}
    </style>
    """, unsafe_allow_html=True)

    # Header
    st.markdown(f"""
    <div class="admin-header">
        <p class="admin-title">Gerenciar Usuarios</p>
        <p class="admin-subtitle">Criar, ativar/desativar e redefinir senhas</p>
    </div>
    """, unsafe_allow_html=True)

    # Tabs
    tab_criar, tab_listar = st.tabs(["Criar Usuario", "Usuarios Cadastrados"])

    # --- Tab: Criar Usuario ---
    with tab_criar:
        st.markdown(f"""
        <div style="color: {cores['texto_secundario']}; font-size: 0.85rem; margin-bottom: 1rem;">
            Preencha os dados para criar um novo usuario.
        </div>
        """, unsafe_allow_html=True)

        with st.form("form_criar_usuario", clear_on_submit=True):
            nome = st.text_input("Nome completo", placeholder="Nome do usuario")
            email = st.text_input("Email", placeholder="usuario@email.com")
            senha = st.text_input("Senha inicial", type="password", placeholder="Minimo 6 caracteres")
            perfil = st.selectbox("Perfil", ["usuario", "admin"])
            submit = st.form_submit_button("Criar Usuario", use_container_width=True)

            if submit:
                if not nome or not email or not senha:
                    st.error("Preencha todos os campos.")
                else:
                    resultado = criar_usuario(nome, email, senha, perfil)
                    if resultado["sucesso"]:
                        st.success(resultado["mensagem"])
                    else:
                        st.error(resultado["mensagem"])

    # --- Tab: Listar Usuarios ---
    with tab_listar:
        usuarios = listar_usuarios()

        if not usuarios:
            st.info("Nenhum usuario cadastrado.")
            return

        st.markdown(f"""
        <div style="color: {cores['texto_secundario']}; font-size: 0.85rem; margin-bottom: 1rem;">
            {len(usuarios)} usuario(s) cadastrado(s)
        </div>
        """, unsafe_allow_html=True)

        for u in usuarios:
            perfil_badge = "admin" if u["perfil"] == "admin" else "usuario"
            status_badge = "ativo" if u["ativo"] else "inativo"
            status_texto = "Ativo" if u["ativo"] else "Inativo"
            perfil_texto = "Admin" if u["perfil"] == "admin" else "Usuario"

            ultimo_login = ""
            if u["ultimo_login"]:
                ultimo_login = u["ultimo_login"].strftime("%d/%m/%Y %H:%M")

            criado_em = ""
            if u["criado_em"]:
                criado_em = u["criado_em"].strftime("%d/%m/%Y")

            col_info, col_acoes = st.columns([3, 2])

            with col_info:
                st.markdown(f"""
                <div class="user-card">
                    <span class="user-name">{u["nome"]}</span>
                    <span class="badge-{perfil_badge}" style="margin-left: 8px;">{perfil_texto}</span>
                    <span class="badge-{status_badge}" style="margin-left: 4px;">{status_texto}</span>
                    <br>
                    <span class="user-email">{u["email"]}</span>
                    <br>
                    <span style="color: #64748b; font-size: 0.7rem;">
                        Criado: {criado_em}
                        {f' | Ultimo login: {ultimo_login}' if ultimo_login else ''}
                    </span>
                </div>
                """, unsafe_allow_html=True)

            with col_acoes:
                col_btn1, col_btn2 = st.columns(2)

                with col_btn1:
                    btn_label = "Desativar" if u["ativo"] else "Ativar"
                    btn_type = "secondary" if u["ativo"] else "primary"
                    if st.button(
                        btn_label,
                        key=f"toggle_{u['id']}",
                        use_container_width=True,
                        type=btn_type
                    ):
                        resultado = alternar_status_usuario(u["id"])
                        if resultado["sucesso"]:
                            st.success(resultado["mensagem"])
                            st.rerun()
                        else:
                            st.error(resultado["mensagem"])

                with col_btn2:
                    if st.button(
                        "Resetar Senha",
                        key=f"reset_{u['id']}",
                        use_container_width=True,
                        type="secondary"
                    ):
                        st.session_state[f"show_reset_{u['id']}"] = True

            # Form de redefinicao de senha (expandido sob demanda)
            if st.session_state.get(f"show_reset_{u['id']}"):
                with st.form(f"form_reset_{u['id']}"):
                    nova_senha = st.text_input(
                        f"Nova senha para {u['nome']}",
                        type="password",
                        placeholder="Minimo 6 caracteres",
                        key=f"input_reset_{u['id']}"
                    )
                    col_salvar, col_cancelar = st.columns(2)
                    with col_salvar:
                        if st.form_submit_button("Salvar", use_container_width=True):
                            if nova_senha:
                                resultado = redefinir_senha(u["id"], nova_senha)
                                if resultado["sucesso"]:
                                    st.success(resultado["mensagem"])
                                    st.session_state[f"show_reset_{u['id']}"] = False
                                    st.rerun()
                                else:
                                    st.error(resultado["mensagem"])
                            else:
                                st.error("Digite a nova senha.")
                    with col_cancelar:
                        if st.form_submit_button("Cancelar", use_container_width=True):
                            st.session_state[f"show_reset_{u['id']}"] = False
                            st.rerun()

            st.divider()
