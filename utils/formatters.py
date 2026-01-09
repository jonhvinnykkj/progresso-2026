"""
Funções de formatação de valores
"""
import pandas as pd
import streamlit as st
from io import BytesIO


def formatar_moeda(valor, completo=False):
    """Formata valor em moeda brasileira"""
    if pd.isna(valor) or valor == 0:
        return "R$ 0"
    if completo:
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if abs(valor) >= 1_000_000_000:
        return f"R$ {valor/1_000_000_000:.2f}Bi"
    if abs(valor) >= 1_000_000:
        return f"R$ {valor/1_000_000:.1f}M"
    if abs(valor) >= 1_000:
        return f"R$ {valor/1_000:.0f}K"
    return f"R$ {valor:,.0f}".replace(",", ".")


def formatar_numero(valor):
    """Formata número com separador de milhar"""
    return f"{valor:,.0f}".replace(",", ".")


def calcular_variacao(atual, anterior):
    """Calcula variação percentual entre dois valores"""
    if anterior == 0:
        return 0
    return ((atual - anterior) / anterior) * 100


def formatar_delta(valor, inverso=False):
    """Formata delta com sinal. inverso=True quando menor é melhor"""
    if valor == 0:
        return "0%"
    sinal = "+" if valor > 0 else ""
    return f"{sinal}{valor:.1f}%"


def formatar_percentual(valor, decimais=1):
    """Formata valor como percentual"""
    return f"{valor:.{decimais}f}%"


def formatar_dias(valor):
    """Formata quantidade de dias"""
    if valor == 1:
        return "1 dia"
    return f"{valor:.0f} dias"


@st.cache_data
def to_excel(_df):
    """Converte DataFrame para Excel"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        _df.to_excel(writer, index=False, sheet_name='Dados')
    return output.getvalue()


@st.cache_data
def to_csv(_df):
    """Converte DataFrame para CSV"""
    return _df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
