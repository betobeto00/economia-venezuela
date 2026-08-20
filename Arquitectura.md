# Arquitectura del Sistema - Economía Venezuela

## 📐 Visión General de la Arquitectura

Este documento describe la arquitectura técnica del sistema de monitoreo económico de Venezuela. El diseño sigue un enfoque modular, escalable y orientado a microservicios para garantizar flexibilidad y mantenibilidad.

## ✅ Estado de Implementación

> Secciones de este documento con `**DISEÑO**` describen el estado objetivo. Lo que sigue
> ya está **implementado y testeado** (341 tests):

| Componente | Estado |
|------------|--------|
| Collectors Fase A | ✅ BCV, OVF, BVC, Binance, Bybit, INE, OPEP, ONAPRE, CGR, World Bank, RSS, Reddit (RSS/JSON público), IBC components, IBC stocks, dolar paralelo bancos |
| Collectors Fiscales | ✅ SENIAT, MPPEF, Gaceta Oficial (OCR), AN, Cendas-FVM |
| Collectors Internacionales | ✅ FMI (SDMX), CEPAL, UNSCEB, PDVSA |
| Collectors Consumo | ✅ ANSA, Atenas Grupo Consultor |
| Integración econométrica | ✅ `analyzers/market_integration.py` (ARIMA/SARIMA sobre collectors) |
| Encuestas (código) | ✅ Collector gspread idempotente, modelos, KPIs, contraste, dashboard |
| Encuestas (manual) | 🟡 Formularios Google + service account pendientes |
| Persistencia | ✅ `db/` con ORMs (9 tablas), repositorios y migraciones SQL |
| Dashboard Streamlit | ✅ 3 tabs (Inicio, Noticias, Encuestas), métricas desde DB, gráficos Plotly |
| Scheduler | ✅ APScheduler: 11 jobs (mercado, encuestas, noticias, informe semanal, 6 informes periódicos) |
| Informes | ✅ Semanal (IA) + periódicos diario→anual (MD + PDF) |
| CLIs | ✅ collect_market, collect_news, collect_surveys, backfill_rates, backfill_ibc, generate_report |

---

## 🏛️ Principios de Diseño

### 1. Modularidad
Cada componente es independiente y puede desarrollarse, testearse y desplegarse por separado.

### 2. Escalabilidad Horizontal
El sistema puede escalar añadiendo más instancias de los componentes que lo requieran.

### 3. Resiliencia
El sistema tolera fallos en fuentes de datos individuales sin afectar el funcionamiento global.

### 4. Extensibilidad
Nuevas fuentes de datos y análisis se pueden añadir con mínimos cambios al código existente.

### 5. Desacoplamiento
Los componentes se comunican mediante eventos y colas de mensajes, no directamente.

---

## 🔄 Arquitectura de Alto Nivel

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           SISTEMA ECONOMÍA VENEZUELA                        │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  Dashboard  │  │   Reports   │  │   Alerts    │  │    API      │        │
│  │  Streamlit  │  │   PDF/MD    │  │  Telegram   │  │   REST      │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         │                │                │                │                 │
│         └────────────────┴────────────────┴────────────────┘                 │
│                                      │                                       │
│                              ┌───────┴───────┐                               │
│                              │    API GATEWAY │                               │
│                              │   (FastAPI)    │                               │
│                              └───────┬───────┘                               │
│                                      │                                       │
│  ┌───────────────────────────────────┼───────────────────────────────────┐   │
│  │                          EVENT BUS (Redis Streams)                    │   │
│  └───────────────────────────────────┼───────────────────────────────────┘   │
│                                      │                                       │
│         ┌────────────────────────────┼────────────────────────────┐          │
│         │                            │                            │          │
│  ┌──────┴──────┐             ┌───────┴───────┐             ┌─────┴─────┐   │
│  │ COLLECTORS  │             │  PROCESSORS   │             │ ANALYZERS │   │
│  │             │             │               │             │           │   │
│  │ • BCV       │             │ • Cleaner     │             │ • Macro   │   │
│  │ • Dólar     │────────────▶│ • Normalizer  │────────────▶│ • Micro   │   │
│  │ • News      │             │ • Enricher    │             │ • Sentim. │   │
│  │ • Social    │             │ • Validator   │             │ • Trends  │   │
│  │ • Mercado   │             │               │             │ • Predict │   │
│  └─────────────┘             └───────────────┘             └───────────┘   │
│         │                            │                            │          │
│         └────────────────────────────┴────────────────────────────┘          │
│                                      │                                       │
│                              ┌───────┴───────┐                               │
│                              │    STORAGE     │                               │
│                              │  PostgreSQL +  │                               │
│                              │  TimescaleDB   │                               │
│                              └───────────────┘                               │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 📦 Componentes Detallados

### 1. 🔄 Capa de Recolección (Collectors)

