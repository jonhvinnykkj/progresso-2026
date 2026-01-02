"""
Aba Filiais - Análise por filial
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from config.theme import get_cores
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero
from utils.data_helpers import get_df_vencidos


def render_filiais(df):
    """Renderiza a aba de Filiais"""
    cores = get_cores()

    # Verificar DataFrame vazio
    if len(df) == 0:
        st.warning("Nenhum dado disponivel para o periodo selecionado.")
        return

    # Calcular internamente
    df_vencidos = get_df_vencidos(df)

    st.markdown("### Analise por Filial")

    # Preparar dados
    df_fil = df.groupby('NOME_FILIAL').agg({
        'VALOR_ORIGINAL': ['sum', 'count'],
        'SALDO': 'sum',
        'FORNECEDOR': 'nunique'
    }).reset_index()

    df_fil.columns = ['Filial', 'Total', 'Qtd_Titulos', 'Pendente', 'Fornecedores']
    df_fil['Pago'] = df_fil['Total'] - df_fil['Pendente']
    df_fil['Pct_Pago'] = (df_fil['Pago'] / df_fil['Total'] * 100).fillna(0).round(1)
    df_fil = df_fil.sort_values('Total', ascending=False)

    # Calcular vencidos por filial
    if len(df_vencidos) > 0:
        df_venc_fil = df_vencidos.groupby('NOME_FILIAL').agg({
            'SALDO': 'sum',
            'DIAS_ATRASO': 'mean'
        }).reset_index()
        df_venc_fil.columns = ['Filial', 'Vencido', 'Atraso_Medio']
        df_fil = df_fil.merge(df_venc_fil, on='Filial', how='left').fillna(0)
    else:
        df_fil['Vencido'] = 0
        df_fil['Atraso_Medio'] = 0

    df_fil['Pct_Vencido'] = (df_fil['Vencido'] / df_fil['Total'] * 100).fillna(0).round(1)
    df_fil['Ticket_Medio'] = (df_fil['Total'] / df_fil['Qtd_Titulos']).fillna(0)

    # KPIs principais
    _render_kpis(df_fil)

    st.markdown("---")

    # Gráfico principal e resumo
    col1, col2 = st.columns([2, 1])

    with col1:
        _render_grafico_principal(df_fil, cores)

    with col2:
        _render_resumo_filiais(df_fil, cores)

    st.markdown("---")

    # Tabela detalhada
    _render_tabela(df_fil)


def _render_kpis(df_fil):
    """Renderiza KPIs principais"""
    total_filiais = len(df_fil)
    total_geral = df_fil['Total'].sum()
    total_pendente = df_fil['Pendente'].sum()
    total_vencido = df_fil['Vencido'].sum()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Filiais", formatar_numero(total_filiais))
    col2.metric("Volume Total", formatar_moeda(total_geral))
    col3.metric("Pendente", formatar_moeda(total_pendente))
    col4.metric("Vencido", formatar_moeda(total_vencido),
                delta=f"{(total_vencido/total_geral*100):.1f}%" if total_geral > 0 else "0%",
                delta_color="inverse")


def _render_grafico_principal(df_fil, cores):
    """Renderiza gráfico de barras horizontal empilhado"""
    st.markdown("##### Composição por Filial")

    fig = go.Figure()

    # Pago
    fig.add_trace(go.Bar(
        y=df_fil['Filial'],
        x=df_fil['Pago'],
        orientation='h',
        name='Pago',
        marker_color=cores['primaria'],
        text=[formatar_moeda(v) for v in df_fil['Pago']],
        textposition='inside',
        insidetextanchor='middle',
        textfont=dict(size=11, color='white')
    ))

    # A Vencer (Pendente - Vencido)
    a_vencer = (df_fil['Pendente'] - df_fil['Vencido']).clip(lower=0)
    fig.add_trace(go.Bar(
        y=df_fil['Filial'],
        x=a_vencer,
        orientation='h',
        name='A Vencer',
        marker_color=cores['alerta'],
        text=[formatar_moeda(v) if v > 0 else '' for v in a_vencer],
        textposition='inside',
        insidetextanchor='middle',
        textfont=dict(size=11, color='white')
    ))

    # Vencido
    fig.add_trace(go.Bar(
        y=df_fil['Filial'],
        x=df_fil['Vencido'],
        orientation='h',
        name='Vencido',
        marker_color=cores['perigo'],
        text=[formatar_moeda(v) if v > 0 else '' for v in df_fil['Vencido']],
        textposition='inside',
        insidetextanchor='middle',
        textfont=dict(size=11, color='white')
    ))

    # Calcular altura baseada no número de filiais
    altura = max(300, len(df_fil) * 40)

    fig.update_layout(
        criar_layout(altura, barmode='stack'),
        yaxis={'autorange': 'reversed', 'tickfont': {'size': 11}},
        xaxis_title='',
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='center',
            x=0.5
        ),
        margin=dict(l=10, r=10, t=30, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_resumo_filiais(df_fil, cores):
    """Renderiza resumo lateral com ranking"""
    st.markdown("##### Eficiência de Pagamento")

    df_rank = df_fil.sort_values('Pct_Pago', ascending=False).head(10)

    for _, row in df_rank.iterrows():
        pct = row['Pct_Pago']
        filial = row['Filial'][:20] if len(str(row['Filial'])) > 20 else row['Filial']

        # Definir cor do indicador
        if pct >= 80:
            cor = "🟢"
        elif pct >= 50:
            cor = "🟡"
        else:
            cor = "🔴"

        st.markdown(f"{cor} **{filial}** - {pct:.0f}%")
        st.progress(min(pct / 100, 1.0))

    # Média geral
    media = df_fil['Pct_Pago'].mean()
    st.markdown("---")
    st.markdown(f"**Média geral: {media:.1f}%**")


def _render_tabela(df_fil):
    """Renderiza tabela detalhada"""
    st.markdown("##### Detalhamento por Filial")

    # Preparar dados para exibição
    df_tabela = df_fil.copy()

    # Classificação
    def get_status(row):
        if row['Pct_Pago'] >= 80 and row['Pct_Vencido'] <= 10:
            return '🟢 Excelente'
        elif row['Pct_Pago'] >= 60 and row['Pct_Vencido'] <= 20:
            return '🟡 Bom'
        elif row['Pct_Pago'] >= 40:
            return '🟠 Regular'
        else:
            return '🔴 Crítico'

    df_tabela['Status'] = df_tabela.apply(get_status, axis=1)

    # Formatar colunas monetárias
    df_exibir = pd.DataFrame({
        'Filial': df_tabela['Filial'],
        'Total': df_tabela['Total'].apply(lambda x: formatar_moeda(x, completo=True)),
        'Pago': df_tabela['Pago'].apply(lambda x: formatar_moeda(x, completo=True)),
        'Pendente': df_tabela['Pendente'].apply(lambda x: formatar_moeda(x, completo=True)),
        'Vencido': df_tabela['Vencido'].apply(lambda x: formatar_moeda(x, completo=True)),
        'Títulos': df_tabela['Qtd_Titulos'],
        '% Pago': df_tabela['Pct_Pago'],
        '% Vencido': df_tabela['Pct_Vencido'],
        'Status': df_tabela['Status']
    })

    st.dataframe(
        df_exibir,
        use_container_width=True,
        hide_index=True,
        column_config={
            '% Pago': st.column_config.ProgressColumn(
                '% Pago',
                format='%.0f%%',
                min_value=0,
                max_value=100
            ),
            '% Vencido': st.column_config.ProgressColumn(
                '% Vencido',
                format='%.0f%%',
                min_value=0,
                max_value=100
            )
        }
    )
