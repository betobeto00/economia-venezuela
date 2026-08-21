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


def _collect_social() -> Dict:
    """Recolecta datos sociales (Reddit posts + sentimiento) para el informe."""
    try:
        from sqlalchemy import func, select
        from src.db.models import SocialPostORM, SentimentScoreORM
        from src.db.session import get_session

        with get_session() as sess:
            total = sess.scalar(select(func.count(SocialPostORM.id))) or 0
            avg_score = sess.scalar(select(func.avg(SocialPostORM.score)))
            avg_comments = sess.scalar(select(func.avg(SocialPostORM.num_comments)))
            sent_rows = sess.execute(
                select(SentimentScoreORM.label, func.count(SentimentScoreORM.id))
                .where(SentimentScoreORM.item_type == "social")
                .group_by(SentimentScoreORM.label)
            ).all()
            sentiment_dist = {label: int(n) for label, n in sent_rows}
            sentiment_mean = sess.scalar(
                select(func.avg(SentimentScoreORM.score))
                .where(SentimentScoreORM.item_type == "social")
            )
            ch_rows = sess.execute(
                select(SocialPostORM.channel, func.count(SocialPostORM.id))
                .group_by(SocialPostORM.channel)
            ).all()
            posts_per_channel = {ch: int(n) for ch, n in ch_rows}
            # Posts con sentimiento
            posts_orm = sess.scalars(
                select(SocialPostORM).order_by(SocialPostORM.published.desc()).limit(10)
            ).all()
            sent_map = {}
            for s in sess.scalars(
                select(SentimentScoreORM).where(SentimentScoreORM.item_type == "social")
            ).all():
                sent_map[s.item_id] = s
            posts = []
            for p in posts_orm:
                s = sent_map.get(p.id)
                posts.append({
                    "title": p.title, "url": p.url,
                    "score": p.score, "num_comments": p.num_comments,
                    "sentiment_label": s.label if s else None,
                    "sentiment_score": float(s.score) if s else None,
                })

        return {
            "total_posts": int(total),
            "avg_score": round(float(avg_score or 0), 1),
            "avg_comments": round(float(avg_comments or 0), 1),
            "sentiment_dist": sentiment_dist,
            "sentiment_mean": round(float(sentiment_mean or 0), 4),
            "posts_per_channel": posts_per_channel,
            "posts": posts,
        }
    except Exception as exc:
        logger.warning("Datos sociales no disponibles para informe: %s", exc)
        return {}


def _collect_bancos() -> List[Dict]:
    """Tasas de bancos venezolanos + BCV oficial via pyDolarVenezuela."""
    try:
        from src.collectors.market.dolar_paralelo_collector import fetch_bancos

        rates = fetch_bancos()
        return [
            {"source": r.source, "rate": r.rate, "date": r.date.isoformat()}
            for r in rates
        ]
    except Exception as exc:  # noqa: BLE001 - sección opcional
        logger.warning("Dólar paralelo no disponible para el informe: %s", exc)
        return []


def _collect_ibc_index(session=None, since=None, until=None) -> Dict:
    """Datos del índice IBC y sus componentes desde la BD."""
    try:
        from src.db.repositories import IBCIndexRepository
        from src.db.session import get_session

        if session is None:
            with get_session() as sess:
                return _query_ibc_index(sess, since, until)
        return _query_ibc_index(session, since, until)
    except Exception as exc:  # noqa: BLE001
        logger.warning("IBC desde BD no disponible: %s", exc)
        return {}


def _query_ibc_index(session, since, until) -> Dict:
    """Consulta IBC desde la BD."""
    from src.db.repositories import IBCIndexRepository

    repo = IBCIndexRepository(session)
    index_points = repo.list_index(since=since, until=until, limit=1)
    components = repo.list_components(since=since, until=until, limit=20)

    if not index_points and not components:
        return {}

    point = index_points[0] if index_points else {}

    # Agrupar componentes por fecha más reciente
    latest_date = components[0]["date"] if components else None
    latest_comps = [c for c in components if c["date"] == latest_date] if latest_date else []

    gainers = sorted(
        [c for c in latest_comps if c["change_pct"] > 0],
        key=lambda x: x["change_pct"], reverse=True,
    )
    losers = sorted(
        [c for c in latest_comps if c["change_pct"] < 0],
        key=lambda x: x["change_pct"],
    )

    return {
        "value": point.get("value", 0),
        "change": point.get("change", 0),
        "change_pct": point.get("change_pct", 0),
        "date": point.get("date", ""),
        "components": [
            {"ticker": c["ticker"], "name": c["name"],
             "price": c["price"], "change_pct": c["change_pct"],
             "volume": c["volume"]}
            for c in latest_comps
        ],
        "gainers": [
            {"ticker": c["ticker"], "name": c["name"],
             "price": c["price"], "change_pct": c["change_pct"]}
            for c in gainers[:5]
        ],
        "losers": [
            {"ticker": c["ticker"], "name": c["name"],
             "price": c["price"], "change_pct": c["change_pct"]}
            for c in losers[:5]
        ],
    }


