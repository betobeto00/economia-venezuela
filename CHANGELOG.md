# Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.

El formato se basa en [Keep a Changelog](https://keepachangelog.com/es/1.1.0/),
y este proyecto adhiere al [Semantic Versioning](https://semver.org/lang/es/).

## [Unreleased]

### Changed
- Documentación completa actualizada: readme.md, Arquitectura.md, roadmap.md, knowledge.md, docs/review.md, docs/fuentes_fiscales.md
- 24 collectors documentados correctamente en todos los archivos
- 299 tests reflejados en toda la documentación
- Dashboard documentado con 3 tabs (Inicio, Noticias, Encuestas)
- Scheduler documentado con 11 jobs

### Added
- LICENSE (MIT)
- CONTRIBUTING.md
- CHANGELOG.md
- docker-compose.dev.yml

## [0.1.0] - 2026-08-19

### Added

#### Collectors (Fase A - Mercado)
- BCV Collector: tasa de cambio oficial e IPC vía dolarapi.com
- OVF Collector: inflación independiente (observatoriodefinanzas.com)
- BVC Collector: Índice bursátil Caracas (yfinance)
- Binance P2P Collector: precio USDT/VES mercado paralelo
- Bybit P2P Collector: precio USDT/VES alternativo (brecha)
- IBC Components Collector: 8 componentes del IBC (Investing.com)
- IBC Stocks Collector: tickers venezolanos relevantes (Yahoo Finance)
- Dólar Paralelo Bancos: tasas de 12 bancos + BCV (pyDolarVenezuela)

#### Collectors (Fiscales)
- ONAPRE Collector: ejecución presupuestaria (web + PDF)
- CGR Collector: informes de gestión (web scraping)
- SENIAT Collector: recaudación tributaria (web scraping)
- MPPEF Collector: ejecución presupuestaria (web scraping)
- Gaceta Oficial Collector: índice + PDFs (API + HTML)
- AN Collector: leyes y actos legislativos (web scraping)

#### Collectors (Internacionales)
- World Bank Collector: PIB, indicadores (API REST)
- IMF Collector: PIB, inflación (SDMX-JSON)
- CEPAL Collector: PIB, crecimiento (CEPALSTAT)
- UNSCEB Collector: gasto ONU por país (CSV)
- OPEP Collector: producción petrolera
- PDVSA Collector: cesta venezolana (pdvsa-adhoc.com)

#### Collectors (Otros)
- INE Collector: empleo, demografía (web scraping)
- RSS Collector: noticias (Diario Las Américas, Cocuyo, El Tiempo, Primicia)
- Reddit Collector: sentimiento ciudadano (API OAuth2)
- Survey Collector: encuestas Google Forms → Sheets (gspread)

#### Análisis
- Módulo econométrico: ADF/KPSS, SARIMA, VECM, GARCH, Newey-West, diagnósticos
- Integración collectors → econometría (market_integration.py)
- Análisis de sentimiento (léxico español)
- Filtro de relevancia económica (léxico fuerte/débil)
- Cadena de LLMs con fallback (LLM1..LLM8)
- Encuestas: KPIs por segmento, contraste percepción vs datos oficiales

#### Informes
- Informe semanal automatizado con resumen IA
- Informes periódicos (diario → anual) en Markdown y PDF
- CLI generate_report: --cadence, --since/--until, --format, --no-ai
- Render PDF con ReportLab + matplotlib

#### Dashboard (Streamlit)
- Tab Inicio: métricas de dólar oficial/paralelo/Bybit, inflación, brecha cambiaria, gráfico Plotly 6 meses
- Tab Noticias: sentimiento, distribución, últimos titulares
- Tab Encuestas: KPIs por segmento, serie temporal, contraste percepción vs realidad, informe ejecutivo

#### Persistencia
- 9 tablas ORMs: exchange_rates, inflation_points, news_articles, social_posts, sentiment_scores, ibc_index, ibc_components, venezuelan_tickers, surveys, survey_responses
- Repositorios: SurveyRepository, MarketRepository, IBCIndexRepository, VenezuelanTickerRepository

#### Scheduler (APScheduler)
- Job mercado: cada 30 min
- Job encuestas: cada 60 min
- Job noticias: cada 6 horas
- Job informe semanal: domingo 08:00
- 6 jobs informes periódicos: diario (07:00), semanal (lun 08:00), mensual (día 1 09:00), trimestral, semestral, anual

#### Scripts CLI
- collect_market.py: recolección de mercado → DB
- collect_news.py: noticias RSS + Reddit + sentimiento
- collect_surveys.py: ingesta de encuestas
- backfill_rates.py: backfill histórico (usdt.com.ve CSV)
- backfill_ibc.py: backfill IBC + tickers venezolanos
- generate_report.py: informes periódicos MD/PDF

#### Infraestructura
- Docker + Docker Compose (PostgreSQL/TimescaleDB, Redis, Prometheus, Grafana)
- 299 tests (pytest)

### Changed
- README actualizado con estructura completa del proyecto
- Arquitectura.md actualizada con diagramas de BD y componentes

### Fixed
- PDF sin código Paragraph visible
- Prompts IA en español para resumen y proyección
- Wire periodic report jobs into scheduler + resilient AN collector
