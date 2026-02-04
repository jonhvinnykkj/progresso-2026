"""
Carregamento e processamento de dados
"""
import pandas as pd
import streamlit as st
from datetime import datetime

from config.settings import CACHE_TTL, INTERCOMPANY_PADRONIZACAO, INTERCOMPANY_PATTERNS, GRUPOS_FILIAIS, get_grupo_filial


def padronizar_nome_intercompany(nome):
    """Padroniza nomes de empresas do grupo para comparação correta"""
    if pd.isna(nome):
        return nome

    nome_limpo = str(nome).strip().upper()

    # Busca no mapeamento de padronização
    for variacao, padrao in INTERCOMPANY_PADRONIZACAO.items():
        if variacao.upper() in nome_limpo:
            return padrao

    return nome  # Retorna original se não for intercompany


def eh_intercompany(nome):
    """Verifica se o nome é de uma empresa do grupo"""
    if pd.isna(nome):
        return False
    nome_upper = str(nome).strip().upper()
    return any(p.upper() in nome_upper for p in INTERCOMPANY_PATTERNS)


def padronizar_forma_pagamento(serie):
    """Padroniza as formas de pagamento para evitar duplicatas"""
    # Regras de mapeamento por padrão (ordem importa - mais específico primeiro)
    regras = [
        # PIX (antes de transferência para evitar conflito)
        ('PIX', 'PIX'),

        # Boleto
        ('BOLETO', 'Boleto'),
        ('COBRANCA', 'Boleto'),
        ('COBRANÇA', 'Boleto'),

        # TED/Transferência
        ('TED', 'TED'),
        ('TRANSFER', 'TED'),  # Captura TRANSFERENCIA, TRANSFERÊNCIA, etc
        ('CREDITO EM CONTA', 'TED'),

        # Compensação
        ('COMPENSACAO', 'Compensacao'),
        ('COMPENSAÇÃO', 'Compensacao'),
        ('TITULO PARA COMPENSACAO', 'Compensacao'),

        # Dinheiro
        ('DINHEIRO', 'Dinheiro'),
        ('ESPECIE', 'Dinheiro'),
        ('ESPÉCIE', 'Dinheiro'),

        # Cheque
        ('CHEQUE', 'Cheque'),

        # Débito em Conta
        ('DEBITO', 'Debito em Conta'),
        ('DÉBITO', 'Debito em Conta'),

        # Cartão
        ('CARTAO', 'Cartao'),
        ('CARTÃO', 'Cartao'),

        # Depósito
        ('DEPOSITO', 'Deposito'),
        ('DEPÓSITO', 'Deposito'),

        # Tributos
        ('TRIBUTO', 'Tributos'),
        ('DARF', 'Tributos'),
        ('GPS', 'Tributos'),
        ('FGTS', 'Tributos'),

        # Concessionárias
        ('CONCESSIONARIA', 'Concessionarias'),
        ('CONCESSIONÁRIA', 'Concessionarias'),

        # Sem pagamento
        ('SEM PAGAMENTO', 'Sem Pagamento'),
    ]

    def mapear(valor):
        if pd.isna(valor) or str(valor).strip() == '':
            return 'Nao Informado'

        valor_upper = str(valor).upper().strip()

        # Corrigir encoding quebrado (caractere � = encoding issue)
        valor_upper = valor_upper.replace('�', 'E')

        # Buscar por padrão (contains)
        for padrao, resultado in regras:
            if padrao in valor_upper:
                return resultado

        # Se não encontrar, retorna "Outros"
        return 'Outros'

    return serie.apply(mapear)


