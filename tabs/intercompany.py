"""
Aba Intercompany - Análise de operações entre empresas do grupo
- Progresso Agrícola <-> Progresso Agroindustrial
- Brasil Agricola LTDA
- Família Sanders (PF): Cornelio, Greicy, Gregory, Gueberson
- Fazendas do Grupo: Ouro Branco, Imperial
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from config.theme import get_cores
from config.settings import INTERCOMPANY_PATTERNS, INTERCOMPANY_TIPOS
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero


def identificar_intercompany(df):
    """Identifica operações intercompany no dataframe"""
    mask = df['NOME_FORNECEDOR'].str.upper().str.contains('|'.join(INTERCOMPANY_PATTERNS), na=False, regex=True)
    return df[mask].copy()


def classificar_tipo_intercompany(nome):
    """Classifica o tipo de operação intercompany usando config centralizada"""
    nome_upper = str(nome).upper()
    for padrao, tipo in INTERCOMPANY_TIPOS.items():
        if padrao in nome_upper:
            return tipo
    return 'Outros'


def render_intercompany(df_contas):
    """Renderiza a aba de operações Intercompany"""
    cores = get_cores()
    hoje = datetime.now()

    st.markdown("### Operações Intercompany")
    st.caption("Análise de operações entre empresas do Grupo Progresso, Família Sanders e fazendas relacionadas")

    # Identificar operações intercompany
    df_ic = identificar_intercompany(df_contas)

    if len(df_ic) == 0:
        st.warning("Nenhuma operação intercompany encontrada no período selecionado.")
        return

    # Classificar tipo
    df_ic['TIPO_INTERCOMPANY'] = df_ic['NOME_FORNECEDOR'].apply(classificar_tipo_intercompany)

    # ========== RESUMO GERAL ==========
    st.markdown("#### Resumo Geral")

    total_ic = df_ic['VALOR_ORIGINAL'].sum()
    total_geral = df_contas['VALOR_ORIGINAL'].sum()
    pct_ic = (total_ic / total_geral * 100) if total_geral > 0 else 0

    saldo_ic = df_ic['SALDO'].sum()
    pago_ic = total_ic - saldo_ic

    qtd_ic = len(df_ic)
    qtd_total = len(df_contas)

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric(
        "Total Intercompany",
        formatar_moeda(total_ic),
        delta=f"{pct_ic:.1f}% do total",
        help="Soma de todas as operações entre empresas do grupo"
    )

    col2.metric(
        "Pago",
        formatar_moeda(pago_ic),
        help="Valor já liquidado"
    )

    col3.metric(
        "Saldo Pendente",
        formatar_moeda(saldo_ic),
        delta_color="inverse" if saldo_ic > 0 else "normal"
    )

    col4.metric(
        "Títulos",
        formatar_numero(qtd_ic),
        delta=f"{(qtd_ic/qtd_total*100):.1f}% do total" if qtd_total > 0 else "0%"
    )

    vencidos_ic = len(df_ic[df_ic['STATUS'] == 'Vencido'])
    col5.metric(
        "Vencidos",
        formatar_numero(vencidos_ic),
        delta="Atenção" if vencidos_ic > 0 else "OK",
        delta_color="inverse" if vencidos_ic > 0 else "off"
    )

    st.markdown("---")

    # ========== ANÁLISE POR TIPO ==========
    st.markdown("#### Análise por Tipo de Operação")

    df_tipo = df_ic.groupby('TIPO_INTERCOMPANY').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'FORNECEDOR': 'count'
    }).reset_index()
    df_tipo.columns = ['Tipo', 'Total', 'Saldo', 'Qtd']
    df_tipo['Pago'] = df_tipo['Total'] - df_tipo['Saldo']
    df_tipo['% Pago'] = ((df_tipo['Pago'] / df_tipo['Total']) * 100).round(1)
    df_tipo = df_tipo.sort_values('Total', ascending=False)

    col1, col2 = st.columns([2, 1])

    with col1:
        # Gráfico de barras empilhadas
        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=df_tipo['Tipo'],
            y=df_tipo['Pago'],
            name='Pago',
            marker_color=cores['sucesso'],
            text=[formatar_moeda(v) for v in df_tipo['Pago']],
            textposition='inside',
            textfont=dict(size=10, color='white')
        ))

        fig.add_trace(go.Bar(
            x=df_tipo['Tipo'],
            y=df_tipo['Saldo'],
            name='Pendente',
            marker_color=cores['alerta'],
            text=[formatar_moeda(v) for v in df_tipo['Saldo']],
            textposition='inside',
            textfont=dict(size=10, color='white')
        ))

        fig.update_layout(
            criar_layout(350, barmode='stack'),
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
            margin=dict(l=10, r=10, t=40, b=10)
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Cards de resumo
        for _, row in df_tipo.iterrows():
            tipo = row['Tipo']
            total = row['Total']
            pct_pago = row['% Pago']

            if 'Agroindustrial' in tipo:
                icone = "🏭"
                cor = cores['primaria']
            elif 'Agricola' in tipo:
                icone = "🌾"
                cor = cores['sucesso']
            elif 'Empresas do Grupo' in tipo:
                icone = "🏢"
                cor = cores['info']
            elif 'Familia Sanders' in tipo:
                icone = "👤"
                cor = cores['alerta']
            elif 'Fazendas' in tipo:
                icone = "🌿"
                cor = '#84cc16'
            else:
                icone = "📋"
                cor = cores['texto_secundario']

            st.markdown(f"""
            <div style="background: {cores['card']}; border-left: 4px solid {cor};
                        padding: 12px; border-radius: 8px; margin-bottom: 10px;">
                <div style="font-size: 1.1rem; font-weight: 600; color: {cores['texto']};">
                    {icone} {tipo}
                </div>
                <div style="font-size: 0.85rem; color: {cores['texto_secundario']}; margin-top: 5px;">
                    Total: {formatar_moeda(total)} | {pct_pago:.0f}% pago
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # ========== TABS DETALHADAS ==========
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Visão por Empresa",
        "📅 Evolução Temporal",
        "🏢 Por Filial",
        "📋 Detalhes"
    ])

    with tab1:
        _render_por_empresa(df_ic, cores)

    with tab2:
        _render_evolucao_temporal(df_ic, cores)

    with tab3:
        _render_por_filial_ic(df_ic, cores)

    with tab4:
        _render_detalhes_ic(df_ic, cores, hoje)


