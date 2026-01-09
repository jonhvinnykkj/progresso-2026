"""
Intercompany Unificado - Visao Completa A Pagar + A Receber
Dashboard Financeiro - Grupo Progresso
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


def carregar_dados_intercompany():
    """Carrega e processa dados de ambas as bases (Pagar e Receber)"""

    # Carregar dados brutos
    df_pagar_raw, _, _ = carregar_dados()
    df_receber_raw, _, _ = carregar_dados_receber()

    # Filtrar apenas intercompany - PAGAR
    mask_pagar = df_pagar_raw['NOME_FORNECEDOR'].str.upper().str.contains(
        '|'.join(INTERCOMPANY_PATTERNS), na=False, regex=True
    )
    df_pagar = df_pagar_raw[mask_pagar].copy()
    df_pagar['CONTRAPARTE'] = df_pagar['NOME_FORNECEDOR']
    df_pagar['TIPO_IC'] = df_pagar['CONTRAPARTE'].apply(classificar_tipo_ic)
    df_pagar['ORIGEM'] = 'A Pagar'

    # Filtrar apenas intercompany - RECEBER
    mask_receber = df_receber_raw['NOME_CLIENTE'].str.upper().str.contains(
        '|'.join(INTERCOMPANY_PATTERNS), na=False, regex=True
    )
    df_receber = df_receber_raw[mask_receber].copy()
    df_receber['CONTRAPARTE'] = df_receber['NOME_CLIENTE']
    df_receber['TIPO_IC'] = df_receber['CONTRAPARTE'].apply(classificar_tipo_ic)
    df_receber['ORIGEM'] = 'A Receber'

    return df_pagar, df_receber


def render_intercompany_unificado():
    """Renderiza a pagina unificada de Intercompany"""

    cores = get_cores()
    hoje = datetime.now()

    # Carregar dados
    df_pagar, df_receber = carregar_dados_intercompany()

    # ========== CALCULOS PRINCIPAIS ==========
    total_pagar = df_pagar['SALDO'].sum()
    total_receber = df_receber['SALDO'].sum()
    saldo_liquido = total_receber - total_pagar

    # Vencidos
    pagar_vencido = df_pagar[(df_pagar['SALDO'] > 0) & (df_pagar['DIAS_VENC'] < 0)]['SALDO'].sum()
    receber_vencido = df_receber[(df_receber['SALDO'] > 0) & (df_receber['DIAS_VENC'] < 0)]['SALDO'].sum()

    # A vencer
    pagar_a_vencer = df_pagar[(df_pagar['SALDO'] > 0) & (df_pagar['DIAS_VENC'] >= 0)]['SALDO'].sum()
    receber_a_vencer = df_receber[(df_receber['SALDO'] > 0) & (df_receber['DIAS_VENC'] >= 0)]['SALDO'].sum()

    pct_pagar_vencido = (pagar_vencido / total_pagar * 100) if total_pagar > 0 else 0
    pct_receber_vencido = (receber_vencido / total_receber * 100) if total_receber > 0 else 0

    # Potencial compensacao
    potencial_compensar = min(total_pagar, total_receber)

    # Contrapartes
    contrapartes_pagar = set(df_pagar['CONTRAPARTE'].unique())
    contrapartes_receber = set(df_receber['CONTRAPARTE'].unique())
    total_contrapartes = len(contrapartes_pagar | contrapartes_receber)
    contrapartes_ambos = len(contrapartes_pagar & contrapartes_receber)

    # ========== HEADER PRINCIPAL ==========
    if saldo_liquido < 0:
        cor_saldo = cores['perigo']
        msg_posicao = "POSICAO DEVEDORA"
        icone_posicao = "⚠️"
        desc_posicao = "Devemos mais do que temos a receber"
    else:
        cor_saldo = cores['sucesso']
        msg_posicao = "POSICAO CREDORA"
        icone_posicao = "✅"
        desc_posicao = "Temos mais a receber do que devemos"

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, {cor_saldo}15, {cores['card']});
                border: 2px solid {cor_saldo}; border-radius: 16px;
                padding: 1.5rem; margin-bottom: 1.25rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
            <div>
                <p style="color: {cor_saldo}; font-size: 0.9rem; font-weight: 600; margin: 0; letter-spacing: 0.5px;">
                    {icone_posicao} {msg_posicao} NO GRUPO</p>
                <p style="color: {cores['texto']}; font-size: 2.5rem; font-weight: 700; margin: 0.25rem 0;">
                    {formatar_moeda(abs(saldo_liquido))}</p>
                <p style="color: {cores['texto_secundario']}; font-size: 0.85rem; margin: 0;">
                    {desc_posicao}</p>
            </div>
            <div style="display: flex; gap: 2rem; flex-wrap: wrap;">
                <div style="text-align: center; padding: 1rem; background: {cores['perigo']}15; border-radius: 10px; min-width: 140px;">
                    <p style="color: {cores['perigo']}; font-size: 0.7rem; font-weight: 600; margin: 0;">DEVEMOS</p>
                    <p style="color: {cores['perigo']}; font-size: 1.5rem; font-weight: 700; margin: 0.2rem 0;">
                        {formatar_moeda(total_pagar)}</p>
                    <p style="color: {cores['texto_secundario']}; font-size: 0.65rem; margin: 0;">
                        {pct_pagar_vencido:.0f}% vencido</p>
                </div>
                <div style="text-align: center; padding: 1rem; background: {cores['sucesso']}15; border-radius: 10px; min-width: 140px;">
                    <p style="color: {cores['sucesso']}; font-size: 0.7rem; font-weight: 600; margin: 0;">A RECEBER</p>
                    <p style="color: {cores['sucesso']}; font-size: 1.5rem; font-weight: 700; margin: 0.2rem 0;">
                        {formatar_moeda(total_receber)}</p>
                    <p style="color: {cores['texto_secundario']}; font-size: 0.65rem; margin: 0;">
                        {pct_receber_vencido:.0f}% vencido</p>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ========== KPIs SECUNDARIOS ==========
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['borda']};
                    border-radius: 10px; padding: 0.9rem; text-align: center;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">Pagar Vencido</p>
            <p style="color: {cores['perigo']}; font-size: 1.2rem; font-weight: 700; margin: 0.2rem 0;">
                {formatar_moeda(pagar_vencido)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.65rem; margin: 0;">
                {len(df_pagar[(df_pagar['SALDO'] > 0) & (df_pagar['DIAS_VENC'] < 0)])} titulos</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['borda']};
                    border-radius: 10px; padding: 0.9rem; text-align: center;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">Receber Vencido</p>
            <p style="color: {cores['alerta']}; font-size: 1.2rem; font-weight: 700; margin: 0.2rem 0;">
                {formatar_moeda(receber_vencido)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.65rem; margin: 0;">
                {len(df_receber[(df_receber['SALDO'] > 0) & (df_receber['DIAS_VENC'] < 0)])} titulos</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['info']};
                    border-radius: 10px; padding: 0.9rem; text-align: center;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">Potencial Netting</p>
            <p style="color: {cores['info']}; font-size: 1.2rem; font-weight: 700; margin: 0.2rem 0;">
                {formatar_moeda(potencial_compensar)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.65rem; margin: 0;">
                compensacao possivel</p>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['borda']};
                    border-radius: 10px; padding: 0.9rem; text-align: center;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">Contrapartes</p>
            <p style="color: {cores['texto']}; font-size: 1.2rem; font-weight: 700; margin: 0.2rem 0;">
                {total_contrapartes}</p>
            <p style="color: {cores['info']}; font-size: 0.65rem; margin: 0;">
                {contrapartes_ambos} em ambos os lados</p>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        # Maior exposicao
        exposicao_pagar = df_pagar.groupby('CONTRAPARTE')['SALDO'].sum()
        exposicao_receber = df_receber.groupby('CONTRAPARTE')['SALDO'].sum()
        maior_credor = exposicao_receber.idxmax() if len(exposicao_receber) > 0 else "N/A"
        maior_devedor = exposicao_pagar.idxmax() if len(exposicao_pagar) > 0 else "N/A"

        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['borda']};
                    border-radius: 10px; padding: 0.9rem; text-align: center;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">Maior Exposicao</p>
            <p style="color: {cores['texto']}; font-size: 0.75rem; font-weight: 600; margin: 0.2rem 0;
                      overflow: hidden; text-overflow: ellipsis; white-space: nowrap;"
               title="{maior_devedor}">{maior_devedor[:18]}...</p>
            <p style="color: {cores['perigo']}; font-size: 0.65rem; margin: 0;">
                {formatar_moeda(exposicao_pagar.max()) if len(exposicao_pagar) > 0 else 'R$ 0'}</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)

    # ========== TABS ==========
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📊 Visao Geral",
        "💰 A Pagar",
        "💵 A Receber",
        "🏢 Contrapartes",
        "📍 Filiais",
        "⏰ Aging",
        "📋 Detalhes"
    ])

    with tab1:
        _render_visao_geral(df_pagar, df_receber, cores)

    with tab2:
        _render_a_pagar(df_pagar, cores)

    with tab3:
        _render_a_receber(df_receber, cores)

    with tab4:
        _render_contrapartes(df_pagar, df_receber, cores)

    with tab5:
        _render_filiais(df_pagar, df_receber, cores)

    with tab6:
        _render_aging(df_pagar, df_receber, cores)

    with tab7:
        _render_detalhes(df_pagar, df_receber, cores)


def _render_visao_geral(df_pagar, df_receber, cores):
    """Visao geral com graficos comparativos"""

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"<p style='color: {cores['texto']}; font-weight: 600;'>Comparativo Pagar vs Receber</p>", unsafe_allow_html=True)

        # Grafico comparativo
        total_pagar = df_pagar['SALDO'].sum()
        total_receber = df_receber['SALDO'].sum()
        pagar_vencido = df_pagar[(df_pagar['SALDO'] > 0) & (df_pagar['DIAS_VENC'] < 0)]['SALDO'].sum()
        pagar_a_vencer = total_pagar - pagar_vencido
        receber_vencido = df_receber[(df_receber['SALDO'] > 0) & (df_receber['DIAS_VENC'] < 0)]['SALDO'].sum()
        receber_a_vencer = total_receber - receber_vencido

        fig = go.Figure()

        fig.add_trace(go.Bar(
            name='Vencido',
            x=['A Pagar', 'A Receber'],
            y=[pagar_vencido, receber_vencido],
            marker_color=cores['perigo'],
            text=[formatar_moeda(pagar_vencido), formatar_moeda(receber_vencido)],
            textposition='inside',
            textfont=dict(color='white', size=11)
        ))

        fig.add_trace(go.Bar(
            name='A Vencer',
            x=['A Pagar', 'A Receber'],
            y=[pagar_a_vencer, receber_a_vencer],
            marker_color=cores['sucesso'],
            text=[formatar_moeda(pagar_a_vencer), formatar_moeda(receber_a_vencer)],
            textposition='inside',
            textfont=dict(color='white', size=11)
        ))

        fig.update_layout(
            barmode='stack',
            height=300,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(tickfont=dict(color=cores['texto'], size=12)),
            yaxis=dict(showticklabels=False, showgrid=False),
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5,
                       font=dict(color=cores['texto'], size=10))
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown(f"<p style='color: {cores['texto']}; font-weight: 600;'>Posicao por Tipo de Empresa</p>", unsafe_allow_html=True)

        # Agrupar por tipo
        pagar_tipo = df_pagar.groupby('TIPO_IC')['SALDO'].sum().reset_index()
        pagar_tipo.columns = ['Tipo', 'Pagar']

        receber_tipo = df_receber.groupby('TIPO_IC')['SALDO'].sum().reset_index()
        receber_tipo.columns = ['Tipo', 'Receber']

        df_tipo = pd.merge(pagar_tipo, receber_tipo, on='Tipo', how='outer').fillna(0)
        df_tipo['Saldo'] = df_tipo['Receber'] - df_tipo['Pagar']
        df_tipo = df_tipo.sort_values('Saldo')

        colors = [cores['sucesso'] if x >= 0 else cores['perigo'] for x in df_tipo['Saldo']]

        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            y=df_tipo['Tipo'],
            x=df_tipo['Saldo'],
            orientation='h',
            marker_color=colors,
            text=[formatar_moeda(x) for x in df_tipo['Saldo']],
            textposition='outside',
            textfont=dict(size=10, color=cores['texto'])
        ))

        fig2.add_vline(x=0, line_dash="dash", line_color=cores['texto_secundario'], line_width=1)

        fig2.update_layout(
            height=300,
            margin=dict(l=10, r=80, t=10, b=10),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
            yaxis=dict(tickfont=dict(color=cores['texto'], size=10))
        )

        st.plotly_chart(fig2, use_container_width=True)

    # Top 5 maiores posicoes
    st.markdown(f"<p style='color: {cores['texto']}; font-weight: 600; margin-top: 1rem;'>Top 10 Maiores Posicoes (Saldo Liquido)</p>", unsafe_allow_html=True)

    # Calcular saldo por contraparte
    pagar_cp = df_pagar.groupby('CONTRAPARTE')['SALDO'].sum().reset_index()
    pagar_cp.columns = ['Contraparte', 'Pagar']

    receber_cp = df_receber.groupby('CONTRAPARTE')['SALDO'].sum().reset_index()
    receber_cp.columns = ['Contraparte', 'Receber']

    df_cp = pd.merge(pagar_cp, receber_cp, on='Contraparte', how='outer').fillna(0)
    df_cp['Saldo'] = df_cp['Receber'] - df_cp['Pagar']
    df_cp['Abs_Saldo'] = df_cp['Saldo'].abs()
    df_cp = df_cp.nlargest(10, 'Abs_Saldo').sort_values('Saldo')

    colors = [cores['sucesso'] if x >= 0 else cores['perigo'] for x in df_cp['Saldo']]

    fig3 = go.Figure()
    fig3.add_trace(go.Bar(
        y=df_cp['Contraparte'].str[:30],
        x=df_cp['Saldo'],
        orientation='h',
        marker_color=colors,
        text=[formatar_moeda(x) for x in df_cp['Saldo']],
        textposition='outside',
        textfont=dict(size=9, color=cores['texto'])
    ))

    fig3.add_vline(x=0, line_dash="dash", line_color=cores['texto_secundario'], line_width=1)

    fig3.update_layout(
        height=400,
        margin=dict(l=10, r=100, t=10, b=10),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showticklabels=False, showgrid=True, gridcolor=cores['borda'], zeroline=False),
        yaxis=dict(tickfont=dict(color=cores['texto'], size=9))
    )

    st.plotly_chart(fig3, use_container_width=True)
    st.caption("Verde = Credores (nos devem) | Vermelho = Devedores (devemos)")


def _render_a_pagar(df_pagar, cores):
    """Detalhes do que devemos para o grupo"""

    total = df_pagar['SALDO'].sum()
    vencido = df_pagar[(df_pagar['SALDO'] > 0) & (df_pagar['DIAS_VENC'] < 0)]['SALDO'].sum()

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown(f"<p style='color: {cores['texto']}; font-weight: 600;'>Para quem Devemos (Top 10)</p>", unsafe_allow_html=True)

        # Top fornecedores
        df_forn = df_pagar.groupby('CONTRAPARTE').agg({
            'SALDO': ['sum', 'count'],
            'DIAS_VENC': 'min'
        }).reset_index()
        df_forn.columns = ['Fornecedor', 'Saldo', 'Qtd', 'Dias_Venc']
        df_forn = df_forn.nlargest(10, 'Saldo')

        # Separar vencido e a vencer por fornecedor
        fig = go.Figure()

        for _, row in df_forn.iterrows():
            venc = df_pagar[(df_pagar['CONTRAPARTE'] == row['Fornecedor']) &
                           (df_pagar['DIAS_VENC'] < 0)]['SALDO'].sum()
            a_venc = row['Saldo'] - venc

            fig.add_trace(go.Bar(
                y=[row['Fornecedor'][:25]],
                x=[venc],
                orientation='h',
                marker_color=cores['perigo'],
                showlegend=False,
                text=formatar_moeda(venc) if venc > 1000000 else '',
                textposition='inside',
                textfont=dict(size=9, color='white')
            ))

            fig.add_trace(go.Bar(
                y=[row['Fornecedor'][:25]],
                x=[a_venc],
                orientation='h',
                marker_color=cores['sucesso'],
                showlegend=False,
                text=formatar_moeda(a_venc) if a_venc > 1000000 else '',
                textposition='inside',
                textfont=dict(size=9, color='white')
            ))

        fig.update_layout(
            barmode='stack',
            height=400,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showticklabels=False, showgrid=False),
            yaxis=dict(tickfont=dict(color=cores['texto'], size=9), autorange='reversed')
        )

        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"Vermelho = Vencido | Verde = A Vencer")

    with col2:
        # Cards resumo
        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['perigo']};
                    border-radius: 10px; padding: 1rem; margin-bottom: 0.75rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0;">Total A Pagar IC</p>
            <p style="color: {cores['perigo']}; font-size: 1.8rem; font-weight: 700; margin: 0;">
                {formatar_moeda(total)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">
                {len(df_pagar)} titulos</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['borda']};
                    border-radius: 10px; padding: 1rem; margin-bottom: 0.75rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0;">Vencido</p>
            <p style="color: {cores['perigo']}; font-size: 1.5rem; font-weight: 700; margin: 0;">
                {formatar_moeda(vencido)}</p>
            <p style="color: {cores['perigo']}; font-size: 0.7rem; margin: 0;">
                {(vencido/total*100):.0f}% do total</p>
        </div>
        """, unsafe_allow_html=True)

        # Dias medio de atraso
        dias_medio = df_pagar[df_pagar['DIAS_VENC'] < 0]['DIAS_VENC'].abs().mean()
        dias_medio = dias_medio if pd.notna(dias_medio) else 0

        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['borda']};
                    border-radius: 10px; padding: 1rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0;">Dias Medio Atraso</p>
            <p style="color: {cores['alerta']}; font-size: 1.5rem; font-weight: 700; margin: 0;">
                {dias_medio:.0f} dias</p>
        </div>
        """, unsafe_allow_html=True)


def _render_a_receber(df_receber, cores):
    """Detalhes do que temos a receber do grupo"""

    total = df_receber['SALDO'].sum()
    vencido = df_receber[(df_receber['SALDO'] > 0) & (df_receber['DIAS_VENC'] < 0)]['SALDO'].sum()

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown(f"<p style='color: {cores['texto']}; font-weight: 600;'>Quem nos Deve (Top 10)</p>", unsafe_allow_html=True)

        # Top clientes
        df_cli = df_receber.groupby('CONTRAPARTE').agg({
            'SALDO': ['sum', 'count'],
            'DIAS_VENC': 'min'
        }).reset_index()
        df_cli.columns = ['Cliente', 'Saldo', 'Qtd', 'Dias_Venc']
        df_cli = df_cli.nlargest(10, 'Saldo')

        fig = go.Figure()

        for _, row in df_cli.iterrows():
            venc = df_receber[(df_receber['CONTRAPARTE'] == row['Cliente']) &
                             (df_receber['DIAS_VENC'] < 0)]['SALDO'].sum()
            a_venc = row['Saldo'] - venc

            fig.add_trace(go.Bar(
                y=[row['Cliente'][:25]],
                x=[venc],
                orientation='h',
                marker_color=cores['perigo'],
                showlegend=False,
                text=formatar_moeda(venc) if venc > 1000000 else '',
                textposition='inside',
                textfont=dict(size=9, color='white')
            ))

            fig.add_trace(go.Bar(
                y=[row['Cliente'][:25]],
                x=[a_venc],
                orientation='h',
                marker_color=cores['sucesso'],
                showlegend=False,
                text=formatar_moeda(a_venc) if a_venc > 1000000 else '',
                textposition='inside',
                textfont=dict(size=9, color='white')
            ))

        fig.update_layout(
            barmode='stack',
            height=400,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showticklabels=False, showgrid=False),
            yaxis=dict(tickfont=dict(color=cores['texto'], size=9), autorange='reversed')
        )

        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"Vermelho = Vencido | Verde = A Vencer")

    with col2:
        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['sucesso']};
                    border-radius: 10px; padding: 1rem; margin-bottom: 0.75rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0;">Total A Receber IC</p>
            <p style="color: {cores['sucesso']}; font-size: 1.8rem; font-weight: 700; margin: 0;">
                {formatar_moeda(total)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">
                {len(df_receber)} titulos</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['borda']};
                    border-radius: 10px; padding: 1rem; margin-bottom: 0.75rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0;">Vencido</p>
            <p style="color: {cores['alerta']}; font-size: 1.5rem; font-weight: 700; margin: 0;">
                {formatar_moeda(vencido)}</p>
            <p style="color: {cores['alerta']}; font-size: 0.7rem; margin: 0;">
                {(vencido/total*100):.0f}% do total</p>
        </div>
        """, unsafe_allow_html=True)

        dias_medio = df_receber[df_receber['DIAS_VENC'] < 0]['DIAS_VENC'].abs().mean()
        dias_medio = dias_medio if pd.notna(dias_medio) else 0

        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['borda']};
                    border-radius: 10px; padding: 1rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0;">Dias Medio Atraso</p>
            <p style="color: {cores['alerta']}; font-size: 1.5rem; font-weight: 700; margin: 0;">
                {dias_medio:.0f} dias</p>
        </div>
        """, unsafe_allow_html=True)


def _render_contrapartes(df_pagar, df_receber, cores):
    """Posicao liquida por contraparte"""

    st.markdown(f"<p style='color: {cores['texto']}; font-weight: 600;'>Posicao Liquida por Contraparte</p>", unsafe_allow_html=True)
    st.markdown(f"<p style='color: {cores['texto_secundario']}; font-size: 0.8rem;'>Saldo = A Receber - A Pagar (positivo = eles nos devem)</p>", unsafe_allow_html=True)

    # Calcular posicao por contraparte
    pagar_cp = df_pagar.groupby(['CONTRAPARTE', 'TIPO_IC'])['SALDO'].sum().reset_index()
    pagar_cp.columns = ['Contraparte', 'Tipo', 'Pagar']

    receber_cp = df_receber.groupby(['CONTRAPARTE', 'TIPO_IC'])['SALDO'].sum().reset_index()
    receber_cp.columns = ['Contraparte', 'Tipo', 'Receber']

    df_cp = pd.merge(pagar_cp, receber_cp, on=['Contraparte', 'Tipo'], how='outer').fillna(0)
    df_cp['Saldo'] = df_cp['Receber'] - df_cp['Pagar']
    df_cp = df_cp.sort_values('Saldo')

    col1, col2 = st.columns([3, 1])

    with col1:
        colors = [cores['sucesso'] if x >= 0 else cores['perigo'] for x in df_cp['Saldo']]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=df_cp['Contraparte'].str[:30],
            x=df_cp['Saldo'],
            orientation='h',
            marker_color=colors,
            text=[formatar_moeda(x) for x in df_cp['Saldo']],
            textposition='outside',
            textfont=dict(size=9, color=cores['texto'])
        ))

        fig.add_vline(x=0, line_dash="dash", line_color=cores['texto_secundario'], line_width=1)

        fig.update_layout(
            height=max(400, len(df_cp) * 35),
            margin=dict(l=10, r=100, t=10, b=10),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showticklabels=False, showgrid=True, gridcolor=cores['borda'], zeroline=False),
            yaxis=dict(tickfont=dict(color=cores['texto'], size=9))
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Resumo
        credores = df_cp[df_cp['Saldo'] > 0]
        devedores = df_cp[df_cp['Saldo'] < 0]

        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['sucesso']};
                    border-radius: 10px; padding: 1rem; margin-bottom: 0.75rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0;">Posicao Credora</p>
            <p style="color: {cores['sucesso']}; font-size: 1.3rem; font-weight: 700; margin: 0;">
                {formatar_moeda(credores['Saldo'].sum())}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">
                {len(credores)} nos devem</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['perigo']};
                    border-radius: 10px; padding: 1rem; margin-bottom: 0.75rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0;">Posicao Devedora</p>
            <p style="color: {cores['perigo']}; font-size: 1.3rem; font-weight: 700; margin: 0;">
                {formatar_moeda(abs(devedores['Saldo'].sum()))}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">
                {len(devedores)} devemos</p>
        </div>
        """, unsafe_allow_html=True)

        # Maior credor e devedor
        if len(credores) > 0:
            maior_credor = credores.nlargest(1, 'Saldo').iloc[0]
            st.markdown(f"""
            <div style="background: {cores['card']}; border-left: 4px solid {cores['sucesso']};
                        border-radius: 8px; padding: 0.75rem; margin-bottom: 0.5rem;">
                <p style="color: {cores['texto_secundario']}; font-size: 0.65rem; margin: 0;">Maior Credor</p>
                <p style="color: {cores['texto']}; font-size: 0.75rem; font-weight: 600; margin: 0;
                          overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                    {maior_credor['Contraparte'][:20]}</p>
                <p style="color: {cores['sucesso']}; font-size: 0.9rem; font-weight: 700; margin: 0;">
                    {formatar_moeda(maior_credor['Saldo'])}</p>
            </div>
            """, unsafe_allow_html=True)

        if len(devedores) > 0:
            maior_devedor = devedores.nsmallest(1, 'Saldo').iloc[0]
            st.markdown(f"""
            <div style="background: {cores['card']}; border-left: 4px solid {cores['perigo']};
                        border-radius: 8px; padding: 0.75rem;">
                <p style="color: {cores['texto_secundario']}; font-size: 0.65rem; margin: 0;">Maior Devedor</p>
                <p style="color: {cores['texto']}; font-size: 0.75rem; font-weight: 600; margin: 0;
                          overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                    {maior_devedor['Contraparte'][:20]}</p>
                <p style="color: {cores['perigo']}; font-size: 0.9rem; font-weight: 700; margin: 0;">
                    {formatar_moeda(abs(maior_devedor['Saldo']))}</p>
            </div>
            """, unsafe_allow_html=True)

    # Tabela detalhada
    st.markdown(f"<p style='color: {cores['texto']}; font-weight: 600; margin-top: 1.5rem;'>Tabela de Posicoes</p>", unsafe_allow_html=True)

    df_tabela = df_cp[['Contraparte', 'Tipo', 'Pagar', 'Receber', 'Saldo']].copy()
    df_tabela['Posicao'] = df_tabela['Saldo'].apply(lambda x: 'Credor' if x >= 0 else 'Devedor')
    df_tabela = df_tabela.sort_values('Saldo', ascending=False)

    df_tabela['Pagar'] = df_tabela['Pagar'].apply(lambda x: formatar_moeda(x, completo=True))
    df_tabela['Receber'] = df_tabela['Receber'].apply(lambda x: formatar_moeda(x, completo=True))
    df_tabela['Saldo'] = df_tabela['Saldo'].apply(lambda x: formatar_moeda(x, completo=True))

    st.dataframe(df_tabela, use_container_width=True, hide_index=True, height=300)


