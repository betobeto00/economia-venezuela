# Roadmap - Economía Venezuela

## 🗺️ Hoja de Ruta del Proyecto

---

## 📅 Estado Actual

```
FASE 1: Fundamentos    ████████████████████ 100% ✅
FASE 2: Recolección    ████░░░░░░░░░░░░░░░░  20% 🟡
FASE 3: Análisis       ████████████████████ 100% ✅
FASE 4: Visualización  ░░░░░░░░░░░░░░░░░░░░   0% ⏳
FASE 5: Automatización ░░░░░░░░░░░░░░░░░░░░   0% ⏳

TOTAL: 44%
```

---

## 📦 Fase 2: Recolección de Datos (Semanas 5-8)

### Estado: 🟡 EN PROGRESIO

### Prioridad de Implementación

#### 🔴 Prioridad 1 (Inmediato - 2 semanas)

| # | Collector | Fuente | Librería | Estado |
|---|-----------|--------|----------|--------|
| 1 | `bcv_collector.py` | BCV | pyDolarVenezuela | ⏳ Pendiente |
| 2 | `ovf_collector.py` | OVF | BeautifulSoup | ⏳ Pendiente |
| 3 | `worldbank_collector.py` | Banco Mundial | wbgapi | ⏳ Pendiente |
| 4 | `bvc_collector.py` | BVC/Yahoo | yfinance | ⏳ Pendiente |
| 5 | `binance_collector.py` | Binance P2P | API oficial | ⏳ Pendiente |

#### 🟡 Prioridad 2 (Corto plazo - 1 mes)

| # | Collector | Fuente | Librería | Estado |
|---|-----------|--------|----------|--------|
| 6 | `ine_collector.py` | INE | Scraping | ⏳ Pendiente |
| 7 | `opec_collector.py` | OPEP | API/Scraping | ⏳ Pendiente |
| 8 | `rss_collector.py` | Noticias VE | feedparser | ⏳ Pendiente |
| 9 | `imf_collector.py` | FMI | API IMF | ⏳ Pendiente |

#### 🟢 Prioridad 3 (Mediano plazo - 2 meses)

| # | Collector | Fuente | Librería | Estado |
|---|-----------|--------|----------|--------|
| 10 | `cepal_collector.py` | CEPAL | Scraping | ⏳ Pendiente |
| 11 | `reddit_collector.py` | Reddit | PRAW | ⏳ Pendiente |
| 12 | `twitter_collector.py` | Twitter/X | Tweepy | ⏳ Pendiente |
| 13 | `seniat_collector.py` | SENIAT | Scraping | ⏳ Pendiente |

---

## 📦 Fase 3: Análisis (Semanas 9-12)

### Estado: ✅ COMPLETADA

- [x] Módulo econométrico (SARIMA, VECM, GARCH)
- [x] Pruebas de estacionariedad
- [x] Diagnósticos de residuos
- [x] Regresión Newey-West

### Mejoras Sugeridas (Post-Review)

| Mejora | Descripción | Prioridad |
|--------|-------------|-----------|
| Sistema de confiabilidad | Pesos por fuente de datos | Alta |
| Quiebres estructurales | Detección con CUSUM/Chow | Media |
| Manejo de errores | Retry con tenacity | Alta |
| Validación de datos | Entradas NaN, series vacías | Alta |

---

## 📦 Fase 4: Visualización (Semanas 13-16)

### Estado: ⏳ PENDIENTE

#### Dashboard Mínimo Viable

| Componente | Descripción | Estado |
|------------|-------------|--------|
| Tasas de cambio | Oficial y paralelo en tiempo real | ⏳ |
| Gráfico IBC | Evolución del índice bursátil | ⏳ |
| Tabla macro | Indicadores clave | ⏳ |
| Análisis multi-fuente | Dispersión de fuentes | ⏳ |

---

## 📦 Fase 5: Automatización (Semanas 17-20)

### Estado: ⏳ PENDIENTE

---

## 🔧 Mejoras Estratégicas (Post-Review)

