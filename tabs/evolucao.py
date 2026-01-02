"""
Aba Evolução - Análise temporal avançada
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

from config.theme import get_cores
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero
from utils.data_helpers import get_df_pendentes


def render_evolucao(df):
    """Renderiza a aba de Evolucao Temporal"""
    cores = get_cores()

    if len(df) == 0:
        st.warning("Nenhum dado disponivel para analise de evolucao.")
        return

    # Calcular internamente
    df_pendentes = get_df_pendentes(df)

    # KPIs de Tendencia
    _render_kpis_tendencia(df, cores)

    st.divider()

    # Seletor de periodo
    periodo = st.radio("Agrupar por:", ["Mes", "Trimestre", "Ano"], horizontal=True)
    df_tempo = _preparar_dados_temporais(df, periodo)

    # Linha 1: Evolucao + Tendencia
    col1, col2 = st.columns(2)

    with col1:
        _render_evolucao_valores(df_tempo, periodo, cores)

    with col2:
        _render_taxa_pagamento(df_tempo, periodo, cores)

    st.divider()

    # Linha 2: Comparativo Anual + Heatmap
    col1, col2 = st.columns(2)

    with col1:
        _render_comparativo_anual(df, cores)

    with col2:
        _render_heatmap_mensal(df, cores)

    st.divider()

    # Linha 3: Sazonalidade + Projecao
    col1, col2 = st.columns(2)

    with col1:
        _render_sazonalidade(df, cores)

    with col2:
        _render_projecao_fluxo(df_pendentes, cores)

    st.divider()

    # Tabela de resumo mensal
    _render_tabela_resumo(df, cores)


def _render_kpis_tendencia(df_contas, cores):
    """KPIs de tendência e variação"""

    hoje = datetime.now()
    mes_atual = hoje.replace(day=1)
    mes_anterior = (mes_atual - timedelta(days=1)).replace(day=1)

    # Calcular valores do mês atual e anterior
    periodo_atual = pd.Period(hoje, freq='M')
    periodo_anterior = pd.Period(mes_anterior, freq='M')

    df_mes_atual = df_contas[df_contas['EMISSAO'].dt.to_period('M') == periodo_atual]
    df_mes_anterior = df_contas[df_contas['EMISSAO'].dt.to_period('M') == periodo_anterior]

    valor_mes_atual = df_mes_atual['VALOR_ORIGINAL'].sum()
    valor_mes_anterior = df_mes_anterior['VALOR_ORIGINAL'].sum()

    # Variação MoM
    if valor_mes_anterior > 0:
        var_mom = ((valor_mes_atual - valor_mes_anterior) / valor_mes_anterior) * 100
    else:
        var_mom = 0

    # Calcular YoY (mesmo mês ano anterior)
    ano_anterior = hoje.year - 1
    df_mesmo_mes_ano_ant = df_contas[
        (df_contas['EMISSAO'].dt.year == ano_anterior) &
        (df_contas['EMISSAO'].dt.month == hoje.month)
    ]
    valor_ano_anterior = df_mesmo_mes_ano_ant['VALOR_ORIGINAL'].sum()

    if valor_ano_anterior > 0:
        var_yoy = ((valor_mes_atual - valor_ano_anterior) / valor_ano_anterior) * 100
    else:
        var_yoy = 0

    # Média mensal dos últimos 6 meses
    ultimos_6m = df_contas[df_contas['EMISSAO'] >= (hoje - timedelta(days=180))]
    media_6m = ultimos_6m.groupby(ultimos_6m['EMISSAO'].dt.to_period('M'))['VALOR_ORIGINAL'].sum().mean()
    media_6m = media_6m if pd.notna(media_6m) else 0

    # Taxa de pagamento média
    total_original = df_contas['VALOR_ORIGINAL'].sum()
    total_pago = total_original - df_contas['SALDO'].sum()
    taxa_pgto = (total_pago / total_original * 100) if total_original > 0 else 0

    # Tendência (crescente/decrescente baseado nos últimos 3 meses)
    ultimos_3m = df_contas[df_contas['EMISSAO'] >= (hoje - timedelta(days=90))]
    valores_3m = ultimos_3m.groupby(ultimos_3m['EMISSAO'].dt.to_period('M'))['VALOR_ORIGINAL'].sum()
    if len(valores_3m) >= 2:
        tendencia = "📈 Crescente" if valores_3m.iloc[-1] > valores_3m.iloc[0] else "📉 Decrescente"
    else:
        tendencia = "➡️ Estável"

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        delta_mom = f"{var_mom:+.1f}%" if var_mom != 0 else "—"
        st.metric(
            label="📅 Mês Atual",
            value=formatar_moeda(valor_mes_atual),
            delta=f"vs mês anterior: {delta_mom}",
            delta_color="inverse" if var_mom > 0 else "normal"
        )

    with col2:
        delta_yoy = f"{var_yoy:+.1f}%" if var_yoy != 0 else "—"
        st.metric(
            label="📊 Variação Anual",
            value=delta_yoy,
            delta="vs mesmo mês ano anterior",
            delta_color="off"
        )

    with col3:
        st.metric(
            label="📈 Média Mensal (6M)",
            value=formatar_moeda(media_6m),
            delta="Últimos 6 meses",
            delta_color="off"
        )

    with col4:
        st.metric(
            label="✅ Taxa de Pagamento",
            value=f"{taxa_pgto:.1f}%",
            delta="Geral",
            delta_color="off"
        )

    with col5:
        st.metric(
            label="📉 Tendência",
            value=tendencia,
            delta="Últimos 3 meses",
            delta_color="off"
        )


def _preparar_dados_temporais(df_contas, periodo):
    """Prepara dados agrupados por período"""
    if len(df_contas) == 0:
        return pd.DataFrame(columns=['EMISSAO', 'VALOR_ORIGINAL', 'SALDO', 'PAGO'])

    if periodo == "Mês":
        df_tempo = df_contas.groupby(df_contas['EMISSAO'].dt.to_period('M')).agg({
            'VALOR_ORIGINAL': 'sum',
            'SALDO': 'sum',
            'FORNECEDOR': 'count'
        }).reset_index()
        df_tempo['EMISSAO'] = df_tempo['EMISSAO'].astype(str)
        df_tempo = df_tempo.tail(12)

    elif periodo == "Trimestre":
        df_contas_copy = df_contas.copy()
        df_contas_copy['TRIM'] = df_contas_copy['EMISSAO'].dt.year.astype(str) + '-Q' + df_contas_copy['TRIMESTRE'].astype(str)
        df_tempo = df_contas_copy.groupby('TRIM').agg({
            'VALOR_ORIGINAL': 'sum',
            'SALDO': 'sum',
            'FORNECEDOR': 'count'
        }).reset_index()
        df_tempo.columns = ['EMISSAO', 'VALOR_ORIGINAL', 'SALDO', 'FORNECEDOR']
        df_tempo = df_tempo.tail(8)

    else:  # Ano
        df_tempo = df_contas.groupby('ANO').agg({
            'VALOR_ORIGINAL': 'sum',
            'SALDO': 'sum',
            'FORNECEDOR': 'count'
        }).reset_index()
        df_tempo['ANO'] = df_tempo['ANO'].astype(int).astype(str)
        df_tempo.columns = ['EMISSAO', 'VALOR_ORIGINAL', 'SALDO', 'FORNECEDOR']

    df_tempo['PAGO'] = df_tempo['VALOR_ORIGINAL'] - df_tempo['SALDO']
    df_tempo['PCT_PAGO'] = (df_tempo['PAGO'] / df_tempo['VALOR_ORIGINAL'] * 100).fillna(0)
    return df_tempo


def _render_evolucao_valores(df_tempo, periodo, cores):
    """Renderiza gráfico de evolução de valores"""

    st.markdown(f"##### 💰 Evolução de Valores por {periodo}")

    if len(df_tempo) == 0:
        st.info("Sem dados para exibir")
        return

    fig = go.Figure()

    # Barras empilhadas
    fig.add_trace(go.Bar(
        x=df_tempo['EMISSAO'],
        y=df_tempo['PAGO'],
        name='Pago',
        marker_color=cores['sucesso'],
        text=[formatar_moeda(v) for v in df_tempo['PAGO']],
        textposition='inside',
        textfont=dict(size=9, color='white')
    ))

    fig.add_trace(go.Bar(
        x=df_tempo['EMISSAO'],
        y=df_tempo['SALDO'],
        name='Pendente',
        marker_color=cores['alerta'],
        text=[formatar_moeda(v) for v in df_tempo['SALDO']],
        textposition='inside',
        textfont=dict(size=9, color='white')
    ))

    # Linha de média móvel (3 períodos)
    if len(df_tempo) >= 3:
        df_tempo['MM3'] = df_tempo['VALOR_ORIGINAL'].rolling(window=3, min_periods=1).mean()
        fig.add_trace(go.Scatter(
            x=df_tempo['EMISSAO'],
            y=df_tempo['MM3'],
            name='Média Móvel (3)',
            mode='lines+markers',
            line=dict(color=cores['texto'], width=2, dash='dot'),
            marker=dict(size=6)
        ))

    fig.update_layout(
        criar_layout(300, barmode='stack'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=30, b=40),
        xaxis_tickangle=-45
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_taxa_pagamento(df_tempo, periodo, cores):
    """Renderiza evolução da taxa de pagamento"""

    st.markdown(f"##### 📊 Taxa de Pagamento por {periodo}")

    if len(df_tempo) == 0:
        st.info("Sem dados para exibir")
        return

    # Definir cores baseadas na taxa
    def get_bar_color(pct):
        if pct >= 80:
            return cores['sucesso']
        elif pct >= 50:
            return cores['alerta']
        else:
            return cores['perigo']

    bar_colors = [get_bar_color(p) for p in df_tempo['PCT_PAGO']]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df_tempo['EMISSAO'],
        y=df_tempo['PCT_PAGO'],
        marker_color=bar_colors,
        text=[f"{p:.1f}%" for p in df_tempo['PCT_PAGO']],
        textposition='outside',
        textfont=dict(size=10),
        hovertemplate='<b>%{x}</b><br>Taxa: %{y:.1f}%<extra></extra>'
    ))

    # Linha de referência 80%
    fig.add_hline(y=80, line_dash="dash", line_color=cores['sucesso'],
                  annotation_text="Meta 80%", annotation_position="right")

    fig.update_layout(
        criar_layout(300),
        yaxis=dict(range=[0, 105], title="% Pago"),
        margin=dict(l=10, r=10, t=10, b=40),
        xaxis_tickangle=-45
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_comparativo_anual(df_contas, cores):
    """Comparativo mês a mês entre anos"""

    st.markdown("##### 📅 Comparativo Ano vs Ano Anterior")

    anos = sorted(df_contas['EMISSAO'].dt.year.unique())

    if len(anos) < 2:
        st.info("Necessário dados de pelo menos 2 anos para comparativo")
        return

    ano_atual = anos[-1]
    ano_anterior = anos[-2]

    # Agrupar por mês para cada ano
    df_atual = df_contas[df_contas['EMISSAO'].dt.year == ano_atual]
    df_anterior = df_contas[df_contas['EMISSAO'].dt.year == ano_anterior]

    meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

    valores_atual = df_atual.groupby(df_atual['EMISSAO'].dt.month)['VALOR_ORIGINAL'].sum()
    valores_anterior = df_anterior.groupby(df_anterior['EMISSAO'].dt.month)['VALOR_ORIGINAL'].sum()

    # Criar DataFrame completo
    df_comp = pd.DataFrame({
        'MES_NUM': range(1, 13),
        'MES': meses
    })
    df_comp[str(ano_anterior)] = df_comp['MES_NUM'].map(valores_anterior).fillna(0)
    df_comp[str(ano_atual)] = df_comp['MES_NUM'].map(valores_atual).fillna(0)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df_comp['MES'],
        y=df_comp[str(ano_anterior)],
        name=str(ano_anterior),
        marker_color=cores['info'],
        opacity=0.7
    ))

    fig.add_trace(go.Bar(
        x=df_comp['MES'],
        y=df_comp[str(ano_atual)],
        name=str(ano_atual),
        marker_color=cores['primaria']
    ))

    fig.update_layout(
        criar_layout(300, barmode='group'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=30, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_heatmap_mensal(df_contas, cores):
    """Renderiza heatmap mês x ano"""

    st.markdown("##### 🗓️ Heatmap Mensal")

    df_heat = df_contas.copy()
    df_heat['MES_NUM'] = df_heat['EMISSAO'].dt.month
    df_heat['ANO_NUM'] = df_heat['EMISSAO'].dt.year

    pivot = df_heat.pivot_table(
        values='VALOR_ORIGINAL',
        index='MES_NUM',
        columns='ANO_NUM',
        aggfunc='sum',
        fill_value=0
    )

    if pivot.empty:
        st.info("Sem dados para heatmap")
        return

    meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
             'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

    # Formatar valores para hover
    hover_text = [[formatar_moeda(val) for val in row] for row in pivot.values]

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=[str(int(c)) for c in pivot.columns],
        y=[meses[int(i)-1] for i in pivot.index],
        colorscale='Greens',
        text=hover_text,
        texttemplate="%{text}",
        textfont={"size": 9},
        hovertemplate='<b>%{y} %{x}</b><br>%{text}<extra></extra>'
    ))

    fig.update_layout(
        criar_layout(300),
        margin=dict(l=10, r=10, t=10, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_sazonalidade(df_contas, cores):
    """Análise de sazonalidade por mês"""

    st.markdown("##### 📈 Padrão Sazonal (Média por Mês)")

    meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
             'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

    df_saz = df_contas.copy()
    df_saz['MES'] = df_saz['EMISSAO'].dt.month

    # Média por mês (considerando todos os anos)
    media_mes = df_saz.groupby('MES')['VALOR_ORIGINAL'].mean()
    media_geral = media_mes.mean()

    # Criar DataFrame para o gráfico
    df_media = pd.DataFrame({
        'MES_NUM': range(1, 13),
        'MES': meses,
        'MEDIA': [media_mes.get(i, 0) for i in range(1, 13)]
    })

    # Definir cores (acima/abaixo da média)
    bar_colors = [cores['primaria'] if v >= media_geral else cores['info'] for v in df_media['MEDIA']]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df_media['MES'],
        y=df_media['MEDIA'],
        marker_color=bar_colors,
        text=[formatar_moeda(v) for v in df_media['MEDIA']],
        textposition='outside',
        textfont=dict(size=8),
        hovertemplate='<b>%{x}</b><br>Média: %{text}<extra></extra>'
    ))

    # Linha de média geral
    fig.add_hline(y=media_geral, line_dash="dash", line_color=cores['texto'],
                  annotation_text=f"Média: {formatar_moeda(media_geral)}")

    fig.update_layout(
        criar_layout(300),
        margin=dict(l=10, r=10, t=10, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_projecao_fluxo(df_pendentes, cores):
    """Renderiza projeção de fluxo de caixa"""

    st.markdown("##### 💸 Projeção - Próximos 30 Dias")

    if len(df_pendentes) == 0:
        st.info("Sem dados para projeção")
        return

    hoje = datetime.now()
    df_proj = df_pendentes[df_pendentes['VENCIMENTO'].notna()].copy()
    df_proj = df_proj[(df_proj['VENCIMENTO'] >= hoje) & (df_proj['VENCIMENTO'] <= hoje + timedelta(days=30))]

    if len(df_proj) == 0:
        st.info("Nenhum vencimento nos próximos 30 dias")
        return

    # Agrupar por dia
    df_proj['DIA'] = df_proj['VENCIMENTO'].dt.date
    df_grp = df_proj.groupby('DIA').agg({
        'SALDO': 'sum',
        'FORNECEDOR': 'count'
    }).reset_index()
    df_grp['ACUMULADO'] = df_grp['SALDO'].cumsum()

    fig = go.Figure()

    # Barras de valor diário
    fig.add_trace(go.Bar(
        x=df_grp['DIA'],
        y=df_grp['SALDO'],
        name='Valor Diário',
        marker_color=cores['primaria'],
        text=[formatar_moeda(v) for v in df_grp['SALDO']],
        textposition='outside',
        textfont=dict(size=8)
    ))

    # Linha acumulada
    fig.add_trace(go.Scatter(
        x=df_grp['DIA'],
        y=df_grp['ACUMULADO'],
        name='Acumulado',
        mode='lines+markers',
        line=dict(color=cores['perigo'], width=3),
        yaxis='y2'
    ))

    fig.update_layout(
        criar_layout(300),
        yaxis2=dict(overlaying='y', side='right', showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=40, t=30, b=40),
        xaxis_tickangle=-45,
        xaxis=dict(tickformat='%d/%m')
    )

    st.plotly_chart(fig, use_container_width=True)

    # Resumo
    total_30d = df_grp['SALDO'].sum()
    qtd_titulos = df_proj['FORNECEDOR'].count()
    st.caption(f"Total a vencer: **{formatar_moeda(total_30d)}** em **{qtd_titulos}** títulos")


def _render_tabela_resumo(df_contas, cores):
    """Tabela de resumo mensal"""

    st.markdown("##### 📋 Resumo Mensal")

    # Preparar dados
    df_resumo = df_contas.copy()
    df_resumo['MES_ANO'] = df_resumo['EMISSAO'].dt.to_period('M')

    df_grp = df_resumo.groupby('MES_ANO').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'FORNECEDOR': 'count',
        'NOME_FORNECEDOR': 'nunique'
    }).reset_index()

    df_grp.columns = ['Período', 'Total', 'Pendente', 'Títulos', 'Fornecedores']
    df_grp['Pago'] = df_grp['Total'] - df_grp['Pendente']
    df_grp['% Pago'] = (df_grp['Pago'] / df_grp['Total'] * 100).round(1)

    # Ordenar do mais recente para o mais antigo
    df_grp = df_grp.sort_values('Período', ascending=False).head(12)
    df_grp['Período'] = df_grp['Período'].astype(str)

    # Formatar valores
    df_show = df_grp.copy()
    df_show['Total'] = df_show['Total'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Pendente'] = df_show['Pendente'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Pago'] = df_show['Pago'].apply(lambda x: formatar_moeda(x, completo=True))

    st.dataframe(
        df_show[['Período', 'Total', 'Pago', 'Pendente', '% Pago', 'Títulos', 'Fornecedores']],
        use_container_width=True,
        hide_index=True,
        height=350,
        column_config={
            "% Pago": st.column_config.ProgressColumn(
                "% Pago",
                format="%.1f%%",
                min_value=0,
                max_value=100,
            ),
        }
    )
