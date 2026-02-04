"""
Aba Categorias - Analise completa por categoria com comportamento de pagamento
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

from config.theme import get_cores
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero
from utils.data_helpers import get_df_pendentes, get_df_vencidos
from config.settings import GRUPOS_FILIAIS, get_grupo_filial


def render_categorias(df):
    """Renderiza a aba de Categorias"""
    cores = get_cores()

    if len(df) == 0:
        st.warning("Nenhum dado disponivel.")
        return

    # Calcular dataframes
    df_pendentes = get_df_pendentes(df)
    df_vencidos = get_df_vencidos(df)
    df_pagos = df[df['SALDO'] == 0].copy()

    # Dados agregados por categoria
    df_cat = _preparar_dados_categoria(df, df_pagos)

    # ========== KPIs ==========
    _render_kpis(df_cat, df, df_pagos, df_vencidos, cores)

    st.divider()

    # ========== LINHA 1: Distribuicao ==========
    col1, col2 = st.columns(2)

    with col1:
        _render_treemap(df_cat, cores)

    with col2:
        _render_donut(df_cat, cores)

    st.divider()

    # ========== EVOLUCAO MENSAL ==========
    _render_evolucao_mensal(df, cores)

    st.divider()

    # ========== PARETO / ABC ==========
    _render_pareto_abc(df_cat, cores)

    st.divider()

    # ========== LINHA 2: Comportamento de Pagamento ==========
    col1, col2 = st.columns(2)

    with col1:
        _render_prazo_por_categoria(df_pagos, cores)

    with col2:
        _render_pontualidade_por_categoria(df_pagos, cores)

    st.divider()

    # ========== SAZONALIDADE ==========
    _render_sazonalidade(df, cores)

    st.divider()

    # ========== MATRIZ FILIAL x CATEGORIA ==========
    _render_matriz_filial_categoria(df, cores)

    st.divider()

    # ========== LINHA 3: Valor e Vencidos ==========
    col1, col2 = st.columns(2)

    with col1:
        _render_top_categorias(df_cat, cores)

    with col2:
        _render_vencidos_por_categoria(df_vencidos, cores)

    st.divider()

    # ========== BUSCA CATEGORIA ==========
    _render_busca_categoria(df, df_pagos, df_vencidos, cores)

    st.divider()

    # ========== RANKING ==========
    _render_ranking(df_cat, df_pagos, cores)


def _render_alertas(df, df_cat, df_pagos, cores):
    """Alertas e insights de categorias"""

    alertas = []
    hoje = datetime.now()

    # 1. Categoria com maior concentracao em um fornecedor
    for _, row in df_cat.head(10).iterrows():
        cat = row['Categoria']
        df_cat_forn = df[df['DESCRICAO'] == cat].groupby('NOME_FORNECEDOR')['VALOR_ORIGINAL'].sum()
        if len(df_cat_forn) > 0:
            total_cat = df_cat_forn.sum()
            maior_forn = df_cat_forn.idxmax()
            pct_maior = df_cat_forn.max() / total_cat * 100 if total_cat > 0 else 0
            if pct_maior > 60 and total_cat > 100000:
                alertas.append({
                    'tipo': 'warning',
                    'icone': '⚠️',
                    'titulo': 'Concentracao Fornecedor',
                    'msg': f'{cat[:20]}: {pct_maior:.0f}% em {maior_forn[:15]}'
                })
                break

    # 2. Crescimento anormal (>50% vs trimestre anterior)
    df_atual = df[df['EMISSAO'] >= hoje - timedelta(days=90)]
    df_anterior = df[(df['EMISSAO'] >= hoje - timedelta(days=180)) & (df['EMISSAO'] < hoje - timedelta(days=90))]

    if len(df_atual) > 0 and len(df_anterior) > 0:
        atual_grp = df_atual.groupby('DESCRICAO')['VALOR_ORIGINAL'].sum()
        anterior_grp = df_anterior.groupby('DESCRICAO')['VALOR_ORIGINAL'].sum()
        comparativo = pd.DataFrame({'atual': atual_grp, 'anterior': anterior_grp}).fillna(0)
        comparativo['crescimento'] = ((comparativo['atual'] - comparativo['anterior']) / comparativo['anterior'].replace(0, 1)) * 100
        crescimento_alto = comparativo[(comparativo['crescimento'] > 50) & (comparativo['atual'] > 100000)]
        if len(crescimento_alto) > 0:
            top_cresc = crescimento_alto.nlargest(1, 'crescimento')
            cat = top_cresc.index[0]
            pct = top_cresc['crescimento'].iloc[0]
            alertas.append({
                'tipo': 'success',
                'icone': '📈',
                'titulo': 'Crescimento Alto',
                'msg': f'{cat[:20]}: +{pct:.0f}% vs trimestre anterior'
            })

        # Queda significativa
        queda_alta = comparativo[(comparativo['crescimento'] < -30) & (comparativo['anterior'] > 100000)]
        if len(queda_alta) > 0:
            top_queda = queda_alta.nsmallest(1, 'crescimento')
            cat = top_queda.index[0]
            pct = top_queda['crescimento'].iloc[0]
            alertas.append({
                'tipo': 'info',
                'icone': '📉',
                'titulo': 'Reducao Significativa',
                'msg': f'{cat[:20]}: {pct:.0f}% vs trimestre anterior'
            })

    # 3. Categoria com pior pontualidade
    if len(df_pagos) > 0 and 'DIAS_ATRASO_PGTO' in df_pagos.columns:
        def calc_pont(group):
            atraso = group['DIAS_ATRASO_PGTO'].dropna()
            if len(atraso) < 10:
                return None
            return (atraso <= 0).sum() / len(atraso) * 100

        pont_por_cat = df_pagos.groupby('DESCRICAO').apply(calc_pont).dropna()
        if len(pont_por_cat) > 0:
            pior_pont = pont_por_cat.nsmallest(1)
            cat = pior_pont.index[0]
            taxa = pior_pont.iloc[0]
            if taxa < 50:
                alertas.append({
                    'tipo': 'error',
                    'icone': '⏰',
                    'titulo': 'Baixa Pontualidade',
                    'msg': f'{cat[:20]}: apenas {taxa:.0f}% no prazo'
                })

    if len(alertas) == 0:
        return

    st.markdown("##### Alertas e Insights")

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


def _preparar_dados_categoria(df, df_pagos):
    """Prepara dados agregados por categoria"""

    df_cat = df.groupby('DESCRICAO').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'FORNECEDOR': 'count',
        'NOME_FORNECEDOR': 'nunique',
        'NOME_FILIAL': 'nunique'
    }).reset_index()

    df_cat.columns = ['Categoria', 'Total', 'Pendente', 'Qtd', 'Fornecedores', 'Filiais']
    df_cat['Pago'] = df_cat['Total'] - df_cat['Pendente']
    df_cat['Pct_Pago'] = (df_cat['Pago'] / df_cat['Total'] * 100).fillna(0).round(1)
    df_cat = df_cat.sort_values('Total', ascending=False)

    return df_cat


def _render_kpis(df_cat, df, df_pagos, df_vencidos, cores):
    """KPIs principais"""

    total_categorias = len(df_cat)
    total_valor = df_cat['Total'].sum()
    total_vencido = df_vencidos['SALDO'].sum() if len(df_vencidos) > 0 else 0

    # Taxa pontualidade geral
    taxa_pontual = 0
    if len(df_pagos) > 0 and 'DIAS_ATRASO_PGTO' in df_pagos.columns:
        atraso = df_pagos['DIAS_ATRASO_PGTO'].dropna()
        if len(atraso) > 0:
            taxa_pontual = (atraso <= 0).sum() / len(atraso) * 100

    # Prazo medio geral
    prazo_medio = 0
    if len(df_pagos) > 0 and 'DIAS_PARA_PAGAR' in df_pagos.columns:
        prazo = df_pagos['DIAS_PARA_PAGAR'].dropna()
        if len(prazo) > 0:
            prazo_medio = prazo.mean()

    # Categorias com vencido
    cat_com_vencido = df_vencidos['DESCRICAO'].nunique() if len(df_vencidos) > 0 else 0

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            label="Total Categorias",
            value=formatar_numero(total_categorias),
            delta=f"{formatar_numero(df_cat['Qtd'].sum())} titulos",
            delta_color="off"
        )

    with col2:
        st.metric(
            label="Valor Total",
            value=formatar_moeda(total_valor),
            delta=f"Vencido: {formatar_moeda(total_vencido)}",
            delta_color="off"
        )

    with col3:
        st.metric(
            label="Taxa Pontualidade",
            value=f"{taxa_pontual:.1f}%",
            delta="pagos no prazo",
            delta_color="off"
        )

    with col4:
        st.metric(
            label="Prazo Medio Pgto",
            value=f"{prazo_medio:.0f} dias",
            delta="emissao ate pagamento",
            delta_color="off"
        )

    with col5:
        pct = (cat_com_vencido / total_categorias * 100) if total_categorias > 0 else 0
        st.metric(
            label="Cat. com Vencido",
            value=formatar_numero(cat_com_vencido),
            delta=f"{pct:.0f}% do total",
            delta_color="off"
        )


def _render_treemap(df_cat, cores):
    """Treemap de categorias"""

    st.markdown("##### Treemap - Distribuicao")

    df_tree = df_cat.head(15).copy()

    if len(df_tree) == 0:
        st.info("Sem dados")
        return

    fig = px.treemap(
        df_tree,
        path=['Categoria'],
        values='Total',
        color='Pct_Pago',
        color_continuous_scale='RdYlGn',
        hover_data={'Total': ':,.2f', 'Pendente': ':,.2f', 'Pct_Pago': ':.1f'}
    )

    fig.update_layout(
        criar_layout(300),
        coloraxis_colorbar=dict(title="% Pago", len=0.6),
        margin=dict(l=10, r=10, t=10, b=10)
    )

    fig.update_traces(
        textinfo='label+value',
        texttemplate='%{label}<br>R$ %{value:,.0f}',
        textfont=dict(size=11)
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_evolucao_mensal(df, cores):
    """Evolucao mensal das Top 5 categorias"""

    st.markdown("##### Evolucao Mensal - Top 5 Categorias")

    # Identificar top 5 categorias por valor total
    top5 = df.groupby('DESCRICAO')['VALOR_ORIGINAL'].sum().nlargest(5).index.tolist()

    if len(top5) == 0:
        st.info("Dados insuficientes")
        return

    # Filtrar e agrupar por mes
    df_top = df[df['DESCRICAO'].isin(top5)].copy()
    df_top['MES'] = df_top['EMISSAO'].dt.to_period('M').astype(str)

    df_pivot = df_top.pivot_table(
        values='VALOR_ORIGINAL',
        index='MES',
        columns='DESCRICAO',
        aggfunc='sum',
        fill_value=0
    ).reset_index()

    if len(df_pivot) < 2:
        st.info("Historico insuficiente")
        return

    fig = go.Figure()

    cores_linha = [cores['primaria'], cores['sucesso'], cores['alerta'], cores['info'], cores['perigo']]

    for i, cat in enumerate(top5):
        if cat in df_pivot.columns:
            fig.add_trace(go.Scatter(
                x=df_pivot['MES'],
                y=df_pivot[cat],
                name=cat[:20],
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


def _render_pareto_abc(df_cat, cores):
    """Analise Pareto / Curva ABC de categorias"""

    st.markdown("##### Analise ABC - Concentracao de Gastos")

    if len(df_cat) == 0:
        st.info("Sem dados")
        return

    df_pareto = df_cat[['Categoria', 'Total', 'Pendente', 'Qtd', 'Fornecedores']].copy()
    df_pareto = df_pareto.sort_values('Total', ascending=False).reset_index(drop=True)

    total_geral = df_pareto['Total'].sum()
    if total_geral == 0:
        st.info("Sem valores para analise")
        return

    df_pareto['Pct'] = df_pareto['Total'] / total_geral * 100
    df_pareto['Acumulado'] = df_pareto['Pct'].cumsum()

    # Classificacao ABC
    df_pareto['Classe'] = df_pareto['Acumulado'].apply(
        lambda x: 'A' if x <= 80 else ('B' if x <= 95 else 'C')
    )
    # A primeira categoria que cruza o limiar fica na classe anterior
    for i in range(len(df_pareto)):
        if i == 0:
            df_pareto.loc[i, 'Classe'] = 'A'
        elif df_pareto.loc[i - 1, 'Acumulado'] < 80:
            df_pareto.loc[i, 'Classe'] = 'A'
        elif df_pareto.loc[i - 1, 'Acumulado'] < 95:
            df_pareto.loc[i, 'Classe'] = 'B'
        else:
            df_pareto.loc[i, 'Classe'] = 'C'

    qtd_a = len(df_pareto[df_pareto['Classe'] == 'A'])
    qtd_b = len(df_pareto[df_pareto['Classe'] == 'B'])
    qtd_c = len(df_pareto[df_pareto['Classe'] == 'C'])
    val_a = df_pareto[df_pareto['Classe'] == 'A']['Total'].sum()
    val_b = df_pareto[df_pareto['Classe'] == 'B']['Total'].sum()
    val_c = df_pareto[df_pareto['Classe'] == 'C']['Total'].sum()

    # Cards ABC
    st.markdown(f"""
    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem; margin-bottom: 1rem;">
        <div style="background: {cores['perigo']}15; border: 1px solid {cores['perigo']}50;
                    border-radius: 10px; padding: 1rem; text-align: center;">
            <p style="color: {cores['perigo']}; font-size: 1.4rem; font-weight: 700; margin: 0;">Classe A</p>
            <p style="color: {cores['texto']}; font-size: 1.1rem; font-weight: 600; margin: 0.25rem 0;">
                {qtd_a} categorias</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0;">
                {formatar_moeda(val_a)} ({val_a/total_geral*100:.0f}% do total)</p>
        </div>
        <div style="background: {cores['alerta']}15; border: 1px solid {cores['alerta']}50;
                    border-radius: 10px; padding: 1rem; text-align: center;">
            <p style="color: {cores['alerta']}; font-size: 1.4rem; font-weight: 700; margin: 0;">Classe B</p>
            <p style="color: {cores['texto']}; font-size: 1.1rem; font-weight: 600; margin: 0.25rem 0;">
                {qtd_b} categorias</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0;">
                {formatar_moeda(val_b)} ({val_b/total_geral*100:.0f}% do total)</p>
        </div>
        <div style="background: {cores['sucesso']}15; border: 1px solid {cores['sucesso']}50;
                    border-radius: 10px; padding: 1rem; text-align: center;">
            <p style="color: {cores['sucesso']}; font-size: 1.4rem; font-weight: 700; margin: 0;">Classe C</p>
            <p style="color: {cores['texto']}; font-size: 1.1rem; font-weight: 600; margin: 0.25rem 0;">
                {qtd_c} categorias</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0;">
                {formatar_moeda(val_c)} ({val_c/total_geral*100:.0f}% do total)</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Grafico Pareto (top 20 para nao poluir)
    df_plot = df_pareto.head(20)

    cor_classe = {'A': cores['perigo'], 'B': cores['alerta'], 'C': cores['sucesso']}
    bar_colors = [cor_classe[c] for c in df_plot['Classe']]

    fig = go.Figure()

    # Barras de valor
    fig.add_trace(go.Bar(
        x=df_plot['Categoria'].str[:18],
        y=df_plot['Total'],
        name='Valor',
        marker_color=bar_colors,
        text=[formatar_moeda(v) for v in df_plot['Total']],
        textposition='outside',
        textfont=dict(size=8, color=cores['texto']),
        yaxis='y'
    ))

    # Linha acumulada
    fig.add_trace(go.Scatter(
        x=df_plot['Categoria'].str[:18],
        y=df_plot['Acumulado'],
        name='% Acumulado',
        mode='lines+markers+text',
        line=dict(color=cores['texto'], width=2),
        marker=dict(size=5),
        text=[f"{v:.0f}%" for v in df_plot['Acumulado']],
        textposition='top center',
        textfont=dict(size=8, color=cores['texto']),
        yaxis='y2'
    ))

    # Linhas de referencia 80% e 95%
    fig.add_hline(y=80, line_dash="dot", line_color=cores['perigo'], line_width=1,
                  annotation_text="80% (A)", annotation_position="right",
                  annotation_font=dict(size=9, color=cores['perigo']),
                  yref='y2')
    fig.add_hline(y=95, line_dash="dot", line_color=cores['alerta'], line_width=1,
                  annotation_text="95% (B)", annotation_position="right",
                  annotation_font=dict(size=9, color=cores['alerta']),
                  yref='y2')

    fig.update_layout(
        criar_layout(350),
        margin=dict(l=10, r=50, t=10, b=80),
        xaxis=dict(tickangle=-45, tickfont=dict(size=8, color=cores['texto'])),
        yaxis=dict(showticklabels=False, showgrid=False, title=None),
        yaxis2=dict(overlaying='y', side='right', range=[0, 105], showgrid=False,
                    tickfont=dict(size=9, color=cores['texto']), title=None),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1,
                    font=dict(size=9, color=cores['texto'])),
        showlegend=True
    )

    st.plotly_chart(fig, use_container_width=True)

    # Tabela resumo ABC
    with st.expander("Ver detalhes da classificacao ABC"):
        df_abc = df_pareto[['Categoria', 'Total', 'Pct', 'Acumulado', 'Classe', 'Qtd', 'Fornecedores']].copy()
        df_abc['Total'] = df_abc['Total'].apply(formatar_moeda)
        df_abc['Pct'] = df_abc['Pct'].apply(lambda x: f"{x:.1f}%")
        df_abc['Acumulado'] = df_abc['Acumulado'].apply(lambda x: f"{x:.1f}%")
        df_abc.columns = ['Categoria', 'Valor', '% Individual', '% Acumulado', 'Classe', 'Titulos', 'Fornecedores']
        st.dataframe(df_abc, use_container_width=True, hide_index=True, height=400)


