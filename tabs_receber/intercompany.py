"""
Tab Intercompany - Contas a Receber
Analise completa de operacoes entre empresas do grupo
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

from config.theme import get_cores
from config.settings import INTERCOMPANY_PATTERNS, INTERCOMPANY_TIPOS, INTERCOMPANY_PADRONIZACAO
from utils.formatters import formatar_moeda, formatar_numero


def padronizar_nome_ic(nome):
    """Padroniza o nome para comparação"""
    if pd.isna(nome):
        return nome
    nome_limpo = str(nome).strip().upper()
    for variacao, padrao in INTERCOMPANY_PADRONIZACAO.items():
        if variacao.upper() in nome_limpo:
            return padrao
    return nome


def identificar_intercompany(df):
    """Identifica titulos intercompany baseado no nome do cliente"""
    mask = df['NOME_CLIENTE'].str.upper().str.contains(
        '|'.join(INTERCOMPANY_PATTERNS), na=False, regex=True
    )
    return df[mask].copy(), df[~mask].copy()


def classificar_tipo_intercompany(nome):
    """Classifica o tipo de operacao intercompany"""
    nome_padrao = padronizar_nome_ic(nome)
    if nome_padrao in INTERCOMPANY_TIPOS:
        return INTERCOMPANY_TIPOS[nome_padrao]
    # Fallback para busca parcial
    nome_upper = str(nome).upper()
    for padrao, tipo in INTERCOMPANY_TIPOS.items():
        if padrao in nome_upper:
            return tipo
    return 'Outros'


def render_intercompany_receber(df):
    """Renderiza a aba de analise intercompany"""
    cores = get_cores()
    hoje = datetime.now()

    # Separar intercompany de terceiros
    df_inter, df_terceiros = identificar_intercompany(df)

    if len(df_inter) == 0:
        st.info("Nenhuma operacao intercompany encontrada no periodo selecionado.")
        return

    # Classificar tipo de intercompany
    df_inter['TIPO_IC'] = df_inter['NOME_CLIENTE'].apply(classificar_tipo_intercompany)

    # Calcular metricas
    total_geral = df['SALDO'].sum()
    total_inter = df_inter['SALDO'].sum()
    total_terceiros = df_terceiros['SALDO'].sum()
    pct_inter = (total_inter / total_geral * 100) if total_geral > 0 else 0

    # Separar vencidos
    df_inter_vencido = df_inter[(df_inter['SALDO'] > 0) & (df_inter['DIAS_VENC'] < 0)]
    df_inter_a_vencer = df_inter[(df_inter['SALDO'] > 0) & (df_inter['DIAS_VENC'] >= 0)]

    saldo_vencido = df_inter_vencido['SALDO'].sum()
    saldo_a_vencer = df_inter_a_vencer['SALDO'].sum()
    pct_vencido = (saldo_vencido / total_inter * 100) if total_inter > 0 else 0

    # Dias medio de atraso
    dias_medio_atraso = df_inter_vencido['DIAS_VENC'].abs().mean() if len(df_inter_vencido) > 0 else 0

    # Taxa de recuperacao (recebido / total original)
    valor_original_inter = df_inter['VALOR_ORIGINAL'].sum()
    valor_recebido = valor_original_inter - total_inter
    taxa_recuperacao = (valor_recebido / valor_original_inter * 100) if valor_original_inter > 0 else 0

    # ========== HEADER COM ALERTAS ==========
    if pct_vencido > 80:
        cor_alerta = cores['perigo']
        msg_alerta = "CRITICO: Maioria do saldo esta vencido!"
    elif pct_vencido > 50:
        cor_alerta = cores['alerta']
        msg_alerta = "ATENCAO: Alto percentual vencido"
    else:
        cor_alerta = cores['sucesso']
        msg_alerta = "Situacao sob controle"

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, {cor_alerta}20, {cores['card']});
                border: 2px solid {cor_alerta}; border-radius: 12px;
                padding: 1rem; margin-bottom: 1rem;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <p style="color: {cor_alerta}; font-size: 0.9rem; font-weight: 600; margin: 0;">
                    {msg_alerta}</p>
                <p style="color: {cores['texto']}; font-size: 1.8rem; font-weight: 700; margin: 0;">
                    {formatar_moeda(saldo_vencido)} vencido</p>
                <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0;">
                    de {formatar_moeda(total_inter)} total intercompany ({pct_vencido:.0f}%)</p>
            </div>
            <div style="text-align: right;">
                <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0;">Dias medio atraso</p>
                <p style="color: {cor_alerta}; font-size: 2rem; font-weight: 700; margin: 0;">
                    {dias_medio_atraso:.0f}</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ========== KPIs PRINCIPAIS ==========
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['borda']};
                    border-radius: 8px; padding: 0.8rem; text-align: center;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">Saldo Intercompany</p>
            <p style="color: {cores['primaria']}; font-size: 1.3rem; font-weight: 700; margin: 0.2rem 0;">
                {formatar_moeda(total_inter)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">
                {pct_inter:.1f}% do total a receber</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['perigo']};
                    border-radius: 8px; padding: 0.8rem; text-align: center;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">Vencido</p>
            <p style="color: {cores['perigo']}; font-size: 1.3rem; font-weight: 700; margin: 0.2rem 0;">
                {formatar_moeda(saldo_vencido)}</p>
            <p style="color: {cores['perigo']}; font-size: 0.7rem; margin: 0;">
                {len(df_inter_vencido)} titulos</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['sucesso']};
                    border-radius: 8px; padding: 0.8rem; text-align: center;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">A Vencer</p>
            <p style="color: {cores['sucesso']}; font-size: 1.3rem; font-weight: 700; margin: 0.2rem 0;">
                {formatar_moeda(saldo_a_vencer)}</p>
            <p style="color: {cores['sucesso']}; font-size: 0.7rem; margin: 0;">
                {len(df_inter_a_vencer)} titulos</p>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['borda']};
                    border-radius: 8px; padding: 0.8rem; text-align: center;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">Taxa Recuperacao</p>
            <p style="color: {cores['info']}; font-size: 1.3rem; font-weight: 700; margin: 0.2rem 0;">
                {taxa_recuperacao:.1f}%</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">
                {formatar_moeda(valor_recebido)} recebido</p>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['borda']};
                    border-radius: 8px; padding: 0.8rem; text-align: center;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">Titulos</p>
            <p style="color: {cores['texto']}; font-size: 1.3rem; font-weight: 700; margin: 0.2rem 0;">
                {formatar_numero(len(df_inter))}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">
                {formatar_numero(len(df_inter[df_inter['SALDO'] > 0]))} pendentes</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ========== TABS DE ANALISE ==========
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Devedores",
        "📂 Categorias",
        "⏰ Aging Detalhado",
        "🔄 Fluxo Intercompany",
        "📋 Detalhes"
    ])

    # ========== TAB 1: DEVEDORES ==========
    with tab1:
        _render_analise_devedores(df_inter, cores)

    # ========== TAB 2: CATEGORIAS ==========
    with tab2:
        _render_analise_categorias(df_inter, cores)

    # ========== TAB 3: AGING DETALHADO ==========
    with tab3:
        _render_aging_detalhado(df_inter, cores)

    # ========== TAB 4: FLUXO ==========
    with tab4:
        _render_fluxo_intercompany(df_inter, cores)

    # ========== TAB 5: DETALHES ==========
    with tab5:
        _render_detalhes(df_inter, cores)


def _render_analise_devedores(df_inter, cores):
    """Analise detalhada dos devedores intercompany"""

    st.markdown(f"<p style='color: {cores['texto']}; font-weight: 600; font-size: 1rem;'>Concentracao de Risco por Devedor</p>", unsafe_allow_html=True)

    # Agrupar por cliente
    df_clientes = df_inter.groupby(['NOME_CLIENTE', 'TIPO_IC']).agg({
        'SALDO': 'sum',
        'VALOR_ORIGINAL': 'sum',
        'NUMERO': 'count',
        'DIAS_VENC': 'min'  # Pior situacao
    }).reset_index()
    df_clientes.columns = ['Cliente', 'Tipo', 'Saldo', 'Original', 'Qtd', 'Dias_Venc']
    df_clientes['Recebido'] = df_clientes['Original'] - df_clientes['Saldo']
    df_clientes['Pct_Recebido'] = (df_clientes['Recebido'] / df_clientes['Original'] * 100).round(1)
    df_clientes = df_clientes.sort_values('Saldo', ascending=False)

    total_saldo = df_clientes['Saldo'].sum()
    df_clientes['Pct_Total'] = (df_clientes['Saldo'] / total_saldo * 100).round(1)
    df_clientes['Pct_Acum'] = df_clientes['Pct_Total'].cumsum()

    col1, col2 = st.columns([3, 2])

    with col1:
        # Grafico de barras horizontais
        df_top = df_clientes.head(10)

        cores_tipo = {
            'Empresas Progresso': cores['primaria'],
            'Ouro Branco': cores['sucesso'],
            'Fazenda Peninsula': '#84cc16',
            'Hotelaria': cores['info'],
            'Outros': cores['texto_secundario']
        }

        fig = go.Figure()

        # Saldo vencido vs a vencer por cliente
        for _, row in df_top.iterrows():
            vencido = df_inter[(df_inter['NOME_CLIENTE'] == row['Cliente']) & (df_inter['DIAS_VENC'] < 0)]['SALDO'].sum()
            a_vencer = row['Saldo'] - vencido

            fig.add_trace(go.Bar(
                y=[row['Cliente'][:25]],
                x=[vencido],
                name='Vencido',
                orientation='h',
                marker_color=cores['perigo'],
                showlegend=False,
                text=formatar_moeda(vencido) if vencido > 0 else '',
                textposition='inside',
                textfont=dict(size=9, color='white')
            ))

            fig.add_trace(go.Bar(
                y=[row['Cliente'][:25]],
                x=[a_vencer],
                name='A Vencer',
                orientation='h',
                marker_color=cores['sucesso'],
                showlegend=False,
                text=formatar_moeda(a_vencer) if a_vencer > 0 else '',
                textposition='inside',
                textfont=dict(size=9, color='white')
            ))

        fig.update_layout(
            barmode='stack',
            height=400,
            margin=dict(l=10, r=10, t=30, b=10),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=True, gridcolor=cores['borda'], showticklabels=False),
            yaxis=dict(tickfont=dict(color=cores['texto'], size=9), autorange='reversed'),
            legend=dict(orientation='h', y=1.1)
        )

        st.plotly_chart(fig, use_container_width=True)

        # Legenda
        st.markdown(f"""
        <div style="display: flex; gap: 1rem; justify-content: center; margin-top: -1rem;">
            <span style="color: {cores['perigo']}; font-size: 0.8rem;">● Vencido</span>
            <span style="color: {cores['sucesso']}; font-size: 0.8rem;">● A Vencer</span>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        # Indicador de concentracao
        top3_pct = df_clientes.head(3)['Pct_Total'].sum()

        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['borda']};
                    border-radius: 10px; padding: 1rem; margin-bottom: 1rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0;">Concentracao Top 3</p>
            <p style="color: {cores['alerta'] if top3_pct > 70 else cores['sucesso']}; font-size: 2rem; font-weight: 700; margin: 0;">
                {top3_pct:.1f}%</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">
                {"Alta concentracao de risco" if top3_pct > 70 else "Risco diversificado"}</p>
        </div>
        """, unsafe_allow_html=True)

        # Cards dos top 3 devedores
        for i, row in df_clientes.head(3).iterrows():
            cor_borda = cores['perigo'] if row['Dias_Venc'] < 0 else cores['sucesso']
            status = "Vencido" if row['Dias_Venc'] < 0 else "Em dia"

            st.markdown(f"""
            <div style="background: {cores['card']}; border-left: 4px solid {cor_borda};
                        border-radius: 8px; padding: 0.8rem; margin-bottom: 0.5rem;">
                <p style="color: {cores['texto']}; font-size: 0.85rem; font-weight: 600; margin: 0;
                          overflow: hidden; text-overflow: ellipsis; white-space: nowrap;"
                   title="{row['Cliente']}">{row['Cliente'][:22]}...</p>
                <p style="color: {cor_borda}; font-size: 1.1rem; font-weight: 700; margin: 0.2rem 0;">
                    {formatar_moeda(row['Saldo'])}</p>
                <div style="display: flex; justify-content: space-between;">
                    <span style="color: {cores['texto_secundario']}; font-size: 0.7rem;">
                        {row['Pct_Total']:.1f}% do total</span>
                    <span style="color: {cor_borda}; font-size: 0.7rem;">{status}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Tabela completa
    st.markdown(f"<p style='color: {cores['texto']}; font-weight: 600; margin-top: 1rem;'>Tabela Completa de Devedores</p>", unsafe_allow_html=True)

    df_exib = df_clientes[['Cliente', 'Tipo', 'Saldo', 'Original', 'Pct_Recebido', 'Qtd', 'Pct_Total']].copy()
    df_exib['Saldo'] = df_exib['Saldo'].apply(lambda x: formatar_moeda(x, completo=True))
    df_exib['Original'] = df_exib['Original'].apply(lambda x: formatar_moeda(x, completo=True))

    st.dataframe(
        df_exib,
        use_container_width=True,
        hide_index=True,
        height=300,
        column_config={
            'Pct_Recebido': st.column_config.ProgressColumn(
                '% Recebido',
                format='%.0f%%',
                min_value=0,
                max_value=100
            ),
            'Pct_Total': st.column_config.NumberColumn('% do Total', format='%.1f%%')
        }
    )


