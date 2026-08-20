"""
Collector de componentes del IBC vía Yahoo Finance (Playwright)
================================================================

Yahoo Finance tiene precios ACTUALES de las acciones del IBC (.CA suffix).
Investing.com bloquea 403. yfinance no tiene datos históricos para BVC.
Playwright scrapea Yahoo Finance para obtener precio, cambio y variación.

Las 9 componentes del IBC:
  BPV.CA  - Banco Provincial
  MPA.CA  - Manufacturas de Papel
  CRMa.CA - Corimon
  TDV.CA  - Nacional Teléfonos de Venezuela
  MVZ.CA  - Mercantil Servicios Fin B
  VEN.CA  - Corporación Electroquímica
  BOVEN.CA - Banco Venezolano de Crédito
  BNC.CA  - Banco Nacional de Crédito
  CGA.CA  - Cementos Argos
"""

import logging
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Yahoo Finance tickers for IBC components (.CA = Caracas Exchange)
IBC_YAHOO_TICKERS: Dict[str, str] = {
    "BPV": "Banco Provincial",
    "MPA": "Manufacturas de Papel",
    "CRMa": "Corimon",
    "TDV": "Nacional Teléfonos de Venezuela",
    "MVZ": "Mercantil Servicios Fin B",
    "VEN": "Corporación Electroquímica",
    "BOVEN": "Banco Venezolano de Crédito",
    "BNC": "Banco Nacional de Crédito",
    "CGA": "Cementos Argos",
}


def _parse_number(text: str) -> float:
    """Parsea número español (1.234,56) o inglés (1,234.56) a float."""
    if not text:
        return 0.0
    cleaned = text.strip().replace(" ", "")
    # Detect format: if has comma before dot, it's European
    if "," in cleaned and "." in cleaned:
        if cleaned.index(",") < cleaned.index("."):
            # European: 1.234,56
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            # English: 1,234.56
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        # Could be European (1234,56) or English thousands (1,234)
        parts = cleaned.split(",")
        if len(parts) == 2 and len(parts[1]) <= 2:
            # European decimal: 1234,56
            cleaned = cleaned.replace(",", ".")
        else:
            # English thousands: 1,234
            cleaned = cleaned.replace(",", "")
    cleaned = re.sub(r"[^\d.\-]", "", cleaned)
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def fetch_ibc_components_yahoo() -> List[Dict]:
    """Obtiene precios actuales de las 9 componentes del IBC desde Yahoo Finance.

    Returns:
        Lista de dicts con ticker, name, price, change, change_pct, prev_close.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning("Playwright no instalado: pip install playwright && playwright install chromium")
        return []

    components = []

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

            for ticker, name in IBC_YAHOO_TICKERS.items():
                yahoo_ticker = f"{ticker}.CA"
                try:
                    page = context.new_page()
                    url = f"https://es.finance.yahoo.com/quote/{yahoo_ticker}/"
                    page.goto(url, timeout=20000)
                    page.wait_for_timeout(3000)

                    price = 0.0
                    change = 0.0
                    change_pct = 0.0

                    # Try fin-streamer elements (Yahoo Finance React)
                    price_el = page.query_selector(
                        f'fin-streamer[data-field="regularMarketPrice"][data-symbol="{yahoo_ticker}"]'
                    )
                    if price_el:
                        price = _parse_number(price_el.inner_text())

                    change_el = page.query_selector(
                        f'fin-streamer[data-field="regularMarketChange"][data-symbol="{yahoo_ticker}"]'
                    )
                    if change_el:
                        change = _parse_number(change_el.inner_text())

                    pct_el = page.query_selector(
                        f'fin-streamer[data-field="regularMarketChangePercent"][data-symbol="{yahoo_ticker}"]'
                    )
                    if pct_el:
                        raw_pct = pct_el.inner_text().strip().replace("%", "").replace("(", "").replace(")", "")
                        change_pct = _parse_number(raw_pct)

                    # Fallback: try data-testid
                    if price == 0:
                        price_testid = page.query_selector('[data-testid="qsp-price"]')
                        if price_testid:
                            price = _parse_number(price_testid.inner_text())

                    # Calculate prev_close
                    prev_close = price - change if price > 0 else 0.0

                    if price > 0:
                        components.append({
                            "ticker": ticker,
                            "name": name,
                            "yahoo_ticker": yahoo_ticker,
                            "price": price,
                            "change": change,
                            "change_pct": change_pct,
                            "prev_close": prev_close,
                            "date": datetime.now(timezone.utc).isoformat(),
                        })
                        logger.info("IBC %s: %.2f (%.2f%%)", ticker, price, change_pct)
                    else:
                        logger.warning("IBC %s: no se pudo obtener precio", ticker)

                    page.close()

                except Exception as exc:
                    logger.warning("Error scraping %s: %s", yahoo_ticker, exc)
                    try:
                        page.close()
                    except Exception:
                        pass

            browser.close()

    except Exception as exc:
        logger.warning("Playwright IBC components error: %s", exc)

    logger.info("IBC components obtenidos: %d/9", len(components))
    return components


def fetch_ibc_current_yahoo() -> Optional[Dict]:
    """Obtiene el valor actual del IBC y sus componentes desde Yahoo Finance.

    Returns:
        Dict con value, change, change_pct, components, gainers, losers.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning("Playwright no instalado")
        return None

    ibc_value = 0.0
    ibc_change = 0.0
    ibc_change_pct = 0.0
    components = []

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

            # 1. Get IBC index value
            page = context.new_page()
            url = "https://es.finance.yahoo.com/quote/IBC.CR/"
            page.goto(url, timeout=20000)
            page.wait_for_timeout(3000)

            price_el = page.query_selector('fin-streamer[data-field="regularMarketPrice"]')
            if price_el:
                ibc_value = _parse_number(price_el.inner_text())

            change_el = page.query_selector('fin-streamer[data-field="regularMarketChange"]')
            if change_el:
                ibc_change = _parse_number(change_el.inner_text())

            pct_el = page.query_selector('fin-streamer[data-field="regularMarketChangePercent"]')
            if pct_el:
                raw = pct_el.inner_text().strip().replace("%", "").replace("(", "").replace(")", "")
                ibc_change_pct = _parse_number(raw)

            page.close()

            # 2. Get all components
            components = fetch_ibc_components_yahoo()

            browser.close()

    except Exception as exc:
        logger.warning("Playwright IBC current error: %s", exc)
        return None

    if ibc_value == 0 and not components:
        return None

    # Sort gainers/losers
    sorted_comps = sorted(components, key=lambda x: x.get("change_pct", 0), reverse=True)
    gainers = [c for c in sorted_comps if c.get("change_pct", 0) > 0]
    losers = [c for c in sorted_comps if c.get("change_pct", 0) < 0]

    return {
        "value": ibc_value,
        "change": ibc_change,
        "change_pct": ibc_change_pct,
        "date": datetime.now(timezone.utc).isoformat(),
        "components": components,
        "gainers": gainers,
        "losers": losers,
    }


