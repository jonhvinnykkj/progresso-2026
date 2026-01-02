import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
from io import BytesIO
import warnings
warnings.filterwarnings('ignore')

# ═══════════════════════════════════════════════════════════════════════════════
# FUNÇÕES DE EXPORTAÇÃO (Com Cache)
# ═══════════════════════════════════════════════════════════════════════════════
@st.cache_data
def to_excel(_df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        _df.to_excel(writer, index=False, sheet_name='Dados')
    return output.getvalue()

@st.cache_data
def to_csv(_df):
    return _df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Grupo Progresso | Contas a Pagar",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ═══════════════════════════════════════════════════════════════════════════════
# MODO CLARO/ESCURO
# ═══════════════════════════════════════════════════════════════════════════════
if 'tema_escuro' not in st.session_state:
    st.session_state.tema_escuro = True

def get_cores():
    if st.session_state.tema_escuro:
        return {
            'primaria': '#00873D',
            'primaria_escura': '#005A28',
            'sucesso': '#10b981',
            'alerta': '#f59e0b',
            'perigo': '#ef4444',
            'info': '#3b82f6',
            'fundo': '#0a0f1a',
            'card': '#131c2e',
            'borda': '#1e293b',
            'texto': '#e2e8f0',
            'texto_secundario': '#94a3b8'
        }
    else:
        return {
            'primaria': '#00873D',
            'primaria_escura': '#005A28',
            'sucesso': '#059669',
            'alerta': '#d97706',
            'perigo': '#dc2626',
            'info': '#2563eb',
            'fundo': '#f8fafc',
            'card': '#ffffff',
            'borda': '#e2e8f0',
            'texto': '#1e293b',
            'texto_secundario': '#64748b'
        }

CORES = get_cores()
SEQUENCIA_CORES = [CORES['primaria'], CORES['alerta'], CORES['info'],
                   CORES['perigo'], '#8b5cf6', '#ec4899']

# ═══════════════════════════════════════════════════════════════════════════════
# CSS REFINADO - Mínimo e funcional
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');

    * {{ font-family: 'DM Sans', sans-serif !important; }}

    /* Tema base */
    .stApp {{
        background-color: {CORES['fundo']} !important;
    }}

    .main .block-container {{
        padding-top: 2rem;
        padding-bottom: 2rem;
    }}

    /* Textos gerais */
    .stMarkdown, .stMarkdown p, .stMarkdown span {{
        color: {CORES['texto']} !important;
    }}

    h1, h2, h3, h4, h5, h6 {{
        color: {CORES['texto']} !important;
    }}

    /* Header personalizado */
    .header-gp {{
        background: linear-gradient(135deg, {CORES['primaria_escura']} 0%, {CORES['primaria']} 100%);
        padding: 1.5rem 2rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        gap: 1.5rem;
    }}

    .header-gp .logo {{
        width: 56px;
        height: 56px;
        background: rgba(255,255,255,0.15);
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.5rem;
        font-weight: 700;
        color: white;
    }}

    .header-gp .titulo {{
        color: white;
        font-size: 1.75rem;
        font-weight: 700;
        margin: 0;
    }}

    .header-gp .subtitulo {{
        color: rgba(255,255,255,0.8);
        font-size: 0.9rem;
        margin: 0;
    }}

    /* Cards de alerta melhorados */
    .alerta-card {{
        background: {CORES['card']};
        border-radius: 12px;
        padding: 1rem 1.25rem;
        border-left: 4px solid;
        margin-bottom: 0.5rem;
    }}

    .alerta-vermelho {{ border-color: {CORES['perigo']}; }}
    .alerta-laranja {{ border-color: {CORES['alerta']}; }}
    .alerta-azul {{ border-color: {CORES['info']}; }}
    .alerta-verde {{ border-color: {CORES['sucesso']}; }}

    .alerta-card .valor {{
        font-size: 1.25rem;
        font-weight: 700;
        color: {CORES['texto']};
    }}

    .alerta-card .label {{
        font-size: 0.8rem;
        color: {CORES['texto_secundario']};
        margin-top: 0.25rem;
    }}

    /* Tabs modernas */
    .stTabs {{
        background: transparent;
    }}

    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        background: {CORES['card']};
        border-radius: 16px;
        padding: 8px;
        border: 1px solid {CORES['borda']};
        overflow-x: auto;
        flex-wrap: nowrap;
    }}

    .stTabs [data-baseweb="tab"] {{
        border-radius: 10px;
        padding: 10px 20px;
        color: {CORES['texto_secundario']};
        font-weight: 500;
        font-size: 0.9rem;
        background: transparent;
        border: none;
        white-space: nowrap;
        transition: all 0.2s ease;
    }}

    .stTabs [data-baseweb="tab"]:hover {{
        background: rgba(0, 135, 61, 0.1);
        color: {CORES['primaria']};
    }}

    .stTabs [aria-selected="true"] {{
        background: linear-gradient(135deg, {CORES['primaria']} 0%, {CORES['primaria_escura']} 100%) !important;
        color: white !important;
        box-shadow: 0 4px 12px rgba(0, 135, 61, 0.3);
    }}

    .stTabs [data-baseweb="tab-highlight"] {{
        display: none;
    }}

    .stTabs [data-baseweb="tab-border"] {{
        display: none;
    }}

    /* Métricas */
    [data-testid="stMetric"] {{
        background: {CORES['card']};
        padding: 1rem 1.25rem;
        border-radius: 12px;
        border: 1px solid {CORES['borda']};
    }}

    [data-testid="stMetricLabel"] {{
        color: {CORES['texto_secundario']} !important;
        font-size: 0.85rem !important;
    }}

    [data-testid="stMetricValue"] {{
        color: {CORES['texto']} !important;
        font-weight: 600 !important;
    }}

    /* Dataframes */
    [data-testid="stDataFrame"] {{
        background: {CORES['card']} !important;
        border-radius: 12px;
        border: 1px solid {CORES['borda']};
    }}

    [data-testid="stDataFrame"] * {{
        color: {CORES['texto']} !important;
    }}

    /* Selectbox */
    .stSelectbox > div > div {{
        background: {CORES['card']} !important;
        border-color: {CORES['borda']} !important;
        color: {CORES['texto']} !important;
    }}

    .stSelectbox [data-baseweb="select"] > div {{
        background: {CORES['card']} !important;
        border-color: {CORES['borda']} !important;
    }}

    .stSelectbox [data-baseweb="select"] span {{
        color: {CORES['texto']} !important;
    }}

    /* Expander */
    .streamlit-expanderHeader {{
        background: {CORES['card']} !important;
        color: {CORES['texto']} !important;
    }}

    /* Alertas */
    .stAlert {{
        background: {CORES['card']} !important;
        border: 1px solid {CORES['borda']} !important;
    }}

    /* Esconder elementos do Streamlit */
    #MainMenu, footer, header {{ visibility: hidden; }}

    /* Sidebar moderna */
    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, {CORES['card']} 0%, {CORES['fundo']} 100%);
        border-right: 1px solid {CORES['borda']};
    }}

    [data-testid="stSidebar"] > div:first-child {{
        padding-top: 1rem;
    }}

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h4 {{
        color: {CORES['texto']} !important;
        font-weight: 600;
    }}

    /* Inputs da sidebar */
    [data-testid="stSidebar"] .stSelectbox > div > div {{
        background: {CORES['fundo']};
        border: 1px solid {CORES['borda']};
        border-radius: 10px;
    }}

    [data-testid="stSidebar"] .stSelectbox > div > div:hover {{
        border-color: {CORES['primaria']};
    }}

    [data-testid="stSidebar"] .stTextInput > div > div > input {{
        background: {CORES['fundo']};
        border: 1px solid {CORES['borda']};
        border-radius: 10px;
        color: {CORES['texto']};
    }}

    [data-testid="stSidebar"] .stTextInput > div > div > input:focus {{
        border-color: {CORES['primaria']};
        box-shadow: 0 0 0 2px rgba(0, 135, 61, 0.2);
    }}

    [data-testid="stSidebar"] .stDateInput > div > div > input {{
        background: {CORES['fundo']};
        border: 1px solid {CORES['borda']};
        border-radius: 10px;
        color: {CORES['texto']};
    }}

    /* Botão toggle tema */
    [data-testid="stSidebar"] button[kind="secondary"] {{
        background: {CORES['fundo']} !important;
        border: 1px solid {CORES['borda']} !important;
        border-radius: 50% !important;
        width: 40px !important;
        height: 40px !important;
        padding: 0 !important;
        font-size: 1.2rem !important;
        transition: all 0.3s ease !important;
    }}

    [data-testid="stSidebar"] button[kind="secondary"]:hover {{
        background: {CORES['primaria']} !important;
        transform: rotate(180deg) !important;
    }}

    /* Botões de download */
    [data-testid="stSidebar"] .stDownloadButton > button {{
        background: linear-gradient(135deg, {CORES['primaria']} 0%, {CORES['primaria_escura']} 100%);
        color: white;
        border: none;
        border-radius: 10px;
        font-weight: 500;
        transition: all 0.2s ease;
    }}

    [data-testid="stSidebar"] .stDownloadButton > button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 135, 61, 0.3);
    }}

    /* Divider na sidebar */
    [data-testid="stSidebar"] hr {{
        border-color: {CORES['borda']};
        margin: 1.5rem 0;
    }}

    /* Labels na sidebar */
    [data-testid="stSidebar"] .stMarkdown p strong {{
        color: {CORES['texto']};
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}

    /* Sidebar limpa */
    [data-testid="stSidebar"] {{
        background: {CORES['card']} !important;
    }}

    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stDateInput label,
    [data-testid="stSidebar"] .stTextInput label {{
        color: {CORES['texto']} !important;
        font-weight: 500 !important;
    }}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO PLOTLY
# ═══════════════════════════════════════════════════════════════════════════════
def criar_layout(altura=400, **kwargs):
    layout = {
        'paper_bgcolor': 'rgba(0,0,0,0)',
        'plot_bgcolor': 'rgba(0,0,0,0)',
        'font': {'family': 'DM Sans', 'color': CORES['texto_secundario'], 'size': 12},
        'margin': {'t': 40, 'b': 50, 'l': 50, 'r': 30},
        'height': altura,
        'legend': {'orientation': 'h', 'yanchor': 'bottom', 'y': 1.02, 'xanchor': 'right', 'x': 1},
        'xaxis': {'gridcolor': CORES['borda'], 'zerolinecolor': CORES['borda']},
        'yaxis': {'gridcolor': CORES['borda'], 'zerolinecolor': CORES['borda']}
    }
    layout.update(kwargs)
    return layout

# ═══════════════════════════════════════════════════════════════════════════════
# FUNÇÕES AUXILIARES
# ═══════════════════════════════════════════════════════════════════════════════
def formatar_moeda(valor, completo=False):
    if pd.isna(valor) or valor == 0:
        return "R$ 0"
    if completo:
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if abs(valor) >= 1_000_000:
        return f"R$ {valor/1_000_000:.1f}M"
    if abs(valor) >= 1_000:
        return f"R$ {valor/1_000:.0f}K"
    return f"R$ {valor:,.0f}".replace(",", ".")

def formatar_numero(valor):
    return f"{valor:,.0f}".replace(",", ".")

def calcular_variacao(atual, anterior):
    if anterior == 0:
        return 0
    return ((atual - anterior) / anterior) * 100

def formatar_delta(valor, inverso=False):
    """Formata delta com seta. inverso=True quando menor é melhor"""
    if valor == 0:
        return "0%"
    sinal = "+" if valor > 0 else ""
    return f"{sinal}{valor:.1f}%"

# ═══════════════════════════════════════════════════════════════════════════════
# CARREGAR DADOS
# ═══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=300)
def carregar_dados():
    df_contas = pd.read_excel('Contas a Pagar.xlsx')
    df_adiant = pd.read_excel('Adiantamentos a pagar.xlsx')
    df_baixas = pd.read_excel('Baixas de adiantamentos a pagar.xlsx')

    for col in ['EMISSAO', 'VENCIMENTO', 'VENCTO_REAL', 'DT_BAIXA']:
        for df in [df_contas, df_adiant, df_baixas]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')

    hoje = datetime.now()
    df_contas['ANO'] = df_contas['EMISSAO'].dt.year
    df_contas['MES'] = df_contas['EMISSAO'].dt.month
    df_contas['TRIMESTRE'] = df_contas['EMISSAO'].dt.quarter

    # Classificar vencimento usando vetorização (muito mais rápido que apply)
    df_contas['DIAS_VENC'] = (df_contas['VENCIMENTO'] - hoje).dt.days

    # Inicializar com 'Vence em +60 dias' e sobrescrever
    df_contas['STATUS'] = 'Vence em +60 dias'
    df_contas.loc[df_contas['SALDO'] <= 0, 'STATUS'] = 'Pago'
    df_contas.loc[df_contas['VENCIMENTO'].isna() & (df_contas['SALDO'] > 0), 'STATUS'] = 'Sem data'
    df_contas.loc[(df_contas['DIAS_VENC'] < 0) & (df_contas['SALDO'] > 0), 'STATUS'] = 'Vencido'
    df_contas.loc[(df_contas['DIAS_VENC'] >= 0) & (df_contas['DIAS_VENC'] <= 7) & (df_contas['SALDO'] > 0), 'STATUS'] = 'Vence em 7 dias'
    df_contas.loc[(df_contas['DIAS_VENC'] > 7) & (df_contas['DIAS_VENC'] <= 15) & (df_contas['SALDO'] > 0), 'STATUS'] = 'Vence em 15 dias'
    df_contas.loc[(df_contas['DIAS_VENC'] > 15) & (df_contas['DIAS_VENC'] <= 30) & (df_contas['SALDO'] > 0), 'STATUS'] = 'Vence em 30 dias'
    df_contas.loc[(df_contas['DIAS_VENC'] > 30) & (df_contas['DIAS_VENC'] <= 60) & (df_contas['SALDO'] > 0), 'STATUS'] = 'Vence em 60 dias'

    # Dias de atraso vetorizado
    df_contas['DIAS_ATRASO'] = 0
    mask_vencido = (df_contas['STATUS'] == 'Vencido') & df_contas['DIAS_VENC'].notna()
    df_contas.loc[mask_vencido, 'DIAS_ATRASO'] = df_contas.loc[mask_vencido, 'DIAS_VENC'].abs()

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

df_contas, df_adiant, df_baixas = carregar_dados()
filiais_opcoes, categorias_opcoes = get_opcoes_filtros(df_contas)
hoje = datetime.now()

# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR - FILTROS (Design Moderno)
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    # Header com logo e toggle de tema
    col_logo, col_tema = st.columns([4, 1])
    with col_tema:
        tema_icon = "🌙" if st.session_state.tema_escuro else "☀️"
        if st.button(tema_icon, key="toggle_tema", help="Alternar modo claro/escuro"):
            st.session_state.tema_escuro = not st.session_state.tema_escuro
            st.rerun()

    st.markdown(f"""
    <div style="text-align: center; padding: 1.5rem 0; border-bottom: 2px solid {CORES['primaria']}; margin-bottom: 1.5rem;">
        <div style="background: linear-gradient(135deg, {CORES['primaria']} 0%, {CORES['primaria_escura']} 100%);
                    width: 70px; height: 70px; border-radius: 20px; margin: 0 auto 1rem;
                    display: flex; align-items: center; justify-content: center;
                    font-size: 1.8rem; font-weight: 700; color: white;
                    box-shadow: 0 8px 20px rgba(0, 135, 61, 0.3);">GP</div>
        <h2 style="margin: 0; color: {CORES['texto']}; font-size: 1.3rem; font-weight: 600;">Grupo Progresso</h2>
        <p style="margin: 0.3rem 0 0; color: {CORES['texto_secundario']}; font-size: 0.85rem;">Dashboard Financeiro</p>
    </div>
    """, unsafe_allow_html=True)

    # Período
    data_min = df_contas['EMISSAO'].min().date()
    data_max = df_contas['EMISSAO'].max().date()
    ano_min = data_min.year
    ano_max = data_max.year
    anos_disponiveis = list(range(ano_min, ano_max + 1))

    meses_nomes = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
        5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
        9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }

    st.markdown(f"""<p style="color: {CORES['primaria']}; font-weight: 600; font-size: 0.9rem;
                margin-bottom: 0.8rem; text-transform: uppercase; letter-spacing: 1px;">📅 Período</p>""",
                unsafe_allow_html=True)

    # Tipo de filtro de período
    tipo_periodo = st.selectbox(
        "Tipo de período",
        ['Rápido', 'Por Ano', 'Por Semestre', 'Por Mês', 'Intervalo de Datas'],
        label_visibility="collapsed"
    )

    # Lógica para cada tipo de período
    if tipo_periodo == 'Rápido':
        opcoes_rapidas = ['Todos os dados', 'Hoje', 'Últimos 7 dias', 'Últimos 30 dias', 'Últimos 90 dias', 'Este mês', 'Mês passado', 'Este ano']
        opcao_rapida = st.selectbox("Opção", opcoes_rapidas, label_visibility="collapsed")

        if opcao_rapida == 'Todos os dados':
            data_inicio, data_fim = data_min, data_max
        elif opcao_rapida == 'Hoje':
            data_inicio = data_fim = hoje.date()
        elif opcao_rapida == 'Últimos 7 dias':
            data_inicio, data_fim = hoje.date() - timedelta(days=7), hoje.date()
        elif opcao_rapida == 'Últimos 30 dias':
            data_inicio, data_fim = hoje.date() - timedelta(days=30), hoje.date()
        elif opcao_rapida == 'Últimos 90 dias':
            data_inicio, data_fim = hoje.date() - timedelta(days=90), hoje.date()
        elif opcao_rapida == 'Este mês':
            data_inicio, data_fim = hoje.date().replace(day=1), hoje.date()
        elif opcao_rapida == 'Mês passado':
            primeiro_dia_mes = hoje.date().replace(day=1)
            data_fim = primeiro_dia_mes - timedelta(days=1)
            data_inicio = data_fim.replace(day=1)
        elif opcao_rapida == 'Este ano':
            data_inicio = hoje.date().replace(month=1, day=1)
            data_fim = hoje.date()

    elif tipo_periodo == 'Por Ano':
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"<p style='color:{CORES['texto_secundario']};font-size:0.7rem;margin:0;'>De:</p>", unsafe_allow_html=True)
            ano_inicio = st.selectbox("Ano início", anos_disponiveis, index=0, label_visibility="collapsed", key="ano_ini")
        with col2:
            st.markdown(f"<p style='color:{CORES['texto_secundario']};font-size:0.7rem;margin:0;'>Até:</p>", unsafe_allow_html=True)
            ano_fim = st.selectbox("Ano fim", anos_disponiveis, index=len(anos_disponiveis)-1, label_visibility="collapsed", key="ano_fim")

        from datetime import date
        data_inicio = date(ano_inicio, 1, 1)
        data_fim = date(ano_fim, 12, 31)

    elif tipo_periodo == 'Por Semestre':
        col1, col2 = st.columns(2)
        with col1:
            ano_sem = st.selectbox("Ano", anos_disponiveis, index=len(anos_disponiveis)-1, label_visibility="collapsed", key="ano_sem")
        with col2:
            semestre = st.selectbox("Semestre", ['1º Semestre', '2º Semestre'], label_visibility="collapsed")

        from datetime import date
        if semestre == '1º Semestre':
            data_inicio = date(ano_sem, 1, 1)
            data_fim = date(ano_sem, 6, 30)
        else:
            data_inicio = date(ano_sem, 7, 1)
            data_fim = date(ano_sem, 12, 31)

    elif tipo_periodo == 'Por Mês':
        col1, col2 = st.columns(2)
        with col1:
            ano_mes = st.selectbox("Ano", anos_disponiveis, index=len(anos_disponiveis)-1, label_visibility="collapsed", key="ano_mes")
        with col2:
            mes_opcoes = [f"{v}" for k, v in meses_nomes.items()]
            mes_sel = st.selectbox("Mês", mes_opcoes, index=hoje.month-1, label_visibility="collapsed")
            mes_num = [k for k, v in meses_nomes.items() if v == mes_sel][0]

        from datetime import date
        import calendar
        data_inicio = date(ano_mes, mes_num, 1)
        ultimo_dia = calendar.monthrange(ano_mes, mes_num)[1]
        data_fim = date(ano_mes, mes_num, ultimo_dia)

    elif tipo_periodo == 'Intervalo de Datas':
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"<p style='color:{CORES['texto_secundario']};font-size:0.7rem;margin:0;'>De:</p>", unsafe_allow_html=True)
            data_inicio = st.date_input("De", value=data_min, min_value=data_min, max_value=data_max, label_visibility="collapsed")
        with col2:
            st.markdown(f"<p style='color:{CORES['texto_secundario']};font-size:0.7rem;margin:0;'>Até:</p>", unsafe_allow_html=True)
            data_fim = st.date_input("Até", value=data_max, min_value=data_min, max_value=data_max, label_visibility="collapsed")

    # Ajustar para limites dos dados disponíveis
    data_inicio = max(data_inicio, data_min)
    data_fim = min(data_fim, data_max)

    # Mostrar período selecionado
    dias_periodo = (data_fim - data_inicio).days + 1
    st.markdown(f"""
    <div style="background: {CORES['fundo']}; border-radius: 8px; padding: 0.6rem; margin-top: 0.5rem;
                border-left: 3px solid {CORES['primaria']};">
        <p style="color: {CORES['texto_secundario']}; font-size: 0.7rem; margin: 0; text-transform: uppercase;">Período ativo</p>
        <p style="color: {CORES['texto']}; font-size: 0.85rem; margin: 0.2rem 0 0; font-weight: 500;">
            {data_inicio.strftime('%d/%m/%Y')} → {data_fim.strftime('%d/%m/%Y')}</p>
        <p style="color: {CORES['texto_secundario']}; font-size: 0.7rem; margin: 0.2rem 0 0;">
            {dias_periodo} dias</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height: 1rem'></div>", unsafe_allow_html=True)

    # Filtros principais
    st.markdown(f"""<p style="color: {CORES['primaria']}; font-weight: 600; font-size: 0.9rem;
                margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 1px;">🎯 Filtros</p>""",
                unsafe_allow_html=True)

    filtro_filial = st.selectbox("Filial", filiais_opcoes, label_visibility="collapsed")

    status_opcoes = ['Todos os Status', 'Vencido', 'Vence em 7 dias', 'Vence em 15 dias', 'Vence em 30 dias', 'Pago']
    filtro_status = st.selectbox("Status", status_opcoes, label_visibility="collapsed")

    filtro_categoria = st.selectbox("Categoria", categorias_opcoes, label_visibility="collapsed")

    # Filtro Tipo de Documento (Com NF / Sem NF)
    filtro_tipo_doc = st.selectbox("Tipo Documento", ['Todos', 'Com NF', 'Sem NF'], label_visibility="collapsed")

    # Filtro Forma de Pagamento
    formas_pagto_opcoes = ['Todas']
    if 'DESCRICAO_FORMA_PAGAMENTO' in df_contas.columns:
        formas_unicas = df_contas['DESCRICAO_FORMA_PAGAMENTO'].dropna().unique().tolist()
        formas_pagto_opcoes += sorted([f for f in formas_unicas if f and str(f).strip()])
    filtro_forma_pagto = st.selectbox("Forma Pagamento", formas_pagto_opcoes, label_visibility="collapsed")

    st.markdown("<div style='height: 1rem'></div>", unsafe_allow_html=True)

    # Busca
    st.markdown(f"""<p style="color: {CORES['primaria']}; font-weight: 600; font-size: 0.9rem;
                margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 1px;">🔍 Busca</p>""",
                unsafe_allow_html=True)
    busca_fornecedor = st.text_input("Fornecedor", placeholder="Nome do fornecedor...", label_visibility="collapsed")

    st.markdown("<div style='height: 1.5rem'></div>", unsafe_allow_html=True)

    # Exportação
    st.markdown(f"""<p style="color: {CORES['primaria']}; font-weight: 600; font-size: 0.9rem;
                margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 1px;">📥 Exportar</p>""",
                unsafe_allow_html=True)
    col_exp1, col_exp2 = st.columns(2)
    with col_exp1:
        st.download_button(
            label="📊 Excel",
            data=to_excel(df_contas),
            file_name=f"contas_pagar_{hoje.strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    with col_exp2:
        st.download_button(
            label="📄 CSV",
            data=to_csv(df_contas),
            file_name=f"contas_pagar_{hoje.strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )

    # Resumo rápido
    st.markdown("<div style='height: 1.5rem'></div>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, {CORES['fundo']} 0%, {CORES['card']} 100%);
                border: 1px solid {CORES['borda']}; border-radius: 12px; padding: 1rem; margin-top: 0.5rem;">
        <p style="color: {CORES['texto_secundario']}; font-size: 0.75rem; margin: 0 0 0.5rem; text-transform: uppercase;">
            Dados disponíveis</p>
        <p style="color: {CORES['texto']}; font-size: 0.85rem; margin: 0;">
            📆 {data_min.strftime('%d/%m/%Y')} até {data_max.strftime('%d/%m/%Y')}</p>
        <p style="color: {CORES['texto_secundario']}; font-size: 0.7rem; margin: 0.5rem 0 0;">
            Atualizado: {hoje.strftime('%d/%m/%Y %H:%M')}</p>
    </div>
    """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# APLICAR FILTROS (Com Cache para Performance)
# ═══════════════════════════════════════════════════════════════════════════════
df = aplicar_filtros(df_contas, data_inicio, data_fim, filtro_filial, filtro_status, filtro_categoria,
                     busca_fornecedor, filtro_tipo_doc, filtro_forma_pagto)
df_pendentes = df[df['SALDO'] > 0]
df_vencidos = df[df['STATUS'] == 'Vencido']

# ═══════════════════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="header-gp">
    <div class="logo">GP</div>
    <div>
        <p class="titulo">Contas a Pagar</p>
        <p class="subtitulo">{formatar_numero(len(df))} títulos selecionados | {data_inicio.strftime('%d/%m/%Y')} - {data_fim.strftime('%d/%m/%Y')}</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# KPIs COM VARIAÇÃO TEMPORAL
# ═══════════════════════════════════════════════════════════════════════════════
total = df['VALOR_ORIGINAL'].sum()
pago = total - df['SALDO'].sum()
pendente = df['SALDO'].sum()
vencido = df_vencidos['SALDO'].sum()
pct_pago = (pago / total * 100) if total > 0 else 0
dias_atraso = df_vencidos['DIAS_ATRASO'].mean() if len(df_vencidos) > 0 else 0

# Calcular variação vs mês anterior
mes_atual = hoje.month
ano_atual = hoje.year
mes_anterior = mes_atual - 1 if mes_atual > 1 else 12
ano_mes_anterior = ano_atual if mes_atual > 1 else ano_atual - 1

df_mes_atual = df_contas[(df_contas['EMISSAO'].dt.month == mes_atual) & (df_contas['EMISSAO'].dt.year == ano_atual)]
df_mes_anterior = df_contas[(df_contas['EMISSAO'].dt.month == mes_anterior) & (df_contas['EMISSAO'].dt.year == ano_mes_anterior)]

total_mes_atual = df_mes_atual['VALOR_ORIGINAL'].sum()
total_mes_anterior = df_mes_anterior['VALOR_ORIGINAL'].sum()
var_total = calcular_variacao(total_mes_atual, total_mes_anterior)

pendente_mes_atual = df_mes_atual['SALDO'].sum()
pendente_mes_anterior = df_mes_anterior['SALDO'].sum()
var_pendente = calcular_variacao(pendente_mes_atual, pendente_mes_anterior)

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total", formatar_moeda(total), f"{formatar_numero(len(df))} títulos")
col2.metric("Pago", formatar_moeda(pago), f"{pct_pago:.1f}%")
col3.metric("Pendente", formatar_moeda(pendente), formatar_delta(var_pendente), delta_color="inverse")
col4.metric("Vencido", formatar_moeda(vencido), f"{formatar_numero(len(df_vencidos))} títulos", delta_color="inverse")
col5.metric("Atraso Médio", f"{dias_atraso:.0f} dias")

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# NOTIFICAÇÕES DE ALERTAS CRÍTICOS
# ═══════════════════════════════════════════════════════════════════════════════
qtd_vencidos = len(df_vencidos)
valor_vence_7d = df_pendentes[df_pendentes['STATUS'] == 'Vence em 7 dias']['SALDO'].sum()

# Calcular alerta de 48h
titulos_48h = df[df['ALERTA_48H'] == True] if 'ALERTA_48H' in df.columns else pd.DataFrame()
qtd_48h = len(titulos_48h)
valor_48h = titulos_48h['SALDO'].sum() if qtd_48h > 0 else 0

if qtd_vencidos > 0 or valor_vence_7d > 100000 or qtd_48h > 0:
    with st.container():
        cols = st.columns([0.02, 0.98])
        with cols[1]:
            if qtd_vencidos > 0:
                st.warning(f"Atenção: {qtd_vencidos} títulos vencidos totalizando {formatar_moeda(vencido, completo=True)}")
            if qtd_48h > 0:
                st.error(f"Entrada < 48h do vencimento: {qtd_48h} títulos ({formatar_moeda(valor_48h, completo=True)})")
            if valor_vence_7d > 100000:
                st.info(f"Próximos 7 dias: {formatar_moeda(valor_vence_7d, completo=True)} a vencer")

# ═══════════════════════════════════════════════════════════════════════════════
# ALERTAS
# ═══════════════════════════════════════════════════════════════════════════════
col1, col2, col3, col4 = st.columns(4)

alertas = [
    ('Vencido', 'vermelho', df_pendentes[df_pendentes['STATUS'] == 'Vencido']),
    ('Vence em 7 dias', 'laranja', df_pendentes[df_pendentes['STATUS'] == 'Vence em 7 dias']),
    ('Vence em 15 dias', 'azul', df_pendentes[df_pendentes['STATUS'] == 'Vence em 15 dias']),
    ('Vence em 30 dias', 'verde', df_pendentes[df_pendentes['STATUS'] == 'Vence em 30 dias'])
]

for col, (label, cor, dados) in zip([col1, col2, col3, col4], alertas):
    valor = dados['SALDO'].sum()
    qtd = len(dados)
    with col:
        st.markdown(f"""
        <div class="alerta-card alerta-{cor}">
            <div class="valor">{formatar_moeda(valor)}</div>
            <div class="label">{label} ({qtd} títulos)</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11, tab12 = st.tabs([
    "Visão Geral", "Vencimentos", "Fornecedores", "Categorias", "Evolução", "Filiais",
    "Adiantamentos", "Custos Financeiros", "Formas Pagamento", "Câmbio", "Detalhes", "Análise Avançada"
])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: VISÃO GERAL
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Distribuição por Status")
        df_status = df.groupby('STATUS')['SALDO'].sum().reset_index()
        df_status = df_status[df_status['SALDO'] > 0].sort_values('SALDO', ascending=False)

        if len(df_status) > 0:
            fig = px.pie(df_status, values='SALDO', names='STATUS', hole=0.5,
                        color_discrete_sequence=SEQUENCIA_CORES)
            fig.update_traces(textposition='outside', textinfo='percent+label',
                            textfont_size=11, pull=[0.02] * len(df_status))
            fig.update_layout(criar_layout(320), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("##### Fluxo de Caixa Semanal")
        df_fluxo = df_pendentes[df_pendentes['VENCIMENTO'].notna()].copy()
        df_fluxo = df_fluxo[df_fluxo['DIAS_VENC'].between(-14, 60)]

        if len(df_fluxo) > 0:
            df_fluxo['SEMANA'] = df_fluxo['VENCIMENTO'].dt.to_period('W').astype(str)
            df_grp = df_fluxo.groupby('SEMANA')['SALDO'].sum().reset_index()
            df_grp['ACUM'] = df_grp['SALDO'].cumsum()

            fig = go.Figure()
            fig.add_trace(go.Bar(x=df_grp['SEMANA'], y=df_grp['SALDO'],
                                name='Semanal', marker_color=CORES['primaria']))
            fig.add_trace(go.Scatter(x=df_grp['SEMANA'], y=df_grp['ACUM'],
                                    name='Acumulado', line=dict(color=CORES['alerta'], width=3),
                                    yaxis='y2'))
            fig.update_layout(criar_layout(320,
                yaxis2={'overlaying': 'y', 'side': 'right', 'showgrid': False}))
            st.plotly_chart(fig, use_container_width=True)

    # Curva ABC
    st.markdown("##### Curva ABC - Top 20 Fornecedores")
    df_abc = df.groupby('NOME_FORNECEDOR')['VALOR_ORIGINAL'].sum().nlargest(20).reset_index()
    df_abc['ACUM'] = df_abc['VALOR_ORIGINAL'].cumsum()
    df_abc['PCT'] = df_abc['ACUM'] / df_abc['VALOR_ORIGINAL'].sum() * 100
    df_abc['CLASSE'] = df_abc['PCT'].apply(lambda x: 'A' if x <= 80 else ('B' if x <= 95 else 'C'))

    fig = go.Figure()
    cores_classe = {'A': CORES['primaria'], 'B': CORES['alerta'], 'C': CORES['perigo']}

    for classe in ['A', 'B', 'C']:
        df_c = df_abc[df_abc['CLASSE'] == classe]
        if len(df_c) > 0:
            fig.add_trace(go.Bar(
                x=df_c['NOME_FORNECEDOR'].str[:20], y=df_c['VALOR_ORIGINAL'],
                name=f'Classe {classe}', marker_color=cores_classe[classe]
            ))

    fig.add_trace(go.Scatter(
        x=df_abc['NOME_FORNECEDOR'].str[:20], y=df_abc['PCT'],
        name='% Acumulado', yaxis='y2', line=dict(color='white', width=2),
        mode='lines+markers', marker=dict(size=4)
    ))

    fig.add_hline(y=80, line_dash="dash", line_color=CORES['texto_secundario'],
                  annotation_text="80%", yref='y2')

    fig.update_layout(criar_layout(380, barmode='stack',
        yaxis2={'overlaying': 'y', 'side': 'right', 'range': [0, 105], 'showgrid': False},
        xaxis_tickangle=-45))
    st.plotly_chart(fig, use_container_width=True)

    # Resumo ABC
    col1, col2, col3 = st.columns(3)
    for i, classe in enumerate(['A', 'B', 'C']):
        df_c = df_abc[df_abc['CLASSE'] == classe]
        with [col1, col2, col3][i]:
            pct = df_c['VALOR_ORIGINAL'].sum() / df_abc['VALOR_ORIGINAL'].sum() * 100 if len(df_abc) > 0 else 0
            st.metric(f"Classe {classe}", f"{len(df_c)} forn.", f"{pct:.1f}% do valor")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2: VENCIMENTOS
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Aging de Vencimentos")
        ordem = ['Vencido', 'Vence em 7 dias', 'Vence em 15 dias', 'Vence em 30 dias',
                'Vence em 60 dias', 'Vence em +60 dias']
        df_aging = df_pendentes.groupby('STATUS').agg({'SALDO': 'sum', 'FORNECEDOR': 'count'}).reset_index()
        df_aging.columns = ['Status', 'Valor', 'Qtd']
        df_aging['ordem'] = df_aging['Status'].apply(lambda x: ordem.index(x) if x in ordem else 99)
        df_aging = df_aging.sort_values('ordem')

        cores_status = []
        for s in df_aging['Status']:
            if 'Vencido' in s: cores_status.append(CORES['perigo'])
            elif '7' in s: cores_status.append(CORES['alerta'])
            elif '15' in s or '30' in s: cores_status.append('#fbbf24')
            else: cores_status.append(CORES['info'])

        fig = go.Figure(go.Bar(
            x=df_aging['Status'], y=df_aging['Valor'],
            marker_color=cores_status,
            text=[f'{formatar_moeda(v)}' for v in df_aging['Valor']],
            textposition='outside', textfont_size=10
        ))
        fig.update_layout(criar_layout(350), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("##### Calendário - Próximos 30 dias")
        df_cal = df_pendentes[df_pendentes['VENCIMENTO'].notna()].copy()
        df_cal = df_cal[df_cal['DIAS_VENC'].between(-7, 30)]

        if len(df_cal) > 0:
            df_cal['DIA'] = df_cal['VENCIMENTO'].dt.date
            df_cal_grp = df_cal.groupby('DIA')['SALDO'].sum().reset_index()

            fig = px.bar(df_cal_grp, x='DIA', y='SALDO', color='SALDO',
                        color_continuous_scale=[[0, CORES['info']], [0.5, CORES['alerta']], [1, CORES['perigo']]])
            fig.update_layout(criar_layout(350), coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem vencimentos nos próximos 30 dias")

    # Tabela de vencidos
    st.markdown("##### Títulos Vencidos")
    if len(df_vencidos) > 0:
        df_show = df_vencidos.nlargest(20, 'SALDO')[
            ['NOME_FILIAL', 'NOME_FORNECEDOR', 'DESCRICAO', 'VENCIMENTO', 'DIAS_ATRASO', 'SALDO']
        ].copy()
        df_show['VENCIMENTO'] = df_show['VENCIMENTO'].dt.strftime('%d/%m/%Y')
        df_show['SALDO'] = df_show['SALDO'].apply(lambda x: formatar_moeda(x, completo=True))
        df_show.columns = ['Filial', 'Fornecedor', 'Categoria', 'Vencimento', 'Dias Atraso', 'Valor']
        st.dataframe(df_show, use_container_width=True, hide_index=True)
    else:
        st.success("Nenhum título vencido!")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3: FORNECEDORES
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Top 15 - Valor Total")
        df_forn = df.groupby('NOME_FORNECEDOR')['VALOR_ORIGINAL'].sum().nlargest(15).reset_index()

        fig = go.Figure(go.Bar(
            y=df_forn['NOME_FORNECEDOR'].str[:28], x=df_forn['VALOR_ORIGINAL'],
            orientation='h', marker_color=CORES['primaria'],
            text=[formatar_moeda(v) for v in df_forn['VALOR_ORIGINAL']],
            textposition='outside', textfont_size=10
        ))
        fig.update_layout(criar_layout(480, yaxis={'autorange': 'reversed'}))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("##### Top 15 - Saldo Pendente")
        df_pend = df_pendentes.groupby('NOME_FORNECEDOR')['SALDO'].sum().nlargest(15).reset_index()

        fig = go.Figure(go.Bar(
            y=df_pend['NOME_FORNECEDOR'].str[:28], x=df_pend['SALDO'],
            orientation='h', marker_color=CORES['perigo'],
            text=[formatar_moeda(v) for v in df_pend['SALDO']],
            textposition='outside', textfont_size=10
        ))
        fig.update_layout(criar_layout(480, yaxis={'autorange': 'reversed'}))
        st.plotly_chart(fig, use_container_width=True)

    # Tabela
    st.markdown("##### Ranking Completo")
    df_rank = df.groupby('NOME_FORNECEDOR').agg({
        'VALOR_ORIGINAL': 'sum', 'SALDO': 'sum', 'FORNECEDOR': 'count'
    }).reset_index().nlargest(30, 'VALOR_ORIGINAL')
    df_rank.columns = ['Fornecedor', 'Total', 'Pendente', 'Títulos']
    df_rank['% Pago'] = ((df_rank['Total'] - df_rank['Pendente']) / df_rank['Total'] * 100).round(1)
    df_rank['Total'] = df_rank['Total'].apply(lambda x: formatar_moeda(x, completo=True))
    df_rank['Pendente'] = df_rank['Pendente'].apply(lambda x: formatar_moeda(x, completo=True))
    st.dataframe(df_rank, use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4: CATEGORIAS
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("##### Análise por Categoria de Despesa")

    if len(df) == 0:
        st.warning("Nenhum dado disponível para o período selecionado.")
    else:
        # KPIs por categoria
        df_cat = df.groupby('DESCRICAO').agg({
            'VALOR_ORIGINAL': 'sum', 'SALDO': 'sum', 'FORNECEDOR': 'count'
        }).reset_index()
        df_cat.columns = ['Categoria', 'Total', 'Pendente', 'Qtd']
        df_cat['Pago'] = df_cat['Total'] - df_cat['Pendente']
        df_cat['Pct_Pago'] = (df_cat['Pago'] / df_cat['Total'] * 100).fillna(0).round(1)
        df_cat = df_cat.sort_values('Total', ascending=False)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("##### Treemap - Distribuição por Categoria")
            df_tree = df_cat.head(15).copy()
            if len(df_tree) > 0:
                fig = px.treemap(df_tree, path=['Categoria'], values='Total',
                                color='Pct_Pago', color_continuous_scale='RdYlGn',
                                hover_data={'Total': ':,.2f', 'Pendente': ':,.2f', 'Pct_Pago': ':.1f'})
                fig.update_layout(criar_layout(400), coloraxis_colorbar_title="% Pago")
                fig.update_traces(textinfo='label+value', texttemplate='%{label}<br>R$ %{value:,.0f}')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sem dados para exibir treemap.")

        with col2:
            st.markdown("##### Top 10 Categorias - Valor")
            df_top = df_cat.head(10)
            if len(df_top) > 0:
                fig = go.Figure()
                fig.add_trace(go.Bar(y=df_top['Categoria'].str[:30], x=df_top['Pago'],
                                    orientation='h', name='Pago', marker_color=CORES['primaria']))
                fig.add_trace(go.Bar(y=df_top['Categoria'].str[:30], x=df_top['Pendente'],
                                    orientation='h', name='Pendente', marker_color=CORES['alerta']))
                fig.update_layout(criar_layout(400, barmode='stack', yaxis={'autorange': 'reversed'}))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sem dados para exibir gráfico.")

        # Tabela detalhada
        st.markdown("##### Ranking Completo por Categoria")
        df_cat_show = df_cat.copy()
        df_cat_show['Total_fmt'] = df_cat_show['Total'].apply(lambda x: formatar_moeda(x, completo=True))
        df_cat_show['Pendente_fmt'] = df_cat_show['Pendente'].apply(lambda x: formatar_moeda(x, completo=True))
        df_cat_show = df_cat_show[['Categoria', 'Total_fmt', 'Pendente_fmt', 'Qtd', 'Pct_Pago']]
        df_cat_show.columns = ['Categoria', 'Total', 'Pendente', 'Títulos', '% Pago']
        st.dataframe(df_cat_show, use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5: EVOLUÇÃO
# ═══════════════════════════════════════════════════════════════════════════════
with tab5:
    periodo = st.radio("Agrupar por:", ["Mês", "Trimestre", "Ano"], horizontal=True)

    if periodo == "Mês":
        df_tempo = df_contas.groupby(df_contas['EMISSAO'].dt.to_period('M')).agg({
            'VALOR_ORIGINAL': 'sum', 'SALDO': 'sum'
        }).reset_index()
        df_tempo['EMISSAO'] = df_tempo['EMISSAO'].astype(str)
        df_tempo = df_tempo.tail(18)
    elif periodo == "Trimestre":
        df_contas['TRIM'] = df_contas['EMISSAO'].dt.year.astype(str) + '-Q' + df_contas['TRIMESTRE'].astype(str)
        df_tempo = df_contas.groupby('TRIM').agg({'VALOR_ORIGINAL': 'sum', 'SALDO': 'sum'}).reset_index()
        df_tempo.columns = ['EMISSAO', 'VALOR_ORIGINAL', 'SALDO']
    else:
        df_tempo = df_contas.groupby('ANO').agg({'VALOR_ORIGINAL': 'sum', 'SALDO': 'sum'}).reset_index()
        df_tempo['ANO'] = df_tempo['ANO'].astype(int).astype(str)
        df_tempo.columns = ['EMISSAO', 'VALOR_ORIGINAL', 'SALDO']

    df_tempo['PAGO'] = df_tempo['VALOR_ORIGINAL'] - df_tempo['SALDO']

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"##### Pago vs Pendente por {periodo}")
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df_tempo['EMISSAO'], y=df_tempo['PAGO'],
                            name='Pago', marker_color=CORES['primaria']))
        fig.add_trace(go.Bar(x=df_tempo['EMISSAO'], y=df_tempo['SALDO'],
                            name='Pendente', marker_color=CORES['alerta']))
        fig.update_layout(criar_layout(380, barmode='stack'))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("##### Heatmap Mês x Ano")
        df_heat = df_contas.copy()
        df_heat['MES_NUM'] = df_heat['EMISSAO'].dt.month
        df_heat['ANO_NUM'] = df_heat['EMISSAO'].dt.year

        pivot = df_heat.pivot_table(values='VALOR_ORIGINAL', index='MES_NUM',
                                   columns='ANO_NUM', aggfunc='sum', fill_value=0)
        meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

        fig = go.Figure(go.Heatmap(
            z=pivot.values,
            x=[str(int(c)) for c in pivot.columns],
            y=[meses[int(i)-1] for i in pivot.index],
            colorscale=[[0, CORES['fundo']], [0.5, CORES['alerta']], [1, CORES['primaria']]],
            hovertemplate='%{y} %{x}<br>R$ %{z:,.0f}<extra></extra>'
        ))
        fig.update_layout(criar_layout(380))
        st.plotly_chart(fig, use_container_width=True)

    # Projeção de Fluxo de Caixa
    st.markdown("##### Projeção de Fluxo de Caixa - Próximos 90 dias")
    df_proj = df_pendentes[df_pendentes['VENCIMENTO'].notna()].copy()
    df_proj = df_proj[df_proj['DIAS_VENC'].between(-30, 90)]

    if len(df_proj) > 0:
        df_proj['SEMANA'] = df_proj['VENCIMENTO'].dt.to_period('W').astype(str)
        df_grp_proj = df_proj.groupby('SEMANA')['SALDO'].sum().reset_index()
        df_grp_proj['ACUMULADO'] = df_grp_proj['SALDO'].cumsum()

        fig = go.Figure()
        fig.add_trace(go.Bar(x=df_grp_proj['SEMANA'], y=df_grp_proj['SALDO'],
                            name='Semanal', marker_color=CORES['primaria']))
        fig.add_trace(go.Scatter(x=df_grp_proj['SEMANA'], y=df_grp_proj['ACUMULADO'],
                                name='Acumulado', line=dict(color=CORES['perigo'], width=3),
                                yaxis='y2'))
        fig.update_layout(criar_layout(350,
            yaxis2={'overlaying': 'y', 'side': 'right', 'showgrid': False},
            xaxis_tickangle=-45))
        st.plotly_chart(fig, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 6: FILIAIS (COM COMPARATIVO)
# ═══════════════════════════════════════════════════════════════════════════════
with tab6:
    st.markdown("##### Performance por Filial")

    df_fil = df.groupby('NOME_FILIAL').agg({
        'VALOR_ORIGINAL': 'sum', 'SALDO': 'sum', 'FORNECEDOR': 'count'
    }).reset_index()
    df_fil.columns = ['Filial', 'Total', 'Pendente', 'Qtd']
    df_fil['Pago'] = df_fil['Total'] - df_fil['Pendente']
    df_fil['Pct'] = (df_fil['Pago'] / df_fil['Total'] * 100).round(1)
    df_fil = df_fil.sort_values('Total', ascending=False)

    # Calcular vencidos por filial
    df_venc_fil = df_vencidos.groupby('NOME_FILIAL')['SALDO'].sum().reset_index()
    df_venc_fil.columns = ['Filial', 'Vencido']
    df_fil = df_fil.merge(df_venc_fil, on='Filial', how='left').fillna(0)
    df_fil['Pct_Vencido'] = (df_fil['Vencido'] / df_fil['Total'] * 100).round(1)

    col1, col2 = st.columns([2, 1])

    with col1:
        fig = go.Figure()
        fig.add_trace(go.Bar(y=df_fil['Filial'], x=df_fil['Pago'],
                            orientation='h', name='Pago', marker_color=CORES['primaria']))
        fig.add_trace(go.Bar(y=df_fil['Filial'], x=df_fil['Pendente'],
                            orientation='h', name='Pendente', marker_color=CORES['alerta']))
        fig.update_layout(criar_layout(400, barmode='stack', yaxis={'autorange': 'reversed'}))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("##### Ranking % Pagamento")
        for _, row in df_fil.sort_values('Pct', ascending=False).iterrows():
            pct = row['Pct']
            st.markdown(f"**{row['Filial'][:20]}**: {pct:.0f}%")
            st.progress(min(pct/100, 1.0))

    # Comparativo entre Filiais
    st.markdown("---")
    st.markdown("##### Comparativo entre Filiais")

    col1, col2 = st.columns(2)

    with col1:
        # Radar Chart para comparação
        if len(df_fil) > 1:
            # Normalizar métricas para o radar
            df_radar = df_fil.head(6).copy()
            df_radar['Total_norm'] = (df_radar['Total'] / df_radar['Total'].max() * 100).round(1)
            df_radar['Pct_Pgto'] = df_radar['Pct']
            df_radar['Qtd_norm'] = (df_radar['Qtd'] / df_radar['Qtd'].max() * 100).round(1)
            df_radar['Eficiencia'] = (100 - df_radar['Pct_Vencido']).round(1)

            fig = go.Figure()
            for _, row in df_radar.iterrows():
                fig.add_trace(go.Scatterpolar(
                    r=[row['Total_norm'], row['Pct_Pgto'], row['Qtd_norm'], row['Eficiencia']],
                    theta=['Volume', '% Pago', 'Qtd Títulos', 'Eficiência'],
                    fill='toself',
                    name=row['Filial'][:15]
                ))
            fig.update_layout(criar_layout(350),
                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                showlegend=True)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Tabela de benchmark
        st.markdown("##### Benchmark de Filiais")
        media_pct = df_fil['Pct'].mean()
        media_vencido = df_fil['Pct_Vencido'].mean()

        df_bench = df_fil[['Filial', 'Total', 'Pct', 'Pct_Vencido']].copy()
        df_bench['Status'] = df_bench.apply(
            lambda r: 'Acima da média' if r['Pct'] > media_pct else 'Abaixo da média', axis=1
        )
        df_bench['Total'] = df_bench['Total'].apply(lambda x: formatar_moeda(x, completo=True))
        df_bench.columns = ['Filial', 'Total', '% Pago', '% Vencido', 'Status']
        st.dataframe(df_bench, use_container_width=True, hide_index=True)

        st.caption(f"Média % Pago: {media_pct:.1f}% | Média % Vencido: {media_vencido:.1f}%")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 7: ADIANTAMENTOS
# ═══════════════════════════════════════════════════════════════════════════════
with tab7:
    st.markdown("##### Adiantamentos a Pagar")

    total_adiant = df_adiant['VALOR_ORIGINAL'].sum() if 'VALOR_ORIGINAL' in df_adiant.columns else 0
    total_baixas = df_baixas['VALOR_BAIXA'].sum() if 'VALOR_BAIXA' in df_baixas.columns else 0
    saldo_adiant = total_adiant - total_baixas
    pct_baixado = (total_baixas / total_adiant * 100) if total_adiant > 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Adiantamentos", formatar_moeda(total_adiant))
    col2.metric("Total Baixas", formatar_moeda(total_baixas))
    col3.metric("Saldo Pendente", formatar_moeda(saldo_adiant))
    col4.metric("% Baixado", f"{pct_baixado:.1f}%")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Top Fornecedores - Adiantamentos")
        if 'NOME_FORNECEDOR' in df_adiant.columns and 'VALOR_ORIGINAL' in df_adiant.columns:
            df_ad = df_adiant.groupby('NOME_FORNECEDOR')['VALOR_ORIGINAL'].sum().nlargest(10).reset_index()

            fig = go.Figure(go.Bar(
                y=df_ad['NOME_FORNECEDOR'].str[:25], x=df_ad['VALOR_ORIGINAL'],
                orientation='h', marker_color=CORES['alerta'],
                text=[formatar_moeda(v) for v in df_ad['VALOR_ORIGINAL']],
                textposition='outside'
            ))
            fig.update_layout(criar_layout(350, yaxis={'autorange': 'reversed'}))
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("##### Top Fornecedores - Baixas")
        if 'NOME_FORNECEDOR' in df_baixas.columns and 'VALOR_BAIXA' in df_baixas.columns:
            df_bx = df_baixas.groupby('NOME_FORNECEDOR')['VALOR_BAIXA'].sum().nlargest(10).reset_index()

            fig = go.Figure(go.Bar(
                y=df_bx['NOME_FORNECEDOR'].str[:25], x=df_bx['VALOR_BAIXA'],
                orientation='h', marker_color=CORES['primaria'],
                text=[formatar_moeda(v) for v in df_bx['VALOR_BAIXA']],
                textposition='outside'
            ))
            fig.update_layout(criar_layout(350, yaxis={'autorange': 'reversed'}))
            st.plotly_chart(fig, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 8: CUSTOS FINANCEIROS
# ═══════════════════════════════════════════════════════════════════════════════
with tab8:
    from tabs.custos_financeiros import render_custos_financeiros
    render_custos_financeiros(df)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 9: FORMAS DE PAGAMENTO
# ═══════════════════════════════════════════════════════════════════════════════
with tab9:
    from tabs.formas_pagamento import render_formas_pagamento
    render_formas_pagamento(df)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 10: ANÁLISE CAMBIAL
# ═══════════════════════════════════════════════════════════════════════════════
with tab10:
    from tabs.cambio import render_cambio
    render_cambio(df)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 11: DETALHES (DRILL-DOWN)
# ═══════════════════════════════════════════════════════════════════════════════
with tab11:
    st.markdown("##### Consulta Detalhada de Títulos")

    # Filtros específicos
    col1, col2, col3 = st.columns(3)
    status_options = df['STATUS'].unique().tolist()
    default_status = [s for s in ['Vencido'] if s in status_options]
    with col1:
        filtro_status_det = st.multiselect("Status", status_options, default=default_status)
    with col2:
        filtro_filial_det = st.multiselect("Filial", df['NOME_FILIAL'].unique().tolist())
    with col3:
        busca_titulo = st.text_input("Buscar título/fornecedor", placeholder="Digite...")

    # Aplicar filtros
    df_det = df.copy()
    if filtro_status_det:
        df_det = df_det[df_det['STATUS'].isin(filtro_status_det)]
    if filtro_filial_det:
        df_det = df_det[df_det['NOME_FILIAL'].isin(filtro_filial_det)]
    if busca_titulo:
        df_det = df_det[
            df_det['NOME_FORNECEDOR'].str.contains(busca_titulo, case=False, na=False) |
            df_det['DESCRICAO'].astype(str).str.contains(busca_titulo, case=False, na=False)
        ]

    # Métricas do filtro
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Títulos", formatar_numero(len(df_det)))
    col2.metric("Valor Total", formatar_moeda(df_det['VALOR_ORIGINAL'].sum()))
    col3.metric("Saldo Pendente", formatar_moeda(df_det['SALDO'].sum()))
    col4.metric("Vencidos", formatar_numero(len(df_det[df_det['STATUS'] == 'Vencido'])))

    # Botão de exportar filtrados
    st.download_button(
        label="Exportar Seleção para Excel",
        data=to_excel(df_det),
        file_name=f"titulos_filtrados_{hoje.strftime('%Y%m%d_%H%M')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Tabela com paginação
    st.markdown("##### Lista de Títulos")
    page_size = st.selectbox("Itens por página", [25, 50, 100, 200], index=0)

    df_show = df_det[[
        'NOME_FILIAL', 'NOME_FORNECEDOR', 'DESCRICAO',
        'EMISSAO', 'VENCIMENTO', 'VALOR_ORIGINAL', 'SALDO', 'STATUS', 'DIAS_ATRASO'
    ]].copy()
    df_show['EMISSAO'] = df_show['EMISSAO'].dt.strftime('%d/%m/%Y')
    df_show['VENCIMENTO'] = df_show['VENCIMENTO'].dt.strftime('%d/%m/%Y')
    df_show['VALOR_ORIGINAL'] = df_show['VALOR_ORIGINAL'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['SALDO'] = df_show['SALDO'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show.columns = ['Filial', 'Fornecedor', 'Categoria', 'Emissão', 'Vencimento', 'Valor', 'Saldo', 'Status', 'Dias Atraso']

    total_pages = max(1, len(df_show) // page_size + (1 if len(df_show) % page_size > 0 else 0))
    page = st.number_input("Página", min_value=1, max_value=total_pages, value=1)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size

    st.dataframe(df_show.iloc[start_idx:end_idx], use_container_width=True, hide_index=True)
    st.caption(f"Mostrando {start_idx + 1} - {min(end_idx, len(df_show))} de {len(df_show)} títulos | Página {page} de {total_pages}")

    # Indicadores de Performance
    st.markdown("---")
    st.markdown("##### Indicadores de Performance")

    col1, col2, col3, col4 = st.columns(4)

    # DPO (Days Payable Outstanding) - média de dias para pagar
    df_pagos = df_contas[df_contas['SALDO'] == 0].copy()
    if len(df_pagos) > 0 and 'DT_BAIXA' in df_pagos.columns:
        df_pagos['DIAS_PGTO'] = (df_pagos['DT_BAIXA'] - df_pagos['EMISSAO']).dt.days
        dpo = df_pagos['DIAS_PGTO'].mean()
    else:
        dpo = 0

    # Taxa de pontualidade
    df_com_baixa = df_contas[df_contas['SALDO'] == 0].copy()
    if len(df_com_baixa) > 0 and 'DT_BAIXA' in df_com_baixa.columns and 'VENCIMENTO' in df_com_baixa.columns:
        df_com_baixa['PONTUAL'] = df_com_baixa['DT_BAIXA'] <= df_com_baixa['VENCIMENTO']
        taxa_pontual = df_com_baixa['PONTUAL'].sum() / len(df_com_baixa) * 100
    else:
        taxa_pontual = 0

    # Concentração de fornecedores (top 10)
    total_geral = df['VALOR_ORIGINAL'].sum()
    top10_valor = df.groupby('NOME_FORNECEDOR')['VALOR_ORIGINAL'].sum().nlargest(10).sum()
    concentracao = (top10_valor / total_geral * 100) if total_geral > 0 else 0

    # Ticket médio
    ticket_medio = df['VALOR_ORIGINAL'].mean()

    with col1:
        st.metric("DPO Médio", f"{dpo:.0f} dias", help="Days Payable Outstanding - Média de dias para pagamento")
    with col2:
        st.metric("Taxa Pontualidade", f"{taxa_pontual:.1f}%", help="Percentual de títulos pagos até o vencimento")
    with col3:
        st.metric("Concentração Top 10", f"{concentracao:.1f}%", help="Percentual do valor concentrado nos 10 maiores fornecedores")
    with col4:
        st.metric("Ticket Médio", formatar_moeda(ticket_medio), help="Valor médio por título")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 12: ANÁLISE AVANÇADA
# ═══════════════════════════════════════════════════════════════════════════════
with tab12:
    st.markdown("### Análise Avançada de Dados")

    # Sub-abas para organizar as análises
    analise_tab1, analise_tab2, analise_tab3, analise_tab4 = st.tabs([
        "Estatísticas", "Pareto & Concentração", "Sazonalidade", "Risco & Previsão"
    ])

    # ─────────────────────────────────────────────────────────────────────────────
    # SUB-TAB 1: ESTATÍSTICAS DESCRITIVAS
    # ─────────────────────────────────────────────────────────────────────────────
    with analise_tab1:
        st.markdown("##### Estatísticas Descritivas")

        col1, col2 = st.columns(2)

        with col1:
            # Estatísticas de valores
            st.markdown("###### Distribuição de Valores")
            stats_valores = df['VALOR_ORIGINAL'].describe()

            stats_df = pd.DataFrame({
                'Métrica': ['Contagem', 'Média', 'Desvio Padrão', 'Mínimo', '25%', 'Mediana', '75%', 'Máximo'],
                'Valor': [
                    formatar_numero(stats_valores['count']),
                    formatar_moeda(stats_valores['mean']),
                    formatar_moeda(stats_valores['std']),
                    formatar_moeda(stats_valores['min']),
                    formatar_moeda(stats_valores['25%']),
                    formatar_moeda(stats_valores['50%']),
                    formatar_moeda(stats_valores['75%']),
                    formatar_moeda(stats_valores['max'])
                ]
            })
            st.dataframe(stats_df, use_container_width=True, hide_index=True)

            # Histograma de valores
            fig_hist = go.Figure()
            fig_hist.add_trace(go.Histogram(
                x=df['VALOR_ORIGINAL'],
                nbinsx=30,
                marker_color=CORES['primaria'],
                opacity=0.7
            ))
            fig_hist.update_layout(
                title="Distribuição de Valores dos Títulos",
                xaxis_title="Valor (R$)",
                yaxis_title="Frequência",
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                height=300
            )
            st.plotly_chart(fig_hist, use_container_width=True)

        with col2:
            # Box plot por status
            st.markdown("###### Valores por Status")
            fig_box = go.Figure()
            for status in df['STATUS'].unique():
                df_status = df[df['STATUS'] == status]
                fig_box.add_trace(go.Box(
                    y=df_status['VALOR_ORIGINAL'],
                    name=status,
                    boxpoints='outliers'
                ))
            fig_box.update_layout(
                title="Distribuição de Valores por Status",
                yaxis_title="Valor (R$)",
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                height=300,
                showlegend=False
            )
            st.plotly_chart(fig_box, use_container_width=True)

            # Estatísticas por filial
            st.markdown("###### Resumo por Filial")
            stats_filial = df.groupby('NOME_FILIAL').agg({
                'VALOR_ORIGINAL': ['count', 'sum', 'mean'],
                'SALDO': 'sum'
            }).round(2)
            stats_filial.columns = ['Qtd Títulos', 'Valor Total', 'Ticket Médio', 'Saldo Pendente']
            stats_filial = stats_filial.sort_values('Valor Total', ascending=False)
            st.dataframe(stats_filial, use_container_width=True)

    # ─────────────────────────────────────────────────────────────────────────────
    # SUB-TAB 2: ANÁLISE DE PARETO E CONCENTRAÇÃO
    # ─────────────────────────────────────────────────────────────────────────────
    with analise_tab2:
        st.markdown("##### Análise de Pareto (80/20)")

        # Análise de Pareto por Fornecedor
        df_pareto = df.groupby('NOME_FORNECEDOR')['VALOR_ORIGINAL'].sum().sort_values(ascending=False).reset_index()
        df_pareto['Percentual'] = df_pareto['VALOR_ORIGINAL'] / df_pareto['VALOR_ORIGINAL'].sum() * 100
        df_pareto['Acumulado'] = df_pareto['Percentual'].cumsum()
        df_pareto['Rank'] = range(1, len(df_pareto) + 1)

        # Encontrar o ponto 80%
        ponto_80 = df_pareto[df_pareto['Acumulado'] <= 80].shape[0]
        total_fornecedores = len(df_pareto)
        perc_fornecedores_80 = (ponto_80 / total_fornecedores * 100) if total_fornecedores > 0 else 0

        col1, col2, col3 = st.columns(3)
        col1.metric("Fornecedores que representam 80%", f"{ponto_80} de {total_fornecedores}")
        col2.metric("Percentual de fornecedores", f"{perc_fornecedores_80:.1f}%")
        col3.metric("Concentração", "Alta" if perc_fornecedores_80 < 30 else "Moderada" if perc_fornecedores_80 < 50 else "Baixa")

        # Gráfico de Pareto
        fig_pareto = go.Figure()

        # Barras (valores)
        fig_pareto.add_trace(go.Bar(
            x=df_pareto['NOME_FORNECEDOR'][:20],
            y=df_pareto['VALOR_ORIGINAL'][:20],
            name='Valor',
            marker_color=CORES['primaria'],
            yaxis='y'
        ))

        # Linha (acumulado)
        fig_pareto.add_trace(go.Scatter(
            x=df_pareto['NOME_FORNECEDOR'][:20],
            y=df_pareto['Acumulado'][:20],
            name='% Acumulado',
            mode='lines+markers',
            marker_color=CORES['alerta'],
            yaxis='y2'
        ))

        # Linha de referência 80%
        fig_pareto.add_hline(y=80, line_dash="dash", line_color="red",
                            annotation_text="80%", yref='y2')

        fig_pareto.update_layout(
            title="Curva de Pareto - Top 20 Fornecedores",
            xaxis_title="Fornecedor",
            yaxis=dict(title="Valor (R$)", side='left'),
            yaxis2=dict(title="% Acumulado", side='right', overlaying='y', range=[0, 105]),
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            height=400,
            xaxis_tickangle=-45,
            legend=dict(orientation="h", yanchor="bottom", y=1.02)
        )
        st.plotly_chart(fig_pareto, use_container_width=True)

        # Análise de concentração por categoria
        st.markdown("##### Concentração por Categoria")
        df_cat_conc = df.groupby('DESCRICAO')['VALOR_ORIGINAL'].sum().sort_values(ascending=False).head(15)

        fig_cat = go.Figure(go.Treemap(
            labels=df_cat_conc.index,
            parents=[""] * len(df_cat_conc),
            values=df_cat_conc.values,
            texttemplate="<b>%{label}</b><br>%{value:,.0f}<br>%{percentRoot:.1%}",
            marker=dict(
                colors=df_cat_conc.values,
                colorscale='Greens'
            )
        ))
        fig_cat.update_layout(
            title="Mapa de Concentração por Categoria",
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            height=400
        )
        st.plotly_chart(fig_cat, use_container_width=True)

    # ─────────────────────────────────────────────────────────────────────────────
    # SUB-TAB 3: ANÁLISE DE SAZONALIDADE
    # ─────────────────────────────────────────────────────────────────────────────
    with analise_tab3:
        st.markdown("##### Análise de Sazonalidade")

        # Análise por dia da semana
        df['DIA_SEMANA'] = df['VENCIMENTO'].dt.dayofweek
        dias_semana = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
        df_dia_semana = df.groupby('DIA_SEMANA').agg({
            'VALOR_ORIGINAL': ['sum', 'count', 'mean']
        }).reset_index()
        df_dia_semana.columns = ['DIA_SEMANA', 'Valor Total', 'Quantidade', 'Ticket Médio']
        df_dia_semana['Dia'] = df_dia_semana['DIA_SEMANA'].map(lambda x: dias_semana[int(x)])

        col1, col2 = st.columns(2)

        with col1:
            fig_semana = go.Figure()
            fig_semana.add_trace(go.Bar(
                x=df_dia_semana['Dia'],
                y=df_dia_semana['Valor Total'],
                marker_color=CORES['primaria'],
                text=[formatar_moeda(v, completo=True) for v in df_dia_semana['Valor Total']],
                textposition='outside'
            ))
            fig_semana.update_layout(
                title="Vencimentos por Dia da Semana",
                xaxis_title="Dia",
                yaxis_title="Valor Total",
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                height=350
            )
            st.plotly_chart(fig_semana, use_container_width=True)

        with col2:
            # Análise por dia do mês
            df['DIA_MES'] = df['VENCIMENTO'].dt.day
            df_dia_mes = df.groupby('DIA_MES')['VALOR_ORIGINAL'].sum().reset_index()

            fig_dia_mes = go.Figure()
            fig_dia_mes.add_trace(go.Scatter(
                x=df_dia_mes['DIA_MES'],
                y=df_dia_mes['VALOR_ORIGINAL'],
                mode='lines+markers',
                fill='tozeroy',
                marker_color=CORES['primaria'],
                fillcolor=f"rgba(0, 135, 61, 0.3)"
            ))
            fig_dia_mes.update_layout(
                title="Vencimentos por Dia do Mês",
                xaxis_title="Dia do Mês",
                yaxis_title="Valor Total",
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                height=350
            )
            st.plotly_chart(fig_dia_mes, use_container_width=True)

        # Heatmap mensal
        st.markdown("##### Padrão Mensal de Vencimentos")
        df['MES'] = df['VENCIMENTO'].dt.month
        df['ANO'] = df['VENCIMENTO'].dt.year

        pivot_mensal = df.pivot_table(
            values='VALOR_ORIGINAL',
            index='MES',
            columns='ANO',
            aggfunc='sum',
            fill_value=0
        )

        meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

        fig_heat = go.Figure(data=go.Heatmap(
            z=pivot_mensal.values,
            x=[str(c) for c in pivot_mensal.columns],
            y=[meses[int(i)-1] for i in pivot_mensal.index],
            colorscale='Greens',
            text=[[formatar_moeda(v, completo=True) for v in row] for row in pivot_mensal.values],
            texttemplate="%{text}",
            textfont={"size": 10}
        ))
        fig_heat.update_layout(
            title="Mapa de Calor - Vencimentos por Mês/Ano",
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            height=400
        )
        st.plotly_chart(fig_heat, use_container_width=True)

    # ─────────────────────────────────────────────────────────────────────────────
    # SUB-TAB 4: ANÁLISE DE RISCO E PREVISÃO
    # ─────────────────────────────────────────────────────────────────────────────
    with analise_tab4:
        st.markdown("##### Análise de Risco e Projeções")

        # Métricas de risco
        col1, col2, col3, col4 = st.columns(4)

        # Índice de inadimplência
        total_vencido = df[df['STATUS'] == 'Vencido']['SALDO'].sum()
        total_geral = df['SALDO'].sum()
        indice_inadimplencia = (total_vencido / total_geral * 100) if total_geral > 0 else 0

        # Aging médio dos vencidos
        df_vencidos = df[df['STATUS'] == 'Vencido']
        aging_medio = df_vencidos['DIAS_ATRASO'].mean() if len(df_vencidos) > 0 else 0

        # Risco de concentração (Herfindahl)
        participacoes = df.groupby('NOME_FORNECEDOR')['VALOR_ORIGINAL'].sum() / df['VALOR_ORIGINAL'].sum()
        hhi = (participacoes ** 2).sum() * 10000  # Índice HHI

        # Volatilidade mensal
        valores_mensais = df.groupby(df['VENCIMENTO'].dt.to_period('M'))['VALOR_ORIGINAL'].sum()
        volatilidade = (valores_mensais.std() / valores_mensais.mean() * 100) if valores_mensais.mean() > 0 else 0

        col1.metric("Índice Inadimplência", f"{indice_inadimplencia:.1f}%",
                   delta="Alto" if indice_inadimplencia > 20 else "Moderado" if indice_inadimplencia > 10 else "Baixo",
                   delta_color="inverse")
        col2.metric("Aging Médio Vencidos", f"{aging_medio:.0f} dias")
        col3.metric("Índice HHI", f"{hhi:.0f}", help="< 1500 = Baixa concentração, 1500-2500 = Moderada, > 2500 = Alta")
        col4.metric("Volatilidade Mensal", f"{volatilidade:.1f}%")

        col1, col2 = st.columns(2)

        with col1:
            # Distribuição de risco por faixa de atraso
            st.markdown("###### Distribuição por Faixa de Atraso")

            def classificar_atraso(dias):
                if dias <= 0:
                    return '0 - Em dia'
                elif dias <= 30:
                    return '1 - 1-30 dias'
                elif dias <= 60:
                    return '2 - 31-60 dias'
                elif dias <= 90:
                    return '3 - 61-90 dias'
                else:
                    return '4 - 90+ dias'

            df['FAIXA_ATRASO'] = df['DIAS_ATRASO'].apply(classificar_atraso)
            df_risco = df.groupby('FAIXA_ATRASO').agg({
                'SALDO': 'sum',
                'VALOR_ORIGINAL': 'count'
            }).reset_index()
            df_risco.columns = ['Faixa', 'Valor', 'Quantidade']
            df_risco = df_risco.sort_values('Faixa')

            cores_risco = [CORES['sucesso'], CORES['info'], CORES['alerta'], '#ff6b35', CORES['perigo']]

            fig_risco = go.Figure()
            fig_risco.add_trace(go.Bar(
                x=[f.split(' - ')[1] for f in df_risco['Faixa']],
                y=df_risco['Valor'],
                marker_color=cores_risco[:len(df_risco)],
                text=[formatar_moeda(v, completo=True) for v in df_risco['Valor']],
                textposition='outside'
            ))
            fig_risco.update_layout(
                title="Saldo por Faixa de Atraso",
                xaxis_title="Faixa de Atraso",
                yaxis_title="Saldo (R$)",
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                height=350
            )
            st.plotly_chart(fig_risco, use_container_width=True)

        with col2:
            # Projeção de vencimentos próximos 30 dias
            st.markdown("###### Projeção Próximos 30 Dias")

            proximos_30 = df[(df['VENCIMENTO'] >= hoje) & (df['VENCIMENTO'] <= hoje + timedelta(days=30))]
            proj_diaria = proximos_30.groupby(proximos_30['VENCIMENTO'].dt.date)['SALDO'].sum().reset_index()
            proj_diaria.columns = ['Data', 'Valor']
            proj_diaria['Acumulado'] = proj_diaria['Valor'].cumsum()

            fig_proj = go.Figure()
            fig_proj.add_trace(go.Bar(
                x=proj_diaria['Data'],
                y=proj_diaria['Valor'],
                name='Valor Diário',
                marker_color=CORES['primaria'],
                opacity=0.7
            ))
            fig_proj.add_trace(go.Scatter(
                x=proj_diaria['Data'],
                y=proj_diaria['Acumulado'],
                name='Acumulado',
                mode='lines+markers',
                line=dict(color=CORES['alerta'], width=3)
            ))
            fig_proj.update_layout(
                title="Vencimentos Próximos 30 Dias",
                xaxis_title="Data",
                yaxis_title="Valor (R$)",
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                height=350,
                legend=dict(orientation="h", yanchor="bottom", y=1.02)
            )
            st.plotly_chart(fig_proj, use_container_width=True)

        # Análise de fornecedores críticos
        st.markdown("##### Fornecedores Críticos (Alto Risco)")

        # Fornecedores com mais vencidos
        df_forn_risco = df[df['STATUS'] == 'Vencido'].groupby('NOME_FORNECEDOR').agg({
            'SALDO': 'sum',
            'VALOR_ORIGINAL': 'count',
            'DIAS_ATRASO': 'mean'
        }).reset_index()
        df_forn_risco.columns = ['Fornecedor', 'Saldo Vencido', 'Qtd Títulos', 'Atraso Médio']
        df_forn_risco = df_forn_risco.sort_values('Saldo Vencido', ascending=False).head(10)
        df_forn_risco['Saldo Vencido'] = df_forn_risco['Saldo Vencido'].apply(lambda x: formatar_moeda(x, completo=True))
        df_forn_risco['Atraso Médio'] = df_forn_risco['Atraso Médio'].apply(lambda x: f"{x:.0f} dias")

        st.dataframe(df_forn_risco, use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════════════
st.divider()
st.caption(f"Grupo Progresso - Dashboard Financeiro | Atualizado em {hoje.strftime('%d/%m/%Y %H:%M')}")
