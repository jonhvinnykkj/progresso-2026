"""
Aba Vencimentos - Análise de prazos e aging - Contas a Receber
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

from config.theme import get_cores
from config.settings import ORDEM_AGING
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero


def get_df_pendentes(df):
    return df[df['SALDO'] > 0]


def get_df_vencidos(df):
    return df[df['STATUS'] == 'Vencido']


def render_vencimentos_receber(df):
    """Renderiza a aba de Vencimentos"""
    cores = get_cores()
    hoje = datetime.now()

    df_pendentes = get_df_pendentes(df)
    df_vencidos = get_df_vencidos(df)

    # KPIs
    _render_kpis_vencimento(df_pendentes, df_vencidos, cores)

    st.divider()

    # Linha 1: Aging + Timeline
    col1, col2 = st.columns(2)

    with col1:
        _render_aging_visual(df_pendentes, cores)

    with col2:
        _render_timeline_vencimentos(df_pendentes, cores, hoje)

    st.divider()

    # Linha 2: Distribuição + Top Clientes
    col1, col2 = st.columns(2)

    with col1:
        _render_distribuicao_atraso(df_vencidos, cores)

    with col2:
        _render_top_clientes_vencidos(df_vencidos, cores)

    st.divider()

    # Análise de Renegociações
    _render_renegociacoes(df, cores)

    st.divider()

    # Tabela
    _render_tabela_vencidos_completa(df_vencidos, df_pendentes, cores)


def _render_kpis_vencimento(df_pendentes, df_vencidos, cores):
    """Renderiza KPIs de vencimento"""

    total_vencido = df_vencidos['SALDO'].sum()
    qtd_vencidos = len(df_vencidos)
    dias_atraso_medio = df_vencidos['DIAS_ATRASO'].mean() if len(df_vencidos) > 0 else 0

    vence_7d = df_pendentes[df_pendentes['STATUS'] == 'Vence em 7 dias']['SALDO'].sum()
    qtd_7d = len(df_pendentes[df_pendentes['STATUS'] == 'Vence em 7 dias'])

    vence_15d = df_pendentes[df_pendentes['STATUS'] == 'Vence em 15 dias']['SALDO'].sum()
    qtd_15d = len(df_pendentes[df_pendentes['STATUS'] == 'Vence em 15 dias'])

    vence_30d = df_pendentes[df_pendentes['STATUS'] == 'Vence em 30 dias']['SALDO'].sum()
    qtd_30d = len(df_pendentes[df_pendentes['STATUS'] == 'Vence em 30 dias'])

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Vencido",
            value=formatar_moeda(total_vencido),
            delta=f"{qtd_vencidos} títulos - {dias_atraso_medio:.0f}d médio",
            delta_color="off"
        )

    with col2:
        st.metric(
            label="Vence em 7 dias",
            value=formatar_moeda(vence_7d),
            delta=f"{qtd_7d} títulos",
            delta_color="off"
        )

    with col3:
        st.metric(
            label="Vence em 15 dias",
            value=formatar_moeda(vence_15d),
            delta=f"{qtd_15d} títulos",
            delta_color="off"
        )

    with col4:
        st.metric(
            label="Vence em 30 dias",
            value=formatar_moeda(vence_30d),
            delta=f"{qtd_30d} títulos",
            delta_color="off"
        )


def _render_aging_visual(df_pendentes, cores):
    """Renderiza gráfico de aging"""

    st.markdown("##### Aging de Vencimentos")

    df_aging = df_pendentes.groupby('STATUS').agg({
        'SALDO': 'sum',
        'CLIENTE': 'count'
    }).reset_index()
    df_aging.columns = ['Status', 'Valor', 'Qtd']
    df_aging['ordem'] = df_aging['Status'].apply(
        lambda x: ORDEM_AGING.index(x) if x in ORDEM_AGING else 99
    )
    df_aging = df_aging.sort_values('ordem')

    if len(df_aging) > 0:
        cores_map = {
            'Vencido': cores['perigo'],
            'Vence em 7 dias': cores['alerta'],
            'Vence em 15 dias': '#fbbf24',
            'Vence em 30 dias': '#a3e635',
            'Vence em 60 dias': cores['info'],
            'Vence em +60 dias': cores['primaria']
        }

        cores_status = [cores_map.get(s, cores['info']) for s in df_aging['Status']]

        fig = go.Figure()

        fig.add_trace(go.Bar(
            y=df_aging['Status'],
            x=df_aging['Valor'],
            orientation='h',
            marker=dict(color=cores_status, line=dict(width=0)),
            text=[f'{formatar_moeda(v)} ({q})' for v, q in zip(df_aging['Valor'], df_aging['Qtd'])],
            textposition='outside',
            textfont=dict(size=10, color=cores['texto']),
            hovertemplate='<b>%{y}</b><br>Valor: R$ %{x:,.2f}<extra></extra>'
        ))

        fig.update_layout(
            criar_layout(300),
            showlegend=False,
            yaxis=dict(autorange='reversed'),
            xaxis=dict(showgrid=True, gridcolor=cores['borda']),
            margin=dict(l=10, r=80, t=10, b=10)
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados de aging")


def _render_timeline_vencimentos(df_pendentes, cores, hoje):
    """Renderiza timeline de vencimentos próximos"""

    st.markdown("##### Timeline - Próximos 30 Dias")

    df_cal = df_pendentes[df_pendentes['VENCIMENTO'].notna()].copy()
    df_cal = df_cal[df_cal['DIAS_VENC'].between(-7, 30)]

    if len(df_cal) > 0:
        df_cal['DIA'] = df_cal['VENCIMENTO'].dt.date
        df_cal_grp = df_cal.groupby('DIA').agg({
            'SALDO': 'sum',
            'CLIENTE': 'count'
        }).reset_index()
        df_cal_grp.columns = ['DIA', 'SALDO', 'QTD']

        max_val = df_cal_grp['SALDO'].max()

        def get_bar_color(val, dia):
            if dia < hoje.date():
                return cores['perigo']
            elif dia == hoje.date():
                return cores['alerta']
            else:
                intensity = val / max_val if max_val > 0 else 0
                if intensity > 0.7:
                    return cores['perigo']
                elif intensity > 0.4:
                    return cores['alerta']
                else:
                    return cores['primaria']

        bar_colors = [get_bar_color(row['SALDO'], row['DIA']) for _, row in df_cal_grp.iterrows()]

        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=df_cal_grp['DIA'],
            y=df_cal_grp['SALDO'],
            marker=dict(color=bar_colors, line=dict(width=0)),
            text=[f'{formatar_moeda(v)}' for v in df_cal_grp['SALDO']],
            textposition='outside',
            textfont=dict(size=8, color=cores['texto']),
            hovertemplate='<b>%{x}</b><br>Valor: R$ %{y:,.2f}<extra></extra>'
        ))

        fig.update_layout(
            criar_layout(300),
            showlegend=False,
            xaxis=dict(tickformat='%d/%m', tickangle=-45),
            margin=dict(l=10, r=10, t=30, b=50)
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem vencimentos nos próximos 30 dias")


def _render_distribuicao_atraso(df_vencidos, cores):
    """Renderiza distribuição por faixa de atraso"""

    st.markdown("##### Distribuição por Faixa de Atraso")

    if len(df_vencidos) > 0:
        def classificar_atraso(dias):
            if dias <= 7:
                return '1-7 dias'
            elif dias <= 15:
                return '8-15 dias'
            elif dias <= 30:
                return '16-30 dias'
            elif dias <= 60:
                return '31-60 dias'
            else:
                return '60+ dias'

        df_vencidos_copy = df_vencidos.copy()
        df_vencidos_copy['FAIXA'] = df_vencidos_copy['DIAS_ATRASO'].apply(classificar_atraso)

        df_faixa = df_vencidos_copy.groupby('FAIXA').agg({
            'SALDO': 'sum',
            'CLIENTE': 'count'
        }).reset_index()

        ordem_faixas = ['1-7 dias', '8-15 dias', '16-30 dias', '31-60 dias', '60+ dias']
        df_faixa['ordem'] = df_faixa['FAIXA'].apply(lambda x: ordem_faixas.index(x) if x in ordem_faixas else 99)
        df_faixa = df_faixa.sort_values('ordem')

        cores_faixas = [cores['alerta'], '#fbbf24', cores['perigo'], '#dc2626', '#7f1d1d']

        fig = go.Figure()

        fig.add_trace(go.Pie(
            labels=df_faixa['FAIXA'],
            values=df_faixa['SALDO'],
            hole=0.6,
            marker=dict(colors=cores_faixas[:len(df_faixa)]),
            textinfo='percent',
            textfont=dict(size=11, color='white'),
            hovertemplate='<b>%{label}</b><br>Valor: R$ %{value:,.2f}<br>%{percent}<extra></extra>'
        ))

        total_vencido = df_faixa['SALDO'].sum()
        fig.add_annotation(
            text=f"<b>{formatar_moeda(total_vencido)}</b>",
            x=0.5, y=0.5,
            font=dict(size=14, color=cores['texto']),
            showarrow=False
        )

        fig.update_layout(
            criar_layout(300),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5, font=dict(size=10)),
            margin=dict(l=10, r=10, t=10, b=50)
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.success("Nenhum título vencido!")


def _render_top_clientes_vencidos(df_vencidos, cores):
    """Renderiza top clientes com mais vencidos"""

    st.markdown("##### Top Clientes Vencidos")

    if len(df_vencidos) > 0:
        df_top = df_vencidos.groupby('NOME_CLIENTE').agg({
            'SALDO': 'sum',
            'DIAS_ATRASO': 'max',
            'CLIENTE': 'count'
        }).nlargest(5, 'SALDO').reset_index()

        for i, row in df_top.iterrows():
            nome = row['NOME_CLIENTE'][:30]
            valor = formatar_moeda(row['SALDO'])
            dias = int(row['DIAS_ATRASO'])
            qtd = int(row['CLIENTE'])

            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.write(f"**{nome}**")
                st.caption(f"{qtd} título(s) - {dias} dias de atraso")
            with col2:
                st.write(f"**{valor}**")
            with col3:
                if dias > 30:
                    st.error("Crítico")
                elif dias > 15:
                    st.warning("Alto")
                else:
                    st.info("Médio")
    else:
        st.success("Nenhum cliente com títulos vencidos!")


def _render_tabela_vencidos_completa(df_vencidos, df_pendentes, cores):
    """Renderiza tabela de vencidos com filtros"""

    st.markdown("##### Detalhamento")

    tab1, tab2, tab3 = st.tabs(["Vencidos", "Próximos 7 dias", "Por Filial"])

    with tab1:
        if len(df_vencidos) > 0:
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                ordenar_por = st.selectbox(
                    "Ordenar por",
                    ["Maior valor", "Maior atraso", "Cliente A-Z"],
                    key="ord_vencidos_rec"
                )
            with col2:
                filtro_dias = st.selectbox(
                    "Filtrar atraso",
                    ["Todos", "Até 7 dias", "8-30 dias", "Mais de 30 dias"],
                    key="filtro_dias_rec"
                )

            df_show = df_vencidos.copy()

            if filtro_dias == "Até 7 dias":
                df_show = df_show[df_show['DIAS_ATRASO'] <= 7]
            elif filtro_dias == "8-30 dias":
                df_show = df_show[(df_show['DIAS_ATRASO'] > 7) & (df_show['DIAS_ATRASO'] <= 30)]
            elif filtro_dias == "Mais de 30 dias":
                df_show = df_show[df_show['DIAS_ATRASO'] > 30]

            if ordenar_por == "Maior valor":
                df_show = df_show.nlargest(50, 'SALDO')
            elif ordenar_por == "Maior atraso":
                df_show = df_show.nlargest(50, 'DIAS_ATRASO')
            else:
                df_show = df_show.sort_values('NOME_CLIENTE').head(50)

            df_show = df_show[[
                'NOME_FILIAL', 'NOME_CLIENTE', 'DESCRICAO',
                'VENCIMENTO', 'DIAS_ATRASO', 'SALDO'
            ]].copy()

            df_show['VENCIMENTO'] = df_show['VENCIMENTO'].dt.strftime('%d/%m/%Y')
            df_show['SALDO'] = df_show['SALDO'].apply(lambda x: formatar_moeda(x, completo=True))
            df_show.columns = ['Filial', 'Cliente', 'Categoria', 'Vencimento', 'Dias Atraso', 'Valor']

            st.dataframe(df_show, use_container_width=True, hide_index=True, height=400)
            st.caption(f"Exibindo {len(df_show)} de {len(df_vencidos)} títulos vencidos")
        else:
            st.success("Parabéns! Nenhum título vencido no período selecionado.")

    with tab2:
        df_7d = df_pendentes[df_pendentes['STATUS'] == 'Vence em 7 dias']

        if len(df_7d) > 0:
            df_show = df_7d.nlargest(30, 'SALDO')[[
                'NOME_FILIAL', 'NOME_CLIENTE', 'DESCRICAO',
                'VENCIMENTO', 'DIAS_VENC', 'SALDO'
            ]].copy()

            df_show['VENCIMENTO'] = df_show['VENCIMENTO'].dt.strftime('%d/%m/%Y')
            df_show['SALDO'] = df_show['SALDO'].apply(lambda x: formatar_moeda(x, completo=True))
            df_show.columns = ['Filial', 'Cliente', 'Categoria', 'Vencimento', 'Dias p/ Vencer', 'Valor']

            st.dataframe(df_show, use_container_width=True, hide_index=True, height=400)
            st.caption(f"Total: {formatar_moeda(df_7d['SALDO'].sum(), completo=True)} em {len(df_7d)} títulos")
        else:
            st.info("Nenhum título vence nos próximos 7 dias")

    with tab3:
        _render_por_filial(df_pendentes, df_vencidos, cores)


def _render_renegociacoes(df, cores):
    """Renderiza análise de renegociações usando VENCTO_REAL"""

    st.markdown("##### Analise de Renegociacoes")

    if 'RENEGOCIADO' not in df.columns or 'VENCTO_REAL' not in df.columns:
        st.info("Dados de renegociacao nao disponiveis (coluna VENCTO_REAL)")
        return

    df_reneg = df[df['RENEGOCIADO'] == True].copy()
    df_normal = df[df['RENEGOCIADO'] == False].copy()

    total_reneg = len(df_reneg)
    total_normal = len(df_normal)
    pct_reneg = (total_reneg / (total_reneg + total_normal) * 100) if (total_reneg + total_normal) > 0 else 0

    valor_reneg = df_reneg['SALDO'].sum() if len(df_reneg) > 0 else 0
    valor_normal = df_normal['SALDO'].sum() if len(df_normal) > 0 else 0
    dias_prorrog_medio = df_reneg['DIAS_PRORROGACAO'].mean() if len(df_reneg) > 0 and 'DIAS_PRORROGACAO' in df_reneg.columns else 0

    # KPIs de renegociação
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Titulos Renegociados", formatar_numero(total_reneg), f"{pct_reneg:.1f}% do total")
    with col2:
        st.metric("Valor Renegociado", formatar_moeda(valor_reneg))
    with col3:
        st.metric("Dias Prorrogacao Medio", f"{dias_prorrog_medio:.0f} dias")
    with col4:
        # Taxa de inadimplência em renegociados vs normais
        venc_reneg = df_reneg[df_reneg['STATUS'] == 'Vencido']['SALDO'].sum() if len(df_reneg) > 0 else 0
        taxa_inad_reneg = (venc_reneg / valor_reneg * 100) if valor_reneg > 0 else 0
        st.metric("Inadimpl. Renegociados", f"{taxa_inad_reneg:.1f}%")

    if total_reneg == 0:
        st.success("Nenhum titulo renegociado no periodo!")
        return

    col1, col2 = st.columns(2)

    with col1:
        # Gráfico comparativo
        st.markdown("###### Comparativo: Normal vs Renegociado")

        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=['Quantidade'],
            y=[total_normal],
            name='Normal',
            marker_color=cores['sucesso'],
            text=[formatar_numero(total_normal)],
            textposition='auto'
        ))

        fig.add_trace(go.Bar(
            x=['Quantidade'],
            y=[total_reneg],
            name='Renegociado',
            marker_color=cores['alerta'],
            text=[formatar_numero(total_reneg)],
            textposition='auto'
        ))

        fig.update_layout(
            criar_layout(250, barmode='group'),
            margin=dict(l=10, r=10, t=10, b=30),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Top clientes que mais renegociam
        st.markdown("###### Top Clientes - Mais Renegociacoes")

        df_cli_reneg = df_reneg.groupby('NOME_CLIENTE').agg({
            'SALDO': 'sum',
            'DIAS_PRORROGACAO': 'mean',
            'CLIENTE': 'count'
        }).nlargest(5, 'CLIENTE').reset_index()

        if len(df_cli_reneg) > 0:
            for _, row in df_cli_reneg.iterrows():
                nome = str(row['NOME_CLIENTE'])[:25]
                qtd = int(row['CLIENTE'])
                dias = row['DIAS_PRORROGACAO']
                valor = row['SALDO']
                st.markdown(f"""
                <div style="background: {cores['card']}; border-left: 3px solid {cores['alerta']};
                            padding: 0.5rem; border-radius: 0 6px 6px 0; margin-bottom: 0.3rem;">
                    <span style="color: {cores['texto']}; font-weight: 600;">{nome}</span><br>
                    <span style="color: {cores['texto_secundario']}; font-size: 0.75rem;">
                        {qtd} reneg. | {dias:.0f}d medio | {formatar_moeda(valor)}</span>
                </div>
                """, unsafe_allow_html=True)


def _render_por_filial(df_pendentes, df_vencidos, cores):
    """Renderiza análise por filial"""

    df_all = pd.concat([df_pendentes, df_vencidos]).drop_duplicates()

    if len(df_all) == 0:
        st.info("Sem dados por filial")
        return

    df_fil = df_all.groupby('NOME_FILIAL').agg({
        'SALDO': 'sum',
        'VALOR_ORIGINAL': 'count'
    }).reset_index()
    df_fil.columns = ['Filial', 'Saldo', 'Qtd']

    if len(df_vencidos) > 0:
        df_venc_fil = df_vencidos.groupby('NOME_FILIAL')['SALDO'].sum().reset_index()
        df_venc_fil.columns = ['Filial', 'Vencido']
        df_fil = df_fil.merge(df_venc_fil, on='Filial', how='left').fillna(0)
    else:
        df_fil['Vencido'] = 0

    df_fil['Pct_Vencido'] = (df_fil['Vencido'] / df_fil['Saldo'] * 100).fillna(0).round(1)
    df_fil = df_fil.sort_values('Saldo', ascending=False)

    fig = go.Figure()

    a_vencer = df_fil['Saldo'] - df_fil['Vencido']
    fig.add_trace(go.Bar(
        y=df_fil['Filial'],
        x=a_vencer,
        orientation='h',
        name='A Vencer',
        marker_color=cores['alerta'],
        text=[formatar_moeda(v) for v in a_vencer],
        textposition='inside',
        textfont=dict(size=10, color='white')
    ))

    fig.add_trace(go.Bar(
        y=df_fil['Filial'],
        x=df_fil['Vencido'],
        orientation='h',
        name='Vencido',
        marker_color=cores['perigo'],
        text=[formatar_moeda(v) if v > 0 else '' for v in df_fil['Vencido']],
        textposition='inside',
        textfont=dict(size=10, color='white')
    ))

    altura = max(250, len(df_fil) * 35)

    fig.update_layout(
        criar_layout(altura, barmode='stack'),
        yaxis={'autorange': 'reversed'},
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
        margin=dict(l=10, r=10, t=30, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)

    df_exibir = pd.DataFrame({
        'Filial': df_fil['Filial'],
        'Saldo Pendente': df_fil['Saldo'].apply(lambda x: formatar_moeda(x, completo=True)),
        'Vencido': df_fil['Vencido'].apply(lambda x: formatar_moeda(x, completo=True)),
        'Títulos': df_fil['Qtd'],
        '% Vencido': df_fil['Pct_Vencido']
    })

    st.dataframe(
        df_exibir,
        use_container_width=True,
        hide_index=True,
        column_config={
            '% Vencido': st.column_config.ProgressColumn(
                '% Vencido',
                format='%.0f%%',
                min_value=0,
                max_value=100
            )
        }
    )
