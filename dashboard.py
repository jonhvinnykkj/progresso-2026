"""
Dashboard Financeiro - Grupo Progresso
Versão refatorada usando módulos
"""
import streamlit as st
from datetime import datetime, timedelta
import calendar

# ═══════════════════════════════════════════════════════════════════════════════
# IMPORTS DOS MÓDULOS
# ═══════════════════════════════════════════════════════════════════════════════
from config.settings import PAGE_CONFIG, MESES_NOMES, STATUS_OPCOES
from config.theme import get_cores, get_sequencia_cores, get_css
from data.loader import carregar_dados, aplicar_filtros, get_opcoes_filtros, get_dados_filtrados, calcular_metricas
from utils.formatters import formatar_moeda, formatar_numero, formatar_percentual, to_excel, to_csv

# Imports das tabs
from tabs.visao_geral import render_visao_geral
from tabs.vencimentos import render_vencimentos
from tabs.fornecedores import render_fornecedores
from tabs.categorias import render_categorias
from tabs.evolucao import render_evolucao
from tabs.filiais import render_filiais
from tabs.adiantamentos import render_adiantamentos
from tabs.detalhes import render_detalhes
from tabs.analise_avancada import render_analise_avancada
from tabs.custos_financeiros import render_custos_financeiros
from tabs.formas_pagamento import render_formas_pagamento
from tabs.cambio import render_cambio

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO DA PÁGINA
# ═══════════════════════════════════════════════════════════════════════════════
st.set_page_config(**PAGE_CONFIG)

# Estado do tema
if 'tema_escuro' not in st.session_state:
    st.session_state.tema_escuro = True

# Estado da pagina selecionada
if 'pagina_atual' not in st.session_state:
    st.session_state.pagina_atual = "Dashboard"

PAGINAS = [
    "Dashboard", "Vencimentos", "Fornecedores", "Categorias",
    "Evolucao", "Filiais", "Adiantamentos", "Custos Financ.",
    "Formas Pagto", "Cambio", "Detalhes", "Estatisticas"
]

