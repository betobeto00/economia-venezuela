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


def _collect_fiscal_docs() -> List[Dict]:
    """Documentos fiscales recientes (gaceta + AN) recogidos en vivo."""
    docs: List[Dict] = []
    try:
        from src.collectors.fiscal.gaceta_collector import GacetaOficialCollector

        gaceta = GacetaOficialCollector().fetch_documentos(["presupuesto"])
        docs += [
            {"source": "gaceta", "title": d.title, "url": d.url, "year": d.year}
            for d in gaceta[:10]
        ]
    except Exception as exc:  # noqa: BLE001 - sección opcional
        logger.warning("Gaceta Oficial no disponible para el informe: %s", exc)
    try:
        from src.collectors.fiscal.an_collector import ANCollector

        an = ANCollector().fetch_documentos(
            keywords=list(FISCAL_KEYWORDS), max_pages=2
        )
        docs += [
            {"source": "an", "title": d.title, "url": d.url, "year": d.year}
            for d in an[:10]
        ]
    except Exception as exc:  # noqa: BLE001 - sección opcional
        logger.warning("AN no disponible para el informe: %s", exc)
    return docs


def _collect_macro() -> List[Dict]:
    """Indicadores macroeconómicos internacionales recogidos en vivo."""
    points: List[Dict] = []
    try:
        from src.collectors.international.cepal_collector import CEPALCollector

        points += [
            p.model_dump() for p in CEPALCollector().fetch_gdp()[-5:]
        ]
    except Exception as exc:  # noqa: BLE001 - sección opcional
        logger.warning("CEPAL no disponible para el informe: %s", exc)
    try:
        from src.collectors.international.imf_collector import IMFCollector

        imf = IMFCollector()
        points += [p.model_dump() for p in imf.fetch_gdp_growth()[-3:]]
        points += [p.model_dump() for p in imf.fetch_inflation()[-3:]]
    except Exception as exc:  # noqa: BLE001 - sección opcional
        logger.warning("FMI no disponible para el informe: %s", exc)
    try:
        from src.collectors.international.unsceb_collector import UNSCEBCollector

        points += [
            p.model_dump()
            for p in UNSCEBCollector().fetch_venezuela_expenses()[-3:]
        ]
    except Exception as exc:  # noqa: BLE001 - sección opcional
        logger.warning("UNSCEB no disponible para el informe: %s", exc)
    try:
        from src.collectors.international.worldbank_collector import WorldBankCollector

        wb = WorldBankCollector()
        points += [
            {"source": "world_bank", "indicator": "pib_usd", "value": p.value,
             "period": str(p.year), "unit": "USD"}
            for p in wb.fetch_gdp()[-3:]
        ]
    except Exception as exc:  # noqa: BLE001 - sección opcional
        logger.warning("Banco Mundial no disponible para el informe: %s", exc)
    return points


def _ai_resumen(markdown: str) -> str:
    """Resumen ejecutivo por IA con fallback silencioso."""
    if not settings.llm_providers():
        return ""
    try:
        from src.analyzers.llm import summarize

        return summarize(
            (
                "Eres un economista jefe para Venezuela. Redacta un resumen "
                "ejecutivo de 5-8 frases del informe para un lector no técnico: "
                "contexto general, cifras clave y tendencias del período."
            ),
            markdown,
            max_tokens=500,
        ) or ""
    except Exception as exc:  # noqa: BLE001 - el informe no debe fallar
        logger.warning("Resumen IA no disponible: %s", exc)
        return ""


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
        "fiscal_docs": _collect_fiscal_docs() if with_fiscal else [],
        "macro": _collect_macro() if with_macro else [],
        "resumen": "",
    }

    if with_ai:
        md = build_markdown(snapshot)
        snapshot["resumen"] = _ai_resumen(md)
    return snapshot


def _market_series(session, days: int) -> List[Dict]:
    """Serie completa de tasas del período (para gráficos)."""
    from src.db.repositories import MarketRepository

    since = datetime.now(timezone.utc) - timedelta(days=days)
    rates = MarketRepository(session).list_rates(since=since, limit=5000)
    return [
        {"source": r.source, "currency": r.currency, "rate": float(r.rate),
         "date": r.date.isoformat()}
        for r in rates
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
        lines += ["_Sin documentos fiscales en el período._", ""]
        return lines
    lines += ["| Fuente | Año | Documento | URL |", "|---|---|---|---|"]
    for d in docs:
        lines.append(f"| {d.get('source', '?')} | {d.get('year', '—')} | "
                     f"{d.get('title', '')} | {d.get('url', '')} |")
    lines.append("")
    return lines


def macro_block(points: List[Dict]) -> List[str]:
    lines = ["## Indicadores Macroeconómicos", ""]
    if not points:
        lines += ["_Sin indicadores macroeconómicos en el período._", ""]
        return lines
    lines += ["| Fuente | Indicador | Período | Valor | Unidad |",
              "|---|---|---|---|---|"]
    for p in points:
        lines.append(f"| {p.get('source', '?')} | {p.get('indicator', '')} | "
                     f"{p.get('period', '—')} | {_fmt(p.get('value'))} | "
                     f"{p.get('unit', '')} |")
    lines.append("")
    return lines


def build_markdown(snapshot: Dict) -> str:
    """Construye el informe en Markdown a partir del snapshot."""
    from src.analyzers.reports.weekly import (
        articles_block,
        inflation_block,
        market_block,
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