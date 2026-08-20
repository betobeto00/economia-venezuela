"""
Scraper histórico del IBC vía Playwright (Investing.com)
========================================================

Investing.com bloquea requests HTTP directos (403). Usa Playwright con
un browser real para obtener datos históricos del IBC y sus componentes.

Requiere: `playwright install chromium`
"""

import logging
import re
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger(__name__)

IBC_HISTORY_URL = "https://es.investing.com/indices/bursatil-historical-data"
IBC_COMPONENTS_URL = "https://es.investing.com/indices/bursatil"

# Known IBC component tickers
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


def fetch_ibc_current_playwright() -> Optional[dict]:
    """Obtiene el valor actual del IBC y componentes usando Playwright.

    Returns:
        Dict con value, change, change_pct, components, o None si falla.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning("Playwright no instalado. Ejecuta: pip install playwright && playwright install chromium")
        return None

    result = {"value": 0.0, "change": 0.0, "change_pct": 0.0, "components": []}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                ),
                locale="es-VE",
            )
            page = context.new_page()

            # 1. Get main IBC value
            page.goto(IBC_COMPONENTS_URL, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)  # Wait for JS rendering

            # Extract IBC value from the page
            try:
                # Try to find the last price element
                price_el = page.locator('[data-test="lastPrice"]').first
                if price_el.count() > 0:
                    result["value"] = _parse_number(price_el.inner_text())
            except Exception:
                pass

            if result["value"] == 0:
                # Fallback: search for the price in the page content
                content = page.content()
                patterns = [
                    r'"lastPrice"[:\s]*"?([\d.,]+)"?',
                    r'"last"[:\s]*"?([\d.,]+)"?',
                ]
                for pat in patterns:
                    m = re.search(pat, content)
                    if m:
                        result["value"] = _parse_number(m.group(1))
                        if result["value"] > 0:
                            break

            # Extract change
            try:
                change_el = page.locator('[data-test="priceChange"]').first
                if change_el.count() > 0:
                    result["change"] = _parse_number(change_el.inner_text())
            except Exception:
                pass

            # Extract change percent
            try:
                pct_el = page.locator('[data-test="percentChange"]').first
                if pct_el.count() > 0:
                    result["change_pct"] = _parse_number(pct_el.inner_text())
            except Exception:
                pass

            # 2. Get components from the table
            try:
                rows = page.locator("table tbody tr").all()
                for row in rows:
                    cells = row.locator("td").all()
                    if len(cells) >= 5:
                        ticker_text = cells[0].inner_text().strip()
                        # Check if it's a known component
                        for tk, name in KNOWN_COMPONENTS.items():
                            if tk.lower() in ticker_text.lower() or name.lower() in ticker_text.lower():
                                price = _parse_number(cells[1].inner_text()) if len(cells) > 1 else 0
                                change_pct = _parse_number(cells[4].inner_text()) if len(cells) > 4 else 0
                                vol_text = cells[5].inner_text() if len(cells) > 5 else "0"
                                vol = _parse_volume(vol_text)
                                result["components"].append({
                                    "ticker": tk,
                                    "name": name,
                                    "price": price,
                                    "change_pct": change_pct,
                                    "volume": vol,
                                })
                                break
            except Exception as exc:
                logger.debug("Error extracting components: %s", exc)

            browser.close()

    except Exception as exc:
        logger.warning("Playwright IBC scrape falló: %s", exc)
        return None

    if result["value"] == 0:
        return None

    return result


def fetch_ibc_history_playwright(
    months: int = 6,
) -> List[dict]:
    """Obtiene datos históricos del IBC desde Investing.com usando Playwright.

    Args:
        months: Meses de historial a obtener.

    Returns:
        Lista de dicts con date, value, change, change_pct.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning("Playwright no instalado")
        return []

    results = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                ),
                locale="es-VE",
            )
            page = context.new_page()

            page.goto(IBC_HISTORY_URL, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(5000)  # Wait for JS rendering

            # Try to get the historical data table
            content = page.content()

            # Look for table rows with date and price
            # Investing.com historical data table format:
            # Date | Close | Open | High | Low | Volume | Change %
            row_pattern = re.compile(
                r'<tr[^>]*>\s*<td[^>]*>(\d{2}/\d{2}/\d{4})</td>'  # date
                r'\s*<td[^>]*>([\d.,]+)</td>'  # close
                r'\s*<td[^>]*>([\d.,]+)</td>'  # open
                r'\s*<td[^>]*>([\d.,]+)</td>'  # high
                r'\s*<td[^>]*>([\d.,]+)</td>'  # low
                r'\s*<td[^>]*>([\d.,]*[KMB]?)</td>'  # volume
                r'\s*<td[^>]*>([\d.,\-+]+)%?</td>',  # change %
                re.DOTALL,
            )

            matches = row_pattern.findall(content)
            for match in matches:
                date_str, close, open_p, high, low, vol, change_pct = match
                try:
                    date = datetime.strptime(date_str, "%d/%m/%Y").replace(tzinfo=timezone.utc)
                    results.append({
                        "date": date,
                        "value": _parse_number(close),
                        "open": _parse_number(open_p),
                        "high": _parse_number(high),
                        "low": _parse_number(low),
                        "change_pct": _parse_number(change_pct),
                    })
                except ValueError:
                    continue

            browser.close()

    except Exception as exc:
        logger.warning("Playwright IBC history scrape falló: %s", exc)

    return results


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
