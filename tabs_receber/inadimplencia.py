"""
Aba Inadimplencia - Recuperacao de Credito e Comportamento de Pagamento
Foco: Tendencia | Sazonalidade | Historico | Previsao | Comportamento
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta

from config.theme import get_cores
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero


def render_inadimplencia(df):
    """Renderiza a aba de Inadimplencia - Recuperacao de Credito"""
    cores = get_cores()

    if len(df) == 0:
        st.warning("Nenhum dado disponivel.")
        return

    df = df.copy()
    hoje = datetime.now()
    col_cliente = 'NOME_CLIENTE'

    # Separar dados
    df_pendentes = df[df['SALDO'] > 0].copy()
    df_vencidos = df[df['DIAS_ATRASO'] > 0].copy()

    # ========== HEADER ==========
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, {cores['card']}, {cores['fundo']});
                border-left: 4px solid {cores['alerta']}; border-radius: 0 10px 10px 0;
                padding: 1rem; margin-bottom: 1rem;">
        <h4 style="color: {cores['texto']}; margin: 0;">Recuperacao de Credito & Comportamento</h4>
        <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0.25rem 0 0 0;">
            Tendencia | Sazonalidade | Historico | Previsao de recebimento
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ========== PAINEL DE RECUPERACAO ==========
    _render_painel_recuperacao(df, df_vencidos, cores)

    st.divider()

    # ========== TENDENCIA + SAZONALIDADE ==========
    col1, col2 = st.columns(2)

    with col1:
        _render_tendencia_inadimplencia(df, cores)

    with col2:
        _render_sazonalidade_inadimplencia(df, cores)

    st.divider()

    # ========== HISTORICO + COMPORTAMENTO ==========
    col1, col2 = st.columns(2)

    with col1:
        _render_historico_recebimentos(df, cores)

    with col2:
        _render_comportamento_pagamento(df, col_cliente, cores)

    st.divider()

    # ========== PREVISAO DE RECEBIMENTO ==========
    _render_previsao_recebimento(df_pendentes, cores)

    st.divider()

    # ========== ANALISE DE RECUPERACAO ==========
    col1, col2 = st.columns(2)

    with col1:
        _render_taxa_recuperacao(df, cores)

    with col2:
        _render_tempo_medio_recebimento(df, cores)

    st.divider()

    # ========== CLIENTES - PERFIL DE PAGAMENTO ==========
    _render_perfil_pagamento_cliente(df, col_cliente, cores)

    st.divider()

    # ========== LISTA DE COBRANCA ==========
    _render_lista_cobranca(df_vencidos, col_cliente, cores)


def _render_painel_recuperacao(df, df_vencidos, cores):
    """Painel principal de recuperacao"""

    # Taxa de inadimplencia = vencido / valor original emitido (nao sobre saldo pendente)
    total_emitido = df['VALOR_ORIGINAL'].sum()
    total_vencido = df_vencidos['SALDO'].sum()
    taxa_vencido = total_vencido / total_emitido * 100 if total_emitido > 0 else 0

    # Saldo pendente (para contexto)
    total_pendente = df['SALDO'].sum()

    # Calcular recuperacao geral (quanto ja foi pago do total emitido)
    total_recebido = total_emitido - total_pendente
    taxa_recuperacao = total_recebido / total_emitido * 100 if total_emitido > 0 else 0

    # Segmentar por urgencia
    venc_7d = df_vencidos[df_vencidos['DIAS_ATRASO'] <= 7]['SALDO'].sum()
    venc_30d = df_vencidos[(df_vencidos['DIAS_ATRASO'] > 7) & (df_vencidos['DIAS_ATRASO'] <= 30)]['SALDO'].sum()
    venc_60d = df_vencidos[(df_vencidos['DIAS_ATRASO'] > 30) & (df_vencidos['DIAS_ATRASO'] <= 60)]['SALDO'].sum()
    venc_90d = df_vencidos[df_vencidos['DIAS_ATRASO'] > 60]['SALDO'].sum()

    # Definir cor do painel
    if taxa_vencido > 30:
        cor_status = cores['perigo']
        status = "CRITICO"
    elif taxa_vencido > 15:
        cor_status = cores['alerta']
        status = "ATENCAO"
    elif taxa_vencido > 5:
        cor_status = '#fbbf24'
        status = "MONITORAR"
    else:
        cor_status = cores['sucesso']
        status = "SAUDAVEL"

    col1, col2, col3, col4, col5 = st.columns([1.5, 1, 1, 1, 1])

    with col1:
        st.markdown(f"""
        <div style="background: {cores['card']}; border: 2px solid {cor_status};
                    border-radius: 10px; padding: 1rem; text-align: center; height: 100%;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">STATUS CARTEIRA</p>
            <p style="color: {cor_status}; font-size: 1.8rem; font-weight: 800; margin: 0.25rem 0;">{status}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">
                {taxa_vencido:.1f}% vencido</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.metric("Total Vencido", formatar_moeda(total_vencido), f"{len(df_vencidos)} titulos", delta_color="inverse")

    with col3:
        st.metric("Taxa Recuperacao", f"{taxa_recuperacao:.1f}%", formatar_moeda(total_recebido))

    with col4:
        # Urgencia alta (ate 30 dias)
        urgente = venc_7d + venc_30d
        st.metric("Urgente (<=30d)", formatar_moeda(urgente), "Prioridade alta", delta_color="inverse" if urgente > 0 else "off")

    with col5:
        # Risco de perda (+60 dias)
        st.metric("Risco Perda (+60d)", formatar_moeda(venc_90d), "Provisionar", delta_color="inverse" if venc_90d > 0 else "off")


