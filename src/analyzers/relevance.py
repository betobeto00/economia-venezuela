"""
Filtro de relevancia económica (Fase A)
=======================================

Clasifica si un texto (título + resumen de noticia o post) trata temas
económicos de interés para el proyecto. Es determinista y sin dependencias
(exactamente igual que ``sentiment.py``), pensado para filtrar el ruido de
feeds generalistas (guerras, cultura, deportes, desastres) antes de analizar
el sentimiento económico.

Regla de decisión:
- Términos FUERTES (inconfundiblemente económicos): 1 coincidencia basta.
- Términos DÉBILES (contextuales): hacen falta 2 coincidencias.

La API es inyectable (``is_economically_relevant`` / ``relevance_score``),
como el resto de analizadores, para poder sustituirla por un modelo más
pesado sin tocar el pipeline.
"""

import re
import unicodedata
from typing import Iterable, List, Tuple

# Términos inconfundiblemente económicos: una sola aparición clasifica.
_STRONG_TERMS = frozenset({
    "dolar", "dolarizacion", "dolarizado", "dolares",
    "inflacion", "hiperinflacion", "ipc",
    "pib", "bcv", "opep", "fmi",
    "salario", "salarios", "sueldo", "desempleo",
    "petroleo", "crudo", "gasolina", "combustible",
    "tipo de cambio", "tasa de cambio", "divisa", "divisas",
    "canasta", "cesta", "costo de vida", "canasta basica",
    "deficit", "superavit", "devaluacion",
    "arancel", "aranceles", "remesas",
    "reservas internacionales", "banco central",
    "presupuesto nacional", "presupuesto publico",
    "bonos soberanos", "deuda soberana",
    "criptomoneda", "criptomonedas", "bitcoin", "usdt", "cripto",
    "control de cambio", "encaje legal", "emision monetaria",
})

# Términos contextuales: necesitan 2 coincidencias para no dar falsos
# positivos (p.ej. "mercado" en deportes, "banco" de datos).
_WEAK_TERMS = frozenset({
    "economia", "economico", "economica", "economicos", "economicas",
    "mercado", "mercados",
    "precio", "precios",
    "banco", "bancos", "bancario", "bancaria", "bancarios",
    "finanzas", "financiero", "financiera", "financieros",
    "empresa", "empresas", "negocio", "negocios", "corporativo",
    "impuesto", "impuestos", "fiscal", "tributario", "tributos",
    "inversion", "inversiones", "inversionista", "inversionistas",
    "credito", "creditos", "deuda", "deudas", "prestamo", "prestamos",
    "exportacion", "exportaciones", "importacion", "importaciones",
    "comercio", "moneda", "monedas",
    "empleo", "empleados", "laboral",
    "subsidio", "subsidios", "regulacion", "regulaciones",
    "utilidades", "ganancias", "rentabilidad", "dividendos",
    "reservas", "gasto", "gastos", "ingresos",
    "produccion", "productividad", "manufactura", "industria",
})

_WORD_RE = re.compile(r"[a-z]+")


def _normalize(text: str) -> str:
    """Minúsculas y sin acentos (comparación léxica)."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return text.lower()


def _tokens(text: str) -> List[str]:
    return _WORD_RE.findall(_normalize(text))


def _matches(text: str) -> Tuple[int, int]:
    """(strong, weak): coincidencias de términos en el texto normalizado."""
    window = " ".join(_tokens(text))
    strong = sum(1 for term in _STRONG_TERMS if term in window)
    weak = sum(1 for term in _WEAK_TERMS if term in window)
    return strong, weak


def relevance_score(text: str) -> int:
    """Número ponderado de señales económicas (fuerte=3, débil=1)."""
    if not text or not text.strip():
        return 0
    strong, weak = _matches(text)
    return strong * 3 + weak


def is_economically_relevant(text: str, min_strong: int = 1, min_weak: int = 2) -> bool:
    """Clasifica un texto como económicamente relevante.

    Args:
        text: Texto a evaluar (título + resumen).
        min_strong: Coincidencias fuertes requeridas (default 1).
        min_weak: Coincidencias débiles requeridas si no hay fuertes (default 2).

    Returns:
        True si el texto trata de economía.
    """
    if not text or not text.strip():
        return False
    strong, weak = _matches(text)
    return strong >= min_strong or weak >= min_weak


def filter_relevant(texts: Iterable[str]) -> List[Tuple[str, bool]]:
    """Clasifica una lista de textos; útil para inspeccionar el filtro."""
    return [(t, is_economically_relevant(t)) for t in texts]