Responsable de obtener datos de múltiples fuentes externas.

#### 1.1 BCV Collector
```python
# src/collectors/bcv.py

class BCVCollector:
    """
    Recolector de datos del Banco Central de Venezuela.
    
    Fuentes:
    - pyvenezuela (librería Python)
    - Web scraping de bcv.org.ve
    - API pública BCV (si disponible)
    """
    
    async def fetch_dollar_rate(self) -> DollarRate:
        """Obtiene tasa de cambio oficial USD/VES"""
        pass
    
    async def fetch_inflation(self) -> InflationData:
        """Obtiene datos de inflación IPC"""
        pass
    
    async def fetch_reserves(self) -> ReservesData:
        """Obtiene reservas internacionales"""
        pass
    
    async def fetch_money_supply(self) -> MoneySupply:
        """Obtiene masa monetaria"""
        pass
```

#### 1.2 Dólar Collector
```python
# src/collectors/dolar.py

class DolarCollector:
    """
    Recolector de precios del dólar de múltiples monitores.
    
    Monitores soportados:
    - pydolarvenezuela
    - DolarToday
    - Monitor Dólar
    - Binance P2P
    - LocalBitcoins
    """
    
    async def fetch_all_monitors(self) -> List[DollarMonitor]:
        """Obtiene precios de todos los monitores"""
        pass
    
    async def fetch_binance_p2p(self) -> P2PPrice:
        """Obtiene precio del dólar en Binance P2P"""
        pass
    
    async def calculate_spread(self) -> SpreadAnalysis:
        """Calcula spread entre diferentes mercados"""
        pass
```

#### 1.3 News Collector
```python
# src/collectors/news.py

class NewsCollector:
    """
    Recolector de noticias económicas.
    
    Fuentes:
    - RSS feeds de portales venezolanos
    - Web scraping de noticias
    - APIs de noticias (NewsAPI, etc.)
    """
    
    async def fetch_rss_feeds(self) -> List[NewsArticle]:
        """Obtiene noticias de feeds RSS"""
        pass
    
    async def fetch_web_news(self) -> List[NewsArticle]:
        """Obtiene noticias vía web scraping"""
        pass
    
    async def filter_economic_news(self, articles: List[NewsArticle]) -> List[NewsArticle]:
        """Filtra solo noticias económicas relevantes"""
        pass
```

#### 1.4 Social Collector
```python
# src/collectors/social.py

class SocialCollector:
    """
    Recolector de datos de redes sociales.
    
    Plataformas:
    - Reddit (r/vzla, r/vzlaconomics)
    - Twitter/X (cuentas económicas relevantes)
    - Facebook (grupos económicos)
    """
    
    async def fetch_reddit_threads(self) -> List[RedditThread]:
        """Obtiene hilos relevantes de Reddit"""
        pass
    
    async def fetch_twitter_sentiment(self) -> TwitterSentiment:
        """Obtiene datos de sentimiento de Twitter"""
        pass
    
    async def fetch_facebook_groups(self) -> List[FacebookPost]:
        """Obtiene publicaciones de grupos de Facebook"""
        pass
```

#### 1.5 Mercado Libre Collector
```python
# src/collectors/mercado_libre.py

class MercadoLibreCollector:
    """
    Recolector de precios de referencia de Mercado Libre Venezuela.
    
    Categorías:
    - Alimentos básicos
    - Productos electrónicos
    - Vehículos
    - Inmuebles
    """
    
    async def fetch_product_prices(self, category: str) -> List[Product]:
        """Obtiene precios de productos por categoría"""
        pass
    
    async def calculate_inflation_basket(self) -> InflationBasket:
        """Calcula canasta básica de inflación"""
        pass
```

#### 1.6 Survey Collector (NUEVO — Encuestas Google)

Recolección de datos primarios desde **Google Forms → Google Sheets** para análisis
microeconómico y de percepción ciudadana.

```python
# src/collectors/surveys/survey_collector.py
import gspread
from google.oauth2 import service_account

class SurveyCollector:
    """
    Recolector de respuestas de encuestas vía Google Sheets API (gspread).
    
    Flujo:
    - Google Forms registra respuestas en una Google Sheet vinculada.
    - Este collector lee las filas nuevas (idempotente, marca última fila).
    - Normaliza y persiste en survey_responses (PostgreSQL/TimescaleDB).
    
    Tipos soportados:
    - persona_comun    (ciudadano promedio)
    - comerciante      (negocios y comercio)
    - extensible a más segmentos (empresa, remesas, ...)
    """
    
    def __init__(self, credentials_path: str):
        self.client = gspread.authorize(
            service_account.Credentials.from_service_account_file(credentials_path)
        )
    
    async def fetch_new_responses(self, survey: Survey) -> List[SurveyResponse]:
        """Obtiene respuestas nuevas (desde la última fila procesada)"""
        pass
    
    async def process_response(self, raw: dict, survey: Survey) -> SurveyResponse:
        """Normaliza la respuesta cruda a SurveyResponse con KPIs derivados"""
        pass
```

