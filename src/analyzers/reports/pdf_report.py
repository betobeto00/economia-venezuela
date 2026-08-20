"""
Informes económicos en PDF
==========================

Genera informes profesionales en PDF (ReportLab + matplotlib) a partir de un
snapshot estructurado. El snapshot es un dict con las secciones:

``market_series`` (serie completa para gráficos), ``market`` (última tasa por
fuente con variación), ``inflation`` (puntos mensuales), ``surveys`` (KPIs por
segmento), ``sentiment`` (resumen de sentimiento), ``articles`` (noticias),
``fiscal_docs`` (gacetas y leyes/actos de la AN), ``macro`` (indicadores
internacionales) y opcionalmente ``resumen`` (texto IA).

El renderizador nunca falla: sección sin datos se omite o se documenta con
"_Sin datos_".
"""

import logging
from datetime import datetime
from html import escape as _esc
from io import BytesIO
from src.analyzers.reports.weekly import _clean_summary, _strip_html
from typing import Dict, List, Optional

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ paleta
NAVY = colors.HexColor("#12355B")
NAVY_LIGHT = colors.HexColor("#1E4E7B")
GOLD = colors.HexColor("#C9A227")
RED = colors.HexColor("#B3392F")
GREEN = colors.HexColor("#2E7D32")
GRAY = colors.HexColor("#6B7280")
LIGHT = colors.HexColor("#F4F6F8")
BORDER = colors.HexColor("#D8DEE6")
TEXT = colors.HexColor("#1F2937")

CHART_COLORS = ["#12355B", "#C9A227", "#B3392F", "#2E7D32", "#7C3AED", "#0E7490"]

_SOURCE_LABELS = {"bcv": "BCV", "binance": "Binance", "bybit": "Bybit"}

CADENCE_LABELS = {
    "diario": "Informe Diario",
    "semanal": "Informe Semanal",
    "mensual": "Informe Mensual",
    "trimestral": "Informe Trimestral",
    "semestral": "Informe Semestral",
    "anual": "Informe Anual",
}

_TITLE_FONT = "Helvetica-Bold"
_BODY_FONT = "Helvetica"

# ------------------------------------------------------------------ estilos
def _styles() -> Dict:
    base = getSampleStyleSheet()
    s = {
        "CoverTitle": ParagraphStyle(
            "CoverTitle", fontName=_TITLE_FONT, fontSize=24,
            leading=29, textColor=colors.white, alignment=TA_CENTER,
        ),
        "CoverSub": ParagraphStyle(
            "CoverSub", fontName=_BODY_FONT, fontSize=12,
            leading=16, textColor=colors.HexColor("#E5EAF1"),
            alignment=TA_CENTER,
        ),
        "CoverMeta": ParagraphStyle(
            "CoverMeta", fontName=_BODY_FONT, fontSize=10,
            leading=14, textColor=colors.HexColor("#C9D3E0"),
            alignment=TA_CENTER,
        ),
        "H1": ParagraphStyle(
            "H1", fontName=_TITLE_FONT, fontSize=15, leading=19,
            textColor=NAVY, spaceBefore=16, spaceAfter=8,
        ),
        "H2": ParagraphStyle(
            "H2", fontName=_TITLE_FONT, fontSize=12, leading=15,
            textColor=TEXT, spaceBefore=10, spaceAfter=5,
        ),
        "Body": ParagraphStyle(
            "Body", fontName=_BODY_FONT, fontSize=9.5, leading=13,
            textColor=TEXT, alignment=TA_JUSTIFY, spaceAfter=4,
        ),
        "Small": ParagraphStyle(
            "Small", fontName=_BODY_FONT, fontSize=8, leading=11,
            textColor=GRAY, spaceAfter=2,
        ),
        "Cell": ParagraphStyle(
            "Cell", fontName=_BODY_FONT, fontSize=8.5, leading=11,
            textColor=TEXT,
        ),
        "CellB": ParagraphStyle(
            "CellB", fontName=_TITLE_FONT, fontSize=8.5, leading=11,
            textColor=colors.white,
        ),
    }
    return s


