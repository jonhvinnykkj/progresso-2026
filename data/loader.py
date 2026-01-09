"""
Carregamento e processamento de dados
"""
import pandas as pd
import streamlit as st
from datetime import datetime
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os

from config.settings import CACHE_TTL

# Carregar variáveis de ambiente
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')


def get_engine():
    """Cria engine de conexão com o Neon"""
    return create_engine(DATABASE_URL)


def padronizar_forma_pagamento(serie):
    """Padroniza as formas de pagamento para evitar duplicatas"""
    # Mapeamento de variações para forma padronizada
    mapeamento = {
        # Boleto
        'BOLETO': 'Boleto',
        'BOLETO BANCARIO': 'Boleto',
        'BOLETO BANCÁRIO': 'Boleto',
        'BOL': 'Boleto',
        'BOLETOS': 'Boleto',

        # PIX
        'PIX': 'PIX',
        'TRANSFERENCIA PIX': 'PIX',
        'TRANSFERÊNCIA PIX': 'PIX',
        'TED/PIX': 'PIX',

        # Transferência/TED/DOC
        'TRANSFERENCIA': 'Transferencia',
        'TRANSFERÊNCIA': 'Transferencia',
        'TRANSFERENCIA BANCARIA': 'Transferencia',
        'TRANSFERÊNCIA BANCÁRIA': 'Transferencia',
        'TED': 'Transferencia',
        'DOC': 'Transferencia',
        'TED/DOC': 'Transferencia',

        # Débito em Conta
        'DEBITO EM CONTA': 'Debito em Conta',
        'DÉBITO EM CONTA': 'Debito em Conta',
        'DEBITO CONTA': 'Debito em Conta',
        'DÉBITO CONTA': 'Debito em Conta',
        'DEB. CONTA': 'Debito em Conta',
        'DEBITO AUTOMATICO': 'Debito em Conta',
        'DÉBITO AUTOMÁTICO': 'Debito em Conta',
        'DEB. AUTOMATICO': 'Debito em Conta',

        # Cartão de Crédito
        'CARTAO DE CREDITO': 'Cartao Credito',
        'CARTÃO DE CRÉDITO': 'Cartao Credito',
        'CARTAO CREDITO': 'Cartao Credito',
        'CARTÃO CRÉDITO': 'Cartao Credito',
        'CART. CREDITO': 'Cartao Credito',
        'CARTAO': 'Cartao Credito',
        'CARTÃO': 'Cartao Credito',
        'C. CREDITO': 'Cartao Credito',

        # Cartão de Débito
        'CARTAO DE DEBITO': 'Cartao Debito',
        'CARTÃO DE DÉBITO': 'Cartao Debito',
        'CARTAO DEBITO': 'Cartao Debito',
        'CARTÃO DÉBITO': 'Cartao Debito',

        # Dinheiro/Espécie
        'DINHEIRO': 'Dinheiro',
        'ESPECIE': 'Dinheiro',
        'ESPÉCIE': 'Dinheiro',
        'EM ESPECIE': 'Dinheiro',
        'EM ESPÉCIE': 'Dinheiro',

        # Cheque
        'CHEQUE': 'Cheque',
        'CHQ': 'Cheque',
        'CHEQUES': 'Cheque',
        'CHEQUE A VISTA': 'Cheque',
        'CHEQUE À VISTA': 'Cheque',
        'CHEQUE PRE': 'Cheque Pre-datado',
        'CHEQUE PRÉ': 'Cheque Pre-datado',
        'CHEQUE PRE-DATADO': 'Cheque Pre-datado',
        'CHEQUE PRÉ-DATADO': 'Cheque Pre-datado',

        # Compensação/Encontro de Contas
        'COMPENSACAO': 'Compensacao',
        'COMPENSAÇÃO': 'Compensacao',
        'ENCONTRO DE CONTAS': 'Compensacao',
        'ACERTO': 'Compensacao',

        # Depósito
        'DEPOSITO': 'Deposito',
        'DEPÓSITO': 'Deposito',
        'DEPOSITO BANCARIO': 'Deposito',
        'DEPÓSITO BANCÁRIO': 'Deposito',
        'DEP. BANCARIO': 'Deposito',

        # Duplicata/Cobrança
        'DUPLICATA': 'Duplicata',
        'COBRANCA': 'Cobranca',
        'COBRANÇA': 'Cobranca',
        'COBRANCA BANCARIA': 'Cobranca',
        'COBRANÇA BANCÁRIA': 'Cobranca',

        # Outros
        'A DEFINIR': 'A Definir',
        'NAO INFORMADO': 'Nao Informado',
        'NÃO INFORMADO': 'Nao Informado',
        'OUTROS': 'Outros',
        'OUTRO': 'Outros',
    }

    def mapear(valor):
        if pd.isna(valor) or str(valor).strip() == '':
            return ''
        valor_upper = str(valor).upper().strip()
        # Tenta encontrar no mapeamento
        if valor_upper in mapeamento:
            return mapeamento[valor_upper]
        # Se não encontrar, retorna o valor original com primeira letra maiúscula
        return str(valor).strip().title()

    return serie.apply(mapear)


