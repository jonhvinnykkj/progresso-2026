"""
Aba Fornecedores - Contas a Pagar por Fornecedor
Foco em valores pagos e pendentes, não em vencimentos
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

from config.theme import get_cores
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero
from config.settings import GRUPOS_FILIAIS, get_grupo_filial


def render_fornecedores(df):
    """Renderiza a aba de Fornecedores - Contas a Pagar"""
    cores = get_cores()

    if len(df) == 0:
        st.warning("Nenhum dado disponivel.")
        return

    # ========== ALERTAS E INSIGHTS ==========
    _render_alertas(df, cores)

    st.divider()

    # ========== KPIs ==========
    _render_kpis(df, cores)

    st.divider()

    # ========== TOP FORNECEDORES (Valor Total) ==========
    _render_top_fornecedores(df, cores)

    st.divider()

    # ========== COMPARATIVO TRIMESTRAL ==========
    _render_comparativo_trimestral(df, cores)

    st.divider()

    # ========== TICKET MEDIO ==========
    _render_ticket_medio(df, cores)

    st.divider()

    # ========== PRAZOS DE PAGAMENTO ==========
    _render_prazos_pagamento(df, cores)

    st.divider()

    # ========== CURVA ABC (unificada com Concentracao) ==========
    _render_curva_abc(df, cores)

    st.divider()

    # ========== FORNECEDORES POR FILIAL ==========
    _render_fornecedores_por_filial(df, cores)

    st.divider()

    # ========== MATRIZ FILIAL x FORNECEDOR ==========
    _render_matriz_filial_fornecedor(df, cores)

    st.divider()

    # ========== POR CATEGORIA ==========
    _render_por_categoria(df, cores)

    st.divider()

    # ========== CONSULTA FORNECEDOR ==========
    _render_consulta_fornecedor(df, cores)

    st.divider()

    # ========== RANKING ==========
    _render_ranking(df, cores)


# =============================================
# HELPERS
# =============================================

def _get_nome_grupo_forn(cod_filial):
    grupo_id = get_grupo_filial(int(cod_filial))
    return GRUPOS_FILIAIS.get(grupo_id, f"Grupo {grupo_id}")

def _detectar_multiplos_grupos_forn(df):
    if 'FILIAL' not in df.columns or len(df) == 0:
        return False
    grupos = df['FILIAL'].dropna().apply(lambda x: get_grupo_filial(int(x))).nunique()
    return grupos > 1

def _calcular_classe_abc(df):
    """Retorna dict {NOME_FORNECEDOR: 'A'/'B'/'C'}"""
    df_abc = df.groupby('NOME_FORNECEDOR')['VALOR_ORIGINAL'].sum().sort_values(ascending=False)
    total = df_abc.sum()
    if total == 0:
        return {}
    pct_acum = (df_abc / total * 100).cumsum()
    classes = {}
    for forn, pct in pct_acum.items():
        if pct <= 80:
            classes[forn] = 'A'
        elif pct <= 95:
            classes[forn] = 'B'
        else:
            classes[forn] = 'C'
    return classes


# =============================================
# SECOES
# =============================================

def _render_alertas(df, cores):
    """Alertas e insights automaticos"""

    alertas = []
    hoje = datetime.now()

    # 1. Concentracao excessiva (>30% em um fornecedor)
    total = df['VALOR_ORIGINAL'].sum()
    df_forn = df.groupby('NOME_FORNECEDOR')['VALOR_ORIGINAL'].sum().sort_values(ascending=False)
    if len(df_forn) > 0:
        maior_forn = df_forn.index[0]
        pct_maior = df_forn.iloc[0] / total * 100 if total > 0 else 0
        if pct_maior > 30:
            alertas.append({
                'tipo': 'warning',
                'icone': '⚠️',
                'titulo': 'Concentracao Excessiva',
                'msg': f'{maior_forn[:25]} representa {pct_maior:.1f}% do total'
            })

    # 2. Fornecedores novos com alto volume (>R$100k nos ultimos 60 dias)
    df_novo = df.copy()
    df_novo['PRIMEIRA_COMPRA'] = df_novo.groupby('NOME_FORNECEDOR')['EMISSAO'].transform('min')
    limite_novo = hoje - timedelta(days=60)
    novos_alto_vol = df_novo[df_novo['PRIMEIRA_COMPRA'] >= limite_novo].groupby('NOME_FORNECEDOR')['VALOR_ORIGINAL'].sum()
    novos_alto_vol = novos_alto_vol[novos_alto_vol > 100000]
    if len(novos_alto_vol) > 0:
        for forn, valor in novos_alto_vol.head(3).items():
            alertas.append({
                'tipo': 'info',
                'icone': '🆕',
                'titulo': 'Novo Fornecedor Alto Volume',
                'msg': f'{forn[:25]}: {formatar_moeda(valor)} em 60 dias'
            })

    # 3. Crescimento anormal (>50% vs periodo anterior)
    df_atual = df[df['EMISSAO'] >= hoje - timedelta(days=90)]
    df_anterior = df[(df['EMISSAO'] >= hoje - timedelta(days=180)) & (df['EMISSAO'] < hoje - timedelta(days=90))]

    if len(df_atual) > 0 and len(df_anterior) > 0:
        atual_grp = df_atual.groupby('NOME_FORNECEDOR')['VALOR_ORIGINAL'].sum()
        anterior_grp = df_anterior.groupby('NOME_FORNECEDOR')['VALOR_ORIGINAL'].sum()
        comparativo = pd.DataFrame({'atual': atual_grp, 'anterior': anterior_grp}).fillna(0)
        comparativo['crescimento'] = ((comparativo['atual'] - comparativo['anterior']) / comparativo['anterior'].replace(0, 1)) * 100
        crescimento_alto = comparativo[(comparativo['crescimento'] > 50) & (comparativo['atual'] > 50000)]
        crescimento_alto = crescimento_alto.nlargest(2, 'crescimento')
        for forn in crescimento_alto.index:
            alertas.append({
                'tipo': 'success',
                'icone': '📈',
                'titulo': 'Crescimento Acima de 50%',
                'msg': f'{forn[:25]}: +{crescimento_alto.loc[forn, "crescimento"]:.0f}% vs trimestre anterior'
            })

    # 4. Fornecedor com maior atraso medio
    df_pagos = df[df['SALDO'] == 0].copy()
    if 'DT_BAIXA' in df_pagos.columns and len(df_pagos) > 0:
        df_pagos['ATRASO'] = (df_pagos['DT_BAIXA'] - df_pagos['VENCIMENTO']).dt.days
        atraso_medio = df_pagos[df_pagos['ATRASO'] > 0].groupby('NOME_FORNECEDOR')['ATRASO'].mean()
        if len(atraso_medio) > 0:
            pior_atraso = atraso_medio.nlargest(1)
            forn_atraso = pior_atraso.index[0]
            dias_atraso = pior_atraso.iloc[0]
            if dias_atraso > 15:
                alertas.append({
                    'tipo': 'error',
                    'icone': '⏰',
                    'titulo': 'Maior Atraso Medio',
                    'msg': f'{forn_atraso[:25]}: {dias_atraso:.0f} dias de atraso medio'
                })

    if len(alertas) == 0:
        return

    st.markdown("##### Alertas e Insights")

    # Exibir em cards
    cols = st.columns(min(len(alertas), 4))
    for i, alerta in enumerate(alertas[:4]):
        with cols[i % 4]:
            cor_borda = {
                'warning': cores['alerta'],
                'info': cores['info'],
                'success': cores['sucesso'],
                'error': cores['perigo']
            }.get(alerta['tipo'], cores['borda'])

            st.markdown(f"""
            <div style="background: {cores['card']}; border: 2px solid {cor_borda};
                        border-radius: 8px; padding: 0.75rem; height: 100%;">
                <p style="font-size: 1.2rem; margin: 0 0 0.3rem 0;">{alerta['icone']}</p>
                <p style="color: {cores['texto']}; font-size: 0.75rem; font-weight: 600; margin: 0 0 0.3rem 0;">
                    {alerta['titulo']}</p>
                <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">
                    {alerta['msg']}</p>
            </div>
            """, unsafe_allow_html=True)


def _render_kpis(df, cores):
    """KPIs principais - foco em valores pagos/pendentes"""

    total_fornecedores = df['NOME_FORNECEDOR'].nunique()
    total_valor = df['VALOR_ORIGINAL'].sum()
    total_pendente = df['SALDO'].sum()
    total_pago = total_valor - total_pendente

    pct_pago = (total_pago / total_valor * 100) if total_valor > 0 else 0

    # Concentracao top 10
    df_top10 = df.groupby('NOME_FORNECEDOR')['VALOR_ORIGINAL'].sum().nlargest(10)
    pct_top10 = (df_top10.sum() / total_valor * 100) if total_valor > 0 else 0

    # Ticket medio
    ticket_medio = total_valor / len(df) if len(df) > 0 else 0

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        st.metric(
            label="Fornecedores",
            value=formatar_numero(total_fornecedores),
            delta=f"{formatar_numero(len(df))} titulos",
            delta_color="off"
        )

    with col2:
        st.metric(
            label="Valor Total",
            value=formatar_moeda(total_valor)
        )

    with col3:
        st.metric(
            label="Total Pago",
            value=formatar_moeda(total_pago),
            delta=f"{pct_pago:.1f}%",
            delta_color="off"
        )

    with col4:
        st.metric(
            label="Total Pendente",
            value=formatar_moeda(total_pendente)
        )

    with col5:
        st.metric(
            label="Ticket Medio",
            value=formatar_moeda(ticket_medio)
        )

    with col6:
        st.metric(
            label="Concentracao Top 10",
            value=f"{pct_top10:.1f}%",
            delta="do valor total",
            delta_color="off"
        )


def _render_top_fornecedores(df, cores):
    """Top 15 fornecedores por valor total - Pago vs Pendente"""

    st.markdown("##### Top 15 Fornecedores - Valor Total")

    # Agrupar por fornecedor
    df_forn = df.groupby('NOME_FORNECEDOR').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'NUMERO': 'count'
    }).reset_index()
    df_forn.columns = ['Fornecedor', 'Total', 'Pendente', 'Qtd']
    df_forn['Pago'] = df_forn['Total'] - df_forn['Pendente']

    # Top 15
    df_top = df_forn.nlargest(15, 'Total')
    df_top = df_top.sort_values('Total', ascending=True)

    fig = go.Figure()

    # Pago
    fig.add_trace(go.Bar(
        y=df_top['Fornecedor'].str[:35],
        x=df_top['Pago'],
        orientation='h',
        name='Pago',
        marker_color=cores['sucesso'],
        text=[formatar_moeda(v) if v > 0 else '' for v in df_top['Pago']],
        textposition='inside',
        textfont=dict(size=9, color='white')
    ))

    # Pendente
    fig.add_trace(go.Bar(
        y=df_top['Fornecedor'].str[:35],
        x=df_top['Pendente'],
        orientation='h',
        name='Pendente',
        marker_color=cores['alerta'],
        text=[formatar_moeda(v) if v > 0 else '' for v in df_top['Pendente']],
        textposition='inside',
        textfont=dict(size=9, color='white')
    ))

    fig.update_layout(
        criar_layout(450),
        barmode='stack',
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(showticklabels=False, showgrid=False),
        yaxis=dict(tickfont=dict(size=10, color=cores['texto'])),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1,
            font=dict(size=10, color=cores['texto'])
        )
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_comparativo_trimestral(df, cores):
    """Comparativo trimestral dos top fornecedores"""

    st.markdown("##### Comparativo Trimestral - Top 10 Fornecedores")

    hoje = datetime.now()

    # Trimestre atual e anterior
    inicio_tri_atual = hoje - timedelta(days=90)
    inicio_tri_anterior = hoje - timedelta(days=180)

    df_atual = df[df['EMISSAO'] >= inicio_tri_atual].copy()
    df_anterior = df[(df['EMISSAO'] >= inicio_tri_anterior) & (df['EMISSAO'] < inicio_tri_atual)].copy()

    if len(df_atual) == 0 and len(df_anterior) == 0:
        st.info("Dados insuficientes para comparativo trimestral")
        return

    # Top 10 por valor total (considerando ambos periodos)
    grp_atual = df_atual.groupby('NOME_FORNECEDOR')['VALOR_ORIGINAL'].sum()
    grp_anterior = df_anterior.groupby('NOME_FORNECEDOR')['VALOR_ORIGINAL'].sum()

    df_comp = pd.DataFrame({
        'Atual': grp_atual,
        'Anterior': grp_anterior
    }).fillna(0)
    df_comp['Total'] = df_comp['Atual'] + df_comp['Anterior']
    df_comp = df_comp.nlargest(10, 'Total')
    df_comp = df_comp.sort_values('Total', ascending=True)

    # Calcular variacao
    df_comp['Variacao'] = np.where(
        df_comp['Anterior'] > 0,
        ((df_comp['Atual'] - df_comp['Anterior']) / df_comp['Anterior'] * 100),
        np.where(df_comp['Atual'] > 0, 100, 0)
    )

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=[f[:30] for f in df_comp.index],
        x=df_comp['Anterior'],
        orientation='h',
        name='Trimestre Anterior',
        marker_color=cores['texto_secundario'],
        text=[formatar_moeda(v) if v > 0 else '' for v in df_comp['Anterior']],
        textposition='inside',
        textfont=dict(size=9, color='white')
    ))

    fig.add_trace(go.Bar(
        y=[f[:30] for f in df_comp.index],
        x=df_comp['Atual'],
        orientation='h',
        name='Trimestre Atual',
        marker_color=cores['primaria'],
        text=[formatar_moeda(v) if v > 0 else '' for v in df_comp['Atual']],
        textposition='inside',
        textfont=dict(size=9, color='white')
    ))

    fig.update_layout(
        criar_layout(380),
        barmode='group',
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(showticklabels=False, showgrid=False),
        yaxis=dict(tickfont=dict(size=9, color=cores['texto'])),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1,
            font=dict(size=10, color=cores['texto'])
        )
    )

    st.plotly_chart(fig, use_container_width=True)

    # Cards de variacao
    destaques = df_comp.sort_values('Variacao', ascending=False)
    maiores_altas = destaques[destaques['Variacao'] > 0].head(3)
    maiores_quedas = destaques[destaques['Variacao'] < 0].head(3)

    col1, col2 = st.columns(2)

    with col1:
        if len(maiores_altas) > 0:
            st.markdown("###### Maiores Altas")
            for forn, row in maiores_altas.iterrows():
                st.markdown(f"""
                <div style="background: {cores['card']}; border-left: 3px solid {cores['sucesso']};
                            border-radius: 4px; padding: 0.4rem 0.6rem; margin-bottom: 0.3rem;">
                    <span style="color: {cores['texto']}; font-size: 0.8rem; font-weight: 600;">
                        {forn[:30]}</span>
                    <span style="color: {cores['sucesso']}; font-size: 0.8rem; float: right;">
                        +{row['Variacao']:.0f}%</span>
                </div>
                """, unsafe_allow_html=True)

    with col2:
        if len(maiores_quedas) > 0:
            st.markdown("###### Maiores Quedas")
            for forn, row in maiores_quedas.iterrows():
                st.markdown(f"""
                <div style="background: {cores['card']}; border-left: 3px solid {cores['perigo']};
                            border-radius: 4px; padding: 0.4rem 0.6rem; margin-bottom: 0.3rem;">
                    <span style="color: {cores['texto']}; font-size: 0.8rem; font-weight: 600;">
                        {forn[:30]}</span>
                    <span style="color: {cores['perigo']}; font-size: 0.8rem; float: right;">
                        {row['Variacao']:.0f}%</span>
                </div>
                """, unsafe_allow_html=True)


def _render_ticket_medio(df, cores):
    """Scatter plot: Ticket Medio x Qtd Titulos x Valor Total"""

    st.markdown("##### Ticket Medio por Fornecedor")

    df_forn = df.groupby('NOME_FORNECEDOR').agg({
        'VALOR_ORIGINAL': 'sum',
        'NUMERO': 'count'
    }).reset_index()
    df_forn.columns = ['Fornecedor', 'Total', 'Qtd']
    df_forn['Ticket'] = df_forn['Total'] / df_forn['Qtd']

    # Classificar ABC
    classes = _calcular_classe_abc(df)
    df_forn['Classe'] = df_forn['Fornecedor'].map(classes).fillna('C')

    # Filtrar fornecedores com pelo menos 2 titulos para scatter legivel
    df_plot = df_forn[df_forn['Qtd'] >= 2].copy()

    if len(df_plot) == 0:
        st.info("Dados insuficientes")
        return

    # Normalizar tamanho dos bubbles
    max_total = df_plot['Total'].max()
    df_plot['Size'] = (df_plot['Total'] / max_total * 40).clip(lower=5)

    cores_classe = {'A': cores['primaria'], 'B': cores['alerta'], 'C': cores['texto_secundario']}

    fig = go.Figure()

    for classe in ['A', 'B', 'C']:
        df_c = df_plot[df_plot['Classe'] == classe]
        if len(df_c) == 0:
            continue

        fig.add_trace(go.Scatter(
            x=df_c['Qtd'],
            y=df_c['Ticket'],
            mode='markers',
            name=f'Classe {classe}',
            marker=dict(
                size=df_c['Size'],
                color=cores_classe[classe],
                opacity=0.7,
                line=dict(width=1, color=cores['borda'])
            ),
            text=df_c['Fornecedor'].str[:25],
            customdata=np.stack([
                df_c['Total'].values,
                df_c['Qtd'].values,
                df_c['Ticket'].values
            ], axis=-1),
            hovertemplate=(
                '<b>%{text}</b><br>'
                'Titulos: %{customdata[1]:.0f}<br>'
                'Ticket Medio: R$ %{customdata[2]:,.0f}<br>'
                'Total: R$ %{customdata[0]:,.0f}<extra></extra>'
            )
        ))

    fig.update_layout(
        criar_layout(350),
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(
            title='Quantidade de Titulos',
            title_font=dict(size=10, color=cores['texto_secundario']),
            tickfont=dict(size=9, color=cores['texto']),
            showgrid=True,
            gridcolor=cores['borda']
        ),
        yaxis=dict(
            title='Ticket Medio (R$)',
            title_font=dict(size=10, color=cores['texto_secundario']),
            tickfont=dict(size=9, color=cores['texto']),
            showgrid=True,
            gridcolor=cores['borda']
        ),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1,
            font=dict(size=10, color=cores['texto'])
        )
    )

    st.plotly_chart(fig, use_container_width=True)

    # Insights
    col1, col2, col3 = st.columns(3)

    # Maior ticket medio (min 3 titulos)
    df_ticket_min3 = df_forn[df_forn['Qtd'] >= 3]
    if len(df_ticket_min3) > 0:
        maior_ticket = df_ticket_min3.nlargest(1, 'Ticket').iloc[0]
        col1.metric(
            "Maior Ticket Medio",
            formatar_moeda(maior_ticket['Ticket']),
            f"{maior_ticket['Fornecedor'][:20]}"
        )

    # Mais titulos
    if len(df_forn) > 0:
        mais_titulos = df_forn.nlargest(1, 'Qtd').iloc[0]
        col2.metric(
            "Mais Titulos",
            formatar_numero(int(mais_titulos['Qtd'])),
            f"{mais_titulos['Fornecedor'][:20]}"
        )

    # Media geral
    ticket_geral = df['VALOR_ORIGINAL'].sum() / len(df) if len(df) > 0 else 0
    col3.metric(
        "Ticket Medio Geral",
        formatar_moeda(ticket_geral)
    )


def _render_prazos_pagamento(df, cores):
    """Analise de prazos de pagamento por fornecedor"""

    st.markdown("##### Prazos de Pagamento")

    # Calcular prazo concedido (emissao ate vencimento)
    df_prazos = df.copy()
    df_prazos['PRAZO_CONCEDIDO'] = (df_prazos['VENCIMENTO'] - df_prazos['EMISSAO']).dt.days

    # Calcular prazo real (emissao ate pagamento) - apenas para pagos
    df_pagos = df_prazos[df_prazos['SALDO'] == 0].copy()
    if 'DT_BAIXA' in df_pagos.columns:
        df_pagos['PRAZO_REAL'] = (df_pagos['DT_BAIXA'] - df_pagos['EMISSAO']).dt.days
    else:
        df_pagos['PRAZO_REAL'] = None

    # KPIs de prazo
    prazo_medio_concedido = df_prazos['PRAZO_CONCEDIDO'].mean()
    prazo_medio_real = df_pagos['PRAZO_REAL'].mean() if 'PRAZO_REAL' in df_pagos.columns and len(df_pagos) > 0 else 0

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Prazo Medio Concedido",
            value=f"{prazo_medio_concedido:.0f} dias" if pd.notna(prazo_medio_concedido) else "N/A",
            delta="emissao > vencimento",
            delta_color="off"
        )

    with col2:
        st.metric(
            label="Prazo Medio Real",
            value=f"{prazo_medio_real:.0f} dias" if pd.notna(prazo_medio_real) and prazo_medio_real > 0 else "N/A",
            delta="emissao > pagamento",
            delta_color="off"
        )

    with col3:
        diferenca = prazo_medio_real - prazo_medio_concedido if pd.notna(prazo_medio_real) and pd.notna(prazo_medio_concedido) else 0
        cor_diff = "normal" if diferenca <= 0 else "inverse"
        st.metric(
            label="Diferenca Media",
            value=f"{diferenca:+.0f} dias" if diferenca != 0 else "0 dias",
            delta="antecipado" if diferenca < 0 else ("atrasado" if diferenca > 0 else "no prazo"),
            delta_color=cor_diff
        )

    with col4:
        # % pagos no prazo
        if 'PRAZO_REAL' in df_pagos.columns and len(df_pagos) > 0:
            df_pagos_valid = df_pagos[df_pagos['PRAZO_REAL'].notna() & df_pagos['PRAZO_CONCEDIDO'].notna()]
            if len(df_pagos_valid) > 0:
                pct_no_prazo = (df_pagos_valid['PRAZO_REAL'] <= df_pagos_valid['PRAZO_CONCEDIDO']).mean() * 100
            else:
                pct_no_prazo = 0
        else:
            pct_no_prazo = 0
        st.metric(
            label="Pagos no Prazo",
            value=f"{pct_no_prazo:.0f}%",
            delta=f"{len(df_pagos)} titulos pagos",
            delta_color="off"
        )

    # Graficos lado a lado
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("###### Fornecedores que dao mais prazo")

        # Agrupar por fornecedor - prazo concedido
        df_forn_prazo = df_prazos.groupby('NOME_FORNECEDOR').agg({
            'PRAZO_CONCEDIDO': 'mean',
            'VALOR_ORIGINAL': 'sum',
            'NUMERO': 'count'
        }).reset_index()
        df_forn_prazo.columns = ['Fornecedor', 'Prazo', 'Valor', 'Qtd']

        # Filtrar fornecedores com pelo menos 3 titulos
        df_forn_prazo = df_forn_prazo[df_forn_prazo['Qtd'] >= 3]

        # Top 10 mais prazo
        df_mais_prazo = df_forn_prazo.nlargest(10, 'Prazo')
        df_mais_prazo = df_mais_prazo.sort_values('Prazo', ascending=True)

        if len(df_mais_prazo) > 0:
            fig = go.Figure()

            fig.add_trace(go.Bar(
                y=df_mais_prazo['Fornecedor'].str[:30],
                x=df_mais_prazo['Prazo'],
                orientation='h',
                marker_color=cores['sucesso'],
                text=[f"{int(p)} dias" for p in df_mais_prazo['Prazo']],
                textposition='outside',
                textfont=dict(size=9, color=cores['texto'])
            ))

            fig.update_layout(
                criar_layout(280),
                margin=dict(l=10, r=60, t=10, b=10),
                xaxis=dict(showticklabels=False, showgrid=False),
                yaxis=dict(tickfont=dict(size=9, color=cores['texto']))
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Dados insuficientes")

    with col2:
        st.markdown("###### Fornecedores que dao menos prazo")

        # Top 10 menos prazo (excluir prazos negativos ou zero)
        df_menos_prazo = df_forn_prazo[df_forn_prazo['Prazo'] > 0].nsmallest(10, 'Prazo')
        df_menos_prazo = df_menos_prazo.sort_values('Prazo', ascending=True)

        if len(df_menos_prazo) > 0:
            fig = go.Figure()

            fig.add_trace(go.Bar(
                y=df_menos_prazo['Fornecedor'].str[:30],
                x=df_menos_prazo['Prazo'],
                orientation='h',
                marker_color=cores['perigo'],
                text=[f"{int(p)} dias" for p in df_menos_prazo['Prazo']],
                textposition='outside',
                textfont=dict(size=9, color=cores['texto'])
            ))

            fig.update_layout(
                criar_layout(280),
                margin=dict(l=10, r=60, t=10, b=10),
                xaxis=dict(showticklabels=False, showgrid=False),
                yaxis=dict(tickfont=dict(size=9, color=cores['texto']))
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Dados insuficientes")

    # Tabela comparativa
    with st.expander("Ver detalhes por fornecedor"):
        df_detalhe = df_prazos.copy()

        # Adicionar prazo real
        if 'DT_BAIXA' in df_detalhe.columns:
            df_detalhe['PRAZO_REAL'] = (df_detalhe['DT_BAIXA'] - df_detalhe['EMISSAO']).dt.days

        df_detalhe_grp = df_detalhe.groupby('NOME_FORNECEDOR').agg({
            'PRAZO_CONCEDIDO': 'mean',
            'VALOR_ORIGINAL': 'sum',
            'SALDO': 'sum',
            'NUMERO': 'count'
        }).reset_index()

        # Adicionar prazo real medio (apenas dos pagos)
        if 'PRAZO_REAL' in df_detalhe.columns:
            prazo_real_grp = df_detalhe[df_detalhe['SALDO'] == 0].groupby('NOME_FORNECEDOR')['PRAZO_REAL'].mean()
            df_detalhe_grp = df_detalhe_grp.merge(
                prazo_real_grp.reset_index().rename(columns={'PRAZO_REAL': 'Prazo Real'}),
                on='NOME_FORNECEDOR',
                how='left'
            )
        else:
            df_detalhe_grp['Prazo Real'] = None

        df_detalhe_grp.columns = ['Fornecedor', 'Prazo Concedido', 'Valor Total', 'Saldo', 'Qtd', 'Prazo Real']
        df_detalhe_grp['Diferenca'] = df_detalhe_grp['Prazo Real'] - df_detalhe_grp['Prazo Concedido']

        # Formatar
        df_show = df_detalhe_grp.copy()
        df_show['Prazo Concedido'] = df_show['Prazo Concedido'].apply(lambda x: f"{x:.0f} dias" if pd.notna(x) else "-")
        df_show['Prazo Real'] = df_show['Prazo Real'].apply(lambda x: f"{x:.0f} dias" if pd.notna(x) else "-")
        df_show['Diferenca'] = df_show['Diferenca'].apply(lambda x: f"{x:+.0f} dias" if pd.notna(x) else "-")
        df_show['Valor Total'] = df_show['Valor Total'].apply(lambda x: formatar_moeda(x, completo=True))
        df_show['Saldo'] = df_show['Saldo'].apply(lambda x: formatar_moeda(x, completo=True))

        df_show = df_show.sort_values('Qtd', ascending=False).head(50)

        st.dataframe(
            df_show[['Fornecedor', 'Prazo Concedido', 'Prazo Real', 'Diferenca', 'Valor Total', 'Qtd']],
            use_container_width=True,
            hide_index=True,
            height=300
        )


def _render_curva_abc(df, cores):
    """Curva ABC unificada com analise de concentracao"""

    st.markdown("##### Curva ABC e Concentracao")

    df_abc = df.groupby('NOME_FORNECEDOR')['VALOR_ORIGINAL'].sum().sort_values(ascending=False).reset_index()
    total = df_abc['VALOR_ORIGINAL'].sum()
    if total == 0:
        st.info("Sem dados")
        return

    df_abc['PCT'] = df_abc['VALOR_ORIGINAL'] / total * 100
    df_abc['PCT_ACUM'] = df_abc['PCT'].cumsum()
    df_abc['RANK'] = range(1, len(df_abc) + 1)

    df_abc['CLASSE'] = df_abc['PCT_ACUM'].apply(
        lambda x: 'A' if x <= 80 else ('B' if x <= 95 else 'C')
    )

    # Estatisticas por classe
    qtd_a = len(df_abc[df_abc['CLASSE'] == 'A'])
    qtd_b = len(df_abc[df_abc['CLASSE'] == 'B'])
    qtd_c = len(df_abc[df_abc['CLASSE'] == 'C'])
    val_a = df_abc[df_abc['CLASSE'] == 'A']['VALOR_ORIGINAL'].sum()
    val_b = df_abc[df_abc['CLASSE'] == 'B']['VALOR_ORIGINAL'].sum()
    val_c = df_abc[df_abc['CLASSE'] == 'C']['VALOR_ORIGINAL'].sum()

    col1, col2 = st.columns([2, 1])

    with col1:
        # Grafico Pareto
        cores_abc = {'A': cores['primaria'], 'B': cores['alerta'], 'C': cores['texto_secundario']}

        df_show = df_abc.head(30)
        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=df_show['RANK'],
            y=df_show['VALOR_ORIGINAL'],
            name='Valor',
            marker_color=[cores_abc[c] for c in df_show['CLASSE']]
        ))

        fig.add_trace(go.Scatter(
            x=df_show['RANK'],
            y=df_show['PCT_ACUM'],
            name='% Acumulado',
            mode='lines+markers',
            line=dict(color=cores['texto'], width=2),
            marker=dict(size=4),
            yaxis='y2'
        ))

        fig.add_hline(y=80, line_dash="dash", line_color=cores['sucesso'], line_width=1, yref='y2')
        fig.add_hline(y=95, line_dash="dash", line_color=cores['alerta'], line_width=1, yref='y2')

        fig.update_layout(
            criar_layout(320),
            yaxis=dict(showticklabels=False, showgrid=False),
            yaxis2=dict(overlaying='y', side='right', range=[0, 105], showgrid=False,
                        tickfont=dict(size=9, color=cores['texto'])),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                        font=dict(size=9, color=cores['texto'])),
            margin=dict(l=10, r=40, t=30, b=30),
            xaxis=dict(title='Rank', tickfont=dict(size=9, color=cores['texto']))
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Cards por classe
        for classe, qtd, val, cor in [
            ('A', qtd_a, val_a, cores['primaria']),
            ('B', qtd_b, val_b, cores['alerta']),
            ('C', qtd_c, val_c, cores['texto_secundario'])
        ]:
            pct_forn = qtd / len(df_abc) * 100 if len(df_abc) > 0 else 0
            pct_val = val / total * 100

            st.markdown(f"""
            <div style="background: {cores['card']}; border-left: 4px solid {cor};
                        border-radius: 4px; padding: 0.6rem; margin-bottom: 0.5rem;">
                <p style="color: {cor}; font-size: 1rem; font-weight: 700; margin: 0;">
                    Classe {classe}</p>
                <p style="color: {cores['texto']}; font-size: 0.85rem; margin: 0.2rem 0 0 0;">
                    {qtd} fornecedores ({pct_forn:.0f}%)</p>
                <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0.1rem 0 0 0;">
                    {formatar_moeda(val)} ({pct_val:.1f}%)</p>
            </div>
            """, unsafe_allow_html=True)

        # Concentracao resumida
        st.markdown("###### Concentracao")
        for n in [1, 5, 10, 20]:
            if n <= len(df_abc):
                val_top = df_abc.head(n)['VALOR_ORIGINAL'].sum()
                pct = val_top / total * 100
                st.caption(f"Top {n}: **{pct:.1f}%** do total")


def _render_fornecedores_por_filial(df, cores):
    """Fornecedores exclusivos vs compartilhados por filial/grupo"""

    multiplos = _detectar_multiplos_grupos_forn(df)

    if 'FILIAL' not in df.columns or 'NOME_FILIAL' not in df.columns:
        return

    if multiplos:
        st.markdown("##### Fornecedores por Grupo")
        df_aux = df.copy()
        df_aux['LABEL'] = df_aux['FILIAL'].apply(lambda x: _get_nome_grupo_forn(x))
    else:
        st.markdown("##### Fornecedores por Filial")
        df_aux = df.copy()
        df_aux['LABEL'] = df_aux['FILIAL'].astype(int).astype(str) + ' - ' + df_aux['NOME_FILIAL'].str.split(' - ').str[-1].str.strip()

    # Para cada fornecedor, contar em quantas filiais/grupos aparece
    forn_filiais = df_aux.groupby('NOME_FORNECEDOR')['LABEL'].nunique()
    n_unidades = df_aux['LABEL'].nunique()

    # Classificar: exclusivo (1 unidade) vs compartilhado (2+)
    exclusivos = set(forn_filiais[forn_filiais == 1].index)
    compartilhados = set(forn_filiais[forn_filiais > 1].index)

    # Contar por unidade
    unidades = sorted(df_aux['LABEL'].unique())
    dados = []
    for unidade in unidades:
        forns_unidade = set(df_aux[df_aux['LABEL'] == unidade]['NOME_FORNECEDOR'].unique())
        qtd_excl = len(forns_unidade & exclusivos)
        qtd_comp = len(forns_unidade & compartilhados)
        val_excl = df_aux[(df_aux['LABEL'] == unidade) & (df_aux['NOME_FORNECEDOR'].isin(exclusivos))]['VALOR_ORIGINAL'].sum()
        val_comp = df_aux[(df_aux['LABEL'] == unidade) & (df_aux['NOME_FORNECEDOR'].isin(compartilhados))]['VALOR_ORIGINAL'].sum()
        dados.append({
            'Unidade': unidade,
            'Exclusivos': qtd_excl,
            'Compartilhados': qtd_comp,
            'Val_Excl': val_excl,
            'Val_Comp': val_comp
        })

    df_dados = pd.DataFrame(dados)
    df_dados = df_dados.sort_values('Exclusivos', ascending=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("###### Quantidade de Fornecedores")

        fig = go.Figure()

        fig.add_trace(go.Bar(
            y=df_dados['Unidade'],
            x=df_dados['Exclusivos'],
            orientation='h',
            name='Exclusivos',
            marker_color=cores['alerta'],
            text=[str(v) for v in df_dados['Exclusivos']],
            textposition='inside',
            textfont=dict(size=9, color='white')
        ))

        fig.add_trace(go.Bar(
            y=df_dados['Unidade'],
            x=df_dados['Compartilhados'],
            orientation='h',
            name='Compartilhados',
            marker_color=cores['info'],
            text=[str(v) for v in df_dados['Compartilhados']],
            textposition='inside',
            textfont=dict(size=9, color='white')
        ))

        fig.update_layout(
            criar_layout(280),
            barmode='stack',
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis=dict(showticklabels=False, showgrid=False),
            yaxis=dict(tickfont=dict(size=9, color=cores['texto'])),
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='right',
                x=1,
                font=dict(size=9, color=cores['texto'])
            )
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("###### Valor por Tipo")

        fig = go.Figure()

        fig.add_trace(go.Bar(
            y=df_dados['Unidade'],
            x=df_dados['Val_Excl'],
            orientation='h',
            name='Exclusivos',
            marker_color=cores['alerta'],
            text=[formatar_moeda(v) if v > 0 else '' for v in df_dados['Val_Excl']],
            textposition='inside',
            textfont=dict(size=9, color='white')
        ))

        fig.add_trace(go.Bar(
            y=df_dados['Unidade'],
            x=df_dados['Val_Comp'],
            orientation='h',
            name='Compartilhados',
            marker_color=cores['info'],
            text=[formatar_moeda(v) if v > 0 else '' for v in df_dados['Val_Comp']],
            textposition='inside',
            textfont=dict(size=9, color='white')
        ))

        fig.update_layout(
            criar_layout(280),
            barmode='stack',
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis=dict(showticklabels=False, showgrid=False),
            yaxis=dict(showticklabels=False),
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='right',
                x=1,
                font=dict(size=9, color=cores['texto'])
            )
        )

        st.plotly_chart(fig, use_container_width=True)

    # KPIs resumo
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Fornecedores", formatar_numero(len(exclusivos) + len(compartilhados)))
    col2.metric("Exclusivos", formatar_numero(len(exclusivos)), f"{len(exclusivos)/(len(exclusivos)+len(compartilhados))*100:.0f}%" if (len(exclusivos)+len(compartilhados)) > 0 else "0%")
    col3.metric("Compartilhados", formatar_numero(len(compartilhados)), f"em 2+ {'grupos' if multiplos else 'filiais'}")


def _render_matriz_filial_fornecedor(df, cores):
    """Matriz de relacionamento Filial x Fornecedor"""

    multiplos = _detectar_multiplos_grupos_forn(df)

    # Top 10 fornecedores
    top10_forn = df.groupby('NOME_FORNECEDOR')['VALOR_ORIGINAL'].sum().nlargest(10).index.tolist()

    if len(top10_forn) == 0 or 'NOME_FILIAL' not in df.columns:
        st.info("Dados insuficientes")
        return

    # Filtrar e criar pivot
    df_matriz = df[df['NOME_FORNECEDOR'].isin(top10_forn)].copy()

    if multiplos:
        st.markdown("##### Matriz Grupo x Fornecedor")
        df_matriz['GRUPO'] = df_matriz['FILIAL'].apply(lambda x: _get_nome_grupo_forn(x))
        pivot = df_matriz.pivot_table(
            values='VALOR_ORIGINAL',
            index='GRUPO',
            columns='NOME_FORNECEDOR',
            aggfunc='sum',
            fill_value=0
        )
    else:
        st.markdown("##### Matriz Filial x Fornecedor")
        df_matriz['FILIAL_LABEL'] = df_matriz['FILIAL'].astype(int).astype(str) + ' - ' + df_matriz['NOME_FILIAL'].str.split(' - ').str[-1].str.strip()
        pivot = df_matriz.pivot_table(
            values='VALOR_ORIGINAL',
            index='FILIAL_LABEL',
            columns='NOME_FORNECEDOR',
            aggfunc='sum',
            fill_value=0
        )

    if pivot.empty:
        st.info("Dados insuficientes para matriz")
        return

    # Heatmap
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=[f[:20] for f in pivot.columns],
        y=[f[:25] for f in pivot.index],
        colorscale=[
            [0, cores['fundo']],
            [0.5, cores['info']],
            [1, cores['primaria']]
        ],
        hovertemplate='Filial: %{y}<br>Fornecedor: %{x}<br>Valor: R$ %{z:,.0f}<extra></extra>'
    ))

    fig.update_layout(
        criar_layout(400),
        margin=dict(l=10, r=10, t=10, b=80),
        xaxis=dict(tickangle=-45, tickfont=dict(size=8, color=cores['texto'])),
        yaxis=dict(tickfont=dict(size=9, color=cores['texto']))
    )

    st.plotly_chart(fig, use_container_width=True)

    # Insights
    with st.expander("Ver insights da matriz"):
        for forn in top10_forn[:5]:
            if forn in pivot.columns:
                total_forn = pivot[forn].sum()
                if total_forn > 0:
                    max_filial = pivot[forn].idxmax()
                    pct_max = pivot[forn].max() / total_forn * 100
                    if pct_max > 70:
                        st.caption(f"**{forn[:30]}**: {pct_max:.0f}% concentrado em {max_filial}")


def _render_por_categoria(df, cores):
    """Valores por categoria (DESCRICAO) - Pago vs Pendente"""

    st.markdown("##### Por Categoria")

    if 'DESCRICAO' not in df.columns:
        st.info("Sem dados de categoria")
        return

    # Agrupar por categoria
    df_cat = df.groupby('DESCRICAO').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'NOME_FORNECEDOR': 'nunique'
    }).reset_index()
    df_cat.columns = ['Categoria', 'Total', 'Pendente', 'Fornecedores']
    df_cat['Pago'] = df_cat['Total'] - df_cat['Pendente']

    # Top 12
    df_top = df_cat.nlargest(12, 'Total')
    df_top = df_top.sort_values('Total', ascending=True)

    col1, col2 = st.columns([2, 1])

    with col1:
        fig = go.Figure()

        fig.add_trace(go.Bar(
            y=df_top['Categoria'].str[:30],
            x=df_top['Pago'],
            orientation='h',
            name='Pago',
            marker_color=cores['sucesso'],
            text=[formatar_moeda(v) if v > 0 else '' for v in df_top['Pago']],
            textposition='inside',
            textfont=dict(size=8, color='white')
        ))

        fig.add_trace(go.Bar(
            y=df_top['Categoria'].str[:30],
            x=df_top['Pendente'],
            orientation='h',
            name='Pendente',
            marker_color=cores['alerta'],
            text=[formatar_moeda(v) if v > 0 else '' for v in df_top['Pendente']],
            textposition='inside',
            textfont=dict(size=8, color='white')
        ))

        fig.update_layout(
            criar_layout(380),
            barmode='stack',
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis=dict(showticklabels=False, showgrid=False),
            yaxis=dict(tickfont=dict(size=9, color=cores['texto'])),
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='right',
                x=1,
                font=dict(size=10, color=cores['texto'])
            )
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("**Top 5 categorias:**")
        for _, row in df_top.tail(5).iloc[::-1].iterrows():
            pct_pago = (row['Pago'] / row['Total'] * 100) if row['Total'] > 0 else 0
            st.markdown(f"""
            <div style="background: {cores['card']}; border: 1px solid {cores['borda']};
                        border-radius: 8px; padding: 0.5rem; margin-bottom: 0.5rem;">
                <p style="color: {cores['texto']}; font-size: 0.8rem; font-weight: 600; margin: 0;">
                    {row['Categoria'][:25]}</p>
                <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">
                    {int(row['Fornecedores'])} fornecedores</p>
                <p style="color: {cores['texto']}; font-size: 0.75rem; margin: 0;">
                    Total: {formatar_moeda(row['Total'])}</p>
                <p style="color: {cores['sucesso']}; font-size: 0.7rem; margin: 0;">
                    {pct_pago:.0f}% pago</p>
            </div>
            """, unsafe_allow_html=True)


def _render_consulta_fornecedor(df, cores):
    """Consulta detalhada de fornecedor - Raio-X completo"""

    st.markdown("##### Raio-X do Fornecedor")

    fornecedores = sorted([str(x) for x in df['NOME_FORNECEDOR'].unique().tolist()])

    fornecedor_selecionado = st.selectbox(
        "Selecione um fornecedor",
        options=[""] + fornecedores,
        key="busca_forn"
    )

    if not fornecedor_selecionado:
        st.info("Selecione um fornecedor para ver detalhes")
        return

    df_forn = df[df['NOME_FORNECEDOR'] == fornecedor_selecionado]

    # Metricas basicas
    total_valor = df_forn['VALOR_ORIGINAL'].sum()
    total_pendente = df_forn['SALDO'].sum()
    total_pago = total_valor - total_pendente
    qtd_titulos = len(df_forn)
    pct_pago = (total_pago / total_valor * 100) if total_valor > 0 else 0
    ticket_medio = total_valor / qtd_titulos if qtd_titulos > 0 else 0

    # Classe ABC
    classes = _calcular_classe_abc(df)
    classe = classes.get(fornecedor_selecionado, 'C')
    cor_classe = {'A': cores['primaria'], 'B': cores['alerta'], 'C': cores['texto_secundario']}.get(classe, cores['texto'])

    # Prazo medio concedido
    df_forn_prazos = df_forn.copy()
    df_forn_prazos['PRAZO_CONC'] = (df_forn_prazos['VENCIMENTO'] - df_forn_prazos['EMISSAO']).dt.days
    prazo_medio = df_forn_prazos['PRAZO_CONC'].mean()

    # Atraso medio (dos pagos)
    atraso_medio = 0
    df_pagos_forn = df_forn[df_forn['SALDO'] == 0].copy()
    if 'DT_BAIXA' in df_pagos_forn.columns and len(df_pagos_forn) > 0:
        df_pagos_forn['ATRASO'] = (df_pagos_forn['DT_BAIXA'] - df_pagos_forn['VENCIMENTO']).dt.days
        atraso_vals = df_pagos_forn[df_pagos_forn['ATRASO'] > 0]['ATRASO']
        atraso_medio = atraso_vals.mean() if len(atraso_vals) > 0 else 0

    # Filiais que compram
    filiais_forn = []
    if 'NOME_FILIAL' in df_forn.columns:
        filiais_forn = df_forn['NOME_FILIAL'].unique().tolist()

    # Linha 1: KPIs principais
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    col1.markdown(f"""
    <div style="background: {cores['card']}; border: 2px solid {cor_classe};
                border-radius: 8px; padding: 0.5rem; text-align: center;">
        <p style="color: {cor_classe}; font-size: 1.5rem; font-weight: 700; margin: 0;">
            {classe}</p>
        <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">
            Classe ABC</p>
    </div>
    """, unsafe_allow_html=True)

    col2.metric("Valor Total", formatar_moeda(total_valor), f"{qtd_titulos} titulos")
    col3.metric("Pago", formatar_moeda(total_pago), f"{pct_pago:.1f}%")
    col4.metric("Pendente", formatar_moeda(total_pendente))
    col5.metric("Ticket Medio", formatar_moeda(ticket_medio))

    prazo_str = f"{prazo_medio:.0f} dias" if pd.notna(prazo_medio) else "N/A"
    atraso_str = f"{atraso_medio:.0f} dias" if pd.notna(atraso_medio) and atraso_medio > 0 else "Sem atraso"
    col6.metric("Prazo Medio", prazo_str, atraso_str if atraso_medio > 0 else None)

    # Filiais
    if len(filiais_forn) > 0:
        filiais_txt = " | ".join([f.split(' - ')[-1].strip()[:20] if ' - ' in str(f) else str(f)[:20] for f in filiais_forn[:6]])
        st.caption(f"Filiais: {filiais_txt}")

    # Tabs
    tab1, tab2 = st.tabs(["Evolucao", "Titulos"])

    with tab1:
        df_hist = df_forn.copy()
        df_hist['MES'] = df_hist['EMISSAO'].dt.to_period('M').astype(str)
        df_hist_grp = df_hist.groupby('MES').agg({
            'VALOR_ORIGINAL': 'sum',
            'SALDO': 'sum'
        }).reset_index()
        df_hist_grp['PAGO'] = df_hist_grp['VALOR_ORIGINAL'] - df_hist_grp['SALDO']

        if len(df_hist_grp) > 1:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df_hist_grp['MES'],
                y=df_hist_grp['PAGO'],
                name='Pago',
                marker_color=cores['sucesso']
            ))
            fig.add_trace(go.Bar(
                x=df_hist_grp['MES'],
                y=df_hist_grp['SALDO'],
                name='Pendente',
                marker_color=cores['alerta']
            ))
            fig.update_layout(
                criar_layout(200),
                barmode='stack',
                margin=dict(l=10, r=10, t=10, b=40),
                xaxis=dict(tickangle=-45, tickfont=dict(size=9)),
                yaxis=dict(showticklabels=False),
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Historico insuficiente para grafico")

    with tab2:
        colunas = ['NOME_FILIAL', 'NUMERO', 'DESCRICAO', 'EMISSAO', 'VENCIMENTO', 'VALOR_ORIGINAL', 'SALDO']
        colunas_disp = [c for c in colunas if c in df_forn.columns]
        df_tab = df_forn[colunas_disp].copy()

        for col in ['EMISSAO', 'VENCIMENTO']:
            if col in df_tab.columns:
                df_tab[col] = pd.to_datetime(df_tab[col], errors='coerce').dt.strftime('%d/%m/%Y')
                df_tab[col] = df_tab[col].fillna('-')

        df_tab['VALOR_ORIGINAL'] = df_tab['VALOR_ORIGINAL'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab['SALDO'] = df_tab['SALDO'].apply(lambda x: formatar_moeda(x, completo=True))

        nomes = {
            'NOME_FILIAL': 'Filial',
            'NUMERO': 'NF/Doc',
            'DESCRICAO': 'Categoria',
            'EMISSAO': 'Emissao',
            'VENCIMENTO': 'Vencimento',
            'VALOR_ORIGINAL': 'Valor',
            'SALDO': 'Saldo'
        }
        df_tab.columns = [nomes.get(c, c) for c in df_tab.columns]

        st.dataframe(df_tab, use_container_width=True, hide_index=True, height=300)


def _render_ranking(df, cores):
    """Ranking de fornecedores"""

    st.markdown("##### Ranking de Fornecedores")

    # Filtros
    col1, col2, col3 = st.columns(3)

    with col1:
        ordenar = st.selectbox(
            "Ordenar por",
            ["Valor Total", "Valor Pago", "Saldo Pendente"],
            key="rank_ordem"
        )

    with col2:
        qtd_exibir = st.selectbox("Exibir", [20, 50, 100], key="rank_qtd")

    with col3:
        filtro = st.selectbox("Filtrar", ["Todos", "Com Pendencia", "Quitados"], key="rank_filtro")

    # Preparar dados
    df_rank = df.groupby('NOME_FORNECEDOR').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'NUMERO': 'count'
    }).reset_index()
    df_rank.columns = ['Fornecedor', 'Total', 'Pendente', 'Titulos']
    df_rank['Pago'] = df_rank['Total'] - df_rank['Pendente']
    df_rank['% Pago'] = ((df_rank['Pago']) / df_rank['Total'] * 100).round(1)

    # Classe ABC
    classes = _calcular_classe_abc(df)
    df_rank['Classe'] = df_rank['Fornecedor'].map(classes).fillna('C')

    # Filtrar
    if filtro == "Com Pendencia":
        df_rank = df_rank[df_rank['Pendente'] > 0]
    elif filtro == "Quitados":
        df_rank = df_rank[df_rank['Pendente'] <= 0]

    # Ordenar
    if ordenar == "Valor Total":
        df_rank = df_rank.sort_values('Total', ascending=False)
    elif ordenar == "Valor Pago":
        df_rank = df_rank.sort_values('Pago', ascending=False)
    else:
        df_rank = df_rank.sort_values('Pendente', ascending=False)

    df_rank = df_rank.head(qtd_exibir)

    # Formatar
    df_show = df_rank.copy()
    df_show['Total'] = df_show['Total'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Pago'] = df_show['Pago'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Pendente'] = df_show['Pendente'].apply(lambda x: formatar_moeda(x, completo=True))

    df_show = df_show[['Fornecedor', 'Classe', 'Total', 'Pago', 'Pendente', 'Titulos', '% Pago']]

    st.dataframe(
        df_show,
        use_container_width=True,
        hide_index=True,
        height=400,
        column_config={
            "% Pago": st.column_config.ProgressColumn(
                "% Pago",
                format="%.1f%%",
                min_value=0,
                max_value=100
            )
        }
    )

    st.caption(f"Exibindo {len(df_show)} fornecedores")
