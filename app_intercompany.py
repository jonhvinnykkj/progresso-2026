# -*- coding: utf-8 -*-
"""
Dashboard Financeiro - Grupo Progresso
Operacoes Intercompany (Separado)
"""
import streamlit as st
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(
    page_title="Intercompany - Grupo Progresso",
    page_icon="GP",
    layout="wide",
    initial_sidebar_state="expanded"
)

from datetime import datetime
import pandas as pd

from config.theme import get_cores, get_css
from config.settings import INTERCOMPANY_PATTERNS
from data.loader import carregar_dados
from utils.formatters import formatar_moeda, formatar_numero, to_excel
from tabs.intercompany import identificar_intercompany, classificar_tipo_intercompany
import plotly.graph_objects as go
from components.charts import criar_layout


def main():
    if 'tema_escuro' not in st.session_state:
        st.session_state.tema_escuro = True

    cores = get_cores()
    st.markdown(get_css(), unsafe_allow_html=True)

    df_contas, df_adiant, df_baixas = carregar_dados()

    st.markdown(f"""
    <div class="header-gp">
        <div class="logo" style="background: {cores['alerta']};">IC</div>
        <div>
            <p class="titulo">Operacoes Intercompany</p>
            <p class="subtitulo">Analise de operacoes entre empresas do Grupo Progresso</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    df_ic = identificar_intercompany(df_contas)

    if len(df_ic) == 0:
        st.warning("Nenhuma operacao intercompany encontrada.")
        return

    df_ic['TIPO_INTERCOMPANY'] = df_ic['NOME_FORNECEDOR'].apply(classificar_tipo_intercompany)

    with st.sidebar:
        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 1rem;">
            <div style="background: {cores['alerta']}; width: 40px; height: 40px;
                        border-radius: 10px; display: flex; align-items: center;
                        justify-content: center; color: white; font-weight: 700;">IC</div>
            <div>
                <div style="color: {cores['texto']}; font-weight: 600;">Grupo Progresso</div>
                <div style="color: {cores['texto_secundario']}; font-size: 0.7rem;">Intercompany</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()
        st.markdown(f"<p style='color: {cores['texto']}; font-size: 0.8rem; font-weight: 600;'>Filtros</p>", unsafe_allow_html=True)

        tipos = ['Todos'] + sorted(df_ic['TIPO_INTERCOMPANY'].unique().tolist())
        filtro_tipo = st.selectbox("Tipo de Operacao", tipos, key="ic_tipo_sep")

        filiais = ['Todas'] + sorted(df_ic['NOME_FILIAL'].dropna().unique().tolist())
        filtro_filial = st.selectbox("Filial", filiais, key="ic_filial_sep")

        filtro_status = st.selectbox("Status", ['Todos', 'Pendente', 'Pago', 'Vencido'], key="ic_status_sep")

        anos = sorted(df_ic['EMISSAO'].dt.year.dropna().unique().tolist(), reverse=True)
        filtro_ano = st.selectbox("Ano", ['Todos'] + [str(a) for a in anos], key="ic_ano_sep")

        st.divider()
        st.markdown(f"<p style='color: {cores['texto']}; font-size: 0.8rem; font-weight: 600;'>Resumo Geral</p>", unsafe_allow_html=True)

        total_ic = df_ic['VALOR_ORIGINAL'].sum()
        saldo_ic = df_ic['SALDO'].sum()

        st.markdown(f"""
        <div style="background: {cores['card']}; border: 1px solid {cores['borda']};
                    border-radius: 8px; padding: 0.75rem; font-size: 0.8rem;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.4rem;">
                <span style="color: {cores['texto_secundario']};">Total</span>
                <span style="color: {cores['texto']}; font-weight: 600;">{formatar_moeda(total_ic)}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.4rem;">
                <span style="color: {cores['texto_secundario']};">Saldo</span>
                <span style="color: {cores['alerta']}; font-weight: 600;">{formatar_moeda(saldo_ic)}</span>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <span style="color: {cores['texto_secundario']};">Titulos</span>
                <span style="color: {cores['texto']}; font-weight: 600;">{formatar_numero(len(df_ic))}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    df_filtrado = df_ic.copy()

    if filtro_tipo != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['TIPO_INTERCOMPANY'] == filtro_tipo]

    if filtro_filial != 'Todas':
        df_filtrado = df_filtrado[df_filtrado['NOME_FILIAL'] == filtro_filial]

    if filtro_status == 'Pendente':
        df_filtrado = df_filtrado[df_filtrado['SALDO'] > 0]
    elif filtro_status == 'Pago':
        df_filtrado = df_filtrado[df_filtrado['SALDO'] == 0]
    elif filtro_status == 'Vencido':
        df_filtrado = df_filtrado[df_filtrado['STATUS'] == 'Vencido']

    if filtro_ano != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['EMISSAO'].dt.year == int(filtro_ano)]

    st.markdown("### Visao Geral")

    total_filtrado = df_filtrado['VALOR_ORIGINAL'].sum()
    saldo_filtrado = df_filtrado['SALDO'].sum()
    pago_filtrado = total_filtrado - saldo_filtrado
    qtd_filtrado = len(df_filtrado)
    vencidos = len(df_filtrado[df_filtrado['STATUS'] == 'Vencido'])

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total", formatar_moeda(total_filtrado))
    col2.metric("Pago", formatar_moeda(pago_filtrado))
    col3.metric("Saldo Pendente", formatar_moeda(saldo_filtrado))
    col4.metric("Titulos", formatar_numero(qtd_filtrado))
    col5.metric("Vencidos", formatar_numero(vencidos),
                delta="Atencao" if vencidos > 0 else "OK",
                delta_color="inverse" if vencidos > 0 else "off")

    st.markdown("---")

    tab1, tab2, tab3, tab4 = st.tabs(["Por Tipo", "Por Filial", "Evolucao", "Detalhes"])

    with tab1:
        _render_por_tipo(df_filtrado, cores)

    with tab2:
        _render_por_filial(df_filtrado, cores)

    with tab3:
        _render_evolucao(df_filtrado, cores)

    with tab4:
        _render_detalhes(df_filtrado, cores)

    hoje = datetime.now()
    st.divider()
    st.caption(f"Grupo Progresso - Dashboard Intercompany | Atualizado em {hoje.strftime('%d/%m/%Y %H:%M')}")


