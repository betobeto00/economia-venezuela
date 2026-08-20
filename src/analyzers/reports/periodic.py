"""
Informes periódicos por cadencia (diario/semanal/mensual/trimestral/semestral/anual)
====================================================================================

Compila el snapshot de datos del período (mercado, inflación, encuestas,
sentimiento, noticias, marco fiscal y macro) y lo exporta en Markdown y PDF.

El snapshot siempre se genera: si una sección no tiene datos, se documenta con
"_Sin datos_" y nunca falla. Los documentos fiscales e indicadores macro se
recogen en vivo desde los collectors (si fallan, la sección queda vacía).
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from src.config import settings

logger = logging.getLogger(__name__)

CADENCES = {
    "diario": {"days": 1, "label": "Informe Diario"},
    "semanal": {"days": 7, "label": "Informe Semanal"},
    "mensual": {"days": 30, "label": "Informe Mensual"},
    "trimestral": {"days": 91, "label": "Informe Trimestral"},
    "semestral": {"days": 182, "label": "Informe Semestral"},
    "anual": {"days": 365, "label": "Informe Anual"},
}

FISCAL_KEYWORDS = ("presupuesto", "endeudamiento", "gasto", "fiscal", "finanza")

TOP_ARTICLES = 10


def _period_label(cadence: str, now: datetime) -> str:
    if cadence == "diario":
        return f"Día {now:%Y-%m-%d}"
    if cadence == "semanal":
        iso = now.isocalendar()
        return f"Semana del {now:%Y-%m-%d} (W{iso.week:02d} de {now.year})"
    if cadence == "mensual":
        return f"Mes de {now:%B %Y}"
    if cadence == "trimestral":
        quarter = (now.month - 1) // 3 + 1
        return f"Trimestre {quarter} de {now.year}"
    if cadence == "semestral":
        half = 1 if now.month <= 6 else 2
        return f"Semestre {half} de {now.year}"
    return f"Año {now.year}"


def _collect_fiscal_docs(days: int) -> List[Dict]:
    """Documentos fiscales del período con impacto económico (gaceta + AN).

    Gacetas: se buscan por palabras clave, se conservan solo las publicadas
    dentro del período y se enriquecen con sus sumarios; se descartan las que
    no tienen trámites con impacto económico.
    """
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc).date() - timedelta(days=days)
    docs: List[Dict] = []
    try:
        from src.collectors.fiscal.gaceta_collector import GacetaOficialCollector

        gaceta = GacetaOficialCollector()
        catalog = gaceta.fetch_documentos(
            ["presupuesto", "endeudamiento", "economía", "finanzas"]
        )
        recent = [d for d in catalog if d.date and d.date >= cutoff]
        enriched = gaceta.enrich_con_sumarios(recent, max_docs=8)
        docs += [
            {
                "source": "gaceta", "title": d.title, "url": d.url,
                "year": d.year, "date": d.date,
                "description": d.description,
            }
            for d in enriched
        ]
    except Exception as exc:  # noqa: BLE001 - sección opcional
        logger.warning("Gaceta Oficial no disponible para el informe: %s", exc)
    try:
        from src.collectors.fiscal.an_collector import ANCollector

        an = ANCollector().fetch_documentos(
            keywords=list(FISCAL_KEYWORDS), max_pages=2
        )
        docs += [
            {
                "source": "an", "title": d.title, "url": d.url,
                "year": d.year, "date": d.date, "description": "",
            }
            for d in an if d.date and d.date >= cutoff
        ]
    except Exception as exc:  # noqa: BLE001 - sección opcional
        logger.warning("AN no disponible para el informe: %s", exc)
    return docs


# Cómo impacta cada indicador macro en el corto plazo (semana/mes).
_MACRO_IMPACT = {
    ("cepal", "pib"): "Contexto estructural: fija el nivel de actividad anual; "
                      "no mueve la semana, sí el riesgo soberano.",
    ("world_bank", "pib_usd"): "Referencia anual de tamaño de la economía.",
    ("imf", "crecimiento_pib"): "Señal de corto plazo de actividad; incide en "
                                "la percepción de riesgo cambiario.",
    ("imf", "inflacion"): "Ancla de referencia para política monetaria y "
                          "expectativas de devaluación.",
    ("unsceb", "gasto_onu_venezuela"): "Flujo externo de divisas del sistema "
                                        "ONU; aporta liquidez marginal al dólar.",
}


def _collect_macro(days: int) -> List[Dict]:
    """Indicadores macro: última observación por indicador con nota de impacto.

    Solo se conserva el valor más reciente de cada indicador (no la serie
    histórica completa) y se explica por qué importa en el corto plazo.
    """
    points: List[Dict] = []
    try:
        from src.collectors.international.cepal_collector import CEPALCollector

        gdp = CEPALCollector().fetch_gdp()
        if gdp:
            p = gdp[-1]
            points.append({"source": "cepal", "indicator": "pib",
                           "value": p.value, "period": p.period,
                           "unit": p.unit})
    except Exception as exc:  # noqa: BLE001 - sección opcional
        logger.warning("CEPAL no disponible para el informe: %s", exc)
    try:
        from src.collectors.international.imf_collector import IMFCollector

        imf = IMFCollector()
        growth = imf.fetch_gdp_growth()
        if growth:
            p = growth[-1]
            points.append({"source": "imf", "indicator": "crecimiento_pib",
                           "value": p.value, "period": p.period,
                           "unit": p.unit})
        infl = imf.fetch_inflation()
        if infl:
            p = infl[-1]
            points.append({"source": "imf", "indicator": "inflacion",
                           "value": p.value, "period": p.period,
                           "unit": p.unit})
    except Exception as exc:  # noqa: BLE001 - sección opcional
        logger.warning("FMI no disponible para el informe: %s", exc)
    try:
        from src.collectors.international.unsceb_collector import UNSCEBCollector

        gasto = UNSCEBCollector().fetch_venezuela_expenses()
        if gasto:
            p = gasto[-1]
            points.append({"source": "unsceb", "indicator": "gasto_onu_venezuela",
                           "value": p.value, "period": p.period,
                           "unit": p.unit})
    except Exception as exc:  # noqa: BLE001 - sección opcional
        logger.warning("UNSCEB no disponible para el informe: %s", exc)
    try:
        from src.collectors.international.worldbank_collector import WorldBankCollector

        wb = WorldBankCollector().fetch_gdp()
        if wb:
            p = wb[-1]
            points.append({"source": "world_bank", "indicator": "pib_usd",
                           "value": p.value, "period": str(p.year),
                           "unit": "USD"})
    except Exception as exc:  # noqa: BLE001 - sección opcional
        logger.warning("Banco Mundial no disponible para el informe: %s", exc)

    for p in points:
        p["impact"] = _MACRO_IMPACT.get(
            (p["source"], p["indicator"]),
            "Dato de contexto macroeconómico.",
        )
    return points


def _ai_resumen(markdown: str) -> str:
    """Resumen ejecutivo por IA con fallback silencioso."""
    if not settings.llm_providers():
        return ""
    try:
        from src.analyzers.llm import summarize

        text = summarize(
            (
                "Eres un economista jefe para Venezuela. Escribe un resumen "
                "ejecutivo amplio (10-15 frases) del informe para un lector "
                "no técnico. No te limites a listar cifras: analiza, compara, "
                "explora relaciones entre secciones y valida coherencia. "
                "Incluye:\n"
                "1. Contexto general del período.\n"
                "2. Mercado cambiario: tendencias por fuente, brechas, volatilidad.\n"
                "3. Inflación: trayectoria y comparación con el período anterior.\n"
                "4. Sentimiento de noticias y encuestas: qué信号 envía la calle.\n"
                "5. Marco fiscal y macro: qué cambió y por qué importa.\n"
                "6. Proyección para la próxima semana: hacia dónde apuntan "
                "tipo de cambio, inflación y sentimiento; riesgos al alza y "
                "a la baja.\n"
                "Termina cada frase con punto final. "
                "Responde siempre en español."
            ),
            markdown,
            max_tokens=2500,
        ) or ""
    except Exception as exc:  # noqa: BLE001 - el informe no debe fallar
        logger.warning("Resumen IA no disponible: %s", exc)
        return ""
    return _ensure_complete(text)


def _ai_proyeccion(markdown: str) -> str:
    """Proyección para el próximo período generada por IA (fallback silencioso)."""
    if not settings.llm_providers():
        return ""
    try:
        from src.analyzers.llm import summarize

        text = summarize(
            (
                "Eres un economista jefe para Venezuela. Con base en el "
                "informe del período, escribe una PROYECCIÓN para la próxima "
                "semana en 3-5 frases: hacia dónde apuntan el tipo de cambio "
                "(por fuente), la inflación y el sentimiento del mercado; "
                "menciona los riesgos al alza y a la baja. "
                "Responde SOLO con la proyección final (sin introducciones, "
                "sin repetir las instrucciones, sin comentarios meta). "
                "Termina cada frase con un punto final. "
                "No inventes cifras que no estén en el informe. "
                "Responde siempre en español."
            ),
            markdown,
            max_tokens=900,
        ) or ""
    except Exception as exc:  # noqa: BLE001 - el informe no debe fallar
        logger.warning("Proyección IA no disponible: %s", exc)
        return ""
    return _clean_proyeccion(text)


_META_PREFIXES = (
    "we need", "we must", "you are", "instructions",
    "to produce", "must not invent", "we can",
    "let me", "i need", "i must", "the user", "to respond", "i will",
)


def _clean_proyeccion(text: str) -> str:
    """Quita prefacios meta que algunos LLMs añaden (razonamiento en voz alta)."""
    lines = text.splitlines()
    out: List[str] = []
    started = False
    for ln in lines:
        low = ln.strip().lower()
        if not started and (low.startswith(_META_PREFIXES) or not ln.strip()):
            continue
        started = True
        out.append(ln)
    cleaned = _ensure_complete("\n".join(out).strip())
    return cleaned


def _ensure_complete(text: str) -> str:
    """Recorta al último punto/sentencia terminada si el LLM cortó a media frase."""
    t = text.strip()
    if not t:
        return ""
    if t[-1] in ".!?…":
        return t
    for sep in (".", "!", "?"):
        idx = t.rfind(sep)
        if idx >= 1 and idx > len(t) * 0.3:
            return t[: idx + 1]
    return t


def _projection_rows(market: List[Dict]) -> List[Dict]:
    """Proyección heurística de tasas: última tasa × (1 + variación semanal)."""
    rows = []
    for m in market:
        var = m.get("variation_pct")
        rate = m.get("rate")
        if var is None or not rate:
            continue
        rows.append({"source": m.get("source", "?"),
                     "rate": rate * (1 + var / 100.0)})
    return rows


def collect_snapshot(
    cadence: str = "semanal",
    session=None,
    with_fiscal: bool = True,
    with_macro: bool = True,
    with_ai: bool = True,
) -> Dict:
    """Compila el snapshot de datos del período para el informe.

    Args:
        cadence: Una de las claves de ``CADENCES``.
        session: Sesión inyectable (tests); si es None abre una propia.
        with_fiscal: Recoge documentos fiscales en vivo.
        with_macro: Recoge indicadores macro en vivo.
        with_ai: Añade resumen ejecutivo por IA.

    Returns:
        Snapshot con secciones: market, market_series, inflation, surveys,
        sentiment, articles, fiscal_docs, macro, resumen.
    """
    if cadence not in CADENCES:
        raise ValueError(f"Cadencia inválida: {cadence}. Usar {list(CADENCES)}")

    from src.analyzers.reports.weekly import _snapshot_from_session
    from src.db.session import get_session

    days = CADENCES[cadence]["days"]
    now = datetime.now(timezone.utc)

    if session is None:
        with get_session() as session:
            base = _snapshot_from_session(session, days)
    else:
        base = _snapshot_from_session(session, days)

    market_series = base.get("market") or []
    snapshot = {
        "cadence": cadence,
        "period": _period_label(cadence, now),
        "generated_at": now,
        "market": market_series,
        "market_series": _market_series(session, days),
        "inflation": base.get("inflation") or [],
        "surveys": base.get("surveys") or {},
        "sentiment": base.get("sentiment") or {},
        "articles": (base.get("articles") or [])[:TOP_ARTICLES],
        "fiscal_docs": _collect_fiscal_docs(days) if with_fiscal else [],
        "macro": _collect_macro(days) if with_macro else [],
        "resumen": "",
        "proyeccion": "",
        "proyeccion_rows": _projection_rows(market_series),
    }

    if with_ai:
        md = build_markdown(snapshot)
        snapshot["resumen"] = _ai_resumen(md)
        snapshot["proyeccion"] = _ai_proyeccion(md)
    return snapshot


def _market_series(session, days: int) -> List[Dict]:
    """Serie completa de tasas del período (para gráficos), sin outliers."""
    from src.analyzers.reports.weekly import _clean_rates
    from src.db.repositories import MarketRepository

    since = datetime.now(timezone.utc) - timedelta(days=days)
    rates = MarketRepository(session).list_rates(since=since, limit=5000)
    return [
        {"source": r.source, "currency": r.currency, "rate": float(r.rate),
         "date": r.date.isoformat()}
        for r in _clean_rates(rates)
    ]


def _fmt(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:,.2f}"
    return str(v)


def fiscal_docs_block(docs: List[Dict]) -> List[str]:
    lines = ["## Marco Fiscal y Legislativo Reciente", ""]
    if not docs:
        lines += ["_Sin trámites fiscales con impacto económico en el período._", ""]
        return lines
    lines += ["| Fuente | Año | Fecha | Documento / Trámite |", "|---|---|---|---|"]
    for d in docs:
        desc = d.get("description") or d.get("title") or ""
        lines.append(f"| {d.get('source', '?')} | {d.get('year', '—')} | "
                     f"{d.get('date') or '—'} | {desc} |")
    lines += ["",
              "_Solo se listan los trámites con posible impacto económico "
              "(presupuesto, endeudamiento, impuestos, comercio, ...)._",
              ""]
    return lines


def macro_block(points: List[Dict]) -> List[str]:
    lines = ["## Indicadores Macroeconómicos", ""]
    if not points:
        lines += ["_Sin indicadores macroeconómicos disponibles._", ""]
        return lines
    lines += ["| Fuente | Indicador | Período | Valor | Unidad | Por qué importa |",
              "|---|---|---|---|---|---|"]
    for p in points:
        lines.append(f"| {p.get('source', '?')} | {p.get('indicator', '')} | "
                     f"{p.get('period', '—')} | {_fmt(p.get('value'))} | "
                     f"{p.get('unit', '')} | {p.get('impact', '')} |")
    lines += ["",
              "_Última observación disponible; los datos anuales son contexto "
              "estructural, no impulsores de la semana._",
              ""]
    return lines


def build_markdown(snapshot: Dict) -> str:
    """Construye el informe en Markdown a partir del snapshot."""
    from src.analyzers.reports.weekly import (
        articles_block,
        inflation_block,
        market_block,
        projection_block,
        sentiment_block,
        surveys_block,
    )

    now = snapshot.get("generated_at") or datetime.now(timezone.utc)
    lines = [
        f"# {CADENCES[snapshot.get('cadence', 'semanal')]['label']} — Economía Venezuela",
        "",
        f"**Período:** {snapshot.get('period', '')}  ",
        f"**Generado:** {now:%Y-%m-%d %H:%M UTC}",
        "",
    ]
    lines += market_block(snapshot.get("market") or [])
    lines += inflation_block(snapshot.get("inflation") or [])
    lines += surveys_block(snapshot.get("surveys") or {})
    lines += sentiment_block(snapshot.get("sentiment") or {})
    lines += articles_block(snapshot.get("articles") or [])
    lines += fiscal_docs_block(snapshot.get("fiscal_docs") or [])
    lines += macro_block(snapshot.get("macro") or [])
    base = "\n".join(lines)

    resumen = snapshot.get("resumen") or ""
    if resumen:
        base += "\n\n## Resumen Ejecutivo\n\n" + resumen.strip()
    base += "\n\n---\n_Informe generado automáticamente (Fases A + B + 5b)._"
    return base


def save_report(markdown: str, cadence: str, output_dir: Optional[str] = None,
                generated_at: Optional[datetime] = None) -> str:
    """Guarda el Markdown en ``output_dir/<cadence>_<fecha>.md``."""
    from pathlib import Path

    now = generated_at or datetime.now()
    name = f"{cadence}_{now:%Y-%m-%d}.md"
    output_dir = output_dir or str(Path("data", "reports"))
    path = Path(output_dir) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
    return str(path)


def generate_periodic_report(
    cadence: str = "semanal",
    output_dir: Optional[str] = None,
    formats=("md", "pdf"),
    session=None,
    **snapshot_kwargs,
) -> Dict:
    """Genera el informe del período en Markdown y/o PDF.

    Args:
        cadence: Cadencia del informe.
        output_dir: Carpeta de salida (default: data/reports).
        formats: Formatos a generar ('md', 'pdf').
        session: Sesión inyectable (tests).
        snapshot_kwargs: Argumentos extra para ``collect_snapshot``.

    Returns:
        Dict con las rutas generadas y el snapshot.
    """
    snapshot = collect_snapshot(cadence, session=session, **snapshot_kwargs)
    md = build_markdown(snapshot)
    out: Dict = {"snapshot": snapshot, "paths": {}}

    if "md" in formats:
        out["paths"]["md"] = save_report(md, cadence, output_dir,
                                         snapshot["generated_at"])

    if "pdf" in formats:
        from src.analyzers.reports.pdf_report import render_pdf

        pdf_path = (out["paths"].get("md") or
                    f"{output_dir or 'data/reports'}/{cadence}_{snapshot['generated_at']:%Y-%m-%d}.pdf")
        out["paths"]["pdf"] = render_pdf(snapshot, pdf_path.replace(".md", ".pdf"))
    return out