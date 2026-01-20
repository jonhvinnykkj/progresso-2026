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

    # ========== EVOLUCAO TOP 5 ==========
    _render_evolucao_top5(df, cores)

    st.divider()

    # ========== PRAZOS DE PAGAMENTO ==========
    _render_prazos_pagamento(df, cores)

    st.divider()

    # ========== CURVA ABC + CONCENTRACAO ==========
    col1, col2 = st.columns(2)

    with col1:
        _render_curva_abc(df, cores)

    with col2:
        _render_concentracao(df, cores)

    st.divider()

    # ========== NOVOS E INATIVOS ==========
    col1, col2 = st.columns(2)

    with col1:
        _render_novos_fornecedores(df, cores)

    with col2:
        _render_inativos(df, cores)

    st.divider()

    # ========== MATRIZ FILIAL x FORNECEDOR ==========
    _render_matriz_filial_fornecedor(df, cores)

    st.divider()

    # ========== POR CATEGORIA ==========
    _render_por_categoria(df, cores)

    st.divider()

    # ========== TOP PENDENTES ==========
    _render_top_pendentes(df, cores)

    st.divider()

    # ========== CONSULTA FORNECEDOR ==========
    _render_consulta_fornecedor(df, cores)

    st.divider()

    # ========== RANKING ==========
    _render_ranking(df, cores)


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

    col1, col2, col3, col4, col5 = st.columns(5)

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


def _render_evolucao_top5(df, cores):
    """Evolucao mensal dos Top 5 fornecedores"""

    st.markdown("##### Evolucao Mensal - Top 5 Fornecedores")

    # Identificar top 5 fornecedores por valor total
    top5 = df.groupby('NOME_FORNECEDOR')['VALOR_ORIGINAL'].sum().nlargest(5).index.tolist()

    if len(top5) == 0:
        st.info("Dados insuficientes")
        return

    # Filtrar e agrupar por mes
    df_top = df[df['NOME_FORNECEDOR'].isin(top5)].copy()
    df_top['MES'] = df_top['EMISSAO'].dt.to_period('M').astype(str)

    df_pivot = df_top.pivot_table(
        values='VALOR_ORIGINAL',
        index='MES',
        columns='NOME_FORNECEDOR',
        aggfunc='sum',
        fill_value=0
    ).reset_index()

    if len(df_pivot) < 2:
        st.info("Historico insuficiente para mostrar evolucao")
        return

    fig = go.Figure()

    cores_linha = [cores['primaria'], cores['sucesso'], cores['alerta'], cores['info'], cores['perigo']]

    for i, forn in enumerate(top5):
        if forn in df_pivot.columns:
            fig.add_trace(go.Scatter(
                x=df_pivot['MES'],
                y=df_pivot[forn],
                name=forn[:20],
                mode='lines+markers',
                line=dict(color=cores_linha[i % len(cores_linha)], width=2),
                marker=dict(size=6)
            ))

    fig.update_layout(
        criar_layout(300),
        margin=dict(l=10, r=10, t=10, b=40),
        xaxis=dict(tickangle=-45, tickfont=dict(size=9, color=cores['texto'])),
        yaxis=dict(showticklabels=False, showgrid=True, gridcolor=cores['borda']),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1,
            font=dict(size=9, color=cores['texto'])
        ),
        hovermode='x unified'
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_novos_fornecedores(df, cores):
    """Fornecedores novos (primeira compra recente)"""

    st.markdown("##### Novos Fornecedores")

    hoje = datetime.now()

    # Encontrar primeira compra de cada fornecedor
    df_primeira = df.groupby('NOME_FORNECEDOR').agg({
        'EMISSAO': 'min',
        'VALOR_ORIGINAL': 'sum',
        'NUMERO': 'count'
    }).reset_index()
    df_primeira.columns = ['Fornecedor', 'Primeira Compra', 'Valor Total', 'Qtd']

    # Filtros
    periodo = st.selectbox(
        "Periodo",
        ['Ultimos 30 dias', 'Ultimos 60 dias', 'Ultimos 90 dias'],
        key='novos_periodo'
    )

    dias = {'Ultimos 30 dias': 30, 'Ultimos 60 dias': 60, 'Ultimos 90 dias': 90}[periodo]
    limite = hoje - timedelta(days=dias)

    df_novos = df_primeira[df_primeira['Primeira Compra'] >= limite].copy()
    df_novos = df_novos.sort_values('Valor Total', ascending=False)

    if len(df_novos) == 0:
        st.info(f"Nenhum fornecedor novo nos {periodo.lower()}")
        return

    # Metricas
    st.metric(
        "Total de Novos",
        f"{len(df_novos)} fornecedores",
        f"{formatar_moeda(df_novos['Valor Total'].sum())} total"
    )

    # Tabela
    df_show = df_novos.head(10).copy()
    df_show['Primeira Compra'] = df_show['Primeira Compra'].dt.strftime('%d/%m/%Y')
    df_show['Valor Total'] = df_show['Valor Total'].apply(lambda x: formatar_moeda(x, completo=True))

    st.dataframe(
        df_show[['Fornecedor', 'Primeira Compra', 'Valor Total', 'Qtd']],
        use_container_width=True,
        hide_index=True,
        height=250
    )


