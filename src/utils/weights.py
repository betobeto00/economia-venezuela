"""Pesos configurables por entorno
=================================

Los índices compuestos (IAE, riesgo soberano) llevan pesos en el código. Aquí
se permite sobrescribirlos con una variable de entorno en formato JSON, sin
romper el arranque si el valor viene mal: se avisa y se usan los defaults.
"""

from __future__ import annotations

import json
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def parse_weights(
    raw: Optional[str],
    defaults: Dict[str, float],
    label: str,
) -> Dict[str, float]:
    """Devuelve los pesos efectivos a partir de un JSON de configuración.

    Reglas:
        - Vacío o ``None`` → defaults.
        - JSON inválido, no-dict o sin claves conocidas → defaults + warning.
        - Claves desconocidas se ignoran (con warning): el índice solo suma
          los componentes que conoce.
        - Valores negativos o suma <= 0 → defaults + warning.

    Args:
        raw: Valor de la variable de entorno (JSON).
        defaults: Pesos por defecto del índice.
        label: Nombre del índice, para los mensajes de log.

    Returns:
        Diccionario de pesos listo para usar.
    """
    if not raw or not raw.strip():
        return dict(defaults)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("%s: pesos con JSON inválido (%s); se usan los defaults", label, exc)
        return dict(defaults)

    if not isinstance(data, dict) or not data:
        logger.warning("%s: los pesos deben ser un objeto JSON no vacío; defaults", label)
        return dict(defaults)

    unknown = sorted(set(data) - set(defaults))
    if unknown:
        logger.warning("%s: claves de peso desconocidas ignoradas: %s", label, unknown)

    merged = dict(defaults)
    try:
        for key, value in data.items():
            if key in defaults:
                merged[key] = float(value)
    except (TypeError, ValueError) as exc:
        logger.warning("%s: pesos no numéricos (%s); se usan los defaults", label, exc)
        return dict(defaults)

    if any(value < 0 for value in merged.values()) or sum(merged.values()) <= 0:
        logger.warning("%s: pesos negativos o suma nula; se usan los defaults", label)
        return dict(defaults)

    total = sum(merged.values())
    if abs(total - 1.0) > 0.01:
        logger.info("%s: los pesos suman %.3f (no se normalizan)", label, total)
    return merged
