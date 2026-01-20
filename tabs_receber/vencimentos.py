"""
Aba Vencimentos - Visao de Gestao - Contas a Receber
Analise de vencimentos por faixas, filiais, categorias e clientes
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

from config.theme import get_cores
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero


def get_df_pendentes(df):
    """Retorna titulos com saldo pendente (a vencer)"""
    df_pend = df[(df['SALDO'] > 0) & (df['STATUS'] != 'Vencido')]
    return df_pend


def get_df_vencidos(df):
    """Retorna titulos vencidos"""
    return df[df['STATUS'] == 'Vencido']


def render_vencimentos_receber(df):
    """Renderiza a aba de Vencimentos - Visao de Gestao"""
    cores = get_cores()
    hoje = datetime.now()

    if len(df) == 0:
        st.warning("Nenhum dado disponivel.")
        return

    # Calcular dataframes
    df_pendentes = get_df_pendentes(df)
    df_vencidos = get_df_vencidos(df)

    # ========== RESUMO GERAL ==========
    _render_resumo_geral(df_pendentes, df_vencidos, cores, hoje)

    st.divider()

    # ========== AGING COMPLETO ==========
    _render_aging_completo(df_pendentes, df_vencidos, cores, hoje)

    st.divider()

    # ========== POR FILIAL + POR CATEGORIA ==========
    col1, col2 = st.columns(2)

    with col1:
        _render_por_filial(df_pendentes, df_vencidos, cores)

    with col2:
        _render_por_categoria(df_pendentes, df_vencidos, cores)

    st.divider()

    # ========== TOP CLIENTES ==========
    _render_top_clientes(df_pendentes, df_vencidos, cores)

    st.divider()

    # ========== EVOLUCAO MENSAL ==========
    _render_evolucao_mensal(df_pendentes, cores, hoje)

    st.divider()

    # ========== DETALHAMENTO ==========
    _render_detalhamento(df_pendentes, df_vencidos, cores, hoje)


def _padronizar_nome_filial(nome):
    """Padroniza nome da filial para exibicao"""
    if not nome:
        return nome

    nome = str(nome).strip()

    # Padronizar Progresso Agroindustrial por estado
    if 'PROGRESSO AGROINDUST' in nome.upper():
        if ' - BA' in nome or '(BA)' in nome:
            return 'Progresso BA'
        elif ' - DF' in nome or '(DF)' in nome:
            return 'Progresso DF'
        elif ' - GO' in nome or '(GO)' in nome or 'ST HELENA' in nome.upper():
            return 'Progresso GO'
        elif ' - MA' in nome or '(MA)' in nome or 'BALSAS' in nome.upper():
            return 'Progresso MA'
        elif ' - MG' in nome or '(MG)' in nome:
            return 'Progresso MG'
        elif ' - MT' in nome or '(MT)' in nome or '(PL)' in nome or '(LV)' in nome:
            return 'Progresso MT'
        elif ' - PA' in nome or '(PA)' in nome or 'TAILANDIA' in nome.upper():
            return 'Progresso PA'
        elif ' - PI' in nome or '(PI)' in nome:
            return 'Progresso PI'
        elif ' - RO' in nome or '(RO)' in nome:
            return 'Progresso RO'
        elif ' - TO' in nome or '(TO)' in nome:
            return 'Progresso TO'
        else:
            return 'Progresso Agro'

    # Outras padronizacoes
    padronizacao = {
        'PROGRESSO MATRIZ': 'Progresso Matriz',
        'PROGRESSO FBO': 'Ouro Branco',
        'FAZENDA OURO BRANCO': 'Ouro Branco',
        'BRASIL AGRICOLA LTDA': 'Brasil Agricola',
        'BRASIL AGRICOLA': 'Brasil Agricola',
        'RAINHA DA SERRA': 'Rainha da Serra',
        'SDS PARTICIPACOES': 'SDS Participacoes',
        'TROPICAL AGROPARTICIPACOES': 'Tropical',
        'TROPICAL': 'Tropical',
        'AG3 AGRO': 'AG3 Agro',
        'CG3 AGRO': 'CG3 Agro',
        'IMPERIAL': 'Imperial',
        'PENINSULA': 'Peninsula',
    }

    nome_upper = nome.upper()
    for padrao, novo_nome in padronizacao.items():
        if padrao in nome_upper:
            return novo_nome

    return nome


def _render_resumo_geral(df_pendentes, df_vencidos, cores, hoje):
    """Resumo geral dos recebimentos"""

    hoje_date = hoje.date()

    # Calculos
    total_pendente = df_pendentes['SALDO'].sum() + df_vencidos['SALDO'].sum()
    qtd_pendente = len(df_pendentes) + len(df_vencidos)

    total_vencido = df_vencidos['SALDO'].sum()
    qtd_vencidos = len(df_vencidos)

    # Proximos 30 dias
    data_30d = hoje_date + timedelta(days=30)
    df_30d = df_pendentes[df_pendentes['VENCIMENTO'].dt.date <= data_30d]
    valor_30d = df_30d['SALDO'].sum()
    qtd_30d = len(df_30d)

    # Proximos 60 dias
    data_60d = hoje_date + timedelta(days=60)
    df_60d = df_pendentes[
        (df_pendentes['VENCIMENTO'].dt.date > data_30d) &
        (df_pendentes['VENCIMENTO'].dt.date <= data_60d)
    ]
    valor_60d = df_60d['SALDO'].sum()
    qtd_60d = len(df_60d)

    # Percentual vencido
    pct_vencido = (total_vencido / total_pendente * 100) if total_pendente > 0 else 0

    # Cards
    st.markdown(f"""
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1rem;">
        <div style="background: {cores['card']}; border: 1px solid {cores['borda']};
                    border-radius: 12px; padding: 1.25rem;">
            <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0;">TOTAL A RECEBER</p>
            <p style="color: {cores['sucesso']}; font-size: 1.5rem; font-weight: 700; margin: 0.25rem 0;">
                {formatar_moeda(total_pendente)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">{qtd_pendente} titulos</p>
        </div>
        <div style="background: {cores['perigo']}15; border: 1px solid {cores['perigo']}50;
                    border-radius: 12px; padding: 1.25rem;">
            <p style="color: {cores['perigo']}; font-size: 0.75rem; margin: 0;">VENCIDO</p>
            <p style="color: {cores['perigo']}; font-size: 1.5rem; font-weight: 700; margin: 0.25rem 0;">
                {formatar_moeda(total_vencido)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">
                {qtd_vencidos} titulos | {pct_vencido:.1f}% do total</p>
        </div>
        <div style="background: {cores['alerta']}15; border: 1px solid {cores['alerta']}50;
                    border-radius: 12px; padding: 1.25rem;">
            <p style="color: {cores['alerta']}; font-size: 0.75rem; margin: 0;">RECEBER EM 30 DIAS</p>
            <p style="color: {cores['alerta']}; font-size: 1.5rem; font-weight: 700; margin: 0.25rem 0;">
                {formatar_moeda(valor_30d)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">{qtd_30d} titulos</p>
        </div>
        <div style="background: {cores['info']}15; border: 1px solid {cores['info']}50;
                    border-radius: 12px; padding: 1.25rem;">
            <p style="color: {cores['info']}; font-size: 0.75rem; margin: 0;">RECEBER 31-60 DIAS</p>
            <p style="color: {cores['info']}; font-size: 1.5rem; font-weight: 700; margin: 0.25rem 0;">
                {formatar_moeda(valor_60d)}</p>
            <p style="color: {cores['texto_secundario']}; font-size: 0.7rem; margin: 0;">{qtd_60d} titulos</p>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _render_aging_completo(df_pendentes, df_vencidos, cores, hoje):
    """Aging completo - vencidos e a vencer"""

    st.markdown("##### Aging - Distribuicao por Faixa de Vencimento")

    hoje_date = hoje.date()

    # Combinar todos os dados
    df_all = pd.concat([df_pendentes, df_vencidos]).drop_duplicates()

    if len(df_all) == 0:
        st.info("Sem dados")
        return

    def faixa_vencimento(row):
        if pd.isna(row.get('VENCIMENTO')):
            return '9_Sem data'

        venc = row['VENCIMENTO'].date() if hasattr(row['VENCIMENTO'], 'date') else row['VENCIMENTO']
        diff = (venc - hoje_date).days

        if diff < -60:
            return '1_Venc +60 dias'
        elif diff < -30:
            return '2_Venc 31-60 dias'
        elif diff < -15:
            return '3_Venc 16-30 dias'
        elif diff < -7:
            return '4_Venc 8-15 dias'
        elif diff < 0:
            return '5_Venc 1-7 dias'
        elif diff <= 7:
            return '6_Vence em 7 dias'
        elif diff <= 30:
            return '7_Vence em 8-30 dias'
        elif diff <= 60:
            return '8_Vence em 31-60 dias'
        else:
            return '9_Vence em +60 dias'

    df_all['FAIXA'] = df_all.apply(faixa_vencimento, axis=1)

    df_grp = df_all.groupby('FAIXA').agg({
        'SALDO': 'sum',
        'NUMERO': 'count'
    }).sort_index().reset_index()
    df_grp.columns = ['Faixa', 'Valor', 'Qtd']

    # Labels mais limpos
    labels = {
        '1_Venc +60 dias': '+60 dias vencido',
        '2_Venc 31-60 dias': '31-60 dias vencido',
        '3_Venc 16-30 dias': '16-30 dias vencido',
        '4_Venc 8-15 dias': '8-15 dias vencido',
        '5_Venc 1-7 dias': '1-7 dias vencido',
        '6_Vence em 7 dias': 'Receber em 7 dias',
        '7_Vence em 8-30 dias': 'Receber em 8-30 dias',
        '8_Vence em 31-60 dias': 'Receber em 31-60 dias',
        '9_Vence em +60 dias': 'Receber em +60 dias',
        '9_Sem data': 'Sem data'
    }
    df_grp['Label'] = df_grp['Faixa'].map(labels)

    # Cores por faixa (vermelho para vencido, verde para a receber)
    cores_faixas = {
        '1_Venc +60 dias': '#7f1d1d',
        '2_Venc 31-60 dias': '#dc2626',
        '3_Venc 16-30 dias': '#ef4444',
        '4_Venc 8-15 dias': '#f97316',
        '5_Venc 1-7 dias': '#fbbf24',
        '6_Vence em 7 dias': '#84cc16',
        '7_Vence em 8-30 dias': '#22c55e',
        '8_Vence em 31-60 dias': '#3b82f6',
        '9_Vence em +60 dias': '#6366f1',
        '9_Sem data': '#64748b'
    }
    df_grp['Cor'] = df_grp['Faixa'].map(cores_faixas)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=df_grp['Label'],
        x=df_grp['Valor'],
        orientation='h',
        marker_color=df_grp['Cor'],
        text=[f"{formatar_moeda(v)} ({int(q)})" for v, q in zip(df_grp['Valor'], df_grp['Qtd'])],
        textposition='outside',
        textfont=dict(size=10, color=cores['texto'])
    ))

    fig.update_layout(
        criar_layout(350),
        margin=dict(l=10, r=120, t=10, b=10),
        xaxis=dict(showticklabels=False, showgrid=False),
        yaxis=dict(tickfont=dict(size=11, color=cores['texto']), autorange='reversed')
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_por_filial(df_pendentes, df_vencidos, cores):
    """Saldo a receber por filial"""

    st.markdown("##### Por Filial")

    df_all = pd.concat([df_pendentes, df_vencidos]).drop_duplicates()

    if len(df_all) == 0:
        st.info("Sem dados")
        return

    # Padronizar nomes
    df_all['FILIAL_PADRAO'] = df_all['NOME_FILIAL'].apply(_padronizar_nome_filial)

    # Agrupar
    df_filial = df_all.groupby('FILIAL_PADRAO').agg({
        'SALDO': 'sum',
        'NUMERO': 'count'
    }).reset_index()
    df_filial.columns = ['Filial', 'Valor', 'Qtd']

    # Calcular vencido por filial
    if len(df_vencidos) > 0:
        df_vencidos_temp = df_vencidos.copy()
        df_vencidos_temp['FILIAL_PADRAO'] = df_vencidos_temp['NOME_FILIAL'].apply(_padronizar_nome_filial)
        df_venc_fil = df_vencidos_temp.groupby('FILIAL_PADRAO')['SALDO'].sum().reset_index()
        df_venc_fil.columns = ['Filial', 'Vencido']
        df_filial = df_filial.merge(df_venc_fil, on='Filial', how='left')
    else:
        df_filial['Vencido'] = 0

    df_filial['Vencido'] = df_filial['Vencido'].fillna(0)
    df_filial['A_Receber'] = df_filial['Valor'] - df_filial['Vencido']

    df_filial = df_filial.sort_values('Valor', ascending=True)

    # Top 12
    if len(df_filial) > 12:
        df_filial = df_filial.tail(12)

    fig = go.Figure()

    # Barra de vencido
    fig.add_trace(go.Bar(
        y=df_filial['Filial'].astype(str).str[:25],
        x=df_filial['Vencido'],
        orientation='h',
        name='Vencido',
        marker_color=cores['perigo'],
        text=[formatar_moeda(v) if v > 0 else '' for v in df_filial['Vencido']],
        textposition='inside',
        textfont=dict(size=8, color='white')
    ))

    # Barra de a receber
    fig.add_trace(go.Bar(
        y=df_filial['Filial'].astype(str).str[:25],
        x=df_filial['A_Receber'],
        orientation='h',
        name='A Receber',
        marker_color=cores['sucesso'],
        text=[formatar_moeda(v) if v > 0 else '' for v in df_filial['A_Receber']],
        textposition='inside',
        textfont=dict(size=8, color='white')
    ))

    fig.update_layout(
        criar_layout(320),
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


def _render_por_categoria(df_pendentes, df_vencidos, cores):
    """Saldo a receber por categoria (DESCRICAO) - Vencido vs A Receber"""

    st.markdown("##### Por Categoria")

    df_all = pd.concat([df_pendentes, df_vencidos]).drop_duplicates()

    if len(df_all) == 0 or 'DESCRICAO' not in df_all.columns:
        st.info("Sem dados de categoria")
        return

    # Agrupar total por categoria
    df_cat = df_all.groupby('DESCRICAO').agg({
        'SALDO': 'sum',
        'NUMERO': 'count'
    }).reset_index()
    df_cat.columns = ['Categoria', 'Valor', 'Qtd']

    # Calcular vencido por categoria
    if len(df_vencidos) > 0 and 'DESCRICAO' in df_vencidos.columns:
        df_venc_cat = df_vencidos.groupby('DESCRICAO')['SALDO'].sum().reset_index()
        df_venc_cat.columns = ['Categoria', 'Vencido']
        df_cat = df_cat.merge(df_venc_cat, on='Categoria', how='left')
    else:
        df_cat['Vencido'] = 0

    df_cat['Vencido'] = df_cat['Vencido'].fillna(0)
    df_cat['A_Receber'] = df_cat['Valor'] - df_cat['Vencido']

    df_cat = df_cat.sort_values('Valor', ascending=True)

    # Top 12
    if len(df_cat) > 12:
        df_cat = df_cat.tail(12)

    fig = go.Figure()

    # Barra de vencido
    fig.add_trace(go.Bar(
        y=df_cat['Categoria'].astype(str).str[:28],
        x=df_cat['Vencido'],
        orientation='h',
        name='Vencido',
        marker_color=cores['perigo'],
        text=[formatar_moeda(v) if v > 0 else '' for v in df_cat['Vencido']],
        textposition='inside',
        textfont=dict(size=8, color='white')
    ))

    # Barra de a receber
    fig.add_trace(go.Bar(
        y=df_cat['Categoria'].astype(str).str[:28],
        x=df_cat['A_Receber'],
        orientation='h',
        name='A Receber',
        marker_color=cores['sucesso'],
        text=[formatar_moeda(v) if v > 0 else '' for v in df_cat['A_Receber']],
        textposition='inside',
        textfont=dict(size=8, color='white')
    ))

    fig.update_layout(
        criar_layout(320),
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


def _render_top_clientes(df_pendentes, df_vencidos, cores):
    """Top clientes com maior saldo a receber"""

    st.markdown("##### Top 15 Clientes - Maior Saldo a Receber")

    df_all = pd.concat([df_pendentes, df_vencidos]).drop_duplicates()

    if len(df_all) == 0:
        st.info("Sem dados")
        return

    # Agrupar e calcular vencido por cliente
    df_cli = df_all.groupby('NOME_CLIENTE').agg({
        'SALDO': 'sum',
        'NUMERO': 'count'
    }).reset_index()
    df_cli.columns = ['Cliente', 'Valor', 'Qtd']

    # Calcular quanto esta vencido por cliente
    if len(df_vencidos) > 0:
        df_venc_cli = df_vencidos.groupby('NOME_CLIENTE')['SALDO'].sum().reset_index()
        df_venc_cli.columns = ['Cliente', 'Vencido']
        df_cli = df_cli.merge(df_venc_cli, on='Cliente', how='left')
    else:
        df_cli['Vencido'] = 0

    df_cli['Vencido'] = df_cli['Vencido'].fillna(0)
    df_cli['A_Receber'] = df_cli['Valor'] - df_cli['Vencido']

    df_cli = df_cli.sort_values('Valor', ascending=True).tail(15)

    fig = go.Figure()

    # Barra de vencido
    fig.add_trace(go.Bar(
        y=df_cli['Cliente'].astype(str).str[:35],
        x=df_cli['Vencido'],
        orientation='h',
        name='Vencido',
        marker_color=cores['perigo'],
        text=[formatar_moeda(v) if v > 0 else '' for v in df_cli['Vencido']],
        textposition='inside',
        textfont=dict(size=8, color='white')
    ))

    # Barra de a receber
    fig.add_trace(go.Bar(
        y=df_cli['Cliente'].astype(str).str[:35],
        x=df_cli['A_Receber'],
        orientation='h',
        name='A Receber',
        marker_color=cores['sucesso'],
        text=[formatar_moeda(v) if v > 0 else '' for v in df_cli['A_Receber']],
        textposition='inside',
        textfont=dict(size=8, color='white')
    ))

    fig.update_layout(
        criar_layout(400),
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


def _render_evolucao_mensal(df_pendentes, cores, hoje):
    """Evolucao mensal dos recebimentos previstos"""

    st.markdown("##### Previsao de Recebimentos por Mes")

    if len(df_pendentes) == 0:
        st.info("Sem dados")
        return

    # Agrupar por mes
    df_mes = df_pendentes.copy()
    df_mes['MES'] = df_mes['VENCIMENTO'].dt.to_period('M')

    df_grp = df_mes.groupby('MES').agg({
        'SALDO': 'sum',
        'NUMERO': 'count'
    }).reset_index()
    df_grp.columns = ['Mes', 'Valor', 'Qtd']

    # Converter periodo para string
    df_grp['Label'] = df_grp['Mes'].astype(str)
    df_grp['MesDate'] = df_grp['Mes'].dt.to_timestamp()

    # Limitar a 12 meses
    df_grp = df_grp.sort_values('MesDate').tail(12)

    # Cores: mes atual diferente
    mes_atual = hoje.strftime('%Y-%m')
    cores_barras = [cores['alerta'] if m == mes_atual else cores['sucesso'] for m in df_grp['Label']]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df_grp['Label'],
        y=df_grp['Valor'],
        marker_color=cores_barras,
        text=[formatar_moeda(v) for v in df_grp['Valor']],
        textposition='outside',
        textfont=dict(size=9, color=cores['texto'])
    ))

    fig.update_layout(
        criar_layout(280),
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(tickfont=dict(size=10, color=cores['texto']), tickangle=-45),
        yaxis=dict(showticklabels=False, showgrid=False)
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_detalhamento(df_pendentes, df_vencidos, cores, hoje):
    """Detalhamento com filtros"""

    st.markdown("##### Detalhamento")

    # Filtros
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        status = st.selectbox(
            "Status",
            ["Todos", "Vencidos", "A Receber"],
            key="venc_rec_status"
        )

    with col2:
        # Combinar dados para pegar filiais
        df_all = pd.concat([df_pendentes, df_vencidos]).drop_duplicates()
        df_all['FILIAL_PADRAO'] = df_all['NOME_FILIAL'].apply(_padronizar_nome_filial)
        filiais = ['Todas'] + sorted([str(x) for x in df_all['FILIAL_PADRAO'].unique() if pd.notna(x)])
        filtro_filial = st.selectbox("Filial", filiais, key="venc_rec_filial")

    with col3:
        if 'DESCRICAO' in df_all.columns:
            categorias = ['Todas'] + sorted([str(x) for x in df_all['DESCRICAO'].unique() if pd.notna(x)])
            filtro_categoria = st.selectbox("Categoria", categorias, key="venc_rec_categoria")
        else:
            filtro_categoria = 'Todas'

    with col4:
        ordenar = st.selectbox(
            "Ordenar por",
            ["Maior valor", "Vencimento", "Cliente"],
            key="venc_rec_ordem"
        )

    # Aplicar filtros
    if status == "Vencidos":
        df_show = df_vencidos.copy()
    elif status == "A Receber":
        df_show = df_pendentes.copy()
    else:
        df_show = pd.concat([df_pendentes, df_vencidos]).drop_duplicates()

    df_show['FILIAL_PADRAO'] = df_show['NOME_FILIAL'].apply(_padronizar_nome_filial)

    if filtro_filial != 'Todas':
        df_show = df_show[df_show['FILIAL_PADRAO'] == filtro_filial]

    if filtro_categoria != 'Todas' and 'DESCRICAO' in df_show.columns:
        df_show = df_show[df_show['DESCRICAO'] == filtro_categoria]

    # Ordenar
    if ordenar == "Maior valor":
        df_show = df_show.sort_values('SALDO', ascending=False)
    elif ordenar == "Vencimento":
        df_show = df_show.sort_values('VENCIMENTO')
    else:
        df_show = df_show.sort_values('NOME_CLIENTE')

    df_show = df_show.head(100)

    if len(df_show) == 0:
        st.info("Nenhum titulo encontrado")
        return

    # Metricas
    total = df_show['SALDO'].sum()
    st.markdown(f"**{len(df_show)} titulos** | Total: **{formatar_moeda(total)}**")

    # Tabela
    colunas = ['FILIAL_PADRAO', 'NOME_CLIENTE', 'DESCRICAO', 'VENCIMENTO', 'SALDO', 'STATUS']
    colunas_disp = [c for c in colunas if c in df_show.columns]
    df_tab = df_show[colunas_disp].copy()

    if 'VENCIMENTO' in df_tab.columns:
        df_tab['VENCIMENTO'] = pd.to_datetime(df_tab['VENCIMENTO']).dt.strftime('%d/%m/%Y')

    if 'SALDO' in df_tab.columns:
        df_tab['SALDO'] = df_tab['SALDO'].apply(lambda x: formatar_moeda(x, completo=True))

    nomes = {
        'FILIAL_PADRAO': 'Filial',
        'NOME_CLIENTE': 'Cliente',
        'DESCRICAO': 'Categoria',
        'VENCIMENTO': 'Vencimento',
        'SALDO': 'Valor',
        'STATUS': 'Status'
    }
    df_tab.columns = [nomes.get(c, c) for c in df_tab.columns]

    st.dataframe(df_tab, use_container_width=True, hide_index=True, height=400)
