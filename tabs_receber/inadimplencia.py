"""
Aba Inadimplencia - Analise detalhada de atrasos e aging
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

from config.theme import get_cores
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero


def render_inadimplencia(df):
    """Renderiza a aba de Inadimplencia"""
    cores = get_cores()

    if len(df) == 0:
        st.warning("Nenhum dado disponivel.")
        return

    df = df.copy()
    hoje = datetime.now()

    # Separar dados
    df_pendentes = df[df['SALDO'] > 0]
    df_recebidos = df[df['SALDO'] == 0]
    df_vencidos = df[df['STATUS'] == 'Vencido']

    # ========== KPIs PRINCIPAIS ==========
    total_saldo = df_pendentes['SALDO'].sum()
    total_vencido = df_vencidos['SALDO'].sum()
    taxa_inadimplencia = (total_vencido / total_saldo * 100) if total_saldo > 0 else 0
    qtd_vencidos = len(df_vencidos)
    dias_atraso_medio = df_vencidos['DIAS_ATRASO'].mean() if len(df_vencidos) > 0 else 0

    # Taxa de recebimento geral
    total_original = df['VALOR_ORIGINAL'].sum()
    total_recebido = total_original - df['SALDO'].sum()
    taxa_recebimento = (total_recebido / total_original * 100) if total_original > 0 else 0

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric(
        "Taxa Inadimplencia",
        f"{taxa_inadimplencia:.1f}%",
        f"{formatar_moeda(total_vencido)} vencido",
        delta_color="inverse"
    )

    col2.metric(
        "Titulos Vencidos",
        formatar_numero(qtd_vencidos),
        f"de {formatar_numero(len(df_pendentes))} pendentes"
    )

    col3.metric(
        "Atraso Medio",
        f"{dias_atraso_medio:.0f} dias",
        "titulos vencidos"
    )

    col4.metric(
        "Taxa Recebimento",
        f"{taxa_recebimento:.1f}%",
        formatar_moeda(total_recebido)
    )

    col5.metric(
        "Saldo Pendente",
        formatar_moeda(total_saldo),
        f"{len(df_pendentes)} titulos"
    )

    # Alertas
    if taxa_inadimplencia > 30:
        st.error(f"CRITICO: Taxa de inadimplencia em {taxa_inadimplencia:.1f}%! Acoes urgentes necessarias.")
    elif taxa_inadimplencia > 15:
        st.warning(f"ALERTA: Taxa de inadimplencia em {taxa_inadimplencia:.1f}%. Monitorar de perto.")
    elif taxa_inadimplencia > 5:
        st.info(f"Atencao: Taxa de inadimplencia em {taxa_inadimplencia:.1f}%.")

    st.divider()

    # ========== AGING DETALHADO ==========
    st.markdown(f"""
    <div style="background: {cores['card']}; border-left: 4px solid {cores['perigo']};
                padding: 0.75rem 1rem; border-radius: 0 8px 8px 0; margin-bottom: 1rem;">
        <h4 style="color: {cores['texto']}; margin: 0;">Aging de Recebiveis</h4>
        <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0;">
            Distribuicao por faixa de vencimento
        </p>
    </div>
    """, unsafe_allow_html=True)

    _render_aging_detalhado(df_pendentes, cores)

    st.divider()

    # ========== EVOLUCAO TEMPORAL ==========
    col1, col2 = st.columns(2)

    with col1:
        _render_evolucao_inadimplencia(df, cores)

    with col2:
        _render_aging_por_filial(df_vencidos, cores)

    st.divider()

    # ========== ANALISE POR CATEGORIA ==========
    _render_inadimplencia_categoria(df, df_vencidos, cores)

    st.divider()

    # ========== TITULOS MAIS ANTIGOS ==========
    _render_titulos_criticos(df_vencidos, cores)


def _render_aging_detalhado(df_pendentes, cores):
    """Aging detalhado com faixas de vencimento"""

    if len(df_pendentes) == 0:
        st.info("Nenhum titulo pendente para analise de aging.")
        return

    # Definir faixas de aging
    faixas = [
        ('A Vencer', df_pendentes['DIAS_VENC'] > 0, cores['sucesso']),
        ('Vencido 1-7 dias', (df_pendentes['DIAS_VENC'] <= 0) & (df_pendentes['DIAS_VENC'] > -7), cores['info']),
        ('Vencido 8-15 dias', (df_pendentes['DIAS_VENC'] <= -7) & (df_pendentes['DIAS_VENC'] > -15), '#8b5cf6'),
        ('Vencido 16-30 dias', (df_pendentes['DIAS_VENC'] <= -15) & (df_pendentes['DIAS_VENC'] > -30), cores['alerta']),
        ('Vencido 31-60 dias', (df_pendentes['DIAS_VENC'] <= -30) & (df_pendentes['DIAS_VENC'] > -60), '#f97316'),
        ('Vencido 61-90 dias', (df_pendentes['DIAS_VENC'] <= -60) & (df_pendentes['DIAS_VENC'] > -90), cores['perigo']),
        ('Vencido +90 dias', df_pendentes['DIAS_VENC'] <= -90, '#991b1b')
    ]

    dados = []
    for nome, mask, cor in faixas:
        df_faixa = df_pendentes[mask]
        qtd = len(df_faixa)
        valor = df_faixa['SALDO'].sum()
        dados.append({
            'Faixa': nome,
            'Qtd': qtd,
            'Valor': valor,
            'Cor': cor
        })

    df_aging = pd.DataFrame(dados)
    total_valor = df_aging['Valor'].sum()
    df_aging['Pct'] = df_aging['Valor'] / total_valor * 100 if total_valor > 0 else 0

    col1, col2 = st.columns(2)

    with col1:
        # Grafico de barras
        st.markdown("##### Distribuicao por Faixa")

        fig = go.Figure(go.Bar(
            x=df_aging['Faixa'],
            y=df_aging['Valor'],
            marker_color=df_aging['Cor'],
            text=[f"{formatar_moeda(v)}<br>({p:.1f}%)" for v, p in zip(df_aging['Valor'], df_aging['Pct'])],
            textposition='outside',
            textfont=dict(size=9)
        ))

        fig.update_layout(
            criar_layout(350),
            xaxis_tickangle=-45,
            margin=dict(l=10, r=10, t=10, b=100)
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Tabela de aging
        st.markdown("##### Resumo Aging")

        df_show = df_aging[['Faixa', 'Qtd', 'Valor', 'Pct']].copy()
        df_show['Valor'] = df_show['Valor'].apply(lambda x: formatar_moeda(x, completo=True))
        df_show['Pct'] = df_show['Pct'].apply(lambda x: f"{x:.1f}%")
        df_show.columns = ['Faixa', 'Qtd Titulos', 'Valor', '% do Total']

        st.dataframe(df_show, use_container_width=True, hide_index=True, height=300)

        # Total vencido
        total_vencido = df_aging[df_aging['Faixa'] != 'A Vencer']['Valor'].sum()
        st.metric("Total Vencido", formatar_moeda(total_vencido))


def _render_evolucao_inadimplencia(df, cores):
    """Evolucao mensal da inadimplencia"""
    st.markdown("##### Evolucao Mensal")

    df_temp = df.copy()
    df_temp['MES'] = df_temp['EMISSAO'].dt.to_period('M')

    # Agrupar por mes
    df_mes = df_temp.groupby('MES').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum'
    }).reset_index()

    df_mes['MES'] = df_mes['MES'].astype(str)
    df_mes['Recebido'] = df_mes['VALOR_ORIGINAL'] - df_mes['SALDO']
    df_mes['Taxa_Receb'] = (df_mes['Recebido'] / df_mes['VALOR_ORIGINAL'] * 100).fillna(0)

    if len(df_mes) < 2:
        st.info("Dados insuficientes para grafico de evolucao")
        return

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df_mes['MES'],
        y=df_mes['VALOR_ORIGINAL'],
        name='Valor Emitido',
        marker_color=cores['info'],
        opacity=0.5
    ))

    fig.add_trace(go.Bar(
        x=df_mes['MES'],
        y=df_mes['Recebido'],
        name='Recebido',
        marker_color=cores['sucesso']
    ))

    fig.add_trace(go.Scatter(
        x=df_mes['MES'],
        y=df_mes['Taxa_Receb'],
        mode='lines+markers',
        name='% Recebido',
        yaxis='y2',
        line=dict(color=cores['texto'], width=2),
        marker=dict(size=6)
    ))

    fig.update_layout(
        criar_layout(300, barmode='overlay'),
        yaxis=dict(title='Valor (R$)'),
        yaxis2=dict(title='% Recebido', overlaying='y', side='right', showgrid=False, range=[0, 105]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=9)),
        margin=dict(l=10, r=50, t=40, b=60),
        xaxis_tickangle=-45
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_aging_por_filial(df_vencidos, cores):
    """Aging por filial"""
    st.markdown("##### Vencidos por Filial")

    if len(df_vencidos) == 0:
        st.success("Sem titulos vencidos!")
        return

    df_grp = df_vencidos.groupby('NOME_FILIAL').agg({
        'SALDO': 'sum',
        'DIAS_ATRASO': 'mean',
        'VALOR_ORIGINAL': 'count'
    }).nlargest(10, 'SALDO').reset_index()
    df_grp.columns = ['Filial', 'Saldo', 'Dias_Atraso', 'Qtd']

    fig = go.Figure(go.Bar(
        y=df_grp['Filial'].str[:25],
        x=df_grp['Saldo'],
        orientation='h',
        marker_color=cores['perigo'],
        text=[f"{formatar_moeda(v)} ({d:.0f}d)" for v, d in zip(df_grp['Saldo'], df_grp['Dias_Atraso'])],
        textposition='outside',
        textfont=dict(size=8)
    ))

    fig.update_layout(
        criar_layout(300),
        yaxis={'autorange': 'reversed'},
        margin=dict(l=10, r=100, t=10, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_inadimplencia_categoria(df, df_vencidos, cores):
    """Inadimplencia por categoria"""
    st.markdown("##### Inadimplencia por Categoria")

    col1, col2 = st.columns(2)

    with col1:
        # Top categorias com mais vencidos
        if len(df_vencidos) > 0:
            df_cat = df_vencidos.groupby('DESCRICAO').agg({
                'SALDO': 'sum',
                'DIAS_ATRASO': 'mean'
            }).nlargest(10, 'SALDO').reset_index()

            fig = go.Figure(go.Bar(
                y=df_cat['DESCRICAO'].str[:25],
                x=df_cat['SALDO'],
                orientation='h',
                marker_color=cores['perigo'],
                text=[formatar_moeda(v) for v in df_cat['SALDO']],
                textposition='outside',
                textfont=dict(size=9)
            ))

            fig.update_layout(
                criar_layout(300),
                yaxis={'autorange': 'reversed'},
                margin=dict(l=10, r=80, t=10, b=10),
                title=dict(text='Valor Vencido por Categoria', font=dict(size=12))
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.success("Sem titulos vencidos!")

    with col2:
        # Taxa de inadimplencia por categoria
        df_total = df[df['SALDO'] > 0].groupby('DESCRICAO')['SALDO'].sum()
        df_venc = df_vencidos.groupby('DESCRICAO')['SALDO'].sum()

        df_taxa = pd.DataFrame({
            'Pendente': df_total,
            'Vencido': df_venc
        }).fillna(0)

        df_taxa['Taxa'] = (df_taxa['Vencido'] / df_taxa['Pendente'] * 100).fillna(0)
        df_taxa = df_taxa[df_taxa['Pendente'] > 10000]  # Filtrar categorias relevantes
        df_taxa = df_taxa.nlargest(10, 'Taxa').reset_index()

        if len(df_taxa) > 0:
            # Cores por taxa
            def cor_taxa(t):
                if t > 50:
                    return cores['perigo']
                elif t > 30:
                    return cores['alerta']
                elif t > 15:
                    return cores['info']
                return cores['sucesso']

            fig = go.Figure(go.Bar(
                y=df_taxa['DESCRICAO'].str[:25],
                x=df_taxa['Taxa'],
                orientation='h',
                marker_color=[cor_taxa(t) for t in df_taxa['Taxa']],
                text=[f"{t:.1f}%" for t in df_taxa['Taxa']],
                textposition='outside',
                textfont=dict(size=9)
            ))

            fig.update_layout(
                criar_layout(300),
                yaxis={'autorange': 'reversed'},
                xaxis=dict(title='% Inadimplencia', range=[0, max(df_taxa['Taxa']) * 1.2]),
                margin=dict(l=10, r=50, t=10, b=10),
                title=dict(text='Taxa de Inadimplencia por Categoria', font=dict(size=12))
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados suficientes")


def _render_titulos_criticos(df_vencidos, cores):
    """Titulos mais criticos (maior valor e atraso)"""
    st.markdown("##### Titulos Criticos - Maior Atraso e Valor")

    if len(df_vencidos) == 0:
        st.success("Sem titulos vencidos!")
        return

    col1, col2 = st.columns(2)

    with col1:
        ordenar = st.selectbox(
            "Ordenar por",
            ['Maior Valor', 'Maior Atraso'],
            key="inad_ordem"
        )

    with col2:
        qtd = st.selectbox("Exibir", [20, 50, 100], key="inad_qtd")

    # Preparar dados
    col_cliente = 'NOME_CLIENTE' if 'NOME_CLIENTE' in df_vencidos.columns else 'NOME_FORNECEDOR'
    colunas = ['NOME_FILIAL', col_cliente, 'DESCRICAO', 'EMISSAO', 'VENCIMENTO',
               'DIAS_ATRASO', 'VALOR_ORIGINAL', 'SALDO']
    colunas_disp = [c for c in colunas if c in df_vencidos.columns]

    df_show = df_vencidos[colunas_disp].copy()

    if ordenar == 'Maior Valor':
        df_show = df_show.nlargest(qtd, 'SALDO')
    else:
        df_show = df_show.nlargest(qtd, 'DIAS_ATRASO')

    # Formatar
    df_show['EMISSAO'] = pd.to_datetime(df_show['EMISSAO']).dt.strftime('%d/%m/%Y')
    df_show['VENCIMENTO'] = pd.to_datetime(df_show['VENCIMENTO']).dt.strftime('%d/%m/%Y')
    df_show['VALOR_ORIGINAL'] = df_show['VALOR_ORIGINAL'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['SALDO'] = df_show['SALDO'].apply(lambda x: formatar_moeda(x, completo=True))

    nomes = {
        'NOME_FILIAL': 'Filial',
        'NOME_CLIENTE': 'Cliente',
        'NOME_FORNECEDOR': 'Cliente',
        'DESCRICAO': 'Categoria',
        'EMISSAO': 'Emissao',
        'VENCIMENTO': 'Vencimento',
        'DIAS_ATRASO': 'Dias Atraso',
        'VALOR_ORIGINAL': 'Valor Original',
        'SALDO': 'Saldo'
    }
    df_show.columns = [nomes.get(c, c) for c in df_show.columns]

    st.dataframe(df_show, use_container_width=True, hide_index=True, height=400)

    # Resumo
    total_critico = df_vencidos.nlargest(qtd, 'SALDO' if ordenar == 'Maior Valor' else 'DIAS_ATRASO')['SALDO'].sum()
    st.caption(f"Total exibido: {formatar_moeda(total_critico)} em {len(df_show)} titulos")