def _render_tendencia_inadimplencia(df, cores):
    """Tendencia da taxa de inadimplencia ao longo do tempo"""

    st.markdown("##### Tendencia de Inadimplencia")

    if 'EMISSAO' not in df.columns:
        st.info("Coluna EMISSAO nao disponivel")
        return

    df_temp = df.copy()
    df_temp['MES'] = df_temp['EMISSAO'].dt.to_period('M')

    # Calcular taxa de inadimplencia por mes
    dados_mes = []
    for mes in sorted(df_temp['MES'].unique())[-12:]:
        df_mes = df_temp[df_temp['MES'] == mes]
        total_saldo = df_mes['SALDO'].sum()
        total_vencido = df_mes[df_mes['DIAS_ATRASO'] > 0]['SALDO'].sum()
        taxa = total_vencido / total_saldo * 100 if total_saldo > 0 else 0

        dados_mes.append({
            'Mes': str(mes),
            'Taxa': taxa,
            'Vencido': total_vencido,
            'Total': total_saldo
        })

    if len(dados_mes) < 2:
        st.info("Dados insuficientes para tendencia")
        return

    df_trend = pd.DataFrame(dados_mes)

    # Calcular tendencia (regressao linear simples)
    x = list(range(len(df_trend)))
    y = df_trend['Taxa'].tolist()
    n = len(x)
    if n > 1:
        slope = (n * sum(x[i] * y[i] for i in range(n)) - sum(x) * sum(y)) / (n * sum(xi**2 for xi in x) - sum(x)**2)
        tendencia = "crescente" if slope > 0.5 else "decrescente" if slope < -0.5 else "estavel"
    else:
        tendencia = "estavel"
        slope = 0

    fig = go.Figure()

    # Barras de taxa
    cores_barra = [cores['perigo'] if t > 20 else cores['alerta'] if t > 10 else '#fbbf24' if t > 5 else cores['sucesso'] for t in df_trend['Taxa']]

    fig.add_trace(go.Bar(
        x=df_trend['Mes'],
        y=df_trend['Taxa'],
        marker_color=cores_barra,
        text=[f"{t:.1f}%" for t in df_trend['Taxa']],
        textposition='outside',
        textfont=dict(size=8),
        name='Taxa'
    ))

    # Linha de tendencia
    trend_line = [y[0] + slope * i for i in range(n)]
    fig.add_trace(go.Scatter(
        x=df_trend['Mes'],
        y=trend_line,
        mode='lines',
        name='Tendencia',
        line=dict(color=cores['texto_secundario'], dash='dash', width=2)
    ))

    # Linha de meta (10%)
    fig.add_hline(y=10, line_dash="dot", line_color=cores['sucesso'],
                  annotation_text="Meta 10%", annotation_position="right")

    fig.update_layout(
        criar_layout(280),
        yaxis=dict(title='% Inadimplencia', range=[0, max(df_trend['Taxa']) * 1.3 + 5]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=8)),
        margin=dict(l=10, r=10, t=40, b=60),
        xaxis_tickangle=-45,
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)

    # Insight de tendencia
    ultima = df_trend['Taxa'].iloc[-1]
    anterior = df_trend['Taxa'].iloc[-2] if len(df_trend) > 1 else ultima
    variacao = ultima - anterior

    if tendencia == "crescente":
        st.error(f"Tendencia de ALTA na inadimplencia ({slope:.2f}pp/mes)")
    elif tendencia == "decrescente":
        st.success(f"Tendencia de QUEDA na inadimplencia ({abs(slope):.2f}pp/mes)")
    else:
        st.info(f"Inadimplencia estavel | Ultimo mes: {ultima:.1f}%")