def save_components_to_db(components: List[Dict]) -> int:
    """Guarda componentes del IBC en la DB.

    Returns:
        Número de registros guardados.
    """
    from src.db.session import get_session
    from src.db.models import IBCComponentORM
    from sqlalchemy import select
    from datetime import date as date_type

    saved = 0
    with get_session() as sess:
        for comp in components:
            ticker = comp["ticker"]
            today = datetime.now(timezone.utc).date()

            # Check if already exists for today
            existing = sess.execute(
                select(IBCComponentORM).where(
                    IBCComponentORM.ticker == ticker,
                    IBCComponentORM.date >= datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc),
                )
            ).scalar_one_or_none()

            if existing:
                # Update
                existing.price = comp["price"]
                existing.change_pct = comp["change_pct"]
                existing.name = comp["name"]
            else:
                # Insert
                orm = IBCComponentORM(
                    ticker=ticker,
                    name=comp["name"],
                    price=comp["price"],
                    change_pct=comp["change_pct"],
                    volume=0,
                    date=datetime.now(timezone.utc),
                )
                sess.add(orm)
                saved += 1

        sess.commit()

    logger.info("IBC components guardados: %d", saved)
    return saved


def run_ibc_components_collection() -> Dict:
    """Ejecuta la colección completa de componentes IBC.

    Returns:
        Dict con resultados de la colección.
    """
    logger.info("=== Iniciando colección de componentes IBC ===")

    components = fetch_ibc_components_yahoo()
    if not components:
        logger.warning("No se obtuvieron componentes del IBC")
        return {"success": False, "components": 0, "message": "No data obtained"}

    saved = save_components_to_db(components)

    return {
        "success": True,
        "components": len(components),
        "saved": saved,
        "tickers": [c["ticker"] for c in components],
        "message": f"{len(components)} componentes obtenidos, {saved} guardados",
    }
