"""
Collector de componentes del IBC vía Investing.com (Playwright)
================================================================

Scrapea la página del IBC en Investing.com con Playwright para obtener
las 9 acciones componentes del índice con precios, variaciones y volumen.

Yahoo Finance NO tiene estas acciones, por eso se usa Investing.com.
Playwright evita el bloqueo 403 de httpx.
"""

import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

IBC_URL = "https://es.investing.com/indices/bursatil"

KNOWN_COMPONENTS = {
    "BPV": "Banco Provincial",
    "MPA": "Manufacturas de Papel",
    "CRMa": "Corimon",
    "TDVd": "Nacional Teléfonos de Venezuela",
    "MVZb": "Mercantil Servicios Fin B",
    "MVZa": "Mercantil Servicios Fin A",
    "ENV": "Envases Venezolanos",
    "FVIb": "FVI SACA B",
}


@dataclass
class IBCComponent:
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
    value: float
    change: float
    change_pct: float
    date: str
    components: List[IBCComponent]
    gainers: List[IBCComponent]
    losers: List[IBCComponent]


def _parse_es_number(text: str) -> float:
    """Parsea numero espanol (1.234,56) a float."""
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
    """Obtiene datos del IBC y sus componentes desde Investing.com usando Playwright."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning("Playwright no instalado: pip install playwright && playwright install chromium")
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            )
            page.goto(IBC_URL, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(8000)

            # Extract IBC value from body text
            body = page.inner_text("body")
            ibc_value = 0.0
            for line in body.split("\n"):
                line = line.strip()
                m = re.match(r"^[\d.]+,\d{2}$", line)
                if m:
                    ibc_value = _parse_es_number(line)
                    if ibc_value > 100:
                        break

            # Extract tables
            tables = page.query_selector_all("table")
            components = []
            gainers = []
            losers = []

            # Table 1: IBC components (Nombre, Ultimo, Anterior, Maximo, Minimo, % Var., Vol., Fecha)
            if len(tables) > 1:
                rows = tables[1].query_selector_all("tr")
                for row in rows[1:]:  # skip header
                    cells = row.query_selector_all("td")
                    if len(cells) >= 7:
                        cell_text = [c.inner_text().strip() for c in cells]
                        # Parse: BPV\nBanco Provincial SA | 61,45 | 3,81 | 62,17 | 59,00 | 0,00% | 0 | 19/08
                        name_raw = cell_text[0]
                        ticker = ""
                        comp_name = ""
                        for t, n in KNOWN_COMPONENTS.items():
                            if t in name_raw:
                                ticker = t
                                comp_name = n
                                break
                        if not ticker:
                            continue

                        price = _parse_es_number(cell_text[1])
                        prev_close = _parse_es_number(cell_text[2])
                        high = _parse_es_number(cell_text[3])
                        low = _parse_es_number(cell_text[4])
                        change_pct = _parse_es_number(cell_text[5])
                        vol = _parse_volume(cell_text[6])

                        comp = IBCComponent(
                            ticker=ticker,
                            name=comp_name,
                            price=price,
                            change_pct=change_pct,
                            prev_close=prev_close,
                            high=high,
                            low=low,
                            volume=vol,
                        )
                        components.append(comp)

            # Table 2: Ganadores, Table 3: Perdedores
            if len(tables) > 2:
                gainers = _extract_gainers_losers(tables[2], is_gainers=True)
            if len(tables) > 3:
                losers = _extract_gainers_losers(tables[3], is_gainers=False)

            browser.close()

            return IBCIndex(
                value=ibc_value,
                change=0.0,
                change_pct=0.0,
                date="",
                components=components,
                gainers=gainers if gainers else sorted(components, key=lambda x: x.change_pct, reverse=True)[:5],
                losers=losers if losers else sorted(components, key=lambda x: x.change_pct)[:5],
            )

    except Exception as exc:
        logger.warning("Playwright error: %s", exc)
        return None


def _extract_gainers_losers(table, is_gainers: bool = True) -> List[IBCComponent]:
    """Extrae tabla de ganadores/perdedores."""
    components = []
    rows = table.query_selector_all("tr")
    for row in rows[1:]:  # skip header
        cells = row.query_selector_all("td")
        if len(cells) >= 2:
            name_raw = cells[0].inner_text().strip()
            price_data = cells[1].inner_text().strip()

            ticker = ""
            comp_name = ""
            for t, n in KNOWN_COMPONENTS.items():
                if t in name_raw or n.split()[0].lower() in name_raw.lower():
                    ticker = t
                    comp_name = n
                    break

            if not ticker:
                continue

            lines = price_data.split("\n")
            price = _parse_es_number(lines[0]) if lines else 0
            change_pct = _parse_es_number(lines[2]) if len(lines) > 2 else 0

            components.append(IBCComponent(
                ticker=ticker,
                name=comp_name,
                price=price,
                change_pct=change_pct,
                prev_close=0.0,
                high=0.0,
                low=0.0,
                volume=0,
            ))

    return components
