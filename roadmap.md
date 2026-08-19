# Roadmap - Economía Venezuela

## 🗺️ Hoja de Ruta del Proyecto

Documento de planificación estratégica para el desarrollo de la herramienta de monitoreo económico de Venezuela. Define fases, hitos, entregables y cronograma.

---

## 📅 Vista General del Timeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ROADMAP ECONOMÍA VENEZUELA                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  FASE 1         FASE 2         FASE 3         FASE 4         FASE 5        │
│  Fundamentos    Recolección    Análisis       Visualización  Automatización │
│  [Semanas 1-4]  [Semanas 5-8]  [Semanas 9-12] [Semanas 13-16][Semanas 17-20]│
│      │              │              │              │              │            │
│      ▼              ▼              ▼              ▼              ▼            │
│  ┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐        │
│  │ 15%    │    │ 30%    │    │ 25%    │    │ 20%    │    │ 10%    │        │
│  │Progreso│    │Progreso│    │Progreso│    │Progreso│    │Progreso│        │
│  └────────┘    └────────┘    └────────┘    └────────┘    └────────┘        │
│                                                                              │
│  Línea de Tiempo: 20 semanas (5 meses)                                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Objetivos del Proyecto

### Objetivo General
Crear una herramienta automatizada de monitoreo y análisis de la economía venezolana que proporcione:
- Datos en tiempo real de múltiples fuentes
- Análisis macro y microeconómico con IA y econometría
- Dashboards interactivos para visualización
- Informes semanales automatizados
- Sistema de alertas tempranas

---

## 📦 Fase 1: Fundamentos (Semanas 1-4)

### Estado: ✅ COMPLETADA

#### Hitos Completados
- [x] Crear repositorio en GitHub
- [x] Configurar estructura de proyecto
- [x] Crear Docker Compose
- [x] Implementar modelos de datos
- [x] Crear módulo econométrico completo
- [x] Crear tests unitarios

---

## 📦 Fase 2: Recolección de Datos (Semanas 5-8)

### Estado: 🟡 EN PROGRESO

### Detalle de Collectors

#### 2.1 Collector BCV (Banco Central de Venezuela)

**Objetivo:** Obtener tasas de cambio oficiales e indicadores económicos

**Estrategia de Implementación:**

| Método | Prioridad | Librería/Herramienta | Datos |
|--------|-----------|---------------------|-------|
| API Comunitaria | 1️⃣ | bcv-api / bcv-exchange | Tasas USD, EUR |
| Librería Python | 2️⃣ | pyDolarVenezuela | Tasas múltiples |
| Scraping HTML | 3️⃣ | BeautifulSoup | Indicadores |
| Descarga Excel | 4️⃣ | pandas + openpyxl | Series históricas |

**Estructura del Collector:**

```text
src/collectors/bcv/
├── __init__.py
├── exchange_rates.py    # Tasas de cambio (pyDolarVenezuela)
├── indicators.py        # Indicadores económicos (scraping)
├── excel_downloader.py  # Descarga archivos Excel
└── utils.py             # Headers, timeouts, logging
```

**Implementación Sugerida:**

```python
# src/collectors/bcv/exchange_rates.py
from pyDolarVenezuela import Bcv
import pandas as pd
from datetime import datetime

class BCVCollector:
    """Colector de datos del Banco Central de Venezuela"""
    
    def __init__(self):
        self.bcv = Bcv()
    
    def get_exchange_rates(self) -> dict:
        """Obtiene tasas de cambio oficiales"""
        rates = self.bcv.get_rates()
        return {
            'usd': rates.get('USD'),
            'eur': rates.get('EUR'),
            'timestamp': datetime.now()
        }
    
    def get_historical_rates(self, days: int = 30) -> pd.DataFrame:
        """Obtiene tasas históricas"""
        # Implementar con descarga de Excel del BCV
        pass
```

**Indicadores a Obtener del BCV:**

| Indicador | Método | Frecuencia |
|-----------|--------|------------|
| Tasa USD | API comunitaria | Diaria |
| Tasa EUR | API comunitaria | Diaria |
| IPC (Inflación) | Excel | Mensual |
| Reservas | Scraping | Semanal |
| Base Monetaria | Excel | Mensual |
| Balanza Comercial | Excel | Trimestral |

---

#### 2.2 Collector BVC (Bolsa de Valores de Caracas)

**Objetivo:** Obtener datos del mercado accionario venezolano

