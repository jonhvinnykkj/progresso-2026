"""
Aba Concentracao e Risco - Analise de exposicao e risco de credito
Foco: Concentracao de clientes + Risco de inadimplencia
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from config.theme import get_cores
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero


def render_concentracao_risco(df):
    """Renderiza a aba de Concentracao e Risco"""
    cores = get_cores()

    if len(df) == 0:
        st.warning("Nenhum dado disponivel.")
        return

    col_cliente = 'NOME_CLIENTE'
    df = df.copy()

    # ========== HEADER ==========
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, {cores['card']}, {cores['fundo']});
                border-left: 4px solid {cores['alerta']}; border-radius: 0 10px 10px 0;
                padding: 1rem; margin-bottom: 1rem;">
        <h4 style="color: {cores['texto']}; margin: 0;">Analise de Concentracao e Risco de Credito</h4>
        <p style="color: {cores['texto_secundario']}; font-size: 0.8rem; margin: 0.25rem 0 0 0;">
            Exposicao por cliente | Risco de inadimplencia | Score de credito
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ========== PAINEL DE RISCO ==========
    _render_painel_risco(df, col_cliente, cores)

    st.divider()

    # ========== INDICADORES DE CONCENTRACAO ==========
    _render_indicadores_concentracao(df, col_cliente, cores)

    st.divider()

    # ========== EVOLUCAO + COMPARATIVO ==========
    col1, col2 = st.columns(2)

    with col1:
        _render_evolucao_concentracao(df, col_cliente, cores)

    with col2:
        _render_concentracao_por_filial(df, col_cliente, cores)

    st.divider()

    # ========== CONCENTRACAO: TOP CLIENTES + CURVA ==========
    col1, col2 = st.columns(2)

    with col1:
        _render_top_devedores(df, col_cliente, cores)

    with col2:
        _render_curva_concentracao(df, col_cliente, cores)

    st.divider()

    # ========== RISCO: SCORE + MATRIZ ==========
    col1, col2 = st.columns(2)

    with col1:
        _render_score_risco(df, col_cliente, cores)

    with col2:
        _render_matriz_risco(df, col_cliente, cores)

    st.divider()

    # ========== AGING TOP DEVEDORES + SIMULACAO ==========
    col1, col2 = st.columns(2)

    with col1:
        _render_aging_top_devedores(df, col_cliente, cores)

    with col2:
        _render_simulacao_impacto(df, col_cliente, cores)

    st.divider()

    # ========== CLIENTES EM ALERTA ==========
    _render_clientes_alerta(df, col_cliente, cores)

    st.divider()

    # ========== HISTORICO DO CLIENTE ==========
    _render_historico_cliente(df, col_cliente, cores)

    st.divider()

    # ========== RANKING DE RISCO ==========
    _render_ranking_risco(df, col_cliente, cores)


def _render_painel_risco(df, col_cliente, cores):
    """Painel de alertas de risco"""

    total_saldo = df['SALDO'].sum()
    df_vencidos = df[df['DIAS_ATRASO'] > 0]
    total_vencido = df_vencidos['SALDO'].sum()

    # Calcular metricas de risco
    df_cli = df.groupby(col_cliente)['SALDO'].sum()
    top5_valor = df_cli.nlargest(5).sum()
    conc_top5 = top5_valor / total_saldo * 100 if total_saldo > 0 else 0

    pct_vencido = total_vencido / total_saldo * 100 if total_saldo > 0 else 0
    total_90d = df[df['DIAS_ATRASO'] > 90]['SALDO'].sum()
    clientes_criticos = (df_vencidos.groupby(col_cliente)['SALDO'].sum() > 50000).sum()

    # Nivel de risco geral
    score_geral = 0
    if conc_top5 > 50:
        score_geral += 30
    elif conc_top5 > 35:
        score_geral += 15

    if pct_vencido > 30:
        score_geral += 40
    elif pct_vencido > 15:
        score_geral += 20

    if total_90d > 0:
        score_geral += 30

    if score_geral >= 60:
        nivel_risco = "CRITICO"
        cor_risco = cores['perigo']
    elif score_geral >= 35:
        nivel_risco = "ALTO"
        cor_risco = cores['alerta']
    elif score_geral >= 15:
        nivel_risco = "MODERADO"
        cor_risco = '#fbbf24'
    else:
        nivel_risco = "BAIXO"
        cor_risco = cores['sucesso']

    # Renderizar painel
    col1, col2, col3, col4, col5 = st.columns([1.5, 1, 1, 1, 1])

    with col1:
        st.markdown(f"""
        <div style="background: {cores['card']}; border: 2px solid {cor_risco};
                    border-radius: 10px; padding: 1rem; text-align: center; height: 100%;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">NIVEL DE RISCO</p>
            <p style="color: {cor_risco}; font-size: 1.8rem; font-weight: 800; margin: 0.25rem 0;">{nivel_risco}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">Score: {score_geral}/100</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.metric("Concentracao Top 5", f"{conc_top5:.1f}%", "ALTO" if conc_top5 > 35 else "OK", delta_color="inverse" if conc_top5 > 35 else "normal")

    with col3:
        st.metric("% Vencido", f"{pct_vencido:.1f}%", formatar_moeda(total_vencido), delta_color="inverse" if pct_vencido > 15 else "off")

    with col4:
        st.metric("Vencido +90d", formatar_moeda(total_90d), "CRITICO" if total_90d > 0 else "OK", delta_color="inverse" if total_90d > 0 else "normal")

    with col5:
        st.metric("Clientes Criticos", clientes_criticos, "+R$ 50k vencido", delta_color="inverse" if clientes_criticos > 0 else "off")


