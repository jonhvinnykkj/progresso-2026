"""
Aba Filtro por Periodo - Analise com selecao de datas por calendario
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

from config.theme import get_cores
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero


def render_filtro_periodo(df):
    """Renderiza a aba de Filtro por Periodo com calendario"""
    cores = get_cores()

    if len(df) == 0:
        st.warning("Nenhum dado disponivel.")
        return

    # ========== HEADER ==========
    st.markdown(f"""
    <div style="background: {cores['card']}; border-left: 4px solid {cores['primaria']};
                padding: 0.75rem 1rem; border-radius: 0 8px 8px 0; margin-bottom: 1.5rem;">
        <h4 style="color: {cores['texto']}; margin: 0;">Analise por Periodo Personalizado</h4>
        <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0;">
            Selecione um intervalo de datas para analise detalhada
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ========== FILTROS DE DATA ==========
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])

    # Datas min/max dos dados
    data_min = df['EMISSAO'].min().date()
    data_max = df['EMISSAO'].max().date()

    with col1:
        st.markdown(f"<p style='color: {cores['texto']}; font-size: 0.85rem; font-weight: 600; margin-bottom: 0.5rem;'>Data Inicial</p>", unsafe_allow_html=True)
        data_inicio = st.date_input(
            "Data Inicial",
            value=data_min,
            min_value=data_min,
            max_value=data_max,
            key="fp_data_inicio",
            label_visibility="collapsed"
        )

    with col2:
        st.markdown(f"<p style='color: {cores['texto']}; font-size: 0.85rem; font-weight: 600; margin-bottom: 0.5rem;'>Data Final</p>", unsafe_allow_html=True)
        data_fim = st.date_input(
            "Data Final",
            value=data_max,
            min_value=data_min,
            max_value=data_max,
            key="fp_data_fim",
            label_visibility="collapsed"
        )

    with col3:
        st.markdown(f"<p style='color: {cores['texto']}; font-size: 0.85rem; font-weight: 600; margin-bottom: 0.5rem;'>Tipo de Data</p>", unsafe_allow_html=True)
        tipo_data = st.selectbox(
            "Tipo de Data",
            ['Emissao', 'Vencimento'],
            key="fp_tipo_data",
            label_visibility="collapsed"
        )

    with col4:
        st.markdown(f"<p style='color: {cores['texto']}; font-size: 0.85rem; font-weight: 600; margin-bottom: 0.5rem;'>Atalhos</p>", unsafe_allow_html=True)
        atalho = st.selectbox(
            "Atalhos",
            ['Personalizado', 'Hoje', 'Ultimos 7 dias', 'Ultimos 30 dias', 'Este mes', 'Mes passado', 'Este ano'],
            key="fp_atalho",
            label_visibility="collapsed"
        )

    # Aplicar atalhos
    hoje = datetime.now().date()
    if atalho == 'Hoje':
        data_inicio = hoje
        data_fim = hoje
    elif atalho == 'Ultimos 7 dias':
        data_inicio = hoje - timedelta(days=7)
        data_fim = hoje
    elif atalho == 'Ultimos 30 dias':
        data_inicio = hoje - timedelta(days=30)
        data_fim = hoje
    elif atalho == 'Este mes':
        data_inicio = hoje.replace(day=1)
        data_fim = hoje
    elif atalho == 'Mes passado':
        primeiro_dia_mes = hoje.replace(day=1)
        data_fim = primeiro_dia_mes - timedelta(days=1)
        data_inicio = data_fim.replace(day=1)
    elif atalho == 'Este ano':
        data_inicio = hoje.replace(month=1, day=1)
        data_fim = hoje

    # Ajustar aos limites dos dados
    data_inicio = max(data_inicio, data_min)
    data_fim = min(data_fim, data_max)

    # ========== APLICAR FILTRO ==========
    col_data = 'EMISSAO' if tipo_data == 'Emissao' else 'VENCIMENTO'

    df_filtrado = df[
        (df[col_data].dt.date >= data_inicio) &
        (df[col_data].dt.date <= data_fim)
    ].copy()

    # Info do periodo
    dias_periodo = (data_fim - data_inicio).days + 1

    st.markdown(f"""
    <div style="background: {cores['primaria']}15; border: 1px solid {cores['primaria']}40;
                border-radius: 8px; padding: 0.75rem 1rem; margin: 1rem 0;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="color: {cores['texto']}; font-weight: 600;">
                Periodo: {data_inicio.strftime('%d/%m/%Y')} ate {data_fim.strftime('%d/%m/%Y')}
            </span>
            <span style="color: {cores['texto_secundario']}; font-size: 0.85rem;">
                {dias_periodo} dias | {formatar_numero(len(df_filtrado))} titulos | Filtro por {tipo_data}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if len(df_filtrado) == 0:
        st.warning("Nenhum registro encontrado no periodo selecionado.")
        return

    # ========== METRICAS DO PERIODO ==========
    _render_metricas_periodo(df_filtrado, cores)

    st.divider()

    # ========== GRAFICOS ==========
    col1, col2 = st.columns(2)

    with col1:
        _render_evolucao_diaria(df_filtrado, col_data, cores)

    with col2:
        _render_distribuicao_status(df_filtrado, cores)

    st.divider()

    # ========== COMPARATIVO ==========
    _render_comparativo_periodos(df, df_filtrado, data_inicio, data_fim, col_data, cores)

    st.divider()

    # ========== TABELA DETALHADA ==========
    _render_tabela_periodo(df_filtrado, cores)


def _render_metricas_periodo(df, cores):
    """Metricas do periodo selecionado"""

    total = df['VALOR_ORIGINAL'].sum()
    pendente = df['SALDO'].sum()
    recebido = total - pendente
    pct_recebido = (recebido / total * 100) if total > 0 else 0

    df_vencidos = df[df['STATUS'] == 'Vencido']
    vencido = df_vencidos['SALDO'].sum()
    qtd_vencidos = len(df_vencidos)

    st.markdown(f"""
    <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 1rem;">
        <div style="background: {cores['card']}; border-radius: 10px; padding: 1rem; text-align: center;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0;">Total Periodo</p>
            <p style="color: {cores['texto']}; font-size: 1.25rem; font-weight: 700; margin: 0.25rem 0 0 0;">{formatar_moeda(total)}</p>
        </div>
        <div style="background: {cores['card']}; border-radius: 10px; padding: 1rem; text-align: center;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0;">Recebido</p>
            <p style="color: {cores['sucesso']}; font-size: 1.25rem; font-weight: 700; margin: 0.25rem 0 0 0;">{formatar_moeda(recebido)}</p>
        </div>
        <div style="background: {cores['card']}; border-radius: 10px; padding: 1rem; text-align: center;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0;">Pendente</p>
            <p style="color: {cores['alerta']}; font-size: 1.25rem; font-weight: 700; margin: 0.25rem 0 0 0;">{formatar_moeda(pendente)}</p>
        </div>
        <div style="background: {cores['card']}; border-radius: 10px; padding: 1rem; text-align: center;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0;">Vencido</p>
            <p style="color: {cores['perigo']}; font-size: 1.25rem; font-weight: 700; margin: 0.25rem 0 0 0;">{formatar_moeda(vencido)}</p>
        </div>
        <div style="background: {cores['card']}; border-radius: 10px; padding: 1rem; text-align: center;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0;">Taxa Recebimento</p>
            <p style="color: {cores['info']}; font-size: 1.25rem; font-weight: 700; margin: 0.25rem 0 0 0;">{pct_recebido:.1f}%</p>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _render_evolucao_diaria(df, col_data, cores):
    """Evolucao diaria no periodo"""
    st.markdown("##### Evolucao Diaria")

    df_dia = df.groupby(df[col_data].dt.date).agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum'
    }).reset_index()
    df_dia.columns = ['Data', 'Total', 'Pendente']
    df_dia['Recebido'] = df_dia['Total'] - df_dia['Pendente']

    if len(df_dia) == 0:
        st.info("Sem dados para o grafico")
        return

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df_dia['Data'],
        y=df_dia['Total'],
        mode='lines+markers',
        name='Total',
        line=dict(color=cores['info'], width=2),
        marker=dict(size=6)
    ))

    fig.add_trace(go.Scatter(
        x=df_dia['Data'],
        y=df_dia['Recebido'],
        mode='lines+markers',
        name='Recebido',
        line=dict(color=cores['sucesso'], width=2),
        marker=dict(size=6),
        fill='tozeroy',
        fillcolor=f"{cores['sucesso']}20"
    ))

    fig.update_layout(
        criar_layout(300),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=30, b=30),
        xaxis_tickangle=-45
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_distribuicao_status(df, cores):
    """Distribuicao por status no periodo"""
    st.markdown("##### Distribuicao por Status")

    df_status = df.groupby('STATUS')['SALDO'].sum().reset_index()
    df_status.columns = ['Status', 'Valor']
    df_status = df_status[df_status['Valor'] > 0].sort_values('Valor', ascending=True)

    cores_status = {
        'Recebido': cores['sucesso'],
        'Vencido': cores['perigo'],
        'Vence em 7 dias': cores['alerta'],
        'Vence em 15 dias': '#f59e0b',
        'Vence em 30 dias': cores['info'],
        'Vence em 60 dias': '#8b5cf6',
        'Vence em +60 dias': cores['texto_secundario']
    }

    fig = go.Figure(go.Bar(
        y=df_status['Status'],
        x=df_status['Valor'],
        orientation='h',
        marker_color=[cores_status.get(s, cores['info']) for s in df_status['Status']],
        text=[formatar_moeda(v) for v in df_status['Valor']],
        textposition='outside',
        textfont=dict(size=9)
    ))

    fig.update_layout(
        criar_layout(300),
        margin=dict(l=10, r=80, t=10, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_comparativo_periodos(df_total, df_filtrado, data_inicio, data_fim, col_data, cores):
    """Comparativo com periodo anterior"""
    st.markdown("##### Comparativo com Periodo Anterior")

    # Calcular periodo anterior de mesmo tamanho
    dias = (data_fim - data_inicio).days + 1
    data_inicio_ant = data_inicio - timedelta(days=dias)
    data_fim_ant = data_inicio - timedelta(days=1)

    df_anterior = df_total[
        (df_total[col_data].dt.date >= data_inicio_ant) &
        (df_total[col_data].dt.date <= data_fim_ant)
    ]

    # Metricas atuais
    total_atual = df_filtrado['VALOR_ORIGINAL'].sum()
    recebido_atual = total_atual - df_filtrado['SALDO'].sum()
    qtd_atual = len(df_filtrado)

    # Metricas anteriores
    total_ant = df_anterior['VALOR_ORIGINAL'].sum()
    recebido_ant = total_ant - df_anterior['SALDO'].sum()
    qtd_ant = len(df_anterior)

    # Variacoes
    var_total = ((total_atual / total_ant - 1) * 100) if total_ant > 0 else 0
    var_recebido = ((recebido_atual / recebido_ant - 1) * 100) if recebido_ant > 0 else 0
    var_qtd = ((qtd_atual / qtd_ant - 1) * 100) if qtd_ant > 0 else 0

    col1, col2, col3 = st.columns(3)

    with col1:
        delta_color = "normal" if var_total >= 0 else "inverse"
        st.metric(
            "Total Emitido",
            formatar_moeda(total_atual),
            f"{var_total:+.1f}% vs periodo anterior",
            delta_color=delta_color
        )

    with col2:
        delta_color = "normal" if var_recebido >= 0 else "inverse"
        st.metric(
            "Total Recebido",
            formatar_moeda(recebido_atual),
            f"{var_recebido:+.1f}% vs periodo anterior",
            delta_color=delta_color
        )

    with col3:
        delta_color = "normal" if var_qtd >= 0 else "inverse"
        st.metric(
            "Quantidade Titulos",
            formatar_numero(qtd_atual),
            f"{var_qtd:+.1f}% vs periodo anterior",
            delta_color=delta_color
        )

    st.caption(f"Periodo anterior: {data_inicio_ant.strftime('%d/%m/%Y')} a {data_fim_ant.strftime('%d/%m/%Y')}")


def _render_tabela_periodo(df, cores):
    """Tabela detalhada do periodo"""
    st.markdown("##### Detalhamento do Periodo")

    col1, col2 = st.columns(2)

    with col1:
        ordenar = st.selectbox(
            "Ordenar por",
            ['Maior Valor', 'Mais Recente', 'Maior Atraso'],
            key="fp_ordenar"
        )

    with col2:
        qtd = st.selectbox("Exibir", [20, 50, 100], key="fp_qtd")

    # Preparar dados
    col_cliente = 'NOME_CLIENTE' if 'NOME_CLIENTE' in df.columns else 'NOME_FORNECEDOR'
    colunas = ['NOME_FILIAL', col_cliente, 'DESCRICAO', 'EMISSAO', 'VENCIMENTO', 'VALOR_ORIGINAL', 'SALDO', 'STATUS']
    colunas_disp = [c for c in colunas if c in df.columns]

    df_show = df[colunas_disp].copy()

    if ordenar == 'Maior Valor':
        df_show = df_show.nlargest(qtd, 'VALOR_ORIGINAL')
    elif ordenar == 'Mais Recente':
        df_show = df_show.nlargest(qtd, 'EMISSAO')
    else:
        df_show = df_show.sort_values('VENCIMENTO', ascending=True).head(qtd)

    # Formatar
    df_show['EMISSAO'] = pd.to_datetime(df_show['EMISSAO']).dt.strftime('%d/%m/%Y')
    df_show['VENCIMENTO'] = pd.to_datetime(df_show['VENCIMENTO']).dt.strftime('%d/%m/%Y')
    df_show['VALOR_ORIGINAL'] = df_show['VALOR_ORIGINAL'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['SALDO'] = df_show['SALDO'].apply(lambda x: formatar_moeda(x, completo=True))

    nomes = {
        'NOME_FILIAL': 'Filial',
        'NOME_CLIENTE': 'Cliente',
        'NOME_FORNECEDOR': 'Cliente',
        'DESCRICAO': 'Categoria',
        'EMISSAO': 'Emissao',
        'VENCIMENTO': 'Vencimento',
        'VALOR_ORIGINAL': 'Valor',
        'SALDO': 'Saldo',
        'STATUS': 'Status'
    }
    df_show.columns = [nomes.get(c, c) for c in df_show.columns]

    st.dataframe(df_show, use_container_width=True, hide_index=True, height=400)
    st.caption(f"Exibindo {len(df_show)} de {len(df)} registros no periodo")