def _collect_ibc_stocks(session=None, since=None, until=None) -> Dict:
    """Otros tickers venezolanos relevantes desde la BD."""
    try:
        from src.db.repositories import VenezuelanTickerRepository
        from src.db.session import get_session

        if session is None:
            with get_session() as sess:
                return _query_tickers(sess, since, until)
        return _query_tickers(session, since, until)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Tickers venezolanos desde BD no disponibles: %s", exc)
        return {}


def _query_tickers(session, since, until) -> Dict:
    """Consulta tickers venezolanos desde la BD."""
    from src.db.repositories import VenezuelanTickerRepository

    repo = VenezuelanTickerRepository(session)
    tickers = repo.list_tickers(since=since, until=until, limit=100)

    if not tickers:
        return {}

    # Tomar la fecha más reciente
    latest_date = tickers[0]["date"] if tickers else None
    latest = [t for t in tickers if t["date"] == latest_date] if latest_date else []

    by_change = sorted(latest, key=lambda x: x["change_pct"], reverse=True)

    return {
        "gainers": [
            {"ticker": t["ticker"], "name": t["name"],
             "close": t["close"], "change_pct": t["change_pct"],
             "avg_volume": t["avg_volume"]}
            for t in by_change[:5] if t["change_pct"] > 0
        ],
        "losers": [
            {"ticker": t["ticker"], "name": t["name"],
             "close": t["close"], "change_pct": t["change_pct"],
             "avg_volume": t["avg_volume"]}
            for t in by_change[-5:][::-1] if t["change_pct"] < 0
        ],
    }


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
                "El informe contiene datos de:\n"
                "- Mercado cambiario (BCV, Binance, Bybit, bancos)\n"
                "- Inflación y sentimiento de mercado\n"
                "- IBC y mercados bursátiles\n"
                "- Noticias y redes sociales (Reddit)\n"
                "- Marco fiscal (gacetas, leyes AN)\n"
                "- Indicadores macro (PIB, inflación FMI, petróleo OPEP)\n"
                "- Riesgo soberano, balanza de pagos, deuda pública\n"
                "- Pronóstico integral con escenarios\n"
                "- Nowcasting con modelos ML (RandomForest, GradientBoosting)\n"
                "Incluye:\n"
                "1. Contexto general del período.\n"
                "2. Mercado cambiario: tendencias por fuente, brechas, volatilidad.\n"
                "3. Inflación: trayectoria y comparación con el período anterior.\n"
                "4. Sentimiento de noticias y encuestas: qué señal envía la calle.\n"
                "5. Marco fiscal y macro: qué cambió y por qué importa.\n"
                "6. Riesgo soberano y balanza de pagos: análisis integral.\n"
                "7. Deuda pública y sostenibilidad fiscal.\n"
                "8. Pronóstico ML y nowcasting: qué dicen los modelos.\n"
                "9. Proyección para la próxima semana: hacia dónde apuntan "
                "tipo de cambio, inflación y sentimiento; riesgos al alza y "
                "a la baja.\n"
                "Termina cada frase con punto final. "
                "Responde siempre en español."
            ),
            markdown,
            max_tokens=3000,
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