---

### 2. ⚙️ Capa de Procesamiento (Processors)

Limpieza, normalización y validación de datos crudos.

#### 2.1 Cleaner
```python
# src/processors/cleaner.py

class DataCleaner:
    """
    Limpia y transforma datos crudos.
    
    Operaciones:
    - Eliminación de duplicados
    - Manejo de valores faltantes
    - Corrección de formato
    - Validación de rangos
    """
    
    def clean_dollar_data(self, data: RawDollarData) -> CleanDollarData:
        pass
    
    def clean_news_data(self, articles: List[RawArticle]) -> List[CleanArticle]:
        pass
    
    def clean_social_data(self, posts: List[RawPost]) -> List[CleanPost]:
        pass
```

#### 2.2 Normalizer
```python
# src/processors/normalizer.py

class DataNormalizer:
    """
    Normaliza datos a formatos estándar.
    
    Estandarización:
    - Monedas (VES, USD, EUR)
    - Fechas (ISO 8601)
    - Unidades (kg, litros, etc.)
    - Categorías económicas
    """
    
    def normalize_currency(self, amount: float, currency: str) -> NormalizedAmount:
        pass
    
    def normalize_date(self, date_str: str) -> datetime:
        pass
    
    def normalize_category(self, category: str) -> EconomicCategory:
        pass
```

#### 2.3 Storage
```python
# src/processors/storage.py

class DataStorage:
    """
    Almacenamiento persistente en PostgreSQL + TimescaleDB.
    
    Tipos de datos:
    - Series temporales (TimescaleDB hypertables)
    - Datos estándar (tablas PostgreSQL)
    - Datos derivados (vistas materializadas)
    """
    
    async def store_dollar_rate(self, rate: DollarRate) -> None:
        pass
    
    async def store_news(self, article: NewsArticle) -> None:
        pass
    
    async def store_sentiment(self, sentiment: SentimentData) -> None:
        pass
    
    async def get_time_series(self, metric: str, period: str) -> TimeSeries:
        pass
```

---

### 3. 🧠 Capa de Análisis (Analyzers)

Motor de análisis e inteligencia artificial.

#### 3.1 Macro Analyzer
```python
# src/analyzers/macro.py

class MacroAnalyzer:
    """
    Análisis macroeconómico usando DeepSeek V4-Pro.
    
    Métricas:
    - PIB y crecimiento económico
    - Inflación (IPC)
    - Tipo de cambio oficial vs paralelo
    - Reservas internacionales
    - Deuda pública
    - Balanza comercial
    - Producción petrolera
    """
    
    async def analyze_economic_health(self, data: EconomicData) -> MacroReport:
        """Genera reporte de salud económica macro"""
        pass
    
    async def predict_inflation(self, historical: List[InflationData]) -> InflationForecast:
        """Predice tendencia de inflación"""
        pass
    
    async def analyze_currency_stability(self, rates: List[DollarRate]) -> CurrencyAnalysis:
        """Analiza estabilidad de la moneda"""
        pass
```

#### 3.2 Micro Analyzer
```python
# src/analyzers/micro.py

class MicroAnalyzer:
    """
    Análisis microeconómico.
    
    Métricas:
    - Precios de productos de consumo
    - Poder adquisitivo
    - Salarios vs inflación
    - Costo de vida
    - Empleo informal
    """
    
    async def analyze_purchasing_power(self, data: PurchasingData) -> PowerReport:
        """Analiza poder adquisitivo"""
        pass
    
    async def analyze_cost_of_living(self, prices: List[ProductPrice]) -> CostReport:
        """Analiza costo de vida"""
        pass
    
    async def analyze_wage_trends(self, wages: List[WageData]) -> WageReport:
        """Analiza tendencias salariales"""
        pass
```

#### 3.3 Sentiment Analyzer
```python
# src/analyzers/sentiment.py

class SentimentAnalyzer:
    """
    Análisis de sentimiento usando NLP y DeepSeek.
    
    Fuentes:
    - Reddit posts y comments
    - Tweets
    - Noticias
    - Comentarios deFacebook
    
    Clasificación:
    - Positivo / Negativo / Neutro
    - Emoconómico específico
    - Tendencia temporal
    """
    
    async def analyze_text_sentiment(self, text: str) -> SentimentScore:
        """Analiza sentimiento de un texto"""
        pass
    
    async def analyze_batch_sentiment(self, texts: List[str]) -> BatchSentiment:
        """Analiza sentimiento de múltiples textos"""
        pass
    
    async def generate_sentiment_trend(self, period: str) -> SentimentTrend:
        """Genera tendencia de sentimiento temporal"""
        pass
```

