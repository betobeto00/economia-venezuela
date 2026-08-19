# Economía Venezuela - Herramienta de Monitoreo y Análisis

![Venezuela Economy Tracker](https://img.shields.io/badge/Status-En%20Desarrollo-yellow) ![Python](https://img.shields.io/badge/Language-Python-blue) ![AI Powered](https://img.shields.io/badge/AI-DeepSeek%20V4--Pro-purple) ![Econometrics](https://img.shields.io/badge/Econometrics-Statsmodels-green)

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
| BCV (Banco Central de Venezuela) | API/Web Scraping | Diaria | Tasa de cambio oficial, inflación, reservas |
| pydolarvenezuela | Python Library | Tiempo real | Múltiples monitores de dólar |
| Cotizave | API REST | Tiempo real | Tasas BCV + exchanges P2P |
| Binance P2P | API | Tiempo real | Precio del dólar en mercado paralelo |
| Mercado Libre | Web Scraping | Semanal | Precios de productos de referencia |

### 📰 Noticias y Sentimiento
| Fuente | Tipo | Frecuencia | Datos |
|--------|------|------------|-------|
| Reddit r/vzla | Web Scraping | Diaria | Sentimiento ciudadano |
| Twitter/X | API/Sentiment | Tiempo real | Análisis de sentimiento |
| Portales de noticias | RSS/Scraping | Diaria | Noticias económicas |
| Facebook Groups | Web Scraping | Semanal | Opinión pública |

### 📋 Encuestas Ciudadanas y Comerciantes (NUEVO)

Datos primarios de percepción económica vía **Google Forms** que fortalecen el análisis
microeconómico y se contrastan con los datos oficiales.

| Fuente | Tipo | Frecuencia | Datos |
|--------|------|------------|-------|
| Formulario Persona Común | Google Forms → Sheets | Continua (ingesta horaria) | Percepción de inflación, poder adquisitivo, gasto, ahorro, empleo |
| Formulario Comerciante | Google Forms → Sheets | Continua (ingesta horaria) | Clima de negocios, precios, demanda, métodos de pago, costos |

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

# Ejecutar
python main.py
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
├── src/
│   ├── __init__.py
│   ├── config.py               # Configuración
│   ├── collectors/             # Módulos de recolección
│   │   └── surveys/            #   Encuestas Google (Forms→Sheets) (NUEVO)
│   ├── processors/             # Procesamiento
│   ├── analyzers/              # Análisis e IA
│   │   ├── macro.py            # Análisis macroeconómico
│   │   ├── micro.py            # Análisis microeconómico
│   │   ├── sentiment.py        # Análisis de sentimiento
│   │   ├── trends.py           # Detección de tendencias
│   │   ├── surveys/            # Encuestas: KPIs y contraste (NUEVO)
│   │   └── econometric/        # Módulo econométrico (NUEVO)
│   │       ├── __init__.py
│   │       ├── stationarity.py # ADF, KPSS
│   │       ├── forecasting.py  # ARIMA, SARIMA
│   │       ├── causality.py    # Granger, VECM
│   │       ├── volatility.py   # GARCH
│   │       ├── diagnostics.py  # Residuos
│   │       └── regression.py   # Newey-West OLS
│   ├── reports/                # Generación de informes
│   ├── dashboard/              # Visualización
│   │   └── app.py              # Streamlit app
│   ├── alerts/                 # Sistema de alertas
│   ├── metrics/                # Métricas del sistema
│   ├── security/               # Seguridad
│   └── scheduler/              # Programación
├── data/
│   ├── raw/                    # Datos crudos
│   ├── processed/              # Datos procesados
│   └── reports/                # Informes generados
├── tests/
│   └── test_econometric.py     # Tests econométricos
└── docs/                       # Documentación
```

## 📅 Frecuencia de Actualización

| Componente | Frecuencia | Horario |
|------------|------------|---------|
| Tasa de cambio | Tiempo real | 24/7 |
| Noticias | Cada 6 horas | 06:00, 12:00, 18:00, 00:00 |
| Análisis de sentimiento | Diaria | 22:00 |
| Análisis GARCH (volatilidad) | Diaria | 23:00 |
| Informe semanal | Semanal | Domingos 08:00 |
| Datos macroeconómicos | Mensual | Primer día del mes |

## 📈 Métricas del Dashboard

| Métrica | Descripción | Fuente |
|---------|-------------|--------|
| **Dólar Oficial** | Tasa BCV | BCV API |
| **Dólar Paralelo** | Tasa mercado | DólarToday |
| **Inflación Mensual** | IPC | BCV |
| **Spread Cambiario** | Diferencia oficial-paralelo | Cálculo |
| **Índice de Nerviosismo** | Volatilidad GARCH | Binance P2P |
| **Sentimiento** | Análisis NLP | Reddit/Twitter |
| **Pronóstico Inflación** | SARIMA | Modelo econométrico |

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