def _render_por_empresa(df_ic, cores):
    """Análise detalhada por empresa"""

    # Agrupar por fornecedor
    df_emp = df_ic.groupby(['NOME_FORNECEDOR', 'TIPO_INTERCOMPANY']).agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'FORNECEDOR': 'count'
    }).reset_index()
    df_emp.columns = ['Fornecedor', 'Tipo', 'Total', 'Saldo', 'Qtd']
    df_emp['Pago'] = df_emp['Total'] - df_emp['Saldo']
    df_emp['% Pago'] = ((df_emp['Pago'] / df_emp['Total']) * 100).fillna(0).round(1)
    df_emp = df_emp.sort_values('Total', ascending=False)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Top 10 por Valor")

        df_top = df_emp.head(10)

        def get_cor_tipo(t):
            if 'Agroindustrial' in t:
                return cores['primaria']
            elif 'Agricola' in t:
                return cores['sucesso']
            elif 'Empresas do Grupo' in t:
                return cores['info']
            elif 'Familia Sanders' in t:
                return cores['alerta']
            elif 'Fazendas' in t:
                return '#84cc16'
            return cores['texto_secundario']

        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=df_top['Fornecedor'].str[:30],
            x=df_top['Total'],
            orientation='h',
            marker_color=[get_cor_tipo(t) for t in df_top['Tipo']],
            text=[formatar_moeda(v) for v in df_top['Total']],
            textposition='outside',
            textfont=dict(size=9)
        ))

        fig.update_layout(
            criar_layout(350),
            yaxis={'autorange': 'reversed'},
            margin=dict(l=10, r=70, t=10, b=10)
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("##### Distribuição por Tipo")

        df_tipo = df_ic.groupby('TIPO_INTERCOMPANY')['VALOR_ORIGINAL'].sum().reset_index()

        cores_tipo = {
            'Progresso Agroindustrial': cores['primaria'],
            'Progresso Agricola': cores['sucesso'],
            'Empresas do Grupo': cores['info'],
            'Familia Sanders (PF)': cores['alerta'],
            'Fazendas do Grupo': '#84cc16',
            'Outros': cores['texto_secundario']
        }

        fig = go.Figure(data=[go.Pie(
            labels=df_tipo['TIPO_INTERCOMPANY'],
            values=df_tipo['VALOR_ORIGINAL'],
            hole=0.5,
            marker_colors=[cores_tipo.get(t, cores['info']) for t in df_tipo['TIPO_INTERCOMPANY']],
            textinfo='percent+label',
            textfont_size=11
        )])

        fig.update_layout(
            criar_layout(350),
            showlegend=False,
            margin=dict(l=10, r=10, t=10, b=10)
        )

        st.plotly_chart(fig, use_container_width=True)

    # Tabela completa
    st.markdown("##### Tabela Completa")

    df_exib = pd.DataFrame({
        'Fornecedor': df_emp['Fornecedor'],
        'Tipo': df_emp['Tipo'],
        'Total': df_emp['Total'].apply(lambda x: formatar_moeda(x, completo=True)),
        'Pago': df_emp['Pago'].apply(lambda x: formatar_moeda(x, completo=True)),
        'Saldo': df_emp['Saldo'].apply(lambda x: formatar_moeda(x, completo=True)),
        'Qtd': df_emp['Qtd'],
        '% Pago': df_emp['% Pago']
    })

    st.dataframe(
        df_exib,
        use_container_width=True,
        hide_index=True,
        height=350,
        column_config={
            '% Pago': st.column_config.ProgressColumn(
                '% Pago',
                format='%.0f%%',
                min_value=0,
                max_value=100
            )
        }
    )


def _render_evolucao_temporal(df_ic, cores):
    """Evolução temporal das operações intercompany"""

    df_temp = df_ic.copy()
    df_temp['MES_ANO'] = df_temp['EMISSAO'].dt.to_period('M')

    df_mensal = df_temp.groupby(['MES_ANO', 'TIPO_INTERCOMPANY']).agg({
        'VALOR_ORIGINAL': 'sum'
    }).reset_index()
    df_mensal['MES_ANO'] = df_mensal['MES_ANO'].astype(str)

    # Últimos 12 meses
    meses_unicos = sorted(df_mensal['MES_ANO'].unique())[-12:]
    df_mensal = df_mensal[df_mensal['MES_ANO'].isin(meses_unicos)]

    st.markdown("##### Evolução Mensal por Tipo")

    cores_tipo = {
        'Progresso Agroindustrial': cores['primaria'],
        'Progresso Agricola': cores['sucesso'],
        'Empresas do Grupo': cores['info'],
        'Familia Sanders (PF)': cores['alerta'],
        'Fazendas do Grupo': '#84cc16',
        'Outros': cores['texto_secundario']
    }

    fig = go.Figure()

    for tipo in df_mensal['TIPO_INTERCOMPANY'].unique():
        df_t = df_mensal[df_mensal['TIPO_INTERCOMPANY'] == tipo]
        fig.add_trace(go.Scatter(
            x=df_t['MES_ANO'],
            y=df_t['VALOR_ORIGINAL'],
            mode='lines+markers',
            name=tipo,
            line=dict(color=cores_tipo.get(tipo, cores['info']), width=2),
            marker=dict(size=8)
        ))

    fig.update_layout(
        criar_layout(350),
        xaxis_tickangle=-45,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
        margin=dict(l=10, r=10, t=40, b=60)
    )

    st.plotly_chart(fig, use_container_width=True)

    # Evolução acumulada
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Total Mensal Consolidado")

        df_total = df_temp.groupby('MES_ANO')['VALOR_ORIGINAL'].sum().reset_index()
        df_total['MES_ANO'] = df_total['MES_ANO'].astype(str)
        df_total = df_total[df_total['MES_ANO'].isin(meses_unicos)]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_total['MES_ANO'],
            y=df_total['VALOR_ORIGINAL'],
            marker_color=cores['primaria'],
            text=[formatar_moeda(v) for v in df_total['VALOR_ORIGINAL']],
            textposition='outside',
            textfont=dict(size=8)
        ))

        fig.update_layout(
            criar_layout(280),
            xaxis_tickangle=-45,
            margin=dict(l=10, r=10, t=10, b=60)
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("##### Resumo por Ano")

        df_ano = df_temp.groupby(df_temp['EMISSAO'].dt.year).agg({
            'VALOR_ORIGINAL': 'sum',
            'FORNECEDOR': 'count'
        }).reset_index()
        df_ano.columns = ['Ano', 'Total', 'Qtd']

        df_ano_exib = pd.DataFrame({
            'Ano': df_ano['Ano'].astype(int),
            'Total': df_ano['Total'].apply(lambda x: formatar_moeda(x, completo=True)),
            'Qtd Títulos': df_ano['Qtd']
        })

        st.dataframe(df_ano_exib, use_container_width=True, hide_index=True)


def _render_por_filial_ic(df_ic, cores):
    """Análise por filial das operações intercompany"""

    df_filial = df_ic.groupby('NOME_FILIAL').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'FORNECEDOR': 'count'
    }).reset_index()
    df_filial.columns = ['Filial', 'Total', 'Saldo', 'Qtd']
    df_filial['Pago'] = df_filial['Total'] - df_filial['Saldo']
    df_filial = df_filial.sort_values('Total', ascending=False)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Total por Filial")

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_filial['Filial'],
            y=df_filial['Total'],
            marker_color=cores['primaria'],
            text=[formatar_moeda(v) for v in df_filial['Total']],
            textposition='outside',
            textfont=dict(size=9)
        ))

        fig.update_layout(
            criar_layout(300),
            xaxis_tickangle=-45,
            margin=dict(l=10, r=10, t=10, b=80)
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("##### Status por Filial")

        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=df_filial['Filial'],
            y=df_filial['Pago'],
            name='Pago',
            marker_color=cores['sucesso']
        ))

        fig.add_trace(go.Bar(
            x=df_filial['Filial'],
            y=df_filial['Saldo'],
            name='Pendente',
            marker_color=cores['alerta']
        ))

        fig.update_layout(
            criar_layout(300, barmode='stack'),
            xaxis_tickangle=-45,
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
            margin=dict(l=10, r=10, t=40, b=80)
        )

        st.plotly_chart(fig, use_container_width=True)

    # Matriz Filial x Tipo
    st.markdown("##### Matriz Filial x Tipo de Operação")

    df_matrix = df_ic.pivot_table(
        index='NOME_FILIAL',
        columns='TIPO_INTERCOMPANY',
        values='VALOR_ORIGINAL',
        aggfunc='sum',
        fill_value=0
    )

    df_matrix_exib = df_matrix.copy()
    for col in df_matrix_exib.columns:
        df_matrix_exib[col] = df_matrix_exib[col].apply(lambda x: formatar_moeda(x, completo=True) if x > 0 else '-')

    st.dataframe(df_matrix_exib, use_container_width=True)


