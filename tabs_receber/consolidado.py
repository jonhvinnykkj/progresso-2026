"""
Tab Intercompany Consolidado - Cruzamento A Pagar x A Receber
Analise completa das operacoes entre empresas do grupo
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

from config.theme import get_cores
from config.settings import INTERCOMPANY_PATTERNS, INTERCOMPANY_TIPOS
from data.loader import carregar_dados
from data.loader_receber import carregar_dados_receber
from utils.formatters import formatar_moeda, formatar_numero


def classificar_tipo_ic(nome):
    """Classifica o tipo de operacao intercompany"""
    nome_upper = str(nome).upper()
    for padrao, tipo in INTERCOMPANY_TIPOS.items():
        if padrao in nome_upper:
            return tipo
    return 'Outros'


def render_consolidado():
    """Renderiza a aba de Intercompany Consolidado"""

    cores = get_cores()
    hoje = datetime.now()

    # Carregar dados de AMBAS as tabelas
    df_pagar_raw, _, _ = carregar_dados()
    df_receber_raw, _, _ = carregar_dados_receber()

    # Filtrar APENAS intercompany
    mask_ic_pagar = df_pagar_raw['NOME_FORNECEDOR'].str.upper().str.contains(
        '|'.join(INTERCOMPANY_PATTERNS), na=False, regex=True
    )
    df_pagar_ic = df_pagar_raw[mask_ic_pagar].copy()
    df_pagar_ic['CONTRAPARTE'] = df_pagar_ic['NOME_FORNECEDOR']
    df_pagar_ic['TIPO_IC'] = df_pagar_ic['CONTRAPARTE'].apply(classificar_tipo_ic)

    mask_ic_receber = df_receber_raw['NOME_CLIENTE'].str.upper().str.contains(
        '|'.join(INTERCOMPANY_PATTERNS), na=False, regex=True
    )
    df_receber_ic = df_receber_raw[mask_ic_receber].copy()
    df_receber_ic['CONTRAPARTE'] = df_receber_ic['NOME_CLIENTE']
    df_receber_ic['TIPO_IC'] = df_receber_ic['CONTRAPARTE'].apply(classificar_tipo_ic)

    # Calcular metricas principais
    total_pagar = df_pagar_ic['SALDO'].sum()
    total_receber = df_receber_ic['SALDO'].sum()
    saldo_liquido = total_receber - total_pagar

    # Vencidos
    pagar_vencido = df_pagar_ic[(df_pagar_ic['SALDO'] > 0) & (df_pagar_ic['DIAS_VENC'] < 0)]['SALDO'].sum()
    receber_vencido = df_receber_ic[(df_receber_ic['SALDO'] > 0) & (df_receber_ic['DIAS_VENC'] < 0)]['SALDO'].sum()

    pct_pagar_vencido = (pagar_vencido / total_pagar * 100) if total_pagar > 0 else 0
    pct_receber_vencido = (receber_vencido / total_receber * 100) if total_receber > 0 else 0

    # ========== HEADER DE IMPACTO ==========
    if saldo_liquido < 0:
        cor_saldo = cores['perigo']
        msg_saldo = "POSICAO DEVEDORA"
        icone = "⚠️"
    else:
        cor_saldo = cores['sucesso']
        msg_saldo = "POSICAO CREDORA"
        icone = "✅"

    # Alerta de criticidade
    if pct_pagar_vencido > 90 or pct_receber_vencido > 90:
        cor_alerta = cores['perigo']
        msg_alerta = "CRITICO: Quase totalidade vencida!"
    elif pct_pagar_vencido > 50 or pct_receber_vencido > 50:
        cor_alerta = cores['alerta']
        msg_alerta = "ATENCAO: Alto percentual vencido"
    else:
        cor_alerta = cores['sucesso']
        msg_alerta = "Situacao sob controle"

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, {cor_saldo}20, {cores['card']});
                border: 2px solid {cor_saldo}; border-radius: 12px;
                padding: 1.2rem; margin-bottom: 1rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
            <div>
                <p style="color: {cor_saldo}; font-size: 0.85rem; font-weight: 600; margin: 0;">
                    {icone} {msg_saldo} NO GRUPO</p>
                <p style="color: {cores['texto']}; font-size: 2.2rem; font-weight: 700; margin: 0;">
                    {formatar_moeda(abs(saldo_liquido))}</p>
                <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0;">
                    A Receber {formatar_moeda(total_receber)} - A Pagar {formatar_moeda(total_pagar)}</p>
            </div>
            <div style="text-align: center; padding: 0.8rem; background: {cor_alerta}20; border-radius: 8px;">
                <p style="color: {cor_alerta}; font-size: 0.75rem; font-weight: 600; margin: 0;">{msg_alerta}</p>
                <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0.3rem 0 0 0;">
                    Pagar: {pct_pagar_vencido:.0f}% vencido | Receber: {pct_receber_vencido:.0f}% vencido</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ========== KPIs PRINCIPAIS ==========
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['perigo']};
                    border-radius: 8px; padding: 0.7rem; text-align: center;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.65rem; margin: 0;">A PAGAR</p>
            <p style="color: {cores['perigo']}; font-size: 1.1rem; font-weight: 700; margin: 0.2rem 0;">
                {formatar_moeda(total_pagar)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.6rem; margin: 0;">
                {len(df_pagar_ic)} titulos</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['perigo']}50;
                    border-radius: 8px; padding: 0.7rem; text-align: center;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.65rem; margin: 0;">PAGAR VENCIDO</p>
            <p style="color: {cores['perigo']}; font-size: 1.1rem; font-weight: 700; margin: 0.2rem 0;">
                {formatar_moeda(pagar_vencido)}</p>
            <p style="color: {cores['perigo']}; font-size: 0.6rem; margin: 0;">
                {pct_pagar_vencido:.0f}%</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['sucesso']};
                    border-radius: 8px; padding: 0.7rem; text-align: center;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.65rem; margin: 0;">A RECEBER</p>
            <p style="color: {cores['sucesso']}; font-size: 1.1rem; font-weight: 700; margin: 0.2rem 0;">
                {formatar_moeda(total_receber)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.6rem; margin: 0;">
                {len(df_receber_ic)} titulos</p>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['sucesso']}50;
                    border-radius: 8px; padding: 0.7rem; text-align: center;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.65rem; margin: 0;">RECEBER VENCIDO</p>
            <p style="color: {cores['alerta']}; font-size: 1.1rem; font-weight: 700; margin: 0.2rem 0;">
                {formatar_moeda(receber_vencido)}</p>
            <p style="color: {cores['alerta']}; font-size: 0.6rem; margin: 0;">
                {pct_receber_vencido:.0f}%</p>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        # Potencial de compensacao (menor entre pagar e receber)
        potencial_comp = min(total_pagar, total_receber)
        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['info']};
                    border-radius: 8px; padding: 0.7rem; text-align: center;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.65rem; margin: 0;">POTENCIAL COMPENSAR</p>
            <p style="color: {cores['info']}; font-size: 1.1rem; font-weight: 700; margin: 0.2rem 0;">
                {formatar_moeda(potencial_comp)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.6rem; margin: 0;">
                possivel netting</p>
        </div>
        """, unsafe_allow_html=True)

    with col6:
        # Contrapartes unicas
        contrapartes_pagar = set(df_pagar_ic['CONTRAPARTE'].unique())
        contrapartes_receber = set(df_receber_ic['CONTRAPARTE'].unique())
        contrapartes_comum = len(contrapartes_pagar & contrapartes_receber)
        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['borda']};
                    border-radius: 8px; padding: 0.7rem; text-align: center;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.65rem; margin: 0;">CONTRAPARTES</p>
            <p style="color: {cores['texto']}; font-size: 1.1rem; font-weight: 700; margin: 0.2rem 0;">
                {len(contrapartes_pagar | contrapartes_receber)}</p>
            <p style="color: {cores['info']}; font-size: 0.6rem; margin: 0;">
                {contrapartes_comum} em ambos</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ========== TABS DE ANALISE ==========
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Posicao Liquida",
        "🏢 Por Tipo Empresa",
        "⏰ Aging Consolidado",
        "🔄 Fluxo Filiais",
        "📋 Detalhes"
    ])

    with tab1:
        _render_posicao_liquida(df_pagar_ic, df_receber_ic, cores)

    with tab2:
        _render_por_tipo_empresa(df_pagar_ic, df_receber_ic, cores)

    with tab3:
        _render_aging_consolidado(df_pagar_ic, df_receber_ic, cores)

    with tab4:
        _render_fluxo_filiais(df_pagar_ic, df_receber_ic, cores)

    with tab5:
        _render_detalhes(df_pagar_ic, df_receber_ic, cores)