def _render_indicadores_concentracao(df, col_cliente, cores):
    """Indicadores de concentracao"""

    total_saldo = df['SALDO'].sum()
    total_clientes = df[col_cliente].nunique()

    df_cli = df.groupby(col_cliente)['SALDO'].sum().sort_values(ascending=False)

    # Calcular concentracoes
    top1 = df_cli.iloc[0] / total_saldo * 100 if len(df_cli) > 0 else 0
    top5 = df_cli.head(5).sum() / total_saldo * 100 if len(df_cli) >= 5 else 0
    top10 = df_cli.head(10).sum() / total_saldo * 100 if len(df_cli) >= 10 else 0
    top20 = df_cli.head(20).sum() / total_saldo * 100 if len(df_cli) >= 20 else 0

    # HHI
    shares = df_cli / total_saldo * 100
    hhi = (shares ** 2).sum()

    # Gini
    n = len(df_cli)
    if n > 0:
        pct_acum = (df_cli.cumsum() / total_saldo * 100).tolist()
        area = sum(pct_acum) / len(pct_acum) / 100
        gini = (0.5 - area) / 0.5
    else:
        gini = 0

    # Clientes para 80%
    df_cli_acum = df_cli.cumsum() / total_saldo * 100
    cli_80 = (df_cli_acum <= 80).sum() + 1

    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)

    col1.metric("Total Clientes", formatar_numero(total_clientes))
    col2.metric("Top 1", f"{top1:.1f}%", df_cli.index[0][:12] if len(df_cli) > 0 else "")
    col3.metric("Top 5", f"{top5:.1f}%")
    col4.metric("Top 10", f"{top10:.1f}%")
    col5.metric("Top 20", f"{top20:.1f}%")
    col6.metric("Clientes p/ 80%", f"{cli_80}", f"{cli_80/total_clientes*100:.1f}% do total")

    # HHI classificacao
    if hhi < 1500:
        hhi_class = "Baixa"
    elif hhi < 2500:
        hhi_class = "Moderada"
    else:
        hhi_class = "Alta"

    col7.metric("Indice HHI", f"{hhi:.0f}", f"Concentracao {hhi_class}")


def _render_evolucao_concentracao(df, col_cliente, cores):
    """Evolucao temporal da concentracao"""

    st.markdown("##### Evolucao da Concentracao")

    if 'EMISSAO' not in df.columns:
        st.info("Coluna EMISSAO nao disponivel")
        return

    df_temp = df.copy()
    df_temp['MES'] = df_temp['EMISSAO'].dt.to_period('M')

    meses = sorted(df_temp['MES'].unique())
    if len(meses) < 2:
        st.info("Dados insuficientes para evolucao")
        return

    # Calcular concentracao por mes
    dados_evolucao = []
    for mes in meses[-12:]:  # Ultimos 12 meses
        df_mes = df_temp[df_temp['MES'] == mes]
        total_mes = df_mes['SALDO'].sum()

        if total_mes > 0:
            df_cli_mes = df_mes.groupby(col_cliente)['SALDO'].sum().sort_values(ascending=False)

            top5 = df_cli_mes.head(5).sum() / total_mes * 100 if len(df_cli_mes) >= 5 else 0
            top10 = df_cli_mes.head(10).sum() / total_mes * 100 if len(df_cli_mes) >= 10 else 0

            dados_evolucao.append({
                'Mes': str(mes),
                'Top 5': top5,
                'Top 10': top10
            })

    if len(dados_evolucao) < 2:
        st.info("Dados insuficientes")
        return

    df_evol = pd.DataFrame(dados_evolucao)

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df_evol['Mes'],
        y=df_evol['Top 5'],
        mode='lines+markers',
        name='Top 5',
        line=dict(color=cores['perigo'], width=2),
        marker=dict(size=8)
    ))

    fig.add_trace(go.Scatter(
        x=df_evol['Mes'],
        y=df_evol['Top 10'],
        mode='lines+markers',
        name='Top 10',
        line=dict(color=cores['alerta'], width=2),
        marker=dict(size=8)
    ))

    # Linha de referencia
    fig.add_hline(y=50, line_dash="dash", line_color=cores['texto_secundario'],
                  annotation_text="50%", annotation_position="right")

    fig.update_layout(
        criar_layout(300),
        xaxis_title='',
        yaxis_title='% do Saldo',
        yaxis=dict(range=[0, 100]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=40, b=60),
        xaxis_tickangle=-45
    )

    st.plotly_chart(fig, use_container_width=True)

    # Tendencia
    if len(df_evol) >= 3:
        ultimo = df_evol['Top 5'].iloc[-1]
        anterior = df_evol['Top 5'].iloc[-2]
        variacao = ultimo - anterior

        if variacao > 2:
            st.warning(f"Concentracao Top 5 aumentou {variacao:.1f}pp no ultimo mes")
        elif variacao < -2:
            st.success(f"Concentracao Top 5 reduziu {abs(variacao):.1f}pp no ultimo mes")


