"""
Aba Adiantamentos - Controle de adiantamentos e compensacoes
Reestruturado para visao analitica
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

from config.theme import get_cores
from config.settings import INTERCOMPANY_PATTERNS
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero


def render_adiantamentos(df_adiant, df_baixas):
    """Renderiza a aba de Adiantamentos"""
    cores = get_cores()
    hoje = datetime.now()

    # ========== PREPARAR DADOS ==========
    df_ad, df_bx = _preparar_dados(df_adiant, df_baixas, hoje)

    # Calcular totais gerais
    total_adiantado = df_ad['VALOR_ORIGINAL'].sum() if len(df_ad) > 0 else 0
    saldo_pendente = df_ad['SALDO'].sum() if len(df_ad) > 0 and 'SALDO' in df_ad.columns else 0
    total_compensado = total_adiantado - saldo_pendente

    # Prazo medio de compensacao
    prazo_medio = 0
    if len(df_bx) > 0 and 'DIF_DIAS_EMIS_BAIXA' in df_bx.columns:
        prazo_medio = pd.to_numeric(df_bx['DIF_DIAS_EMIS_BAIXA'], errors='coerce').mean()

    # ========== KPIs PRINCIPAIS ==========
    # Qtd pendentes
    qtd_pendentes = len(df_ad[df_ad['SALDO'] > 0]) if len(df_ad) > 0 and 'SALDO' in df_ad.columns else 0

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric(
        "Total Adiantado",
        formatar_moeda(total_adiantado),
        f"{len(df_ad)} registros"
    )

    col2.metric(
        "Compensado",
        formatar_moeda(total_compensado),
        f"{(total_compensado/total_adiantado*100):.1f}%" if total_adiantado > 0 else "0%"
    )

    col3.metric(
        "Saldo Pendente",
        formatar_moeda(saldo_pendente),
        f"{qtd_pendentes} titulos"
    )

    col4.metric(
        "Taxa Compensacao",
        f"{(total_compensado/total_adiantado*100):.1f}%" if total_adiantado > 0 else "0%"
    )

    col5.metric(
        "Prazo Medio",
        f"{prazo_medio:.0f} dias",
        "adiantamento → baixa"
    )

    st.divider()

    # ========== TABS ==========
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Visao Geral",
        "Por Tipo",
        "Por Filial",
        "Adto x NF",
        "Por Fornecedor",
        "Aging"
    ])

    with tab1:
        _render_visao_geral(df_ad, df_bx, cores, hoje)

    with tab2:
        _render_por_tipo(df_ad, df_bx, cores)

    with tab3:
        _render_por_filial(df_ad, df_bx, cores)

    with tab4:
        _render_adto_nf(df_ad, df_bx, cores)

    with tab5:
        _render_por_fornecedor(df_ad, df_bx, cores)

    with tab6:
        _render_aging(df_ad, cores, hoje)


def _preparar_dados(df_adiant, df_baixas, hoje):
    """Prepara e limpa os dados"""

    # Copiar dados
    df_ad = df_adiant.copy() if len(df_adiant) > 0 else pd.DataFrame()
    df_bx = df_baixas.copy() if len(df_baixas) > 0 else pd.DataFrame()

    # Remover intercompany
    if len(df_ad) > 0 and 'NOME_FORNECEDOR' in df_ad.columns:
        mask_ic = df_ad['NOME_FORNECEDOR'].str.upper().str.contains(
            '|'.join(INTERCOMPANY_PATTERNS), na=False, regex=True
        )
        df_ad = df_ad[~mask_ic].copy()

    if len(df_bx) > 0 and 'NOME_FORNECEDOR' in df_bx.columns:
        mask_ic = df_bx['NOME_FORNECEDOR'].str.upper().str.contains(
            '|'.join(INTERCOMPANY_PATTERNS), na=False, regex=True
        )
        df_bx = df_bx[~mask_ic].copy()

    # Converter datas
    if len(df_ad) > 0:
        if 'EMISSAO' in df_ad.columns:
            df_ad['EMISSAO'] = pd.to_datetime(df_ad['EMISSAO'], errors='coerce')
        if 'VENCIMENTO' in df_ad.columns:
            df_ad['VENCIMENTO'] = pd.to_datetime(df_ad['VENCIMENTO'], errors='coerce')

        # Calcular dias pendente
        if 'EMISSAO' in df_ad.columns:
            df_ad['DIAS_PENDENTE'] = (hoje - df_ad['EMISSAO']).dt.days

        # Classificar tipo de adiantamento
        if 'DESCRICAO' in df_ad.columns:
            df_ad['TIPO_ADTO'] = df_ad['DESCRICAO'].apply(_classificar_tipo)

    if len(df_bx) > 0:
        if 'EMISSAO' in df_bx.columns:
            df_bx['EMISSAO'] = pd.to_datetime(df_bx['EMISSAO'], errors='coerce')
        if 'DT_BAIXA' in df_bx.columns:
            df_bx['DT_BAIXA'] = pd.to_datetime(df_bx['DT_BAIXA'], errors='coerce')

        # Classificar tipo
        if 'DESCRICAO' in df_bx.columns:
            df_bx['TIPO_ADTO'] = df_bx['DESCRICAO'].apply(_classificar_tipo)

    return df_ad, df_bx


def _classificar_tipo(descricao):
    """Classifica o tipo de adiantamento"""
    if pd.isna(descricao):
        return 'Outros'

    desc = str(descricao).upper()

    if 'ADTO FORNECEDOR' in desc or 'ADIANTAMENTO FORNECEDOR' in desc:
        return 'Fornecedor'
    elif 'VIAGEM' in desc or 'HOSPEDAGEM' in desc:
        return 'Viagem'
    elif 'EXTRAORDIN' in desc:
        return 'Extraordinario'
    elif 'SALARIO' in desc or 'FERIAS' in desc or '13' in desc:
        return 'Folha'
    else:
        return 'Outros'


def _render_visao_geral(df_ad, df_bx, cores, hoje):
    """Visao Geral - Resumo Executivo + Tendencia + Fluxo + Distribuicao"""

    if len(df_ad) == 0:
        st.info("Nenhum adiantamento encontrado.")
        return

    df_pend = df_ad[df_ad['SALDO'] > 0].copy()
    total_adiantado = df_ad['VALOR_ORIGINAL'].sum()
    saldo_pendente = df_ad['SALDO'].sum() if 'SALDO' in df_ad.columns else 0
    total_compensado = total_adiantado - saldo_pendente

    # Prazo medio
    prazo_medio = 0
    if len(df_bx) > 0 and 'DIF_DIAS_EMIS_BAIXA' in df_bx.columns:
        prazo_medio = pd.to_numeric(df_bx['DIF_DIAS_EMIS_BAIXA'], errors='coerce').mean()

    # ========== RESUMO EXECUTIVO ==========
    st.markdown("##### Resumo Executivo")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        pct_comp = (total_compensado / total_adiantado * 100) if total_adiantado > 0 else 0
        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['borda']};
                    border-radius: 12px; padding: 1.2rem; text-align: center;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0 0 0.5rem 0;">
                TAXA DE COMPENSACAO</p>
            <p style="color: {cores['sucesso']}; font-size: 2rem; font-weight: 700; margin: 0;">
                {pct_comp:.1f}%</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0.3rem 0 0 0;">
                {formatar_moeda(total_compensado)} compensado</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['borda']};
                    border-radius: 12px; padding: 1.2rem; text-align: center;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0 0 0.5rem 0;">
                SALDO PENDENTE</p>
            <p style="color: {cores['alerta']}; font-size: 2rem; font-weight: 700; margin: 0;">
                {formatar_moeda(saldo_pendente)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0.3rem 0 0 0;">
                {len(df_pend)} titulos pendentes</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['borda']};
                    border-radius: 12px; padding: 1.2rem; text-align: center;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0 0 0.5rem 0;">
                PRAZO MEDIO</p>
            <p style="color: {cores['primaria']}; font-size: 2rem; font-weight: 700; margin: 0;">
                {prazo_medio:.0f} dias</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0.3rem 0 0 0;">
                entre adiantamento e baixa</p>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        # Variacao do saldo (ultimos 3 meses vs 3 meses anteriores)
        variacao = 0
        variacao_txt = "vs periodo anterior"
        if len(df_ad) > 0 and 'EMISSAO' in df_ad.columns:
            df_3m = df_ad[df_ad['EMISSAO'] >= hoje - timedelta(days=90)]
            df_6m = df_ad[(df_ad['EMISSAO'] >= hoje - timedelta(days=180)) & (df_ad['EMISSAO'] < hoje - timedelta(days=90))]
            saldo_3m = df_3m['SALDO'].sum() if len(df_3m) > 0 else 0
            saldo_6m = df_6m['SALDO'].sum() if len(df_6m) > 0 else 0
            if saldo_6m > 0:
                variacao = ((saldo_3m - saldo_6m) / saldo_6m) * 100
                variacao_txt = "vs trimestre anterior"

        cor_var = cores['sucesso'] if variacao <= 0 else cores['perigo']
        sinal = "+" if variacao > 0 else ""
        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['borda']};
                    border-radius: 12px; padding: 1.2rem; text-align: center;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0 0 0.5rem 0;">
                VARIACAO SALDO</p>
            <p style="color: {cor_var}; font-size: 2rem; font-weight: 700; margin: 0;">
                {sinal}{variacao:.1f}%</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0.3rem 0 0 0;">
                {variacao_txt}</p>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ========== TENDENCIA DO SALDO ==========
    st.markdown("##### Tendencia do Saldo Pendente")

    if len(df_ad) > 0 and 'EMISSAO' in df_ad.columns:
        # Calcular saldo acumulado por mes
        df_ad_mes = df_ad.copy()
        df_ad_mes['MES'] = df_ad_mes['EMISSAO'].dt.to_period('M')

        # Agrupar adiantamentos por mes
        adiant_mes = df_ad_mes.groupby('MES')['VALOR_ORIGINAL'].sum()

        # Agrupar baixas por mes
        if len(df_bx) > 0 and 'DT_BAIXA' in df_bx.columns:
            df_bx_mes = df_bx.copy()
            df_bx_mes['MES'] = df_bx_mes['DT_BAIXA'].dt.to_period('M')
            baixa_mes = df_bx_mes.groupby('MES')['VALOR_BAIXA'].sum() if 'VALOR_BAIXA' in df_bx_mes.columns else pd.Series(dtype=float)
        else:
            baixa_mes = pd.Series(dtype=float)

        # Criar serie temporal
        all_months = sorted(set(adiant_mes.index.tolist() + baixa_mes.index.tolist()))
        if len(all_months) > 12:
            all_months = all_months[-12:]

        saldo_acum = []
        saldo_atual = 0
        for mes in all_months:
            entrada = adiant_mes.get(mes, 0)
            saida = baixa_mes.get(mes, 0)
            saldo_atual = saldo_atual + entrada - saida
            saldo_acum.append({'MES': str(mes), 'Saldo': max(0, saldo_atual), 'Entrada': entrada, 'Saida': saida})

        df_trend = pd.DataFrame(saldo_acum)

        if len(df_trend) > 1:
            fig = go.Figure()

            # Area do saldo
            fig.add_trace(go.Scatter(
                x=df_trend['MES'],
                y=df_trend['Saldo'],
                mode='lines+markers',
                name='Saldo Pendente',
                line=dict(color=cores['alerta'], width=3),
                marker=dict(size=8),
                fill='tozeroy',
                fillcolor=f"rgba(251, 191, 36, 0.2)"
            ))

            # Linha de tendencia
            if len(df_trend) >= 3:
                z = pd.Series(range(len(df_trend)))
                coef = pd.Series(df_trend['Saldo']).corr(z)
                tendencia = "crescente" if coef > 0.3 else ("decrescente" if coef < -0.3 else "estavel")

            fig.update_layout(
                criar_layout(280),
                margin=dict(l=10, r=10, t=10, b=50),
                xaxis=dict(tickangle=-45, tickfont=dict(size=9, color=cores['texto'])),
                yaxis=dict(showticklabels=False, showgrid=True, gridcolor=cores['borda']),
                showlegend=False,
                hovermode='x unified'
            )

            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ========== FLUXO MENSAL ==========
    st.markdown("##### Fluxo Mensal - Entradas vs Saidas")

    col1, col2 = st.columns([2, 1])

    with col1:
        if len(df_ad) > 0 and 'EMISSAO' in df_ad.columns:
            # Adiantamentos por mes
            df_ad_mes = df_ad.copy()
            df_ad_mes['MES'] = df_ad_mes['EMISSAO'].dt.to_period('M').astype(str)
            adiant_mes = df_ad_mes.groupby('MES')['VALOR_ORIGINAL'].sum()

            # Baixas por mes
            if len(df_bx) > 0 and 'DT_BAIXA' in df_bx.columns:
                df_bx_mes = df_bx.copy()
                df_bx_mes['MES'] = df_bx_mes['DT_BAIXA'].dt.to_period('M').astype(str)
                baixa_mes = df_bx_mes.groupby('MES')['VALOR_BAIXA'].sum() if 'VALOR_BAIXA' in df_bx_mes.columns else pd.Series()
            else:
                baixa_mes = pd.Series()

            meses = sorted(set(adiant_mes.index.tolist() + baixa_mes.index.tolist()))[-12:]
            df_fluxo = pd.DataFrame({
                'MES': meses,
                'Adiantado': [adiant_mes.get(m, 0) for m in meses],
                'Compensado': [baixa_mes.get(m, 0) for m in meses]
            })
            df_fluxo['Liquido'] = df_fluxo['Adiantado'] - df_fluxo['Compensado']

            fig = go.Figure()

            fig.add_trace(go.Bar(
                x=df_fluxo['MES'],
                y=df_fluxo['Adiantado'],
                name='Adiantado',
                marker_color=cores['alerta']
            ))

            fig.add_trace(go.Bar(
                x=df_fluxo['MES'],
                y=-df_fluxo['Compensado'],
                name='Compensado',
                marker_color=cores['sucesso']
            ))

            # Linha do liquido
            fig.add_trace(go.Scatter(
                x=df_fluxo['MES'],
                y=df_fluxo['Liquido'],
                name='Liquido',
                mode='lines+markers',
                line=dict(color=cores['texto'], width=2, dash='dot'),
                marker=dict(size=6)
            ))

            fig.update_layout(
                criar_layout(280),
                barmode='relative',
                margin=dict(l=10, r=10, t=10, b=50),
                xaxis=dict(tickangle=-45, tickfont=dict(size=9, color=cores['texto'])),
                yaxis=dict(showticklabels=False, showgrid=False),
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1,
                            font=dict(size=9))
            )

            st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Resumo do fluxo ultimos 3 meses
        st.markdown("###### Ultimos 3 meses")

        if len(df_ad) > 0:
            df_3m = df_ad[df_ad['EMISSAO'] >= hoje - timedelta(days=90)]
            adiant_3m = df_3m['VALOR_ORIGINAL'].sum()

            comp_3m = 0
            if len(df_bx) > 0 and 'DT_BAIXA' in df_bx.columns:
                df_bx_3m = df_bx[df_bx['DT_BAIXA'] >= hoje - timedelta(days=90)]
                comp_3m = df_bx_3m['VALOR_BAIXA'].sum() if 'VALOR_BAIXA' in df_bx_3m.columns else 0

            liquido_3m = adiant_3m - comp_3m

            st.markdown(f"""
            <div style="padding: 0.5rem 0; border-bottom: 1px solid {cores['borda']};">
                <span style="color: {cores['texto_secundario']}; font-size: 0.8rem;">Adiantado</span>
                <span style="color: {cores['alerta']}; font-size: 0.9rem; font-weight: 600; float: right;">
                    +{formatar_moeda(adiant_3m)}</span>
            </div>
            <div style="padding: 0.5rem 0; border-bottom: 1px solid {cores['borda']};">
                <span style="color: {cores['texto_secundario']}; font-size: 0.8rem;">Compensado</span>
                <span style="color: {cores['sucesso']}; font-size: 0.9rem; font-weight: 600; float: right;">
                    -{formatar_moeda(comp_3m)}</span>
            </div>
            <div style="padding: 0.5rem 0;">
                <span style="color: {cores['texto']}; font-size: 0.85rem; font-weight: 600;">Liquido</span>
                <span style="color: {cores['perigo'] if liquido_3m > 0 else cores['sucesso']};
                       font-size: 1rem; font-weight: 700; float: right;">
                    {'+' if liquido_3m > 0 else ''}{formatar_moeda(liquido_3m)}</span>
            </div>
            """, unsafe_allow_html=True)

            if liquido_3m > 0:
                st.caption("⚠️ Saldo pendente aumentando")
            else:
                st.caption("✅ Saldo pendente diminuindo")

    st.divider()

    # ========== DISTRIBUICAO ==========
    st.markdown("##### Distribuicao do Saldo Pendente")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("###### Por Tipo")

        if len(df_pend) > 0 and 'TIPO_ADTO' in df_pend.columns:
            df_tipo = df_pend.groupby('TIPO_ADTO')['SALDO'].sum().reset_index()
            df_tipo.columns = ['Tipo', 'Saldo']
            df_tipo = df_tipo.sort_values('Saldo', ascending=False)

            fig = go.Figure(go.Pie(
                labels=df_tipo['Tipo'],
                values=df_tipo['Saldo'],
                hole=0.5,
                textinfo='percent+label',
                textfont=dict(size=10),
                marker=dict(colors=[cores['primaria'], cores['sucesso'], cores['alerta'], cores['info'], cores['perigo']])
            ))

            fig.add_annotation(
                text=f"<b>{formatar_moeda(df_tipo['Saldo'].sum())}</b>",
                x=0.5, y=0.5,
                font=dict(size=12, color=cores['texto']),
                showarrow=False
            )

            fig.update_layout(
                criar_layout(250),
                showlegend=False,
                margin=dict(l=10, r=10, t=10, b=10)
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados")

    with col2:
        st.markdown("###### Por Filial (Top 5)")

        if len(df_pend) > 0 and 'NOME_FILIAL' in df_pend.columns:
            df_fil = df_pend.groupby('NOME_FILIAL')['SALDO'].sum().nlargest(5).reset_index()
            df_fil.columns = ['Filial', 'Saldo']

            outros = df_pend['SALDO'].sum() - df_fil['Saldo'].sum()
            if outros > 0:
                df_fil = pd.concat([df_fil, pd.DataFrame([{'Filial': 'Outras', 'Saldo': outros}])], ignore_index=True)

            fig = go.Figure(go.Pie(
                labels=df_fil['Filial'].str[:15],
                values=df_fil['Saldo'],
                hole=0.5,
                textinfo='percent',
                textfont=dict(size=10)
            ))

            fig.add_annotation(
                text=f"<b>{len(df_pend['NOME_FILIAL'].unique())}</b><br>filiais",
                x=0.5, y=0.5,
                font=dict(size=11, color=cores['texto']),
                showarrow=False
            )

            fig.update_layout(
                criar_layout(250),
                showlegend=True,
                legend=dict(orientation='v', yanchor='middle', y=0.5, xanchor='left', x=1.02,
                            font=dict(size=8)),
                margin=dict(l=10, r=80, t=10, b=10)
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados")

    st.divider()

    # ========== TOP PENDENCIAS ==========
    st.markdown("##### Top 5 Fornecedores com Maior Saldo Pendente")

    if len(df_pend) > 0:
        df_top_forn = df_pend.groupby('NOME_FORNECEDOR').agg({
            'SALDO': 'sum',
            'VALOR_ORIGINAL': 'sum',
            'NUMERO': 'count'
        }).nlargest(5, 'SALDO').reset_index()
        df_top_forn.columns = ['Fornecedor', 'Pendente', 'Total', 'Qtd']
        df_top_forn['Pct_Comp'] = ((df_top_forn['Total'] - df_top_forn['Pendente']) / df_top_forn['Total'] * 100)

        cols = st.columns(5)
        for i, (_, row) in enumerate(df_top_forn.iterrows()):
            with cols[i]:
                pct = row['Pct_Comp']
                st.markdown(f"""
                <div style="background: {cores['card']}; border: 1px solid {cores['borda']};
                            border-radius: 10px; padding: 0.8rem; height: 100%;">
                    <p style="color: {cores['texto']}; font-size: 0.75rem; font-weight: 600;
                              margin: 0 0 0.5rem 0; white-space: nowrap; overflow: hidden;
                              text-overflow: ellipsis;" title="{row['Fornecedor']}">
                        {row['Fornecedor'][:18]}</p>
                    <p style="color: {cores['alerta']}; font-size: 1.1rem; font-weight: 700; margin: 0;">
                        {formatar_moeda(row['Pendente'])}</p>
                    <p style="color: {cores['texto_secundario']}; font-size: 0.65rem; margin: 0.3rem 0;">
                        {int(row['Qtd'])} titulos</p>
                    <div style="background: {cores['borda']}; border-radius: 4px; height: 6px; margin-top: 0.5rem;">
                        <div style="background: {cores['sucesso']}; width: {pct}%; height: 100%; border-radius: 4px;"></div>
                    </div>
                    <p style="color: {cores['texto_secundario']}; font-size: 0.6rem; margin: 0.2rem 0 0 0;">
                        {pct:.0f}% compensado</p>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.success("Nenhum adiantamento pendente!")


