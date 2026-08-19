"""
Informe Semanal Automatizado
============================

Compila las métricas de la semana (mercado, encuestas, sentimiento de
noticias) en un informe Markdown determinista y le añade un resumen narrativo
por IA usando la cadena de LLMs con fallback (:mod:`src.analyzers.llm`).

El informe es un snapshot: si algún bloque no tiene datos (p.ej. la base está
vacía), se documenta con "_Sin datos_", nunca falla la generación.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from src.config import settings

logger = logging.getLogger(__name__)

DEFAULT_DAYS = 7
TOP_ARTICLES = 5


def _fmt_date(dt: Optional[datetime]) -> str:
    if dt is None:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d")


def _fmt_currency(value: Optional[float], digits: int = 2) -> str:
    if value is None:
        return "—"
    return f"{value:,.{digits}f}"


def market_block(rows: List[Dict]) -> List[str]:
    """Sección de mercado: tasas por fuente y variación en el período."""
    lines = ["## Mercado", ""]
    if not rows:
        lines += ["_Sin datos de mercado en el período._", ""]
        return lines

    lines += ["| Fuente | Última (Bs/USD) | Variación semanal % | Fecha |", "|---|---|---|---|"]
    for row in rows:
        lines.append(
            f"| {row.get('source', '?')} | {_fmt_currency(row.get('rate'))} | "
            f"{_fmt_currency(row.get('variation_pct'), 2)} | {_fmt_date(row.get('date'))} |"
        )
    lines.append("")
    return lines


def inflation_block(points: List[Dict]) -> List[str]:
    """Sección de inflación (últimos puntos mensuales por fuente)."""
    lines = ["## Inflación", ""]
    if not points:
        lines += ["_Sin datos de inflación en la base._", ""]
        return lines
    lines += ["| Fuente | Período | Mensual % | Anual % |", "|---|---|---|---|"]
    for row in points:
        lines.append(
            f"| {row.get('source', '?')} | {row.get('period', '—')} | "
            f"{_fmt_currency(row.get('monthly_rate'), 1)} | "
            f"{_fmt_currency(row.get('annual_rate'), 1)} |"
        )
    lines.append("")
    return lines


def surveys_block(per_segment: Dict[str, Dict]) -> List[str]:
    """Sección de encuestas: KPIs por segmento."""
    lines = ["## Encuestas", ""]
    if not per_segment:
        lines += ["_Sin respuestas de encuestas en el período._", ""]
        return lines

    for segment, info in per_segment.items():
        label = info.get("label", segment)
        lines += [f"### {label}", ""]
        kpis = info.get("kpis", {})
        n = info.get("n_responses", 0)
        lines.append(f"**Respuestas en el período:** {n}")
        if kpis:
            lines.append("")
            lines += ["| Indicador | Media (0-100) | N |", "|---|---|---|"]
            for name, kpi in kpis.items():
                lines.append(
                    f"| {kpi.get('label', name)} | {_fmt_currency(kpi.get('mean'), 1)} "
                    f"| {kpi.get('n', '—')} |"
                )
        lines.append("")
    return lines


def sentiment_block(summary: Dict) -> List[str]:
    """Sección de sentimiento de noticias/posts de la semana."""
    lines = ["## Sentimiento de Noticias", ""]
    if not summary or not summary.get("total"):
        lines += ["_Sin análisis de sentimiento en el período._", ""]
        return lines

    total = summary["total"]
    pos, neu, neg = summary["positive"], summary["neutral"], summary["negative"]
    mean = summary.get("mean_score", 0.0)
    tone = "Positivo" if mean > 0.05 else ("Negativo" if mean < -0.05 else "Neutral")
    lines += [
        f"- **Tono general:** {tone} ({mean:+.2f})",
        f"- Positivas: {pos} | Neutrales: {neu} | Negativas: {neg}",
        f"- Ítems analizados: {total}",
        "",
    ]
    return lines


def articles_block(articles: List[Dict]) -> List[str]:
    """Lista de los artículos más recientes de la semana."""
    lines = ["### Noticias destacadas", ""]
    if not articles:
        lines += ["_Sin artículos en el período._", ""]
        return lines
    lines += ["- " + _fmt_date(a.get("published")) + " — " + a.get("title", "") for a in articles]
    lines.append("")
    return lines


def build_weekly_report(
    *,
    market: Optional[List[Dict]] = None,
    inflation: Optional[List[Dict]] = None,
    surveys: Optional[Dict[str, Dict]] = None,
    sentiment: Optional[Dict] = None,
    articles: Optional[List[Dict]] = None,
    period: Optional[str] = None,
    ai_enabled: Optional[bool] = None,
) -> str:
    """Construye el informe semanal Markdown (plantilla + resumen IA opcional).

    Args:
        market: Tasas de cambio del período (dicts con source/rate/variation_pct/date).
        inflation: Puntos de inflación (dicts con source/period/monthly_rate/annual_rate).
        surveys: KPIs por segmento (segmento → {label, kpis, n_responses}).
        sentiment: Resumen de sentimiento (total/positive/neutral/negative/mean_score).
        articles: Artículos recientes (dicts con title/published).
        period: Etiqueta del período (default: semana actual ISO).
        ai_enabled: Habilita resumen IA (None = según LLMs configurados).

    Returns:
        Informe Markdown completo.
    """
    now = datetime.now(timezone.utc)
    period = period or f"Semana del {now.strftime('%Y-%m-%d')}"
    use_ai = settings.llm_providers() if ai_enabled is None else ai_enabled

    lines = [
        "# Informe Semanal — Economía Venezuela",
        "",
        f"**Período:** {period}  ",
        f"**Generado:** {now.strftime('%Y-%m-%d %H:%M UTC')}",
        "",
    ]
    lines += market_block(market or [])
    lines += inflation_block(inflation or [])
    lines += surveys_block(surveys or {})
    lines += sentiment_block(sentiment or {})
    lines += articles_block(articles or [])
    lines += ["---", "_Informe generado automáticamente (Fase A + Fase B)._"]

    base = "\n".join(lines)

    if not use_ai:
        return base

    try:
        from src.analyzers.llm import summarize

        summary = summarize(
            (
                "Eres un economista especializado en Venezuela. Redacta un "
                "resumen ejecutivo de 4-6 frases del informe semanal para un "
                "lector no técnico: contexto general, cifras clave y tendencias."
            ),
            base,
            max_tokens=400,
        )
    except Exception as exc:  # noqa: BLE001 - el informe no debe fallar
        logger.warning("Resumen IA del informe semanal no disponible: %s", exc)
        return base

    if not summary:
        return base
    return base + "\n\n## Resumen IA\n\n" + summary.strip()


def collect_weekly_snapshot(days: int = DEFAULT_DAYS, session=None) -> Dict:
    """Lee de la base los datos de la semana para el informe.

    Args:
        days: Ventana en días hacia atrás.
        session: Sesión inyectable (tests); si es None abre una propia.

    Returns:
        Dict con las secciones: market, inflation, surveys, sentiment, articles.
    """
    from src.db.repositories import MarketRepository, NewsRepository, SurveyRepository

    if session is None:
        from src.db.session import get_session
        with get_session() as session:
            return _snapshot_from_session(session, days)
    return _snapshot_from_session(session, days)


def _snapshot_from_session(session, days: int) -> Dict:
    """Lee y agrega los datos de la semana desde una sesión abierta."""
    from src.db.repositories import MarketRepository, NewsRepository, SurveyRepository

    since = datetime.now(timezone.utc) - timedelta(days=days)

    market_repo = MarketRepository(session)
    news_repo = NewsRepository(session)
    survey_repo = SurveyRepository(session)

    rates = market_repo.list_rates(since=since, limit=50)
    inflation = market_repo.list_inflation(limit=12)
    articles = news_repo.list_articles(since=since, limit=TOP_ARTICLES)
    sentiment = news_repo.sentiment_summary()

    surveys: Dict[str, Dict] = {}
    for segment in ("persona_comun", "comerciante"):
        responses = survey_repo.list_responses(segment=segment, since=since)
        kpis = _compute_kpis(segment, responses)
        surveys[segment] = {
            "label": "Persona Común" if segment == "persona_comun" else "Comerciante",
            "kpis": kpis,
            "n_responses": len(responses),
        }

    # Última tasa por fuente dentro del período, con variación semanal.
    market = _aggregate_rates(rates)
    return {
        "market": market,
        "inflation": [_to_dict(p) for p in inflation],
        "surveys": surveys,
        "sentiment": sentiment,
        "articles": [_to_dict(a) for a in articles],
    }


def _aggregate_rates(rates) -> List[Dict]:
    """Última tasa por (source, currency) y variación vs la primera del período."""
    by_source: Dict[tuple, Dict] = {}
    for r in rates:
        key = (r.source, r.currency)
        entry = by_source.setdefault(
            key,
            {"source": r.source, "currency": r.currency, "first": r.rate, "date": r.date},
        )
        entry["rate"] = r.rate
        entry["date"] = max(entry["date"], r.date) if entry["date"] else r.date
    out = []
    for (source, currency), e in by_source.items():
        variation = None
        if e.get("first"):
            variation = ((e["rate"] - e["first"]) / e["first"]) * 100.0
        out.append({
            "source": source,
            "currency": currency,
            "rate": e["rate"],
            "variation_pct": variation,
            "date": e["date"],
        })
    return out


def _compute_kpis(segment: str, responses) -> Dict[str, Dict]:
    from src.dashboard.surveys_data import kpi_cards

    kpis = kpi_cards(responses)
    return {
        name: {"label": kpi.label, "mean": kpi.mean, "n": kpi.n_responses}
        for name, kpi in kpis.items()
    }


def _to_dict(obj) -> Dict:
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return dict(obj)


def save_report(markdown: str, output_path: Optional[str] = None) -> str:
    """Persiste el informe en ``data/reports/weekly_<fecha>.md``.

    Args:
        markdown: Contenido del informe.
        output_path: Ruta opcional (default: data/reports/weekly_YYYY-Www.md).

    Returns:
        Ruta donde se guardó.
    """
    from pathlib import Path

    if output_path is None:
        now = datetime.now()
        iso = now.isocalendar()
        name = f"weekly_{now.year}-W{iso.week:02d}.md"
        output_path = str(Path("data", "reports", name))
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(markdown, encoding="utf-8")
    return output_path


def generate_weekly_report(output_path: Optional[str] = None, days: int = DEFAULT_DAYS) -> str:
    """Ejecuta el flujo completo: snapshot → informe → guardar.

    Returns:
        Ruta del informe generado.
    """
    snapshot = collect_weekly_snapshot(days=days)
    markdown = build_weekly_report(
        market=snapshot["market"],
        inflation=snapshot["inflation"],
        surveys=snapshot["surveys"],
        sentiment=snapshot["sentiment"],
        articles=snapshot["articles"],
    )
    return save_report(markdown, output_path)