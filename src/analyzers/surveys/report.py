"""
Informe Ejecutivo de Encuestas
==============================

Genera un resumen ejecutivo en Markdown a partir de los KPIs de encuestas y
el contraste con datos oficiales. Usa una plantilla determinista como base y
un refinamiento opcional por IA (DeepSeek) si DEEPSEEK_API_KEY está
configurada.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from src.config import settings
from src.analyzers.surveys.indicators import KPIResult

logger = logging.getLogger(__name__)


def _format_kpi_table(kpis: Dict[str, KPIResult]) -> List[str]:
    """Tabla Markdown de KPIs agregados."""
    if not kpis:
        return ["_Sin KPIs calculados (no hay respuestas válidas en el período)._"]
    lines = [
        "| Indicador | Media | Desv. | N |",
        "|---|---|---|---|",
    ]
    for result in sorted(kpis.values(), key=lambda r: -r.mean):
        lines.append(
            f"| {result.label} | {result.mean:.1f} | {result.std:.1f} | {result.n_responses} |"
        )
    return lines


def build_markdown_report(
    survey_type: str,
    kpis: Dict[str, KPIResult],
    contrast: Optional[dict] = None,
    n_responses: int = 0,
    period: Optional[str] = None,
) -> str:
    """Construye el resumen ejecutivo en Markdown (plantilla determinista).

    Args:
        survey_type: Segmento encuestado (persona_comun | comerciante).
        kpis: KPIs agregados del período.
        contrast: Resultado de ``contrast_perception_inflation`` (opcional).
        n_responses: Total de respuestas del período.
        period: Descripción del período (p.ej. "Semana del 2026-08-17").

    Returns:
        Markdown listo para el dashboard o exportación.
    """
    segment = "Persona Común" if survey_type == "persona_comun" else "Comerciante"
    period_label = period or datetime.now().strftime("%Y-%m-%d")

    report = [
        f"# Informe Ejecutivo de Encuestas — {segment}",
        "",
        f"**Período:** {period_label}  ",
        f"**Respuestas:** {n_responses}",
        "",
        "## Indicadores (0-100)",
        "",
        *_format_kpi_table(kpis),
    ]

    if contrast and contrast.get("official") is not None:
        report += [
            "",
            "## Contraste Percepción vs Realidad",
            "",
            f"**{contrast['interpretation']}**",
            "",
            f"- Percepción: {contrast['perceived']}%",
            f"- IPC oficial BCV: {contrast['official']}%",
            f"- OVF: {contrast['ovf']}%" if contrast.get("ovf") is not None else "",
            f"- Brecha vs oficial: {contrast['gap_vs_official']} puntos",
        ]

    report += [
        "",
        "## Limitaciones",
        "",
        "- Muestreo voluntario (sesgo de autoselección); los resultados no son",
        "  representativos de la población en su totalidad.",
        f"- N={n_responses}; interpretar con cautela si N < 50.",
        "",
        "---",
        "_Generado automáticamente por Economía Venezuela (Fase B)._",
    ]
    return "\n".join(line for line in report if line is not None)


class SurveyReport:
    """Generador de informes ejecutivos de encuestas.

    Usa la plantilla determinista y, si ``DEEPSEEK_API_KEY`` está configurada,
    genera un resumen narrativo con IA (OpenAI-compatible).
    """

    def __init__(self, ai_enabled: Optional[bool] = None):
        self.ai_enabled = (
            bool(settings.llm_providers())
            if ai_enabled is None
            else ai_enabled
        )

    def generate(
        self,
        survey_type: str,
        kpis: Dict[str, KPIResult],
        contrast: Optional[dict] = None,
        n_responses: int = 0,
        period: Optional[str] = None,
    ) -> str:
        """Genera el informe ejecutivo completo.

        Returns:
            Markdown del informe. Si la IA falla, devuelve la plantilla base.
        """
        base = build_markdown_report(
            survey_type, kpis, contrast, n_responses, period
        )
        if not self.ai_enabled:
            return base

        try:
            summary = self._summarize_with_ai(base, survey_type)
            if not summary:
                return base
            return base + "\n\n## Resumen IA\n\n" + summary
        except Exception as exc:  # noqa: BLE001 - el informe no debe fallar
            logger.warning("Resumen IA no disponible: %s", exc)
            return base

    def _summarize_with_ai(self, report: str, survey_type: str) -> str:
        """Resumen narrativo vía la cadena de LLMs con fallback.

        Usa el primer proveedor de ``settings.llm_providers()`` que responda
        (LLM1..LLM8, con DEEPSEEK como fallback de último recurso).
        """
        from src.analyzers.llm import chat_completion, LLMError

        try:
            content = chat_completion(
                [
                    {
                        "role": "system",
                        "content": (
                            "Eres un economista especializado en Venezuela. Resume en "
                            "3-4 frases los hallazgos clave del informe de encuestas "
                            "para un lector no técnico."
                        ),
                    },
                    {"role": "user", "content": report},
                ],
                temperature=0.3,
                max_tokens=250,
            )
        except LLMError as exc:
            logger.warning("Cadena de LLMs no disponible: %s", exc)
            return ""
        return content.strip()