# ------------------------------------------------------------------ gráficos
def _fig_to_image(fig, width: float, height: float) -> Image:
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=180, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=width, height=height)


def _rates_chart(rows: List[Dict]) -> Optional[Image]:
    """Líneas de tasa por fuente: mediana diaria, etiquetas por día."""
    if not rows:
        return None

    def _parse_dt(value):
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value))
        except ValueError:
            return None

    points = [
        (r.get("source"), r.get("currency"), _parse_dt(r.get("date")), r.get("rate"))
        for r in rows
    ]
    df = pd.DataFrame(points, columns=["source", "currency", "date", "rate"])
    df = df.dropna(subset=["rate", "date"])
    df["day"] = pd.to_datetime(df["date"].dt.date)
    span_days = (df["day"].max() - df["day"].min()).days
    # Rellenar días faltantes por fuente (forward-fill): un punto por día del
    # período para que la línea sea continua desde el primer al último día.
    full_index = pd.date_range(df["day"].min(), df["day"].max(), freq="D")
    frames = []
    for (source, currency), grp in df.groupby(["source", "currency"]):
        series = (
            grp.drop_duplicates("day", keep="last")
            .set_index("day")["rate"]
            .reindex(full_index)
            .ffill()
            .dropna()
        )
        frames.append(pd.DataFrame({
            "source": source, "currency": currency,
            "day": series.index, "rate": series.values,
        }))
    daily = pd.concat(frames, ignore_index=True)
    if daily.empty:
        return None

    fig, ax = plt.subplots(figsize=(8.8, 3.6))
    for i, ((source, currency), grp) in enumerate(
        daily.groupby(["source", "currency"])
    ):
        grp = grp.sort_values("day")
        ax.plot(
            grp["day"], grp["rate"], marker="o", markersize=4,
            linewidth=1.8, color=CHART_COLORS[i % len(CHART_COLORS)],
            label=_SOURCE_LABELS.get(source, source),
        )
    ax.set_title("Tasa de cambio por fuente (Bs/USD) — un punto por día",
                 fontsize=10, color="#12355B", fontweight="bold")
    fmt = "%d" if span_days <= 15 else "%m-%d"
    ax.xaxis.set_major_formatter(mdates.DateFormatter(fmt))
    ax.xaxis.set_major_locator(mdates.DayLocator())
    ax.legend(fontsize=8, loc="best", frameon=False, ncol=3)
    ax.grid(alpha=0.3, linestyle="--", axis="y")
    ax.set_xlim(daily["day"].min() - pd.Timedelta(days=0.5),
                daily["day"].max() + pd.Timedelta(days=0.5))
    ax.tick_params(labelsize=8)
    fig.tight_layout()
    return _fig_to_image(fig, 17 * cm, 6.8 * cm)


def _inflation_chart(points: List[Dict]) -> Optional[Image]:
    """Barras agrupadas de inflación mensual vs anual por fuente."""
    if not points:
        return None
    labels = [f"{p.get('source', '?')}\n{p.get('period', '')}" for p in points]
    monthly = [p.get("monthly_rate") or 0 for p in points]
    annual = [p.get("annual_rate") or 0 for p in points]
    x = range(len(labels))
    fig, ax = plt.subplots(figsize=(8.6, 3.2))
    w = 0.38
    ax.bar([i - w / 2 for i in x], monthly, width=w, label="Mensual %",
           color=CHART_COLORS[0])
    ax.bar([i + w / 2 for i in x], annual, width=w, label="Anual %",
           color=CHART_COLORS[1])
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=7)
    ax.set_title("Inflación por fuente (%)", fontsize=10, color="#12355B",
                 fontweight="bold")
    ax.legend(fontsize=7)
    ax.grid(alpha=0.3, axis="y", linestyle="--")
    ax.tick_params(labelsize=7)
    fig.tight_layout()
    return _fig_to_image(fig, 17 * cm, 6 * cm)


