"""
Script para atualizar o banco de dados PostgreSQL (Neon) com dados dos arquivos Excel
"""
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

# Carregar variáveis de ambiente
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

# Arquivos Excel - Contas a Pagar
ARQUIVOS_PAGAR = {
    "contas_pagar": "Contas a Pagar.xlsx",
    "adiantamentos": "Adiantamentos a pagar.xlsx",
    "baixas_adiantamentos": "Baixas de adiantamentos a pagar.xlsx"
}

# Arquivos Excel - Contas a Receber
ARQUIVOS_RECEBER = {
    "contas_receber": "Contas a receber.xlsx",
    "adiantamentos_receber": "Adiantamento a receber.xlsx",
    "baixas_adiantamentos_receber": "Baixas de adiantamentos a receber.xlsx"
}


def get_engine():
    """Cria engine de conexão com o Neon"""
    return create_engine(DATABASE_URL)


def carregar_excel(arquivo):
    """Carrega arquivo Excel e padroniza colunas"""
    print(f"  Carregando {arquivo}...")
    df = pd.read_excel(arquivo)

    # Converter nomes de colunas para lowercase (padrão do banco)
    df.columns = [c.lower().strip() for c in df.columns]

    # Limpar strings
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].apply(lambda x: str(x).strip() if pd.notna(x) else x)

    print(f"    -> {len(df)} registros carregados")
    return df


def atualizar_tabela(engine, tabela, df):
    """Atualiza tabela no banco (substitui todos os dados)"""
    print(f"  Atualizando tabela '{tabela}'...")

    # Usar replace para substituir todos os dados
    df.to_sql(tabela, engine, if_exists='replace', index=False)

    # Verificar quantidade de registros
    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT COUNT(*) FROM {tabela}"))
        count = result.scalar()

    print(f"    -> {count} registros inseridos no banco")
    return count


def main():
    print("=" * 60)
    print("ATUALIZACAO DO BANCO DE DADOS - GRUPO PROGRESSO")
    print("=" * 60)

    engine = get_engine()

    # Testar conexão
    print("\n[1] Testando conexão com o banco...")
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("    -> Conexão OK!")
    except Exception as e:
        print(f"    -> ERRO: {e}")
        return

    # Processar Contas a Pagar
    print("\n[2] Processando CONTAS A PAGAR...")
    for tabela, arquivo in ARQUIVOS_PAGAR.items():
        try:
            df = carregar_excel(arquivo)
            atualizar_tabela(engine, tabela, df)
        except FileNotFoundError:
            print(f"    -> AVISO: Arquivo '{arquivo}' não encontrado, pulando...")
        except Exception as e:
            print(f"    -> ERRO ao processar {arquivo}: {e}")

    # Processar Contas a Receber
    print("\n[3] Processando CONTAS A RECEBER...")
    for tabela, arquivo in ARQUIVOS_RECEBER.items():
        try:
            df = carregar_excel(arquivo)
            atualizar_tabela(engine, tabela, df)
        except FileNotFoundError:
            print(f"    -> AVISO: Arquivo '{arquivo}' não encontrado, pulando...")
        except Exception as e:
            print(f"    -> ERRO ao processar {arquivo}: {e}")

    # Resumo final
    print("\n" + "=" * 60)
    print("RESUMO - Tabelas no banco:")
    print("=" * 60)

    with engine.connect() as conn:
        # Listar todas as tabelas
        result = conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
        """))
        tabelas = [row[0] for row in result]

        for tabela in tabelas:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {tabela}"))
            count = result.scalar()
            print(f"  {tabela}: {count} registros")

    print("\n-> Atualização concluída com sucesso!")


if __name__ == "__main__":
    main()