def _render_por_tipo(df, cores):
    df_tipo = df.groupby('TIPO_INTERCOMPANY').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'FORNECEDOR': 'count'
    }).reset_index()
    df_tipo.columns = ['Tipo', 'Total', 'Saldo', 'Qtd']
    df_tipo['Pago'] = df_tipo['Total'] - df_tipo['Saldo']
    df_tipo = df_tipo.sort_values('Total', ascending=False)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Total por Tipo")
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df_tipo['Tipo'], y=df_tipo['Pago'], name='Pago',
                            marker_color=cores['sucesso'],
                            text=[formatar_moeda(v) for v in df_tipo['Pago']],
                            textposition='inside', textfont=dict(size=10, color='white')))
        fig.add_trace(go.Bar(x=df_tipo['Tipo'], y=df_tipo['Saldo'], name='Pendente',
                            marker_color=cores['alerta'],
                            text=[formatar_moeda(v) for v in df_tipo['Saldo']],
                            textposition='inside', textfont=dict(size=10, color='white')))
        fig.update_layout(criar_layout(350, barmode='stack'),
                         legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
                         margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("##### Distribuicao")
        cores_tipo = {
            'Empresas Progresso': cores['primaria'],
            'Ouro Branco': cores['sucesso'],
            'Fazenda Peninsula': '#84cc16',
            'Hotelaria': cores['info'],
            'Outros': cores['texto_secundario']
        }
        fig = go.Figure(data=[go.Pie(
            labels=df_tipo['Tipo'], values=df_tipo['Total'], hole=0.5,
            marker_colors=[cores_tipo.get(t, cores['info']) for t in df_tipo['Tipo']],
            textinfo='percent+label', textfont_size=11
        )])
        fig.update_layout(criar_layout(350), showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("##### Resumo por Tipo")
    df_exib = pd.DataFrame({
        'Tipo': df_tipo['Tipo'],
        'Total': df_tipo['Total'].apply(lambda x: formatar_moeda(x, completo=True)),
        'Pago': df_tipo['Pago'].apply(lambda x: formatar_moeda(x, completo=True)),
        'Saldo': df_tipo['Saldo'].apply(lambda x: formatar_moeda(x, completo=True)),
        'Qtd': df_tipo['Qtd']
    })
    st.dataframe(df_exib, use_container_width=True, hide_index=True)


def _render_por_filial(df, cores):
    df_filial = df.groupby('NOME_FILIAL').agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'FORNECEDOR': 'count'
    }).reset_index()
    df_filial.columns = ['Filial', 'Total', 'Saldo', 'Qtd']
    df_filial = df_filial.sort_values('Total', ascending=False)

    st.markdown("##### Por Filial")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_filial['Filial'], y=df_filial['Total'],
                        marker_color=cores['primaria'],
                        text=[formatar_moeda(v) for v in df_filial['Total']],
                        textposition='outside', textfont=dict(size=9)))
    fig.update_layout(criar_layout(350), xaxis_tickangle=-45, margin=dict(l=10, r=10, t=10, b=80))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("##### Matriz Filial x Tipo")
    df_matrix = df.pivot_table(index='NOME_FILIAL', columns='TIPO_INTERCOMPANY',
                               values='VALOR_ORIGINAL', aggfunc='sum', fill_value=0)
    df_matrix_exib = df_matrix.copy()
    for col in df_matrix_exib.columns:
        df_matrix_exib[col] = df_matrix_exib[col].apply(lambda x: formatar_moeda(x, completo=True) if x > 0 else '-')
    st.dataframe(df_matrix_exib, use_container_width=True)


