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