#### 3.4 Trends Analyzer
```python
# src/analyzers/trends.py

class TrendsAnalyzer:
    """
    Detección y análisis de tendencias económicas.
    
    Técnicas:
    - Series temporales (ARIMA, Prophet)
    - Análisis de ciclo económico
    - Detección de anomalías
    - Correlación entre variables
    """
    
    async def detect_trends(self, data: TimeSeries) -> List[Trend]:
        """Detecta tendencias en series temporales"""
        pass
    
    async def forecast_values(self, series: TimeSeries, horizon: int) -> Forecast:
        """Predice valores futuros"""
        pass
    
    async def detect_anomalies(self, data: TimeSeries) -> List[Anomaly]:
        """Detecta anomalías en los datos"""
        pass
```

#### 3.5 Survey Analyzer (NUEVO — Encuestas)

Análisis de respuestas de encuestas por segmento y contraste con datos oficiales.

```python
# src/analyzers/surveys/

class SurveyAnalyzer:
    """
    Análisis de datos de encuestas.
    
    Indicadores por segmento:
    - persona_comun: percepción de inflación, poder adquisitivo percibido,
                     índice de ahorro, medios de pago, expectativas.
    - comerciante:   clima de negocios, índice de ajuste de precios,
                     evolución de demanda, acceso a crédito, dolarización.
    
    Métodos:
    - Contraste percepción vs IPC oficial/OVF (brecha de percepción)
    - Tendencias temporales por segmento
    - Resumen ejecutivo generado con DeepSeek
    """
    
    async def compute_indicators(self, responses: List[SurveyResponse]) -> Dict:
        """Calcula KPIs agregados por segmento y período"""
        pass
    
    async def contrast_with_official(self, indicators: Dict) -> ContrastResult:
        """Contrasta percepción vs datos oficiales (BCV, OVF)"""
        pass
    
    async def generate_executive_summary(self, analysis: Dict) -> str:
        """Genera resumen ejecutivo del período con IA"""
        pass
```

---

### 4. 📊 Capa de Visualización (Dashboard)

Interfaz de usuario para explorar datos e informes.

#### 4.1 Streamlit Dashboard

El dashboard tiene 3 tabs:
- **🏠 Inicio**: Tarjetas de dólar oficial/paralelo/Bybit, inflación, brecha cambiaria, gráfico 6 meses
- **📰 Noticias**: Sentimiento de noticias/posts, distribución, últimos titulares
- **📋 Encuestas**: KPIs por segmento, serie temporal, contraste percepción vs realidad, informe ejecutivo

```python
# src/dashboard/app.py (fragmento)

import streamlit as st

# Page config
st.set_page_config(
    page_title="Economía Venezuela",
    page_icon="🇻🇪",
    layout="wide"
)

# Tabs
tab_inicio, tab_noticias, tab_encuestas = st.tabs(
    ["🏠 Inicio", "📰 Noticias", "📋 Encuestas"]
)

with tab_inicio:
    metrics = dashboard_metrics()
    brecha = brecha_porcentaje(metrics["oficial"], metrics["paralelo"])
    # 4 métricas: Oficial, Binance, Bybit, Inflación
    # + 2 tarjetas de brecha + gráfico Plotly 6 meses

with tab_noticias:
    render_news_section()  # Sentimiento + titulares

with tab_encuestas:
    render_survey_section(survey_segment)  # KPIs + serie + contraste + informe
```

#### 4.2 Componentes del Dashboard
```python
# src/dashboard/components/

# Tarjetas de métricas
def render_metric_card(title: str, value: str, change: float):
    """Renderiza tarjeta de métrica con cambio porcentual"""
    pass

# Gráficos de series temporales
def render_time_series_chart(data: TimeSeries, title: str):
    """Renderiza gráfico de series temporales"""
    pass

# Mapa de calor de sentimiento
def render_sentiment_heatmap(sentiment_data: SentimentData):
    """Renderiza mapa de calor de sentimiento"""
    pass

# Tabla de datos
def render_data_table(data: pd.DataFrame):
    """Renderiza tabla interactiva de datos"""
    pass
```

---

### 5. 🔔 Capa de Alertas

Notificaciones y alertas automáticas.

```python
# src/alerts/

class AlertManager:
    """
    Gestor de alertas del sistema.
    
    Tipos de alerta:
    - Cambios significativos en tipo de cambio
    - Inflación fuera de rango esperado
    - Anomalías en datos económicos
    - Sentimiento extremadamente negativo
    - Caídas en reservas internacionales
    """
    
    async def check_alerts(self, data: EconomicData) -> List[Alert]:
        """Verifica condiciones de alerta"""
        pass
    
    async def send_alert(self, alert: Alert):
        """Envía alerta por múltiples canales"""
        # Telegram
        # Email
        # Dashboard
        pass
```

---

### 6. ⏰ Capa de Orquestación (Scheduler)

Programación y ejecución de tareas.