**Estrategia de Implementación:**

| Método | Prioridad | Librería/Herramienta | Datos |
|--------|-----------|---------------------|-------|
| Yahoo Finance | 1️⃣ | yfinance | IBC, histórico |
| Scraping BVC | 2️⃣ | BeautifulSoup | Subíndices, detalle |
| ICE (pago) | 3️⃣ | API institucional | Datos premium |

**Estructura del Collector:**

```text
src/collectors/bvc/
├── __init__.py
├── yfinance_collector.py    # Yahoo Finance (recomendado)
├── scraper.py               # Scraping directo BVC
├── indicators.py            # Indicadores derivados
└── utils.py                 # Headers, logging
```

**Implementación Sugerida:**

```python
# src/collectors/bvc/yfinance_collector.py
import yfinance as yf
import pandas as pd
from datetime import datetime

class BVCCollector:
    """Colector de datos de la Bolsa de Valores de Caracas"""
    
    def get_ibc_data(self) -> dict:
        """Obtiene el IBC desde Yahoo Finance"""
        ticker = yf.Ticker("IBC.CR")
        
        today = ticker.history(period="1d")
        hist = ticker.history(period="1mo")
        
        return {
            'ibc': today['Close'].iloc[-1] if not today.empty else None,
            'volume': today['Volume'].iloc[-1] if not today.empty else None,
            'high_52w': ticker.info.get('fiftyTwoWeekHigh'),
            'low_52w': ticker.info.get('fiftyTwoWeekLow'),
            'historical': hist['Close'].tolist(),
            'timestamp': datetime.now()
        }
    
    def get_historical_ibc(self, period: str = "1y") -> pd.DataFrame:
        """Obtiene histórico del IBC"""
        ticker = yf.Ticker("IBC.CR")
        return ticker.history(period=period)
```

**Indicadores de la BVC:**

| Indicador | Fuente | Utilidad |
|-----------|--------|----------|
| IBC | Yahoo Finance | Termómetro del mercado |
| IBC Industrial | Scraping | Salud sector productivo |
| IBC Financiero | Scraping | Salud sector bancario |
| Capitalización | Yahoo Finance | Tamaño del mercado |
| Volumen | Yahoo Finance | Liquidez |

---

#### 2.3 Collector Dólar Paralelo

**Objetivo:** Obtener precio del dólar en mercado no regulado

**Estrategia:**

| Fuente | Método | Datos |
|--------|--------|-------|
| DólarToday | Scraping | Tasa paralela |
| Monitor Dólar | Scraping | Múltiples monitores |
| Binance P2P | API oficial | Precio USDT/VES |

**Implementación:**

```python
# src/collectors/dolar/parallel.py
import requests
from bs4 import BeautifulSoup

class DolarParaleloCollector:
    """Colector de dólar paralelo"""
    
    def get_dolartoday(self) -> dict:
        """Obtiene tasa de DólarToday"""
        url = 'https://dolartoday.com/'
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        # Parsear y extraer tasa
        pass
    
    def get_binance_p2p(self) -> dict:
        """Obtiene precio Binance P2P"""
        url = 'https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search'
        # Implementar con API de Binance
        pass
```

---

#### 2.4 Collector Noticias

**Objetivo:** Recopilar noticias económicas de portales venezolanos

**Fuentes:**

| Portal | URL | Método |
|--------|-----|--------|
| El Nacional | elnacional.com | RSS + Scraping |
| TalCual | talcualdigital.com | RSS |
| Efecto Cocuyo | efectococuyo.com | RSS |
| Reuters | reuters.com | RSS |

---

#### 2.5 Collector Redes Sociales

**Objetivo:** Obtener sentimiento de ciudadanos

| Plataforma | API | Costo |
|------------|-----|-------|
| Reddit | PRAW (OAuth2) | Gratis |
| Twitter/X | API v2 | $100/mes |
| Facebook | Scraping | Gratis (limitado) |

---

### Hitos Fase 2

#### Semana 5: Collectors de Dólar
- [ ] Implementar `DolarCollector` con pyDolarVenezuela
- [ ] Implementar `DolarParaleloCollector` con DólarToday
- [ ] Conectar con Binance P2P API
- [ ] Implementar cálculo de spreads
- [ ] Crear tests

**Entregable**: Collectors de dólar funcionales

