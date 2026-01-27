"""
Aba Intercompany - Análise de operações entre empresas do grupo
Empresas: Progresso, Ouro Branco, Peninsula, Hotelaria (Tropical)
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

from config.theme import get_cores
from config.settings import INTERCOMPANY_PATTERNS, INTERCOMPANY_TIPOS, INTERCOMPANY_PADRONIZACAO
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero


def identificar_intercompany(df):
    """Identifica operações intercompany no dataframe"""
    mask = df['NOME_FORNECEDOR'].str.upper().str.contains('|'.join(INTERCOMPANY_PATTERNS), na=False, regex=True)
    return df[mask].copy()


def padronizar_nome_ic(nome):
    """Padroniza o nome para comparação"""
    if pd.isna(nome):
        return nome
    nome_limpo = str(nome).strip().upper()
    for variacao, padrao in INTERCOMPANY_PADRONIZACAO.items():
        if variacao.upper() in nome_limpo:
            return padrao
    return nome


def classificar_tipo_intercompany(nome):
    """Classifica o tipo de operação intercompany usando config centralizada"""
    nome_padrao = padronizar_nome_ic(nome)
    if nome_padrao in INTERCOMPANY_TIPOS:
        return INTERCOMPANY_TIPOS[nome_padrao]
    nome_upper = str(nome).upper()
    for padrao, tipo in INTERCOMPANY_TIPOS.items():
        if padrao in nome_upper:
            return tipo
    return 'Outros'


def render_intercompany(df_contas):
    """Renderiza a aba de operações Intercompany"""
    cores = get_cores()
    hoje = datetime.now()

    # Identificar operações intercompany
    df_ic = identificar_intercompany(df_contas)

    if len(df_ic) == 0:
        st.warning("Nenhuma operação intercompany encontrada no período selecionado.")
        return

    # Classificar tipo
    df_ic['TIPO_INTERCOMPANY'] = df_ic['NOME_FORNECEDOR'].apply(classificar_tipo_intercompany)

    # Calcular métricas
    total_ic = df_ic['VALOR_ORIGINAL'].sum()
    total_geral = df_contas['VALOR_ORIGINAL'].sum()
    pct_ic = (total_ic / total_geral * 100) if total_geral > 0 else 0
    saldo_ic = df_ic['SALDO'].sum()
    pago_ic = total_ic - saldo_ic
    pct_pago = (pago_ic / total_ic * 100) if total_ic > 0 else 0
    qtd_ic = len(df_ic)
    qtd_pendentes = len(df_ic[df_ic['SALDO'] > 0])

    # Vencimentos
    df_vencidos = df_ic[df_ic['STATUS'] == 'Vencido']
    valor_vencido = df_vencidos['SALDO'].sum()
    qtd_vencidos = len(df_vencidos)
    dias_atraso_medio = df_vencidos['DIAS_ATRASO'].mean() if len(df_vencidos) > 0 else 0

    hoje_date = hoje.date()
    df_vence_hoje = df_ic[(df_ic['SALDO'] > 0) & (df_ic['VENCIMENTO'].dt.date == hoje_date)]
    df_vence_amanha = df_ic[(df_ic['SALDO'] > 0) & (df_ic['VENCIMENTO'].dt.date == hoje_date + timedelta(days=1))]
    df_vence_semana = df_ic[
        (df_ic['SALDO'] > 0) &
        (df_ic['VENCIMENTO'].dt.date > hoje_date) &
        (df_ic['VENCIMENTO'].dt.date <= hoje_date + timedelta(days=7))
    ]
    df_vence_mes = df_ic[
        (df_ic['SALDO'] > 0) &
        (df_ic['VENCIMENTO'].dt.date > hoje_date + timedelta(days=7)) &
        (df_ic['VENCIMENTO'].dt.date <= hoje_date + timedelta(days=30))
    ]

    # ========== CARDS PRINCIPAIS ==========
    st.markdown(f"""
    <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 1rem; margin-bottom: 1.5rem;">
        <div style="background: linear-gradient(135deg, {cores['primaria']}20 0%, {cores['primaria']}10 100%);
                    border: 1px solid {cores['primaria']}40; border-radius: 12px; padding: 1.25rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0 0 0.5rem 0;">Total Intercompany</p>
            <p style="color: {cores['texto']}; font-size: 1.5rem; font-weight: 700; margin: 0;">{formatar_moeda(total_ic)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0.25rem 0 0 0;">{pct_ic:.1f}% do total geral | {qtd_ic} títulos</p>
        </div>
        <div style="background: linear-gradient(135deg, {cores['sucesso']}20 0%, {cores['sucesso']}10 100%);
                    border: 1px solid {cores['sucesso']}40; border-radius: 12px; padding: 1.25rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0 0 0.5rem 0;">Pago</p>
            <p style="color: {cores['sucesso']}; font-size: 1.5rem; font-weight: 700; margin: 0;">{formatar_moeda(pago_ic)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0.25rem 0 0 0;">{pct_pago:.1f}% liquidado</p>
        </div>
        <div style="background: linear-gradient(135deg, {cores['alerta']}20 0%, {cores['alerta']}10 100%);
                    border: 1px solid {cores['alerta']}40; border-radius: 12px; padding: 1.25rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0 0 0.5rem 0;">Saldo Pendente</p>
            <p style="color: {cores['alerta']}; font-size: 1.5rem; font-weight: 700; margin: 0;">{formatar_moeda(saldo_ic)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0.25rem 0 0 0;">{qtd_pendentes} títulos pendentes</p>
        </div>
        <div style="background: linear-gradient(135deg, {cores['perigo']}20 0%, {cores['perigo']}10 100%);
                    border: 1px solid {cores['perigo']}40; border-radius: 12px; padding: 1.25rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0 0 0.5rem 0;">Vencido</p>
            <p style="color: {cores['perigo']}; font-size: 1.5rem; font-weight: 700; margin: 0;">{formatar_moeda(valor_vencido)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0.25rem 0 0 0;">{qtd_vencidos} títulos | {dias_atraso_medio:.0f} dias atraso médio</p>
        </div>
        <div style="background: linear-gradient(135deg, {cores['info']}20 0%, {cores['info']}10 100%);
                    border: 1px solid {cores['info']}40; border-radius: 12px; padding: 1.25rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0 0 0.5rem 0;">Ticket Médio</p>
            <p style="color: {cores['info']}; font-size: 1.5rem; font-weight: 700; margin: 0;">{formatar_moeda(total_ic / qtd_ic if qtd_ic > 0 else 0)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0.25rem 0 0 0;">por título</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ========== ALERTAS DE VENCIMENTO ==========
    st.markdown(f"""
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.75rem; margin-bottom: 1.5rem;">
        <div style="background: {cores['perigo']}15; border: 1px solid {cores['perigo']}50;
                    border-radius: 10px; padding: 1rem; text-align: center;">
            <p style="color: {cores['perigo']}; font-size: 0.7rem; font-weight: 600; margin: 0; text-transform: uppercase;">
                Vencido</p>
            <p style="color: {cores['perigo']}; font-size: 1.4rem; font-weight: 700; margin: 0.25rem 0;">
                {formatar_moeda(valor_vencido)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">
                {qtd_vencidos} títulos</p>
        </div>
        <div style="background: {cores['alerta']}15; border: 1px solid {cores['alerta']}50;
                    border-radius: 10px; padding: 1rem; text-align: center;">
            <p style="color: {cores['alerta']}; font-size: 0.7rem; font-weight: 600; margin: 0; text-transform: uppercase;">
                Vence Hoje</p>
            <p style="color: {cores['alerta']}; font-size: 1.4rem; font-weight: 700; margin: 0.25rem 0;">
                {formatar_moeda(df_vence_hoje['SALDO'].sum())}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">
                {len(df_vence_hoje)} títulos</p>
        </div>
        <div style="background: {cores['info']}15; border: 1px solid {cores['info']}50;
                    border-radius: 10px; padding: 1rem; text-align: center;">
            <p style="color: {cores['info']}; font-size: 0.7rem; font-weight: 600; margin: 0; text-transform: uppercase;">
                Próximos 7 dias</p>
            <p style="color: {cores['info']}; font-size: 1.4rem; font-weight: 700; margin: 0.25rem 0;">
                {formatar_moeda(df_vence_semana['SALDO'].sum())}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">
                {len(df_vence_semana)} títulos</p>
        </div>
        <div style="background: {cores['sucesso']}15; border: 1px solid {cores['sucesso']}50;
                    border-radius: 10px; padding: 1rem; text-align: center;">
            <p style="color: {cores['sucesso']}; font-size: 0.7rem; font-weight: 600; margin: 0; text-transform: uppercase;">
                Próximos 30 dias</p>
            <p style="color: {cores['sucesso']}; font-size: 1.4rem; font-weight: 700; margin: 0.25rem 0;">
                {formatar_moeda(df_vence_mes['SALDO'].sum())}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">
                {len(df_vence_mes)} títulos</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ========== ABAS DETALHADAS ==========
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Visão Geral",
        "🏢 Por Empresa",
        "📅 Evolução Temporal",
        "🏭 Por Filial",
        "📋 Títulos Detalhados"
    ])

    with tab1:
        _render_visao_geral(df_ic, cores, hoje)

    with tab2:
        _render_por_empresa(df_ic, cores)

    with tab3:
        _render_evolucao_temporal(df_ic, cores)

    with tab4:
        _render_por_filial(df_ic, cores)

    with tab5:
        _render_titulos_detalhados(df_ic, cores)


def _render_visao_geral(df_ic, cores, hoje):
    """Visão geral com gráficos principais"""

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Saldo por Tipo de Empresa")
        df_pendente = df_ic[df_ic['SALDO'] > 0]

        if len(df_pendente) > 0:
            df_tipo = df_pendente.groupby('TIPO_INTERCOMPANY').agg({
                'SALDO': 'sum',
                'VALOR_ORIGINAL': 'sum',
                'FORNECEDOR': 'count'
            }).reset_index()
            df_tipo.columns = ['Tipo', 'Saldo', 'Total', 'Qtd']
            df_tipo['% Pago'] = ((df_tipo['Total'] - df_tipo['Saldo']) / df_tipo['Total'] * 100).round(1)
            df_tipo = df_tipo.sort_values('Saldo', ascending=True)

            cores_tipo = {
                'Empresas Progresso': cores['primaria'],
                'Ouro Branco': cores['sucesso'],
                'Fazenda Peninsula': '#84cc16',
                'Hotelaria': cores['info'],
                'Outros': cores['texto_secundario']
            }

            fig = go.Figure()
            fig.add_trace(go.Bar(
                y=df_tipo['Tipo'],
                x=df_tipo['Saldo'],
                orientation='h',
                marker_color=[cores_tipo.get(t, cores['info']) for t in df_tipo['Tipo']],
                text=[f"{formatar_moeda(v)} ({p:.0f}% pago)" for v, p in zip(df_tipo['Saldo'], df_tipo['% Pago'])],
                textposition='outside',
                textfont=dict(size=10)
            ))

            fig.update_layout(
                criar_layout(300),
                yaxis={'categoryorder': 'total ascending'},
                margin=dict(l=10, r=120, t=10, b=10)
            )

            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("##### Distribuição por Status")

        df_status = df_ic.groupby('STATUS').agg({
            'SALDO': 'sum',
            'FORNECEDOR': 'count'
        }).reset_index()
        df_status.columns = ['Status', 'Valor', 'Qtd']

        cores_status = {
            'Vencido': cores['perigo'],
            'A Vencer': cores['sucesso'],
            'Pago': cores['info']
        }

        fig = go.Figure(data=[go.Pie(
            labels=df_status['Status'],
            values=df_status['Valor'],
            hole=0.5,
            marker_colors=[cores_status.get(s, cores['texto_secundario']) for s in df_status['Status']],
            textinfo='percent+label',
            textfont_size=11,
            hovertemplate='<b>%{label}</b><br>Valor: %{value:,.2f}<br>%{percent}<extra></extra>'
        )])

        fig.update_layout(
            criar_layout(300),
            showlegend=False,
            margin=dict(l=10, r=10, t=10, b=10)
        )

        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Segunda linha: Fluxo de vencimentos + Top empresas
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Fluxo de Vencimentos (Próximas Semanas)")
        _render_fluxo_vencimentos(df_ic, cores, hoje)

    with col2:
        st.markdown("##### Top 10 Maiores Saldos Pendentes")
        _render_top_empresas(df_ic, cores)

    st.divider()

    # Terceira linha: Análise de atrasos
    st.markdown("##### Análise de Títulos Vencidos")
    _render_analise_vencidos(df_ic, cores)


def _render_fluxo_vencimentos(df_ic, cores, hoje):
    """Fluxo de vencimentos detalhado"""
    df_pendente = df_ic[df_ic['SALDO'] > 0].copy()

    if len(df_pendente) == 0:
        st.info("Sem saldo pendente")
        return

    hoje_date = hoje.date()

    def get_semana(data):
        if pd.isna(data):
            return 'Sem data'
        data_date = data.date() if hasattr(data, 'date') else data
        diff = (data_date - hoje_date).days
        if diff < 0:
            return 'Vencido'
        elif diff == 0:
            return 'Hoje'
        elif diff <= 7:
            return 'Semana 1'
        elif diff <= 14:
            return 'Semana 2'
        elif diff <= 21:
            return 'Semana 3'
        elif diff <= 30:
            return 'Semana 4'
        else:
            return '+30 dias'

    df_pendente['SEMANA'] = df_pendente['VENCIMENTO'].apply(get_semana)

    ordem = ['Vencido', 'Hoje', 'Semana 1', 'Semana 2', 'Semana 3', 'Semana 4', '+30 dias']
    df_fluxo = df_pendente.groupby('SEMANA').agg({
        'SALDO': 'sum',
        'FORNECEDOR': 'count'
    }).reindex(ordem, fill_value=0).reset_index()
    df_fluxo.columns = ['Período', 'Saldo', 'Qtd']

    cores_fluxo = [cores['perigo'], cores['alerta'], cores['info'], cores['info'],
                   cores['sucesso'], cores['sucesso'], cores['texto_secundario']]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_fluxo['Período'],
        y=df_fluxo['Saldo'],
        marker_color=cores_fluxo,
        text=[f"{formatar_moeda(v)}<br>({q} tít)" for v, q in zip(df_fluxo['Saldo'], df_fluxo['Qtd'])],
        textposition='outside',
        textfont=dict(size=9)
    ))

    fig.update_layout(
        criar_layout(280),
        margin=dict(l=10, r=10, t=10, b=40),
        xaxis_tickangle=-30
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_top_empresas(df_ic, cores):
    """Top empresas com maior saldo"""
    df_pendente = df_ic[df_ic['SALDO'] > 0]

    if len(df_pendente) == 0:
        st.info("Sem saldo pendente")
        return

    df_emp = df_pendente.groupby('NOME_FORNECEDOR').agg({
        'SALDO': 'sum',
        'VALOR_ORIGINAL': 'sum',
        'FORNECEDOR': 'count'
    }).reset_index()
    df_emp.columns = ['Empresa', 'Saldo', 'Total', 'Qtd']
    df_emp['% Pago'] = ((df_emp['Total'] - df_emp['Saldo']) / df_emp['Total'] * 100).round(1)
    df_emp = df_emp.sort_values('Saldo', ascending=True).tail(10)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=df_emp['Empresa'].str[:30],
        x=df_emp['Saldo'],
        orientation='h',
        marker_color=cores['primaria'],
        text=[f"{formatar_moeda(v)}" for v in df_emp['Saldo']],
        textposition='outside',
        textfont=dict(size=9)
    ))

    fig.update_layout(
        criar_layout(280),
        yaxis={'categoryorder': 'total ascending'},
        margin=dict(l=10, r=80, t=10, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_analise_vencidos(df_ic, cores):
    """Análise detalhada de títulos vencidos"""
    df_vencidos = df_ic[df_ic['STATUS'] == 'Vencido'].copy()

    if len(df_vencidos) == 0:
        st.success("Nenhum título vencido! Parabéns!")
        return

    col1, col2, col3 = st.columns(3)

    with col1:
        # Por faixa de atraso
        st.markdown("###### Por Faixa de Atraso")

        def faixa_atraso(dias):
            if dias <= 7:
                return '1-7 dias'
            elif dias <= 15:
                return '8-15 dias'
            elif dias <= 30:
                return '16-30 dias'
            elif dias <= 60:
                return '31-60 dias'
            elif dias <= 90:
                return '61-90 dias'
            else:
                return '+90 dias'

        df_vencidos['FAIXA'] = df_vencidos['DIAS_ATRASO'].apply(faixa_atraso)

        df_faixa = df_vencidos.groupby('FAIXA').agg({
            'SALDO': 'sum',
            'FORNECEDOR': 'count'
        }).reset_index()
        df_faixa.columns = ['Faixa', 'Valor', 'Qtd']

        ordem_faixa = ['1-7 dias', '8-15 dias', '16-30 dias', '31-60 dias', '61-90 dias', '+90 dias']
        df_faixa['Faixa'] = pd.Categorical(df_faixa['Faixa'], categories=ordem_faixa, ordered=True)
        df_faixa = df_faixa.sort_values('Faixa')

        df_faixa_exib = df_faixa.copy()
        df_faixa_exib['Valor'] = df_faixa_exib['Valor'].apply(lambda x: formatar_moeda(x, completo=True))

        st.dataframe(df_faixa_exib, use_container_width=True, hide_index=True, height=230)

    with col2:
        # Top vencidos por empresa
        st.markdown("###### Top Empresas com Vencidos")

        df_venc_emp = df_vencidos.groupby('NOME_FORNECEDOR').agg({
            'SALDO': 'sum',
            'DIAS_ATRASO': 'mean',
            'FORNECEDOR': 'count'
        }).reset_index()
        df_venc_emp.columns = ['Empresa', 'Valor', 'Dias Médio', 'Qtd']
        df_venc_emp = df_venc_emp.sort_values('Valor', ascending=False).head(5)

        df_venc_emp_exib = df_venc_emp.copy()
        df_venc_emp_exib['Valor'] = df_venc_emp_exib['Valor'].apply(lambda x: formatar_moeda(x, completo=True))
        df_venc_emp_exib['Dias Médio'] = df_venc_emp_exib['Dias Médio'].apply(lambda x: f"{x:.0f}")
        df_venc_emp_exib['Empresa'] = df_venc_emp_exib['Empresa'].str[:25]

        st.dataframe(df_venc_emp_exib, use_container_width=True, hide_index=True, height=230)

    with col3:
        # Por filial
        st.markdown("###### Vencidos por Filial")

        df_venc_fil = df_vencidos.groupby('NOME_FILIAL').agg({
            'SALDO': 'sum',
            'FORNECEDOR': 'count'
        }).reset_index()
        df_venc_fil.columns = ['Filial', 'Valor', 'Qtd']
        df_venc_fil = df_venc_fil.sort_values('Valor', ascending=False)

        df_venc_fil_exib = df_venc_fil.copy()
        df_venc_fil_exib['Valor'] = df_venc_fil_exib['Valor'].apply(lambda x: formatar_moeda(x, completo=True))
        df_venc_fil_exib['Filial'] = df_venc_fil_exib['Filial'].str[:20]

        st.dataframe(df_venc_fil_exib, use_container_width=True, hide_index=True, height=230)


def _render_por_empresa(df_ic, cores):
    """Análise detalhada por empresa"""

    # Filtros
    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        tipos = ['Todos'] + sorted([str(x) for x in df_ic['TIPO_INTERCOMPANY'].unique().tolist()])
        filtro_tipo = st.selectbox("Tipo de Empresa", tipos, key="emp_tipo")

    with col2:
        status_opcoes = ['Todos', 'Pendente', 'Vencido', 'Pago']
        filtro_status = st.selectbox("Status", status_opcoes, key="emp_status")

    # Aplicar filtros
    df_show = df_ic.copy()

    if filtro_tipo != 'Todos':
        df_show = df_show[df_show['TIPO_INTERCOMPANY'] == filtro_tipo]

    if filtro_status == 'Pendente':
        df_show = df_show[df_show['SALDO'] > 0]
    elif filtro_status == 'Vencido':
        df_show = df_show[df_show['STATUS'] == 'Vencido']
    elif filtro_status == 'Pago':
        df_show = df_show[df_show['SALDO'] == 0]

    # Agrupar por fornecedor
    df_emp = df_show.groupby(['NOME_FORNECEDOR', 'TIPO_INTERCOMPANY']).agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'FORNECEDOR': 'count',
        'EMISSAO': 'min',
        'VENCIMENTO': 'max'
    }).reset_index()
    df_emp.columns = ['Empresa', 'Tipo', 'Total', 'Saldo', 'Qtd', 'Primeira Emissão', 'Último Vencimento']
    df_emp['Pago'] = df_emp['Total'] - df_emp['Saldo']
    df_emp['% Pago'] = ((df_emp['Pago'] / df_emp['Total']) * 100).fillna(0).round(1)
    df_emp = df_emp.sort_values('Total', ascending=False)

    # Métricas
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Empresas", len(df_emp))
    col2.metric("Total", formatar_moeda(df_emp['Total'].sum()))
    col3.metric("Pago", formatar_moeda(df_emp['Pago'].sum()))
    col4.metric("Saldo Pendente", formatar_moeda(df_emp['Saldo'].sum()))
    col5.metric("Títulos", formatar_numero(df_emp['Qtd'].sum()))

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Por Valor Total")

        df_chart = df_emp.head(15).sort_values('Total', ascending=True)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=df_chart['Empresa'].str[:30],
            x=df_chart['Pago'],
            orientation='h',
            name='Pago',
            marker_color=cores['sucesso']
        ))
        fig.add_trace(go.Bar(
            y=df_chart['Empresa'].str[:30],
            x=df_chart['Saldo'],
            orientation='h',
            name='Pendente',
            marker_color=cores['alerta']
        ))

        fig.update_layout(
            criar_layout(400, barmode='stack'),
            yaxis={'categoryorder': 'total ascending'},
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
            margin=dict(l=10, r=10, t=40, b=10)
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("##### Distribuição por Tipo")

        df_tipo = df_emp.groupby('Tipo').agg({
            'Total': 'sum',
            'Saldo': 'sum',
            'Qtd': 'sum'
        }).reset_index()

        cores_tipo = {
            'Empresas Progresso': cores['primaria'],
            'Ouro Branco': cores['sucesso'],
            'Fazenda Peninsula': '#84cc16',
            'Hotelaria': cores['info'],
            'Outros': cores['texto_secundario']
        }

        fig = go.Figure(data=[go.Pie(
            labels=df_tipo['Tipo'],
            values=df_tipo['Total'],
            hole=0.5,
            marker_colors=[cores_tipo.get(t, cores['info']) for t in df_tipo['Tipo']],
            textinfo='percent+label',
            textfont_size=11
        )])

        fig.update_layout(
            criar_layout(400),
            showlegend=False,
            margin=dict(l=10, r=10, t=10, b=10)
        )

        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Tabela completa
    st.markdown("##### Tabela Detalhada por Empresa")

    df_exib = pd.DataFrame({
        'Empresa': df_emp['Empresa'],
        'Tipo': df_emp['Tipo'],
        'Qtd': df_emp['Qtd'],
        'Total': df_emp['Total'].apply(lambda x: formatar_moeda(x, completo=True)),
        'Pago': df_emp['Pago'].apply(lambda x: formatar_moeda(x, completo=True)),
        'Saldo': df_emp['Saldo'].apply(lambda x: formatar_moeda(x, completo=True)),
        '% Pago': df_emp['% Pago'],
        'Primeira Emissão': pd.to_datetime(df_emp['Primeira Emissão']).dt.strftime('%d/%m/%Y'),
        'Último Vencimento': pd.to_datetime(df_emp['Último Vencimento']).dt.strftime('%d/%m/%Y')
    })

    st.dataframe(
        df_exib,
        use_container_width=True,
        hide_index=True,
        height=400,
        column_config={
            '% Pago': st.column_config.ProgressColumn(
                '% Pago',
                format='%.0f%%',
                min_value=0,
                max_value=100
            )
        }
    )


def _render_evolucao_temporal(df_ic, cores):
    """Evolução temporal das operações"""

    df_temp = df_ic.copy()
    df_temp['MES_ANO'] = df_temp['EMISSAO'].dt.to_period('M')

    # Últimos 12 meses
    meses = sorted(df_temp['MES_ANO'].unique())[-12:]
    df_temp = df_temp[df_temp['MES_ANO'].isin(meses)]

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Evolução Mensal por Tipo")

        df_mensal = df_temp.groupby(['MES_ANO', 'TIPO_INTERCOMPANY']).agg({
            'VALOR_ORIGINAL': 'sum'
        }).reset_index()
        df_mensal['MES_ANO'] = df_mensal['MES_ANO'].astype(str)

        cores_tipo = {
            'Empresas Progresso': cores['primaria'],
            'Ouro Branco': cores['sucesso'],
            'Fazenda Peninsula': '#84cc16',
            'Hotelaria': cores['info'],
            'Outros': cores['texto_secundario']
        }

        fig = go.Figure()

        for tipo in df_mensal['TIPO_INTERCOMPANY'].unique():
            df_t = df_mensal[df_mensal['TIPO_INTERCOMPANY'] == tipo]
            fig.add_trace(go.Scatter(
                x=df_t['MES_ANO'],
                y=df_t['VALOR_ORIGINAL'],
                mode='lines+markers',
                name=tipo,
                line=dict(color=cores_tipo.get(tipo, cores['info']), width=2),
                marker=dict(size=8)
            ))

        fig.update_layout(
            criar_layout(350),
            xaxis_tickangle=-45,
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
            margin=dict(l=10, r=10, t=50, b=60)
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("##### Total Mensal Consolidado")

        df_total = df_temp.groupby('MES_ANO').agg({
            'VALOR_ORIGINAL': 'sum',
            'SALDO': 'sum',
            'FORNECEDOR': 'count'
        }).reset_index()
        df_total['MES_ANO'] = df_total['MES_ANO'].astype(str)
        df_total['PAGO'] = df_total['VALOR_ORIGINAL'] - df_total['SALDO']

        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=df_total['MES_ANO'],
            y=df_total['PAGO'],
            name='Pago',
            marker_color=cores['sucesso']
        ))

        fig.add_trace(go.Bar(
            x=df_total['MES_ANO'],
            y=df_total['SALDO'],
            name='Pendente',
            marker_color=cores['alerta']
        ))

        fig.update_layout(
            criar_layout(350, barmode='stack'),
            xaxis_tickangle=-45,
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
            margin=dict(l=10, r=10, t=50, b=60)
        )

        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Tabela por ano
    st.markdown("##### Resumo por Ano")

    df_ano = df_ic.groupby(df_ic['EMISSAO'].dt.year).agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'FORNECEDOR': 'count'
    }).reset_index()
    df_ano.columns = ['Ano', 'Total', 'Saldo', 'Qtd']
    df_ano['Pago'] = df_ano['Total'] - df_ano['Saldo']
    df_ano['% Pago'] = ((df_ano['Pago'] / df_ano['Total']) * 100).round(1)
    df_ano = df_ano.sort_values('Ano', ascending=False)

    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        df_ano_exib = pd.DataFrame({
            'Ano': df_ano['Ano'].astype(int),
            'Total': df_ano['Total'].apply(lambda x: formatar_moeda(x, completo=True)),
            'Pago': df_ano['Pago'].apply(lambda x: formatar_moeda(x, completo=True)),
            'Saldo': df_ano['Saldo'].apply(lambda x: formatar_moeda(x, completo=True)),
            'Qtd': df_ano['Qtd'],
            '% Pago': df_ano['% Pago']
        })

        st.dataframe(
            df_ano_exib,
            use_container_width=True,
            hide_index=True,
            column_config={
                '% Pago': st.column_config.ProgressColumn(
                    '% Pago',
                    format='%.0f%%',
                    min_value=0,
                    max_value=100
                )
            }
        )


def _render_por_filial(df_ic, cores):
    """Análise por filial"""

    df_filial = df_ic.groupby(['FILIAL', 'NOME_FILIAL']).agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'FORNECEDOR': 'count'
    }).reset_index()
    df_filial.columns = ['Cod', 'Filial', 'Total', 'Saldo', 'Qtd']
    df_filial['Pago'] = df_filial['Total'] - df_filial['Saldo']
    df_filial['% Pago'] = ((df_filial['Pago'] / df_filial['Total']) * 100).round(1)
    df_filial = df_filial.sort_values('Total', ascending=False)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Total por Filial")

        df_chart = df_filial.sort_values('Total', ascending=True)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=df_chart['Filial'].str[:25],
            x=df_chart['Pago'],
            orientation='h',
            name='Pago',
            marker_color=cores['sucesso']
        ))
        fig.add_trace(go.Bar(
            y=df_chart['Filial'].str[:25],
            x=df_chart['Saldo'],
            orientation='h',
            name='Pendente',
            marker_color=cores['alerta']
        ))

        fig.update_layout(
            criar_layout(350, barmode='stack'),
            yaxis={'categoryorder': 'total ascending'},
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
            margin=dict(l=10, r=10, t=40, b=10)
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("##### Participação por Filial")

        fig = go.Figure(data=[go.Pie(
            labels=df_filial['Filial'].str[:20],
            values=df_filial['Total'],
            hole=0.4,
            textinfo='percent',
            textfont_size=10
        )])

        fig.update_layout(
            criar_layout(350),
            legend=dict(orientation='v', yanchor='middle', y=0.5, xanchor='left', x=1.02, font=dict(size=9)),
            margin=dict(l=10, r=120, t=10, b=10)
        )

        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Matriz Filial x Tipo
    st.markdown("##### Matriz Filial x Tipo de Empresa")

    df_matrix = df_ic.pivot_table(
        index='NOME_FILIAL',
        columns='TIPO_INTERCOMPANY',
        values='SALDO',
        aggfunc='sum',
        fill_value=0
    )

    # Adicionar total
    df_matrix['TOTAL'] = df_matrix.sum(axis=1)
    df_matrix = df_matrix.sort_values('TOTAL', ascending=False)

    df_matrix_exib = df_matrix.copy()
    for col in df_matrix_exib.columns:
        df_matrix_exib[col] = df_matrix_exib[col].apply(lambda x: formatar_moeda(x, completo=True) if x > 0 else '-')

    st.dataframe(df_matrix_exib, use_container_width=True, height=350)


def _render_titulos_detalhados(df_ic, cores):
    """Tabela de títulos detalhados"""

    # Filtros
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        tipos = ['Todos'] + sorted([str(x) for x in df_ic['TIPO_INTERCOMPANY'].unique().tolist()])
        filtro_tipo = st.selectbox("Tipo", tipos, key="det_tipo")

    with col2:
        filiais = ['Todas'] + sorted([str(x) for x in df_ic['NOME_FILIAL'].dropna().unique().tolist()])
        filtro_filial = st.selectbox("Filial", filiais, key="det_filial")

    with col3:
        status_opcoes = ['Todos', 'Pendente', 'Vencido', 'Pago']
        filtro_status = st.selectbox("Status", status_opcoes, key="det_status")

    with col4:
        ordem_opcoes = ['Maior Valor', 'Maior Saldo', 'Mais Antigo', 'Vencimento Próximo', 'Maior Atraso']
        filtro_ordem = st.selectbox("Ordenar por", ordem_opcoes, key="det_ordem")

    # Aplicar filtros
    df_show = df_ic.copy()

    if filtro_tipo != 'Todos':
        df_show = df_show[df_show['TIPO_INTERCOMPANY'] == filtro_tipo]

    if filtro_filial != 'Todas':
        df_show = df_show[df_show['NOME_FILIAL'] == filtro_filial]

    if filtro_status == 'Pendente':
        df_show = df_show[df_show['SALDO'] > 0]
    elif filtro_status == 'Vencido':
        df_show = df_show[df_show['STATUS'] == 'Vencido']
    elif filtro_status == 'Pago':
        df_show = df_show[df_show['SALDO'] == 0]

    # Ordenar
    if filtro_ordem == 'Maior Valor':
        df_show = df_show.sort_values('VALOR_ORIGINAL', ascending=False)
    elif filtro_ordem == 'Maior Saldo':
        df_show = df_show.sort_values('SALDO', ascending=False)
    elif filtro_ordem == 'Mais Antigo':
        df_show = df_show.sort_values('EMISSAO', ascending=True)
    elif filtro_ordem == 'Vencimento Próximo':
        df_show = df_show.sort_values('VENCIMENTO', ascending=True)
    elif filtro_ordem == 'Maior Atraso':
        df_show = df_show.sort_values('DIAS_ATRASO', ascending=False)

    # Métricas
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Títulos", formatar_numero(len(df_show)))
    col2.metric("Total", formatar_moeda(df_show['VALOR_ORIGINAL'].sum()))
    col3.metric("Saldo", formatar_moeda(df_show['SALDO'].sum()))
    col4.metric("Vencidos", formatar_numero(len(df_show[df_show['STATUS'] == 'Vencido'])))

    if len(df_show[df_show['STATUS'] == 'Vencido']) > 0:
        col5.metric("Atraso Médio", f"{df_show[df_show['STATUS'] == 'Vencido']['DIAS_ATRASO'].mean():.0f} dias")
    else:
        col5.metric("Atraso Médio", "0 dias")

    st.divider()

    # Tabela
    colunas = ['NOME_FILIAL', 'NOME_FORNECEDOR', 'TIPO_INTERCOMPANY', 'NUMERO',
               'EMISSAO', 'VENCIMENTO', 'VALOR_ORIGINAL', 'SALDO', 'STATUS', 'DIAS_ATRASO']
    colunas_disp = [c for c in colunas if c in df_show.columns]

    df_exib = df_show[colunas_disp].head(200).copy()

    df_exib['EMISSAO'] = pd.to_datetime(df_exib['EMISSAO']).dt.strftime('%d/%m/%Y')
    df_exib['VENCIMENTO'] = pd.to_datetime(df_exib['VENCIMENTO']).dt.strftime('%d/%m/%Y')
    df_exib['VALOR_ORIGINAL'] = df_exib['VALOR_ORIGINAL'].apply(lambda x: formatar_moeda(x, completo=True))
    df_exib['SALDO'] = df_exib['SALDO'].apply(lambda x: formatar_moeda(x, completo=True))

    nomes = {
        'NOME_FILIAL': 'Filial',
        'NOME_FORNECEDOR': 'Empresa',
        'TIPO_INTERCOMPANY': 'Tipo',
        'NUMERO': 'Número',
        'EMISSAO': 'Emissão',
        'VENCIMENTO': 'Vencimento',
        'VALOR_ORIGINAL': 'Valor',
        'SALDO': 'Saldo',
        'STATUS': 'Status',
        'DIAS_ATRASO': 'Dias Atraso'
    }
    df_exib.columns = [nomes.get(c, c) for c in df_exib.columns]

    st.dataframe(df_exib, use_container_width=True, hide_index=True, height=450)
    st.caption(f"Exibindo {len(df_exib)} de {len(df_show)} títulos")