### 1. Sistema de Confiabilidad de Fuentes

```python
# Implementar en src/analyzers/data_validation.py
source_confidence = {
    "BCV": 0.7,           # Oficial, puede tener sesgo
    "OVF": 0.9,           # Independiente, alta credibilidad
    "FMI": 0.85,          # Internacional
    "Banco Mundial": 0.85,
    "UCAB": 0.8           # Académico
}
```

### 2. Detección de Quiebres Estructurales

```python
# Crear src/analyzers/econometric/breaks.py
- Prueba de Chow
- Test de CUSUM
- Detección de cambios de régimen
```

### 3. Informe Ejecutivo con IA

```python
# Usar DeepSeek V4-Pro para generar resúmenes
- Resumen semanal automatizado
- Lenguaje natural
- Recomendaciones
```

### 4. Manejo de Errores Robusto

```python
# Implementar en todos los collectors
from tenacity import retry, stop_after_attempt

@retry(stop=stop_after_attempt(3))
def fetch_data():
    # Lógica de recolección
    pass
```

---

## 📊 Dependencias Actualizadas

```txt
# Core
fastapi==0.109.0
uvicorn==0.25.0
pydantic==2.5.3
pydantic-settings==2.1.0

# Venezuela
pydolarvenezuela==0.2.0
pyvenezuela==0.1.0
bcv-exchange==0.1.0

# Internacional
wbgapi==1.0.1
yfinance==0.2.31
pandas-datareader==0.10.0

# Scraping
requests==2.31.0
beautifulsoup4==4.12.2
playwright==1.41.0
selenium==4.17.0
feedparser==6.0.11

# Social
tweepy==4.14.0
praw==7.7.1

# Datos
pandas==2.1.4
numpy==1.26.2
openpyxl==3.1.2

# Econometría
statsmodels==0.14.1
arch==6.3.0
linearmodels==5.3
scipy==1.12.0

# Resiliencia
tenacity==8.2.3
```

---

## 📋 Próximos Pasos Inmediatos

### Semana 5 (Actual)

1. **Implementar `bcv_collector.py`**
   ```python
   from pyDolarVenezuela import Bcv
   
   class BCVCollector:
       def get_rates(self):
           bcv = Bcv()
           return bcv.get_rates()
   ```

2. **Implementar `ovf_collector.py`**
   ```python
   # Scraping de observatoriodefinanzas.org
   # Extraer series de inflación y tipo de cambio
   ```

3. **Implementar `worldbank_collector.py`**
   ```python
   import wbgapi as wb
   
   class WorldBankCollector:
       def get_gdp(self):
           return wb.data.DataFrame('NY.GDP.MKTP.CD', countries='VEN')
   ```

4. **Implementar tests básicos**
   ```python
   def test_bcv_collector():
       collector = BCVCollector()
       rates = collector.get_rates()
       assert 'USD' in rates
       assert rates['USD'] > 0
   ```

---

## 📈 Métricas de Progreso

| KPI | Meta | Actual | Estado |
|-----|------|--------|--------|
| Collectors implementados | 13 | 0 | ⏳ |
| Tests unitarios | > 80% | ~20% | 🟡 |
| Cobertura de fuentes | 10+ | 0 | ⏳ |
| Documentación | 100% | 95% | ✅ |

---

## 🏆 Criterios de Éxito

### Éxito Técnico
- [ ] Sistema ejecutándose 99% del tiempo
- [ ] Latencia de datos < 5 minutos
- [ ] Cobertura de tests > 80%
- [ ] Manejo de errores robusto

### Éxito de Datos
- [ ] 10+ fuentes de datos activas
- [ ] Validación multi-fuente funcionando
- [ ] Datos actualizados diariamente

### Éxito de Usuario
- [ ] Dashboard intuitivo
- [ ] Informes claros y accionables
- [ ] Alertas relevantes

---

**Roadmap actualizado: Agosto 2025**
**Versión: 4.0**
**Incluye: Mejoras sugeridas en review**