#### Semana 6: Collector BCV
- [ ] Implementar `BCVCollector` con pyDolarVenezuela
- [ ] Implementar scraping de indicadores
- [ ] Implementar descarga de Excel
- [ ] Crear tests

**Entregable**: Collector BCV funcional

#### Semana 7: Collector BVC
- [ ] Implementar `BVCCollector` con yfinance
- [ ] Implementar scraping de subíndices
- [ ] Crear tests

**Entregable**: Collector BVC funcional

#### Semana 8: Collectors de Noticias y Redes Sociales
- [ ] Implementar `NewsCollector`
- [ ] Implementar `SocialCollector`
- [ ] Crear tests

**Entregable**: Todos los collectors funcionales

---

### Dependencias Fase 2

```txt
# Fase 2 - Data Collection
pyDolarVenezuela==0.2.0
bcv-exchange==0.1.0
yfinance==0.2.31
praw==7.7.1
tweepy==4.14.0
feedparser==6.0.11
beautifulsoup4==4.12.2
requests==2.31.0
```

---

## 📦 Fase 3: Análisis (Semanas 9-12)

### Estado: ✅ COMPLETADA (Módulo Econométrico)

#### Hitos Completados
- [x] Módulo de estacionariedad (ADF, KPSS)
- [x] Pronóstico SARIMA para inflación
- [x] Análisis VECM para mercado cambiario
- [x] Modelos GARCH para volatilidad
- [x] Diagnósticos de residuos
- [x] Regresión Newey-West

---

## 📦 Fase 4: Visualización (Semanas 13-16)

### Estado: ⏳ PENDIENTE

#### Hitos

##### Semana 13: Dashboard Streamlit
- [ ] Crear app Streamlit base
- [ ] Implementar tarjetas de métricas
- [ ] Crear gráficos de series temporales

##### Semana 14: Gráficos Avanzados
- [ ] Gráficos Plotly interactivos
- [ ] Pronósticos SARIMA visualizados
- [ ] Mapa de volatilidad GARCH

##### Semana 15: Sistema de Alertas
- [ ] Implementar `AlertManager`
- [ ] Notificaciones Telegram
- [ ] Alertas por email

##### Semana 16: Informes Automáticos
- [ ] Generación PDF
- [ ] Generación Markdown
- [ ] Informe semanal con IA

---

## 📦 Fase 5: Automatización (Semanas 17-20)

### Estado: ⏳ PENDIENTE

#### Hitos

##### Semana 17: Scheduler
- [ ] Implementar `TaskScheduler`
- [ ] Configurar APScheduler

##### Semana 18: CI/CD
- [ ] GitHub Actions workflow
- [ ] Tests automatizados

##### Semana 19: Despliegue
- [ ] Servidor en la nube
- [ ] Docker Compose producción

##### Semana 20: Documentación
- [ ] Guía de usuario
- [ ] Video demo

---

## 📊 Presupuesto Estimado

| Fase | Costo | Notas |
|------|-------|-------|
| Fase 1: Fundamentos | $0 | Completada |
| Fase 2: Recolección | $0-20 | APIs gratuitas |
| Fase 3: Análisis | $50-100 | API DeepSeek |
| Fase 4: Visualización | $0 | Local |
| Fase 5: Despliegue | $30-65 | Servidor |
| **Total** | **$80-185** | |

---

## 📈 Progreso Actual

```
FASE 1: Fundamentos    ████████████████████ 100% ✅
FASE 2: Recolección    ████░░░░░░░░░░░░░░░░  20% 🟡
FASE 3: Análisis       ████████████████████ 100% ✅
FASE 4: Visualización  ░░░░░░░░░░░░░░░░░░░░   0% ⏳
FASE 5: Automatización ░░░░░░░░░░░░░░░░░░░░   0% ⏳

TOTAL: 44%
```

---

## 📋 Próximos Pasos Inmediatos

### Prioridad Alta
1. **Implementar Collector BCV** con pyDolarVenezuela
2. **Implementar Collector BVC** con yfinance
3. **Implementar Collector Dólar Paralelo**

### Prioridad Media
4. **Integrar collectors en pipeline principal**
5. **Crear tests para cada collector**
6. **Documentar APIs de cada collector**

### Prioridad Baja
7. **Implementar collector de noticias**
8. **Implementar collector de redes sociales**

---

**Roadmap actualizado: Agosto 2025**
**Versión: 2.0**
**Última actualización: Con collectors BCV y BVC**