def _render_sazonalidade_inadimplencia(df, cores):
    """Analise de sazonalidade - em quais meses a inadimplencia e maior"""

    st.markdown("##### Sazonalidade da Inadimplencia")

    if 'EMISSAO' not in df.columns:
        st.info("Coluna EMISSAO nao disponivel")
        return

    df_temp = df.copy()
    df_temp['MES_NUM'] = df_temp['EMISSAO'].dt.month

    # Calcular media de inadimplencia por mes do ano
    dados_sazon = []
    meses_nome = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

    for mes in range(1, 13):
        df_mes = df_temp[df_temp['MES_NUM'] == mes]
        if len(df_mes) > 0:
            total_saldo = df_mes['SALDO'].sum()
            total_vencido = df_mes[df_mes['DIAS_ATRASO'] > 0]['SALDO'].sum()
            taxa = total_vencido / total_saldo * 100 if total_saldo > 0 else 0
        else:
            taxa = 0

        dados_sazon.append({
            'Mes_Num': mes,
            'Mes': meses_nome[mes - 1],
            'Taxa': taxa
        })

    df_sazon = pd.DataFrame(dados_sazon)

    # Identificar meses criticos
    media_geral = df_sazon['Taxa'].mean()
    df_sazon['Critico'] = df_sazon['Taxa'] > media_geral * 1.2

    # Cores baseadas na criticidade
    cores_barra = []
    for _, row in df_sazon.iterrows():
        if row['Taxa'] > media_geral * 1.3:
            cores_barra.append(cores['perigo'])
        elif row['Taxa'] > media_geral * 1.1:
            cores_barra.append(cores['alerta'])
        elif row['Taxa'] < media_geral * 0.8:
            cores_barra.append(cores['sucesso'])
        else:
            cores_barra.append(cores['info'])

    fig = go.Figure(go.Bar(
        x=df_sazon['Mes'],
        y=df_sazon['Taxa'],
        marker_color=cores_barra,
        text=[f"{t:.1f}%" for t in df_sazon['Taxa']],
        textposition='outside',
        textfont=dict(size=8)
    ))

    # Linha de media
    fig.add_hline(y=media_geral, line_dash="dash", line_color=cores['texto_secundario'],
                  annotation_text=f"Media: {media_geral:.1f}%", annotation_position="right")

    fig.update_layout(
        criar_layout(280),
        yaxis=dict(title='% Inadimplencia', range=[0, max(df_sazon['Taxa']) * 1.3 + 5]),
        margin=dict(l=10, r=10, t=10, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)

    # Identificar meses criticos
    meses_criticos = df_sazon[df_sazon['Taxa'] > media_geral * 1.2]['Mes'].tolist()
    meses_bons = df_sazon[df_sazon['Taxa'] < media_geral * 0.8]['Mes'].tolist()

    if meses_criticos:
        st.warning(f"Meses criticos: **{', '.join(meses_criticos)}** - inadimplencia acima da media")
    if meses_bons:
        st.success(f"Meses favoraveis: **{', '.join(meses_bons)}** - inadimplencia abaixo da media")


def _render_historico_recebimentos(df, cores):
    """Historico de recebimentos mensais"""

    st.markdown("##### Historico de Recebimentos")

    if 'EMISSAO' not in df.columns:
        st.info("Coluna EMISSAO nao disponivel")
        return

    df_temp = df.copy()
    df_temp['MES'] = df_temp['EMISSAO'].dt.to_period('M')

    # Agrupar por mes
    df_mes = df_temp.groupby('MES').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum'
    }).reset_index()

    df_mes['MES'] = df_mes['MES'].astype(str)
    df_mes['Recebido'] = df_mes['VALOR_ORIGINAL'] - df_mes['SALDO']
    df_mes['Taxa'] = (df_mes['Recebido'] / df_mes['VALOR_ORIGINAL'] * 100).fillna(0)

    # Ultimos 12 meses
    df_mes = df_mes.tail(12)

    if len(df_mes) < 2:
        st.info("Dados insuficientes")
        return

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df_mes['MES'],
        y=df_mes['Recebido'],
        name='Recebido',
        marker_color=cores['sucesso']
    ))

    fig.add_trace(go.Bar(
        x=df_mes['MES'],
        y=df_mes['SALDO'],
        name='Pendente',
        marker_color=cores['alerta']
    ))

    fig.add_trace(go.Scatter(
        x=df_mes['MES'],
        y=df_mes['Taxa'],
        mode='lines+markers+text',
        name='% Recebido',
        yaxis='y2',
        line=dict(color=cores['primaria'], width=2),
        marker=dict(size=6),
        text=[f"{t:.0f}%" for t in df_mes['Taxa']],
        textposition='top center',
        textfont=dict(size=8)
    ))

    fig.update_layout(
        criar_layout(280, barmode='stack'),
        yaxis=dict(title=''),
        yaxis2=dict(overlaying='y', side='right', showgrid=False, range=[0, 110], visible=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=8)),
        margin=dict(l=10, r=10, t=40, b=60),
        xaxis_tickangle=-45
    )

    st.plotly_chart(fig, use_container_width=True)

    # Media
    media_taxa = df_mes['Taxa'].mean()
    st.caption(f"Taxa media de recebimento: {media_taxa:.1f}%")