def _render_por_tipo(df_ad, df_bx, cores):
    """Analise por tipo de adiantamento - versao completa"""

    if len(df_ad) == 0 or 'TIPO_ADTO' not in df_ad.columns:
        st.info("Nenhum dado disponivel.")
        return

    hoje = datetime.now()

    # Agrupar por tipo
    df_tipo = df_ad.groupby('TIPO_ADTO').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'NUMERO': 'count',
        'NOME_FORNECEDOR': 'nunique'
    }).reset_index()
    df_tipo.columns = ['Tipo', 'Total', 'Pendente', 'Qtd', 'Fornecedores']
    df_tipo['Compensado'] = df_tipo['Total'] - df_tipo['Pendente']
    df_tipo['Pct_Comp'] = (df_tipo['Compensado'] / df_tipo['Total'] * 100).fillna(0)
    df_tipo['Ticket_Medio'] = (df_tipo['Total'] / df_tipo['Qtd']).fillna(0)
    df_tipo = df_tipo.sort_values('Total', ascending=False)

    # Adicionar prazo medio por tipo
    if len(df_bx) > 0 and 'TIPO_ADTO' in df_bx.columns and 'DIF_DIAS_EMIS_BAIXA' in df_bx.columns:
        prazo_tipo = df_bx.groupby('TIPO_ADTO')['DIF_DIAS_EMIS_BAIXA'].apply(
            lambda x: pd.to_numeric(x, errors='coerce').mean()
        )
        df_tipo['Prazo_Medio'] = df_tipo['Tipo'].map(prazo_tipo).fillna(0)
    else:
        df_tipo['Prazo_Medio'] = 0

    # ========== KPIs ==========
    total_valor = df_tipo['Total'].sum()
    total_pendente = df_tipo['Pendente'].sum()
    qtd_tipos = len(df_tipo)
    maior_tipo = df_tipo.iloc[0]['Tipo'] if len(df_tipo) > 0 else '-'
    maior_tipo_valor = df_tipo.iloc[0]['Total'] if len(df_tipo) > 0 else 0
    tipo_mais_pendente = df_tipo.nlargest(1, 'Pendente').iloc[0]['Tipo'] if len(df_tipo) > 0 else '-'
    ticket_medio_geral = total_valor / df_tipo['Qtd'].sum() if df_tipo['Qtd'].sum() > 0 else 0

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Tipos de Adto", qtd_tipos, f"{df_tipo['Qtd'].sum()} titulos")
    col2.metric("Maior Tipo", maior_tipo, formatar_moeda(maior_tipo_valor))
    col3.metric("Mais Pendente", tipo_mais_pendente, formatar_moeda(df_tipo.nlargest(1, 'Pendente').iloc[0]['Pendente']) if len(df_tipo) > 0 else 'R$ 0')
    col4.metric("Ticket Medio", formatar_moeda(ticket_medio_geral))
    col5.metric("Taxa Compensacao", f"{((total_valor - total_pendente) / total_valor * 100):.1f}%" if total_valor > 0 else "0%")

    st.divider()

    # ========== LINHA 1: Donut + Barras ==========
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("###### Participacao por Tipo")

        cores_tipos = [cores['primaria'], cores['sucesso'], cores['alerta'], cores['info'], cores['perigo'], '#8b5cf6']

        fig = go.Figure(go.Pie(
            labels=df_tipo['Tipo'],
            values=df_tipo['Total'],
            hole=0.5,
            textinfo='percent+label',
            textfont=dict(size=10),
            marker=dict(colors=cores_tipos[:len(df_tipo)])
        ))

        fig.add_annotation(
            text=f"<b>{formatar_moeda(total_valor)}</b>",
            x=0.5, y=0.5,
            font=dict(size=12, color=cores['texto']),
            showarrow=False
        )

        fig.update_layout(
            criar_layout(280),
            showlegend=False,
            margin=dict(l=10, r=10, t=10, b=10)
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("###### Compensado vs Pendente")

        fig = go.Figure()

        fig.add_trace(go.Bar(
            y=df_tipo['Tipo'],
            x=df_tipo['Compensado'],
            orientation='h',
            name='Compensado',
            marker_color=cores['sucesso'],
            text=[formatar_moeda(v) for v in df_tipo['Compensado']],
            textposition='inside',
            textfont=dict(size=9, color='white')
        ))

        fig.add_trace(go.Bar(
            y=df_tipo['Tipo'],
            x=df_tipo['Pendente'],
            orientation='h',
            name='Pendente',
            marker_color=cores['alerta'],
            text=[formatar_moeda(v) for v in df_tipo['Pendente']],
            textposition='inside',
            textfont=dict(size=9, color='white')
        ))

        fig.update_layout(
            criar_layout(280),
            barmode='stack',
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis=dict(showticklabels=False, showgrid=False),
            yaxis=dict(tickfont=dict(size=10, color=cores['texto'])),
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1, font=dict(size=9))
        )

        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ========== EVOLUCAO MENSAL ==========
    st.markdown("###### Evolucao Mensal por Tipo")

    df_evol = df_ad.copy()
    df_evol['MES'] = df_evol['EMISSAO'].dt.to_period('M').astype(str)

    df_pivot = df_evol.pivot_table(
        values='VALOR_ORIGINAL',
        index='MES',
        columns='TIPO_ADTO',
        aggfunc='sum',
        fill_value=0
    ).reset_index()

    df_pivot = df_pivot.tail(12)

    if len(df_pivot) > 1:
        fig = go.Figure()

        cores_linha = [cores['primaria'], cores['sucesso'], cores['alerta'], cores['info'], cores['perigo'], '#8b5cf6']
        tipos = [c for c in df_pivot.columns if c != 'MES']

        for i, tipo in enumerate(tipos):
            fig.add_trace(go.Scatter(
                x=df_pivot['MES'],
                y=df_pivot[tipo],
                name=tipo,
                mode='lines+markers',
                line=dict(color=cores_linha[i % len(cores_linha)], width=2),
                marker=dict(size=6)
            ))

        fig.update_layout(
            criar_layout(280),
            margin=dict(l=10, r=10, t=10, b=50),
            xaxis=dict(tickangle=-45, tickfont=dict(size=9, color=cores['texto'])),
            yaxis=dict(showticklabels=False, showgrid=True, gridcolor=cores['borda']),
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1, font=dict(size=9)),
            hovermode='x unified'
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Historico insuficiente")

    st.divider()

    # ========== LINHA 2: Prazo Medio + Ticket Medio ==========
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("###### Prazo Medio de Compensacao")

        df_prazo = df_tipo[df_tipo['Prazo_Medio'] > 0].sort_values('Prazo_Medio', ascending=True)

        if len(df_prazo) > 0:
            def cor_prazo(p):
                if p <= 30:
                    return cores['sucesso']
                elif p <= 60:
                    return cores['info']
                elif p <= 90:
                    return cores['alerta']
                return cores['perigo']

            bar_colors = [cor_prazo(p) for p in df_prazo['Prazo_Medio']]

            fig = go.Figure()

            fig.add_trace(go.Bar(
                y=df_prazo['Tipo'],
                x=df_prazo['Prazo_Medio'],
                orientation='h',
                marker_color=bar_colors,
                text=[f"{int(p)} dias" for p in df_prazo['Prazo_Medio']],
                textposition='outside',
                textfont=dict(size=10, color=cores['texto'])
            ))

            fig.update_layout(
                criar_layout(250),
                margin=dict(l=10, r=60, t=10, b=10),
                xaxis=dict(showticklabels=False, showgrid=False),
                yaxis=dict(tickfont=dict(size=10, color=cores['texto']))
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados de prazo")

    with col2:
        st.markdown("###### Ticket Medio por Tipo")

        df_ticket = df_tipo.sort_values('Ticket_Medio', ascending=True)

        fig = go.Figure()

        fig.add_trace(go.Bar(
            y=df_ticket['Tipo'],
            x=df_ticket['Ticket_Medio'],
            orientation='h',
            marker_color=cores['info'],
            text=[formatar_moeda(v) for v in df_ticket['Ticket_Medio']],
            textposition='outside',
            textfont=dict(size=10, color=cores['texto'])
        ))

        fig.update_layout(
            criar_layout(250),
            margin=dict(l=10, r=80, t=10, b=10),
            xaxis=dict(showticklabels=False, showgrid=False),
            yaxis=dict(tickfont=dict(size=10, color=cores['texto']))
        )

        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ========== VARIACAO VS PERIODO ANTERIOR ==========
    st.markdown("###### Variacao vs Periodo Anterior (90 dias)")

    df_atual = df_ad[df_ad['EMISSAO'] >= hoje - timedelta(days=90)]
    df_anterior = df_ad[(df_ad['EMISSAO'] >= hoje - timedelta(days=180)) & (df_ad['EMISSAO'] < hoje - timedelta(days=90))]

    if len(df_atual) > 0 and len(df_anterior) > 0:
        atual_grp = df_atual.groupby('TIPO_ADTO')['VALOR_ORIGINAL'].sum()
        anterior_grp = df_anterior.groupby('TIPO_ADTO')['VALOR_ORIGINAL'].sum()

        df_var = pd.DataFrame({
            'Atual': atual_grp,
            'Anterior': anterior_grp
        }).fillna(0)
        df_var['Variacao'] = df_var['Atual'] - df_var['Anterior']
        df_var['Pct'] = ((df_var['Atual'] - df_var['Anterior']) / df_var['Anterior'].replace(0, 1)) * 100
        df_var = df_var.reset_index()
        df_var.columns = ['Tipo', 'Atual', 'Anterior', 'Variacao', 'Pct']
        df_var = df_var.sort_values('Variacao', ascending=True)

        fig = go.Figure()

        bar_colors = [cores['sucesso'] if v < 0 else cores['perigo'] for v in df_var['Variacao']]

        fig.add_trace(go.Bar(
            y=df_var['Tipo'],
            x=df_var['Variacao'],
            orientation='h',
            marker_color=bar_colors,
            text=[f"{'+' if v > 0 else ''}{formatar_moeda(v)} ({p:+.0f}%)" for v, p in zip(df_var['Variacao'], df_var['Pct'])],
            textposition='outside',
            textfont=dict(size=9, color=cores['texto'])
        ))

        fig.add_vline(x=0, line_color=cores['texto'], line_width=1)

        fig.update_layout(
            criar_layout(200),
            margin=dict(l=10, r=120, t=10, b=10),
            xaxis=dict(showticklabels=False, showgrid=False),
            yaxis=dict(tickfont=dict(size=10, color=cores['texto']))
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Dados insuficientes para comparacao")

    st.divider()

    # ========== CONSULTA POR TIPO ==========
    st.markdown("###### Consultar Tipo")

    tipo_sel = st.selectbox("Selecione um tipo", options=[""] + df_tipo['Tipo'].tolist(), key="tipo_consulta")

    if tipo_sel:
        df_sel = df_ad[df_ad['TIPO_ADTO'] == tipo_sel]
        df_pend_sel = df_sel[df_sel['SALDO'] > 0]

        # Metricas do tipo
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Valor Total", formatar_moeda(df_sel['VALOR_ORIGINAL'].sum()), f"{len(df_sel)} titulos")
        col2.metric("Pendente", formatar_moeda(df_sel['SALDO'].sum()), f"{len(df_pend_sel)} titulos")
        col3.metric("Fornecedores", df_sel['NOME_FORNECEDOR'].nunique())
        col4.metric("Filiais", df_sel['NOME_FILIAL'].nunique() if 'NOME_FILIAL' in df_sel.columns else 0)

        # Tabs de detalhes
        tab1, tab2, tab3 = st.tabs(["Por Fornecedor", "Por Filial", "Titulos"])

        with tab1:
            df_forn = df_sel.groupby('NOME_FORNECEDOR').agg({
                'VALOR_ORIGINAL': 'sum',
                'SALDO': 'sum',
                'NUMERO': 'count'
            }).nlargest(10, 'VALOR_ORIGINAL').reset_index()

            if len(df_forn) > 0:
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    y=df_forn['NOME_FORNECEDOR'].str[:25],
                    x=df_forn['VALOR_ORIGINAL'] - df_forn['SALDO'],
                    orientation='h',
                    name='Compensado',
                    marker_color=cores['sucesso']
                ))
                fig.add_trace(go.Bar(
                    y=df_forn['NOME_FORNECEDOR'].str[:25],
                    x=df_forn['SALDO'],
                    orientation='h',
                    name='Pendente',
                    marker_color=cores['alerta']
                ))
                fig.update_layout(
                    criar_layout(250, barmode='stack'),
                    yaxis={'autorange': 'reversed'},
                    margin=dict(l=10, r=10, t=10, b=10),
                    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1, font=dict(size=9))
                )
                st.plotly_chart(fig, use_container_width=True)

        with tab2:
            if 'NOME_FILIAL' in df_sel.columns:
                df_fil = df_sel.groupby('NOME_FILIAL').agg({
                    'VALOR_ORIGINAL': 'sum',
                    'SALDO': 'sum'
                }).reset_index()

                if len(df_fil) > 0:
                    fig = go.Figure(go.Pie(
                        labels=df_fil['NOME_FILIAL'].str[:20],
                        values=df_fil['VALOR_ORIGINAL'],
                        hole=0.4,
                        textinfo='percent',
                        textfont=dict(size=9)
                    ))
                    fig.update_layout(
                        criar_layout(250),
                        showlegend=True,
                        legend=dict(orientation='v', yanchor='middle', y=0.5, xanchor='left', x=1.02, font=dict(size=8)),
                        margin=dict(l=10, r=80, t=10, b=10)
                    )
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sem dados de filial")

        with tab3:
            colunas = ['NOME_FILIAL', 'NOME_FORNECEDOR', 'EMISSAO', 'VALOR_ORIGINAL', 'SALDO']
            colunas_disp = [c for c in colunas if c in df_sel.columns]
            df_tab = df_sel[colunas_disp].nlargest(30, 'VALOR_ORIGINAL').copy()

            if 'EMISSAO' in df_tab.columns:
                df_tab['EMISSAO'] = pd.to_datetime(df_tab['EMISSAO'], errors='coerce').dt.strftime('%d/%m/%Y')

            df_tab['VALOR_ORIGINAL'] = df_tab['VALOR_ORIGINAL'].apply(lambda x: formatar_moeda(x, completo=True))
            df_tab['SALDO'] = df_tab['SALDO'].apply(lambda x: formatar_moeda(x, completo=True))

            nomes = {
                'NOME_FILIAL': 'Filial',
                'NOME_FORNECEDOR': 'Fornecedor',
                'EMISSAO': 'Emissao',
                'VALOR_ORIGINAL': 'Valor',
                'SALDO': 'Saldo'
            }
            df_tab.columns = [nomes.get(c, c) for c in df_tab.columns]

            st.dataframe(df_tab, use_container_width=True, hide_index=True, height=250)

    st.divider()

    # ========== TABELA RESUMO ==========
    st.markdown("###### Tabela Resumo por Tipo")

    df_show = df_tipo.copy()
    df_show['Total'] = df_show['Total'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Compensado'] = df_show['Compensado'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Pendente'] = df_show['Pendente'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Ticket_Medio'] = df_show['Ticket_Medio'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Prazo_Medio'] = df_show['Prazo_Medio'].apply(lambda x: f"{int(x)}d" if x > 0 else '-')
    df_show.columns = ['Tipo', 'Total', 'Pendente', 'Qtd', 'Fornecedores', 'Compensado', '% Comp', 'Ticket Medio', 'Prazo Medio']
    df_show = df_show[['Tipo', 'Total', 'Compensado', 'Pendente', 'Qtd', 'Fornecedores', 'Ticket Medio', '% Comp', 'Prazo Medio']]

    st.dataframe(
        df_show,
        use_container_width=True,
        hide_index=True,
        column_config={
            '% Comp': st.column_config.ProgressColumn(
                '% Comp',
                format='%.0f%%',
                min_value=0,
                max_value=100
            )
        }
    )