@st.cache_data(ttl=CACHE_TTL)
def carregar_dados():
    """Carrega e processa os dados do banco Neon PostgreSQL"""
    engine = get_engine()

    # Carregar dados do banco (colunas em lowercase)
    df_contas = pd.read_sql("SELECT * FROM contas_pagar", engine)
    df_adiant = pd.read_sql("SELECT * FROM adiantamentos", engine)
    df_baixas = pd.read_sql("SELECT * FROM baixas_adiantamentos", engine)

    # Converter nomes de colunas para uppercase (compatibilidade)
    df_contas.columns = [c.upper() for c in df_contas.columns]
    df_adiant.columns = [c.upper() for c in df_adiant.columns]
    df_baixas.columns = [c.upper() for c in df_baixas.columns]

    # Converter colunas de data
    for col in ['EMISSAO', 'VENCIMENTO', 'VENCTO_REAL', 'DT_BAIXA']:
        for df in [df_contas, df_adiant, df_baixas]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')

    hoje = datetime.now()

    # Adicionar colunas temporais
    df_contas['ANO'] = df_contas['EMISSAO'].dt.year
    df_contas['MES'] = df_contas['EMISSAO'].dt.month
    df_contas['TRIMESTRE'] = df_contas['EMISSAO'].dt.quarter

    # Calcular dias até vencimento
    df_contas['DIAS_VENC'] = (df_contas['VENCIMENTO'] - hoje).dt.days

    # Classificar status usando vetorização
    df_contas['STATUS'] = 'Vence em +60 dias'
    df_contas.loc[df_contas['SALDO'] <= 0, 'STATUS'] = 'Pago'
    df_contas.loc[df_contas['VENCIMENTO'].isna() & (df_contas['SALDO'] > 0), 'STATUS'] = 'Sem data'
    df_contas.loc[(df_contas['DIAS_VENC'] < 0) & (df_contas['SALDO'] > 0), 'STATUS'] = 'Vencido'
    df_contas.loc[(df_contas['DIAS_VENC'] >= 0) & (df_contas['DIAS_VENC'] <= 7) & (df_contas['SALDO'] > 0), 'STATUS'] = 'Vence em 7 dias'
    df_contas.loc[(df_contas['DIAS_VENC'] > 7) & (df_contas['DIAS_VENC'] <= 15) & (df_contas['SALDO'] > 0), 'STATUS'] = 'Vence em 15 dias'
    df_contas.loc[(df_contas['DIAS_VENC'] > 15) & (df_contas['DIAS_VENC'] <= 30) & (df_contas['SALDO'] > 0), 'STATUS'] = 'Vence em 30 dias'
    df_contas.loc[(df_contas['DIAS_VENC'] > 30) & (df_contas['DIAS_VENC'] <= 60) & (df_contas['SALDO'] > 0), 'STATUS'] = 'Vence em 60 dias'

    # Calcular dias de atraso
    df_contas['DIAS_ATRASO'] = 0
    mask_vencido = (df_contas['STATUS'] == 'Vencido') & df_contas['DIAS_VENC'].notna()
    df_contas.loc[mask_vencido, 'DIAS_ATRASO'] = df_contas.loc[mask_vencido, 'DIAS_VENC'].abs()

    # Calcular dias para pagar (da emissao ate o pagamento)
    if 'DT_BAIXA' in df_contas.columns:
        df_contas['DIAS_PARA_PAGAR'] = (df_contas['DT_BAIXA'] - df_contas['EMISSAO']).dt.days
        # Se pagou antes do vencimento = negativo (antecipado), se pagou depois = positivo (atrasado)
        df_contas['DIAS_ATRASO_PGTO'] = (df_contas['DT_BAIXA'] - df_contas['VENCIMENTO']).dt.days
    else:
        df_contas['DIAS_PARA_PAGAR'] = None
        df_contas['DIAS_ATRASO_PGTO'] = None

    # Classificar COM NF / SEM NF
    tipos_com_nf = ['NF', 'NFE', 'NFSE', 'NDF', 'FT']
    df_contas['COM_NF'] = df_contas['TIPO'].isin(tipos_com_nf)
    df_contas['TIPO_DOC'] = df_contas['COM_NF'].map({True: 'Com NF', False: 'Sem NF'})

    # Padronizar formas de pagamento
    if 'DESCRICAO_FORMA_PAGAMENTO' in df_contas.columns:
        df_contas['DESCRICAO_FORMA_PAGAMENTO'] = padronizar_forma_pagamento(df_contas['DESCRICAO_FORMA_PAGAMENTO'])

    # Alerta NF entrada < 48h do vencimento
    if 'DIF_HORAS_DATAS' in df_contas.columns:
        df_contas['ALERTA_48H'] = (df_contas['DIF_HORAS_DATAS'].abs() <= 48) & (df_contas['SALDO'] > 0)
    elif 'DIF_DIAS_DATAS' in df_contas.columns:
        df_contas['ALERTA_48H'] = (df_contas['DIF_DIAS_DATAS'].abs() <= 2) & (df_contas['SALDO'] > 0)
    else:
        df_contas['ALERTA_48H'] = False

    # Garantir valores numéricos para colunas financeiras
    colunas_financeiras = ['VALOR_JUROS', 'VALOR_MULTA', 'VLR_DESCONTO', 'VALOR_CORRECAO',
                           'VALOR_ACRESCIMO', 'VALOR_DECRESCIMO', 'TX_MOEDA', 'VALOR_REAL']
    for col in colunas_financeiras:
        if col in df_contas.columns:
            df_contas[col] = pd.to_numeric(df_contas[col], errors='coerce').fillna(0)

    # Calcular intervalo entre adiantamento e baixa
    if 'DIF_DIAS_EMIS_BAIXA' in df_baixas.columns:
        df_baixas['DIAS_ATE_BAIXA'] = pd.to_numeric(df_baixas['DIF_DIAS_EMIS_BAIXA'], errors='coerce').fillna(0)

    return df_contas, df_adiant, df_baixas