# Cores e CSS
CORES = get_cores()
SEQUENCIA_CORES = get_sequencia_cores()
st.markdown(get_css(), unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# CARREGAR DADOS
# ═══════════════════════════════════════════════════════════════════════════════
df_contas, df_adiant, df_baixas = carregar_dados()
filiais_opcoes, categorias_opcoes = get_opcoes_filtros(df_contas)
hoje = datetime.now()

# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    # Header com toggle de tema
    col_logo, col_tema = st.columns([4, 1])
    with col_tema:
        tema_icon = "🌙" if st.session_state.tema_escuro else "☀️"
        if st.button(tema_icon, key="toggle_tema", help="Alternar tema"):
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

    # ═══════════════════════════════════════════════════════════════════════════
    # NAVEGACAO
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown(f"<p style='color: {CORES['primaria']}; font-weight: 600; font-size: 0.9rem; margin-bottom: 0.5rem;'>Pagina</p>", unsafe_allow_html=True)
    pagina_selecionada = st.selectbox(
        "Pagina",
        PAGINAS,
        index=PAGINAS.index(st.session_state.pagina_atual),
        key="nav_pagina",
        label_visibility="collapsed"
    )
    if pagina_selecionada != st.session_state.pagina_atual:
        st.session_state.pagina_atual = pagina_selecionada

    # ═══════════════════════════════════════════════════════════════════════════
    # PERIODO
    # ═══════════════════════════════════════════════════════════════════════════
    data_min = df_contas['EMISSAO'].min().date()
    data_max = df_contas['EMISSAO'].max().date()
    anos_disponiveis = list(range(data_min.year, data_max.year + 1))

    st.markdown(f"<p style='color: {CORES['primaria']}; font-weight: 600; font-size: 0.9rem; margin-bottom: 0.8rem;'>📅 Período</p>", unsafe_allow_html=True)

    tipo_periodo = st.selectbox("Tipo", ['Rápido', 'Por Ano', 'Por Mês', 'Intervalo'], label_visibility="collapsed")

    if tipo_periodo == 'Rápido':
        opcoes = ['Todos os dados', 'Últimos 30 dias', 'Últimos 90 dias', 'Este mês', 'Este ano']
        opcao = st.selectbox("Opção", opcoes, label_visibility="collapsed")

        if opcao == 'Todos os dados':
            data_inicio, data_fim = data_min, data_max
        elif opcao == 'Últimos 30 dias':
            data_inicio, data_fim = hoje.date() - timedelta(days=30), hoje.date()
        elif opcao == 'Últimos 90 dias':
            data_inicio, data_fim = hoje.date() - timedelta(days=90), hoje.date()
        elif opcao == 'Este mês':
            data_inicio, data_fim = hoje.date().replace(day=1), hoje.date()
        else:
            data_inicio, data_fim = hoje.date().replace(month=1, day=1), hoje.date()

    elif tipo_periodo == 'Por Ano':
        col1, col2 = st.columns(2)
        with col1:
            ano_ini = st.selectbox("De", anos_disponiveis, index=0, key="ano_ini")
        with col2:
            ano_fim = st.selectbox("Até", anos_disponiveis, index=len(anos_disponiveis)-1, key="ano_fim")
        from datetime import date
        data_inicio, data_fim = date(ano_ini, 1, 1), date(ano_fim, 12, 31)

    elif tipo_periodo == 'Por Mês':
        col1, col2 = st.columns(2)
        with col1:
            ano = st.selectbox("Ano", anos_disponiveis, index=len(anos_disponiveis)-1, key="ano_mes")
        with col2:
            mes_sel = st.selectbox("Mês", list(MESES_NOMES.values()), index=hoje.month-1)
            mes_num = [k for k, v in MESES_NOMES.items() if v == mes_sel][0]
        from datetime import date
        ultimo = calendar.monthrange(ano, mes_num)[1]
        data_inicio, data_fim = date(ano, mes_num, 1), date(ano, mes_num, ultimo)

    else:  # Intervalo
        col1, col2 = st.columns(2)
        with col1:
            data_inicio = st.date_input("De", value=data_min, min_value=data_min, max_value=data_max)
        with col2:
            data_fim = st.date_input("Até", value=data_max, min_value=data_min, max_value=data_max)

    # Ajustar limites
    data_inicio = max(data_inicio, data_min)
    data_fim = min(data_fim, data_max)

    st.caption(f"📅 {data_inicio.strftime('%d/%m/%Y')} → {data_fim.strftime('%d/%m/%Y')}")

    # ═══════════════════════════════════════════════════════════════════════════
    # FILTROS
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown(f"<p style='color: {CORES['primaria']}; font-weight: 600; font-size: 0.9rem; margin: 1rem 0 0.5rem;'>🎯 Filtros</p>", unsafe_allow_html=True)

    filtro_filial = st.selectbox("Filial", filiais_opcoes, label_visibility="collapsed")
    filtro_status = st.selectbox("Status", STATUS_OPCOES, label_visibility="collapsed")
    filtro_categoria = st.selectbox("Categoria", categorias_opcoes, label_visibility="collapsed")

    # Filtros novos
    filtro_tipo_doc = st.selectbox("Tipo Doc", ['Todos', 'Com NF', 'Sem NF'], label_visibility="collapsed")

    formas_pagto = ['Todas']
    if 'DESCRICAO_FORMA_PAGAMENTO' in df_contas.columns:
        formas = df_contas['DESCRICAO_FORMA_PAGAMENTO'].dropna().unique().tolist()
        formas_pagto += sorted([f for f in formas if f and str(f).strip()])
    filtro_forma_pagto = st.selectbox("Forma Pagto", formas_pagto, label_visibility="collapsed")

    busca_fornecedor = st.text_input("🔍 Fornecedor", placeholder="Buscar...")

    # ═══════════════════════════════════════════════════════════════════════════
    # EXPORTAR
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown(f"<p style='color: {CORES['primaria']}; font-weight: 600; font-size: 0.9rem; margin: 1rem 0 0.5rem;'>📥 Exportar</p>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.download_button("Excel", data=to_excel(df_contas), file_name=f"contas_{hoje.strftime('%Y%m%d')}.xlsx",
                          mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    with col2:
        st.download_button("CSV", data=to_csv(df_contas), file_name=f"contas_{hoje.strftime('%Y%m%d')}.csv",
                          mime="text/csv", use_container_width=True)

    # Rodapé
    st.markdown(f"""
    <div style="text-align: center; margin-top: 2rem; padding-top: 1rem; border-top: 1px solid {CORES['borda']};">
        <p style="color: {CORES['texto_secundario']}; font-size: 0.7rem;">Atualizado: {hoje.strftime('%d/%m/%Y %H:%M')}</p>
    </div>
    """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# APLICAR FILTROS
# ═══════════════════════════════════════════════════════════════════════════════
df = aplicar_filtros(df_contas, data_inicio, data_fim, filtro_filial, filtro_status,
                     filtro_categoria, busca_fornecedor, filtro_tipo_doc, filtro_forma_pagto)
df_pendentes, df_vencidos = get_dados_filtrados(df, df_contas)
metricas = calcular_metricas(df, df_vencidos)

# ═══════════════════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div style="background: linear-gradient(135deg, {CORES['primaria_escura']} 0%, {CORES['primaria']} 100%);
            padding: 1.5rem 2rem; border-radius: 16px; margin-bottom: 1.5rem;">
    <h1 style="color: white; margin: 0; font-size: 1.75rem;">Contas a Pagar</h1>
    <p style="color: rgba(255,255,255,0.8); margin: 0.3rem 0 0; font-size: 0.9rem;">
        {formatar_numero(len(df))} títulos | {data_inicio.strftime('%d/%m/%Y')} - {data_fim.strftime('%d/%m/%Y')}</p>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# KPIs PRINCIPAIS
# ═══════════════════════════════════════════════════════════════════════════════
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total", formatar_moeda(metricas['total']), f"{formatar_numero(metricas['qtd_total'])} títulos")
col2.metric("Pago", formatar_moeda(metricas['pago']), f"{metricas['pct_pago']:.1f}%")
col3.metric("Pendente", formatar_moeda(metricas['pendente']))
col4.metric("Vencido", formatar_moeda(metricas['vencido']), f"{formatar_numero(metricas['qtd_vencidos'])} títulos", delta_color="inverse")
col5.metric("Atraso Médio", f"{metricas['dias_atraso']:.0f} dias")

# ═══════════════════════════════════════════════════════════════════════════════
# ALERTAS
# ═══════════════════════════════════════════════════════════════════════════════
valor_7d = df_pendentes[df_pendentes['STATUS'] == 'Vence em 7 dias']['SALDO'].sum()
titulos_48h = df[df['ALERTA_48H'] == True] if 'ALERTA_48H' in df.columns else []

if metricas['qtd_vencidos'] > 0:
    st.warning(f"⚠️ {metricas['qtd_vencidos']} títulos vencidos: {formatar_moeda(metricas['vencido'], completo=True)}")
if len(titulos_48h) > 0:
    st.error(f"🚨 {len(titulos_48h)} títulos com entrada < 48h do vencimento")
if valor_7d > 100000:
    st.info(f"📅 Próximos 7 dias: {formatar_moeda(valor_7d, completo=True)}")

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# CONTEUDO DA PAGINA
# ═══════════════════════════════════════════════════════════════════════════════
pagina = st.session_state.pagina_atual

if pagina == "Dashboard":
    render_visao_geral(df)
elif pagina == "Vencimentos":
    render_vencimentos(df)
elif pagina == "Fornecedores":
    render_fornecedores(df)
elif pagina == "Categorias":
    render_categorias(df)
elif pagina == "Evolucao":
    render_evolucao(df)
elif pagina == "Filiais":
    render_filiais(df)
elif pagina == "Adiantamentos":
    render_adiantamentos(df_adiant, df_baixas)
elif pagina == "Custos Financ.":
    render_custos_financeiros(df)
elif pagina == "Formas Pagto":
    render_formas_pagamento(df)
elif pagina == "Cambio":
    render_cambio(df)
elif pagina == "Detalhes":
    render_detalhes(df)
elif pagina == "Estatisticas":
    render_analise_avancada(df)
