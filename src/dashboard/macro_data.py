"""
Datos macroeconómicos para el dashboard
=========================================

Capa pura (sin Streamlit) que obtiene indicadores macroeconómicos de
fuentes internacionales (World Bank, IMF, CEPAL, OPEP, UNSCEB).
Degradación segura: si una fuente falla, se muestra "—".
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _safe_fetch(fetch_fn, *args, **kwargs):
    """Ejecuta un fetch y devuelve el resultado o None ante fallo."""
    try:
        return fetch_fn(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Macro fetch falló: %s", exc)
        return None


def pib_latest() -> Optional[dict]:
    """Último dato de PIB disponible (prioriza CEPAL > World Bank > IMF)."""
    # Intentar CEPAL (PIB anual en millones USD)
    try:
        from src.collectors.international.cepal_collector import CEPALCollector
        points = CEPALCollector().fetch_gdp()
        if points:
            latest = max(points, key=lambda p: p.period)
            return {
                "value": latest.value,
                "period": latest.period,
                "unit": latest.unit or "millones USD",
                "source": "CEPAL",
            }
    except Exception:
        pass

    # Intentar World Bank
    try:
        from src.collectors.international.worldbank_collector import WorldBankCollector
        points = WorldBankCollector().fetch_gdp()
        if points:
            latest = max(points, key=lambda p: p.year)
            return {
                "value": latest.value,
                "period": str(latest.year),
                "unit": "USD",
                "source": "Banco Mundial",
            }
    except Exception:
        pass

    return None


def pib_crecimiento() -> Optional[dict]:
    """Última tasa de crecimiento del PIB."""
    # Intentar IMF (NGDP_RPCH = crecimiento PIB real)
    try:
        from src.collectors.international.imf_collector import IMFCollector
        points = IMFCollector().fetch_gdp_growth()
        if points:
            latest = max(points, key=lambda p: p.period)
            return {
                "value": latest.value,
                "period": latest.period,
                "unit": latest.unit or "%",
                "source": "FMI",
            }
    except Exception:
        pass

    # Intentar World Bank
    try:
        from src.collectors.international.worldbank_collector import WorldBankCollector
        points = WorldBankCollector().fetch_gdp_growth()
        if points:
            latest = max(points, key=lambda p: p.year)
            return {
                "value": latest.value,
                "period": str(latest.year),
                "unit": "%",
                "source": "Banco Mundial",
            }
    except Exception:
        pass

    return None


def inflacion_internacional() -> Optional[dict]:
    """Última inflación reportada por fuentes internacionales."""
    # IMF (PCPIPCH = inflación IPC)
    try:
        from src.collectors.international.imf_collector import IMFCollector
        points = IMFCollector().fetch_inflation()
        if points:
            latest = max(points, key=lambda p: p.period)
            return {
                "value": latest.value,
                "period": latest.period,
                "unit": latest.unit or "%",
                "source": "FMI",
            }
    except Exception:
        pass

    # World Bank
    try:
        from src.collectors.international.worldbank_collector import WorldBankCollector
        points = WorldBankCollector().fetch_inflation()
        if points:
            latest = max(points, key=lambda p: p.year)
            return {
                "value": latest.value,
                "period": str(latest.year),
                "unit": "%",
                "source": "Banco Mundial",
            }
    except Exception:
        pass

    return None


def produccion_petrolera() -> Optional[dict]:
    """Última producción petrolera de Venezuela (OPEP)."""
    try:
        from src.collectors.international.opec_collector import OPECCollector
        point = OPECCollector().fetch_basket_price()
        if point:
            return {
                "value": point.value,
                "period": point.period,
                "unit": point.unit or "USD/barril",
                "source": "OPEP",
                "indicator": point.indicator,
            }
    except Exception:
        pass

    return None


def gasto_onu() -> Optional[dict]:
    """Último gasto del sistema ONU en Venezuela."""
    try:
        from src.collectors.international.unsceb_collector import UNSCEBCollector
        points = UNSCEBCollector().fetch_venezuela_expenses()
        if points:
            latest = max(points, key=lambda p: p.period)
            return {
                "value": latest.value,
                "period": latest.period,
                "unit": latest.unit or "USD",
                "source": "UNSCEB",
            }
    except Exception:
        pass

    return None


def macro_summary() -> dict:
    """Resumen de todos los indicadores macro."""
    return {
        "pib": pib_latest(),
        "pib_crecimiento": pib_crecimiento(),
        "inflacion_int": inflacion_internacional(),
        "petroleo": produccion_petrolera(),
        "gasto_onu": gasto_onu(),
    }
