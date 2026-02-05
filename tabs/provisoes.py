"""
Aba FAT / FT / PR - Faturamentos e Provisoes excluidos dos totalizadores - Contas a Pagar
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from config.theme import get_cores
from config.settings import GRUPOS_FILIAIS, get_grupo_filial
from components.charts import criar_layout
from utils.formatters import formatar_moeda, formatar_numero


def _get_nome_grupo(cod_filial):
    grupo_id = get_grupo_filial(int(cod_filial))
    return GRUPOS_FILIAIS.get(grupo_id, f"Grupo {grupo_id}")


def _detectar_multiplos_grupos(df):
    if 'FILIAL' not in df.columns or len(df) == 0:
        return False
    grupos = df['FILIAL'].dropna().apply(lambda x: get_grupo_filial(int(x))).nunique()
    return grupos > 1


def render_provisoes(df):
    """Renderiza a aba FAT/FT / PR"""
    cores = get_cores()

    st.markdown("##### FAT / FT / PR - Faturamentos e Provisoes")
    st.caption("Titulos dos tipos FAT, FT e PR sao excluidos dos totalizadores das demais abas para evitar duplicacao de valores.")

    if len(df) == 0:
        st.info("Nenhum titulo FAT, FT ou PR no periodo selecionado.")
        return

    # Filtro interno por tipo
    tipos_disp = sorted(df['TIPO'].str.strip().unique()) if 'TIPO' in df.columns else []
    tipo_sel = st.selectbox("Filtrar por tipo", ['Todos'] + tipos_disp, key='prov_tipo_filtro')

    if tipo_sel != 'Todos':
        df = df[df['TIPO'].str.strip() == tipo_sel]

    if len(df) == 0:
        st.info(f"Nenhum titulo {tipo_sel} no periodo.")
        return

    # Calcular vencidos
    hoje = datetime.now()
    df_vencidos = df[df['STATUS'] == 'Vencido'] if 'STATUS' in df.columns else pd.DataFrame()
    total_vencido = df_vencidos['SALDO'].sum() if len(df_vencidos) > 0 else 0
    qtd_vencido = len(df_vencidos)

    total_emitido = df['VALOR_ORIGINAL'].sum()
    total_pendente = df['SALDO'].sum()
    total_pago = max(total_emitido - total_pendente, 0)
    pct_pago = (total_pago / total_emitido * 100) if total_emitido > 0 else 0

    # ========== KPIs ==========
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Titulos", formatar_numero(len(df)))
    col2.metric("Emitido", formatar_moeda(total_emitido))
    col3.metric("Pago", formatar_moeda(total_pago), f"{pct_pago:.0f}%", delta_color="off")
    col4.metric("Pendente", formatar_moeda(total_pendente))
    col5.metric("Vencido", formatar_moeda(total_vencido), f"{qtd_vencido} titulos", delta_color="off")

    st.divider()

    # ========== TOP 10 FORNECEDORES (3 graficos) ==========
    _render_top_fornecedores(df, cores)

    st.divider()

    # ========== TOP 10 CATEGORIAS (3 graficos) ==========
    _render_por_categoria(df, cores)

    st.divider()

    # ========== FILIAL + VENCIDOS ==========
    col1, col2 = st.columns(2)

    with col1:
        _render_por_filial(df, cores)

    with col2:
        _render_vencidos(df_vencidos, cores)

    st.divider()

    # ========== EVOLUCAO MENSAL ==========
    _render_evolucao_mensal(df, cores)

    st.divider()

    # ========== TABELA DE DETALHES ==========
    _render_detalhes(df, cores)


def _render_top_fornecedores(df, cores):
    """Top 10 fornecedores - 3 graficos: emitido, pago, pendente"""
    st.markdown("##### Top 10 Fornecedores")

    if 'NOME_FORNECEDOR' not in df.columns or len(df) == 0:
        st.info("Sem dados de fornecedores")
        return

    df_forn = df.groupby('NOME_FORNECEDOR').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'NUMERO': 'count'
    }).reset_index()
    df_forn.columns = ['Fornecedor', 'Emitido', 'Pendente', 'Qtd']
    df_forn['Pago'] = (df_forn['Emitido'] - df_forn['Pendente']).clip(lower=0)

    if len(df_forn) == 0:
        st.info("Nenhum fornecedor encontrado.")
        return

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("###### Por Emitido")
        df_top = df_forn.nlargest(10, 'Emitido').sort_values('Emitido', ascending=True)

        fig = go.Figure(go.Bar(
            y=df_top['Fornecedor'].str[:25], x=df_top['Emitido'],
            orientation='h', marker_color=cores['info'],
            text=[formatar_moeda(v) for v in df_top['Emitido']],
            textposition='outside', textfont=dict(size=8)
        ))
        fig.update_layout(
            criar_layout(320),
            margin=dict(l=10, r=80, t=10, b=10),
            xaxis=dict(showticklabels=False, showgrid=False),
            yaxis=dict(tickfont=dict(size=9, color=cores['texto']))
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("###### Por Pago")
        df_top = df_forn[df_forn['Pago'] > 0].nlargest(10, 'Pago').sort_values('Pago', ascending=True)

        if len(df_top) > 0:
            fig = go.Figure(go.Bar(
                y=df_top['Fornecedor'].str[:25], x=df_top['Pago'],
                orientation='h', marker_color=cores['sucesso'],
                text=[formatar_moeda(v) for v in df_top['Pago']],
                textposition='outside', textfont=dict(size=8)
            ))
            fig.update_layout(
                criar_layout(320),
                margin=dict(l=10, r=80, t=10, b=10),
                xaxis=dict(showticklabels=False, showgrid=False),
                yaxis=dict(tickfont=dict(size=9, color=cores['texto']))
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhum pagamento.")

    with col3:
        st.markdown("###### Por Pendente")
        df_top = df_forn[df_forn['Pendente'] > 0].nlargest(10, 'Pendente').sort_values('Pendente', ascending=True)

        if len(df_top) > 0:
            fig = go.Figure(go.Bar(
                y=df_top['Fornecedor'].str[:25], x=df_top['Pendente'],
                orientation='h', marker_color=cores['alerta'],
                text=[formatar_moeda(v) for v in df_top['Pendente']],
                textposition='outside', textfont=dict(size=8)
            ))
            fig.update_layout(
                criar_layout(320),
                margin=dict(l=10, r=80, t=10, b=10),
                xaxis=dict(showticklabels=False, showgrid=False),
                yaxis=dict(tickfont=dict(size=9, color=cores['texto']))
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.success("Sem pendencias!")


def _render_por_categoria(df, cores):
    """Top 10 categorias - 3 graficos: emitido, pago, pendente"""
    st.markdown("##### Top 10 Categorias")

    if 'DESCRICAO' not in df.columns or len(df) == 0:
        st.info("Sem dados de categoria")
        return

    df_cat = df.groupby('DESCRICAO').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'NUMERO': 'count'
    }).reset_index()
    df_cat.columns = ['Categoria', 'Emitido', 'Pendente', 'Qtd']
    df_cat['Pago'] = (df_cat['Emitido'] - df_cat['Pendente']).clip(lower=0)

    if len(df_cat) == 0:
        st.info("Nenhuma categoria encontrada.")
        return

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("###### Por Emitido")
        df_top = df_cat.nlargest(10, 'Emitido').sort_values('Emitido', ascending=True)

        fig = go.Figure(go.Bar(
            y=df_top['Categoria'].str[:25], x=df_top['Emitido'],
            orientation='h', marker_color=cores['info'],
            text=[formatar_moeda(v) for v in df_top['Emitido']],
            textposition='outside', textfont=dict(size=8)
        ))
        fig.update_layout(
            criar_layout(320),
            margin=dict(l=10, r=80, t=10, b=10),
            xaxis=dict(showticklabels=False, showgrid=False),
            yaxis=dict(tickfont=dict(size=9, color=cores['texto']))
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("###### Por Pago")
        df_top = df_cat[df_cat['Pago'] > 0].nlargest(10, 'Pago').sort_values('Pago', ascending=True)

        if len(df_top) > 0:
            fig = go.Figure(go.Bar(
                y=df_top['Categoria'].str[:25], x=df_top['Pago'],
                orientation='h', marker_color=cores['sucesso'],
                text=[formatar_moeda(v) for v in df_top['Pago']],
                textposition='outside', textfont=dict(size=8)
            ))
            fig.update_layout(
                criar_layout(320),
                margin=dict(l=10, r=80, t=10, b=10),
                xaxis=dict(showticklabels=False, showgrid=False),
                yaxis=dict(tickfont=dict(size=9, color=cores['texto']))
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhum pagamento.")

    with col3:
        st.markdown("###### Por Pendente")
        df_top = df_cat[df_cat['Pendente'] > 0].nlargest(10, 'Pendente').sort_values('Pendente', ascending=True)

        if len(df_top) > 0:
            fig = go.Figure(go.Bar(
                y=df_top['Categoria'].str[:25], x=df_top['Pendente'],
                orientation='h', marker_color=cores['alerta'],
                text=[formatar_moeda(v) for v in df_top['Pendente']],
                textposition='outside', textfont=dict(size=8)
            ))
            fig.update_layout(
                criar_layout(320),
                margin=dict(l=10, r=80, t=10, b=10),
                xaxis=dict(showticklabels=False, showgrid=False),
                yaxis=dict(tickfont=dict(size=9, color=cores['texto']))
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.success("Sem pendencias!")


def _render_por_filial(df, cores):
    """Distribuicao por filial/grupo - pago vs pendente"""

    if 'NOME_FILIAL' not in df.columns or len(df) == 0:
        st.info("Coluna de filial nao disponivel")
        return

    multiplos_grupos = _detectar_multiplos_grupos(df)

    if multiplos_grupos:
        st.markdown("###### Por Grupo")
        df_temp = df.copy()
        df_temp['_AGRUP'] = df_temp['FILIAL'].apply(_get_nome_grupo)
    else:
        st.markdown("###### Por Filial")
        df_temp = df.copy()
        if 'FILIAL' in df_temp.columns:
            df_temp['_AGRUP'] = df_temp['FILIAL'].astype(int).astype(str) + ' - ' + df_temp['NOME_FILIAL'].str.split(' - ').str[-1].str.strip()
        else:
            df_temp['_AGRUP'] = df_temp['NOME_FILIAL'].str.split(' - ').str[-1].str.strip()

    df_fil = df_temp.groupby('_AGRUP').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'NUMERO': 'count'
    }).reset_index()
    df_fil.columns = ['Filial', 'Emitido', 'Pendente', 'Qtd']
    df_fil['Pago'] = (df_fil['Emitido'] - df_fil['Pendente']).clip(lower=0)
    df_fil = df_fil.sort_values('Emitido', ascending=True)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=df_fil['Filial'].str[:20],
        x=df_fil['Pago'],
        orientation='h',
        name='Pago',
        marker_color=cores['sucesso'],
        text=[formatar_moeda(v) if v > 0 else '' for v in df_fil['Pago']],
        textposition='inside',
        textfont=dict(size=9, color='white')
    ))

    fig.add_trace(go.Bar(
        y=df_fil['Filial'].str[:20],
        x=df_fil['Pendente'],
        orientation='h',
        name='Pendente',
        marker_color=cores['perigo'],
        text=[formatar_moeda(v) if v > 0 else '' for v in df_fil['Pendente']],
        textposition='inside',
        textfont=dict(size=9, color='white')
    ))

    fig.update_layout(
        criar_layout(350),
        barmode='stack',
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(showticklabels=False, showgrid=False),
        yaxis=dict(tickfont=dict(size=9, color=cores['texto'])),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1,
                    font=dict(size=10, color=cores['texto']))
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_vencidos(df_vencidos, cores):
    """Maiores vencidos por fornecedor"""
    st.markdown("###### Maiores Vencidos por Fornecedor")

    if len(df_vencidos) == 0:
        st.success("Nenhum titulo vencido!")
        return

    nome_col = 'NOME_FORNECEDOR' if 'NOME_FORNECEDOR' in df_vencidos.columns else None
    if not nome_col:
        st.info("Sem dados")
        return

    df_forn = df_vencidos.groupby(nome_col).agg({
        'SALDO': 'sum',
        'NUMERO': 'count'
    }).reset_index()
    df_forn.columns = ['Fornecedor', 'Vencido', 'Qtd']

    # Dias de atraso medio
    if 'DIAS_ATRASO' in df_vencidos.columns:
        df_atraso = df_vencidos.groupby(nome_col)['DIAS_ATRASO'].mean().reset_index()
        df_atraso.columns = ['Fornecedor', 'Atraso_Medio']
        df_forn = df_forn.merge(df_atraso, on='Fornecedor', how='left')
    else:
        df_forn['Atraso_Medio'] = 0

    df_forn = df_forn.nlargest(10, 'Vencido').sort_values('Vencido', ascending=True)

    def cor_atraso(d):
        if d > 30:
            return cores['perigo']
        elif d > 15:
            return '#f97316'
        return cores['alerta']

    bar_colors = [cor_atraso(d) for d in df_forn['Atraso_Medio']]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=df_forn['Fornecedor'].str[:25],
        x=df_forn['Vencido'],
        orientation='h',
        marker_color=bar_colors,
        text=[f"{formatar_moeda(v)} ({int(a)}d)" for v, a in zip(df_forn['Vencido'], df_forn['Atraso_Medio'])],
        textposition='auto',
        textfont=dict(size=9, color='white')
    ))

    fig.update_layout(
        criar_layout(350),
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(showticklabels=False, showgrid=False),
        yaxis=dict(tickfont=dict(size=9, color=cores['texto'])),
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)
    st.caption("Cores: amarelo < 15d, laranja 15-30d, vermelho > 30d de atraso")


def _render_evolucao_mensal(df, cores):
    """Evolucao mensal - emitido vs pago vs pendente"""
    st.markdown("##### Evolucao Mensal")

    if 'EMISSAO' not in df.columns or len(df) == 0:
        st.info("Sem dados de emissao.")
        return

    df_temp = df.copy()
    df_temp['MES'] = df_temp['EMISSAO'].dt.to_period('M')

    meses_disp = sorted(df_temp['MES'].dropna().unique())
    if len(meses_disp) < 2:
        st.info("Dados insuficientes para evolucao mensal.")
        return

    ultimos = meses_disp[-12:]

    df_mes = df_temp[df_temp['MES'].isin(ultimos)].groupby('MES').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'NUMERO': 'count'
    }).reindex(ultimos, fill_value=0).reset_index()
    df_mes.columns = ['MES', 'Emitido', 'Pendente', 'Qtd']
    df_mes['Pago'] = (df_mes['Emitido'] - df_mes['Pendente']).clip(lower=0)
    df_mes['MES'] = df_mes['MES'].astype(str)

    col1, col2 = st.columns([2, 1])

    with col1:
        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=df_mes['MES'], y=df_mes['Emitido'],
            name='Emitido', marker_color=cores['info'], opacity=0.7
        ))
        fig.add_trace(go.Bar(
            x=df_mes['MES'], y=df_mes['Pago'],
            name='Pago', marker_color=cores['sucesso'], opacity=0.7
        ))
        fig.add_trace(go.Scatter(
            x=df_mes['MES'], y=df_mes['Pendente'],
            name='Pendente', mode='lines+markers',
            line=dict(color=cores['perigo'], width=2),
            marker=dict(size=6)
        ))

        fig.update_layout(
            criar_layout(300, barmode='group'),
            margin=dict(l=10, r=10, t=10, b=50),
            xaxis=dict(tickangle=-45, tickfont=dict(size=9, color=cores['texto'])),
            yaxis=dict(showticklabels=False, showgrid=False),
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1, font=dict(size=9))
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("###### Resumo por Tipo")
        if 'TIPO' in df.columns:
            df_tipo = df.groupby('TIPO').agg({
                'VALOR_ORIGINAL': 'sum',
                'SALDO': 'sum',
                'NUMERO': 'count'
            }).reset_index()
            df_tipo.columns = ['Tipo', 'Emitido', 'Pendente', 'Qtd']
            df_tipo['Pago'] = (df_tipo['Emitido'] - df_tipo['Pendente']).clip(lower=0)
            df_tipo['% Pago'] = (df_tipo['Pago'] / df_tipo['Emitido'] * 100).round(1)
            df_tipo = df_tipo.sort_values('Emitido', ascending=False)

            df_show = df_tipo.copy()
            df_show['Emitido'] = df_show['Emitido'].apply(lambda x: formatar_moeda(x, completo=True))
            df_show['Pago'] = df_show['Pago'].apply(lambda x: formatar_moeda(x, completo=True))
            df_show['Pendente'] = df_show['Pendente'].apply(lambda x: formatar_moeda(x, completo=True))
            df_show['% Pago'] = df_show['% Pago'].apply(lambda x: f"{x:.1f}%")
            df_show = df_show[['Tipo', 'Qtd', 'Emitido', 'Pago', 'Pendente', '% Pago']]

            st.dataframe(df_show, use_container_width=True, hide_index=True, height=200)
        else:
            st.info("Coluna TIPO nao disponivel.")


def _render_detalhes(df, cores):
    """Tabela de detalhes com filtros"""
    st.markdown("##### Detalhes")

    # Filtros da tabela
    col1, col2, col3 = st.columns(3)

    with col1:
        filtro_status = st.selectbox("Status", ['Todos', 'Vencido', 'Pendente', 'Pago'], key='prov_det_status')
    with col2:
        ordenar = st.selectbox("Ordenar por", ['Pendente', 'Valor Original', 'Vencimento'], key='prov_det_ordem')
    with col3:
        qtd_exibir = st.selectbox("Exibir", [20, 50, 100, 'Todos'], key='prov_det_qtd')

    df_filtrado = df.copy()

    if filtro_status == 'Vencido' and 'STATUS' in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado['STATUS'] == 'Vencido']
    elif filtro_status == 'Pendente':
        df_filtrado = df_filtrado[df_filtrado['SALDO'] > 0]
    elif filtro_status == 'Pago':
        df_filtrado = df_filtrado[df_filtrado['SALDO'] <= 0]

    if ordenar == 'Pendente':
        df_filtrado = df_filtrado.sort_values('SALDO', ascending=False)
    elif ordenar == 'Valor Original':
        df_filtrado = df_filtrado.sort_values('VALOR_ORIGINAL', ascending=False)
    elif ordenar == 'Vencimento' and 'VENCIMENTO' in df_filtrado.columns:
        df_filtrado = df_filtrado.sort_values('VENCIMENTO', ascending=True)

    if qtd_exibir != 'Todos':
        df_filtrado = df_filtrado.head(int(qtd_exibir))

    colunas = ['NOME_FORNECEDOR', 'NOME_FILIAL', 'TIPO', 'NUMERO', 'DESCRICAO',
               'EMISSAO', 'VENCIMENTO', 'VALOR_ORIGINAL', 'SALDO', 'STATUS']
    colunas_disp = [c for c in colunas if c in df_filtrado.columns]
    df_show = df_filtrado[colunas_disp].copy()

    if 'NOME_FORNECEDOR' in df_show.columns:
        df_show['NOME_FORNECEDOR'] = df_show['NOME_FORNECEDOR'].str[:30]
    if 'NOME_FILIAL' in df_show.columns:
        df_show['NOME_FILIAL'] = df_show['NOME_FILIAL'].str.split(' - ').str[-1].str.strip()
    if 'DESCRICAO' in df_show.columns:
        df_show['DESCRICAO'] = df_show['DESCRICAO'].str[:25]
    if 'EMISSAO' in df_show.columns:
        df_show['EMISSAO'] = pd.to_datetime(df_show['EMISSAO'], errors='coerce').dt.strftime('%d/%m/%Y')
    if 'VENCIMENTO' in df_show.columns:
        df_show['VENCIMENTO'] = pd.to_datetime(df_show['VENCIMENTO'], errors='coerce').dt.strftime('%d/%m/%Y')
    if 'NUMERO' in df_show.columns:
        df_show['NUMERO'] = df_show['NUMERO'].astype(str)
    df_show['VALOR_ORIGINAL'] = df_show['VALOR_ORIGINAL'].apply(lambda x: formatar_moeda(x, completo=True))
    df_show['SALDO'] = df_show['SALDO'].apply(lambda x: formatar_moeda(x, completo=True))

    nomes = {
        'NOME_FORNECEDOR': 'Fornecedor', 'NOME_FILIAL': 'Filial',
        'TIPO': 'Tipo', 'NUMERO': 'Numero Doc', 'DESCRICAO': 'Categoria',
        'EMISSAO': 'Emissao', 'VENCIMENTO': 'Vencimento',
        'VALOR_ORIGINAL': 'Valor Original', 'SALDO': 'Pendente', 'STATUS': 'Status'
    }
    df_show.columns = [nomes.get(c, c) for c in df_show.columns]

    st.dataframe(df_show, use_container_width=True, hide_index=True, height=400)
    st.caption(f"Exibindo {len(df_show)} de {len(df)} titulos")