def _render_inativos(df, cores):
    """Fornecedores inativos (sem compras recentes)"""

    st.markdown("##### Fornecedores Inativos")

    hoje = datetime.now()

    # Encontrar ultima compra de cada fornecedor
    df_ultima = df.groupby('NOME_FORNECEDOR').agg({
        'EMISSAO': 'max',
        'VALOR_ORIGINAL': 'sum',
        'NUMERO': 'count'
    }).reset_index()
    df_ultima.columns = ['Fornecedor', 'Ultima Compra', 'Valor Historico', 'Qtd']

    # Filtros
    periodo = st.selectbox(
        "Sem compras ha",
        ['Mais de 60 dias', 'Mais de 90 dias', 'Mais de 180 dias'],
        key='inativos_periodo'
    )

    dias = {'Mais de 60 dias': 60, 'Mais de 90 dias': 90, 'Mais de 180 dias': 180}[periodo]
    limite = hoje - timedelta(days=dias)

    df_inativos = df_ultima[df_ultima['Ultima Compra'] < limite].copy()
    df_inativos['Dias Inativo'] = (hoje - df_inativos['Ultima Compra']).dt.days
    df_inativos = df_inativos.sort_values('Valor Historico', ascending=False)

    if len(df_inativos) == 0:
        st.success(f"Nenhum fornecedor inativo ha {periodo.lower().replace('mais de ', '')}")
        return

    # Metricas
    st.metric(
        "Total de Inativos",
        f"{len(df_inativos)} fornecedores",
        f"{formatar_moeda(df_inativos['Valor Historico'].sum())} historico"
    )

    # Tabela
    df_show = df_inativos.head(10).copy()
    df_show['Ultima Compra'] = df_show['Ultima Compra'].dt.strftime('%d/%m/%Y')
    df_show['Valor Historico'] = df_show['Valor Historico'].apply(lambda x: formatar_moeda(x, completo=True))

    st.dataframe(
        df_show[['Fornecedor', 'Ultima Compra', 'Dias Inativo', 'Valor Historico']],
        use_container_width=True,
        hide_index=True,
        height=250
    )