def _render_filiais(df_pagar, df_receber, cores):
    """Posicao por filial"""

    st.markdown(f"<p style='color: {cores['texto']}; font-weight: 600;'>Posicao por Filial</p>", unsafe_allow_html=True)
    st.markdown(f"<p style='color: {cores['texto_secundario']}; font-size: 0.8rem;'>Como cada filial esta posicionada no intercompany</p>", unsafe_allow_html=True)

    # Agrupar por filial
    pagar_fil = df_pagar.groupby('NOME_FILIAL')['SALDO'].sum().reset_index()
    pagar_fil.columns = ['Filial', 'Pagar']

    receber_fil = df_receber.groupby('NOME_FILIAL')['SALDO'].sum().reset_index()
    receber_fil.columns = ['Filial', 'Receber']

    df_fil = pd.merge(pagar_fil, receber_fil, on='Filial', how='outer').fillna(0)
    df_fil['Saldo'] = df_fil['Receber'] - df_fil['Pagar']
    df_fil = df_fil.sort_values('Saldo')

    col1, col2 = st.columns([3, 1])

    with col1:
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
            xaxis=dict(showticklabels=False, showgrid=True, gridcolor=cores['borda'], zeroline=False),
            yaxis=dict(tickfont=dict(color=cores['texto'], size=9))
        )

        st.plotly_chart(fig, use_container_width=True)
        st.caption("Positivo = Filial credora (recebe mais do grupo) | Negativo = Filial devedora (deve mais ao grupo)")

    with col2:
        # Top credora e devedora
        if len(df_fil[df_fil['Saldo'] >= 0]) > 0:
            top_credora = df_fil[df_fil['Saldo'] >= 0].nlargest(1, 'Saldo').iloc[0]
            st.markdown(f"""
            <div style="background: {cores['card']}; border: 1px solid {cores['sucesso']};
                        border-radius: 10px; padding: 1rem; margin-bottom: 0.75rem;">
                <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">Maior Credora</p>
                <p style="color: {cores['texto']}; font-size: 0.8rem; font-weight: 600; margin: 0.2rem 0;">
                    {top_credora['Filial'][:20]}</p>
                <p style="color: {cores['sucesso']}; font-size: 1.2rem; font-weight: 700; margin: 0;">
                    {formatar_moeda(top_credora['Saldo'])}</p>
            </div>
            """, unsafe_allow_html=True)

        if len(df_fil[df_fil['Saldo'] < 0]) > 0:
            top_devedora = df_fil[df_fil['Saldo'] < 0].nsmallest(1, 'Saldo').iloc[0]
            st.markdown(f"""
            <div style="background: {cores['card']}; border: 1px solid {cores['perigo']};
                        border-radius: 10px; padding: 1rem; margin-bottom: 0.75rem;">
                <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">Maior Devedora</p>
                <p style="color: {cores['texto']}; font-size: 0.8rem; font-weight: 600; margin: 0.2rem 0;">
                    {top_devedora['Filial'][:20]}</p>
                <p style="color: {cores['perigo']}; font-size: 1.2rem; font-weight: 700; margin: 0;">
                    {formatar_moeda(abs(top_devedora['Saldo']))}</p>
            </div>
            """, unsafe_allow_html=True)

        # Totais
        total_credoras = df_fil[df_fil['Saldo'] >= 0]['Saldo'].sum()
        total_devedoras = abs(df_fil[df_fil['Saldo'] < 0]['Saldo'].sum())

        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['borda']};
                    border-radius: 10px; padding: 1rem;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                <span style="color: {cores['texto_secundario']}; font-size: 0.7rem;">Credoras</span>
                <span style="color: {cores['sucesso']}; font-size: 0.8rem; font-weight: 600;">
                    {len(df_fil[df_fil['Saldo'] >= 0])}</span>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <span style="color: {cores['texto_secundario']}; font-size: 0.7rem;">Devedoras</span>
                <span style="color: {cores['perigo']}; font-size: 0.8rem; font-weight: 600;">
                    {len(df_fil[df_fil['Saldo'] < 0])}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)