def _sentiment_chart(summary: Dict) -> Optional[Image]:
    """Dona de distribución de sentimiento."""
    if not summary or not summary.get("total"):
        return None
    labels = ["Positivas", "Neutrales", "Negativas"]
    sizes = [summary.get("positive", 0), summary.get("neutral", 0),
             summary.get("negative", 0)]
    if sum(sizes) == 0:
        return None
    fig, ax = plt.subplots(figsize=(3.4, 3.4))
    colors_ = ["#2E7D32", "#C9A227", "#B3392F"]
    wedges, _texts, autotexts = ax.pie(
        sizes, labels=labels, autopct="%1.0f%%", startangle=90,
        colors=colors_, textprops={"fontsize": 8},
    )
    for at in autotexts:
        at.set_color("white")
        at.set_fontsize(8)
        at.set_fontweight("bold")
    ax.set_title("Sentimiento de noticias", fontsize=10, color="#12355B",
                 fontweight="bold")
    return _fig_to_image(fig, 6.5 * cm, 6.5 * cm)


def _surveys_chart(surveys: Dict[str, Dict]) -> Optional[Image]:
    """Barras horizontales del KPI por segmento (media 0-100), sin deformar."""
    if not surveys:
        return None
    bars = [
        (info.get("label", segment), kpi.get("label", name))
        for segment, info in surveys.items()
        for name, kpi in (info.get("kpis") or {}).items()
    ]
    if not bars:
        return None
    fig_w, fig_h = 8.8, max(2.4, len(bars) * 0.55 + 0.8)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    for y, (segment_label, kpi_label) in enumerate(bars):
        for segment, info in surveys.items():
            for name, kpi in (info.get("kpis") or {}).items():
                if info.get("label", segment) == segment_label and \
                        kpi.get("label", name) == kpi_label:
                    mean = kpi.get("mean", 0)
                    ax.barh(y, mean, height=0.55,
                            color=CHART_COLORS[y % len(CHART_COLORS)])
                    ax.text(mean + 1, y, f"{mean:.1f}", va="center",
                            fontsize=8, fontweight="bold")
                    ax.text(0.3, y, f"{segment_label} — {kpi_label}",
                            va="center", ha="left", fontsize=8,
                            color="white")
    ax.set_xlim(0, 100)
    ax.set_yticks([])
    ax.set_ylim(-0.6, len(bars) - 0.4)
    ax.set_title("KPIs de encuestas por segmento (0-100)", fontsize=10,
                 color="#12355B", fontweight="bold")
    ax.grid(alpha=0.3, axis="x", linestyle="--")
    ax.tick_params(labelsize=8)
    fig.tight_layout()
    aspect = fig_h / fig_w
    return _fig_to_image(fig, 17 * cm, 17 * cm * aspect)


# ------------------------------------------------------------------ helpers
def _p(text: str, style) -> Paragraph:
    return Paragraph(str(text), style)


def _cell(c) -> Paragraph:
    """Convierte ``c`` a Paragraph; si ya lo es, lo devuelve tal cual."""
    if isinstance(c, Paragraph):
        return c
    return _p(c, styles["Cell"])


def _data_table(headers: List[str], rows: List[List[str]],
                widths: Optional[List] = None) -> Optional[Table]:
    if not rows:
        return None
    data = [[_p(h, styles["CellB"]) for h in headers]]
    for r in rows:
        data.append([_cell(c) for c in r])
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    table.setStyle(TableStyle(style))
    return table


styles = _styles()


def _section(story, title: str) -> None:
    story.append(Spacer(1, 6))
    story.append(Paragraph(title, styles["H1"]))
    story.append(HRFlowable(width="100%", thickness=1.2, color=GOLD,
                            spaceAfter=8))


