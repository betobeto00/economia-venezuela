"""
Collector Cendas-FVM (Canasta Alimentaria Regional)
====================================================

Recolecta datos de la Encuesta Nacional de Presupuestos de Hogares (ENPH)
y la Canasta Alimentaria Regional del Cendas-FVM (Centro de Documentación
y Análisis Social - Federación Venezolana de Maestros).

Fuentes:
- http://www.cendas.org.ve (sitio principal)
- Publicaciones periódicas de la canasta básica alimentaria por estado

Estos datos permiten contrastar el IPC oficial (BCV) con la inflación
real percibida en diferentes regiones del país.
"""

import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

CENDAS_URL = "http://www.cendas.org.ve"
CANASTA_URL = f"{CENDAS_URL}/module/ModItem declaration/Home"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-VE,es;q=0.9,en;q=0.8",
}


@dataclass
class CanastaItem:
    """Item de la canasta básica alimentaria."""
    producto: str
    cantidad: float
    unidad: str
    precio_bs: float
    precio_usd: Optional[float] = None
    estado: str = ""
    fecha: str = ""


@dataclass
class CanastaResumen:
    """Resumen de la canasta básica por región."""
    estado: str
    fecha: str
    total_bs: float
    total_usd: Optional[float]
    items: List[CanastaItem]
    fuente: str = "Cendas-FVM"


def fetch_cendas_page() -> Optional[str]:
    """Obtiene la página principal de Cendas-FVM."""
    try:
        resp = httpx.get(CENDAS_URL, headers=HEADERS, timeout=30, follow_redirects=True)
        if resp.status_code == 200:
            return resp.text
        logger.warning("Cendas respondió %d", resp.status_code)
    except Exception as exc:
        logger.warning("Error consultando Cendas: %s", exc)
    return None


def find_canasta_links(html: str) -> List[Dict[str, str]]:
    """Busca enlaces a publicaciones de canasta básica en el HTML."""
    links = []
    # Buscar enlaces a PDFs o páginas de canasta
    patterns = [
        r'href=["\']([^"\']*(?:canasta|alimentar|presupuesto|hogar)[^"\']*)["\']',
        r'href=["\']([^"\']*\.pdf)["\']',
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, html, re.IGNORECASE):
            url = match.group(1)
            if not url.startswith("http"):
                url = f"{CENDAS_URL}{url}"
            links.append({"url": url, "title": url.split("/")[-1]})
    return links


def parse_canasta_text(text: str) -> List[CanastaItem]:
    """Parsea texto extraído de una tabla de canasta básica.

    Busca patrones como:
        Arroz    3    kg    450.00
        Harina   3    kg    540.00
    """
    items = []
    lines = text.split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Intentar parsear líneas con formato: producto cantidad unidad precio
        parts = re.split(r'\s{2,}|\t', line)
        if len(parts) >= 3:
            try:
                # Buscar el precio (último número)
                precio = None
                for part in reversed(parts):
                    cleaned = part.replace(",", ".").replace("Bs", "").replace("$", "").strip()
                    try:
                        precio = float(cleaned)
                        break
                    except ValueError:
                        continue

                if precio is not None and precio > 0:
                    # El producto es la primera parte
                    producto = parts[0].strip()
                    items.append(CanastaItem(
                        producto=producto,
                        cantidad=0,
                        unidad="",
                        precio_bs=precio,
                    ))
            except (ValueError, IndexError):
                continue

    return items


def fetch_canasta_data() -> Optional[CanastaResumen]:
    """Obtiene datos de la canasta básica desde Cendas-FVM.

    Returns:
        CanastaResumen con los items de la canasta, o None si falla.
    """
    html = fetch_cendas_page()
    if not html:
        return None

    links = find_canasta_links(html)
    if not links:
        logger.info("No se encontraron enlaces de canasta en Cendas")
        return None

    # Intentar descargar el primer PDF encontrado
    for link in links[:3]:
        try:
            resp = httpx.get(
                link["url"], headers=HEADERS, timeout=30, follow_redirects=True
            )
            if resp.status_code == 200:
                if link["url"].endswith(".pdf"):
                    from src.collectors.fiscal.gaceta_ocr import extract_text_from_pdf
                    text = extract_text_from_pdf(resp.content)
                else:
                    text = resp.text

                items = parse_canasta_text(text)
                if items:
                    total_bs = sum(item.precio_bs for item in items)
                    return CanastaResumen(
                        estado="Nacional",
                        fecha="",
                        total_bs=total_bs,
                        total_usd=None,
                        items=items,
                    )
        except Exception as exc:
            logger.debug("Error descargando %s: %s", link["url"], exc)
            continue

    return None


def estimate_canasta_usd(resumen: CanastaResumen, usd_rate: float) -> CanastaResumen:
    """Estima el precio en USD de la canasta básica.

    Args:
        resumen: CanastaResumen con precios en BS.
        usd_rate: Tasa de cambio BS/USD.

    Returns:
        CanastaResumen con precios en USD estimados.
    """
    if usd_rate <= 0:
        return resumen

    for item in resumen.items:
        item.precio_usd = item.precio_bs / usd_rate

    resumen.total_usd = resumen.total_bs / usd_rate
    return resumen
