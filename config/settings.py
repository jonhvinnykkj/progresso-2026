"""
Configurações gerais do dashboard
"""

PAGE_CONFIG = {
    "page_title": "Grupo Progresso | Contas a Pagar",
    "page_icon": "💰",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

# Arquivos de dados
DATA_FILES = {
    "contas": "Contas a Pagar.xlsx",
    "adiantamentos": "Adiantamentos a pagar.xlsx",
    "baixas": "Baixas de adiantamentos a pagar.xlsx"
}

# Configurações de cache
CACHE_TTL = 300  # 5 minutos

# Mapeamento de meses
MESES_NOMES = {
    1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
    5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
    9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
}

# Opções de período rápido
OPCOES_PERIODO_RAPIDO = [
    'Todos os dados', 'Hoje', 'Últimos 7 dias', 'Últimos 30 dias',
    'Últimos 90 dias', 'Este mês', 'Mês passado', 'Este ano'
]

# Opções de status
STATUS_OPCOES = [
    'Todos os Status', 'Vencido', 'Vence em 7 dias',
    'Vence em 15 dias', 'Vence em 30 dias', 'Pago'
]

# Ordem de aging
ORDEM_AGING = [
    'Vencido', 'Vence em 7 dias', 'Vence em 15 dias',
    'Vence em 30 dias', 'Vence em 60 dias', 'Vence em +60 dias'
]

# =============================================================================
# INTERCOMPANY - Padrões de identificação e padronização
# =============================================================================
# REGRA: Se o FORNECEDOR/CLIENTE corresponde a uma FILIAL do grupo = INTERCOMPANY
# Exemplo: PROGRESSO MATRIZ paga para FAZENDA PENINSULA = Intercompany

# Lista de FILIAIS do grupo (27 filiais)
FILIAIS_GRUPO = [
    'AG3 AGRO',
    'BRASIL AGRICOLA LTDA',
    'CG3 AGRO',
    'FAZENDA OURO BRANCO',
    'IMPERIAL',
    'PENINSULA',
    'PROGRESSO AGROINDUSTRIAL - BA',
    'PROGRESSO AGROINDUSTRIAL - DF',
    'PROGRESSO AGROINDUSTRIAL - GO',
    'PROGRESSO AGROINDUSTRIAL - GO(ST HELENA)',
    'PROGRESSO AGROINDUSTRIAL - MA',
    'PROGRESSO AGROINDUSTRIAL - MA(BALSAS)',
    'PROGRESSO AGROINDUSTRIAL - MG',
    'PROGRESSO AGROINDUSTRIAL - MT',
    'PROGRESSO AGROINDUSTRIAL - MT (PL)',
    'PROGRESSO AGROINDUSTRIAL - MT(LV)',
    'PROGRESSO AGROINDUSTRIAL - PA',
    'PROGRESSO AGROINDUSTRIAL - PA(TAILANDIA)',
    'PROGRESSO AGROINDUSTRIAL - PI',
    'PROGRESSO AGROINDUSTRIAL - RO',
    'PROGRESSO AGROINDUSTRIAL - TO',
    'PROGRESSO FBO',
    'PROGRESSO MATRIZ',
    'RAINHA DA SERRA',
    'SDS PARTICIPACOES',
    'TROPICAL',
    'TROPICAL AGROPARTICIPACOES',
]

# Padrões para IDENTIFICAR intercompany no FORNECEDOR/CLIENTE
# Se o nome do fornecedor/cliente contém algum desses padrões = é uma filial = intercompany
# IMPORTANTE: Esses padroes excluem registros de Contas a Pagar e Contas a Receber
INTERCOMPANY_PATTERNS = [
    # Filiais principais (match parcial - ordem importa, mais especifico primeiro)
    'AG3 AGRO',
    'BRASIL AGRICOLA',
    'CG3 AGRO',
    'FAZENDA OURO BRANCO',
    'OURO BRANCO INSUMOS',
    'SEMENTES OURO BRANCO',
    'OURO BRANCO',            # Match generico para qualquer Ouro Branco
    'IMPERIAL',
    'FAZENDA PENINSULA',
    'PENINSULA',
    'PROGRESSO AGROINDUSTRIAL',  # Pega todas as variações de Progresso Agroindustrial
    'PROGRESSO AGRICOLA',        # Pega Progresso Agricola (variacao)
    'PROGRESSO AGRO',
    'PROGRESSO FBO',
    'PROGRESSO MATRIZ',
    'RAINHA DA SERRA',
    'SDS PARTICIPACOES',
    'TROPICAL AGROPART',
    'FAZENDA TROPICAL',
    'HOTEL TROPICAL',
    'POUSADA TROPICAL',
    'TROPICAL',               # Match generico para qualquer Tropical
    # Pessoas do Grupo (socios/familia) - tambem sao intercompany
    'CORNELIO',
    'GREICY',
    'GREGORY SANDERS',
    'GUEBERSON SANDERS',
]

# Mapeamento para PADRONIZAR nomes de FORNECEDOR/CLIENTE -> FILIAL correspondente
INTERCOMPANY_PADRONIZACAO = {
    # Progresso Agroindustrial (filiais por estado)
    'PROGRESSO AGROINDUST': 'PROGRESSO AGROINDUSTRIAL',
    'PROGRESSO MATRIZ': 'PROGRESSO AGROINDUSTRIAL',

    # Progresso Agricola (filial separada)
    'PROGRESSO AGRICOLA': 'PROGRESSO AGRICOLA',

    # Ouro Branco / FBO (todas as variações)
    'PROGRESSO FBO': 'OURO BRANCO',           # FBO = Fazenda Ouro Branco
    'FAZENDA OURO BRANCO': 'OURO BRANCO',
    'OURO BRANCO INSUMOS': 'OURO BRANCO',
    'SEMENTES OURO BRANCO': 'OURO BRANCO',

    # Peninsula
    'FAZENDA PENINSULA': 'PENINSULA',
    'PENINSULA': 'PENINSULA',

    # Tropical (todas as variações)
    'FAZENDA TROPICAL': 'TROPICAL',
    'HOTEL TROPICAL': 'TROPICAL',
    'POUSADA TROPICAL': 'TROPICAL',
    'TROPICAL AGROPART': 'TROPICAL',

    # Outras filiais
    'BRASIL AGRICOLA': 'BRASIL AGRICOLA',
    'AG3 AGRO': 'AG3 AGRO',
    'CG3 AGRO': 'CG3 AGRO',
    'RAINHA DA SERRA': 'RAINHA DA SERRA',
    'SDS PARTICIPACOES': 'SDS PARTICIPACOES',
    'IMPERIAL': 'IMPERIAL',

    # Familia Sanders (socios/pessoas fisicas do grupo)
    'CORNELIO': 'FAMILIA SANDERS',
    'GREICY': 'FAMILIA SANDERS',
    'GREGORY SANDERS': 'FAMILIA SANDERS',
    'GUEBERSON SANDERS': 'FAMILIA SANDERS',
}

# Classificação por TIPO de intercompany (para graficos e agrupamentos)
INTERCOMPANY_TIPOS = {
    'PROGRESSO AGROINDUSTRIAL': 'Progresso Agroindustrial',
    'PROGRESSO AGRICOLA': 'Progresso Agricola',
    'OURO BRANCO': 'Ouro Branco',
    'PENINSULA': 'Peninsula',
    'TROPICAL': 'Tropical',
    'BRASIL AGRICOLA': 'Brasil Agricola',
    'AG3 AGRO': 'AG3 Agro',
    'CG3 AGRO': 'CG3 Agro',
    'RAINHA DA SERRA': 'Rainha da Serra',
    'SDS PARTICIPACOES': 'SDS Participacoes',
    'IMPERIAL': 'Imperial',
    'FAMILIA SANDERS': 'Familia Sanders',
}
