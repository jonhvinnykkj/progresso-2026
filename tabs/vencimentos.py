"""
Aba Vencimentos - Calendario e Fluxo de Caixa
Foco: O que vence e quando pagar
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import calendar

from config.theme import get_cores
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero
from utils.data_helpers import get_df_pendentes, get_df_vencidos


def render_vencimentos(df):
    """Renderiza a aba de Vencimentos"""
    cores = get_cores()
    hoje = datetime.now()

    if len(df) == 0:
        st.warning("Nenhum dado disponivel.")
        return

    # Calcular dataframes
    df_pendentes = get_df_pendentes(df)
    df_vencidos = get_df_vencidos(df)

    # ========== KPIs ==========
    _render_kpis(df_pendentes, df_vencidos, cores, hoje)

    st.divider()

    # ========== LINHA 1: Calendario + Aging ==========
    col1, col2 = st.columns([3, 2])

    with col1:
        _render_calendario_mes(df_pendentes, df_vencidos, cores, hoje)

    with col2:
        _render_aging_vencidos(df_vencidos, cores)

    st.divider()

    # ========== LINHA 2: Projecao Semanal + Top Urgentes ==========
    col1, col2 = st.columns(2)

    with col1:
        _render_projecao_semanal(df_pendentes, cores, hoje)

    with col2:
        _render_top_urgentes(df_pendentes, df_vencidos, cores, hoje)

    st.divider()

    # ========== LINHA 3: Por Filial + Por Fornecedor ==========
    col1, col2 = st.columns(2)

    with col1:
        _render_vencimentos_filial(df_pendentes, df_vencidos, cores)

    with col2:
        _render_vencimentos_fornecedor(df_pendentes, df_vencidos, cores)

    st.divider()

    # ========== DETALHAMENTO ==========
    _render_detalhamento(df_pendentes, df_vencidos, cores, hoje)


def _render_kpis(df_pendentes, df_vencidos, cores, hoje):
    """KPIs focados em vencimentos"""

    # Calculos
    total_vencido = df_vencidos['SALDO'].sum()
    qtd_vencidos = len(df_vencidos)

    # Vence hoje
    vence_hoje = df_pendentes[
        (df_pendentes['VENCIMENTO'].dt.date == hoje.date()) &
        (df_pendentes['SALDO'] > 0)
    ]['SALDO'].sum()
    qtd_hoje = len(df_pendentes[df_pendentes['VENCIMENTO'].dt.date == hoje.date()])

    # Vence em 7 dias
    data_7d = hoje + timedelta(days=7)
    vence_7d = df_pendentes[
        (df_pendentes['VENCIMENTO'].dt.date > hoje.date()) &
        (df_pendentes['VENCIMENTO'].dt.date <= data_7d.date()) &
        (df_pendentes['SALDO'] > 0)
    ]['SALDO'].sum()

    # Vence em 30 dias
    data_30d = hoje + timedelta(days=30)
    vence_30d = df_pendentes[
        (df_pendentes['VENCIMENTO'].dt.date > hoje.date()) &
        (df_pendentes['VENCIMENTO'].dt.date <= data_30d.date()) &
        (df_pendentes['SALDO'] > 0)
    ]['SALDO'].sum()

    # Total pendente
    total_pendente = df_pendentes['SALDO'].sum()

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown(f"""
        <div style="background: {cores['perigo']}15; border: 1px solid {cores['perigo']};
                    border-radius: 10px; padding: 0.8rem; text-align: center;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">VENCIDO</p>
            <p style="color: {cores['perigo']}; font-size: 1.4rem; font-weight: 700; margin: 0.2rem 0;">
                {formatar_moeda(total_vencido)}</p>
            <p style="color: {cores['perigo']}; font-size: 0.65rem; margin: 0;">
                {qtd_vencidos} titulos</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        cor_hoje = cores['alerta'] if vence_hoje > 0 else cores['sucesso']
        st.markdown(f"""
        <div style="background: {cor_hoje}15; border: 1px solid {cor_hoje};
                    border-radius: 10px; padding: 0.8rem; text-align: center;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">VENCE HOJE</p>
            <p style="color: {cor_hoje}; font-size: 1.4rem; font-weight: 700; margin: 0.2rem 0;">
                {formatar_moeda(vence_hoje)}</p>
            <p style="color: {cor_hoje}; font-size: 0.65rem; margin: 0;">
                {qtd_hoje} titulos</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div style="background: {cores['alerta']}15; border: 1px solid {cores['alerta']};
                    border-radius: 10px; padding: 0.8rem; text-align: center;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">PROXIMOS 7 DIAS</p>
            <p style="color: {cores['alerta']}; font-size: 1.4rem; font-weight: 700; margin: 0.2rem 0;">
                {formatar_moeda(vence_7d)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.65rem; margin: 0;">
                urgente</p>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div style="background: {cores['info']}15; border: 1px solid {cores['info']};
                    border-radius: 10px; padding: 0.8rem; text-align: center;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">PROXIMOS 30 DIAS</p>
            <p style="color: {cores['info']}; font-size: 1.4rem; font-weight: 700; margin: 0.2rem 0;">
                {formatar_moeda(vence_30d)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.65rem; margin: 0;">
                planejamento</p>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['borda']};
                    border-radius: 10px; padding: 0.8rem; text-align: center;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">TOTAL PENDENTE</p>
            <p style="color: {cores['texto']}; font-size: 1.4rem; font-weight: 700; margin: 0.2rem 0;">
                {formatar_moeda(total_pendente)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.65rem; margin: 0;">
                {len(df_pendentes)} titulos</p>
        </div>
        """, unsafe_allow_html=True)


