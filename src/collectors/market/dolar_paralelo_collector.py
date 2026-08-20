"""
Collector Dólar Paralelo (BCV / Bancos)
========================================

Tasas de cambio de bancos venezolanos vía ``pyDolarVenezuela`` (proveedor
BCV). Devuelve la tasa de cada banco y la tasa oficial del BCV como
``ExchangeRate`` para integración directa en el informe.

El paquete ``pyDolarVenezuela`` ya está en requirements.txt.
"""

import logging
from datetime import datetime, timezone
from typing import List

from src.collectors.errors import CollectorSourceError
from src.models.market import ExchangeRate

logger = logging.getLogger(__name__)

# Mapeo de nombres de pyDolarVenezuela a códigos cortos
_BANK_MAP = {
    "Banesco": "banesco",
    "BanCaribe": "bancaribe",
    "Banco Mercantil": "mercantil",
    "BBVA Provincial": "provincial",
    "Banco Sofitasa": "sofitasa",
    "Otras Instituciones": "otras",
    "Banco Nacional de Crédito BNC": "bnc",
    "Banco Venezolano de Crédito": "bvc_banco",
    "Banco Activo": "activo",
    "N58 Banco Digital": "n58",
    "Bancamiga": "bancamiga",
    "Banco Exterior": "exterior",
    "Dólar estadounidense": "bcv",
}
# Solo queremos tasas USD (excluir euro, yuan, lira, rublo)
_USD_NAMES = set(_BANK_MAP.keys())


def fetch_bancos() -> List[ExchangeRate]:
    """Tasas de cambio de bancos + BCV oficial.

    Returns:
        Lista de ExchangeRate con source=nombre del banco y rate=Bs/USD.
    """
    try:
        from pyDolarVenezuela import Monitor, pages
    except ImportError:
        logger.warning("pyDolarVenezuela no instalado; omitiendo tasas bancarias")
        return []

    now = datetime.now(timezone.utc)
    rates: List[ExchangeRate] = []

    try:
        m = Monitor(provider=pages.BCV)
        monitors = m.get_all_monitors()
    except Exception as exc:  # noqa: BLE001 - fuente opcional
        logger.warning("pyDolarVenezuela BCV no disponible: %s", exc)
        return []

    for mon in monitors:
        name = getattr(mon, "title", "")
        price = getattr(mon, "price", None)
        last_update = getattr(mon, "last_update", None)
        if price is None or name not in _USD_NAMES:
            continue
        try:
            rate_val = float(price)
        except (TypeError, ValueError):
            continue
        # Parsear fecha del monitor
        if isinstance(last_update, datetime):
            dt = last_update.astimezone(timezone.utc) if last_update.tzinfo else last_update.replace(tzinfo=timezone.utc)
        else:
            dt = now
        source = _BANK_MAP.get(name, name.lower().replace(" ", "_"))
        rates.append(ExchangeRate(
            source=source,
            currency="usd",
            rate=rate_val,
            date=dt,
        ))

    if rates:
        logger.info("Dólar paralelo: %d tasas bancarias recogidas", len(rates))
    return rates