def aplicar_filtros(df_contas, data_inicio, data_fim, filtro_filial, filtro_status, filtro_categoria,
                    busca_fornecedor, filtro_tipo_doc='Todos', filtro_forma_pagto='Todas'):
    """Aplica filtros de forma otimizada usando máscaras booleanas"""
    # Criar máscara base para datas
    mask = (df_contas['EMISSAO'].dt.date >= data_inicio) & (df_contas['EMISSAO'].dt.date <= data_fim)

    # Aplicar filtros adicionais
    if filtro_filial != 'Todas as Filiais':
        mask &= (df_contas['NOME_FILIAL'] == filtro_filial)

    if filtro_status != 'Todos os Status':
        if filtro_status == 'Pago':
            mask &= (df_contas['SALDO'] == 0)
        elif filtro_status == 'Vencido':
            mask &= (df_contas['STATUS'] == 'Vencido')
        elif filtro_status == 'Vence em 7 dias':
            mask &= (df_contas['STATUS'] == 'Vence em 7 dias')
        elif filtro_status == 'Vence em 15 dias':
            mask &= (df_contas['STATUS'] == 'Vence em 15 dias')
        elif filtro_status == 'Vence em 30 dias':
            mask &= (df_contas['STATUS'] == 'Vence em 30 dias')

    if filtro_categoria != 'Todas as Categorias':
        mask &= (df_contas['DESCRICAO'] == filtro_categoria)

    if busca_fornecedor:
        mask &= df_contas['NOME_FORNECEDOR'].str.contains(busca_fornecedor, case=False, na=False)

    # Filtro por tipo de documento (Com NF / Sem NF)
    if filtro_tipo_doc != 'Todos' and 'TIPO_DOC' in df_contas.columns:
        mask &= (df_contas['TIPO_DOC'] == filtro_tipo_doc)

    # Filtro por forma de pagamento
    if filtro_forma_pagto != 'Todas' and 'DESCRICAO_FORMA_PAGAMENTO' in df_contas.columns:
        mask &= (df_contas['DESCRICAO_FORMA_PAGAMENTO'] == filtro_forma_pagto)

    return df_contas[mask]


@st.cache_data
def get_opcoes_filtros(_df_contas):
    """Pré-calcula as opções de filtros"""
    filiais = ['Todas as Filiais'] + sorted(_df_contas['NOME_FILIAL'].dropna().unique().tolist())
    categorias = ['Todas as Categorias'] + sorted(_df_contas['DESCRICAO'].dropna().unique().tolist())
    return filiais, categorias


def get_dados_filtrados(df, df_contas):
    """Retorna dataframes filtrados comuns"""
    df_pendentes = df[df['SALDO'] > 0]
    df_vencidos = df[df['STATUS'] == 'Vencido']
    return df_pendentes, df_vencidos


def calcular_metricas(df, df_vencidos):
    """Calcula métricas principais do dashboard"""
    total = df['VALOR_ORIGINAL'].sum()
    pago = total - df['SALDO'].sum()
    pendente = df['SALDO'].sum()
    vencido = df_vencidos['SALDO'].sum()
    pct_pago = (pago / total * 100) if total > 0 else 0
    dias_atraso = df_vencidos['DIAS_ATRASO'].mean() if len(df_vencidos) > 0 else 0

    return {
        'total': total,
        'pago': pago,
        'pendente': pendente,
        'vencido': vencido,
        'pct_pago': pct_pago,
        'dias_atraso': dias_atraso,
        'qtd_total': len(df),
        'qtd_vencidos': len(df_vencidos)
    }