def _render_calendario_mes(df_pendentes, df_vencidos, cores, hoje):
    """Calendario visual do mes com valores por dia"""

    st.markdown("##### Calendario de Vencimentos")

    # Combinar pendentes e vencidos
    df_all = pd.concat([df_pendentes, df_vencidos]).drop_duplicates()
    df_all = df_all[df_all['VENCIMENTO'].notna()].copy()

    # Periodo: 7 dias atras ate 45 dias a frente
    data_inicio = hoje - timedelta(days=7)
    data_fim = hoje + timedelta(days=45)

    df_periodo = df_all[
        (df_all['VENCIMENTO'].dt.date >= data_inicio.date()) &
        (df_all['VENCIMENTO'].dt.date <= data_fim.date())
    ].copy()

    if len(df_periodo) == 0:
        st.info("Sem vencimentos no periodo")
        return

    # Agrupar por dia
    df_periodo['DIA'] = df_periodo['VENCIMENTO'].dt.date
    df_grp = df_periodo.groupby('DIA').agg({
        'SALDO': 'sum',
        'FORNECEDOR': 'count'
    }).reset_index()
    df_grp.columns = ['DIA', 'VALOR', 'QTD']

    # Criar serie completa de datas
    todas_datas = pd.date_range(start=data_inicio, end=data_fim, freq='D')
    df_completo = pd.DataFrame({'DIA': todas_datas.date})
    df_completo = df_completo.merge(df_grp, on='DIA', how='left').fillna(0)

    # Cores por status
    def cor_dia(row):
        dia = row['DIA']
        valor = row['VALOR']
        if valor == 0:
            return cores['card']
        if dia < hoje.date():
            return cores['perigo']  # Vencido
        elif dia == hoje.date():
            return '#f97316'  # Hoje
        elif dia <= (hoje + timedelta(days=7)).date():
            return cores['alerta']  # Proximos 7 dias
        elif dia <= (hoje + timedelta(days=30)).date():
            return cores['info']  # Proximos 30 dias
        return cores['sucesso']  # Mais de 30 dias

    df_completo['COR'] = df_completo.apply(cor_dia, axis=1)

    # Criar heatmap por semana
    df_completo['DIA_DT'] = pd.to_datetime(df_completo['DIA'])
    df_completo['SEMANA'] = df_completo['DIA_DT'].dt.isocalendar().week
    df_completo['DIA_SEMANA'] = df_completo['DIA_DT'].dt.dayofweek  # 0=Seg, 6=Dom

    # Grafico de barras por dia
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df_completo['DIA'],
        y=df_completo['VALOR'],
        marker_color=df_completo['COR'],
        text=[formatar_moeda(v) if v > 0 else '' for v in df_completo['VALOR']],
        textposition='outside',
        textfont=dict(size=8),
        hovertemplate='<b>%{x}</b><br>R$ %{y:,.2f}<br>%{customdata} titulos<extra></extra>',
        customdata=df_completo['QTD']
    ))

    # Linha vertical para hoje
    fig.add_vline(x=hoje.date(), line_dash="dash", line_color=cores['texto'], line_width=2)
    fig.add_annotation(x=hoje.date(), y=df_completo['VALOR'].max() * 1.1,
                       text="HOJE", showarrow=False, font=dict(size=10, color=cores['texto']))

    fig.update_layout(
        criar_layout(300),
        xaxis=dict(tickformat='%d/%m', tickangle=-45, dtick=86400000 * 3),  # A cada 3 dias
        margin=dict(l=10, r=10, t=10, b=60),
        bargap=0.1
    )

    st.plotly_chart(fig, use_container_width=True)

    # Legenda
    st.markdown(f"""
    <div style="display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap;">
        <span style="color: {cores['perigo']};">● Vencido</span>
        <span style="color: #f97316;">● Hoje</span>
        <span style="color: {cores['alerta']};">● 7 dias</span>
        <span style="color: {cores['info']};">● 30 dias</span>
        <span style="color: {cores['sucesso']};">● +30 dias</span>
    </div>
    """, unsafe_allow_html=True)