def _render_posicao_liquida(df_pagar, df_receber, cores):
    """Posicao liquida por contraparte"""

    st.markdown(f"<p style='color: {cores['texto']}; font-weight: 600; font-size: 1rem;'>Posicao Liquida por Contraparte</p>", unsafe_allow_html=True)
    st.markdown(f"<p style='color: {cores['texto_secundario']}; font-size: 0.8rem;'>Saldo = A Receber - A Pagar (positivo = nos temos a receber)</p>", unsafe_allow_html=True)

    # Agrupar por contraparte
    pagar_grp = df_pagar.groupby('CONTRAPARTE').agg({
        'SALDO': 'sum',
        'NOME_FILIAL': 'count'
    }).reset_index()
    pagar_grp.columns = ['Contraparte', 'A_Pagar', 'Qtd_Pagar']

    receber_grp = df_receber.groupby('CONTRAPARTE').agg({
        'SALDO': 'sum',
        'NOME_FILIAL': 'count'
    }).reset_index()
    receber_grp.columns = ['Contraparte', 'A_Receber', 'Qtd_Receber']

    # Merge
    df_pos = pd.merge(pagar_grp, receber_grp, on='Contraparte', how='outer').fillna(0)
    df_pos['Saldo_Liquido'] = df_pos['A_Receber'] - df_pos['A_Pagar']
    df_pos['Posicao'] = df_pos['Saldo_Liquido'].apply(lambda x: 'Credora' if x >= 0 else 'Devedora')
    df_pos = df_pos.sort_values('Saldo_Liquido', ascending=True)

    col1, col2 = st.columns([3, 2])

    with col1:
        # Grafico de barras horizontais
        colors = [cores['sucesso'] if x >= 0 else cores['perigo'] for x in df_pos['Saldo_Liquido']]

        fig = go.Figure()

        fig.add_trace(go.Bar(
            y=df_pos['Contraparte'].str[:28],
            x=df_pos['Saldo_Liquido'],
            orientation='h',
            marker_color=colors,
            text=[formatar_moeda(x) for x in df_pos['Saldo_Liquido']],
            textposition='outside',
            textfont=dict(size=9, color=cores['texto'])
        ))

        # Linha zero
        fig.add_vline(x=0, line_dash="dash", line_color=cores['texto_secundario'], line_width=1)

        fig.update_layout(
            height=max(350, len(df_pos) * 40),
            margin=dict(l=10, r=100, t=10, b=10),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=True, gridcolor=cores['borda'], zeroline=False,
                      title='Saldo Liquido (+ = A Receber | - = A Pagar)',
                      titlefont=dict(size=10, color=cores['texto_secundario'])),
            yaxis=dict(tickfont=dict(color=cores['texto'], size=9))
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Resumo por posicao
        credores = df_pos[df_pos['Saldo_Liquido'] >= 0]
        devedores = df_pos[df_pos['Saldo_Liquido'] < 0]

        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['sucesso']};
                    border-radius: 10px; padding: 1rem; margin-bottom: 0.5rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0;">Posicao Credora</p>
            <p style="color: {cores['sucesso']}; font-size: 1.4rem; font-weight: 700; margin: 0;">
                {formatar_moeda(credores['Saldo_Liquido'].sum())}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.65rem; margin: 0;">
                {len(credores)} contrapartes nos devem</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['perigo']};
                    border-radius: 10px; padding: 1rem; margin-bottom: 0.5rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0;">Posicao Devedora</p>
            <p style="color: {cores['perigo']}; font-size: 1.4rem; font-weight: 700; margin: 0;">
                {formatar_moeda(abs(devedores['Saldo_Liquido'].sum()))}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.65rem; margin: 0;">
                {len(devedores)} contrapartes nos pagamos</p>
        </div>
        """, unsafe_allow_html=True)

        # Maior credor e devedor
        if len(credores) > 0:
            maior_credor = credores.loc[credores['Saldo_Liquido'].idxmax()]
            st.markdown(f"""
            <div style="background: {cores['fundo']}; border-radius: 6px; padding: 0.6rem; margin-bottom: 0.4rem;">
                <p style="color: {cores['texto_secundario']}; font-size: 0.65rem; margin: 0;">Maior credor</p>
                <p style="color: {cores['sucesso']}; font-size: 0.8rem; font-weight: 600; margin: 0;">
                    {maior_credor['Contraparte'][:20]}...</p>
                <p style="color: {cores['texto']}; font-size: 0.75rem; margin: 0;">
                    {formatar_moeda(maior_credor['Saldo_Liquido'])}</p>
            </div>
            """, unsafe_allow_html=True)

        if len(devedores) > 0:
            maior_devedor = devedores.loc[devedores['Saldo_Liquido'].idxmin()]
            st.markdown(f"""
            <div style="background: {cores['fundo']}; border-radius: 6px; padding: 0.6rem;">
                <p style="color: {cores['texto_secundario']}; font-size: 0.65rem; margin: 0;">Maior devedor</p>
                <p style="color: {cores['perigo']}; font-size: 0.8rem; font-weight: 600; margin: 0;">
                    {maior_devedor['Contraparte'][:20]}...</p>
                <p style="color: {cores['texto']}; font-size: 0.75rem; margin: 0;">
                    {formatar_moeda(abs(maior_devedor['Saldo_Liquido']))}</p>
            </div>
            """, unsafe_allow_html=True)

    # Tabela completa
    st.markdown(f"<p style='color: {cores['texto']}; font-weight: 600; margin-top: 1rem;'>Tabela Detalhada</p>", unsafe_allow_html=True)

    df_exib = df_pos[['Contraparte', 'A_Pagar', 'A_Receber', 'Saldo_Liquido', 'Posicao']].copy()
    df_exib = df_exib.sort_values('Saldo_Liquido', ascending=False)
    df_exib['A_Pagar'] = df_exib['A_Pagar'].apply(lambda x: formatar_moeda(x, completo=True))
    df_exib['A_Receber'] = df_exib['A_Receber'].apply(lambda x: formatar_moeda(x, completo=True))
    df_exib['Saldo_Liquido'] = df_exib['Saldo_Liquido'].apply(lambda x: formatar_moeda(x, completo=True))
    df_exib.columns = ['Contraparte', 'A Pagar', 'A Receber', 'Saldo Liquido', 'Posicao']

    st.dataframe(df_exib, use_container_width=True, hide_index=True, height=300)


def _render_por_tipo_empresa(df_pagar, df_receber, cores):
    """Analise por tipo de empresa do grupo"""

    st.markdown(f"<p style='color: {cores['texto']}; font-weight: 600; font-size: 1rem;'>Posicao por Tipo de Empresa</p>", unsafe_allow_html=True)

    # Agrupar por tipo
    pagar_tipo = df_pagar.groupby('TIPO_IC')['SALDO'].sum().reset_index()
    pagar_tipo.columns = ['Tipo', 'A_Pagar']

    receber_tipo = df_receber.groupby('TIPO_IC')['SALDO'].sum().reset_index()
    receber_tipo.columns = ['Tipo', 'A_Receber']

    df_tipo = pd.merge(pagar_tipo, receber_tipo, on='Tipo', how='outer').fillna(0)
    df_tipo['Saldo'] = df_tipo['A_Receber'] - df_tipo['A_Pagar']
    df_tipo = df_tipo.sort_values('Saldo', ascending=False)

    cores_tipo = {
        'Empresas Progresso': cores['primaria'],
        'Ouro Branco': cores['sucesso'],
        'Fazenda Peninsula': '#84cc16',
        'Hotelaria': cores['info'],
        'Outros': cores['texto_secundario']
    }

    col1, col2 = st.columns(2)

    with col1:
        # Grafico comparativo
        fig = go.Figure()

        fig.add_trace(go.Bar(
            name='A Pagar',
            x=df_tipo['Tipo'],
            y=df_tipo['A_Pagar'],
            marker_color=cores['perigo'],
            text=[formatar_moeda(v) for v in df_tipo['A_Pagar']],
            textposition='outside',
            textfont=dict(size=8)
        ))

        fig.add_trace(go.Bar(
            name='A Receber',
            x=df_tipo['Tipo'],
            y=df_tipo['A_Receber'],
            marker_color=cores['sucesso'],
            text=[formatar_moeda(v) for v in df_tipo['A_Receber']],
            textposition='outside',
            textfont=dict(size=8)
        ))

        fig.update_layout(
            barmode='group',
            height=350,
            margin=dict(l=10, r=10, t=30, b=80),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(tickfont=dict(color=cores['texto'], size=9), tickangle=-30),
            yaxis=dict(showticklabels=False, showgrid=False),
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5,
                       font=dict(color=cores['texto'], size=10))
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Cards por tipo
        for _, row in df_tipo.iterrows():
            cor = cores_tipo.get(row['Tipo'], cores['info'])
            saldo = row['Saldo']
            pos = "Credora" if saldo >= 0 else "Devedora"
            cor_saldo = cores['sucesso'] if saldo >= 0 else cores['perigo']

            st.markdown(f"""
            <div style="background: {cores['card']}; border-left: 4px solid {cor};
                        border-radius: 8px; padding: 0.7rem; margin-bottom: 0.4rem;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <p style="color: {cores['texto']}; font-size: 0.8rem; font-weight: 600; margin: 0;">
                            {row['Tipo']}</p>
                        <p style="color: {cores['texto_secundario']}; font-size: 0.65rem; margin: 0;">
                            Pagar: {formatar_moeda(row['A_Pagar'])} | Receber: {formatar_moeda(row['A_Receber'])}</p>
                    </div>
                    <div style="text-align: right;">
                        <p style="color: {cor_saldo}; font-size: 1rem; font-weight: 700; margin: 0;">
                            {formatar_moeda(abs(saldo))}</p>
                        <p style="color: {cor_saldo}; font-size: 0.6rem; margin: 0;">{pos}</p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)


