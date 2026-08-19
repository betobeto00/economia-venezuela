"""
HTTP compartido para collectors
===============================

Helpers con reintentos (tenacity) y timeouts para las fuentes externas.
Todos los collectors de Fase A usan estos helpers, de modo que los tests
pueden simular respuestas parcheando ``http_get_text`` / ``http_get_json``.
"""

import logging
from typing import Any, Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.collectors.errors import CollectorError

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = httpx.Timeout(15.0)
USER_AGENT = "EconomiaVenezuela/0.1.0 (dashboard economico; contacto: dev@local)"


def _client() -> httpx.Client:
    return httpx.Client(
        timeout=DEFAULT_TIMEOUT,
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
    )


@retry(
    retry=retry_if_exception_type(httpx.HTTPError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, max=4),
    reraise=True,
)
def _get(url: str, params: Optional[dict] = None) -> httpx.Response:
    with _client() as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        return response


def http_get_text(url: str, params: Optional[dict] = None) -> str:
    """GET y devuelve el cuerpo como texto (HTML, JSON crudo, etc.)."""
    try:
        response = _get(url, params=params)
        return response.text
    except httpx.HTTPError as exc:
        raise CollectorError(f"No se pudo consultar {url}: {exc}") from exc


def http_get_json(url: str, params: Optional[dict] = None) -> Any:
    """GET y devuelve el cuerpo parseado como JSON."""
    try:
        response = _get(url, params=params)
        return response.json()
    except httpx.HTTPError as exc:
        raise CollectorError(f"No se pudo consultar {url}: {exc}") from exc
    except ValueError as exc:
        raise CollectorError(f"Respuesta no-JSON desde {url}") from exc


def http_get_bytes(url: str, params: Optional[dict] = None) -> bytes:
    """GET y devuelve el cuerpo como bytes (para XLS/PDF)."""
    try:
        response = _get(url, params=params)
        return response.content
    except httpx.HTTPError as exc:
        raise CollectorError(f"No se pudo descargar {url}: {exc}") from exc