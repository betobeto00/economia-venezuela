"""
Indicadores de Encuestas
========================

Calcula KPIs normalizados (0-100) a partir de las respuestas de encuestas,
agregados por segmento y por período (serie temporal para el dashboard).

El mapa de preguntas (QUESTION_MAP) relaciona cada KPI con los términos de
búsqueda de la pregunta real en la hoja. Cuando se cree el formulario de
Google, basta ajustar este mapa con el texto exacto de las preguntas.

Los puntajes se normalizan a 0-100:
- Categóricos (Sí/No, Mejor/Peor) se mapean a extremos/medio.
- Numéricos (%, rangos) se acotan a [0, 100].
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from src.models.survey import SurveyResponse
from src.collectors.surveys.utils import (
    ALTA_BAJA_MAP,
    DOLAR_MONEDA_MAP,
    MEJOR_PEOR_MAP,
    MUCHO_NADA_MAP,
    SIN_NO_MAP,
    classify,
    to_clamped_percent,
    to_number,
)

# Mapa KPI → configuración de extracción.
# terms: subcadenas para localizar la pregunta en raw_answers.
# categorical: opciones (minúsculas) → puntaje 0-100.
# numeric: True si la pregunta admite respuesta numérica (%, rango).
QUESTION_MAP: Dict[str, Dict[str, Any]] = {
    # --- Persona común ---
    "percepcion_inflacion": {
        "label": "Percepción de inflación (último mes)",
        "terms": ["precios subieron", "los precios subieron", "inflación", "inflacion", "subieron los precios"],
        "categorical": MUCHO_NADA_MAP,
        "numeric": True,
    },
    "expectativa_economia": {
        "label": "Expectativa económica (6 meses)",
        "terms": ["cómo ves la economía", "como ves la economia", "economía en 6 meses", "economia en 6 meses", "economía en los próximos", "economia en los proximos"],
        "categorical": MEJOR_PEOR_MAP,
    },
    "capacidad_ahorro": {
        "label": "Capacidad de ahorro",
        "terms": ["puedes ahorrar", "ahorrar este mes", "lograste ahorrar", "pudo ahorrar"],
        "categorical": SIN_NO_MAP,
    },
    "presion_canasta": {
        "label": "Presión de la canasta (% ingreso en alimentos)",
        "terms": ["destinas a comida", "destina a comida", "% de tu ingreso", "porcentaje de tu ingreso", "gastas al mes en alimentos", "ingreso a alimentos"],
        "numeric": True,
    },
    "dolarizacion_ingreso": {
        "label": "Dolarización del ingreso",
        "terms": ["qué moneda recibes", "que moneda recibes", "moneda recibes tu ingreso", "recibes tu ingreso", "recibe su ingreso"],
        "categorical": DOLAR_MONEDA_MAP,
    },
    # --- Comerciante ---
    "clima_negocios": {
        "label": "Clima de negocios (evolución ventas)",
        "terms": ["evolucionaron tus ventas", "ventas este mes", "ventas vs el anterior", "ventas del mes", "tus ventas"],
        "categorical": MEJOR_PEOR_MAP,
    },
    "ajuste_precios": {
        "label": "Ajuste de precios (mes)",
        "terms": ["ajustaste precios", "ajustaste tus precios", "ajustó precios", "subiste los precios", "reajustó sus precios"],
        "categorical": SIN_NO_MAP,
    },
    "dolarizacion_ventas": {
        "label": "Dolarización de ventas (%)",
        "terms": ["cobras en dólares", "cobras en dolares", "% cobras en dólar", "porcentaje cobras en dólar", "cobra en dólares", "ventas en dólares", "ventas en dolares"],
        "numeric": True,
    },
    "demanda": {
        "label": "Nivel de demanda",
        "terms": ["cómo está tu demanda", "como esta tu demanda", "cómo está la demanda", "como esta la demanda", "nivel de demanda", "tu demanda"],
        "categorical": ALTA_BAJA_MAP,
    },
    "margen": {
        "label": "Evolución del margen",
        "terms": ["tu margen", "margen cambió", "margen cambio", "cambió tu margen", "cambio tu margen", "su margen"],
        "categorical": MEJOR_PEOR_MAP,
    },
    "acceso_credito": {
        "label": "Acceso a crédito",
        "terms": ["acceso a crédito", "acceso a credito", "tienes acceso a crédito", "tiene acceso a crédito", "crédito", "credito"],
        "categorical": SIN_NO_MAP,
    },
}


@dataclass
class KPIResult:
    """Resultado agregado de un KPI para un lote de respuestas."""
    key: str
    label: str
    mean: float
    std: float
    n_responses: int


class SurveyIndicators:
    """Calcula KPIs normalizados (0-100) a partir de respuestas de encuestas.

    Args:
        question_map: Mapa de preguntas; por defecto usa QUESTION_MAP.
    """

    def __init__(self, question_map: Optional[Dict[str, Dict[str, Any]]] = None):
        self.question_map = question_map or QUESTION_MAP

    def _find_answer(self, raw_answers: Dict[str, Any], terms: List[str]) -> Optional[str]:
        """Localiza la respuesta de una pregunta por coincidencia de subcadena.

        Busca de forma case-insensitive y prioriza el término más específico
        (más largo) para evitar que un término genérico (p.ej. "tus ventas")
        capture una pregunta distinta que contenga esa frase.
        """
        scored: List[tuple] = []
        for question, value in raw_answers.items():
            if not str(value).strip():
                continue
            q = str(question).lower()
            for term in terms:
                if term in q:
                    scored.append((len(term), term, str(value)))
        if not scored:
            return None
        scored.sort(key=lambda item: item[0], reverse=True)
        return scored[0][2]

    def _extract_score(
        self, spec: Dict[str, Any], raw_answers: Dict[str, Any]
    ) -> Optional[float]:
        """Extrae el puntaje 0-100 de una respuesta para un KPI.

        Orden de resolución: numérico (%, rango) → categórico.
        """
        answer = self._find_answer(raw_answers, spec["terms"])
        if answer is None:
            return None
        if spec.get("numeric", False):
            numeric = to_clamped_percent(answer)
            if numeric is not None:
                return round(numeric, 2)
        return classify(answer, spec["categorical"])

    def extract_all(self, response: SurveyResponse) -> Dict[str, float]:
        """Extrae todos los KPIs de una sola respuesta (sin agregar)."""
        return {
            key: score
            for key, spec in self.question_map.items()
            if (score := self._extract_score(spec, response.raw_answers)) is not None
        }

    def compute_all(self, responses: List[SurveyResponse]) -> Dict[str, KPIResult]:
        """Agrega los KPIs de un lote de respuestas (media, desviación, N).

        Args:
            responses: Respuestas normalizadas (idealmente de un segmento).

        Returns:
            Dict KPI → KPIResult. Solo KPIs con al menos una respuesta válida.
        """
        results: Dict[str, KPIResult] = {}
        per_kpi: Dict[str, List[float]] = {}
        for response in responses:
            for key, score in self.extract_all(response).items():
                per_kpi.setdefault(key, []).append(score)

        for key, scores in per_kpi.items():
            results[key] = KPIResult(
                key=key,
                label=self.question_map[key]["label"],
                mean=round(float(np.mean(scores)), 2),
                std=round(float(np.std(scores)), 2),
                n_responses=len(scores),
            )
        return results

    def compute_series(
        self,
        responses: List[SurveyResponse],
        freq: str = "W",
        min_responses: int = 1,
    ) -> pd.DataFrame:
        """Serie temporal de KPIs agregados por período (media).

        Args:
            responses: Respuestas normalizadas.
            freq: Frecuencia de pandas (``W``, ``ME``, ``D``...).
            min_responses: Mínimo de respuestas para publicar un punto
                (evita puntos poco robustos; recomendado >= 5).

        Returns:
            DataFrame con columnas ``kpi``, ``date``, ``mean``, ``n``.
        """
        records: List[Dict[str, Any]] = []
        for response in responses:
            if response.submitted_at is None:
                continue
            for key, score in self.extract_all(response).items():
                records.append({
                    "date": response.submitted_at,
                    "kpi": key,
                    "score": score,
                })
        if not records:
            return pd.DataFrame(columns=["kpi", "date", "mean", "n"])

        df = pd.DataFrame(records)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
        grouped = (
            df.groupby(["kpi", pd.Grouper(freq=freq)])["score"]
            .agg(["mean", "count"])
            .reset_index()
        )
        grouped = grouped[grouped["count"] >= min_responses]
        return grouped.rename(columns={"mean": "mean", "count": "n"})


def clean_numeric_ranges(value: str) -> Optional[float]:
    """Limpia rangos numéricos ("15-20%") y devuelve el punto medio (utilidad)."""
    num = to_number(value)
    return num