def _kv_table(items: List[tuple]) -> Table:
    rows = [[_p(k, styles["Cell"]), _p(str(v), styles["Cell"])] for k, v in items]
    table = Table(rows, colWidths=[5 * cm, 12 * cm], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


def _fmt_currency(value, digits: int = 2) -> str:
    if value is None:
        return "—"
    return f"{value:,.{digits}f}"


def _fmt_date(value) -> str:
    if not value:
        return "—"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    return str(value)


# ------------------------------------------------------------------ secciones
def _cover(story, snapshot: Dict) -> None:
    title = CADENCE_LABELS.get(snapshot.get("cadence", ""), "Informe Económico")
    period = snapshot.get("period") or ""
    now = snapshot.get("generated_at") or datetime.now()

    band = Table(
        [[Paragraph(title, styles["CoverTitle"])]],
        colWidths=[17.5 * cm],
        rowHeights=[3 * cm],
    )
    band.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.35 * cm, GOLD),
    ]))
    story.append(band)
    story.append(Spacer(1, 10))
    story.append(Paragraph("Economía de Venezuela", styles["CoverSub"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"Período: {period}  |  Generado: {now:%Y-%m-%d %H:%M}",
        styles["CoverMeta"],
    ))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Mercado cambiario · inflación · encuestas · sentimiento · "
        "noticias · marco fiscal · indicadores macro · proyección",
        styles["CoverMeta"],
    ))
    story.append(Spacer(1, 10))


def _resumen(story, snapshot: Dict) -> None:
    _section(story, "Resumen Ejecutivo")
    resumen = snapshot.get("resumen") or ""
    if resumen:
        story.append(_p(resumen, styles["Body"]))
    else:
        market = snapshot.get("market") or []
        if market:
            first = market[0]
            line = (
                f"En el período {snapshot.get('period') or 'de referencia'}, la "
                f"tasa de referencia de {first.get('source', '?')} se ubicó en "
                f"{_fmt_currency(first.get('rate'))} Bs/USD. "
                f"{len(market)} fuente(s) reportaron cotizaciones."
            )
        else:
            line = "No se disponen datos cuantitativos para el período."
        story.append(_p(line, styles["Body"]))


def _mercado(story, snapshot: Dict) -> None:
    _section(story, "Mercado Cambiario")
    market = snapshot.get("market") or []
    if not market:
        story.append(_p("_Sin datos de mercado en el período._", styles["Body"]))
        return
    headers = ["Fuente", "Moneda", "Última (Bs/USD)", "Variación %", "Fecha"]
    rows = [
        [_SOURCE_LABELS.get(r.get("source"), r.get("source", "?")),
         r.get("currency", "usd").upper(),
         _fmt_currency(r.get("rate")),
         _fmt_currency(r.get("variation_pct"), 2), _fmt_date(r.get("date"))]
        for r in market
    ]
    t = _data_table(headers, rows, widths=[3.2 * cm, 2 * cm, 4 * cm, 3.6 * cm, 3.6 * cm])
    if t:
        story.append(t)
    chart = _rates_chart(snapshot.get("market_series") or market)
    if chart:
        story.append(Spacer(1, 6))
        story.append(chart)


def _bancos(story, snapshot: Dict) -> None:
    _section(story, "Cotizaciones Bancarias (Bs/USD)")
    bancos = snapshot.get("bancos") or []
    if not bancos:
        story.append(_p("_Sin tasas bancarias disponibles._", styles["Body"]))
        return
    # BCV oficial
    bcv = [b for b in bancos if b.get("source") == "bcv"]
    if bcv:
        story.append(_p(
            f"BCV oficial: {_fmt_currency(bcv[0].get('rate'))} Bs/USD",
            styles["Body"],
        ))
        story.append(Spacer(1, 4))
    # Bancos
    others = sorted(
        [b for b in bancos if b.get("source") != "bcv"],
        key=lambda x: x.get("rate", 0),
    )
    if others:
        headers = ["Banco", "Tasa (Bs/USD)", "Fecha"]
        rows = [
            [b.get("source", "?"),
             _fmt_currency(b.get("rate")),
             str(b.get("date", "—"))[:10]]
            for b in others
        ]
        t = _data_table(headers, rows, widths=[6 * cm, 4 * cm, 4 * cm])
        if t:
            story.append(t)


def _inflacion(story, snapshot: Dict) -> None:
    _section(story, "Inflación")
    points = snapshot.get("inflation") or []
    if not points:
        story.append(_p("_Sin datos de inflación en la base._", styles["Body"]))
        return
    headers = ["Fuente", "Período", "Mensual %", "Anual %"]
    rows = [
        [f"({p.get('source', '?').upper()})", p.get("period", "—"),
         _fmt_currency(p.get("monthly_rate"), 1),
         _fmt_currency(p.get("annual_rate"), 1)]
        for p in points
    ]
    t = _data_table(headers, rows, widths=[3.2 * cm, 3.2 * cm, 4.2 * cm, 4.2 * cm])
    if t:
        story.append(t)
    chart = _inflation_chart(points)
    if chart:
        story.append(Spacer(1, 6))
        story.append(chart)