def _render_sazonalidade(df, cores):
    """Analise de sazonalidade por categoria"""

    st.markdown("##### Sazonalidade - Padrao Mensal")

    # Top 6 categorias
    top6 = df.groupby('DESCRICAO')['VALOR_ORIGINAL'].sum().nlargest(6).index.tolist()

    if len(top6) == 0:
        st.info("Dados insuficientes")
        return

    col1, col2 = st.columns([1, 3])

    with col1:
        categoria_sel = st.selectbox(
            "Categoria",
            options=top6,
            key='sazon_cat'
        )

    df_cat = df[df['DESCRICAO'] == categoria_sel].copy()
    df_cat['MES_NUM'] = df_cat['EMISSAO'].dt.month

    # Agrupar por mes do ano (media historica)
    df_sazon = df_cat.groupby('MES_NUM')['VALOR_ORIGINAL'].mean().reset_index()
    df_sazon['MES_NOME'] = df_sazon['MES_NUM'].map({
        1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
        7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'
    })

    with col2:
        if len(df_sazon) < 3:
            st.info("Historico insuficiente para analise de sazonalidade")
            return

        # Identificar meses de pico e baixa
        media_geral = df_sazon['VALOR_ORIGINAL'].mean()
        df_sazon['DESVIO'] = ((df_sazon['VALOR_ORIGINAL'] - media_geral) / media_geral * 100)

        # Cores baseadas no desvio
        def cor_sazon(desvio):
            if desvio > 20:
                return cores['perigo']
            elif desvio > 10:
                return cores['alerta']
            elif desvio < -20:
                return cores['info']
            elif desvio < -10:
                return cores['sucesso']
            return cores['texto_secundario']

        bar_colors = [cor_sazon(d) for d in df_sazon['DESVIO']]

        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=df_sazon['MES_NOME'],
            y=df_sazon['VALOR_ORIGINAL'],
            marker_color=bar_colors,
            text=[f"{d:+.0f}%" for d in df_sazon['DESVIO']],
            textposition='outside',
            textfont=dict(size=9, color=cores['texto'])
        ))

        # Linha de media
        fig.add_hline(
            y=media_geral,
            line_dash="dash",
            line_color=cores['texto'],
            line_width=1,
            annotation_text="Media",
            annotation_position="right"
        )

        fig.update_layout(
            criar_layout(250),
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis=dict(tickfont=dict(size=10, color=cores['texto'])),
            yaxis=dict(showticklabels=False, showgrid=False)
        )

        st.plotly_chart(fig, use_container_width=True)

        # Insights
        meses_pico = df_sazon[df_sazon['DESVIO'] > 15]['MES_NOME'].tolist()
        meses_baixa = df_sazon[df_sazon['DESVIO'] < -15]['MES_NOME'].tolist()

        col_a, col_b = st.columns(2)
        if meses_pico:
            col_a.caption(f"📈 Picos: {', '.join(meses_pico)}")
        if meses_baixa:
            col_b.caption(f"📉 Baixas: {', '.join(meses_baixa)}")