def _render_aging_vencidos(df_vencidos, cores):
    """Aging dos titulos vencidos"""

    st.markdown("##### Aging - Vencidos")

    if len(df_vencidos) == 0:
        st.success("Nenhum titulo vencido!")
        return

    def faixa_atraso(dias):
        if pd.isna(dias) or dias <= 0:
            return '0_Em dia'
        dias = int(dias)
        if dias <= 7:
            return '1_1-7 dias'
        elif dias <= 15:
            return '2_8-15 dias'
        elif dias <= 30:
            return '3_16-30 dias'
        elif dias <= 60:
            return '4_31-60 dias'
        return '5_60+ dias'

    df_ag = df_vencidos.copy()
    df_ag['FAIXA'] = df_ag['DIAS_ATRASO'].apply(faixa_atraso)

    df_grp = df_ag.groupby('FAIXA').agg({
        'SALDO': 'sum',
        'VALOR_ORIGINAL': 'count'
    }).sort_index().reset_index()
    df_grp.columns = ['Faixa', 'Valor', 'Qtd']
    df_grp['Label'] = df_grp['Faixa'].str[2:]  # Remove prefixo de ordenacao

    cores_faixas = [cores['alerta'], '#f97316', '#ef4444', '#dc2626', '#991b1b']
    cores_usadas = cores_faixas[:len(df_grp)]

    fig = go.Figure(data=[go.Pie(
        labels=df_grp['Label'],
        values=df_grp['Valor'],
        hole=0.5,
        marker_colors=cores_usadas,
        textinfo='percent',
        textfont_size=10,
        hovertemplate='<b>%{label}</b><br>R$ %{value:,.2f}<br>%{percent}<extra></extra>'
    )])

    # Texto central
    total = df_grp['Valor'].sum()
    fig.add_annotation(
        text=f"<b>{formatar_moeda(total)}</b>",
        x=0.5, y=0.5,
        font=dict(size=12, color=cores['perigo']),
        showarrow=False
    )

    fig.update_layout(
        criar_layout(250),
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=-0.2, xanchor='center', x=0.5, font=dict(size=9)),
        margin=dict(l=10, r=10, t=10, b=50)
    )

    st.plotly_chart(fig, use_container_width=True)

    # Metricas
    dias_atraso_medio = df_vencidos['DIAS_ATRASO'].mean()
    maior_atraso = df_vencidos['DIAS_ATRASO'].max()
    st.caption(f"Atraso medio: **{dias_atraso_medio:.0f}d** | Maior atraso: **{maior_atraso:.0f}d**")


