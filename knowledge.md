# Knowledge Base - Economía Venezuela

## 📚 Base de Conocimiento del Proyecto

Este documento contiene la base de conocimiento fundamental para el análisis de la economía venezolana. Incluye conceptos económicos relevantes, contexto histórico, fuentes de datos y terminología específica.

---

## 🇻🇪 Contexto Histórico Económico de Venezuela

### 1. Era Petrolera (1920-1999)

| Período | Evento Clave | Impacto Económico |
|---------|--------------|-------------------|
| 1920-1950 | Descubrimiento del petróleo | Transformación de agrario a petrolero |
| 1960-1970 | Boom petrolero | Crecimiento del PIB > 6% anual |
| 1973 | Crisis del petróleo | Triple ingreso petrolero |
| 1980-1990 | Caída de precios | Ajuste económico, deuda externa |
| 1994-1999 | crisis bancaria | Liberalización parcial |

### 2. Era Chavista (1999-2013)

| Período | Evento Clave | Impacto Económico |
|---------|--------------|-------------------|
| 1999-2003 | Controles cambiarios | Mercado paralelo emergence |
| 2003-2008 | Control de precios | Desabastecimiento crónico |
| 2008-2012 | Boom petrolero II | Gasto público masivo |
| 2012-2013 | Fallecimiento Chávez | Incertidumbre económica |

### 3. Era Post-Chavista (2013-Presente)

| Período | Evento Clave | Impacto Económico |
|---------|--------------|-------------------|
| 2013-2017 | Hiperinflación | Colapso del bolívar |
| 2017-2019 | Sanciones US | Caída del PIB > 60% |
| 2019-2021 | Pandemia | Recesión profunda |
| 2021-2023 | Dolarización de facto | Estabilización parcial |
| 2023-2026 | Reformas económicas | Recuperación lenta |

---

## 📊 Conceptos Económicos Clave

### 1. Tipo de Cambio

#### Tipos de Cambio en Venezuela
```
┌─────────────────────────────────────────────────────────────────┐
│                  MERCADO CAMIARIO VENEZOLANO                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   OFICIAL    │  │   PARALELO   │  │  BINANCE P2P │          │
│  │   (BCV)      │  │  (DólarToday)│  │              │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  Tasa Oficial: ~36.5 Bs/USD (fijo)                             │
│  Tasa Paralelo: ~50-100 Bs/USD (fluctuante)                    │
│  Binance P2P: ~45-90 Bs/USD (mercado libre)                    │
│                                                                  │
│  SPREAD = (Paralelo - Oficial) / Oficial * 100                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### Definiciones
- **Tipo de Cambio Oficial**: Fijado por el BCV, used para transacciones formales
- **Tipo de Cambio Paralelo**: Precio en mercado no regulado (DólarToday,Monitor)
- **Binance P2P**: Precio del dólar en plataforma de trading peer-to-peer
- **Spread**: Diferencia porcentual entre oficial y paralelo

### 2. Inflación

#### Índices de Inflación
| Índice | Descripción | Período |
|--------|-------------|---------|
| IPC (Índice de Precios al Consumidor) | Precio de canasta básica | Mensual |
| IPCC | IPC de alimentos | Mensual |
| Índice de Precios al Productor | Costos de producción | Trimestral |
| Deflactor del PIB | Inflación generalizada | Anual |

#### Fórmulas Clave
```
Inflación Mensual = ((IPC Mes Actual - IPC Mes Anterior) / IPC Mes Anterior) * 100

Inflación Anual = ((IPC Mes Actual - IPC Mismo Mes Año Anterior) / IPC Mismo Mes Año Anterior) * 100

Inflación Acumulada = Productorio(1 + inflación_mensual_i) - 1
```

### 3. Producto Interno Bruto (PIB)

#### Componentes del PIB Venezolano
```
PIB Total = PIB Petrolero + PIB No Petrolero

PIB No Petrolero = Consumo + Inversión + Gasto Público + (Exportaciones - Importaciones)

