"""
CRUD de usuarios no PostgreSQL (Neon)
Dashboard Financeiro - Grupo Progresso
"""
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
from datetime import datetime
import streamlit as st

from auth.security import gerar_hash_senha, verificar_senha, validar_forca_senha

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')


@st.cache_resource
def _get_engine():
    """Cria engine de conexao (singleton por sessao do Streamlit)"""
    return create_engine(DATABASE_URL, pool_pre_ping=True)


def criar_tabela_usuarios():
    """Cria tabela de usuarios se nao existir (com campo perfil)"""
    engine = _get_engine()
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(100) NOT NULL,
                email VARCHAR(255) NOT NULL UNIQUE,
                senha_hash VARCHAR(512) NOT NULL,
                perfil VARCHAR(20) DEFAULT 'usuario',
                ativo BOOLEAN DEFAULT TRUE,
                criado_em TIMESTAMP DEFAULT NOW(),
                ultimo_login TIMESTAMP
            )
        """))
        conn.commit()


def autenticar_usuario(email: str, senha: str) -> dict:
    """
    Autentica usuario por email e senha.

    Retorna dict:
        {"sucesso": True, "usuario": {"id", "nome", "email", "perfil"}} ou
        {"sucesso": False, "mensagem": "..."}
    """
    engine = _get_engine()
    email = email.strip().lower()

    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT id, nome, email, senha_hash, perfil, ativo FROM usuarios WHERE email = :email"),
            {"email": email}
        )
        row = result.fetchone()

        if not row:
            return {"sucesso": False, "mensagem": "Email ou senha incorretos."}

        id_, nome, email_db, senha_hash, perfil, ativo = row

        if not ativo:
            return {"sucesso": False, "mensagem": "Conta desativada. Contate o administrador."}

        if not verificar_senha(senha, senha_hash):
            return {"sucesso": False, "mensagem": "Email ou senha incorretos."}

        # Atualizar ultimo login
        conn.execute(
            text("UPDATE usuarios SET ultimo_login = :agora WHERE id = :id"),
            {"agora": datetime.now(), "id": id_}
        )
        conn.commit()

    return {
        "sucesso": True,
        "usuario": {
            "id": id_,
            "nome": nome,
            "email": email_db,
            "perfil": perfil or "usuario"
        }
    }


def criar_usuario(nome: str, email: str, senha: str, perfil: str = "usuario") -> dict:
    """
    Cria novo usuario (uso admin).

    Retorna dict com resultado:
        {"sucesso": True, "mensagem": "..."} ou
        {"sucesso": False, "mensagem": "..."}
    """
    engine = _get_engine()
    email = email.strip().lower()
    nome = nome.strip()

    if not nome:
        return {"sucesso": False, "mensagem": "Nome e obrigatorio."}
    if not email or '@' not in email:
        return {"sucesso": False, "mensagem": "Email invalido."}

    valida, msg = validar_forca_senha(senha)
    if not valida:
        return {"sucesso": False, "mensagem": msg}

    if perfil not in ("admin", "usuario"):
        return {"sucesso": False, "mensagem": "Perfil deve ser 'admin' ou 'usuario'."}

    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT id FROM usuarios WHERE email = :email"),
            {"email": email}
        )
        if result.fetchone():
            return {"sucesso": False, "mensagem": "Este email ja esta cadastrado."}

        senha_hash = gerar_hash_senha(senha)
        conn.execute(
            text("""
                INSERT INTO usuarios (nome, email, senha_hash, perfil)
                VALUES (:nome, :email, :senha_hash, :perfil)
            """),
            {"nome": nome, "email": email, "senha_hash": senha_hash, "perfil": perfil}
        )
        conn.commit()

    return {"sucesso": True, "mensagem": "Usuario criado com sucesso!"}


def listar_usuarios() -> list:
    """Lista todos os usuarios cadastrados (uso admin)."""
    engine = _get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT id, nome, email, perfil, ativo, criado_em, ultimo_login
                FROM usuarios
                ORDER BY criado_em DESC
            """)
        )
        usuarios = []
        for row in result:
            usuarios.append({
                "id": row[0],
                "nome": row[1],
                "email": row[2],
                "perfil": row[3] or "usuario",
                "ativo": row[4],
                "criado_em": row[5],
                "ultimo_login": row[6]
            })
    return usuarios


def alternar_status_usuario(usuario_id: int) -> dict:
    """Ativa/desativa usuario (toggle)."""
    engine = _get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT ativo FROM usuarios WHERE id = :id"),
            {"id": usuario_id}
        )
        row = result.fetchone()
        if not row:
            return {"sucesso": False, "mensagem": "Usuario nao encontrado."}

        novo_status = not row[0]
        conn.execute(
            text("UPDATE usuarios SET ativo = :ativo WHERE id = :id"),
            {"ativo": novo_status, "id": usuario_id}
        )
        conn.commit()

    status_texto = "ativado" if novo_status else "desativado"
    return {"sucesso": True, "mensagem": f"Usuario {status_texto} com sucesso!"}


def redefinir_senha(usuario_id: int, nova_senha: str) -> dict:
    """Admin reseta senha de um usuario."""
    valida, msg = validar_forca_senha(nova_senha)
    if not valida:
        return {"sucesso": False, "mensagem": msg}

    engine = _get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT id FROM usuarios WHERE id = :id"),
            {"id": usuario_id}
        )
        if not result.fetchone():
            return {"sucesso": False, "mensagem": "Usuario nao encontrado."}

        senha_hash = gerar_hash_senha(nova_senha)
        conn.execute(
            text("UPDATE usuarios SET senha_hash = :senha_hash WHERE id = :id"),
            {"senha_hash": senha_hash, "id": usuario_id}
        )
        conn.commit()

    return {"sucesso": True, "mensagem": "Senha redefinida com sucesso!"}


def alterar_senha(usuario_id: int, senha_atual: str, nova_senha: str) -> dict:
    """Usuario altera propria senha."""
    valida, msg = validar_forca_senha(nova_senha)
    if not valida:
        return {"sucesso": False, "mensagem": msg}

    engine = _get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT senha_hash FROM usuarios WHERE id = :id"),
            {"id": usuario_id}
        )
        row = result.fetchone()
        if not row:
            return {"sucesso": False, "mensagem": "Usuario nao encontrado."}

        if not verificar_senha(senha_atual, row[0]):
            return {"sucesso": False, "mensagem": "Senha atual incorreta."}

        senha_hash = gerar_hash_senha(nova_senha)
        conn.execute(
            text("UPDATE usuarios SET senha_hash = :senha_hash WHERE id = :id"),
            {"senha_hash": senha_hash, "id": usuario_id}
        )
        conn.commit()

    return {"sucesso": True, "mensagem": "Senha alterada com sucesso!"}