def _get_nome_grupo_cat(cod_filial):
    grupo_id = get_grupo_filial(int(cod_filial))
    return GRUPOS_FILIAIS.get(grupo_id, f"Grupo {grupo_id}")

def _detectar_multiplos_grupos_cat(df):
    if 'FILIAL' not in df.columns or len(df) == 0:
        return False
    grupos = df['FILIAL'].dropna().apply(lambda x: get_grupo_filial(int(x))).nunique()
    return grupos > 1


def _render_matriz_filial_categoria(df, cores):
    """Matriz Filial x Categoria (Heatmap)"""

    multiplos = _detectar_multiplos_grupos_cat(df)

    # Top 10 categorias
    top10_cat = df.groupby('DESCRICAO')['VALOR_ORIGINAL'].sum().nlargest(10).index.tolist()

    if len(top10_cat) == 0 or 'NOME_FILIAL' not in df.columns:
        st.info("Dados insuficientes")
        return

    # Filtrar e criar pivot
    df_matriz = df[df['DESCRICAO'].isin(top10_cat)].copy()

    if multiplos:
        st.markdown("##### Matriz Grupo x Categoria")
        df_matriz['GRUPO'] = df_matriz['FILIAL'].apply(lambda x: _get_nome_grupo_cat(x))
        pivot = df_matriz.pivot_table(
            values='VALOR_ORIGINAL',
            index='GRUPO',
            columns='DESCRICAO',
            aggfunc='sum',
            fill_value=0
        )
    else:
        st.markdown("##### Matriz Filial x Categoria")
        df_matriz['FILIAL_LABEL'] = df_matriz['FILIAL'].astype(int).astype(str) + ' - ' + df_matriz['NOME_FILIAL'].str.split(' - ').str[-1].str.strip()
        pivot = df_matriz.pivot_table(
            values='VALOR_ORIGINAL',
            index='FILIAL_LABEL',
            columns='DESCRICAO',
            aggfunc='sum',
            fill_value=0
        )

    if pivot.empty:
        st.info("Dados insuficientes para matriz")
        return

    # Heatmap
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=[f[:18] for f in pivot.columns],
        y=[f[:25] for f in pivot.index],
        colorscale=[
            [0, cores['fundo']],
            [0.5, cores['info']],
            [1, cores['primaria']]
        ],
        hovertemplate='Filial: %{y}<br>Categoria: %{x}<br>Valor: R$ %{z:,.0f}<extra></extra>'
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
        # Categoria mais concentrada em uma filial
        for cat in top10_cat[:5]:
            if cat in pivot.columns:
                total_cat = pivot[cat].sum()
                if total_cat > 0:
                    max_filial = pivot[cat].idxmax()
                    pct_max = pivot[cat].max() / total_cat * 100
                    if pct_max > 60:
                        st.caption(f"⚠️ **{cat[:25]}**: {pct_max:.0f}% concentrado em {max_filial}")