Donde:
- Consumo: Gasto de hogares
- Inversión: Formación bruta de capital
- Gasto Público: Gasto del gobierno
- Exportaciones: Petróleo + No petrolero
- Importaciones: Bienes y servicios
```

### 4. Reservas Internacionales

#### Composición de Reservas
```
┌─────────────────────────────────────────────────────────────┐
│               RESERVAS INTERNACIONALES                      │
├─────────────────────────────────────────────────────────────┤
│  ORO (60-70%)                                               │
│  DIVISAS (20-30%)                                           │
│  DERECHOS ESPECIALES (5-10%)                                │
└─────────────────────────────────────────────────────────────┘
```

### 5. Producción Petrolera

#### Datos Clave de PDVSA
| Métrica | 2013 | 2023 | 2025 (Est.) |
|---------|------|------|-------------|
| Producción (barriles/día) | 2.8M | 0.8M | 1.0M |
| Reservas (billones barriles) | 297 | 304 | 304 |

---

## 🗺️ FUENTES DE DATOS DETALLADAS

### 1. BANCO CENTRAL DE VENEZUELA (BCV)

#### ⚠️ Importante: No hay API oficial
El BCV no ofrece una API pública. Se requiere scraping o usar herramientas comunitarias.

#### Opción A: APIs Comunitarias (Recomendado)

| Herramienta | Tecnología | Qué obtienes | Enlace |
|-------------|------------|--------------|--------|
| **BCV-Tasa-Oficial** | Python + FastAPI | Tasas USD y EUR en JSON | github.com/StudiosDanilIs/BCV-Tasa-Oficial |
| **bcv-api** (rafnixg) | Python | Tasas de cambio actuales | github.com/rafnixg/bcv-api |
| **tipo-cambio** (oariasz) | Python | USD, EUR, CNY, RUB, TRY | github.com/oariasz/tipo-cambio |
| **bcv_scraper** (ivanovertime) | Python + FastAPI | Tasas en JSON | github.com/ivanovertime/bcv_scraper |

**Ejemplo de uso con bcv-api:**
```python
import requests

response = requests.get('https://bcv-api.herokuapp.com/api/v1/rates')
data = response.json()
print(f"Dólar oficial: {data['usd']} Bs/USD")
print(f"Euro oficial: {data['eur']} Bs/EUR")
```

#### Opción B: Librerías Python

| Librería | Instalación | Uso básico |
|----------|-------------|------------|
| **bcv-exchange** | `pip install bcv-exchange` | `from bcv_exchange import Bcv; bcv = Bcv(); print(bcv.get_rate('USD'))` |
| **pyDolarVenezuela** | `pip install pyDolarVenezuela` | `import pyDolarVenezuela as pdv; print(pdv.Bcv().get_rates())` |

#### Opción C: Scraping Directo

**Estructura del sitio BCV:**
- Tasas de cambio: `<div id="dolar">` en la portada
- Indicadores económicos: Sección "Estadísticas" → "Indicadores Económicos"
- Datos históricos: Archivos Excel (.xls) descargables

**Ejemplo de scraping:**
```python
import requests
from bs4 import BeautifulSoup
import re

url = 'https://www.bcv.org.ve/'
response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')

# Buscar el elemento con la tasa
dolar_element = soup.find('div', {'id': 'dolar'})
if dolar_element:
    match = re.search(r'(\d+[\.,]?\d*)', dolar_element.text)
    if match:
        tasa = float(match.group(1).replace(',', '.'))
        print(f"Tasa USD: {tasa} Bs/USD")
