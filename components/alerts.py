"""
Componente de Alertas e Notificações
"""
import streamlit as st
from config.theme import get_cores
from utils.formatters import formatar_moeda


def render_alerts(df_pendentes, df_vencidos, metricas):
    """Renderiza alertas e notificações críticas"""
    cores = get_cores()

    qtd_vencidos = metricas['qtd_vencidos']
    vencido = metricas['vencido']
    valor_vence_7d = df_pendentes[df_pendentes['STATUS'] == 'Vence em 7 dias']['SALDO'].sum()

    # Notificações críticas
    if qtd_vencidos > 0 or valor_vence_7d > 100000:
        with st.container():
            cols = st.columns([0.02, 0.98])
            with cols[1]:
                if qtd_vencidos > 0:
                    st.warning(f"⚠️ Atenção: {qtd_vencidos} títulos vencidos totalizando {formatar_moeda(vencido, completo=True)}")
                if valor_vence_7d > 100000:
                    st.info(f"📅 Próximos 7 dias: {formatar_moeda(valor_vence_7d, completo=True)} a vencer")


def render_alert_cards(df_pendentes):
    """Renderiza os cards de alerta por status de vencimento"""
    cores = get_cores()

    col1, col2, col3, col4 = st.columns(4)

    alertas = [
        ('Vencido', 'vermelho', df_pendentes[df_pendentes['STATUS'] == 'Vencido']),
        ('Vence em 7 dias', 'laranja', df_pendentes[df_pendentes['STATUS'] == 'Vence em 7 dias']),
        ('Vence em 15 dias', 'azul', df_pendentes[df_pendentes['STATUS'] == 'Vence em 15 dias']),
        ('Vence em 30 dias', 'verde', df_pendentes[df_pendentes['STATUS'] == 'Vence em 30 dias'])
    ]

    for col, (label, cor, dados) in zip([col1, col2, col3, col4], alertas):
        valor = dados['SALDO'].sum()
        qtd = len(dados)
        with col:
            st.markdown(f"""
            <div class="alerta-card alerta-{cor}">
                <div class="valor">{formatar_moeda(valor)}</div>
                <div class="label">{label} ({qtd} títulos)</div>
            </div>
            """, unsafe_allow_html=True)


def render_resumo_executivo(df, df_pendentes, df_vencidos, metricas):
    """Renderiza um resumo executivo em texto"""
    cores = get_cores()

    # Calcular informações relevantes
    total_vencido = metricas['vencido']
    qtd_vencidos = metricas['qtd_vencidos']
    valor_7d = df_pendentes[df_pendentes['STATUS'] == 'Vence em 7 dias']['SALDO'].sum()

    # Top categoria
    if len(df) > 0:
        top_cat = df.groupby('DESCRICAO')['VALOR_ORIGINAL'].sum().idxmax()
        pct_top_cat = df.groupby('DESCRICAO')['VALOR_ORIGINAL'].sum().max() / df['VALOR_ORIGINAL'].sum() * 100
    else:
        top_cat = "N/A"
        pct_top_cat = 0

    # Construir texto
    resumo_parts = []

    if qtd_vencidos > 0:
        resumo_parts.append(f"<span style='color:{cores['perigo']}'>Você tem {formatar_moeda(total_vencido)} vencidos ({qtd_vencidos} títulos)</span>")

    if valor_7d > 0:
        resumo_parts.append(f"Nos próximos 7 dias vencem <span style='color:{cores['alerta']}'>{formatar_moeda(valor_7d)}</span>")

    if top_cat != "N/A":
        resumo_parts.append(f"A categoria <strong>{top_cat}</strong> representa {pct_top_cat:.1f}% do total")

    if resumo_parts:
        resumo_texto = ". ".join(resumo_parts) + "."
    else:
        resumo_texto = "Não há pendências críticas no momento."

    st.markdown(f"""
    <div style="background: {cores['card']}; border-radius: 12px; padding: 1rem 1.5rem;
                border: 1px solid {cores['borda']}; margin-bottom: 1rem;">
        <p style="color: {cores['texto_secundario']}; font-size: 0.75rem; margin: 0 0 0.5rem;
                  text-transform: uppercase; letter-spacing: 1px;">📊 Resumo Executivo</p>
        <p style="color: {cores['texto']}; font-size: 0.95rem; margin: 0; line-height: 1.5;">
            {resumo_texto}
        </p>
    </div>
    """, unsafe_allow_html=True)