def _render_analise_categorias(df_inter, cores):
    """Analise por categoria/natureza das operacoes"""

    st.markdown(f"<p style='color: {cores['texto']}; font-weight: 600; font-size: 1rem;'>Composicao por Categoria</p>", unsafe_allow_html=True)

    # Agrupar por descricao
    df_cat = df_inter.groupby('DESCRICAO').agg({
        'SALDO': 'sum',
        'VALOR_ORIGINAL': 'sum',
        'NUMERO': 'count',
        'DIAS_VENC': lambda x: (x < 0).sum()  # Qtd vencidos
    }).reset_index()
    df_cat.columns = ['Categoria', 'Saldo', 'Original', 'Qtd', 'Qtd_Vencidos']
    df_cat = df_cat[df_cat['Saldo'] > 0].sort_values('Saldo', ascending=False)
    df_cat['Pct'] = (df_cat['Saldo'] / df_cat['Saldo'].sum() * 100).round(1)

    col1, col2 = st.columns([2, 1])

    with col1:
        # Grafico de pizza/donut
        fig = go.Figure(data=[go.Pie(
            labels=df_cat['Categoria'].head(8),
            values=df_cat['Saldo'].head(8),
            hole=0.5,
            marker_colors=[cores['primaria'], cores['sucesso'], cores['info'],
                          cores['alerta'], '#84cc16', '#8b5cf6', '#ec4899', cores['texto_secundario']],
            textinfo='percent',
            textfont_size=11,
            textfont_color='white',
            hovertemplate='%{label}<br>%{value:,.0f}<br>%{percent}<extra></extra>'
        )])

        fig.update_layout(
            height=350,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            showlegend=True,
            legend=dict(
                orientation='v',
                yanchor='middle',
                y=0.5,
                xanchor='left',
                x=1.05,
                font=dict(color=cores['texto'], size=9)
            )
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Cards das principais categorias
        for _, row in df_cat.head(5).iterrows():
            pct_vencido = (row['Qtd_Vencidos'] / row['Qtd'] * 100) if row['Qtd'] > 0 else 0
            cor = cores['perigo'] if pct_vencido > 50 else cores['sucesso']

            st.markdown(f"""
            <div style="background: {cores['card']}; border: 1px solid {cores['borda']};
                        border-radius: 8px; padding: 0.6rem; margin-bottom: 0.4rem;">
                <p style="color: {cores['texto']}; font-size: 0.75rem; font-weight: 500; margin: 0;
                          overflow: hidden; text-overflow: ellipsis; white-space: nowrap;"
                   title="{row['Categoria']}">{row['Categoria'][:28]}</p>
                <p style="color: {cores['primaria']}; font-size: 1rem; font-weight: 700; margin: 0.2rem 0;">
                    {formatar_moeda(row['Saldo'])}</p>
                <p style="color: {cor}; font-size: 0.65rem; margin: 0;">
                    {pct_vencido:.0f}% vencido | {row['Qtd']} titulos</p>
            </div>
            """, unsafe_allow_html=True)

    # Analise por tipo de documento
    st.markdown(f"<p style='color: {cores['texto']}; font-weight: 600; margin-top: 1rem;'>Por Tipo de Documento</p>", unsafe_allow_html=True)

    df_tipo = df_inter.groupby('TIPO').agg({
        'SALDO': 'sum',
        'NUMERO': 'count'
    }).reset_index()
    df_tipo = df_tipo[df_tipo['SALDO'] > 0].sort_values('SALDO', ascending=False)

    cols = st.columns(len(df_tipo.head(5)))
    for i, (_, row) in enumerate(df_tipo.head(5).iterrows()):
        with cols[i]:
            st.metric(
                row['TIPO'],
                formatar_moeda(row['SALDO']),
                f"{row['NUMERO']} titulos"
            )


def _render_aging_detalhado(df_inter, cores):
    """Aging detalhado com faixas de vencimento"""

    st.markdown(f"<p style='color: {cores['texto']}; font-weight: 600; font-size: 1rem;'>Aging Detalhado - Faixas de Vencimento</p>", unsafe_allow_html=True)

    df_pendente = df_inter[df_inter['SALDO'] > 0].copy()

    if len(df_pendente) == 0:
        st.info("Nenhum titulo pendente encontrado.")
        return

    # Classificar aging com faixas detalhadas
    def classificar_aging_detalhado(dias):
        if pd.isna(dias):
            return '99_Sem data'
        elif dias >= 30:
            return '01_Vence +30 dias'
        elif dias >= 15:
            return '02_Vence 15-30 dias'
        elif dias >= 7:
            return '03_Vence 7-15 dias'
        elif dias >= 0:
            return '04_Vence 0-7 dias'
        elif dias >= -30:
            return '05_Vencido 1-30 dias'
        elif dias >= -60:
            return '06_Vencido 31-60 dias'
        elif dias >= -90:
            return '07_Vencido 61-90 dias'
        elif dias >= -180:
            return '08_Vencido 91-180 dias'
        else:
            return '09_Vencido +180 dias'

    df_pendente['FAIXA_AGING'] = df_pendente['DIAS_VENC'].apply(classificar_aging_detalhado)

    # Agrupar
    aging = df_pendente.groupby('FAIXA_AGING').agg({
        'SALDO': 'sum',
        'NUMERO': 'count'
    }).reset_index()
    aging = aging.sort_values('FAIXA_AGING')
    aging['LABEL'] = aging['FAIXA_AGING'].str[3:]  # Remove prefixo de ordenacao

    # Definir cores
    cores_faixas = {
        'Vence +30 dias': cores['sucesso'],
        'Vence 15-30 dias': '#4ade80',
        'Vence 7-15 dias': '#a3e635',
        'Vence 0-7 dias': cores['alerta'],
        'Vencido 1-30 dias': '#fb923c',
        'Vencido 31-60 dias': '#f97316',
        'Vencido 61-90 dias': '#ef4444',
        'Vencido 91-180 dias': '#dc2626',
        'Vencido +180 dias': '#991b1b',
        'Sem data': cores['texto_secundario']
    }

    col1, col2 = st.columns([3, 1])

    with col1:
        # Grafico de barras
        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=aging['LABEL'],
            y=aging['SALDO'],
            marker_color=[cores_faixas.get(l, cores['info']) for l in aging['LABEL']],
            text=[formatar_moeda(v) for v in aging['SALDO']],
            textposition='outside',
            textfont=dict(size=9, color=cores['texto'])
        ))

        fig.update_layout(
            height=350,
            margin=dict(l=10, r=10, t=10, b=80),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(tickfont=dict(color=cores['texto'], size=9), tickangle=-45, showgrid=False),
            yaxis=dict(showticklabels=False, showgrid=False)
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Resumo do aging
        total_vencido = df_pendente[df_pendente['DIAS_VENC'] < 0]['SALDO'].sum()
        total_a_vencer = df_pendente[df_pendente['DIAS_VENC'] >= 0]['SALDO'].sum()
        total_critico = df_pendente[df_pendente['DIAS_VENC'] < -90]['SALDO'].sum()

        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['perigo']};
                    border-radius: 10px; padding: 1rem; margin-bottom: 0.5rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0;">Total Vencido</p>
            <p style="color: {cores['perigo']}; font-size: 1.5rem; font-weight: 700; margin: 0;">
                {formatar_moeda(total_vencido)}</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['sucesso']};
                    border-radius: 10px; padding: 1rem; margin-bottom: 0.5rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0;">A Vencer</p>
            <p style="color: {cores['sucesso']}; font-size: 1.5rem; font-weight: 700; margin: 0;">
                {formatar_moeda(total_a_vencer)}</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid #991b1b;
                    border-radius: 10px; padding: 1rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0;">Critico (+90 dias)</p>
            <p style="color: #991b1b; font-size: 1.5rem; font-weight: 700; margin: 0;">
                {formatar_moeda(total_critico)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.65rem; margin: 0;">
                {(total_critico/total_vencido*100):.0f}% do vencido</p>
        </div>
        """, unsafe_allow_html=True)

    # Aging por cliente (top vencidos)
    st.markdown(f"<p style='color: {cores['texto']}; font-weight: 600; margin-top: 1rem;'>Maiores Valores Vencidos por Cliente</p>", unsafe_allow_html=True)

    df_vencidos_cliente = df_pendente[df_pendente['DIAS_VENC'] < 0].groupby('NOME_CLIENTE').agg({
        'SALDO': 'sum',
        'DIAS_VENC': 'min'
    }).reset_index()
    df_vencidos_cliente['DIAS_ATRASO'] = df_vencidos_cliente['DIAS_VENC'].abs()
    df_vencidos_cliente = df_vencidos_cliente.sort_values('SALDO', ascending=False).head(10)

    fig2 = go.Figure()

    fig2.add_trace(go.Bar(
        y=df_vencidos_cliente['NOME_CLIENTE'].str[:25],
        x=df_vencidos_cliente['SALDO'],
        orientation='h',
        marker_color=[
            '#991b1b' if d > 180 else '#dc2626' if d > 90 else '#f97316' if d > 30 else cores['alerta']
            for d in df_vencidos_cliente['DIAS_ATRASO']
        ],
        text=[f"{formatar_moeda(v)} ({d:.0f}d)" for v, d in zip(df_vencidos_cliente['SALDO'], df_vencidos_cliente['DIAS_ATRASO'])],
        textposition='outside',
        textfont=dict(size=9, color=cores['texto'])
    ))

    fig2.update_layout(
        height=350,
        margin=dict(l=10, r=120, t=10, b=10),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False, showticklabels=False),
        yaxis=dict(tickfont=dict(color=cores['texto'], size=9), autorange='reversed')
    )

    st.plotly_chart(fig2, use_container_width=True)


def _render_fluxo_intercompany(df_inter, cores):
    """Fluxo de relacionamento intercompany"""

    st.markdown(f"<p style='color: {cores['texto']}; font-weight: 600; font-size: 1rem;'>Fluxo de Divida Intercompany</p>", unsafe_allow_html=True)
    st.markdown(f"<p style='color: {cores['texto_secundario']}; font-size: 0.8rem;'>Quem deve para quem (Filial Credora → Cliente Devedor)</p>", unsafe_allow_html=True)

    df_pendente = df_inter[df_inter['SALDO'] > 0].copy()

    if len(df_pendente) == 0:
        st.info("Nenhum saldo pendente.")
        return

    # Matriz pivot
    matriz = df_pendente.pivot_table(
        index='NOME_FILIAL',
        columns='NOME_CLIENTE',
        values='SALDO',
        aggfunc='sum',
        fill_value=0
    )

    # Filtrar top filiais e clientes
    top_filiais = df_pendente.groupby('NOME_FILIAL')['SALDO'].sum().nlargest(8).index
    top_clientes = df_pendente.groupby('NOME_CLIENTE')['SALDO'].sum().nlargest(6).index

    matriz_filtrada = matriz.loc[matriz.index.isin(top_filiais), matriz.columns.isin(top_clientes)]

    if matriz_filtrada.empty:
        st.warning("Dados insuficientes para matriz.")
        return

    # Abreviar nomes
    matriz_filtrada.index = [f[:20] + '...' if len(f) > 20 else f for f in matriz_filtrada.index]
    matriz_filtrada.columns = [f[:15] + '...' if len(f) > 15 else f for f in matriz_filtrada.columns]

    # Heatmap
    fig = go.Figure(data=go.Heatmap(
        z=matriz_filtrada.values / 1e6,
        x=matriz_filtrada.columns,
        y=matriz_filtrada.index,
        colorscale=[
            [0, cores['fundo']],
            [0.3, 'rgba(34, 197, 94, 0.4)'],
            [0.6, 'rgba(234, 179, 8, 0.6)'],
            [1, cores['perigo']]
        ],
        text=[[f'R$ {v/1e6:.1f}M' if v > 100000 else '' for v in row] for row in matriz_filtrada.values],
        texttemplate='%{text}',
        textfont=dict(size=9, color='white'),
        hovertemplate='%{y} recebe de %{x}<br>Valor: R$ %{z:.2f}M<extra></extra>',
        colorbar=dict(
            title=dict(text='Milhões', font=dict(color=cores['texto'], size=10)),
            tickfont=dict(color=cores['texto'], size=9)
        )
    ))

    fig.update_layout(
        height=400,
        margin=dict(l=10, r=10, t=10, b=80),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(tickfont=dict(color=cores['texto'], size=9), tickangle=-45),
        yaxis=dict(tickfont=dict(color=cores['texto'], size=9))
    )

    st.plotly_chart(fig, use_container_width=True)

    # Resumo por tipo de operacao
    st.markdown(f"<p style='color: {cores['texto']}; font-weight: 600; margin-top: 1rem;'>Por Tipo de Empresa</p>", unsafe_allow_html=True)

    df_tipo = df_pendente.groupby('TIPO_IC').agg({
        'SALDO': 'sum',
        'NUMERO': 'count'
    }).reset_index()
    df_tipo = df_tipo.sort_values('SALDO', ascending=False)

    cores_tipo = {
        'Empresas Progresso': cores['primaria'],
        'Ouro Branco': cores['sucesso'],
        'Fazenda Peninsula': '#84cc16',
        'Hotelaria': cores['info'],
        'Outros': cores['texto_secundario']
    }

    cols = st.columns(len(df_tipo))
    for i, row in df_tipo.iterrows():
        with cols[i]:
            cor = cores_tipo.get(row['TIPO_IC'], cores['info'])
            st.markdown(f"""
            <div style="background: {cores['card']}; border-left: 4px solid {cor};
                        border-radius: 8px; padding: 0.8rem; text-align: center;">
                <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">{row['TIPO_IC']}</p>
                <p style="color: {cor}; font-size: 1.2rem; font-weight: 700; margin: 0.2rem 0;">
                    {formatar_moeda(row['SALDO'])}</p>
                <p style="color: {cores['texto_secundario']}; font-size: 0.65rem; margin: 0;">
                    {row['NUMERO']} titulos</p>
            </div>
            """, unsafe_allow_html=True)


def _render_detalhes(df_inter, cores):
    """Tabela detalhada com filtros"""

    st.markdown(f"<p style='color: {cores['texto']}; font-weight: 600; font-size: 1rem;'>Detalhes dos Titulos</p>", unsafe_allow_html=True)

    # Filtros
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        clientes = ['Todos'] + sorted(df_inter['NOME_CLIENTE'].unique().tolist())
        filtro_cliente = st.selectbox("Cliente", clientes, key="ic_rec_cliente")

    with col2:
        filiais = ['Todas'] + sorted(df_inter['NOME_FILIAL'].dropna().unique().tolist())
        filtro_filial = st.selectbox("Filial", filiais, key="ic_rec_filial")

    with col3:
        status_opcoes = ['Todos', 'Pendente', 'Vencido', 'Recebido']
        filtro_status = st.selectbox("Status", status_opcoes, key="ic_rec_status")

    with col4:
        ordem = st.selectbox("Ordenar", ["Maior Saldo", "Mais Vencido", "Mais Recente"], key="ic_rec_ordem")

    # Aplicar filtros
    df_show = df_inter.copy()

    if filtro_cliente != 'Todos':
        df_show = df_show[df_show['NOME_CLIENTE'] == filtro_cliente]

    if filtro_filial != 'Todas':
        df_show = df_show[df_show['NOME_FILIAL'] == filtro_filial]

    if filtro_status == 'Pendente':
        df_show = df_show[df_show['SALDO'] > 0]
    elif filtro_status == 'Vencido':
        df_show = df_show[(df_show['SALDO'] > 0) & (df_show['DIAS_VENC'] < 0)]
    elif filtro_status == 'Recebido':
        df_show = df_show[df_show['SALDO'] == 0]

    # Ordenar
    if ordem == "Maior Saldo":
        df_show = df_show.sort_values('SALDO', ascending=False)
    elif ordem == "Mais Vencido":
        df_show = df_show.sort_values('DIAS_VENC', ascending=True)
    else:
        df_show = df_show.sort_values('EMISSAO', ascending=False)

    # Metricas do filtro
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Titulos", formatar_numero(len(df_show)))
    col2.metric("Valor Original", formatar_moeda(df_show['VALOR_ORIGINAL'].sum()))
    col3.metric("Saldo", formatar_moeda(df_show['SALDO'].sum()))
    vencidos = len(df_show[(df_show['SALDO'] > 0) & (df_show['DIAS_VENC'] < 0)])
    col4.metric("Vencidos", formatar_numero(vencidos))

    st.markdown("---")

    # Tabela
    df_exib = df_show[[
        'NOME_FILIAL', 'NOME_CLIENTE', 'TIPO', 'NUMERO', 'DESCRICAO',
        'EMISSAO', 'VENCIMENTO', 'VALOR_ORIGINAL', 'SALDO', 'STATUS'
    ]].head(100).copy()

    df_exib['EMISSAO'] = pd.to_datetime(df_exib['EMISSAO']).dt.strftime('%d/%m/%Y')
    df_exib['VENCIMENTO'] = pd.to_datetime(df_exib['VENCIMENTO']).dt.strftime('%d/%m/%Y')
    df_exib['VALOR_ORIGINAL'] = df_exib['VALOR_ORIGINAL'].apply(lambda x: f"R$ {x:,.2f}")
    df_exib['SALDO'] = df_exib['SALDO'].apply(lambda x: f"R$ {x:,.2f}")

    df_exib.columns = ['Filial', 'Cliente', 'Tipo', 'Numero', 'Categoria',
                       'Emissao', 'Vencimento', 'Valor', 'Saldo', 'Status']

    st.dataframe(df_exib, use_container_width=True, hide_index=True, height=450)
    st.caption(f"Exibindo {len(df_exib)} de {len(df_show)} registros")
