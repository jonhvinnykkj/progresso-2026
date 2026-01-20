"""
Aba Adiantamentos - Contas a Receber
Foco: Conciliacao | Fluxo de Caixa | Analise de Clientes
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

from config.theme import get_cores
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero


def render_adiantamentos_receber(df_adiant, df_baixas):
    """Renderiza a aba de Adiantamentos a Receber"""
    cores = get_cores()
    hoje = datetime.now()

    # ========== HEADER ==========
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, {cores['card']}, {cores['fundo']});
                border-left: 4px solid {cores['info']}; border-radius: 0 10px 10px 0;
                padding: 1rem; margin-bottom: 1rem;">
        <h4 style="color: {cores['texto']}; margin: 0;">Adiantamentos de Clientes</h4>
        <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0.25rem 0 0 0;">
            Conciliacao | Fluxo de Caixa | Analise de Clientes
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Verificar dados
    if len(df_adiant) == 0:
        st.warning("Nenhum dado de adiantamentos disponivel.")
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

    # Identificar coluna de cliente
    col_cliente = 'NOME_FORNECEDOR' if 'NOME_FORNECEDOR' in df_ad.columns else 'NOME_CLIENTE'

    # ========== PAINEL DE STATUS ==========
    _render_painel_status(df_ad, df_bx, cores)

    st.divider()

    # ========== FLUXO DE CAIXA ==========
    _render_fluxo_caixa(df_ad, df_bx, cores)

    st.divider()

    # ========== ANALISE DE CLIENTES ==========
    col1, col2 = st.columns(2)

    with col1:
        _render_top_clientes(df_ad, col_cliente, cores)

    with col2:
        _render_comportamento_clientes(df_ad, df_bx, col_cliente, cores)

    st.divider()

    # ========== CONCILIACAO ==========
    _render_conciliacao(df_ad, df_bx, col_cliente, cores, hoje)

    st.divider()

    # ========== POR FILIAL ==========
    _render_por_filial(df_ad, cores)

    st.divider()

    # ========== HISTORICO DO CLIENTE ==========
    _render_historico_cliente(df_ad, df_bx, col_cliente, cores)


def _render_painel_status(df_ad, df_bx, cores):
    """Painel de status dos adiantamentos"""

    total_adiantado = df_ad['VALOR_ORIGINAL'].sum()
    total_pendente = df_ad['SALDO'].sum() if 'SALDO' in df_ad.columns else total_adiantado
    total_compensado = total_adiantado - total_pendente

    taxa_compensacao = total_compensado / total_adiantado * 100 if total_adiantado > 0 else 0

    qtd_adiantamentos = len(df_ad)
    qtd_pendentes = len(df_ad[df_ad['SALDO'] > 0]) if 'SALDO' in df_ad.columns else qtd_adiantamentos

    # Calcular valor medio e ticket
    ticket_medio = total_adiantado / qtd_adiantamentos if qtd_adiantamentos > 0 else 0

    # Status
    if taxa_compensacao >= 80:
        status = "SAUDAVEL"
        cor_status = cores['sucesso']
    elif taxa_compensacao >= 50:
        status = "NORMAL"
        cor_status = cores['info']
    elif taxa_compensacao >= 30:
        status = "ATENCAO"
        cor_status = cores['alerta']
    else:
        status = "CRITICO"
        cor_status = cores['perigo']

    col1, col2, col3, col4, col5 = st.columns([1.5, 1, 1, 1, 1])

    with col1:
        st.markdown(f"""
        <div style="background: {cores['card']}; border: 2px solid {cor_status};
                    border-radius: 10px; padding: 1rem; text-align: center;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">TAXA COMPENSACAO</p>
            <p style="color: {cor_status}; font-size: 1.8rem; font-weight: 800; margin: 0.25rem 0;">{taxa_compensacao:.0f}%</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">{status}</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.metric("Total Adiantado", formatar_moeda(total_adiantado), f"{qtd_adiantamentos} registros")

    with col3:
        st.metric("Compensado", formatar_moeda(total_compensado), f"{qtd_adiantamentos - qtd_pendentes} quitados")

    with col4:
        st.metric("Saldo Pendente", formatar_moeda(total_pendente), f"{qtd_pendentes} abertos", delta_color="inverse")

    with col5:
        st.metric("Ticket Medio", formatar_moeda(ticket_medio))


