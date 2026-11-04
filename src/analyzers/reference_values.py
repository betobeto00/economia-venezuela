"""Valores de referencia y supuestos compartidos
================================================

Un único lugar para las cifras que se usan cuando una fuente no responde y
para los supuestos de estructura que alimentan varios analizadores.

Cada uso de un valor de referencia se registra con ``fallback()``: deja un
``WARNING`` en el log (una vez por combinación clave/contexto) y queda
disponible en ``degraded_report()`` para que los informes declaren qué cifras
no fueron observadas. Así un informe no puede publicar una estimación como si
fuera un dato medido.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

#: Cifras de referencia (no observadas) usadas cuando la fuente falla.
#: Si cambia una, se cambia aquí y queda registrada en los informes.
FALLBACKS: Dict[str, float] = {
    "oil_price_usd": 70.0,
    "oil_production_mbd": 1.08,
    "reserves_usd": 12.7e9,
    "imports_monthly_usd": 2.0e9,
    "gdp_usd": 94e9,
    "total_debt_usd": 150e9,
    "fiscal_deficit_pct": 5.8,
    "exchange_gap_pct": 30.0,
    "monthly_inflation_pct": 10.0,
}

FALLBACK_SOURCE = "referencia interna (no observado)"

#: Supuestos de composición de la deuda. No provienen de una fuente única: se
#: documentan aquí para que dashboard e informes usen el mismo criterio (antes
#: convivían 0.75 en app.py/periodic.py y 0.7 en sustainability_panel.py).
EXTERNAL_DEBT_SHARE = 0.75
SHORT_TERM_DEBT_SHARE = 0.25
MEDIUM_TERM_DEBT_SHARE = 0.42
LONG_TERM_DEBT_SHARE = 0.33

_degraded: Dict[str, Dict] = {}


def fallback(key: str, *, context: str = "", reason: Optional[str] = None) -> float:
    """Devuelve el valor de referencia ``key`` y registra su uso.

    Args:
        key: Clave de :data:`FALLBACKS`.
        context: Módulo/función que cae al valor de referencia (para el log y
            para el bloque de proveniencia del informe).
        reason: Motivo legible (p. ej. ``"CSV Brent y OPEP no disponibles"``).

    Returns:
        El valor de referencia configurado para ``key``.

    Raises:
        KeyError: Si ``key`` no está definida en :data:`FALLBACKS`.
    """
    if key not in FALLBACKS:
        raise KeyError(f"Valor de referencia desconocido: {key}")

    value = FALLBACKS[key]
    entry = _degraded.get(key)
    first_use = entry is None or (context and context not in entry["contexts"])
    if entry is None:
        entry = {
            "key": key,
            "value": value,
            "count": 0,
            "contexts": [],
            "reason": reason,
        }
        _degraded[key] = entry

    entry["count"] += 1
    if context and context not in entry["contexts"]:
        entry["contexts"].append(context)
    if reason:
        entry["reason"] = reason

    msg = "Fallback %s=%s en %s%s"
    detail = f" ({reason})" if reason else ""
    if first_use:
        logger.warning(msg, key, f"{value:g}", context or "-", detail)
    else:
        logger.debug(msg, key, f"{value:g}", context or "-", detail)
    return value


def degraded_report() -> List[Dict]:
    """Cifras de referencia usadas desde el último ``reset_degraded()``.

    Returns:
        Lista de dicts con ``key``, ``value``, ``count``, ``contexts`` y
        ``reason``. Vacía si no se usó ningún valor de referencia.
    """
    return [
        {**entry, "contexts": list(entry["contexts"])}
        for entry in _degraded.values()
    ]


def is_degraded() -> bool:
    """True si se usó al menos un valor de referencia."""
    return bool(_degraded)


def reset_degraded() -> None:
    """Limpia el registro (al inicio de cada informe o corrida)."""
    _degraded.clear()
