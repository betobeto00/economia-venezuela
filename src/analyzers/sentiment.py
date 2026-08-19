"""
Análisis de sentimiento (Fase A)
================================

Clasifica el tono de textos económicos en español (noticias y posts) usando
un léxico de términos económicos con manejo de negación. Es determinista y
no requiere modelos descargados (a diferencia de transformers/spacy), por lo
que es adecuado para el pipeline offline y los tests.

Algoritmo:
- Normaliza el texto (minúsculas, sin acentos).
- Cuenta términos positivos y negativos del léxico (match por palabra).
- Invierte el signo si un término de negación precede a un término de tono.
- ``score`` en [-1, 1] con la fórmula (pos - neg) / total.

La API es inyectable: los componentes consumen ``analyze_text`` / ``analyze_batch``,
por lo que se puede sustituir por un modelo más pesado sin tocar el pipeline.
"""

import re
import unicodedata
from typing import Iterable, List, Optional, Tuple

from src.models.news import SentimentScore

# Léxico económico (español, sin acentos)
_POSITIVE = frozenset({
    "alza", "sube", "suben", "subida", "aumento", "crece", "crecimiento",
    "mejora", "mejoran", "repunte", "ganancia", "ganancias", "superavit",
    "prosperidad", "fortaleza", "fortalecimiento", "recuperacion", "recupera",
    "estabilidad", "estable", "expansion", "record", "exito", "beneficio",
    "beneficios", "rentabilidad", "inversion", "exportaciones", "bajan los",
    "baja de", "descenso de", "menos inflacion", "control de inflacion",
})

_NEGATIVE = frozenset({
    "cae", "caen", "caida", "baja", "bajan", "recesion", "crisis", "colapso",
    "devaluacion", "perdida", "perdidas", "deficit", "quiebra", "quiebras",
    "desempleo", "despidos", "empobrecimiento", "contraccion", "desplome",
    "escasez", "corralito", "default", "sanciones", "embargo", "inflacion",
    "hiperinflacion", "reajuste", "sube el dolar", "suben los precios",
    "alza de precios", "encarece", "encarecen", "precios se disparan",
    "dolarizacion forzada", "costo de vida", "crisis economica",
})

_NEGATIONS = frozenset({"no", "nunca", "sin", "tampoco", "ni", "poco", "menos"})

_WORD_RE = re.compile(r"[a-z]+")


def _normalize(text: str) -> str:
    """Minúsculas y sin acentos (comparación léxica)."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return text.lower()


def _tokens(text: str) -> List[str]:
    return _WORD_RE.findall(_normalize(text))


def score_text(text: str) -> Tuple[float, str]:
    """Puntúa un texto y devuelve (score, label).

    Args:
        text: Texto a analizar (puede ser vacío o None).

    Returns:
        (score en [-1, 1], label: positive|neutral|negative).
    """
    if not text or not text.strip():
        return 0.0, "neutral"

    tokens = _tokens(text)
    if not tokens:
        return 0.0, "neutral"

    positive = 0
    negative = 0
    window = " ".join(tokens)

    # Match de términos (algunos son frases cortas)
    for term in _POSITIVE:
        if term in window:
            positive += 1
    for term in _NEGATIVE:
        if term in window:
            negative += 1

    # Negación simple: si una negación precede a un término de tono (ventana
    # de 3 palabras), invierte su signo.
    for i, token in enumerate(tokens):
        if token not in _NEGATIONS:
            continue
        for lookahead in tokens[i + 1:i + 4]:
            if lookahead in _POSITIVE:
                positive -= 1
                negative += 1
            elif lookahead in _NEGATIVE:
                negative -= 1
                positive += 1

    total = positive + negative
    if total == 0:
        return 0.0, "neutral"

    score = (positive - negative) / total
    if score > 0.15:
        label = "positive"
    elif score < -0.15:
        label = "negative"
    else:
        label = "neutral"
    return round(score, 4), label


def analyze_text(text: str) -> Tuple[float, str]:
    """API pública: puntúa un texto (función pura, sin persistencia)."""
    return score_text(text)


def analyze_batch(texts: Iterable[str]) -> List[Tuple[float, str]]:
    """Puntúa varios textos de una vez (útil para el pipeline)."""
    return [score_text(t) for t in texts]


def to_sentiment_score(
    item_type: str,
    item_id: int,
    text: str,
) -> Optional[SentimentScore]:
    """Construye un ``SentimentScore`` desde un texto (None si es neutro/void)."""
    score, label = score_text(text)
    if label == "neutral":
        return None
    return SentimentScore(
        item_type=item_type,
        item_id=item_id,
        text=text[:500],
        score=score,
        label=label,
    )