```python
# src/scheduler/

class TaskScheduler:
    """
    Programador de tareas del sistema.
    
    Frecuencias:
    - Tiempo real: Tipo de cambio
    - Cada 6 horas: Noticias
    - Diario: Análisis de sentimiento
    - Semanal: Informe completo
    - Mensual: Análisis macroeconómico profundo
    """
    
    def setup_schedules(self):
        """Configura todas las tareas programadas"""
        # Real-time tasks
        scheduler.add_job(
            self.collect_dollar_rates,
            'interval',
            minutes=5
        )
        
        # Periodic tasks
        scheduler.add_job(
            self.collect_news,
            'interval',
            hours=6
        )
        
        # Daily tasks
        scheduler.add_job(
            self.analyze_sentiment,
            'cron',
            hour=22
        )
        
        # Weekly tasks
        scheduler.add_job(
            self.generate_weekly_report,
            'cron',
            day_of_week='sun',
            hour=8
        )
```

---

## 🗄️ Modelo de Base de Datos

### Diagrama Entidad-Relación

```
┌─────────────────────────────────────────────────────────────────────┐
│                         BASE DE DATOS (9 tablas)                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────┐      ┌──────────────────┐                     │
│  │ exchange_rates   │      │  inflation_points│                     │
│  │──────────────────│      │──────────────────│                     │
│  │ id (BIGINT PK)   │      │ id (BIGINT PK)   │                     │
│  │ source           │      │ source           │                     │
│  │ currency         │      │ period (YYYY-MM) │                     │
│  │ rate             │      │ monthly_rate     │                     │
│  │ date             │      │ annual_rate      │                     │
│  │ variation_pct    │      │ index            │                     │
│  └──────────────────┘      └──────────────────┘                     │
│                                                                      │
│  ┌──────────────────┐      ┌──────────────────┐                     │
│  │  news_articles   │      │   social_posts   │                     │
│  │──────────────────│      │──────────────────│                     │
│  │ id (BIGINT PK)   │      │ id (BIGINT PK)   │                     │
│  │ source           │      │ source (reddit)  │                     │
│  │ title            │      │ channel          │                     │
│  │ url              │      │ title            │                     │
│  │ published        │      │ url              │                     │
│  │ summary          │      │ text             │                     │
│  └──────────────────┘      │ score / comments │                     │
│                            │ published        │                     │
│                            └──────────────────┘                     │
│                                                                      │
│  ┌──────────────────┐      ┌──────────────────┐                     │
│  │ sentiment_scores │      │     surveys      │                     │
│  │──────────────────│      │──────────────────│                     │
│  │ id (BIGINT PK)   │      │ id (INT PK)      │                     │
│  │ item_type        │      │ survey_type      │                     │
│  │ item_id (FK)     │      │ form_id          │                     │
│  │ text             │      │ sheet_id         │                     │
│  │ score            │      │ form_version     │                     │
│  │ label            │      │ name             │                     │
│  │ analyzed_at      │      │ active           │                     │
│  └──────────────────┘      └────────┬─────────┘                     │
│                                     │                                │
│                            ┌────────┴─────────┐                     │
│                            │ survey_responses │                     │
│                            │──────────────────│                     │
│                            │ id (BIGINT PK)   │                     │
│                            │ survey_id (FK)   │                     │
│                            │ submitted_at     │                     │
│                            │ respondent_seg.  │                     │
│                            │ raw_answers JSONB│                     │
│                            │ kpis JSONB       │                     │
│                            │ quality_score    │                     │
│                            └──────────────────┘                     │
│                                                                      │
│  ┌──────────────────┐      ┌──────────────────┐                     │
│  │   ibc_index      │      │  ibc_components  │                     │
│  │──────────────────│      │──────────────────│                     │
│  │ id (BIGINT PK)   │      │ id (BIGINT PK)   │                     │
│  │ date             │      │ date             │                     │
│  │ value            │      │ ticker           │                     │
│  │ change           │      │ name             │                     │
│  │ change_pct       │      │ price            │                     │
│  │ fetched_at       │      │ change_pct       │                     │
│  └──────────────────┘      │ volume           │                     │
│                            │ fetched_at       │                     │
│                            └──────────────────┘                     │
│                                                                      │
│  ┌──────────────────────────────────┐                                │
│  │    venezuelan_tickers            │                                │
│  │──────────────────────────────────│                                │
│  │ id (BIGINT PK)                   │                                │
│  │ date / ticker / name             │                                │
│  │ close / change_pct / avg_volume  │                                │
│  │ fetched_at                       │                                │
│  └──────────────────────────────────┘                                │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Esquemas SQL (ORMs SQLAlchemy)

Los ORMs están en `src/db/models.py`. Tablas principales:

```sql
-- Tasas de cambio (por fuente y moneda)
CREATE TABLE exchange_rates (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(20) NOT NULL,        -- bcv, ovf, binance, bybit, bancos...
    currency VARCHAR(10) NOT NULL,      -- usd, usdt...
    rate DECIMAL(18,6) NOT NULL,
    date TIMESTAMPTZ NOT NULL,
    variation_pct DECIMAL(10,4),
    UNIQUE (source, currency, date)
);