@st.cache_data(ttl=CACHE_TTL)
def carregar_dados():
    """Carrega e processa os dados dos arquivos Excel"""

    # Carregar dados dos arquivos Excel
    # Adiantamentos sao extraidos do proprio Contas a Pagar (evita duplicacao)
    df_contas = pd.read_excel('data/Contas a Pagar.xlsx')
    df_baixas = pd.read_excel('data/Baixas de adiantamentos a pagar.xlsx')

    # Converter nomes de colunas para uppercase (compatibilidade)
    df_contas.columns = [c.upper() for c in df_contas.columns]
    df_baixas.columns = [c.upper() for c in df_baixas.columns]

    # Converter colunas de data
    for col in ['EMISSAO', 'VENCIMENTO', 'VENCTO_REAL', 'DT_BAIXA']:
        for df in [df_contas, df_baixas]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')

    hoje = datetime.now()

    # Adicionar colunas temporais
    df_contas['ANO'] = df_contas['EMISSAO'].dt.year
    df_contas['MES'] = df_contas['EMISSAO'].dt.month
    df_contas['TRIMESTRE'] = df_contas['EMISSAO'].dt.quarter

    # Usar VENCTO_REAL como data de vencimento (fallback para VENCIMENTO se não existir)
    df_contas['DATA_VENC'] = df_contas['VENCTO_REAL'].fillna(df_contas['VENCIMENTO'])

    # Calcular dias até vencimento (usando VENCTO_REAL)
    df_contas['DIAS_VENC'] = (df_contas['DATA_VENC'] - hoje).dt.days

    # Classificar status usando vetorização
    df_contas['STATUS'] = 'Vence em +60 dias'
    df_contas.loc[df_contas['SALDO'] <= 0, 'STATUS'] = 'Pago'
    df_contas.loc[df_contas['DATA_VENC'].isna() & (df_contas['SALDO'] > 0), 'STATUS'] = 'Sem data'
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
        df_contas['DIAS_ATRASO_PGTO'] = (df_contas['DT_BAIXA'] - df_contas['DATA_VENC']).dt.days
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

    # Padronizar nomes de fornecedores intercompany
    if 'NOME_FORNECEDOR' in df_contas.columns:
        df_contas['FORNECEDOR_IC_PADRAO'] = df_contas['NOME_FORNECEDOR'].apply(padronizar_nome_intercompany)
        df_contas['IS_INTERCOMPANY'] = df_contas['NOME_FORNECEDOR'].apply(eh_intercompany)

    # Identificar adiantamentos (ADTO FORNECEDOR, ADTO SALARIOS, etc.)
    if 'DESCRICAO' in df_contas.columns:
        df_contas['IS_ADIANTAMENTO'] = df_contas['DESCRICAO'].str.upper().str.contains(
            'ADTO|ADIANT', na=False, regex=True
        )
    else:
        df_contas['IS_ADIANTAMENTO'] = False

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

    return df_contas, df_baixas


def aplicar_filtros(df_contas, data_inicio, data_fim, filtro_filiais, filtro_status, filtro_categoria,
                    busca_fornecedor, filtro_tipo_doc='Todos', filtro_forma_pagto='Todas'):
    """Aplica filtros de forma otimizada usando máscaras booleanas

    filtro_filiais: None (todas) ou lista de codigos int de filiais selecionadas
    """
    # Criar máscara base para datas (comparacao vetorizada em C)
    ts_inicio = pd.Timestamp(data_inicio)
    ts_fim = pd.Timestamp(data_fim) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    mask = (df_contas['EMISSAO'] >= ts_inicio) & (df_contas['EMISSAO'] <= ts_fim)

    # Aplicar filtro de filiais (lista de codigos ou None)
    if filtro_filiais is not None:
        mask &= df_contas['FILIAL'].isin(filtro_filiais)

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
    """Pré-calcula as opções de filtros com estrutura hierarquica de filiais"""
    # Criar estrutura hierarquica: {grupo_id: [(cod, nome), ...]}
    filiais_df = _df_contas[['FILIAL', 'NOME_FILIAL']].drop_duplicates().dropna()
    filiais_df = filiais_df.sort_values('FILIAL')

    filiais_por_grupo = {}
    for _, row in filiais_df.iterrows():
        cod = int(row['FILIAL'])
        nome = row['NOME_FILIAL']
        grupo_id = get_grupo_filial(cod)
        if grupo_id not in filiais_por_grupo:
            filiais_por_grupo[grupo_id] = []
        filiais_por_grupo[grupo_id].append((cod, nome))

    categorias = ['Todas as Categorias'] + sorted(_df_contas['DESCRICAO'].dropna().unique().tolist())
    return filiais_por_grupo, categorias


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
