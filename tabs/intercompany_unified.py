"""
Intercompany Unificado - Conciliacao entre Empresas do Grupo
Dashboard Financeiro - Grupo Progresso

Agrupamento pelo prefixo centenario do codigo da filial (FILIAL // 100):
  1xx -> Progresso Agricola  (Matriz 101, Rainha 102, Imperial 103, Peninsula 104, Tropical 105, Ouro Branco 120)
  2xx -> Progresso Agroindustrial  (filiais estaduais: PI, MG, GO, BA, MA, MT, PA, RO, TO, ...)
  3xx-8xx e demais -> Outros  (Brasil Agricola, Tropical Agropart, FBO, AG3, CG3, SDS)
  Familia Sanders -> identificado pelo nome do fornecedor/cliente (pessoas fisicas do grupo)

Conciliacao: Se Grupo A paga para Grupo B, entao B deve ter a receber de A.
  DIFERENCA = SALDO_PAGAR - SALDO_RECEBER
  Positiva = falta lancamento no A Receber | Negativa = falta no A Pagar
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from config.theme import get_cores
from data.loader import carregar_dados
from data.loader_receber import carregar_dados_receber
from utils.formatters import formatar_moeda, formatar_numero


# =====================================================================
# CONFIGURACAO DE GRUPOS INTERCOMPANY
# =====================================================================

# Prefixo centenario (FILIAL // 100) -> grupo de exibicao
_PREFIXO_GRUPO = {
    1: 'Progresso Agricola',
    2: 'Progresso Agroindustrial',
    4: 'Progresso Agricola',       # Tropical
    5: 'Progresso Agricola',       # FBO (Fazenda Ouro Branco)
}

# Padroes para identificar o grupo do DESTINO (fornecedor/cliente)
# Ordem importa: mais especifico primeiro
_DESTINO_PADROES = [
    # --- Progresso Agroindustrial (filiais 2xx) ---
    ('PROGRESSO AGROINDUST', 'Progresso Agroindustrial'),

    # --- Progresso Agricola (filiais 1xx) ---
    ('PROGRESSO MATRIZ', 'Progresso Agricola'),
    ('PROGRESSO AGRICOLA', 'Progresso Agricola'),
    ('FAZENDA PENINSULA', 'Progresso Agricola'),
    ('PENINSULA', 'Progresso Agricola'),
    ('IMPERIAL', 'Progresso Agricola'),
    ('RAINHA DA SERRA', 'Progresso Agricola'),
    ('FAZENDA OURO BRANCO', 'Progresso Agricola'),
    ('OURO BRANCO INSUMOS', 'Progresso Agricola'),
    ('SEMENTES OURO BRANCO', 'Progresso Agricola'),
    ('OURO BRANCO', 'Progresso Agricola'),
    ('FAZENDA TROPICAL', 'Progresso Agricola'),
    ('HOTEL TROPICAL', 'Progresso Agricola'),
    ('POUSADA TROPICAL', 'Progresso Agricola'),

    # --- Familia Sanders (pessoas fisicas do grupo) ---
    ('CORNELIO', 'Familia Sanders'),
    ('GREICY', 'Familia Sanders'),
    ('GREGORY SANDERS', 'Familia Sanders'),
    ('GUEBERSON SANDERS', 'Familia Sanders'),

    # --- Outros (filiais 3xx-8xx) ---
    ('BRASIL AGRICOLA', 'Outros'),
    ('TROPICAL AGROPART', 'Progresso Agricola'),
    ('PROGRESSO FBO', 'Progresso Agricola'),
    ('AG3 AGRO', 'Outros'),
    ('CG3 AGRO', 'Outros'),
    ('SDS PARTICIPACOES', 'Outros'),
    # TROPICAL generico (apos padroes especificos acima) - filial 105 = 1xx
    ('TROPICAL', 'Progresso Agricola'),
]

# Ordem fixa para exibicao
ORDEM_GRUPOS = ['Progresso Agroindustrial', 'Progresso Agricola', 'Familia Sanders', 'Outros']

# Limiar em R$ para considerar um par como divergente
_LIMIAR_DIVERGENCIA = 1000


# =====================================================================
# FUNCOES DE IDENTIFICACAO
# =====================================================================

def _grupo_por_codigo(cod_filial):
    """Grupo IC pelo prefixo centenario do codigo da filial.
    1xx -> Progresso Agricola, 2xx -> Progresso Agroindustrial, demais -> Outros.
    """
    if pd.isna(cod_filial):
        return 'Outros'
    try:
        prefixo = int(float(cod_filial)) // 100
    except (ValueError, TypeError):
        return 'Outros'
    return _PREFIXO_GRUPO.get(prefixo, 'Outros')


def _grupo_por_nome(nome):
    """Identifica o grupo IC pelo nome do fornecedor/cliente.
    Retorna None se nao for intercompany.
    """
    if pd.isna(nome):
        return None
    nome_upper = str(nome).upper()
    for padrao, grupo in _DESTINO_PADROES:
        if padrao in nome_upper:
            return grupo
    return None


# =====================================================================
# CARGA E PROCESSAMENTO
# =====================================================================

def carregar_dados_intercompany():
    """Carrega dados de A Pagar e A Receber, filtra intercompany e adiciona grupos."""
    df_pagar_raw, _ = carregar_dados()
    df_receber_raw, _ = carregar_dados_receber()

    # Grupo ORIGEM (quem registra o titulo) -> pelo codigo da filial
    df_pagar_raw['GRUPO_ORIGEM'] = df_pagar_raw['FILIAL'].apply(_grupo_por_codigo)
    df_receber_raw['GRUPO_ORIGEM'] = df_receber_raw['FILIAL'].apply(_grupo_por_codigo)

    # Grupo DESTINO (fornecedor/cliente) -> pelo nome
    df_pagar_raw['GRUPO_DESTINO'] = df_pagar_raw['NOME_FORNECEDOR'].apply(_grupo_por_nome)
    df_receber_raw['GRUPO_DESTINO'] = df_receber_raw['NOME_CLIENTE'].apply(_grupo_por_nome)

    # Filtrar: apenas intercompany (destino eh entidade do grupo)
    df_pagar = df_pagar_raw[df_pagar_raw['GRUPO_DESTINO'].notna()].copy()
    df_receber = df_receber_raw[df_receber_raw['GRUPO_DESTINO'].notna()].copy()

    return df_pagar, df_receber


def calcular_conciliacao(df_pagar, df_receber):
    """Concilia A Pagar vs A Receber por pares de grupos.

    Logica: Se Grupo A paga para Grupo B, B deve ter a receber de A.
    DIFERENCA = SALDO_PAGAR - SALDO_RECEBER
    """
    # A PAGAR: GRUPO_ORIGEM paga para GRUPO_DESTINO
    pagar_resumo = df_pagar.groupby(['GRUPO_ORIGEM', 'GRUPO_DESTINO']).agg({
        'SALDO': 'sum',
        'VALOR_ORIGINAL': 'sum',
        'NUMERO': 'count'
    }).reset_index()
    pagar_resumo.columns = ['DE', 'PARA', 'SALDO_PAGAR', 'VALOR_PAGAR', 'QTD_PAGAR']

    # A RECEBER: GRUPO_ORIGEM recebe de GRUPO_DESTINO
    # Invertendo: se X recebe de Y, entao Y paga para X
    receber_resumo = df_receber.groupby(['GRUPO_DESTINO', 'GRUPO_ORIGEM']).agg({
        'SALDO': 'sum',
        'VALOR_ORIGINAL': 'sum',
        'NUMERO': 'count'
    }).reset_index()
    receber_resumo.columns = ['DE', 'PARA', 'SALDO_RECEBER', 'VALOR_RECEBER', 'QTD_RECEBER']

    conciliacao = pd.merge(pagar_resumo, receber_resumo, on=['DE', 'PARA'], how='outer').fillna(0)
    conciliacao['DIFERENCA'] = conciliacao['SALDO_PAGAR'] - conciliacao['SALDO_RECEBER']
    conciliacao['DIFERENCA_ABS'] = conciliacao['DIFERENCA'].abs()

    return conciliacao


# =====================================================================
# HELPER - RESUMO POR GRUPO (inclui grupos sem filial, como Familia Sanders)
# =====================================================================

def _resumo_grupos(df_pagar, df_receber):
    """Retorna DataFrame [Grupo, Paga, Recebe, Qtd_Pagar, Qtd_Receber] para todos os grupos.

    Grupos com filial (tem GRUPO_ORIGEM): usa perspectiva de quem registra o titulo.
    Grupos sem filial (ex: Familia Sanders): usa perspectiva invertida do destino.
    """
    rows = []
    for grupo in ORDEM_GRUPOS:
        pagar_orig = df_pagar[df_pagar['GRUPO_ORIGEM'] == grupo]
        receber_orig = df_receber[df_receber['GRUPO_ORIGEM'] == grupo]
        tem_origem = len(pagar_orig) > 0 or len(receber_orig) > 0

        if tem_origem:
            paga = pagar_orig['SALDO'].sum()
            recebe = receber_orig['SALDO'].sum()
            qtd_p = len(pagar_orig)
            qtd_r = len(receber_orig)
        else:
            pagar_dest = df_pagar[df_pagar['GRUPO_DESTINO'] == grupo]
            receber_dest = df_receber[df_receber['GRUPO_DESTINO'] == grupo]
            paga = receber_dest['SALDO'].sum()
            recebe = pagar_dest['SALDO'].sum()
            qtd_p = len(receber_dest)
            qtd_r = len(pagar_dest)

        rows.append({
            'Grupo': grupo, 'Paga': paga, 'Recebe': recebe,
            'Qtd_Pagar': qtd_p, 'Qtd_Receber': qtd_r
        })

    return pd.DataFrame(rows)


# =====================================================================
# RENDERIZACAO PRINCIPAL
# =====================================================================

def render_intercompany_unificado(data_inicio=None, data_fim=None):
    """Renderiza a pagina unificada de Intercompany."""
    cores = get_cores()

    df_pagar, df_receber = carregar_dados_intercompany()

    # Filtro de data
    if data_inicio is not None and data_fim is not None:
        ts_inicio = pd.Timestamp(data_inicio)
        ts_fim = pd.Timestamp(data_fim) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        if 'EMISSAO' in df_pagar.columns:
            df_pagar = df_pagar[(df_pagar['EMISSAO'] >= ts_inicio) & (df_pagar['EMISSAO'] <= ts_fim)]
        if 'EMISSAO' in df_receber.columns:
            df_receber = df_receber[(df_receber['EMISSAO'] >= ts_inicio) & (df_receber['EMISSAO'] <= ts_fim)]

    conciliacao = calcular_conciliacao(df_pagar, df_receber)

    # ========== METRICAS PRINCIPAIS (header) ==========
    total_pagar = df_pagar['SALDO'].sum()
    total_receber = df_receber['SALDO'].sum()
    diferenca_liq = total_pagar - total_receber
    pares_divergentes = len(conciliacao[conciliacao['DIFERENCA_ABS'] >= _LIMIAR_DIVERGENCIA])

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, {cores['primaria']}15, {cores['card']});
                border: 2px solid {cores['primaria']}; border-radius: 16px;
                padding: 1.5rem; margin-bottom: 1.25rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
            <div>
                <p style="color: {cores['primaria']}; font-size: 0.9rem; font-weight: 600; margin: 0;">
                    CONCILIACAO INTERCOMPANY</p>
                <p style="color: {cores['texto']}; font-size: 2rem; font-weight: 700; margin: 0.25rem 0;">
                    Operacoes entre Empresas do Grupo</p>
                <p style="color: {cores['texto_secundario']}; font-size: 0.85rem; margin: 0;">
                    Agrupado por: Progresso Agroindustrial | Progresso Agricola | Familia Sanders | Outros</p>
            </div>
            <div style="display: flex; gap: 1.5rem; flex-wrap: wrap;">
                <div style="text-align: center; padding: 1rem; background: {cores['perigo']}15; border-radius: 10px; min-width: 130px;">
                    <p style="color: {cores['perigo']}; font-size: 0.7rem; font-weight: 600; margin: 0;">A PAGAR IC</p>
                    <p style="color: {cores['perigo']}; font-size: 1.3rem; font-weight: 700; margin: 0.2rem 0;">
                        {formatar_moeda(total_pagar)}</p>
                    <p style="color: {cores['texto_secundario']}; font-size: 0.65rem; margin: 0;">
                        {len(df_pagar)} titulos</p>
                </div>
                <div style="text-align: center; padding: 1rem; background: {cores['sucesso']}15; border-radius: 10px; min-width: 130px;">
                    <p style="color: {cores['sucesso']}; font-size: 0.7rem; font-weight: 600; margin: 0;">A RECEBER IC</p>
                    <p style="color: {cores['sucesso']}; font-size: 1.3rem; font-weight: 700; margin: 0.2rem 0;">
                        {formatar_moeda(total_receber)}</p>
                    <p style="color: {cores['texto_secundario']}; font-size: 0.65rem; margin: 0;">
                        {len(df_receber)} titulos</p>
                </div>
                <div style="text-align: center; padding: 1rem; background: {cores['alerta']}15; border-radius: 10px; min-width: 130px;">
                    <p style="color: {cores['alerta']}; font-size: 0.7rem; font-weight: 600; margin: 0;">DIVERGENTES</p>
                    <p style="color: {cores['alerta']}; font-size: 1.3rem; font-weight: 700; margin: 0.2rem 0;">
                        {pares_divergentes}</p>
                    <p style="color: {cores['texto_secundario']}; font-size: 0.65rem; margin: 0;">
                        pares com |dif| >= R$ 1.000</p>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Visao Geral", "Por Tipo de Documento", "Conciliacao",
        "Matriz", "Detalhes A Pagar", "Detalhes A Receber"
    ])

    with tab1:
        _render_visao_geral(df_pagar, df_receber, conciliacao, cores)
    with tab2:
        _render_por_tipo(df_pagar, df_receber, cores)
    with tab3:
        _render_conciliacao(conciliacao, cores)
    with tab4:
        _render_matriz(df_pagar, df_receber, cores)
    with tab5:
        _render_detalhes_pagar(df_pagar, cores)
    with tab6:
        _render_detalhes_receber(df_receber, cores)


# =====================================================================
# TAB 1 - VISAO GERAL
# =====================================================================

def _render_visao_geral(df_pagar, df_receber, conciliacao, cores):
    """Visao Geral: KPIs com criterios explicados, resumo por grupo, indicadores de saude."""

    # --- Criterios dos Totalizadores ---
    st.markdown("##### Criterios dos Totalizadores")
    st.markdown(f"""
    <div style="background: {cores['card']}; border: 1px solid {cores['borda']};
                border-radius: 10px; padding: 1rem; margin-bottom: 1rem; font-size: 0.82rem;">
        <div style="display: flex; flex-wrap: wrap; gap: 1.5rem;">
            <div style="flex: 1; min-width: 200px;">
                <p style="color: {cores['perigo']}; font-weight: 700; margin: 0 0 0.3rem 0;">Total A Pagar IC</p>
                <p style="color: {cores['texto_secundario']}; margin: 0;">
                    Soma do <b>SALDO</b> de todos os titulos do <b>Contas a Pagar</b>
                    cujo fornecedor foi identificado como uma entidade do grupo (intercompany).</p>
            </div>
            <div style="flex: 1; min-width: 200px;">
                <p style="color: {cores['sucesso']}; font-weight: 700; margin: 0 0 0.3rem 0;">Total A Receber IC</p>
                <p style="color: {cores['texto_secundario']}; margin: 0;">
                    Soma do <b>SALDO</b> de todos os titulos do <b>Contas a Receber</b>
                    cujo cliente foi identificado como uma entidade do grupo (intercompany).</p>
            </div>
            <div style="flex: 1; min-width: 200px;">
                <p style="color: {cores['alerta']}; font-weight: 700; margin: 0 0 0.3rem 0;">Pares Divergentes</p>
                <p style="color: {cores['texto_secundario']}; margin: 0;">
                    Quantidade de pares <b>[De, Para]</b> onde a diferenca absoluta entre
                    o que o grupo <i>De</i> registra como A Pagar e o que o grupo <i>Para</i>
                    registra como A Receber e <b>>= R$ 1.000</b>.
                    Indica conciliacao incompleta entre os grupos.</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # --- KPIs por Grupo ---
    st.markdown("##### Resumo por Grupo")

    df_resumo = _resumo_grupos(df_pagar, df_receber)

    grupos_data = []
    for _, row in df_resumo.iterrows():
        grupo = row['Grupo']
        conc_grupo = conciliacao[(conciliacao['DE'] == grupo) | (conciliacao['PARA'] == grupo)]
        divergentes = len(conc_grupo[conc_grupo['DIFERENCA_ABS'] >= _LIMIAR_DIVERGENCIA])

        grupos_data.append({
            'grupo': grupo,
            'paga': row['Paga'],
            'recebe': row['Recebe'],
            'qtd_pagar': int(row['Qtd_Pagar']),
            'qtd_receber': int(row['Qtd_Receber']),
            'divergentes': divergentes,
        })

    cols = st.columns(len(ORDEM_GRUPOS))
    for i, gd in enumerate(grupos_data):
        with cols[i]:
            saldo = gd['recebe'] - gd['paga']
            cor_saldo = cores['sucesso'] if saldo >= 0 else cores['perigo']
            status_txt = 'Credor' if saldo >= 0 else 'Devedor'

            st.markdown(f"""
            <div style="background: {cores['card']}; border: 1px solid {cores['borda']};
                        border-radius: 12px; padding: 1rem; text-align: center;">
                <p style="color: {cores['primaria']}; font-weight: 700; font-size: 0.85rem;
                          margin: 0 0 0.5rem 0;">{gd['grupo']}</p>
                <div style="margin-bottom: 0.5rem;">
                    <p style="color: {cores['perigo']}; font-size: 0.7rem; margin: 0;">Paga</p>
                    <p style="color: {cores['texto']}; font-size: 1rem; font-weight: 600; margin: 0;">
                        {formatar_moeda(gd['paga'])}</p>
                    <p style="color: {cores['texto_secundario']}; font-size: 0.65rem; margin: 0;">
                        {gd['qtd_pagar']} titulos</p>
                </div>
                <div style="margin-bottom: 0.5rem;">
                    <p style="color: {cores['sucesso']}; font-size: 0.7rem; margin: 0;">Recebe</p>
                    <p style="color: {cores['texto']}; font-size: 1rem; font-weight: 600; margin: 0;">
                        {formatar_moeda(gd['recebe'])}</p>
                    <p style="color: {cores['texto_secundario']}; font-size: 0.65rem; margin: 0;">
                        {gd['qtd_receber']} titulos</p>
                </div>
                <div style="border-top: 1px solid {cores['borda']}; padding-top: 0.5rem;">
                    <p style="color: {cor_saldo}; font-size: 0.95rem; font-weight: 700; margin: 0;">
                        {formatar_moeda(saldo)}</p>
                    <p style="color: {cor_saldo}; font-size: 0.65rem; margin: 0;">{status_txt}</p>
                </div>
                <div style="margin-top: 0.4rem;">
                    <p style="color: {cores['alerta'] if gd['divergentes'] > 0 else cores['sucesso']};
                              font-size: 0.7rem; margin: 0;">
                        {gd['divergentes']} par(es) divergente(s)</p>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    # --- Grafico de distribuicao por grupo (usando mesmos dados dos cards) ---
    col1, col2 = st.columns(2)

    pie_pagar = pd.DataFrame([{'Grupo': gd['grupo'], 'Saldo': gd['paga']} for gd in grupos_data])
    pie_pagar = pie_pagar[pie_pagar['Saldo'] > 0].sort_values('Saldo', ascending=False)

    pie_receber = pd.DataFrame([{'Grupo': gd['grupo'], 'Saldo': gd['recebe']} for gd in grupos_data])
    pie_receber = pie_receber[pie_receber['Saldo'] > 0].sort_values('Saldo', ascending=False)

    with col1:
        st.markdown("##### Distribuicao A Pagar por Grupo")

        if len(pie_pagar) > 0:
            fig = go.Figure(data=[go.Pie(
                labels=pie_pagar['Grupo'],
                values=pie_pagar['Saldo'],
                hole=0.4,
                textinfo='label+percent',
                textfont=dict(size=10, color=cores['texto']),
                marker=dict(colors=[cores['perigo'], cores['primaria'], cores['alerta'], cores['info']])
            )])
            fig.update_layout(
                height=300,
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor='rgba(0,0,0,0)',
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados de A Pagar intercompany")

    with col2:
        st.markdown("##### Distribuicao A Receber por Grupo")

        if len(pie_receber) > 0:
            fig = go.Figure(data=[go.Pie(
                labels=pie_receber['Grupo'],
                values=pie_receber['Saldo'],
                hole=0.4,
                textinfo='label+percent',
                textfont=dict(size=10, color=cores['texto']),
                marker=dict(colors=[cores['sucesso'], cores['primaria'], cores['alerta'], cores['info']])
            )])
            fig.update_layout(
                height=300,
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor='rgba(0,0,0,0)',
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados de A Receber intercompany")

    st.divider()

    # --- Recebido e Pendente por Filial ---
    st.markdown("##### Situacao por Filial (Intercompany)")
    st.caption("Valores ja recebidos/pagos vs pendentes, agrupados por filial de origem")

    # Combinar A Pagar e A Receber para visao completa por filial
    filial_col = 'NOME_FILIAL'
    if filial_col in df_pagar.columns and filial_col in df_receber.columns:
        # A Pagar por filial
        pagar_fil = df_pagar.groupby(filial_col).agg(
            {'VALOR_ORIGINAL': 'sum', 'SALDO': 'sum'}).reset_index()
        pagar_fil['RECEBIDO'] = pagar_fil['VALOR_ORIGINAL'] - pagar_fil['SALDO']
        pagar_fil['TIPO_OP'] = 'A Pagar'

        # A Receber por filial
        receber_fil = df_receber.groupby(filial_col).agg(
            {'VALOR_ORIGINAL': 'sum', 'SALDO': 'sum'}).reset_index()
        receber_fil['RECEBIDO'] = receber_fil['VALOR_ORIGINAL'] - receber_fil['SALDO']
        receber_fil['TIPO_OP'] = 'A Receber'

        # Consolidar por filial (somar A Pagar + A Receber)
        df_filial = pd.concat([pagar_fil, receber_fil], ignore_index=True)
        df_filial_agg = df_filial.groupby(filial_col).agg(
            {'SALDO': 'sum', 'RECEBIDO': 'sum'}).reset_index()
        df_filial_agg.columns = ['Filial', 'Pendente', 'Recebido']
        df_filial_agg = df_filial_agg[(df_filial_agg['Pendente'] > 0) | (df_filial_agg['Recebido'] > 0)]

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("##### Pendente por Filial")

            df_pend = df_filial_agg[df_filial_agg['Pendente'] > 0].sort_values(
                'Pendente', ascending=True).tail(15)

            if len(df_pend) > 0:
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    y=df_pend['Filial'],
                    x=df_pend['Pendente'],
                    orientation='h',
                    marker_color=cores['alerta'],
                    text=[formatar_moeda(x) for x in df_pend['Pendente']],
                    textposition='outside',
                    textfont=dict(size=8, color=cores['texto'])
                ))
                fig.update_layout(
                    height=max(250, len(df_pend) * 28),
                    margin=dict(l=10, r=80, t=10, b=10),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(showticklabels=False, showgrid=True, gridcolor=cores['borda']),
                    yaxis=dict(tickfont=dict(color=cores['texto'], size=9))
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.success("Nenhum titulo pendente")

        with col2:
            st.markdown("##### Recebido por Filial")

            df_rec = df_filial_agg[df_filial_agg['Recebido'] > 0].sort_values(
                'Recebido', ascending=True).tail(15)

            if len(df_rec) > 0:
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    y=df_rec['Filial'],
                    x=df_rec['Recebido'],
                    orientation='h',
                    marker_color=cores['sucesso'],
                    text=[formatar_moeda(x) for x in df_rec['Recebido']],
                    textposition='outside',
                    textfont=dict(size=8, color=cores['texto'])
                ))
                fig.update_layout(
                    height=max(250, len(df_rec) * 28),
                    margin=dict(l=10, r=80, t=10, b=10),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(showticklabels=False, showgrid=True, gridcolor=cores['borda']),
                    yaxis=dict(tickfont=dict(color=cores['texto'], size=9))
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Nenhum titulo recebido")

    st.divider()

    # --- Indicador de saude geral ---
    st.markdown("##### Indicador de Saude da Conciliacao")

    total_pares = len(conciliacao)
    pares_ok = len(conciliacao[conciliacao['DIFERENCA_ABS'] < _LIMIAR_DIVERGENCIA])
    pares_div = total_pares - pares_ok
    pct_ok = (pares_ok / total_pares * 100) if total_pares > 0 else 0

    if pct_ok >= 80:
        cor_saude = cores['sucesso']
        status_saude = 'Boa'
    elif pct_ok >= 50:
        cor_saude = cores['alerta']
        status_saude = 'Atencao'
    else:
        cor_saude = cores['perigo']
        status_saude = 'Critica'

    st.markdown(f"""
    <div style="background: {cores['card']}; border: 1px solid {cores['borda']};
                border-radius: 10px; padding: 1rem;">
        <div style="display: flex; align-items: center; gap: 2rem; flex-wrap: wrap;">
            <div>
                <p style="color: {cor_saude}; font-size: 2.5rem; font-weight: 700; margin: 0;">
                    {pct_ok:.0f}%</p>
                <p style="color: {cor_saude}; font-size: 0.85rem; font-weight: 600; margin: 0;">
                    Conciliacao {status_saude}</p>
            </div>
            <div style="flex: 1;">
                <div style="background: {cores['borda']}; border-radius: 8px; height: 20px; overflow: hidden;">
                    <div style="background: {cor_saude}; width: {pct_ok}%; height: 100%; border-radius: 8px;"></div>
                </div>
                <div style="display: flex; justify-content: space-between; margin-top: 0.3rem;">
                    <span style="color: {cores['texto_secundario']}; font-size: 0.75rem;">
                        {pares_ok} pares conciliados</span>
                    <span style="color: {cores['texto_secundario']}; font-size: 0.75rem;">
                        {pares_div} pares divergentes (de {total_pares} total)</span>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# =====================================================================
# TAB 2 - POR TIPO DE DOCUMENTO
# =====================================================================

def _render_por_tipo(df_pagar, df_receber, cores):
    """Analise segregada por Tipo de Documento (TIPO)."""

    st.markdown("##### Analise por Tipo de Documento")
    st.caption("Segregacao dos valores intercompany por tipo de documento (NF, DP, FAT, etc.)")

    # --- Tabela resumo por TIPO ---
    tipo_pagar = pd.DataFrame()
    tipo_receber = pd.DataFrame()

    if 'TIPO' in df_pagar.columns:
        tipo_pagar = df_pagar.groupby('TIPO').agg({
            'SALDO': 'sum',
            'VALOR_ORIGINAL': 'sum',
            'NUMERO': 'count'
        }).reset_index()
        tipo_pagar.columns = ['TIPO', 'SALDO_PAGAR', 'VALOR_PAGAR', 'QTD_PAGAR']

    if 'TIPO' in df_receber.columns:
        tipo_receber = df_receber.groupby('TIPO').agg({
            'SALDO': 'sum',
            'VALOR_ORIGINAL': 'sum',
            'NUMERO': 'count'
        }).reset_index()
        tipo_receber.columns = ['TIPO', 'SALDO_RECEBER', 'VALOR_RECEBER', 'QTD_RECEBER']

    if len(tipo_pagar) > 0 or len(tipo_receber) > 0:
        df_tipo = pd.merge(tipo_pagar, tipo_receber, on='TIPO', how='outer').fillna(0)
        df_tipo['DIFERENCA'] = df_tipo['SALDO_PAGAR'] - df_tipo['SALDO_RECEBER']
        df_tipo['DIFERENCA_ABS'] = df_tipo['DIFERENCA'].abs()
        df_tipo = df_tipo.sort_values('SALDO_PAGAR', ascending=False)

        # KPIs por tipo
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Tipos de Documento", len(df_tipo))
        with col2:
            tipo_maior = df_tipo.iloc[0]['TIPO'] if len(df_tipo) > 0 else '-'
            st.metric("Maior Volume (Pagar)", tipo_maior)
        with col3:
            tipos_divergentes = len(df_tipo[df_tipo['DIFERENCA_ABS'] >= _LIMIAR_DIVERGENCIA])
            st.metric("Tipos com Divergencia", tipos_divergentes)

        st.divider()

        # Grafico comparativo por TIPO
        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown("##### Comparativo A Pagar vs A Receber por Tipo")

            fig = go.Figure()

            fig.add_trace(go.Bar(
                name='A Pagar',
                x=df_tipo['TIPO'],
                y=df_tipo['SALDO_PAGAR'],
                marker_color=cores['perigo'],
                text=[formatar_moeda(x) for x in df_tipo['SALDO_PAGAR']],
                textposition='outside',
                textfont=dict(size=8, color=cores['texto'])
            ))

            fig.add_trace(go.Bar(
                name='A Receber',
                x=df_tipo['TIPO'],
                y=df_tipo['SALDO_RECEBER'],
                marker_color=cores['sucesso'],
                text=[formatar_moeda(x) for x in df_tipo['SALDO_RECEBER']],
                textposition='outside',
                textfont=dict(size=8, color=cores['texto'])
            ))

            fig.update_layout(
                barmode='group',
                height=400,
                margin=dict(l=10, r=10, t=10, b=50),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(tickfont=dict(color=cores['texto'], size=10)),
                yaxis=dict(showticklabels=False, showgrid=True, gridcolor=cores['borda']),
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5,
                           font=dict(color=cores['texto'], size=10))
            )

            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("##### Divergencia por Tipo")

            df_div = df_tipo[df_tipo['DIFERENCA_ABS'] >= _LIMIAR_DIVERGENCIA].sort_values(
                'DIFERENCA_ABS', ascending=False)

            if len(df_div) > 0:
                colors = [cores['perigo'] if x > 0 else cores['sucesso'] for x in df_div['DIFERENCA']]

                fig = go.Figure()
                fig.add_trace(go.Bar(
                    y=df_div['TIPO'],
                    x=df_div['DIFERENCA'],
                    orientation='h',
                    marker_color=colors,
                    text=[formatar_moeda(x) for x in df_div['DIFERENCA']],
                    textposition='outside',
                    textfont=dict(size=8, color=cores['texto'])
                ))

                fig.update_layout(
                    height=400,
                    margin=dict(l=10, r=80, t=10, b=10),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(showticklabels=False, showgrid=False),
                    yaxis=dict(tickfont=dict(color=cores['texto'], size=10))
                )

                st.plotly_chart(fig, use_container_width=True)
            else:
                st.success("Nenhum tipo com divergencia >= R$ 1.000")

        st.divider()

        # Tabela detalhada
        st.markdown("##### Tabela por Tipo de Documento")

        df_tab = df_tipo[['TIPO', 'QTD_PAGAR', 'SALDO_PAGAR', 'QTD_RECEBER', 'SALDO_RECEBER', 'DIFERENCA']].copy()
        df_tab['QTD_PAGAR'] = df_tab['QTD_PAGAR'].astype(int)
        df_tab['QTD_RECEBER'] = df_tab['QTD_RECEBER'].astype(int)

        # Linha de totais
        totais = pd.DataFrame([{
            'TIPO': 'TOTAL',
            'QTD_PAGAR': int(df_tab['QTD_PAGAR'].sum()),
            'SALDO_PAGAR': df_tipo['SALDO_PAGAR'].sum(),
            'QTD_RECEBER': int(df_tab['QTD_RECEBER'].sum()),
            'SALDO_RECEBER': df_tipo['SALDO_RECEBER'].sum(),
            'DIFERENCA': df_tipo['DIFERENCA'].sum()
        }])
        df_tab = pd.concat([df_tab, totais], ignore_index=True)

        df_tab['SALDO_PAGAR'] = df_tab['SALDO_PAGAR'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab['SALDO_RECEBER'] = df_tab['SALDO_RECEBER'].apply(lambda x: formatar_moeda(x, completo=True))
        df_tab['DIFERENCA'] = df_tab['DIFERENCA'].apply(lambda x: formatar_moeda(x, completo=True))

        df_tab.columns = ['Tipo', 'Qtd Pagar', 'Saldo Pagar', 'Qtd Receber', 'Saldo Receber', 'Diferenca']

        st.dataframe(df_tab, use_container_width=True, hide_index=True, height=400)

        st.divider()

        # Detalhamento por Tipo e Grupo
        st.markdown("##### Detalhamento: Tipo x Grupo")

        col_tg1, col_tg2 = st.columns(2)

        with col_tg1:
            if 'TIPO' in df_pagar.columns:
                tipo_grupo_pagar = df_pagar.groupby(['TIPO', 'GRUPO_DESTINO']).agg(
                    {'SALDO': 'sum'}).reset_index()
                pivot_pagar = tipo_grupo_pagar.pivot_table(
                    index='TIPO', columns='GRUPO_DESTINO', values='SALDO',
                    aggfunc='sum', fill_value=0
                )
                cols_order = [g for g in ORDEM_GRUPOS if g in pivot_pagar.columns]
                cols_order += [c for c in pivot_pagar.columns if c not in cols_order]
                pivot_pagar = pivot_pagar[cols_order]
                pivot_pagar['Total'] = pivot_pagar.sum(axis=1)
                pivot_pagar = pivot_pagar.sort_values('Total', ascending=False)

                st.markdown(f"<p style='color: {cores['perigo']}; font-weight: 600; font-size: 0.85rem;'>"
                            "A Pagar por Tipo x Grupo Destino</p>", unsafe_allow_html=True)

                pivot_fmt = pivot_pagar.copy()
                for col in pivot_fmt.columns:
                    pivot_fmt[col] = pivot_fmt[col].apply(lambda x: formatar_moeda(x) if x > 0 else '-')

                st.dataframe(pivot_fmt, use_container_width=True, height=300)
                st.caption("Quem recebe o pagamento, por tipo de documento")

        with col_tg2:
            if 'TIPO' in df_receber.columns:
                tipo_grupo_receber = df_receber.groupby(['TIPO', 'GRUPO_DESTINO']).agg(
                    {'SALDO': 'sum'}).reset_index()
                pivot_receber = tipo_grupo_receber.pivot_table(
                    index='TIPO', columns='GRUPO_DESTINO', values='SALDO',
                    aggfunc='sum', fill_value=0
                )
                cols_order = [g for g in ORDEM_GRUPOS if g in pivot_receber.columns]
                cols_order += [c for c in pivot_receber.columns if c not in cols_order]
                pivot_receber = pivot_receber[cols_order]
                pivot_receber['Total'] = pivot_receber.sum(axis=1)
                pivot_receber = pivot_receber.sort_values('Total', ascending=False)

                st.markdown(f"<p style='color: {cores['sucesso']}; font-weight: 600; font-size: 0.85rem;'>"
                            "A Receber por Tipo x Grupo Destino</p>", unsafe_allow_html=True)

                pivot_fmt = pivot_receber.copy()
                for col in pivot_fmt.columns:
                    pivot_fmt[col] = pivot_fmt[col].apply(lambda x: formatar_moeda(x) if x > 0 else '-')

                st.dataframe(pivot_fmt, use_container_width=True, height=300)
                st.caption("De quem se recebe, por tipo de documento")

    else:
        st.info("Coluna TIPO nao disponivel nos dados")


# =====================================================================
# TAB 3 - CONCILIACAO
# =====================================================================

def _render_conciliacao(conciliacao, cores):
    """Conciliacao: pares divergentes explicados, grafico e tabela com filtros De/Para."""

    # --- Explicacao de Pares Divergentes ---
    st.markdown("##### O que sao Pares Divergentes?")
    st.markdown(f"""
    <div style="background: {cores['card']}; border-left: 4px solid {cores['alerta']};
                border-radius: 0 10px 10px 0; padding: 1rem; margin-bottom: 1rem; font-size: 0.82rem;">
        <p style="color: {cores['texto']}; margin: 0 0 0.5rem 0;">
            Um <b>par divergente</b> e uma combinacao <b>[De, Para]</b> (ex: Progresso Agroindustrial -> Progresso Agricola)
            onde a diferenca absoluta entre o que o grupo <i>De</i> registra como <b>Contas a Pagar</b>
            e o que o grupo <i>Para</i> registra como <b>Contas a Receber</b> e <b>>= R$ 1.000</b>.</p>
        <p style="color: {cores['texto_secundario']}; margin: 0;">
            <b>Exemplo:</b> Se Progresso Agroindustrial registra R$ 100.000 a pagar para Progresso Agricola,
            mas Progresso Agricola registra apenas R$ 80.000 a receber de Agroindustrial,
            a diferenca de R$ 20.000 indica titulos nao conciliados — faltam lancamentos no A Receber.</p>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # --- KPIs ---
    col1, col2, col3, col4 = st.columns(4)

    total_pagar = conciliacao['SALDO_PAGAR'].sum()
    total_receber = conciliacao['SALDO_RECEBER'].sum()
    diferenca = conciliacao['DIFERENCA'].sum()

    with col1:
        st.metric("Total A Pagar IC", formatar_moeda(total_pagar))
    with col2:
        st.metric("Total A Receber IC", formatar_moeda(total_receber))
    with col3:
        cor_dif = "inverse" if diferenca > 0 else "normal"
        st.metric("Diferenca Liquida", formatar_moeda(diferenca), delta_color=cor_dif)
    with col4:
        pares_divergentes = len(conciliacao[conciliacao['DIFERENCA_ABS'] >= _LIMIAR_DIVERGENCIA])
        st.metric("Pares Divergentes", pares_divergentes)

    st.divider()

    # --- Grafico de divergencias ---
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("##### Maiores Divergencias")

        top_div = conciliacao[conciliacao['DIFERENCA_ABS'] >= _LIMIAR_DIVERGENCIA].nlargest(
            15, 'DIFERENCA_ABS').copy()
        top_div['PAR'] = top_div['DE'] + ' -> ' + top_div['PARA']

        if len(top_div) > 0:
            colors = [cores['perigo'] if x > 0 else cores['sucesso'] for x in top_div['DIFERENCA']]

            fig = go.Figure()
            fig.add_trace(go.Bar(
                y=top_div['PAR'],
                x=top_div['DIFERENCA'],
                orientation='h',
                marker_color=colors,
                text=[formatar_moeda(x) for x in top_div['DIFERENCA']],
                textposition='outside',
                textfont=dict(size=9, color=cores['texto'])
            ))

            fig.add_vline(x=0, line_dash="dash", line_color=cores['texto_secundario'], line_width=1)

            fig.update_layout(
                height=400,
                margin=dict(l=10, r=100, t=10, b=10),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showticklabels=False, showgrid=True, gridcolor=cores['borda'], zeroline=False),
                yaxis=dict(tickfont=dict(color=cores['texto'], size=9))
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.success("Todas as operacoes estao conciliadas!")

    with col2:
        st.markdown("##### Legenda")
        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['borda']};
                    border-radius: 10px; padding: 1rem; font-size: 0.8rem;">
            <p style="color: {cores['texto']}; margin-bottom: 0.75rem;"><b>Como interpretar:</b></p>
            <p style="color: {cores['perigo']}; margin: 0.5rem 0;">
                <b>Diferenca Positiva:</b><br>
                A Pagar > A Receber<br>
                <i>Falta lancamento no Contas a Receber do grupo destino</i>
            </p>
            <p style="color: {cores['sucesso']}; margin: 0.5rem 0;">
                <b>Diferenca Negativa:</b><br>
                A Receber > A Pagar<br>
                <i>Falta lancamento no Contas a Pagar do grupo origem</i>
            </p>
            <p style="color: {cores['texto_secundario']}; margin: 0.5rem 0;">
                <b>Limiar:</b> R$ 1.000<br>
                Diferencas abaixo desse valor sao consideradas conciliadas.
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # --- Tabela de conciliacao com filtros aprimorados ---
    st.markdown("##### Tabela de Conciliacao Completa")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        filtro_status = st.selectbox(
            "Status", ["Todos", "Divergentes", "Conciliados"], key="conc_status")
    with col2:
        grupos_de = ['Todos'] + sorted(conciliacao['DE'].dropna().unique().tolist())
        filtro_de = st.selectbox("De (Origem)", grupos_de, key="conc_de")
    with col3:
        grupos_para = ['Todos'] + sorted(conciliacao['PARA'].dropna().unique().tolist())
        filtro_para = st.selectbox("Para (Destino)", grupos_para, key="conc_para")
    with col4:
        ordenar = st.selectbox(
            "Ordenar por",
            ["Maior Divergencia", "Maior Valor Pagar", "Maior Valor Receber"],
            key="conc_ordem")

    df_show = conciliacao.copy()

    if filtro_status == "Divergentes":
        df_show = df_show[df_show['DIFERENCA_ABS'] >= _LIMIAR_DIVERGENCIA]
    elif filtro_status == "Conciliados":
        df_show = df_show[df_show['DIFERENCA_ABS'] < _LIMIAR_DIVERGENCIA]

    if filtro_de != 'Todos':
        df_show = df_show[df_show['DE'] == filtro_de]
    if filtro_para != 'Todos':
        df_show = df_show[df_show['PARA'] == filtro_para]

    if ordenar == "Maior Divergencia":
        df_show = df_show.sort_values('DIFERENCA_ABS', ascending=False)
    elif ordenar == "Maior Valor Pagar":
        df_show = df_show.sort_values('SALDO_PAGAR', ascending=False)
    else:
        df_show = df_show.sort_values('SALDO_RECEBER', ascending=False)

    df_tab = df_show[['DE', 'PARA', 'QTD_PAGAR', 'SALDO_PAGAR', 'QTD_RECEBER',
                       'SALDO_RECEBER', 'DIFERENCA']].copy()
    df_tab['QTD_PAGAR'] = df_tab['QTD_PAGAR'].astype(int)
    df_tab['QTD_RECEBER'] = df_tab['QTD_RECEBER'].astype(int)
    df_tab['SALDO_PAGAR'] = df_tab['SALDO_PAGAR'].apply(lambda x: formatar_moeda(x, completo=True))
    df_tab['SALDO_RECEBER'] = df_tab['SALDO_RECEBER'].apply(lambda x: formatar_moeda(x, completo=True))
    df_tab['DIFERENCA'] = df_tab['DIFERENCA'].apply(lambda x: formatar_moeda(x, completo=True))

    df_tab.columns = ['De', 'Para', 'Qtd Pagar', 'Saldo Pagar', 'Qtd Receber', 'Saldo Receber', 'Diferenca']

    st.dataframe(df_tab, use_container_width=True, hide_index=True, height=400)
    st.caption(f"{len(df_tab)} pares exibidos")


# =====================================================================
# TAB 4 - MATRIZ
# =====================================================================

def _render_matriz(df_pagar, df_receber, cores):
    """Matrizes pivot A Pagar / A Receber e comparativo por grupo."""

    st.markdown("##### Matriz de Operacoes Intercompany")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"<p style='color: {cores['perigo']}; font-weight: 600;'>"
                    "A PAGAR: Quem paga para quem</p>", unsafe_allow_html=True)

        matriz_pagar = df_pagar.pivot_table(
            index='GRUPO_ORIGEM',
            columns='GRUPO_DESTINO',
            values='SALDO',
            aggfunc='sum',
            fill_value=0
        )

        # Reordenar por ORDEM_GRUPOS
        idx_order = [g for g in ORDEM_GRUPOS if g in matriz_pagar.index]
        col_order = [g for g in ORDEM_GRUPOS if g in matriz_pagar.columns]
        idx_order += [g for g in matriz_pagar.index if g not in idx_order]
        col_order += [g for g in matriz_pagar.columns if g not in col_order]
        matriz_pagar = matriz_pagar.reindex(index=idx_order, columns=col_order, fill_value=0)

        matriz_pagar_fmt = matriz_pagar.copy()
        for col in matriz_pagar_fmt.columns:
            matriz_pagar_fmt[col] = matriz_pagar_fmt[col].apply(
                lambda x: formatar_moeda(x) if x > 0 else '-')

        st.dataframe(matriz_pagar_fmt, use_container_width=True, height=250)
        st.caption("Linha = Quem paga | Coluna = Para quem")

    with col2:
        st.markdown(f"<p style='color: {cores['sucesso']}; font-weight: 600;'>"
                    "A RECEBER: Quem recebe de quem</p>", unsafe_allow_html=True)

        matriz_receber = df_receber.pivot_table(
            index='GRUPO_ORIGEM',
            columns='GRUPO_DESTINO',
            values='SALDO',
            aggfunc='sum',
            fill_value=0
        )

        idx_order = [g for g in ORDEM_GRUPOS if g in matriz_receber.index]
        col_order = [g for g in ORDEM_GRUPOS if g in matriz_receber.columns]
        idx_order += [g for g in matriz_receber.index if g not in idx_order]
        col_order += [g for g in matriz_receber.columns if g not in col_order]
        matriz_receber = matriz_receber.reindex(index=idx_order, columns=col_order, fill_value=0)

        matriz_receber_fmt = matriz_receber.copy()
        for col in matriz_receber_fmt.columns:
            matriz_receber_fmt[col] = matriz_receber_fmt[col].apply(
                lambda x: formatar_moeda(x) if x > 0 else '-')

        st.dataframe(matriz_receber_fmt, use_container_width=True, height=250)
        st.caption("Linha = Quem recebe | Coluna = De quem")

    st.divider()

    # Comparativo por grupo (barras horizontais espelhadas) - inclui grupos sem filial
    st.markdown("##### Comparativo por Grupo")

    df_comp = _resumo_grupos(df_pagar, df_receber)
    df_comp['Saldo'] = df_comp['Recebe'] - df_comp['Paga']

    # Ordenar pela ORDEM_GRUPOS (invertido para grafico horizontal)
    df_comp['_ordem'] = df_comp['Grupo'].apply(
        lambda x: ORDEM_GRUPOS.index(x) if x in ORDEM_GRUPOS else len(ORDEM_GRUPOS))
    df_comp = df_comp.sort_values('_ordem', ascending=False)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        name='A Pagar',
        y=df_comp['Grupo'],
        x=-df_comp['Paga'],
        orientation='h',
        marker_color=cores['perigo'],
        text=[formatar_moeda(x) for x in df_comp['Paga']],
        textposition='inside',
        textfont=dict(size=9, color='white')
    ))

    fig.add_trace(go.Bar(
        name='A Receber',
        y=df_comp['Grupo'],
        x=df_comp['Recebe'],
        orientation='h',
        marker_color=cores['sucesso'],
        text=[formatar_moeda(x) for x in df_comp['Recebe']],
        textposition='inside',
        textfont=dict(size=9, color='white')
    ))

    fig.add_vline(x=0, line_color=cores['texto'], line_width=2)

    fig.update_layout(
        barmode='relative',
        height=300,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showticklabels=False, showgrid=False),
        yaxis=dict(tickfont=dict(color=cores['texto'], size=10)),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5,
                   font=dict(color=cores['texto'], size=10))
    )

    st.plotly_chart(fig, use_container_width=True)

    # Tabela resumo comparativo
    df_comp_tab = df_comp[['Grupo', 'Paga', 'Recebe', 'Saldo']].copy()
    df_comp_tab['Paga'] = df_comp_tab['Paga'].apply(lambda x: formatar_moeda(x, completo=True))
    df_comp_tab['Recebe'] = df_comp_tab['Recebe'].apply(lambda x: formatar_moeda(x, completo=True))
    df_comp_tab['Saldo'] = df_comp_tab['Saldo'].apply(lambda x: formatar_moeda(x, completo=True))
    df_comp_tab.columns = ['Grupo', 'Total A Pagar', 'Total A Receber', 'Saldo (Receber - Pagar)']

    st.dataframe(df_comp_tab, use_container_width=True, hide_index=True)


# =====================================================================
# TAB 5 - DETALHES A PAGAR
# =====================================================================

def _render_detalhes_pagar(df_pagar, cores):
    """Titulos individuais A Pagar com filtros completos."""

    st.markdown("##### Titulos A Pagar - Intercompany")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        grupos_origem = ['Todos'] + sorted(df_pagar['GRUPO_ORIGEM'].dropna().unique().tolist())
        filtro_grupo_orig = st.selectbox("Grupo Origem", grupos_origem, key="pagar_grupo_orig")

    with col2:
        grupos_destino = ['Todos'] + sorted(df_pagar['GRUPO_DESTINO'].dropna().unique().tolist())
        filtro_grupo_dest = st.selectbox("Paga Para", grupos_destino, key="pagar_grupo_dest")

    with col3:
        filtro_status = st.selectbox("Status", ['Todos', 'Pendente', 'Vencido'], key="pagar_status")

    with col4:
        if 'TIPO' in df_pagar.columns:
            tipos = ['Todos'] + sorted(df_pagar['TIPO'].dropna().unique().tolist())
        else:
            tipos = ['Todos']
        filtro_tipo = st.selectbox("Tipo Doc", tipos, key="pagar_tipo")

    with col5:
        ordenar = st.selectbox("Ordenar", ["Maior Saldo", "Mais Recente", "Mais Antigo"], key="pagar_ordem")

    df_show = df_pagar.copy()

    if filtro_grupo_orig != 'Todos':
        df_show = df_show[df_show['GRUPO_ORIGEM'] == filtro_grupo_orig]
    if filtro_grupo_dest != 'Todos':
        df_show = df_show[df_show['GRUPO_DESTINO'] == filtro_grupo_dest]
    if filtro_status == 'Pendente':
        df_show = df_show[df_show['SALDO'] > 0]
    elif filtro_status == 'Vencido':
        df_show = df_show[(df_show['SALDO'] > 0) & (df_show['DIAS_VENC'] < 0)]
    if filtro_tipo != 'Todos' and 'TIPO' in df_show.columns:
        df_show = df_show[df_show['TIPO'] == filtro_tipo]

    if ordenar == "Maior Saldo":
        df_show = df_show.sort_values('SALDO', ascending=False)
    elif ordenar == "Mais Recente":
        df_show = df_show.sort_values('EMISSAO', ascending=False)
    else:
        df_show = df_show.sort_values('EMISSAO', ascending=True)

    # Metricas
    col1, col2, col3 = st.columns(3)
    col1.metric("Titulos", formatar_numero(len(df_show)))
    col2.metric("Saldo Total", formatar_moeda(df_show['SALDO'].sum()))
    col3.metric("Vencidos", formatar_numero(
        len(df_show[(df_show['SALDO'] > 0) & (df_show['DIAS_VENC'] < 0)])))

    st.divider()

    colunas = ['GRUPO_ORIGEM', 'NOME_FILIAL', 'NOME_FORNECEDOR', 'GRUPO_DESTINO',
               'TIPO', 'EMISSAO', 'VENCIMENTO', 'VALOR_ORIGINAL', 'SALDO', 'STATUS']
    colunas_disp = [c for c in colunas if c in df_show.columns]
    df_tab = df_show[colunas_disp].head(500).copy()

    for col in ['EMISSAO', 'VENCIMENTO']:
        if col in df_tab.columns:
            df_tab[col] = pd.to_datetime(df_tab[col], errors='coerce').dt.strftime('%d/%m/%Y')
    for col in ['VALOR_ORIGINAL', 'SALDO']:
        if col in df_tab.columns:
            df_tab[col] = df_tab[col].apply(lambda x: formatar_moeda(x, completo=True))

    nomes = {
        'GRUPO_ORIGEM': 'Grupo Origem',
        'NOME_FILIAL': 'Filial',
        'NOME_FORNECEDOR': 'Fornecedor',
        'GRUPO_DESTINO': 'Paga Para (Grupo)',
        'TIPO': 'Tipo',
        'EMISSAO': 'Emissao',
        'VENCIMENTO': 'Vencimento',
        'VALOR_ORIGINAL': 'Valor',
        'SALDO': 'Saldo',
        'STATUS': 'Status'
    }
    df_tab.columns = [nomes.get(c, c) for c in df_tab.columns]

    st.dataframe(df_tab, use_container_width=True, hide_index=True, height=450)
    st.caption(f"Exibindo {len(df_tab)} de {len(df_show)} registros")


# =====================================================================
# TAB 6 - DETALHES A RECEBER
# =====================================================================

def _render_detalhes_receber(df_receber, cores):
    """Titulos individuais A Receber com filtros completos."""

    st.markdown("##### Titulos A Receber - Intercompany")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        grupos_origem = ['Todos'] + sorted(df_receber['GRUPO_ORIGEM'].dropna().unique().tolist())
        filtro_grupo_orig = st.selectbox("Grupo Origem", grupos_origem, key="receber_grupo_orig")

    with col2:
        grupos_destino = ['Todos'] + sorted(df_receber['GRUPO_DESTINO'].dropna().unique().tolist())
        filtro_grupo_dest = st.selectbox("Recebe De", grupos_destino, key="receber_grupo_dest")

    with col3:
        filtro_status = st.selectbox("Status", ['Todos', 'Pendente', 'Vencido'], key="receber_status")

    with col4:
        if 'TIPO' in df_receber.columns:
            tipos = ['Todos'] + sorted(df_receber['TIPO'].dropna().unique().tolist())
        else:
            tipos = ['Todos']
        filtro_tipo = st.selectbox("Tipo Doc", tipos, key="receber_tipo")

    with col5:
        ordenar = st.selectbox("Ordenar", ["Maior Saldo", "Mais Recente", "Mais Antigo"], key="receber_ordem")

    df_show = df_receber.copy()

    if filtro_grupo_orig != 'Todos':
        df_show = df_show[df_show['GRUPO_ORIGEM'] == filtro_grupo_orig]
    if filtro_grupo_dest != 'Todos':
        df_show = df_show[df_show['GRUPO_DESTINO'] == filtro_grupo_dest]
    if filtro_status == 'Pendente':
        df_show = df_show[df_show['SALDO'] > 0]
    elif filtro_status == 'Vencido':
        df_show = df_show[(df_show['SALDO'] > 0) & (df_show['DIAS_VENC'] < 0)]
    if filtro_tipo != 'Todos' and 'TIPO' in df_show.columns:
        df_show = df_show[df_show['TIPO'] == filtro_tipo]

    if ordenar == "Maior Saldo":
        df_show = df_show.sort_values('SALDO', ascending=False)
    elif ordenar == "Mais Recente":
        df_show = df_show.sort_values('EMISSAO', ascending=False)
    else:
        df_show = df_show.sort_values('EMISSAO', ascending=True)

    # Metricas
    col1, col2, col3 = st.columns(3)
    col1.metric("Titulos", formatar_numero(len(df_show)))
    col2.metric("Saldo Total", formatar_moeda(df_show['SALDO'].sum()))
    col3.metric("Vencidos", formatar_numero(
        len(df_show[(df_show['SALDO'] > 0) & (df_show['DIAS_VENC'] < 0)])))

    st.divider()

    colunas = ['GRUPO_ORIGEM', 'NOME_FILIAL', 'NOME_CLIENTE', 'GRUPO_DESTINO',
               'TIPO', 'EMISSAO', 'VENCIMENTO', 'VALOR_ORIGINAL', 'SALDO', 'STATUS']
    colunas_disp = [c for c in colunas if c in df_show.columns]
    df_tab = df_show[colunas_disp].head(500).copy()

    for col in ['EMISSAO', 'VENCIMENTO']:
        if col in df_tab.columns:
            df_tab[col] = pd.to_datetime(df_tab[col], errors='coerce').dt.strftime('%d/%m/%Y')
    for col in ['VALOR_ORIGINAL', 'SALDO']:
        if col in df_tab.columns:
            df_tab[col] = df_tab[col].apply(lambda x: formatar_moeda(x, completo=True))

    nomes = {
        'GRUPO_ORIGEM': 'Grupo Origem',
        'NOME_FILIAL': 'Filial',
        'NOME_CLIENTE': 'Cliente',
        'GRUPO_DESTINO': 'Recebe De (Grupo)',
        'TIPO': 'Tipo',
        'EMISSAO': 'Emissao',
        'VENCIMENTO': 'Vencimento',
        'VALOR_ORIGINAL': 'Valor',
        'SALDO': 'Saldo',
        'STATUS': 'Status'
    }
    df_tab.columns = [nomes.get(c, c) for c in df_tab.columns]

    st.dataframe(df_tab, use_container_width=True, hide_index=True, height=450)
    st.caption(f"Exibindo {len(df_tab)} de {len(df_show)} registros")