def _render_detalhes_ic(df_ic, cores, hoje):
    """Detalhes das operações intercompany"""

    # Filtros
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        tipos = ['Todos'] + sorted(df_ic['TIPO_INTERCOMPANY'].unique().tolist())
        filtro_tipo = st.selectbox("Tipo", tipos, key="ic_det_tipo")

    with col2:
        filiais = ['Todas'] + sorted(df_ic['NOME_FILIAL'].dropna().unique().tolist())
        filtro_filial = st.selectbox("Filial", filiais, key="ic_det_filial")

    with col3:
        status_opcoes = ['Todos', 'Pendente', 'Pago', 'Vencido']
        filtro_status = st.selectbox("Status", status_opcoes, key="ic_det_status")

    with col4:
        ordem = st.selectbox("Ordenar", ["Maior Valor", "Mais Recente", "Fornecedor A-Z"], key="ic_det_ordem")

    # Aplicar filtros
    df_show = df_ic.copy()

    if filtro_tipo != 'Todos':
        df_show = df_show[df_show['TIPO_INTERCOMPANY'] == filtro_tipo]

    if filtro_filial != 'Todas':
        df_show = df_show[df_show['NOME_FILIAL'] == filtro_filial]

    if filtro_status == 'Pendente':
        df_show = df_show[df_show['SALDO'] > 0]
    elif filtro_status == 'Pago':
        df_show = df_show[df_show['SALDO'] == 0]
    elif filtro_status == 'Vencido':
        df_show = df_show[df_show['STATUS'] == 'Vencido']

    # Ordenar
    if ordem == "Maior Valor":
        df_show = df_show.sort_values('VALOR_ORIGINAL', ascending=False)
    elif ordem == "Mais Recente":
        df_show = df_show.sort_values('EMISSAO', ascending=False)
    else:
        df_show = df_show.sort_values('NOME_FORNECEDOR')

    # Métricas do filtro
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Títulos", formatar_numero(len(df_show)))
    col2.metric("Total", formatar_moeda(df_show['VALOR_ORIGINAL'].sum()))
    col3.metric("Saldo", formatar_moeda(df_show['SALDO'].sum()))
    col4.metric("Vencidos", formatar_numero(len(df_show[df_show['STATUS'] == 'Vencido'])))

    st.markdown("---")

    # Tabela
    df_exib = df_show[[
        'NOME_FILIAL', 'NOME_FORNECEDOR', 'TIPO_INTERCOMPANY',
        'EMISSAO', 'VENCIMENTO', 'VALOR_ORIGINAL', 'SALDO', 'STATUS'
    ]].head(100).copy()

    df_exib['EMISSAO'] = pd.to_datetime(df_exib['EMISSAO']).dt.strftime('%d/%m/%Y')
    df_exib['VENCIMENTO'] = pd.to_datetime(df_exib['VENCIMENTO']).dt.strftime('%d/%m/%Y')
    df_exib['VALOR_ORIGINAL'] = df_exib['VALOR_ORIGINAL'].apply(lambda x: formatar_moeda(x, completo=True))
    df_exib['SALDO'] = df_exib['SALDO'].apply(lambda x: formatar_moeda(x, completo=True))

    df_exib.columns = ['Filial', 'Fornecedor', 'Tipo', 'Emissão', 'Vencimento', 'Valor', 'Saldo', 'Status']

    st.dataframe(df_exib, use_container_width=True, hide_index=True, height=450)
    st.caption(f"Exibindo {len(df_exib)} de {len(df_show)} registros")
