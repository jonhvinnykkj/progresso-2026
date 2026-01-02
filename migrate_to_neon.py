"""
Script para migrar dados Excel para o banco Neon PostgreSQL
"""
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

# Carregar variáveis de ambiente
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

def criar_engine():
    """Cria conexão com o banco Neon"""
    return create_engine(DATABASE_URL)

def migrar_dados():
    """Migra os 3 arquivos Excel para o PostgreSQL"""

    print("=" * 60)
    print("MIGRACAO EXCEL -> NEON POSTGRESQL")
    print("=" * 60)

    engine = criar_engine()

    # Testar conexão
    print("\n[1/4] Testando conexão...")
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        version = result.fetchone()[0]
        print(f"[OK] Conectado ao PostgreSQL: {version[:50]}...")

    # Ler arquivos Excel
    print("\n[2/4] Lendo arquivos Excel...")

    df_contas = pd.read_excel('Contas a Pagar.xlsx')
    print(f"  [OK] Contas a Pagar: {len(df_contas):,} registros")

    df_adiant = pd.read_excel('Adiantamentos a pagar.xlsx')
    print(f"  [OK] Adiantamentos: {len(df_adiant):,} registros")

    df_baixas = pd.read_excel('Baixas de adiantamentos a pagar.xlsx')
    print(f"  [OK] Baixas: {len(df_baixas):,} registros")

    # Converter colunas de data para datetime
    print("\n[3/4] Processando dados...")

    date_columns = ['EMISSAO', 'VENCIMENTO', 'VENCTO_REAL', 'DT_BAIXA', 'DT_ESCRITURACAO']
    for col in date_columns:
        for df in [df_contas, df_adiant, df_baixas]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')

    # Normalizar nomes de colunas (lowercase para PostgreSQL)
    df_contas.columns = [c.lower() for c in df_contas.columns]
    df_adiant.columns = [c.lower() for c in df_adiant.columns]
    df_baixas.columns = [c.lower() for c in df_baixas.columns]

    print("  [OK] Dados processados")

    # Fazer upload para o banco
    print("\n[4/4] Enviando para o Neon...")

    # Contas a Pagar
    print("  -> Enviando contas_pagar...")
    df_contas.to_sql('contas_pagar', engine, if_exists='replace', index=False, chunksize=1000)
    print(f"  [OK] contas_pagar: {len(df_contas):,} registros")

    # Adiantamentos
    print("  -> Enviando adiantamentos...")
    df_adiant.to_sql('adiantamentos', engine, if_exists='replace', index=False, chunksize=1000)
    print(f"  [OK] adiantamentos: {len(df_adiant):,} registros")

    # Baixas
    print("  -> Enviando baixas_adiantamentos...")
    df_baixas.to_sql('baixas_adiantamentos', engine, if_exists='replace', index=False, chunksize=1000)
    print(f"  [OK] baixas_adiantamentos: {len(df_baixas):,} registros")

    # Criar índices para performance
    print("\n[5/5] Criando índices...")
    with engine.connect() as conn:
        # Índices para contas_pagar
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_contas_emissao ON contas_pagar(emissao)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_contas_vencimento ON contas_pagar(vencimento)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_contas_filial ON contas_pagar(nome_filial)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_contas_fornecedor ON contas_pagar(fornecedor)"))

        # Índices para adiantamentos
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_adiant_emissao ON adiantamentos(emissao)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_adiant_filial ON adiantamentos(nome_filial)"))

        # Índices para baixas
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_baixas_dt_baixa ON baixas_adiantamentos(dt_baixa)"))

        conn.commit()
    print("  [OK] Indices criados")

    print("\n" + "=" * 60)
    print("MIGRACAO CONCLUIDA COM SUCESSO!")
    print("=" * 60)

    # Verificar contagem final
    with engine.connect() as conn:
        for tabela in ['contas_pagar', 'adiantamentos', 'baixas_adiantamentos']:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {tabela}"))
            count = result.fetchone()[0]
            print(f"  {tabela}: {count:,} registros")

if __name__ == "__main__":
    migrar_dados()