```

#### Opción D: Scrapers Comunitarios GitHub

| Repositorio | Qué extrae | Tecnología |
|-------------|------------|------------|
| **fquivera/scraper-bcv** | Tasas de cambio (scraper defensivo) | Python |
| **pcamilo89/bcv-scraper** | USD y EUR desde HTML y Excel | Python |
| **Guerrero85/Tasa-BCV** | Tasas de cambio + INPC | C# |
| **AlexR1712/bcv-extractor** | Tasas compra/venta + Excel | Python |

**Recomendación:** Usar `fquivera/scraper-bcv` (diseñado con tolerancia a cambios en HTML).

#### Estructura de Colector BCV Sugerida

```text
src/collectors/bcv/
├── __init__.py
├── exchange_rates.py    # Usa pyDolarVenezuela o bcv-exchange
├── indicators.py        # Scraping de indicadores económicos
├── excel_downloader.py  # Descarga y procesa archivos Excel
└── utils.py             # Funciones comunes
```

#### Indicadores Disponibles en BCV

| Indicador | Disponibilidad | Método |
|-----------|----------------|--------|
| Tasa de cambio USD | API comunitaria | Fácil |
| Tasa de cambio EUR | API comunitaria | Fácil |
| IPC (Inflación) | Excel descargable | Scraping |
| Reservas internacionales | Semanal | Scraping |
| Base monetaria (M2) | Mensual | Scraping |
| Balanza de pagos | Trimestral | Excel |

---

### 2. BOLSA DE VALORES DE CARACAS (BVC)

#### Datos Relevantes de la BVC

| Indicador | Descripción | Utilidad |
|-----------|-------------|----------|
| **Índice Bursátil Caracas (IBC)** | Índice principal, 16 mayores empresas | Termómetro del mercado |
| **IBC Industrial** | Subíndice sector industrial | Salud sector productivo |
| **IBC Financiero** | Subíndice sector financiero | Salud sector bancario |
| **Capitalización Bursátil** | Valor total de mercado | Tamaño del mercado |
| **Monto Efectivo Negociado** | Volumen en bolívares | Liquidez del mercado |
| **Precios de acciones** | Cotizaciones individuales | Análisis microeconómico |

#### Opción A: Yahoo Finance (Recomendado para empezar)

**Librería:** `yfinance`

```python
# src/collectors/bvc/yfinance_collector.py
import yfinance as yf
import pandas as pd

def get_ibc_data():
    """Obtiene el IBC desde Yahoo Finance"""
    ticker = yf.Ticker("IBC.CR")
    
    # Datos del día
    today = ticker.history(period="1d")
    
    # Datos históricos (últimos 30 días)
    hist = ticker.history(period="1mo")
    
    return {
        'current_price': today['Close'].iloc[-1] if not today.empty else None,
        'volume': today['Volume'].iloc[-1] if not today.empty else None,
        'high_52w': ticker.info.get('fiftyTwoWeekHigh'),
        'low_52w': ticker.info.get('fiftyTwoWeekLow'),
        'historical': hist['Close'].tolist(),
        'dates': hist.index.tolist()
    }
```

**Ventajas:** No scraping, estable, datos históricos
**Desventajas:** Solo IBC, no acciones individuales

#### Opción B: Scraping Directo de la BVC

**URL:** https://www.bolsadecaracas.com/

```python
# src/collectors/bvc/scraper.py
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

def scrape_bvc_home():
    """Scraping de la portada de la BVC"""
    url = 'https://www.bolsadecaracas.com/'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Selectores hipotéticos (ajustar tras inspeccionar HTML)
    ibc_element = soup.find('span', {'id': 'ibc-value'})
    
    return {
        'ibc': float(re.sub(r'[^\d.]', '', ibc_element.text)) if ibc_element else None,
        'timestamp': datetime.now()
    }
```

#### Opción C: ICE (Intercontinental Exchange)

Para uso profesional con datos institucionales de alta calidad (servicio de pago).

#### Estructura de Colector BVC Sugerida

```text
src/collectors/bvc/
├── __init__.py
├── yfinance_collector.py    # Yahoo Finance (recomendado)
├── scraper.py               # Scraping directo
├── indicators.py            # Indicadores derivados
└── utils.py                 # Headers, timeouts, logging
```

#### Modelo de Datos BVC

```python
from pydantic import BaseModel
from datetime import datetime

class BVCData(BaseModel):
    timestamp: datetime
    ibc: float
    ibc_industrial: float | None = None
    ibc_financiero: float | None = None
    market_cap_usd: float | None = None
    traded_volume_bs: float | None = None
    operations_count: int | None = None
    top_gainers: list[dict] = []
    top_losers: list[dict] = []