def _render_donut(df_cat, cores):
    """Donut das top 8 categorias"""

    st.markdown("##### Top 8 Categorias")

    df_top = df_cat.head(8).copy()
    outros = df_cat.iloc[8:]['Total'].sum() if len(df_cat) > 8 else 0

    if outros > 0:
        df_top = pd.concat([df_top, pd.DataFrame([{
            'Categoria': 'Outros',
            'Total': outros
        }])], ignore_index=True)

    if len(df_top) == 0:
        st.info("Sem dados")
        return

    fig = go.Figure(go.Pie(
        labels=df_top['Categoria'].str[:20],
        values=df_top['Total'],
        hole=0.5,
        textinfo='percent',
        textfont=dict(size=10),
        hovertemplate='<b>%{label}</b><br>R$ %{value:,.2f}<br>%{percent}<extra></extra>'
    ))

    total = df_cat['Total'].sum()
    fig.add_annotation(
        text=f"<b>{formatar_moeda(total)}</b>",
        x=0.5, y=0.5,
        font=dict(size=14, color=cores['texto']),
        showarrow=False
    )

    fig.update_layout(
        criar_layout(300),
        showlegend=True,
        legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02, font=dict(size=9)),
        margin=dict(l=10, r=100, t=10, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_prazo_por_categoria(df_pagos, cores):
    """Prazo medio por categoria"""

    st.markdown("##### Prazo Medio por Categoria")

    if len(df_pagos) == 0 or 'DIAS_PARA_PAGAR' not in df_pagos.columns:
        st.info("Sem dados de pagamento")
        return

    df_prazo = df_pagos.groupby('DESCRICAO').agg({
        'DIAS_PARA_PAGAR': 'mean',
        'VALOR_ORIGINAL': 'sum'
    }).reset_index()
    df_prazo.columns = ['Categoria', 'Prazo', 'Valor']
    df_prazo = df_prazo.dropna(subset=['Prazo'])

    # Top 10 com maior prazo
    df_top = df_prazo.nlargest(10, 'Prazo')

    def cor_prazo(p):
        if p <= 30:
            return cores['sucesso']
        elif p <= 45:
            return cores['info']
        elif p <= 60:
            return cores['alerta']
        return cores['perigo']

    bar_colors = [cor_prazo(p) for p in df_top['Prazo']]

    fig = go.Figure(go.Bar(
        y=df_top['Categoria'].str[:25],
        x=df_top['Prazo'],
        orientation='h',
        marker_color=bar_colors,
        text=[f"{p:.0f}d" for p in df_top['Prazo']],
        textposition='outside',
        textfont=dict(size=10)
    ))

    fig.update_layout(
        criar_layout(300),
        yaxis={'autorange': 'reversed'},
        margin=dict(l=10, r=50, t=10, b=10),
        xaxis_title='Dias'
    )

    st.plotly_chart(fig, use_container_width=True)
    st.caption("Categorias com maior prazo de pagamento")


def _render_pontualidade_por_categoria(df_pagos, cores):
    """Pontualidade por categoria"""

    st.markdown("##### Pontualidade por Categoria")

    if len(df_pagos) == 0 or 'DIAS_ATRASO_PGTO' not in df_pagos.columns:
        st.info("Sem dados de pagamento")
        return

    def calc_pontualidade(group):
        atraso = group['DIAS_ATRASO_PGTO'].dropna()
        if len(atraso) < 5:  # Minimo 5 para ser estatisticamente relevante
            return pd.Series({'Pontualidade': None, 'Qtd': len(atraso)})
        pontual = (atraso <= 0).sum() / len(atraso) * 100
        return pd.Series({'Pontualidade': pontual, 'Qtd': len(atraso)})

    df_pont = df_pagos.groupby('DESCRICAO').apply(calc_pontualidade).reset_index()
    df_pont = df_pont.dropna(subset=['Pontualidade'])

    if len(df_pont) == 0:
        st.info("Dados insuficientes (min. 5 pagamentos)")
        return

    # Top 10 com pior pontualidade
    df_piores = df_pont.nsmallest(10, 'Pontualidade')

    def cor_pont(p):
        if p >= 80:
            return cores['sucesso']
        elif p >= 60:
            return cores['info']
        elif p >= 40:
            return cores['alerta']
        return cores['perigo']

    bar_colors = [cor_pont(p) for p in df_piores['Pontualidade']]

    fig = go.Figure(go.Bar(
        y=df_piores['DESCRICAO'].str[:25],
        x=df_piores['Pontualidade'],
        orientation='h',
        marker_color=bar_colors,
        text=[f"{p:.0f}%" for p in df_piores['Pontualidade']],
        textposition='outside',
        textfont=dict(size=10)
    ))

    fig.update_layout(
        criar_layout(300),
        yaxis={'autorange': 'reversed'},
        margin=dict(l=10, r=50, t=10, b=10),
        xaxis_title='% Pontualidade',
        xaxis=dict(range=[0, 105])
    )

    st.plotly_chart(fig, use_container_width=True)
    st.caption("Categorias com pior pontualidade (min. 5 pagamentos)")


def _render_top_categorias(df_cat, cores):
    """Top 10 categorias - Pago vs Pendente"""

    st.markdown("##### Top 10 - Pago vs Pendente")

    df_top = df_cat.head(10)

    if len(df_top) == 0:
        st.info("Sem dados")
        return

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=df_top['Categoria'].str[:25],
        x=df_top['Pago'],
        orientation='h',
        name='Pago',
        marker_color=cores['sucesso'],
        text=[formatar_moeda(v) for v in df_top['Pago']],
        textposition='inside',
        textfont=dict(size=9, color='white')
    ))

    fig.add_trace(go.Bar(
        y=df_top['Categoria'].str[:25],
        x=df_top['Pendente'],
        orientation='h',
        name='Pendente',
        marker_color=cores['alerta'],
        text=[formatar_moeda(v) for v in df_top['Pendente']],
        textposition='inside',
        textfont=dict(size=9, color='white')
    ))

    fig.update_layout(
        criar_layout(300, barmode='stack'),
        yaxis={'autorange': 'reversed'},
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=30, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_vencidos_por_categoria(df_vencidos, cores):
    """Vencidos por categoria"""

    st.markdown("##### Vencidos por Categoria")

    if len(df_vencidos) == 0:
        st.success("Nenhum titulo vencido!")
        return

    df_venc = df_vencidos.groupby('DESCRICAO').agg({
        'SALDO': 'sum',
        'DIAS_ATRASO': 'mean',
        'VALOR_ORIGINAL': 'count'
    }).nlargest(10, 'SALDO').reset_index()
    df_venc.columns = ['Categoria', 'Valor', 'Atraso_Medio', 'Qtd']

    def cor_atraso(d):
        if d > 30:
            return cores['perigo']
        elif d > 15:
            return '#f97316'
        return cores['alerta']

    bar_colors = [cor_atraso(d) for d in df_venc['Atraso_Medio']]

    fig = go.Figure(go.Bar(
        y=df_venc['Categoria'].str[:25],
        x=df_venc['Valor'],
        orientation='h',
        marker_color=bar_colors,
        text=[f"{formatar_moeda(v)} ({d:.0f}d)" for v, d in zip(df_venc['Valor'], df_venc['Atraso_Medio'])],
        textposition='outside',
        textfont=dict(size=9)
    ))

    fig.update_layout(
        criar_layout(300),
        yaxis={'autorange': 'reversed'},
        margin=dict(l=10, r=80, t=10, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)
    st.caption("Cor indica atraso medio (amarelo < 15d, laranja < 30d, vermelho > 30d)")


def _render_busca_categoria(df, df_pagos, df_vencidos, cores):
    """Busca e detalhes de categoria"""

    st.markdown("##### Consultar Categoria")

    categorias = sorted(df['DESCRICAO'].unique().tolist())

    categoria_sel = st.selectbox(
        "Selecione uma categoria",
        options=[""] + categorias,
        key="busca_cat"
    )

    if not categoria_sel:
        return

    df_sel = df[df['DESCRICAO'] == categoria_sel]
    df_pago_sel = df_pagos[df_pagos['DESCRICAO'] == categoria_sel]
    df_venc_sel = df_vencidos[df_vencidos['DESCRICAO'] == categoria_sel]

    # Metricas financeiras
    total_valor = df_sel['VALOR_ORIGINAL'].sum()
    total_pendente = df_sel['SALDO'].sum()
    total_pago = total_valor - total_pendente
    total_vencido = df_venc_sel['SALDO'].sum() if len(df_venc_sel) > 0 else 0

    # Metricas de pagamento
    prazo_medio = 0
    taxa_pontual = 0
    if len(df_pago_sel) > 0:
        if 'DIAS_PARA_PAGAR' in df_pago_sel.columns:
            prazo = df_pago_sel['DIAS_PARA_PAGAR'].dropna()
            if len(prazo) > 0:
                prazo_medio = prazo.mean()

        if 'DIAS_ATRASO_PGTO' in df_pago_sel.columns:
            atraso = df_pago_sel['DIAS_ATRASO_PGTO'].dropna()
            if len(atraso) > 0:
                taxa_pontual = (atraso <= 0).sum() / len(atraso) * 100

    # Linha 1: Metricas financeiras
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Valor Total", formatar_moeda(total_valor), f"{len(df_sel)} titulos")
    col2.metric("Pago", formatar_moeda(total_pago))
    col3.metric("Pendente", formatar_moeda(total_pendente))
    col4.metric("Vencido", formatar_moeda(total_vencido))

    # Linha 2: Metricas de comportamento
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Prazo Medio Pgto", f"{prazo_medio:.0f} dias")
    col2.metric("Taxa Pontualidade", f"{taxa_pontual:.1f}%")
    col3.metric("Fornecedores", df_sel['NOME_FORNECEDOR'].nunique())
    col4.metric("Filiais", df_sel['NOME_FILIAL'].nunique())

    # Tabs
    tab1, tab2, tab3 = st.tabs(["Por Fornecedor", "Por Filial", "Titulos"])

    with tab1:
        df_forn = df_sel.groupby('NOME_FORNECEDOR').agg({
            'VALOR_ORIGINAL': 'sum',
            'SALDO': 'sum'
        }).nlargest(10, 'VALOR_ORIGINAL').reset_index()

        if len(df_forn) > 0:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                y=df_forn['NOME_FORNECEDOR'].str[:20],
                x=df_forn['VALOR_ORIGINAL'] - df_forn['SALDO'],
                orientation='h',
                name='Pago',
                marker_color=cores['sucesso']
            ))
            fig.add_trace(go.Bar(
                y=df_forn['NOME_FORNECEDOR'].str[:20],
                x=df_forn['SALDO'],
                orientation='h',
                name='Pendente',
                marker_color=cores['alerta']
            ))
            fig.update_layout(
                criar_layout(250, barmode='stack'),
                yaxis={'autorange': 'reversed'},
                margin=dict(l=10, r=10, t=10, b=10)
            )
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        multiplos_busca = _detectar_multiplos_grupos_cat(df_sel)
        if multiplos_busca:
            df_fil = df_sel.copy()
            df_fil['GRUPO'] = df_fil['FILIAL'].apply(lambda x: _get_nome_grupo_cat(x))
            df_fil = df_fil.groupby('GRUPO').agg({
                'VALOR_ORIGINAL': 'sum',
                'SALDO': 'sum'
            }).reset_index()
            pie_labels = df_fil['GRUPO']
        else:
            df_fil = df_sel.copy()
            df_fil['FILIAL_LABEL'] = df_fil['FILIAL'].astype(int).astype(str) + ' - ' + df_fil['NOME_FILIAL'].str.split(' - ').str[-1].str.strip()
            df_fil = df_fil.groupby('FILIAL_LABEL').agg({
                'VALOR_ORIGINAL': 'sum',
                'SALDO': 'sum'
            }).reset_index()
            pie_labels = df_fil['FILIAL_LABEL']

        if len(df_fil) > 0:
            fig = go.Figure(go.Pie(
                labels=pie_labels,
                values=df_fil['VALOR_ORIGINAL'],
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

    with tab3:
        colunas = ['NOME_FILIAL', 'NOME_FORNECEDOR', 'NUMERO', 'EMISSAO', 'VENCIMENTO', 'DT_BAIXA', 'DIAS_PARA_PAGAR', 'VALOR_ORIGINAL', 'SALDO', 'STATUS']
        colunas_disp = [c for c in colunas if c in df_sel.columns]
        df_tab = df_sel[colunas_disp].nlargest(50, 'VALOR_ORIGINAL').copy()

        for col in ['EMISSAO', 'VENCIMENTO', 'DT_BAIXA']:
            if col in df_tab.columns:
                df_tab[col] = pd.to_datetime(df_tab[col], errors='coerce').dt.strftime('%d/%m/%Y')
                df_tab[col] = df_tab[col].fillna('-')

        df_tab['VALOR_ORIGINAL'] = df_tab['VALOR_ORIGINAL'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab['SALDO'] = df_tab['SALDO'].apply(lambda x: formatar_moeda(x, completo=True))

        if 'DIAS_PARA_PAGAR' in df_tab.columns:
            df_tab['DIAS_PARA_PAGAR'] = df_tab['DIAS_PARA_PAGAR'].apply(lambda x: f"{int(x)}d" if pd.notna(x) else '-')

        nomes = {
            'NOME_FILIAL': 'Filial',
            'NOME_FORNECEDOR': 'Fornecedor',
            'NUMERO': 'NF/Doc',
            'EMISSAO': 'Emissao',
            'VENCIMENTO': 'Vencimento',
            'DT_BAIXA': 'Dt Pagto',
            'DIAS_PARA_PAGAR': 'Dias p/ Pagar',
            'VALOR_ORIGINAL': 'Valor',
            'SALDO': 'Saldo',
            'STATUS': 'Status'
        }
        df_tab.columns = [nomes.get(c, c) for c in df_tab.columns]

        st.dataframe(df_tab, use_container_width=True, hide_index=True, height=300)


def _render_ranking(df_cat, df_pagos, cores):
    """Ranking completo"""

    st.markdown("##### Ranking de Categorias")

    # Filtros
    col1, col2, col3 = st.columns(3)
    with col1:
        ordenar = st.selectbox(
            "Ordenar por",
            ["Valor Total", "Saldo Pendente", "Prazo Medio", "Pontualidade"],
            key="cat_ordem"
        )
    with col2:
        qtd_exibir = st.selectbox("Exibir", [15, 30, 50], key="cat_qtd")
    with col3:
        filtro = st.selectbox("Filtrar", ["Todas", "Com Pendencia", "Quitadas"], key="cat_filtro")

    # Adicionar metricas de pagamento
    df_rank = df_cat.copy()

    if len(df_pagos) > 0:
        def calc_metricas(cat):
            df_c = df_pagos[df_pagos['DESCRICAO'] == cat]
            if len(df_c) == 0:
                return pd.Series({'Prazo': None, 'Pontualidade': None})

            prazo = None
            pont = None

            if 'DIAS_PARA_PAGAR' in df_c.columns:
                p = df_c['DIAS_PARA_PAGAR'].dropna()
                if len(p) > 0:
                    prazo = p.mean()

            if 'DIAS_ATRASO_PGTO' in df_c.columns:
                a = df_c['DIAS_ATRASO_PGTO'].dropna()
                if len(a) > 0:
                    pont = (a <= 0).sum() / len(a) * 100

            return pd.Series({'Prazo': prazo, 'Pontualidade': pont})

        metricas = df_rank['Categoria'].apply(calc_metricas)
        df_rank = pd.concat([df_rank, metricas], axis=1)
    else:
        df_rank['Prazo'] = None
        df_rank['Pontualidade'] = None

    # Filtrar
    if filtro == "Com Pendencia":
        df_rank = df_rank[df_rank['Pendente'] > 0]
    elif filtro == "Quitadas":
        df_rank = df_rank[df_rank['Pendente'] <= 0]

    # Ordenar
    if ordenar == "Valor Total":
        df_rank = df_rank.sort_values('Total', ascending=False)
    elif ordenar == "Saldo Pendente":
        df_rank = df_rank.sort_values('Pendente', ascending=False)
    elif ordenar == "Prazo Medio":
        df_rank = df_rank.sort_values('Prazo', ascending=False, na_position='last')
    else:
        df_rank = df_rank.sort_values('Pontualidade', ascending=True, na_position='last')

    df_rank = df_rank.head(qtd_exibir)

    # Formatar
    df_show = df_rank[['Categoria', 'Total', 'Pendente', 'Qtd', 'Fornecedores', 'Prazo', 'Pontualidade', 'Pct_Pago']].copy()
    df_show['Total'] = df_show['Total'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Pendente'] = df_show['Pendente'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Prazo'] = df_show['Prazo'].apply(lambda x: f"{x:.0f}d" if pd.notna(x) else '-')
    df_show['Pontualidade'] = df_show['Pontualidade'].apply(lambda x: f"{x:.0f}%" if pd.notna(x) else '-')
    df_show.columns = ['Categoria', 'Total', 'Pendente', 'Titulos', 'Fornecedores', 'Prazo', 'Pontualidade', '% Pago']

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

    st.caption(f"Exibindo {len(df_show)} categorias")
