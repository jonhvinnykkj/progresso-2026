"""
Tema e estilos do dashboard
"""
import streamlit as st


def get_cores():
    """Retorna esquema de cores do tema escuro"""
    return {
        'primaria': '#00873D',
        'primaria_escura': '#005A28',
        'sucesso': '#22c55e',
        'alerta': '#f59e0b',
        'perigo': '#ef4444',
        'info': '#3b82f6',
        'fundo': '#0f172a',
        'card': '#1e293b',
        'borda': '#334155',
        'texto': '#f1f5f9',
        'texto_secundario': '#94a3b8'
    }


def get_sequencia_cores():
    """Sequência de cores para gráficos"""
    cores = get_cores()
    return [cores['primaria'], cores['alerta'], cores['info'],
            cores['perigo'], '#8b5cf6', '#ec4899']


SEQUENCIA_CORES = get_sequencia_cores()


def get_css():
    """CSS do dashboard"""
    cores = get_cores()

    return f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        body, p, span, div, h1, h2, h3, h4, h5, h6, label, input, button, select, textarea {{
            font-family: 'Inter', sans-serif;
        }}

        /* Background */
        .stApp {{
            background-color: {cores['fundo']} !important;
        }}

        .main .block-container {{
            padding: 1.5rem 2rem 2rem 2rem;
        }}

        /* Textos */
        .stMarkdown, .stMarkdown p, .stMarkdown span, h1, h2, h3, h4, h5, h6 {{
            color: {cores['texto']} !important;
        }}

        /* Esconder menu */
        #MainMenu, footer {{ visibility: hidden; }}

        /* Manter header visível para o botão da sidebar */
        header[data-testid="stHeader"] {{
            background: transparent !important;
        }}

        /* Sidebar */
        [data-testid="stSidebar"] {{
            background: {cores['card']} !important;
            border-right: 1px solid {cores['borda']};
            min-width: 0 !important;
        }}

        [data-testid="stSidebar"] > div:first-child {{
            padding: 1rem;
        }}

        [data-testid="stSidebar"][aria-expanded="false"] {{
            min-width: 0 !important;
        }}

        /* Botão de expandir sidebar */
        [data-testid="collapsedControl"] {{
            background: {cores['card']} !important;
            border: 1px solid {cores['borda']} !important;
            color: {cores['texto']} !important;
        }}

        [data-testid="stSidebar"] .stSelectbox > div > div,
        [data-testid="stSidebar"] .stTextInput > div > div {{
            background: {cores['fundo']} !important;
            border: 1px solid {cores['borda']} !important;
            border-radius: 8px !important;
        }}

        [data-testid="stSidebar"] .stDownloadButton > button {{
            background: {cores['primaria']} !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            font-size: 0.8rem !important;
        }}

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 4px;
            background: {cores['card']};
            border-radius: 12px;
            padding: 6px;
            border: 1px solid {cores['borda']};
        }}

        .stTabs [data-baseweb="tab"] {{
            border-radius: 8px;
            padding: 8px 16px;
            color: {cores['texto_secundario']};
            font-weight: 500;
            font-size: 0.85rem;
            background: transparent;
            border: none;
            white-space: nowrap;
        }}

        .stTabs [data-baseweb="tab"]:hover {{
            background: {cores['primaria']}15;
            color: {cores['primaria']};
        }}

        .stTabs [aria-selected="true"] {{
            background: {cores['primaria']} !important;
            color: white !important;
        }}

        .stTabs [data-baseweb="tab-highlight"],
        .stTabs [data-baseweb="tab-border"] {{
            display: none;
        }}

        /* Métricas */
        [data-testid="stMetric"] {{
            background: {cores['card']};
            padding: 1rem;
            border-radius: 10px;
            border: 1px solid {cores['borda']};
        }}

        [data-testid="stMetricLabel"] {{
            color: {cores['texto_secundario']} !important;
            font-size: 0.8rem !important;
        }}

        [data-testid="stMetricValue"] {{
            color: {cores['texto']} !important;
            font-weight: 600 !important;
            font-size: 1.3rem !important;
        }}

        /* Dataframes */
        [data-testid="stDataFrame"] {{
            background: {cores['card']} !important;
            border-radius: 10px;
            border: 1px solid {cores['borda']};
        }}

        /* Selectbox */
        .stSelectbox > div > div {{
            background: {cores['card']} !important;
            border-color: {cores['borda']} !important;
        }}

        .stSelectbox span {{
            color: {cores['texto']} !important;
        }}

        /* Divider */
        hr {{
            border-color: {cores['borda']} !important;
        }}

        /* Header */
        .header-gp {{
            background: linear-gradient(135deg, {cores['primaria']} 0%, {cores['primaria_escura']} 100%);
            padding: 1.25rem 1.5rem;
            border-radius: 12px;
            margin-bottom: 1.25rem;
        }}

        /* Cards alerta */
        .alerta-card {{
            background: {cores['card']};
            border-radius: 10px;
            padding: 1rem;
            border-left: 4px solid;
        }}

        .alerta-vermelho {{ border-color: {cores['perigo']}; }}
        .alerta-laranja {{ border-color: {cores['alerta']}; }}
        .alerta-azul {{ border-color: {cores['info']}; }}
        .alerta-verde {{ border-color: {cores['sucesso']}; }}

        .alerta-card .valor {{
            font-size: 1.2rem;
            font-weight: 600;
            color: {cores['texto']};
        }}

        .alerta-card .label {{
            font-size: 0.75rem;
            color: {cores['texto_secundario']};
        }}

        /* Multiselect */
        .stMultiSelect > div > div {{
            background: {cores['card']} !important;
            border-color: {cores['borda']} !important;
        }}

        .stMultiSelect span {{
            color: {cores['texto']} !important;
        }}

        /* Checkbox */
        .stCheckbox label span {{
            color: {cores['texto']} !important;
        }}

        /* Text input */
        .stTextInput > div > div {{
            background: {cores['card']} !important;
            border-color: {cores['borda']} !important;
        }}

        .stTextInput input {{
            color: {cores['texto']} !important;
        }}

        /* Download button */
        .stDownloadButton > button {{
            background: {cores['primaria']} !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
        }}

        /* Expander */
        .streamlit-expanderHeader {{
            background: {cores['card']} !important;
            color: {cores['texto']} !important;
            border: 1px solid {cores['borda']} !important;
            border-radius: 8px !important;
        }}

        /* Progress */
        .stProgress > div > div {{
            background-color: {cores['borda']} !important;
        }}

        .stProgress > div > div > div {{
            background-color: {cores['primaria']} !important;
        }}
    </style>
    """