def _render_aging_consolidado(df_pagar, df_receber, cores):
    """Aging consolidado de pagar e receber"""

    st.markdown(f"<p style='color: {cores['texto']}; font-weight: 600; font-size: 1rem;'>Aging Consolidado</p>", unsafe_allow_html=True)

    # Classificar aging
    def classificar_aging(dias):
        if pd.isna(dias):
            return '99_Sem data'
        elif dias >= 30:
            return '01_A vencer +30d'
        elif dias >= 0:
            return '02_A vencer 0-30d'
        elif dias >= -30:
            return '03_Vencido 1-30d'
        elif dias >= -60:
            return '04_Vencido 31-60d'
        elif dias >= -90:
            return '05_Vencido 61-90d'
        else:
            return '06_Vencido +90d'

    # Aplicar classificacao
    df_pagar_aging = df_pagar[df_pagar['SALDO'] > 0].copy()
    df_pagar_aging['FAIXA'] = df_pagar_aging['DIAS_VENC'].apply(classificar_aging)

    df_receber_aging = df_receber[df_receber['SALDO'] > 0].copy()
    df_receber_aging['FAIXA'] = df_receber_aging['DIAS_VENC'].apply(classificar_aging)

    # Agrupar
    pagar_grp = df_pagar_aging.groupby('FAIXA')['SALDO'].sum().reset_index()
    pagar_grp['ORIGEM'] = 'A Pagar'

    receber_grp = df_receber_aging.groupby('FAIXA')['SALDO'].sum().reset_index()
    receber_grp['ORIGEM'] = 'A Receber'

    df_aging = pd.concat([pagar_grp, receber_grp])
    df_aging = df_aging.sort_values('FAIXA')
    df_aging['LABEL'] = df_aging['FAIXA'].str[3:]

    # Cores por faixa
    cores_faixas = {
        'A vencer +30d': cores['sucesso'],
        'A vencer 0-30d': '#a3e635',
        'Vencido 1-30d': cores['alerta'],
        'Vencido 31-60d': '#fb923c',
        'Vencido 61-90d': '#ef4444',
        'Vencido +90d': '#991b1b',
        'Sem data': cores['texto_secundario']
    }

    col1, col2 = st.columns([3, 1])

    with col1:
        # Grafico de barras agrupadas
        fig = go.Figure()

        # Preparar dados para grafico
        faixas = df_aging['LABEL'].unique()
        pagar_vals = []
        receber_vals = []

        for f in faixas:
            p = df_aging[(df_aging['LABEL'] == f) & (df_aging['ORIGEM'] == 'A Pagar')]['SALDO'].sum()
            r = df_aging[(df_aging['LABEL'] == f) & (df_aging['ORIGEM'] == 'A Receber')]['SALDO'].sum()
            pagar_vals.append(p)
            receber_vals.append(r)

        fig.add_trace(go.Bar(
            name='A Pagar',
            x=list(faixas),
            y=pagar_vals,
            marker_color=cores['perigo'],
            text=[formatar_moeda(v) if v > 0 else '' for v in pagar_vals],
            textposition='outside',
            textfont=dict(size=8)
        ))

        fig.add_trace(go.Bar(
            name='A Receber',
            x=list(faixas),
            y=receber_vals,
            marker_color=cores['sucesso'],
            text=[formatar_moeda(v) if v > 0 else '' for v in receber_vals],
            textposition='outside',
            textfont=dict(size=8)
        ))

        fig.update_layout(
            barmode='group',
            height=350,
            margin=dict(l=10, r=10, t=40, b=80),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(tickfont=dict(color=cores['texto'], size=9), tickangle=-30),
            yaxis=dict(showticklabels=False, showgrid=False),
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5,
                       font=dict(color=cores['texto'], size=10))
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Resumo
        total_pagar_vencido = df_pagar_aging[df_pagar_aging['DIAS_VENC'] < 0]['SALDO'].sum()
        total_receber_vencido = df_receber_aging[df_receber_aging['DIAS_VENC'] < 0]['SALDO'].sum()
        total_pagar_a_vencer = df_pagar_aging[df_pagar_aging['DIAS_VENC'] >= 0]['SALDO'].sum()
        total_receber_a_vencer = df_receber_aging[df_receber_aging['DIAS_VENC'] >= 0]['SALDO'].sum()

        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['perigo']};
                    border-radius: 8px; padding: 0.8rem; margin-bottom: 0.4rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">Total Vencido</p>
            <div style="display: flex; justify-content: space-between; margin-top: 0.3rem;">
                <div>
                    <p style="color: {cores['perigo']}; font-size: 0.6rem; margin: 0;">Pagar</p>
                    <p style="color: {cores['perigo']}; font-size: 0.9rem; font-weight: 700; margin: 0;">
                        {formatar_moeda(total_pagar_vencido)}</p>
                </div>
                <div style="text-align: right;">
                    <p style="color: {cores['alerta']}; font-size: 0.6rem; margin: 0;">Receber</p>
                    <p style="color: {cores['alerta']}; font-size: 0.9rem; font-weight: 700; margin: 0;">
                        {formatar_moeda(total_receber_vencido)}</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['sucesso']};
                    border-radius: 8px; padding: 0.8rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">A Vencer</p>
            <div style="display: flex; justify-content: space-between; margin-top: 0.3rem;">
                <div>
                    <p style="color: {cores['perigo']}; font-size: 0.6rem; margin: 0;">Pagar</p>
                    <p style="color: {cores['texto']}; font-size: 0.9rem; font-weight: 700; margin: 0;">
                        {formatar_moeda(total_pagar_a_vencer)}</p>
                </div>
                <div style="text-align: right;">
                    <p style="color: {cores['sucesso']}; font-size: 0.6rem; margin: 0;">Receber</p>
                    <p style="color: {cores['texto']}; font-size: 0.9rem; font-weight: 700; margin: 0;">
                        {formatar_moeda(total_receber_a_vencer)}</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Saldo liquido vencido
        saldo_vencido = total_receber_vencido - total_pagar_vencido
        cor_sv = cores['sucesso'] if saldo_vencido >= 0 else cores['perigo']

        st.markdown(f"""
        <div style="background: {cores['fundo']}; border-radius: 6px; padding: 0.6rem; margin-top: 0.5rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.65rem; margin: 0;">Saldo Liquido Vencido</p>
            <p style="color: {cor_sv}; font-size: 1rem; font-weight: 700; margin: 0;">
                {formatar_moeda(saldo_vencido)}</p>
        </div>
        """, unsafe_allow_html=True)


