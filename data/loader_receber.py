"""
Carregamento e processamento de dados - Contas a Receber
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


@st.cache_data(ttl=CACHE_TTL)
def carregar_dados_receber():
    """Carrega e processa os dados de Contas a Receber dos arquivos Excel"""

    # Carregar dados dos arquivos Excel
    # Adiantamentos sao extraidos do proprio Contas a Receber (evita duplicacao)
    df_contas = pd.read_excel('data/Contas a receber.xlsx', sheet_name='Planilha1')
    df_baixas = pd.read_excel('data/Baixas de adiantamentos a receber.xlsx')

    # Converter nomes de colunas para uppercase (compatibilidade)
    df_contas.columns = [str(c).upper() for c in df_contas.columns]
    df_baixas.columns = [str(c).upper() for c in df_baixas.columns]

    # Garantir que colunas de nome sejam string (evita erro de tipos mistos no Arrow)
    if 'NOME_CLIENTE' in df_contas.columns:
        df_contas['NOME_CLIENTE'] = df_contas['NOME_CLIENTE'].astype(str)
    if 'NOME_CLIENTE' in df_baixas.columns:
        df_baixas['NOME_CLIENTE'] = df_baixas['NOME_CLIENTE'].astype(str)
    if 'NOME_FORNECEDOR' in df_contas.columns:
        df_contas['NOME_FORNECEDOR'] = df_contas['NOME_FORNECEDOR'].astype(str)
    if 'NOME_FORNECEDOR' in df_baixas.columns:
        df_baixas['NOME_FORNECEDOR'] = df_baixas['NOME_FORNECEDOR'].astype(str)

    # Limpar espaços da coluna TIPO (vem com espaços do Excel)
    if 'TIPO' in df_contas.columns:
        df_contas['TIPO'] = df_contas['TIPO'].str.strip()
    if 'TIPO' in df_baixas.columns:
        df_baixas['TIPO'] = df_baixas['TIPO'].str.strip()

    # Converter colunas de data
    for col in ['EMISSAO', 'VENCIMENTO', 'VENCTO_REAL', 'DT_BAIXA', 'DT_ESCRITURACAO']:
        for df in [df_contas, df_baixas]:
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
    df_contas.loc[df_contas['SALDO'] <= 0, 'STATUS'] = 'Recebido'
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

    # ========== NOVAS MÉTRICAS COM COLUNAS ADICIONAIS ==========

    # DSO - Dias para receber (para títulos baixados)
    if 'DT_BAIXA' in df_contas.columns:
        df_contas['DSO'] = (df_contas['DT_BAIXA'] - df_contas['EMISSAO']).dt.days
        df_contas.loc[df_contas['DSO'] < 0, 'DSO'] = None  # Limpar valores inválidos

        # Flag de pontualidade (recebeu antes ou no vencimento)
        df_contas['PONTUAL'] = df_contas['DT_BAIXA'] <= df_contas['VENCIMENTO']
        df_contas.loc[df_contas['DT_BAIXA'].isna(), 'PONTUAL'] = None

        # Dias de atraso no recebimento (DT_BAIXA - VENCIMENTO)
        df_contas['DIAS_ATRASO_RECEB'] = (df_contas['DT_BAIXA'] - df_contas['VENCIMENTO']).dt.days
        df_contas.loc[df_contas['DIAS_ATRASO_RECEB'] < 0, 'DIAS_ATRASO_RECEB'] = 0  # Não atrasou

    # Renegociação (VENCTO_REAL diferente de VENCIMENTO)
    if 'VENCTO_REAL' in df_contas.columns:
        df_contas['RENEGOCIADO'] = (
            df_contas['VENCTO_REAL'].notna() &
            df_contas['VENCIMENTO'].notna() &
            (df_contas['VENCTO_REAL'] != df_contas['VENCIMENTO'])
        )
        # Dias de prorrogação
        df_contas['DIAS_PRORROGACAO'] = (df_contas['VENCTO_REAL'] - df_contas['VENCIMENTO']).dt.days
        df_contas.loc[~df_contas['RENEGOCIADO'], 'DIAS_PRORROGACAO'] = 0

    # Classificar COM NF / SEM NF
    tipos_com_nf = ['NF', 'NFE', 'NFSE', 'NDF', 'FT']
    df_contas['COM_NF'] = df_contas['TIPO'].isin(tipos_com_nf)
    df_contas['TIPO_DOC'] = df_contas['COM_NF'].map({True: 'Com NF', False: 'Sem NF'})

    # Alerta NF entrada < 48h do vencimento
    if 'DIF_HORAS_DATAS' in df_contas.columns:
        df_contas['ALERTA_48H'] = (df_contas['DIF_HORAS_DATAS'].abs() <= 48) & (df_contas['SALDO'] > 0)
    elif 'DIF_DIAS_DATAS' in df_contas.columns:
        df_contas['ALERTA_48H'] = (df_contas['DIF_DIAS_DATAS'].abs() <= 2) & (df_contas['SALDO'] > 0)
    else:
        df_contas['ALERTA_48H'] = False

    # Padronizar nomes de clientes intercompany
    if 'NOME_CLIENTE' in df_contas.columns:
        df_contas['CLIENTE_IC_PADRAO'] = df_contas['NOME_CLIENTE'].apply(padronizar_nome_intercompany)
        df_contas['IS_INTERCOMPANY'] = df_contas['NOME_CLIENTE'].apply(eh_intercompany)

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


def aplicar_filtros_receber(df_contas, data_inicio, data_fim, filtro_filiais, filtro_status, filtro_categoria,
                            busca_cliente, filtro_tipo_doc='Todos', filtro_forma_pagto='Todas'):
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
        if filtro_status == 'Recebido':
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

    if busca_cliente:
        mask &= df_contas['NOME_CLIENTE'].str.contains(busca_cliente, case=False, na=False)

    # Filtro por tipo de documento (Com NF / Sem NF)
    if filtro_tipo_doc != 'Todos' and 'TIPO_DOC' in df_contas.columns:
        mask &= (df_contas['TIPO_DOC'] == filtro_tipo_doc)

    return df_contas[mask]


@st.cache_data
def get_opcoes_filtros_receber(_df_contas):
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


def get_dados_filtrados_receber(df, df_contas):
    """Retorna dataframes filtrados comuns"""
    df_pendentes = df[df['SALDO'] > 0]
    df_vencidos = df[df['STATUS'] == 'Vencido']
    return df_pendentes, df_vencidos


def calcular_metricas_receber(df, df_vencidos):
    """Calcula métricas principais do dashboard"""
    total = df['VALOR_ORIGINAL'].sum()
    recebido = total - df['SALDO'].sum()
    pendente = df['SALDO'].sum()
    vencido = df_vencidos['SALDO'].sum()
    pct_recebido = (recebido / total * 100) if total > 0 else 0
    dias_atraso = df_vencidos['DIAS_ATRASO'].mean() if len(df_vencidos) > 0 else 0

    return {
        'total': total,
        'recebido': recebido,
        'pendente': pendente,
        'vencido': vencido,
        'pct_recebido': pct_recebido,
        'dias_atraso': dias_atraso,
        'qtd_total': len(df),
        'qtd_vencidos': len(df_vencidos)
    }