```

#### Uso en Análisis Econométrico

| Modelo | Variable BVC | Relación |
|--------|--------------|----------|
| VECM | IBC vs. Dólar paralelo | ¿El mercado anticipa devaluaciones? |
| GARCH | Volatilidad del IBC | Medir incertidumbre financiera |
| Regresión | IBC vs. Petróleo | Correlación con commodities |
| Nowcasting | Capitalización vs. PIB | Estimar PIB en tiempo real |

---

### 3. OTROS PROVEEDORES DE DATOS

#### DólarToday
```
URL: https://dolartoday.com
Datos: Tasa paralela, evolución histórica
API: No oficial (scraping)
```

#### Binance P2P
```
URL: https://p2p.binance.com
Datos: Precio USDT en VES, volumen
API: Oficial (REST API)
```

#### Mercado Libre
```
URL: https://www.mercadolibre.com.ve
Datos: Precios de productos de referencia
Método: Web scraping
```

---

### 4. FUENTES DE NOTICIAS

#### Portales Venezolanos
```
- El Nacional: https://www.elnacional.com
- TalCual: https://talcualdigital.com
- Efecto Cocuyo: https://efectococuyo.com
- Runrunes: https://runrunes.org
- El Pitazo: https://elpitazo.net
```

#### Portales Internacionales
```
- Reuters: https://www.reuters.com
- Bloomberg: https://www.bloomberg.com
- Financial Times: https://www.ft.com
```

### 5. REDES SOCIALES

#### Reddit
```
Subreddits: r/vzla, r/vzlaconomics
API: Reddit API (OAuth2)
Límites: 60 requests/minuto
```

#### Twitter/X
```
Cuentas: @BCVOficial, @DolarToday
API: Twitter API v2 (requiere suscripción)
```

---

## 💱 Canasta Básica y Poder Adquisitivo

### Canasta Básica Alimentaria (2025 estimado)

| Producto | Cantidad | Precio (Bs) | Precio (USD) |
|----------|----------|-------------|--------------|
| Arroz | 3 kg | 450 | $12.50 |
| Harina de maíz | 3 kg | 540 | $15.00 |
| Pasta | 2 kg | 360 | $10.00 |
| Aceite vegetal | 1 litro | 300 | $8.33 |
| Azúcar | 2 kg | 240 | $6.67 |
| Pollo | 3 kg | 1,800 | $50.00 |
| Carne de res | 2 kg | 3,000 | $83.33 |
| **TOTAL** | - | **~13,230** | **~$367.50** |

### Salario Mínimo vs Canasta Básica

```
Salario Mínimo 2025: ~130 Bs ($3.61)
Canasta Básica: ~13,230 Bs ($367.50)
Déficit: -99.0%
```

---

## 📊 Métodos de Análisis

### 1. Análisis de Tendencias
```
- Regresión Lineal
- Media Móvil (SMA)
- MACD
- RSI
- Bollinger Bands
```

### 2. Análisis de Sentimiento
```
Pipeline:
1. Recolección (Reddit, Twitter, Noticias)
2. Pre-procesamiento (Limpieza, Tokenización)
3. Análisis (DeepSeek, BERT, VADER)
4. Clasificación (Positivo/Neutro/Negativo)
5. Agregación y tendencia
```

### 3. Modelos Predictivos
```
- ARIMA/SARIMA (series temporales)
- VECM (cointegración)
- GARCH (volatilidad)
- Prophet (estacionalidad)
- LSTM (patrones complejos)
```

---

## ⚠️ Factores de Riesgo

| Riesgo | Probabilidad | Impacto | Señales |
|--------|--------------|---------|---------|
| Hiperinflación | Media | Crítico | IPC > 20% mensual |
| Default de deuda | Media | Alto | spreads > 500 pbs |
| Colapso petrolero | Baja | Crítico | Producción < 0.5M bbl/d |
| Sanciones adicionales | Alta | Alto | Anuncios políticos |

---

## 📋 Checklist de Implementación

### Fase 1: Fundamentos
- [x] Configurar proyecto base
- [x] Implementar modelos de datos
- [ ] Configurar base de datos
- [ ] Crear collector BCV (pyDolarVenezuela)

### Fase 2: Recolección
- [ ] Implementar collector BVC (yfinance)
- [ ] Implementar collector DólarToday
- [ ] Implementar collector Binance P2P
- [ ] Implementar collector Noticias
- [ ] Implementar collector Mercado Libre

### Fase 3: Procesamiento
- [ ] Pipeline de limpieza
- [ ] Normalización de datos
- [ ] Almacenamiento persistente

### Fase 4: Análisis
- [x] Módulo econométrico (SARIMA, VECM, GARCH)
- [ ] Análisis de sentimiento
- [ ] Detección de tendencias

### Fase 5: Visualización
- [ ] Dashboard Streamlit
- [ ] Sistema de alertas
- [ ] Informes automáticos

### Fase 6: Automatización
- [ ] Scheduler de tareas
- [ ] GitHub Actions

---

**Base de conocimiento actualizada: Agosto 2025**
**Última revisión: Con métodos de recolección BCV y BVC**