def _render_fluxo_caixa(df_ad, df_bx, cores):
    """Fluxo de caixa - entradas vs compensacoes"""

    st.markdown(f"""
    <div style="background: {cores['card']}; border-left: 4px solid {cores['sucesso']};
                padding: 0.75rem 1rem; border-radius: 0 8px 8px 0; margin-bottom: 1rem;">
        <h4 style="color: {cores['texto']}; margin: 0;">Fluxo de Caixa - Adiantamentos</h4>
        <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0;">
            Entrada de adiantamentos vs compensacoes realizadas
        </p>
    </div>
    """, unsafe_allow_html=True)

    if 'EMISSAO' not in df_ad.columns:
        st.info("Coluna EMISSAO nao disponivel")
        return

    # Agrupar adiantamentos por mes
    df_ad_temp = df_ad.copy()
    df_ad_temp['MES'] = df_ad_temp['EMISSAO'].dt.to_period('M')

    df_entradas = df_ad_temp.groupby('MES').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'count'
    }).reset_index()
    df_entradas.columns = ['Mes', 'Entrada', 'Qtd_Entrada']
    df_entradas['Mes'] = df_entradas['Mes'].astype(str)

    # Agrupar baixas por mes
    if len(df_bx) > 0 and 'DT_BAIXA' in df_bx.columns and 'VALOR_BAIXA' in df_bx.columns:
        df_bx_temp = df_bx.copy()
        df_bx_temp['MES'] = df_bx_temp['DT_BAIXA'].dt.to_period('M')

        df_saidas = df_bx_temp.groupby('MES').agg({
            'VALOR_BAIXA': 'sum',
            'DT_BAIXA': 'count'
        }).reset_index()
        df_saidas.columns = ['Mes', 'Saida', 'Qtd_Saida']
        df_saidas['Mes'] = df_saidas['Mes'].astype(str)
    else:
        df_saidas = pd.DataFrame(columns=['Mes', 'Saida', 'Qtd_Saida'])

    # Merge
    df_fluxo = df_entradas.merge(df_saidas, on='Mes', how='outer').fillna(0)
    df_fluxo = df_fluxo.sort_values('Mes').tail(12)

    # Calcular saldo acumulado
    df_fluxo['Liquido'] = df_fluxo['Entrada'] - df_fluxo['Saida']
    df_fluxo['Acumulado'] = df_fluxo['Liquido'].cumsum()

    col1, col2 = st.columns([2, 1])

    with col1:
        fig = go.Figure()

        # Barras de entrada
        fig.add_trace(go.Bar(
            x=df_fluxo['Mes'],
            y=df_fluxo['Entrada'],
            name='Adiantamentos Recebidos',
            marker_color=cores['sucesso'],
            text=[formatar_moeda(v) for v in df_fluxo['Entrada']],
            textposition='outside',
            textfont=dict(size=8)
        ))

        # Barras de saida (negativo para visualizacao)
        fig.add_trace(go.Bar(
            x=df_fluxo['Mes'],
            y=-df_fluxo['Saida'],
            name='Compensacoes',
            marker_color=cores['alerta'],
            text=[formatar_moeda(v) for v in df_fluxo['Saida']],
            textposition='outside',
            textfont=dict(size=8)
        ))

        # Linha de saldo acumulado
        fig.add_trace(go.Scatter(
            x=df_fluxo['Mes'],
            y=df_fluxo['Acumulado'],
            mode='lines+markers',
            name='Saldo Acumulado',
            line=dict(color=cores['primaria'], width=3),
            marker=dict(size=8),
            yaxis='y2'
        ))

        fig.update_layout(
            criar_layout(320, barmode='relative'),
            yaxis=dict(title='Valor Mensal'),
            yaxis2=dict(title='Acumulado', overlaying='y', side='right', showgrid=False),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=9)),
            margin=dict(l=10, r=50, t=40, b=60),
            xaxis_tickangle=-45
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("##### Resumo do Periodo")

        total_entradas = df_fluxo['Entrada'].sum()
        total_saidas = df_fluxo['Saida'].sum()
        saldo = total_entradas - total_saidas

        st.metric("Entradas (12m)", formatar_moeda(total_entradas))
        st.metric("Compensacoes (12m)", formatar_moeda(total_saidas))

        cor_saldo = cores['sucesso'] if saldo > 0 else cores['perigo']
        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cor_saldo};
                    border-radius: 8px; padding: 0.75rem; text-align: center; margin-top: 0.5rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">SALDO LIQUIDO</p>
            <p style="color: {cor_saldo}; font-size: 1.3rem; font-weight: 700; margin: 0;">{formatar_moeda(saldo)}</p>
        </div>
        """, unsafe_allow_html=True)

        # Media mensal
        media_entrada = total_entradas / len(df_fluxo) if len(df_fluxo) > 0 else 0
        media_saida = total_saidas / len(df_fluxo) if len(df_fluxo) > 0 else 0

        st.caption(f"Media/mes: +{formatar_moeda(media_entrada)} | -{formatar_moeda(media_saida)}")


def _render_top_clientes(df_ad, col_cliente, cores):
    """Top clientes com adiantamentos"""

    st.markdown("##### Top 10 Clientes - Saldo Pendente")

    df_cli = df_ad.groupby(col_cliente).agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'EMISSAO': 'count'
    }).reset_index()
    df_cli.columns = [col_cliente, 'Total', 'Pendente', 'Qtd']

    df_cli['Compensado'] = df_cli['Total'] - df_cli['Pendente']
    df_cli['Taxa'] = (df_cli['Compensado'] / df_cli['Total'] * 100).fillna(0)

    # Top 10 por saldo pendente
    df_top = df_cli.nlargest(10, 'Pendente')

    if len(df_top) == 0:
        st.success("Todos os adiantamentos foram compensados!")
        return

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=df_top[col_cliente].str[:20],
        x=df_top['Compensado'],
        orientation='h',
        name='Compensado',
        marker_color=cores['sucesso'],
        text=[formatar_moeda(v) for v in df_top['Compensado']],
        textposition='inside',
        textfont=dict(size=8, color='white')
    ))

    fig.add_trace(go.Bar(
        y=df_top[col_cliente].str[:20],
        x=df_top['Pendente'],
        orientation='h',
        name='Pendente',
        marker_color=cores['alerta'],
        text=[formatar_moeda(v) for v in df_top['Pendente']],
        textposition='inside',
        textfont=dict(size=8, color='white')
    ))

    fig.update_layout(
        criar_layout(320, barmode='stack'),
        yaxis={'autorange': 'reversed'},
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=9)),
        margin=dict(l=10, r=10, t=40, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_comportamento_clientes(df_ad, df_bx, col_cliente, cores):
    """Analise de comportamento dos clientes"""

    st.markdown("##### Comportamento de Clientes")

    df_cli = df_ad.groupby(col_cliente).agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'EMISSAO': ['count', 'min', 'max']
    }).reset_index()
    df_cli.columns = [col_cliente, 'Total', 'Pendente', 'Qtd', 'Primeiro', 'Ultimo']

    df_cli['Taxa'] = ((df_cli['Total'] - df_cli['Pendente']) / df_cli['Total'] * 100).fillna(0)

    # Classificar comportamento
    def classificar(row):
        if row['Taxa'] >= 90:
            return 'Excelente', cores['sucesso']
        elif row['Taxa'] >= 70:
            return 'Bom', cores['info']
        elif row['Taxa'] >= 50:
            return 'Regular', '#fbbf24'
        elif row['Taxa'] >= 30:
            return 'Ruim', cores['alerta']
        else:
            return 'Critico', cores['perigo']

    comportamentos = df_cli.apply(classificar, axis=1)
    df_cli['Comportamento'] = [c[0] for c in comportamentos]

    # Contar por comportamento
    df_comp = df_cli.groupby('Comportamento').agg({
        col_cliente: 'count',
        'Pendente': 'sum'
    }).reset_index()
    df_comp.columns = ['Comportamento', 'Clientes', 'Pendente']

    ordem = ['Excelente', 'Bom', 'Regular', 'Ruim', 'Critico']
    cores_comp = {
        'Excelente': cores['sucesso'],
        'Bom': cores['info'],
        'Regular': '#fbbf24',
        'Ruim': cores['alerta'],
        'Critico': cores['perigo']
    }

    df_comp['Ordem'] = df_comp['Comportamento'].apply(lambda x: ordem.index(x) if x in ordem else 99)
    df_comp = df_comp.sort_values('Ordem')

    fig = go.Figure(go.Pie(
        labels=df_comp['Comportamento'],
        values=df_comp['Clientes'],
        marker_colors=[cores_comp.get(c, cores['info']) for c in df_comp['Comportamento']],
        hole=0.5,
        textinfo='label+percent',
        textfont=dict(size=10)
    ))

    fig.update_layout(
        criar_layout(280),
        showlegend=False,
        margin=dict(l=10, r=10, t=10, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)

    # Resumo
    total_cli = df_comp['Clientes'].sum()
    bons = df_comp[df_comp['Comportamento'].isin(['Excelente', 'Bom'])]['Clientes'].sum()
    st.caption(f"{bons} de {total_cli} clientes ({bons/total_cli*100:.0f}%) com boa compensacao")


def _render_conciliacao(df_ad, df_bx, col_cliente, cores, hoje):
    """Conciliacao - adiantamentos para compensar"""

    st.markdown(f"""
    <div style="background: {cores['card']}; border-left: 4px solid {cores['primaria']};
                padding: 0.75rem 1rem; border-radius: 0 8px 8px 0; margin-bottom: 1rem;">
        <h4 style="color: {cores['texto']}; margin: 0;">Conciliacao de Adiantamentos</h4>
        <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0;">
            Adiantamentos pendentes de compensacao
        </p>
    </div>
    """, unsafe_allow_html=True)

    df_pendentes = df_ad[df_ad['SALDO'] > 0].copy() if 'SALDO' in df_ad.columns else df_ad.copy()

    if len(df_pendentes) == 0:
        st.success("Todos os adiantamentos foram compensados!")
        return

    # Calcular dias pendente
    if 'EMISSAO' in df_pendentes.columns:
        df_pendentes['DIAS_PENDENTE'] = (hoje - df_pendentes['EMISSAO']).dt.days

    # Metricas
    total_pendente = df_pendentes['SALDO'].sum()
    qtd_pendente = len(df_pendentes)

    # Aging
    if 'DIAS_PENDENTE' in df_pendentes.columns:
        ate_30 = df_pendentes[df_pendentes['DIAS_PENDENTE'] <= 30]['SALDO'].sum()
        ate_60 = df_pendentes[(df_pendentes['DIAS_PENDENTE'] > 30) & (df_pendentes['DIAS_PENDENTE'] <= 60)]['SALDO'].sum()
        ate_90 = df_pendentes[(df_pendentes['DIAS_PENDENTE'] > 60) & (df_pendentes['DIAS_PENDENTE'] <= 90)]['SALDO'].sum()
        mais_90 = df_pendentes[df_pendentes['DIAS_PENDENTE'] > 90]['SALDO'].sum()

        col1, col2, col3, col4, col5 = st.columns(5)

        col1.metric("Total Pendente", formatar_moeda(total_pendente), f"{qtd_pendente} titulos")
        col2.metric("Ate 30 dias", formatar_moeda(ate_30))
        col3.metric("31-60 dias", formatar_moeda(ate_60))
        col4.metric("61-90 dias", formatar_moeda(ate_90), delta_color="inverse" if ate_90 > 0 else "off")
        col5.metric("+90 dias", formatar_moeda(mais_90), "PRIORIDADE", delta_color="inverse" if mais_90 > 0 else "off")

    st.markdown("---")

    # Filtros
    col1, col2, col3 = st.columns(3)

    with col1:
        filiais = ['Todas'] + sorted(df_pendentes['NOME_FILIAL'].dropna().unique().tolist())
        filtro_filial = st.selectbox("Filial", filiais, key="conc_filial")

    with col2:
        ordenar = st.selectbox("Ordenar por", ['Maior Valor', 'Mais Antigo', 'Cliente'], key="conc_ordem")

    with col3:
        faixa = st.selectbox("Faixa de Tempo", ['Todos', 'Ate 30 dias', '31-60 dias', '61-90 dias', '+90 dias'], key="conc_faixa")

    # Aplicar filtros
    df_show = df_pendentes.copy()

    if filtro_filial != 'Todas':
        df_show = df_show[df_show['NOME_FILIAL'] == filtro_filial]

    if faixa != 'Todos' and 'DIAS_PENDENTE' in df_show.columns:
        faixas_map = {
            'Ate 30 dias': (0, 30),
            '31-60 dias': (31, 60),
            '61-90 dias': (61, 90),
            '+90 dias': (91, 9999)
        }
        min_d, max_d = faixas_map.get(faixa, (0, 9999))
        df_show = df_show[(df_show['DIAS_PENDENTE'] >= min_d) & (df_show['DIAS_PENDENTE'] <= max_d)]

    if ordenar == 'Maior Valor':
        df_show = df_show.sort_values('SALDO', ascending=False)
    elif ordenar == 'Mais Antigo':
        df_show = df_show.sort_values('EMISSAO', ascending=True)
    else:
        df_show = df_show.sort_values(col_cliente)

    # Tabela
    colunas = ['NOME_FILIAL', col_cliente, 'EMISSAO', 'VALOR_ORIGINAL', 'SALDO']
    if 'DIAS_PENDENTE' in df_show.columns:
        colunas.append('DIAS_PENDENTE')

    df_tabela = df_show[colunas].head(50).copy()

    # Formatar
    if 'EMISSAO' in df_tabela.columns:
        df_tabela['EMISSAO'] = df_tabela['EMISSAO'].dt.strftime('%d/%m/%Y')
    df_tabela['VALOR_ORIGINAL'] = df_tabela['VALOR_ORIGINAL'].apply(lambda x: formatar_moeda(x, completo=True))
    df_tabela['SALDO'] = df_tabela['SALDO'].apply(lambda x: formatar_moeda(x, completo=True))

    nomes = {
        'NOME_FILIAL': 'Filial',
        col_cliente: 'Cliente',
        'EMISSAO': 'Data',
        'VALOR_ORIGINAL': 'Valor Original',
        'SALDO': 'Saldo',
        'DIAS_PENDENTE': 'Dias'
    }
    df_tabela.columns = [nomes.get(c, c) for c in df_tabela.columns]

    st.dataframe(df_tabela, use_container_width=True, hide_index=True, height=350)

    st.caption(f"Exibindo {len(df_tabela)} de {len(df_pendentes)} adiantamentos pendentes")


def _render_por_filial(df_ad, cores):
    """Analise por filial"""

    st.markdown("##### Adiantamentos por Filial")

    if 'NOME_FILIAL' not in df_ad.columns:
        st.info("Coluna NOME_FILIAL nao disponivel")
        return

    df_fil = df_ad.groupby('NOME_FILIAL').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'EMISSAO': 'count'
    }).reset_index()
    df_fil.columns = ['Filial', 'Total', 'Pendente', 'Qtd']

    df_fil['Compensado'] = df_fil['Total'] - df_fil['Pendente']
    df_fil['Taxa'] = (df_fil['Compensado'] / df_fil['Total'] * 100).fillna(0)
    df_fil = df_fil.sort_values('Total', ascending=False)

    col1, col2 = st.columns(2)

    with col1:
        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=df_fil['Filial'].str[:15],
            y=df_fil['Compensado'],
            name='Compensado',
            marker_color=cores['sucesso']
        ))

        fig.add_trace(go.Bar(
            x=df_fil['Filial'].str[:15],
            y=df_fil['Pendente'],
            name='Pendente',
            marker_color=cores['alerta']
        ))

        fig.update_layout(
            criar_layout(280, barmode='stack'),
            xaxis_tickangle=-45,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=9)),
            margin=dict(l=10, r=10, t=40, b=80)
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Taxa de compensacao por filial
        df_fil_ord = df_fil.sort_values('Taxa', ascending=True)

        cores_barra = [cores['sucesso'] if t >= 70 else cores['alerta'] if t >= 50 else cores['perigo'] for t in df_fil_ord['Taxa']]

        fig = go.Figure(go.Bar(
            y=df_fil_ord['Filial'].str[:15],
            x=df_fil_ord['Taxa'],
            orientation='h',
            marker_color=cores_barra,
            text=[f"{t:.0f}%" for t in df_fil_ord['Taxa']],
            textposition='outside',
            textfont=dict(size=9)
        ))

        fig.add_vline(x=70, line_dash="dash", line_color=cores['texto_secundario'],
                      annotation_text="Meta 70%", annotation_position="top")

        fig.update_layout(
            criar_layout(280),
            xaxis=dict(title='% Compensado', range=[0, 110]),
            margin=dict(l=10, r=10, t=10, b=10)
        )

        st.plotly_chart(fig, use_container_width=True)


def _render_historico_cliente(df_ad, df_bx, col_cliente, cores):
    """Historico detalhado de um cliente"""

    st.markdown(f"""
    <div style="background: {cores['card']}; border-left: 4px solid {cores['info']};
                padding: 0.75rem 1rem; border-radius: 0 8px 8px 0; margin-bottom: 1rem;">
        <h4 style="color: {cores['texto']}; margin: 0;">Historico do Cliente</h4>
        <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0;">
            Detalhamento de adiantamentos e compensacoes por cliente
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Lista de clientes ordenados por saldo
    df_cli = df_ad.groupby(col_cliente)['SALDO'].sum().nlargest(30).reset_index()
    clientes = df_cli[col_cliente].tolist()

    cliente_sel = st.selectbox(
        "Selecione um cliente:",
        options=[""] + clientes,
        key="hist_cli_adiant",
        format_func=lambda x: x[:40] if x else "Selecione..."
    )

    if not cliente_sel:
        return

    df_cliente = df_ad[df_ad[col_cliente] == cliente_sel].copy()

    if len(df_cliente) == 0:
        st.info("Sem dados para este cliente")
        return

    # Metricas do cliente
    total_adiantado = df_cliente['VALOR_ORIGINAL'].sum()
    total_pendente = df_cliente['SALDO'].sum()
    total_compensado = total_adiantado - total_pendente
    taxa = total_compensado / total_adiantado * 100 if total_adiantado > 0 else 0

    qtd_total = len(df_cliente)
    qtd_pendente = len(df_cliente[df_cliente['SALDO'] > 0])

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Total Adiantado", formatar_moeda(total_adiantado), f"{qtd_total} registros")
    col2.metric("Compensado", formatar_moeda(total_compensado))
    col3.metric("Pendente", formatar_moeda(total_pendente), f"{qtd_pendente} abertos")
    col4.metric("Taxa Compensacao", f"{taxa:.0f}%")

    # Classificar cliente
    if taxa >= 80:
        rating = "A"
        cor_rating = cores['sucesso']
    elif taxa >= 60:
        rating = "B"
        cor_rating = cores['info']
    elif taxa >= 40:
        rating = "C"
        cor_rating = '#fbbf24'
    elif taxa >= 20:
        rating = "D"
        cor_rating = cores['alerta']
    else:
        rating = "E"
        cor_rating = cores['perigo']

    with col5:
        st.markdown(f"""
        <div style="text-align: center; background: {cores['card']}; border: 2px solid {cor_rating};
                    border-radius: 8px; padding: 0.5rem;">
            <span style="color: {cor_rating}; font-size: 2rem; font-weight: 800;">{rating}</span>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">Rating</p>
        </div>
        """, unsafe_allow_html=True)

    # Evolucao mensal
    if 'EMISSAO' in df_cliente.columns:
        st.markdown("##### Evolucao Mensal")

        df_cliente['MES'] = df_cliente['EMISSAO'].dt.to_period('M').astype(str)

        df_mes = df_cliente.groupby('MES').agg({
            'VALOR_ORIGINAL': 'sum',
            'SALDO': 'sum'
        }).reset_index()
        df_mes['Compensado'] = df_mes['VALOR_ORIGINAL'] - df_mes['SALDO']

        if len(df_mes) > 1:
            fig = go.Figure()

            fig.add_trace(go.Bar(
                x=df_mes['MES'],
                y=df_mes['Compensado'],
                name='Compensado',
                marker_color=cores['sucesso']
            ))

            fig.add_trace(go.Bar(
                x=df_mes['MES'],
                y=df_mes['SALDO'],
                name='Pendente',
                marker_color=cores['alerta']
            ))

            fig.update_layout(
                criar_layout(200, barmode='stack'),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=8)),
                margin=dict(l=10, r=10, t=30, b=50),
                xaxis_tickangle=-45
            )

            st.plotly_chart(fig, use_container_width=True)

    # Lista de adiantamentos do cliente
    st.markdown("##### Adiantamentos do Cliente")

    colunas = ['NOME_FILIAL', 'EMISSAO', 'VALOR_ORIGINAL', 'SALDO']
    colunas_disp = [c for c in colunas if c in df_cliente.columns]

    df_tabela = df_cliente[colunas_disp].sort_values('EMISSAO', ascending=False).copy()

    if 'EMISSAO' in df_tabela.columns:
        df_tabela['EMISSAO'] = df_tabela['EMISSAO'].dt.strftime('%d/%m/%Y')
    df_tabela['VALOR_ORIGINAL'] = df_tabela['VALOR_ORIGINAL'].apply(lambda x: formatar_moeda(x, completo=True))
    df_tabela['SALDO'] = df_tabela['SALDO'].apply(lambda x: formatar_moeda(x, completo=True))

    df_tabela.columns = ['Filial', 'Data', 'Valor', 'Saldo']

    st.dataframe(df_tabela, use_container_width=True, hide_index=True, height=250)