def _render_aging(df_pagar, df_receber, cores):
    """Aging consolidado"""

    st.markdown(f"<p style='color: {cores['texto']}; font-weight: 600;'>Aging Consolidado</p>", unsafe_allow_html=True)

    def classificar_aging(dias):
        if pd.isna(dias):
            return '99_Sem data'
        elif dias >= 30:
            return '01_+30 dias'
        elif dias >= 0:
            return '02_0-30 dias'
        elif dias >= -30:
            return '03_Venc 1-30d'
        elif dias >= -90:
            return '04_Venc 31-90d'
        elif dias >= -180:
            return '05_Venc 91-180d'
        else:
            return '06_Venc +180d'

    # Aplicar aging
    df_pagar_aging = df_pagar[df_pagar['SALDO'] > 0].copy()
    df_pagar_aging['FAIXA'] = df_pagar_aging['DIAS_VENC'].apply(classificar_aging)

    df_receber_aging = df_receber[df_receber['SALDO'] > 0].copy()
    df_receber_aging['FAIXA'] = df_receber_aging['DIAS_VENC'].apply(classificar_aging)

    # Agrupar
    aging_pagar = df_pagar_aging.groupby('FAIXA')['SALDO'].sum().reset_index()
    aging_pagar.columns = ['Faixa', 'Pagar']

    aging_receber = df_receber_aging.groupby('FAIXA')['SALDO'].sum().reset_index()
    aging_receber.columns = ['Faixa', 'Receber']

    aging = pd.merge(aging_pagar, aging_receber, on='Faixa', how='outer').fillna(0)
    aging = aging.sort_values('Faixa')
    aging['Label'] = aging['Faixa'].str[3:]

    # Cores por faixa
    cores_faixas = {
        '+30 dias': cores['sucesso'],
        '0-30 dias': '#a3e635',
        'Venc 1-30d': cores['alerta'],
        'Venc 31-90d': '#f97316',
        'Venc 91-180d': '#ef4444',
        'Venc +180d': '#991b1b',
        'Sem data': cores['texto_secundario']
    }

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"<p style='color: {cores['perigo']}; font-size: 0.9rem; font-weight: 600;'>A Pagar por Faixa</p>", unsafe_allow_html=True)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=aging['Label'],
            y=aging['Pagar'],
            marker_color=[cores_faixas.get(l, cores['info']) for l in aging['Label']],
            text=[formatar_moeda(v) for v in aging['Pagar']],
            textposition='outside',
            textfont=dict(size=9, color=cores['texto'])
        ))

        fig.update_layout(
            height=300,
            margin=dict(l=10, r=10, t=10, b=60),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(tickfont=dict(color=cores['texto'], size=9), tickangle=-30),
            yaxis=dict(showticklabels=False, showgrid=False)
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown(f"<p style='color: {cores['sucesso']}; font-size: 0.9rem; font-weight: 600;'>A Receber por Faixa</p>", unsafe_allow_html=True)

        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            x=aging['Label'],
            y=aging['Receber'],
            marker_color=[cores_faixas.get(l, cores['info']) for l in aging['Label']],
            text=[formatar_moeda(v) for v in aging['Receber']],
            textposition='outside',
            textfont=dict(size=9, color=cores['texto'])
        ))

        fig2.update_layout(
            height=300,
            margin=dict(l=10, r=10, t=10, b=60),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(tickfont=dict(color=cores['texto'], size=9), tickangle=-30),
            yaxis=dict(showticklabels=False, showgrid=False)
        )

        st.plotly_chart(fig2, use_container_width=True)

    # Resumo de criticidade
    st.markdown(f"<p style='color: {cores['texto']}; font-weight: 600; margin-top: 1rem;'>Resumo de Criticidade</p>", unsafe_allow_html=True)

    pagar_critico = df_pagar_aging[df_pagar_aging['DIAS_VENC'] < -90]['SALDO'].sum()
    receber_critico = df_receber_aging[df_receber_aging['DIAS_VENC'] < -90]['SALDO'].sum()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Pagar Critico (+90d)", formatar_moeda(pagar_critico))
    with col2:
        st.metric("Receber Critico (+90d)", formatar_moeda(receber_critico))
    with col3:
        pagar_avencer = df_pagar_aging[df_pagar_aging['DIAS_VENC'] >= 0]['SALDO'].sum()
        st.metric("Pagar A Vencer", formatar_moeda(pagar_avencer))
    with col4:
        receber_avencer = df_receber_aging[df_receber_aging['DIAS_VENC'] >= 0]['SALDO'].sum()
        st.metric("Receber A Vencer", formatar_moeda(receber_avencer))


