"""
Collector de IBC histórico (datosmacro) + Componentes (Yahoo Finance Playwright)
=================================================================================

Fuente IBC índice: datosmacro.expansion.com (HTML scraping, sin auth)
Fuente componentes: Yahoo Finance via Playwright (precio actual de cada acción BVC)

Datosmacro provee ~22 registros/día × 6 meses = ~126 registros del IBC.
Yahoo Finance provee precio actual de las 9 componentes (.CA suffix).
"""

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

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


def _parse_es_number(text: str) -> float:
    """Parsea número español (1.234,56) a float."""
    if not text:
        return 0.0
    cleaned = text.strip().replace("%", "").replace("+", "")
    # European format: 1.234,56
    if "," in cleaned and "." in cleaned:
        if cleaned.index(",") < cleaned.index("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        parts = cleaned.split(",")
        if len(parts) == 2 and len(parts[1]) <= 2:
            cleaned = cleaned.replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    cleaned = re.sub(r"[^\d.\-]", "", cleaned)
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _parse_date_es(date_str: str) -> Optional[datetime]:
    """Parsea fecha española DD/MM/YYYY a datetime UTC."""
    try:
        return datetime.strptime(date_str, "%d/%m/%Y").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


# ─── IBC Índice desde datosmacro ─────────────────────────────────────────────


def fetch_ibc_history_datosmacro(months: int = 6) -> List[Dict]:
    """Obtiene datos históricos del IBC desde datosmacro.expansion.com.

    Args:
        months: Número de meses hacia atrás (default 6).

    Returns:
        Lista de dicts con date, value, change_pct.
    """
    all_data = []

    for months_ago in range(months):
        date = datetime.now() - timedelta(days=30 * months_ago)
        dr = date.strftime("%Y-%m")

        url = f"https://datosmacro.expansion.com/bolsa/venezuela?dr={dr}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                logger.warning("datosmacro %s: HTTP %d", dr, resp.status_code)
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            tables = soup.find_all("table")

            if len(tables) < 2:
                continue

            rows = tables[1].find_all("tr")
            count = 0
            for row in rows[1:]:  # skip header
                cells = row.find_all("td")
                if len(cells) >= 3:
                    fecha = cells[0].get_text(strip=True)
                    puntos = cells[1].get_text(strip=True)
                    var_pct = cells[2].get_text(strip=True)

                    if "/" not in fecha:
                        continue

                    dt = _parse_date_es(fecha)
                    if dt is None:
                        continue

                    value = _parse_es_number(puntos)
                    change_pct = _parse_es_number(var_pct)

                    if value > 0:
                        all_data.append({
                            "date": dt,
                            "value": value,
                            "change_pct": change_pct,
                        })
                        count += 1

            logger.info("datosmacro %s: %d registros", dr, count)

        except Exception as exc:
            logger.warning("datosmacro %s error: %s", dr, exc)

    # Deduplicate by date
    seen = set()
    unique = []
    for d in all_data:
        key = d["date"].strftime("%Y-%m-%d")
        if key not in seen:
            seen.add(key)
            unique.append(d)

    logger.info("IBC histórico total: %d registros únicos (de %d)", len(unique), len(all_data))
    return unique


def save_ibc_history_to_db(records: List[Dict]) -> int:
    """Guarda registros del IBC histórico en la DB.

    Returns:
        Número de registros insertados.
    """
    from src.db.session import get_session
    from src.db.models import IBCIndexORM
    from sqlalchemy import select

    inserted = 0
    with get_session() as sess:
        for rec in records:
            dt = rec["date"]

            # Check if already exists
            existing = sess.execute(
                select(IBCIndexORM).where(IBCIndexORM.date == dt)
            ).scalar_one_or_none()

            if existing:
                # Update value if different
                if abs(float(existing.value) - rec["value"]) > 0.01:
                    existing.value = rec["value"]
                    existing.change_pct = rec["change_pct"]
            else:
                orm = IBCIndexORM(
                    date=dt,
                    value=rec["value"],
                    change=0.0,
                    change_pct=rec["change_pct"],
                )
                sess.add(orm)
                inserted += 1

        sess.commit()

    logger.info("IBC histórico guardado: %d insertados", inserted)
    return inserted


# ─── IBC Componentes desde Yahoo Finance (Playwright) ────────────────────────


def fetch_ibc_components_yahoo() -> List[Dict]:
    """Obtiene precios actuales de las 9 componentes del IBC desde Yahoo Finance.

    Returns:
        Lista de dicts con ticker, name, price, change, change_pct.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning("Playwright no instalado")
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

                    # fin-streamer elements
                    price_el = page.query_selector(
                        f'fin-streamer[data-field="regularMarketPrice"][data-symbol="{yahoo_ticker}"]'
                    )
                    if price_el:
                        price = _parse_es_number(price_el.inner_text())

                    change_el = page.query_selector(
                        f'fin-streamer[data-field="regularMarketChange"][data-symbol="{yahoo_ticker}"]'
                    )
                    if change_el:
                        change = _parse_es_number(change_el.inner_text())

                    pct_el = page.query_selector(
                        f'fin-streamer[data-field="regularMarketChangePercent"][data-symbol="{yahoo_ticker}"]'
                    )
                    if pct_el:
                        raw = pct_el.inner_text().strip().replace("%", "").replace("(", "").replace(")", "")
                        change_pct = _parse_es_number(raw)

                    # Fallback: data-testid
                    if price == 0:
                        price_testid = page.query_selector('[data-testid="qsp-price"]')
                        if price_testid:
                            price = _parse_es_number(price_testid.inner_text())

                    if price > 0:
                        components.append({
                            "ticker": ticker,
                            "name": name,
                            "yahoo_ticker": yahoo_ticker,
                            "price": price,
                            "change": change,
                            "change_pct": change_pct,
                            "prev_close": price - change if price > 0 else 0.0,
                            "date": datetime.now(timezone.utc),
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

    logger.info("IBC componentes obtenidos: %d/9", len(components))
    return components


def save_ibc_components_to_db(components: List[Dict]) -> int:
    """Guarda componentes del IBC en la DB.

    Returns:
        Número de registros guardados.
    """
    from src.db.session import get_session
    from src.db.models import IBCComponentORM
    from sqlalchemy import select

    saved = 0
    with get_session() as sess:
        for comp in components:
            ticker = comp["ticker"]
            dt = comp["date"]

            existing = sess.execute(
                select(IBCComponentORM).where(
                    IBCComponentORM.ticker == ticker,
                    IBCComponentORM.date >= dt.replace(hour=0, minute=0, second=0),
                )
            ).scalar_one_or_none()

            if existing:
                existing.price = comp["price"]
                existing.change_pct = comp["change_pct"]
                existing.name = comp["name"]
            else:
                orm = IBCComponentORM(
                    ticker=ticker,
                    name=comp["name"],
                    price=comp["price"],
                    change_pct=comp["change_pct"],
                    volume=0,
                    date=dt,
                )
                sess.add(orm)
                saved += 1

        sess.commit()

    logger.info("IBC components guardados: %d", saved)
    return saved


# ─── Runner principal ────────────────────────────────────────────────────────


def run_ibc_full_collection(months: int = 6) -> Dict:
    """Ejecuta la colección completa del IBC: histórico + componentes.

    Returns:
        Dict con resultados.
    """
    logger.info("=== Colección IBC completa (%d meses) ===", months)

    # 1. IBC histórico desde datosmacro
    history = fetch_ibc_history_datosmacro(months=months)
    history_inserted = 0
    if history:
        history_inserted = save_ibc_history_to_db(history)

    # 2. IBC componentes desde Yahoo Finance
    components = fetch_ibc_components_yahoo()
    components_saved = 0
    if components:
        components_saved = save_ibc_components_to_db(components)

    result = {
        "success": True,
        "history_records": len(history),
        "history_inserted": history_inserted,
        "components_found": len(components),
        "components_saved": components_saved,
        "component_tickers": [c["ticker"] for c in components],
        "message": (
            f"IBC histórico: {len(history)} registros ({history_inserted} nuevos). "
            f"Componentes: {len(components)}/9 obtenidos."
        ),
    }

    logger.info("IBC colección completa: %s", result["message"])
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = run_ibc_full_collection()
    print(f"\nResultado: {result['message']}")