def _render_projecao_semanal(df_pendentes, cores, hoje):
    """Projecao de vencimentos por semana"""

    st.markdown("##### Projecao Semanal")

    if len(df_pendentes) == 0:
        st.info("Sem dados pendentes")
        return

    # Proximas 8 semanas
    df_proj = df_pendentes[
        (df_pendentes['VENCIMENTO'].notna()) &
        (df_pendentes['VENCIMENTO'].dt.date >= hoje.date())
    ].copy()

    if len(df_proj) == 0:
        st.info("Sem vencimentos futuros")
        return

    # Calcular semana
    df_proj['SEMANA_NUM'] = df_proj['VENCIMENTO'].dt.isocalendar().week
    df_proj['ANO'] = df_proj['VENCIMENTO'].dt.year

    # Agrupar por semana
    df_sem = df_proj.groupby(['ANO', 'SEMANA_NUM']).agg({
        'SALDO': 'sum',
        'FORNECEDOR': 'count'
    }).reset_index()
    df_sem.columns = ['Ano', 'Semana', 'Valor', 'Qtd']

    # Criar label da semana
    def label_semana(row):
        # Encontrar primeira data da semana
        datas = df_proj[(df_proj['VENCIMENTO'].dt.isocalendar().week == row['Semana']) &
                        (df_proj['VENCIMENTO'].dt.year == row['Ano'])]['VENCIMENTO']
        if len(datas) > 0:
            inicio = datas.min()
            return f"Sem {int(row['Semana'])}\n{inicio.strftime('%d/%m')}"
        return f"Sem {int(row['Semana'])}"

    df_sem['Label'] = df_sem.apply(label_semana, axis=1)
    df_sem = df_sem.head(8)  # Proximas 8 semanas

    # Cores por valor
    max_valor = df_sem['Valor'].max()
    def cor_valor(v):
        pct = v / max_valor if max_valor > 0 else 0
        if pct > 0.7:
            return cores['perigo']
        elif pct > 0.4:
            return cores['alerta']
        return cores['info']

    bar_colors = [cor_valor(v) for v in df_sem['Valor']]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df_sem['Label'],
        y=df_sem['Valor'],
        marker_color=bar_colors,
        text=[formatar_moeda(v) for v in df_sem['Valor']],
        textposition='outside',
        textfont=dict(size=9),
        hovertemplate='<b>%{x}</b><br>R$ %{y:,.2f}<br>%{customdata} titulos<extra></extra>',
        customdata=df_sem['Qtd']
    ))

    # Media
    media = df_sem['Valor'].mean()
    fig.add_hline(y=media, line_dash="dash", line_color=cores['texto_secundario'],
                  annotation_text=f"Media: {formatar_moeda(media)}", annotation_position="right")

    fig.update_layout(
        criar_layout(280),
        margin=dict(l=10, r=80, t=10, b=60),
        xaxis_tickangle=0
    )

    st.plotly_chart(fig, use_container_width=True)

    # Totais
    total_8sem = df_sem['Valor'].sum()
    st.caption(f"Total proximas 8 semanas: **{formatar_moeda(total_8sem)}**")