def _render_matriz_filial_fornecedor(df, cores):
    """Matriz de relacionamento Filial x Fornecedor"""

    st.markdown("##### Matriz Filial x Fornecedor")

    # Top 10 fornecedores
    top10_forn = df.groupby('NOME_FORNECEDOR')['VALOR_ORIGINAL'].sum().nlargest(10).index.tolist()

    if len(top10_forn) == 0 or 'NOME_FILIAL' not in df.columns:
        st.info("Dados insuficientes")
        return

    # Filtrar e criar pivot
    df_matriz = df[df['NOME_FORNECEDOR'].isin(top10_forn)].copy()

    pivot = df_matriz.pivot_table(
        values='VALOR_ORIGINAL',
        index='NOME_FILIAL',
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
        # Fornecedor mais concentrado em uma filial
        for forn in top10_forn[:5]:
            if forn in pivot.columns:
                total_forn = pivot[forn].sum()
                if total_forn > 0:
                    max_filial = pivot[forn].idxmax()
                    pct_max = pivot[forn].max() / total_forn * 100
                    if pct_max > 70:
                        st.caption(f"⚠️ **{forn[:30]}**: {pct_max:.0f}% concentrado em {max_filial}")


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
            delta="emissao → vencimento",
            delta_color="off"
        )

    with col2:
        st.metric(
            label="Prazo Medio Real",
            value=f"{prazo_medio_real:.0f} dias" if pd.notna(prazo_medio_real) and prazo_medio_real > 0 else "N/A",
            delta="emissao → pagamento",
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
    """Curva ABC de fornecedores"""

    st.markdown("##### Curva ABC")

    df_abc = df.groupby('NOME_FORNECEDOR')['VALOR_ORIGINAL'].sum().sort_values(ascending=False).reset_index()
    total = df_abc['VALOR_ORIGINAL'].sum()
    df_abc['PCT'] = df_abc['VALOR_ORIGINAL'] / total * 100
    df_abc['PCT_ACUM'] = df_abc['PCT'].cumsum()
    df_abc['RANK'] = range(1, len(df_abc) + 1)

    df_abc['CLASSE'] = df_abc['PCT_ACUM'].apply(
        lambda x: 'A' if x <= 80 else ('B' if x <= 95 else 'C')
    )

    # Estatisticas
    qtd_a = len(df_abc[df_abc['CLASSE'] == 'A'])
    qtd_b = len(df_abc[df_abc['CLASSE'] == 'B'])
    qtd_c = len(df_abc[df_abc['CLASSE'] == 'C'])

    fig = go.Figure()

    cores_abc = {'A': cores['primaria'], 'B': cores['alerta'], 'C': cores['texto_secundario']}

    # Barras (top 25)
    df_show = df_abc.head(25)
    fig.add_trace(go.Bar(
        x=df_show['RANK'],
        y=df_show['VALOR_ORIGINAL'],
        name='Valor',
        marker_color=[cores_abc[c] for c in df_show['CLASSE']]
    ))

    # Linha % acumulado
    fig.add_trace(go.Scatter(
        x=df_show['RANK'],
        y=df_show['PCT_ACUM'],
        name='% Acumulado',
        mode='lines+markers',
        line=dict(color=cores['texto'], width=2),
        marker=dict(size=4),
        yaxis='y2'
    ))

    # Linhas de referencia
    fig.add_hline(y=80, line_dash="dash", line_color=cores['sucesso'], line_width=1, yref='y2')
    fig.add_hline(y=95, line_dash="dash", line_color=cores['alerta'], line_width=1, yref='y2')

    fig.update_layout(
        criar_layout(280),
        yaxis=dict(showticklabels=False, showgrid=False),
        yaxis2=dict(overlaying='y', side='right', range=[0, 105], showgrid=False,
                    tickfont=dict(size=9, color=cores['texto'])),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(size=9, color=cores['texto'])),
        margin=dict(l=10, r=40, t=30, b=30),
        xaxis=dict(title='Rank', tickfont=dict(size=9, color=cores['texto']))
    )

    st.plotly_chart(fig, use_container_width=True)

    # Resumo
    col1, col2, col3 = st.columns(3)
    col1.markdown(f"**A (80%):** {qtd_a} forn.")
    col2.markdown(f"**B (15%):** {qtd_b} forn.")
    col3.markdown(f"**C (5%):** {qtd_c} forn.")


