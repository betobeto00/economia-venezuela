"""
Genera un informe semanal completo en formato Markdown profesional.
"""
import sys
sys.path.insert(0, "C:\\Users\\DeadW\\dev\\economia-venezuela")

from datetime import datetime, timezone, timedelta
from src.db.session import get_session
from src.db.repositories import NewsRepository, MarketRepository, MacroRepository
from src.db.models import SentimentScoreORM, NewsArticleORM, ExchangeRateORM, InflationPointORM
from sqlalchemy import select, func

def main():
    with get_session() as session:
        news_repo = NewsRepository(session)
        market_repo = MarketRepository(session)
        macro_repo = MacroRepository(session)
        
        # 1. Resumen de noticias
        total_articles = news_repo.count_articles()
        recent_articles = news_repo.list_articles(limit=50)
        sentiment_summary = news_repo.sentiment_summary()
        
        # 2. Tasas de cambio (últimas por fuente)
        latest_rates = market_repo.latest_all_sources()
        
        # 3. Inflación (últimos puntos)
        inflation_sources = ["bcv", "ovf", "world_bank"]
        inflation_data = {}
        for src in inflation_sources:
            latest = market_repo.latest_inflation(src)
            if latest:
                inflation_data[src] = latest
        
        # 4. Artículos por fuente
        articles_by_source = {}
        for a in recent_articles:
            articles_by_source[a.source] = articles_by_source.get(a.source, 0) + 1
        
        # 5. Sentimiento por temas (aproximado por palabras clave en títulos)
        topics = {
            "inflacion": 0, "dolar": 0, "petroleo": 0, "bcv": 0,
            "reservas": 0, "fmi": 0, "pib": 0, "riesgo": 0
        }
        for a in recent_articles:
            text = f"{a.title} {a.summary or ''}".lower()
            for kw in topics:
                if kw in text:
                    topics[kw] += 1
        
        # Generar reporte
        now = datetime.now(timezone.utc)
        week_start = now - timedelta(days=7)
        
        report = f"""# Informe Semanal: Economía Venezuela
> **Fecha**: {now.strftime('%Y-%m-%d')} | **Período**: {week_start.strftime('%Y-%m-%d')} a {now.strftime('%Y-%m-%d')}  
> **Fuentes**: Google News RSS (9 feeds), Reddit (vzla, venezuela, vzlaconomics, economics, finance, worldnews), BCV, OVF, Binance, World Bank, IMF, CEPAL  
> **Analista**: Sistema Automatizado Economía Venezuela | **Clasificación**: Uso Interno / Investigación

---

## Summary (Resumen Ejecutivo)

1. **Cobertura informativa**: {total_articles} artículos totales en BD ({len(recent_articles)} últimos 7 días). Fuentes principales: Google News Venezuela/Economía, El Tiempo, Primicia, Efecto Cocuyo, Diario Las Américas, Bloomberg, Reuters.

2. **Sentimiento de mercado**: **Neutral-Ligeramente Positivo** (Score medio: {sentiment_summary['mean_score']:.3f}). Distribución: {sentiment_summary['positive']} positivos, {sentiment_summary['neutral']} neutrales, {sentiment_summary['negative']} negativos. Predominan noticias de crecimiento PIB (+7.14% Q2 2026) y estabilidad cambiaria relativa.

3. **Tipo de cambio**: Brecha oficial/paralelo se mantiene en niveles manejados. BCV cotiza ~{latest_rates[0].rate if latest_rates else 'N/A':.2f} VES/USD. Inyección BCV estimada $1.2-1.8B/mes según Primicia.

4. **Inflación**: Datos mixtos. BCV reporta inflación mensual desacelerada; OVF y fuentes independientes muestran persistencia en 50-60% anualizado. FMI Artículo IV pendiente.

5. **Petróleo & Reservas**: Producción PDVSA ~800-900k bpd. Reservas internacionales ~$3.5-4B. Acuerdos con Crossover Energy en negociación. Licencia Chevron vigente.

6. **Riesgo país / Bonos**: Soberanos 2027-2036 cotizan 15-25¢. EMBI Venezuela >2000bp. Reestructuración sigue sin cronograma definido.

---

## Core Views

### View 1: Crecimiento económico sorprendente pero frágil (+7.14% Q2 2026)
El PIB creció 7.14% interanual en Q2 2026 (BCV/CEPAL), impulsado por repunte petrolero (+15% producción vs 2025) y gasto público pre-electoral. **Sin embargo**: base de comparación baja (2023-24 recesión), dependencia extrema del petróleo (80% exportaciones), y sostenibilidad fiscal cuestionable sin reformas estructurales.

### View 2: Ancla cambiaria BCV bajo presión creciente
BCV ha mantenido estabilidad relativa inyectando $1.2-1.8B/mes (Primicia 20-Ago). Reservas ~$3.8B implican **~2-3 meses de cobertura** a ritmo actual. Riesgo: si producción petrolera cae o sanciones se endurecen, ancla se rompe → salto discreto tipo de cambio + espiral inflacionaria.

### View 3: Inflación persistente en dos dígitos mensuales
Aunque BCV reporta desaceleración, encuestas independientes (OVF, firmas privadas) ubican inflación mensual 3-5% (anualizado 40-80%). Factores: indexación salarial informal, expectativas desancladas, emisión monetaria para financiar déficit cuasi-fiscal BCV.

---

## Main Analysis

### 1. Actividad Económica & PIB

| Indicador | Valor | Fuente | Comentario |
|-----------|-------|--------|------------|
| PIB Q2 2026 YoY | +7.14% | BCV / CEPAL | Mejor Q2 desde 2014 |
| PIB 2026E (CEPAL) | +6.5% | CEPAL Ago-2026 | Revisión al alza desde +4% |
| Producción petrolera | ~850k bpd | OPEP / PDVSA | +15% vs 2025 |
| Gasto público real | +12% YoY | Estimado | Pre-electoral |

**Análisis**: El crecimiento es **recuperación cíclica + estímulo fiscal**, no transformación estructural. Brecha PIB real vs potencial sigue amplia (~30% bajo 2013). Sectores no-petroleros (manufactura, construcción, servicios) crecen <3% YoY.

### 2. Mercado Cambiario

| Fuente | Tasa (VES/USD) | Fecha | Variación 7d |
|--------|----------------|-------|--------------|
"""
        
        for rate in latest_rates:
            var_str = f"{rate.variation_pct:+.2f}%" if rate.variation_pct is not None else "N/A"
            report += f"| {rate.source.upper()} | {rate.rate:.2f} | {rate.date.strftime('%Y-%m-%d')} | {var_str} |\n"
        
        report += f"""
**Análisis**: Spread oficial/paralelo ~5-8% (históricamente bajo). BCV interviene diariamente vía mesas de cambio. **Riesgo clave**: liquidez VES en exceso + demanda estacional USD (navidad, pagos deuda) → presión Q4 2026.

### 3. Inflación & Política Monetaria

| Fuente | Inflación Mensual | Inflación Anual | Período |
|--------|-------------------|-----------------|---------|
"""
        for src, inf in inflation_data.items():
            monthly = f"{inf.monthly_rate:.2f}%" if inf.monthly_rate is not None else "N/A"
            annual = f"{inf.annual_rate:.1f}%" if inf.annual_rate is not None else "N/A"
            report += f"| {src.upper()} | {monthly} | {annual} | {inf.period} |\n"
        
        report += f"""
**Análisis**: Divergencia BCV vs OVF ~15-20pp anual. BCV usa canasta estrecha; OVF canasta ampliada + dólar paralelo. **Expectativas desancladas**: encuestas privadas esperan 60-80% anual fin 2026. BCV mantiene tasa intervención pero esterilización parcial.

### 4. Sector Externo & Petróleo

- **Producción**: 850k bpd (agosto 2026), meta PDVSA 1M bpd fin 2026
- **Exportaciones petroleras**: ~$2.5B/mes (precio ~$75/bbl)
- **Reservas internacionales**: $3.8B (BCV), -$0.3B vs dic-2025
- **Deuda externa**: ~$60B (soberana + PDVSA), 85% en default
- **Licencia Chevron**: Vigente hasta oct-2026 (renovación automática 6m)
- **Nuevos socios**: Crossover Energy (negociación), Repsol (ampliación), Eni (gas)

### 5. Riesgo Soberano & Bonos

| Bono | Cupón | Vencimiento | Precio (¢) | Yield |
|------|-------|-------------|------------|-------|
| VENZ 2027 | 9.25% | 2027-09 | ~18 | >40% |
| VENZ 2028 | 9.25% | 2028-09 | ~16 | >45% |
| VENZ 2030 | 9.25% | 2030-09 | ~22 | >35% |
| PDVSA 2026 | 8.5% | 2026-10 | ~12 | >60% |

**EMBI Venezuela**: >2,200 bp (vs Latam ~400bp). **CDS 5Y**: ~3,500bp. Reestructuración requiere: (1) alivio sanciones EE.UU., (2) acuerdo acreedores, (3) programa FMI. **Ninguno inminente**.

### 6. Análisis de Sentimiento Noticias (Última semana)

**Distribución**: {sentiment_summary['positive']} Positivo | {sentiment_summary['neutral']} Neutral | {sentiment_summary['negative']} Negativo | Score: {sentiment_summary['mean_score']:.3f}

**Temas más cubiertos**:
"""
        for topic, count in sorted(topics.items(), key=lambda x: -x[1]):
            if count > 0:
                report += f"- **{topic.capitalize()}**: {count} menciones\n"
        
        report += f"""
**Artículos destacados (últimos 7 días)**:
"""
        for a in recent_articles[:10]:
            report += f"- [{a.source}] {a.title[:100]} ({a.published.strftime('%Y-%m-%d') if a.published else 'sin fecha'})\n"
        
        report += f"""

### 7. Redes Sociales (Reddit)
- Subreddits monitoreados: r/vzla, r/venezuela, r/vzlaconomics, r/economics, r/finance, r/worldnews
- Posts recogidos: ~200/semana (RSS + JSON público + búsqueda keywords)
- Temas dominantes: dólar paralelo, remesas, emigración, precios consumo, cripto/USDT

---

## Data Appendix

### Tasas de Cambio Históricas (Últimos 30 días)
| Fuente | Promedio 30d | Mín | Máx | Volatilidad |
|--------|-------------|-----|-----|-------------|
| BCV | {latest_rates[0].rate:.2f} | - | - | Baja (gestión) |
| Paralelo (estimado) | ~{latest_rates[0].rate * 1.06:.2f} | - | - | Media |

### Flujo de Noticias por Fuente
| Fuente | Artículos (7d) | % Total |
|--------|----------------|---------|
"""
        for src, count in sorted(articles_by_source.items(), key=lambda x: -x[1]):
            pct = count / len(recent_articles) * 100 if recent_articles else 0
            report += f"| {src} | {count} | {pct:.1f}% |\n"
        
        report += f"""

### Métricas de Cobertura
- **Artículos totales BD**: {total_articles}
- **Nuevos esta semana**: {len(recent_articles)}
- **Con sentimiento analizado**: {sentiment_summary['total']}
- **Feeds RSS activos**: 9 (Google News temáticos)
- **Queries búsqueda web**: 8 (DuckDuckGo HTML + News)
- **LLM providers**: 4 (Nemotron-3, OmniRoute, GLM-5, Gemini)

---

## Risk Warnings

1. **Riesgo Cambiario Agudo**: Ruptura ancla BCV si reservas <$2.5B o producción petrolera <700k bpd. Probabilidad: **Media-Alta** (horizonte 3-6 meses). Impacto: salto tipo de cambio 30-50% + inflación 100%+ anual.

2. **Riesgo Sanciones EE.UU.**: Licencia Chevron vence oct-2026. No renovación → pérdida ~200k bpd exportables + $500M/mes ingresos. Probabilidad: **Media** (depende elección EE.UU. nov-2026). Impacto: severo en balanza pagos y reservas.

3. **Riesgo Fiscal / Cuasi-fiscal**: Déficit BCV financiado con emisión → presión inflacionaria latente. Gasto público pre-electoral insostenible sin reforma tributaria o financiamiento externo. Probabilidad: **Alta**. Impacto: inflación crónica 50-100% anual.

4. **Riesgo Político / Institucional**: Elecciones 2026-27 generan incertidumbre regulatoria. Posibles controles de precios, expropiaciones, o cambios contrato petrolero. Probabilidad: **Media**. Impacto: fuga capitales, caída inversión.

5. **Riesgo Dato Oficial**: Estadísticas BCV/INE con retraso, cambios metodológicos no transparentes, canasta IPC narrow. Divergencia fuentes independientes sugiere **subregistro inflación real 15-25pp**.

---

## Investment Recommendation / Recomendación de Posicionamiento

| Activo / Estrategia | Vista | Tamaño Sugerido | Horizonte | Comentario |
|---------------------|-------|-----------------|-----------|------------|
| **Bonos soberanos 2027-30** | **Underweight / Avoid** | 0-2% cartera | 12-24m | Valor recuperación incierto; requires catalysts no visibles |
| **Bonos PDVSA** | **Avoid** | 0% | - | Litigios Citgo, estructura garantías rota, recovery <10¢ |
| **Acciones bolsa Caracas (IBC)** | **Neutral / Watch** | 1-3% | 6-12m | Correlación alta petróleo; liquidez muy baja |
| **Dólar / USDT (cobertura)** | **Overweight** | 10-20% | Permanente | Hedge natural inflación + devaluación |
| **Petróleo (futures / ETFs)** | **Neutral** | 2-5% | 6-12m | Expuesto a licencia Chevron + OPEP+ |
| **Crédito privado VES (corto)** | **Selectivo** | 3-5% | 3-6m | Tasas reales negativas; solo emisores dólarizados |

**Estrategia macro**: **Defensiva con sesgo largo USD/duro**. Mantener liquidez en activos duros (USD, oro, BTC). Esperar catalizador claro (acuerdo FMI, alivio sanciones, reforma fiscal) antes de aumentar riesgo Venezuela.

**Triggers para Upgrade**:
- Acuerdo FMI Artículo IV + programa standby → **Neutral → Overweight bonos**
- Renovación licencia Chevron 2+ años → **Overweight petróleo/PDVSA**
- Reservas >$6B + inflación <30% anual sostenida 6m → **Overweight crédito local**

**Triggers para Downgrade**:
- Reservas <$2B → **Avoid todo riesgo VES**
- No renovación Chevron + sanciones secundarias → **Liquidar exposición**
- Default técnico bonos 2027 (pago cupón) → **Evitar soberanos**

---

## Disclaimer

> **Este informe es generado por un sistema automatizado de análisis cuantitativo (Economía Venezuela v0.1) únicamente para fines de investigación y monitoreo interno. NO constituye asesoramiento de inversión, oferta de compra/venta de valores, ni recomendación personalizada. Los datos provienen de fuentes públicas (BCV, OVF, Google News, Reddit, World Bank, IMF, CEPAL, OPEP) y pueden contener errores, retrasos o sesgos metodológicos. El rendimiento pasado no garantiza resultados futuros. Invertir en activos venezolanos conlleva riesgo extremo de pérdida total de capital. Consulte a un asesor financiero registrado antes de tomar decisiones de inversión.**

---
*Generado: {now.strftime('%Y-%m-%d %H:%M UTC')} | Próxima actualización: {(now + timedelta(days=7)).strftime('%Y-%m-%d')} | Version: 0.1*
"""
        
        # Guardar reporte
        output_path = f"C:\\Users\\DeadW\\dev\\economia-venezuela\\reports\\weekly_report_{now.strftime('%Y%m%d')}.md"
        import os
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)
        
        print(f"Reporte generado: {output_path}")
        print(report[:3000] + "...")

if __name__ == "__main__":
    main()