def _render_comportamento_pagamento(df, col_cliente, cores):
    """Comportamento de pagamento dos clientes"""

    st.markdown("##### Comportamento de Pagamento")

    # Analisar padroes
    df_cli = df.groupby(col_cliente).agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'DIAS_ATRASO': ['mean', 'max'],
        'EMISSAO': 'count'
    }).reset_index()
    df_cli.columns = [col_cliente, 'Valor', 'Saldo', 'Atraso_Medio', 'Atraso_Max', 'Qtd_Titulos']

    df_cli['Recebido'] = df_cli['Valor'] - df_cli['Saldo']
    df_cli['Taxa_Pgto'] = (df_cli['Recebido'] / df_cli['Valor'] * 100).fillna(0)

    # Classificar comportamento
    def classificar(row):
        if row['Taxa_Pgto'] >= 95 and row['Atraso_Medio'] <= 5:
            return 'Excelente', cores['sucesso']
        elif row['Taxa_Pgto'] >= 80 and row['Atraso_Medio'] <= 15:
            return 'Bom', cores['info']
        elif row['Taxa_Pgto'] >= 60 and row['Atraso_Medio'] <= 30:
            return 'Regular', '#fbbf24'
        elif row['Taxa_Pgto'] >= 40:
            return 'Ruim', cores['alerta']
        else:
            return 'Critico', cores['perigo']

    comportamentos = df_cli.apply(classificar, axis=1)
    df_cli['Comportamento'] = [c[0] for c in comportamentos]

    # Contar por comportamento
    df_comp = df_cli.groupby('Comportamento').agg({
        col_cliente: 'count',
        'Saldo': 'sum'
    }).reset_index()
    df_comp.columns = ['Comportamento', 'Clientes', 'Saldo']

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
    st.caption(f"{bons} de {total_cli} clientes ({bons/total_cli*100:.0f}%) com bom comportamento")


