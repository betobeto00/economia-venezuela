"""
Datos macroeconómicos para el dashboard (con cache en DB)
==========================================================

Capa pura (sin Streamlit) que obtiene indicadores macroeconómicos de
fuentes internacionales (World Bank, IMF, CEPAL, OPEP, UNSCEB).

Usa cache en DB para evitar fetch lentos en cada carga del dashboard.
Los datos se refrescan cuando tienen más de 24 horas de antigüedad.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

CACHE_MAX_AGE_HOURS = 24  # Re-fetch después de 24 horas


# Cache global para evitar múltiples queries a la DB
_macro_cache: Optional[dict] = None
_macro_cache_time: float = 0


def _load_macro_cache() -> dict:
    """Carga todos los indicadores macro de la DB en memoria."""
    global _macro_cache, _macro_cache_time
    import time

    # Reusar cache por 5 minutos (evita queries a la DB)
    if _macro_cache is not None and (time.time() - _macro_cache_time) < 300:
        return _macro_cache

    try:
        from sqlalchemy import select
        from src.db.models import MacroIndicatorORM
        from src.db.session import get_session

        session = get_session()
        try:
            stmt = select(MacroIndicatorORM).order_by(MacroIndicatorORM.indicator)
            result = {}
            for orm in session.scalars(stmt):
                result[orm.indicator] = {
                    "value": float(orm.value),
                    "period": orm.period,
                    "unit": orm.unit,
                    "source": orm.source,
                    "fetched_at": orm.fetched_at,
                }
            _macro_cache = result
            _macro_cache_time = time.time()
            return result
        finally:
            session.close()
    except Exception as exc:
        logger.debug("Cache DB no disponible: %s", exc)
        return {}


def _get_cached(indicator: str) -> Optional[dict]:
    """Obtiene un indicador del cache (archivo → DB → None)."""
    # 1. Intentar cache en archivo (más rápido)
    try:
        from src.cache.manager import get_cached_api
        file_data = get_cached_api(f"macro_{indicator}")
        if file_data:
            logger.debug("Cache HIT (archivo): %s", indicator)
            # Ensure fetched_at is datetime
            if isinstance(file_data.get("fetched_at"), str):
                file_data["fetched_at"] = datetime.fromisoformat(file_data["fetched_at"])
            return file_data
    except Exception:
        pass

    # 2. Intentar cache en DB
    cache = _load_macro_cache()
    result = cache.get(indicator)
    if result is not None:
        age_hours = (
            datetime.now(timezone.utc) - result["fetched_at"]
        ).total_seconds() / 3600
        if age_hours <= CACHE_MAX_AGE_HOURS:
            # Populate file cache for next time
            try:
                from src.cache.manager import cache_api_response
                cache_api_response(f"macro_{indicator}", result, ttl_hours=24)
            except Exception:
                pass
            return result

    return None


def _save_cached(source: str, indicator: str, value: float, period: str, unit: str = None):
    """Guarda un indicador en cache (DB + archivo)."""
    result = {
        "value": value,
        "period": period,
        "unit": unit,
        "source": source,
        "fetched_at": datetime.now(timezone.utc),
    }

    # 1. Guardar en DB
    try:
        from src.db.repositories import MacroRepository
        from src.db.session import session_scope

        with session_scope() as session:
            repo = MacroRepository(session)
            repo.save_indicator(source, indicator, value, period, unit)
    except Exception as exc:
        logger.debug("No se pudo guardar en DB: %s", exc)

    # 2. Guardar en archivo (TTL 24h)
    try:
        from src.cache.manager import cache_api_response
        cache_api_response(f"macro_{indicator}", result, ttl_hours=24)
    except Exception as exc:
        logger.debug("No se pudo guardar en archivo: %s", exc)


def _safe_fetch(fetch_fn, *args, **kwargs):
    """Ejecuta un fetch y devuelve el resultado o None ante fallo."""
    try:
        return fetch_fn(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Macro fetch falló: %s", exc)
        return None


def pib_latest() -> Optional[dict]:
    """Último dato de PIB disponible (prioriza CEPAL > World Bank > IMF)."""
    # 1. Intentar cache
    cached = _get_cached("pib")
    if cached:
        return cached

    # 2. Intentar CEPAL
    try:
        from src.collectors.international.cepal_collector import CEPALCollector
        points = CEPALCollector().fetch_gdp()
        if points:
            latest = max(points, key=lambda p: p.period)
            result = {
                "value": latest.value,
                "period": latest.period,
                "unit": latest.unit or "millones USD",
                "source": "CEPAL",
            }
            _save_cached("cepal", "pib", latest.value, latest.period, latest.unit)
            return result
    except Exception:
        pass

    # 3. Intentar World Bank
    try:
        from src.collectors.international.worldbank_collector import WorldBankCollector
        points = WorldBankCollector().fetch_gdp()
        if points:
            latest = max(points, key=lambda p: p.year)
            result = {
                "value": latest.value,
                "period": str(latest.year),
                "unit": "USD",
                "source": "Banco Mundial",
            }
            _save_cached("world_bank", "pib", latest.value, str(latest.year))
            return result
    except Exception:
        pass

    return None


def pib_crecimiento() -> Optional[dict]:
    """Última tasa de crecimiento del PIB."""
    cached = _get_cached("pib_crecimiento")
    if cached:
        return cached

    # Intentar IMF
    try:
        from src.collectors.international.imf_collector import IMFCollector
        points = IMFCollector().fetch_gdp_growth()
        if points:
            latest = max(points, key=lambda p: p.period)
            result = {
                "value": latest.value,
                "period": latest.period,
                "unit": latest.unit or "%",
                "source": "FMI",
            }
            _save_cached("imf", "pib_crecimiento", latest.value, latest.period, latest.unit)
            return result
    except Exception:
        pass

    # Intentar World Bank
    try:
        from src.collectors.international.worldbank_collector import WorldBankCollector
        points = WorldBankCollector().fetch_gdp_growth()
        if points:
            latest = max(points, key=lambda p: p.year)
            result = {
                "value": latest.value,
                "period": str(latest.year),
                "unit": "%",
                "source": "Banco Mundial",
            }
            _save_cached("world_bank", "pib_crecimiento", latest.value, str(latest.year))
            return result
    except Exception:
        pass

    return None


def inflacion_internacional() -> Optional[dict]:
    """Última inflación reportada por fuentes internacionales."""
    cached = _get_cached("inflacion")
    if cached:
        return cached

    # IMF
    try:
        from src.collectors.international.imf_collector import IMFCollector
        points = IMFCollector().fetch_inflation()
        if points:
            latest = max(points, key=lambda p: p.period)
            result = {
                "value": latest.value,
                "period": latest.period,
                "unit": latest.unit or "%",
                "source": "FMI",
            }
            _save_cached("imf", "inflacion", latest.value, latest.period, latest.unit)
            return result
    except Exception:
        pass

    # World Bank
    try:
        from src.collectors.international.worldbank_collector import WorldBankCollector
        points = WorldBankCollector().fetch_inflation()
        if points:
            latest = max(points, key=lambda p: p.year)
            result = {
                "value": latest.value,
                "period": str(latest.year),
                "unit": "%",
                "source": "Banco Mundial",
            }
            _save_cached("world_bank", "inflacion", latest.value, str(latest.year))
            return result
    except Exception:
        pass

    return None


def produccion_petrolera() -> Optional[dict]:
    """Última producción petrolera de Venezuela (OPEP)."""
    cached = _get_cached("petroleo")
    if cached:
        return cached

    try:
        from src.collectors.international.opec_collector import OPECCollector
        point = OPECCollector().fetch_basket_price()
        if point:
            result = {
                "value": point.value,
                "period": point.period,
                "unit": point.unit or "USD/barril",
                "source": "OPEP",
                "indicator": point.indicator,
            }
            _save_cached("opec", "petroleo", point.value, point.period, point.unit)
            return result
    except Exception:
        pass

    return None


def gasto_onu() -> Optional[dict]:
    """Último gasto del sistema ONU en Venezuela."""
    cached = _get_cached("gasto_onu")
    if cached:
        return cached

    try:
        from src.collectors.international.unsceb_collector import UNSCEBCollector
        points = UNSCEBCollector().fetch_venezuela_expenses()
        if points:
            latest = max(points, key=lambda p: p.period)
            result = {
                "value": latest.value,
                "period": latest.period,
                "unit": latest.unit or "USD",
                "source": "UNSCEB",
            }
            _save_cached("unsceb", "gasto_onu", latest.value, latest.period, latest.unit)
            return result
    except Exception:
        pass

    return None


def macro_summary() -> dict:
    """Resumen de todos los indicadores macro (con cache en DB + archivo)."""
    # Pre-load DB cache once (evita múltiples queries)
    _load_macro_cache()

    return {
        "pib": pib_latest(),
        "pib_crecimiento": pib_crecimiento(),
        "inflacion_int": inflacion_internacional(),
        "petroleo": produccion_petrolera(),
        "gasto_onu": gasto_onu(),
    }


def refresh_macro_cache() -> dict:
    """Fuerza el refresh de todos los indicadores macro desde las APIs.

    Returns:
        Dict con el resultado de cada fetch.
    """
    results = {}
    fetchers = {
        "pib": pib_latest,
        "pib_crecimiento": pib_crecimiento,
        "inflacion_int": inflacion_internacional,
        "petroleo": produccion_petrolera,
        "gasto_onu": gasto_onu,
    }
    for name, fn in fetchers.items():
        try:
            result = fn()
            results[name] = result is not None
        except Exception as exc:
            logger.warning("Refresh %s falló: %s", name, exc)
            results[name] = False
    return results


# ─── Datos para Balanza de Pagos ────────────────────────────────────────────

def oil_price_current() -> float:
    """Precio actual del petróleo Brent desde el CSV local o fallback.

    Returns:
        Precio en USD/barril.
    """
    import csv
    from pathlib import Path

    csv_path = Path(__file__).resolve().parent.parent.parent / "data" / "cvs.xls" / "Datos históricos Petróleo Brent.csv"
    if csv_path.exists():
        try:
            with open(csv_path, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f, delimiter=",")
                for row in reader:
                    # Primera fila = más reciente
                    # Try multiple header encodings for the price column
                    raw = row.get("Último", "") or row.get("ltimo", "") or row.get("\u00daltimo", "")
                    if not raw:
                        # Fallback: use second column (price)
                        vals = list(row.values())
                        if len(vals) > 1:
                            raw = vals[1]
                    if raw:
                        price = float(raw.replace(".", "").replace(",", "."))
                        if price > 0:
                            return price
        except Exception as exc:
            logger.debug("CSV petróleo Brent no disponible: %s", exc)

    # Fallback: intentar OPEP collector
    try:
        from src.collectors.international.opec_collector import OPECCollector
        point = OPECCollector().fetch_basket_price()
        if point and point.value > 0:
            return point.value
    except Exception:
        pass

    return 70.0  # Fallback razonable


def oil_production_ve() -> float:
    """Producción petrolera de Venezuela (mbd) desde OPEP o estimación.

    Returns:
        Producción en millones de barriles diarios.
    """
    # Intentar cache en DB
    cached = _get_cached("produccion_ve")
    if cached:
        return cached["value"]

    # Fallback: estimación basada en datos públicos recientes
    # Venezuela: ~1.08 mbd (2025-2026, estimación OPEP)
    return 1.08


def reserves_usd() -> float:
    """Reservas internacionales de Venezuela (USD) desde DB o estimación.

    Returns:
        Reservas en USD.
    """
    cached = _get_cached("reservas")
    if cached:
        return cached["value"]

    # Estimación basada en datos públicos recientes
    # BCV reporta ~$5-6B en reservas (oro + divisas)
    return 5.5e9  # ~5,500 millones USD


def imports_monthly() -> float:
    """Importaciones mensuales estimadas de Venezuela (USD).

    Returns:
        Importaciones mensuales en USD.
    """
    cached = _get_cached("importaciones")
    if cached:
        return cached["value"]

    # Estimación: ~$2B/mes según CEPAL/FMI
    return 2.0e9


def fiscal_deficit_pct() -> float:
    """Déficit fiscal como % del PIB.

    Returns:
        Déficit en porcentaje.
    """
    cached = _get_cached("deficit_fiscal")
    if cached:
        return cached["value"]

    # Estimación FMI: ~5.8% del PIB
    return 5.8


def gdp_usd() -> float:
    """PIB de Venezuela en USD.

    Returns:
        PIB en USD.
    """
    cached = _get_cached("pib")
    if cached:
        # El valor puede estar en millones de USD
        val = cached["value"]
        unit = (cached.get("unit") or "").lower()
        if "millon" in unit:
            return val * 1e6
        return val

    # Estimación FMI: ~$94B (2025-2026)
    return 94e9


def total_debt_usd() -> float:
    """Deuda pública total de Venezuela en USD.

    Returns:
        Deuda total en USD.
    """
    cached = _get_cached("deuda_total")
    if cached:
        return cached["value"]

    # Estimación: ~$150B deuda total reportada
    return 150e9
