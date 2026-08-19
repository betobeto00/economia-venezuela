"""
Collector Binance P2P
=======================

Tasa USDT/VES del mercado P2P de Binance (proxy del dólar paralelo
digital). Usa el endpoint público ``/bapi/c2c/.../adv/search`` (POST, sin
autenticación). Toma la mejor oferta de venta (SELL) de USDT a bolívares.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from src.collectors.errors import CollectorSourceError
from src.collectors.http import http_post_json
from src.config import settings
from src.models.market import ExchangeRate

logger = logging.getLogger(__name__)


class BinanceCollector:
    """Tasa USDT/VES del mercado P2P de Binance."""

    def __init__(self, p2p_url: Optional[str] = None):
        self.p2p_url = p2p_url or settings.BINANCE_P2P_URL

    def fetch_usdt_rate(self, asset: str = "USDT", fiat: str = "VES") -> ExchangeRate:
        """Mejor oferta de venta de ``asset`` a ``fiat``.

        ``tradeType=SELL`` → anuncios de vendedores que venden USDT a
        bolívares (la tasa de venta es la que paga un comprador).
        """
        payload = http_post_json(
            self.p2p_url,
            json={
                "asset": asset,
                "fiat": fiat,
                "merchantCheck": False,
                "page": 1,
                "rows": 1,
                "payTypes": [],
                "tradeType": "SELL",
            },
        )
        data = payload.get("data") if isinstance(payload, dict) else None
        if not data or not isinstance(data, list) or not data:
            raise CollectorSourceError("Binance P2P: sin ofertas disponibles")

        try:
            rate = float(data[0]["adv"]["price"])
        except (KeyError, TypeError, ValueError) as exc:
            raise CollectorSourceError(f"Binance P2P: respuesta no parseable: {exc}") from exc

        return ExchangeRate(
            source="binance",
            currency="usdt",
            rate=rate,
            date=datetime.now(timezone.utc).replace(tzinfo=None),
        )