def _render_previsao_recebimento(df_pendentes, cores):
    """Previsao de recebimento baseada em vencimentos"""

    st.markdown(f"""
    <div style="background: {cores['card']}; border-left: 4px solid {cores['info']};
                padding: 0.75rem 1rem; border-radius: 0 8px 8px 0; margin-bottom: 1rem;">
        <h4 style="color: {cores['texto']}; margin: 0;">Previsao de Recebimento</h4>
        <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0;">
            Fluxo esperado baseado em vencimentos futuros
        </p>
    </div>
    """, unsafe_allow_html=True)

    if len(df_pendentes) == 0:
        st.info("Sem titulos pendentes")
        return

    hoje = datetime.now()

    # Filtrar apenas a vencer
    df_futuro = df_pendentes[df_pendentes['DIAS_ATRASO'] <= 0].copy()

    if len(df_futuro) == 0:
        st.warning("Todos os titulos pendentes estao vencidos")
        return

    # Agrupar por semana
    df_futuro['SEMANA'] = pd.to_datetime(df_futuro['VENCIMENTO']).dt.to_period('W')

    df_sem = df_futuro.groupby('SEMANA').agg({
        'SALDO': 'sum',
        'VALOR_ORIGINAL': 'count'
    }).reset_index()
    df_sem.columns = ['Semana', 'Valor', 'Qtd']
    df_sem['Semana'] = df_sem['Semana'].astype(str)

    # Proximas 8 semanas
    df_sem = df_sem.head(8)

    col1, col2 = st.columns([2, 1])

    with col1:
        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=df_sem['Semana'],
            y=df_sem['Valor'],
            marker_color=cores['sucesso'],
            text=[formatar_moeda(v) for v in df_sem['Valor']],
            textposition='outside',
            textfont=dict(size=9)
        ))

        # Linha de acumulado
        df_sem['Acum'] = df_sem['Valor'].cumsum()

        fig.add_trace(go.Scatter(
            x=df_sem['Semana'],
            y=df_sem['Acum'],
            mode='lines+markers',
            name='Acumulado',
            line=dict(color=cores['primaria'], width=2),
            yaxis='y2'
        ))

        fig.update_layout(
            criar_layout(280),
            yaxis=dict(title='Por Semana'),
            yaxis2=dict(title='Acumulado', overlaying='y', side='right', showgrid=False),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=8)),
            margin=dict(l=10, r=50, t=40, b=60),
            xaxis_tickangle=-45
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("##### Proximos 30 dias")

        # Previsao 30 dias
        data_limite = hoje + timedelta(days=30)
        df_30d = df_futuro[pd.to_datetime(df_futuro['VENCIMENTO']) <= data_limite]

        total_30d = df_30d['SALDO'].sum()
        qtd_30d = len(df_30d)

        st.metric("Previsto", formatar_moeda(total_30d), f"{qtd_30d} titulos")

        # Por semana
        for i, (_, row) in enumerate(df_sem.head(4).iterrows()):
            st.markdown(f"""
            <div style="background: {cores['card']}; border-radius: 6px; padding: 0.4rem 0.6rem;
                        margin-bottom: 0.3rem; display: flex; justify-content: space-between;">
                <span style="color: {cores['texto_secundario']}; font-size: 0.75rem;">Sem {i+1}</span>
                <span style="color: {cores['sucesso']}; font-size: 0.8rem; font-weight: 600;">{formatar_moeda(row['Valor'])}</span>
            </div>
            """, unsafe_allow_html=True)