def _encuestas(story, snapshot: Dict) -> None:
    _section(story, "Encuestas")
    surveys = snapshot.get("surveys") or {}
    if not surveys:
        story.append(_p("_Sin respuestas de encuestas en el período._",
                        styles["Body"]))
        return
    for segment, info in surveys.items():
        label = info.get("label", segment)
        story.append(Paragraph(label, styles["H2"]))
        story.append(_p(
            f"Respuestas en el período: {info.get('n_responses', 0)}",
            styles["Small"],
        ))
        kpis = info.get("kpis") or {}
        if kpis:
            headers = ["Indicador", "Media (0-100)", "N"]
            rows = [
                [kpi.get("label", name), _fmt_currency(kpi.get("mean"), 1),
                 str(kpi.get("n", "—"))]
                for name, kpi in kpis.items()
            ]
            t = _data_table(headers, rows, widths=[8 * cm, 4 * cm, 2.5 * cm])
            if t:
                story.append(t)
    chart = _surveys_chart(surveys)
    if chart:
        story.append(Spacer(1, 6))
        story.append(chart)


def _sentimiento(story, snapshot: Dict) -> None:
    _section(story, "Sentimiento de Noticias")
    summary = snapshot.get("sentiment") or {}
    if not summary or not summary.get("total"):
        story.append(_p("_Sin análisis de sentimiento en el período._",
                        styles["Body"]))
        return
    total = summary["total"]
    mean = summary.get("mean_score", 0.0)
    tone = "Positivo" if mean > 0.05 else ("Negativo" if mean < -0.05 else "Neutral")
    items = [
        ("Tono general", f"{tone} ({mean:+.2f})"),
        ("Positivas", str(summary.get("positive", 0))),
        ("Neutrales", str(summary.get("neutral", 0))),
        ("Negativas", str(summary.get("negative", 0))),
        ("Ítems analizados", str(total)),
    ]
    chart = _sentiment_chart(summary)
    if chart:
        block = [
            chart,
            Spacer(1, 6),
            _kv_table(items),
        ]
        story.append(KeepTogether(block))
    else:
        story.append(_kv_table(items))


def _noticias(story, snapshot: Dict) -> None:
    _section(story, "Noticias Destacadas")
    articles = snapshot.get("articles") or []
    if not articles:
        story.append(_p("_Sin artículos en el período._", styles["Body"]))
        return

    def _cell(a: Dict) -> Paragraph:
        title = _esc(_strip_html(a.get("title", "")))
        summary = _clean_summary(a.get("summary") or "")[:240]
        text = f"<b>{title}</b>"
        if summary:
            text += f"<br/><font size=7 color='#6B7280'>{_esc(summary)}</font>"
        return Paragraph(text, styles["Cell"])

    rows = [
        [_fmt_date(a.get("published")),
         _esc(str(a.get("source", "?"))),
         _cell(a)]
        for a in articles
    ]
    t = _data_table(["Fecha", "Fuente", "Título y resumen"], rows,
                    widths=[2.6 * cm, 3 * cm, 11.6 * cm])
    if t:
        story.append(t)


def _marco_fiscal(story, snapshot: Dict) -> None:
    _section(story, "Marco Fiscal y Legislativo Reciente")
    docs = snapshot.get("fiscal_docs") or []
    if not docs:
        story.append(_p("_Sin trámites fiscales con impacto económico en el "
                        "período._", styles["Body"]))
        return

    def _desc_cell(d: Dict) -> Paragraph:
        text = f"<b>{_esc(_strip_html(d.get('title', '')))}</b>"
        desc = _strip_html(d.get("description") or "")[:260]
        if desc and desc != _strip_html(d.get('title')):
            text += f"<br/><font size=7 color='#374151'>{_esc(desc)}</font>"
        return Paragraph(text, styles["Cell"])

    rows = [
        [_fmt_date(d.get("date")),
         _SOURCE_LABELS.get(d.get("source"), d.get("source", "?")),
         _desc_cell(d)]
        for d in docs[:20]
    ]
    t = _data_table(["Fecha", "Fuente", "Trámite / Impacto económico"], rows,
                    widths=[2.4 * cm, 2 * cm, 12.6 * cm])
    if t:
        story.append(t)
    story.append(_p(
        "Solo se listan los trámites con posible impacto económico "
        "(presupuesto, endeudamiento, impuestos, comercio, ...).",
        styles["Small"],
    ))


