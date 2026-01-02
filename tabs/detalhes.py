"""
Aba Detalhes - Consulta avançada e drill-down de títulos
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from config.theme import get_cores
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero, to_excel


def render_detalhes(df):
    """Renderiza a aba de Detalhes"""
    cores = get_cores()
    hoje = datetime.now()

    st.markdown("### Consulta de Titulos")

    if len(df) == 0:
        st.warning("Nenhum dado disponivel para consulta.")
        return

    # ========== FILTROS ==========
    with st.container():
        col1, col2, col3, col4, col5 = st.columns([1.5, 1.5, 1.5, 1.5, 1])

        with col1:
            filtro_status = st.multiselect(
                "Status",
                options=sorted(df['STATUS'].dropna().unique().tolist()),
                default=[],
                key="det_status",
                placeholder="Todos"
            )

        with col2:
            filtro_filial = st.multiselect(
                "Filial",
                options=sorted(df['NOME_FILIAL'].dropna().unique().tolist()),
                default=[],
                key="det_filial",
                placeholder="Todas"
            )

        with col3:
            filtro_categoria = st.multiselect(
                "Categoria",
                options=sorted(df['DESCRICAO'].dropna().unique().tolist()),
                default=[],
                key="det_categoria",
                placeholder="Todas"
            )

        with col4:
            busca = st.text_input(
                "Buscar fornecedor",
                placeholder="Digite...",
                key="det_busca"
            )

        with col5:
            apenas_saldo = st.checkbox("Com saldo", value=False, key="det_saldo")

    # Aplicar filtros
    df_filtrado = _aplicar_filtros(df)

    # ========== RESUMO ==========
    col1, col2, col3, col4, col5 = st.columns(5)

    valor_total = df_filtrado['VALOR_ORIGINAL'].sum()
    saldo_total = df_filtrado['SALDO'].sum()
    qtd_vencidos = len(df_filtrado[df_filtrado['STATUS'] == 'Vencido'])

    col1.metric("Títulos", formatar_numero(len(df_filtrado)))
    col2.metric("Valor Total", formatar_moeda(valor_total))
    col3.metric("Saldo Pendente", formatar_moeda(saldo_total))
    col4.metric("Vencidos", formatar_numero(qtd_vencidos))

    col5.download_button(
        label="📥 Exportar",
        data=to_excel(df_filtrado),
        file_name=f"titulos_{hoje.strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

    st.markdown("---")

    # ========== CONTEÚDO ==========
    tab1, tab2, tab3 = st.tabs(["📋 Títulos", "📊 Gráficos", "📈 Indicadores"])

    with tab1:
        _render_tabela(df_filtrado)

    with tab2:
        _render_graficos(df_filtrado, cores)

    with tab3:
        _render_indicadores(df, cores)


def _aplicar_filtros(df):
    """Aplica os filtros"""
    df_filtrado = df.copy()

    if st.session_state.get('det_status'):
        df_filtrado = df_filtrado[df_filtrado['STATUS'].isin(st.session_state.det_status)]

    if st.session_state.get('det_filial'):
        df_filtrado = df_filtrado[df_filtrado['NOME_FILIAL'].isin(st.session_state.det_filial)]

    if st.session_state.get('det_categoria'):
        df_filtrado = df_filtrado[df_filtrado['DESCRICAO'].isin(st.session_state.det_categoria)]

    busca = st.session_state.get('det_busca', '')
    if busca:
        df_filtrado = df_filtrado[
            df_filtrado['NOME_FORNECEDOR'].str.contains(busca, case=False, na=False)
        ]

    if st.session_state.get('det_saldo', False):
        df_filtrado = df_filtrado[df_filtrado['SALDO'] > 0]

    return df_filtrado.sort_values('VENCIMENTO', ascending=True)


def _render_tabela(df_filtrado):
    """Renderiza tabela de títulos"""

    if len(df_filtrado) == 0:
        st.info("Nenhum título encontrado.")
        return

    # Preparar dados
    df_show = df_filtrado[[
        'NOME_FILIAL', 'NOME_FORNECEDOR', 'DESCRICAO',
        'EMISSAO', 'VENCIMENTO', 'VALOR_ORIGINAL', 'SALDO', 'STATUS', 'DIAS_ATRASO'
    ]].copy()

    df_show['EMISSAO'] = pd.to_datetime(df_show['EMISSAO'], errors='coerce').dt.strftime('%d/%m/%Y')
    df_show['VENCIMENTO'] = pd.to_datetime(df_show['VENCIMENTO'], errors='coerce').dt.strftime('%d/%m/%Y')
    df_show['VALOR_ORIGINAL'] = df_show['VALOR_ORIGINAL'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['SALDO'] = df_show['SALDO'].apply(lambda x: formatar_moeda(x, completo=True))

    def format_status(s):
        status_map = {
            'Vencido': '🔴 Vencido',
            'Vence em 7 dias': '🟠 7 dias',
            'Vence em 15 dias': '🟡 15 dias',
            'Vence em 30 dias': '🟢 30 dias',
            'Vence em 60 dias': '🔵 60 dias',
            'Vence em +60 dias': '📅 +60 dias',
            'Pago': '✅ Pago'
        }
        return status_map.get(s, s)

    df_show['STATUS'] = df_show['STATUS'].apply(format_status)

    df_show.columns = ['Filial', 'Fornecedor', 'Categoria', 'Emissão', 'Vencimento',
                       'Valor', 'Saldo', 'Status', 'Atraso']

    st.dataframe(
        df_show,
        use_container_width=True,
        hide_index=True,
        height=450
    )

    st.caption(f"Total: {len(df_show)} títulos")


def _render_graficos(df_filtrado, cores):
    """Renderiza gráficos"""

    if len(df_filtrado) == 0:
        st.info("Nenhum dado para visualizar.")
        return

    # Linha 1: Status e Fornecedores
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Por Status")

        df_status = df_filtrado.groupby('STATUS')['SALDO'].sum().reset_index()
        df_status = df_status.sort_values('SALDO', ascending=False)

        cores_status = {
            'Vencido': cores['perigo'],
            'Vence em 7 dias': '#ff6b35',
            'Vence em 15 dias': cores['alerta'],
            'Vence em 30 dias': '#a3e635',
            'Vence em 60 dias': cores['info'],
            'Vence em +60 dias': cores['primaria'],
            'Pago': cores['sucesso']
        }

        fig = go.Figure(data=[go.Pie(
            labels=df_status['STATUS'],
            values=df_status['SALDO'],
            hole=0.5,
            marker_colors=[cores_status.get(s, cores['info']) for s in df_status['STATUS']],
            textinfo='percent',
            textfont_size=11
        )])

        fig.update_layout(
            criar_layout(280),
            showlegend=True,
            legend=dict(orientation='h', yanchor='bottom', y=-0.2, xanchor='center', x=0.5, font=dict(size=9)),
            margin=dict(l=10, r=10, t=10, b=60)
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("##### Top 10 Fornecedores")

        df_forn = df_filtrado.groupby('NOME_FORNECEDOR')['SALDO'].sum().nlargest(10).reset_index()

        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=df_forn['NOME_FORNECEDOR'].str[:18],
            x=df_forn['SALDO'],
            orientation='h',
            marker_color=cores['primaria'],
            text=[formatar_moeda(v) for v in df_forn['SALDO']],
            textposition='outside',
            textfont=dict(size=9)
        ))

        fig.update_layout(
            criar_layout(280),
            yaxis={'autorange': 'reversed'},
            margin=dict(l=10, r=60, t=10, b=10)
        )
        st.plotly_chart(fig, use_container_width=True)

    # Linha 2: Filial e Categoria
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Por Filial")

        df_filial = df_filtrado.groupby('NOME_FILIAL')['SALDO'].sum().reset_index()
        df_filial = df_filial.sort_values('SALDO', ascending=False)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_filial['NOME_FILIAL'],
            y=df_filial['SALDO'],
            marker_color=cores['alerta'],
            text=[formatar_moeda(v) for v in df_filial['SALDO']],
            textposition='outside',
            textfont=dict(size=9)
        ))

        fig.update_layout(
            criar_layout(250),
            xaxis_tickangle=-45,
            margin=dict(l=10, r=10, t=10, b=70)
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("##### Top 10 Categorias")

        df_cat = df_filtrado.groupby('DESCRICAO')['SALDO'].sum().nlargest(10).reset_index()

        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=df_cat['DESCRICAO'].str[:20],
            x=df_cat['SALDO'],
            orientation='h',
            marker_color=cores['info'],
            text=[formatar_moeda(v) for v in df_cat['SALDO']],
            textposition='outside',
            textfont=dict(size=9)
        ))

        fig.update_layout(
            criar_layout(250),
            yaxis={'autorange': 'reversed'},
            margin=dict(l=10, r=60, t=10, b=10)
        )
        st.plotly_chart(fig, use_container_width=True)


def _render_indicadores(df, cores):
    """Renderiza indicadores"""

    # Calcular indicadores
    df_pagos = df[df['SALDO'] == 0].copy()

    # DPO
    dpo = 0
    taxa_pontual = 0
    if len(df_pagos) > 0 and 'DT_BAIXA' in df_pagos.columns:
        df_pagos['DT_BAIXA'] = pd.to_datetime(df_pagos['DT_BAIXA'], errors='coerce')
        df_pagos['DIAS_PGTO'] = (df_pagos['DT_BAIXA'] - df_pagos['EMISSAO']).dt.days
        df_pagos_valid = df_pagos[df_pagos['DIAS_PGTO'] > 0]
        if len(df_pagos_valid) > 0:
            dpo = df_pagos_valid['DIAS_PGTO'].mean()
            df_pagos_valid['PONTUAL'] = df_pagos_valid['DT_BAIXA'] <= df_pagos_valid['VENCIMENTO']
            taxa_pontual = df_pagos_valid['PONTUAL'].sum() / len(df_pagos_valid) * 100

    # Outros indicadores
    total_geral = df['VALOR_ORIGINAL'].sum()
    top10_valor = df.groupby('NOME_FORNECEDOR')['VALOR_ORIGINAL'].sum().nlargest(10).sum()
    concentracao = (top10_valor / total_geral * 100) if total_geral > 0 else 0

    ticket_medio = df['VALOR_ORIGINAL'].mean() if len(df) > 0 else 0

    df_vencidos = df[df['STATUS'] == 'Vencido']
    aging_medio = df_vencidos['DIAS_ATRASO'].mean() if len(df_vencidos) > 0 else 0

    total_saldo = df['SALDO'].sum()
    total_vencido = df_vencidos['SALDO'].sum()
    taxa_inadimplencia = (total_vencido / total_saldo * 100) if total_saldo > 0 else 0

    # Layout em 2 linhas
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("DPO Médio", f"{dpo:.0f} dias", help="Prazo médio de pagamento")
        st.metric("Ticket Médio", formatar_moeda(ticket_medio))

    with col2:
        st.metric("Taxa Pontualidade", f"{taxa_pontual:.1f}%", help="% pagos no prazo")
        st.metric("Concentração Top 10", f"{concentracao:.1f}%")

    with col3:
        st.metric("Aging Médio", f"{aging_medio:.0f} dias", help="Atraso médio dos vencidos")
        st.metric(
            "Taxa Inadimplência",
            f"{taxa_inadimplencia:.1f}%",
            delta="Alto" if taxa_inadimplencia > 20 else "Normal",
            delta_color="inverse" if taxa_inadimplencia > 20 else "off"
        )

    st.markdown("---")

    # Gráficos
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Distribuição de Valores")

        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=df['VALOR_ORIGINAL'],
            nbinsx=25,
            marker_color=cores['primaria'],
            opacity=0.7
        ))

        fig.update_layout(
            criar_layout(220),
            xaxis_title='Valor (R$)',
            yaxis_title='Frequência',
            margin=dict(l=40, r=10, t=10, b=40)
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("##### Faixas de Valor")

        def classificar(v):
            if v <= 1000: return '< 1K'
            elif v <= 5000: return '1K-5K'
            elif v <= 10000: return '5K-10K'
            elif v <= 50000: return '10K-50K'
            else: return '> 50K'

        df_faixa = df.copy()
        df_faixa['FAIXA'] = df_faixa['VALOR_ORIGINAL'].apply(classificar)

        ordem = ['< 1K', '1K-5K', '5K-10K', '10K-50K', '> 50K']
        df_agg = df_faixa.groupby('FAIXA').size().reset_index(name='Qtd')
        df_agg['Ordem'] = df_agg['FAIXA'].apply(lambda x: ordem.index(x) if x in ordem else 99)
        df_agg = df_agg.sort_values('Ordem')

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_agg['FAIXA'],
            y=df_agg['Qtd'],
            marker_color=cores['alerta'],
            text=df_agg['Qtd'],
            textposition='outside'
        ))

        fig.update_layout(
            criar_layout(220),
            yaxis_title='Quantidade',
            margin=dict(l=40, r=10, t=10, b=30)
        )
        st.plotly_chart(fig, use_container_width=True)
