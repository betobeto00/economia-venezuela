"""
Sección de Encuestas del dashboard (Streamlit)
==============================================

Renderiza KPIs de encuestas, serie temporal, contraste percepción vs realidad
y el informe ejecutivo. Toda la lógica de datos vive en ``surveys_data.py``;
aquí solo hay presentación con manejo de estados (carga, vacío, error).

Reglas (skill frontend-visionary-artisan):
- Sin valores hardcodeados: todo sale de la capa de datos.
- Resiliencia: si la base no responde o no hay respuestas, muestra un mensaje
  amigable, nunca un crash.
- Caché con TTL para recálculos pesados.
"""

import logging

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.dashboard import theme
from src.dashboard.surveys_data import (
    build_contrast,
    build_report,
    compare_periods,
    kpi_cards,
    load_responses_from_db,
    segment_label,
    series_df,
    split_periods,
)

logger = logging.getLogger(__name__)


@st.cache_data(ttl=300, show_spinner=False)
def _survey_snapshot(segment: str, days: int, freq: str, current_days: int) -> dict:
    """Snapshot cacheadable de datos de encuestas para un segmento.

    Devuelve solo estructuras serializables (dicts y DataFrame) para que
    ``st.cache_data`` pueda cachearlas.

    Returns:
        Dict con series, kpis (listas), deltas, n_responses y contraste.
    """
    responses = load_responses_from_db(segment, days)
    indicators = _indicators_for(segment)

    current, previous = split_periods(responses, current_days=current_days)
    kpis = kpi_cards(current, indicators=indicators)
    kpis_prev = kpi_cards(previous, indicators=indicators)
    deltas = compare_periods(kpis, kpis_prev)

    return {
        "series": series_df(responses, freq=freq, indicators=indicators),
        "kpis": [
            {"key": key, "label": kpi.label, "mean": kpi.mean,
             "std": kpi.std, "n": kpi.n_responses}
            for key, kpi in sorted(kpis.items(), key=lambda kv: -kv[1].mean)
        ],
        "deltas": deltas,
        "n_responses": len(current),
        "contrast": build_contrast(responses, indicators=indicators),
    }


@st.cache_data(ttl=300, show_spinner=False)
def _report_snapshot(segment: str, days: int, period: str, contrast: dict) -> str:
    """Informe ejecutivo cacheadable (Markdown) para un segmento."""
    responses = load_responses_from_db(segment, days)
    return build_report(segment, responses, contrast=contrast, period=period)


def _indicators_for(segment: str):
    """Calculadora de indicadores estándar (misma para todos los KPIs)."""
    from src.analyzers.surveys.indicators import SurveyIndicators
    return SurveyIndicators()


def _build_series_chart(series: pd.DataFrame) -> go.Figure:
    """Gráfico de líneas de la serie temporal de KPIs (una por KPI)."""
    fig = go.Figure()
    colors = theme.SERIES_COLORS
    for i, (kpi, group) in enumerate(series.groupby("kpi", sort=True)):
        label = kpi.replace("_", " ").capitalize()
        fig.add_trace(go.Scatter(
            x=group["date"], y=group["mean"], name=label,
            mode="lines+markers",
            line=dict(color=colors[i % len(colors)], width=2.5),
            hovertemplate="%{y:.1f}<extra>" + label + "</extra>",
        ))
    fig.update_layout(
        template=theme.plotly_template(),
        hovermode="x unified",
        margin=dict(l=10, r=10, t=40, b=10),
        yaxis=dict(range=[0, 100], title="KPI (0-100)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig


def render_survey_section(segment: str, days: int = 90, freq: str = "W") -> None:
    """Renderiza la sección de encuestas completa.

    Args:
        segment: Segmento encuestado (persona_comun | comerciante).
        days: Ventana en días de respuestas a considerar.
        freq: Frecuencia de la serie temporal (p.ej. ``W``).
    """
    label = segment_label(segment)

    with st.spinner(f"Cargando encuestas de {label}..."):
        try:
            data = _survey_snapshot(segment, days, freq, current_days=30)
        except Exception as exc:  # noqa: BLE001 - nunca romper el dashboard
            logger.warning("Encuestas no disponibles (%s): %s", segment, exc)
            st.warning(
                "⚠️ No se pudo acceder a la base de datos de encuestas. "
                "Verifica DATABASE_URL y que el servicio esté levantado."
            )
            return

    if not data["kpis"] or data["n_responses"] == 0:
        st.info(
            f"📭 Todavía no hay respuestas de **{label}** para este período. "
            "Comparte el formulario para empezar a recibir datos."
        )
        return

    st.subheader(f"📋 Encuestas — {label}")
    st.caption(f"{data['n_responses']} respuestas en el período actual")

    # Fila de KPIs con delta vs período previo
    cols = st.columns(min(4, len(data["kpis"])))
    for idx, kpi in enumerate(data["kpis"]):
        delta = data["deltas"].get(kpi["key"])
        delta_text = f"{delta:+.1f} pp" if delta is not None else None
        with cols[idx % len(cols)]:
            st.metric(
                label=kpi["label"],
                value=f"{kpi['mean']:.1f}",
                delta=delta_text,
                help=f"Desviación: {kpi['std']:.1f} | N={kpi['n']}",
            )

    # Serie temporal
    series = data["series"]
    if not series.empty:
        st.plotly_chart(
            _build_series_chart(series),
            use_container_width=True,
            key=f"series_{segment}",
        )
    else:
        st.info("📈 Serie temporal no disponible (faltan respuestas por período).")

    # Contraste percepción vs realidad (solo persona_comun)
    contrast = data["contrast"]
    if contrast is not None and contrast.get("official") is not None:
        st.markdown("### ⚖️ Contraste Percepción vs Realidad")
        c1, c2, c3 = st.columns(3)
        c1.metric("Percepción (encuesta)", f"{contrast['perceived']:.1f}%")
        c2.metric("IPC oficial BCV", f"{contrast['official']:.1f}%")
        if contrast.get("ovf") is not None:
            c3.metric("OVF", f"{contrast['ovf']:.1f}%")
        st.markdown(f"_{contrast['interpretation']}_")
    elif contrast is not None:
        st.caption(
            "⚖️ Contraste con IPC oficial pendiente: requiere datos BCV/OVF "
            "(Fase A). Percepción registrada: "
            f"**{contrast['perceived']:.1f}%**."
        )

    # Informe ejecutivo
    with st.expander("📄 Informe ejecutivo", expanded=False):
        report = _report_snapshot(segment, days, "Último período", contrast or {})
        st.markdown(report)