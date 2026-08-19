"""
Modelos de Encuestas
====================

Modelos Pydantic para el sistema de encuestas Google (Fase B):

- Survey: formulario de Google Forms vinculado a una hoja de respuestas.
- SurveyResponse: una respuesta individual normalizada (respuestas crudas + KPIs).

Claves de diseño:
- Las respuestas crudas se guardan como dict (JSONB en PostgreSQL) para que
  las preguntas puedan cambiar entre versiones sin romper el esquema.
- Cada formulario tiene form_version; al editar preguntas se versiona,
  no se rompe la serie histórica.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Survey(BaseModel):
    """Formulario de encuesta activo.

    Atributos:
        id: Identificador interno (SERIAL en PostgreSQL).
        survey_type: Segmento encuestado: ``persona_comun`` | ``comerciante``.
        form_id: ID del formulario de Google Forms.
        sheet_id: ID de la Google Sheet vinculada al formulario.
        form_version: Versión del formulario (cambios de preguntas).
        name: Nombre legible del formulario.
        active: Si el formulario está activo para recolección.
    """

    id: int
    survey_type: str
    form_id: str
    sheet_id: str
    form_version: int = 1
    name: str = ""
    active: bool = True


class SurveyResponse(BaseModel):
    """Respuesta individual de una encuesta normalizada.

    Atributos:
        id: Identificador interno (BIGSERIAL); None si aún no se persiste.
        survey_id: FK a la encuesta a la que pertenece.
        submitted_at: Marca de tiempo de la respuesta.
        respondent_segment: Segmento del encuestado (heredado del formulario).
        timezone: Zona horaria registrada (opcional).
        raw_answers: Respuestas crudas (pregunta → valor), JSONB en DB.
        kpis: KPIs derivados normalizados (0-100), calculados por el analyzer.
        quality_score: Fracción de preguntas respondidas (0.0-1.0).
        source: Origen de la respuesta (``google_forms`` por defecto).
    """

    id: Optional[int] = None
    survey_id: int
    submitted_at: datetime
    respondent_segment: str
    timezone: Optional[str] = None
    raw_answers: Dict[str, Any] = Field(default_factory=dict)
    kpis: Dict[str, float] = Field(default_factory=dict)
    quality_score: Optional[float] = None
    source: str = "google_forms"

    def answered(self) -> int:
        """Número de preguntas respondidas (valores no vacíos)."""
        return sum(1 for v in self.raw_answers.values() if str(v).strip())


def dedupe_responses(responses: List[SurveyResponse]) -> List[SurveyResponse]:
    """Elimina respuestas duplicadas (misma survey, misma marca de tiempo y
    mismas respuestas crudas). Mantiene la primera ocurrencia.

    Args:
        responses: Lista de respuestas normalizadas.

    Returns:
        Lista sin duplicados, preservando el orden original.
    """
    seen = set()
    unique: List[SurveyResponse] = []
    for resp in responses:
        key = (
            resp.survey_id,
            resp.submitted_at.isoformat() if resp.submitted_at else None,
            str(sorted(resp.raw_answers.items())),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(resp)
    return unique