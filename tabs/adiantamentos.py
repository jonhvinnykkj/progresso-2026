"""
Aba Adiantamentos - Controle de adiantamentos e compensacoes
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from config.theme import get_cores
from config.settings import INTERCOMPANY_PATTERNS
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero


def render_adiantamentos(df_adiant, df_baixas):
    """Renderiza a aba de Adiantamentos"""
    cores = get_cores()
    hoje = datetime.now()

    if len(df_adiant) == 0:
        st.warning("Nenhum dado de adiantamentos disponivel.")
        return

    # Preparar dados - REMOVER INTERCOMPANY
    df_ad = df_adiant.copy()

    # Filtrar para remover fornecedores intercompany
    if 'NOME_FORNECEDOR' in df_ad.columns:
        mask_ic = df_ad['NOME_FORNECEDOR'].str.upper().str.contains(
            '|'.join(INTERCOMPANY_PATTERNS), na=False, regex=True
        )
        df_ad = df_ad[~mask_ic].copy()

    df_bx = df_baixas.copy() if len(df_baixas) > 0 else pd.DataFrame()

    # Remover intercompany das baixas tambem
    if len(df_bx) > 0 and 'NOME_FORNECEDOR' in df_bx.columns:
        mask_ic_bx = df_bx['NOME_FORNECEDOR'].str.upper().str.contains(
            '|'.join(INTERCOMPANY_PATTERNS), na=False, regex=True
        )
        df_bx = df_bx[~mask_ic_bx].copy()

    # Converter datas
    if 'EMISSAO' in df_ad.columns:
        df_ad['EMISSAO'] = pd.to_datetime(df_ad['EMISSAO'], errors='coerce')
    if len(df_bx) > 0 and 'DT_BAIXA' in df_bx.columns:
        df_bx['DT_BAIXA'] = pd.to_datetime(df_bx['DT_BAIXA'], errors='coerce')
    if len(df_bx) > 0 and 'EMISSAO' in df_bx.columns:
        df_bx['EMISSAO'] = pd.to_datetime(df_bx['EMISSAO'], errors='coerce')

    # Calcular totais
    total_adiantado = df_ad['VALOR_ORIGINAL'].sum()
    total_compensado = df_bx['VALOR_BAIXA'].sum() if len(df_bx) > 0 and 'VALOR_BAIXA' in df_bx.columns else 0
    saldo_pendente = df_ad['SALDO'].sum() if 'SALDO' in df_ad.columns else total_adiantado - total_compensado

    # Prazo medio de compensacao
    prazo_medio = 0
    if len(df_bx) > 0:
        if 'DIF_DIAS_EMIS_BAIXA' in df_bx.columns:
            prazo_medio = pd.to_numeric(df_bx['DIF_DIAS_EMIS_BAIXA'], errors='coerce').mean()
        elif 'DIAS_ATE_BAIXA' in df_bx.columns:
            prazo_medio = df_bx['DIAS_ATE_BAIXA'].mean()

    # ========== KPIs ==========
    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric(
        "Total Adiantado",
        formatar_moeda(total_adiantado),
        f"{len(df_ad)} adiantamentos"
    )

    col2.metric(
        "Total Compensado",
        formatar_moeda(total_compensado),
        f"{len(df_bx)} compensacoes"
    )

    col3.metric(
        "Saldo Pendente",
        formatar_moeda(saldo_pendente),
        f"{(saldo_pendente/total_adiantado*100):.1f}% do total" if total_adiantado > 0 else "0%"
    )

    pct_compensado = ((total_adiantado - saldo_pendente) / total_adiantado * 100) if total_adiantado > 0 else 0
    col4.metric(
        "Taxa Compensacao",
        f"{pct_compensado:.1f}%"
    )

    col5.metric(
        "Prazo Medio",
        f"{prazo_medio:.0f} dias",
        "entre adiantamento e compensacao"
    )

    st.divider()

    # ========== TABS ==========
    tab1, tab2, tab3, tab4 = st.tabs([
        "Adiantamentos",
        "Compensacoes",
        "Adto x NF",
        "Por Fornecedor"
    ])

    with tab1:
        _render_adiantamentos(df_ad, cores, hoje)

    with tab2:
        _render_compensacoes(df_bx, cores)

    with tab3:
        _render_adto_nf(df_ad, df_bx, cores)

    with tab4:
        _render_por_fornecedor(df_ad, df_bx, cores)


def _render_adiantamentos(df_ad, cores, hoje):
    """Lista de adiantamentos"""

    st.markdown("##### Adiantamentos Concedidos")

    # Separar pendentes e quitados
    df_pendentes = df_ad[df_ad['SALDO'] > 0] if 'SALDO' in df_ad.columns else df_ad
    df_quitados = df_ad[df_ad['SALDO'] == 0] if 'SALDO' in df_ad.columns else pd.DataFrame()

    # Metricas
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Adiantamentos", len(df_ad))
    col2.metric("Pendentes", len(df_pendentes), f"{formatar_moeda(df_pendentes['SALDO'].sum())}")
    col3.metric("Quitados", len(df_quitados))

    st.markdown("---")

    # Filtros
    col1, col2, col3 = st.columns(3)

    with col1:
        filtro_tipo = st.radio("Mostrar", ["Pendentes", "Quitados", "Todos"], horizontal=True, key="ad_tipo")

    with col2:
        if 'NOME_FILIAL' in df_ad.columns:
            filiais = ['Todas'] + sorted(df_ad['NOME_FILIAL'].dropna().unique().tolist())
            filtro_filial = st.selectbox("Filial", filiais, key="ad_filial")
        else:
            filtro_filial = 'Todas'

    with col3:
        ordenar = st.selectbox("Ordenar", ["Mais recente", "Maior valor", "Maior saldo"], key="ad_ordem")

    # Aplicar filtros
    if filtro_tipo == "Pendentes":
        df_show = df_pendentes.copy()
    elif filtro_tipo == "Quitados":
        df_show = df_quitados.copy()
    else:
        df_show = df_ad.copy()

    if filtro_filial != 'Todas' and 'NOME_FILIAL' in df_show.columns:
        df_show = df_show[df_show['NOME_FILIAL'] == filtro_filial]

    # Ordenar
    if ordenar == "Mais recente" and 'EMISSAO' in df_show.columns:
        df_show = df_show.sort_values('EMISSAO', ascending=False)
    elif ordenar == "Maior valor":
        df_show = df_show.sort_values('VALOR_ORIGINAL', ascending=False)
    elif ordenar == "Maior saldo" and 'SALDO' in df_show.columns:
        df_show = df_show.sort_values('SALDO', ascending=False)

    df_show = df_show.head(100)

    # Calcular dias pendente
    if 'EMISSAO' in df_show.columns:
        df_show['DIAS_PENDENTE'] = (hoje - df_show['EMISSAO']).dt.days

    # Preparar tabela (SEM STATUS - conforme solicitado)
    colunas = ['NOME_FILIAL', 'NOME_FORNECEDOR', 'EMISSAO', 'VALOR_ORIGINAL', 'SALDO', 'DIAS_PENDENTE']
    colunas_disp = [c for c in colunas if c in df_show.columns]
    df_tab = df_show[colunas_disp].copy()

    # Formatar
    if 'EMISSAO' in df_tab.columns:
        df_tab['EMISSAO'] = pd.to_datetime(df_tab['EMISSAO'], errors='coerce').dt.strftime('%d/%m/%Y')

    df_tab['VALOR_ORIGINAL'] = df_tab['VALOR_ORIGINAL'].apply(lambda x: formatar_moeda(x, completo=True))

    if 'SALDO' in df_tab.columns:
        df_tab['SALDO'] = df_tab['SALDO'].apply(lambda x: formatar_moeda(x, completo=True))

    if 'DIAS_PENDENTE' in df_tab.columns:
        df_tab['DIAS_PENDENTE'] = df_tab['DIAS_PENDENTE'].apply(lambda x: f"{int(x)}d" if pd.notna(x) else '-')

    # Renomear
    nomes = {
        'NOME_FILIAL': 'Filial',
        'NOME_FORNECEDOR': 'Fornecedor',
        'EMISSAO': 'Dt Adiantamento',
        'VALOR_ORIGINAL': 'Valor',
        'SALDO': 'Saldo',
        'DIAS_PENDENTE': 'Dias Pendente'
    }
    df_tab.columns = [nomes.get(c, c) for c in df_tab.columns]

    st.dataframe(df_tab, use_container_width=True, hide_index=True, height=400)
    st.caption(f"Exibindo {len(df_tab)} adiantamentos")


def _render_compensacoes(df_bx, cores):
    """Lista de compensacoes realizadas"""

    st.markdown("##### Compensacoes Realizadas")

    if len(df_bx) == 0:
        st.info("Nenhuma compensacao registrada.")
        return

    total_compensado = df_bx['VALOR_BAIXA'].sum() if 'VALOR_BAIXA' in df_bx.columns else 0

    # Prazo medio
    prazo_medio = 0
    if 'DIF_DIAS_EMIS_BAIXA' in df_bx.columns:
        prazo_medio = pd.to_numeric(df_bx['DIF_DIAS_EMIS_BAIXA'], errors='coerce').mean()

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Compensado", formatar_moeda(total_compensado))
    col2.metric("Qtd Compensacoes", len(df_bx))
    col3.metric("Prazo Medio", f"{prazo_medio:.0f} dias")

    st.markdown("---")

    # Grafico de evolucao
    if 'DT_BAIXA' in df_bx.columns:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("###### Evolucao Mensal")
            df_mensal = df_bx.copy()
            df_mensal['MES'] = df_mensal['DT_BAIXA'].dt.to_period('M').astype(str)
            df_grp = df_mensal.groupby('MES')['VALOR_BAIXA'].sum().tail(12).reset_index()

            fig = go.Figure(go.Bar(
                x=df_grp['MES'],
                y=df_grp['VALOR_BAIXA'],
                marker_color=cores['primaria'],
                text=[formatar_moeda(v) for v in df_grp['VALOR_BAIXA']],
                textposition='outside',
                textfont=dict(size=9)
            ))
            fig.update_layout(
                criar_layout(250),
                xaxis_tickangle=-45,
                margin=dict(l=10, r=10, t=10, b=60)
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("###### Distribuicao por Prazo")

            if 'DIF_DIAS_EMIS_BAIXA' in df_bx.columns:
                def faixa_prazo(d):
                    if pd.isna(d) or d < 0:
                        return 'N/A'
                    d = int(d)
                    if d <= 30:
                        return 'Ate 30d'
                    elif d <= 60:
                        return '31-60d'
                    elif d <= 90:
                        return '61-90d'
                    elif d <= 180:
                        return '91-180d'
                    return '180+d'

                df_bx_temp = df_bx.copy()
                df_bx_temp['PRAZO'] = pd.to_numeric(df_bx_temp['DIF_DIAS_EMIS_BAIXA'], errors='coerce')
                df_bx_temp['FAIXA'] = df_bx_temp['PRAZO'].apply(faixa_prazo)

                ordem = ['Ate 30d', '31-60d', '61-90d', '91-180d', '180+d']
                df_faixa = df_bx_temp.groupby('FAIXA')['VALOR_BAIXA'].sum().reindex(ordem, fill_value=0).reset_index()

                cores_faixas = [cores['sucesso'], cores['info'], cores['alerta'], '#f97316', cores['perigo']]

                fig = go.Figure(go.Bar(
                    x=df_faixa['FAIXA'],
                    y=df_faixa['VALOR_BAIXA'],
                    marker_color=cores_faixas,
                    text=[formatar_moeda(v) for v in df_faixa['VALOR_BAIXA']],
                    textposition='outside',
                    textfont=dict(size=9)
                ))
                fig.update_layout(
                    criar_layout(250),
                    margin=dict(l=10, r=10, t=10, b=30)
                )
                st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Filtros
    col1, col2 = st.columns(2)
    with col1:
        ordenar = st.selectbox("Ordenar", ["Mais recente", "Maior valor"], key="comp_ordem")

    # Tabela
    df_show = df_bx.copy()

    if ordenar == "Mais recente" and 'DT_BAIXA' in df_show.columns:
        df_show = df_show.sort_values('DT_BAIXA', ascending=False)
    else:
        df_show = df_show.sort_values('VALOR_BAIXA', ascending=False)

    df_show = df_show.head(100)

    # Preparar tabela
    colunas = ['NOME_FILIAL', 'NOME_FORNECEDOR', 'EMISSAO', 'DT_BAIXA', 'DIF_DIAS_EMIS_BAIXA', 'VALOR_BAIXA']
    colunas_disp = [c for c in colunas if c in df_show.columns]
    df_tab = df_show[colunas_disp].copy()

    # Formatar
    for col in ['EMISSAO', 'DT_BAIXA']:
        if col in df_tab.columns:
            df_tab[col] = pd.to_datetime(df_tab[col], errors='coerce').dt.strftime('%d/%m/%Y')

    if 'VALOR_BAIXA' in df_tab.columns:
        df_tab['VALOR_BAIXA'] = df_tab['VALOR_BAIXA'].apply(lambda x: formatar_moeda(x, completo=True))

    if 'DIF_DIAS_EMIS_BAIXA' in df_tab.columns:
        df_tab['DIF_DIAS_EMIS_BAIXA'] = pd.to_numeric(df_tab['DIF_DIAS_EMIS_BAIXA'], errors='coerce').apply(
            lambda x: f"{int(x)}d" if pd.notna(x) else '-'
        )

    nomes = {
        'NOME_FILIAL': 'Filial',
        'NOME_FORNECEDOR': 'Fornecedor',
        'EMISSAO': 'Dt Adiantamento',
        'DT_BAIXA': 'Dt Compensacao',
        'DIF_DIAS_EMIS_BAIXA': 'Prazo',
        'VALOR_BAIXA': 'Valor'
    }
    df_tab.columns = [nomes.get(c, c) for c in df_tab.columns]

    st.dataframe(df_tab, use_container_width=True, hide_index=True, height=400)


def _render_adto_nf(df_ad, df_bx, cores):
    """Relacionamento Adiantamento x NF (Compensacao)"""

    st.markdown("##### Relacionamento Adiantamento x NF")
    st.caption("Visualize a relacao entre adiantamentos e suas compensacoes via NF")

    if len(df_bx) == 0:
        st.info("Nenhuma compensacao registrada.")
        return

    # Metricas
    total_compensacoes = len(df_bx)
    total_valor = df_bx['VALOR_BAIXA'].sum() if 'VALOR_BAIXA' in df_bx.columns else 0

    prazo_medio = 0
    if 'DIF_DIAS_EMIS_BAIXA' in df_bx.columns:
        prazo_medio = pd.to_numeric(df_bx['DIF_DIAS_EMIS_BAIXA'], errors='coerce').mean()

    # Compensacoes longas (> 90 dias)
    qtd_longo = 0
    if 'DIF_DIAS_EMIS_BAIXA' in df_bx.columns:
        prazo = pd.to_numeric(df_bx['DIF_DIAS_EMIS_BAIXA'], errors='coerce')
        qtd_longo = (prazo > 90).sum()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Compensacoes", total_compensacoes)
    col2.metric("Valor Total", formatar_moeda(total_valor))
    col3.metric("Prazo Medio", f"{prazo_medio:.0f} dias")
    col4.metric("Prazo > 90 dias", qtd_longo, "atencao" if qtd_longo > 0 else None)

    st.markdown("---")

    # Filtros
    col1, col2, col3 = st.columns(3)

    with col1:
        if 'NOME_FORNECEDOR' in df_bx.columns:
            fornecedores = ['Todos'] + sorted(df_bx['NOME_FORNECEDOR'].dropna().unique().tolist())
            filtro_forn = st.selectbox("Fornecedor", fornecedores, key="adto_forn")
        else:
            filtro_forn = 'Todos'

    with col2:
        filtro_prazo = st.selectbox("Prazo", ["Todos", "Ate 30d", "31-90d", "90+d"], key="adto_prazo")

    with col3:
        ordenar = st.selectbox("Ordenar", ["Mais recente", "Maior valor", "Maior prazo"], key="adto_ordem")

    # Aplicar filtros
    df_show = df_bx.copy()

    if filtro_forn != 'Todos' and 'NOME_FORNECEDOR' in df_show.columns:
        df_show = df_show[df_show['NOME_FORNECEDOR'] == filtro_forn]

    if 'DIF_DIAS_EMIS_BAIXA' in df_show.columns:
        df_show['PRAZO_NUM'] = pd.to_numeric(df_show['DIF_DIAS_EMIS_BAIXA'], errors='coerce')

        if filtro_prazo == "Ate 30d":
            df_show = df_show[df_show['PRAZO_NUM'] <= 30]
        elif filtro_prazo == "31-90d":
            df_show = df_show[(df_show['PRAZO_NUM'] > 30) & (df_show['PRAZO_NUM'] <= 90)]
        elif filtro_prazo == "90+d":
            df_show = df_show[df_show['PRAZO_NUM'] > 90]

    # Ordenar
    if ordenar == "Mais recente" and 'DT_BAIXA' in df_show.columns:
        df_show = df_show.sort_values('DT_BAIXA', ascending=False)
    elif ordenar == "Maior valor" and 'VALOR_BAIXA' in df_show.columns:
        df_show = df_show.sort_values('VALOR_BAIXA', ascending=False)
    elif ordenar == "Maior prazo" and 'PRAZO_NUM' in df_show.columns:
        df_show = df_show.sort_values('PRAZO_NUM', ascending=False)

    df_show = df_show.head(100)

    # Preparar tabela com todas as datas relevantes
    colunas = [
        'NOME_FILIAL', 'NOME_FORNECEDOR',
        'EMISSAO',  # Dt do Adiantamento
        'DT_BAIXA',  # Dt da Compensacao
        'DIF_DIAS_EMIS_BAIXA',  # Prazo
        'VALOR_BAIXA',
        'NUMERO',  # Numero NF
        'HISTORICO'
    ]
    colunas_disp = [c for c in colunas if c in df_show.columns]
    df_tab = df_show[colunas_disp].copy()

    # Formatar
    for col in ['EMISSAO', 'DT_BAIXA']:
        if col in df_tab.columns:
            df_tab[col] = pd.to_datetime(df_tab[col], errors='coerce').dt.strftime('%d/%m/%Y')

    if 'VALOR_BAIXA' in df_tab.columns:
        df_tab['VALOR_BAIXA'] = df_tab['VALOR_BAIXA'].apply(lambda x: formatar_moeda(x, completo=True))

    if 'DIF_DIAS_EMIS_BAIXA' in df_tab.columns:
        df_tab['DIF_DIAS_EMIS_BAIXA'] = pd.to_numeric(df_tab['DIF_DIAS_EMIS_BAIXA'], errors='coerce').apply(
            lambda x: f"{int(x)}d" if pd.notna(x) else '-'
        )

    if 'HISTORICO' in df_tab.columns:
        df_tab['HISTORICO'] = df_tab['HISTORICO'].astype(str).str[:40]

    nomes = {
        'NOME_FILIAL': 'Filial',
        'NOME_FORNECEDOR': 'Fornecedor',
        'EMISSAO': 'Dt Adiantamento',
        'DT_BAIXA': 'Dt Compensacao',
        'DIF_DIAS_EMIS_BAIXA': 'Prazo',
        'VALOR_BAIXA': 'Valor',
        'NUMERO': 'NF/Doc',
        'HISTORICO': 'Historico'
    }
    df_tab.columns = [nomes.get(c, c) for c in df_tab.columns]

    st.dataframe(df_tab, use_container_width=True, hide_index=True, height=400)
    st.caption(f"Exibindo {len(df_tab)} compensacoes")


def _render_por_fornecedor(df_ad, df_bx, cores):
    """Analise por fornecedor"""

    st.markdown("##### Analise por Fornecedor")

    # Agrupar adiantamentos
    df_forn = df_ad.groupby('NOME_FORNECEDOR').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'FORNECEDOR': 'count'
    }).reset_index()
    df_forn.columns = ['Fornecedor', 'Total', 'Saldo', 'Qtd']
    df_forn['Compensado'] = df_forn['Total'] - df_forn['Saldo']
    df_forn['Pct'] = (df_forn['Compensado'] / df_forn['Total'] * 100).fillna(0).round(1)
    df_forn = df_forn.sort_values('Saldo', ascending=False)

    # Metricas
    total_fornecedores = len(df_forn)
    forn_pendentes = len(df_forn[df_forn['Saldo'] > 0])
    forn_quitados = total_fornecedores - forn_pendentes

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Fornecedores", total_fornecedores)
    col2.metric("Com Saldo Pendente", forn_pendentes)
    col3.metric("Totalmente Compensados", forn_quitados)

    st.markdown("---")

    # Grafico Top 15
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("###### Top 15 - Saldo Pendente")

        df_top = df_forn.head(15)

        fig = go.Figure()

        fig.add_trace(go.Bar(
            y=df_top['Fornecedor'].str[:25],
            x=df_top['Compensado'],
            orientation='h',
            name='Compensado',
            marker_color=cores['primaria'],
            text=[formatar_moeda(v) for v in df_top['Compensado']],
            textposition='inside',
            textfont=dict(size=9, color='white')
        ))

        fig.add_trace(go.Bar(
            y=df_top['Fornecedor'].str[:25],
            x=df_top['Saldo'],
            orientation='h',
            name='Pendente',
            marker_color=cores['alerta'],
            text=[formatar_moeda(v) for v in df_top['Saldo']],
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
        st.markdown("###### Maiores Pendencias")

        for _, row in df_forn.head(5).iterrows():
            if row['Saldo'] > 0:
                nome = row['Fornecedor'][:20]
                valor = formatar_moeda(row['Saldo'])
                pct = row['Pct']

                st.markdown(f"**{nome}**")
                st.caption(f"Pendente: {valor} ({pct:.0f}% compensado)")
                st.progress(pct / 100)

    st.markdown("---")

    # Tabela completa
    st.markdown("###### Tabela Completa")

    df_exibir = df_forn.copy()
    df_exibir['Total'] = df_exibir['Total'].apply(lambda x: formatar_moeda(x, completo=True))
    df_exibir['Compensado'] = df_exibir['Compensado'].apply(lambda x: formatar_moeda(x, completo=True))
    df_exibir['Saldo'] = df_exibir['Saldo'].apply(lambda x: formatar_moeda(x, completo=True))
    df_exibir.columns = ['Fornecedor', 'Total Adiantado', 'Saldo Pendente', 'Qtd Adiant', 'Ja Compensado', '% Compensado']

    # Reordenar colunas
    df_exibir = df_exibir[['Fornecedor', 'Total Adiantado', 'Ja Compensado', 'Saldo Pendente', 'Qtd Adiant', '% Compensado']]

    st.dataframe(
        df_exibir,
        use_container_width=True,
        hide_index=True,
        height=400,
        column_config={
            '% Compensado': st.column_config.ProgressColumn(
                '% Compensado',
                format='%.0f%%',
                min_value=0,
                max_value=100
            )
        }
    )
