# Economía Venezuela - Herramienta de Monitoreo y Análisis

![Venezuela Economy Tracker](https://img.shields.io/badge/Status-En%20Desarrollo-yellow) ![Python](https://img.shields.io/badge/Language-Python-blue) ![AI Powered](https://img.shields.io/badge/AI-DeepSeek%20V4--Pro-purple) ![Econometrics](https://img.shields.io/badge/Econometrics-Statsmodels-green) ![Tests](https://img.shields.io/badge/Tests-158%20passing-brightgreen)

## 📋 Visión General

Herramienta inteligente de monitoreo y análisis de la economía venezolana que integra múltiples fuentes de datos, análisis econométrico avanzado e inteligencia artificial para proporcionar una visión integral del panorama económico del país.

### 🎯 Objetivo

Crear un sistema automatizado que:
- Recopile datos económicos en tiempo real de múltiples fuentes
- Analice tendencias macro y microeconómicas con modelos econométricos
- Genere pronósticos con SARIMA, VECM y GARCH
- Evalúe el sentimiento público sobre la economía
- Proporcione dashboards interactivos para la visualización de datos
- Genere informes semanales automatizados con IA

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
| Binance P2P | API | Tiempo real | Precio del dólar en mercado paralelo |
| BVC (Bolsa de Caracas) | yfinance | Diaria | Índice IBC |
| OPEP | API | Mensual | Producción petrolera |

### 🏛️ Fuentes Fiscales y Oficiales
| Fuente | Tipo | Frecuencia | Datos |
|--------|------|------------|-------|
| ONAPRE | Web + PDF | Mensual | Ejecución presupuestaria |
| CGR (Contraloría General) | Web | Trimestral | Informes de gestión |
| INE | Web | Periódica | Empleo, demografía |
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
- **Motor de Análisis IA**: DeepSeek V4-Pro (1M tokens contexto)
- **Base de Datos**: PostgreSQL + TimescaleDB (series temporales)
- **Cache**: Redis

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
- `Grafana` - Monitoreo en tiempo real

### Automatización
- `GitHub Actions` - CI/CD y scheduling
- `Docker` - Contenedores
- `APScheduler` - Tareas programadas

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

# Ejecutar (scheduler + dashboard)
python main.py

# O solo el dashboard
streamlit run src/dashboard/app.py

# Ingestas manuales
python -m src.scripts.collect_surveys   # Encuestas Google
python -m src.scripts.collect_market    # Tasa de cambio / inflación → DB
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
│   │   ├── market/             #   bcv, ovf, bvc, binance
│   │   ├── fiscal/             #   onapre, cgr, seniat, mppef + documents.py
│   │   ├── official/           #   ine
│   │   ├── international/      #   worldbank, opec, imf, cepal, pdvsa
│   │   ├── news/               #   rss
│   │   ├── social/             #   reddit
│   │   └── surveys/            #   Encuestas Google (Forms→Sheets)
│   ├── models/                 # Modelos Pydantic
│   │   ├── market.py           #   ExchangeRate, InflationPoint, GDPPoint, BudgetExecution
│   │   ├── survey.py           #   Survey, SurveyResponse
│   │   └── news.py             #   NewsArticle, SocialPost
│   ├── db/                     # Persistencia
│   │   ├── session.py          #   Conexión (psycopg2)
│   │   ├── models.py           #   ORMs: SurveyORM, SurveyResponseORM, ExchangeRateORM...
│   │   ├── repositories.py     #   SurveyRepository, MarketRepository
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
│   │   ├── reports/            # Informe semanal automatizado (con IA)
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
│   │   └── backfill_rates.py   #   Backfill histórico (usdt.com.ve)
│   ├── scheduler/              # Programación
│   │   └── jobs.py             #   Jobs APScheduler (encuestas, mercado)
│   ├── alerts/                 # Sistema de alertas
│   ├── metrics/                # Métricas del sistema
│   └── security/               # Seguridad
├── data/
│   ├── raw/                    # Datos crudos
│   ├── processed/              # Datos procesados
│   └── reports/                # Informes generados
├── tests/                      # 158 tests (pytest)
└── docs/                       # Documentación
```

## 📅 Frecuencia de Actualización

| Componente | Frecuencia | Config |
|------------|------------|--------|
| Tasa de cambio (BCV + Binance P2P) | Cada 30 min | `MARKET_COLLECT_INTERVAL_MINUTES` |
| Encuestas (Google Forms → Sheets) | Cada 60 min | `SURVEY_COLLECT_INTERVAL_MINUTES` |
| Noticias RSS + sentimiento | Cada 6 h | `NEWS_COLLECT_INTERVAL_HOURS` |
| Análisis GARCH (volatilidad) | Pendiente | — |
| Informe semanal (con IA) | Cada domingo 08:00 | `WEEKLY_REPORT_DAY`/`WEEKLY_REPORT_HOUR` |

> El scheduler (APScheduler en `main.py`) ya registra los jobs de mercado, encuestas, noticias e informe semanal.

## 📈 Métricas del Dashboard

| Métrica | Descripción | Fuente | Estado |
|---------|-------------|--------|--------|
| **Dólar Oficial** | Tasa BCV | BCV API | ✅ En vivo |
| **Dólar Paralelo** | Precio USDT/VES Binance P2P | Binance | ✅ En vivo |
| **Inflación Mensual** | IPC | BCV | ✅ En vivo |
| **Encuestas** | Percepción por segmento | Google Forms | ✅ En vivo |
| **Spread Cambiario** | Diferencia oficial-paralelo | Cálculo | ⏳ |
| **Índice de Nerviosismo** | Volatilidad GARCH | Binance P2P | ⏳ |
| **Sentimiento** | Análisis léxico español + filtro relevancia económica | RSS/Reddit | ✅ En vivo |
| **Informe Semanal** | Markdown + resumen IA (cadena de 4 LLMs) | Todo el sistema | ✅ Semanal |
| **Pronóstico Inflación** | SARIMA | Modelo econométrico | ⏳ |

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor, lee `CONTRIBUTING.md` para detalles.

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo `LICENSE` para detalles.

## ⚠️ Disclaimer

Esta herramienta es solo para fines informativos y educativos. Los datos y análisis generados no deben tomarse como asesoría financiera o económica profesional. Siempre consulta a un experto antes de tomar decisiones basadas en estos datos.

## 📞 Contacto

- **GitHub**: [@betobeto00](https://github.com/betobeto00)
- **Repositorio**: [economia-venezuela](https://github.com/betobeto00/economia-venezuela)

---

**Hecho con ❤️ para la comunidad venezolana**
