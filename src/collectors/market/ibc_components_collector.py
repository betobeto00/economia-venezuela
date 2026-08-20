"""
Collector de componentes del IBC vía Investing.com
====================================================

Scrapea la página del IBC en Investing.com para obtener las 9 acciones
componentes del índice con sus precios, variaciones y volumen.

Yahoo Finance NO tiene estas acciones, por eso se usa Investing.com.
"""

import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

IBC_URL = "https://es.investing.com/indices/bursatil"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
}


@dataclass
class IBCComponent:
    """Componente del índice IBC."""
    ticker: str
    name: str
    price: float
    change_pct: float
    prev_close: float
    high: float
    low: float
    volume: int


@dataclass
class IBCIndex:
    """Índice IBC completo."""
    value: float
    change: float
    change_pct: float
    date: str
    components: List[IBCComponent]
    gainers: List[IBCComponent]
    losers: List[IBCComponent]


def _parse_number(text: str) -> float:
    """Parsea un número con formato español (1.234,56) a float."""
    if not text:
        return 0.0
    cleaned = text.strip().replace(".", "").replace(",", ".")
    cleaned = re.sub(r"[^\d.\-]", "", cleaned)
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _parse_volume(text: str) -> int:
    """Parsea volumen (516,17K -> 516170)."""
    if not text:
        return 0
    text = text.strip().replace(",", ".")
    multiplier = 1
    if text.upper().endswith("K"):
        multiplier = 1000
        text = text[:-1]
    elif text.upper().endswith("M"):
        multiplier = 1_000_000
        text = text[:-1]
    try:
        return int(float(text) * multiplier)
    except ValueError:
        return 0


def fetch_ibc_from_investing() -> Optional[IBCIndex]:
    """Obtiene datos del IBC y sus componentes desde Investing.com.

    Returns:
        IBCIndex con todos los datos, o None si falla el scraping.
    """
    try:
        resp = httpx.get(IBC_URL, headers=HEADERS, follow_redirects=True, timeout=30)
        if resp.status_code != 200:
            logger.warning("Investing.com responded %d", resp.status_code)
            return None
        text = resp.text
    except Exception as exc:
        logger.warning("Error fetching Investing.com: %s", exc)
        return None

    # Extract main IBC value
    # Pattern: "5.562,55" followed by change info
    ibc_match = re.search(
        r'"lastPrice"[:\s]*"?([\d.,]+)"?', text
    )
    ibc_value = 0.0
    if ibc_match:
        ibc_value = _parse_number(ibc_match.group(1))

    # Try alternative patterns
    if ibc_value == 0:
        # Look for the main price display
        price_patterns = [
            r'"last"[:\s]*"?([\d.,]+)"?',
            r'"close"[:\s]*"?([\d.,]+)"?',
            r'data-test="lastPrice"[^>]*>([\d.,]+)<',
        ]
        for pat in price_patterns:
            m = re.search(pat, text)
            if m:
                ibc_value = _parse_number(m.group(1))
                if ibc_value > 0:
                    break

    # Extract change percentage
    change_pct = 0.0
    change_patterns = [
        r'"changePercent"[:\s]*"?([\d.,\-+]+)"?',
        r'"percentChange"[:\s]*"?([\d.,\-+]+)"?',
    ]
    for pat in change_patterns:
        m = re.search(pat, text)
        if m:
            change_pct = _parse_number(m.group(1))
            break

    # Extract change value
    change_val = 0.0
    change_val_patterns = [
        r'"change"[:\s]*"?([\d.,\-+]+)"?',
    ]
    for pat in change_val_patterns:
        m = re.search(pat, text)
        if m:
            change_val = _parse_number(m.group(1))
            break

    # Extract components from the table
    components = _extract_components_from_html(text)

    # Sort into gainers/losers
    gainers = sorted(
        [c for c in components if c.change_pct > 0],
        key=lambda x: x.change_pct,
        reverse=True,
    )
    losers = sorted(
        [c for c in components if c.change_pct < 0],
        key=lambda x: x.change_pct,
    )

    # Extract date
    date_match = re.search(r'"lastUpdate"[:\s]*"?(\d{2}/\d{2}/\d{4})', text)
    date_str = date_match.group(1) if date_match else ""

    return IBCIndex(
        value=ibc_value,
        change=change_val,
        change_pct=change_pct,
        date=date_str,
        components=components,
        gainers=gainers,
        losers=losers,
    )