def _render_fluxo_filiais(df_pagar, df_receber, cores):
    """Fluxo entre filiais do grupo"""

    st.markdown(f"<p style='color: {cores['texto']}; font-weight: 600; font-size: 1rem;'>Posicao por Filial</p>", unsafe_allow_html=True)

    # Agrupar por filial
    pagar_fil = df_pagar.groupby('NOME_FILIAL')['SALDO'].sum().reset_index()
    pagar_fil.columns = ['Filial', 'A_Pagar']

    receber_fil = df_receber.groupby('NOME_FILIAL')['SALDO'].sum().reset_index()
    receber_fil.columns = ['Filial', 'A_Receber']

    df_fil = pd.merge(pagar_fil, receber_fil, on='Filial', how='outer').fillna(0)
    df_fil['Saldo'] = df_fil['A_Receber'] - df_fil['A_Pagar']
    df_fil = df_fil.sort_values('Saldo', ascending=True)

    # Grafico
    colors = [cores['sucesso'] if x >= 0 else cores['perigo'] for x in df_fil['Saldo']]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=df_fil['Filial'].str[:25],
        x=df_fil['Saldo'],
        orientation='h',
        marker_color=colors,
        text=[formatar_moeda(x) for x in df_fil['Saldo']],
        textposition='outside',
        textfont=dict(size=9, color=cores['texto'])
    ))

    fig.add_vline(x=0, line_dash="dash", line_color=cores['texto_secundario'], line_width=1)

    fig.update_layout(
        height=max(350, len(df_fil) * 35),
        margin=dict(l=10, r=100, t=10, b=10),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=True, gridcolor=cores['borda'], zeroline=False,
                  title='Saldo Liquido (+ = Credora | - = Devedora)',
                  titlefont=dict(size=10, color=cores['texto_secundario'])),
        yaxis=dict(tickfont=dict(color=cores['texto'], size=9))
    )

    st.plotly_chart(fig, use_container_width=True)

    # Matriz Filial x Contraparte
    st.markdown(f"<p style='color: {cores['texto']}; font-weight: 600; margin-top: 1rem;'>Matriz Filial x Contraparte (Saldo Liquido)</p>", unsafe_allow_html=True)

    # Calcular saldo liquido por filial x contraparte
    pagar_matrix = df_pagar.groupby(['NOME_FILIAL', 'CONTRAPARTE'])['SALDO'].sum().reset_index()
    pagar_matrix.columns = ['Filial', 'Contraparte', 'Pagar']

    receber_matrix = df_receber.groupby(['NOME_FILIAL', 'CONTRAPARTE'])['SALDO'].sum().reset_index()
    receber_matrix.columns = ['Filial', 'Contraparte', 'Receber']

    df_matrix = pd.merge(pagar_matrix, receber_matrix, on=['Filial', 'Contraparte'], how='outer').fillna(0)
    df_matrix['Saldo'] = df_matrix['Receber'] - df_matrix['Pagar']

    # Pivot para heatmap
    top_filiais = df_fil.nlargest(8, 'Saldo', keep='first')['Filial'].tolist() + df_fil.nsmallest(4, 'Saldo', keep='first')['Filial'].tolist()
    top_filiais = list(dict.fromkeys(top_filiais))[:10]

    top_contrapartes = df_matrix.groupby('Contraparte')['Saldo'].apply(lambda x: abs(x).sum()).nlargest(6).index.tolist()

    df_matrix_filt = df_matrix[df_matrix['Filial'].isin(top_filiais) & df_matrix['Contraparte'].isin(top_contrapartes)]

    if len(df_matrix_filt) > 0:
        pivot = df_matrix_filt.pivot_table(index='Filial', columns='Contraparte', values='Saldo', aggfunc='sum', fill_value=0)

        # Abreviar nomes
        pivot.index = [f[:20] + '...' if len(f) > 20 else f for f in pivot.index]
        pivot.columns = [f[:15] + '...' if len(f) > 15 else f for f in pivot.columns]

        fig2 = go.Figure(data=go.Heatmap(
            z=pivot.values / 1e6,
            x=pivot.columns,
            y=pivot.index,
            colorscale=[
                [0, cores['perigo']],
                [0.5, cores['fundo']],
                [1, cores['sucesso']]
            ],
            zmid=0,
            text=[[f'{v/1e6:.1f}M' if abs(v) > 100000 else '' for v in row] for row in pivot.values],
            texttemplate='%{text}',
            textfont=dict(size=9, color='white'),
            hovertemplate='%{y} x %{x}<br>Saldo: R$ %{z:.2f}M<extra></extra>',
            colorbar=dict(title='Milhoes', tickfont=dict(color=cores['texto'], size=9),
                         titlefont=dict(color=cores['texto'], size=9))
        ))

        fig2.update_layout(
            height=350,
            margin=dict(l=10, r=10, t=10, b=80),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(tickfont=dict(color=cores['texto'], size=9), tickangle=-45),
            yaxis=dict(tickfont=dict(color=cores['texto'], size=9))
        )

        st.plotly_chart(fig2, use_container_width=True)
        st.caption("Verde = Posicao Credora (recebemos mais) | Vermelho = Posicao Devedora (pagamos mais)")


