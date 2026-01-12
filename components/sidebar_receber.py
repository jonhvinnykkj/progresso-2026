"""
Componente de Sidebar - Contas a Receber
"""
import streamlit as st
from datetime import datetime, timedelta, date
import calendar
from config.theme import get_cores
from config.settings import MESES_NOMES, OPCOES_PERIODO_RAPIDO
from utils.formatters import to_excel, to_csv, formatar_moeda, formatar_numero


STATUS_OPCOES_RECEBER = [
    'Todos os Status',
    'Recebido',
    'Vencido',
    'Vence em 7 dias',
    'Vence em 15 dias',
    'Vence em 30 dias'
]


def render_sidebar_receber(df_contas, filiais_opcoes, categorias_opcoes):
    """Renderiza a sidebar para Contas a Receber"""
    cores = get_cores()
    hoje = datetime.now()

    with st.sidebar:
        # Header
        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 1rem;">
            <div style="background: {cores['sucesso']}; width: 40px; height: 40px;
                        border-radius: 10px; display: flex; align-items: center;
                        justify-content: center; color: white; font-weight: 700;">GP</div>
            <div>
                <div style="color: {cores['texto']}; font-weight: 600; font-size: 0.95rem;">Grupo Progresso</div>
                <div style="color: {cores['texto_secundario']}; font-size: 0.7rem;">Contas a Receber</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        # Período
        st.markdown(f"<p style='color: {cores['texto']}; font-size: 0.8rem; font-weight: 600; margin-bottom: 0.5rem;'>Período</p>", unsafe_allow_html=True)

        data_min = df_contas['EMISSAO'].min().date()
        data_max = df_contas['EMISSAO'].max().date()
        anos = list(range(data_min.year, data_max.year + 1))

        tipo = st.selectbox("Tipo", ['Rápido', 'Por Ano', 'Por Mês', 'Intervalo'], label_visibility="collapsed", key="tipo_periodo_rec")

        data_inicio, data_fim = _processar_periodo(tipo, data_min, data_max, anos, hoje)

        data_inicio = max(data_inicio, data_min)
        data_fim = min(data_fim, data_max)

        st.caption(f"De {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}")

        st.divider()

        # Filtros
        st.markdown(f"<p style='color: {cores['texto']}; font-size: 0.8rem; font-weight: 600; margin-bottom: 0.5rem;'>Filtros</p>", unsafe_allow_html=True)

        filtro_filial = st.selectbox("Filial", filiais_opcoes, key="filtro_filial_rec")
        filtro_status = st.selectbox("Status", STATUS_OPCOES_RECEBER, key="filtro_status_rec")
        filtro_categoria = st.selectbox("Categoria", categorias_opcoes, key="filtro_categoria_rec")

        # Filtro por tipo de documento
        filtro_tipo_doc = st.selectbox("Tipo Documento", ['Todos', 'Com NF', 'Sem NF'], key="filtro_tipo_doc_rec")

        busca_cliente = st.text_input("Cliente", placeholder="Buscar...", key="busca_cliente_rec")

        st.divider()

        # Exportar
        st.markdown(f"<p style='color: {cores['texto']}; font-size: 0.8rem; font-weight: 600; margin-bottom: 0.5rem;'>Exportar</p>", unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "Excel",
                data=to_excel(df_contas),
                file_name=f"receber_{hoje.strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        with col2:
            st.download_button(
                "CSV",
                data=to_csv(df_contas),
                file_name=f"receber_{hoje.strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )

        st.divider()

        # Resumo
        st.markdown(f"<p style='color: {cores['texto']}; font-size: 0.8rem; font-weight: 600; margin-bottom: 0.5rem;'>Resumo</p>", unsafe_allow_html=True)

        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['borda']};
                    border-radius: 8px; padding: 0.75rem; font-size: 0.8rem;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.4rem;">
                <span style="color: {cores['texto_secundario']};">Títulos</span>
                <span style="color: {cores['texto']}; font-weight: 600;">{formatar_numero(len(df_contas))}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.4rem;">
                <span style="color: {cores['texto_secundario']};">Valor Total</span>
                <span style="color: {cores['texto']}; font-weight: 600;">{formatar_moeda(df_contas['VALOR_ORIGINAL'].sum())}</span>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <span style="color: {cores['texto_secundario']};">A Receber</span>
                <span style="color: {cores['sucesso']}; font-weight: 600;">{formatar_moeda(df_contas['SALDO'].sum())}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Footer
        st.markdown(f"""
        <div style="text-align: center; margin-top: 1.5rem; padding-top: 1rem;
                    border-top: 1px solid {cores['borda']};">
            <p style="color: {cores['texto_secundario']}; font-size: 0.65rem; margin: 0;">
                Atualizado: {hoje.strftime('%d/%m/%Y %H:%M')}</p>
        </div>
        """, unsafe_allow_html=True)

    return data_inicio, data_fim, filtro_filial, filtro_status, filtro_categoria, busca_cliente, filtro_tipo_doc


def _processar_periodo(tipo, data_min, data_max, anos, hoje):
    """Processa seleção de período"""

    if tipo == 'Rápido':
        opcao = st.selectbox("Período", OPCOES_PERIODO_RAPIDO, label_visibility="collapsed", key="periodo_rapido_rec")

        if opcao == 'Todos os dados':
            return data_min, data_max
        elif opcao == 'Hoje':
            return hoje.date(), hoje.date()
        elif opcao == 'Últimos 7 dias':
            return hoje.date() - timedelta(days=7), hoje.date()
        elif opcao == 'Últimos 30 dias':
            return hoje.date() - timedelta(days=30), hoje.date()
        elif opcao == 'Últimos 90 dias':
            return hoje.date() - timedelta(days=90), hoje.date()
        elif opcao == 'Este mês':
            return hoje.date().replace(day=1), hoje.date()
        elif opcao == 'Mês passado':
            primeiro = hoje.date().replace(day=1)
            fim = primeiro - timedelta(days=1)
            return fim.replace(day=1), fim
        elif opcao == 'Este ano':
            return hoje.date().replace(month=1, day=1), hoje.date()

    elif tipo == 'Por Ano':
        col1, col2 = st.columns(2)
        with col1:
            ano_ini = st.selectbox("De", anos, index=0, key="ano_ini_rec")
        with col2:
            ano_fim = st.selectbox("Até", anos, index=len(anos)-1, key="ano_fim_rec")
        return date(ano_ini, 1, 1), date(ano_fim, 12, 31)

    elif tipo == 'Por Mês':
        col1, col2 = st.columns(2)
        with col1:
            ano = st.selectbox("Ano", anos, index=len(anos)-1, key="ano_mes_rec")
        with col2:
            meses = list(MESES_NOMES.values())
            mes_sel = st.selectbox("Mês", meses, index=hoje.month-1, key="mes_sel_rec")
            mes_num = [k for k, v in MESES_NOMES.items() if v == mes_sel][0]
        ultimo = calendar.monthrange(ano, mes_num)[1]
        return date(ano, mes_num, 1), date(ano, mes_num, ultimo)

    elif tipo == 'Intervalo':
        col1, col2 = st.columns(2)
        with col1:
            d_ini = st.date_input("De", value=data_min, min_value=data_min, max_value=data_max, key="d_ini_rec")
        with col2:
            d_fim = st.date_input("Até", value=data_max, min_value=data_min, max_value=data_max, key="d_fim_rec")
        return d_ini, d_fim

    return data_min, data_max
