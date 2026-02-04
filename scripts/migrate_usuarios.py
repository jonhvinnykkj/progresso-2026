"""
Script de migracao - Cria tabela de usuarios e admin inicial
Executar uma vez: python migrate_usuarios.py
Idempotente: pode rodar multiplas vezes sem problemas.
"""
from auth.database import criar_tabela_usuarios, _get_engine
from auth.security import gerar_hash_senha
from sqlalchemy import text


def main():
    print("=" * 50)
    print("MIGRACAO - TABELA USUARIOS")
    print("=" * 50)

    # 1. Criar tabela (com campo perfil)
    print("\n[1/3] Criando tabela usuarios...")
    criar_tabela_usuarios()
    print("  [OK] Tabela criada/verificada")

    engine = _get_engine()

    # 2. Adicionar coluna perfil se nao existir
    print("\n[2/3] Verificando coluna 'perfil'...")
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'usuarios' AND column_name = 'perfil'
        """))
        if result.fetchone():
            print("  [OK] Coluna 'perfil' ja existe")
        else:
            conn.execute(text("""
                ALTER TABLE usuarios
                ADD COLUMN perfil VARCHAR(20) DEFAULT 'usuario'
            """))
            conn.commit()
            print("  [OK] Coluna 'perfil' adicionada")

    # 3. Criar/atualizar usuario admin
    print("\n[3/3] Verificando usuario admin...")
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT id, perfil FROM usuarios WHERE email = :email"),
            {"email": "admin@grupoprogresso.com.br"}
        )
        row = result.fetchone()

        if row:
            id_, perfil = row
            if perfil != 'admin':
                conn.execute(
                    text("UPDATE usuarios SET perfil = 'admin' WHERE id = :id"),
                    {"id": id_}
                )
                conn.commit()
                print("  [OK] Admin atualizado com perfil='admin'")
            else:
                print("  [OK] Admin ja existe com perfil correto")
        else:
            senha_hash = gerar_hash_senha("mudar123")
            conn.execute(
                text("""
                    INSERT INTO usuarios (nome, email, senha_hash, perfil)
                    VALUES (:nome, :email, :senha_hash, :perfil)
                """),
                {
                    "nome": "Administrador",
                    "email": "admin@grupoprogresso.com.br",
                    "senha_hash": senha_hash,
                    "perfil": "admin"
                }
            )
            conn.commit()
            print("  [OK] Admin criado: admin@grupoprogresso.com.br / mudar123")

    print("\n" + "=" * 50)
    print("MIGRACAO CONCLUIDA!")
    print("=" * 50)


if __name__ == "__main__":
    main()
