"""
Aba Dashboard - Overview Executivo
Foco: KPIs principais + Aging + Filiais (por Grupo) + Categorias + Fluxo de Caixa + Evolucao
"""
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

from config.theme import get_cores
from config.settings import GRUPOS_FILIAIS, get_grupo_filial
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

    # ========== BARRA DE PROGRESSO ==========
    pct_pago = metricas['pct_pago']
    st.markdown(f"""
    <div style="background: {cores['card']}; border: 1px solid {cores['borda']}; border-radius: 12px; padding: 1rem; margin-bottom: 1.5rem;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
            <span style="color: {cores['texto']}; font-weight: 600;">Taxa de Pagamento</span>
            <span style="color: {cores['sucesso']}; font-weight: 700;">{pct_pago:.1f}%</span>
        </div>
        <div style="background: {cores['borda']}; border-radius: 8px; height: 12px; overflow: hidden;">
            <div style="background: linear-gradient(90deg, {cores['sucesso']} 0%, {cores['primaria']} 100%);
                        width: {min(pct_pago, 100):.1f}%; height: 100%; border-radius: 8px;"></div>
        </div>
        <div style="display: flex; justify-content: space-between; margin-top: 0.5rem;">
            <span style="color: {cores['texto_secundario']}; font-size: 0.75rem;">Pago: {formatar_moeda(metricas['pago'])}</span>
            <span style="color: {cores['texto_secundario']}; font-size: 0.75rem;">Total: {formatar_moeda(metricas['total'])}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ========== ALERTAS - VENCIMENTOS HOJE E SEMANA ==========
    _render_alertas_vencimentos(df_pendentes, df_vencidos, cores, hoje)

    # ========== AGING CARDS ==========
    _render_aging_cards(df_pendentes, cores)

    st.divider()

    # ========== PAGO E PENDENTE POR FILIAL ==========
    _render_pago_pendente_filial(df, cores)

    st.divider()

    # ========== TOP CATEGORIAS ==========
    _render_top_categorias(df_pendentes, cores)

    st.divider()

    # ========== LINHA 2: Fluxo de Caixa + Top Fornecedores ==========
    col1, col2 = st.columns(2)

    with col1:
        _render_fluxo_caixa(df_pendentes, cores, hoje)

    with col2:
        _render_top_fornecedores(df_pendentes, cores)

    st.divider()

    # ========== EVOLUCAO MENSAL ==========
    _render_evolucao_mensal(df, cores)

    st.divider()

    # ========== TABELA POR FILIAL/GRUPO ==========
    _render_tabela_filiais(df, df_pendentes, df_vencidos, cores)


def _render_alertas_vencimentos(df_pendentes, df_vencidos, cores, hoje):
    """Alertas de vencimentos - hoje, amanha, semana"""

    hoje_date = hoje.date() if hasattr(hoje, 'date') else hoje
    amanha = hoje_date + timedelta(days=1)
    fim_semana = hoje_date + timedelta(days=7)

    if len(df_pendentes) > 0:
        df_hoje = df_pendentes[df_pendentes['VENCIMENTO'].dt.normalize() == pd.Timestamp(hoje_date)]
        df_amanha = df_pendentes[df_pendentes['VENCIMENTO'].dt.normalize() == pd.Timestamp(amanha)]
        df_semana = df_pendentes[
            (df_pendentes['VENCIMENTO'].dt.normalize() >= pd.Timestamp(hoje_date)) &
            (df_pendentes['VENCIMENTO'].dt.normalize() <= pd.Timestamp(fim_semana))
        ]
    else:
        df_hoje = df_amanha = df_semana = pd.DataFrame()

    valor_hoje = df_hoje['SALDO'].sum() if len(df_hoje) > 0 else 0
    valor_amanha = df_amanha['SALDO'].sum() if len(df_amanha) > 0 else 0
    valor_semana = df_semana['SALDO'].sum() if len(df_semana) > 0 else 0

    qtd_hoje = len(df_hoje)
    qtd_amanha = len(df_amanha)
    qtd_semana = len(df_semana)

    label_semana = f"Hoje ate {fim_semana.strftime('%d/%m')}"

    st.markdown(f"""
    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem; margin-bottom: 1rem;">
        <div style="background: {cores['alerta']}15; border: 1px solid {cores['alerta']}50;
                    border-radius: 10px; padding: 1rem; text-align: center;">
            <p style="color: {cores['alerta']}; font-size: 0.7rem; font-weight: 600; margin: 0; text-transform: uppercase;">
                Vence Hoje ({hoje_date.strftime('%d/%m')})</p>
            <p style="color: {cores['alerta']}; font-size: 1.4rem; font-weight: 700; margin: 0.25rem 0;">
                {formatar_moeda(valor_hoje)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">
                {qtd_hoje} titulos</p>
        </div>
        <div style="background: {cores['info']}15; border: 1px solid {cores['info']}50;
                    border-radius: 10px; padding: 1rem; text-align: center;">
            <p style="color: {cores['info']}; font-size: 0.7rem; font-weight: 600; margin: 0; text-transform: uppercase;">
                Vence Amanha ({amanha.strftime('%d/%m')})</p>
            <p style="color: {cores['info']}; font-size: 1.4rem; font-weight: 700; margin: 0.25rem 0;">
                {formatar_moeda(valor_amanha)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">
                {qtd_amanha} titulos</p>
        </div>
        <div style="background: {cores['sucesso']}15; border: 1px solid {cores['sucesso']}50;
                    border-radius: 10px; padding: 1rem; text-align: center;">
            <p style="color: {cores['sucesso']}; font-size: 0.7rem; font-weight: 600; margin: 0; text-transform: uppercase;">
                Proximos 7 dias ({label_semana})</p>
            <p style="color: {cores['sucesso']}; font-size: 1.4rem; font-weight: 700; margin: 0.25rem 0;">
                {formatar_moeda(valor_semana)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">
                {qtd_semana} titulos</p>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _render_aging_cards(df_pendentes, cores):
    """Cards de aging por faixa de vencimento"""

    vencido = df_pendentes[df_pendentes['STATUS'] == 'Vencido']['SALDO'].sum()
    qtd_vencido = len(df_pendentes[df_pendentes['STATUS'] == 'Vencido'])

    # Acumulado: tudo que vence nos proximos N dias (inclui hoje)
    df_futuro = df_pendentes[df_pendentes['DIAS_VENC'] >= 0] if 'DIAS_VENC' in df_pendentes.columns else pd.DataFrame()

    ate_7d = df_futuro[df_futuro['DIAS_VENC'] <= 7] if len(df_futuro) > 0 else pd.DataFrame()
    ate_15d = df_futuro[df_futuro['DIAS_VENC'] <= 15] if len(df_futuro) > 0 else pd.DataFrame()
    ate_30d = df_futuro[df_futuro['DIAS_VENC'] <= 30] if len(df_futuro) > 0 else pd.DataFrame()

    vence_7d = ate_7d['SALDO'].sum() if len(ate_7d) > 0 else 0
    qtd_7d = len(ate_7d)
    vence_15d = ate_15d['SALDO'].sum() if len(ate_15d) > 0 else 0
    qtd_15d = len(ate_15d)
    vence_30d = ate_30d['SALDO'].sum() if len(ate_30d) > 0 else 0
    qtd_30d = len(ate_30d)

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
                <span style="color: {cores['texto_secundario']}; font-size: 0.75rem; text-transform: uppercase;">Ate 7 dias</span>
            </div>
            <p style="color: {cores['alerta']}; font-size: 1.25rem; font-weight: 700; margin: 0;">{formatar_moeda(vence_7d)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0.25rem 0 0 0;">{formatar_numero(qtd_7d)} titulos</p>
        </div>
        <div style="background: {cores['card']}; border-left: 4px solid {cores['info']};
                    border-radius: 0 8px 8px 0; padding: 1rem;">
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                <div style="width: 8px; height: 8px; background: {cores['info']}; border-radius: 50%;"></div>
                <span style="color: {cores['texto_secundario']}; font-size: 0.75rem; text-transform: uppercase;">Ate 15 dias</span>
            </div>
            <p style="color: {cores['info']}; font-size: 1.25rem; font-weight: 700; margin: 0;">{formatar_moeda(vence_15d)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0.25rem 0 0 0;">{formatar_numero(qtd_15d)} titulos</p>
        </div>
        <div style="background: {cores['card']}; border-left: 4px solid {cores['sucesso']};
                    border-radius: 0 8px 8px 0; padding: 1rem;">
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                <div style="width: 8px; height: 8px; background: {cores['sucesso']}; border-radius: 50%;"></div>
                <span style="color: {cores['texto_secundario']}; font-size: 0.75rem; text-transform: uppercase;">Ate 30 dias</span>
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
    """Saldo por Filial - agrupa por Grupo quando vendo todas as filiais"""

    if len(df_pendentes) == 0:
        st.info("Sem saldo pendente")
        return

    multiplos_grupos = _detectar_multiplos_grupos(df_pendentes)

    if multiplos_grupos:
        # Agrupar por GRUPO
        st.markdown("##### Saldo por Grupo")
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
            marker_color=cores['primaria'],
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
        st.markdown("##### Saldo por Filial")
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

    df_cat = df_pendentes.groupby('DESCRICAO').agg({
        'SALDO': 'sum',
        'VALOR_ORIGINAL': 'count'
    }).reset_index()
    df_cat.columns = ['Categoria', 'Saldo', 'Qtd']
    df_cat = df_cat.sort_values('Saldo', ascending=False).head(10)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df_cat['Categoria'].str[:20],
        y=df_cat['Saldo'],
        marker_color=cores['primaria'],
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


def _render_pago_pendente_filial(df, cores):
    """Graficos de Pago e Pendente - por Grupo ou por Filial conforme filtro"""

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
        df_agg['PAGO'] = df_agg['VALOR_ORIGINAL'] - df_agg['SALDO']
        df_agg = df_agg[(df_agg['PAGO'] > 0) | (df_agg['SALDO'] > 0)]
        label_col = 'GRUPO'
        titulo_pago = '##### Pago por Grupo'
        titulo_pend = '##### Pendente por Grupo'
    else:
        if 'NOME_FILIAL' not in df.columns:
            return
        df_agg = df.groupby('NOME_FILIAL').agg({
            'VALOR_ORIGINAL': 'sum', 'SALDO': 'sum'
        }).reset_index()
        df_agg['PAGO'] = df_agg['VALOR_ORIGINAL'] - df_agg['SALDO']
        df_agg = df_agg[(df_agg['PAGO'] > 0) | (df_agg['SALDO'] > 0)]
        label_col = 'NOME_FILIAL'
        titulo_pago = '##### Pago por Filial'
        titulo_pend = '##### Pendente por Filial'

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(titulo_pago)
        df_pago = df_agg[df_agg['PAGO'] > 0].sort_values('PAGO', ascending=True).tail(15)
        if len(df_pago) > 0:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                y=df_pago[label_col].str[-30:],
                x=df_pago['PAGO'],
                orientation='h',
                marker_color=cores['sucesso'],
                text=[formatar_moeda(x) for x in df_pago['PAGO']],
                textposition='outside',
                textfont=dict(size=8, color=cores['texto'])
            ))
            fig.update_layout(
                criar_layout(max(250, len(df_pago) * 28)),
                margin=dict(l=10, r=80, t=10, b=10),
                xaxis=dict(showticklabels=False, showgrid=True, gridcolor=cores['borda']),
                yaxis=dict(tickfont=dict(color=cores['texto'], size=9))
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhum titulo pago")

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


def _render_fluxo_caixa(df_pendentes, cores, hoje):
    """Fluxo de caixa - vencimentos futuros por semana"""

    st.markdown("##### Proximas 8 Semanas a Pagar")

    if len(df_pendentes) == 0:
        st.info("Sem pendente a pagar")
        return

    hoje_date = hoje.date() if hasattr(hoje, 'date') else hoje

    df_futuro = df_pendentes[df_pendentes['VENCIMENTO'] >= pd.Timestamp(hoje_date)].copy()

    if len(df_futuro) == 0:
        st.success("Nenhum vencimento futuro pendente")
        return

    limite = pd.Timestamp(hoje_date + timedelta(days=56))
    df_futuro = df_futuro[df_futuro['VENCIMENTO'] < limite].copy()

    if len(df_futuro) == 0:
        st.success("Nenhum vencimento nas proximas 8 semanas")
        return

    df_futuro['SEMANA'] = df_futuro['VENCIMENTO'].apply(
        lambda d: (d.date() - hoje_date).days // 7 + 1 if pd.notna(d) else None
    )
    df_futuro = df_futuro[df_futuro['SEMANA'].notna()]

    df_sem = df_futuro.groupby('SEMANA').agg({
        'SALDO': 'sum',
        'VALOR_ORIGINAL': 'count'
    }).reset_index()
    df_sem.columns = ['Semana', 'Valor', 'Qtd']

    todas_semanas = pd.DataFrame({'Semana': range(1, 9)})
    df_sem = todas_semanas.merge(df_sem, on='Semana', how='left').fillna(0)

    # Gerar labels e mapeamento semana -> periodo
    labels = []
    semana_labels = {}
    for i in range(1, 9):
        inicio = hoje_date + timedelta(days=(i-1)*7)
        fim = hoje_date + timedelta(days=i*7 - 1)
        label = f"S{i} ({inicio.strftime('%d/%m')}-{fim.strftime('%d/%m')})"
        labels.append(f"S{i}\n{inicio.strftime('%d/%m')}-{fim.strftime('%d/%m')}")
        semana_labels[i] = label

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
        textfont=dict(size=8, color=cores['texto']),
        hovertemplate='%{x}<br>Valor: %{text}<extra></extra>'
    ))

    fig.update_layout(
        criar_layout(320),
        margin=dict(l=10, r=10, t=10, b=50),
        yaxis=dict(showticklabels=False, showgrid=False),
        xaxis=dict(tickfont=dict(size=8, color=cores['texto']))
    )

    st.plotly_chart(fig, use_container_width=True)

    total_futuro = df_sem['Valor'].sum()
    st.caption(f"**Total proximas 8 semanas:** {formatar_moeda(total_futuro)} | Vencimentos alem de 8 semanas nao sao exibidos.")

    # Detalhamento por semana
    semanas_com_dados = [int(s) for s in df_futuro['SEMANA'].unique()]
    semanas_com_dados.sort()
    opcoes = {semana_labels[s]: s for s in semanas_com_dados if s in semana_labels}

    if opcoes:
        semana_sel = st.selectbox(
            "Detalhar semana:",
            options=list(opcoes.keys()),
            key="fluxo_semana_detalhe"
        )
        num_semana = opcoes[semana_sel]
        df_detalhe = df_futuro[df_futuro['SEMANA'] == num_semana].copy()

        if len(df_detalhe) > 0:
            colunas = ['NOME_FORNECEDOR', 'TIPO', 'NUMERO', 'VENCIMENTO', 'SALDO', 'NOME_FILIAL', 'DESCRICAO']
            colunas_disp = [c for c in colunas if c in df_detalhe.columns]
            df_show = df_detalhe[colunas_disp].sort_values('SALDO', ascending=False).copy()

            if 'NOME_FORNECEDOR' in df_show.columns:
                df_show['NOME_FORNECEDOR'] = df_show['NOME_FORNECEDOR'].str[:30]
            if 'NOME_FILIAL' in df_show.columns:
                df_show['NOME_FILIAL'] = df_show['NOME_FILIAL'].str.split(' - ').str[-1].str.strip()
            if 'DESCRICAO' in df_show.columns:
                df_show['DESCRICAO'] = df_show['DESCRICAO'].str[:20]
            if 'VENCIMENTO' in df_show.columns:
                df_show['VENCIMENTO'] = df_show['VENCIMENTO'].dt.strftime('%d/%m/%Y')
            if 'NUMERO' in df_show.columns:
                df_show['NUMERO'] = df_show['NUMERO'].astype(str)
            df_show['SALDO'] = df_show['SALDO'].apply(lambda x: formatar_moeda(x, completo=True))

            nomes = {
                'NOME_FORNECEDOR': 'Fornecedor', 'TIPO': 'Tipo', 'NUMERO': 'Numero Doc',
                'VENCIMENTO': 'Vencimento', 'SALDO': 'Pendente',
                'NOME_FILIAL': 'Filial', 'DESCRICAO': 'Categoria'
            }
            df_show.columns = [nomes.get(c, c) for c in df_show.columns]

            st.dataframe(df_show, use_container_width=True, hide_index=True, height=300)


def _render_top_fornecedores(df_pendentes, cores):
    """Top 10 fornecedores com maior valor pendente a pagar"""

    st.markdown("##### Top 10 Fornecedores - Pendente a Pagar")

    if len(df_pendentes) == 0:
        st.info("Sem pendente a pagar")
        return

    df_forn = df_pendentes.groupby('NOME_FORNECEDOR')['SALDO'].sum().reset_index()
    df_forn.columns = ['Fornecedor', 'Pendente']
    df_forn = df_forn.nlargest(10, 'Pendente')
    df_forn = df_forn.sort_values('Pendente', ascending=True)

    if len(df_forn) == 0:
        st.info("Sem dados")
        return

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=df_forn['Fornecedor'].str[:25],
        x=df_forn['Pendente'],
        orientation='h',
        marker_color=cores['perigo'],
        text=[formatar_moeda(v) for v in df_forn['Pendente']],
        textposition='outside',
        textfont=dict(size=9, color=cores['texto'])
    ))

    fig.update_layout(
        criar_layout(320),
        yaxis=dict(tickfont=dict(size=9, color=cores['texto'])),
        xaxis=dict(showticklabels=False, showgrid=False),
        margin=dict(l=10, r=80, t=10, b=10),
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)
    st.caption("Top 10 fornecedores rankeados pelo valor pendente a pagar.")


def _render_evolucao_mensal(df, cores):
    """Evolucao mensal de emissao e pagamento"""

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
    df_mes['Pago'] = df_mes['VALOR_ORIGINAL'] - df_mes['SALDO']
    df_mes['Taxa'] = (df_mes['Pago'] / df_mes['VALOR_ORIGINAL'] * 100).fillna(0)
    df_mes = df_mes.tail(12)

    if len(df_mes) < 2:
        st.info("Dados insuficientes para evolucao")
        return

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df_mes['MES'],
        y=df_mes['Pago'],
        name='Pago',
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
        mode='lines+markers',
        name='% Pago',
        yaxis='y2',
        line=dict(color=cores['texto'], width=2),
        marker=dict(size=6)
    ))

    fig.update_layout(
        criar_layout(300, barmode='stack'),
        yaxis=dict(title='Valor (R$)', tickfont=dict(size=9, color=cores['texto'])),
        yaxis2=dict(title='% Pago', overlaying='y', side='right', showgrid=False, range=[0, 105],
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
            'VALOR_ORIGINAL': 'sum',
            'SALDO': 'sum',
            'NUMERO': 'count',
            'FILIAL': 'nunique'
        }).reset_index()
        df_resumo.columns = ['Grupo', 'Total', 'Saldo', 'Titulos', 'Filiais']

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

        df_resumo['Pago'] = df_resumo['Total'] - df_resumo['Saldo']
        df_resumo['% Pago'] = (df_resumo['Pago'] / df_resumo['Total'] * 100).round(1)
        df_resumo['% Vencido'] = (df_resumo['Vencido'] / df_resumo['Saldo'] * 100).fillna(0).round(1)
        df_resumo = df_resumo.sort_values('Saldo', ascending=False)

        df_display = df_resumo[['Grupo', 'Filiais', 'Titulos', 'Total', 'Pago', 'Saldo', 'Vencido', '% Pago', '% Vencido']].copy()
        df_display['Total'] = df_display['Total'].apply(formatar_moeda)
        df_display['Pago'] = df_display['Pago'].apply(formatar_moeda)
        df_display['Saldo'] = df_display['Saldo'].apply(formatar_moeda)
        df_display['Vencido'] = df_display['Vencido'].apply(formatar_moeda)
        df_display['% Pago'] = df_display['% Pago'].apply(lambda x: f"{x:.1f}%")
        df_display['% Vencido'] = df_display['% Vencido'].apply(lambda x: f"{x:.1f}%")
        df_display['Titulos'] = df_display['Titulos'].apply(formatar_numero)
    else:
        st.markdown("##### Resumo por Filial")

        df_resumo = df.groupby(['FILIAL', 'NOME_FILIAL']).agg({
            'VALOR_ORIGINAL': 'sum',
            'SALDO': 'sum',
            'NUMERO': 'count'
        }).reset_index()

        df_venc_filial = df_vencidos.groupby('FILIAL')['SALDO'].sum().reset_index()
        df_venc_filial.columns = ['FILIAL', 'Vencido']

        df_resumo = df_resumo.merge(df_venc_filial, on='FILIAL', how='left')
        df_resumo['Vencido'] = df_resumo['Vencido'].fillna(0)

        df_resumo['Pago'] = df_resumo['VALOR_ORIGINAL'] - df_resumo['SALDO']
        df_resumo['% Pago'] = (df_resumo['Pago'] / df_resumo['VALOR_ORIGINAL'] * 100).round(1)
        df_resumo['% Vencido'] = (df_resumo['Vencido'] / df_resumo['SALDO'] * 100).fillna(0).round(1)

        df_resumo = df_resumo.rename(columns={
            'FILIAL': 'Cod',
            'NOME_FILIAL': 'Filial',
            'VALOR_ORIGINAL': 'Total',
            'SALDO': 'Pendente',
            'NUMERO': 'Titulos'
        })
        df_resumo = df_resumo.sort_values('Saldo', ascending=False)

        df_display = df_resumo[['Cod', 'Filial', 'Titulos', 'Total', 'Pago', 'Saldo', 'Vencido', '% Pago', '% Vencido']].copy()
        df_display['Total'] = df_display['Total'].apply(formatar_moeda)
        df_display['Pago'] = df_display['Pago'].apply(formatar_moeda)
        df_display['Saldo'] = df_display['Saldo'].apply(formatar_moeda)
        df_display['Vencido'] = df_display['Vencido'].apply(formatar_moeda)
        df_display['% Pago'] = df_display['% Pago'].apply(lambda x: f"{x:.1f}%")
        df_display['% Vencido'] = df_display['% Vencido'].apply(lambda x: f"{x:.1f}%")
        df_display['Titulos'] = df_display['Titulos'].apply(formatar_numero)

    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        height=400
    )