-- Inflación mensual por emisor y período
CREATE TABLE inflation_points (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(20) NOT NULL,        -- bcv, ovf, world_bank
    period VARCHAR(7) NOT NULL,         -- YYYY-MM
    monthly_rate DECIMAL(10,4),
    annual_rate DECIMAL(10,4),
    index DECIMAL(18,6),
    UNIQUE (source, period)
);

-- Artículos de noticias (RSS)
CREATE TABLE news_articles (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(100) NOT NULL,
    title VARCHAR(300) NOT NULL,
    url VARCHAR(1000) NOT NULL,
    published TIMESTAMPTZ,
    summary VARCHAR(500),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (source, url)
);

-- Publicaciones sociales (Reddit)
CREATE TABLE social_posts (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(20) NOT NULL,        -- reddit
    channel VARCHAR(100) NOT NULL,      -- subreddit
    title VARCHAR(300) NOT NULL,
    url VARCHAR(1000) NOT NULL,
    text VARCHAR(1000),
    score INTEGER,
    num_comments INTEGER,
    published TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (source, url)
);

-- Puntajes de sentimiento (por ítem)
CREATE TABLE sentiment_scores (
    id BIGSERIAL PRIMARY KEY,
    item_type VARCHAR(20) NOT NULL,     -- news | social
    item_id BIGINT NOT NULL,
    text VARCHAR(500) NOT NULL,
    score DECIMAL(5,4) NOT NULL,
    label VARCHAR(10) NOT NULL,         -- positive | neutral | negative
    analyzed_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (item_type, item_id)
);

-- Índice IBC (Bolsa de Valores de Caracas)
CREATE TABLE ibc_index (
    id BIGSERIAL PRIMARY KEY,
    date TIMESTAMPTZ NOT NULL UNIQUE,
    value DECIMAL(12,2) NOT NULL,
    "change" DECIMAL(12,2) DEFAULT 0,
    change_pct DECIMAL(8,4) DEFAULT 0,
    fetched_at TIMESTAMPTZ DEFAULT NOW()
);

-- Componentes del IBC (acciones individuales)
CREATE TABLE ibc_components (
    id BIGSERIAL PRIMARY KEY,
    date TIMESTAMPTZ NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    name VARCHAR(100) NOT NULL,
    price DECIMAL(12,2) NOT NULL,
    change_pct DECIMAL(8,4) DEFAULT 0,
    volume BIGINT DEFAULT 0,
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (date, ticker)
);

-- Tickers venezolanos relevantes (fuera del IBC)
CREATE TABLE venezuelan_tickers (
    id BIGSERIAL PRIMARY KEY,
    date TIMESTAMPTZ NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    name VARCHAR(100) NOT NULL,
    close DECIMAL(12,2) NOT NULL,
    change_pct DECIMAL(8,4) DEFAULT 0,
    avg_volume BIGINT DEFAULT 0,
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (date, ticker)
);

