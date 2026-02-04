"""
Aba Adiantamentos - Contas a Receber
Layout flat alinhado com tabs/adiantamentos.py (espelho pagar -> receber)
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

from config.theme import get_cores
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero
from config.settings import GRUPOS_FILIAIS, get_grupo_filial


def render_adiantamentos_receber(df_adiant, df_baixas):
    """Renderiza a aba de Adiantamentos a Receber (layout flat)"""
    cores = get_cores()
    hoje = datetime.now()

    # ========== PREPARAR DADOS ==========
    df_ad = df_adiant.copy() if len(df_adiant) > 0 else pd.DataFrame()
    df_bx = df_baixas.copy() if len(df_baixas) > 0 else pd.DataFrame()

    # Correlacionar baixas com adiantamentos
    if len(df_ad) > 0 and len(df_bx) > 0 and 'FILIAL' in df_ad.columns and 'NUMERO' in df_ad.columns:
        chaves_ad = set(zip(df_ad['FILIAL'], df_ad['NUMERO'].astype(str)))
        mask_match = df_bx.apply(lambda r: (r['FILIAL'], str(r['NUMERO'])) in chaves_ad, axis=1)
        df_bx = df_bx[mask_match].copy()

    # Converter datas
    for col in ['EMISSAO', 'VENCIMENTO']:
        if len(df_ad) > 0 and col in df_ad.columns:
            df_ad[col] = pd.to_datetime(df_ad[col], errors='coerce')
    if len(df_bx) > 0 and 'DT_BAIXA' in df_bx.columns:
        df_bx['DT_BAIXA'] = pd.to_datetime(df_bx['DT_BAIXA'], errors='coerce')

    # Identificar coluna de cliente (NOME_FORNECEDOR ou NOME_CLIENTE)
    col_cliente = 'NOME_FORNECEDOR' if 'NOME_FORNECEDOR' in df_ad.columns else 'NOME_CLIENTE' if 'NOME_CLIENTE' in df_ad.columns else None

    if len(df_ad) == 0:
        st.info("Nenhum adiantamento encontrado no periodo.")
        return

    # Calcular dias pendente
    if 'EMISSAO' in df_ad.columns:
        df_ad['DIAS_PENDENTE'] = (hoje - df_ad['EMISSAO']).dt.days

    # Calcular totais gerais
    total_adiantado = df_ad['VALOR_ORIGINAL'].sum()
    saldo_pendente = df_ad['SALDO'].sum() if 'SALDO' in df_ad.columns else 0
    total_compensado = total_adiantado - saldo_pendente
    qtd_pendentes = len(df_ad[df_ad['SALDO'] > 0]) if 'SALDO' in df_ad.columns else 0

    prazo_medio = 0
    if len(df_bx) > 0 and 'DIF_DIAS_EMIS_BAIXA' in df_bx.columns:
        prazo_medio = pd.to_numeric(df_bx['DIF_DIAS_EMIS_BAIXA'], errors='coerce').mean()

    # ========== 1. KPIs PRINCIPAIS ==========
    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Total Adiantado", formatar_moeda(total_adiantado), f"{len(df_ad)} registros")
    col2.metric("Compensado", formatar_moeda(total_compensado),
                f"{(total_compensado/total_adiantado*100):.1f}%" if total_adiantado > 0 else "0%")
    col3.metric("Saldo Pendente", formatar_moeda(saldo_pendente), f"{qtd_pendentes} titulos")
    col4.metric("Taxa Compensacao",
                f"{(total_compensado/total_adiantado*100):.1f}%" if total_adiantado > 0 else "0%")
    col5.metric("Prazo Medio", f"{prazo_medio:.0f} dias", "adiantamento -> baixa")

    st.divider()

    # ========== 2. FLUXO MENSAL ==========
    _render_fluxo_mensal(df_ad, df_bx, cores, hoje)

    st.divider()

    # ========== 3. TOP 10 CLIENTES ==========
    _render_top_clientes(df_ad, col_cliente, cores)

    st.divider()

    # ========== 4. AGING ==========
    _render_aging(df_ad, cores, hoje)

    st.divider()

    # ========== 5. POR FILIAL/GRUPO ==========
    _render_por_filial(df_ad, cores)

    st.divider()

    # ========== 6. PRAZOS DE COMPENSACAO ==========
    _render_prazos(df_bx, cores)

    st.divider()

    # ========== 7. CONSULTA CLIENTE ==========
    _render_consulta_cliente(df_ad, df_bx, col_cliente, cores)

    st.divider()

    # ========== 8. TABELA RANKING ==========
    _render_tabela_ranking(df_ad, df_bx, col_cliente, cores)


# ==========================================================================
# Helpers
# ==========================================================================

def _get_nome_grupo(cod_filial):
    """Retorna o nome do grupo a partir do codigo da filial"""
    grupo_id = get_grupo_filial(int(cod_filial))
    return GRUPOS_FILIAIS.get(grupo_id, f"Grupo {grupo_id}")


def _detectar_multiplos_grupos(df):
    """Detecta se o dataframe contem filiais de multiplos grupos"""
    if 'FILIAL' not in df.columns or len(df) == 0:
        return False
    grupos = df['FILIAL'].dropna().apply(lambda x: get_grupo_filial(int(x))).nunique()
    return grupos > 1


def _get_label_filial(row):
    """Retorna label curta da filial"""
    cod = str(int(row['FILIAL'])) if pd.notna(row.get('FILIAL')) else ''
    nome = str(row.get('NOME_FILIAL', ''))
    partes = nome.split(' - ')
    sufixo = partes[-1].strip() if len(partes) > 1 else nome.strip()
    return f"{cod} - {sufixo}" if cod else sufixo


# ==========================================================================
# Secoes
# ==========================================================================

def _render_fluxo_mensal(df_ad, df_bx, cores, hoje):
    """Secao 2 - Fluxo Mensal: Entradas vs Compensacoes"""
    st.markdown("##### Fluxo Mensal")

    if 'EMISSAO' not in df_ad.columns:
        st.info("Coluna EMISSAO nao disponivel.")
        return

    col1, col2 = st.columns([2, 1])

    with col1:
        df_ad_mes = df_ad.copy()
        df_ad_mes['MES'] = df_ad_mes['EMISSAO'].dt.to_period('M').astype(str)
        adiant_mes = df_ad_mes.groupby('MES')['VALOR_ORIGINAL'].sum()

        if len(df_bx) > 0 and 'DT_BAIXA' in df_bx.columns and 'VALOR_BAIXA' in df_bx.columns:
            df_bx_mes = df_bx.copy()
            df_bx_mes['MES'] = df_bx_mes['DT_BAIXA'].dt.to_period('M').astype(str)
            baixa_mes = df_bx_mes.groupby('MES')['VALOR_BAIXA'].sum()
        else:
            baixa_mes = pd.Series(dtype=float)

        meses = sorted(set(adiant_mes.index.tolist() + baixa_mes.index.tolist()))[-12:]
        df_fluxo = pd.DataFrame({
            'MES': meses,
            'Adiantado': [adiant_mes.get(m, 0) for m in meses],
            'Compensado': [baixa_mes.get(m, 0) for m in meses]
        })
        df_fluxo['Liquido'] = df_fluxo['Adiantado'] - df_fluxo['Compensado']

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_fluxo['MES'], y=df_fluxo['Adiantado'],
            name='Adiantado', marker_color=cores['sucesso']
        ))
        fig.add_trace(go.Bar(
            x=df_fluxo['MES'], y=-df_fluxo['Compensado'],
            name='Compensado', marker_color=cores['alerta']
        ))
        fig.add_trace(go.Scatter(
            x=df_fluxo['MES'], y=df_fluxo['Liquido'],
            name='Liquido', mode='lines+markers',
            line=dict(color=cores['texto'], width=2, dash='dot'),
            marker=dict(size=6)
        ))
        fig.update_layout(
            criar_layout(280),
            barmode='relative',
            margin=dict(l=10, r=10, t=10, b=50),
            xaxis=dict(tickangle=-45, tickfont=dict(size=9, color=cores['texto'])),
            yaxis=dict(showticklabels=False, showgrid=False),
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1, font=dict(size=9))
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("###### Ultimos 3 meses")
        df_3m = df_ad[df_ad['EMISSAO'] >= hoje - timedelta(days=90)]
        adiant_3m = df_3m['VALOR_ORIGINAL'].sum()

        comp_3m = 0
        if len(df_bx) > 0 and 'DT_BAIXA' in df_bx.columns and 'VALOR_BAIXA' in df_bx.columns:
            df_bx_3m = df_bx[df_bx['DT_BAIXA'] >= hoje - timedelta(days=90)]
            comp_3m = df_bx_3m['VALOR_BAIXA'].sum()

        liquido_3m = adiant_3m - comp_3m

        st.markdown(f"""
        <div style="padding: 0.5rem 0; border-bottom: 1px solid {cores['borda']};">
            <span style="color: {cores['texto_secundario']}; font-size: 0.8rem;">Adiantado</span>
            <span style="color: {cores['sucesso']}; font-size: 0.9rem; font-weight: 600; float: right;">
                +{formatar_moeda(adiant_3m)}</span>
        </div>
        <div style="padding: 0.5rem 0; border-bottom: 1px solid {cores['borda']};">
            <span style="color: {cores['texto_secundario']}; font-size: 0.8rem;">Compensado</span>
            <span style="color: {cores['alerta']}; font-size: 0.9rem; font-weight: 600; float: right;">
                -{formatar_moeda(comp_3m)}</span>
        </div>
        <div style="padding: 0.5rem 0;">
            <span style="color: {cores['texto']}; font-size: 0.85rem; font-weight: 600;">Liquido</span>
            <span style="color: {cores['perigo'] if liquido_3m > 0 else cores['sucesso']};
                   font-size: 1rem; font-weight: 700; float: right;">
                {'+' if liquido_3m > 0 else ''}{formatar_moeda(liquido_3m)}</span>
        </div>
        """, unsafe_allow_html=True)


def _render_top_clientes(df_ad, col_cliente, cores):
    """Secao 3 - Top 10 Clientes (stacked bar + donut concentracao)"""
    st.markdown("##### Top 10 Clientes")

    if col_cliente is None or col_cliente not in df_ad.columns:
        st.info("Coluna de cliente nao disponivel.")
        return

    df_cli = df_ad.groupby(col_cliente).agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'EMISSAO': 'count'
    }).reset_index()
    df_cli.columns = ['Cliente', 'Total', 'Pendente', 'Qtd']
    df_cli['Compensado'] = df_cli['Total'] - df_cli['Pendente']
    df_cli = df_cli.sort_values('Pendente', ascending=False)

    df_top = df_cli.head(10).sort_values('Pendente', ascending=True)

    if len(df_top) == 0:
        st.success("Nenhum adiantamento encontrado.")
        return

    col1, col2 = st.columns([2, 1])

    with col1:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=df_top['Cliente'].str[:30], x=df_top['Compensado'],
            orientation='h', name='Compensado', marker_color=cores['sucesso'],
            text=[formatar_moeda(v) for v in df_top['Compensado']],
            textposition='inside', textfont=dict(size=8, color='white')
        ))
        fig.add_trace(go.Bar(
            y=df_top['Cliente'].str[:30], x=df_top['Pendente'],
            orientation='h', name='Pendente', marker_color=cores['alerta'],
            text=[formatar_moeda(v) for v in df_top['Pendente']],
            textposition='inside', textfont=dict(size=8, color='white')
        ))
        fig.update_layout(
            criar_layout(320),
            barmode='stack',
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis=dict(showticklabels=False, showgrid=False),
            yaxis=dict(tickfont=dict(size=9, color=cores['texto'])),
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1, font=dict(size=9))
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        valor_pendente = df_cli['Pendente'].sum()
        df_pend = df_cli[df_cli['Pendente'] > 0]

        if len(df_pend) > 5:
            df_donut = df_pend.head(5)[['Cliente', 'Pendente']].copy()
            outros = df_pend.iloc[5:]['Pendente'].sum()
            df_donut = pd.concat([df_donut, pd.DataFrame({'Cliente': ['Outros'], 'Pendente': [outros]})], ignore_index=True)
        else:
            df_donut = df_pend[['Cliente', 'Pendente']].copy()

        if len(df_donut) > 0:
            fig = go.Figure(go.Pie(
                labels=df_donut['Cliente'].str[:20],
                values=df_donut['Pendente'],
                hole=0.6,
                textinfo='percent',
                textfont=dict(size=9, color=cores['texto'])
            ))
            fig.update_layout(
                criar_layout(280),
                showlegend=False,
                margin=dict(l=10, r=10, t=10, b=10),
                annotations=[dict(
                    text=f"<b>{formatar_moeda(valor_pendente)}</b><br>Pendente",
                    x=0.5, y=0.5, font=dict(size=10, color=cores['texto']),
                    showarrow=False
                )]
            )
            st.plotly_chart(fig, use_container_width=True)


def _render_aging(df_ad, cores, hoje):
    """Secao 4 - Aging: pendentes por faixa de tempo"""
    st.markdown("##### Aging - Pendentes por Faixa de Tempo")

    if 'SALDO' not in df_ad.columns:
        st.info("Sem dados de saldo.")
        return

    df_pend = df_ad[df_ad['SALDO'] > 0].copy()
    if len(df_pend) == 0:
        st.success("Nenhum adiantamento pendente!")
        return

    if 'DIAS_PENDENTE' not in df_pend.columns:
        df_pend['DIAS_PENDENTE'] = (hoje - df_pend['EMISSAO']).dt.days

    def faixa_aging(dias):
        if pd.isna(dias) or dias < 0:
            return 'N/A'
        dias = int(dias)
        if dias <= 30:
            return '0-30d'
        elif dias <= 60:
            return '31-60d'
        elif dias <= 90:
            return '61-90d'
        elif dias <= 180:
            return '91-180d'
        return '180+d'

    df_pend['FAIXA'] = df_pend['DIAS_PENDENTE'].apply(faixa_aging)
    ordem = ['0-30d', '31-60d', '61-90d', '91-180d', '180+d']
    cores_aging = [cores['sucesso'], cores['info'], cores['alerta'], '#f97316', cores['perigo']]

    total_pendente = df_pend['SALDO'].sum()
    dias_medio = df_pend['DIAS_PENDENTE'].mean()
    dias_max = df_pend['DIAS_PENDENTE'].max()
    df_critico = df_pend[df_pend['DIAS_PENDENTE'] > 90]
    valor_critico = df_critico['SALDO'].sum()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Valor sem Baixa", formatar_moeda(total_pendente), f"{len(df_pend)} titulos")
    col2.metric("Tempo Medio", f"{dias_medio:.0f} dias")
    col3.metric("Mais Antigo", f"{int(dias_max)} dias")
    col4.metric("Criticos >90d", formatar_moeda(valor_critico), f"{len(df_critico)} titulos")

    df_aging = df_pend.groupby('FAIXA').agg({
        'SALDO': 'sum',
        'DIAS_PENDENTE': 'count'
    }).reindex(ordem, fill_value=0).reset_index()
    df_aging.columns = ['Faixa', 'Valor', 'Qtd']

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=df_aging['Faixa'], x=df_aging['Valor'],
        orientation='h', marker_color=cores_aging,
        text=[f"{formatar_moeda(v)} ({int(q)} tit.)" for v, q in zip(df_aging['Valor'], df_aging['Qtd'])],
        textposition='outside', textfont=dict(size=9, color=cores['texto'])
    ))
    fig.update_layout(
        criar_layout(250),
        margin=dict(l=10, r=120, t=10, b=10),
        xaxis=dict(showticklabels=False, showgrid=False),
        yaxis=dict(tickfont=dict(size=10, color=cores['texto']), autorange='reversed')
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_por_filial(df_ad, cores):
    """Secao 5 - Por Filial/Grupo (stacked bar horizontal)"""

    if 'NOME_FILIAL' not in df_ad.columns:
        return

    multiplos_grupos = _detectar_multiplos_grupos(df_ad)

    if multiplos_grupos:
        st.markdown("##### Por Grupo")
        df_temp = df_ad.copy()
        df_temp['_AGRUP'] = df_temp['FILIAL'].apply(lambda x: _get_nome_grupo(x))
    else:
        st.markdown("##### Por Filial")
        df_temp = df_ad.copy()
        df_temp['_AGRUP'] = df_temp.apply(_get_label_filial, axis=1)

    df_fil = df_temp.groupby('_AGRUP').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'EMISSAO': 'count'
    }).reset_index()
    df_fil.columns = ['Filial', 'Total', 'Pendente', 'Qtd']
    df_fil['Compensado'] = df_fil['Total'] - df_fil['Pendente']
    df_fil = df_fil.sort_values('Total', ascending=False)

    df_top = df_fil.head(12).sort_values('Total', ascending=True)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=df_top['Filial'].str[:22], x=df_top['Compensado'],
        orientation='h', name='Compensado', marker_color=cores['sucesso'],
        text=[formatar_moeda(v) for v in df_top['Compensado']],
        textposition='inside', textfont=dict(size=8, color='white')
    ))
    fig.add_trace(go.Bar(
        y=df_top['Filial'].str[:22], x=df_top['Pendente'],
        orientation='h', name='Pendente', marker_color=cores['alerta'],
        text=[formatar_moeda(v) for v in df_top['Pendente']],
        textposition='inside', textfont=dict(size=8, color='white')
    ))
    fig.update_layout(
        criar_layout(320),
        barmode='stack',
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(showticklabels=False, showgrid=False),
        yaxis=dict(tickfont=dict(size=9, color=cores['texto'])),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1, font=dict(size=9))
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_prazos(df_bx, cores):
    """Secao 6 - Prazos de Compensacao (distribuicao + evolucao mensal)"""
    st.markdown("##### Prazos de Compensacao")

    if len(df_bx) == 0 or 'DIF_DIAS_EMIS_BAIXA' not in df_bx.columns:
        st.info("Sem dados de compensacao.")
        return

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("###### Distribuicao por Faixa de Prazo")

        df_temp = df_bx.copy()
        df_temp['PRAZO'] = pd.to_numeric(df_temp['DIF_DIAS_EMIS_BAIXA'], errors='coerce')

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

        df_temp['FAIXA'] = df_temp['PRAZO'].apply(faixa_prazo)
        ordem = ['Ate 15d', '16-30d', '31-60d', '61-90d', '91-180d', '180+d']

        df_faixa = df_temp.groupby('FAIXA').agg({
            'VALOR_BAIXA': 'sum' if 'VALOR_BAIXA' in df_temp.columns else 'count',
            'PRAZO': 'count'
        }).reindex(ordem, fill_value=0).reset_index()
        df_faixa.columns = ['Faixa', 'Valor', 'Qtd']

        cores_faixas = [cores['sucesso'], cores['info'], '#22d3ee', cores['alerta'], '#f97316', cores['perigo']]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_faixa['Faixa'], y=df_faixa['Valor'],
            marker_color=cores_faixas,
            text=[f"{formatar_moeda(v)}<br>({int(q)})" for v, q in zip(df_faixa['Valor'], df_faixa['Qtd'])],
            textposition='outside', textfont=dict(size=9, color=cores['texto'])
        ))
        fig.update_layout(
            criar_layout(280),
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis=dict(tickfont=dict(size=10, color=cores['texto'])),
            yaxis=dict(showticklabels=False, showgrid=False)
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("###### Evolucao do Prazo Medio")

        if 'DT_BAIXA' in df_bx.columns:
            df_evol = df_bx.copy()
            df_evol['MES'] = df_evol['DT_BAIXA'].dt.to_period('M').astype(str)
            df_evol['PRAZO'] = pd.to_numeric(df_evol['DIF_DIAS_EMIS_BAIXA'], errors='coerce')

            df_prazo_mes = df_evol.groupby('MES')['PRAZO'].mean().tail(12).reset_index()
            df_prazo_mes.columns = ['MES', 'Prazo']

            if len(df_prazo_mes) > 1:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df_prazo_mes['MES'], y=df_prazo_mes['Prazo'],
                    mode='lines+markers',
                    line=dict(color=cores['primaria'], width=2),
                    marker=dict(size=8),
                    text=[f"{int(p)}d" for p in df_prazo_mes['Prazo']],
                    textposition='top center', textfont=dict(size=9, color=cores['texto'])
                ))
                fig.add_hline(y=60, line_dash="dash", line_color=cores['alerta'], line_width=1)
                fig.update_layout(
                    criar_layout(280),
                    margin=dict(l=10, r=10, t=30, b=50),
                    xaxis=dict(tickangle=-45, tickfont=dict(size=9, color=cores['texto'])),
                    yaxis=dict(title='Dias', tickfont=dict(size=9, color=cores['texto']))
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Historico insuficiente")
        else:
            st.info("Sem dados de data de baixa")


def _render_consulta_cliente(df_ad, df_bx, col_cliente, cores):
    """Secao 7 - Consulta por Cliente (drill-down)"""
    st.markdown("##### Consulta por Cliente")

    if col_cliente is None or col_cliente not in df_ad.columns:
        return

    clientes = sorted(df_ad[col_cliente].dropna().unique().tolist())
    cliente_sel = st.selectbox(
        "Selecione um cliente",
        options=['Selecione...'] + clientes,
        key="adto_rec_cli_drill"
    )

    if cliente_sel == 'Selecione...':
        return

    df_sel = df_ad[df_ad[col_cliente] == cliente_sel]
    df_bx_sel = df_bx[df_bx[col_cliente] == cliente_sel] if len(df_bx) > 0 and col_cliente in df_bx.columns else pd.DataFrame()

    total_cli = df_sel['VALOR_ORIGINAL'].sum()
    saldo_cli = df_sel['SALDO'].sum() if 'SALDO' in df_sel.columns else 0
    pct_comp = ((total_cli - saldo_cli) / total_cli * 100) if total_cli > 0 else 0

    prazo_cli = 0
    if len(df_bx_sel) > 0 and 'DIF_DIAS_EMIS_BAIXA' in df_bx_sel.columns:
        prazo_cli = pd.to_numeric(df_bx_sel['DIF_DIAS_EMIS_BAIXA'], errors='coerce').mean()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Adiantado", formatar_moeda(total_cli), f"{len(df_sel)} titulos")
    col2.metric("Saldo Pendente", formatar_moeda(saldo_cli))
    col3.metric("% Compensado", f"{pct_comp:.1f}%")
    col4.metric("Prazo Medio", f"{prazo_cli:.0f}d" if prazo_cli > 0 else "-")

    # Tabela de titulos
    colunas = ['NOME_FILIAL', 'NUMERO', 'EMISSAO', 'VALOR_ORIGINAL', 'SALDO']
    colunas_disp = [c for c in colunas if c in df_sel.columns]
    df_tab = df_sel[colunas_disp].sort_values('EMISSAO', ascending=False).head(30).copy()

    if 'EMISSAO' in df_tab.columns:
        df_tab['EMISSAO'] = pd.to_datetime(df_tab['EMISSAO'], errors='coerce').dt.strftime('%d/%m/%Y')
    if 'VALOR_ORIGINAL' in df_tab.columns:
        df_tab['VALOR_ORIGINAL'] = df_tab['VALOR_ORIGINAL'].apply(lambda x: formatar_moeda(x, completo=True))
    if 'SALDO' in df_tab.columns:
        df_tab['SALDO'] = df_tab['SALDO'].apply(lambda x: formatar_moeda(x, completo=True))

    nomes = {
        'NOME_FILIAL': 'Filial',
        'NUMERO': 'NF/Doc',
        'EMISSAO': 'Emissao',
        'VALOR_ORIGINAL': 'Valor',
        'SALDO': 'Saldo'
    }
    df_tab.columns = [nomes.get(c, c) for c in df_tab.columns]

    st.dataframe(df_tab, use_container_width=True, hide_index=True, height=250)


def _render_tabela_ranking(df_ad, df_bx, col_cliente, cores):
    """Secao 8 - Tabela Ranking de Clientes"""
    st.markdown("##### Ranking de Clientes")

    if col_cliente is None or col_cliente not in df_ad.columns:
        return

    df_cli = df_ad.groupby(col_cliente).agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'EMISSAO': 'count'
    }).reset_index()
    df_cli.columns = ['Cliente', 'Total', 'Pendente', 'Qtd']
    df_cli['Compensado'] = df_cli['Total'] - df_cli['Pendente']
    df_cli['Pct_Comp'] = (df_cli['Compensado'] / df_cli['Total'] * 100).fillna(0).round(1)

    # Prazo medio
    if len(df_bx) > 0 and col_cliente in df_bx.columns and 'DIF_DIAS_EMIS_BAIXA' in df_bx.columns:
        prazo_cli = df_bx.groupby(col_cliente)['DIF_DIAS_EMIS_BAIXA'].apply(
            lambda x: pd.to_numeric(x, errors='coerce').mean()
        )
        df_cli['Prazo_Medio'] = df_cli['Cliente'].map(prazo_cli).fillna(0)
    else:
        df_cli['Prazo_Medio'] = 0

    # Filtros
    col1, col2, col3 = st.columns(3)
    with col1:
        ordenar = st.selectbox(
            "Ordenar por",
            ["Maior Pendente", "Maior Total", "Menor % Compensado", "Maior Prazo"],
            key="adto_rec_rank_ordem"
        )
    with col2:
        filtro = st.selectbox(
            "Filtrar",
            ["Todos", "Com Pendencia", "Quitados"],
            key="adto_rec_rank_filtro"
        )
    with col3:
        busca = st.text_input("Buscar cliente", key="adto_rec_rank_busca")

    df_exibir = df_cli.copy()

    if filtro == "Com Pendencia":
        df_exibir = df_exibir[df_exibir['Pendente'] > 0]
    elif filtro == "Quitados":
        df_exibir = df_exibir[df_exibir['Pendente'] <= 0]

    if busca:
        df_exibir = df_exibir[df_exibir['Cliente'].str.upper().str.contains(busca.upper(), na=False)]

    sort_map = {
        "Maior Pendente": ('Pendente', False),
        "Maior Total": ('Total', False),
        "Menor % Compensado": ('Pct_Comp', True),
        "Maior Prazo": ('Prazo_Medio', False),
    }
    col_sort, asc = sort_map[ordenar]
    df_exibir = df_exibir.sort_values(col_sort, ascending=asc).head(100)

    # Formatar
    df_show = df_exibir.copy()
    df_show['Total'] = df_show['Total'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Compensado'] = df_show['Compensado'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Pendente'] = df_show['Pendente'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Prazo_Medio'] = df_show['Prazo_Medio'].apply(lambda x: f"{int(x)}d" if x > 0 else '-')
    df_show = df_show[['Cliente', 'Total', 'Compensado', 'Pendente', 'Qtd', 'Pct_Comp', 'Prazo_Medio']]
    df_show.columns = ['Cliente', 'Total', 'Compensado', 'Pendente', 'Qtd', '% Comp', 'Prazo Medio']

    st.dataframe(
        df_show,
        use_container_width=True,
        hide_index=True,
        height=400,
        column_config={
            '% Comp': st.column_config.ProgressColumn(
                '% Comp', format='%.0f%%', min_value=0, max_value=100
            )
        }
    )
    st.caption(f"Exibindo {len(df_show)} de {len(df_cli)} clientes")