def _render_detalhes(df_pagar, df_receber, cores):
    """Tabela detalhada com filtros"""

    st.markdown(f"<p style='color: {cores['texto']}; font-weight: 600;'>Detalhes dos Titulos</p>", unsafe_allow_html=True)

    # ========== DIAGNOSTICO INTERCOMPANY ==========
    with st.expander("Diagnostico: Contrapartes Capturadas pelo Filtro", expanded=False):
        col_diag1, col_diag2 = st.columns(2)

        with col_diag1:
            st.markdown(f"**A PAGAR (Fornecedores)**")
            pagar_por_cp = df_pagar.groupby('CONTRAPARTE').agg({
                'SALDO': 'sum',
                'VALOR_ORIGINAL': 'sum'
            }).reset_index()
            pagar_por_cp.columns = ['Contraparte', 'Saldo', 'Valor Original']
            pagar_por_cp = pagar_por_cp.sort_values('Saldo', ascending=False)
            pagar_por_cp['Saldo'] = pagar_por_cp['Saldo'].apply(lambda x: f"R$ {x:,.2f}")
            pagar_por_cp['Valor Original'] = pagar_por_cp['Valor Original'].apply(lambda x: f"R$ {x:,.2f}")
            st.dataframe(pagar_por_cp, use_container_width=True, hide_index=True, height=250)
            st.caption(f"Total A Pagar: R$ {df_pagar['SALDO'].sum():,.2f} | {len(df_pagar)} titulos")

        with col_diag2:
            st.markdown(f"**A RECEBER (Clientes)**")
            receber_por_cp = df_receber.groupby('CONTRAPARTE').agg({
                'SALDO': 'sum',
                'VALOR_ORIGINAL': 'sum'
            }).reset_index()
            receber_por_cp.columns = ['Contraparte', 'Saldo', 'Valor Original']
            receber_por_cp = receber_por_cp.sort_values('Saldo', ascending=False)
            receber_por_cp['Saldo'] = receber_por_cp['Saldo'].apply(lambda x: f"R$ {x:,.2f}")
            receber_por_cp['Valor Original'] = receber_por_cp['Valor Original'].apply(lambda x: f"R$ {x:,.2f}")
            st.dataframe(receber_por_cp, use_container_width=True, hide_index=True, height=250)
            st.caption(f"Total A Receber: R$ {df_receber['SALDO'].sum():,.2f} | {len(df_receber)} titulos")

        # Mostrar padrao de filtro usado
        st.markdown("---")
        st.markdown(f"**Padroes usados no filtro:**")
        st.code(", ".join(INTERCOMPANY_PATTERNS), language=None)

    # Preparar dados combinados - usar apenas colunas que existem
    colunas_base = ['NOME_FILIAL', 'CONTRAPARTE', 'TIPO', 'EMISSAO',
                    'VENCIMENTO', 'VALOR_ORIGINAL', 'SALDO', 'DIAS_VENC', 'STATUS', 'ORIGEM']

    df_pagar_det = df_pagar[[c for c in colunas_base if c in df_pagar.columns]].copy()
    df_receber_det = df_receber[[c for c in colunas_base if c in df_receber.columns]].copy()

    df_todos = pd.concat([df_pagar_det, df_receber_det], ignore_index=True)

    # Filtros
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        origem_opcoes = ['Todos', 'A Pagar', 'A Receber']
        filtro_origem = st.selectbox("Origem", origem_opcoes, key="ic_det_origem")

    with col2:
        contrapartes = ['Todas'] + sorted(df_todos['CONTRAPARTE'].unique().tolist())
        filtro_contraparte = st.selectbox("Contraparte", contrapartes, key="ic_det_cp")

    with col3:
        filiais = ['Todas'] + sorted(df_todos['NOME_FILIAL'].dropna().unique().tolist())
        filtro_filial = st.selectbox("Filial", filiais, key="ic_det_fil")

    with col4:
        status_opcoes = ['Todos', 'Pendente', 'Vencido', 'A Vencer']
        filtro_status = st.selectbox("Status", status_opcoes, key="ic_det_status")

    # Aplicar filtros
    df_show = df_todos.copy()

    if filtro_origem != 'Todos':
        df_show = df_show[df_show['ORIGEM'] == filtro_origem]

    if filtro_contraparte != 'Todas':
        df_show = df_show[df_show['CONTRAPARTE'] == filtro_contraparte]

    if filtro_filial != 'Todas':
        df_show = df_show[df_show['NOME_FILIAL'] == filtro_filial]

    if filtro_status == 'Pendente':
        df_show = df_show[df_show['SALDO'] > 0]
    elif filtro_status == 'Vencido':
        df_show = df_show[(df_show['SALDO'] > 0) & (df_show['DIAS_VENC'] < 0)]
    elif filtro_status == 'A Vencer':
        df_show = df_show[(df_show['SALDO'] > 0) & (df_show['DIAS_VENC'] >= 0)]

    df_show = df_show.sort_values('SALDO', ascending=False)

    # Metricas
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Titulos", formatar_numero(len(df_show)))
    col2.metric("Valor Total", formatar_moeda(df_show['VALOR_ORIGINAL'].sum()))
    col3.metric("Saldo", formatar_moeda(df_show['SALDO'].sum()))
    col4.metric("Vencidos", formatar_numero(len(df_show[(df_show['SALDO'] > 0) & (df_show['DIAS_VENC'] < 0)])))

    st.markdown("---")

    # Tabela
    df_exib = df_show.head(200).copy()
    df_exib['EMISSAO'] = pd.to_datetime(df_exib['EMISSAO']).dt.strftime('%d/%m/%Y')
    df_exib['VENCIMENTO'] = pd.to_datetime(df_exib['VENCIMENTO']).dt.strftime('%d/%m/%Y')
    df_exib['VALOR_ORIGINAL'] = df_exib['VALOR_ORIGINAL'].apply(lambda x: f"R$ {x:,.2f}")
    df_exib['SALDO'] = df_exib['SALDO'].apply(lambda x: f"R$ {x:,.2f}")

    colunas_exibir = ['ORIGEM', 'NOME_FILIAL', 'CONTRAPARTE', 'TIPO',
                        'EMISSAO', 'VENCIMENTO', 'VALOR_ORIGINAL', 'SALDO', 'STATUS']
    colunas_exibir = [c for c in colunas_exibir if c in df_exib.columns]
    df_exib = df_exib[colunas_exibir]

    nomes_colunas = {
        'ORIGEM': 'Origem', 'NOME_FILIAL': 'Filial', 'CONTRAPARTE': 'Contraparte',
        'TIPO': 'Tipo', 'EMISSAO': 'Emissao', 'VENCIMENTO': 'Vencimento',
        'VALOR_ORIGINAL': 'Valor', 'SALDO': 'Saldo', 'STATUS': 'Status'
    }
    df_exib.columns = [nomes_colunas.get(c, c) for c in df_exib.columns]

    st.dataframe(df_exib, use_container_width=True, hide_index=True, height=450)
    st.caption(f"Exibindo {len(df_exib)} de {len(df_show)} registros")
