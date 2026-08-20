# Economía Venezuela - Herramienta de Monitoreo y Análisis

![Venezuela Economy Tracker](https://img.shields.io/badge/Status-En%20Desarrollo-yellow) ![Python](https://img.shields.io/badge/Language-Python-blue) ![AI Powered](https://img.shields.io/badge/AI-Cadena%20LLM%20con%20fallback-purple) ![Econometrics](https://img.shields.io/badge/Econometrics-Statsmodels-green) ![Tests](https://img.shields.io/badge/Tests-299%20passing-brightgreen)

## 📋 Visión General

Herramienta inteligente de monitoreo y análisis de la economía venezolana que integra múltiples fuentes de datos, análisis econométrico avanzado e inteligencia artificial para proporcionar una visión integral del panorama económico del país.

### 🎯 Objetivo

Crear un sistema automatizado que:
- Recopile datos económicos en tiempo real de múltiples fuentes
- Analice tendencias macro y microeconómicas con modelos econométricos
- Genere pronósticos con SARIMA, VECM y GARCH
- Evalúe el sentimiento público sobre la economía
- Proporcione dashboards interactivos para la visualización de datos
- Genere informes automatizados con IA: semanal en Markdown y periódicos (diario → anual) en PDF

## 🏗️ Arquitectura del Sistema

El sistema se compone de 5 capas principales:

```
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE VISUALIZACIÓN                     │
│              Dashboards / Informes / Alertas                 │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │
┌─────────────────────────────────────────────────────────────┐
│              CAPA DE ANÁLISIS (IA + ECONOMETRÍA)            │
│   Cadena LLMs + NLP + ML + SARIMA + VECM + GARCH           │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │
┌─────────────────────────────────────────────────────────────┐
│                  CAPA DE PROCESAMIENTO                       │
│          Limpieza / Normalización / Almacenamiento          │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │
┌─────────────────────────────────────────────────────────────┐
│                   CAPA DE RECOLECCIÓN                        │
│       APIs / Web Scraping / RSS / Redes Sociales            │
└─────────────────────────────────────────────────────────────┘
```

## 📊 Módulo Econométrico

Análisis econométrico formal para pronóstico y alerta temprana:

| Modelo | Uso | Módulo |
|--------|-----|--------|
| **ADF/KPSS** | Pruebas de estacionariedad | `stationarity.py` |
| **SARIMA** | Pronóstico de inflación con estacionalidad | `forecasting.py` |
| **VECM** | Relación dólar oficial vs paralelo | `causality.py` |
| **Granger** | Causalidad entre series | `causality.py` |
| **GARCH** | Volatilidad y riesgo cambiario | `volatility.py` |
| **Newey-West** | Regresión con errores robustos | `regression.py` |
| **Diagnósticos** | Validación de modelos | `diagnostics.py` |

### Ejemplo de Uso

```python
from src.analyzers.econometric import (
    InflationForecaster,
    GARCHVolatilityAnalyzer,
    VECMAnalyzer
)

# Pronóstico de inflación con SARIMA
forecaster = InflationForecaster()
result = forecaster.forecast_inflation(inflation_series, periods=6)

# Índice de Nerviosismo Monetario
analyzer = GARCHVolatilityAnalyzer()
risk = analyzer.analyze_dollar_volatility(dollar_parallel)

# Relación oficial-paralelo con VECM
vecm = VECMAnalyzer()
vecm_result = vecm.fit_vecm(official_rate, parallel_rate)
```

## 📊 Fuentes de Datos

### 📈 Datos Financieros y de Cambio
| Fuente | Tipo | Frecuencia | Datos |
|--------|------|------------|-------|
| BCV (Banco Central de Venezuela) | API comunitaria (dolarapi.com) | Diaria | Tasa de cambio oficial, IPC |
| OVF (Observatorio Venezolano de Finanzas) | Web scraping | Mensual | Inflación independiente |
| Binance P2P | API P2P | Tiempo real | Precio USDT/VES mercado paralelo |
| Bybit P2P | API P2P | Tiempo real | Precio USDT/VES alternativo (brecha) |
| BCV Bancos (pyDolarVenezuela) | Librería Python | Tiempo real | Tasas de 12 bancos + BCV oficial |
| OPEP | API | Mensual | Producción petrolera |

### 📊 Índice Bursátil Caracas (IBC)
| Fuente | Tipo | Frecuencia | Datos |
|--------|------|------------|-------|
| Investing.com | Web scraping | Diaria (backfill) | Índice IBC + 8 componentes (BPV, MPA, CRMa, TDVd, MVZb, MVZa, ENV, FVIb) |

> **Nota:** Yahoo Finance NO tiene las acciones del IBC. Se usa Investing.com para componentes del índice.

### 📊 Tickers Venezolanos Relevantes
| Fuente | Tipo | Frecuencia | Datos |
|--------|------|------------|-------|
| Yahoo Finance | API | Diaria (backfill) | CCC, BAM, BIV, BRO, DIA, EDC, etc. (acciones fuera del IBC) |

> **Nota:** Estos tickers son empresas venezolanas que cotizan en Yahoo Finance pero NO son componentes del IBC.

### 🏛️ Fuentes Fiscales y Oficiales
| Fuente | Tipo | Frecuencia | Datos |
|--------|------|------------|-------|
| SENIAT | Web scraping | Periódica | Recaudación tributaria |
| MPPEF | Web scraping | Mensual | Ejecución presupuestaria |
| ONAPRE | Web + PDF | Mensual | Presupuesto y ejecución |
| CGR (Contraloría General) | Web scraping | Trimestral | Informes de gestión |
| Gaceta Oficial | API + HTML | Diaria | Índice + PDFs de gacetas |
| AN (Asamblea Nacional) | Web scraping | Periódica | Leyes y actos legislativos |
| INE | Web scraping | Periódica | Empleo, demografía |
| PDVSA | Web scraping | Periódica | Cesta venezolana, documentos |
| FMI (IFS/SDMX) | API REST | Mensual | PIB, inflación, indicadores |
| CEPAL | API (CEPALSTAT) | Anual | PIB, crecimiento |
| UNSCEB | CSV | Anual | Gasto del sistema ONU en Venezuela |
| Banco Mundial | API REST | Anual | PIB, indicadores de desarrollo |

### 📰 Noticias y Sentimiento
| Fuente | Tipo | Frecuencia | Datos |
|--------|------|------------|-------|
| Reddit r/vzla | API OAuth2 | Diaria | Sentimiento ciudadano |
| RSS (Diario Las Américas, Efecto Cocuyo, El Tiempo, Primicia) | RSS | Diaria | Noticias económicas |

### 📋 Encuestas Ciudadanas y Comerciantes

Datos primarios de percepción económica vía **Google Forms** que fortalecen el análisis
microeconómico y se contrastan con los datos oficiales.

| Fuente | Tipo | Frecuencia | Datos | Estado |
|--------|------|------------|-------|--------|
| Formulario Persona Común | Google Forms → Sheets | Continua (ingesta horaria) | Percepción de inflación, poder adquisitivo, gasto, ahorro, empleo | 🟡 Formulario pendiente de crear |
| Formulario Comerciante | Google Forms → Sheets | Continua (ingesta horaria) | Clima de negocios, precios, demanda, métodos de pago, costos | 🟡 Formulario pendiente de crear |

*Código de ingesta completo. Solo faltan los pasos manuales: crear los 2 formularios
Google Forms y el service account, y configurar los IDs en `.env`.*

*Más tipos de encuesta planificados: empresa, remesas.*

## 🔧 Stack Tecnológico

### Core
- **Lenguaje Principal**: Python 3.10+
- **Motor de Análisis IA**: Cadena de 8+ LLMs con fallback (LLM1..LLM8 configurable)
- **Base de Datos**: PostgreSQL (Railway)
- **Cache**: Redis (opcional)

### Econometrics
- `statsmodels` - Modelos econométricos (ARIMA, SARIMA, VECM)
- `arch` - Modelos de volatilidad (GARCH, EGARCH)
- `scipy` - Estadística avanzada
- `linearmodels` - Modelos de panel y regresión robusta

### Análisis
- `pandas` / `numpy` - Procesamiento de datos
- `scikit-learn` - ML para predicciones
- `transformers` - NLP para sentimiento
- `spacy` - Procesamiento de lenguaje natural

### Visualización
- `Streamlit` - Dashboard principal
- `Plotly` - Gráficos interactivos
- `matplotlib` - Gráficos para informes PDF

### Automatización
- `Docker` - Contenedores
- `APScheduler` - Tareas programadas (recolección + informes)

## 🚀 Instalación Rápida

```bash
# Clonar el repositorio
git clone https://github.com/betobeto00/economia-venezuela.git
cd economia-venezuela

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus API keys

# Ejecutar el scheduler (recolección + informes automáticos)
python main.py

# O solo el dashboard
streamlit run src/dashboard/app.py
```

### 📜 Scripts Disponibles

| Script | Función | Ejemplo |
|--------|---------|--------|
| `collect_market.py` | Recolecta datos de mercado (BCV, Binance, Bybit, bancos) → DB | `python -m src.scripts.collect_market` |
| `collect_news.py` | Recolecta noticias RSS + Reddit y analiza sentimiento | `python -m src.scripts.collect_news` |
| `collect_surveys.py` | Ingesta de encuestas Google Forms → Sheets | `python -m src.scripts.collect_surveys` |
| `backfill_ibc.py` | Backfill histórico del IBC + tickers venezolanos | `python -m src.scripts.backfill_ibc --since 2026-08-01 --until 2026-08-14` |
| `backfill_rates.py` | Backfill histórico de tasas (dataset usdt.com.ve, CC-BY-4.0) | `python -m src.scripts.backfill_rates` |
| `generate_report.py` | Genera informes económicos en MD y PDF | `python -m src.scripts.generate_report --cadence semanal --format md,pdf` |

## 📁 Estructura del Proyecto

```
economia-venezuela/
├── README.md                    # Este archivo
├── Arquitectura.md              # Documentación de arquitectura
├── knowledge.md                 # Base de conocimiento
├── roadmap.md                   # Hoja de ruta del proyecto
├── requirements.txt             # Dependencias Python
├── docker-compose.yml           # Contenedores Docker
├── .env.example                 # Variables de entorno ejemplo
├── main.py                      # Bootstrap: init DB + scheduler
├── src/
│   ├── __init__.py
│   ├── config.py               # Configuración (pydantic-settings, .env)
│   ├── collectors/             # Módulos de recolección (24 collectors)
│   │   ├── http.py             #   Cliente HTTP compartido (GET/POST, retries)
│   │   ├── errors.py           #   Excepciones del dominio
│   │   ├── market/             #   bcv, ovf, bvc, binance, ibc_components, ibc_stocks, dolar_paralelo
│   │   ├── fiscal/             #   onapre, cgr, seniat, mppef, gaceta, an + documents.py
│   │   ├── official/           #   ine
│   │   ├── international/      #   worldbank, opec, imf, cepal, pdvsa, unsceb
│   │   ├── news/               #   rss
│   │   ├── social/             #   reddit
│   │   └── surveys/            #   Encuestas Google (Forms→Sheets): survey_collector, form_registry, utils
│   ├── models/                 # Modelos Pydantic
│   │   ├── market.py           #   ExchangeRate, InflationPoint, GDPPoint, BudgetExecution
│   │   ├── survey.py           #   Survey, SurveyResponse
│   │   └── news.py             #   NewsArticle, SocialPost
│   ├── db/                     # Persistencia
│   │   ├── session.py          #   Conexión (psycopg2)
│   │   ├── models.py           #   ORMs: SurveyORM, ExchangeRateORM, IBCIndexORM, IBCComponentORM,
│   │   │                       #          VenezuelanTickerORM, NewsArticleORM, SocialPostORM,
│   │   │                       #          SentimentScoreORM, InflationPointORM
│   │   └── repositories.py     #   SurveyRepository, MarketRepository, IBCIndexRepository,
│   │                           #   VenezuelanTickerRepository
│   ├── analyzers/              # Análisis e IA
│   │   ├── llm.py              # Cadena de LLMs con fallback (LLM1..LLM8)
│   │   ├── sentiment.py        # Análisis de sentimiento (léxico español)
│   │   ├── relevance.py        # Filtro de relevancia económica (léxico fuerte/débil)
│   │   ├── market_integration.py # Collectors → ARIMA/SARIMA
│   │   ├── surveys/            # Encuestas: KPIs y contraste
│   │   │   ├── indicators.py   #   KPIs por segmento
│   │   │   ├── contrast.py     #   Percepción vs datos oficiales
│   │   │   └── report.py       #   Resumen ejecutivo con IA
│   │   ├── reports/            # Informes: semanal (IA) + periódicos MD/PDF
│   │   │   ├── weekly.py       #   Informe semanal con resumen IA
│   │   │   ├── periodic.py     #   Snapshot por cadencia (diario→anual) + Markdown
│   │   │   └── pdf_report.py   #   Render PDF (ReportLab + matplotlib)
│   │   └── econometric/        # Módulo econométrico
│   │       ├── stationarity.py #   ADF, KPSS
│   │       ├── forecasting.py  #   ARIMA, SARIMA
│   │       ├── causality.py    #   Granger, VECM
│   │       ├── volatility.py   #   GARCH
│   │       ├── diagnostics.py  #   Residuos
│   │       └── regression.py   #   Newey-West OLS
│   ├── dashboard/              # Visualización (Streamlit)
│   │   ├── app.py              #   Dashboard principal (3 tabs: Inicio, Noticias, Encuestas)
│   │   ├── theme.py            #   Tema visual
│   │   ├── market_data.py      #   Métricas de mercado desde DB
│   │   ├── surveys_data.py     #   Métricas de encuestas desde DB
│   │   ├── news_data.py        #   Datos de noticias y sentimiento
│   │   └── components/         #   Componentes
│   │       ├── survey_section.py   # Sección de encuestas
│   │       └── news_section.py     # Sección de noticias
│   ├── scripts/                # CLIs
│   │   ├── collect_market.py   #   Recolección de mercado → DB
│   │   ├── collect_news.py     #   Noticias RSS + Reddit + sentimiento
│   │   ├── collect_surveys.py  #   Ingesta de encuestas
│   │   ├── backfill_rates.py   #   Backfill histórico (usdt.com.ve CSV)
│   │   ├── backfill_ibc.py     #   Backfill IBC + tickers venezolanos → DB
│   │   └── generate_report.py  #   Informes periódicos MD/PDF (--cadence, --since/--until)
│   ├── scheduler/              # Programación
│   │   └── jobs.py             #   Jobs APScheduler (mercado, encuestas, noticias, informes)
│   ├── alerts/                 # Sistema de alertas
│   ├── metrics/                # Métricas del sistema
│   └── security/               # Seguridad
├── data/
│   ├── raw/                    # Datos crudos
│   ├── processed/              # Datos procesados
│   └── reports/                # Informes generados
├── tests/                      # 299 tests (pytest)
└── docs/                       # Documentación
    ├── fuentes_fiscales.md     # Fuentes fiscales gubernamentales
    └── review.md               # Revisión técnica del proyecto
```

## 📅 Frecuencia de Actualización

| Componente | Frecuencia | Config |
|------------|------------|--------|
| Tasa de cambio (BCV + Binance P2P + Bybit + Bancos) | Cada 30 min | `MARKET_COLLECT_INTERVAL_MINUTES` |
| IBC + Tickers (backfill) | Diaria | `python -m src.scripts.backfill_ibc` |
| Encuestas (Google Forms → Sheets) | Cada 60 min | `SURVEY_COLLECT_INTERVAL_MINUTES` |
| Noticias RSS + sentimiento | Cada 6 h | `NEWS_COLLECT_INTERVAL_HOURS` |
| Informe semanal (con IA) | Cada domingo 08:00 | `WEEKLY_REPORT_DAY`/`WEEKLY_REPORT_HOUR` |
| Informe diario | 07:00 Lunes-Viernes | cron `report_diario` |
| Informe semanal (PDF) | Lunes 08:00 | cron `report_semanal` |
| Informe mensual | Día 1, 09:00 | cron `report_mensual` |
| Informe trimestral | 1° de ene/abr/jul/oct 10:00 | cron `report_trimestral` |
| Informe semestral | 1° de ene/jul 11:00 | cron `report_semestral` |
| Informe anual | 1° de enero 12:00 | cron `report_anual` |

> El scheduler (APScheduler en `main.py`) registra 11 jobs: mercado, encuestas, noticias, informe semanal e informes periódicos (6 cadencias: diario a anual).

## 📈 Métricas del Dashboard

### Tab "🏠 Inicio"
| Métrica | Descripción | Fuente | Estado |
|---------|-------------|--------|--------|
| **Dólar Oficial** | Tasa BCV | dolarapi.com | ✅ En vivo |
| **Dólar Paralelo** | Precio USDT/VES Binance P2P | Binance | ✅ En vivo |
| **Dólar Bybit** | Precio USDT/VES Bybit P2P | Bybit | ✅ En vivo |
| **Inflación Mensual** | IPC (BCV, fallback OVF) | BCV/OVF | ✅ En vivo |
| **Brecha Cambiaria** | Diferencia oficial-paralelo % | Cálculo | ✅ En vivo |
| **Gráfico 6 meses** | Evolución BCV + Binance + Bybit | DB | ✅ Plotly |

### Tab "📰 Noticias"
| Métrica | Descripción | Fuente | Estado |
|---------|-------------|--------|--------|
| **Tono general** | Sentimiento promedio (-1 a +1) | Léxico español | ✅ En vivo |
| **Positivas/Neutrales/Negativas** | Distribución de sentimiento | RSS + Reddit | ✅ En vivo |
| **Últimos titulares** | Artículos recientes con fuente y fecha | RSS | ✅ En vivo |

### Tab "📋 Encuestas"
| Métrica | Descripción | Fuente | Estado |
|---------|-------------|--------|--------|
| **KPIs por segmento** | Percepción, ahorro, medios de pago | Google Forms | ✅ En vivo |
| **Serie temporal** | Evolución de KPIs por período | DB | ✅ Plotly |
| **Contraste percepción vs realidad** | Brecha percepción ciudadana vs IPC oficial | Cálculo | ✅ En vivo |
| **Informe ejecutivo** | Resumen con IA por segmento | Cadena LLMs | ✅ En vivo |

### Otros
| Métrica | Descripción | Fuente | Estado |
|---------|-------------|--------|--------|
| **Índice IBC** | Bolsa de Valores de Caracas | Investing.com | ✅ Backfill |
| **Componentes IBC** | Top gainers/losers del índice | Investing.com | ✅ Backfill |
| **Acciones venezolanas** | Tickers relevantes fuera del IBC | Yahoo Finance | ✅ Backfill |
| **Informe Semanal** | Markdown + resumen IA (cadena de LLMs con fallback) | Todo el sistema | ✅ Semanal |
| **Informes Periódicos PDF** | Diario→anual: carátula, resumen IA, gráficos, tablas | Todo el sistema | ✅ 6 cadencias |
| **Informes Rango Personalizado** | Generar informes para fechas específicas (--since/--until) | CLI | ✅ |
| **Pronóstico Inflación** | SARIMA | Modelo econométrico | ⏳ |

## 🗄️ Base de Datos

El proyecto usa **PostgreSQL** con 9 tablas principales. El esquema completo está documentado en [Arquitectura.md](Arquitectura.md#esquemas-sql-orms-sqlalchemy).

| Tabla | Descripción |
|-------|-------------|
| `exchange_rates` | Tasas de cambio por fuente y moneda |
| `inflation_points` | Inflación mensual por emisor y período |
| `news_articles` | Artículos de noticias (RSS) |
| `social_posts` | Publicaciones sociales (Reddit) |
| `sentiment_scores` | Puntajes de sentimiento por ítem |
| `ibc_index` | Índice bursátil Caracas (IBC) |
| `ibc_components` | Componentes del IBC (acciones) |
| `venezuelan_tickers` | Tickers venezolanos relevantes |
| `surveys` | Formularios de encuesta |
| `survey_responses` | Respuestas de encuestas (JSONB flexible) |

## 🤝 Contribuciones

Lee [CONTRIBUTING.md](CONTRIBUTING.md) para instrucciones detalladas. En resumen:

1. Abre un issue para discutir el cambio
2. Crea una rama desde `master`
3. Implementa con tests
4. Ejecuta `pytest` y asegura que todo pasa
5. Abre un Pull Request

## 📄 Licencia

Este proyecto se distribuye bajo la Licencia MIT.

## ⚠️ Disclaimer

Esta herramienta es solo para fines informativos y educativos. Los datos y análisis generados no deben tomarse como asesoría financiera o económica profesional. Siempre consulta a un experto antes de tomar decisiones basadas en estos datos.

## 📞 Contacto

- **GitHub**: [@betobeto00](https://github.com/betobeto00)
- **Repositorio**: [economia-venezuela](https://github.com/betobeto00/economia-venezuela)

---

**Hecho con ❤️ para la comunidad venezolana**
