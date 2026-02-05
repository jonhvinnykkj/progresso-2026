"""
Aba Clientes - Contas a Receber por Cliente
Foco em valores recebidos e pendentes, nao em vencimentos
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta


from config.theme import get_cores
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero
from config.settings import GRUPOS_FILIAIS, get_grupo_filial


def render_clientes(df):
    """Renderiza a aba de Clientes - Contas a Receber"""
    cores = get_cores()

    if len(df) == 0:
        st.warning("Nenhum dado disponivel.")
        return

    # ========== KPIs ==========
    _render_kpis(df, cores)

    st.divider()

    # ========== TOP CLIENTES (Valor Total) ==========
    _render_top_clientes(df, cores)

    st.divider()

    # ========== TICKET MEDIO ==========
    _render_ticket_medio(df, cores)

    st.divider()

    # ========== PRAZOS DE RECEBIMENTO ==========
    _render_prazos_recebimento(df, cores)

    st.divider()

    # ========== CURVA ABC (unificada com Concentracao) ==========
    _render_curva_abc(df, cores)

    st.divider()

    # ========== CLIENTES POR FILIAL ==========
    _render_clientes_por_filial(df, cores)

    st.divider()

    # ========== MATRIZ FILIAL x CLIENTE ==========
    _render_matriz_filial_cliente(df, cores)

    st.divider()

    # ========== POR CATEGORIA ==========
    _render_por_categoria(df, cores)

    st.divider()

    # ========== CONSULTA CLIENTE ==========
    _render_consulta_cliente(df, cores)

    st.divider()

    # ========== RANKING ==========
    _render_ranking(df, cores)


# =============================================
# HELPERS
# =============================================

def _get_nome_grupo_cli(cod_filial):
    grupo_id = get_grupo_filial(int(cod_filial))
    return GRUPOS_FILIAIS.get(grupo_id, f"Grupo {grupo_id}")

def _detectar_multiplos_grupos_cli(df):
    if 'FILIAL' not in df.columns or len(df) == 0:
        return False
    grupos = df['FILIAL'].dropna().apply(lambda x: get_grupo_filial(int(x))).nunique()
    return grupos > 1

def _calcular_classe_abc(df):
    """Retorna dict {NOME_CLIENTE: 'A'/'B'/'C'}"""
    df_abc = df.groupby('NOME_CLIENTE')['VALOR_ORIGINAL'].sum().sort_values(ascending=False)
    total = df_abc.sum()
    if total == 0:
        return {}
    pct_acum = (df_abc / total * 100).cumsum()
    classes = {}
    for cli, pct in pct_acum.items():
        if pct <= 80:
            classes[cli] = 'A'
        elif pct <= 95:
            classes[cli] = 'B'
        else:
            classes[cli] = 'C'
    return classes


# =============================================
# SECOES
# =============================================

def _render_kpis(df, cores):
    """KPIs principais - foco em valores recebidos/pendentes"""

    total_clientes = df['NOME_CLIENTE'].nunique()
    total_valor = df['VALOR_ORIGINAL'].sum()
    total_pendente = df['SALDO'].sum()
    total_recebido = total_valor - total_pendente

    pct_recebido = (total_recebido / total_valor * 100) if total_valor > 0 else 0

    # Concentracao top 10
    df_top10 = df.groupby('NOME_CLIENTE')['VALOR_ORIGINAL'].sum().nlargest(10)
    pct_top10 = (df_top10.sum() / total_valor * 100) if total_valor > 0 else 0

    # Ticket medio
    ticket_medio = total_valor / len(df) if len(df) > 0 else 0

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        st.metric(
            label="Clientes",
            value=formatar_numero(total_clientes),
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
            label="Total Recebido",
            value=formatar_moeda(total_recebido),
            delta=f"{pct_recebido:.1f}%",
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


def _render_top_clientes(df, cores):
    """Top 15 clientes por valor total - Recebido vs Pendente"""

    st.markdown("##### Top 15 Clientes - Valor Total")

    # Agrupar por cliente
    df_cli = df.groupby('NOME_CLIENTE').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'CLIENTE': 'count'
    }).reset_index()
    df_cli.columns = ['Cliente', 'Total', 'Pendente', 'Qtd']
    df_cli['Recebido'] = df_cli['Total'] - df_cli['Pendente']

    # Top 15
    df_top = df_cli.nlargest(15, 'Total')
    df_top = df_top.sort_values('Total', ascending=True)

    fig = go.Figure()

    # Recebido
    fig.add_trace(go.Bar(
        y=df_top['Cliente'].str[:35],
        x=df_top['Recebido'],
        orientation='h',
        name='Recebido',
        marker_color=cores['sucesso'],
        text=[formatar_moeda(v) if v > 0 else '' for v in df_top['Recebido']],
        textposition='inside',
        textfont=dict(size=9, color='white')
    ))

    # Pendente
    fig.add_trace(go.Bar(
        y=df_top['Cliente'].str[:35],
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
    st.caption("Exibe o valor total emitido (VALOR_ORIGINAL) por cliente, dividido em Recebido e Pendente.")


def _render_ticket_medio(df, cores):
    """Ticket Medio geral e top 15 clientes em cards"""

    st.markdown("##### Ticket Medio por Cliente (todos os clientes)")

    if len(df) == 0:
        st.info("Dados insuficientes")
        return

    df_cli = df.groupby('NOME_CLIENTE').agg({
        'VALOR_ORIGINAL': 'sum',
        'CLIENTE': 'count'
    }).reset_index()
    df_cli.columns = ['Cliente', 'Total', 'Qtd']
    df_cli['Ticket'] = df_cli['Total'] / df_cli['Qtd']

    # Metricas gerais
    ticket_geral = df['VALOR_ORIGINAL'].sum() / len(df)
    total_clientes = len(df_cli)
    total_titulos = len(df)

    col1, col2, col3 = st.columns(3)
    col1.metric("Ticket Medio Geral", formatar_moeda(ticket_geral))
    col2.metric("Clientes", formatar_numero(total_clientes))
    col3.metric("Titulos", formatar_numero(total_titulos))

    # Top 15 por ticket medio (min 2 titulos)
    df_top = df_cli[df_cli['Qtd'] >= 2].nlargest(15, 'Ticket')

    if len(df_top) == 0:
        return

    st.markdown("###### Top 15 - Maior Ticket Medio")

    # Renderizar em 3 colunas de 5 cards
    cols = st.columns(3)
    for i, (_, row) in enumerate(df_top.iterrows()):
        col = cols[i % 3]
        with col:
            st.markdown(f"""
            <div style="background: {cores['card']}; border-left: 3px solid {cores['primaria']};
                        border-radius: 4px; padding: 0.5rem 0.7rem; margin-bottom: 0.4rem;">
                <div style="color: {cores['texto']}; font-size: 0.78rem; font-weight: 600;
                            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                    {row['Cliente'][:28]}</div>
                <div style="color: {cores['primaria']}; font-size: 0.85rem; font-weight: 700;">
                    {formatar_moeda(row['Ticket'])}</div>
                <div style="color: {cores['texto_secundario']}; font-size: 0.7rem;">
                    {int(row['Qtd'])} titulos | Total: {formatar_moeda(row['Total'])}</div>
            </div>
            """, unsafe_allow_html=True)


def _render_prazos_recebimento(df, cores):
    """Analise de prazos de recebimento por cliente"""

    st.markdown("##### Prazos de Recebimento")

    # Calcular prazo concedido (emissao ate vencimento)
    df_prazos = df.copy()
    df_prazos['PRAZO_CONCEDIDO'] = (df_prazos['VENCIMENTO'] - df_prazos['EMISSAO']).dt.days

    # Calcular prazo real (emissao ate recebimento) - apenas para recebidos
    df_recebidos = df_prazos[df_prazos['SALDO'] == 0].copy()
    if 'DT_BAIXA' in df_recebidos.columns:
        df_recebidos['PRAZO_REAL'] = (df_recebidos['DT_BAIXA'] - df_recebidos['EMISSAO']).dt.days
    else:
        df_recebidos['PRAZO_REAL'] = None

    # KPIs de prazo
    prazo_medio_concedido = df_prazos['PRAZO_CONCEDIDO'].mean()
    prazo_medio_real = df_recebidos['PRAZO_REAL'].mean() if 'PRAZO_REAL' in df_recebidos.columns and len(df_recebidos) > 0 else 0

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
            delta="emissao > recebimento",
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
        # % recebidos no prazo
        if 'PRAZO_REAL' in df_recebidos.columns and len(df_recebidos) > 0:
            df_rec_valid = df_recebidos[df_recebidos['PRAZO_REAL'].notna() & df_recebidos['PRAZO_CONCEDIDO'].notna()]
            if len(df_rec_valid) > 0:
                pct_no_prazo = (df_rec_valid['PRAZO_REAL'] <= df_rec_valid['PRAZO_CONCEDIDO']).mean() * 100
            else:
                pct_no_prazo = 0
        else:
            pct_no_prazo = 0
        st.metric(
            label="Recebidos no Prazo",
            value=f"{pct_no_prazo:.0f}%",
            delta=f"{len(df_recebidos)} titulos recebidos",
            delta_color="off"
        )

    # Graficos lado a lado
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("###### Clientes com maior prazo concedido")

        # Agrupar por cliente - prazo concedido
        df_cli_prazo = df_prazos.groupby('NOME_CLIENTE').agg({
            'PRAZO_CONCEDIDO': 'mean',
            'VALOR_ORIGINAL': 'sum',
            'CLIENTE': 'count'
        }).reset_index()
        df_cli_prazo.columns = ['Cliente', 'Prazo', 'Valor', 'Qtd']

        # Filtrar clientes com pelo menos 3 titulos
        df_cli_prazo = df_cli_prazo[df_cli_prazo['Qtd'] >= 3]

        # Top 10 mais prazo
        df_mais_prazo = df_cli_prazo.nlargest(10, 'Prazo')
        df_mais_prazo = df_mais_prazo.sort_values('Prazo', ascending=True)

        if len(df_mais_prazo) > 0:
            fig = go.Figure()

            fig.add_trace(go.Bar(
                y=df_mais_prazo['Cliente'].str[:30],
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
        st.markdown("###### Clientes com menor prazo concedido")

        # Recalcular excluindo titulos com prazo <= 2 dias
        df_prazos_pos = df_prazos[df_prazos['PRAZO_CONCEDIDO'] > 2]
        df_cli_prazo_pos = df_prazos_pos.groupby('NOME_CLIENTE').agg({
            'PRAZO_CONCEDIDO': 'mean',
            'VALOR_ORIGINAL': 'sum',
            'CLIENTE': 'count'
        }).reset_index()
        df_cli_prazo_pos.columns = ['Cliente', 'Prazo', 'Valor', 'Qtd']
        df_cli_prazo_pos = df_cli_prazo_pos[df_cli_prazo_pos['Qtd'] >= 3]

        df_menos_prazo = df_cli_prazo_pos.nsmallest(10, 'Prazo')
        df_menos_prazo = df_menos_prazo.sort_values('Prazo', ascending=True)

        if len(df_menos_prazo) > 0:
            fig = go.Figure()

            fig.add_trace(go.Bar(
                y=df_menos_prazo['Cliente'].str[:30],
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

    # Vencimentos no dia da emissao (prazo = 0)
    df_no_dia = df_prazos[df_prazos['PRAZO_CONCEDIDO'] == 0]

    if len(df_no_dia) > 0:
        st.markdown("###### Vencimentos no Dia da Emissao (prazo = 0 dias)")

        total_no_dia = df_no_dia['VALOR_ORIGINAL'].sum()
        total_geral = df_prazos['VALOR_ORIGINAL'].sum()
        pct_no_dia = (total_no_dia / total_geral * 100) if total_geral > 0 else 0

        col1, col2, col3 = st.columns(3)
        col1.metric("Valor Total no Dia", formatar_moeda(total_no_dia))
        col2.metric("Titulos no Dia", formatar_numero(len(df_no_dia)))
        col3.metric("% do Total Emitido", f"{pct_no_dia:.1f}%")

        # Top 10 clientes com mais valor no dia
        df_no_dia_cli = df_no_dia.groupby('NOME_CLIENTE').agg({
            'VALOR_ORIGINAL': 'sum',
            'CLIENTE': 'count'
        }).reset_index()
        df_no_dia_cli.columns = ['Cliente', 'Valor', 'Qtd']
        df_no_dia_top = df_no_dia_cli.nlargest(10, 'Valor').sort_values('Valor', ascending=True)

        fig = go.Figure()

        fig.add_trace(go.Bar(
            y=df_no_dia_top['Cliente'].str[:30],
            x=df_no_dia_top['Valor'],
            orientation='h',
            marker_color=cores['alerta'],
            text=[f"{formatar_moeda(v)} ({int(q)} tit.)" for v, q in zip(df_no_dia_top['Valor'], df_no_dia_top['Qtd'])],
            textposition='outside',
            textfont=dict(size=8, color=cores['texto'])
        ))

        fig.update_layout(
            criar_layout(300),
            margin=dict(l=10, r=120, t=10, b=10),
            xaxis=dict(showticklabels=False, showgrid=False),
            yaxis=dict(tickfont=dict(size=9, color=cores['texto']))
        )

        st.plotly_chart(fig, use_container_width=True)
        st.caption("Titulos emitidos com vencimento no mesmo dia da emissao (prazo concedido = 0 dias).")

    # Tabela comparativa - apenas titulos com prazo = 0
    if len(df_no_dia) > 0:
        with st.expander("Ver detalhes por cliente"):
            df_detalhe_grp = df_no_dia.groupby('NOME_CLIENTE').agg({
                'VALOR_ORIGINAL': 'sum',
                'SALDO': 'sum',
                'CLIENTE': 'count'
            }).reset_index()

            df_detalhe_grp.columns = ['Cliente', 'Valor Total', 'Pendente', 'Qtd']
            df_detalhe_grp['Recebido'] = (df_detalhe_grp['Valor Total'] - df_detalhe_grp['Pendente']).clip(lower=0)

            # Formatar
            df_show = df_detalhe_grp.sort_values('Valor Total', ascending=False).head(50).copy()
            df_show['Valor Total'] = df_show['Valor Total'].apply(lambda x: formatar_moeda(x, completo=True))
            df_show['Recebido'] = df_show['Recebido'].apply(lambda x: formatar_moeda(x, completo=True))
            df_show['Pendente'] = df_show['Pendente'].apply(lambda x: formatar_moeda(x, completo=True))

            st.dataframe(
                df_show[['Cliente', 'Valor Total', 'Recebido', 'Pendente', 'Qtd']],
                use_container_width=True,
                hide_index=True,
                height=300
            )


def _render_curva_abc(df, cores):
    """Curva ABC unificada com analise de concentracao"""

    st.markdown("##### Curva ABC e Concentracao")

    df_abc = df.groupby('NOME_CLIENTE')['VALOR_ORIGINAL'].sum().sort_values(ascending=False).reset_index()
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

    # Cards por classe + Concentracao
    col_a, col_b, col_c, col_conc = st.columns(4)

    for col, classe, qtd, val, cor in [
        (col_a, 'A', qtd_a, val_a, cores['primaria']),
        (col_b, 'B', qtd_b, val_b, cores['alerta']),
        (col_c, 'C', qtd_c, val_c, cores['texto_secundario'])
    ]:
        pct_cli = qtd / len(df_abc) * 100 if len(df_abc) > 0 else 0
        pct_val = val / total * 100

        with col:
            st.markdown(f"""
            <div style="background: {cores['card']}; border-left: 4px solid {cor};
                        border-radius: 4px; padding: 0.6rem;">
                <p style="color: {cor}; font-size: 1rem; font-weight: 700; margin: 0;">
                    Classe {classe}</p>
                <p style="color: {cores['texto']}; font-size: 0.85rem; margin: 0.2rem 0 0 0;">
                    {qtd} clientes ({pct_cli:.0f}%)</p>
                <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0.1rem 0 0 0;">
                    {formatar_moeda(val)} ({pct_val:.1f}%)</p>
            </div>
            """, unsafe_allow_html=True)

    with col_conc:
        conc_lines = ""
        for n in [1, 5, 10, 20]:
            if n <= len(df_abc):
                val_top = df_abc.head(n)['VALOR_ORIGINAL'].sum()
                pct = val_top / total * 100
                conc_lines += f"<p style='color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0.1rem 0;'>Top {n}: <b>{pct:.1f}%</b></p>"

        st.markdown(f"""
        <div style="background: {cores['card']}; border-left: 4px solid {cores['sucesso']};
                    border-radius: 4px; padding: 0.6rem;">
            <p style="color: {cores['sucesso']}; font-size: 1rem; font-weight: 700; margin: 0;">
                Concentracao</p>
            {conc_lines}
        </div>
        """, unsafe_allow_html=True)

    # Selectbox para detalhar classe
    classe_sel = st.selectbox(
        "Detalhar clientes da classe:",
        ['Selecione...', 'Classe A', 'Classe B', 'Classe C'],
        key='abc_classe_detalhe_rec'
    )

    if classe_sel != 'Selecione...':
        letra = classe_sel[-1]  # A, B ou C
        df_classe = df_abc[df_abc['CLASSE'] == letra].copy()

        # Buscar pendente (SALDO) por cliente
        df_saldo = df.groupby('NOME_CLIENTE')['SALDO'].sum().reset_index()
        df_classe = df_classe.merge(df_saldo, on='NOME_CLIENTE', how='left')
        df_classe['RECEBIDO'] = (df_classe['VALOR_ORIGINAL'] - df_classe['SALDO']).clip(lower=0)

        df_classe = df_classe.sort_values('VALOR_ORIGINAL', ascending=False)
        df_show = df_classe[['NOME_CLIENTE', 'VALOR_ORIGINAL', 'RECEBIDO', 'SALDO', 'PCT', 'PCT_ACUM']].copy()
        df_show.columns = ['Cliente', 'Valor Emitido', 'Recebido', 'Pendente', '% do Total', '% Acumulado']

        df_show['Valor Emitido'] = df_show['Valor Emitido'].apply(lambda x: formatar_moeda(x, completo=True))
        df_show['Recebido'] = df_show['Recebido'].apply(lambda x: formatar_moeda(x, completo=True))
        df_show['Pendente'] = df_show['Pendente'].apply(lambda x: formatar_moeda(x, completo=True))
        df_show['% do Total'] = df_show['% do Total'].apply(lambda x: f"{x:.2f}%")
        df_show['% Acumulado'] = df_show['% Acumulado'].apply(lambda x: f"{x:.1f}%")

        st.dataframe(df_show, use_container_width=True, hide_index=True, height=400)


def _render_clientes_por_filial(df, cores):
    """Clientes por filial/grupo - quantidade e valor"""

    multiplos = _detectar_multiplos_grupos_cli(df)

    if 'FILIAL' not in df.columns or 'NOME_FILIAL' not in df.columns:
        return

    if multiplos:
        st.markdown("##### Clientes por Grupo")
        df_aux = df.copy()
        df_aux['LABEL'] = df_aux['FILIAL'].apply(lambda x: _get_nome_grupo_cli(x))
    else:
        st.markdown("##### Clientes por Filial")
        df_aux = df.copy()
        df_aux['LABEL'] = df_aux['FILIAL'].astype(int).astype(str) + ' - ' + df_aux['NOME_FILIAL'].str.split(' - ').str[-1].str.strip()

    # Agrupar por unidade
    df_grp = df_aux.groupby('LABEL').agg(
        Clientes=('NOME_CLIENTE', 'nunique'),
        Valor=('VALOR_ORIGINAL', 'sum'),
        Pendente=('SALDO', 'sum'),
        Titulos=('CLIENTE', 'count')
    ).reset_index()
    df_grp['Recebido'] = df_grp['Valor'] - df_grp['Pendente']

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("###### Clientes por Unidade")
        df_plot = df_grp.sort_values('Clientes', ascending=True)

        fig = go.Figure(go.Bar(
            y=df_plot['LABEL'],
            x=df_plot['Clientes'],
            orientation='h',
            marker_color=cores['sucesso'],
            text=[f"{v} clientes" for v in df_plot['Clientes']],
            textposition='outside',
            textfont=dict(size=9, color=cores['texto']),
            hovertemplate='<b>%{y}</b><br>%{x} clientes<extra></extra>'
        ))

        fig.update_layout(
            criar_layout(280),
            margin=dict(l=10, r=80, t=10, b=10),
            xaxis=dict(showticklabels=False, showgrid=False),
            yaxis=dict(tickfont=dict(size=9, color=cores['texto']))
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("###### Valor por Unidade")
        df_plot = df_grp.sort_values('Valor', ascending=True)

        fig = go.Figure()

        fig.add_trace(go.Bar(
            y=df_plot['LABEL'],
            x=df_plot['Recebido'],
            orientation='h',
            name='Recebido',
            marker_color=cores['sucesso'],
            text=[formatar_moeda(v) if v > 0 else '' for v in df_plot['Recebido']],
            textposition='inside',
            textfont=dict(size=9, color='white')
        ))

        fig.add_trace(go.Bar(
            y=df_plot['LABEL'],
            x=df_plot['Pendente'],
            orientation='h',
            name='Pendente',
            marker_color=cores['alerta'],
            text=[formatar_moeda(v) if v > 0 else '' for v in df_plot['Pendente']],
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


def _render_matriz_filial_cliente(df, cores):
    """Matriz de relacionamento Filial x Cliente"""

    multiplos = _detectar_multiplos_grupos_cli(df)

    # Top 10 clientes
    top10_cli = df.groupby('NOME_CLIENTE')['VALOR_ORIGINAL'].sum().nlargest(10).index.tolist()

    if len(top10_cli) == 0 or 'NOME_FILIAL' not in df.columns:
        st.info("Dados insuficientes")
        return

    # Filtrar e criar pivot
    df_matriz = df[df['NOME_CLIENTE'].isin(top10_cli)].copy()

    if multiplos:
        st.markdown("##### Matriz Grupo x Cliente")
        df_matriz['GRUPO'] = df_matriz['FILIAL'].apply(lambda x: _get_nome_grupo_cli(x))
        pivot = df_matriz.pivot_table(
            values='VALOR_ORIGINAL',
            index='GRUPO',
            columns='NOME_CLIENTE',
            aggfunc='sum',
            fill_value=0
        )
    else:
        st.markdown("##### Matriz Filial x Cliente")
        df_matriz['FILIAL_LABEL'] = df_matriz['FILIAL'].astype(int).astype(str) + ' - ' + df_matriz['NOME_FILIAL'].str.split(' - ').str[-1].str.strip()
        pivot = df_matriz.pivot_table(
            values='VALOR_ORIGINAL',
            index='FILIAL_LABEL',
            columns='NOME_CLIENTE',
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
        hovertemplate='Filial: %{y}<br>Cliente: %{x}<br>Valor: R$ %{z:,.0f}<extra></extra>'
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
        for cli in top10_cli[:5]:
            if cli in pivot.columns:
                total_cli = pivot[cli].sum()
                if total_cli > 0:
                    max_filial = pivot[cli].idxmax()
                    pct_max = pivot[cli].max() / total_cli * 100
                    if pct_max > 70:
                        st.caption(f"**{cli[:30]}**: {pct_max:.0f}% concentrado em {max_filial}")


def _render_por_categoria(df, cores):
    """Valores por categoria (DESCRICAO) - Recebido vs Pendente"""

    st.markdown("##### Por Categoria")

    if 'DESCRICAO' not in df.columns:
        st.info("Sem dados de categoria")
        return

    # Agrupar por categoria
    df_cat = df.groupby('DESCRICAO').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'NOME_CLIENTE': 'nunique'
    }).reset_index()
    df_cat.columns = ['Categoria', 'Total', 'Pendente', 'Clientes']
    df_cat['Recebido'] = df_cat['Total'] - df_cat['Pendente']

    # Vencido por categoria
    if 'STATUS' in df.columns:
        df_vencido_cat = df[df['STATUS'] == 'Vencido'].groupby('DESCRICAO')['SALDO'].sum().reset_index()
        df_vencido_cat.columns = ['Categoria', 'Vencido']
        df_cat = df_cat.merge(df_vencido_cat, on='Categoria', how='left')
        df_cat['Vencido'] = df_cat['Vencido'].fillna(0)
    else:
        df_cat['Vencido'] = 0
    df_cat['A_Vencer'] = (df_cat['Pendente'] - df_cat['Vencido']).clip(lower=0)

    # Top 12
    df_top = df_cat.nlargest(12, 'Total')
    df_top = df_top.sort_values('Total', ascending=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("###### Top 10 - Recebido")
        df_top_rec = df_top.sort_values('Recebido', ascending=True).tail(10)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=df_top_rec['Categoria'].str[:30],
            x=df_top_rec['Recebido'],
            orientation='h',
            marker_color=cores['sucesso'],
            text=[formatar_moeda(v) if v > 0 else '' for v in df_top_rec['Recebido']],
            textposition='outside',
            textfont=dict(size=8, color=cores['texto'])
        ))
        fig.update_layout(
            criar_layout(350),
            margin=dict(l=10, r=80, t=10, b=10),
            xaxis=dict(showticklabels=False, showgrid=False),
            yaxis=dict(tickfont=dict(size=9, color=cores['texto'])),
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("###### Top 10 - Pendente (a vencer)")
        df_top_avencer = df_top.sort_values('A_Vencer', ascending=True).tail(10)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=df_top_avencer['Categoria'].str[:30],
            x=df_top_avencer['A_Vencer'],
            orientation='h',
            marker_color=cores['alerta'],
            text=[formatar_moeda(v) if v > 0 else '' for v in df_top_avencer['A_Vencer']],
            textposition='outside',
            textfont=dict(size=8, color=cores['texto'])
        ))
        fig.update_layout(
            criar_layout(350),
            margin=dict(l=10, r=80, t=10, b=10),
            xaxis=dict(showticklabels=False, showgrid=False),
            yaxis=dict(tickfont=dict(size=9, color=cores['texto'])),
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)

    with col3:
        st.markdown("###### Top 10 - Vencido")
        df_top_venc = df_top.sort_values('Vencido', ascending=True).tail(10)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=df_top_venc['Categoria'].str[:30],
            x=df_top_venc['Vencido'],
            orientation='h',
            marker_color=cores['perigo'],
            text=[formatar_moeda(v) if v > 0 else '' for v in df_top_venc['Vencido']],
            textposition='outside',
            textfont=dict(size=8, color=cores['texto'])
        ))
        fig.update_layout(
            criar_layout(350),
            margin=dict(l=10, r=80, t=10, b=10),
            xaxis=dict(showticklabels=False, showgrid=False),
            yaxis=dict(tickfont=dict(size=9, color=cores['texto'])),
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)

    # Detalhar categoria
    categorias_lista = df_top.sort_values('Total', ascending=False)['Categoria'].tolist()
    cat_sel = st.selectbox(
        "Detalhar categoria:",
        options=categorias_lista,
        key="cli_cat_detalhe_rec"
    )

    if cat_sel:
        row_cat = df_top[df_top['Categoria'] == cat_sel].iloc[0]
        pct_rec = (row_cat['Recebido'] / row_cat['Total'] * 100) if row_cat['Total'] > 0 else 0

        col_r1, col_r2, col_r3 = st.columns(3)
        col_r1.metric("Total", formatar_moeda(row_cat['Total']))
        col_r2.metric("Pendente", formatar_moeda(row_cat['Pendente']))
        col_r3.metric("Clientes", f"{int(row_cat['Clientes'])} | {pct_rec:.0f}% recebido")

        # Clientes da categoria selecionada
        df_cat_cli = df[df['DESCRICAO'] == cat_sel].groupby('NOME_CLIENTE').agg({
            'VALOR_ORIGINAL': 'sum',
            'SALDO': 'sum',
            'CLIENTE': 'count'
        }).reset_index()
        df_cat_cli.columns = ['Cliente', 'Total', 'Pendente', 'Qtd']
        df_cat_cli = df_cat_cli.sort_values('Total', ascending=False)

        df_cat_show = df_cat_cli.copy()
        df_cat_show['Cliente'] = df_cat_show['Cliente'].str[:25]
        df_cat_show['Total'] = df_cat_show['Total'].apply(lambda x: formatar_moeda(x, completo=True))
        df_cat_show['Pendente'] = df_cat_show['Pendente'].apply(lambda x: formatar_moeda(x, completo=True))

        st.dataframe(df_cat_show, use_container_width=True, hide_index=True, height=280)


def _render_consulta_cliente(df, cores):
    """Consulta detalhada de cliente - Raio-X completo"""

    st.markdown("##### Raio-X do Cliente")

    clientes = sorted([str(x) for x in df['NOME_CLIENTE'].unique().tolist()])

    cliente_selecionado = st.selectbox(
        "Selecione um cliente",
        options=[""] + clientes,
        key="busca_cli_rec"
    )

    if not cliente_selecionado:
        st.info("Selecione um cliente para ver detalhes")
        return

    df_cli = df[df['NOME_CLIENTE'] == cliente_selecionado]

    # Metricas basicas
    total_valor = df_cli['VALOR_ORIGINAL'].sum()
    total_pendente = df_cli['SALDO'].sum()
    total_recebido = total_valor - total_pendente
    qtd_titulos = len(df_cli)
    pct_recebido = (total_recebido / total_valor * 100) if total_valor > 0 else 0
    ticket_medio = total_valor / qtd_titulos if qtd_titulos > 0 else 0

    # Classe ABC
    classes = _calcular_classe_abc(df)
    classe = classes.get(cliente_selecionado, 'C')
    cor_classe = {'A': cores['primaria'], 'B': cores['alerta'], 'C': cores['texto_secundario']}.get(classe, cores['texto'])

    # Prazo medio concedido
    df_cli_prazos = df_cli.copy()
    df_cli_prazos['PRAZO_CONC'] = (df_cli_prazos['VENCIMENTO'] - df_cli_prazos['EMISSAO']).dt.days
    prazo_medio = df_cli_prazos['PRAZO_CONC'].mean()

    # Atraso medio (dos recebidos)
    atraso_medio = 0
    df_rec_cli = df_cli[df_cli['SALDO'] == 0].copy()
    if 'DT_BAIXA' in df_rec_cli.columns and len(df_rec_cli) > 0:
        df_rec_cli['ATRASO'] = (df_rec_cli['DT_BAIXA'] - df_rec_cli['VENCIMENTO']).dt.days
        atraso_vals = df_rec_cli[df_rec_cli['ATRASO'] > 0]['ATRASO']
        atraso_medio = atraso_vals.mean() if len(atraso_vals) > 0 else 0

    # Filiais que vendem para este cliente
    filiais_cli = []
    if 'NOME_FILIAL' in df_cli.columns:
        filiais_cli = df_cli['NOME_FILIAL'].unique().tolist()

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
    col3.metric("Recebido", formatar_moeda(total_recebido), f"{pct_recebido:.1f}%")
    col4.metric("Pendente", formatar_moeda(total_pendente))
    col5.metric("Ticket Medio", formatar_moeda(ticket_medio))

    prazo_str = f"{prazo_medio:.0f} dias" if pd.notna(prazo_medio) else "N/A"
    atraso_str = f"{atraso_medio:.0f} dias" if pd.notna(atraso_medio) and atraso_medio > 0 else "Sem atraso"
    col6.metric("Prazo Medio", prazo_str, atraso_str if atraso_medio > 0 else None)

    # Filiais
    if len(filiais_cli) > 0:
        filiais_txt = " | ".join([f.split(' - ')[-1].strip()[:20] if ' - ' in str(f) else str(f)[:20] for f in filiais_cli[:6]])
        st.caption(f"Filiais: {filiais_txt}")

    # Tabs
    tab1, tab2 = st.tabs(["Evolucao", "Titulos"])

    with tab1:
        df_hist = df_cli.copy()
        df_hist['MES'] = df_hist['EMISSAO'].dt.to_period('M').astype(str)
        df_hist_grp = df_hist.groupby('MES').agg({
            'VALOR_ORIGINAL': 'sum',
            'SALDO': 'sum'
        }).reset_index()
        df_hist_grp['RECEBIDO'] = df_hist_grp['VALOR_ORIGINAL'] - df_hist_grp['SALDO']

        if len(df_hist_grp) > 1:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df_hist_grp['MES'],
                y=df_hist_grp['RECEBIDO'],
                name='Recebido',
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
        colunas = ['NOME_FILIAL', 'TIPO', 'NUMERO', 'DESCRICAO', 'EMISSAO', 'VENCIMENTO', 'VALOR_ORIGINAL', 'SALDO']
        colunas_disp = [c for c in colunas if c in df_cli.columns]
        df_tab = df_cli[colunas_disp].copy()

        for col in ['EMISSAO', 'VENCIMENTO']:
            if col in df_tab.columns:
                df_tab[col] = pd.to_datetime(df_tab[col], errors='coerce').dt.strftime('%d/%m/%Y')
                df_tab[col] = df_tab[col].fillna('-')

        df_tab['VALOR_ORIGINAL'] = df_tab['VALOR_ORIGINAL'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab['SALDO'] = df_tab['SALDO'].apply(lambda x: formatar_moeda(x, completo=True))

        nomes = {
            'NOME_FILIAL': 'Filial',
            'TIPO': 'Tipo',
            'NUMERO': 'Numero Doc',
            'DESCRICAO': 'Categoria',
            'EMISSAO': 'Emissao',
            'VENCIMENTO': 'Vencimento',
            'VALOR_ORIGINAL': 'Valor',
            'SALDO': 'Pendente'
        }
        df_tab.columns = [nomes.get(c, c) for c in df_tab.columns]

        st.dataframe(df_tab, use_container_width=True, hide_index=True, height=300)


def _render_ranking(df, cores):
    """Ranking de clientes"""

    st.markdown("##### Ranking de Clientes")

    # Filtros
    col1, col2, col3 = st.columns(3)

    with col1:
        ordenar = st.selectbox(
            "Ordenar por",
            ["Valor Total", "Valor Recebido", "Saldo Pendente", "Vencido"],
            key="rank_ordem_rec"
        )

    with col2:
        qtd_exibir = st.selectbox("Exibir", [20, 50, 100], key="rank_qtd_rec")

    with col3:
        filtro = st.selectbox("Filtrar", ["Todos", "Com Pendencia", "Quitados"], key="rank_filtro_rec")

    # Preparar dados
    df_rank = df.groupby('NOME_CLIENTE').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'CLIENTE': 'count'
    }).reset_index()
    df_rank.columns = ['Cliente', 'Total', 'Pendente', 'Titulos']
    df_rank['Recebido'] = df_rank['Total'] - df_rank['Pendente']
    df_rank['% Recebido'] = ((df_rank['Recebido']) / df_rank['Total'] * 100).round(1)

    # Vencido por cliente
    if 'STATUS' in df.columns:
        df_venc = df[df['STATUS'] == 'Vencido'].groupby('NOME_CLIENTE')['SALDO'].sum().reset_index()
        df_venc.columns = ['Cliente', 'Vencido']
        df_rank = df_rank.merge(df_venc, on='Cliente', how='left')
        df_rank['Vencido'] = df_rank['Vencido'].fillna(0)
    else:
        df_rank['Vencido'] = 0

    # Classe ABC
    classes = _calcular_classe_abc(df)
    df_rank['Classe'] = df_rank['Cliente'].map(classes).fillna('C')

    # Filtrar
    if filtro == "Com Pendencia":
        df_rank = df_rank[df_rank['Pendente'] > 0]
    elif filtro == "Quitados":
        df_rank = df_rank[df_rank['Pendente'] <= 0]

    # Ordenar
    if ordenar == "Valor Total":
        df_rank = df_rank.sort_values('Total', ascending=False)
    elif ordenar == "Valor Recebido":
        df_rank = df_rank.sort_values('Recebido', ascending=False)
    elif ordenar == "Vencido":
        df_rank = df_rank.sort_values('Vencido', ascending=False)
    else:
        df_rank = df_rank.sort_values('Pendente', ascending=False)

    df_rank = df_rank.head(qtd_exibir)

    # Formatar
    df_show = df_rank.copy()
    df_show['Total'] = df_show['Total'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Recebido'] = df_show['Recebido'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Pendente'] = df_show['Pendente'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Vencido'] = df_show['Vencido'].apply(lambda x: formatar_moeda(x, completo=True))

    df_show = df_show[['Cliente', 'Classe', 'Total', 'Recebido', 'Pendente', 'Vencido', 'Titulos', '% Recebido']]

    st.dataframe(
        df_show,
        use_container_width=True,
        hide_index=True,
        height=400,
        column_config={
            "% Recebido": st.column_config.ProgressColumn(
                "% Recebido",
                format="%.1f%%",
                min_value=0,
                max_value=100
            )
        }
    )

    st.caption(f"Exibindo {len(df_show)} clientes")
