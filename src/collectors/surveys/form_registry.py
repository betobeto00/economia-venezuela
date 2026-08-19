"""
Registro de Formularios de Encuesta
===================================

Construye los objetos ``Survey`` (persona_comun, comerciante) a partir de las
variables de entorno del sistema. Los IDs de formulario y hoja se configuran
vía entorno para no exponer información en el repo.

Variables esperadas (ver .env.example):
    SURVEY_PERSONA_COMUN_FORM_ID / _SHEET_ID
    SURVEY_COMERCIANTE_FORM_ID / _SHEET_ID
"""

from typing import List, Optional

from src.config import settings
from src.models.survey import Survey

# Definición de segmentos: clave → (id, nombre legible)
SEGMENTS = {
    "persona_comun": ("Encuesta Persona Común",),
    "comerciante": ("Encuesta Comerciante",),
}


class SurveyRegistry:
    """Registro central de formularios de encuesta activos.

    Solo devuelve los formularios cuyos IDs de form/sheet están configurados
    en el entorno. Los no configurados se omiten para no fallar en ejecuciones
    sin las credenciales listas (p.ej. desarrollo local).
    """

    def __init__(self, config=None):
        self.config = config or settings

    def _build(
        self,
        survey_id: int,
        survey_type: str,
        form_id: Optional[str],
        sheet_id: Optional[str],
        name: str,
    ) -> Optional[Survey]:
        if not form_id or not sheet_id:
            return None
        return Survey(
            id=survey_id,
            survey_type=survey_type,
            form_id=form_id,
            sheet_id=sheet_id,
            name=name,
            active=True,
        )

    def list_surveys(self) -> List[Survey]:
        """Lista los formularios activos configurados en el entorno."""
        surveys: List[Survey] = []
        persona = self._build(
            1,
            "persona_comun",
            self.config.SURVEY_PERSONA_COMUN_FORM_ID,
            self.config.SURVEY_PERSONA_COMUN_SHEET_ID,
            SEGMENTS["persona_comun"][0],
        )
        if persona is not None:
            surveys.append(persona)

        comerciante = self._build(
            2,
            "comerciante",
            self.config.SURVEY_COMERCIANTE_FORM_ID,
            self.config.SURVEY_COMERCIANTE_SHEET_ID,
            SEGMENTS["comerciante"][0],
        )
        if comerciante is not None:
            surveys.append(comerciante)
        return surveys

    def get_survey(self, survey_type: str) -> Optional[Survey]:
        """Busca un formulario por su tipo de segmento."""
        for survey in self.list_surveys():
            if survey.survey_type == survey_type:
                return survey
        return None