def _render_concentracao_por_filial(df, col_cliente, cores):
    """Concentracao por filial - visão detalhada"""

    st.markdown("##### Concentração por Filial")
    st.caption("Quanto do saldo de cada filial está concentrado nos 5 maiores clientes")

    if 'NOME_FILIAL' not in df.columns:
        st.info("Coluna NOME_FILIAL nao disponivel")
        return

    # Agrupar por filial
    filiais = df['NOME_FILIAL'].dropna().unique().tolist()

    dados_filial = []
    for filial in filiais:
        df_fil = df[df['NOME_FILIAL'] == filial]
        total_fil = df_fil['SALDO'].sum()
        cod_filial = df_fil['FILIAL'].iloc[0] if 'FILIAL' in df_fil.columns and len(df_fil) > 0 else ''

        if total_fil > 0:
            df_cli = df_fil.groupby(col_cliente)['SALDO'].sum().sort_values(ascending=False)

            top5_valor = df_cli.head(5).sum()
            top5_pct = top5_valor / total_fil * 100 if len(df_cli) >= 5 else 100
            n_clientes = len(df_cli)
            maior_cliente = df_cli.index[0] if len(df_cli) > 0 else ''
            maior_cliente_pct = df_cli.iloc[0] / total_fil * 100 if len(df_cli) > 0 else 0

            # Vencido da filial
            vencido = df_fil[df_fil['STATUS'] == 'Vencido']['SALDO'].sum()

            dados_filial.append({
                'Codigo': cod_filial,
                'Filial': filial,
                'Saldo': total_fil,
                'Vencido': vencido,
                'Top5_Pct': top5_pct,
                'Top5_Valor': top5_valor,
                'Clientes': n_clientes,
                'Maior_Cliente': maior_cliente,
                'Maior_Pct': maior_cliente_pct
            })

    if len(dados_filial) == 0:
        st.info("Sem dados por filial")
        return

    df_fil = pd.DataFrame(dados_filial).sort_values('Saldo', ascending=False)

    # Padronizar nomes para exibição
    def _padronizar(row):
        nome = str(row['Filial']).upper() if row['Filial'] else ''
        cod = row['Codigo']

        nome_curto = nome
        if 'AGROINDUSTRIAL' in nome and 'GO' in nome:
            nome_curto = 'Progresso GO'
        elif 'AGROINDUSTRIAL' in nome and 'MT' in nome:
            nome_curto = 'Progresso MT'
        elif 'BRASIL AGRICOLA' in nome:
            nome_curto = 'Brasil Agricola'
        elif 'FAZENDA' in nome:
            nome_curto = 'Fazenda'
        elif 'PROGRESSO MATRIZ' in nome:
            nome_curto = 'Progresso Matriz'
        elif 'RAINHA DA SERRA' in nome:
            nome_curto = 'Rainha da Serra'
        else:
            nome_curto = nome[:18]

        if cod:
            return f"{int(cod)} - {nome_curto}"
        return nome_curto

    df_fil['Filial_Display'] = df_fil.apply(_padronizar, axis=1)

    # Layout: Gráfico + Tabela
    col_graf, col_tab = st.columns([1, 1])

    with col_graf:
        # Cores por nivel de concentracao
        def get_cor(top5):
            if top5 > 70:
                return cores['perigo']
            elif top5 > 50:
                return cores['alerta']
            elif top5 > 30:
                return '#fbbf24'
            return cores['sucesso']

        df_plot = df_fil.head(10).sort_values('Top5_Pct', ascending=True)
        colors = [get_cor(t) for t in df_plot['Top5_Pct']]

        fig = go.Figure(go.Bar(
            y=df_plot['Filial_Display'],
            x=df_plot['Top5_Pct'],
            orientation='h',
            marker_color=colors,
            text=[f"{t:.0f}%" for t in df_plot['Top5_Pct']],
            textposition='outside',
            textfont=dict(size=9),
            hovertemplate="<b>%{y}</b><br>Concentração Top 5: %{x:.1f}%<extra></extra>"
        ))

        fig.add_vline(x=50, line_dash="dash", line_color=cores['texto_secundario'],
                      annotation_text="50%", annotation_position="top")

        fig.update_layout(
            criar_layout(320),
            xaxis_title='Concentração Top 5 (%)',
            xaxis=dict(range=[0, 110]),
            margin=dict(l=10, r=50, t=10, b=30)
        )

        st.plotly_chart(fig, use_container_width=True)

    with col_tab:
        # Tabela detalhada
        df_tabela = df_fil.head(10).copy()
        df_tabela['Saldo_Fmt'] = df_tabela['Saldo'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tabela['Top5_Fmt'] = df_tabela['Top5_Pct'].apply(lambda x: f"{x:.0f}%")
        df_tabela['Maior_Fmt'] = df_tabela.apply(
            lambda x: f"{x['Maior_Cliente'][:15]}... ({x['Maior_Pct']:.0f}%)" if len(x['Maior_Cliente']) > 15
            else f"{x['Maior_Cliente']} ({x['Maior_Pct']:.0f}%)",
            axis=1
        )

        df_show = df_tabela[['Filial_Display', 'Saldo_Fmt', 'Clientes', 'Top5_Fmt', 'Maior_Fmt']].copy()
        df_show.columns = ['Filial', 'Saldo', 'Clientes', 'Top 5', 'Maior Cliente']

        st.dataframe(
            df_show,
            use_container_width=True,
            hide_index=True,
            height=320
        )

    # Legenda de cores
    st.markdown(f"""
    <div style="display: flex; gap: 1.5rem; font-size: 0.75rem; color: {cores['texto_secundario']}; margin-top: 0.5rem;">
        <span><span style="color: {cores['sucesso']};">●</span> Baixa (até 30%)</span>
        <span><span style="color: #fbbf24;">●</span> Moderada (31-50%)</span>
        <span><span style="color: {cores['alerta']};">●</span> Alta (51-70%)</span>
        <span><span style="color: {cores['perigo']};">●</span> Crítica (+70%)</span>
    </div>
    """, unsafe_allow_html=True)

    # Expander com detalhamento por filial
    with st.expander("Ver detalhes dos Top 5 clientes por filial"):
        filial_sel = st.selectbox(
            "Selecione a filial",
            options=df_fil['Filial_Display'].tolist(),
            key="conc_filial_sel"
        )

        if filial_sel:
            # Buscar código da filial selecionada
            cod_sel = df_fil[df_fil['Filial_Display'] == filial_sel]['Codigo'].iloc[0]
            nome_sel = df_fil[df_fil['Filial_Display'] == filial_sel]['Filial'].iloc[0]

            # Filtrar dados da filial
            if cod_sel:
                df_filial_sel = df[df['FILIAL'] == cod_sel]
            else:
                df_filial_sel = df[df['NOME_FILIAL'] == nome_sel]

            # Top 5 clientes
            df_top5 = df_filial_sel.groupby(col_cliente).agg({
                'SALDO': 'sum',
                'VALOR_ORIGINAL': ['sum', 'count']
            }).reset_index()
            df_top5.columns = ['Cliente', 'Saldo', 'Valor_Total', 'Titulos']
            df_top5 = df_top5.sort_values('Saldo', ascending=False).head(5)

            total_filial = df_filial_sel['SALDO'].sum()
            df_top5['Pct'] = (df_top5['Saldo'] / total_filial * 100).round(1)

            # Mostrar
            col1, col2 = st.columns([2, 1])

            with col1:
                df_top5_show = df_top5.copy()
                df_top5_show['Saldo'] = df_top5_show['Saldo'].apply(lambda x: formatar_moeda(x, completo=True))
                df_top5_show['Pct'] = df_top5_show['Pct'].apply(lambda x: f"{x:.1f}%")
                df_top5_show = df_top5_show[['Cliente', 'Saldo', 'Titulos', 'Pct']]
                df_top5_show.columns = ['Cliente', 'Saldo', 'Títulos', '% da Filial']

                st.dataframe(df_top5_show, use_container_width=True, hide_index=True)

            with col2:
                conc_top5 = df_top5['Saldo'].sum() / total_filial * 100 if total_filial > 0 else 0
                st.metric("Concentração Top 5", f"{conc_top5:.1f}%")
                st.metric("Total da Filial", formatar_moeda(total_filial))
                st.metric("Total Clientes", df_filial_sel[col_cliente].nunique())


def _render_top_devedores(df, col_cliente, cores):
    """Top clientes devedores"""

    st.markdown("##### Top 20 Maiores Devedores")

    total_saldo = df['SALDO'].sum()

    df_cli = df.groupby(col_cliente).agg({
        'SALDO': 'sum',
        'DIAS_ATRASO': 'max'
    }).nlargest(20, 'SALDO').reset_index()

    df_cli['Pct'] = df_cli['SALDO'] / total_saldo * 100
    df_cli['Acum'] = df_cli['Pct'].cumsum()

    # Cores por status de atraso
    def get_cor(dias):
        if dias > 90:
            return cores['perigo']
        elif dias > 60:
            return '#f97316'
        elif dias > 30:
            return cores['alerta']
        elif dias > 0:
            return '#fbbf24'
        return cores['sucesso']

    colors = [get_cor(d) for d in df_cli['DIAS_ATRASO']]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=df_cli[col_cliente].str[:22],
        x=df_cli['SALDO'],
        orientation='h',
        marker_color=colors,
        text=[f"{formatar_moeda(v)} | {p:.1f}%" for v, p in zip(df_cli['SALDO'], df_cli['Pct'])],
        textposition='outside',
        textfont=dict(size=8),
        hovertemplate='<b>%{y}</b><br>Saldo: %{text}<br>Atraso: %{customdata}d<extra></extra>',
        customdata=df_cli['DIAS_ATRASO']
    ))

    fig.update_layout(
        criar_layout(480),
        yaxis={'autorange': 'reversed'},
        margin=dict(l=10, r=100, t=10, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)

    # Legenda
    st.markdown(f"""
    <div style="display: flex; gap: 1rem; font-size: 0.7rem; color: {cores['texto_secundario']};">
        <span><span style="color: {cores['sucesso']};">●</span> Em dia</span>
        <span><span style="color: #fbbf24;">●</span> 1-30d</span>
        <span><span style="color: {cores['alerta']};">●</span> 31-60d</span>
        <span><span style="color: #f97316;">●</span> 61-90d</span>
        <span><span style="color: {cores['perigo']};">●</span> +90d</span>
    </div>
    """, unsafe_allow_html=True)


def _render_curva_concentracao(df, col_cliente, cores):
    """Curva de Lorenz com analise"""

    st.markdown("##### Curva de Concentracao")

    df_cli = df.groupby(col_cliente)['SALDO'].sum().sort_values(ascending=False)
    total = df_cli.sum()

    if total == 0:
        st.info("Sem dados")
        return

    n = len(df_cli)
    pct_clientes = [(i + 1) / n * 100 for i in range(n)]
    pct_valor_acum = (df_cli.cumsum() / total * 100).tolist()

    fig = go.Figure()

    # Linha de igualdade
    fig.add_trace(go.Scatter(
        x=[0, 100], y=[0, 100],
        mode='lines', name='Distribuicao Uniforme',
        line=dict(color=cores['texto_secundario'], dash='dash', width=1)
    ))

    # Curva real
    fig.add_trace(go.Scatter(
        x=[0] + pct_clientes,
        y=[0] + pct_valor_acum,
        mode='lines', name='Concentracao Real',
        fill='tozeroy',
        line=dict(color=cores['primaria'], width=2),
        fillcolor='rgba(59, 130, 246, 0.15)'
    ))

    # Marcadores de referencia
    referencias = [
        (10, 'Top 10%'),
        (20, 'Top 20%'),
        (50, 'Top 50%')
    ]

    for pct, label in referencias:
        idx = int(n * pct / 100)
        if idx > 0 and idx < len(pct_valor_acum):
            valor = pct_valor_acum[idx-1]
            fig.add_annotation(
                x=pct, y=valor,
                text=f"{label}: {valor:.0f}%",
                showarrow=True, arrowhead=2, arrowsize=0.8,
                font=dict(size=9, color=cores['texto']),
                bgcolor=cores['card'], bordercolor=cores['borda']
            )

    # Linha 80%
    fig.add_hline(y=80, line_dash="dot", line_color=cores['sucesso'],
                  annotation_text="80% do saldo", annotation_position="right")

    fig.update_layout(
        criar_layout(400),
        xaxis_title='% Clientes (do maior para menor)',
        yaxis_title='% Saldo Acumulado',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=40, b=40)
    )

    st.plotly_chart(fig, use_container_width=True)

    # Indice Gini
    area = sum(pct_valor_acum) / len(pct_valor_acum) / 100
    gini = (0.5 - area) / 0.5

    if gini > 0.7:
        gini_class = "Muito Alta"
        gini_cor = cores['perigo']
    elif gini > 0.5:
        gini_class = "Alta"
        gini_cor = cores['alerta']
    elif gini > 0.3:
        gini_class = "Moderada"
        gini_cor = '#fbbf24'
    else:
        gini_class = "Baixa"
        gini_cor = cores['sucesso']

    st.markdown(f"""
    <div style="background: {cores['card']}; border-radius: 8px; padding: 0.5rem 1rem;
                display: flex; justify-content: space-between; align-items: center;">
        <span style="color: {cores['texto_secundario']}; font-size: 0.8rem;">Indice de Gini</span>
        <span style="color: {gini_cor}; font-weight: 700;">{gini:.3f} - Concentracao {gini_class}</span>
    </div>
    """, unsafe_allow_html=True)


