"""
Aba Detalhes - Consulta e busca avancada de titulos
Foco: Busca, filtros avancados, tabela completa e exportacao
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from config.theme import get_cores
from utils.formatters import formatar_moeda, formatar_numero, to_excel


def render_detalhes(df):
    """Renderiza a aba de Detalhes - Consulta de Titulos"""
    cores = get_cores()
    hoje = datetime.now()

    if len(df) == 0:
        st.warning("Nenhum dado disponivel.")
        return

    # ========== FILTROS AVANCADOS ==========
    st.markdown("##### Filtros")

    # Linha 1: Filtros principais
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        filtro_status = st.multiselect(
            "Status",
            options=['Pago', 'Vencido', 'Vence em 7 dias', 'Vence em 15 dias', 'Vence em 30 dias', 'Vence em 60 dias', 'Vence em +60 dias'],
            default=[],
            key="det_status",
            placeholder="Todos"
        )

    with col2:
        filiais = sorted(df['NOME_FILIAL'].dropna().unique().tolist())
        filtro_filial = st.multiselect(
            "Filial",
            options=filiais,
            default=[],
            key="det_filial",
            placeholder="Todas"
        )

    with col3:
        categorias = sorted(df['DESCRICAO'].dropna().unique().tolist())
        filtro_categoria = st.multiselect(
            "Categoria",
            options=categorias,
            default=[],
            key="det_categoria",
            placeholder="Todas"
        )

    with col4:
        formas_pagto = sorted(df['DESCRICAO_FORMA_PAGAMENTO'].dropna().unique().tolist()) if 'DESCRICAO_FORMA_PAGAMENTO' in df.columns else []
        filtro_forma = st.multiselect(
            "Forma Pagto",
            options=formas_pagto,
            default=[],
            key="det_forma",
            placeholder="Todas"
        )

    # Linha 2: Busca e filtros adicionais
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        busca_fornecedor = st.text_input(
            "Buscar Fornecedor",
            placeholder="Nome do fornecedor...",
            key="det_busca_forn"
        )

    with col2:
        busca_numero = st.text_input(
            "Numero/Documento",
            placeholder="NF, boleto...",
            key="det_busca_num"
        )

    with col3:
        filtro_tipo = st.radio(
            "Mostrar",
            ["Todos", "Com Saldo", "Pagos"],
            horizontal=True,
            key="det_tipo"
        )

    with col4:
        filtro_tipo_doc = st.radio(
            "Documento",
            ["Todos", "Com NF", "Sem NF"],
            horizontal=True,
            key="det_tipo_doc"
        )

    # Linha 3: Filtros de valor e datas
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        valor_min = st.number_input(
            "Valor Minimo",
            min_value=0.0,
            value=0.0,
            step=1000.0,
            key="det_valor_min"
        )

    with col2:
        valor_max = st.number_input(
            "Valor Maximo",
            min_value=0.0,
            value=0.0,
            step=1000.0,
            key="det_valor_max",
            help="0 = sem limite"
        )

    with col3:
        filtro_venc_inicio = st.date_input(
            "Vencimento de",
            value=None,
            key="det_venc_inicio"
        )

    with col4:
        filtro_venc_fim = st.date_input(
            "Vencimento ate",
            value=None,
            key="det_venc_fim"
        )

    # ========== APLICAR FILTROS ==========
    df_filtrado = _aplicar_filtros(df)

    st.divider()

    # ========== RESUMO DOS RESULTADOS ==========
    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Titulos", formatar_numero(len(df_filtrado)))
    col2.metric("Valor Total", formatar_moeda(df_filtrado['VALOR_ORIGINAL'].sum()))
    col3.metric("Saldo", formatar_moeda(df_filtrado['SALDO'].sum()))

    qtd_vencidos = len(df_filtrado[df_filtrado['STATUS'] == 'Vencido'])
    col4.metric("Vencidos", formatar_numero(qtd_vencidos))

    qtd_fornecedores = df_filtrado['NOME_FORNECEDOR'].nunique()
    col5.metric("Fornecedores", formatar_numero(qtd_fornecedores))

    # ========== TABS ==========
    tab1, tab2, tab3 = st.tabs(["Titulos", "Por Fornecedor", "Exportar"])

    with tab1:
        _render_tabela_titulos(df_filtrado, cores, hoje)

    with tab2:
        _render_por_fornecedor(df_filtrado, cores)

    with tab3:
        _render_exportar(df_filtrado, hoje)


def _aplicar_filtros(df):
    """Aplica todos os filtros selecionados"""
    df_filtrado = df.copy()

    # Status
    if st.session_state.get('det_status'):
        df_filtrado = df_filtrado[df_filtrado['STATUS'].isin(st.session_state.det_status)]

    # Filial
    if st.session_state.get('det_filial'):
        df_filtrado = df_filtrado[df_filtrado['NOME_FILIAL'].isin(st.session_state.det_filial)]

    # Categoria
    if st.session_state.get('det_categoria'):
        df_filtrado = df_filtrado[df_filtrado['DESCRICAO'].isin(st.session_state.det_categoria)]

    # Forma de pagamento
    if st.session_state.get('det_forma') and 'DESCRICAO_FORMA_PAGAMENTO' in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado['DESCRICAO_FORMA_PAGAMENTO'].isin(st.session_state.det_forma)]

    # Busca fornecedor
    busca_forn = st.session_state.get('det_busca_forn', '')
    if busca_forn:
        df_filtrado = df_filtrado[
            df_filtrado['NOME_FORNECEDOR'].str.contains(busca_forn, case=False, na=False)
        ]

    # Busca numero/documento
    busca_num = st.session_state.get('det_busca_num', '')
    if busca_num:
        mask = pd.Series([False] * len(df_filtrado), index=df_filtrado.index)
        if 'NUMERO' in df_filtrado.columns:
            mask |= df_filtrado['NUMERO'].astype(str).str.contains(busca_num, case=False, na=False)
        if 'DOCUMENTO' in df_filtrado.columns:
            mask |= df_filtrado['DOCUMENTO'].astype(str).str.contains(busca_num, case=False, na=False)
        df_filtrado = df_filtrado[mask]

    # Tipo (saldo)
    filtro_tipo = st.session_state.get('det_tipo', 'Todos')
    if filtro_tipo == 'Com Saldo':
        df_filtrado = df_filtrado[df_filtrado['SALDO'] > 0]
    elif filtro_tipo == 'Pagos':
        df_filtrado = df_filtrado[df_filtrado['SALDO'] == 0]

    # Tipo documento
    filtro_tipo_doc = st.session_state.get('det_tipo_doc', 'Todos')
    if filtro_tipo_doc != 'Todos' and 'TIPO_DOC' in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado['TIPO_DOC'] == filtro_tipo_doc]

    # Valor minimo
    valor_min = st.session_state.get('det_valor_min', 0)
    if valor_min > 0:
        df_filtrado = df_filtrado[df_filtrado['VALOR_ORIGINAL'] >= valor_min]

    # Valor maximo
    valor_max = st.session_state.get('det_valor_max', 0)
    if valor_max > 0:
        df_filtrado = df_filtrado[df_filtrado['VALOR_ORIGINAL'] <= valor_max]

    # Vencimento de
    venc_inicio = st.session_state.get('det_venc_inicio')
    if venc_inicio:
        df_filtrado = df_filtrado[df_filtrado['VENCIMENTO'].dt.date >= venc_inicio]

    # Vencimento ate
    venc_fim = st.session_state.get('det_venc_fim')
    if venc_fim:
        df_filtrado = df_filtrado[df_filtrado['VENCIMENTO'].dt.date <= venc_fim]

    return df_filtrado.sort_values('VENCIMENTO', ascending=True)


def _render_tabela_titulos(df_filtrado, cores, hoje):
    """Tabela completa de titulos"""

    if len(df_filtrado) == 0:
        st.info("Nenhum titulo encontrado com os filtros selecionados.")
        return

    # Controles
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        ordem = st.radio(
            "Ordenar por:",
            ["Vencimento", "Emissao", "Maior Valor", "Menor Valor", "Fornecedor", "Maior Atraso"],
            horizontal=True,
            key="det_ordem"
        )

    with col2:
        limite = st.selectbox("Exibir", ["100", "500", "1000", "Todos"], key="det_limite")

    with col3:
        colunas_extra = st.checkbox("Mais colunas", value=False, key="det_mais_cols")

    # Aplicar ordenacao
    ordem_map = {
        "Vencimento": ("VENCIMENTO", True),
        "Emissao": ("EMISSAO", False),
        "Maior Valor": ("VALOR_ORIGINAL", False),
        "Menor Valor": ("VALOR_ORIGINAL", True),
        "Fornecedor": ("NOME_FORNECEDOR", True),
        "Maior Atraso": ("DIAS_ATRASO", False)
    }
    col_ordem, asc = ordem_map[ordem]
    df_ord = df_filtrado.sort_values(col_ordem, ascending=asc, na_position='last')

    # Aplicar limite
    if limite != "Todos":
        df_ord = df_ord.head(int(limite))

    # Colunas a exibir
    if colunas_extra:
        colunas_exibir = [
            'NOME_FILIAL', 'NOME_FORNECEDOR', 'DESCRICAO', 'TIPO',
            'EMISSAO', 'VENCIMENTO', 'DT_BAIXA',
            'VALOR_ORIGINAL', 'SALDO', 'STATUS',
            'DIAS_ATRASO', 'DIAS_PARA_PAGAR', 'DIAS_ATRASO_PGTO',
            'DESCRICAO_FORMA_PAGAMENTO'
        ]
    else:
        colunas_exibir = [
            'NOME_FILIAL', 'NOME_FORNECEDOR',
            'EMISSAO', 'VENCIMENTO', 'DT_BAIXA',
            'VALOR_ORIGINAL', 'SALDO', 'STATUS', 'DIAS_ATRASO'
        ]

    colunas_disponiveis = [c for c in colunas_exibir if c in df_ord.columns]
    df_show = df_ord[colunas_disponiveis].copy()

    # Formatar datas
    for col in ['EMISSAO', 'VENCIMENTO', 'DT_BAIXA']:
        if col in df_show.columns:
            df_show[col] = pd.to_datetime(df_show[col], errors='coerce').dt.strftime('%d/%m/%Y')
            df_show[col] = df_show[col].fillna('-')

    # Formatar valores
    df_show['VALOR_ORIGINAL'] = df_show['VALOR_ORIGINAL'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['SALDO'] = df_show['SALDO'].apply(lambda x: formatar_moeda(x, completo=True))

    # Formatar dias
    def fmt_dias(d):
        if pd.isna(d) or d == 0:
            return '-'
        return f"{int(d)}d"

    def fmt_atraso_pgto(d):
        if pd.isna(d):
            return '-'
        d = int(d)
        if d < 0:
            return f"{abs(d)}d antecip."
        elif d == 0:
            return "No prazo"
        else:
            return f"{d}d atraso"

    if 'DIAS_ATRASO' in df_show.columns:
        df_show['DIAS_ATRASO'] = df_show['DIAS_ATRASO'].apply(fmt_dias)

    if 'DIAS_PARA_PAGAR' in df_show.columns:
        df_show['DIAS_PARA_PAGAR'] = df_show['DIAS_PARA_PAGAR'].apply(fmt_dias)

    if 'DIAS_ATRASO_PGTO' in df_show.columns:
        df_show['DIAS_ATRASO_PGTO'] = df_show['DIAS_ATRASO_PGTO'].apply(fmt_atraso_pgto)

    # Renomear colunas
    nomes = {
        'NOME_FILIAL': 'Filial',
        'NOME_FORNECEDOR': 'Fornecedor',
        'DESCRICAO': 'Categoria',
        'TIPO': 'Tipo',
        'EMISSAO': 'Emissao',
        'VENCIMENTO': 'Vencimento',
        'DT_BAIXA': 'Dt Pagto',
        'VALOR_ORIGINAL': 'Valor',
        'SALDO': 'Saldo',
        'STATUS': 'Status',
        'DIAS_ATRASO': 'Atraso',
        'DIAS_PARA_PAGAR': 'Dias p/ Pagar',
        'DIAS_ATRASO_PGTO': 'Pgto vs Venc',
        'DESCRICAO_FORMA_PAGAMENTO': 'Forma Pgto'
    }
    df_show.columns = [nomes.get(c, c) for c in df_show.columns]

    # Truncar nome fornecedor
    if 'Fornecedor' in df_show.columns:
        df_show['Fornecedor'] = df_show['Fornecedor'].astype(str).str[:30]

    st.dataframe(df_show, use_container_width=True, hide_index=True, height=500)
    st.caption(f"Exibindo {len(df_show)} de {len(df_filtrado)} titulos")


def _render_por_fornecedor(df_filtrado, cores):
    """Agrupamento por fornecedor"""

    if len(df_filtrado) == 0:
        st.info("Nenhum titulo encontrado.")
        return

    st.markdown("##### Resumo por Fornecedor")

    # Agrupar
    df_grp = df_filtrado.groupby('NOME_FORNECEDOR').agg({
        'VALOR_ORIGINAL': ['count', 'sum'],
        'SALDO': 'sum',
        'DIAS_ATRASO': 'mean'
    }).reset_index()
    df_grp.columns = ['Fornecedor', 'Qtd', 'Total', 'Saldo', 'Atraso Medio']

    # Ordenacao
    col1, col2 = st.columns([3, 1])
    with col1:
        ordem = st.radio(
            "Ordenar por:",
            ["Maior Total", "Maior Saldo", "Mais Titulos", "Maior Atraso"],
            horizontal=True,
            key="det_forn_ordem"
        )
    with col2:
        limite = st.selectbox("Exibir", ["50", "100", "Todos"], key="det_forn_limite")

    # Aplicar ordenacao
    ordem_map = {
        "Maior Total": ("Total", False),
        "Maior Saldo": ("Saldo", False),
        "Mais Titulos": ("Qtd", False),
        "Maior Atraso": ("Atraso Medio", False)
    }
    col_ord, asc = ordem_map[ordem]
    df_grp = df_grp.sort_values(col_ord, ascending=asc, na_position='last')

    if limite != "Todos":
        df_grp = df_grp.head(int(limite))

    # Formatar
    df_show = df_grp.copy()
    df_show['Total'] = df_show['Total'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Saldo'] = df_show['Saldo'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Atraso Medio'] = df_show['Atraso Medio'].apply(lambda x: f"{x:.0f}d" if pd.notna(x) and x > 0 else '-')
    df_show['Fornecedor'] = df_show['Fornecedor'].str[:40]

    st.dataframe(df_show, use_container_width=True, hide_index=True, height=450)
    st.caption(f"Total: {len(df_grp)} fornecedores")


def _render_exportar(df_filtrado, hoje):
    """Opcoes de exportacao"""

    st.markdown("##### Exportar Dados")

    if len(df_filtrado) == 0:
        st.info("Nenhum dado para exportar.")
        return

    # Resumo dos dados
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Titulos", formatar_numero(len(df_filtrado)))
    col2.metric("Valor Total", formatar_moeda(df_filtrado['VALOR_ORIGINAL'].sum()))
    col3.metric("Saldo", formatar_moeda(df_filtrado['SALDO'].sum()))
    col4.metric("Fornecedores", formatar_numero(df_filtrado['NOME_FORNECEDOR'].nunique()))

    st.markdown("---")

    # Opcoes de exportacao
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("###### Dados Filtrados")
        st.caption(f"{len(df_filtrado)} titulos")
        st.download_button(
            label="Baixar Excel",
            data=to_excel(df_filtrado),
            file_name=f"titulos_{hoje.strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    with col2:
        st.markdown("###### Apenas Vencidos")
        df_venc = df_filtrado[df_filtrado['STATUS'] == 'Vencido']
        st.caption(f"{len(df_venc)} titulos")
        if len(df_venc) > 0:
            st.download_button(
                label="Baixar Vencidos",
                data=to_excel(df_venc),
                file_name=f"vencidos_{hoje.strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        else:
            st.info("Sem vencidos")

    with col3:
        st.markdown("###### Apenas Pendentes")
        df_pend = df_filtrado[df_filtrado['SALDO'] > 0]
        st.caption(f"{len(df_pend)} titulos")
        if len(df_pend) > 0:
            st.download_button(
                label="Baixar Pendentes",
                data=to_excel(df_pend),
                file_name=f"pendentes_{hoje.strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        else:
            st.info("Sem pendentes")

    st.markdown("---")

    # Detalhes dos campos
    with st.expander("Campos incluidos na exportacao"):
        st.markdown("""
        **Identificacao:** Filial, Fornecedor, Categoria, Tipo, Numero

        **Datas:** Emissao, Vencimento, Data Pagamento

        **Valores:** Valor Original, Saldo, Juros, Multa, Desconto

        **Status:** Status, Dias de Atraso, Dias para Pagar

        **Pagamento:** Forma de Pagamento, Banco
        """)
