"""
Aba Vencimentos - Visao de Gestao
Analise de vencimentos por faixas, filiais, categorias e fornecedores
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

from config.theme import get_cores
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero
from utils.data_helpers import get_df_pendentes, get_df_vencidos
from config.settings import GRUPOS_FILIAIS, get_grupo_filial


def render_vencimentos(df):
    """Renderiza a aba de Vencimentos - Visao de Gestao"""
    cores = get_cores()
    hoje = datetime.now()

    if len(df) == 0:
        st.warning("Nenhum dado disponivel.")
        return

    df_pendentes = get_df_pendentes(df)
    df_vencidos = get_df_vencidos(df)

    # ========== RESUMO GERAL ==========
    _render_resumo_geral(df_pendentes, df_vencidos, cores, hoje)

    st.divider()

    # ========== CALENDARIO 30 DIAS ==========
    _render_calendario_30d(df_pendentes, df_vencidos, cores, hoje)

    st.divider()

    # ========== AGING COMPLETO ==========
    _render_aging_completo(df_pendentes, df_vencidos, cores, hoje)

    st.divider()

    # ========== FILIAL x AGING + CATEGORIA ==========
    col1, col2 = st.columns(2)

    with col1:
        _render_filial_aging(df_pendentes, df_vencidos, cores)

    with col2:
        _render_por_categoria(df_pendentes, df_vencidos, cores)

    st.divider()

    # ========== VENCIDOS CRITICOS + CONCENTRACAO ==========
    col1, col2 = st.columns(2)

    with col1:
        _render_vencidos_criticos(df_vencidos, cores)

    with col2:
        _render_concentracao_vencidos(df_vencidos, cores)

    st.divider()

    # ========== DETALHAMENTO ==========
    _render_detalhamento(df_pendentes, df_vencidos, cores, hoje)


# =============================================================================
# RESUMO GERAL (melhorado com ticket medio e atraso medio)
# =============================================================================
def _render_resumo_geral(df_pendentes, df_vencidos, cores, hoje):
    """Resumo geral dos vencimentos"""

    hoje_date = hoje.date()

    total_pendente = df_pendentes['SALDO'].sum() + df_vencidos['SALDO'].sum()
    qtd_pendente = len(df_pendentes) + len(df_vencidos)

    total_vencido = df_vencidos['SALDO'].sum()
    qtd_vencidos = len(df_vencidos)

    data_30d = hoje_date + timedelta(days=30)
    df_30d = df_pendentes[df_pendentes['VENCIMENTO'] <= pd.Timestamp(data_30d)]
    valor_30d = df_30d['SALDO'].sum()
    qtd_30d = len(df_30d)

    data_60d = hoje_date + timedelta(days=60)
    df_31_60d = df_pendentes[
        (df_pendentes['VENCIMENTO'] > pd.Timestamp(data_30d)) &
        (df_pendentes['VENCIMENTO'] <= pd.Timestamp(data_60d))
    ]
    valor_31_60d = df_31_60d['SALDO'].sum()
    qtd_31_60d = len(df_31_60d)

    pct_vencido = (total_vencido / total_pendente * 100) if total_pendente > 0 else 0

    # Cards principais
    st.markdown(f"""
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1rem;">
        <div style="background: {cores['card']}; border: 1px solid {cores['borda']};
                    border-radius: 12px; padding: 1.25rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0;">TOTAL PENDENTE</p>
            <p style="color: {cores['texto']}; font-size: 1.5rem; font-weight: 700; margin: 0.25rem 0;">
                {formatar_moeda(total_pendente)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">{qtd_pendente} titulos</p>
        </div>
        <div style="background: {cores['perigo']}15; border: 1px solid {cores['perigo']}50;
                    border-radius: 12px; padding: 1.25rem;">
            <p style="color: {cores['perigo']}; font-size: 0.75rem; margin: 0;">VENCIDO</p>
            <p style="color: {cores['perigo']}; font-size: 1.5rem; font-weight: 700; margin: 0.25rem 0;">
                {formatar_moeda(total_vencido)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">
                {qtd_vencidos} titulos | {pct_vencido:.1f}% do total</p>
        </div>
        <div style="background: {cores['alerta']}15; border: 1px solid {cores['alerta']}50;
                    border-radius: 12px; padding: 1.25rem;">
            <p style="color: {cores['alerta']}; font-size: 0.75rem; margin: 0;">PROXIMOS 30 DIAS</p>
            <p style="color: {cores['alerta']}; font-size: 1.5rem; font-weight: 700; margin: 0.25rem 0;">
                {formatar_moeda(valor_30d)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">{qtd_30d} titulos</p>
        </div>
        <div style="background: {cores['info']}15; border: 1px solid {cores['info']}50;
                    border-radius: 12px; padding: 1.25rem;">
            <p style="color: {cores['info']}; font-size: 0.75rem; margin: 0;">31-60 DIAS</p>
            <p style="color: {cores['info']}; font-size: 1.5rem; font-weight: 700; margin: 0.25rem 0;">
                {formatar_moeda(valor_31_60d)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">{qtd_31_60d} titulos</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Indicadores complementares
    ticket_medio_vencido = (total_vencido / qtd_vencidos) if qtd_vencidos > 0 else 0
    dias_atraso_medio = 0
    if len(df_vencidos) > 0 and 'DIAS_ATRASO' in df_vencidos.columns:
        dias_atraso_medio = df_vencidos['DIAS_ATRASO'].mean()
    fornecedores_vencido = df_vencidos['NOME_FORNECEDOR'].nunique() if len(df_vencidos) > 0 else 0

    st.markdown(f"""
    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem; margin-bottom: 0.5rem;">
        <div style="background: {cores['card']}; border-left: 3px solid {cores['perigo']};
                    border-radius: 0 8px 8px 0; padding: 0.75rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">TICKET MEDIO VENCIDO</p>
            <p style="color: {cores['texto']}; font-size: 1.1rem; font-weight: 700; margin: 0.15rem 0;">
                {formatar_moeda(ticket_medio_vencido)}</p>
        </div>
        <div style="background: {cores['card']}; border-left: 3px solid {cores['alerta']};
                    border-radius: 0 8px 8px 0; padding: 0.75rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">ATRASO MEDIO</p>
            <p style="color: {cores['texto']}; font-size: 1.1rem; font-weight: 700; margin: 0.15rem 0;">
                {dias_atraso_medio:.0f} dias</p>
        </div>
        <div style="background: {cores['card']}; border-left: 3px solid {cores['info']};
                    border-radius: 0 8px 8px 0; padding: 0.75rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">FORNECEDORES C/ VENCIDO</p>
            <p style="color: {cores['texto']}; font-size: 1.1rem; font-weight: 700; margin: 0.15rem 0;">
                {fornecedores_vencido}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# CALENDARIO 30 DIAS (NOVO)
# =============================================================================
def _render_calendario_30d(df_pendentes, df_vencidos, cores, hoje):
    """Calendario de vencimentos - proximos 30 dias, dia a dia"""

    st.markdown("##### Calendario de Vencimentos - Proximos 30 Dias")

    hoje_date = hoje.date()

    df_all = pd.concat([df_pendentes, df_vencidos]).drop_duplicates()

    if len(df_all) == 0:
        st.info("Sem dados")
        return

    data_fim = hoje_date + timedelta(days=30)
    df_futuro = df_all[
        (df_all['VENCIMENTO'] >= pd.Timestamp(hoje_date)) &
        (df_all['VENCIMENTO'] <= pd.Timestamp(data_fim))
    ].copy()

    if len(df_futuro) == 0:
        st.info("Nenhum vencimento nos proximos 30 dias")
        return

    df_futuro['DIA'] = df_futuro['VENCIMENTO'].dt.date

    df_dia = df_futuro.groupby('DIA').agg({
        'SALDO': 'sum',
        'NUMERO': 'count'
    }).reset_index()
    df_dia.columns = ['Dia', 'Valor', 'Qtd']

    # Preencher todos os dias
    datas = [hoje_date + timedelta(days=i) for i in range(31)]
    all_days = pd.DataFrame({'Dia': datas})
    df_dia = all_days.merge(df_dia, on='Dia', how='left').fillna(0)
    df_dia['Label'] = df_dia['Dia'].apply(lambda d: d.strftime('%d/%m'))

    # Cores por intensidade
    max_val = df_dia['Valor'].max() if df_dia['Valor'].max() > 0 else 1

    def cor_dia(val):
        if val == 0:
            return cores['borda']
        ratio = val / max_val
        if ratio > 0.7:
            return cores['perigo']
        elif ratio > 0.4:
            return cores['alerta']
        elif ratio > 0.1:
            return '#f59e0b'
        return cores['sucesso']

    bar_colors = [cor_dia(v) for v in df_dia['Valor']]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df_dia['Label'],
        y=df_dia['Valor'],
        marker_color=bar_colors,
        text=[formatar_moeda(v) if v > 0 else '' for v in df_dia['Valor']],
        textposition='outside',
        textfont=dict(size=7, color=cores['texto']),
        hovertemplate='%{x}<br>Valor: R$ %{y:,.0f}<extra></extra>'
    ))

    fig.update_layout(
        criar_layout(280),
        margin=dict(l=10, r=10, t=10, b=50),
        xaxis=dict(tickfont=dict(size=7, color=cores['texto']), tickangle=-90),
        yaxis=dict(showticklabels=False, showgrid=False)
    )

    st.plotly_chart(fig, use_container_width=True)

    # Resumo
    total_30d = df_dia['Valor'].sum()
    idx_pico = df_dia['Valor'].idxmax()
    dia_pico = df_dia.loc[idx_pico]
    if dia_pico['Valor'] > 0:
        st.caption(
            f"Total 30 dias: **{formatar_moeda(total_30d)}** | "
            f"Dia mais pesado: **{dia_pico['Label']}** com **{formatar_moeda(dia_pico['Valor'])}**"
        )
    else:
        st.caption(f"Total 30 dias: **{formatar_moeda(total_30d)}**")


# =============================================================================
# AGING COMPLETO (mantido)
# =============================================================================
def _render_aging_completo(df_pendentes, df_vencidos, cores, hoje):
    """Aging completo - vencidos e a vencer"""

    st.markdown("##### Aging - Distribuicao por Faixa de Vencimento")

    hoje_date = hoje.date()

    df_all = pd.concat([df_pendentes, df_vencidos]).drop_duplicates()

    if len(df_all) == 0:
        st.info("Sem dados")
        return

    def faixa_vencimento(row):
        if pd.isna(row.get('VENCIMENTO')):
            return '9_Sem data'

        venc = row['VENCIMENTO'].date() if hasattr(row['VENCIMENTO'], 'date') else row['VENCIMENTO']
        diff = (venc - hoje_date).days

        if diff < -60:
            return '1_Venc +60 dias'
        elif diff < -30:
            return '2_Venc 31-60 dias'
        elif diff < -15:
            return '3_Venc 16-30 dias'
        elif diff < -7:
            return '4_Venc 8-15 dias'
        elif diff < 0:
            return '5_Venc 1-7 dias'
        elif diff <= 7:
            return '6_Vence em 7 dias'
        elif diff <= 30:
            return '7_Vence em 8-30 dias'
        elif diff <= 60:
            return '8_Vence em 31-60 dias'
        else:
            return '9_Vence em +60 dias'

    df_all['FAIXA'] = df_all.apply(faixa_vencimento, axis=1)

    df_grp = df_all.groupby('FAIXA').agg({
        'SALDO': 'sum',
        'NUMERO': 'count'
    }).sort_index().reset_index()
    df_grp.columns = ['Faixa', 'Valor', 'Qtd']

    labels = {
        '1_Venc +60 dias': '+60 dias vencido',
        '2_Venc 31-60 dias': '31-60 dias vencido',
        '3_Venc 16-30 dias': '16-30 dias vencido',
        '4_Venc 8-15 dias': '8-15 dias vencido',
        '5_Venc 1-7 dias': '1-7 dias vencido',
        '6_Vence em 7 dias': 'Vence em 7 dias',
        '7_Vence em 8-30 dias': 'Vence em 8-30 dias',
        '8_Vence em 31-60 dias': 'Vence em 31-60 dias',
        '9_Vence em +60 dias': 'Vence em +60 dias',
        '9_Sem data': 'Sem data'
    }
    df_grp['Label'] = df_grp['Faixa'].map(labels)

    cores_faixas = {
        '1_Venc +60 dias': '#7f1d1d',
        '2_Venc 31-60 dias': '#dc2626',
        '3_Venc 16-30 dias': '#ef4444',
        '4_Venc 8-15 dias': '#f97316',
        '5_Venc 1-7 dias': '#fbbf24',
        '6_Vence em 7 dias': '#84cc16',
        '7_Vence em 8-30 dias': '#22c55e',
        '8_Vence em 31-60 dias': '#3b82f6',
        '9_Vence em +60 dias': '#6366f1',
        '9_Sem data': '#64748b'
    }
    df_grp['Cor'] = df_grp['Faixa'].map(cores_faixas)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=df_grp['Label'],
        x=df_grp['Valor'],
        orientation='h',
        marker_color=df_grp['Cor'],
        text=[f"{formatar_moeda(v)} ({int(q)})" for v, q in zip(df_grp['Valor'], df_grp['Qtd'])],
        textposition='outside',
        textfont=dict(size=10, color=cores['texto'])
    ))

    fig.update_layout(
        criar_layout(350),
        margin=dict(l=10, r=120, t=10, b=10),
        xaxis=dict(showticklabels=False, showgrid=False),
        yaxis=dict(tickfont=dict(size=11, color=cores['texto']), autorange='reversed')
    )

    st.plotly_chart(fig, use_container_width=True)


# =============================================================================
# HELPERS GRUPO / FILIAL
# =============================================================================
def _get_nome_grupo(cod_filial):
    grupo_id = get_grupo_filial(int(cod_filial))
    return GRUPOS_FILIAIS.get(grupo_id, f"Grupo {grupo_id}")


def _detectar_multiplos_grupos(df):
    if 'FILIAL' not in df.columns or len(df) == 0:
        return False
    grupos = df['FILIAL'].dropna().apply(lambda x: get_grupo_filial(int(x))).nunique()
    return grupos > 1


# =============================================================================
# FILIAL x AGING (NOVO - vinculado ao filtro geral)
# =============================================================================
def _render_filial_aging(df_pendentes, df_vencidos, cores):
    """Aging por Filial/Grupo - vinculado ao filtro geral"""

    df_all = pd.concat([df_pendentes, df_vencidos]).drop_duplicates()

    if len(df_all) == 0:
        st.info("Sem dados")
        return

    multiplos = _detectar_multiplos_grupos(df_all)
    hoje_date = datetime.now().date()

    if multiplos:
        st.markdown("##### Aging por Grupo")
        df_all['AGRUPAMENTO'] = df_all['FILIAL'].apply(
            lambda x: _get_nome_grupo(x) if pd.notna(x) else 'Outros')
    else:
        st.markdown("##### Aging por Filial")
        if 'NOME_FILIAL' not in df_all.columns:
            st.info("Dados de filial nao disponiveis")
            return
        df_all['AGRUPAMENTO'] = (
            df_all['FILIAL'].astype(int).astype(str) + ' - ' +
            df_all['NOME_FILIAL'].str.split(' - ').str[-1].str.strip()
        )

    # Classificar em faixas de aging
    def faixa_simples(row):
        if pd.isna(row.get('VENCIMENTO')):
            return 'Outros'
        venc = row['VENCIMENTO'].date() if hasattr(row['VENCIMENTO'], 'date') else row['VENCIMENTO']
        diff = (venc - hoje_date).days
        if diff < 0:
            return 'Vencido'
        elif diff <= 30:
            return '0-30 dias'
        elif diff <= 60:
            return '31-60 dias'
        else:
            return '60+ dias'

    df_all['FAIXA'] = df_all.apply(faixa_simples, axis=1)

    # Pivot por agrupamento x faixa
    df_pivot = df_all.groupby(['AGRUPAMENTO', 'FAIXA'])['SALDO'].sum().unstack(fill_value=0).reset_index()

    for col in ['Vencido', '0-30 dias', '31-60 dias', '60+ dias']:
        if col not in df_pivot.columns:
            df_pivot[col] = 0

    df_pivot['_total'] = df_pivot[['Vencido', '0-30 dias', '31-60 dias', '60+ dias']].sum(axis=1)
    df_pivot = df_pivot.sort_values('_total', ascending=True)

    if len(df_pivot) > 12:
        df_pivot = df_pivot.tail(12)

    fig = go.Figure()

    faixas_cores = [
        ('Vencido', cores['perigo']),
        ('0-30 dias', cores['alerta']),
        ('31-60 dias', cores['info']),
        ('60+ dias', cores['sucesso']),
    ]

    for faixa, cor in faixas_cores:
        if faixa in df_pivot.columns:
            fig.add_trace(go.Bar(
                y=df_pivot['AGRUPAMENTO'].str[:28],
                x=df_pivot[faixa],
                orientation='h',
                name=faixa,
                marker_color=cor,
                text=[formatar_moeda(v) if v > 0 else '' for v in df_pivot[faixa]],
                textposition='inside',
                textfont=dict(size=8, color='white')
            ))

    fig.update_layout(
        criar_layout(max(280, len(df_pivot) * 30)),
        barmode='stack',
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(showticklabels=False, showgrid=False),
        yaxis=dict(tickfont=dict(size=9, color=cores['texto'])),
        legend=dict(
            orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1,
            font=dict(size=9, color=cores['texto'])
        )
    )

    st.plotly_chart(fig, use_container_width=True)


# =============================================================================
# POR CATEGORIA (mantido)
# =============================================================================
def _render_por_categoria(df_pendentes, df_vencidos, cores):
    """Saldo pendente por categoria (DESCRICAO) - Vencido vs A Vencer"""

    st.markdown("##### Por Categoria")

    df_all = pd.concat([df_pendentes, df_vencidos]).drop_duplicates()

    if len(df_all) == 0 or 'DESCRICAO' not in df_all.columns:
        st.info("Sem dados de categoria")
        return

    df_cat = df_all.groupby('DESCRICAO').agg({
        'SALDO': 'sum',
        'NUMERO': 'count'
    }).reset_index()
    df_cat.columns = ['Categoria', 'Valor', 'Qtd']

    if len(df_vencidos) > 0 and 'DESCRICAO' in df_vencidos.columns:
        df_venc_cat = df_vencidos.groupby('DESCRICAO')['SALDO'].sum().reset_index()
        df_venc_cat.columns = ['Categoria', 'Vencido']
        df_cat = df_cat.merge(df_venc_cat, on='Categoria', how='left')
    else:
        df_cat['Vencido'] = 0

    df_cat['Vencido'] = df_cat['Vencido'].fillna(0)
    df_cat['A_Vencer'] = df_cat['Valor'] - df_cat['Vencido']

    df_cat = df_cat.sort_values('Valor', ascending=True)

    if len(df_cat) > 12:
        df_cat = df_cat.tail(12)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=df_cat['Categoria'].astype(str).str[:28],
        x=df_cat['Vencido'],
        orientation='h',
        name='Vencido',
        marker_color=cores['perigo'],
        text=[formatar_moeda(v) if v > 0 else '' for v in df_cat['Vencido']],
        textposition='inside',
        textfont=dict(size=8, color='white')
    ))

    fig.add_trace(go.Bar(
        y=df_cat['Categoria'].astype(str).str[:28],
        x=df_cat['A_Vencer'],
        orientation='h',
        name='A Vencer',
        marker_color=cores['info'],
        text=[formatar_moeda(v) if v > 0 else '' for v in df_cat['A_Vencer']],
        textposition='inside',
        textfont=dict(size=8, color='white')
    ))

    fig.update_layout(
        criar_layout(320),
        barmode='stack',
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(showticklabels=False, showgrid=False),
        yaxis=dict(tickfont=dict(size=9, color=cores['texto'])),
        legend=dict(
            orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1,
            font=dict(size=10, color=cores['texto'])
        )
    )

    st.plotly_chart(fig, use_container_width=True)


# =============================================================================
# VENCIDOS CRITICOS (NOVO)
# =============================================================================
def _render_vencidos_criticos(df_vencidos, cores):
    """Top titulos vencidos - maiores valores com dias de atraso"""

    st.markdown("##### Vencidos Criticos - Acao Imediata")
    st.caption("Top 15 titulos com maior valor pendente entre os vencidos (STATUS = Vencido), ordenados por saldo. A coluna Atraso mostra quantos dias se passaram desde o vencimento.")

    if len(df_vencidos) == 0:
        st.success("Nenhum titulo vencido!")
        return

    df_top = df_vencidos.nlargest(15, 'SALDO').copy()

    colunas = ['NOME_FORNECEDOR', 'NOME_FILIAL', 'TIPO', 'NUMERO', 'VENCIMENTO', 'DIAS_ATRASO', 'VALOR_ORIGINAL', 'SALDO']
    colunas_disp = [c for c in colunas if c in df_top.columns]
    df_show = df_top[colunas_disp].copy()

    if 'NOME_FORNECEDOR' in df_show.columns:
        df_show['NOME_FORNECEDOR'] = df_show['NOME_FORNECEDOR'].str[:30]
    if 'NOME_FILIAL' in df_show.columns:
        df_show['NOME_FILIAL'] = df_show['NOME_FILIAL'].str.split(' - ').str[-1].str.strip()
    if 'NUMERO' in df_show.columns:
        df_show['NUMERO'] = df_show['NUMERO'].apply(
            lambda x: str(int(x)) if pd.notna(x) and str(x).replace('.0', '').isdigit() else (str(x) if pd.notna(x) else '-'))
    if 'VENCIMENTO' in df_show.columns:
        df_show['VENCIMENTO'] = df_show['VENCIMENTO'].dt.strftime('%d/%m/%Y')
    if 'DIAS_ATRASO' in df_show.columns:
        df_show['DIAS_ATRASO'] = df_show['DIAS_ATRASO'].apply(
            lambda x: f"{int(x)} dias" if pd.notna(x) else '-')
    if 'VALOR_ORIGINAL' in df_show.columns:
        df_show['VALOR_ORIGINAL'] = df_show['VALOR_ORIGINAL'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['SALDO'] = df_show['SALDO'].apply(lambda x: formatar_moeda(x, completo=True))

    nomes = {
        'NOME_FORNECEDOR': 'Fornecedor',
        'NOME_FILIAL': 'Filial',
        'TIPO': 'Tipo',
        'NUMERO': 'Numero Doc',
        'VENCIMENTO': 'Vencimento',
        'DIAS_ATRASO': 'Atraso',
        'VALOR_ORIGINAL': 'Valor Original',
        'SALDO': 'Pendente'
    }
    df_show.columns = [nomes.get(c, c) for c in df_show.columns]

    st.dataframe(df_show, use_container_width=True, hide_index=True, height=390)


# =============================================================================
# CONCENTRACAO VENCIDOS (NOVO)
# =============================================================================
def _render_concentracao_vencidos(df_vencidos, cores):
    """Top fornecedores com maior valor vencido - concentracao de risco"""

    st.markdown("##### Concentracao - Maiores Vencidos por Fornecedor")

    if len(df_vencidos) == 0:
        st.success("Nenhum titulo vencido!")
        return

    df_forn = df_vencidos.groupby('NOME_FORNECEDOR').agg({
        'SALDO': 'sum',
        'DIAS_ATRASO': 'mean',
        'NUMERO': 'count'
    }).reset_index()
    df_forn.columns = ['Fornecedor', 'Vencido', 'Atraso_Medio', 'Qtd']
    df_forn = df_forn.sort_values('Vencido', ascending=True).tail(10)

    total_vencido = df_vencidos['SALDO'].sum()

    def cor_atraso(d):
        if d > 30:
            return cores['perigo']
        elif d > 15:
            return '#f97316'
        return cores['alerta']

    bar_colors = [cor_atraso(d) for d in df_forn['Atraso_Medio']]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=df_forn['Fornecedor'].str[:28],
        x=df_forn['Vencido'],
        orientation='h',
        marker_color=bar_colors,
        text=[
            f"{formatar_moeda(v)} ({v / total_vencido * 100:.0f}%)" if total_vencido > 0
            else formatar_moeda(v)
            for v in df_forn['Vencido']
        ],
        textposition='outside',
        textfont=dict(size=8, color=cores['texto']),
        hovertemplate=(
            '<b>%{y}</b><br>'
            'Vencido: R$ %{x:,.0f}<br>'
            '<extra></extra>'
        )
    ))

    fig.update_layout(
        criar_layout(max(280, len(df_forn) * 28)),
        margin=dict(l=10, r=100, t=10, b=10),
        xaxis=dict(showticklabels=False, showgrid=False),
        yaxis=dict(tickfont=dict(size=9, color=cores['texto']))
    )

    st.plotly_chart(fig, use_container_width=True)

    # Concentracao top 5
    top5_val = df_forn.tail(5)['Vencido'].sum()
    pct_top5 = (top5_val / total_vencido * 100) if total_vencido > 0 else 0
    st.caption(f"Top 5 concentram **{pct_top5:.0f}%** do total vencido | Cor indica atraso medio")


# =============================================================================
# FLUXO SEMANAL (NOVO - substitui Evolucao Mensal)
# =============================================================================
def _render_fluxo_semanal(df_pendentes, cores, hoje):
    """Projecao semanal de vencimentos com acumulado"""

    st.markdown("##### Fluxo Semanal - Proximas 8 Semanas")

    if len(df_pendentes) == 0:
        st.info("Sem dados")
        return

    hoje_date = hoje.date()

    df_futuro = df_pendentes[df_pendentes['VENCIMENTO'] >= pd.Timestamp(hoje_date)].copy()

    if len(df_futuro) == 0:
        st.info("Nenhum vencimento futuro")
        return

    def get_semana(data):
        if pd.isna(data):
            return None
        data_date = data.date() if hasattr(data, 'date') else data
        dias = (data_date - hoje_date).days
        if dias < 0:
            return None
        return min(dias // 7 + 1, 8)

    df_futuro['SEMANA'] = df_futuro['VENCIMENTO'].apply(get_semana)
    df_futuro = df_futuro[df_futuro['SEMANA'].notna()]

    df_sem = df_futuro.groupby('SEMANA').agg({
        'SALDO': 'sum',
        'NUMERO': 'count'
    }).reset_index()
    df_sem.columns = ['Semana', 'Valor', 'Qtd']

    todas_semanas = pd.DataFrame({'Semana': range(1, 9)})
    df_sem = todas_semanas.merge(df_sem, on='Semana', how='left').fillna(0)

    # Acumulado
    df_sem['Acumulado'] = df_sem['Valor'].cumsum()

    labels = []
    for i in range(1, 9):
        inicio = hoje_date + timedelta(days=(i - 1) * 7)
        fim = inicio + timedelta(days=6)
        labels.append(f"S{i}\n{inicio.strftime('%d/%m')}-{fim.strftime('%d/%m')}")

    cores_semana = [
        cores['perigo'], cores['alerta'], '#f59e0b', '#84cc16',
        cores['sucesso'], cores['info'], '#8b5cf6', '#6366f1'
    ]

    fig = go.Figure()

    # Barras semanais
    fig.add_trace(go.Bar(
        x=labels,
        y=df_sem['Valor'],
        name='Semanal',
        marker_color=cores_semana,
        text=[formatar_moeda(v) for v in df_sem['Valor']],
        textposition='outside',
        textfont=dict(size=8, color=cores['texto'])
    ))

    # Linha acumulada
    fig.add_trace(go.Scatter(
        x=labels,
        y=df_sem['Acumulado'],
        name='Acumulado',
        mode='lines+markers+text',
        line=dict(color=cores['texto'], width=2),
        marker=dict(size=6),
        text=[formatar_moeda(v) for v in df_sem['Acumulado']],
        textposition='top center',
        textfont=dict(size=8, color=cores['texto']),
        yaxis='y2'
    ))

    fig.update_layout(
        criar_layout(300),
        margin=dict(l=10, r=50, t=30, b=50),
        xaxis=dict(tickfont=dict(size=8, color=cores['texto'])),
        yaxis=dict(showticklabels=False, showgrid=False),
        yaxis2=dict(overlaying='y', side='right', showticklabels=False, showgrid=False),
        legend=dict(
            orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1,
            font=dict(size=9, color=cores['texto'])
        ),
        showlegend=True
    )

    st.plotly_chart(fig, use_container_width=True)

    total_8sem = df_sem['Valor'].sum()
    st.caption(
        f"Total 8 semanas: **{formatar_moeda(total_8sem)}** em "
        f"{int(df_sem['Qtd'].sum())} titulos"
    )


# =============================================================================
# DETALHAMENTO (mantido)
# =============================================================================
def _render_detalhamento(df_pendentes, df_vencidos, cores, hoje):
    """Detalhamento com filtros"""

    st.markdown("##### Detalhamento")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        status = st.selectbox(
            "Status",
            ["Todos", "Vencidos", "A Vencer"],
            key="venc_status"
        )

    with col2:
        df_all = pd.concat([df_pendentes, df_vencidos]).drop_duplicates()
        filiais = ['Todas'] + sorted([str(x) for x in df_all['NOME_FILIAL'].unique() if pd.notna(x)])
        filtro_filial = st.selectbox("Filial", filiais, key="venc_filial")

    with col3:
        if 'DESCRICAO' in df_all.columns:
            categorias = ['Todas'] + sorted([str(x) for x in df_all['DESCRICAO'].unique() if pd.notna(x)])
            filtro_categoria = st.selectbox("Categoria", categorias, key="venc_categoria")
        else:
            filtro_categoria = 'Todas'

    with col4:
        ordenar = st.selectbox(
            "Ordenar por",
            ["Maior valor", "Vencimento", "Fornecedor"],
            key="venc_ordem"
        )

    # Aplicar filtros
    if status == "Vencidos":
        df_show = df_vencidos.copy()
    elif status == "A Vencer":
        df_show = df_pendentes.copy()
    else:
        df_show = pd.concat([df_pendentes, df_vencidos]).drop_duplicates()

    if filtro_filial != 'Todas':
        df_show = df_show[df_show['NOME_FILIAL'] == filtro_filial]

    if filtro_categoria != 'Todas' and 'DESCRICAO' in df_show.columns:
        df_show = df_show[df_show['DESCRICAO'] == filtro_categoria]

    # Ordenar
    if ordenar == "Maior valor":
        df_show = df_show.sort_values('SALDO', ascending=False)
    elif ordenar == "Vencimento":
        df_show = df_show.sort_values('VENCIMENTO')
    else:
        df_show = df_show.sort_values('NOME_FORNECEDOR')

    df_show = df_show.head(100)

    if len(df_show) == 0:
        st.info("Nenhum titulo encontrado")
        return

    # Metricas
    total = df_show['SALDO'].sum()
    st.markdown(f"**{len(df_show)} titulos** | Total: **{formatar_moeda(total)}**")

    # Tabela
    colunas = ['NOME_FILIAL', 'NOME_FORNECEDOR', 'TIPO', 'NUMERO', 'DESCRICAO', 'VENCIMENTO', 'SALDO', 'STATUS']
    colunas_disp = [c for c in colunas if c in df_show.columns]
    df_tab = df_show[colunas_disp].copy()

    if 'VENCIMENTO' in df_tab.columns:
        df_tab['VENCIMENTO'] = pd.to_datetime(df_tab['VENCIMENTO']).dt.strftime('%d/%m/%Y')

    if 'SALDO' in df_tab.columns:
        df_tab['SALDO'] = df_tab['SALDO'].apply(lambda x: formatar_moeda(x, completo=True))

    nomes = {
        'NOME_FILIAL': 'Filial',
        'NOME_FORNECEDOR': 'Fornecedor',
        'TIPO': 'Tipo',
        'NUMERO': 'Numero Doc',
        'DESCRICAO': 'Categoria',
        'VENCIMENTO': 'Vencimento',
        'SALDO': 'Pendente',
        'STATUS': 'Status'
    }
    df_tab.columns = [nomes.get(c, c) for c in df_tab.columns]

    st.dataframe(df_tab, use_container_width=True, hide_index=True, height=400)
