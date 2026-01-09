"""
Componente de Navegacao - NavBar Unificada
Dashboard Financeiro - Grupo Progresso
"""
import streamlit as st
from datetime import datetime, timedelta
import calendar
from config.theme import get_cores

# Nomes dos meses em portugues
MESES_PT = {
    1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
    7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'
}

MESES_COMPLETO = {
    1: 'Janeiro', 2: 'Fevereiro', 3: 'Marco', 4: 'Abril', 5: 'Maio', 6: 'Junho',
    7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
}


def render_navbar(pagina_atual: str = "pagar", mostrar_filtro_tempo: bool = True):
    """
    Renderiza a barra de navegacao superior com filtros de tempo

    Args:
        pagina_atual: 'pagar', 'intercompany', 'receber'
        mostrar_filtro_tempo: Se deve mostrar os filtros de tempo

    Returns:
        tuple: (data_inicio, data_fim) se mostrar_filtro_tempo=True, else None
    """
    cores = get_cores()
    hoje = datetime.now()

    # CSS da navbar
    st.markdown(f"""
    <style>
        .navbar-container {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: {cores['card']};
            border: 1px solid {cores['borda']};
            border-radius: 12px;
            padding: 0.6rem 1.2rem;
            margin-bottom: 0.75rem;
        }}

        .navbar-brand {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .navbar-logo {{
            width: 38px;
            height: 38px;
            background: linear-gradient(135deg, {cores['primaria']} 0%, {cores['primaria_escura']} 100%);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 700;
            font-size: 1rem;
            box-shadow: 0 2px 8px {cores['primaria']}40;
        }}

        .navbar-title {{
            color: {cores['texto']};
            font-weight: 600;
            font-size: 1rem;
            margin: 0;
        }}

        .navbar-subtitle {{
            color: {cores['texto_secundario']};
            font-size: 0.65rem;
            margin: 0;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .nav-btn-active {{
            background: {cores['primaria']} !important;
            color: white !important;
            padding: 6px 12px;
            border-radius: 6px;
            text-align: center;
            font-size: 0.75rem;
            font-weight: 500;
        }}
    </style>
    """, unsafe_allow_html=True)

    # Renderizar navbar HTML - Brand
    st.markdown(f"""
    <div class="navbar-container">
        <div class="navbar-brand">
            <div class="navbar-logo">GP</div>
            <div>
                <p class="navbar-title">Grupo Progresso</p>
                <p class="navbar-subtitle">Dashboard Financeiro</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Linha com navegacao entre paginas (3 modulos principais)
    col_spacer, col_nav1, col_nav2, col_nav3, col_spacer2 = st.columns([2, 1.2, 1.2, 1.2, 2])

    # Navegacao entre paginas
    with col_nav1:
        if pagina_atual == 'pagar':
            st.markdown(f"""
            <div style="background: {cores['primaria']}; color: white; padding: 8px 14px;
                        border-radius: 8px; text-align: center; font-size: 0.8rem; font-weight: 600;">
                A Pagar
            </div>
            """, unsafe_allow_html=True)
        else:
            st.page_link("app.py", label="A Pagar", icon=":material/payments:")

    with col_nav2:
        if pagina_atual == 'intercompany':
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, {cores['alerta']}, {cores['info']}); color: white; padding: 8px 14px;
                        border-radius: 8px; text-align: center; font-size: 0.8rem; font-weight: 600;">
                Intercompany
            </div>
            """, unsafe_allow_html=True)
        else:
            st.page_link("pages/1_Intercompany.py", label="Intercompany", icon=":material/sync_alt:")

    with col_nav3:
        if pagina_atual == 'receber':
            st.markdown(f"""
            <div style="background: {cores['sucesso']}; color: white; padding: 8px 14px;
                        border-radius: 8px; text-align: center; font-size: 0.8rem; font-weight: 600;">
                A Receber
            </div>
            """, unsafe_allow_html=True)
        else:
            st.page_link("pages/2_Contas_a_Receber.py", label="A Receber", icon=":material/account_balance:")

    # Filtros de tempo
    data_inicio = None
    data_fim = None

    if mostrar_filtro_tempo:
        # Inicializar estados
        if 'filtro_tipo_periodo' not in st.session_state:
            st.session_state.filtro_tipo_periodo = 'rapido'
        if 'filtro_rapido' not in st.session_state:
            st.session_state.filtro_rapido = 'todos'
        if 'filtro_ano' not in st.session_state:
            st.session_state.filtro_ano = hoje.year
        if 'filtro_mes_inicio' not in st.session_state:
            st.session_state.filtro_mes_inicio = 1
        if 'filtro_mes_fim' not in st.session_state:
            st.session_state.filtro_mes_fim = hoje.month
        if 'filtro_data_inicio' not in st.session_state:
            st.session_state.filtro_data_inicio = (hoje - timedelta(days=30)).date()
        if 'filtro_data_fim' not in st.session_state:
            st.session_state.filtro_data_fim = hoje.date()

        # Container de filtros de tempo
        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['borda']};
                    border-radius: 10px; padding: 0.5rem 1rem; margin-bottom: 0.5rem;">
            <span style="color: {cores['texto_secundario']}; font-size: 0.7rem; font-weight: 600;">
                PERIODO
            </span>
        </div>
        """, unsafe_allow_html=True)

        # Tabs para tipo de filtro
        col_tipo, col_filtros = st.columns([1, 4])

        with col_tipo:
            tipo_periodo = st.radio(
                "Tipo",
                ['Rapido', 'Ano/Mes', 'Periodo'],
                key="nav_tipo_periodo",
                horizontal=False,
                label_visibility="collapsed"
            )
            if tipo_periodo == 'Rapido':
                st.session_state.filtro_tipo_periodo = 'rapido'
            elif tipo_periodo == 'Ano/Mes':
                st.session_state.filtro_tipo_periodo = 'ano_mes'
            else:
                st.session_state.filtro_tipo_periodo = 'periodo'

        with col_filtros:
            if st.session_state.filtro_tipo_periodo == 'rapido':
                # Filtros rapidos
                opcoes_rapido = {
                    '7d': '7 dias',
                    '30d': '30 dias',
                    '90d': '90 dias',
                    'mes': 'Este mes',
                    'ano': 'Este ano',
                    'todos': 'Todos'
                }

                cols = st.columns(len(opcoes_rapido))
                for i, (key, label) in enumerate(opcoes_rapido.items()):
                    with cols[i]:
                        is_active = st.session_state.filtro_rapido == key
                        if st.button(
                            label,
                            key=f"nav_rapido_{key}",
                            use_container_width=True,
                            type="primary" if is_active else "secondary"
                        ):
                            st.session_state.filtro_rapido = key
                            st.rerun()

                # Calcular datas baseado no filtro rapido
                filtro = st.session_state.filtro_rapido

                if filtro == 'todos':
                    data_inicio = datetime(2000, 1, 1).date()
                    data_fim = hoje.date()
                elif filtro == 'mes':
                    data_inicio = hoje.replace(day=1).date()
                    data_fim = hoje.date()
                elif filtro == 'ano':
                    data_inicio = hoje.replace(month=1, day=1).date()
                    data_fim = hoje.date()
                elif filtro == '7d':
                    data_inicio = (hoje - timedelta(days=7)).date()
                    data_fim = hoje.date()
                elif filtro == '30d':
                    data_inicio = (hoje - timedelta(days=30)).date()
                    data_fim = hoje.date()
                elif filtro == '90d':
                    data_inicio = (hoje - timedelta(days=90)).date()
                    data_fim = hoje.date()

            elif st.session_state.filtro_tipo_periodo == 'ano_mes':
                # Filtros por Ano/Mes
                col_ano, col_mes_ini, col_mes_fim = st.columns([1, 1.5, 1.5])

                with col_ano:
                    anos_disponiveis = list(range(hoje.year, 2019, -1))
                    ano_selecionado = st.selectbox(
                        "Ano",
                        anos_disponiveis,
                        index=anos_disponiveis.index(st.session_state.filtro_ano) if st.session_state.filtro_ano in anos_disponiveis else 0,
                        key="nav_ano"
                    )
                    st.session_state.filtro_ano = ano_selecionado

                with col_mes_ini:
                    meses_opcoes = [(i, MESES_COMPLETO[i]) for i in range(1, 13)]
                    mes_inicio_idx = st.selectbox(
                        "Mes Inicio",
                        range(1, 13),
                        format_func=lambda x: MESES_COMPLETO[x],
                        index=st.session_state.filtro_mes_inicio - 1,
                        key="nav_mes_inicio"
                    )
                    st.session_state.filtro_mes_inicio = mes_inicio_idx

                with col_mes_fim:
                    mes_fim_idx = st.selectbox(
                        "Mes Fim",
                        range(1, 13),
                        format_func=lambda x: MESES_COMPLETO[x],
                        index=st.session_state.filtro_mes_fim - 1,
                        key="nav_mes_fim"
                    )
                    st.session_state.filtro_mes_fim = mes_fim_idx

                # Calcular datas baseado no ano/mes selecionado
                ano = st.session_state.filtro_ano
                mes_ini = st.session_state.filtro_mes_inicio
                mes_fim = st.session_state.filtro_mes_fim

                # Garantir que mes_fim >= mes_ini
                if mes_fim < mes_ini:
                    mes_fim = mes_ini

                data_inicio = datetime(ano, mes_ini, 1).date()
                ultimo_dia = calendar.monthrange(ano, mes_fim)[1]
                data_fim = datetime(ano, mes_fim, ultimo_dia).date()

            else:
                # Filtros por Periodo (calendario)
                col_data_ini, col_data_fim = st.columns(2)

                with col_data_ini:
                    data_inicio_sel = st.date_input(
                        "Data Inicio",
                        value=st.session_state.filtro_data_inicio,
                        key="nav_data_inicio",
                        format="DD/MM/YYYY"
                    )
                    st.session_state.filtro_data_inicio = data_inicio_sel

                with col_data_fim:
                    data_fim_sel = st.date_input(
                        "Data Fim",
                        value=st.session_state.filtro_data_fim,
                        key="nav_data_fim",
                        format="DD/MM/YYYY"
                    )
                    st.session_state.filtro_data_fim = data_fim_sel

                data_inicio = st.session_state.filtro_data_inicio
                data_fim = st.session_state.filtro_data_fim

                # Garantir que data_fim >= data_inicio
                if data_fim < data_inicio:
                    data_fim = data_inicio

        # Mostrar periodo selecionado
        if data_inicio and data_fim:
            st.markdown(f"""
            <div style="text-align: center; padding: 0.3rem; background: {cores['primaria']}15;
                        border-radius: 6px; margin-top: 0.3rem;">
                <span style="color: {cores['primaria']}; font-size: 0.75rem; font-weight: 500;">
                    {data_inicio.strftime('%d/%m/%Y')} - {data_fim.strftime('%d/%m/%Y')}
                </span>
            </div>
            """, unsafe_allow_html=True)

    if mostrar_filtro_tempo:
        return data_inicio, data_fim
    return None


def render_page_header(titulo: str, subtitulo: str, icone: str = "GP", cor: str = None):
    """
    Renderiza o header da pagina atual

    Args:
        titulo: Titulo principal
        subtitulo: Subtitulo/descricao
        icone: Texto do icone (2 letras)
        cor: Cor do icone (opcional)
    """
    cores = get_cores()
    cor_icone = cor or cores['primaria']

    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 0.75rem;">
        <div style="width: 45px; height: 45px; background: linear-gradient(135deg, {cor_icone} 0%, {cor_icone}dd 100%);
                    border-radius: 10px; display: flex; align-items: center; justify-content: center;
                    color: white; font-weight: 700; font-size: 1.1rem;
                    box-shadow: 0 3px 10px {cor_icone}40;">
            {icone}
        </div>
        <div>
            <h2 style="color: {cores['texto']}; margin: 0; font-size: 1.3rem; font-weight: 600;">{titulo}</h2>
            <p style="color: {cores['texto_secundario']}; margin: 0; font-size: 0.8rem;">{subtitulo}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
