"""
Módulo de Recolección de Encuestas (Google Forms → Sheets)
==========================================================

Lee las respuestas de los formularios de Google (Persona Común y Comerciante)
desde la Google Sheet vinculada, usando gspread + service account.

Claves de diseño:
- Idempotente: solo ingesta filas nuevas (checkpoint de última fila por sheet).
- Flexible: las respuestas crudas se guardan como dict (JSONB en DB),
  pregunta → valor, para soportar cambios de preguntas entre versiones.
- Seguridad: credenciales de la service account por variable de entorno
  (GOOGLE_CREDENTIALS_PATH), nunca en el repo.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config import settings
from src.models.survey import Survey, SurveyResponse
from src.collectors.surveys.utils import compute_quality_score

logger = logging.getLogger(__name__)

# Google Forms añade la columna de marca de tiempo con encabezado variable
# según el idioma/versión ("Marca de tiempo" / "Marca temporal" / "Timestamp").
TIMESTAMP_HEADERS = (
    "marca de tiempo",
    "marca temporal",
    "marca de fecha y hora",
    "fecha y hora",
    "timestamp",
    "time stamp",
)


def _find_timestamp_header(header: List[str]) -> Optional[str]:
    """Localiza el encabezado de marca de tiempo (case-insensitive, parcial)."""
    for column in header:
        if any(token in str(column).strip().lower() for token in TIMESTAMP_HEADERS):
            return column
    return None

# Formatos de fecha típicos de la hoja de respuestas (dd/mm/yyyy por defecto)
_TIMESTAMP_FORMATS = (
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%m/%d/%Y %H:%M:%S",
    "%Y-%m-%d %H:%M",
)


def parse_timestamp(value: str) -> Optional[datetime]:
    """Parsea la marca de tiempo de la hoja de respuestas.

    Args:
        value: Valor crudo (p.ej. ``"19/08/2026 14:30:00"``).

    Returns:
        Datetime, o None si el formato no es reconocible.
    """
    if not value or not str(value).strip():
        return None
    text = str(value).strip()
    for fmt in _TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    logger.warning("Marca de tiempo no reconocida: %r", value)
    return None


class SurveyCheckpoint:
    """Checkpoint de última fila procesada por sheet (idempotencia).

    Persiste en un archivo JSON la cantidad de filas de datos ya ingeridas
    para cada ``sheet_id``. Google Forms añade filas al final de la hoja, por
    lo que el índice de fila es un cursor válido entre ejecuciones.
    """

    def __init__(self, checkpoint_path: Optional[Path] = None):
        self.path = Path(checkpoint_path or Path("data/survey_checkpoints.json"))
        self._state: Dict[str, int] = self._load()

    def _load(self) -> Dict[str, int]:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Checkpoint de encuestas ilegible (%s); reiniciando.", exc)
        return {}

    def get_last_row(self, sheet_id: str) -> int:
        """Número de filas de datos ya procesadas para un sheet."""
        return self._state.get(sheet_id, 0)

    def set_last_row(self, sheet_id: str, row_index: int) -> None:
        self._state[sheet_id] = row_index

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._state, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


class SurveyCollector:
    """Recolector de respuestas de encuestas vía Google Sheets API (gspread).

    Args:
        credentials_path: Ruta al JSON de la service account de Google.
            Si es None, usa ``settings.GOOGLE_CREDENTIALS_PATH``.
        checkpoint: Checkpoint de idempotencia (útil en tests).
    """

    def __init__(
        self,
        credentials_path: Optional[str] = None,
        checkpoint: Optional[SurveyCheckpoint] = None,
    ):
        self.credentials_path = credentials_path or settings.GOOGLE_CREDENTIALS_PATH
        if not self.credentials_path:
            raise ValueError(
                "GOOGLE_CREDENTIALS_PATH no está configurado. "
                "Crea una service account de Google y establece la ruta al JSON "
                "(ver knowledge.md > Pipeline Google → Sistema)."
            )
        self.checkpoint = checkpoint or SurveyCheckpoint()
        self._client: Any = None

    def _get_client(self):
        """Cliente gspread (lazy para no depender de gspread en imports)."""
        if self._client is None:
            import gspread  # import diferido: permite testear sin el paquete

            self._client = gspread.service_account(filename=self.credentials_path)
        return self._client

    def _open_worksheet(self, survey: Survey):
        """Abre la hoja de respuestas vinculada al formulario."""
        sheet = self._get_client().open_by_key(survey.sheet_id)
        return sheet.sheet1

    def fetch_new_responses(self, survey: Survey) -> List[SurveyResponse]:
        """Lee las filas nuevas de la hoja vinculada y las normaliza.

        Solo procesa las filas posteriores al checkpoint del sheet (cursor de
        idempotencia) y las convierte en ``SurveyResponse``.

        Args:
            survey: Formulario a recolectar.

        Returns:
            Lista de respuestas normalizadas (fila por respuesta).
        """
        worksheet = self._open_worksheet(survey)
        values = worksheet.get_all_values()
        if not values:
            return []

        header = values[0]
        data_rows = values[1:]
        last_row = self.checkpoint.get_last_row(survey.sheet_id)
        new_rows = data_rows[last_row:]
        if not new_rows:
            return []

        responses: List[SurveyResponse] = []
        for raw_row in new_rows:
            response = self.process_response(raw_row, header, survey)
            if response is not None:
                responses.append(response)

        # Avanza el checkpoint solo con filas de datos reales ingeridas
        self.checkpoint.set_last_row(survey.sheet_id, last_row + len(new_rows))
        self.checkpoint.save()
        return responses

    def process_response(
        self,
        raw_row: List[str],
        header: List[str],
        survey: Survey,
    ) -> Optional[SurveyResponse]:
        """Normaliza una fila cruda de la hoja a ``SurveyResponse``.

        Args:
            raw_row: Valores de una fila de la hoja.
            header: Encabezados (preguntas) de la hoja.
            survey: Formulario al que pertenece la respuesta.

        Returns:
            Respuesta normalizada, o None si la fila es inválida (vacía o
            sin marca de tiempo parseable).
        """
        if not raw_row or not any(str(c).strip() for c in raw_row):
            return None

        timestamp_header = _find_timestamp_header(header)
        submitted_at = parse_timestamp(
            raw_row[header.index(timestamp_header)]
            if timestamp_header is not None else ""
        )
        if submitted_at is None:
            return None

        answers = {
            header[i]: (raw_row[i] if i < len(raw_row) else "")
            for i in range(len(header))
        }
        answers.pop(timestamp_header, None)

        return SurveyResponse(
            survey_id=survey.id,
            submitted_at=submitted_at,
            respondent_segment=survey.survey_type,
            raw_answers=answers,
            quality_score=compute_quality_score(answers),
        )