def _render_concentracao(df, cores):
    """Analise de concentracao de fornecedores"""

    st.markdown("##### Concentracao")

    total = df['VALOR_ORIGINAL'].sum()
    df_forn = df.groupby('NOME_FORNECEDOR')['VALOR_ORIGINAL'].sum().sort_values(ascending=False)

    # Calcular concentracao em diferentes niveis
    concentracoes = []
    for n in [1, 5, 10, 20, 50]:
        if n <= len(df_forn):
            valor_top = df_forn.head(n).sum()
            pct = valor_top / total * 100
            concentracoes.append({'Top': f'Top {n}', 'Valor': valor_top, 'Pct': pct, 'N': n})

    df_conc = pd.DataFrame(concentracoes)

    # Grafico de barras
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df_conc['Top'],
        y=df_conc['Pct'],
        marker_color=[cores['perigo'], cores['alerta'], '#f97316', cores['info'], cores['sucesso']][:len(df_conc)],
        text=[f"{p:.1f}%" for p in df_conc['Pct']],
        textposition='outside',
        textfont=dict(size=11, color=cores['texto'])
    ))

    fig.update_layout(
        criar_layout(280),
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(tickfont=dict(size=10, color=cores['texto'])),
        yaxis=dict(showticklabels=False, showgrid=False, range=[0, 110])
    )

    st.plotly_chart(fig, use_container_width=True)

    # Detalhes
    st.markdown("**Maiores fornecedores:**")
    for i, (forn, valor) in enumerate(df_forn.head(5).items()):
        pct = valor / total * 100
        st.caption(f"{i+1}. {forn[:40]} - {formatar_moeda(valor)} ({pct:.1f}%)")


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

        # Pago
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

        # Pendente
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


def _render_top_pendentes(df, cores):
    """Top fornecedores com maior saldo pendente"""

    st.markdown("##### Top 15 - Maior Saldo Pendente")

    # Filtrar apenas com saldo pendente
    df_pend = df[df['SALDO'] > 0].copy()

    if len(df_pend) == 0:
        st.success("Nenhum fornecedor com saldo pendente!")
        return

    df_forn = df_pend.groupby('NOME_FORNECEDOR').agg({
        'SALDO': 'sum',
        'NUMERO': 'count'
    }).reset_index()
    df_forn.columns = ['Fornecedor', 'Pendente', 'Qtd']
    df_forn = df_forn.nlargest(15, 'Pendente')
    df_forn = df_forn.sort_values('Pendente', ascending=True)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=df_forn['Fornecedor'].str[:35],
        x=df_forn['Pendente'],
        orientation='h',
        marker_color=cores['alerta'],
        text=[f"{formatar_moeda(v)} ({int(q)} tit.)" for v, q in zip(df_forn['Pendente'], df_forn['Qtd'])],
        textposition='outside',
        textfont=dict(size=9, color=cores['texto'])
    ))

    fig.update_layout(
        criar_layout(420),
        margin=dict(l=10, r=120, t=10, b=10),
        xaxis=dict(showticklabels=False, showgrid=False),
        yaxis=dict(tickfont=dict(size=10, color=cores['texto']))
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_consulta_fornecedor(df, cores):
    """Consulta detalhada de fornecedor"""

    st.markdown("##### Consultar Fornecedor")

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

    # Metricas
    total_valor = df_forn['VALOR_ORIGINAL'].sum()
    total_pendente = df_forn['SALDO'].sum()
    total_pago = total_valor - total_pendente
    qtd_titulos = len(df_forn)
    pct_pago = (total_pago / total_valor * 100) if total_valor > 0 else 0

    # Cards
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Valor Total", formatar_moeda(total_valor), f"{qtd_titulos} titulos")
    col2.metric("Pago", formatar_moeda(total_pago), f"{pct_pago:.1f}%")
    col3.metric("Pendente", formatar_moeda(total_pendente))

    # Categorias do fornecedor
    if 'DESCRICAO' in df_forn.columns:
        cats = df_forn.groupby('DESCRICAO')['VALOR_ORIGINAL'].sum().nlargest(3)
        cats_str = ", ".join([f"{c[:15]}" for c in cats.index])
        col4.metric("Principais Categorias", cats_str[:30])

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
        colunas = ['NOME_FILIAL', 'DESCRICAO', 'EMISSAO', 'VENCIMENTO', 'VALOR_ORIGINAL', 'SALDO']
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

    df_show = df_show[['Fornecedor', 'Total', 'Pago', 'Pendente', 'Titulos', '% Pago']]

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