def _render_top_urgentes(df_pendentes, df_vencidos, cores, hoje):
    """Top titulos mais urgentes"""

    st.markdown("##### Top 10 Mais Urgentes")

    # Combinar vencidos + proximos 7 dias
    data_7d = hoje + timedelta(days=7)

    df_urgentes = pd.concat([
        df_vencidos,
        df_pendentes[
            (df_pendentes['VENCIMENTO'].dt.date <= data_7d.date()) &
            (~df_pendentes.index.isin(df_vencidos.index))
        ]
    ]).copy()

    if len(df_urgentes) == 0:
        st.success("Nenhum titulo urgente!")
        return

    # Ordenar por urgencia (vencido primeiro, depois por dias)
    df_urgentes['URGENCIA'] = df_urgentes['DIAS_VENC'].fillna(-999)
    df_urgentes = df_urgentes.sort_values('URGENCIA').head(10)

    # Criar tabela visual
    for _, row in df_urgentes.iterrows():
        dias = row['DIAS_VENC'] if pd.notna(row['DIAS_VENC']) else 0

        if dias < 0:
            status = f"Vencido ha {abs(int(dias))}d"
            cor_status = cores['perigo']
            bg = f"{cores['perigo']}15"
        elif dias == 0:
            status = "Vence HOJE"
            cor_status = '#f97316'
            bg = "#f9731615"
        else:
            status = f"Vence em {int(dias)}d"
            cor_status = cores['alerta']
            bg = f"{cores['alerta']}15"

        fornecedor = str(row['NOME_FORNECEDOR'])[:30] if pd.notna(row['NOME_FORNECEDOR']) else '-'
        valor = formatar_moeda(row['SALDO'])
        venc = row['VENCIMENTO'].strftime('%d/%m') if pd.notna(row['VENCIMENTO']) else '-'

        st.markdown(f"""
        <div style="background: {bg}; border-left: 4px solid {cor_status};
                    border-radius: 6px; padding: 0.5rem 0.75rem; margin-bottom: 0.4rem;
                    display: flex; justify-content: space-between; align-items: center;">
            <div style="flex: 2;">
                <p style="color: {cores['texto']}; font-size: 0.8rem; font-weight: 500; margin: 0;">
                    {fornecedor}</p>
                <p style="color: {cor_status}; font-size: 0.7rem; margin: 0;">
                    {status} ({venc})</p>
            </div>
            <div style="text-align: right;">
                <p style="color: {cores['texto']}; font-size: 0.95rem; font-weight: 700; margin: 0;">
                    {valor}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)


def _render_vencimentos_filial(df_pendentes, df_vencidos, cores):
    """Vencimentos por filial"""

    st.markdown("##### Por Filial")

    df_all = pd.concat([df_pendentes, df_vencidos]).drop_duplicates()

    if len(df_all) == 0:
        st.info("Sem dados")
        return

    # Agrupar
    df_fil = df_all.groupby('NOME_FILIAL').agg({
        'SALDO': 'sum'
    }).reset_index()
    df_fil.columns = ['Filial', 'Valor']

    # Adicionar vencidos
    if len(df_vencidos) > 0:
        df_venc_fil = df_vencidos.groupby('NOME_FILIAL')['SALDO'].sum().reset_index()
        df_venc_fil.columns = ['Filial', 'Vencido']
        df_fil = df_fil.merge(df_venc_fil, on='Filial', how='left').fillna(0)
    else:
        df_fil['Vencido'] = 0

    df_fil['A_Vencer'] = df_fil['Valor'] - df_fil['Vencido']
    df_fil = df_fil.sort_values('Valor', ascending=True).tail(8)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=df_fil['Filial'].str[:20],
        x=df_fil['Vencido'],
        orientation='h',
        name='Vencido',
        marker_color=cores['perigo'],
        text=[formatar_moeda(v) if v > 0 else '' for v in df_fil['Vencido']],
        textposition='inside',
        textfont=dict(size=9, color='white')
    ))

    fig.add_trace(go.Bar(
        y=df_fil['Filial'].str[:20],
        x=df_fil['A_Vencer'],
        orientation='h',
        name='A Vencer',
        marker_color=cores['info'],
        text=[formatar_moeda(v) if v > 0 else '' for v in df_fil['A_Vencer']],
        textposition='inside',
        textfont=dict(size=9, color='white')
    ))

    fig.update_layout(
        criar_layout(280, barmode='stack'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
        margin=dict(l=10, r=10, t=30, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_vencimentos_fornecedor(df_pendentes, df_vencidos, cores):
    """Top fornecedores com vencimentos"""

    st.markdown("##### Top Fornecedores")

    df_all = pd.concat([df_pendentes, df_vencidos]).drop_duplicates()

    if len(df_all) == 0:
        st.info("Sem dados")
        return

    # Agrupar
    df_forn = df_all.groupby('NOME_FORNECEDOR').agg({
        'SALDO': 'sum',
        'DIAS_VENC': 'min'  # Menor dias = mais urgente
    }).reset_index()
    df_forn.columns = ['Fornecedor', 'Valor', 'Dias_Min']

    # Adicionar vencidos
    if len(df_vencidos) > 0:
        df_venc_forn = df_vencidos.groupby('NOME_FORNECEDOR')['SALDO'].sum().reset_index()
        df_venc_forn.columns = ['Fornecedor', 'Vencido']
        df_forn = df_forn.merge(df_venc_forn, on='Fornecedor', how='left').fillna(0)
    else:
        df_forn['Vencido'] = 0

    df_forn = df_forn.nlargest(8, 'Valor')

    # Cor por urgencia
    def cor_urgencia(dias):
        if pd.isna(dias) or dias < 0:
            return cores['perigo']
        elif dias <= 7:
            return cores['alerta']
        elif dias <= 30:
            return cores['info']
        return cores['sucesso']

    bar_colors = [cor_urgencia(d) for d in df_forn['Dias_Min']]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=df_forn['Fornecedor'].str[:20],
        x=df_forn['Valor'],
        orientation='h',
        marker_color=bar_colors,
        text=[formatar_moeda(v) for v in df_forn['Valor']],
        textposition='outside',
        textfont=dict(size=9)
    ))

    fig.update_layout(
        criar_layout(280),
        margin=dict(l=10, r=80, t=10, b=10),
        yaxis={'autorange': 'reversed'}
    )

    st.plotly_chart(fig, use_container_width=True)
    st.caption("Cor: Vencido | 7d | 30d | +30d")


def _render_detalhamento(df_pendentes, df_vencidos, cores, hoje):
    """Tabs de detalhamento"""

    st.markdown("##### Detalhamento")

    tab1, tab2, tab3 = st.tabs([
        "Vencidos",
        "Proximos 7 dias",
        "Todos Pendentes"
    ])

    with tab1:
        _render_tab_vencidos(df_vencidos, cores)

    with tab2:
        _render_tab_proximos(df_pendentes, cores, hoje)

    with tab3:
        _render_tab_todos(df_pendentes, cores)


def _render_tab_vencidos(df_vencidos, cores):
    """Tab de titulos vencidos"""

    if len(df_vencidos) == 0:
        st.success("Nenhum titulo vencido!")
        return

    # Filtros
    col1, col2 = st.columns([2, 1])
    with col1:
        ordenar = st.selectbox(
            "Ordenar por",
            ["Maior valor", "Maior atraso", "Fornecedor A-Z"],
            key="venc_ordem"
        )
    with col2:
        filtro_dias = st.selectbox(
            "Filtrar atraso",
            ["Todos", "Ate 7 dias", "8-30 dias", "30+ dias"],
            key="venc_filtro"
        )

    df_show = df_vencidos.copy()

    # Aplicar filtro
    if filtro_dias == "Ate 7 dias":
        df_show = df_show[df_show['DIAS_ATRASO'] <= 7]
    elif filtro_dias == "8-30 dias":
        df_show = df_show[(df_show['DIAS_ATRASO'] > 7) & (df_show['DIAS_ATRASO'] <= 30)]
    elif filtro_dias == "30+ dias":
        df_show = df_show[df_show['DIAS_ATRASO'] > 30]

    # Aplicar ordenacao
    if ordenar == "Maior valor":
        df_show = df_show.nlargest(50, 'SALDO')
    elif ordenar == "Maior atraso":
        df_show = df_show.nlargest(50, 'DIAS_ATRASO')
    else:
        df_show = df_show.sort_values('NOME_FORNECEDOR').head(50)

    # Preparar tabela
    colunas = ['NOME_FILIAL', 'NOME_FORNECEDOR', 'VENCIMENTO', 'DIAS_ATRASO', 'SALDO']
    colunas_disp = [c for c in colunas if c in df_show.columns]
    df_tab = df_show[colunas_disp].copy()

    # Formatar
    if 'VENCIMENTO' in df_tab.columns:
        df_tab['VENCIMENTO'] = pd.to_datetime(df_tab['VENCIMENTO']).dt.strftime('%d/%m/%Y')

    df_tab['SALDO'] = df_tab['SALDO'].apply(lambda x: formatar_moeda(x, completo=True))
    if 'DIAS_ATRASO' in df_tab.columns:
        df_tab['DIAS_ATRASO'] = df_tab['DIAS_ATRASO'].apply(lambda x: f"{int(x)}d" if pd.notna(x) and x > 0 else '-')

    # Renomear
    nomes = {
        'NOME_FILIAL': 'Filial',
        'NOME_FORNECEDOR': 'Fornecedor',
        'VENCIMENTO': 'Vencimento',
        'DIAS_ATRASO': 'Atraso',
        'SALDO': 'Valor'
    }
    df_tab.columns = [nomes.get(c, c) for c in df_tab.columns]

    st.dataframe(df_tab, use_container_width=True, hide_index=True, height=350)
    st.caption(f"Exibindo {len(df_tab)} de {len(df_vencidos)} titulos vencidos | Total: **{formatar_moeda(df_vencidos['SALDO'].sum())}**")


def _render_tab_proximos(df_pendentes, cores, hoje):
    """Tab de proximos vencimentos"""

    data_7d = hoje + timedelta(days=7)
    df_7d = df_pendentes[
        (df_pendentes['VENCIMENTO'].dt.date > hoje.date()) &
        (df_pendentes['VENCIMENTO'].dt.date <= data_7d.date())
    ]

    if len(df_7d) == 0:
        st.info("Nenhum titulo vence nos proximos 7 dias")
        return

    df_show = df_7d.sort_values('VENCIMENTO').head(50).copy()

    colunas = ['NOME_FILIAL', 'NOME_FORNECEDOR', 'VENCIMENTO', 'DIAS_VENC', 'SALDO']
    colunas_disp = [c for c in colunas if c in df_show.columns]
    df_tab = df_show[colunas_disp].copy()

    # Formatar
    if 'VENCIMENTO' in df_tab.columns:
        df_tab['VENCIMENTO'] = pd.to_datetime(df_tab['VENCIMENTO']).dt.strftime('%d/%m/%Y')

    df_tab['SALDO'] = df_tab['SALDO'].apply(lambda x: formatar_moeda(x, completo=True))
    if 'DIAS_VENC' in df_tab.columns:
        df_tab['DIAS_VENC'] = df_tab['DIAS_VENC'].apply(lambda x: f"{int(x)}d" if pd.notna(x) else '-')

    nomes = {
        'NOME_FILIAL': 'Filial',
        'NOME_FORNECEDOR': 'Fornecedor',
        'VENCIMENTO': 'Vencimento',
        'DIAS_VENC': 'Dias p/ Vencer',
        'SALDO': 'Valor'
    }
    df_tab.columns = [nomes.get(c, c) for c in df_tab.columns]

    st.dataframe(df_tab, use_container_width=True, hide_index=True, height=350)
    st.caption(f"Total: **{formatar_moeda(df_7d['SALDO'].sum())}** em {len(df_7d)} titulos")


def _render_tab_todos(df_pendentes, cores):
    """Tab de todos os pendentes"""

    if len(df_pendentes) == 0:
        st.info("Nenhum titulo pendente")
        return

    # Filtro
    col1, col2 = st.columns(2)
    with col1:
        ordenar = st.selectbox(
            "Ordenar por",
            ["Vencimento", "Maior valor", "Fornecedor A-Z"],
            key="todos_ordem"
        )
    with col2:
        filtro_status = st.selectbox(
            "Status",
            ["Todos", "Vencido", "Vence em 7 dias", "Vence em 30 dias"],
            key="todos_status"
        )

    df_show = df_pendentes.copy()

    if filtro_status != "Todos":
        df_show = df_show[df_show['STATUS'] == filtro_status]

    if ordenar == "Vencimento":
        df_show = df_show.sort_values('VENCIMENTO').head(100)
    elif ordenar == "Maior valor":
        df_show = df_show.nlargest(100, 'SALDO')
    else:
        df_show = df_show.sort_values('NOME_FORNECEDOR').head(100)

    colunas = ['NOME_FILIAL', 'NOME_FORNECEDOR', 'VENCIMENTO', 'STATUS', 'SALDO']
    colunas_disp = [c for c in colunas if c in df_show.columns]
    df_tab = df_show[colunas_disp].copy()

    if 'VENCIMENTO' in df_tab.columns:
        df_tab['VENCIMENTO'] = pd.to_datetime(df_tab['VENCIMENTO']).dt.strftime('%d/%m/%Y')

    df_tab['SALDO'] = df_tab['SALDO'].apply(lambda x: formatar_moeda(x, completo=True))

    nomes = {
        'NOME_FILIAL': 'Filial',
        'NOME_FORNECEDOR': 'Fornecedor',
        'VENCIMENTO': 'Vencimento',
        'STATUS': 'Status',
        'SALDO': 'Valor'
    }
    df_tab.columns = [nomes.get(c, c) for c in df_tab.columns]

    st.dataframe(df_tab, use_container_width=True, hide_index=True, height=350)
    st.caption(f"Exibindo {len(df_tab)} de {len(df_pendentes)} titulos")
