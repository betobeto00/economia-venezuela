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

from src.analyzers import reference_values

logger = logging.getLogger(__name__)

CACHE_MAX_AGE_HOURS = 24  # Re-fetch después de 24 horas


# Cache global para evitar múltiples queries a la DB
_macro_cache: Optional[dict] = None
_macro_cache_time: float = 0
# Un refresh forzado ignora el cache (archivo + DB) y va a las fuentes
_bypass_cache: bool = False


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
                entry = {
                    "value": float(orm.value),
                    "period": orm.period,
                    "unit": orm.unit,
                    "source": orm.source,
                    "fetched_at": orm.fetched_at,
                }
                # Un indicador puede tener fila por fuente: manda la más reciente
                previo = result.get(orm.indicator)
                if previo is None or (orm.fetched_at and orm.fetched_at >= previo["fetched_at"]):
                    result[orm.indicator] = entry
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
    if _bypass_cache:
        return None

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
    except Exception as exc:  # noqa: BLE001
        logger.debug("Cache archivo macro no disponible: %s", exc)

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
            except Exception as exc:  # noqa: BLE001
                logger.debug("No se pudo poblar cache archivo macro: %s", exc)
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
    except Exception as exc:  # noqa: BLE001
        logger.debug("CEPAL no disponible para PIB: %s", exc)

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
    except Exception as exc:  # noqa: BLE001
        logger.debug("Banco Mundial no disponible para PIB: %s", exc)

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
    except Exception as exc:  # noqa: BLE001
        logger.debug("FMI no disponible para crecimiento del PIB: %s", exc)

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
    except Exception as exc:  # noqa: BLE001
        logger.debug("Banco Mundial no disponible para crecimiento del PIB: %s", exc)

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
    except Exception as exc:  # noqa: BLE001
        logger.debug("FMI no disponible para inflación: %s", exc)

    # World Bank (InflationPoint no tiene ``value``: la tasa anual va en
    # ``annual_rate``)
    try:
        from src.collectors.international.worldbank_collector import WorldBankCollector
        points = WorldBankCollector().fetch_inflation()
        if points:
            latest = max(points, key=lambda p: p.period)
            value = latest.annual_rate if latest.annual_rate is not None else latest.monthly_rate
            if value is not None:
                result = {
                    "value": value,
                    "period": latest.period,
                    "unit": "%",
                    "source": "Banco Mundial",
                }
                _save_cached("world_bank", "inflacion", value, latest.period, "%")
                return result
    except Exception as exc:  # noqa: BLE001
        logger.debug("Banco Mundial no disponible para inflación: %s", exc)

    return None


def produccion_petrolera() -> Optional[dict]:
    """Precio de referencia del crudo (OPEP → cesta venezolana → Brent local)."""
    cached = _get_cached("petroleo")
    if cached:
        return cached

    fuentes = (
        ("OPEP", "opec", "OPECCollector", "fetch_basket_price"),
        ("PDVSA", "pdvsa", "PDVSACollector", "fetch_basket_price"),
    )
    for nombre, slug, clase, metodo in fuentes:
        try:
            modulo = __import__(
                f"src.collectors.international.{slug}_collector", fromlist=[clase]
            )
            point = getattr(getattr(modulo, clase)(), metodo)()
            if point and point.value > 0:
                result = {
                    "value": point.value,
                    "period": point.period,
                    "unit": point.unit or "USD/barril",
                    "source": nombre,
                    "indicator": point.indicator,
                }
                _save_cached(slug, "petroleo", point.value, point.period, point.unit)
                return result
        except Exception as exc:  # noqa: BLE001
            logger.debug("%s no disponible para crudo: %s", nombre, exc)

    # 3. Brent del CSV local (dato real del proyecto, sin estimaciones)
    price = _brent_from_csv()
    if price is not None:
        period = datetime.now(timezone.utc).strftime("%Y-%m")
        result = {
            "value": price,
            "period": period,
            "unit": "USD/barril",
            "source": "Brent (CSV local)",
        }
        _save_cached("brent_csv", "petroleo", price, period, "USD/barril")
        return result

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
    except Exception as exc:  # noqa: BLE001
        logger.debug("UNSCEB no disponible para gasto ONU: %s", exc)

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
        "reservas": reservas_internacionales(),
    }


def refresh_macro_cache(force: bool = False) -> dict:
    """Refresca todos los indicadores macro desde las APIs.

    Args:
        force: Ignora el cache (archivo y DB) y consulta las fuentes.

    Returns:
        Dict con el resultado de cada fetch.
    """
    global _macro_cache, _macro_cache_time, _bypass_cache
    if force:
        _macro_cache = None
        _macro_cache_time = 0
        _bypass_cache = True
    results = {}
    fetchers = {
        "pib": pib_latest,
        "pib_crecimiento": pib_crecimiento,
        "inflacion_int": inflacion_internacional,
        "petroleo": produccion_petrolera,
        "gasto_onu": gasto_onu,
        "reservas": reservas_internacionales,
    }
    try:
        for name, fn in fetchers.items():
            try:
                result = fn()
                results[name] = result is not None
            except Exception as exc:
                logger.warning("Refresh %s falló: %s", name, exc)
                results[name] = False
    finally:
        _bypass_cache = False
    return results