-- Encuestas (Google Forms)
CREATE TABLE surveys (
    id SERIAL PRIMARY KEY,
    survey_type VARCHAR(50) NOT NULL,   -- persona_comun | comerciante
    form_id VARCHAR(100) NOT NULL,
    sheet_id VARCHAR(100) NOT NULL,
    form_version INT NOT NULL DEFAULT 1,
    name VARCHAR(200),
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Respuestas de encuestas (JSONB flexible)
CREATE TABLE survey_responses (
    id BIGSERIAL PRIMARY KEY,
    survey_id INT REFERENCES surveys(id),
    submitted_at TIMESTAMPTZ NOT NULL,
    respondent_segment VARCHAR(50),
    timezone VARCHAR(50),
    raw_answers JSONB,
    kpis JSONB,
    quality_score DECIMAL(3,2),
    source VARCHAR(20) DEFAULT 'google_forms',
    UNIQUE (survey_id, submitted_at, raw_answers)
);
```

---

## 🔌 APIs Externas Integradas

### 1. APIs de Datos Financieros

| API | Endpoint | Autenticación | Rate Limit |
|-----|----------|---------------|------------|
| pydolarvenezuela | Librería Python | Ninguna | Sin límite |
| pyvenezuela | Librería Python | Ninguna | Sin límite |
| Cotizave API | REST API | API Key | 1000 req/hora |
| Binance P2P | REST API | API Key | 1200 req/min |
| Mercado Libre | REST API | OAuth2 | 5000 req/día |

### 2. APIs de Noticias

| API | Endpoint | Autenticación | Costo |
|-----|----------|---------------|-------|
| NewsAPI | REST API | API Key | Gratis (100/día) |
| RSS Feeds | XML | Ninguna | Gratis |
| Web Scraping | HTML | Ninguna | Gratis |

### 3. APIs de Redes Sociales

| API | Endpoint | Autenticación | Costo |
|-----|----------|---------------|-------|
| Reddit API | REST API | OAuth2 | Gratis (60 req/min) |
| Twitter API | REST API | Bearer Token | Desde $100/mes |
| Facebook Graph | REST API | App Token | Gratis (limitado) |

### 4. APIs de IA

| API | Endpoint | Autenticación | Costo |
|-----|----------|---------------|-------|
| DeepSeek V4-Pro | REST API | API Key | Pay-per-use |
| OpenAI | REST API | API Key | Pay-per-use |
| Hugging Face | REST API | API Token | Gratis (limitado) |

### 5. APIs de Encuestas (NUEVO — Google)

| API | Librería | Autenticación | Costo | Uso |
|-----|----------|---------------|-------|-----|
| Google Sheets API | `gspread` | Service Account (OAuth2) | Gratis (60 req/min) | Leer respuestas de formularios |
| Google Forms | — | Vincular a Google Sheet | Gratis | Capturar respuestas (sin API directa) |
| Google Drive API | `google-auth` | Service Account | Gratis | Compartir/permisos de hojas |

---

## 🔐 Seguridad

### Autenticación y Autorización
```python
# src/security/

class SecurityManager:
    """
    Gestión de seguridad del sistema.
    
    Funciones:
    - Gestión de API keys (vault)
    - Autenticación de usuarios
    - Control de acceso
    - Encriptación de datos sensibles
    """
    
    def __init__(self):
        self.vault = SecretVault()
    
    async def get_api_key(self, service: str) -> str:
        """Obtiene API key del vault seguro"""
        pass
    
    async def validate_token(self, token: str) -> bool:
        """Valida token de autenticación"""
        pass
```

### Almacenamiento Seguro de Credenciales
```bash
# Variables de entorno (nunca en código)
export BCV_API_KEY="tu-api-key-aqui"
export BINANCE_API_KEY="tu-api-key-aqui"
export DEEPSEEK_API_KEY="tu-api-key-aqui"
export DATABASE_URL="postgresql://user:pass@localhost/db"
```

---

## 📊 Métricas del Sistema

### Métricas de Rendimiento
```python
# src/metrics/

class SystemMetrics:
    """
    Métricas de rendimiento del sistema.
    
    Métricas:
    - Tiempo de recolección de datos
    - Tiempo de procesamiento
    - Tiempo de análisis IA
    - Tasa de éxito de recolección
    - Tamaño de datos procesados
    - Costo de API acumulado
    """
    
    async def record_collection_time(self, source: str, duration: float):
        pass
    
    async def record_processing_time(self, stage: str, duration: float):
        pass
    
    async def record_api_cost(self, service: str, cost: float):
        pass
    
    async def get_dashboard_metrics(self) -> Dict:
        """Retorna métricas para el dashboard"""
        pass
```

### Monitoreo con Prometheus/Grafana
```yaml
# docker-compose.yml (fragmento)
services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
  
  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
```

---

## 🔄 Flujo de Datos

### Diagrama de Flujo Completo

```
┌─────────────────────────────────────────────────────────────────────┐
│                    FLUJO DE DATOS COMPLETO                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐                                                    │
│  │   SCHEDULE    │                                                    │
│  │  (Cron/Timer) │                                                    │
│  └──────┬───────┘                                                    │
│         │                                                             │
│         ▼                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐           │
│  │  COLLECT      │───▶│   PROCESS    │───▶│   STORE      │           │
│  │  (Fetch Data) │    │ (Clean/Norm) │    │ (Database)   │           │
│  └──────────────┘    └──────────────┘    └──────────────┘           │
│         │                      │                      │               │
│         │                      │                      │               │
│         ▼                      ▼                      ▼               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐           │
│  │  Raw Data     │    │ Clean Data   │    │ Stored Data  │           │
│  │  (JSON/CSV)   │    │ (DataFrame)  │    │ (PostgreSQL) │           │
│  └──────────────┘    └──────────────┘    └──────────────┘           │
│                                                                     │
│                                    │                                │
│                                    ▼                                │
│                           ┌──────────────┐                          │
│                           │   ANALYZE     │                          │
│                           │  (AI/ML)      │                          │
│                           └──────────────┘                          │
│                                    │                                │
│                                    ▼                                │
│                           ┌──────────────┐                          │
│                           │   INSIGHTS   │                          │
│                           │  (Reports)   │                          │
│                           └──────────────┘                          │
│                                    │                                │
│                          ┌─────────┼─────────┐                      │
│                          ▼         ▼         ▼                      │
│                    ┌──────────┐ ┌────────┐ ┌──────────┐            │
│                    │Dashboard │ │ Reports│ │  Alerts  │            │
│                    └──────────┘ └────────┘ └──────────┘            │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🐳 Despliegue con Docker

### Estructura de Contenedores

```yaml
# docker-compose.yml
version: '3.8'

services:
  # Servicio principal
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/economia_ve
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
    volumes:
      - ./data:/app/data
  
  # Dashboard Streamlit
  dashboard:
    build: .
    command: streamlit run src/dashboard/app.py
    ports:
      - "8501:8501"
    volumes:
      - ./data:/app/data
  
  # Base de datos PostgreSQL + TimescaleDB
  db:
    image: timescale/timescaledb:latest-pg14
    environment:
      POSTGRES_DB: economia_ve
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  # Cache Redis
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
  
  # Prometheus (monitoreo)
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./config/prometheus.yml:/etc/prometheus/prometheus.yml
  
  # Grafana (visualización de métricas)
  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin

volumes:
  postgres_data:
```

### Dockerfile

```dockerfile
# Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY . .

# Exponer puertos
EXPOSE 8000 8501

# Comando por defecto
CMD ["python", "main.py"]
```

---

## 🔧 Configuración del Sistema

### Archivo de Configuración
```python
# src/config.py

from pydantic import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Configuración del sistema"""
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/economia_ve"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # API Keys
    BCV_API_KEY: Optional[str] = None
    BINANCE_API_KEY: Optional[str] = None
    BINANCE_API_SECRET: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None
    NEWS_API_KEY: Optional[str] = None
    
    # Google (encuestas)
    GOOGLE_CREDENTIALS_PATH: Optional[str] = None  # Ruta al JSON de service account
    SURVEY_COLLECT_INTERVAL_MINUTES: int = 60      # Frecuencia de ingesta
    
    # Scheduling
    DOLLAR_COLLECT_INTERVAL_MINUTES: int = 5
    NEWS_COLLECT_INTERVAL_HOURS: int = 6
    SENTIMENT_ANALYSIS_HOUR: int = 22
    WEEKLY_REPORT_DAY: str = "sunday"
    WEEKLY_REPORT_HOUR: int = 8
    
    # Dashboard
    DASHBOARD_PORT: int = 8501
    API_PORT: int = 8000
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"

settings = Settings()
```

---

## 📈 Escalabilidad

### Estrategias de Escalabilidad

1. **Escalabilidad Horizontal**: Añadir más workers de recolección
2. **Escalabilidad Vertical**: Aumentar recursos de base de datos
3. **Caché Inteligente**: Redis para datos de alta frecuencia
4. **Procesamiento Asíncrono**: Colas de mensajes para tareas pesadas
5. **Base de Datos Read Replicas**: Para consultas del dashboard

### Límites y Umbrales

| Componente | Umbral | Acción |
|------------|--------|--------|
| Workers de recolección | > 80% CPU | Escalar horizontalmente |
| Base de datos | > 80% almacenamiento | Archivar datos antiguos |
| API IA | > 1000 req/día | Implementar cache |
| Memoria | > 80% uso | Optimizar queries |

---

## 🔍 Monitoreo y Observabilidad

### Stack de Monitoreo

```
┌─────────────────────────────────────────────────────────────┐
│                    MONITOREO DEL SISTEMA                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  Prometheus   │───▶│   Grafana    │    │   Alerting   │  │
│  │  (Métricas)   │    │(Dashboard)   │    │  (PagerDuty) │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Sentry     │    │   ELK Stack  │    │   Uptime     │  │
│  │  (Errores)   │    │   (Logs)     │    │  (Uptime)    │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Métricas Clave a Monitorear

1. **Disponibilidad del sistema** (uptime)
2. **Latencia de recolección de datos**
3. **Tasa de éxito de recolección**
4. **Costo acumulado de API**
5. **Errores por componente**
6. **Uso de recursos (CPU, RAM, Disco)**

---

## 📋 Resumen de Arquitectura

| Aspecto | Descripción |
|---------|-------------|
| **Tipo** | Modular monolith + Scheduler |
| **Lenguaje** | Python 3.10+ |
| **Base de Datos** | PostgreSQL + TimescaleDB (9 tablas ORMs, hypertables) |
| **Cache** | Redis (opcional) |
| **IA** | Cadena de 8 LLMs con fallback (LLM1..LLM8) |
| **Dashboard** | Streamlit (3 tabs: Inicio, Noticias, Encuestas) |
| **Encuestas** | Google Forms + Google Sheets API (gspread) |
| **Informes** | Semanal (IA) + periódicos diario→anual (MD + PDF) |
| **Despliegue** | Docker + Docker Compose |
| **Scheduler** | APScheduler (11 jobs) |
| **Tests** | 299 tests (pytest) |

---

**Documento generado como parte de la documentación técnica del proyecto Economía Venezuela.**
