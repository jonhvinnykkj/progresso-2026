"""
Componentes de gráficos reutilizáveis
"""
import plotly.express as px
import plotly.graph_objects as go
from config.theme import get_cores, get_sequencia_cores


def criar_layout(height=350, **kwargs):
    """Cria layout padrão para gráficos Plotly"""
    cores = get_cores()

    layout = {
        'height': height,
        'margin': {'l': 40, 'r': 40, 't': 40, 'b': 40},
        'paper_bgcolor': 'rgba(0,0,0,0)',
        'plot_bgcolor': 'rgba(0,0,0,0)',
        'font': {'color': cores['texto'], 'family': 'DM Sans'},
        'legend': {
            'bgcolor': 'rgba(0,0,0,0)',
            'font': {'color': cores['texto']},
            'orientation': 'h',
            'yanchor': 'bottom',
            'y': 1.02,
            'xanchor': 'right',
            'x': 1
        },
        'xaxis': {
            'gridcolor': cores['borda'],
            'tickfont': {'color': cores['texto_secundario']},
            'showgrid': True,
            'gridwidth': 1
        },
        'yaxis': {
            'gridcolor': cores['borda'],
            'tickfont': {'color': cores['texto_secundario']},
            'showgrid': True,
            'gridwidth': 1
        }
    }
    layout.update(kwargs)
    return layout


def grafico_pizza(df, values, names, title=None, hole=0.5, height=320):
    """Cria gráfico de pizza/donut"""
    cores = get_cores()
    seq_cores = get_sequencia_cores()

    fig = px.pie(
        df, values=values, names=names, hole=hole,
        color_discrete_sequence=seq_cores
    )
    fig.update_traces(
        textposition='outside',
        textinfo='percent+label',
        textfont_size=11,
        pull=[0.02] * len(df)
    )
    fig.update_layout(criar_layout(height), showlegend=False)

    return fig


def grafico_barras(df, x, y, orientation='v', color=None, title=None, height=350,
                   text=None, textposition='outside', show_values=True):
    """Cria gráfico de barras"""
    cores = get_cores()

    if color is None:
        color = cores['primaria']

    fig = go.Figure(go.Bar(
        x=df[x] if orientation == 'v' else df[y],
        y=df[y] if orientation == 'v' else df[x],
        orientation='h' if orientation == 'h' else 'v',
        marker_color=color,
        text=text,
        textposition=textposition if show_values else 'none',
        textfont_size=10
    ))

    layout_opts = {}
    if orientation == 'h':
        layout_opts['yaxis'] = {'autorange': 'reversed'}

    fig.update_layout(criar_layout(height, **layout_opts))

    return fig


def grafico_barras_empilhadas(df, x, y_cols, names, colors=None, height=380):
    """Cria gráfico de barras empilhadas"""
    cores = get_cores()

    if colors is None:
        colors = [cores['primaria'], cores['alerta']]

    fig = go.Figure()

    for i, (y_col, name) in enumerate(zip(y_cols, names)):
        fig.add_trace(go.Bar(
            x=df[x],
            y=df[y_col],
            name=name,
            marker_color=colors[i % len(colors)]
        ))

    fig.update_layout(criar_layout(height, barmode='stack'))

    return fig


def grafico_linha(df, x, y, name=None, color=None, height=350, mode='lines+markers'):
    """Cria gráfico de linha"""
    cores = get_cores()

    if color is None:
        color = cores['primaria']

    fig = go.Figure(go.Scatter(
        x=df[x],
        y=df[y],
        mode=mode,
        name=name,
        line=dict(color=color, width=2),
        marker=dict(size=6)
    ))

    fig.update_layout(criar_layout(height))

    return fig


def grafico_combo_bar_line(df, x, y_bar, y_line, bar_name='Valor', line_name='Acumulado',
                           bar_color=None, line_color=None, height=350):
    """Cria gráfico combinado de barras e linha"""
    cores = get_cores()

    if bar_color is None:
        bar_color = cores['primaria']
    if line_color is None:
        line_color = cores['alerta']

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df[x],
        y=df[y_bar],
        name=bar_name,
        marker_color=bar_color
    ))

    fig.add_trace(go.Scatter(
        x=df[x],
        y=df[y_line],
        name=line_name,
        line=dict(color=line_color, width=3),
        yaxis='y2'
    ))

    fig.update_layout(criar_layout(height,
        yaxis2={'overlaying': 'y', 'side': 'right', 'showgrid': False}
    ))

    return fig


def grafico_heatmap(pivot_data, x_labels, y_labels, height=400):
    """Cria gráfico de heatmap"""
    cores = get_cores()

    fig = go.Figure(go.Heatmap(
        z=pivot_data,
        x=x_labels,
        y=y_labels,
        colorscale=[[0, cores['fundo']], [0.5, cores['alerta']], [1, cores['primaria']]],
        hovertemplate='%{y} %{x}<br>R$ %{z:,.0f}<extra></extra>'
    ))

    fig.update_layout(criar_layout(height))

    return fig


def grafico_treemap(df, path, values, color=None, height=400):
    """Cria gráfico treemap"""
    cores = get_cores()

    fig = px.treemap(
        df, path=path, values=values,
        color=color,
        color_continuous_scale='RdYlGn' if color else None
    )

    fig.update_layout(criar_layout(height))
    fig.update_traces(textinfo='label+value', texttemplate='%{label}<br>R$ %{value:,.0f}')

    return fig


def adicionar_linha_referencia(fig, y_value, text, line_dash="dash", yref='y2'):
    """Adiciona linha de referência horizontal ao gráfico"""
    cores = get_cores()

    fig.add_hline(
        y=y_value,
        line_dash=line_dash,
        line_color=cores['texto_secundario'],
        annotation_text=text,
        yref=yref
    )

    return fig


def adicionar_marcador_hoje(fig, data_hoje, ymax=None):
    """Adiciona linha vertical marcando a data de hoje"""
    cores = get_cores()

    fig.add_vline(
        x=data_hoje,
        line_dash="dash",
        line_color=cores['perigo'],
        annotation_text="Hoje",
        annotation_position="top"
    )

    return fig