# ─── Datos para Balanza de Pagos ────────────────────────────────────────────

def _brent_from_csv() -> Optional[float]:
    """Último precio del Brent en el CSV histórico local (o ``None``)."""
    import csv
    from pathlib import Path

    csv_path = Path(__file__).resolve().parent.parent.parent / "data" / "cvs.xls" / "Datos históricos Petróleo Brent.csv"
    if not csv_path.exists():
        return None
    try:
        with open(csv_path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter=",")
            for row in reader:
                # Primera fila = más reciente
                raw = row.get("Último", "") or row.get("ltimo", "") or row.get("\u00daltimo", "")
                if not raw:
                    vals = list(row.values())
                    if len(vals) > 1:
                        raw = vals[1]
                if raw:
                    price = float(raw.replace(".", "").replace(",", "."))
                    if price > 0:
                        return price
    except Exception as exc:  # noqa: BLE001
        logger.debug("CSV petróleo Brent no disponible: %s", exc)
    return None


def oil_price_current() -> float:
    """Precio actual del petróleo Brent desde el CSV local o fallback.

    Returns:
        Precio en USD/barril.
    """
    price = _brent_from_csv()
    if price is not None:
        return price

    # Fallback: intentar OPEP collector
    try:
        from src.collectors.international.opec_collector import OPECCollector
        point = OPECCollector().fetch_basket_price()
        if point and point.value > 0:
            return point.value
    except Exception as exc:  # noqa: BLE001
        logger.debug("OPEP no disponible para precio del crudo: %s", exc)

    return reference_values.fallback(
        "oil_price_usd",
        context="oil_price_current",
        reason="CSV Brent y OPEP no disponibles",
    )


def oil_production_ve() -> float:
    """Producción petrolera de Venezuela (mbd) desde OPEP o estimación.

    Returns:
        Producción en millones de barriles diarios.
    """
    # Intentar cache en DB
    cached = _get_cached("produccion_ve")
    if cached:
        return cached["value"]

    # Estimación de referencia: ~1.08 mbd (OPEP 2025-2026)
    return reference_values.fallback(
        "oil_production_mbd", context="oil_production_ve"
    )


def reservas_internacionales() -> Optional[dict]:
    """Último dato de reservas internacionales del BCV (USD)."""
    cached = _get_cached("reservas")
    if cached:
        return cached

    try:
        from src.collectors.official.bcv_reserves_collector import BCVReservesCollector
        point = BCVReservesCollector().fetch_reserves()
        if point and point.value > 0:
            result = {
                "value": point.value,
                "period": point.period,
                "unit": point.unit or "USD",
                "source": "BCV",
            }
            _save_cached("bcv", "reservas", point.value, point.period, point.unit)
            return result
    except Exception as exc:  # noqa: BLE001
        logger.debug("BCV no disponible para reservas: %s", exc)

    return None


def reserves_usd() -> float:
    """Reservas internacionales de Venezuela (USD) desde DB o estimación.

    Returns:
        Reservas en USD.
    """
    data = reservas_internacionales()
    if data:
        return data["value"]

    return reference_values.fallback("reserves_usd", context="reserves_usd")


def imports_monthly() -> float:
    """Importaciones mensuales estimadas de Venezuela (USD).

    Returns:
        Importaciones mensuales en USD.
    """
    cached = _get_cached("importaciones")
    if cached:
        return cached["value"]

    # Estimación: ~$2B/mes según CEPAL/FMI
    return reference_values.fallback(
        "imports_monthly_usd", context="imports_monthly"
    )


def fiscal_deficit_pct() -> float:
    """Déficit fiscal como % del PIB.

    Returns:
        Déficit en porcentaje.
    """
    cached = _get_cached("deficit_fiscal")
    if cached:
        return cached["value"]

    # Estimación FMI: ~5.8% del PIB
    return reference_values.fallback(
        "fiscal_deficit_pct", context="fiscal_deficit_pct"
    )


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
    return reference_values.fallback("gdp_usd", context="gdp_usd")


def total_debt_usd() -> float:
    """Deuda pública total de Venezuela en USD.

    Returns:
        Deuda total en USD.
    """
    cached = _get_cached("deuda_total")
    if cached:
        return cached["value"]

    # Estimación: ~$150B deuda total reportada
    return reference_values.fallback("total_debt_usd", context="total_debt_usd")