def _macro(story, snapshot: Dict) -> None:
    _section(story, "Indicadores Macroeconómicos")
    macro = snapshot.get("macro") or []
    if not macro:
        story.append(_p("_Sin indicadores macroeconómicos disponibles._",
                        styles["Body"]))
        return

    def _impact_cell(m: Dict) -> Paragraph:
        return Paragraph(
            _esc(str(m.get("impact") or "")), styles["Cell"],
        )

    headers = ["Fuente", "Indicador", "Período", "Valor", "Nota"]
    rows = [
        [_SOURCE_LABELS.get(m.get("source"), m.get("source", "?")),
         _esc(str(m.get("indicator", ""))),
         _esc(str(m.get("period", "—"))),
         _fmt_currency(m.get("value"), 2),
         _impact_cell(m)]
        for m in macro
    ]
    t = _data_table(headers, rows,
                    widths=[2.4 * cm, 3.6 * cm, 2.2 * cm, 2.6 * cm, 6.2 * cm])
    if t:
        story.append(t)
    story.append(_p(
        "Última observación disponible; los datos anuales son contexto "
        "estructural, no impulsores de la semana.",
        styles["Small"],
    ))


def _proyeccion(story, snapshot: Dict) -> None:
    _section(story, "Proyección para la próxima semana")
    proyeccion = snapshot.get("proyeccion") or ""
    rows = snapshot.get("proyeccion_rows") or []
    if proyeccion:
        story.append(_p(proyeccion, styles["Body"]))
    elif rows:
        story.append(_p(
            "Proyección heurística: última tasa × (1 + variación del período).",
            styles["Small"],
        ))
        t = _data_table(
            ["Fuente", "Proyección (Bs/USD)"],
            [[_SOURCE_LABELS.get(r.get("source"), r.get("source", "?")),
              _fmt_currency(r.get("rate"))] for r in rows],
            widths=[6 * cm, 6 * cm],
        )
        if t:
            story.append(t)
    else:
        story.append(_p(
            "_Sin datos suficientes para proyectar el próximo período._",
            styles["Body"],
        ))
        return
    story.append(_p(
        "Proyección a partir de la tendencia del período; no constituye "
        "asesoría financiera.",
        styles["Small"],
    ))


def _footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont(_BODY_FONT, 7.5)
    canvas.setFillColor(GRAY)
    canvas.drawString(2 * cm, 1.1 * cm,
                      "Economía Venezuela — informe automático (Fases A + B + 5b)")
    canvas.drawRightString(19.5 * cm, 1.1 * cm, f"Página {doc.page}")
    canvas.restoreState()


def render_pdf(snapshot: Dict, output_path: str) -> str:
    """Renderiza el snapshot como PDF profesional.

    Args:
        snapshot: Dict con las secciones del informe.
        output_path: Ruta de salida del PDF.

    Returns:
        Ruta del PDF generado.
    """
    story = []
    _cover(story, snapshot)
    story.append(PageBreak())

    _resumen(story, snapshot)
    _mercado(story, snapshot)
    _bancos(story, snapshot)
    _inflacion(story, snapshot)
    story.append(PageBreak())
    _encuestas(story, snapshot)
    _sentimiento(story, snapshot)
    story.append(PageBreak())
    _noticias(story, snapshot)
    _marco_fiscal(story, snapshot)
    _macro(story, snapshot)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="Informe Económico de Venezuela",
        author="Economía Venezuela",
    )
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    logger.info("PDF generado en %s", output_path)
    return output_path