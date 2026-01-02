"""
Funções auxiliares para manipulação de dados
Usadas por todas as abas para evitar duplicação de código
"""


def get_df_pendentes(df):
    """Retorna apenas títulos pendentes (saldo > 0)"""
    return df[df['SALDO'] > 0]


def get_df_vencidos(df):
    """Retorna apenas títulos vencidos"""
    return df[df['STATUS'] == 'Vencido']


def calcular_metricas_basicas(df):
    """Calcula métricas básicas para qualquer aba"""
    df_vencidos = get_df_vencidos(df)
    total = df['VALOR_ORIGINAL'].sum()
    pago = total - df['SALDO'].sum()
    pendente = df['SALDO'].sum()
    vencido = df_vencidos['SALDO'].sum()

    return {
        'total': total,
        'pago': pago,
        'pendente': pendente,
        'vencido': vencido,
        'pct_pago': (pago / total * 100) if total > 0 else 0,
        'dias_atraso': df_vencidos['DIAS_ATRASO'].mean() if len(df_vencidos) > 0 else 0,
        'qtd_total': len(df),
        'qtd_vencidos': len(df_vencidos)
    }
