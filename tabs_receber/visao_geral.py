"""
Aba Visao Geral - Overview Executivo - Contas a Receber
Design moderno e completo (alinhado com Contas a Pagar)
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta

from config.theme import get_cores
from config.settings import GRUPOS_FILIAIS, get_grupo_filial
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero


def render_visao_geral_receber(df):
    """Renderiza a aba Visao Geral com design moderno"""
    cores = get_cores()
    hoje = datetime.now()

    if len(df) == 0:
        st.warning("Nenhum dado disponivel.")
        return

    # Calcular metricas
    df_pendentes = df[df['SALDO'] > 0]
    df_vencidos = df[df['STATUS'] == 'Vencido']
    df_recebidos = df[df['SALDO'] == 0]

    total = df['VALOR_ORIGINAL'].sum()
    recebido = total - df['SALDO'].sum()
    pendente = df['SALDO'].sum()
    vencido = df_vencidos['SALDO'].sum()
    pct_recebido = (recebido / total * 100) if total > 0 else 0
    pct_vencido = (vencido / pendente * 100) if pendente > 0 else 0

    # ========== CARDS PRINCIPAIS ==========
    st.markdown(f"""
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1.5rem;">
        <div style="background: linear-gradient(135deg, {cores['sucesso']}20 0%, {cores['sucesso']}10 100%);
                    border: 1px solid {cores['sucesso']}40; border-radius: 12px; padding: 1.25rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0 0 0.5rem 0;">Total Emitido</p>
            <p style="color: {cores['texto']}; font-size: 1.5rem; font-weight: 700; margin: 0;">{formatar_moeda(total)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0.25rem 0 0 0;">{formatar_numero(len(df))} titulos</p>
        </div>
        <div style="background: linear-gradient(135deg, {cores['info']}20 0%, {cores['info']}10 100%);
                    border: 1px solid {cores['info']}40; border-radius: 12px; padding: 1.25rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0 0 0.5rem 0;">Recebido</p>
            <p style="color: {cores['sucesso']}; font-size: 1.5rem; font-weight: 700; margin: 0;">{formatar_moeda(recebido)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0.25rem 0 0 0;">{pct_recebido:.1f}% do total</p>
        </div>
        <div style="background: linear-gradient(135deg, {cores['alerta']}20 0%, {cores['alerta']}10 100%);
                    border: 1px solid {cores['alerta']}40; border-radius: 12px; padding: 1.25rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0 0 0.5rem 0;">A Receber</p>
            <p style="color: {cores['alerta']}; font-size: 1.5rem; font-weight: 700; margin: 0;">{formatar_moeda(pendente)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0.25rem 0 0 0;">{formatar_numero(len(df_pendentes))} titulos pendentes</p>
        </div>
        <div style="background: linear-gradient(135deg, {cores['perigo']}20 0%, {cores['perigo']}10 100%);
                    border: 1px solid {cores['perigo']}40; border-radius: 12px; padding: 1.25rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0 0 0.5rem 0;">Vencido</p>
            <p style="color: {cores['perigo']}; font-size: 1.5rem; font-weight: 700; margin: 0;">{formatar_moeda(vencido)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0.25rem 0 0 0;">{pct_vencido:.1f}% do pendente</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ========== ALERTAS DE RECEBIMENTOS ==========
    _render_alertas_recebimentos(df_pendentes, df_vencidos, cores, hoje)

    # ========== BARRA DE PROGRESSO ==========
    st.markdown(f"""
    <div style="background: {cores['card']}; border: 1px solid {cores['borda']}; border-radius: 12px; padding: 1rem; margin-bottom: 1.5rem;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
            <span style="color: {cores['texto']}; font-weight: 600;">Taxa de Recebimento</span>
            <span style="color: {cores['sucesso']}; font-weight: 700;">{pct_recebido:.1f}%</span>
        </div>
        <div style="background: {cores['borda']}; border-radius: 8px; height: 12px; overflow: hidden;">
            <div style="background: linear-gradient(90deg, {cores['sucesso']} 0%, {cores['primaria']} 100%);
                        width: {min(pct_recebido, 100):.1f}%; height: 100%; border-radius: 8px;"></div>
        </div>
        <div style="display: flex; justify-content: space-between; margin-top: 0.5rem;">
            <span style="color: {cores['texto_secundario']}; font-size: 0.75rem;">Recebido: {formatar_moeda(recebido)}</span>
            <span style="color: {cores['texto_secundario']}; font-size: 0.75rem;">Meta: {formatar_moeda(total)}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ========== AGING CARDS ==========
    _render_aging_cards(df_pendentes, cores)

    st.divider()

    # ========== LINHA 1: Por Filial + Top Categorias ==========
    col1, col2 = st.columns(2)

    with col1:
        _render_por_filial(df_pendentes, cores)

    with col2:
        _render_top_categorias(df_pendentes, cores)

    st.divider()

    # ========== RECEBIDO E PENDENTE POR FILIAL ==========
    _render_recebido_pendente_filial(df, cores)

    st.divider()

    # ========== LINHA 2: Fluxo de Caixa + Top Clientes ==========
    col1, col2 = st.columns(2)

    with col1:
        _render_fluxo_caixa(df_pendentes, cores, hoje)

    with col2:
        _render_top_clientes(df_pendentes, cores)

    st.divider()

    # ========== EVOLUCAO ==========
    _render_evolucao_mensal(df, cores)

    st.divider()

    # ========== TABELA POR FILIAL/GRUPO ==========
    _render_tabela_filiais(df, df_pendentes, df_vencidos, cores)


def _render_alertas_recebimentos(df_pendentes, df_vencidos, cores, hoje):
    """Alertas de recebimentos - vencido, hoje, amanha, semana"""

    hoje_date = hoje.date() if hasattr(hoje, 'date') else hoje

    # Recebimentos de hoje
    df_hoje = df_pendentes[
        (df_pendentes['VENCIMENTO'].dt.normalize() == pd.Timestamp(hoje_date))
    ] if len(df_pendentes) > 0 else pd.DataFrame()

    # Recebimentos de amanha
    amanha = hoje_date + timedelta(days=1)
    df_amanha = df_pendentes[
        (df_pendentes['VENCIMENTO'].dt.normalize() == pd.Timestamp(amanha))
    ] if len(df_pendentes) > 0 else pd.DataFrame()

    # Recebimentos proximos 7 dias (exceto hoje e amanha)
    df_semana = df_pendentes[
        (df_pendentes['VENCIMENTO'] > pd.Timestamp(amanha)) &
        (df_pendentes['VENCIMENTO'] <= pd.Timestamp(hoje_date + timedelta(days=7)))
    ] if len(df_pendentes) > 0 else pd.DataFrame()

    valor_vencido = df_vencidos['SALDO'].sum() if len(df_vencidos) > 0 else 0
    valor_hoje = df_hoje['SALDO'].sum() if len(df_hoje) > 0 else 0
    valor_amanha = df_amanha['SALDO'].sum() if len(df_amanha) > 0 else 0
    valor_semana = df_semana['SALDO'].sum() if len(df_semana) > 0 else 0

    qtd_vencido = len(df_vencidos)
    qtd_hoje = len(df_hoje)
    qtd_amanha = len(df_amanha)
    qtd_semana = len(df_semana)

    # Dias de atraso medio
    dias_atraso_medio = 0
    if len(df_vencidos) > 0 and 'DIAS_ATRASO' in df_vencidos.columns:
        dias_atraso_medio = df_vencidos['DIAS_ATRASO'].mean()

    st.markdown(f"""
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.75rem; margin-bottom: 1rem;">
        <div style="background: {cores['perigo']}15; border: 1px solid {cores['perigo']}50;
                    border-radius: 10px; padding: 1rem; text-align: center;">
            <p style="color: {cores['perigo']}; font-size: 0.7rem; font-weight: 600; margin: 0; text-transform: uppercase;">
                Vencido</p>
            <p style="color: {cores['perigo']}; font-size: 1.4rem; font-weight: 700; margin: 0.25rem 0;">
                {formatar_moeda(valor_vencido)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">
                {qtd_vencido} titulos{f' | {dias_atraso_medio:.0f}d atraso' if dias_atraso_medio > 0 else ''}</p>
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


def _render_aging_cards(df_pendentes, cores):
    """Cards de aging com design limpo"""

    # Calcular valores por faixa
    vencido = df_pendentes[df_pendentes['STATUS'] == 'Vencido']['SALDO'].sum()
    qtd_vencido = len(df_pendentes[df_pendentes['STATUS'] == 'Vencido'])

    vence_7d = df_pendentes[df_pendentes['STATUS'] == 'Vence em 7 dias']['SALDO'].sum()
    qtd_7d = len(df_pendentes[df_pendentes['STATUS'] == 'Vence em 7 dias'])

    vence_15d = df_pendentes[df_pendentes['STATUS'] == 'Vence em 15 dias']['SALDO'].sum()
    qtd_15d = len(df_pendentes[df_pendentes['STATUS'] == 'Vence em 15 dias'])

    vence_30d = df_pendentes[df_pendentes['STATUS'] == 'Vence em 30 dias']['SALDO'].sum()
    qtd_30d = len(df_pendentes[df_pendentes['STATUS'] == 'Vence em 30 dias'])

    st.markdown(f"""
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.75rem;">
        <div style="background: {cores['card']}; border-left: 4px solid {cores['perigo']};
                    border-radius: 0 8px 8px 0; padding: 1rem;">
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                <div style="width: 8px; height: 8px; background: {cores['perigo']}; border-radius: 50%;"></div>
                <span style="color: {cores['texto_secundario']}; font-size: 0.75rem; text-transform: uppercase;">Vencido</span>
            </div>
            <p style="color: {cores['perigo']}; font-size: 1.25rem; font-weight: 700; margin: 0;">{formatar_moeda(vencido)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0.25rem 0 0 0;">{formatar_numero(qtd_vencido)} titulos</p>
        </div>
        <div style="background: {cores['card']}; border-left: 4px solid {cores['alerta']};
                    border-radius: 0 8px 8px 0; padding: 1rem;">
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                <div style="width: 8px; height: 8px; background: {cores['alerta']}; border-radius: 50%;"></div>
                <span style="color: {cores['texto_secundario']}; font-size: 0.75rem; text-transform: uppercase;">Vence em 7 dias</span>
            </div>
            <p style="color: {cores['alerta']}; font-size: 1.25rem; font-weight: 700; margin: 0;">{formatar_moeda(vence_7d)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0.25rem 0 0 0;">{formatar_numero(qtd_7d)} titulos</p>
        </div>
        <div style="background: {cores['card']}; border-left: 4px solid {cores['info']};
                    border-radius: 0 8px 8px 0; padding: 1rem;">
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                <div style="width: 8px; height: 8px; background: {cores['info']}; border-radius: 50%;"></div>
                <span style="color: {cores['texto_secundario']}; font-size: 0.75rem; text-transform: uppercase;">Vence em 15 dias</span>
            </div>
            <p style="color: {cores['info']}; font-size: 1.25rem; font-weight: 700; margin: 0;">{formatar_moeda(vence_15d)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0.25rem 0 0 0;">{formatar_numero(qtd_15d)} titulos</p>
        </div>
        <div style="background: {cores['card']}; border-left: 4px solid {cores['sucesso']};
                    border-radius: 0 8px 8px 0; padding: 1rem;">
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                <div style="width: 8px; height: 8px; background: {cores['sucesso']}; border-radius: 50%;"></div>
                <span style="color: {cores['texto_secundario']}; font-size: 0.75rem; text-transform: uppercase;">Vence em 30 dias</span>
            </div>
            <p style="color: {cores['sucesso']}; font-size: 1.25rem; font-weight: 700; margin: 0;">{formatar_moeda(vence_30d)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0.25rem 0 0 0;">{formatar_numero(qtd_30d)} titulos</p>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _get_nome_grupo(cod_filial):
    """Retorna nome do grupo a partir do codigo da filial"""
    grupo_id = get_grupo_filial(int(cod_filial))
    return GRUPOS_FILIAIS.get(grupo_id, f"Grupo {grupo_id}")


def _detectar_multiplos_grupos(df):
    """Detecta se os dados contem filiais de multiplos grupos"""
    if 'FILIAL' not in df.columns or len(df) == 0:
        return False
    grupos = df['FILIAL'].dropna().apply(lambda x: get_grupo_filial(int(x))).nunique()
    return grupos > 1


def _render_por_filial(df_pendentes, cores):
    """Saldo a receber por Filial - agrupa por Grupo quando vendo todas as filiais"""

    if len(df_pendentes) == 0:
        st.info("Sem saldo pendente")
        return

    multiplos_grupos = _detectar_multiplos_grupos(df_pendentes)

    if multiplos_grupos:
        # Agrupar por GRUPO
        st.markdown("##### A Receber por Grupo")
        df_temp = df_pendentes.copy()
        df_temp['GRUPO'] = df_temp['FILIAL'].apply(lambda x: _get_nome_grupo(x) if pd.notna(x) else 'Outros')

        df_grp = df_temp.groupby('GRUPO').agg({
            'SALDO': 'sum',
            'VALOR_ORIGINAL': 'count'
        }).reset_index()
        df_grp.columns = ['Grupo', 'Saldo', 'Qtd']
        df_grp = df_grp.sort_values('Saldo', ascending=True)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=df_grp['Grupo'],
            x=df_grp['Saldo'],
            orientation='h',
            marker_color=cores['sucesso'],
            text=[f"{formatar_moeda(v)}" for v in df_grp['Saldo']],
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
    else:
        # Agrupar por filial individual (dentro de um grupo)
        st.markdown("##### A Receber por Filial")

        if 'NOME_FILIAL' not in df_pendentes.columns and 'FILIAL' not in df_pendentes.columns:
            st.info("Dados de filial nao disponiveis.")
            return

        df_filial = df_pendentes.groupby(['FILIAL', 'NOME_FILIAL']).agg({
            'SALDO': 'sum',
            'VALOR_ORIGINAL': 'count'
        }).reset_index()
        df_filial.columns = ['Cod', 'Nome', 'Saldo', 'Qtd']
        df_filial['Filial'] = df_filial['Cod'].astype(int).astype(str) + ' - ' + df_filial['Nome'].str.split(' - ').str[-1].str.strip()
        df_filial = df_filial.sort_values('Saldo', ascending=True)

        if len(df_filial) > 12:
            df_filial = df_filial.tail(12)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=df_filial['Filial'],
            x=df_filial['Saldo'],
            orientation='h',
            marker_color=cores['sucesso'],
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
    """Top categorias a receber"""

    st.markdown("##### Top Categorias")

    col_cat = 'CATEGORIA' if 'CATEGORIA' in df_pendentes.columns else 'DESCRICAO'

    if col_cat not in df_pendentes.columns:
        st.info("Dados de categoria nao disponiveis.")
        return

    df_cat = df_pendentes.groupby(col_cat).agg({
        'SALDO': 'sum',
        'VALOR_ORIGINAL': 'count'
    }).reset_index()
    df_cat.columns = ['Categoria', 'Saldo', 'Qtd']
    df_cat = df_cat.sort_values('Saldo', ascending=True).tail(8)

    if len(df_cat) == 0:
        st.info("Sem dados")
        return

    total = df_cat['Saldo'].sum()

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=df_cat['Categoria'].astype(str).str[:25],
        x=df_cat['Saldo'],
        orientation='h',
        marker=dict(
            color=df_cat['Saldo'],
            colorscale=[[0, cores['alerta']], [1, cores['perigo']]],
            showscale=False
        ),
        text=[f"{formatar_moeda(v)} ({v/total*100:.1f}%)" for v in df_cat['Saldo']],
        textposition='outside',
        textfont=dict(size=9, color=cores['texto'])
    ))

    fig.update_layout(
        criar_layout(280),
        margin=dict(l=10, r=100, t=10, b=10),
        xaxis=dict(showticklabels=False, showgrid=False),
        yaxis=dict(tickfont=dict(size=9, color=cores['texto']))
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_fluxo_caixa(df_pendentes, cores, hoje):
    """Projecao de fluxo de caixa - entradas previstas"""

    st.markdown("##### Previsao de Entradas (30 dias)")

    if len(df_pendentes) == 0 or 'VENCIMENTO' not in df_pendentes.columns:
        st.info("Sem dados para projecao")
        return

    hoje_date = hoje.date() if hasattr(hoje, 'date') else hoje

    # Proximos 30 dias
    df_futuro = df_pendentes[
        (df_pendentes['VENCIMENTO'] >= pd.Timestamp(hoje_date)) &
        (df_pendentes['VENCIMENTO'] <= pd.Timestamp(hoje_date + timedelta(days=30)))
    ].copy()

    if len(df_futuro) == 0:
        st.info("Nenhum recebimento previsto para os proximos 30 dias")
        return

    # Agrupar por semana
    df_futuro['SEMANA'] = df_futuro['VENCIMENTO'].dt.isocalendar().week
    df_futuro['ANO'] = df_futuro['VENCIMENTO'].dt.year

    df_semana = df_futuro.groupby(['ANO', 'SEMANA']).agg({
        'SALDO': 'sum',
        'VALOR_ORIGINAL': 'count'
    }).reset_index()
    df_semana.columns = ['Ano', 'Semana', 'Valor', 'Qtd']
    df_semana['Label'] = df_semana.apply(lambda x: f"Sem {int(x['Semana'])}", axis=1)
    df_semana = df_semana.head(5)  # Proximas 5 semanas

    # Acumulado
    df_semana['Acumulado'] = df_semana['Valor'].cumsum()

    fig = go.Figure()

    # Barras de valor semanal
    fig.add_trace(go.Bar(
        x=df_semana['Label'],
        y=df_semana['Valor'],
        name='Semanal',
        marker_color=cores['sucesso'],
        text=[formatar_moeda(v) for v in df_semana['Valor']],
        textposition='outside',
        textfont=dict(size=9, color=cores['texto'])
    ))

    # Linha de acumulado
    fig.add_trace(go.Scatter(
        x=df_semana['Label'],
        y=df_semana['Acumulado'],
        mode='lines+markers+text',
        name='Acumulado',
        line=dict(color=cores['info'], width=2),
        marker=dict(size=8),
        text=[formatar_moeda(v) for v in df_semana['Acumulado']],
        textposition='top center',
        textfont=dict(size=8, color=cores['info'])
    ))

    fig.update_layout(
        criar_layout(280),
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(tickfont=dict(size=9, color=cores['texto'])),
        yaxis=dict(showticklabels=False, showgrid=False),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1, font=dict(size=9)),
        showlegend=True
    )

    st.plotly_chart(fig, use_container_width=True)

    # Total previsto
    total_previsto = df_futuro['SALDO'].sum()
    st.caption(f"Total previsto: **{formatar_moeda(total_previsto)}** em {len(df_futuro)} titulos")


def _render_top_clientes(df_pendentes, cores):
    """Top clientes devedores com concentracao"""

    st.markdown("##### Top 5 Clientes - Maior Saldo")

    col_cliente = 'NOME_CLIENTE' if 'NOME_CLIENTE' in df_pendentes.columns else 'NOME_FORNECEDOR'

    if col_cliente not in df_pendentes.columns:
        st.info("Dados de cliente nao disponiveis.")
        return

    df_top = df_pendentes.groupby(col_cliente).agg({
        'SALDO': 'sum',
        'VALOR_ORIGINAL': 'count'
    }).reset_index()
    df_top.columns = ['Cliente', 'Saldo', 'Qtd']
    df_top = df_top.sort_values('Saldo', ascending=False).head(5)

    if len(df_top) == 0:
        st.info("Sem dados")
        return

    total_pendente = df_pendentes['SALDO'].sum()
    total_top5 = df_top['Saldo'].sum()
    concentracao = (total_top5 / total_pendente * 100) if total_pendente > 0 else 0

    # Alerta de concentracao
    cor_conc = cores['perigo'] if concentracao > 70 else (cores['alerta'] if concentracao > 50 else cores['sucesso'])

    st.markdown(f"""
    <div style="background: {cor_conc}15; border: 1px solid {cor_conc}50; border-radius: 8px;
                padding: 0.5rem; margin-bottom: 0.75rem; text-align: center;">
        <span style="color: {cores['texto_secundario']}; font-size: 0.75rem;">Concentracao Top 5: </span>
        <span style="color: {cor_conc}; font-weight: 700;">{concentracao:.1f}%</span>
        <span style="color: {cores['texto_secundario']}; font-size: 0.75rem;"> do total a receber</span>
    </div>
    """, unsafe_allow_html=True)

    fig = go.Figure(go.Bar(
        y=df_top['Cliente'].str[:25],
        x=df_top['Saldo'],
        orientation='h',
        marker=dict(
            color=df_top['Saldo'],
            colorscale=[[0, cores['info']], [1, cores['sucesso']]],
            showscale=False
        ),
        text=[f"{formatar_moeda(v)} ({v/total_pendente*100:.1f}%)" for v in df_top['Saldo']],
        textposition='outside',
        textfont=dict(size=9, color=cores['texto'])
    ))

    fig.update_layout(
        criar_layout(240),
        yaxis={'autorange': 'reversed'},
        margin=dict(l=10, r=110, t=10, b=10),
        xaxis=dict(showticklabels=False, showgrid=False),
        yaxis_tickfont=dict(size=9, color=cores['texto'])
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_evolucao_mensal(df, cores):
    """Evolucao mensal de emissao e recebimento"""

    st.markdown("##### Evolucao Mensal")

    if 'EMISSAO' not in df.columns:
        st.info("Dados de evolucao nao disponiveis")
        return

    df_temp = df.copy()
    df_temp['MES'] = df_temp['EMISSAO'].dt.to_period('M')

    df_mes = df_temp.groupby('MES').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum'
    }).reset_index()

    df_mes['MES'] = df_mes['MES'].astype(str)
    df_mes['Recebido'] = df_mes['VALOR_ORIGINAL'] - df_mes['SALDO']
    df_mes['Taxa'] = (df_mes['Recebido'] / df_mes['VALOR_ORIGINAL'] * 100).fillna(0)
    df_mes = df_mes.tail(12)

    if len(df_mes) < 2:
        st.info("Dados insuficientes para evolucao")
        return

    fig = go.Figure()

    # Barras empilhadas
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

    # Linha de taxa
    fig.add_trace(go.Scatter(
        x=df_mes['MES'],
        y=df_mes['Taxa'],
        mode='lines+markers',
        name='% Recebido',
        yaxis='y2',
        line=dict(color=cores['texto'], width=2),
        marker=dict(size=6)
    ))

    fig.update_layout(
        criar_layout(300, barmode='stack'),
        yaxis=dict(title='Valor (R$)', tickfont=dict(size=9, color=cores['texto'])),
        yaxis2=dict(title='% Recebido', overlaying='y', side='right', showgrid=False, range=[0, 105],
                    tickfont=dict(size=9, color=cores['texto'])),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=9)),
        margin=dict(l=10, r=50, t=40, b=40),
        xaxis_tickangle=-45,
        xaxis_tickfont=dict(size=9, color=cores['texto'])
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_tabela_filiais(df, df_pendentes, df_vencidos, cores):
    """Tabela detalhada - por Grupo quando vendo todas, por filial quando filtrado"""

    if len(df) == 0:
        st.info("Sem dados")
        return

    multiplos_grupos = _detectar_multiplos_grupos(df)

    if multiplos_grupos:
        st.markdown("##### Resumo por Grupo")

        df_temp = df.copy()
        df_temp['GRUPO'] = df_temp['FILIAL'].apply(lambda x: _get_nome_grupo(x) if pd.notna(x) else 'Outros')

        df_resumo = df_temp.groupby('GRUPO').agg({
            'VALOR_ORIGINAL': ['sum', 'count'],
            'SALDO': 'sum',
            'FILIAL': 'nunique'
        }).reset_index()
        df_resumo.columns = ['Grupo', 'Total', 'Titulos', 'Saldo', 'Filiais']

        # Vencidos por grupo
        df_venc_temp = df_vencidos.copy()
        if len(df_venc_temp) > 0:
            df_venc_temp['GRUPO'] = df_venc_temp['FILIAL'].apply(lambda x: _get_nome_grupo(x) if pd.notna(x) else 'Outros')
            df_venc_grp = df_venc_temp.groupby('GRUPO')['SALDO'].sum().reset_index()
            df_venc_grp.columns = ['Grupo', 'Vencido']
            df_resumo = df_resumo.merge(df_venc_grp, on='Grupo', how='left')
        else:
            df_resumo['Vencido'] = 0.0
        df_resumo['Vencido'] = df_resumo['Vencido'].fillna(0)

        df_resumo['Recebido'] = df_resumo['Total'] - df_resumo['Saldo']
        df_resumo['% Recebido'] = (df_resumo['Recebido'] / df_resumo['Total'] * 100).round(1)
        df_resumo['% Vencido'] = (df_resumo['Vencido'] / df_resumo['Saldo'] * 100).fillna(0).round(1)
        df_resumo = df_resumo.sort_values('Saldo', ascending=False)

        df_display = df_resumo[['Grupo', 'Filiais', 'Titulos', 'Total', 'Recebido', 'Saldo', 'Vencido', '% Recebido', '% Vencido']].copy()
        df_display['Total'] = df_display['Total'].apply(formatar_moeda)
        df_display['Recebido'] = df_display['Recebido'].apply(formatar_moeda)
        df_display['Saldo'] = df_display['Saldo'].apply(formatar_moeda)
        df_display['Vencido'] = df_display['Vencido'].apply(formatar_moeda)
        df_display['% Recebido'] = df_display['% Recebido'].apply(lambda x: f"{x:.1f}%")
        df_display['% Vencido'] = df_display['% Vencido'].apply(lambda x: f"{x:.1f}%")
        df_display['Titulos'] = df_display['Titulos'].apply(formatar_numero)
    else:
        st.markdown("##### Resumo por Filial")

        df_resumo = df.groupby(['FILIAL', 'NOME_FILIAL']).agg({
            'VALOR_ORIGINAL': ['sum', 'count'],
            'SALDO': 'sum'
        }).reset_index()
        df_resumo.columns = ['FILIAL', 'NOME_FILIAL', 'VALOR_ORIGINAL', 'Titulos_count', 'SALDO']

        df_venc_filial = df_vencidos.groupby('FILIAL')['SALDO'].sum().reset_index()
        df_venc_filial.columns = ['FILIAL', 'Vencido']

        df_resumo = df_resumo.merge(df_venc_filial, on='FILIAL', how='left')
        df_resumo['Vencido'] = df_resumo['Vencido'].fillna(0)

        df_resumo['Recebido'] = df_resumo['VALOR_ORIGINAL'] - df_resumo['SALDO']
        df_resumo['% Recebido'] = (df_resumo['Recebido'] / df_resumo['VALOR_ORIGINAL'] * 100).round(1)
        df_resumo['% Vencido'] = (df_resumo['Vencido'] / df_resumo['SALDO'] * 100).fillna(0).round(1)

        df_resumo = df_resumo.rename(columns={
            'FILIAL': 'Cod',
            'NOME_FILIAL': 'Filial',
            'VALOR_ORIGINAL': 'Total',
            'SALDO': 'Saldo',
            'Titulos_count': 'Titulos'
        })
        df_resumo = df_resumo.sort_values('Saldo', ascending=False)

        df_display = df_resumo[['Cod', 'Filial', 'Titulos', 'Total', 'Recebido', 'Saldo', 'Vencido', '% Recebido', '% Vencido']].copy()
        df_display['Total'] = df_display['Total'].apply(formatar_moeda)
        df_display['Recebido'] = df_display['Recebido'].apply(formatar_moeda)
        df_display['Saldo'] = df_display['Saldo'].apply(formatar_moeda)
        df_display['Vencido'] = df_display['Vencido'].apply(formatar_moeda)
        df_display['% Recebido'] = df_display['% Recebido'].apply(lambda x: f"{x:.1f}%")
        df_display['% Vencido'] = df_display['% Vencido'].apply(lambda x: f"{x:.1f}%")
        df_display['Titulos'] = df_display['Titulos'].apply(formatar_numero)

    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        height=400
    )


def _render_recebido_pendente_filial(df, cores):
    """Graficos de Recebido e Pendente - por Grupo ou por Filial conforme filtro"""

    if len(df) == 0:
        return

    multiplos_grupos = _detectar_multiplos_grupos(df)

    if multiplos_grupos:
        # Agrupar por GRUPO
        df_temp = df.copy()
        df_temp['GRUPO'] = df_temp['FILIAL'].apply(lambda x: _get_nome_grupo(x) if pd.notna(x) else 'Outros')
        df_agg = df_temp.groupby('GRUPO').agg({
            'VALOR_ORIGINAL': 'sum', 'SALDO': 'sum'
        }).reset_index()
        df_agg['RECEBIDO'] = df_agg['VALOR_ORIGINAL'] - df_agg['SALDO']
        df_agg = df_agg[(df_agg['RECEBIDO'] > 0) | (df_agg['SALDO'] > 0)]
        label_col = 'GRUPO'
        titulo_rec = '##### Recebido por Grupo'
        titulo_pend = '##### Pendente por Grupo'
    else:
        if 'NOME_FILIAL' not in df.columns:
            return
        df_agg = df.groupby('NOME_FILIAL').agg({
            'VALOR_ORIGINAL': 'sum', 'SALDO': 'sum'
        }).reset_index()
        df_agg['RECEBIDO'] = df_agg['VALOR_ORIGINAL'] - df_agg['SALDO']
        df_agg = df_agg[(df_agg['RECEBIDO'] > 0) | (df_agg['SALDO'] > 0)]
        label_col = 'NOME_FILIAL'
        titulo_rec = '##### Recebido por Filial'
        titulo_pend = '##### Pendente por Filial'

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(titulo_rec)
        df_rec = df_agg[df_agg['RECEBIDO'] > 0].sort_values('RECEBIDO', ascending=True).tail(15)
        if len(df_rec) > 0:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                y=df_rec[label_col].str[-30:],
                x=df_rec['RECEBIDO'],
                orientation='h',
                marker_color=cores['sucesso'],
                text=[formatar_moeda(x) for x in df_rec['RECEBIDO']],
                textposition='outside',
                textfont=dict(size=8, color=cores['texto'])
            ))
            fig.update_layout(
                criar_layout(max(250, len(df_rec) * 28)),
                margin=dict(l=10, r=80, t=10, b=10),
                xaxis=dict(showticklabels=False, showgrid=True, gridcolor=cores['borda']),
                yaxis=dict(tickfont=dict(color=cores['texto'], size=9))
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhum titulo recebido")

    with col2:
        st.markdown(titulo_pend)
        df_pend = df_agg[df_agg['SALDO'] > 0].sort_values('SALDO', ascending=True).tail(15)
        if len(df_pend) > 0:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                y=df_pend[label_col].str[-30:],
                x=df_pend['SALDO'],
                orientation='h',
                marker_color=cores['alerta'],
                text=[formatar_moeda(x) for x in df_pend['SALDO']],
                textposition='outside',
                textfont=dict(size=8, color=cores['texto'])
            ))
            fig.update_layout(
                criar_layout(max(250, len(df_pend) * 28)),
                margin=dict(l=10, r=80, t=10, b=10),
                xaxis=dict(showticklabels=False, showgrid=True, gridcolor=cores['borda']),
                yaxis=dict(tickfont=dict(color=cores['texto'], size=9))
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhum titulo pendente")
