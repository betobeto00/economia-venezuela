"""
Utilidades de parseo de respuestas de encuestas
===============================================

Funciones auxiliares para normalizar respuestas crudas de Google Forms:
extracción de números, clasificación categórica, calidad de respuesta, etc.

Se asume que las preguntas piden rangos o categorías (ver knowledge.md) para
reducir el sesgo de percepción imprecisa.
"""

import re
from typing import Any, Dict, Optional, Union

# Mapeos categóricos comunes usados por el analyzer de KPIs
SIN_NO_MAP = {"sí": 100, "si": 100, "no": 0}
MEJOR_PEOR_MAP = {"mejor": 100, "igual": 50, "peor": 0}
MUCHO_NADA_MAP = {"mucho": 100, "algo": 66, "poco": 33, "nada": 0}
ALTA_BAJA_MAP = {"alta": 100, "normal": 50, "baja": 0}
DOLAR_MONEDA_MAP = {
    "dólar": 100, "dolar": 100, "usd": 100, "$": 100,
    "ambos": 50, "mixto": 50, "mixta": 50,
    "bolívares": 0, "bolivares": 0, "bs": 0, "bs.": 0,
}


def to_number(value: Any) -> Optional[float]:
    """Extrae el primer número de una respuesta (o el punto medio de un rango).

    Args:
        value: Valor crudo (p.ej. ``"42%"``, ``"$12,5"``, ``"15 - 20"``, 30).

    Returns:
        Float normalizado, o None si no hay ningún número.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).replace(",", ".").replace("$", "").replace("%", "").strip()
    numbers = re.findall(r"-?\d+(?:\.\d+)?", text)
    if not numbers:
        return None
    nums = [float(n) for n in numbers]
    if len(nums) >= 2 and "-" in text:
        # Rango ("15 - 20") → usar el punto medio
        return (nums[0] + nums[1]) / 2.0
    return nums[0]


def to_clamped_percent(value: Any, scale: float = 100.0) -> Optional[float]:
    """Convierte un valor a porcentaje acotado a [0, scale].

    Útil para respuestas numéricas tipo ``"70%"`` o ``"0.8"`` (fracción).
    """
    num = to_number(value)
    if num is None:
        return None
    if 0 < num <= 1 and scale == 100.0:
        num = num * 100  # fracción tipo 0.75 → 75%
    return max(0.0, min(scale, num))


def classify(value: Any, mapping: Dict[str, Union[int, float]]) -> Optional[float]:
    """Clasifica una respuesta categórica usando coincidencia por subcadena.

    Args:
        value: Respuesta cruda (p.ej. ``"Mucho"``, ``"Sí, todo subió"``).
        mapping: Diccionario opción (minúsculas) → puntaje.

    Returns:
        Puntaje de la primera opción encontrada, o None si no coincide.
    """
    if value is None:
        return None
    text = str(value).strip().lower()
    if not text:
        return None
    for option, score in mapping.items():
        if option in text:
            return float(score)
    return None


def yes_no(value: Any) -> Optional[float]:
    """Interpreta una respuesta Sí/No como 100/0 (None si no es interpretable)."""
    return classify(value, SIN_NO_MAP)


def compute_quality_score(answers: Dict[str, Any]) -> float:
    """Fracción de preguntas respondidas (0.0-1.0) usada como control de calidad.

    Args:
        answers: Respuestas crudas (pregunta → valor).

    Returns:
        Proporción de valores no vacíos.
    """
    if not answers:
        return 0.0
    answered = sum(1 for v in answers.values() if str(v).strip())
    return round(answered / len(answers), 2)