def _render_taxa_recuperacao(df, cores):
    """Taxa de recuperacao por faixa de atraso"""

    st.markdown("##### Taxa de Recuperacao por Faixa")

    # Criar faixas
    df_temp = df.copy()

    def faixa_atraso(dias):
        if dias <= 0:
            return 'Em dia'
        elif dias <= 30:
            return '1-30 dias'
        elif dias <= 60:
            return '31-60 dias'
        elif dias <= 90:
            return '61-90 dias'
        else:
            return '+90 dias'

    df_temp['Faixa'] = df_temp['DIAS_ATRASO'].apply(faixa_atraso)

    df_faixa = df_temp.groupby('Faixa').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum'
    }).reset_index()

    df_faixa['Recebido'] = df_faixa['VALOR_ORIGINAL'] - df_faixa['SALDO']
    df_faixa['Taxa'] = (df_faixa['Recebido'] / df_faixa['VALOR_ORIGINAL'] * 100).fillna(0)

    ordem = ['Em dia', '1-30 dias', '31-60 dias', '61-90 dias', '+90 dias']
    df_faixa['Ordem'] = df_faixa['Faixa'].apply(lambda x: ordem.index(x) if x in ordem else 99)
    df_faixa = df_faixa.sort_values('Ordem')

    cores_faixa = [cores['sucesso'], '#fbbf24', cores['alerta'], '#f97316', cores['perigo']]

    fig = go.Figure(go.Bar(
        x=df_faixa['Faixa'],
        y=df_faixa['Taxa'],
        marker_color=cores_faixa[:len(df_faixa)],
        text=[f"{t:.0f}%" for t in df_faixa['Taxa']],
        textposition='outside',
        textfont=dict(size=10)
    ))

    fig.add_hline(y=80, line_dash="dash", line_color=cores['texto_secundario'],
                  annotation_text="Meta 80%", annotation_position="right")

    fig.update_layout(
        criar_layout(280),
        yaxis=dict(title='% Recuperado', range=[0, 110]),
        margin=dict(l=10, r=10, t=10, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)

    # Insight
    taxa_90d = df_faixa[df_faixa['Faixa'] == '+90 dias']['Taxa'].values
    if len(taxa_90d) > 0 and taxa_90d[0] < 50:
        st.warning(f"Titulos +90 dias tem apenas {taxa_90d[0]:.0f}% de recuperacao. Considere provisionar.")


def _render_tempo_medio_recebimento(df, cores):
    """Tempo medio de recebimento"""

    st.markdown("##### Tempo Medio de Recebimento")

    # Calcular dias ate recebimento (para titulos pagos)
    df_pagos = df[df['SALDO'] == 0].copy()

    if len(df_pagos) == 0:
        st.info("Sem titulos pagos para analise")
        return

    # Simular dias de recebimento (vencimento - emissao + atraso medio)
    df_pagos['Dias_Receb'] = (pd.to_datetime(df_pagos['VENCIMENTO']) - pd.to_datetime(df_pagos['EMISSAO'])).dt.days

    # Por categoria
    df_cat = df_pagos.groupby('DESCRICAO').agg({
        'Dias_Receb': 'mean',
        'VALOR_ORIGINAL': 'sum'
    }).nlargest(8, 'VALOR_ORIGINAL').reset_index()

    fig = go.Figure(go.Bar(
        y=df_cat['DESCRICAO'].str[:20],
        x=df_cat['Dias_Receb'],
        orientation='h',
        marker_color=cores['info'],
        text=[f"{d:.0f}d" for d in df_cat['Dias_Receb']],
        textposition='outside',
        textfont=dict(size=9)
    ))

    # Linha de media geral
    media_geral = df_pagos['Dias_Receb'].mean()
    fig.add_vline(x=media_geral, line_dash="dash", line_color=cores['texto_secundario'],
                  annotation_text=f"Media: {media_geral:.0f}d", annotation_position="top")

    fig.update_layout(
        criar_layout(280),
        yaxis={'autorange': 'reversed'},
        xaxis=dict(title='Dias'),
        margin=dict(l=10, r=60, t=10, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_perfil_pagamento_cliente(df, col_cliente, cores):
    """Perfil de pagamento detalhado por cliente"""

    st.markdown(f"""
    <div style="background: {cores['card']}; border-left: 4px solid {cores['primaria']};
                padding: 0.75rem 1rem; border-radius: 0 8px 8px 0; margin-bottom: 1rem;">
        <h4 style="color: {cores['texto']}; margin: 0;">Perfil de Pagamento - Clientes</h4>
        <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0;">
            Analise detalhada de comportamento por cliente
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Calcular metricas por cliente
    df_cli = df.groupby(col_cliente).agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'DIAS_ATRASO': ['mean', 'max', 'std'],
        'EMISSAO': 'count'
    }).reset_index()
    df_cli.columns = [col_cliente, 'Valor', 'Saldo', 'Atraso_Medio', 'Atraso_Max', 'Atraso_Var', 'Titulos']

    df_cli['Recebido'] = df_cli['Valor'] - df_cli['Saldo']
    df_cli['Taxa_Pgto'] = (df_cli['Recebido'] / df_cli['Valor'] * 100).fillna(0)
    df_cli['Atraso_Var'] = df_cli['Atraso_Var'].fillna(0)

    # Score de confiabilidade (0-100)
    # Baseado em: taxa de pagamento (40%), atraso medio (30%), variabilidade (15%), historico (15%)
    max_titulos = df_cli['Titulos'].max()

    df_cli['Score'] = (
        (df_cli['Taxa_Pgto'] * 0.4) +
        ((100 - df_cli['Atraso_Medio'].clip(0, 100)) * 0.3) +
        ((100 - df_cli['Atraso_Var'].clip(0, 100)) * 0.15) +
        (df_cli['Titulos'] / max_titulos * 100 * 0.15)
    ).clip(0, 100)

    # Classificar
    def classificar_score(s):
        if s >= 80:
            return 'A', cores['sucesso']
        elif s >= 60:
            return 'B', cores['info']
        elif s >= 40:
            return 'C', '#fbbf24'
        elif s >= 20:
            return 'D', cores['alerta']
        return 'E', cores['perigo']

    ratings = df_cli['Score'].apply(classificar_score)
    df_cli['Rating'] = [r[0] for r in ratings]

    # Filtros
    col1, col2, col3 = st.columns(3)

    with col1:
        filtro_rating = st.selectbox("Filtrar por Rating", ['Todos', 'A', 'B', 'C', 'D', 'E'], key="perfil_rating")

    with col2:
        ordenar = st.selectbox("Ordenar por", ['Score', 'Maior Saldo', 'Maior Atraso'], key="perfil_ordem")

    with col3:
        qtd = st.selectbox("Exibir", [25, 50, 100], key="perfil_qtd")

    # Aplicar filtros
    df_show = df_cli.copy()
    if filtro_rating != 'Todos':
        df_show = df_show[df_show['Rating'] == filtro_rating]

    if ordenar == 'Score':
        df_show = df_show.nlargest(qtd, 'Score')
    elif ordenar == 'Maior Saldo':
        df_show = df_show.nlargest(qtd, 'Saldo')
    else:
        df_show = df_show.nlargest(qtd, 'Atraso_Max')

    # Preparar tabela
    df_tabela = df_show[[col_cliente, 'Valor', 'Recebido', 'Saldo', 'Taxa_Pgto', 'Atraso_Medio', 'Score', 'Rating']].copy()
    df_tabela['Valor'] = df_tabela['Valor'].apply(lambda x: formatar_moeda(x, completo=True))
    df_tabela['Recebido'] = df_tabela['Recebido'].apply(lambda x: formatar_moeda(x, completo=True))
    df_tabela['Saldo'] = df_tabela['Saldo'].apply(lambda x: formatar_moeda(x, completo=True))
    df_tabela['Taxa_Pgto'] = df_tabela['Taxa_Pgto'].apply(lambda x: f"{x:.1f}%")
    df_tabela['Atraso_Medio'] = df_tabela['Atraso_Medio'].apply(lambda x: f"{x:.0f}d")
    df_tabela['Score'] = df_tabela['Score'].apply(lambda x: f"{x:.0f}")

    df_tabela.columns = ['Cliente', 'Valor Total', 'Recebido', 'Pendente', '% Pago', 'Atraso Medio', 'Score', 'Rating']

    st.dataframe(df_tabela, use_container_width=True, hide_index=True, height=350)

    # Resumo por rating
    col1, col2, col3, col4, col5 = st.columns(5)
    for i, (rating, cor) in enumerate([('A', cores['sucesso']), ('B', cores['info']), ('C', '#fbbf24'), ('D', cores['alerta']), ('E', cores['perigo'])]):
        qtd_rating = len(df_cli[df_cli['Rating'] == rating])
        with [col1, col2, col3, col4, col5][i]:
            st.markdown(f"""
            <div style="text-align: center; background: {cores['card']}; border-radius: 8px; padding: 0.5rem;">
                <span style="color: {cor}; font-size: 1.5rem; font-weight: 800;">{rating}</span>
                <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0;">{qtd_rating} clientes</p>
            </div>
            """, unsafe_allow_html=True)


def _render_lista_cobranca(df_vencidos, col_cliente, cores):
    """Lista de cobranca exportavel"""

    st.markdown(f"""
    <div style="background: {cores['card']}; border-left: 4px solid {cores['alerta']};
                padding: 0.75rem 1rem; border-radius: 0 8px 8px 0; margin-bottom: 1rem;">
        <h4 style="color: {cores['texto']}; margin: 0;">Lista de Cobranca</h4>
        <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0;">
            Titulos vencidos para acao de cobranca
        </p>
    </div>
    """, unsafe_allow_html=True)

    if len(df_vencidos) == 0:
        st.success("Nenhum titulo vencido!")
        return

    # Filtros
    col1, col2, col3 = st.columns(3)

    with col1:
        faixa = st.selectbox("Faixa de Atraso", ['Todas', '1-7 dias', '8-30 dias', '31-60 dias', '61-90 dias', '+90 dias'], key="cob_faixa")

    with col2:
        valor_min = st.number_input("Valor minimo (R$)", value=0, step=1000, key="cob_valor")

    with col3:
        ordenar = st.selectbox("Ordenar por", ['Maior Valor', 'Maior Atraso', 'Cliente'], key="cob_ordem")

    # Aplicar filtros
    df_lista = df_vencidos.copy()

    if faixa != 'Todas':
        faixas_map = {
            '1-7 dias': (1, 7),
            '8-30 dias': (8, 30),
            '31-60 dias': (31, 60),
            '61-90 dias': (61, 90),
            '+90 dias': (91, 9999)
        }
        min_d, max_d = faixas_map.get(faixa, (0, 9999))
        df_lista = df_lista[(df_lista['DIAS_ATRASO'] >= min_d) & (df_lista['DIAS_ATRASO'] <= max_d)]

    df_lista = df_lista[df_lista['SALDO'] >= valor_min]

    if ordenar == 'Maior Valor':
        df_lista = df_lista.sort_values('SALDO', ascending=False)
    elif ordenar == 'Maior Atraso':
        df_lista = df_lista.sort_values('DIAS_ATRASO', ascending=False)
    else:
        df_lista = df_lista.sort_values(col_cliente)

    # Preparar tabela
    colunas = ['NOME_FILIAL', col_cliente, 'DESCRICAO', 'VENCIMENTO', 'DIAS_ATRASO', 'VALOR_ORIGINAL', 'SALDO']
    colunas_disp = [c for c in colunas if c in df_lista.columns]

    df_show = df_lista[colunas_disp].head(100).copy()

    # Formatar
    if 'VENCIMENTO' in df_show.columns:
        df_show['VENCIMENTO'] = pd.to_datetime(df_show['VENCIMENTO']).dt.strftime('%d/%m/%Y')
    df_show['VALOR_ORIGINAL'] = df_show['VALOR_ORIGINAL'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['SALDO'] = df_show['SALDO'].apply(lambda x: formatar_moeda(x, completo=True))

    nomes = {
        'NOME_FILIAL': 'Filial',
        'NOME_CLIENTE': 'Cliente',
        'DESCRICAO': 'Categoria',
        'VENCIMENTO': 'Vencimento',
        'DIAS_ATRASO': 'Dias Atraso',
        'VALOR_ORIGINAL': 'Valor',
        'SALDO': 'Saldo'
    }
    df_show.columns = [nomes.get(c, c) for c in df_show.columns]

    st.dataframe(df_show, use_container_width=True, hide_index=True, height=400)

    # Resumo
    total = df_lista['SALDO'].sum()
    st.info(f"**{len(df_lista)} titulos** | Total a cobrar: **{formatar_moeda(total)}**")