def _collect_macro_analytics() -> Dict:
    """Recolecta datos de analizadores macro para el informe.

    Incluye: Riesgo Soberano, Balanza de Pagos, Deuda Pública, Pronóstico.
    Usa datos reales de macro_data (CSV petróleo, DB, APIs internacionales).
    """
    # Cargar datos reales una sola vez
    try:
        from src.dashboard.macro_data import (
            oil_price_current, oil_production_ve, reserves_usd,
            imports_monthly, gdp_usd, total_debt_usd, fiscal_deficit_pct,
        )
        _oil_price = oil_price_current()
        _oil_prod = oil_production_ve()
        _reserves = reserves_usd()
        _imports = imports_monthly()
        _gdp = gdp_usd()
        _debt = total_debt_usd()
        _deficit = fiscal_deficit_pct()
        _oil_rev = _oil_prod * _oil_price * 365 * 1e6  # USD/año
    except Exception:
        # Fallback a estimaciones si macro_data falla
        _oil_price, _oil_prod = 70.0, 1.08
        _reserves, _imports = 5.5e9, 2.0e9
        _gdp, _debt, _deficit = 94e9, 150e9, 5.8
        _oil_rev = _oil_prod * _oil_price * 365 * 1e6

    # Cargar datos de mercado para brecha cambiaria real
    _brecha = 30.0  # Default
    try:
        from src.dashboard.market_data import dashboard_metrics
        metrics = dashboard_metrics()
        if metrics.get("oficial") and metrics.get("paralelo") and metrics["oficial"].rate > 0:
            _brecha = (metrics["paralelo"].rate / metrics["oficial"].rate - 1) * 100
    except Exception:
        pass

    # Cargar inflación actual
    _inflation = 10.0  # Default mensual
    try:
        from src.dashboard.market_data import dashboard_metrics
        metrics = dashboard_metrics()
        if metrics.get("inflacion") and metrics["inflacion"].monthly_rate:
            _inflation = metrics["inflacion"].monthly_rate
    except Exception:
        pass

    result = {}

    # ── Riesgo Soberano ──
    try:
        from src.analyzers.sovereign_risk import SovereignRiskIndex
        from src.dashboard.bvc_capitalization import get_capitalization_summary
        cap = get_capitalization_summary()
        risk = SovereignRiskIndex()

        # Calcular volatilidad desde historial de TC
        _volatility = 0.0
        try:
            from src.db.session import get_session as _get_sess
            from src.db.repositories import MarketRepository as _MR
            with _get_sess() as _sess:
                _rates = _MR(_sess).list_rates(
                    since=datetime.now(timezone.utc) - timedelta(days=30),
                    limit=200,
                )
                _volatility = SovereignRiskIndex.compute_volatility_from_rates(_rates)
        except Exception:
            pass

        # Calcular incertidumbre
        _sent_vol, _survey_disp, _forecast_err = 0.0, 0.0, 0.0
        try:
            from src.dashboard.social_data import social_summary as _soc_sum
            _soc = _soc_sum()
            _sent_vol, _survey_disp, _forecast_err = SovereignRiskIndex.compute_uncertainty_from_data(
                sentiment_mean=_soc.get("sentiment_mean", 0),
                sentiment_count=_soc.get("total_posts", 0),
            )
        except Exception:
            pass

        risk_result = risk.calculate(
            spread_pct=_brecha,
            volatility=_volatility,
            annual_inflation=_inflation * 12,  # Mensual → anual
            reserves_months=_reserves / _imports if _imports > 0 else 0,
            debt_gdp_pct=_debt / _gdp * 100 if _gdp > 0 else 250,
            oil_production_mbd=_oil_prod,
            sanctions_level=80,  # Sanciones US/UE activas
            social_unrest=30,    # Tensión social moderada
            governance_score=25, # Gobernanza baja
            sentiment_volatility=_sent_vol,
            survey_dispersion=_survey_disp,
            forecast_error=_forecast_err,
            market_cap_bs=cap.get("total_bs", 0),
            market_cap_change_pct=cap.get("total_change_pct", 0),
            market_cap_months=cap.get("months_available", 0),
        )
        result["sovereign_risk"] = {
            "score": risk_result.score,
            "level": risk_result.level,
            "components": risk_result.components,
            "interpretation": risk_result.interpretation,
        }
    except Exception as exc:
        logger.warning("Riesgo soberano no disponible: %s", exc)

    # ── Balanza de Pagos ──
    try:
        from src.analyzers.balance_of_payments import BalanceOfPaymentsAnalyzer
        bop = BalanceOfPaymentsAnalyzer()
        bop_result = bop.analyze(
            reserves=_reserves,
            oil_production_mbd=_oil_prod,
            oil_price_usd=_oil_price,
            imports_monthly=_imports,
        )
        result["bop"] = {
            "current_account": bop_result.current_account.to_dict(),
            "reserves": bop_result.reserves.to_dict(),
            "oil_cycle": bop_result.oil_cycle.to_dict(),
            "interpretation": bop_result.interpretation,
        }
    except Exception as exc:
        logger.warning("Balanza de pagos no disponible: %s", exc)

    # ── Deuda Pública ──
    try:
        from src.analyzers.public_debt import PublicDebtAnalyzer
        debt_analyzer = PublicDebtAnalyzer()
        debt_result = debt_analyzer.analyze(
            total_debt_usd=_debt,
            gdp_usd=_gdp,
            external_debt_usd=_debt * 0.75,
            fiscal_deficit_pct=_deficit,
            oil_revenues_usd=_oil_rev,
            oil_price=_oil_price,
            short_term_debt=_debt * 0.25,
            medium_term_debt=_debt * 0.42,
            long_term_debt=_debt * 0.33,
            pdvsa_debt=40e9,
        )
        result["debt"] = {
            "debt_gdp_ratio": debt_result.debt_gdp_ratio,
            "sustainability": debt_result.sustainability,
            "structure": debt_result.structure.to_dict(),
            "maturity": debt_result.maturity.to_dict(),
            "stress_scenarios": [
                {"name": sc.name, "projected_debt_gdp": sc.projected_debt_gdp,
                 "sustainability": sc.sustainability}
                for sc in debt_result.stress_scenarios
            ],
            "interpretation": debt_result.interpretation,
        }
    except Exception as exc:
        logger.warning("Deuda pública no disponible: %s", exc)

    # ── Pronóstico Integral ──
    try:
        from src.analyzers.integrated_forecast import IntegratedForecaster
        import pandas as pd
        forecaster = IntegratedForecaster()
        forecast_result = forecaster.scenario_analysis(
            macro_data=pd.DataFrame(),
            base_oil=_oil_price,
            base_inflation=_inflation,
            base_gdp=3.0,  # Crecimiento PIB estimado
            base_spread=_brecha,
            base_exchange=_brecha + 100 if _brecha > 0 else 500,  # Proxy TC
        )
        result["forecast"] = {
            "optimistic": {
                "inflation_forecast": forecast_result.optimistic_scenario.inflation_forecast,
                "exchange_rate_forecast": forecast_result.optimistic_scenario.exchange_rate_forecast,
            },
            "central": {
                "inflation_forecast": forecast_result.central_scenario.inflation_forecast,
                "exchange_rate_forecast": forecast_result.central_scenario.exchange_rate_forecast,
            },
            "pessimistic": {
                "inflation_forecast": forecast_result.pessimistic_scenario.inflation_forecast,
                "exchange_rate_forecast": forecast_result.pessimistic_scenario.exchange_rate_forecast,
            },
            "interpretation": forecast_result.interpretation,
        }
    except Exception as exc:
        logger.warning("Pronóstico no disponible: %s", exc)

    # ── Nowcasting ──
    try:
        from src.analyzers.nowcasting import InflationNowcaster
        import pandas as pd
        from src.db.session import get_session
        from src.db.repositories import MarketRepository
        from datetime import timedelta

        with get_session() as sess:
            repo = MarketRepository(sess)
            rates = repo.list_rates(
                since=datetime.now(timezone.utc) - timedelta(days=90),
                limit=200,
            )
            if len(rates) >= 20:
                df_now = pd.DataFrame([
                    {"date": r.date, "official_rate": float(r.rate) if r.source == "bcv" else None,
                     "parallel_rate": float(r.rate) if r.source in ("binance", "bybit") else None}
                    for r in rates
                ])
                df_now = df_now.groupby("date").mean(numeric_only=True).dropna()
                if len(df_now) >= 10:
                    nowcaster = InflationNowcaster()
                    df_now["inflation_lag1"] = df_now["parallel_rate"].pct_change().shift(1) * 100
                    df_now["inflation_lag2"] = df_now["parallel_rate"].pct_change().shift(2) * 100
                    features = nowcaster.prepare_features(df_now)
                    target = df_now["parallel_rate"].pct_change() * 100
                    r2 = nowcaster.train(features, target)
                    if r2 > 0:
                        prediction = nowcaster.predict(features)
                        result["nowcasting"] = {
                            "r_squared": r2,
                            "prediction": prediction.predicted_value,
                            "confidence_lower": prediction.confidence_lower,
                            "confidence_upper": prediction.confidence_upper,
                            "features": prediction.features_used,
                        }
    except Exception as exc:
        logger.debug("Nowcasting no disponible para informe: %s", exc)

    # ── Comparativa Regional ──
    try:
        from src.analyzers.regional import RegionalAnalyzer
        regional = RegionalAnalyzer()
        regional_result = regional.full_comparison()
        if regional_result:
            result["regional"] = regional_result
    except Exception as exc:
        logger.debug("Comparativa regional no disponible: %s", exc)

    # ── Outlook Petrolero ──
    try:
        import csv
        from pathlib import Path
        csv_path = Path(__file__).resolve().parent.parent.parent.parent / "data" / "cvs.xls" / "Datos hist\u00f3ricos Petr\u00f3leo Brent.csv"
        if not csv_path.exists():
            csv_path = Path(__file__).resolve().parent.parent.parent.parent / "data" / "cvs.xls" / "Datos históricos Petróleo Brent.csv"
        trend_analysis = ""
        if csv_path.exists():
            with open(csv_path, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f, delimiter=",")
                prices = []
                for row in reader:
                    # Try multiple header encodings for the price column
                    raw = row.get("Último", "") or row.get("ltimo", "") or row.get("\u00daltimo", "")
                    if not raw:
                        # Fallback: use second column (price)
                        vals = list(row.values())
                        if len(vals) > 1:
                            raw = vals[1]
                    if raw:
                        try:
                            p = float(raw.replace(".", "").replace(",", "."))
                            if p > 0:
                                prices.append(p)
                        except ValueError:
                            pass
                if len(prices) >= 5:
                    week_avg = sum(prices[:5]) / 5
                    month_avg = sum(prices[:20]) / min(20, len(prices))
                    if week_avg > month_avg * 1.02:
                        trend = "Alcista (+{:.1f}% vs promedio mes)".format((week_avg/month_avg - 1) * 100)
                    elif week_avg < month_avg * 0.98:
                        trend = "Bajista ({:.1f}% vs promedio mes)".format((week_avg/month_avg - 1) * 100)
                    else:
                        trend = "Estable (dentro del rango del mes)"
                    trend_analysis = (
                        f"Brent promedio semanal: ${week_avg:.2f}. "
                        f"Promedio mensual: ${month_avg:.2f}. "
                        f"{trend}. "
                        f"Para Venezuela, cada $1/barril = ~${_oil_prod * 365 * 1e6 / 1e9:.1f}B/año en ingresos petroleros."
                    )
        result["oil_outlook"] = {
            "current_price": _oil_price,
            "venezuela_production_mbd": _oil_prod,
            "trend": trend if 'trend' in dir() else "",
            "analysis": trend_analysis,
        }
    except Exception as exc:
        logger.debug("Outlook petrolero no disponible: %s", exc)

    return result


