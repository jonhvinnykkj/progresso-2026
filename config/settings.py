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
# INTERCOMPANY - Padrões de identificação
# =============================================================================
# Empresas do Grupo Progresso e pessoas relacionadas (CPFs)
# Usado para separar operações internas das contas a pagar externas
# IMPORTANTE: Esses padrões são usados com .str.contains() - parcial match
# NOTA: Os dados são convertidos para UPPERCASE antes da comparação
#
# NOMES EXATOS extraídos dos arquivos Excel:
# A Pagar: PROGRESSO AGRICOLA (I,M,P,T,-), PROGRESSO AGROINDUST, BRASIL AGRICOLA LTDA,
#          FAZENDA OURO BRANCO, FAZENDA PENINSULA, FAZENDA TROPICAL, SEMENTES OURO BRANCO,
#          OURO BRANCO INSUMOS, HOTEL TROPICAL PARAC, POUSADA TROPICAL,
#          CORNELIO ADRIANO SAN, GREGORY SANDERS - FA, GREICY HEINRICH SAND,
#          GREICY HEIRINCH SAND, GUEBERSON SANDERS -
# A Receber: Similar + PROGRESSO AGRICOLA L, PROGRESSO AGRICOLA ', GUEBERSON SANDERS (

INTERCOMPANY_PATTERNS = [
    # Empresas Progresso (todas as filiais)
    'PROGRESSO AGROINDUST',   # Progresso Agroindustrial
    'PROGRESSO AGRICOLA',     # Progresso Agricola (filiais: I, L, M, P, T, -, ')
    'BRASIL AGRICOLA LTDA',   # Brasil Agricola LTDA

    # Fazendas do Grupo (específicas)
    'FAZENDA TROPICAL',       # Fazenda Tropical
    'FAZENDA PENINSULA',      # Fazenda Peninsula
    'FAZENDA OURO BRANCO',    # Fazenda Ouro Branco

    # Ouro Branco (Sementes/Insumos)
    'SEMENTES OURO BRANCO',   # Sementes Ouro Branco
    'OURO BRANCO INSUMOS',    # Ouro Branco Insumos

    # Hotelaria do Grupo
    'HOTEL TROPICAL PARAC',   # Hotel Tropical Paracatu
    'POUSADA TROPICAL',       # Pousada Tropical

    # Família Sanders (CPFs do Grupo) - nomes exatos
    'CORNELIO ADRIANO SAN',   # Cornelio Adriano Sanders
    'GREGORY SANDERS - FA',   # Gregory Sanders - Fazenda
    'GREICY HEINRICH SAND',   # Greicy Heinrich Sanders
    'GREICY HEIRINCH SAND',   # Greicy Heirinch Sanders (variação)
    'GUEBERSON SANDERS',      # Gueberson Sanders (- e ()
]

# Mapeamento de tipo de intercompany para classificação
INTERCOMPANY_TIPOS = {
    # Empresas Progresso
    'PROGRESSO AGROINDUST': 'Progresso Agroindustrial',
    'PROGRESSO AGRICOLA': 'Progresso Agricola',
    'BRASIL AGRICOLA': 'Brasil Agricola',

    # Fazendas do Grupo
    'FAZENDA TROPICAL': 'Fazendas do Grupo',
    'FAZENDA PENINSULA': 'Fazendas do Grupo',
    'FAZENDA OURO BRANCO': 'Fazendas do Grupo',

    # Ouro Branco (Sementes/Insumos)
    'SEMENTES OURO BRANCO': 'Ouro Branco (Sementes/Insumos)',
    'OURO BRANCO INSUMOS': 'Ouro Branco (Sementes/Insumos)',

    # Hotelaria do Grupo
    'HOTEL TROPICAL': 'Hotelaria do Grupo',
    'POUSADA TROPICAL': 'Hotelaria do Grupo',

    # Família Sanders (PF/CPF)
    'CORNELIO': 'Familia Sanders (PF)',
    'GREGORY SANDERS': 'Familia Sanders (PF)',
    'GREICY': 'Familia Sanders (PF)',
    'GUEBERSON': 'Familia Sanders (PF)',
}