def _render_score_risco(df, col_cliente, cores):
    """Score de risco por cliente"""

    st.markdown("##### Score de Risco de Credito")

    total_saldo = df['SALDO'].sum()

    # Agregar por cliente
    df_cli = df.groupby(col_cliente).agg({
        'SALDO': 'sum',
        'DIAS_ATRASO': 'max',
        'VALOR_ORIGINAL': 'count'
    }).reset_index()
    df_cli.columns = [col_cliente, 'Saldo', 'Dias', 'Qtd']

    # Vencido por cliente
    df_venc = df[df['DIAS_ATRASO'] > 0].groupby(col_cliente)['SALDO'].sum().reset_index()
    df_venc.columns = [col_cliente, 'Vencido']
    df_cli = df_cli.merge(df_venc, on=col_cliente, how='left')
    df_cli['Vencido'] = df_cli['Vencido'].fillna(0)

    # Calcular score (0-100)
    # Componentes:
    # 1. Concentracao (25%): quanto maior % do saldo, maior risco
    # 2. Dias atraso (35%): quanto mais dias, maior risco
    # 3. % Vencido (25%): quanto maior % do saldo vencido, maior risco
    # 4. Valor absoluto vencido (15%): valores altos = maior risco

    df_cli['Pct_Saldo'] = df_cli['Saldo'] / total_saldo * 100
    df_cli['Pct_Vencido'] = (df_cli['Vencido'] / df_cli['Saldo'] * 100).fillna(0)

    max_pct = df_cli['Pct_Saldo'].max() if df_cli['Pct_Saldo'].max() > 0 else 1
    max_venc = df_cli['Vencido'].max() if df_cli['Vencido'].max() > 0 else 1

    df_cli['Score'] = (
        (df_cli['Pct_Saldo'] / max_pct * 25) +  # Concentracao
        (df_cli['Dias'].clip(0, 120) / 120 * 35) +  # Dias atraso
        (df_cli['Pct_Vencido'] / 100 * 25) +  # % Vencido
        (df_cli['Vencido'] / max_venc * 15)  # Valor absoluto
    ).clip(0, 100)

    # Top 15 por score
    df_top = df_cli.nlargest(15, 'Score')

    # Classificar
    def get_rating(score):
        if score >= 70:
            return 'Critico', cores['perigo']
        elif score >= 50:
            return 'Alto', cores['alerta']
        elif score >= 30:
            return 'Moderado', '#fbbf24'
        return 'Baixo', cores['sucesso']

    ratings = [get_rating(s) for s in df_top['Score']]
    df_top['Rating'] = [r[0] for r in ratings]
    colors = [r[1] for r in ratings]

    fig = go.Figure(go.Bar(
        y=df_top[col_cliente].str[:20],
        x=df_top['Score'],
        orientation='h',
        marker_color=colors,
        text=[f"{s:.0f} | {formatar_moeda(v)}" for s, v in zip(df_top['Score'], df_top['Vencido'])],
        textposition='outside',
        textfont=dict(size=8)
    ))

    fig.update_layout(
        criar_layout(380),
        yaxis={'autorange': 'reversed'},
        xaxis=dict(range=[0, 110], title='Score de Risco'),
        margin=dict(l=10, r=100, t=10, b=30)
    )

    st.plotly_chart(fig, use_container_width=True)

    # Legenda
    st.markdown(f"""
    <div style="display: flex; gap: 1rem; font-size: 0.7rem; color: {cores['texto_secundario']};">
        <span><span style="color: {cores['perigo']};">●</span> Critico (70+)</span>
        <span><span style="color: {cores['alerta']};">●</span> Alto (50-69)</span>
        <span><span style="color: #fbbf24;">●</span> Moderado (30-49)</span>
        <span><span style="color: {cores['sucesso']};">●</span> Baixo (0-29)</span>
    </div>
    """, unsafe_allow_html=True)