def _render_evolucao(df, cores):
    df_temp = df.copy()
    df_temp['MES_ANO'] = df_temp['EMISSAO'].dt.to_period('M')

    df_mensal = df_temp.groupby('MES_ANO').agg({
        'VALOR_ORIGINAL': 'sum',
        'FORNECEDOR': 'count'
    }).reset_index()
    df_mensal['MES_ANO'] = df_mensal['MES_ANO'].astype(str)
    df_mensal.columns = ['Periodo', 'Total', 'Qtd']
    df_mensal = df_mensal.tail(24)

    st.markdown("##### Evolucao Mensal")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_mensal['Periodo'], y=df_mensal['Total'],
                        marker_color=cores['primaria'],
                        text=[formatar_moeda(v) for v in df_mensal['Total']],
                        textposition='outside', textfont=dict(size=8)))
    fig.update_layout(criar_layout(350), xaxis_tickangle=-45, margin=dict(l=10, r=10, t=10, b=60))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("##### Por Ano")
    df_ano = df_temp.groupby(df_temp['EMISSAO'].dt.year).agg({
        'VALOR_ORIGINAL': 'sum',
        'SALDO': 'sum',
        'FORNECEDOR': 'count'
    }).reset_index()
    df_ano.columns = ['Ano', 'Total', 'Saldo', 'Qtd']
    df_ano['Pago'] = df_ano['Total'] - df_ano['Saldo']

    df_ano_exib = pd.DataFrame({
        'Ano': df_ano['Ano'].astype(int),
        'Total': df_ano['Total'].apply(lambda x: formatar_moeda(x, completo=True)),
        'Pago': df_ano['Pago'].apply(lambda x: formatar_moeda(x, completo=True)),
        'Saldo': df_ano['Saldo'].apply(lambda x: formatar_moeda(x, completo=True)),
        'Qtd': df_ano['Qtd']
    })
    st.dataframe(df_ano_exib, use_container_width=True, hide_index=True)


def _render_detalhes(df, cores):
    col1, col2, col3 = st.columns(3)

    with col1:
        ordem = st.selectbox("Ordenar por", ["Maior Valor", "Mais Recente", "Fornecedor A-Z"], key="ic_det_ordem")

    with col2:
        limite = st.selectbox("Exibir", ["50 primeiros", "100 primeiros", "Todos"], key="ic_det_limite")

    with col3:
        st.download_button(
            label="Exportar Excel",
            data=to_excel(df),
            file_name=f"intercompany_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    df_show = df.copy()
    if ordem == "Maior Valor":
        df_show = df_show.sort_values('VALOR_ORIGINAL', ascending=False)
    elif ordem == "Mais Recente":
        df_show = df_show.sort_values('EMISSAO', ascending=False)
    else:
        df_show = df_show.sort_values('NOME_FORNECEDOR')

    if limite == "50 primeiros":
        df_show = df_show.head(50)
    elif limite == "100 primeiros":
        df_show = df_show.head(100)

    df_exib = df_show[[
        'NOME_FILIAL', 'NOME_FORNECEDOR', 'TIPO_INTERCOMPANY',
        'EMISSAO', 'VENCIMENTO', 'VALOR_ORIGINAL', 'SALDO', 'STATUS'
    ]].copy()

    df_exib['EMISSAO'] = pd.to_datetime(df_exib['EMISSAO']).dt.strftime('%d/%m/%Y')
    df_exib['VENCIMENTO'] = pd.to_datetime(df_exib['VENCIMENTO']).dt.strftime('%d/%m/%Y')
    df_exib['VALOR_ORIGINAL'] = df_exib['VALOR_ORIGINAL'].apply(lambda x: formatar_moeda(x, completo=True))
    df_exib['SALDO'] = df_exib['SALDO'].apply(lambda x: formatar_moeda(x, completo=True))

    df_exib.columns = ['Filial', 'Fornecedor', 'Tipo', 'Emissao', 'Vencimento', 'Valor', 'Saldo', 'Status']

    st.dataframe(df_exib, use_container_width=True, hide_index=True, height=500)
    st.caption(f"Exibindo {len(df_exib)} de {len(df)} registros")


if __name__ == "__main__":
    main()