def collect_snapshot(
    cadence: str = "semanal",
    session=None,
    with_fiscal: bool = True,
    with_macro: bool = True,
    with_ai: bool = True,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
) -> Dict:
    """Compila el snapshot de datos del período para el informe.

    Args:
        cadence: Una de las claves de ``CADENCES``.
        session: Sesión inyectable (tests); si es None abre una propia.
        with_fiscal: Recoge documentos fiscales en vivo.
        with_macro: Recoge indicadores macro en vivo.
        with_ai: Añade resumen ejecutivo por IA.
        since: Fecha de inicio personalizada (override de cadencia).
        until: Fecha de fin personalizada (override de cadencia).

    Returns:
        Snapshot con secciones: market, market_series, inflation, surveys,
        sentiment, articles, fiscal_docs, macro, resumen.
    """
    if cadence not in CADENCES:
        raise ValueError(f"Cadencia inválida: {cadence}. Usar {list(CADENCES)}")

    from src.analyzers.reports.weekly import _snapshot_from_session
    from src.db.session import get_session

    now = datetime.now(timezone.utc)

    if since and until:
        days = (until - since).days
        period_label = f"Del {since:%Y-%m-%d} al {until:%Y-%m-%d}"
    else:
        days = CADENCES[cadence]["days"]
        period_label = _period_label(cadence, now)

    if session is None:
        with get_session() as session:
            base = _snapshot_from_session(session, days, since=since, until=until)
    else:
        base = _snapshot_from_session(session, days, since=since, until=until)

    market_series = base.get("market") or []
    # Recoger datos macro para informe
    macro_snapshot = {}
    if with_macro:
        macro_snapshot = _collect_macro_analytics()

    snapshot = {
        "cadence": cadence,
        "period": period_label,
        "generated_at": now,
        "market": market_series,
        "market_series": _market_series(session, days),
        "inflation": base.get("inflation") or [],
        "surveys": base.get("surveys") or {},
        "sentiment": base.get("sentiment") or {},
        "articles": (base.get("articles") or [])[:TOP_ARTICLES],
        "fiscal_docs": _collect_fiscal_docs(days) if with_fiscal else [],
        "macro": _collect_macro(days) if with_macro else [],
        "sovereign_risk": macro_snapshot.get("sovereign_risk", {}),
        "bop": macro_snapshot.get("bop", {}),
        "debt": macro_snapshot.get("debt", {}),
        "forecast": macro_snapshot.get("forecast", {}),
        "nowcasting": macro_snapshot.get("nowcasting", {}),
        "regional": macro_snapshot.get("regional", {}),
        "oil_outlook": macro_snapshot.get("oil_outlook", {}),
        "bancos": _collect_bancos(),
        "ibc_index": _collect_ibc_index(session, since, until),
        "ibc_stocks": _collect_ibc_stocks(session, since, until),
        "social": _collect_social(),
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


def bancos_block(bancos: List[Dict]) -> List[str]:
    lines = ["## Cotizaciones Bancarias (Bs/USD)", ""]
    if not bancos:
        lines += ["_Sin tasas bancarias disponibles._", ""]
        return lines
    # Separar BCV oficial del resto
    bcv = [b for b in bancos if b.get("source") == "bcv"]
    others = [b for b in bancos if b.get("source") != "bcv"]
    if bcv:
        lines += [f"**BCV oficial:** {_fmt(bcv[0].get('rate'))} Bs/USD", ""]
    if others:
        lines += ["| Banco | Tasa (Bs/USD) | Fecha |",
                  "|---|---|---|"]
        for b in sorted(others, key=lambda x: x.get("rate", 0)):
            lines.append(
                f"| {b.get('source', '?')} | {_fmt(b.get('rate'))} | "
                f"{b.get('date', '—')[:10]} |"
            )
    lines.append("")
    return lines


def macro_block(points: List[Dict]) -> List[str]:
    lines = ["## Indicadores Macroeconómicos", ""]
    if not points:
        lines += ["_Sin indicadores macroeconómicos disponibles._", ""]
        return lines
    lines += ["| Fuente | Indicador | Período | Valor | Nota |",
              "|---|---|---|---|---|"]
    for p in points:
        lines.append(f"| {p.get('source', '?')} | {p.get('indicator', '')} | "
                     f"{p.get('period', '—')} | {_fmt(p.get('value'))} | "
                     f"{p.get('impact', '')} |")
    lines += ["",
              "_Última observación disponible; los datos anuales son contexto "
              "estructural, no impulsores de la semana._",
              ""]
    return lines


def sovereign_risk_block(risk_data: Dict) -> List[str]:
    """Sección de Riesgo Soberano para el informe."""
    lines = ["## 🚨 Índice de Riesgo Soberano", ""]
    if not risk_data:
        lines += ["_Sin datos de riesgo soberano._", ""]
        return lines
    score = risk_data.get("score", 0)
    level = risk_data.get("level", "desconocido")
    lines.append(f"**Score: {score:.0f}/100 — Nivel: {level.upper()}**")
    lines.append("")
    # Desglose de factores
    components = risk_data.get("components", {})
    if components:
        lines += ["| Factor | Score |",
                  "|---|---|"]
        labels = {
            "spread": "Brecha cambiaria", "volatility": "Volatilidad",
            "inflation": "Inflación", "reserves": "Reservas",
            "debt": "Deuda", "oil": "Petróleo",
            "political": "Riesgo político", "uncertainty": "Incertidumbre",
        }
        for k, v in sorted(components.items(), key=lambda x: -x[1]):
            lines.append(f"| {labels.get(k, k)} | {v:.0f}/100 |")
    lines.append("")
    interp = risk_data.get("interpretation", "")
    if interp:
        lines += [f"_{interp}_", ""]
    return lines


def bop_block(bop_data: Dict) -> List[str]:
    """Sección de Balanza de Pagos para el informe."""
    lines = ["## 💱 Balanza de Pagos", ""]
    if not bop_data:
        lines += ["_Sin datos de balanza de pagos._", ""]
        return lines
    # Reservas
    reserves = bop_data.get("reserves", {})
    months = reserves.get("months_coverage", 0)
    total = reserves.get("total_usd", 0)
    lines.append(f"**Reservas:** ${total/1e9:.1f}B — Cobertura: {months:.1f} meses de importaciones")
    lines.append("")
    # Cuenta corriente
    ca = bop_data.get("current_account", {})
    balance = ca.get("balance", 0)
    oil_rev = ca.get("oil_revenues", 0)
    imports = ca.get("imports", 0)
    lines.append(f"**Cuenta corriente:** {'Superávit' if balance >= 0 else 'Déficit'} de ${abs(balance)/1e9:.1f}B")
    lines.append(f"_Ingresos petroleros: ${oil_rev/1e9:.1f}B | Importaciones: ${imports/1e9:.1f}B_")
    lines.append("")
    # Ciclo petrolero
    oil = bop_data.get("oil_cycle", {})
    if oil.get("interpretation"):
        lines += ["### 🛢️ Ciclo Petrolero", "", f"_{oil['interpretation']}_", ""]
    interp = bop_data.get("interpretation", "")
    if interp:
        lines += [f"_{interp}_", ""]
    return lines


def debt_block(debt_data: Dict) -> List[str]:
    """Sección de Deuda Pública para el informe."""
    lines = ["## 💳 Deuda Pública", ""]
    if not debt_data:
        lines += ["_Sin datos de deuda pública._", ""]
        return lines
    debt_gdp = debt_data.get("debt_gdp_ratio")
    sustain = debt_data.get("sustainability", "desconocido")
    lines.append(f"**Deuda/PIB:** {debt_gdp:.0f}% — Sostenibilidad: {sustain.upper()}")
    lines.append("")
    # Estructura
    structure = debt_data.get("structure", {})
    ext = structure.get("external_usd", 0)
    internal = structure.get("internal_usd", 0)
    if ext or internal:
        lines += ["| Tipo | Monto |",
                  "|---|---|"]
        lines.append(f"| Externa | ${ext/1e9:.1f}B |")
        lines.append(f"| Interna | ${internal/1e9:.1f}B |")
        lines.append("")
    # Vencimientos
    maturity = debt_data.get("maturity", {})
    rollover = maturity.get("rollover_risk", "")
    if rollover:
        lines.append(f"**Riesgo de refinanciamiento:** {rollover.upper()}")
        lines.append("")
    # Escenarios de estrés
    scenarios = debt_data.get("stress_scenarios", [])
    if scenarios:
        lines += ["### 🔥 Escenarios de Estrés", "",
                  "| Escenario | Deuda/PIB Proyectada | Estado |",
                  "|---|---|---|"]
        for sc in scenarios:
            lines.append(f"| {sc.get('name', '?')} | {sc.get('projected_debt_gdp', 0):.0f}% | {sc.get('sustainability', '?').upper()} |")
        lines.append("")
    interp = debt_data.get("interpretation", "")
    if interp:
        lines += [f"_{interp}_", ""]
    return lines


def social_block(social_data: Dict) -> List[str]:
    """Sección de Redes Sociales (Reddit) para el informe."""
    lines = ["## 💬 Redes Sociales (Reddit)", ""]
    if not social_data:
        lines += ["_Sin datos de redes sociales._", ""]
        return lines
    total = social_data.get("total_posts", 0)
    avg_score = social_data.get("avg_score", 0)
    avg_comments = social_data.get("avg_comments", 0)
    sentiment_mean = social_data.get("sentiment_mean", 0)
    sentiment_dist = social_data.get("sentiment_dist", {})
    posts_per_channel = social_data.get("posts_per_channel", {})
    posts = social_data.get("posts", [])

    lines.append(f"**Total de posts:** {total} | **Score promedio:** {avg_score:.1f} | **Comentarios prom:** {avg_comments:.1f}")
    lines.append("")

    # Sentiment
    label = "Positivo" if sentiment_mean > 0.15 else "Negativo" if sentiment_mean < -0.15 else "Neutral"
    lines.append(f"**Sentimiento promedio:** {label} ({sentiment_mean:.3f})")
    if sentiment_dist:
        dist_str = ", ".join(f"{k}: {v}" for k, v in sentiment_dist.items())
        lines.append(f"_Distribución: {dist_str}_")
    lines.append("")

    # Posts per channel
    if posts_per_channel:
        lines += ["| Subreddit | Posts |", "|---|---|"]
        for ch, count in posts_per_channel.items():
            lines.append(f"| r/{ch} | {count} |")
        lines.append("")

    # Top posts
    if posts:
        lines += ["### Posts Destacados", ""]
        lines += ["| Post | Score | Comentarios | Sentimiento |",
                  "|---|---|---|---|"]
        for p in posts[:5]:
            title = (p.get("title") or "")[:60]
            score = p.get("score") or 0
            comments = p.get("num_comments") or 0
            sent = p.get("sentiment_label") or "—"
            lines.append(f"| {title} | {score} | {comments} | {sent} |")
        lines.append("")
    return lines


def nowcasting_block(nc_data: Dict) -> List[str]:
    """Sección de Nowcasting (ML) para el informe."""
    lines = ["## 📡 Nowcasting (Predicción ML)", ""]
    if not nc_data:
        lines += ["_Sin datos de nowcasting._", ""]
        return lines
    r2 = nc_data.get("r_squared", 0)
    pred = nc_data.get("prediction", 0)
    lower = nc_data.get("confidence_lower", 0)
    upper = nc_data.get("confidence_upper", 0)
    features = nc_data.get("features", [])
    lines.append(f"**Predicción inflación mensual:** {pred:.2f}% (IC 95%: [{lower:.2f}, {upper:.2f}])")
    lines.append(f"**Calidad del modelo (R²):** {r2:.3f}")
    if features:
        lines.append(f"**Variables usadas:** {', '.join(features[:8])}")
    lines.append("")
    return lines


def forecast_block(forecast_data: Dict) -> List[str]:
    """Sección de Pronóstico Integral para el informe."""
    lines = ["## 🔮 Pronóstico Integral", ""]
    if not forecast_data:
        lines += ["_Sin datos de pronóstico._", ""]
        return lines
    # Escenarios
    scenarios = [
        ("🟢 Optimista", forecast_data.get("optimistic", {})),
        ("🟡 Central", forecast_data.get("central", {})),
        ("🔴 Pesimista", forecast_data.get("pessimistic", {})),
    ]
    lines += ["| Escenario | Inflación | Tipo de Cambio |",
              "|---|---|---|"]
    for label, sc in scenarios:
        infl = sc.get("inflation_forecast", 0)
        tc = sc.get("exchange_rate_forecast", 0)
        lines.append(f"| {label} | {infl:.1f}% | {tc:.0f} Bs/USD |")
    lines.append("")
    interp = forecast_data.get("interpretation", "")
    if interp:
        lines += [f"_{interp}_", ""]
    return lines


def regional_block(regional_data: Dict) -> List[str]:
    """Sección de Comparativa Regional para el informe."""
    lines = ["## 🌎 Comparativa Regional", ""]
    if not regional_data:
        lines += ["_Sin datos de comparativa regional._", ""]
        return lines
    for indicator_name, comparison in regional_data.items():
        lines.append(f"### {indicator_name}")
        if comparison.venezuela:
            # Formato especial para PIB (USD) - mostrar en miles de millones
            val = comparison.venezuela.value
            if "PIB" in indicator_name and "USD" in indicator_name and val > 1e9:
                lines.append(f"**Venezuela:** ${val/1e9:.1f}B ({comparison.venezuela.period})")
            else:
                lines.append(f"**Venezuela:** {_fmt(val)} ({comparison.venezuela.period})")
        if comparison.latam_average is not None:
            avg = comparison.latam_average
            if "PIB" in indicator_name and "USD" in indicator_name and avg > 1e9:
                lines.append(f"**Promedio regional:** ${avg/1e9:.1f}B")
            else:
                lines.append(f"**Promedio regional:** {_fmt(avg)}")
        if comparison.interpretation:
            lines.append(f"_{comparison.interpretation}_")
        lines.append("")
        # Top 5 rankings
        if comparison.rankings:
            lines += ["| País | Valor |",
                      "|---|---|"]
            for r in comparison.rankings[:5]:
                marker = " **VEN**" if r.country_code == "VEN" else ""
                rval = r.value
                if "PIB" in indicator_name and "USD" in indicator_name and rval > 1e9:
                    lines.append(f"| {r.country_name}{marker} | ${rval/1e9:.1f}B |")
                else:
                    lines.append(f"| {r.country_name}{marker} | {_fmt(rval)} |")
            lines.append("")
    return lines


def oil_outlook_block(oil_data: Dict) -> List[str]:
    """Sección de Outlook Petrolero para el informe."""
    lines = ["## 🛢️ Outlook Petrolero", ""]
    if not oil_data:
        lines += ["_Sin datos de outlook petrolero._", ""]
        return lines
    # Precio actual
    current_price = oil_data.get("current_price", 0)
    if current_price:
        lines.append(f"**Brent Actual:** ${current_price:.2f}/bbl")
    # Producción Venezuela
    production = oil_data.get("venezuela_production_mbd", 0)
    if production:
        lines.append(f"**Producción Venezuela:** {production:.2f} mbd")
    # Tendencia
    trend = oil_data.get("trend", "")
    if trend:
        lines.append(f"**Tendencia:** {trend}")
    lines.append("")
    # Análisis
    analysis = oil_data.get("analysis", "")
    if analysis:
        lines += ["### Análisis", "", f"_{analysis}_", ""]
    return lines


def build_markdown(snapshot: Dict) -> str:
    """Construye el informe en Markdown a partir del snapshot."""
    from src.analyzers.reports.weekly import (
        articles_block,
        ibc_index_block,
        ibc_stocks_block,
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
    lines += ibc_index_block(snapshot.get("ibc_index"))
    lines += inflation_block(snapshot.get("inflation") or [])
    lines += surveys_block(snapshot.get("surveys") or {})
    lines += sentiment_block(snapshot.get("sentiment") or {})
    lines += articles_block(snapshot.get("articles") or [])
    lines += ibc_stocks_block(snapshot.get("ibc_stocks"))
    lines += bancos_block(snapshot.get("bancos") or [])
    lines += social_block(snapshot.get("social") or {})
    lines += fiscal_docs_block(snapshot.get("fiscal_docs") or [])
    lines += macro_block(snapshot.get("macro") or [])
    lines += sovereign_risk_block(snapshot.get("sovereign_risk") or {})
    lines += bop_block(snapshot.get("bop") or {})
    lines += debt_block(snapshot.get("debt") or {})
    lines += forecast_block(snapshot.get("forecast") or {})
    lines += nowcasting_block(snapshot.get("nowcasting") or {})
    lines += oil_outlook_block(snapshot.get("oil_outlook") or {})
    lines += regional_block(snapshot.get("regional") or {})
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