def _render_matriz_risco(df, col_cliente, cores):
    """Matriz de risco: Concentracao x Inadimplencia"""

    st.markdown("##### Matriz: Concentracao x Inadimplencia")

    total_saldo = df['SALDO'].sum()

    df_cli = df.groupby(col_cliente).agg({
        'SALDO': 'sum',
        'DIAS_ATRASO': 'max'
    }).reset_index()

    # Vencido
    df_venc = df[df['DIAS_ATRASO'] > 0].groupby(col_cliente)['SALDO'].sum().reset_index()
    df_venc.columns = [col_cliente, 'Vencido']
    df_cli = df_cli.merge(df_venc, on=col_cliente, how='left')
    df_cli['Vencido'] = df_cli['Vencido'].fillna(0)

    df_cli['Pct_Saldo'] = df_cli['SALDO'] / total_saldo * 100
    df_cli['Pct_Vencido'] = (df_cli['Vencido'] / df_cli['SALDO'] * 100).fillna(0)

    # Filtrar apenas com saldo relevante
    df_cli = df_cli[df_cli['SALDO'] > 0]

    if len(df_cli) == 0:
        st.info("Sem dados")
        return

    # Classificar quadrante
    def get_quadrante(row):
        alta_conc = row['Pct_Saldo'] > 5  # Mais de 5% do saldo
        alta_inad = row['Pct_Vencido'] > 30  # Mais de 30% vencido

        if alta_conc and alta_inad:
            return 'Critico', cores['perigo']
        elif alta_conc:
            return 'Monitorar', cores['alerta']
        elif alta_inad:
            return 'Atencao', '#fbbf24'
        return 'OK', cores['sucesso']

    quadrantes = [get_quadrante(row) for _, row in df_cli.iterrows()]
    df_cli['Quadrante'] = [q[0] for q in quadrantes]

    fig = go.Figure()

    for quad, cor in [('OK', cores['sucesso']), ('Atencao', '#fbbf24'),
                       ('Monitorar', cores['alerta']), ('Critico', cores['perigo'])]:
        df_q = df_cli[df_cli['Quadrante'] == quad]
        if len(df_q) > 0:
            fig.add_trace(go.Scatter(
                x=df_q['Pct_Saldo'],
                y=df_q['Pct_Vencido'],
                mode='markers',
                name=quad,
                marker=dict(
                    color=cor,
                    size=df_q['SALDO'] / df_cli['SALDO'].max() * 30 + 8,
                    opacity=0.7
                ),
                text=df_q[col_cliente],
                hovertemplate='<b>%{text}</b><br>Concentracao: %{x:.1f}%<br>% Vencido: %{y:.1f}%<extra></extra>'
            ))

    # Linhas de corte
    fig.add_hline(y=30, line_dash="dash", line_color=cores['texto_secundario'])
    fig.add_vline(x=5, line_dash="dash", line_color=cores['texto_secundario'])

    # Anotacoes dos quadrantes
    fig.add_annotation(x=2.5, y=15, text="OK", font=dict(size=12, color=cores['sucesso']), showarrow=False)
    fig.add_annotation(x=2.5, y=65, text="Atencao", font=dict(size=12, color='#fbbf24'), showarrow=False)
    fig.add_annotation(x=15, y=15, text="Monitorar", font=dict(size=12, color=cores['alerta']), showarrow=False)
    fig.add_annotation(x=15, y=65, text="CRITICO", font=dict(size=14, color=cores['perigo']), showarrow=False)

    fig.update_layout(
        criar_layout(380),
        xaxis_title='% do Saldo Total (Concentracao)',
        yaxis_title='% Vencido (Inadimplencia)',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=40, b=40)
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_aging_top_devedores(df, col_cliente, cores):
    """Aging dos maiores devedores"""

    st.markdown("##### Aging - Top 10 Devedores")

    total_saldo = df['SALDO'].sum()
    df_pendentes = df[df['SALDO'] > 0].copy()

    if len(df_pendentes) == 0:
        st.info("Sem titulos pendentes")
        return

    # Top 10 clientes
    top_clientes = df_pendentes.groupby(col_cliente)['SALDO'].sum().nlargest(10).index.tolist()
    df_top = df_pendentes[df_pendentes[col_cliente].isin(top_clientes)]

    # Faixas de aging
    df_top['FAIXA'] = pd.cut(
        df_top['DIAS_ATRASO'],
        bins=[-float('inf'), 0, 30, 60, 90, float('inf')],
        labels=['A Vencer', '1-30d', '31-60d', '61-90d', '+90d']
    )

    # Pivot
    df_pivot = df_top.groupby([col_cliente, 'FAIXA'])['SALDO'].sum().unstack(fill_value=0)
    df_pivot['TOTAL'] = df_pivot.sum(axis=1)
    df_pivot = df_pivot.sort_values('TOTAL', ascending=True)
    df_pivot = df_pivot.drop(columns=['TOTAL'])

    fig = go.Figure()

    cores_faixas = {
        'A Vencer': cores['sucesso'],
        '1-30d': '#fbbf24',
        '31-60d': cores['alerta'],
        '61-90d': '#f97316',
        '+90d': cores['perigo']
    }

    for faixa in ['A Vencer', '1-30d', '31-60d', '61-90d', '+90d']:
        if faixa in df_pivot.columns:
            fig.add_trace(go.Bar(
                y=df_pivot.index.str[:18],
                x=df_pivot[faixa],
                orientation='h',
                name=faixa,
                marker_color=cores_faixas.get(faixa, cores['info'])
            ))

    fig.update_layout(
        criar_layout(320, barmode='stack'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=8)),
        margin=dict(l=10, r=10, t=40, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_simulacao_impacto(df, col_cliente, cores):
    """Simulacao de impacto se cliente nao pagar"""

    st.markdown("##### Simulacao de Impacto")

    total_saldo = df['SALDO'].sum()

    # Top 10 clientes para simular
    df_cli = df.groupby(col_cliente)['SALDO'].sum().nlargest(10).reset_index()
    df_cli['Pct'] = df_cli['SALDO'] / total_saldo * 100

    clientes_opcoes = [f"{row[col_cliente][:25]} ({row['Pct']:.1f}%)" for _, row in df_cli.iterrows()]

    cliente_sel = st.selectbox(
        "Simular inadimplencia de:",
        options=["Selecione um cliente..."] + clientes_opcoes,
        key="sim_cliente"
    )

    if cliente_sel and cliente_sel != "Selecione um cliente...":
        # Extrair nome do cliente
        nome_cliente = cliente_sel.split(" (")[0]

        # Buscar dados do cliente
        saldo_cliente = df_cli[df_cli[col_cliente].str[:25] == nome_cliente]['SALDO'].values
        if len(saldo_cliente) > 0:
            saldo_cliente = saldo_cliente[0]
        else:
            saldo_cliente = df[df[col_cliente].str.startswith(nome_cliente)]['SALDO'].sum()

        pct_cliente = saldo_cliente / total_saldo * 100

        # Calcular impactos
        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"""
            <div style="background: {cores['card']}; border: 1px solid {cores['perigo']};
                        border-radius: 8px; padding: 1rem; text-align: center;">
                <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">VALOR EM RISCO</p>
                <p style="color: {cores['perigo']}; font-size: 1.5rem; font-weight: 800; margin: 0.25rem 0;">
                    {formatar_moeda(saldo_cliente)}</p>
                <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0;">
                    {pct_cliente:.1f}% da carteira</p>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            # Novo saldo sem o cliente
            novo_saldo = total_saldo - saldo_cliente

            # Recalcular concentracao sem o cliente
            df_sem_cli = df[~df[col_cliente].str.startswith(nome_cliente)]
            df_cli_sem = df_sem_cli.groupby(col_cliente)['SALDO'].sum().sort_values(ascending=False)
            novo_top5 = df_cli_sem.head(5).sum() / novo_saldo * 100 if novo_saldo > 0 and len(df_cli_sem) >= 5 else 0

            st.markdown(f"""
            <div style="background: {cores['card']}; border: 1px solid {cores['alerta']};
                        border-radius: 8px; padding: 1rem; text-align: center;">
                <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">IMPACTO NA CARTEIRA</p>
                <p style="color: {cores['alerta']}; font-size: 1.5rem; font-weight: 800; margin: 0.25rem 0;">
                    -{pct_cliente:.1f}%</p>
                <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0;">
                    Nova conc. Top 5: {novo_top5:.1f}%</p>
            </div>
            """, unsafe_allow_html=True)

        # Alerta de dependencia
        if pct_cliente > 10:
            st.error(f"ALTA DEPENDENCIA: {nome_cliente} representa {pct_cliente:.1f}% da carteira!")
        elif pct_cliente > 5:
            st.warning(f"Atencao: {nome_cliente} representa {pct_cliente:.1f}% da carteira.")


def _render_historico_cliente(df, col_cliente, cores):
    """Historico detalhado de um cliente"""

    st.markdown("##### Historico do Cliente")

    # Lista de clientes ordenados por saldo
    df_cli = df.groupby(col_cliente)['SALDO'].sum().nlargest(50).reset_index()
    clientes = df_cli[col_cliente].tolist()

    col1, col2 = st.columns([3, 1])

    with col1:
        cliente_sel = st.selectbox(
            "Selecione um cliente para ver historico:",
            options=[""] + clientes,
            key="hist_cliente",
            format_func=lambda x: x[:40] if x else "Selecione..."
        )

    if not cliente_sel:
        return

    df_cliente = df[df[col_cliente] == cliente_sel].copy()

    if len(df_cliente) == 0:
        st.info("Sem dados para este cliente")
        return

    # Metricas do cliente
    total_valor = df_cliente['VALOR_ORIGINAL'].sum()
    total_saldo = df_cliente['SALDO'].sum()
    total_recebido = total_valor - total_saldo
    pct_recebido = total_recebido / total_valor * 100 if total_valor > 0 else 0

    df_vencido = df_cliente[df_cliente['DIAS_ATRASO'] > 0]
    total_vencido = df_vencido['SALDO'].sum()
    dias_max = df_cliente['DIAS_ATRASO'].max()

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Valor Total", formatar_moeda(total_valor), f"{len(df_cliente)} titulos")
    col2.metric("Recebido", formatar_moeda(total_recebido), f"{pct_recebido:.0f}%")
    col3.metric("Saldo Pendente", formatar_moeda(total_saldo))
    col4.metric("Vencido", formatar_moeda(total_vencido), delta_color="inverse" if total_vencido > 0 else "off")
    col5.metric("Maior Atraso", f"{int(dias_max)} dias" if dias_max > 0 else "Em dia")

    # Grafico de evolucao mensal
    if 'EMISSAO' in df_cliente.columns:
        df_cliente['MES'] = df_cliente['EMISSAO'].dt.to_period('M').astype(str)

        df_mes = df_cliente.groupby('MES').agg({
            'VALOR_ORIGINAL': 'sum',
            'SALDO': 'sum'
        }).reset_index()
        df_mes['Recebido'] = df_mes['VALOR_ORIGINAL'] - df_mes['SALDO']

        if len(df_mes) > 1:
            col1, col2 = st.columns(2)

            with col1:
                fig = go.Figure()

                fig.add_trace(go.Bar(
                    x=df_mes['MES'],
                    y=df_mes['Recebido'],
                    name='Recebido',
                    marker_color=cores['sucesso']
                ))

                fig.add_trace(go.Bar(
                    x=df_mes['MES'],
                    y=df_mes['SALDO'],
                    name='Pendente',
                    marker_color=cores['alerta']
                ))

                fig.update_layout(
                    criar_layout(200, barmode='stack'),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=8)),
                    margin=dict(l=10, r=10, t=30, b=50),
                    xaxis_tickangle=-45
                )

                st.plotly_chart(fig, use_container_width=True)

            with col2:
                # Aging do cliente
                df_pend = df_cliente[df_cliente['SALDO'] > 0]
                if len(df_pend) > 0:
                    df_pend['FAIXA'] = pd.cut(
                        df_pend['DIAS_ATRASO'],
                        bins=[-float('inf'), 0, 30, 60, 90, float('inf')],
                        labels=['A Vencer', '1-30d', '31-60d', '61-90d', '+90d']
                    )

                    df_aging = df_pend.groupby('FAIXA')['SALDO'].sum().reset_index()

                    cores_faixas = {
                        'A Vencer': cores['sucesso'],
                        '1-30d': '#fbbf24',
                        '31-60d': cores['alerta'],
                        '61-90d': '#f97316',
                        '+90d': cores['perigo']
                    }

                    fig = go.Figure(go.Bar(
                        x=df_aging['FAIXA'],
                        y=df_aging['SALDO'],
                        marker_color=[cores_faixas.get(f, cores['info']) for f in df_aging['FAIXA']],
                        text=[formatar_moeda(v) for v in df_aging['SALDO']],
                        textposition='outside',
                        textfont=dict(size=9)
                    ))

                    fig.update_layout(
                        criar_layout(200),
                        margin=dict(l=10, r=10, t=10, b=10)
                    )

                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.success("Cliente sem pendencias!")


def _render_clientes_alerta(df, col_cliente, cores):
    """Clientes em alerta - watchlist"""

    st.markdown("##### Clientes em Alerta")

    total_saldo = df['SALDO'].sum()

    df_cli = df.groupby(col_cliente).agg({
        'SALDO': 'sum',
        'DIAS_ATRASO': 'max',
        'VALOR_ORIGINAL': 'count'
    }).reset_index()
    df_cli.columns = [col_cliente, 'Saldo', 'Dias', 'Titulos']

    # Vencido
    df_venc = df[df['DIAS_ATRASO'] > 0].groupby(col_cliente)['SALDO'].sum().reset_index()
    df_venc.columns = [col_cliente, 'Vencido']
    df_cli = df_cli.merge(df_venc, on=col_cliente, how='left')
    df_cli['Vencido'] = df_cli['Vencido'].fillna(0)

    df_cli['Pct_Saldo'] = df_cli['Saldo'] / total_saldo * 100

    # Criterios de alerta
    alertas = []

    # 1. Alto valor vencido (+R$ 100k)
    df_alto_valor = df_cli[df_cli['Vencido'] > 100000].nlargest(5, 'Vencido')
    for _, row in df_alto_valor.iterrows():
        alertas.append({
            'Cliente': row[col_cliente],
            'Tipo': 'ALTO VALOR',
            'Cor': cores['perigo'],
            'Valor': row['Vencido'],
            'Detalhe': f"{formatar_moeda(row['Vencido'])} vencido"
        })

    # 2. Atraso longo (+90 dias)
    df_longo = df_cli[(df_cli['Dias'] > 90) & (~df_cli[col_cliente].isin(df_alto_valor[col_cliente]))].nlargest(5, 'Dias')
    for _, row in df_longo.iterrows():
        alertas.append({
            'Cliente': row[col_cliente],
            'Tipo': 'ATRASO LONGO',
            'Cor': '#f97316',
            'Valor': row['Vencido'],
            'Detalhe': f"{int(row['Dias'])} dias de atraso"
        })

    # 3. Alta concentracao com vencido (+5% do saldo e tem vencido)
    df_conc = df_cli[(df_cli['Pct_Saldo'] > 5) & (df_cli['Vencido'] > 0)]
    df_conc = df_conc[~df_conc[col_cliente].isin([a['Cliente'] for a in alertas])].nlargest(5, 'Pct_Saldo')
    for _, row in df_conc.iterrows():
        alertas.append({
            'Cliente': row[col_cliente],
            'Tipo': 'CONCENTRACAO',
            'Cor': cores['alerta'],
            'Valor': row['Vencido'],
            'Detalhe': f"{row['Pct_Saldo']:.1f}% do saldo + {formatar_moeda(row['Vencido'])} vencido"
        })

    if len(alertas) == 0:
        st.success("Nenhum cliente em alerta no momento!")
        return

    # Exibir em 3 colunas
    cols = st.columns(3)

    for i, alerta in enumerate(alertas[:9]):
        with cols[i % 3]:
            st.markdown(f"""
            <div style="background: {cores['card']}; border-left: 4px solid {alerta['Cor']};
                        padding: 0.6rem 0.8rem; border-radius: 0 8px 8px 0; margin-bottom: 0.5rem;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="color: {alerta['Cor']}; font-size: 0.65rem; font-weight: 700;">{alerta['Tipo']}</span>
                    <span style="color: {cores['perigo']}; font-size: 0.8rem; font-weight: 700;">{formatar_moeda(alerta['Valor'])}</span>
                </div>
                <p style="color: {cores['texto']}; font-size: 0.8rem; font-weight: 600; margin: 0.2rem 0;">{alerta['Cliente'][:25]}</p>
                <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">{alerta['Detalhe']}</p>
            </div>
            """, unsafe_allow_html=True)

    # Resumo
    total_alerta = sum(a['Valor'] for a in alertas)
    st.error(f"**{len(alertas)} clientes em alerta** | Valor em risco: {formatar_moeda(total_alerta)}")


def _render_ranking_risco(df, col_cliente, cores):
    """Ranking completo com filtros de risco"""

    st.markdown("##### Ranking de Risco")

    col1, col2, col3 = st.columns(3)

    with col1:
        ordenar = st.selectbox("Ordenar por", ['Score de Risco', 'Maior Saldo', 'Maior Vencido', 'Maior Atraso'], key="rr_ord")
    with col2:
        filtro_risco = st.selectbox("Filtrar por Risco", ['Todos', 'Critico', 'Alto', 'Moderado', 'Baixo'], key="rr_risco")
    with col3:
        qtd = st.selectbox("Exibir", [25, 50, 100], key="rr_qtd")

    total_saldo = df['SALDO'].sum()

    # Agregar
    df_cli = df.groupby(col_cliente).agg({
        'SALDO': 'sum',
        'DIAS_ATRASO': 'max',
        'VALOR_ORIGINAL': 'count'
    }).reset_index()
    df_cli.columns = [col_cliente, 'Saldo', 'Dias', 'Titulos']

    # Vencido
    df_venc = df[df['DIAS_ATRASO'] > 0].groupby(col_cliente)['SALDO'].sum().reset_index()
    df_venc.columns = [col_cliente, 'Vencido']
    df_cli = df_cli.merge(df_venc, on=col_cliente, how='left')
    df_cli['Vencido'] = df_cli['Vencido'].fillna(0)

    # Calcular score
    df_cli['Pct_Saldo'] = df_cli['Saldo'] / total_saldo * 100
    df_cli['Pct_Vencido'] = (df_cli['Vencido'] / df_cli['Saldo'] * 100).fillna(0)

    max_pct = df_cli['Pct_Saldo'].max() if df_cli['Pct_Saldo'].max() > 0 else 1
    max_venc = df_cli['Vencido'].max() if df_cli['Vencido'].max() > 0 else 1

    df_cli['Score'] = (
        (df_cli['Pct_Saldo'] / max_pct * 25) +
        (df_cli['Dias'].clip(0, 120) / 120 * 35) +
        (df_cli['Pct_Vencido'] / 100 * 25) +
        (df_cli['Vencido'] / max_venc * 15)
    ).clip(0, 100)

    # Classificar
    def get_risco(score):
        if score >= 70:
            return 'Critico'
        elif score >= 50:
            return 'Alto'
        elif score >= 30:
            return 'Moderado'
        return 'Baixo'

    df_cli['Risco'] = df_cli['Score'].apply(get_risco)

    # Filtrar
    if filtro_risco != 'Todos':
        df_cli = df_cli[df_cli['Risco'] == filtro_risco]

    # Ordenar
    if ordenar == 'Score de Risco':
        df_cli = df_cli.nlargest(qtd, 'Score')
    elif ordenar == 'Maior Saldo':
        df_cli = df_cli.nlargest(qtd, 'Saldo')
    elif ordenar == 'Maior Vencido':
        df_cli = df_cli.nlargest(qtd, 'Vencido')
    else:
        df_cli = df_cli.nlargest(qtd, 'Dias')

    # Formatar
    df_show = df_cli[[col_cliente, 'Saldo', 'Vencido', 'Dias', 'Pct_Saldo', 'Score', 'Risco']].copy()
    df_show['Saldo'] = df_show['Saldo'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Vencido'] = df_show['Vencido'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['Pct_Saldo'] = df_show['Pct_Saldo'].apply(lambda x: f"{x:.2f}%")
    df_show['Score'] = df_show['Score'].apply(lambda x: f"{x:.0f}")
    df_show.columns = ['Cliente', 'Saldo', 'Vencido', 'Dias Atraso', '% Carteira', 'Score', 'Risco']

    st.dataframe(df_show, use_container_width=True, hide_index=True, height=400)

    # Resumo
    total_exibido = df_cli['Saldo'].sum() if 'Saldo' in df_cli.columns else 0
    st.caption(f"Exibindo {len(df_show)} clientes | Saldo total: {formatar_moeda(df.groupby(col_cliente)['SALDO'].sum().sum())}")