def _render_por_filial(df_ad, df_bx, cores):
    """Analise por filial - versao completa"""

    if len(df_ad) == 0 or 'NOME_FILIAL' not in df_ad.columns:
        st.info("Nenhum dado disponivel.")
        return

    hoje = datetime.now()

    # Agrupar por filial
    df_fil = df_ad.groupby('NOME_FILIAL').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'NUMERO': 'count',
        'NOME_FORNECEDOR': 'nunique'
    }).reset_index()
    df_fil.columns = ['Filial', 'Total', 'Pendente', 'Qtd', 'Fornecedores']
    df_fil['Compensado'] = df_fil['Total'] - df_fil['Pendente']
    df_fil['Pct_Comp'] = (df_fil['Compensado'] / df_fil['Total'] * 100).fillna(0)
    df_fil['Ticket_Medio'] = (df_fil['Total'] / df_fil['Qtd']).fillna(0)
    df_fil = df_fil.sort_values('Total', ascending=False)

    # Adicionar prazo medio por filial
    if len(df_bx) > 0 and 'NOME_FILIAL' in df_bx.columns and 'DIF_DIAS_EMIS_BAIXA' in df_bx.columns:
        prazo_fil = df_bx.groupby('NOME_FILIAL')['DIF_DIAS_EMIS_BAIXA'].apply(
            lambda x: pd.to_numeric(x, errors='coerce').mean()
        )
        df_fil['Prazo_Medio'] = df_fil['Filial'].map(prazo_fil).fillna(0)
    else:
        df_fil['Prazo_Medio'] = 0

    # ========== KPIs ==========
    total_valor = df_fil['Total'].sum()
    total_pendente = df_fil['Pendente'].sum()
    qtd_filiais = len(df_fil)
    maior_filial = df_fil.iloc[0]['Filial'] if len(df_fil) > 0 else '-'
    maior_filial_valor = df_fil.iloc[0]['Total'] if len(df_fil) > 0 else 0

    # Melhor e pior taxa
    melhor_taxa_fil = df_fil.nlargest(1, 'Pct_Comp').iloc[0] if len(df_fil) > 0 else None
    pior_taxa_fil = df_fil[df_fil['Total'] > df_fil['Total'].mean() * 0.1].nsmallest(1, 'Pct_Comp').iloc[0] if len(df_fil) > 0 else None

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Filiais", qtd_filiais, f"{df_fil['Qtd'].sum()} titulos")
    col2.metric("Maior Volume", maior_filial[:15], formatar_moeda(maior_filial_valor))
    col3.metric("Mais Pendente", df_fil.nlargest(1, 'Pendente').iloc[0]['Filial'][:15] if len(df_fil) > 0 else '-',
                formatar_moeda(df_fil.nlargest(1, 'Pendente').iloc[0]['Pendente']) if len(df_fil) > 0 else 'R$ 0')
    col4.metric("Melhor Taxa", f"{melhor_taxa_fil['Pct_Comp']:.0f}%" if melhor_taxa_fil is not None else '-',
                melhor_taxa_fil['Filial'][:12] if melhor_taxa_fil is not None else '')
    col5.metric("Pior Taxa", f"{pior_taxa_fil['Pct_Comp']:.0f}%" if pior_taxa_fil is not None else '-',
                pior_taxa_fil['Filial'][:12] if pior_taxa_fil is not None else '')

    st.divider()

    # ========== LINHA 1: Donut + Barras ==========
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("###### Concentracao por Filial")

        # Top 5 + Outras
        df_donut = df_fil.head(5).copy()
        outras = df_fil.iloc[5:]['Total'].sum() if len(df_fil) > 5 else 0
        if outras > 0:
            df_donut = pd.concat([df_donut, pd.DataFrame([{'Filial': 'Outras', 'Total': outras}])], ignore_index=True)

        fig = go.Figure(go.Pie(
            labels=df_donut['Filial'].str[:18],
            values=df_donut['Total'],
            hole=0.5,
            textinfo='percent',
            textfont=dict(size=10)
        ))

        # Calcular concentracao (top 3)
        conc_top3 = df_fil.head(3)['Total'].sum() / total_valor * 100 if total_valor > 0 else 0

        fig.add_annotation(
            text=f"<b>Top 3</b><br>{conc_top3:.0f}%",
            x=0.5, y=0.5,
            font=dict(size=11, color=cores['texto']),
            showarrow=False
        )

        fig.update_layout(
            criar_layout(280),
            showlegend=True,
            legend=dict(orientation='v', yanchor='middle', y=0.5, xanchor='left', x=1.02, font=dict(size=8)),
            margin=dict(l=10, r=80, t=10, b=10)
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("###### Compensado vs Pendente")

        df_top = df_fil.head(10).sort_values('Total', ascending=True)

        fig = go.Figure()

        fig.add_trace(go.Bar(
            y=df_top['Filial'].str[:22],
            x=df_top['Compensado'],
            orientation='h',
            name='Compensado',
            marker_color=cores['sucesso'],
            text=[formatar_moeda(v) for v in df_top['Compensado']],
            textposition='inside',
            textfont=dict(size=8, color='white')
        ))

        fig.add_trace(go.Bar(
            y=df_top['Filial'].str[:22],
            x=df_top['Pendente'],
            orientation='h',
            name='Pendente',
            marker_color=cores['alerta'],
            text=[formatar_moeda(v) for v in df_top['Pendente']],
            textposition='inside',
            textfont=dict(size=8, color='white')
        ))

        fig.update_layout(
            criar_layout(280),
            barmode='stack',
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis=dict(showticklabels=False, showgrid=False),
            yaxis=dict(tickfont=dict(size=9, color=cores['texto'])),
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1, font=dict(size=9))
        )

        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ========== EVOLUCAO MENSAL ==========
    st.markdown("###### Evolucao Mensal - Top 5 Filiais")

    top5_filiais = df_fil.head(5)['Filial'].tolist()

    df_evol = df_ad[df_ad['NOME_FILIAL'].isin(top5_filiais)].copy()
    df_evol['MES'] = df_evol['EMISSAO'].dt.to_period('M').astype(str)

    df_pivot = df_evol.pivot_table(
        values='VALOR_ORIGINAL',
        index='MES',
        columns='NOME_FILIAL',
        aggfunc='sum',
        fill_value=0
    ).reset_index()

    df_pivot = df_pivot.tail(12)

    if len(df_pivot) > 1:
        fig = go.Figure()

        cores_linha = [cores['primaria'], cores['sucesso'], cores['alerta'], cores['info'], cores['perigo']]

        for i, filial in enumerate(top5_filiais):
            if filial in df_pivot.columns:
                fig.add_trace(go.Scatter(
                    x=df_pivot['MES'],
                    y=df_pivot[filial],
                    name=filial[:15],
                    mode='lines+markers',
                    line=dict(color=cores_linha[i % len(cores_linha)], width=2),
                    marker=dict(size=6)
                ))

        fig.update_layout(
            criar_layout(280),
            margin=dict(l=10, r=10, t=10, b=50),
            xaxis=dict(tickangle=-45, tickfont=dict(size=9, color=cores['texto'])),
            yaxis=dict(showticklabels=False, showgrid=True, gridcolor=cores['borda']),
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1, font=dict(size=8)),
            hovermode='x unified'
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Historico insuficiente")

    st.divider()

    # ========== LINHA 2: Taxa + Prazo ==========
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("###### Taxa de Compensacao")

        df_taxa = df_fil.sort_values('Pct_Comp', ascending=True).head(12)

        def cor_taxa(t):
            if t >= 80:
                return cores['sucesso']
            elif t >= 60:
                return cores['info']
            elif t >= 40:
                return cores['alerta']
            return cores['perigo']

        bar_colors = [cor_taxa(t) for t in df_taxa['Pct_Comp']]

        fig = go.Figure()

        fig.add_trace(go.Bar(
            y=df_taxa['Filial'].str[:22],
            x=df_taxa['Pct_Comp'],
            orientation='h',
            marker_color=bar_colors,
            text=[f"{t:.0f}%" for t in df_taxa['Pct_Comp']],
            textposition='outside',
            textfont=dict(size=9, color=cores['texto'])
        ))

        fig.update_layout(
            criar_layout(280),
            margin=dict(l=10, r=50, t=10, b=10),
            xaxis=dict(showticklabels=False, showgrid=False, range=[0, 110]),
            yaxis=dict(tickfont=dict(size=9, color=cores['texto']))
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("###### Prazo Medio de Compensacao")

        df_prazo = df_fil[df_fil['Prazo_Medio'] > 0].sort_values('Prazo_Medio', ascending=False).head(12)

        if len(df_prazo) > 0:
            def cor_prazo(p):
                if p <= 30:
                    return cores['sucesso']
                elif p <= 60:
                    return cores['info']
                elif p <= 90:
                    return cores['alerta']
                return cores['perigo']

            bar_colors = [cor_prazo(p) for p in df_prazo['Prazo_Medio']]

            fig = go.Figure()

            fig.add_trace(go.Bar(
                y=df_prazo['Filial'].str[:22],
                x=df_prazo['Prazo_Medio'],
                orientation='h',
                marker_color=bar_colors,
                text=[f"{int(p)}d" for p in df_prazo['Prazo_Medio']],
                textposition='outside',
                textfont=dict(size=9, color=cores['texto'])
            ))

            fig.update_layout(
                criar_layout(280),
                margin=dict(l=10, r=50, t=10, b=10),
                xaxis=dict(showticklabels=False, showgrid=False),
                yaxis=dict(tickfont=dict(size=9, color=cores['texto']), autorange='reversed')
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados de prazo")

    st.divider()

    # ========== VARIACAO VS PERIODO ANTERIOR ==========
    st.markdown("###### Variacao vs Periodo Anterior (90 dias)")

    df_atual = df_ad[df_ad['EMISSAO'] >= hoje - timedelta(days=90)]
    df_anterior = df_ad[(df_ad['EMISSAO'] >= hoje - timedelta(days=180)) & (df_ad['EMISSAO'] < hoje - timedelta(days=90))]

    if len(df_atual) > 0 and len(df_anterior) > 0:
        atual_grp = df_atual.groupby('NOME_FILIAL')['VALOR_ORIGINAL'].sum()
        anterior_grp = df_anterior.groupby('NOME_FILIAL')['VALOR_ORIGINAL'].sum()

        df_var = pd.DataFrame({
            'Atual': atual_grp,
            'Anterior': anterior_grp
        }).fillna(0)
        df_var['Variacao'] = df_var['Atual'] - df_var['Anterior']
        df_var['Pct'] = ((df_var['Atual'] - df_var['Anterior']) / df_var['Anterior'].replace(0, 1)) * 100
        df_var = df_var.reset_index()
        df_var.columns = ['Filial', 'Atual', 'Anterior', 'Variacao', 'Pct']

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Maior Crescimento**")
            df_cresc = df_var[df_var['Variacao'] > 0].nlargest(5, 'Variacao')

            if len(df_cresc) > 0:
                for _, row in df_cresc.iterrows():
                    st.markdown(f"""
                    <div style="display: flex; justify-content: space-between; padding: 0.3rem 0;
                                border-bottom: 1px solid {cores['borda']};">
                        <span style="color: {cores['texto']}; font-size: 0.85rem;">{row['Filial'][:25]}</span>
                        <span style="color: {cores['perigo']}; font-size: 0.85rem; font-weight: 600;">
                            +{formatar_moeda(row['Variacao'])} ({row['Pct']:+.0f}%)</span>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Nenhuma filial com crescimento")

        with col2:
            st.markdown("**Maior Reducao**")
            df_queda = df_var[df_var['Variacao'] < 0].nsmallest(5, 'Variacao')

            if len(df_queda) > 0:
                for _, row in df_queda.iterrows():
                    st.markdown(f"""
                    <div style="display: flex; justify-content: space-between; padding: 0.3rem 0;
                                border-bottom: 1px solid {cores['borda']};">
                        <span style="color: {cores['texto']}; font-size: 0.85rem;">{row['Filial'][:25]}</span>
                        <span style="color: {cores['sucesso']}; font-size: 0.85rem; font-weight: 600;">
                            {formatar_moeda(row['Variacao'])} ({row['Pct']:.0f}%)</span>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Nenhuma filial com reducao")
    else:
        st.info("Dados insuficientes para comparacao")

    st.divider()

    # ========== MATRIZ FILIAL x TIPO ==========
    st.markdown("###### Matriz Filial x Tipo de Adiantamento")

    if 'TIPO_ADTO' in df_ad.columns:
        # Top 10 filiais
        top10_fil = df_fil.head(10)['Filial'].tolist()

        df_matriz = df_ad[df_ad['NOME_FILIAL'].isin(top10_fil)].copy()

        pivot = df_matriz.pivot_table(
            values='VALOR_ORIGINAL',
            index='NOME_FILIAL',
            columns='TIPO_ADTO',
            aggfunc='sum',
            fill_value=0
        )

        if not pivot.empty and len(pivot.columns) > 1:
            fig = go.Figure(data=go.Heatmap(
                z=pivot.values,
                x=pivot.columns,
                y=[f[:22] for f in pivot.index],
                colorscale=[
                    [0, cores['fundo']],
                    [0.5, cores['info']],
                    [1, cores['primaria']]
                ],
                hovertemplate='Filial: %{y}<br>Tipo: %{x}<br>Valor: R$ %{z:,.0f}<extra></extra>'
            ))

            fig.update_layout(
                criar_layout(350),
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis=dict(tickfont=dict(size=9, color=cores['texto'])),
                yaxis=dict(tickfont=dict(size=9, color=cores['texto']))
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Dados insuficientes para matriz")
    else:
        st.info("Dados de tipo nao disponiveis")

    st.divider()

    # ========== CONSULTA POR FILIAL ==========
    st.markdown("###### Consultar Filial")

    filial_sel = st.selectbox("Selecione uma filial", options=[""] + df_fil['Filial'].tolist(), key="filial_consulta")

    if filial_sel:
        df_sel = df_ad[df_ad['NOME_FILIAL'] == filial_sel]
        df_pend_sel = df_sel[df_sel['SALDO'] > 0]

        # Metricas da filial
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Valor Total", formatar_moeda(df_sel['VALOR_ORIGINAL'].sum()), f"{len(df_sel)} titulos")
        col2.metric("Pendente", formatar_moeda(df_sel['SALDO'].sum()), f"{len(df_pend_sel)} titulos")
        col3.metric("Taxa Comp.", f"{((df_sel['VALOR_ORIGINAL'].sum() - df_sel['SALDO'].sum()) / df_sel['VALOR_ORIGINAL'].sum() * 100):.0f}%" if df_sel['VALOR_ORIGINAL'].sum() > 0 else "0%")
        col4.metric("Fornecedores", df_sel['NOME_FORNECEDOR'].nunique())

        # Prazo medio da filial
        prazo_fil = 0
        if len(df_bx) > 0 and 'NOME_FILIAL' in df_bx.columns:
            df_bx_fil = df_bx[df_bx['NOME_FILIAL'] == filial_sel]
            if len(df_bx_fil) > 0 and 'DIF_DIAS_EMIS_BAIXA' in df_bx_fil.columns:
                prazo_fil = pd.to_numeric(df_bx_fil['DIF_DIAS_EMIS_BAIXA'], errors='coerce').mean()
        col5.metric("Prazo Medio", f"{prazo_fil:.0f}d" if prazo_fil > 0 else "-")

        # Tabs de detalhes
        tab1, tab2, tab3 = st.tabs(["Por Fornecedor", "Por Tipo", "Titulos"])

        with tab1:
            df_forn = df_sel.groupby('NOME_FORNECEDOR').agg({
                'VALOR_ORIGINAL': 'sum',
                'SALDO': 'sum',
                'NUMERO': 'count'
            }).nlargest(10, 'VALOR_ORIGINAL').reset_index()

            if len(df_forn) > 0:
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    y=df_forn['NOME_FORNECEDOR'].str[:25],
                    x=df_forn['VALOR_ORIGINAL'] - df_forn['SALDO'],
                    orientation='h',
                    name='Compensado',
                    marker_color=cores['sucesso']
                ))
                fig.add_trace(go.Bar(
                    y=df_forn['NOME_FORNECEDOR'].str[:25],
                    x=df_forn['SALDO'],
                    orientation='h',
                    name='Pendente',
                    marker_color=cores['alerta']
                ))
                fig.update_layout(
                    criar_layout(250, barmode='stack'),
                    yaxis={'autorange': 'reversed'},
                    margin=dict(l=10, r=10, t=10, b=10),
                    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1, font=dict(size=9))
                )
                st.plotly_chart(fig, use_container_width=True)

        with tab2:
            if 'TIPO_ADTO' in df_sel.columns:
                df_tipo = df_sel.groupby('TIPO_ADTO').agg({
                    'VALOR_ORIGINAL': 'sum',
                    'SALDO': 'sum'
                }).reset_index()

                if len(df_tipo) > 0:
                    fig = go.Figure(go.Pie(
                        labels=df_tipo['TIPO_ADTO'],
                        values=df_tipo['VALOR_ORIGINAL'],
                        hole=0.4,
                        textinfo='percent+label',
                        textfont=dict(size=10)
                    ))
                    fig.update_layout(
                        criar_layout(250),
                        showlegend=False,
                        margin=dict(l=10, r=10, t=10, b=10)
                    )
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sem dados de tipo")

        with tab3:
            colunas = ['NOME_FORNECEDOR', 'TIPO_ADTO', 'EMISSAO', 'VALOR_ORIGINAL', 'SALDO']
            colunas_disp = [c for c in colunas if c in df_sel.columns]
            df_tab = df_sel[colunas_disp].nlargest(30, 'VALOR_ORIGINAL').copy()

            if 'EMISSAO' in df_tab.columns:
                df_tab['EMISSAO'] = pd.to_datetime(df_tab['EMISSAO'], errors='coerce').dt.strftime('%d/%m/%Y')

            df_tab['VALOR_ORIGINAL'] = df_tab['VALOR_ORIGINAL'].apply(lambda x: formatar_moeda(x, completo=True))
            df_tab['SALDO'] = df_tab['SALDO'].apply(lambda x: formatar_moeda(x, completo=True))

            nomes = {
                'NOME_FORNECEDOR': 'Fornecedor',
                'TIPO_ADTO': 'Tipo',
                'EMISSAO': 'Emissao',
                'VALOR_ORIGINAL': 'Valor',
                'SALDO': 'Saldo'
            }
            df_tab.columns = [nomes.get(c, c) for c in df_tab.columns]

            st.dataframe(df_tab, use_container_width=True, hide_index=True, height=250)

    st.divider()

    # ========== TABELA COMPLETA ==========
    st.markdown("###### Tabela Completa")

    col1, col2 = st.columns(2)
    with col1:
        ordenar = st.selectbox("Ordenar por", ["Maior Total", "Maior Pendente", "Menor Taxa", "Maior Prazo"], key="fil_ordem")
    with col2:
        filtro = st.selectbox("Filtrar", ["Todas", "Com Pendencia", "Taxa < 50%"], key="fil_filtro")

    df_exibir = df_fil.copy()

    if filtro == "Com Pendencia":
        df_exibir = df_exibir[df_exibir['Pendente'] > 0]
    elif filtro == "Taxa < 50%":
        df_exibir = df_exibir[df_exibir['Pct_Comp'] < 50]

    if ordenar == "Maior Total":
        df_exibir = df_exibir.sort_values('Total', ascending=False)
    elif ordenar == "Maior Pendente":
        df_exibir = df_exibir.sort_values('Pendente', ascending=False)
    elif ordenar == "Menor Taxa":
        df_exibir = df_exibir.sort_values('Pct_Comp', ascending=True)
    else:
        df_exibir = df_exibir.sort_values('Prazo_Medio', ascending=False)

    df_show = df_exibir.copy()
    df_show['Total'] = df_show['Total'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Compensado'] = df_show['Compensado'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Pendente'] = df_show['Pendente'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Ticket_Medio'] = df_show['Ticket_Medio'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Prazo_Medio'] = df_show['Prazo_Medio'].apply(lambda x: f"{int(x)}d" if x > 0 else '-')
    df_show.columns = ['Filial', 'Total', 'Pendente', 'Qtd', 'Fornecedores', 'Compensado', '% Comp', 'Ticket Medio', 'Prazo Medio']
    df_show = df_show[['Filial', 'Total', 'Compensado', 'Pendente', 'Qtd', 'Fornecedores', 'Ticket Medio', '% Comp', 'Prazo Medio']]

    st.dataframe(
        df_show,
        use_container_width=True,
        hide_index=True,
        height=350,
        column_config={
            '% Comp': st.column_config.ProgressColumn(
                '% Comp',
                format='%.0f%%',
                min_value=0,
                max_value=100
            )
        }
    )
    st.caption(f"Exibindo {len(df_show)} filiais")


def _render_adto_nf(df_ad, df_bx, cores):
    """Prazos entre adiantamento e baixa"""

    st.markdown("##### Adiantamento x NF - Prazos de Compensacao")

    if len(df_bx) == 0:
        st.info("Nenhuma compensacao registrada.")
        return

    # Metricas
    total_compensado = df_bx['VALOR_BAIXA'].sum() if 'VALOR_BAIXA' in df_bx.columns else 0

    prazo_medio = 0
    prazo_mediano = 0
    if 'DIF_DIAS_EMIS_BAIXA' in df_bx.columns:
        prazo_num = pd.to_numeric(df_bx['DIF_DIAS_EMIS_BAIXA'], errors='coerce')
        prazo_medio = prazo_num.mean()
        prazo_mediano = prazo_num.median()

    # Compensacoes longas (> 90 dias)
    qtd_longo = 0
    valor_longo = 0
    if 'DIF_DIAS_EMIS_BAIXA' in df_bx.columns:
        prazo = pd.to_numeric(df_bx['DIF_DIAS_EMIS_BAIXA'], errors='coerce')
        mask_longo = prazo > 90
        qtd_longo = mask_longo.sum()
        if 'VALOR_BAIXA' in df_bx.columns:
            valor_longo = df_bx.loc[mask_longo, 'VALOR_BAIXA'].sum()

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Compensacoes", len(df_bx))
    col2.metric("Valor Total", formatar_moeda(total_compensado))
    col3.metric("Prazo Medio", f"{prazo_medio:.0f} dias")
    col4.metric("Prazo Mediano", f"{prazo_mediano:.0f} dias")
    col5.metric("Prazo > 90d", f"{qtd_longo}", f"{formatar_moeda(valor_longo)}")

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        # Distribuicao por prazo
        st.markdown("###### Distribuicao por Faixa de Prazo")

        if 'DIF_DIAS_EMIS_BAIXA' in df_bx.columns:
            def faixa_prazo(d):
                if pd.isna(d) or d < 0:
                    return 'N/A'
                d = int(d)
                if d <= 15:
                    return 'Ate 15d'
                elif d <= 30:
                    return '16-30d'
                elif d <= 60:
                    return '31-60d'
                elif d <= 90:
                    return '61-90d'
                elif d <= 180:
                    return '91-180d'
                return '180+d'

            df_bx_temp = df_bx.copy()
            df_bx_temp['PRAZO'] = pd.to_numeric(df_bx_temp['DIF_DIAS_EMIS_BAIXA'], errors='coerce')
            df_bx_temp['FAIXA'] = df_bx_temp['PRAZO'].apply(faixa_prazo)

            ordem = ['Ate 15d', '16-30d', '31-60d', '61-90d', '91-180d', '180+d']
            df_faixa = df_bx_temp.groupby('FAIXA').agg({
                'VALOR_BAIXA': 'sum',
                'PRAZO': 'count'
            }).reindex(ordem, fill_value=0).reset_index()
            df_faixa.columns = ['Faixa', 'Valor', 'Qtd']

            cores_faixas = [cores['sucesso'], cores['info'], '#22d3ee', cores['alerta'], '#f97316', cores['perigo']]

            fig = go.Figure()

            fig.add_trace(go.Bar(
                x=df_faixa['Faixa'],
                y=df_faixa['Valor'],
                marker_color=cores_faixas,
                text=[f"{formatar_moeda(v)}<br>({int(q)})" for v, q in zip(df_faixa['Valor'], df_faixa['Qtd'])],
                textposition='outside',
                textfont=dict(size=9, color=cores['texto'])
            ))

            fig.update_layout(
                criar_layout(280),
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis=dict(tickfont=dict(size=10, color=cores['texto'])),
                yaxis=dict(showticklabels=False, showgrid=False)
            )

            st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Evolucao mensal do prazo
        st.markdown("###### Evolucao do Prazo Medio")

        if 'DT_BAIXA' in df_bx.columns and 'DIF_DIAS_EMIS_BAIXA' in df_bx.columns:
            df_evol = df_bx.copy()
            df_evol['MES'] = df_evol['DT_BAIXA'].dt.to_period('M').astype(str)
            df_evol['PRAZO'] = pd.to_numeric(df_evol['DIF_DIAS_EMIS_BAIXA'], errors='coerce')

            df_prazo_mes = df_evol.groupby('MES')['PRAZO'].mean().tail(12).reset_index()
            df_prazo_mes.columns = ['MES', 'Prazo']

            fig = go.Figure()

            fig.add_trace(go.Scatter(
                x=df_prazo_mes['MES'],
                y=df_prazo_mes['Prazo'],
                mode='lines+markers',
                line=dict(color=cores['primaria'], width=2),
                marker=dict(size=8),
                text=[f"{int(p)}d" for p in df_prazo_mes['Prazo']],
                textposition='top center',
                textfont=dict(size=9, color=cores['texto'])
            ))

            # Linha de referencia 60 dias
            fig.add_hline(y=60, line_dash="dash", line_color=cores['alerta'], line_width=1)

            fig.update_layout(
                criar_layout(280),
                margin=dict(l=10, r=10, t=30, b=50),
                xaxis=dict(tickangle=-45, tickfont=dict(size=9, color=cores['texto'])),
                yaxis=dict(title='Dias', tickfont=dict(size=9, color=cores['texto']))
            )

            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Tabela de compensacoes
    st.markdown("###### Detalhamento das Compensacoes")

    col1, col2, col3 = st.columns(3)

    with col1:
        if 'NOME_FORNECEDOR' in df_bx.columns:
            fornecedores = ['Todos'] + sorted(df_bx['NOME_FORNECEDOR'].dropna().unique().tolist())
            filtro_forn = st.selectbox("Fornecedor", fornecedores, key="adto_nf_forn")
        else:
            filtro_forn = 'Todos'

    with col2:
        filtro_prazo = st.selectbox("Prazo", ["Todos", "Ate 30d", "31-90d", "90+d"], key="adto_nf_prazo")

    with col3:
        ordenar = st.selectbox("Ordenar", ["Mais recente", "Maior valor", "Maior prazo"], key="adto_nf_ordem")

    # Aplicar filtros
    df_show = df_bx.copy()

    if filtro_forn != 'Todos' and 'NOME_FORNECEDOR' in df_show.columns:
        df_show = df_show[df_show['NOME_FORNECEDOR'] == filtro_forn]

    if 'DIF_DIAS_EMIS_BAIXA' in df_show.columns:
        df_show['PRAZO_NUM'] = pd.to_numeric(df_show['DIF_DIAS_EMIS_BAIXA'], errors='coerce')

        if filtro_prazo == "Ate 30d":
            df_show = df_show[df_show['PRAZO_NUM'] <= 30]
        elif filtro_prazo == "31-90d":
            df_show = df_show[(df_show['PRAZO_NUM'] > 30) & (df_show['PRAZO_NUM'] <= 90)]
        elif filtro_prazo == "90+d":
            df_show = df_show[df_show['PRAZO_NUM'] > 90]

    # Ordenar
    if ordenar == "Mais recente" and 'DT_BAIXA' in df_show.columns:
        df_show = df_show.sort_values('DT_BAIXA', ascending=False)
    elif ordenar == "Maior valor" and 'VALOR_BAIXA' in df_show.columns:
        df_show = df_show.sort_values('VALOR_BAIXA', ascending=False)
    elif ordenar == "Maior prazo" and 'PRAZO_NUM' in df_show.columns:
        df_show = df_show.sort_values('PRAZO_NUM', ascending=False)

    df_show = df_show.head(100)

    # Preparar tabela
    colunas = ['NOME_FILIAL', 'NOME_FORNECEDOR', 'EMISSAO', 'DT_BAIXA', 'DIF_DIAS_EMIS_BAIXA', 'VALOR_BAIXA']
    colunas_disp = [c for c in colunas if c in df_show.columns]
    df_tab = df_show[colunas_disp].copy()

    for col in ['EMISSAO', 'DT_BAIXA']:
        if col in df_tab.columns:
            df_tab[col] = pd.to_datetime(df_tab[col], errors='coerce').dt.strftime('%d/%m/%Y')

    if 'VALOR_BAIXA' in df_tab.columns:
        df_tab['VALOR_BAIXA'] = df_tab['VALOR_BAIXA'].apply(lambda x: formatar_moeda(x, completo=True))

    if 'DIF_DIAS_EMIS_BAIXA' in df_tab.columns:
        df_tab['DIF_DIAS_EMIS_BAIXA'] = pd.to_numeric(df_tab['DIF_DIAS_EMIS_BAIXA'], errors='coerce').apply(
            lambda x: f"{int(x)}d" if pd.notna(x) else '-'
        )

    nomes = {
        'NOME_FILIAL': 'Filial',
        'NOME_FORNECEDOR': 'Fornecedor',
        'EMISSAO': 'Dt Adiantamento',
        'DT_BAIXA': 'Dt Compensacao',
        'DIF_DIAS_EMIS_BAIXA': 'Prazo',
        'VALOR_BAIXA': 'Valor'
    }
    df_tab.columns = [nomes.get(c, c) for c in df_tab.columns]

    st.dataframe(df_tab, use_container_width=True, hide_index=True, height=350)
    st.caption(f"Exibindo {len(df_tab)} compensacoes")


def _render_por_fornecedor(df_ad, df_bx, cores):
    """Analise completa por fornecedor"""

    st.markdown("##### Analise por Fornecedor")

    if len(df_ad) == 0 or 'NOME_FORNECEDOR' not in df_ad.columns:
        st.info("Nenhum dado disponivel.")
        return

    # Preparar dados base
    df_forn = df_ad.groupby('NOME_FORNECEDOR').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'NUMERO': 'count'
    }).reset_index()
    df_forn.columns = ['Fornecedor', 'Total', 'Saldo', 'Qtd']
    df_forn['Compensado'] = df_forn['Total'] - df_forn['Saldo']
    df_forn['Pct'] = (df_forn['Compensado'] / df_forn['Total'] * 100).fillna(0).round(1)
    df_forn['Ticket_Medio'] = (df_forn['Total'] / df_forn['Qtd']).fillna(0)
    df_forn = df_forn.sort_values('Saldo', ascending=False)

    # Adicionar prazo medio das baixas
    if len(df_bx) > 0 and 'NOME_FORNECEDOR' in df_bx.columns and 'DIF_DIAS_EMIS_BAIXA' in df_bx.columns:
        prazo_forn = df_bx.groupby('NOME_FORNECEDOR')['DIF_DIAS_EMIS_BAIXA'].apply(
            lambda x: pd.to_numeric(x, errors='coerce').mean()
        )
        df_forn['Prazo_Medio'] = df_forn['Fornecedor'].map(prazo_forn).fillna(0)
    else:
        df_forn['Prazo_Medio'] = 0

    # ==========================================================================
    # SECAO 1: KPIs (5 metricas)
    # ==========================================================================
    total_fornecedores = len(df_forn)
    valor_total = df_forn['Total'].sum()
    valor_pendente = df_forn['Saldo'].sum()
    forn_pendentes = len(df_forn[df_forn['Saldo'] > 0])
    ticket_medio_geral = valor_total / df_forn['Qtd'].sum() if df_forn['Qtd'].sum() > 0 else 0

    # Top 3 concentracao
    df_top3 = df_forn.head(3)
    conc_top3 = (df_top3['Saldo'].sum() / valor_pendente * 100) if valor_pendente > 0 else 0

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.markdown(f"""
    <div style="background: {cores['card']}; border: 1px solid {cores['borda']}; border-radius: 8px; padding: 0.8rem; text-align: center;">
        <div style="color: {cores['texto_secundario']}; font-size: 0.7rem;">FORNECEDORES</div>
        <div style="color: {cores['texto']}; font-size: 1.4rem; font-weight: 700;">{total_fornecedores}</div>
        <div style="color: {cores['info']}; font-size: 0.7rem;">{forn_pendentes} com pendencia</div>
    </div>
    """, unsafe_allow_html=True)

    col2.markdown(f"""
    <div style="background: {cores['card']}; border: 1px solid {cores['borda']}; border-radius: 8px; padding: 0.8rem; text-align: center;">
        <div style="color: {cores['texto_secundario']}; font-size: 0.7rem;">VALOR TOTAL</div>
        <div style="color: {cores['texto']}; font-size: 1.4rem; font-weight: 700;">{formatar_moeda(valor_total)}</div>
        <div style="color: {cores['texto_secundario']}; font-size: 0.7rem;">{df_forn['Qtd'].sum()} adiantamentos</div>
    </div>
    """, unsafe_allow_html=True)

    col3.markdown(f"""
    <div style="background: {cores['card']}; border: 1px solid {cores['borda']}; border-radius: 8px; padding: 0.8rem; text-align: center;">
        <div style="color: {cores['texto_secundario']}; font-size: 0.7rem;">SALDO PENDENTE</div>
        <div style="color: {cores['alerta']}; font-size: 1.4rem; font-weight: 700;">{formatar_moeda(valor_pendente)}</div>
        <div style="color: {cores['texto_secundario']}; font-size: 0.7rem;">{(valor_pendente/valor_total*100):.1f}% do total</div>
    </div>
    """, unsafe_allow_html=True)

    col4.markdown(f"""
    <div style="background: {cores['card']}; border: 1px solid {cores['borda']}; border-radius: 8px; padding: 0.8rem; text-align: center;">
        <div style="color: {cores['texto_secundario']}; font-size: 0.7rem;">TICKET MEDIO</div>
        <div style="color: {cores['texto']}; font-size: 1.4rem; font-weight: 700;">{formatar_moeda(ticket_medio_geral)}</div>
        <div style="color: {cores['texto_secundario']}; font-size: 0.7rem;">por adiantamento</div>
    </div>
    """, unsafe_allow_html=True)

    col5.markdown(f"""
    <div style="background: {cores['card']}; border: 1px solid {cores['borda']}; border-radius: 8px; padding: 0.8rem; text-align: center;">
        <div style="color: {cores['texto_secundario']}; font-size: 0.7rem;">CONC. TOP 3</div>
        <div style="color: {'#f97316' if conc_top3 > 50 else cores['texto']}; font-size: 1.4rem; font-weight: 700;">{conc_top3:.1f}%</div>
        <div style="color: {cores['texto_secundario']}; font-size: 0.7rem;">do saldo pendente</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ==========================================================================
    # SECAO 2: Donut Concentracao + Top 15 Barras
    # ==========================================================================
    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("###### Concentracao por Fornecedor")

        # Preparar dados para donut (Top 5 + Outros)
        df_donut = df_forn[df_forn['Saldo'] > 0].copy()
        if len(df_donut) > 5:
            df_top5 = df_donut.head(5)
            outros_valor = df_donut.iloc[5:]['Saldo'].sum()
            df_chart = pd.concat([
                df_top5[['Fornecedor', 'Saldo']],
                pd.DataFrame({'Fornecedor': ['Outros'], 'Saldo': [outros_valor]})
            ])
        else:
            df_chart = df_donut[['Fornecedor', 'Saldo']]

        cores_donut = [cores['info'], cores['sucesso'], cores['alerta'], '#8b5cf6', '#f97316', cores['texto_secundario']]

        fig = go.Figure(data=[go.Pie(
            labels=df_chart['Fornecedor'].str[:20],
            values=df_chart['Saldo'],
            hole=0.6,
            marker=dict(colors=cores_donut[:len(df_chart)]),
            textinfo='percent',
            textposition='outside',
            textfont=dict(size=9, color=cores['texto']),
            hovertemplate='<b>%{label}</b><br>Pendente: R$ %{value:,.0f}<br>%{percent}<extra></extra>'
        )])

        fig.update_layout(
            criar_layout(280),
            margin=dict(l=10, r=10, t=10, b=10),
            showlegend=True,
            legend=dict(
                orientation='h', yanchor='bottom', y=-0.3, xanchor='center', x=0.5,
                font=dict(size=8, color=cores['texto'])
            ),
            annotations=[dict(
                text=f"<b>{formatar_moeda(valor_pendente)}</b><br>Pendente",
                x=0.5, y=0.5, font=dict(size=10, color=cores['texto']),
                showarrow=False
            )]
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("###### Top 15 - Compensado vs Pendente")

        df_top15 = df_forn.head(15).sort_values('Saldo', ascending=True)

        fig = go.Figure()

        fig.add_trace(go.Bar(
            y=df_top15['Fornecedor'].str[:30],
            x=df_top15['Compensado'],
            orientation='h',
            name='Compensado',
            marker_color=cores['sucesso'],
            text=[formatar_moeda(v) for v in df_top15['Compensado']],
            textposition='inside',
            textfont=dict(size=8, color='white')
        ))

        fig.add_trace(go.Bar(
            y=df_top15['Fornecedor'].str[:30],
            x=df_top15['Saldo'],
            orientation='h',
            name='Pendente',
            marker_color=cores['alerta'],
            text=[formatar_moeda(v) for v in df_top15['Saldo']],
            textposition='inside',
            textfont=dict(size=8, color='white')
        ))

        fig.update_layout(
            criar_layout(380),
            barmode='stack',
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis=dict(showticklabels=False, showgrid=False),
            yaxis=dict(tickfont=dict(size=9, color=cores['texto'])),
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
        )

        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ==========================================================================
    # SECAO 3: Evolucao Mensal Top 5 Fornecedores
    # ==========================================================================
    st.markdown("###### Evolucao Mensal - Top 5 Fornecedores")

    # Top 5 por saldo
    top5_forn = df_forn.head(5)['Fornecedor'].tolist()

    if 'EMISSAO' in df_ad.columns:
        df_evol = df_ad[df_ad['NOME_FORNECEDOR'].isin(top5_forn)].copy()
        df_evol['MES'] = df_evol['EMISSAO'].dt.to_period('M').astype(str)

        df_evol_agg = df_evol.groupby(['MES', 'NOME_FORNECEDOR'])['VALOR_ORIGINAL'].sum().reset_index()
        df_evol_agg.columns = ['Mes', 'Fornecedor', 'Valor']

        cores_linha = [cores['info'], cores['sucesso'], cores['alerta'], '#8b5cf6', '#f97316']

        fig = go.Figure()

        for i, forn in enumerate(top5_forn):
            df_f = df_evol_agg[df_evol_agg['Fornecedor'] == forn].sort_values('Mes')
            if len(df_f) > 0:
                fig.add_trace(go.Scatter(
                    x=df_f['Mes'],
                    y=df_f['Valor'],
                    mode='lines+markers',
                    name=forn[:25],
                    line=dict(color=cores_linha[i % len(cores_linha)], width=2),
                    marker=dict(size=6),
                    hovertemplate=f'<b>{forn[:25]}</b><br>%{{x}}<br>R$ %{{y:,.0f}}<extra></extra>'
                ))

        fig.update_layout(
            criar_layout(280),
            margin=dict(l=10, r=10, t=30, b=10),
            xaxis=dict(tickfont=dict(size=9, color=cores['texto']), tickangle=-45),
            yaxis=dict(tickfont=dict(size=9, color=cores['texto']), tickformat=',.0f'),
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1, font=dict(size=8))
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Dados de evolucao nao disponiveis.")

    st.divider()

    # ==========================================================================
    # SECAO 4: Prazo Medio + Ticket Medio por Fornecedor (Top 10)
    # ==========================================================================
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("###### Prazo Medio de Compensacao (Top 10)")

        df_prazo = df_forn[df_forn['Prazo_Medio'] > 0].sort_values('Prazo_Medio', ascending=False).head(10)

        if len(df_prazo) > 0:
            fig = go.Figure()

            prazo_medio_geral = df_forn[df_forn['Prazo_Medio'] > 0]['Prazo_Medio'].mean()

            fig.add_trace(go.Bar(
                x=df_prazo['Prazo_Medio'],
                y=df_prazo['Fornecedor'].str[:25],
                orientation='h',
                marker_color=[cores['perigo'] if p > prazo_medio_geral * 1.5 else cores['alerta'] if p > prazo_medio_geral else cores['sucesso'] for p in df_prazo['Prazo_Medio']],
                text=[f"{int(p)}d" for p in df_prazo['Prazo_Medio']],
                textposition='outside',
                textfont=dict(size=9, color=cores['texto'])
            ))

            # Linha media
            fig.add_vline(x=prazo_medio_geral, line_dash="dash", line_color=cores['info'], annotation_text=f"Media: {prazo_medio_geral:.0f}d")

            fig.update_layout(
                criar_layout(300),
                margin=dict(l=10, r=60, t=10, b=10),
                xaxis=dict(showticklabels=False, showgrid=False),
                yaxis=dict(tickfont=dict(size=9, color=cores['texto']))
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhum dado de prazo disponivel.")

    with col2:
        st.markdown("###### Ticket Medio por Fornecedor (Top 10)")

        df_ticket = df_forn.sort_values('Ticket_Medio', ascending=False).head(10)

        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=df_ticket['Ticket_Medio'],
            y=df_ticket['Fornecedor'].str[:25],
            orientation='h',
            marker_color=cores['info'],
            text=[formatar_moeda(v) for v in df_ticket['Ticket_Medio']],
            textposition='outside',
            textfont=dict(size=9, color=cores['texto'])
        ))

        # Linha media geral
        fig.add_vline(x=ticket_medio_geral, line_dash="dash", line_color=cores['alerta'], annotation_text=f"Media: {formatar_moeda(ticket_medio_geral)}")

        fig.update_layout(
            criar_layout(300),
            margin=dict(l=10, r=80, t=10, b=10),
            xaxis=dict(showticklabels=False, showgrid=False),
            yaxis=dict(tickfont=dict(size=9, color=cores['texto']))
        )

        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ==========================================================================
    # SECAO 5: Variacao vs Periodo Anterior (90 dias)
    # ==========================================================================
    st.markdown("###### Variacao vs Periodo Anterior (90 dias)")

    if 'EMISSAO' in df_ad.columns:
        hoje = pd.Timestamp.now()
        df_atual = df_ad[df_ad['EMISSAO'] >= (hoje - pd.Timedelta(days=90))]
        df_anterior = df_ad[(df_ad['EMISSAO'] >= (hoje - pd.Timedelta(days=180))) & (df_ad['EMISSAO'] < (hoje - pd.Timedelta(days=90)))]

        forn_atual = df_atual.groupby('NOME_FORNECEDOR')['VALOR_ORIGINAL'].sum()
        forn_anterior = df_anterior.groupby('NOME_FORNECEDOR')['VALOR_ORIGINAL'].sum()

        # Calcular variacao
        todos_forn = set(forn_atual.index) | set(forn_anterior.index)
        variacoes = []
        for f in todos_forn:
            val_atual = forn_atual.get(f, 0)
            val_anterior = forn_anterior.get(f, 0)
            if val_anterior > 0:
                var_pct = ((val_atual - val_anterior) / val_anterior) * 100
            elif val_atual > 0:
                var_pct = 100  # Novo fornecedor
            else:
                var_pct = 0
            variacoes.append({
                'Fornecedor': f,
                'Atual': val_atual,
                'Anterior': val_anterior,
                'Var_Pct': var_pct
            })

        df_var = pd.DataFrame(variacoes)
        df_var = df_var[df_var['Atual'] > 0]  # Apenas ativos

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Maior Crescimento**")
            df_cresc = df_var.sort_values('Var_Pct', ascending=False).head(5)
            for _, row in df_cresc.iterrows():
                if row['Var_Pct'] > 0:
                    st.markdown(f"""
                    <div style="background: {cores['card']}; border-left: 3px solid {cores['perigo']};
                                padding: 0.5rem; margin-bottom: 0.5rem; border-radius: 4px;">
                        <div style="color: {cores['texto']}; font-size: 0.85rem; font-weight: 600;">{row['Fornecedor'][:30]}</div>
                        <div style="color: {cores['texto_secundario']}; font-size: 0.7rem;">
                            {formatar_moeda(row['Anterior'])} → {formatar_moeda(row['Atual'])}
                        </div>
                        <div style="color: {cores['perigo']}; font-size: 0.8rem; font-weight: 600;">+{row['Var_Pct']:.1f}%</div>
                    </div>
                    """, unsafe_allow_html=True)

        with col2:
            st.markdown("**Maior Reducao**")
            df_reduc = df_var[df_var['Var_Pct'] < 0].sort_values('Var_Pct', ascending=True).head(5)
            for _, row in df_reduc.iterrows():
                st.markdown(f"""
                <div style="background: {cores['card']}; border-left: 3px solid {cores['sucesso']};
                            padding: 0.5rem; margin-bottom: 0.5rem; border-radius: 4px;">
                    <div style="color: {cores['texto']}; font-size: 0.85rem; font-weight: 600;">{row['Fornecedor'][:30]}</div>
                    <div style="color: {cores['texto_secundario']}; font-size: 0.7rem;">
                        {formatar_moeda(row['Anterior'])} → {formatar_moeda(row['Atual'])}
                    </div>
                    <div style="color: {cores['sucesso']}; font-size: 0.8rem; font-weight: 600;">{row['Var_Pct']:.1f}%</div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("Dados de variacao nao disponiveis.")

    st.divider()

    # ==========================================================================
    # SECAO 6: Matriz Fornecedor x Filial (Heatmap)
    # ==========================================================================
    st.markdown("###### Matriz Fornecedor x Filial")

    if 'FILIAL' in df_ad.columns:
        # Top 10 fornecedores x Filiais
        top10_forn = df_forn.head(10)['Fornecedor'].tolist()
        df_matriz = df_ad[df_ad['NOME_FORNECEDOR'].isin(top10_forn)].copy()

        matriz = df_matriz.pivot_table(
            values='SALDO',
            index='NOME_FORNECEDOR',
            columns='FILIAL',
            aggfunc='sum',
            fill_value=0
        )

        if len(matriz) > 0:
            fig = go.Figure(data=go.Heatmap(
                z=matriz.values,
                x=[str(c)[:20] for c in matriz.columns],
                y=[str(i)[:25] for i in matriz.index],
                colorscale='YlOrRd',
                text=[[formatar_moeda(v) for v in row] for row in matriz.values],
                texttemplate='%{text}',
                textfont=dict(size=8),
                hovertemplate='<b>%{y}</b><br>%{x}<br>Pendente: R$ %{z:,.0f}<extra></extra>'
            ))

            fig.update_layout(
                criar_layout(350),
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis=dict(tickfont=dict(size=9, color=cores['texto']), tickangle=-45),
                yaxis=dict(tickfont=dict(size=9, color=cores['texto']))
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Dados insuficientes para matriz.")
    else:
        st.info("Coluna FILIAL nao disponivel.")

    st.divider()

    # ==========================================================================
    # SECAO 7: Consulta Detalhada por Fornecedor (Drill-down)
    # ==========================================================================
    st.markdown("###### Consulta por Fornecedor")

    fornecedor_sel = st.selectbox(
        "Selecione um fornecedor",
        options=['Selecione...'] + df_forn['Fornecedor'].tolist(),
        key="forn_drill_select"
    )

    if fornecedor_sel != 'Selecione...':
        df_forn_sel = df_ad[df_ad['NOME_FORNECEDOR'] == fornecedor_sel]
        df_baixas_forn = df_bx[df_bx['NOME_FORNECEDOR'] == fornecedor_sel] if len(df_bx) > 0 and 'NOME_FORNECEDOR' in df_bx.columns else pd.DataFrame()

        # Metricas do fornecedor
        total_forn = df_forn_sel['VALOR_ORIGINAL'].sum()
        saldo_forn = df_forn_sel['SALDO'].sum()
        qtd_forn = len(df_forn_sel)
        pct_comp = ((total_forn - saldo_forn) / total_forn * 100) if total_forn > 0 else 0

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Adiantamentos", formatar_moeda(total_forn))
        col2.metric("Saldo Pendente", formatar_moeda(saldo_forn))
        col3.metric("Qtd Adiantamentos", qtd_forn)
        col4.metric("% Compensado", f"{pct_comp:.1f}%")

        # Tabs de detalhes
        tab_ad, tab_bx, tab_evol = st.tabs(["Adiantamentos", "Baixas", "Evolucao"])

        with tab_ad:
            cols_show = ['NUMERO', 'EMISSAO', 'VALOR_ORIGINAL', 'SALDO', 'FILIAL', 'TIPO']
            cols_disp = [c for c in cols_show if c in df_forn_sel.columns]

            df_ad_show = df_forn_sel[cols_disp].copy()
            df_ad_show = df_ad_show.sort_values('EMISSAO', ascending=False)

            if 'VALOR_ORIGINAL' in df_ad_show.columns:
                df_ad_show['VALOR_ORIGINAL'] = df_ad_show['VALOR_ORIGINAL'].apply(lambda x: formatar_moeda(x, completo=True))
            if 'SALDO' in df_ad_show.columns:
                df_ad_show['SALDO'] = df_ad_show['SALDO'].apply(lambda x: formatar_moeda(x, completo=True))
            if 'EMISSAO' in df_ad_show.columns:
                df_ad_show['EMISSAO'] = pd.to_datetime(df_ad_show['EMISSAO']).dt.strftime('%d/%m/%Y')

            st.dataframe(df_ad_show, use_container_width=True, hide_index=True, height=300)

        with tab_bx:
            if len(df_baixas_forn) > 0:
                cols_bx = ['NUMERO', 'DATA_BAIXA', 'VALOR_BAIXA', 'DIF_DIAS_EMIS_BAIXA', 'FILIAL']
                cols_bx_disp = [c for c in cols_bx if c in df_baixas_forn.columns]

                df_bx_show = df_baixas_forn[cols_bx_disp].copy()
                df_bx_show = df_bx_show.sort_values('DATA_BAIXA', ascending=False) if 'DATA_BAIXA' in df_bx_show.columns else df_bx_show

                if 'VALOR_BAIXA' in df_bx_show.columns:
                    df_bx_show['VALOR_BAIXA'] = df_bx_show['VALOR_BAIXA'].apply(lambda x: formatar_moeda(x, completo=True))
                if 'DATA_BAIXA' in df_bx_show.columns:
                    df_bx_show['DATA_BAIXA'] = pd.to_datetime(df_bx_show['DATA_BAIXA']).dt.strftime('%d/%m/%Y')

                st.dataframe(df_bx_show, use_container_width=True, hide_index=True, height=300)
            else:
                st.info("Nenhuma baixa registrada para este fornecedor.")

        with tab_evol:
            if 'EMISSAO' in df_forn_sel.columns:
                df_evol_f = df_forn_sel.copy()
                df_evol_f['MES'] = df_evol_f['EMISSAO'].dt.to_period('M').astype(str)
                df_evol_agg = df_evol_f.groupby('MES').agg({
                    'VALOR_ORIGINAL': 'sum',
                    'SALDO': 'sum',
                    'NUMERO': 'count'
                }).reset_index()

                fig = go.Figure()

                fig.add_trace(go.Bar(
                    x=df_evol_agg['MES'],
                    y=df_evol_agg['VALOR_ORIGINAL'] - df_evol_agg['SALDO'],
                    name='Compensado',
                    marker_color=cores['sucesso']
                ))

                fig.add_trace(go.Bar(
                    x=df_evol_agg['MES'],
                    y=df_evol_agg['SALDO'],
                    name='Pendente',
                    marker_color=cores['alerta']
                ))

                fig.update_layout(
                    criar_layout(250),
                    barmode='stack',
                    margin=dict(l=10, r=10, t=10, b=10),
                    xaxis=dict(tickfont=dict(size=9, color=cores['texto']), tickangle=-45),
                    yaxis=dict(tickfont=dict(size=9, color=cores['texto']), tickformat=',.0f'),
                    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
                )

                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Dados de evolucao nao disponiveis.")

    st.divider()

    # ==========================================================================
    # SECAO 8: Tabela Completa com Filtros
    # ==========================================================================
    st.markdown("###### Tabela Completa de Fornecedores")

    col1, col2, col3 = st.columns(3)
    with col1:
        ordenar = st.selectbox(
            "Ordenar por",
            ["Maior Saldo", "Maior Total", "Maior Ticket", "Menor % Compensado", "Maior Prazo"],
            key="forn_ordem_v2"
        )
    with col2:
        filtro = st.selectbox(
            "Filtrar",
            ["Todos", "Com Pendencia", "Quitados", "Prazo > 60d", "Ticket > Media"],
            key="forn_filtro_v2"
        )
    with col3:
        busca = st.text_input("Buscar fornecedor", key="forn_busca")

    df_exibir = df_forn.copy()

    # Aplicar filtros
    if filtro == "Com Pendencia":
        df_exibir = df_exibir[df_exibir['Saldo'] > 0]
    elif filtro == "Quitados":
        df_exibir = df_exibir[df_exibir['Saldo'] <= 0]
    elif filtro == "Prazo > 60d":
        df_exibir = df_exibir[df_exibir['Prazo_Medio'] > 60]
    elif filtro == "Ticket > Media":
        df_exibir = df_exibir[df_exibir['Ticket_Medio'] > ticket_medio_geral]

    if busca:
        df_exibir = df_exibir[df_exibir['Fornecedor'].str.upper().str.contains(busca.upper(), na=False)]

    # Ordenar
    if ordenar == "Maior Saldo":
        df_exibir = df_exibir.sort_values('Saldo', ascending=False)
    elif ordenar == "Maior Total":
        df_exibir = df_exibir.sort_values('Total', ascending=False)
    elif ordenar == "Maior Ticket":
        df_exibir = df_exibir.sort_values('Ticket_Medio', ascending=False)
    elif ordenar == "Menor % Compensado":
        df_exibir = df_exibir.sort_values('Pct', ascending=True)
    elif ordenar == "Maior Prazo":
        df_exibir = df_exibir.sort_values('Prazo_Medio', ascending=False)

    df_exibir = df_exibir.head(100)

    # Preparar para exibicao
    df_show = df_exibir.copy()
    df_show['Total'] = df_show['Total'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Compensado'] = df_show['Compensado'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Saldo'] = df_show['Saldo'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Ticket_Medio'] = df_show['Ticket_Medio'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Prazo_Medio'] = df_show['Prazo_Medio'].apply(lambda x: f"{int(x)}d" if x > 0 else '-')
    df_show.columns = ['Fornecedor', 'Total', 'Pendente', 'Qtd', 'Compensado', '% Comp', 'Ticket Medio', 'Prazo Medio']
    df_show = df_show[['Fornecedor', 'Total', 'Compensado', 'Pendente', 'Qtd', '% Comp', 'Ticket Medio', 'Prazo Medio']]

    st.dataframe(
        df_show,
        use_container_width=True,
        hide_index=True,
        height=400,
        column_config={
            '% Comp': st.column_config.ProgressColumn(
                '% Comp',
                format='%.0f%%',
                min_value=0,
                max_value=100
            )
        }
    )

    st.caption(f"Exibindo {len(df_show)} de {len(df_forn)} fornecedores")


def _render_aging(df_ad, cores, hoje):
    """Analise completa de antiguidade dos adiantamentos pendentes"""

    # Titulo com explicacao
    st.markdown("##### Aging - Ha quanto tempo os adiantamentos estao sem baixa?")

    # Box explicativo no topo
    st.markdown(f"""
    <div style="background: {cores['card']}; border: 1px solid {cores['borda']}; border-left: 4px solid {cores['info']};
                border-radius: 8px; padding: 1rem; margin-bottom: 1rem;">
        <div style="color: {cores['texto']}; font-size: 0.9rem; font-weight: 600; margin-bottom: 0.5rem;">
            O que e esta analise?
        </div>
        <div style="color: {cores['texto_secundario']}; font-size: 0.8rem; line-height: 1.5;">
            Esta pagina mostra <b style="color: {cores['texto']};">ha quantos dias cada adiantamento esta pendente</b> (sem receber a nota fiscal ou prestacao de contas).
            <br><br>
            <b style="color: {cores['sucesso']};">Verde</b> = Adiantamento recente, situacao normal<br>
            <b style="color: {cores['alerta']};">Amarelo</b> = Ja passou do prazo esperado, precisa de atencao<br>
            <b style="color: {cores['perigo']};">Vermelho</b> = Muito atrasado, precisa cobrar urgente a NF/prestacao de contas
        </div>
    </div>
    """, unsafe_allow_html=True)

    if len(df_ad) == 0 or 'SALDO' not in df_ad.columns:
        st.info("Nenhum dado disponivel.")
        return

    df_pend = df_ad[df_ad['SALDO'] > 0].copy()

    if len(df_pend) == 0:
        st.success("Nenhum adiantamento pendente!")
        return

    # Calcular dias pendente
    if 'DIAS_PENDENTE' not in df_pend.columns:
        df_pend['DIAS_PENDENTE'] = (hoje - df_pend['EMISSAO']).dt.days

    # Classificar por faixa de aging
    def faixa_aging(dias):
        if pd.isna(dias) or dias < 0:
            return 'N/A'
        dias = int(dias)
        if dias <= 30:
            return '0-30 dias'
        elif dias <= 60:
            return '31-60 dias'
        elif dias <= 90:
            return '61-90 dias'
        elif dias <= 180:
            return '91-180 dias'
        elif dias <= 365:
            return '181-365 dias'
        return '365+ dias'

    df_pend['FAIXA_AGING'] = df_pend['DIAS_PENDENTE'].apply(faixa_aging)

    # Ordem das faixas e cores
    ordem_faixas = ['0-30 dias', '31-60 dias', '61-90 dias', '91-180 dias', '181-365 dias', '365+ dias']
    cores_aging = [cores['sucesso'], cores['info'], cores['alerta'], '#f97316', cores['perigo'], '#7f1d1d']

    # ==========================================================================
    # SECAO 1: LEGENDA DAS FAIXAS (Visual e clara)
    # ==========================================================================
    st.markdown("###### Entenda as Faixas de Tempo")

    st.markdown(f"""
    <div style="display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 1rem;">
        <div style="background: {cores['sucesso']}22; border: 1px solid {cores['sucesso']}; border-radius: 6px; padding: 0.5rem 0.8rem; flex: 1; min-width: 140px;">
            <div style="color: {cores['sucesso']}; font-weight: 700; font-size: 0.85rem;">0-30 dias</div>
            <div style="color: {cores['texto_secundario']}; font-size: 0.7rem;">Normal - Adiantamento recente</div>
        </div>
        <div style="background: {cores['info']}22; border: 1px solid {cores['info']}; border-radius: 6px; padding: 0.5rem 0.8rem; flex: 1; min-width: 140px;">
            <div style="color: {cores['info']}; font-weight: 700; font-size: 0.85rem;">31-60 dias</div>
            <div style="color: {cores['texto_secundario']}; font-size: 0.7rem;">Aceitavel - Acompanhar</div>
        </div>
        <div style="background: {cores['alerta']}22; border: 1px solid {cores['alerta']}; border-radius: 6px; padding: 0.5rem 0.8rem; flex: 1; min-width: 140px;">
            <div style="color: {cores['alerta']}; font-weight: 700; font-size: 0.85rem;">61-90 dias</div>
            <div style="color: {cores['texto_secundario']}; font-size: 0.7rem;">Atencao - Cobrar NF</div>
        </div>
        <div style="background: #f9731622; border: 1px solid #f97316; border-radius: 6px; padding: 0.5rem 0.8rem; flex: 1; min-width: 140px;">
            <div style="color: #f97316; font-weight: 700; font-size: 0.85rem;">91-180 dias</div>
            <div style="color: {cores['texto_secundario']}; font-size: 0.7rem;">Alerta - Muito atrasado</div>
        </div>
        <div style="background: {cores['perigo']}22; border: 1px solid {cores['perigo']}; border-radius: 6px; padding: 0.5rem 0.8rem; flex: 1; min-width: 140px;">
            <div style="color: {cores['perigo']}; font-weight: 700; font-size: 0.85rem;">181-365 dias</div>
            <div style="color: {cores['texto_secundario']}; font-size: 0.7rem;">Critico - Acao urgente</div>
        </div>
        <div style="background: #7f1d1d22; border: 1px solid #7f1d1d; border-radius: 6px; padding: 0.5rem 0.8rem; flex: 1; min-width: 140px;">
            <div style="color: #7f1d1d; font-weight: 700; font-size: 0.85rem;">365+ dias</div>
            <div style="color: {cores['texto_secundario']}; font-size: 0.7rem;">Esquecido - Risco de perda</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ==========================================================================
    # SECAO 2: KPIs (5 cards estilizados com explicacoes)
    # ==========================================================================
    st.markdown("###### Resumo da Situacao Atual")

    total_pendente = df_pend['SALDO'].sum()
    qtd_total = len(df_pend)
    dias_medio = df_pend['DIAS_PENDENTE'].mean()
    dias_max = df_pend['DIAS_PENDENTE'].max()

    # Criticos (>90 dias)
    df_critico = df_pend[df_pend['DIAS_PENDENTE'] > 90]
    valor_critico = df_critico['SALDO'].sum()
    qtd_critico = len(df_critico)
    pct_critico = (valor_critico / total_pendente * 100) if total_pendente > 0 else 0

    # Score de risco (valor ponderado por dias)
    df_pend['SCORE_RISCO'] = df_pend['SALDO'] * (df_pend['DIAS_PENDENTE'] / 30)
    score_total = df_pend['SCORE_RISCO'].sum()

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.markdown(f"""
    <div style="background: {cores['card']}; border: 1px solid {cores['borda']}; border-radius: 8px; padding: 0.8rem; text-align: center;">
        <div style="color: {cores['texto_secundario']}; font-size: 0.65rem;">VALOR SEM BAIXA</div>
        <div style="color: {cores['alerta']}; font-size: 1.3rem; font-weight: 700;">{formatar_moeda(total_pendente)}</div>
        <div style="color: {cores['texto_secundario']}; font-size: 0.65rem;">{qtd_total} adiantamentos<br>aguardando NF</div>
    </div>
    """, unsafe_allow_html=True)

    # Cor da idade media baseada no valor
    if dias_medio <= 60:
        cor_idade = cores['sucesso']
        status_idade = "Bom"
    elif dias_medio <= 90:
        cor_idade = cores['alerta']
        status_idade = "Atencao"
    else:
        cor_idade = cores['perigo']
        status_idade = "Ruim"

    col2.markdown(f"""
    <div style="background: {cores['card']}; border: 1px solid {cores['borda']}; border-radius: 8px; padding: 0.8rem; text-align: center;">
        <div style="color: {cores['texto_secundario']}; font-size: 0.65rem;">TEMPO MEDIO ESPERANDO</div>
        <div style="color: {cor_idade}; font-size: 1.3rem; font-weight: 700;">{dias_medio:.0f} dias</div>
        <div style="color: {cor_idade}; font-size: 0.65rem;">{status_idade}<br>(~{dias_medio/30:.1f} meses)</div>
    </div>
    """, unsafe_allow_html=True)

    col3.markdown(f"""
    <div style="background: {cores['card']}; border: 1px solid {cores['borda']}; border-radius: 8px; padding: 0.8rem; text-align: center;">
        <div style="color: {cores['texto_secundario']}; font-size: 0.65rem;">ADIANTAMENTO MAIS ANTIGO</div>
        <div style="color: {cores['perigo']}; font-size: 1.3rem; font-weight: 700;">{int(dias_max)} dias</div>
        <div style="color: {cores['texto_secundario']}; font-size: 0.65rem;">sem receber NF<br>(~{dias_max/30:.0f} meses)</div>
    </div>
    """, unsafe_allow_html=True)

    col4.markdown(f"""
    <div style="background: {cores['card']}; border: 1px solid {cores['borda']}; border-radius: 8px; padding: 0.8rem; text-align: center;">
        <div style="color: {cores['texto_secundario']}; font-size: 0.65rem;">VALOR EM SITUACAO CRITICA</div>
        <div style="color: {cores['perigo']}; font-size: 1.3rem; font-weight: 700;">{formatar_moeda(valor_critico)}</div>
        <div style="color: {cores['texto_secundario']}; font-size: 0.65rem;">{qtd_critico} adiant. com<br>mais de 90 dias</div>
    </div>
    """, unsafe_allow_html=True)

    # Classificar score de risco
    if score_total > 1000000:
        score_nivel = "ALTO"
        score_cor = cores['perigo']
        score_desc = "Acao urgente"
    elif score_total > 500000:
        score_nivel = "MEDIO"
        score_cor = cores['alerta']
        score_desc = "Requer atencao"
    else:
        score_nivel = "BAIXO"
        score_cor = cores['sucesso']
        score_desc = "Situacao ok"

    col5.markdown(f"""
    <div style="background: {cores['card']}; border: 1px solid {cores['borda']}; border-radius: 8px; padding: 0.8rem; text-align: center;">
        <div style="color: {cores['texto_secundario']}; font-size: 0.65rem;">NIVEL DE RISCO GERAL</div>
        <div style="color: {score_cor}; font-size: 1.3rem; font-weight: 700;">{score_nivel}</div>
        <div style="color: {score_cor}; font-size: 0.65rem;">{score_desc}<br>(valor x tempo)</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ==========================================================================
    # SECAO 3: Distribuicao por Faixa (Barras + Donut)
    # ==========================================================================
    st.markdown("###### Quanto dinheiro esta em cada faixa de tempo?")
    st.caption("Este grafico mostra a distribuicao do valor pendente por tempo de espera")

    col1, col2 = st.columns(2)

    df_aging = df_pend.groupby('FAIXA_AGING').agg({
        'SALDO': 'sum',
        'DIAS_PENDENTE': 'count'
    }).reindex(ordem_faixas, fill_value=0).reset_index()
    df_aging.columns = ['Faixa', 'Valor', 'Qtd']

    with col1:
        st.markdown("###### Valor por Faixa de Tempo")
        st.caption("Barras maiores = mais dinheiro parado nessa faixa")

        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=df_aging['Faixa'],
            y=df_aging['Valor'],
            marker_color=cores_aging,
            text=[f"{formatar_moeda(v)}<br>({int(q)} tit.)" for v, q in zip(df_aging['Valor'], df_aging['Qtd'])],
            textposition='outside',
            textfont=dict(size=9, color=cores['texto'])
        ))

        fig.update_layout(
            criar_layout(300),
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis=dict(tickfont=dict(size=8, color=cores['texto']), tickangle=-30),
            yaxis=dict(showticklabels=False, showgrid=False)
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("###### Percentual em cada Faixa")
        st.caption("Mostra a % do valor total em cada faixa")

        df_donut = df_aging[df_aging['Valor'] > 0]

        if len(df_donut) > 0:
            fig = go.Figure(go.Pie(
                labels=df_donut['Faixa'],
                values=df_donut['Valor'],
                hole=0.6,
                textinfo='percent',
                textposition='outside',
                textfont=dict(size=9, color=cores['texto']),
                marker=dict(colors=cores_aging[:len(df_donut)]),
                hovertemplate='<b>%{label}</b><br>Valor: R$ %{value:,.0f}<br>%{percent}<extra></extra>'
            ))

            fig.update_layout(
                criar_layout(300),
                showlegend=True,
                legend=dict(orientation='h', yanchor='bottom', y=-0.2, xanchor='center', x=0.5,
                            font=dict(size=8, color=cores['texto'])),
                margin=dict(l=10, r=10, t=10, b=50),
                annotations=[dict(
                    text=f"<b>{formatar_moeda(total_pendente)}</b><br>Total",
                    x=0.5, y=0.5, font=dict(size=10, color=cores['texto']),
                    showarrow=False
                )]
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados")

    st.divider()

    # ==========================================================================
    # SECAO 4: Evolucao Temporal do Aging (Area Stackada)
    # ==========================================================================
    st.markdown("###### A situacao esta melhorando ou piorando?")
    st.caption("Este grafico mostra como os adiantamentos pendentes evoluiram ao longo do tempo. Se as cores vermelhas estao crescendo, a situacao esta piorando.")

    if 'EMISSAO' in df_ad.columns:
        # Simular evolucao baseada nas emissoes (snapshot mensal)
        df_evol = df_ad[df_ad['SALDO'] > 0].copy()
        df_evol['MES_EMISSAO'] = df_evol['EMISSAO'].dt.to_period('M').astype(str)

        # Adicionar coluna FAIXA_AGING ao df_evol
        df_evol['DIAS_PEND_EVOL'] = (hoje - df_evol['EMISSAO']).dt.days
        df_evol['FAIXA_AGING'] = df_evol['DIAS_PEND_EVOL'].apply(faixa_aging)

        # Agrupar por mes de emissao e calcular aging acumulado
        meses = df_evol['MES_EMISSAO'].unique()
        meses = sorted(meses)[-12:]  # Ultimos 12 meses

        evol_data = []
        for mes in meses:
            df_mes = df_evol[df_evol['MES_EMISSAO'] <= mes]
            for faixa in ordem_faixas:
                valor = df_mes[df_mes['FAIXA_AGING'] == faixa]['SALDO'].sum()
                evol_data.append({'Mes': mes, 'Faixa': faixa, 'Valor': valor})

        df_evol_agg = pd.DataFrame(evol_data)

        if len(df_evol_agg) > 0:
            fig = go.Figure()

            for i, faixa in enumerate(ordem_faixas):
                df_f = df_evol_agg[df_evol_agg['Faixa'] == faixa].sort_values('Mes')
                if len(df_f) > 0 and df_f['Valor'].sum() > 0:
                    fig.add_trace(go.Scatter(
                        x=df_f['Mes'],
                        y=df_f['Valor'],
                        mode='lines',
                        name=faixa,
                        stackgroup='one',
                        line=dict(width=0.5, color=cores_aging[i]),
                        fillcolor=cores_aging[i],
                        hovertemplate=f'<b>{faixa}</b><br>%{{x}}<br>R$ %{{y:,.0f}}<extra></extra>'
                    ))

            fig.update_layout(
                criar_layout(280),
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis=dict(tickfont=dict(size=9, color=cores['texto']), tickangle=-45),
                yaxis=dict(tickfont=dict(size=9, color=cores['texto']), tickformat=',.0f'),
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1, font=dict(size=8))
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Dados de evolucao nao disponiveis.")
    else:
        st.info("Coluna EMISSAO nao disponivel.")

    st.divider()

    # ==========================================================================
    # SECAO 5: Heatmaps - Filial x Faixa e Tipo x Faixa
    # ==========================================================================
    st.markdown("###### Onde estao os problemas?")
    st.caption("Cores mais escuras = mais dinheiro parado. Identifique quais filiais e tipos de adiantamento estao com mais atraso.")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Por Filial** - Qual unidade tem mais atraso?")

        if 'FILIAL' in df_pend.columns or 'NOME_FILIAL' in df_pend.columns:
            col_filial = 'NOME_FILIAL' if 'NOME_FILIAL' in df_pend.columns else 'FILIAL'

            matriz_filial = df_pend.pivot_table(
                values='SALDO',
                index=col_filial,
                columns='FAIXA_AGING',
                aggfunc='sum',
                fill_value=0
            )

            # Reordenar colunas
            cols_order = [c for c in ordem_faixas if c in matriz_filial.columns]
            matriz_filial = matriz_filial[cols_order]

            # Top 10 filiais por saldo total
            matriz_filial['Total'] = matriz_filial.sum(axis=1)
            matriz_filial = matriz_filial.sort_values('Total', ascending=False).head(10)
            matriz_filial = matriz_filial.drop('Total', axis=1)

            if len(matriz_filial) > 0:
                fig = go.Figure(data=go.Heatmap(
                    z=matriz_filial.values,
                    x=[c.replace(' dias', 'd') for c in matriz_filial.columns],
                    y=[str(i)[:20] for i in matriz_filial.index],
                    colorscale='YlOrRd',
                    text=[[formatar_moeda(v) if v > 0 else '' for v in row] for row in matriz_filial.values],
                    texttemplate='%{text}',
                    textfont=dict(size=7),
                    hovertemplate='<b>%{y}</b><br>%{x}<br>R$ %{z:,.0f}<extra></extra>'
                ))

                fig.update_layout(
                    criar_layout(300),
                    margin=dict(l=10, r=10, t=10, b=10),
                    xaxis=dict(tickfont=dict(size=8, color=cores['texto'])),
                    yaxis=dict(tickfont=dict(size=8, color=cores['texto']))
                )

                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Dados insuficientes.")
        else:
            st.info("Coluna FILIAL nao disponivel.")

    with col2:
        st.markdown("**Por Tipo** - Qual tipo de adiantamento esta mais atrasado?")

        if 'TIPO_ADTO' in df_pend.columns or 'DESCRICAO' in df_pend.columns:
            col_tipo = 'TIPO_ADTO' if 'TIPO_ADTO' in df_pend.columns else 'DESCRICAO'

            matriz_tipo = df_pend.pivot_table(
                values='SALDO',
                index=col_tipo,
                columns='FAIXA_AGING',
                aggfunc='sum',
                fill_value=0
            )

            # Reordenar colunas
            cols_order = [c for c in ordem_faixas if c in matriz_tipo.columns]
            matriz_tipo = matriz_tipo[cols_order]

            # Top 8 tipos por saldo total
            matriz_tipo['Total'] = matriz_tipo.sum(axis=1)
            matriz_tipo = matriz_tipo.sort_values('Total', ascending=False).head(8)
            matriz_tipo = matriz_tipo.drop('Total', axis=1)

            if len(matriz_tipo) > 0:
                fig = go.Figure(data=go.Heatmap(
                    z=matriz_tipo.values,
                    x=[c.replace(' dias', 'd') for c in matriz_tipo.columns],
                    y=[str(i)[:25] for i in matriz_tipo.index],
                    colorscale='YlOrRd',
                    text=[[formatar_moeda(v) if v > 0 else '' for v in row] for row in matriz_tipo.values],
                    texttemplate='%{text}',
                    textfont=dict(size=7),
                    hovertemplate='<b>%{y}</b><br>%{x}<br>R$ %{z:,.0f}<extra></extra>'
                ))

                fig.update_layout(
                    criar_layout(300),
                    margin=dict(l=10, r=10, t=10, b=10),
                    xaxis=dict(tickfont=dict(size=8, color=cores['texto'])),
                    yaxis=dict(tickfont=dict(size=8, color=cores['texto']))
                )

                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Dados insuficientes.")
        else:
            st.info("Coluna TIPO nao disponivel.")

    st.divider()

    # ==========================================================================
    # SECAO 6: Comparativo vs Periodo Anterior
    # ==========================================================================
    st.markdown("###### Resumo Rapido por Faixa")
    st.caption("Visao consolidada: quanto tem em cada faixa e quantos adiantamentos")

    if 'EMISSAO' in df_ad.columns:
        # Calcular aging do mes passado (simulado)
        mes_atual = hoje.month
        ano_atual = hoje.year

        # Cards de comparativo por faixa
        col_cards = st.columns(len(ordem_faixas))

        for i, faixa in enumerate(ordem_faixas):
            valor_faixa = df_aging[df_aging['Faixa'] == faixa]['Valor'].values[0] if faixa in df_aging['Faixa'].values else 0
            qtd_faixa = df_aging[df_aging['Faixa'] == faixa]['Qtd'].values[0] if faixa in df_aging['Faixa'].values else 0

            # Determinar cor e icone baseado na faixa
            if i <= 1:  # 0-30, 31-60 = saudavel
                status_icon = "✓"
                status_cor = cores['sucesso']
            elif i <= 2:  # 61-90 = atencao
                status_icon = "!"
                status_cor = cores['alerta']
            else:  # >90 = critico
                status_icon = "⚠"
                status_cor = cores['perigo']

            with col_cards[i]:
                st.markdown(f"""
                <div style="background: {cores['card']}; border: 1px solid {cores['borda']};
                            border-left: 3px solid {cores_aging[i]}; border-radius: 6px;
                            padding: 0.6rem; text-align: center;">
                    <div style="color: {cores['texto_secundario']}; font-size: 0.65rem;">{faixa.replace(' dias', 'd')}</div>
                    <div style="color: {cores['texto']}; font-size: 1rem; font-weight: 700;">{formatar_moeda(valor_faixa)}</div>
                    <div style="color: {status_cor}; font-size: 0.7rem;">{status_icon} {int(qtd_faixa)} tit.</div>
                </div>
                """, unsafe_allow_html=True)

    st.divider()

    # ==========================================================================
    # SECAO 7: Top 15 Mais Criticos (Detalhado com Score)
    # ==========================================================================
    st.markdown("###### Quem precisa ser cobrado com urgencia?")
    st.caption("Lista dos fornecedores com adiantamentos mais antigos e de maior valor. Esses sao os que precisam enviar NF/prestacao de contas primeiro.")

    # Ordenar por score de risco
    df_top_criticos = df_pend.sort_values('SCORE_RISCO', ascending=False).head(15)

    if len(df_top_criticos) > 0:
        col1, col2 = st.columns([2, 1])

        with col1:
            fig = go.Figure()

            # Cor baseada nos dias
            bar_colors = []
            for d in df_top_criticos['DIAS_PENDENTE']:
                if d > 365:
                    bar_colors.append('#7f1d1d')
                elif d > 180:
                    bar_colors.append(cores['perigo'])
                elif d > 90:
                    bar_colors.append('#f97316')
                elif d > 60:
                    bar_colors.append(cores['alerta'])
                else:
                    bar_colors.append(cores['info'])

            fig.add_trace(go.Bar(
                y=df_top_criticos['NOME_FORNECEDOR'].str[:25],
                x=df_top_criticos['SALDO'],
                orientation='h',
                marker_color=bar_colors,
                text=[f"{formatar_moeda(s)} | {int(d)}d" for s, d in zip(df_top_criticos['SALDO'], df_top_criticos['DIAS_PENDENTE'])],
                textposition='outside',
                textfont=dict(size=8, color=cores['texto'])
            ))

            fig.update_layout(
                criar_layout(380),
                margin=dict(l=10, r=100, t=10, b=10),
                xaxis=dict(showticklabels=False, showgrid=False),
                yaxis=dict(tickfont=dict(size=8, color=cores['texto']), autorange='reversed')
            )

            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("**O que significa cada cor?**")
            st.markdown(f"""
            <div style="font-size: 0.75rem;">
                <div style="display: flex; align-items: center; margin-bottom: 0.4rem;">
                    <div style="width: 14px; height: 14px; background: {cores['info']}; border-radius: 2px; margin-right: 0.5rem;"></div>
                    <span style="color: {cores['texto']};">0-60 dias - OK</span>
                </div>
                <div style="display: flex; align-items: center; margin-bottom: 0.4rem;">
                    <div style="width: 14px; height: 14px; background: {cores['alerta']}; border-radius: 2px; margin-right: 0.5rem;"></div>
                    <span style="color: {cores['texto']};">61-90 dias - Cobrar</span>
                </div>
                <div style="display: flex; align-items: center; margin-bottom: 0.4rem;">
                    <div style="width: 14px; height: 14px; background: #f97316; border-radius: 2px; margin-right: 0.5rem;"></div>
                    <span style="color: {cores['texto']};">91-180 dias - Atrasado</span>
                </div>
                <div style="display: flex; align-items: center; margin-bottom: 0.4rem;">
                    <div style="width: 14px; height: 14px; background: {cores['perigo']}; border-radius: 2px; margin-right: 0.5rem;"></div>
                    <span style="color: {cores['texto']};">181-365 dias - Critico</span>
                </div>
                <div style="display: flex; align-items: center;">
                    <div style="width: 14px; height: 14px; background: #7f1d1d; border-radius: 2px; margin-right: 0.5rem;"></div>
                    <span style="color: {cores['texto']};">365+ dias - Esquecido</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("**Resumo Criticos**")
            st.markdown(f"""
            <div style="font-size: 0.8rem; color: {cores['texto_secundario']};">
                <div>Total: <b style="color: {cores['texto']};">{formatar_moeda(df_top_criticos['SALDO'].sum())}</b></div>
                <div>Media dias: <b style="color: {cores['texto']};">{df_top_criticos['DIAS_PENDENTE'].mean():.0f}d</b></div>
                <div>Maior: <b style="color: {cores['perigo']};">{int(df_top_criticos['DIAS_PENDENTE'].max())}d</b></div>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    # ==========================================================================
    # SECAO 8: Drill-down por Faixa
    # ==========================================================================
    st.markdown("###### Explorar uma Faixa Especifica")
    st.caption("Selecione uma faixa abaixo para ver detalhes: quais fornecedores, quais filiais e lista completa dos adiantamentos nessa faixa.")

    faixa_drill = st.selectbox(
        "Qual faixa voce quer analisar?",
        options=['Selecione uma faixa...'] + ordem_faixas,
        key="aging_drill_faixa"
    )

    if faixa_drill != 'Selecione uma faixa...':
        df_faixa = df_pend[df_pend['FAIXA_AGING'] == faixa_drill]

        # Metricas da faixa
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Valor na Faixa", formatar_moeda(df_faixa['SALDO'].sum()))
        col2.metric("Quantidade", len(df_faixa))
        col3.metric("Ticket Medio", formatar_moeda(df_faixa['SALDO'].mean()) if len(df_faixa) > 0 else "R$ 0")
        col4.metric("% do Total", f"{(df_faixa['SALDO'].sum() / total_pendente * 100):.1f}%" if total_pendente > 0 else "0%")

        # Tabs de detalhes
        tab_forn, tab_fil, tab_lista = st.tabs(["Por Fornecedor", "Por Filial", "Lista Completa"])

        with tab_forn:
            df_forn_faixa = df_faixa.groupby('NOME_FORNECEDOR').agg({
                'SALDO': 'sum',
                'DIAS_PENDENTE': 'mean'
            }).reset_index().sort_values('SALDO', ascending=False).head(10)

            if len(df_forn_faixa) > 0:
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=df_forn_faixa['SALDO'],
                    y=df_forn_faixa['NOME_FORNECEDOR'].str[:25],
                    orientation='h',
                    marker_color=cores_aging[ordem_faixas.index(faixa_drill)],
                    text=[formatar_moeda(v) for v in df_forn_faixa['SALDO']],
                    textposition='outside',
                    textfont=dict(size=9, color=cores['texto'])
                ))
                fig.update_layout(
                    criar_layout(280),
                    margin=dict(l=10, r=80, t=10, b=10),
                    xaxis=dict(showticklabels=False, showgrid=False),
                    yaxis=dict(tickfont=dict(size=9, color=cores['texto']))
                )
                st.plotly_chart(fig, use_container_width=True)

        with tab_fil:
            col_filial = 'NOME_FILIAL' if 'NOME_FILIAL' in df_faixa.columns else 'FILIAL'
            if col_filial in df_faixa.columns:
                df_fil_faixa = df_faixa.groupby(col_filial).agg({
                    'SALDO': 'sum',
                    'DIAS_PENDENTE': 'count'
                }).reset_index().sort_values('SALDO', ascending=False).head(10)
                df_fil_faixa.columns = [col_filial, 'Valor', 'Qtd']

                if len(df_fil_faixa) > 0:
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=df_fil_faixa['Valor'],
                        y=df_fil_faixa[col_filial].astype(str).str[:20],
                        orientation='h',
                        marker_color=cores_aging[ordem_faixas.index(faixa_drill)],
                        text=[f"{formatar_moeda(v)} ({int(q)})" for v, q in zip(df_fil_faixa['Valor'], df_fil_faixa['Qtd'])],
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
            else:
                st.info("Dados de filial nao disponiveis.")

        with tab_lista:
            cols_lista = ['NOME_FORNECEDOR', 'NOME_FILIAL', 'EMISSAO', 'DIAS_PENDENTE', 'VALOR_ORIGINAL', 'SALDO']
            cols_disp = [c for c in cols_lista if c in df_faixa.columns]

            df_lista = df_faixa[cols_disp].sort_values('SALDO', ascending=False).head(30).copy()

            if 'EMISSAO' in df_lista.columns:
                df_lista['EMISSAO'] = pd.to_datetime(df_lista['EMISSAO']).dt.strftime('%d/%m/%Y')
            if 'VALOR_ORIGINAL' in df_lista.columns:
                df_lista['VALOR_ORIGINAL'] = df_lista['VALOR_ORIGINAL'].apply(lambda x: formatar_moeda(x, completo=True))
            if 'SALDO' in df_lista.columns:
                df_lista['SALDO'] = df_lista['SALDO'].apply(lambda x: formatar_moeda(x, completo=True))
            if 'DIAS_PENDENTE' in df_lista.columns:
                df_lista['DIAS_PENDENTE'] = df_lista['DIAS_PENDENTE'].apply(lambda x: f"{int(x)}d")

            st.dataframe(df_lista, use_container_width=True, hide_index=True, height=300)

    st.divider()

    # ==========================================================================
    # SECAO 9: Tabela Completa com Filtros Avancados
    # ==========================================================================
    st.markdown("###### Lista Completa - Todos os Adiantamentos Pendentes")
    st.caption("Use os filtros abaixo para encontrar adiantamentos especificos. Voce pode filtrar por faixa de tempo, filial, ou buscar por nome do fornecedor.")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        faixa_sel = st.selectbox("Faixa", ["Todas"] + ordem_faixas, key="aging_tab_faixa")
    with col2:
        ordenar = st.selectbox("Ordenar", ["Maior Valor", "Mais Antigo", "Maior Score"], key="aging_tab_ordem")
    with col3:
        col_filial = 'NOME_FILIAL' if 'NOME_FILIAL' in df_pend.columns else 'FILIAL'
        filiais = ['Todas'] + sorted(df_pend[col_filial].dropna().unique().astype(str).tolist()) if col_filial in df_pend.columns else ['Todas']
        filial_sel = st.selectbox("Filial", filiais, key="aging_tab_filial")
    with col4:
        busca = st.text_input("Buscar fornecedor", key="aging_tab_busca")

    df_tab = df_pend.copy()

    # Aplicar filtros
    if faixa_sel != "Todas":
        df_tab = df_tab[df_tab['FAIXA_AGING'] == faixa_sel]

    if filial_sel != "Todas" and col_filial in df_tab.columns:
        df_tab = df_tab[df_tab[col_filial].astype(str) == filial_sel]

    if busca:
        df_tab = df_tab[df_tab['NOME_FORNECEDOR'].str.upper().str.contains(busca.upper(), na=False)]

    # Ordenar
    if ordenar == "Maior Valor":
        df_tab = df_tab.sort_values('SALDO', ascending=False)
    elif ordenar == "Mais Antigo":
        df_tab = df_tab.sort_values('DIAS_PENDENTE', ascending=False)
    else:
        df_tab = df_tab.sort_values('SCORE_RISCO', ascending=False)

    df_tab = df_tab.head(100)

    # Preparar para exibicao
    colunas = ['NOME_FILIAL', 'NOME_FORNECEDOR', 'DESCRICAO', 'EMISSAO', 'DIAS_PENDENTE', 'VALOR_ORIGINAL', 'SALDO', 'FAIXA_AGING', 'SCORE_RISCO']
    colunas_disp = [c for c in colunas if c in df_tab.columns]
    df_show = df_tab[colunas_disp].copy()

    if 'EMISSAO' in df_show.columns:
        df_show['EMISSAO'] = pd.to_datetime(df_show['EMISSAO'], errors='coerce').dt.strftime('%d/%m/%Y')

    if 'VALOR_ORIGINAL' in df_show.columns:
        df_show['VALOR_ORIGINAL'] = df_show['VALOR_ORIGINAL'].apply(lambda x: formatar_moeda(x, completo=True))
    if 'SALDO' in df_show.columns:
        df_show['SALDO'] = df_show['SALDO'].apply(lambda x: formatar_moeda(x, completo=True))
    if 'DIAS_PENDENTE' in df_show.columns:
        df_show['DIAS_PENDENTE'] = df_show['DIAS_PENDENTE'].apply(lambda x: f"{int(x)}d" if pd.notna(x) else '-')
    if 'SCORE_RISCO' in df_show.columns:
        df_show['SCORE_RISCO'] = df_show['SCORE_RISCO'].apply(lambda x: f"{x:,.0f}")

    nomes = {
        'NOME_FILIAL': 'Filial',
        'NOME_FORNECEDOR': 'Fornecedor',
        'DESCRICAO': 'Tipo',
        'EMISSAO': 'Emissao',
        'DIAS_PENDENTE': 'Dias',
        'VALOR_ORIGINAL': 'Valor Orig.',
        'SALDO': 'Saldo',
        'FAIXA_AGING': 'Faixa',
        'SCORE_RISCO': 'Score'
    }
    df_show.columns = [nomes.get(c, c) for c in df_show.columns]

    st.dataframe(df_show, use_container_width=True, hide_index=True, height=400)
    st.caption(f"Exibindo {len(df_show)} de {len(df_pend)} adiantamentos pendentes")


def _render_tendencias(df_ad, df_bx, cores, hoje):
    """Analise de tendencias e sazonalidade"""

    st.markdown("##### Tendencias e Projecoes")

    if len(df_ad) == 0:
        st.info("Nenhum dado disponivel.")
        return

    # ========== COMPARATIVO PERIODOS ==========
    st.markdown("###### Comparativo de Periodos")

    col1, col2 = st.columns([1, 3])

    with col1:
        periodo = st.selectbox(
            "Comparar",
            ['Ultimo mes vs anterior', 'Ultimo trimestre vs anterior', 'Ultimo semestre vs anterior'],
            key='tend_periodo'
        )

    dias_map = {
        'Ultimo mes vs anterior': 30,
        'Ultimo trimestre vs anterior': 90,
        'Ultimo semestre vs anterior': 180
    }
    dias = dias_map[periodo]

    df_atual = df_ad[df_ad['EMISSAO'] >= hoje - timedelta(days=dias)]
    df_anterior = df_ad[(df_ad['EMISSAO'] >= hoje - timedelta(days=dias*2)) & (df_ad['EMISSAO'] < hoje - timedelta(days=dias))]

    with col2:
        if len(df_atual) > 0 or len(df_anterior) > 0:
            col_a, col_b, col_c, col_d = st.columns(4)

            val_atual = df_atual['VALOR_ORIGINAL'].sum()
            val_anterior = df_anterior['VALOR_ORIGINAL'].sum()
            var_val = ((val_atual - val_anterior) / val_anterior * 100) if val_anterior > 0 else 0

            qtd_atual = len(df_atual)
            qtd_anterior = len(df_anterior)
            var_qtd = ((qtd_atual - qtd_anterior) / qtd_anterior * 100) if qtd_anterior > 0 else 0

            ticket_atual = val_atual / qtd_atual if qtd_atual > 0 else 0
            ticket_anterior = val_anterior / qtd_anterior if qtd_anterior > 0 else 0
            var_ticket = ((ticket_atual - ticket_anterior) / ticket_anterior * 100) if ticket_anterior > 0 else 0

            col_a.metric("Valor Atual", formatar_moeda(val_atual), f"{var_val:+.1f}%")
            col_b.metric("Valor Anterior", formatar_moeda(val_anterior))
            col_c.metric("Qtd Atual", f"{qtd_atual}", f"{var_qtd:+.1f}%")
            col_d.metric("Ticket Medio", formatar_moeda(ticket_atual), f"{var_ticket:+.1f}%")
        else:
            st.info("Dados insuficientes para comparacao")

    st.divider()

    # ========== EVOLUCAO MENSAL ==========
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("###### Evolucao Mensal de Adiantamentos")

        df_evol = df_ad.copy()
        df_evol['MES'] = df_evol['EMISSAO'].dt.to_period('M').astype(str)

        df_mensal = df_evol.groupby('MES').agg({
            'VALOR_ORIGINAL': 'sum',
            'SALDO': 'sum',
            'NUMERO': 'count'
        }).reset_index()
        df_mensal.columns = ['MES', 'Adiantado', 'Saldo', 'Qtd']
        df_mensal = df_mensal.tail(12)

        if len(df_mensal) > 1:
            fig = go.Figure()

            fig.add_trace(go.Bar(
                x=df_mensal['MES'],
                y=df_mensal['Adiantado'],
                name='Adiantado',
                marker_color=cores['alerta']
            ))

            # Linha de tendencia
            if len(df_mensal) >= 3:
                x_num = list(range(len(df_mensal)))
                z = pd.Series(df_mensal['Adiantado']).rolling(3).mean()

                fig.add_trace(go.Scatter(
                    x=df_mensal['MES'],
                    y=z,
                    name='Media Movel 3m',
                    mode='lines',
                    line=dict(color=cores['texto'], width=2, dash='dot')
                ))

            fig.update_layout(
                criar_layout(280),
                margin=dict(l=10, r=10, t=10, b=50),
                xaxis=dict(tickangle=-45, tickfont=dict(size=9, color=cores['texto'])),
                yaxis=dict(showticklabels=False, showgrid=False),
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1,
                            font=dict(size=9))
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Historico insuficiente")

    with col2:
        st.markdown("###### Evolucao das Compensacoes")

        if len(df_bx) > 0 and 'DT_BAIXA' in df_bx.columns:
            df_bx_evol = df_bx.copy()
            df_bx_evol['MES'] = df_bx_evol['DT_BAIXA'].dt.to_period('M').astype(str)

            df_bx_mensal = df_bx_evol.groupby('MES').agg({
                'VALOR_BAIXA': 'sum',
                'DIF_DIAS_EMIS_BAIXA': 'mean'
            }).reset_index()
            df_bx_mensal.columns = ['MES', 'Compensado', 'Prazo_Medio']
            df_bx_mensal = df_bx_mensal.tail(12)

            if len(df_bx_mensal) > 1:
                fig = go.Figure()

                fig.add_trace(go.Bar(
                    x=df_bx_mensal['MES'],
                    y=df_bx_mensal['Compensado'],
                    name='Compensado',
                    marker_color=cores['sucesso']
                ))

                # Linha de prazo medio
                fig.add_trace(go.Scatter(
                    x=df_bx_mensal['MES'],
                    y=df_bx_mensal['Prazo_Medio'] * (df_bx_mensal['Compensado'].max() / df_bx_mensal['Prazo_Medio'].max()),
                    name='Prazo Medio (escala)',
                    mode='lines+markers',
                    line=dict(color=cores['info'], width=2),
                    yaxis='y2'
                ))

                fig.update_layout(
                    criar_layout(280),
                    margin=dict(l=10, r=40, t=10, b=50),
                    xaxis=dict(tickangle=-45, tickfont=dict(size=9, color=cores['texto'])),
                    yaxis=dict(showticklabels=False, showgrid=False),
                    yaxis2=dict(overlaying='y', side='right', showticklabels=False),
                    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1,
                                font=dict(size=9))
                )

                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Historico insuficiente")
        else:
            st.info("Sem dados de compensacao")

    st.divider()

    # ========== SAZONALIDADE ==========
    st.markdown("###### Sazonalidade - Padrao por Mes do Ano")

    df_sazon = df_ad.copy()
    df_sazon['MES_NUM'] = df_sazon['EMISSAO'].dt.month

    df_sazon_agg = df_sazon.groupby('MES_NUM')['VALOR_ORIGINAL'].mean().reset_index()
    df_sazon_agg['MES_NOME'] = df_sazon_agg['MES_NUM'].map({
        1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
        7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'
    })

    if len(df_sazon_agg) >= 6:
        media_geral = df_sazon_agg['VALOR_ORIGINAL'].mean()
        df_sazon_agg['DESVIO'] = ((df_sazon_agg['VALOR_ORIGINAL'] - media_geral) / media_geral * 100)

        def cor_sazon(d):
            if d > 20:
                return cores['perigo']
            elif d > 10:
                return cores['alerta']
            elif d < -20:
                return cores['info']
            elif d < -10:
                return cores['sucesso']
            return cores['texto_secundario']

        bar_colors = [cor_sazon(d) for d in df_sazon_agg['DESVIO']]

        col1, col2 = st.columns([3, 1])

        with col1:
            fig = go.Figure()

            fig.add_trace(go.Bar(
                x=df_sazon_agg['MES_NOME'],
                y=df_sazon_agg['VALOR_ORIGINAL'],
                marker_color=bar_colors,
                text=[f"{d:+.0f}%" for d in df_sazon_agg['DESVIO']],
                textposition='outside',
                textfont=dict(size=9, color=cores['texto'])
            ))

            fig.add_hline(y=media_geral, line_dash="dash", line_color=cores['texto'], line_width=1)

            fig.update_layout(
                criar_layout(280),
                margin=dict(l=10, r=10, t=30, b=10),
                xaxis=dict(tickfont=dict(size=10, color=cores['texto'])),
                yaxis=dict(showticklabels=False, showgrid=False)
            )

            st.plotly_chart(fig, use_container_width=True)

        with col2:
            meses_pico = df_sazon_agg[df_sazon_agg['DESVIO'] > 15]['MES_NOME'].tolist()
            meses_baixa = df_sazon_agg[df_sazon_agg['DESVIO'] < -15]['MES_NOME'].tolist()

            st.markdown(f"""
            <div style="background: {cores['card']}; border: 1px solid {cores['borda']};
                        border-radius: 8px; padding: 1rem;">
                <p style="color: {cores['texto']}; font-size: 0.8rem; font-weight: 600; margin: 0 0 0.5rem 0;">
                    Insights</p>
                <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0 0 0.5rem 0;">
                    Media mensal: {formatar_moeda(media_geral)}</p>
            """, unsafe_allow_html=True)

            if meses_pico:
                st.caption(f"📈 Picos: {', '.join(meses_pico)}")
            if meses_baixa:
                st.caption(f"📉 Baixas: {', '.join(meses_baixa)}")

            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Dados insuficientes para analise de sazonalidade")

    st.divider()

    # ========== TENDENCIA POR TIPO ==========
    st.markdown("###### Tendencia por Tipo de Adiantamento")

    if 'TIPO_ADTO' in df_ad.columns:
        df_tipo_evol = df_ad.copy()
        df_tipo_evol['MES'] = df_tipo_evol['EMISSAO'].dt.to_period('M').astype(str)

        df_pivot = df_tipo_evol.pivot_table(
            values='VALOR_ORIGINAL',
            index='MES',
            columns='TIPO_ADTO',
            aggfunc='sum',
            fill_value=0
        ).reset_index()

        df_pivot = df_pivot.tail(12)

        if len(df_pivot) > 1:
            fig = go.Figure()

            cores_tipo = [cores['primaria'], cores['sucesso'], cores['alerta'], cores['info'], cores['perigo']]
            tipos = [c for c in df_pivot.columns if c != 'MES']

            for i, tipo in enumerate(tipos):
                fig.add_trace(go.Scatter(
                    x=df_pivot['MES'],
                    y=df_pivot[tipo],
                    name=tipo,
                    mode='lines+markers',
                    line=dict(color=cores_tipo[i % len(cores_tipo)], width=2),
                    marker=dict(size=6)
                ))

            fig.update_layout(
                criar_layout(300),
                margin=dict(l=10, r=10, t=10, b=50),
                xaxis=dict(tickangle=-45, tickfont=dict(size=9, color=cores['texto'])),
                yaxis=dict(showticklabels=False, showgrid=True, gridcolor=cores['borda']),
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1,
                            font=dict(size=9)),
                hovermode='x unified'
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Historico insuficiente")
    else:
        st.info("Dados de tipo nao disponiveis")


def _render_alertas(df_ad, df_bx, cores, hoje):
    """Alertas e monitoramento de adiantamentos"""

    st.markdown("##### Alertas e Monitoramento")

    if len(df_ad) == 0:
        st.info("Nenhum dado disponivel.")
        return

    df_pend = df_ad[df_ad['SALDO'] > 0].copy()

    # Calcular dias pendente se nao existir
    if len(df_pend) > 0 and 'DIAS_PENDENTE' not in df_pend.columns:
        df_pend['DIAS_PENDENTE'] = (hoje - df_pend['EMISSAO']).dt.days

    # ========== RESUMO DE ALERTAS ==========
    alertas = []

    # 1. Adiantamentos muito antigos (>180 dias)
    if len(df_pend) > 0:
        df_antigo = df_pend[df_pend['DIAS_PENDENTE'] > 180]
        if len(df_antigo) > 0:
            alertas.append({
                'tipo': 'critico',
                'icone': '🚨',
                'titulo': 'Adiantamentos Antigos',
                'valor': formatar_moeda(df_antigo['SALDO'].sum()),
                'detalhe': f"{len(df_antigo)} titulos > 180 dias",
                'cor': cores['perigo']
            })

    # 2. Adiantamentos em alerta (91-180 dias)
    if len(df_pend) > 0:
        df_alerta = df_pend[(df_pend['DIAS_PENDENTE'] > 90) & (df_pend['DIAS_PENDENTE'] <= 180)]
        if len(df_alerta) > 0:
            alertas.append({
                'tipo': 'alerta',
                'icone': '⚠️',
                'titulo': 'Em Alerta',
                'valor': formatar_moeda(df_alerta['SALDO'].sum()),
                'detalhe': f"{len(df_alerta)} titulos 91-180 dias",
                'cor': cores['alerta']
            })

    # 3. Fornecedor com alto saldo
    if len(df_pend) > 0:
        forn_saldo = df_pend.groupby('NOME_FORNECEDOR')['SALDO'].sum()
        total_pend = df_pend['SALDO'].sum()
        if len(forn_saldo) > 0:
            maior_forn = forn_saldo.idxmax()
            maior_valor = forn_saldo.max()
            pct = maior_valor / total_pend * 100 if total_pend > 0 else 0
            if pct > 30:
                alertas.append({
                    'tipo': 'concentracao',
                    'icone': '📊',
                    'titulo': 'Concentracao',
                    'valor': f"{pct:.0f}%",
                    'detalhe': f"{maior_forn[:20]} concentra saldo",
                    'cor': cores['info']
                })

    # 4. Aumento de adiantamentos
    df_30d = df_ad[df_ad['EMISSAO'] >= hoje - timedelta(days=30)]
    df_60d = df_ad[(df_ad['EMISSAO'] >= hoje - timedelta(days=60)) & (df_ad['EMISSAO'] < hoje - timedelta(days=30))]
    if len(df_30d) > 0 and len(df_60d) > 0:
        val_30d = df_30d['VALOR_ORIGINAL'].sum()
        val_60d = df_60d['VALOR_ORIGINAL'].sum()
        if val_60d > 0:
            var = ((val_30d - val_60d) / val_60d) * 100
            if var > 30:
                alertas.append({
                    'tipo': 'tendencia',
                    'icone': '📈',
                    'titulo': 'Aumento Recente',
                    'valor': f"+{var:.0f}%",
                    'detalhe': 'vs mes anterior',
                    'cor': '#f97316'
                })

    # 5. Prazo de compensacao aumentando
    if len(df_bx) > 0 and 'DT_BAIXA' in df_bx.columns and 'DIF_DIAS_EMIS_BAIXA' in df_bx.columns:
        df_bx_30d = df_bx[df_bx['DT_BAIXA'] >= hoje - timedelta(days=30)]
        df_bx_60d = df_bx[(df_bx['DT_BAIXA'] >= hoje - timedelta(days=60)) & (df_bx['DT_BAIXA'] < hoje - timedelta(days=30))]

        prazo_30d = pd.to_numeric(df_bx_30d['DIF_DIAS_EMIS_BAIXA'], errors='coerce').mean() if len(df_bx_30d) > 0 else 0
        prazo_60d = pd.to_numeric(df_bx_60d['DIF_DIAS_EMIS_BAIXA'], errors='coerce').mean() if len(df_bx_60d) > 0 else 0

        if prazo_60d > 0 and prazo_30d > prazo_60d * 1.2:
            alertas.append({
                'tipo': 'prazo',
                'icone': '⏱️',
                'titulo': 'Prazo Aumentando',
                'valor': f"{prazo_30d:.0f}d",
                'detalhe': f'era {prazo_60d:.0f}d mes anterior',
                'cor': cores['alerta']
            })

    # Exibir alertas
    if len(alertas) > 0:
        cols = st.columns(min(len(alertas), 5))
        for i, alerta in enumerate(alertas[:5]):
            with cols[i]:
                st.markdown(f"""
                <div style="background: {cores['card']}; border: 2px solid {alerta['cor']};
                            border-radius: 10px; padding: 1rem; text-align: center; height: 100%;">
                    <p style="font-size: 1.5rem; margin: 0;">{alerta['icone']}</p>
                    <p style="color: {cores['texto']}; font-size: 0.8rem; font-weight: 600; margin: 0.3rem 0;">
                        {alerta['titulo']}</p>
                    <p style="color: {alerta['cor']}; font-size: 1.3rem; font-weight: 700; margin: 0;">
                        {alerta['valor']}</p>
                    <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0.3rem 0 0 0;">
                        {alerta['detalhe']}</p>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.success("Nenhum alerta no momento!")

    st.divider()

    # ========== FORNECEDORES EM ALERTA ==========
    st.markdown("###### Fornecedores que Requerem Atencao")

    if len(df_pend) > 0:
        # Agrupar por fornecedor com metricas
        df_forn_alert = df_pend.groupby('NOME_FORNECEDOR').agg({
            'SALDO': 'sum',
            'DIAS_PENDENTE': ['mean', 'max'],
            'NUMERO': 'count'
        }).reset_index()
        df_forn_alert.columns = ['Fornecedor', 'Saldo', 'Dias_Medio', 'Dias_Max', 'Qtd']

        # Score de risco (combinando valor e tempo)
        df_forn_alert['Score'] = (
            (df_forn_alert['Saldo'] / df_forn_alert['Saldo'].max()) * 50 +
            (df_forn_alert['Dias_Max'] / df_forn_alert['Dias_Max'].max()) * 50
        )

        df_forn_alert = df_forn_alert.sort_values('Score', ascending=False).head(10)

        col1, col2 = st.columns([2, 1])

        with col1:
            fig = go.Figure()

            # Cor baseada no score
            def cor_score(s):
                if s > 70:
                    return cores['perigo']
                elif s > 50:
                    return '#f97316'
                elif s > 30:
                    return cores['alerta']
                return cores['info']

            bar_colors = [cor_score(s) for s in df_forn_alert['Score']]

            fig.add_trace(go.Bar(
                y=df_forn_alert['Fornecedor'].str[:25],
                x=df_forn_alert['Score'],
                orientation='h',
                marker_color=bar_colors,
                text=[f"Score: {s:.0f}" for s in df_forn_alert['Score']],
                textposition='outside',
                textfont=dict(size=9, color=cores['texto'])
            ))

            fig.update_layout(
                criar_layout(300),
                margin=dict(l=10, r=60, t=10, b=10),
                xaxis=dict(title='Score de Risco', tickfont=dict(size=9, color=cores['texto']), range=[0, 110]),
                yaxis=dict(tickfont=dict(size=9, color=cores['texto']), autorange='reversed')
            )

            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("###### Legenda Score")
            st.markdown(f"""
            <div style="font-size: 0.75rem; color: {cores['texto_secundario']};">
                <p style="margin: 0.3rem 0;"><span style="color: {cores['perigo']};">●</span> > 70: Critico</p>
                <p style="margin: 0.3rem 0;"><span style="color: #f97316;">●</span> 50-70: Alto</p>
                <p style="margin: 0.3rem 0;"><span style="color: {cores['alerta']};">●</span> 30-50: Medio</p>
                <p style="margin: 0.3rem 0;"><span style="color: {cores['info']};">●</span> < 30: Baixo</p>
            </div>
            <p style="font-size: 0.65rem; color: {cores['texto_secundario']}; margin-top: 1rem;">
                Score = 50% valor + 50% tempo pendente
            </p>
            """, unsafe_allow_html=True)
    else:
        st.success("Nenhum fornecedor com pendencia!")

    st.divider()

    # ========== ADIANTAMENTOS SEM MOVIMENTO ==========
    st.markdown("###### Adiantamentos sem Movimento (Potencial Esquecimento)")

    if len(df_pend) > 0:
        # Adiantamentos antigos sem compensacao parcial
        df_esquecido = df_pend[
            (df_pend['DIAS_PENDENTE'] > 120) &
            (df_pend['SALDO'] == df_pend['VALOR_ORIGINAL'])
        ].copy()

        if len(df_esquecido) > 0:
            df_esquecido = df_esquecido.sort_values('DIAS_PENDENTE', ascending=False).head(20)

            colunas = ['NOME_FILIAL', 'NOME_FORNECEDOR', 'DESCRICAO', 'EMISSAO', 'DIAS_PENDENTE', 'SALDO']
            colunas_disp = [c for c in colunas if c in df_esquecido.columns]
            df_show = df_esquecido[colunas_disp].copy()

            if 'EMISSAO' in df_show.columns:
                df_show['EMISSAO'] = pd.to_datetime(df_show['EMISSAO'], errors='coerce').dt.strftime('%d/%m/%Y')

            df_show['SALDO'] = df_show['SALDO'].apply(lambda x: formatar_moeda(x, completo=True))
            df_show['DIAS_PENDENTE'] = df_show['DIAS_PENDENTE'].apply(lambda x: f"{int(x)} dias")

            nomes = {
                'NOME_FILIAL': 'Filial',
                'NOME_FORNECEDOR': 'Fornecedor',
                'DESCRICAO': 'Tipo',
                'EMISSAO': 'Emissao',
                'DIAS_PENDENTE': 'Tempo Pend.',
                'SALDO': 'Valor'
            }
            df_show.columns = [nomes.get(c, c) for c in df_show.columns]

            st.dataframe(df_show, use_container_width=True, hide_index=True, height=300)
            st.caption(f"⚠️ {len(df_esquecido)} adiantamentos > 120 dias sem nenhuma compensacao")
        else:
            st.success("Nenhum adiantamento potencialmente esquecido!")
    else:
        st.info("Sem dados")

    st.divider()

    # ========== ACOES RECOMENDADAS ==========
    st.markdown("###### Acoes Recomendadas")

    acoes = []

    if len(df_pend) > 0:
        # Acao 1: Adiantamentos criticos
        df_crit = df_pend[df_pend['DIAS_PENDENTE'] > 180]
        if len(df_crit) > 0:
            acoes.append({
                'prioridade': 'Alta',
                'acao': f"Cobrar prestacao de contas de {len(df_crit)} adiantamentos > 180 dias",
                'valor': formatar_moeda(df_crit['SALDO'].sum()),
                'cor': cores['perigo']
            })

        # Acao 2: Fornecedores concentrados
        forn_saldo = df_pend.groupby('NOME_FORNECEDOR')['SALDO'].sum()
        total = df_pend['SALDO'].sum()
        for forn, valor in forn_saldo.nlargest(3).items():
            pct = valor / total * 100 if total > 0 else 0
            if pct > 25:
                acoes.append({
                    'prioridade': 'Media',
                    'acao': f"Revisar adiantamentos de {forn[:25]}",
                    'valor': f"{pct:.0f}% do saldo total",
                    'cor': cores['alerta']
                })

        # Acao 3: Tendencia de aumento
        if val_30d > val_60d * 1.3 if 'val_30d' in dir() and 'val_60d' in dir() else False:
            acoes.append({
                'prioridade': 'Media',
                'acao': "Analisar motivo do aumento de adiantamentos",
                'valor': "Tendencia de alta",
                'cor': cores['info']
            })

    if len(acoes) > 0:
        for acao in acoes[:5]:
            st.markdown(f"""
            <div style="background: {cores['card']}; border-left: 4px solid {acao['cor']};
                        border-radius: 0 8px 8px 0; padding: 0.75rem; margin-bottom: 0.5rem;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span style="background: {acao['cor']}; color: white; padding: 0.2rem 0.5rem;
                                    border-radius: 4px; font-size: 0.65rem; font-weight: 600;">
                            {acao['prioridade']}</span>
                        <span style="color: {cores['texto']}; font-size: 0.85rem; margin-left: 0.5rem;">
                            {acao['acao']}</span>
                    </div>
                    <span style="color: {cores['texto_secundario']}; font-size: 0.75rem;">
                        {acao['valor']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("Nenhuma acao urgente necessaria!")