def _render_detalhes(df_pagar, df_receber, cores):
    """Tabela detalhada com filtros"""

    st.markdown(f"<p style='color: {cores['texto']}; font-weight: 600; font-size: 1rem;'>Detalhes dos Titulos</p>", unsafe_allow_html=True)

    # Filtros
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        origem_opcoes = ['Ambos', 'A Pagar', 'A Receber']
        filtro_origem = st.selectbox("Origem", origem_opcoes, key="cons_det_origem")

    with col2:
        contrapartes = ['Todas'] + sorted(list(set(
            df_pagar['CONTRAPARTE'].unique().tolist() +
            df_receber['CONTRAPARTE'].unique().tolist()
        )))
        filtro_contra = st.selectbox("Contraparte", contrapartes, key="cons_det_contra")

    with col3:
        filiais = ['Todas'] + sorted(list(set(
            df_pagar['NOME_FILIAL'].dropna().unique().tolist() +
            df_receber['NOME_FILIAL'].dropna().unique().tolist()
        )))
        filtro_filial = st.selectbox("Filial", filiais, key="cons_det_filial")

    with col4:
        status_opcoes = ['Todos', 'Pendente', 'Vencido']
        filtro_status = st.selectbox("Status", status_opcoes, key="cons_det_status")

    # Preparar dados
    df_p = df_pagar.copy()
    df_p['ORIGEM'] = 'A Pagar'

    df_r = df_receber.copy()
    df_r['ORIGEM'] = 'A Receber'

    if filtro_origem == 'A Pagar':
        df_show = df_p
    elif filtro_origem == 'A Receber':
        df_show = df_r
    else:
        df_show = pd.concat([df_p, df_r], ignore_index=True)

    # Aplicar filtros
    if filtro_contra != 'Todas':
        df_show = df_show[df_show['CONTRAPARTE'] == filtro_contra]

    if filtro_filial != 'Todas':
        df_show = df_show[df_show['NOME_FILIAL'] == filtro_filial]

    if filtro_status == 'Pendente':
        df_show = df_show[df_show['SALDO'] > 0]
    elif filtro_status == 'Vencido':
        df_show = df_show[(df_show['SALDO'] > 0) & (df_show['DIAS_VENC'] < 0)]

    # Ordenar por saldo
    df_show = df_show.sort_values('SALDO', ascending=False)

    # Metricas
    col1, col2, col3, col4 = st.columns(4)
    pagar_sum = df_show[df_show['ORIGEM'] == 'A Pagar']['SALDO'].sum()
    receber_sum = df_show[df_show['ORIGEM'] == 'A Receber']['SALDO'].sum()

    col1.metric("Titulos", formatar_numero(len(df_show)))
    col2.metric("A Pagar", formatar_moeda(pagar_sum))
    col3.metric("A Receber", formatar_moeda(receber_sum))
    col4.metric("Saldo Liquido", formatar_moeda(receber_sum - pagar_sum))

    st.markdown("---")

    # Tabela
    colunas = ['ORIGEM', 'NOME_FILIAL', 'CONTRAPARTE', 'TIPO_IC', 'EMISSAO', 'VENCIMENTO', 'VALOR_ORIGINAL', 'SALDO', 'STATUS']
    colunas_disp = [c for c in colunas if c in df_show.columns]

    df_exib = df_show[colunas_disp].head(100).copy()

    for col in ['EMISSAO', 'VENCIMENTO']:
        if col in df_exib.columns:
            df_exib[col] = pd.to_datetime(df_exib[col], errors='coerce').dt.strftime('%d/%m/%Y')

    for col in ['VALOR_ORIGINAL', 'SALDO']:
        if col in df_exib.columns:
            df_exib[col] = df_exib[col].apply(lambda x: f"R$ {x:,.2f}" if pd.notna(x) else '-')

    rename = {
        'ORIGEM': 'Origem',
        'NOME_FILIAL': 'Filial',
        'CONTRAPARTE': 'Contraparte',
        'TIPO_IC': 'Tipo',
        'EMISSAO': 'Emissao',
        'VENCIMENTO': 'Vencimento',
        'VALOR_ORIGINAL': 'Valor',
        'SALDO': 'Saldo',
        'STATUS': 'Status'
    }
    df_exib = df_exib.rename(columns=rename)

    st.dataframe(df_exib, use_container_width=True, hide_index=True, height=450)
    st.caption(f"Exibindo {len(df_exib)} de {len(df_show)} registros")
