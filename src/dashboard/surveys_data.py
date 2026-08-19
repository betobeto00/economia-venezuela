"""
Datos para la sección de Encuestas del dashboard
================================================

Capa de datos pura (sin Streamlit) para la sección de encuestas:
carga respuestas, calcula KPIs, series temporales, comparación entre
períodos y el informe ejecutivo. Al separar la lógica de la presentación,
esta capa es testeable sin levantar el dashboard.

Flujo:
    respuestas = load_responses_from_db(segmento, días)
    kpis        = kpi_cards(respuestas)          # tarjetas de métricas
    serie       = series_df(respuestas)          # serie temporal
    deltas      = compare_periods(kpis_actual, kpis_previo)
    contraste   = build_contrast(respuestas, oficial, ovf)
    informe     = build_report(segmento, respuestas, ...)
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd

from src.analyzers.surveys.contrast import contrast_perception_inflation
from src.analyzers.surveys.indicators import KPIResult, SurveyIndicators
from src.analyzers.surveys.report import SurveyReport
from src.models.survey import SurveyResponse

logger = logging.getLogger(__name__)

DEFAULT_FREQ = "W"
DEFAULT_DAYS = 90
MIN_RESPONSES_SERIES = 3


def segment_label(survey_type: str) -> str:
    """Nombre legible de un segmento de encuesta."""
    return {
        "persona_comun": "Persona Común",
        "comerciante": "Comerciante",
    }.get(survey_type, survey_type.capitalize())


def load_responses_from_db(survey_type: str, days: int = DEFAULT_DAYS) -> List[SurveyResponse]:
    """Carga respuestas de un segmento desde la base (últimos ``days`` días).

    Raises:
        Exception: si la base no está disponible (el caller lo maneja
            mostrando un warning, nunca un crash).
    """
    from src.db.repositories import SurveyRepository
    from src.db.session import get_session

    since = datetime.now() - timedelta(days=days)
    with get_session() as session:
        return SurveyRepository(session).list_responses(
            segment=survey_type, since=since
        )


def kpi_cards(responses: List[SurveyResponse], indicators: Optional[SurveyIndicators] = None) -> Dict[str, KPIResult]:
    """Calcula los KPIs agregados de un lote de respuestas (para tarjetas).

    Args:
        responses: Respuestas normalizadas de un segmento.
        indicators: Calculadora opcional (inyectable en tests).

    Returns:
        Dict KPI → KPIResult (solo KPIs con al menos una respuesta válida).
    """
    indicators = indicators or SurveyIndicators()
    return indicators.compute_all(responses)


def series_df(
    responses: List[SurveyResponse],
    freq: str = DEFAULT_FREQ,
    min_responses: int = MIN_RESPONSES_SERIES,
    indicators: Optional[SurveyIndicators] = None,
) -> pd.DataFrame:
    """Serie temporal de KPIs agregados por período (para el gráfico).

    Args:
        responses: Respuestas normalizadas.
        freq: Frecuencia de pandas (``W``, ``ME``, ``D``...).
        min_responses: Mínimo de respuestas para publicar un punto.
        indicators: Calculadora opcional.

    Returns:
        DataFrame con columnas ``kpi``, ``date``, ``mean``, ``n``.
    """
    indicators = indicators or SurveyIndicators()
    return indicators.compute_series(responses, freq=freq, min_responses=min_responses)


def split_periods(
    responses: List[SurveyResponse],
    current_days: int = 30,
) -> tuple[List[SurveyResponse], List[SurveyResponse]]:
    """Divide respuestas en período actual y período previo (misma duración).

    Args:
        responses: Respuestas del segmento (con submitted_at).
        current_days: Ventana en días del período actual.

    Returns:
        (respuestas del período actual, respuestas del período previo).
    """
    now = datetime.now()
    start_current = now - timedelta(days=current_days)
    start_previous = now - timedelta(days=2 * current_days)

    current = [
        r for r in responses
        if r.submitted_at and start_current <= r.submitted_at <= now
    ]
    previous = [
        r for r in responses
        if r.submitted_at and start_previous <= r.submitted_at < start_current
    ]
    return current, previous


def compare_periods(
    current: Dict[str, KPIResult],
    previous: Dict[str, KPIResult],
) -> Dict[str, float]:
    """Diferencia (en puntos) de cada KPI entre el período actual y el previo.

    Args:
        current: KPIs del período actual.
        previous: KPIs del período previo.

    Returns:
        Dict KPI → delta (actual - previo); solo KPIs presentes en ambos.
    """
    return {
        key: round(current[key].mean - previous[key].mean, 2)
        for key in current
        if key in previous
    }


def build_contrast(
    responses: List[SurveyResponse],
    official: Optional[float] = None,
    ovf: Optional[float] = None,
    indicators: Optional[SurveyIndicators] = None,
) -> Optional[dict]:
    """Contraste percepción de inflación vs mediciones (BCV/OVF).

    Args:
        responses: Respuestas del segmento persona_comun.
        official: IPC oficial BCV (%) u otro dato oficial.
        ovf: Estimación independiente OVF (%).
        indicators: Calculadora opcional.

    Returns:
        Dict de contraste (ver contrast_perception_inflation), o None si no
        hay respuestas con percepción de inflación.
    """
    indicators = indicators or SurveyIndicators()
    kpis = indicators.compute_all(responses)
    kpi = kpis.get("percepcion_inflacion")
    if kpi is None:
        return None
    return contrast_perception_inflation(
        perceived=kpi.mean, official=official, ovf=ovf
    )


def build_report(
    survey_type: str,
    responses: List[SurveyResponse],
    contrast: Optional[dict] = None,
    n_responses: Optional[int] = None,
    period: Optional[str] = None,
    ai_enabled: Optional[bool] = None,
    indicators: Optional[SurveyIndicators] = None,
) -> str:
    """Informe ejecutivo Markdown de encuestas (plantilla + IA opcional).

    Args:
        survey_type: Segmento (persona_comun | comerciante).
        responses: Respuestas del período a resumir.
        contrast: Contraste calculado con ``build_contrast`` (opcional).
        n_responses: Total de respuestas (si None, usa len(responses)).
        period: Etiqueta del período.
        ai_enabled: Habilita resumen IA (None = según DEEPSEEK_API_KEY).
        indicators: Calculadora opcional.

    Returns:
        Markdown del informe ejecutivo.
    """
    kpis = kpi_cards(responses, indicators=indicators)
    report = SurveyReport(ai_enabled=ai_enabled)
    return report.generate(
        survey_type=survey_type,
        kpis=kpis,
        contrast=contrast,
        n_responses=len(responses) if n_responses is None else n_responses,
        period=period or datetime.now().strftime("%Y-%m-%d"),
    )