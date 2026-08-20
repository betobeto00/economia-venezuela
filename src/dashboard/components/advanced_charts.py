"""
Gráficos Avanzados para el Dashboard
======================================

- Mapa de calor de correlaciones entre variables macro
- Fan charts (proyecciones con intervalos de confianza)
- Gráficos de series temporales con overlay
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.dashboard import theme

logger = logging.getLogger(__name__)


def correlation_heatmap(df: pd.DataFrame, title: str = "Correlaciones Macroeconómicas") -> go.Figure:
    """Genera un mapa de calor de correlaciones entre variables.

    Args:
        df: DataFrame con columnas numéricas (ej: inflación, tipo de cambio, petróleo, etc.)
        title: Título del gráfico.

    Returns:
        Figura Plotly con el heatmap.
    """
    corr = df.corr()

    fig = go.Figure(data=go.Heatmap(
        z=corr.values,
        x=corr.columns,
        y=corr.columns,
        colorscale="RdBu_r",
        zmid=0,
        text=np.round(corr.values, 2),
        texttemplate="%{text}",
        textfont={"size": 11},
        hovertemplate="Correlación: %{z:.3f}<extra></extra>",
    ))

    fig.update_layout(
        title=title,
        template=theme.plotly_template(),
        height=400,
        margin=dict(l=10, r=10, t=40, b=10),
    )

    return fig


def fan_chart(
    historical: pd.Series,
    forecast_mean: pd.Series,
    forecast_lower: pd.Series,
    forecast_upper: pd.Series,
    title: str = "Proyección con Intervalos de Confianza",
    y_label: str = "Valor",
) -> go.Figure:
    """Genera un fan chart con proyección e intervalos de confianza.

    Args:
        historical: Serie histórica.
        forecast_mean: Predicción media.
        forecast_lower: Límite inferior del intervalo.
        forecast_upper: Límite superior del intervalo.
        title: Título del gráfico.
        y_label: Etiqueta del eje Y.

    Returns:
        Figura Plotly con el fan chart.
    """
    fig = go.Figure()

    # Intervalo de confianza (95%)
    fig.add_trace(go.Scatter(
        x=forecast_upper.index,
        y=forecast_upper,
        mode="lines",
        line=dict(width=0),
        showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=forecast_lower.index,
        y=forecast_lower,
        mode="lines",
        line=dict(width=0),
        fill="tonexty",
        fillcolor="rgba(124, 94, 167, 0.2)",
        name="IC 95%",
    ))

    # Línea de predicción
    fig.add_trace(go.Scatter(
        x=forecast_mean.index,
        y=forecast_mean,
        mode="lines+markers",
        line=dict(color=theme.PALETTE["violeta"], width=2.5),
        name="Predicción",
    ))

    # Datos históricos
    fig.add_trace(go.Scatter(
        x=historical.index,
        y=historical,
        mode="lines",
        line=dict(color=theme.PALETTE["azul"], width=2),
        name="Histórico",
    ))

    fig.update_layout(
        title=title,
        yaxis_title=y_label,
        template=theme.plotly_template(),
        height=400,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )

    return fig


def multi_series_overlay(
    series_dict: dict,
    title: str = "Evolución de Variables Macroeconómicas",
    y_labels: Optional[dict] = None,
) -> go.Figure:
    """Genera un gráfico con múltiples series en ejes Y secundarios.

    Args:
        series_dict: Dict nombre → Serie de pandas.
        title: Título del gráfico.
        y_labels: Etiquetas por serie (nombre → label).

    Returns:
        Figura Plotly con múltiples ejes.
    """
    if not series_dict:
        return go.Figure()

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    colors = [
        theme.PALETTE["azul"],
        theme.PALETTE["naranja"],
        theme.PALETTE["verde"],
        theme.PALETTE["violeta"],
        theme.PALETTE["rojo"],
    ]

    for i, (name, series) in enumerate(series_dict.items()):
        color = colors[i % len(colors)]
        use_secondary = i % 2 == 1
        fig.add_trace(
            go.Scatter(
                x=series.index,
                y=series,
                mode="lines",
                name=name,
                line=dict(color=color, width=2),
            ),
            secondary_y=use_secondary,
        )

    fig.update_layout(
        title=title,
        template=theme.plotly_template(),
        height=450,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )

    return fig


def waterfall_chart(
    categories: list,
    values: list,
    title: str = "Descomposición del Crecimiento",
) -> go.Figure:
    """Genera un gráfico de cascada (waterfall) para descomposición.

    Args:
        categories: Nombres de las categorías.
        values: Valores de cada categoría (positivos = suma, negativos = resta).
        title: Título del gráfico.

    Returns:
        Figura Plotly waterfall.
    """
    measures = ["relative"] * len(values)
    measures[0] = "total"
    measures[-1] = "total"

    fig = go.Figure(go.Waterfall(
        name="",
        orientation="v",
        measure=measures,
        x=categories,
        y=values,
        textposition="outside",
        text=[f"{v:+.1f}" for v in values],
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        increasing={"marker": {"color": theme.PALETTE["verde"]}},
        decreasing={"marker": {"color": theme.PALETTE["rojo"]}},
        totals={"marker": {"color": theme.PALETTE["azul"]}},
    ))

    fig.update_layout(
        title=title,
        template=theme.plotly_template(),
        height=400,
        margin=dict(l=10, r=10, t=40, b=10),
        showlegend=False,
    )

    return fig
