# Economía Venezuela - Herramienta de Monitoreo y Análisis

![Venezuela Economy Tracker](https://img.shields.io/badge/Status-En%20Desarrollo-yellow) ![Python](https://img.shields.io/badge/Language-Python-blue) ![AI Powered](https://img.shields.io/badge/AI-DeepSeek%20V4--Pro-purple) ![Econometrics](https://img.shields.io/badge/Econometrics-Statsmodels-green) ![Tests](https://img.shields.io/badge/Tests-299%20passing-brightgreen)

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
│   DeepSeek V4-Pro + NLP + ML + SARIMA + VECM + GARCH       │
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

## 📊 Módulo Econométrico (NUEVO)

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
| BCV (Banco Central de Venezuela) | API comunitaria | Diaria | Tasa de cambio oficial, IPC |
| OVF (Observatorio Venezolano de Finanzas) | Web | Mensual | Inflación independiente |
| Binance P2P | API | Tiempo real | Precio USDT/VES mercado paralelo |
| Bybit P2P | API + backfill histórico | Tiempo real | Precio USDT/VES alternativo (brecha) |
| OPEP | API | Mensual | Producción petrolera |

### 📊 Índice Bursátil Caracas (IBC)
| Fuente | Tipo | Frecuencia | Datos |
|--------|------|------------|-------|
| Investing.com | Web scraping | Diaria (backfill) | Índice IBC + 9 componentes (BPV, MPA, CRMa, TDVd, MVZb, MVZa, ENV, FVIb) |

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
| CGR (Contraloría General) | Web | Trimestral | Informes de gestión |
| Gaceta Oficial | Web scraping | Diaria | Índice + PDFs de gacetas |
| AN (Asamblea Nacional) | Web scraping | Periódica | Leyes y actos legislativos |
| INE | Web | Periódica | Empleo, demografía |
| PDVSA | API | Periódica | Documentos operacionales |
| FMI (IFS/SDMX) | API REST | Mensual | PIB, inflación, indicadores |
| CEPAL | API (CEPALSTAT) | Anual | PIB, crecimiento |
| UNSCEB | CSV | Anual | Gasto del sistema ONU en Venezuela |
| Banco Mundial | API REST | Anual | PIB, indicadores de desarrollo |

### 📰 Noticias y Sentimiento
| Fuente | Tipo | Frecuencia | Datos |
|--------|------|------------|-------|
| Reddit r/vzla | API | Diaria | Sentimiento ciudadano |
| Portales de noticias | RSS | Diaria | Noticias económicas |

### 📋 Encuestas Ciudadanas y Comerciantes (NUEVO)

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
- **Motor de Análisis IA**: Cadena de 4+ LLMs con fallback (LLM1..LLM8 configurable)
- **Base de Datos**: PostgreSQL (Railway)
- **Cache**: Redis (opcional)

### Econometrics (NUEVO)
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

# Ingestas manuales
python -m src.scripts.collect_market    # Tasa de cambio / inflación → DB
python -m src.scripts.collect_news      # Noticias RSS + Reddit + sentimiento
python -m src.scripts.collect_surveys   # Encuestas Google

# Backfill de IBC y tickers venezolanos (para informes históricos)
python -m src.scripts.backfill_ibc                          # Backfill últimos 30 días
python -m src.scripts.backfill_ibc --since 2026-08-01 --until 2026-08-14  # Rango específico

# Informes económicos en PDF (diario → anual)
python -m src.scripts.generate_report --cadence semanal --format md,pdf

# Informe rango personalizado (ej: semana 10-14 agosto)
python -m src.scripts.generate_report --since 2026-08-10 --until 2026-08-14 --format md,pdf

# Informe sin resumen IA (más rápido)
python -m src.scripts.generate_report --cadence semanal --format pdf --no-ai
```

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
│   ├── config.py               # Configuración (pydantic, .env)
│   ├── collectors/             # Módulos de recolección
│   │   ├── http.py             #   Cliente HTTP compartido (GET/POST, retries)
│   │   ├── errors.py           #   Excepciones del dominio
│   │   ├── market/             #   bcv, ovf, bvc, binance, ibc_components, ibc_stocks
│   │   ├── fiscal/             #   onapre, cgr, seniat, mppef, gaceta, an + documents.py
│   │   ├── official/           #   ine
│   │   ├── international/      #   worldbank, opec, imf, cepal, pdvsa, unsceb
│   │   ├── news/               #   rss
│   │   ├── social/             #   reddit
│   │   └── surveys/            #   Encuestas Google (Forms→Sheets)
│   ├── models/                 # Modelos Pydantic
│   │   ├── market.py           #   ExchangeRate, InflationPoint, GDPPoint, BudgetExecution
│   │   ├── survey.py           #   Survey, SurveyResponse
│   │   └── news.py             #   NewsArticle, SocialPost
│   ├── db/                     # Persistencia
│   │   ├── session.py          #   Conexión (psycopg2)
│   │   ├── models.py           #   ORMs: SurveyORM, ExchangeRateORM, IBCIndexORM, VenezuelanTickerORM...
│   │   ├── repositories.py     #   SurveyRepository, MarketRepository, IBCIndexRepository, VenezuelanTickerRepository
│   │   └── migrations/         #   SQL de esquema
│   ├── analyzers/              # Análisis e IA
│   │   ├── macro.py            # Análisis macroeconómico
│   │   ├── micro.py            # Análisis microeconómico
│   │   ├── sentiment.py        # Análisis de sentimiento
│   │   ├── relevance.py        # Filtro de relevancia económica
│   │   ├── llm.py              # Cadena de LLMs con fallback (LLM1..LLM8)
│   │   ├── trends.py           # Detección de tendencias
│   │   ├── market_integration.py # Collectors → ARIMA/SARIMA
│   │   ├── surveys/            # Encuestas: KPIs y contraste
│   │   ├── reports/            # Informes: semanal (IA) + periódicos MD/PDF
│   │   │   ├── weekly.py       #   Informe semanal con resumen IA
│   │   │   ├── periodic.py     #   Snapshot por cadencia (diario→anual) + Markdown
│   │   │   └── pdf_report.py   #   Render PDF (ReportLab + matplotlib)
│   │   └── econometric/        # Módulo econométrico (NUEVO)
│   │       ├── stationarity.py # ADF, KPSS
│   │       ├── forecasting.py  # ARIMA, SARIMA
│   │       ├── causality.py    # Granger, VECM
│   │       ├── volatility.py   # GARCH
│   │       ├── diagnostics.py  # Residuos
│   │       └── regression.py   # Newey-West OLS
│   ├── dashboard/              # Visualización (Streamlit)
│   │   ├── app.py              #   Dashboard principal (tabs Inicio/Encuestas)
│   │   ├── theme.py            #   Tema visual
│   │   ├── market_data.py      #   Métricas de mercado desde DB
│   │   ├── surveys_data.py     #   Métricas de encuestas desde DB
│   │   └── components/         #   Componentes (survey_section)
│   ├── scripts/                # CLIs
│   │   ├── collect_surveys.py  #   Ingesta de encuestas
│   │   ├── collect_market.py   #   Recolección de mercado → DB
│   │   ├── collect_news.py     #   Noticias RSS + Reddit + sentimiento
│   │   ├── backfill_rates.py   #   Backfill histórico (usdt.com.ve)
│   │   ├── backfill_ibc.py     #   Backfill IBC + tickers venezolanos → BD
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
```

## 📅 Frecuencia de Actualización

| Componente | Frecuencia | Config |
|------------|------------|--------|
| Tasa de cambio (BCV + Binance P2P) | Cada 30 min | `MARKET_COLLECT_INTERVAL_MINUTES` |
| IBC + Tickers (backfill) | Diaria | `python -m src.scripts.backfill_ibc` |
| Encuestas (Google Forms → Sheets) | Cada 60 min | `SURVEY_COLLECT_INTERVAL_MINUTES` |
| Noticias RSS + sentimiento | Cada 6 h | `NEWS_COLLECT_INTERVAL_HOURS` |
| Análisis GARCH (volatilidad) | Pendiente | — |
| Informe semanal (con IA) | Cada domingo 08:00 | `WEEKLY_REPORT_DAY`/`WEEKLY_REPORT_HOUR` |
| Informe diario | 07:00 | cron `report_diario` |
| Informe semanal (PDF) | Lunes 08:00 | cron `report_semanal` |
| Informe mensual | Día 1, 09:00 | cron `report_mensual` |
| Informe trimestral | 1° de ene/abr/jul/oct 10:00 | cron `report_trimestral` |
| Informe semestral | 1° de ene/jul 11:00 | cron `report_semestral` |
| Informe anual | 1° de enero 12:00 | cron `report_anual` |

> El scheduler (APScheduler en `main.py`) ya registra los jobs de mercado, encuestas, noticias, informe semanal e informes periódicos (MD + PDF).

## 📈 Métricas del Dashboard

| Métrica | Descripción | Fuente | Estado |
|---------|-------------|--------|--------|
| **Dólar Oficial** | Tasa BCV | BCV API | ✅ En vivo |
| **Dólar Paralelo** | Precio USDT/VES Binance P2P | Binance | ✅ En vivo |
| **Dólar Bybit** | Precio USDT/VES Bybit P2P | Bybit | ✅ En vivo |
| **Inflación Mensual** | IPC | BCV | ✅ En vivo |
| **Encuestas** | Percepción por segmento | Google Forms | ✅ En vivo |
| **Brecha Cambiaria** | Diferencia oficial-paralelo % | Cálculo | ✅ En vivo |
| **Índice de Nerviosismo** | Volatilidad GARCH | Binance P2P | ⏳ |
| **Sentimiento** | Análisis léxico español + filtro relevancia económica | RSS/Reddit | ✅ En vivo |
| **Informe Semanal** | Markdown + resumen IA (cadena de LLMs con fallback) | Todo el sistema | ✅ Semanal |
| **Informes Periódicos PDF** | Diario→anual: carátula, resumen IA, gráficos, tablas de mercado/inflación/encuestas/sentimiento/noticias/fiscal/macro | Todo el sistema | ✅ 6 cadencias |
| **Acciones del IBC** | Top gainers/losers del índice bursátil (Yahoo Finance) | BVC via yfinance | ✅ En vivo |
| **Informes Rango Personalizado** | Generar informes para fechas específicas (--since/--until) | CLI | ✅ |
| **Pronóstico Inflación** | SARIMA | Modelo econométrico | ⏳ |

## 🤝 Contribuciones

Las contribuciones son bienvenidas: abre un issue o pull request en el repositorio.

## 📄 Licencia

Este proyecto se distribuye bajo la Licencia MIT.

## ⚠️ Disclaimer

Esta herramienta es solo para fines informativos y educativos. Los datos y análisis generados no deben tomarse como asesoría financiera o económica profesional. Siempre consulta a un experto antes de tomar decisiones basadas en estos datos.

## 📞 Contacto

- **GitHub**: [@betobeto00](https://github.com/betobeto00)
- **Repositorio**: [economia-venezuela](https://github.com/betobeto00/economia-venezuela)

---

**Hecho con ❤️ para la comunidad venezolana**