def _extract_components_from_html(html: str) -> List[IBCComponent]:
    """Extrae componentes del IBC del HTML de Investing.com."""
    components = []

    # Known IBC components (9 total)
    known_components = {
        "BPV": "Banco Provincial",
        "MPA": "Manufacturas de Papel",
        "CRMa": "Corimon",
        "TDVd": "Nacional Teléfonos de Venezuela",
        "MVZb": "Mercantil Servicios Fin B",
        "MVZa": "Mercantil Servicios Fin A",
        "ENV": "Envases Venezolanos",
        "FVIb": "FVI SACA B",
    }

    # Try to find component data in __NEXT_DATA__ or inline JSON
    next_data_match = re.search(
        r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL
    )
    if next_data_match:
        import json
        try:
            data = json.loads(next_data_match.group(1))
            props = data.get("props", {}).get("pageProps", {})
            # Navigate to find table data
            table_data = _find_components_in_json(props)
            if table_data:
                return table_data
        except (json.JSONDecodeError, KeyError):
            pass

    # Fallback: extract from HTML table rows
    # Look for table rows with stock data
    row_pattern = re.compile(
        r'<tr[^>]*>.*?</tr>', re.DOTALL
    )
    rows = row_pattern.findall(html)

    for row in rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
        if len(cells) >= 5:
            clean_cells = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
            # Check if first cell looks like a ticker
            ticker = clean_cells[0] if clean_cells else ""
            if ticker in known_components:
                price = _parse_number(clean_cells[1]) if len(clean_cells) > 1 else 0
                change_pct = _parse_number(clean_cells[4]) if len(clean_cells) > 4 else 0
                vol = _parse_volume(clean_cells[5]) if len(clean_cells) > 5 else 0
                components.append(IBCComponent(
                    ticker=ticker,
                    name=known_components.get(ticker, ticker),
                    price=price,
                    change_pct=change_pct,
                    prev_close=0.0,
                    high=0.0,
                    low=0.0,
                    volume=vol,
                ))

    # If no components found from HTML, return empty (will need manual update)
    if not components:
        logger.info(
            "No se pudieron extraer componentes del HTML. "
            "Usando datos de fallback."
        )

    return components


def _find_components_in_json(data, depth=0) -> Optional[List[IBCComponent]]:
    """Busca recursivamente datos de componentes en JSON anidado."""
    if depth > 5:
        return None

    if isinstance(data, dict):
        # Check if this dict has component-like data
        if "symbol" in data and ("last" in data or "price" in data):
            return None  # Would need to build component

        for key, val in data.items():
            if isinstance(val, list) and len(val) > 0:
                # Check if list items have component-like structure
                first = val[0]
                if isinstance(first, dict) and any(
                    k in first for k in ["symbol", "ticker", "name"]
                ):
                    return _parse_components_list(val)
            result = _find_components_in_json(val, depth + 1)
            if result:
                return result

    return None


def _parse_components_list(items: List[Dict]) -> List[IBCComponent]:
    """Parsea una lista de dicts en componentes IBC."""
    known_names = {
        "BPV": "Banco Provincial",
        "MPA": "Manufacturas de Papel",
        "CRMa": "Corimon",
        "TDVd": "Nacional Teléfonos de Venezuela",
        "MVZb": "Mercantil Servicios Fin B",
        "MVZa": "Mercantil Servicios Fin A",
        "ENV": "Envases Venezolanos",
        "FVIb": "FVI SACA B",
    }

    components = []
    for item in items:
        ticker = item.get("symbol") or item.get("ticker") or ""
        if ticker in known_names:
            price = float(item.get("last") or item.get("price") or 0)
            change_pct = float(item.get("changePercent") or item.get("percentChange") or 0)
            vol = int(item.get("volume") or 0)
            components.append(IBCComponent(
                ticker=ticker,
                name=known_names.get(ticker, ticker),
                price=price,
                change_pct=change_pct,
                prev_close=float(item.get("prevClose") or 0),
                high=float(item.get("high") or 0),
                low=float(item.get("low") or 0),
                volume=vol,
            ))
    return components
