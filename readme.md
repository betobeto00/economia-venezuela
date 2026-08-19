# Economía Venezuela - Herramienta de Monitoreo y Análisis

![Venezuela Economy Tracker](https://img.shields.io/badge/Status-En%20Desarrollo-yellow) ![Python](https://img.shields.io/badge/Language-Python-blue) ![AI Powered](https://img.shields.io/badge/AI-DeepSeek%20V4--Pro-purple)

## 📋 Visión General

Herramienta inteligente de monitoreo y análisis de la economía venezolana que integra múltiples fuentes de datos para proporcionar una visión integral del panorama económico del país.

### 🎯 Objetivo

Crear un sistema automatizado que:
- Recopile datos económicos en tiempo real de múltiples fuentes
- Analice tendencias macro y microeconómicas
- Genere informes semanales automatizados
- Proporcione dashboards interactivos para la visualización de datos
- Evalué el sentimiento público sobre la economía

## 🏗️ Arquitectura del Sistema

El sistema se compone de 4 capas principales:

```
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE VISUALIZACIÓN                     │
│              Dashboards / Informes / Alertas                 │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │
┌─────────────────────────────────────────────────────────────┐
│                   CAPA DE ANÁLISIS (IA)                      │
│            DeepSeek V4-Pro + NLP + ML                        │
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
| Portales de noticias (El Nacional, TalCual, etc.) | RSS/Scraping | Diaria | Noticias económicas |
| Facebook Groups | Web Scraping | Semanal | Opinión pública |

### 📊 Datos Económicos Oficiales
| Fuente | Tipo | Frecuencia | Datos |
|--------|------|------------|-------|
| INE (Instituto Nacional de Estadística) | Web | Mensual | IPC, PIB, empleo |
| OPEV | API | Mensual | Producción petrolera |
| FMI / Banco Mundial | API | Trimestral | Proyecciones macroeconómicas |

## 🔧 Stack Tecnológico

### Core
- **Lenguaje Principal**: Python 3.10+
- **Motor de Análisis IA**: DeepSeek V4-Pro (1M tokens contexto)
- **Orquestación**: OpenCode CLI o Apache Airflow
- **Base de Datos**: PostgreSQL + TimescaleDB (series temporales)
- **Cache**: Redis

### Data Collection
- `pyvenezuela` - Consultas BCV
- `pydolarvenezuela` - Precios del dólar
- `requests` / `httpx` - APIs REST
- `BeautifulSoup` / `Playwright` - Web Scraping
- `tweepy` / `snscrape` - Redes sociales

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
- `cron` / `APScheduler` - Tareas programadas

## 🚀 Instalación Rápida

```bash
# Clonar el repositorio
git clone https://github.com/tu-usuario/economia-venezuela.git
cd economia-venezuela

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate  # Windows

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
│   ├── collectors/              # Módulos de recolección de datos
│   │   ├── bcv.py              # Colector BCV
│   │   ├── dolar.py            # Monitores de dólar
│   │   ├── news.py             # Noticias y RSS
│   │   ├── social.py           # Redes sociales
│   │   └── mercado_libre.py    # Mercado Libre
│   ├── processors/              # Procesamiento y limpieza
│   │   ├── cleaner.py          # Limpieza de datos
│   │   ├── normalizer.py       # Normalización
│   │   └── storage.py          # Almacenamiento
│   ├── analyzers/               # Análisis e IA
│   │   ├── macro.py            # Análisis macroeconómico
│   │   ├── micro.py            # Análisis microeconómico
│   │   ├── sentiment.py        # Análisis de sentimiento
│   │   └── trends.py           # Detección de tendencias
│   ├── reports/                 # Generación de informes
│   │   ├── weekly.py           # Informe semanal
│   │   └── templates/          # Plantillas
│   ├── dashboard/               # Visualización
│   │   ├── app.py              # Streamlit app
│   │   └── components/         # Componentes UI
│   └── config.py               # Configuración
├── data/
│   ├── raw/                    # Datos crudos
│   ├── processed/              # Datos procesados
│   └── reports/                # Informes generados
├── tests/                       # Pruebas unitarias
├── scripts/                     # Scripts auxiliares
└── docs/                        # Documentación adicional
```

## 📅 Frecuencia de Actualización

| Componente | Frecuencia | Horario |
|------------|------------|---------|
| Tasa de cambio | Tiempo real | 24/7 |
| Noticias | Cada 6 horas | 06:00, 12:00, 18:00, 00:00 |
| Análisis de sentimiento | Diaria | 22:00 |
| Informe semanal | Semanal | Domingos 08:00 |
| Datos macroeconómicos | Mensual | Primer día del mes |

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor, lee `CONTRIBUTING.md` para detalles.

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo `LICENSE` para detalles.

## ⚠️ Disclaimer

Esta herramienta es solo para fines informativos y educativos. Los datos y análisis generados no deben tomarse como asesoría financiera o económica profesional. Siempre consulta a un experto antes de tomar decisiones basadas en estos datos.

## 📞 Contacto

- **Email**: tu-email@ejemplo.com
- **GitHub**: [@tu-usuario](https://github.com/tu-usuario)
- **Twitter**: @tu-handle

---

**Hecho con ❤️ para la comunidad venezolana**
