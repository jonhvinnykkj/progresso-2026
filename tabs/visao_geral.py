"""
Aba Dashboard - Overview Executivo
Foco: KPIs principais + Filiais + Categorias + Fluxo de Caixa + Vencimentos
"""
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

from config.theme import get_cores
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero


def render_visao_geral(df, df_pendentes=None, df_vencidos=None, metricas=None):
    """Renderiza a aba Dashboard - Overview executivo"""
    cores = get_cores()
    hoje = datetime.now()

    if len(df) == 0:
        st.warning("Nenhum dado disponivel.")
        return

    # Se nao recebeu os dados, calcular internamente
    if df_pendentes is None:
        df_pendentes = df[df['SALDO'] > 0]
    if df_vencidos is None:
        df_vencidos = df[df['STATUS'] == 'Vencido']
    if metricas is None:
        total = df['VALOR_ORIGINAL'].sum()
        pago = total - df['SALDO'].sum()
        pendente = df['SALDO'].sum()
        vencido = df_vencidos['SALDO'].sum()
        metricas = {
            'total': total,
            'pago': pago,
            'pendente': pendente,
            'vencido': vencido,
            'pct_pago': (pago / total * 100) if total > 0 else 0,
            'dias_atraso': df_vencidos['DIAS_ATRASO'].mean() if len(df_vencidos) > 0 else 0,
            'qtd_total': len(df),
            'qtd_vencidos': len(df_vencidos)
        }

    pct_vencido = (metricas['vencido'] / metricas['pendente'] * 100) if metricas['pendente'] > 0 else 0

    # ========== CARDS PRINCIPAIS ==========
    st.markdown(f"""
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1.5rem;">
        <div style="background: linear-gradient(135deg, {cores['primaria']}20 0%, {cores['primaria']}10 100%);
                    border: 1px solid {cores['primaria']}40; border-radius: 12px; padding: 1.25rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0 0 0.5rem 0;">Total Emitido</p>
            <p style="color: {cores['texto']}; font-size: 1.5rem; font-weight: 700; margin: 0;">{formatar_moeda(metricas['total'])}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0.25rem 0 0 0;">{formatar_numero(metricas['qtd_total'])} titulos</p>
        </div>
        <div style="background: linear-gradient(135deg, {cores['sucesso']}20 0%, {cores['sucesso']}10 100%);
                    border: 1px solid {cores['sucesso']}40; border-radius: 12px; padding: 1.25rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0 0 0.5rem 0;">Pago</p>
            <p style="color: {cores['sucesso']}; font-size: 1.5rem; font-weight: 700; margin: 0;">{formatar_moeda(metricas['pago'])}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0.25rem 0 0 0;">{metricas['pct_pago']:.1f}% do total</p>
        </div>
        <div style="background: linear-gradient(135deg, {cores['alerta']}20 0%, {cores['alerta']}10 100%);
                    border: 1px solid {cores['alerta']}40; border-radius: 12px; padding: 1.25rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0 0 0.5rem 0;">Saldo a Pagar</p>
            <p style="color: {cores['alerta']}; font-size: 1.5rem; font-weight: 700; margin: 0;">{formatar_moeda(metricas['pendente'])}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0.25rem 0 0 0;">{100 - metricas['pct_pago']:.1f}% do total</p>
        </div>
        <div style="background: linear-gradient(135deg, {cores['perigo']}20 0%, {cores['perigo']}10 100%);
                    border: 1px solid {cores['perigo']}40; border-radius: 12px; padding: 1.25rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0 0 0.5rem 0;">Vencido</p>
            <p style="color: {cores['perigo']}; font-size: 1.5rem; font-weight: 700; margin: 0;">{formatar_moeda(metricas['vencido'])}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0.25rem 0 0 0;">{pct_vencido:.1f}% do saldo</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ========== ALERTAS - VENCIMENTOS HOJE E SEMANA ==========
    _render_alertas_vencimentos(df_pendentes, df_vencidos, cores, hoje)

    st.divider()

    # ========== LINHA 1: Por Filial + Top Categorias ==========
    col1, col2 = st.columns(2)

    with col1:
        _render_por_filial(df_pendentes, cores)

    with col2:
        _render_top_categorias(df_pendentes, cores)

    st.divider()

    # ========== LINHA 2: Fluxo de Caixa + Top Fornecedores ==========
    col1, col2 = st.columns(2)

    with col1:
        _render_fluxo_caixa(df_pendentes, cores, hoje)

    with col2:
        _render_top_fornecedores(df_pendentes, cores)

    st.divider()

    # ========== LINHA 3: Tabela Detalhada por Filial ==========
    _render_tabela_filiais(df, df_pendentes, df_vencidos, cores)


def _render_alertas_vencimentos(df_pendentes, df_vencidos, cores, hoje):
    """Alertas de vencimentos - hoje, amanha, semana"""

    # Calcular vencimentos
    hoje_date = hoje.date() if hasattr(hoje, 'date') else hoje

    # Vencimentos de hoje
    df_hoje = df_pendentes[
        (df_pendentes['VENCIMENTO'].dt.date == hoje_date)
    ] if len(df_pendentes) > 0 else pd.DataFrame()

    # Vencimentos de amanha
    amanha = hoje_date + timedelta(days=1)
    df_amanha = df_pendentes[
        (df_pendentes['VENCIMENTO'].dt.date == amanha)
    ] if len(df_pendentes) > 0 else pd.DataFrame()

    # Vencimentos proximos 7 dias (exceto hoje e amanha)
    df_semana = df_pendentes[
        (df_pendentes['VENCIMENTO'].dt.date > amanha) &
        (df_pendentes['VENCIMENTO'].dt.date <= hoje_date + timedelta(days=7))
    ] if len(df_pendentes) > 0 else pd.DataFrame()

    valor_hoje = df_hoje['SALDO'].sum() if len(df_hoje) > 0 else 0
    valor_amanha = df_amanha['SALDO'].sum() if len(df_amanha) > 0 else 0
    valor_semana = df_semana['SALDO'].sum() if len(df_semana) > 0 else 0
    valor_vencido = df_vencidos['SALDO'].sum() if len(df_vencidos) > 0 else 0

    qtd_hoje = len(df_hoje)
    qtd_amanha = len(df_amanha)
    qtd_semana = len(df_semana)
    qtd_vencido = len(df_vencidos)

    # Cards de alerta
    st.markdown(f"""
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.75rem; margin-bottom: 1rem;">
        <div style="background: {cores['perigo']}15; border: 1px solid {cores['perigo']}50;
                    border-radius: 10px; padding: 1rem; text-align: center;">
            <p style="color: {cores['perigo']}; font-size: 0.7rem; font-weight: 600; margin: 0; text-transform: uppercase;">
                Vencido</p>
            <p style="color: {cores['perigo']}; font-size: 1.4rem; font-weight: 700; margin: 0.25rem 0;">
                {formatar_moeda(valor_vencido)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">
                {qtd_vencido} titulos</p>
        </div>
        <div style="background: {cores['alerta']}15; border: 1px solid {cores['alerta']}50;
                    border-radius: 10px; padding: 1rem; text-align: center;">
            <p style="color: {cores['alerta']}; font-size: 0.7rem; font-weight: 600; margin: 0; text-transform: uppercase;">
                Vence Hoje</p>
            <p style="color: {cores['alerta']}; font-size: 1.4rem; font-weight: 700; margin: 0.25rem 0;">
                {formatar_moeda(valor_hoje)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">
                {qtd_hoje} titulos</p>
        </div>
        <div style="background: {cores['info']}15; border: 1px solid {cores['info']}50;
                    border-radius: 10px; padding: 1rem; text-align: center;">
            <p style="color: {cores['info']}; font-size: 0.7rem; font-weight: 600; margin: 0; text-transform: uppercase;">
                Vence Amanha</p>
            <p style="color: {cores['info']}; font-size: 1.4rem; font-weight: 700; margin: 0.25rem 0;">
                {formatar_moeda(valor_amanha)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">
                {qtd_amanha} titulos</p>
        </div>
        <div style="background: {cores['sucesso']}15; border: 1px solid {cores['sucesso']}50;
                    border-radius: 10px; padding: 1rem; text-align: center;">
            <p style="color: {cores['sucesso']}; font-size: 0.7rem; font-weight: 600; margin: 0; text-transform: uppercase;">
                Proximos 7 dias</p>
            <p style="color: {cores['sucesso']}; font-size: 1.4rem; font-weight: 700; margin: 0.25rem 0;">
                {formatar_moeda(valor_semana)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">
                {qtd_semana} titulos</p>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _render_por_filial(df_pendentes, cores):
    """Grafico de saldo por filial com codigo"""

    st.markdown("##### Saldo por Filial")

    if len(df_pendentes) == 0:
        st.info("Sem saldo pendente")
        return

    # Agrupar por filial com codigo
    df_filial = df_pendentes.groupby(['FILIAL', 'NOME_FILIAL']).agg({
        'SALDO': 'sum',
        'NUMERO': 'count'
    }).reset_index()
    df_filial.columns = ['Cod', 'Nome', 'Saldo', 'Qtd']
    df_filial['Filial'] = df_filial['Cod'].astype(str) + ' - ' + df_filial['Nome'].str[:20]
    df_filial = df_filial.sort_values('Saldo', ascending=True)

    # Limitar a 12 filiais para visualizacao
    if len(df_filial) > 12:
        df_filial = df_filial.tail(12)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=df_filial['Filial'],
        x=df_filial['Saldo'],
        orientation='h',
        marker_color=cores['primaria'],
        text=[f"{formatar_moeda(v)}" for v in df_filial['Saldo']],
        textposition='outside',
        textfont=dict(size=9, color=cores['texto'])
    ))

    fig.update_layout(
        criar_layout(350),
        margin=dict(l=10, r=80, t=10, b=10),
        xaxis=dict(showticklabels=False, showgrid=False),
        yaxis=dict(tickfont=dict(size=9, color=cores['texto']))
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_top_categorias(df_pendentes, cores):
    """Top categorias por saldo"""

    st.markdown("##### Saldo por Categoria")

    if len(df_pendentes) == 0:
        st.info("Sem saldo pendente")
        return

    # Agrupar por descricao (categoria)
    df_cat = df_pendentes.groupby('DESCRICAO').agg({
        'SALDO': 'sum',
        'NUMERO': 'count'
    }).reset_index()
    df_cat.columns = ['Categoria', 'Saldo', 'Qtd']
    df_cat = df_cat.sort_values('Saldo', ascending=False).head(10)

    # Cores gradiente
    n_cats = len(df_cat)
    cores_grad = [cores['primaria']] * n_cats

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df_cat['Categoria'].str[:20],
        y=df_cat['Saldo'],
        marker_color=cores_grad,
        text=[f"{formatar_moeda(v)}" for v in df_cat['Saldo']],
        textposition='outside',
        textfont=dict(size=8, color=cores['texto'])
    ))

    fig.update_layout(
        criar_layout(350),
        margin=dict(l=10, r=10, t=10, b=80),
        yaxis=dict(showticklabels=False, showgrid=False),
        xaxis=dict(tickfont=dict(size=8, color=cores['texto']), tickangle=-45)
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_fluxo_caixa(df_pendentes, cores, hoje):
    """Fluxo de caixa - vencimentos futuros por semana"""

    st.markdown("##### Fluxo de Caixa - Proximas 8 Semanas")

    if len(df_pendentes) == 0:
        st.info("Sem saldo pendente")
        return

    hoje_date = hoje.date() if hasattr(hoje, 'date') else hoje

    # Filtrar apenas futuros (incluindo hoje)
    df_futuro = df_pendentes[df_pendentes['VENCIMENTO'].dt.date >= hoje_date].copy()

    if len(df_futuro) == 0:
        st.success("Nenhum vencimento futuro pendente")
        return

    # Agrupar por semana
    def get_semana(data):
        if pd.isna(data):
            return None
        data_date = data.date() if hasattr(data, 'date') else data
        dias = (data_date - hoje_date).days
        if dias < 0:
            return None
        semana = dias // 7 + 1
        return min(semana, 8)  # Limitar a 8 semanas

    df_futuro['SEMANA'] = df_futuro['VENCIMENTO'].apply(get_semana)
    df_futuro = df_futuro[df_futuro['SEMANA'].notna()]

    df_sem = df_futuro.groupby('SEMANA').agg({
        'SALDO': 'sum',
        'NUMERO': 'count'
    }).reset_index()
    df_sem.columns = ['Semana', 'Valor', 'Qtd']

    # Preencher semanas faltantes
    todas_semanas = pd.DataFrame({'Semana': range(1, 9)})
    df_sem = todas_semanas.merge(df_sem, on='Semana', how='left').fillna(0)

    # Labels das semanas
    labels = []
    for i in range(1, 9):
        inicio = hoje_date + timedelta(days=(i-1)*7)
        fim = hoje_date + timedelta(days=i*7-1)
        labels.append(f"S{i}\n{inicio.strftime('%d/%m')}")

    # Cores: mais proximo = mais intenso
    cores_semana = [
        cores['perigo'], cores['alerta'], '#f59e0b', '#84cc16',
        cores['sucesso'], cores['info'], '#8b5cf6', '#6366f1'
    ]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=labels,
        y=df_sem['Valor'],
        marker_color=cores_semana,
        text=[f"{formatar_moeda(v)}" for v in df_sem['Valor']],
        textposition='outside',
        textfont=dict(size=8, color=cores['texto'])
    ))

    fig.update_layout(
        criar_layout(320),
        margin=dict(l=10, r=10, t=10, b=50),
        yaxis=dict(showticklabels=False, showgrid=False),
        xaxis=dict(tickfont=dict(size=9, color=cores['texto']))
    )

    st.plotly_chart(fig, use_container_width=True)

    # Total do periodo
    total_futuro = df_sem['Valor'].sum()
    st.caption(f"**Total proximas 8 semanas:** {formatar_moeda(total_futuro)}")


def _render_top_fornecedores(df_pendentes, cores):
    """Top fornecedores com saldo pendente"""

    st.markdown("##### Top 10 Fornecedores")

    if len(df_pendentes) == 0:
        st.info("Sem saldo pendente")
        return

    df_forn = df_pendentes.groupby('NOME_FORNECEDOR').agg({
        'SALDO': 'sum',
        'NUMERO': 'count'
    }).reset_index()
    df_forn.columns = ['Fornecedor', 'Saldo', 'Qtd']
    df_forn = df_forn.nlargest(10, 'Saldo')

    if len(df_forn) == 0:
        st.info("Sem dados")
        return

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=df_forn['Fornecedor'].str[:25],
        x=df_forn['Saldo'],
        orientation='h',
        marker_color=cores['info'],
        text=[f"{formatar_moeda(v)}" for v in df_forn['Saldo']],
        textposition='outside',
        textfont=dict(size=9, color=cores['texto'])
    ))

    fig.update_layout(
        criar_layout(320),
        yaxis={'autorange': 'reversed', 'tickfont': dict(size=9, color=cores['texto'])},
        xaxis=dict(showticklabels=False, showgrid=False),
        margin=dict(l=10, r=80, t=10, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_tabela_filiais(df, df_pendentes, df_vencidos, cores):
    """Tabela detalhada com metricas por filial"""

    st.markdown("##### Resumo por Filial")

    if len(df) == 0:
        st.info("Sem dados")
        return

    # Agrupar dados por filial
    df_resumo = df.groupby(['FILIAL', 'NOME_FILIAL']).agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'NUMERO': 'count'
    }).reset_index()

    # Calcular vencidos por filial
    df_venc_filial = df_vencidos.groupby('FILIAL')['SALDO'].sum().reset_index()
    df_venc_filial.columns = ['FILIAL', 'Vencido']

    # Merge
    df_resumo = df_resumo.merge(df_venc_filial, on='FILIAL', how='left')
    df_resumo['Vencido'] = df_resumo['Vencido'].fillna(0)

    # Calcular pago
    df_resumo['Pago'] = df_resumo['VALOR_ORIGINAL'] - df_resumo['SALDO']
    df_resumo['% Pago'] = (df_resumo['Pago'] / df_resumo['VALOR_ORIGINAL'] * 100).round(1)
    df_resumo['% Vencido'] = (df_resumo['Vencido'] / df_resumo['SALDO'] * 100).fillna(0).round(1)

    # Renomear colunas
    df_resumo = df_resumo.rename(columns={
        'FILIAL': 'Cod',
        'NOME_FILIAL': 'Filial',
        'VALOR_ORIGINAL': 'Total',
        'SALDO': 'Saldo',
        'NUMERO': 'Titulos'
    })

    # Ordenar por saldo
    df_resumo = df_resumo.sort_values('Saldo', ascending=False)

    # Formatar para exibicao
    df_display = df_resumo[['Cod', 'Filial', 'Titulos', 'Total', 'Pago', 'Saldo', 'Vencido', '% Pago', '% Vencido']].copy()
    df_display['Total'] = df_display['Total'].apply(formatar_moeda)
    df_display['Pago'] = df_display['Pago'].apply(formatar_moeda)
    df_display['Saldo'] = df_display['Saldo'].apply(formatar_moeda)
    df_display['Vencido'] = df_display['Vencido'].apply(formatar_moeda)
    df_display['% Pago'] = df_display['% Pago'].apply(lambda x: f"{x:.1f}%")
    df_display['% Vencido'] = df_display['% Vencido'].apply(lambda x: f"{x:.1f}%")
    df_display['Titulos'] = df_display['Titulos'].apply(formatar_numero)

    # Exibir tabela
    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        height=400
    )
