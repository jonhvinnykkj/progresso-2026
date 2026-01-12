"""
Aba Adiantamentos - Análise detalhada de adiantamentos a clientes - Contas a Receber
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from config.theme import get_cores
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero


def render_adiantamentos_receber(df_adiant, df_baixas):
    """Renderiza a aba de Adiantamentos a Receber"""
    cores = get_cores()
    hoje = datetime.now()

    st.markdown("### Adiantamentos a Clientes")
    st.caption("Controle de adiantamentos recebidos de clientes e suas respectivas baixas/compensações")

    # Verificar dados
    if len(df_adiant) == 0:
        st.warning("Nenhum dado de adiantamentos disponível.")
        return

    # Preparar dados
    df_ad = df_adiant.copy()
    df_bx = df_baixas.copy() if len(df_baixas) > 0 else pd.DataFrame()

    # Converter datas
    for col in ['EMISSAO', 'VENCIMENTO']:
        if col in df_ad.columns:
            df_ad[col] = pd.to_datetime(df_ad[col], errors='coerce')
    if len(df_bx) > 0 and 'DT_BAIXA' in df_bx.columns:
        df_bx['DT_BAIXA'] = pd.to_datetime(df_bx['DT_BAIXA'], errors='coerce')

    # Calcular totais gerais
    total_adiantado = df_ad['VALOR_ORIGINAL'].sum()
    total_baixado = df_bx['VALOR_BAIXA'].sum() if len(df_bx) > 0 and 'VALOR_BAIXA' in df_bx.columns else 0
    saldo_pendente = df_ad['SALDO'].sum() if 'SALDO' in df_ad.columns else total_adiantado - total_baixado

    qtd_adiantamentos = len(df_ad)
    qtd_baixas = len(df_bx)

    # Adiantamentos com saldo pendente
    df_pendentes = df_ad[df_ad['SALDO'] > 0] if 'SALDO' in df_ad.columns else df_ad
    qtd_pendentes = len(df_pendentes)

    # Adiantamentos quitados
    df_quitados = df_ad[df_ad['SALDO'] == 0] if 'SALDO' in df_ad.columns else pd.DataFrame()
    qtd_quitados = len(df_quitados)

    pct_quitado = (qtd_quitados / qtd_adiantamentos * 100) if qtd_adiantamentos > 0 else 0

    # ========== SEÇÃO 1: RESUMO GERAL ==========
    st.markdown("#### Resumo Geral")

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric(
        "Total Adiantado",
        formatar_moeda(total_adiantado),
        help="Soma de todos os adiantamentos recebidos"
    )

    col2.metric(
        "Total Baixado",
        formatar_moeda(total_baixado),
        help="Soma de todas as baixas/compensações realizadas"
    )

    col3.metric(
        "Saldo Pendente",
        formatar_moeda(saldo_pendente),
        delta=f"{(saldo_pendente/total_adiantado*100):.1f}% do total" if total_adiantado > 0 else "0%",
        delta_color="inverse" if saldo_pendente > 0 else "normal",
        help="Valor ainda não compensado"
    )

    col4.metric(
        "Adiantamentos",
        formatar_numero(qtd_adiantamentos),
        delta=f"{qtd_pendentes} pendentes",
        delta_color="off",
        help="Quantidade total de adiantamentos"
    )

    col5.metric(
        "Taxa de Quitação",
        f"{pct_quitado:.1f}%",
        delta=f"{qtd_quitados} quitados",
        delta_color="normal" if pct_quitado >= 50 else "off",
        help="Percentual de adiantamentos já compensados"
    )

    st.markdown("---")

    # ========== SEÇÃO 2: VISÃO ANALÍTICA ==========
    st.markdown("#### Análise Detalhada")

    tab1, tab2, tab3, tab4 = st.tabs([
        "Por Cliente",
        "Por Filial",
        "Pendentes",
        "Baixas Realizadas"
    ])

    with tab1:
        _render_por_cliente(df_ad, df_bx, cores)

    with tab2:
        _render_por_filial(df_ad, cores)

    with tab3:
        _render_pendentes(df_pendentes, cores, hoje)

    with tab4:
        _render_baixas(df_bx, cores)


def _render_por_cliente(df_ad, df_bx, cores):
    """Análise por cliente"""

    # Verificar qual coluna usar (pode ser FORNECEDOR ou CLIENTE dependendo da estrutura)
    col_cliente = 'NOME_FORNECEDOR' if 'NOME_FORNECEDOR' in df_ad.columns else 'NOME_CLIENTE'
    col_id = 'FORNECEDOR' if 'FORNECEDOR' in df_ad.columns else 'CLIENTE'

    df_cli = df_ad.groupby(col_cliente).agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        col_id: 'count'
    }).reset_index()
    df_cli.columns = ['Cliente', 'Total_Adiantado', 'Saldo_Pendente', 'Qtd_Adiant']

    df_cli['Valor_Baixado'] = df_cli['Total_Adiantado'] - df_cli['Saldo_Pendente']
    df_cli['Pct_Quitado'] = ((df_cli['Valor_Baixado'] / df_cli['Total_Adiantado']) * 100).fillna(0).round(1)
    df_cli = df_cli.sort_values('Saldo_Pendente', ascending=False)

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("##### Top 15 Clientes - Saldo Pendente")

        df_top = df_cli.head(15)

        fig = go.Figure()

        fig.add_trace(go.Bar(
            y=df_top['Cliente'].str[:25],
            x=df_top['Valor_Baixado'],
            orientation='h',
            name='Já Compensado',
            marker_color=cores['primaria'],
            text=[formatar_moeda(v) for v in df_top['Valor_Baixado']],
            textposition='inside',
            textfont=dict(size=9, color='white')
        ))

        fig.add_trace(go.Bar(
            y=df_top['Cliente'].str[:25],
            x=df_top['Saldo_Pendente'],
            orientation='h',
            name='Pendente',
            marker_color=cores['alerta'],
            text=[formatar_moeda(v) for v in df_top['Saldo_Pendente']],
            textposition='inside',
            textfont=dict(size=9, color='white')
        ))

        fig.update_layout(
            criar_layout(400, barmode='stack'),
            yaxis={'autorange': 'reversed'},
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
            margin=dict(l=10, r=10, t=30, b=10)
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("##### Status por Cliente")

        total_clientes = len(df_cli)
        cli_quitados = len(df_cli[df_cli['Saldo_Pendente'] == 0])
        cli_pendentes = total_clientes - cli_quitados

        st.metric("Total de Clientes", total_clientes)
        st.metric("Com Saldo Pendente", cli_pendentes, delta_color="inverse")
        st.metric("Totalmente Quitados", cli_quitados, delta_color="normal")

        st.markdown("---")

        st.markdown("**Maiores Pendentes:**")
        for _, row in df_cli.head(5).iterrows():
            nome = row['Cliente'][:20]
            valor = formatar_moeda(row['Saldo_Pendente'])
            pct = row['Pct_Quitado']

            if pct >= 80:
                icone = "🟢"
            elif pct >= 50:
                icone = "🟡"
            else:
                icone = "🔴"

            st.markdown(f"{icone} **{nome}**")
            st.caption(f"Pendente: {valor} ({pct:.0f}% quitado)")

    # Tabela completa
    st.markdown("##### Tabela Completa por Cliente")

    def get_status(pct):
        if pct >= 100:
            return 'Quitado'
        elif pct >= 80:
            return 'Quase lá'
        elif pct >= 50:
            return 'Parcial'
        elif pct > 0:
            return 'Iniciado'
        else:
            return 'Pendente'

    df_cli['Status'] = df_cli['Pct_Quitado'].apply(get_status)

    df_exibir = pd.DataFrame({
        'Cliente': df_cli['Cliente'],
        'Total Adiantado': df_cli['Total_Adiantado'].apply(lambda x: formatar_moeda(x, completo=True)),
        'Já Compensado': df_cli['Valor_Baixado'].apply(lambda x: formatar_moeda(x, completo=True)),
        'Saldo Pendente': df_cli['Saldo_Pendente'].apply(lambda x: formatar_moeda(x, completo=True)),
        'Qtd Adiant.': df_cli['Qtd_Adiant'],
        '% Quitado': df_cli['Pct_Quitado'],
        'Status': df_cli['Status']
    })

    st.dataframe(
        df_exibir,
        use_container_width=True,
        hide_index=True,
        height=400,
        column_config={
            '% Quitado': st.column_config.ProgressColumn(
                '% Quitado',
                format='%.0f%%',
                min_value=0,
                max_value=100
            )
        }
    )


def _render_por_filial(df_ad, cores):
    """Análise por filial"""

    col_id = 'FORNECEDOR' if 'FORNECEDOR' in df_ad.columns else 'CLIENTE'

    df_filial = df_ad.groupby('NOME_FILIAL').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        col_id: 'count'
    }).reset_index()
    df_filial.columns = ['Filial', 'Total_Adiantado', 'Saldo_Pendente', 'Qtd_Adiant']
    df_filial['Valor_Baixado'] = df_filial['Total_Adiantado'] - df_filial['Saldo_Pendente']
    df_filial['Pct_Quitado'] = ((df_filial['Valor_Baixado'] / df_filial['Total_Adiantado']) * 100).fillna(0).round(1)
    df_filial = df_filial.sort_values('Total_Adiantado', ascending=False)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Adiantamentos por Filial")

        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=df_filial['Filial'],
            y=df_filial['Valor_Baixado'],
            name='Compensado',
            marker_color=cores['primaria'],
            text=[formatar_moeda(v) for v in df_filial['Valor_Baixado']],
            textposition='outside',
            textfont=dict(size=9)
        ))

        fig.add_trace(go.Bar(
            x=df_filial['Filial'],
            y=df_filial['Saldo_Pendente'],
            name='Pendente',
            marker_color=cores['alerta'],
            text=[formatar_moeda(v) for v in df_filial['Saldo_Pendente']],
            textposition='outside',
            textfont=dict(size=9)
        ))

        fig.update_layout(
            criar_layout(300, barmode='group'),
            xaxis_tickangle=-45,
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
            margin=dict(l=10, r=10, t=30, b=80)
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("##### Taxa de Quitação por Filial")

        df_filial_ord = df_filial.sort_values('Pct_Quitado', ascending=True)

        fig = go.Figure()

        cores_barras = [cores['sucesso'] if p >= 80 else cores['alerta'] if p >= 50 else cores['perigo']
                       for p in df_filial_ord['Pct_Quitado']]

        fig.add_trace(go.Bar(
            y=df_filial_ord['Filial'],
            x=df_filial_ord['Pct_Quitado'],
            orientation='h',
            marker_color=cores_barras,
            text=[f"{p:.0f}%" for p in df_filial_ord['Pct_Quitado']],
            textposition='outside'
        ))

        fig.add_vline(x=80, line_dash="dash", line_color="gray",
                     annotation_text="Meta 80%", annotation_position="top")

        fig.update_layout(
            criar_layout(300),
            xaxis=dict(range=[0, 105], title='% Quitado'),
            margin=dict(l=10, r=10, t=30, b=10)
        )

        st.plotly_chart(fig, use_container_width=True)

    # Tabela resumo
    st.markdown("##### Resumo por Filial")

    df_exibir = pd.DataFrame({
        'Filial': df_filial['Filial'],
        'Total Adiantado': df_filial['Total_Adiantado'].apply(lambda x: formatar_moeda(x, completo=True)),
        'Compensado': df_filial['Valor_Baixado'].apply(lambda x: formatar_moeda(x, completo=True)),
        'Pendente': df_filial['Saldo_Pendente'].apply(lambda x: formatar_moeda(x, completo=True)),
        'Qtd Adiantamentos': df_filial['Qtd_Adiant'],
        '% Quitado': df_filial['Pct_Quitado']
    })

    st.dataframe(
        df_exibir,
        use_container_width=True,
        hide_index=True,
        column_config={
            '% Quitado': st.column_config.ProgressColumn(
                '% Quitado',
                format='%.0f%%',
                min_value=0,
                max_value=100
            )
        }
    )


def _render_pendentes(df_pendentes, cores, hoje):
    """Lista de adiantamentos pendentes"""

    if len(df_pendentes) == 0:
        st.success("Todos os adiantamentos foram compensados!")
        return

    total_pendente = df_pendentes['SALDO'].sum()
    qtd_pendente = len(df_pendentes)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Pendente", formatar_moeda(total_pendente))
    col2.metric("Quantidade", formatar_numero(qtd_pendente))
    col3.metric("Ticket Médio", formatar_moeda(total_pendente / qtd_pendente) if qtd_pendente > 0 else "R$ 0")

    st.markdown("---")

    col_cliente = 'NOME_FORNECEDOR' if 'NOME_FORNECEDOR' in df_pendentes.columns else 'NOME_CLIENTE'

    # Filtros
    col1, col2, col3 = st.columns(3)

    with col1:
        filiais = ['Todas'] + sorted(df_pendentes['NOME_FILIAL'].dropna().unique().tolist())
        filtro_filial = st.selectbox("Filtrar por Filial", filiais, key="pend_filial_rec")

    with col2:
        ordenar = st.selectbox("Ordenar por",
                              ["Maior Saldo", "Menor Saldo", "Mais Antigo", "Cliente A-Z"],
                              key="pend_ordem_rec")

    with col3:
        limite = st.selectbox("Exibir", ["50 primeiros", "100 primeiros", "Todos"], key="pend_limite_rec")

    df_show = df_pendentes.copy()

    if filtro_filial != 'Todas':
        df_show = df_show[df_show['NOME_FILIAL'] == filtro_filial]

    if ordenar == "Maior Saldo":
        df_show = df_show.sort_values('SALDO', ascending=False)
    elif ordenar == "Menor Saldo":
        df_show = df_show.sort_values('SALDO', ascending=True)
    elif ordenar == "Mais Antigo":
        df_show = df_show.sort_values('EMISSAO', ascending=True)
    else:
        df_show = df_show.sort_values(col_cliente)

    if limite == "50 primeiros":
        df_show = df_show.head(50)
    elif limite == "100 primeiros":
        df_show = df_show.head(100)

    if 'EMISSAO' in df_show.columns:
        df_show['DIAS_PENDENTE'] = (hoje - df_show['EMISSAO']).dt.days

    colunas = ['NOME_FILIAL', col_cliente, 'EMISSAO', 'VALOR_ORIGINAL', 'SALDO']
    if 'DIAS_PENDENTE' in df_show.columns:
        colunas.append('DIAS_PENDENTE')
    if 'HISTORICO' in df_show.columns:
        colunas.append('HISTORICO')

    df_exibir = df_show[colunas].copy()

    rename_map = {
        'NOME_FILIAL': 'Filial',
        col_cliente: 'Cliente',
        'EMISSAO': 'Emissão',
        'VALOR_ORIGINAL': 'Valor Original',
        'SALDO': 'Saldo Pendente',
        'DIAS_PENDENTE': 'Dias Pendente',
        'HISTORICO': 'Motivo'
    }
    df_exibir = df_exibir.rename(columns=rename_map)

    if 'Emissão' in df_exibir.columns:
        df_exibir['Emissão'] = df_exibir['Emissão'].dt.strftime('%d/%m/%Y')

    df_exibir['Valor Original'] = df_exibir['Valor Original'].apply(lambda x: formatar_moeda(x, completo=True))
    df_exibir['Saldo Pendente'] = df_exibir['Saldo Pendente'].apply(lambda x: formatar_moeda(x, completo=True))

    if 'Motivo' in df_exibir.columns:
        df_exibir['Motivo'] = df_exibir['Motivo'].astype(str).str[:50]

    st.dataframe(df_exibir, use_container_width=True, hide_index=True, height=500)
    st.caption(f"Exibindo {len(df_exibir)} de {len(df_pendentes)} adiantamentos pendentes")


def _render_baixas(df_bx, cores):
    """Lista de baixas realizadas"""

    if len(df_bx) == 0:
        st.info("Nenhuma baixa registrada.")
        return

    total_baixas = df_bx['VALOR_BAIXA'].sum() if 'VALOR_BAIXA' in df_bx.columns else 0
    qtd_baixas = len(df_bx)

    prazo_medio = 0
    if 'DIAS_ATE_BAIXA' in df_bx.columns:
        prazo_medio = df_bx['DIAS_ATE_BAIXA'].mean()
    elif 'DIF_DIAS_EMIS_BAIXA' in df_bx.columns:
        prazo_medio = pd.to_numeric(df_bx['DIF_DIAS_EMIS_BAIXA'], errors='coerce').mean()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Baixado", formatar_moeda(total_baixas))
    col2.metric("Quantidade de Baixas", formatar_numero(qtd_baixas))
    col3.metric("Valor Médio", formatar_moeda(total_baixas / qtd_baixas) if qtd_baixas > 0 else "R$ 0")
    col4.metric("Prazo Médio Compensação", f"{prazo_medio:.0f} dias" if prazo_medio > 0 else "N/A",
                help="Dias médios entre adiantamento e baixa")

    st.markdown("---")

    if 'DT_BAIXA' in df_bx.columns:
        st.markdown("##### Evolução Mensal das Baixas")

        df_bx_temp = df_bx.copy()
        df_bx_temp['MES_ANO'] = df_bx_temp['DT_BAIXA'].dt.to_period('M')

        col_id = 'FORNECEDOR' if 'FORNECEDOR' in df_bx.columns else 'CLIENTE'

        df_mensal = df_bx_temp.groupby('MES_ANO').agg({
            'VALOR_BAIXA': 'sum',
            col_id: 'count'
        }).reset_index()
        df_mensal.columns = ['Período', 'Valor', 'Qtd']
        df_mensal['Período'] = df_mensal['Período'].astype(str)
        df_mensal = df_mensal.tail(12)

        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=df_mensal['Período'],
            y=df_mensal['Valor'],
            marker_color=cores['primaria'],
            text=[formatar_moeda(v) for v in df_mensal['Valor']],
            textposition='outside',
            textfont=dict(size=9)
        ))

        fig.update_layout(
            criar_layout(250),
            xaxis_tickangle=-45,
            margin=dict(l=10, r=10, t=10, b=60)
        )

        st.plotly_chart(fig, use_container_width=True)

    col_cliente = 'NOME_CLIENTE' if 'NOME_CLIENTE' in df_bx.columns else 'NOME_FORNECEDOR'
    col_id = 'CLIENTE' if 'CLIENTE' in df_bx.columns else 'FORNECEDOR'

    # Filtros
    col1, col2 = st.columns(2)

    with col1:
        if 'NOME_FILIAL' in df_bx.columns:
            filiais = ['Todas'] + sorted(df_bx['NOME_FILIAL'].dropna().unique().tolist())
            filtro_filial = st.selectbox("Filtrar por Filial", filiais, key="baixa_filial_rec")
        else:
            filtro_filial = 'Todas'

    with col2:
        ordenar = st.selectbox("Ordenar por",
                              ["Mais Recente", "Maior Valor", "Cliente A-Z"],
                              key="baixa_ordem_rec")

    df_show = df_bx.copy()

    if filtro_filial != 'Todas' and 'NOME_FILIAL' in df_show.columns:
        df_show = df_show[df_show['NOME_FILIAL'] == filtro_filial]

    if ordenar == "Mais Recente" and 'DT_BAIXA' in df_show.columns:
        df_show = df_show.sort_values('DT_BAIXA', ascending=False)
    elif ordenar == "Maior Valor" and 'VALOR_BAIXA' in df_show.columns:
        df_show = df_show.sort_values('VALOR_BAIXA', ascending=False)
    elif col_cliente in df_show.columns:
        df_show = df_show.sort_values(col_cliente)

    df_show = df_show.head(100)

    colunas_disponiveis = df_show.columns.tolist()
    colunas = []
    rename_map = {}

    if 'NOME_FILIAL' in colunas_disponiveis:
        colunas.append('NOME_FILIAL')
        rename_map['NOME_FILIAL'] = 'Filial'

    if col_cliente in colunas_disponiveis:
        colunas.append(col_cliente)
        rename_map[col_cliente] = 'Cliente'

    if 'DT_BAIXA' in colunas_disponiveis:
        colunas.append('DT_BAIXA')
        rename_map['DT_BAIXA'] = 'Data Baixa'

    if 'VALOR_BAIXA' in colunas_disponiveis:
        colunas.append('VALOR_BAIXA')
        rename_map['VALOR_BAIXA'] = 'Valor Baixa'

    if 'HISTORICO' in colunas_disponiveis:
        colunas.append('HISTORICO')
        rename_map['HISTORICO'] = 'Motivo'

    if 'DIAS_ATE_BAIXA' in colunas_disponiveis:
        colunas.append('DIAS_ATE_BAIXA')
        rename_map['DIAS_ATE_BAIXA'] = 'Dias até Baixa'
    elif 'DIF_DIAS_EMIS_BAIXA' in colunas_disponiveis:
        colunas.append('DIF_DIAS_EMIS_BAIXA')
        rename_map['DIF_DIAS_EMIS_BAIXA'] = 'Dias até Baixa'

    df_exibir = df_show[colunas].copy()
    df_exibir = df_exibir.rename(columns=rename_map)

    if 'Data Baixa' in df_exibir.columns:
        df_exibir['Data Baixa'] = pd.to_datetime(df_exibir['Data Baixa'], errors='coerce').dt.strftime('%d/%m/%Y')

    if 'Valor Baixa' in df_exibir.columns:
        df_exibir['Valor Baixa'] = df_exibir['Valor Baixa'].apply(lambda x: formatar_moeda(x, completo=True))

    if 'Motivo' in df_exibir.columns:
        df_exibir['Motivo'] = df_exibir['Motivo'].astype(str).str[:50]

    if 'Dias até Baixa' in df_exibir.columns:
        df_exibir['Dias até Baixa'] = pd.to_numeric(df_exibir['Dias até Baixa'], errors='coerce').fillna(0).astype(int)

    st.dataframe(df_exibir, use_container_width=True, hide_index=True, height=400)
    st.caption(f"Exibindo {len(df_exibir)} de {len(df_bx)} baixas")
