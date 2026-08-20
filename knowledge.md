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

```
┌─────────────────────────────────────────────────────────────────┐
│                  MERCADO CAMBIO VENEZOLANO                      │
├─────────────────────────────────────────────────────────────────┤
│  OFICIAL (BCV)    PARALELO (DólarToday)    BINANCE P2P         │
│  ~36.5 Bs/USD     ~50-100 Bs/USD          ~45-90 Bs/USD       │
│                                                                  │
│  SPREAD = (Paralelo - Oficial) / Oficial * 100                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Inflación

| Índice | Descripción | Período |
|--------|-------------|---------|
| IPC (INPC) | Índice Nacional de Precios al Consumidor | Mensual |
| IPCC | IPC de alimentos | Mensual |
| IPP | Índice de Precios al Productor | Trimestral |

### 3. Producto Interno Bruto (PIB)

```
PIB Total = PIB Petrolero + PIB No Petrolero
PIB No Petrolero = Consumo + Inversión + Gasto Público + (Exportaciones - Importaciones)
```

### 4. Producción Petrolera

| Métrica | 2013 | 2023 | 2025 (Est.) |
|---------|------|------|-------------|
| Producción (barriles/día) | 2.8M | 0.8M | 1.0M |
| Reservas (billones barriles) | 297 | 304 | 304 |

---

## 🏛️ FUENTES DE DATOS INSTITUCIONALES

### 1. ENTES OFICIALES NACIONALES (Canal Oficial)

Son la base del sistema. Publican la información que el Estado declara como oficial. **Es crucial contrastarla con fuentes independientes.**

#### 1.1 Banco Central de Venezuela (BCV)
**URL:** https://www.bcv.org.ve

| Categoría | Indicadores | Frecuencia |
|-----------|-------------|------------|
| **Tasas de Cambio** | USD, EUR, CNY | Diaria |
| **Monetarios** | Base monetaria (M0), Liquidez (M1, M2), Reservas | Semanal/Mensual |
| **Precios** | INPC (Inflación) | Mensual |
| **Cuentas Nacionales** | PIB trimestral y anual | Trimestral |
| **Balanza de Pagos** | Comercio exterior, Deuda externa | Trimestral |

**Métodos de Extracción:**
- Web scraping del portal de estadísticas
- Descarga de archivos PDF/Excel
- Librerías: `pyvenezuela`, `pydolarvenezuela`

#### 1.2 Instituto Nacional de Estadística (INE)
**URL:** https://www.ine.gov.ve

| Categoría | Indicadores |
|-----------|-------------|
| **Demográficos** | Censos de población y vivienda |
| **Laborales** | Encuestas de hogares: Empleo, desempleo, ingresos |
| **Vitales** | Natalidad, mortalidad, migración |

**Método:** Descarga de bases de datos y reportes en PDF/Excel

#### 1.3 Ministerio del Poder Popular de Economía y Finanzas (MPPEF)
**URL:** https://www.mppef.gob.ve

| Categoría | Indicadores |
|-----------|-------------|
| **Fiscal** | Ejecución presupuestaria |
| **Finanzas Públicas** | Deuda del gobierno central |

**Método:** Web scraping y descarga de reportes financieros

#### 1.4 Servicio Nacional Integrado de Administración Aduanera y Tributaria (SENIAT)
**URL:** https://www.seniat.gob.ve

| Categoría | Indicadores |
|-----------|-------------|
| **Recaudación** | ISLR, IVA, rentas aduaneras |

**Método:** Web scraping de boletines de prensa y reportes de gestión

#### 1.5 Superintendencia Nacional de Valores (SUNAVAL)
**URL:** https://www.sunaval.gob.ve

| Categoría | Indicadores |
|-----------|-------------|
| **Mercado de Capitales** | Capitalización bursátil, monto de transacciones |
| **Regulación** | Autorizaciones de emisiones, evolución del IBC |

**Método:** Web scraping de reportes periódicos

---

### 2. ORGANISMOS INTERNACIONALES Y MULTILATERALES

Estas fuentes son cruciales para tener una visión externa y objetiva, y para **contrastar los datos oficiales**.

#### 2.1 Banco Mundial
**URL:** https://datos.bancomundial.org

| Categoría | Indicadores | API |
|-----------|-------------|-----|
| **PIB** | PIB nominal, per cápita, crecimiento | wbgapi (Python) |
| **Desarrollo** | Formación bruta de capital, inflación estimada | API pública |
| **Sociales** | Pobreza, desigualdad | CSV descargable |

**Librería Python:** `wbgapi`
```python
import wbgapi as wb
# PIB de Venezuela
data = wb.data.DataFrame('NY.GDP.MKTP.CD', countries='VEN')
```

#### 2.2 Fondo Monetario Internacional (FMI)
**URL:** https://www.imf.org

| Categoría | Indicadores | Publicación |
|-----------|-------------|-------------|
| **Perspectivas** | Proyecciones de PIB, inflación | World Economic Outlook |
| **Finanzas** | Balanza cuenta corriente, deuda pública | Informes trimestrales |

**API:** https://dataservices.imf.org/REST/SDMX_JSON.svc/

#### 2.3 Comisión Económica para América Latina y el Caribe (CEPAL)
**URL:** https://www.cepal.org

| Categoría | Indicadores |
|-----------|-------------|
| **Macroeconomía** | PIB, balanza comercial, inversión |
| **Social** | Empleo, pobreza, desigualdad |

**Portal:** CEPALSTAT (https://estadisticas.cepal.org)

---

### 3. OBSERVATORIOS, THINK TANKS Y ACADEMIA

Son fuentes independientes que **llenan los vacíos de información oficial** y ofrecen análisis de alta calidad.

#### 3.1 Observatorio de Finanzas (OVF)
**URL:** https://observatoriodefinanzas.org

| Categoría | Indicadores | Importancia |
|-----------|-------------|-------------|
| **Inflación** | Estimación independiente del IPC | ⭐⭐⭐⭐⭐ |
| **Tipo de Cambio** | Múltiples monitores | ⭐⭐⭐⭐⭐ |
| **Salario Real** | Índice de poder adquisitivo | ⭐⭐⭐⭐ |
| **Actividad Económica** | Índice mensual | ⭐⭐⭐⭐ |
| **Recaudación Fiscal** | Estimación independiente | ⭐⭐⭐ |

**Método:** Web scraping de series de datos ordenadas

#### 3.2 Observatorio Venezolano de Economía (OVE)
**URL:** https://ove-venezuela.com

| Categoría | Indicadores |
|-----------|-------------|
| **Sectoriales** | Análisis por sector económico |
| **Coyuntura** | Informes de análisis económico |

#### 3.3 Universidad Católica Andrés Bello (UCAB) - IIES
**URL:** https://www.ucab.ve/iies

| Categoría | Indicadores |
|-----------|-------------|
| **Proyecciones** | Inflación, PIB, precio del petróleo |
| **Social** | Análisis de pobreza |
| **Coyuntura** | Informes trimestrales |

#### 3.4 Transparencia Venezuela
**URL:** https://transparencia.org.ve

| Categoría | Indicadores |
|-----------|-------------|
| **Gobernanza** | Informes sobre transparencia |
| **Sector Petrolero** | Análisis de PDVSA |

---

### 4. SECTOR ENERGÉTICO (El Pilar de la Economía)

Dada la dependencia venezolana del petróleo, es un sector crítico.

#### 4.1 Fuentes Oficiales

| Fuente | URL | Datos |
|--------|-----|-------|
| **PDVSA** | pdvsa.com | Producción oficial |
| **Ministerio de Hidrocarburos** | minhidrocarburos.gob.ve | Producción, precio de cesta |

#### 4.2 Fuentes Internacionales (Para Contraste)

| Fuente | URL | Datos | Importancia |
|--------|-----|-------|-------------|
| **OPEP** | opec.org | Producción (fuentes secundarias) | ⭐⭐⭐⭐⭐ |
| **EIA (EE.UU.)** | eia.gov | Estimaciones de producción | ⭐⭐⭐⭐ |
| **Reuters** | reuters.com | Datos de mercado | ⭐⭐⭐⭐ |
| **datosmacro** | datosmacro.expansion.com | Precio cesta venezolana | ⭐⭐⭐ |

**Importancia:** Las fuentes secundarias (OPEP, EIA) son fundamentales para **contrastar la producción oficial de PDVSA**, que tiende a ser sobreestimada.

---

### 5. SECTOR FINANCIERO Y PRECIOS DE MERCADO

#### 5.1 Bolsa de Valores de Caracas (BVC)
**URL:** https://www.bolsadecaracas.com

| Indicador | Fuente Alternativa | Método |
|-----------|-------------------|--------|
| IBC | Yahoo Finance (IBC.CR) | yfinance |
| Subíndices | Scraping BVC | BeautifulSoup |
| Acciones individuales | Scraping BVC | BeautifulSoup |

#### 5.2 Monitores de Dólar

| Monitor | Tipo | Método |
|---------|------|--------|
| DólarToday | Paralelo | Scraping |
| EnParaleloVzla | Paralelo | Scraping |
| Binance P2P | Mercado libre | API oficial |
| Mercado Libre | Precios reales | Scraping |
| **pydolarvenezuela** | Consolida todos | Librería Python |

---

## 🔧 ESTRATEGIA DE INTEGRACIÓN

### Arquitectura Modular de Collectors

```
src/collectors/
├── oficial/                    # Fuentes oficiales
│   ├── bcv_collector.py       # Banco Central
│   ├── ine_collector.py       # Instituto Nacional de Estadística
│   ├── mppef_collector.py     # Ministerio de Economía
│   └── seniat_collector.py    # SENIAT (fiscal)
├── internacional/              # Organismos internacionales
│   ├── worldbank_collector.py # Banco Mundial
│   ├── imf_collector.py       # FMI
│   └── cepal_collector.py     # CEPAL
├── independiente/              # Fuentes independientes
│   ├── ovf_collector.py       # Observatorio de Finanzas
│   ├── ove_collector.py       # Observatorio Venezolano
│   └── ucab_collector.py      # UCAB IIES
├── mercado/                    # Mercados financieros
│   ├── bvc_collector.py       # Bolsa de Valores
│   ├── dolar_collector.py     # Monitores de dólar
│   └── binance_collector.py   # Binance P2P
├── energetico/                 # Sector petrolero
│   ├── pdvsa_collector.py     # PDVSA
│   ├── opec_collector.py      # OPEP
│   └── eia_collector.py       # EIA (EE.UU.)
├── noticias/                   # Prensa
│   ├── rss_collector.py       # RSS feeds
│   └── scraper_collector.py   # Scraping
└── social/                     # Redes sociales
    ├── reddit_collector.py    # Reddit
    └── twitter_collector.py   # Twitter/X
```

### Lógica de Contraste y Validación

```python
# src/analyzers/data_validation.py

def validate_indicator(indicator_name: str, sources: dict) -> dict:
    """
    Valida un indicador comparando múltiples fuentes.
    
    Args:
        indicator_name: Nombre del indicador (ej. 'inflacion')
        sources: Dict con valores de cada fuente
                 {'bcv': 120, 'ovf': 180, 'fmi': 150}
    
    Returns:
        Dict con análisis de dispersión
    """
    values = list(sources.values())
    
    result = {
        'indicator': indicator_name,
        'sources': sources,
        'mean': np.mean(values),
        'std': np.std(values),
        'min': min(values),
        'max': max(values),
        'dispersion': (max(values) - min(values)) / np.mean(values) * 100,
        'confidence': 'alta' if np.std(values) < 10 else ('media' if np.std(values) < 30 else 'baja')
    }
    
    # Generar interpretación
    if result['dispersion'] > 50:
        result['interpretation'] = (
            f"ALTA INCERTIDUMBRE: {indicator_name} varía significativamente "
            f"entre fuentes ({result['min']:.1f}% - {result['max']:.1f}%). "
            f"La medición oficial puede no ser confiable."
        )
    elif result['dispersion'] > 20:
        result['interpretation'] = (
            f"MEDIA INCERTIDUMBRE: Existe variación entre fuentes "
            f"({result['min']:.1f}% - {result['max']:.1f}%). "
            f"Considerar el rango como estimación."
        )
    else:
        result['interpretation'] = (
            f"BAJA INCERTIDUMBRE: Las fuentes coinciden "
            f"({result['min']:.1f}% - {result['max']:.1f}%). "
            f"Estimación confiable."
        )
    
    return result
```

### Ejemplo: Análisis de Inflación Multi-Fuente

```python
# Resultado típico del sistema
inflacion_analysis = {
    'bcv': 120,        # Inflación oficial
    'ovf': 180,        # Observatorio de Finanzas
    'fmi': 150,        # Fondo Monetario Internacional
    'ucab': 160,       # UCAB
}

# Conclusión del Sistema:
"""
La inflación se estima entre 120% y 180%, con una media de 152.5%.
La alta dispersión (39.3%) sugiere incertidumbre en la medición oficial.
El modelo SARIMA sugiere una tendencia a la baja para el próximo trimestre
si se mantiene la política monetaria actual.
"""
```

### Tabla Resumen de Fuentes por Indicador

| Indicador | BCV | OVF | FMI | BM | CEPAL | OPEP |
|-----------|-----|-----|-----|----|-------|------|
| Inflación (IPC) | ✅ | ✅ | ✅ | ✅ | ✅ | - |
| Tipo de Cambio | ✅ | ✅ | - | - | - | - |
| PIB | ✅ | ✅ | ✅ | ✅ | ✅ | - |
| Reservas | ✅ | - | ✅ | ✅ | - | - |
| Producción Petrolera | ✅ | - | - | ✅ | - | ✅ |
| Deuda Pública | ✅ | - | ✅ | ✅ | - | - |
| Empleo | ✅ | ✅ | - | ✅ | ✅ | - |
| Balanza Comercial | ✅ | - | ✅ | ✅ | ✅ | - |

---

## 📋 DEPENDENCIAS PARA requirements.txt

```txt
# Fuentes oficiales y APIs
pydolarvenezuela   # Monitores de dólar y BCV
pyvenezuela        # Datos del BCV
wbgapi             # API del Banco Mundial
imfpy              # API del FMI
pandas-datareader  # Para yfinance y otras fuentes
yfinance           # Yahoo Finance (BVC)

# Web scraping robusto
requests
beautifulsoup4
selenium           # Si algún sitio usa JavaScript
playwright         # Alternativa moderna a Selenium

# Manejo de datos
pandas
numpy
openpyxl           # Para archivos Excel del BCV/INE
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

---

## 📝 ENCUESTAS CIUDADANAS Y COMERCIANTES (NUEVO)

Datos primarios vía Google Forms para medir la **percepción económica** y contrastarla
con los datos oficiales. Complementan la lógica de contraste multi-fuente: añaden la
dimensión "cómo lo vive la gente" frente a "qué dicen los números".

### 1. Tipos de Encuesta (segmentos)

| Tipo | Segmento | Objetivo | Indicadores derivados |
|------|----------|----------|----------------------|
| `persona_comun` | Ciudadano promedio | Poder adquisitivo, percepción de inflación, costo de vida | Índice de percepción de inflación, brecha ingreso-vs-canasta, medios de pago |
| `comerciante` | Negocios y comercio | Clima de negocios, dinámica de precios, demanda | Clima de negocios, índice de ajuste de precios, dolarización de transacciones |

### 2. Diseño de Preguntas — Persona Común

Bloques recomendados (Google Forms):

| Bloque | Preguntas (ejemplos) | Tipo |
|--------|----------------------|------|
| **Perfil** | Rango de edad, estado, zona, ocupación, ¿cuántas personas en tu hogar? | Selección |
| **Ingreso** | ¿En qué moneda recibes tu ingreso principal? ¿Rango mensual en USD/BS? | Selección/Número |
| **Gasto y canasta** | ¿Cuánto gastas al mes en alimentos? ¿Qué % de tu ingreso destinas a comida? | Número/Escala |
| **Percepción de inflación** | ¿En el último mes los precios subieron: mucho, algo, poco, nada? ¿Cuánto estimas que subieron (%)? | Escala/Número |
| **Ahorro y deuda** | ¿Puedes ahorrar este mes? ¿Tienes deudas? | Sí/No |
| **Medios de pago** | ¿Pagas más en efectivo, bolívares digitales, dólares, tarjetas? | Selección múltiple |
| **Expectativas** | ¿Cómo ves la economía en 6 meses: mejor, igual, peor? | Escala |

### 3. Diseño de Preguntas — Comerciante

| Bloque | Preguntas (ejemplos) | Tipo |
|--------|----------------------|------|
| **Perfil del negocio** | Sector, ciudad, tamaño (empleados), antigüedad | Selección |
| **Ventas** | ¿Cómo evolucionaron tus ventas este mes vs el anterior? (%, rango) | Escala/Número |
| **Precios** | ¿Ajustaste precios este mes? ¿Por qué causa (dólar, costos, demanda)? | Selección/Número |
| **Inventario y demanda** | ¿Cómo está tu demanda: alta, normal, baja? ¿Abastecimiento fácil o difícil? | Escala |
| **Métodos de pago** | ¿En qué % cobras en dólares/bolívares/electrónico? | Número |
| **Costos y márgenes** | ¿Tus costos subieron? ¿Tu margen cambió? | Escala |
| **Crédito y empleo** | ¿Tienes acceso a crédito? ¿Contrataste o despediste personal? | Sí/No/Selección |

### 4. Pipeline Google → Sistema

```
Google Forms (formulario por segmento)
      │  (respuestas automáticas)
      ▼
Google Sheet vinculada al formulario
      │  gspread + service account (Google Sheets API)
      ▼
survey_collector.py  ──►  survey_responses (PostgreSQL/TimescaleDB)
      │                        ├─ raw_answers JSONB  (flexible, versionado)
      │                        └─ kpis derivados     (columnas normalizadas)
      ▼
analyzers/surveys/
      ├─ indicators.py   → KPIs por segmento
      ├─ contrast.py     → percepción vs IPC oficial/OVF
      └─ report.py       → resumen ejecutivo DeepSeek
```

**Claves de diseño:**
- **Flexibilidad:** las respuestas crudas se guardan como `JSONB` (las preguntas cambian entre versiones); los KPIs se calculan y normalizan en columnas.
- **Versionado:** cada formulario tiene `form_version`; si se editan preguntas, se versiona, no se rompe la serie histórica.
- **Idempotencia:** el collector solo ingesta filas nuevas (marca de última fila procesada por sheet).
- **Seguridad:** credenciales de la service account por variable de entorno (`GOOGLE_CREDENTIALS_PATH`), nunca en el repo.

### 5. Contraste Percepción vs Realidad

```python
# src/analyzers/surveys/contrast.py

def contrast_perception_inflation(perceived: float, official: float, ovf: float) -> dict:
    """
    Compara la inflación percibida por la población con la medición oficial.
    
    Args:
        perceived: Inflación percibida (promedio encuesta, %)
        official:  IPC oficial BCV (%)
        ovf:       Estimación independiente OVF (%)
    """
    gap = perceived - official
    return {
        'perceived': perceived,
        'official': official,
        'ovf': ovf,
        'gap_vs_official': gap,
        'gap_vs_ovf': perceived - ovf,
        'interpretation': (
            f"La población percibe {perceived:.1f}% vs {official:.1f}% oficial "
            f"y {ovf:.1f}% OVF. Brecha de {gap:.1f} puntos."
            if abs(gap) > 5 else
            "La percepción ciudadana coincide con las mediciones."
        )
    }
```

### 6. Limitaciones Metodológicas (advertir en informes)

| Limitación | Mitigación |
|------------|------------|
| **Sesgo de autoselección** | No es muestreo aleatorio; los encuestados son voluntarios | 
| **Tamaño muestral variable** | Reportar N por período; alertar si N < umbral (p.ej. 50) |
| **Cambio de preguntas** | `form_version` en cada edición del formulario |
| **Múltiples respuestas por persona** | Marca de tiempo + calidad; opcional deduplicación por dispositivo |
| **Memoria/percepción imprecisa** | Preguntar rangos en vez de cifras exactas cuando aplique |

---

## 📊 Métodos de Análisis

### 1. Modelos Predictivos
```
- ARIMA/SARIMA (series temporales)
- VECM (cointegración)
- GARCH (volatilidad)
- Prophet (estacionalidad)
```

### 2. Análisis de Contraste
```
Pipeline:
1. Recolectar de múltiples fuentes
2. Calcular estadísticas de dispersión
3. Identificar incertidumbre
4. Generar escenarios (optimista, base, pesimista)
```

---

## 📋 Checklist de Implementación

### Fase 1: Fundamentos
- [x] Configurar proyecto base
- [x] Implementar modelos de datos
- [x] Módulo econométrico

### Fase 2: Recolección
- [x] Collector BCV (DolarAPI oficial + IPC)
- [x] Collector BVC (yfinance)
- [x] Collector OVF (scraping)
- [x] Collector Banco Mundial (API REST)
- [x] Collector OPEP
- [x] Collector Binance P2P (paralelo digital)
- [x] Collector ONAPRE (ejecución presupuestaria)
- [x] Collector CGR (contraloría)
- [x] Collector INE
- [x] Collector RSS (noticias)
- [x] Collector Reddit (sentimiento)
- [ ] Collector Dólar Paralelo (pydolarvenezuela)
- [x] **Formulario Persona Común (Google Forms)** ✅ activo
- [x] **Formulario Comerciante (Google Forms)** ✅ activo
- [x] **Collector de Encuestas (gspread)** ✅ pipeline end-to-end
- [x] **Ingesta noticias/RSS + análisis de sentimiento** ✅ pipeline + dashboard
- [x] **Filtro de relevancia económica** ✅ `analyzers/relevance.py` (léxico fuerte/débil)

### Fase 3: Análisis
- [x] Módulo econométrico
- [x] Integración collectors → econometría (market_integration)
- [x] **Análisis de sentimiento (léxico español)** — `analyzers/sentiment.py`
- [x] **Filtro de relevancia económica** — `analyzers/relevance.py`
- [ ] Lógica de contraste multi-fuente
- [ ] Generación de escenarios
- [x] **Análisis de encuestas (percepción vs datos oficiales)**
- [x] **Clima de negocios**

### Fase 4: Visualización
- [x] Dashboard con métricas en vivo (dólar oficial/paralelo, inflación)
- [x] **Sección de encuestas en el dashboard**
- [x] **Sección de noticias y sentimiento en el dashboard**
- [ ] Dashboard con dispersión de fuentes
- [ ] Sistema de alertas

### Fase 5: Automatización (Informe semanal)
- [x] **Cadena de LLMs con fallback** — `analyzers/llm.py` (LLM1..LLM8, estilo `dev/ds`)
- [x] **Informe semanal automatizado** — `analyzers/reports/weekly.py` → `data/reports/`
- [x] **Job semanal** (cron `WEEKLY_REPORT_DAY`/`WEEKLY_REPORT_HOUR`) → 4 jobs totales
- [x] **Backfill histórico de tasas** — `scripts/backfill_rates.py` (usdt.com.ve CSV, CC-BY-4.0)

> **Nota histórico:** el CSV de usdt.com.ve (`/data/usdt-ves-historical.csv`, ~10MB,
> snapshots 5 min de Binance/Bybit/BCV) cubre desde 2026-01-17. El backfill agrega a
> promedio diario (``source/currency``: binance/usdt, bybit/usdt, bcv/usd) e inserta
> idempotente. Se cargaron 6 meses (2026-02-20 → hoy): ~195 tasas por fuente.

### Fase 5b: Nuevas fuentes (dashboard + collectors)
- [x] **Dashboard con Bybit + brecha cambiaria** — `market_data.brecha_porcentaje`
      y `brecha_series`; gráfico histórico de 6 meses en `app.py` (Plotly)
- [x] **SENIAT** — `collectors/fiscal/seniat_collector.py` (catálogo `FiscalDocument`)
- [x] **MPPEF** — `collectors/fiscal/mppef_collector.py` (catálogo `FiscalDocument`)
- [x] **PDVSA** — `collectors/international/pdvsa_collector.py` (cesta venezolana)
- [x] **FMI** — `collectors/international/imf_collector.py` (API SDMX-JSON de IFS)
- [x] **CEPAL** — `collectors/international/cepal_collector.py` (API CEPALSTAT)
- [x] **UNSCEB** — `collectors/international/unsceb_collector.py` (gasto ONU por país)

> **Helpers compartidos:** `collectors/fiscal/documents.py` centraliza el catálogo de
> documentos (filtra hrefs `#`/`javascript:`, hosts externos, y deriva título del
> nombre de archivo si el ancla está vacía). CGR usa este helper.
>
> **API CEPALSTAT** (`api-cepalstat.cepal.org/cepalstat/api/v1`): indicador 2216 =
> PIB anual a precios constantes (millones USD). Dimensiones: 208=país (Venezuela
> 259, nombre "Venezuela (República Bolivariana de)"), 21004=rubro (21166=PIB total),
> 29117=años (id→año). Data: `members=<país>,<rubro>` devuelve la serie anual.
> Verificado en vivo: PIB 2025 ≈ 94.368 millones USD.
>
> **API FMI** (`dataservices.imf.org/REST/SDMX_JSON.svc`): `CompactData/IFS/A.VE.<ind>`.
> NGDP_RPCH (crec. PIB real) y PCPIPCH (inflación IPC). DNS caído desde la red local
> (como BCV IPC); funciona desde Railway u otras redes. `data.imf.org` y el DataMapper
> (`www.imf.org/external/datamapper/api/v1`) responden 403 desde scripts.
>
> **API UNSCEB** (`unsceb.org`): CSVs del sistema ONU. El dataset
> `FS/expenses_by_country_region_sub_agency.csv` (~10MB, 116k filas) desglosa el gasto
> de agencias de la ONU por país (Venezuela = "Venezuela (Bolivarian Republic of)").
> `UNSCEBCollector.fetch_venezuela_expenses()` agrega por (año, moneda) →
> `IndicatorPoint(gasto_onu_venezuela)`. Verificado en vivo: ~38 observaciones
> (2021-2024), ≈ $160-210M USD/año de gasto ONU en Venezuela.
>
> **Nota PDVSA/CEPAL:** los datos de mercado con DNS caído localmente se recogen
> mejor desde Railway (ver `pdvsa.com`, `dataservices.imf.org`).
>
> **Fuente real de PDVSA:** `www.pdvsa.com` suele fallar por DNS; se usa el portal
> de la Junta Administradora Ad Hoc **`pdvsa-adhoc.com`** → `/documentacion-de-interes/`
> publica comunicados y resultados operacionales (CITGO, producción, gacetas
> legislativas de la AN de 2022-23). `PDVSACollector.fetch_documents()` devuelve el
> catálogo (`FiscalDocument`); `fetch_basket_price()` (cesta venezolana) se mantiene
> como método secundario y degrada si la página no trae el precio.
>
> **FMI (referencias adicionales):** `data.imf.org`, `data.imf.org/en/Datasets`
> (portal de datasets) y `unsceb.org/data-download/` (datos del sistema de la ONU,
> útil para remuneraciones/personal). La API SDMX-JSON ya integrada es
> `dataservices.imf.org`.
>
> **Dashboard:** `market_data` ahora expone `list_rates` (serie), `brecha_porcentaje`
> y `brecha_series`; `app.py` muestra 4 tarjetas (Oficial, Binance, Bybit, Inflación),
> 2 tarjetas de brecha y un gráfico Plotly de 6 meses.

---

## ☁️ Notas de Despliegue

### Railway + Binance P2P (geo-blocking)

**Problema:** Binance P2P bloquea por geolocalización las IPs de EE.UU.
Railway despliega por defecto en regiones de EE.UU. (`us-west`, `us-east`),
por lo que **el job de Binance fallará si el scheduler corre en Railway**.

**Estado actual:** la recolección de mercado corre desde la máquina local
(`python -m src.scripts.collect_market` o `main.py`), donde Binance funciona
normalmente. El pipeline ya degrada con gracia: si Binance falla, solo se
omite `binance_usdt` y el resto (BCV, OVF) se guarda igual.

**Opciones si se despliega el scheduler a Railway:**
1. Elegir una región no bloqueada por Binance (p.ej. `eu-west`) al escalar.
2. Correr solo el job de mercado en local y el resto del scheduler en Railway.
3. Sustituir Binance P2P por otro proxy del paralelo (DólarToday, EnParaleloVzla)
   cuando se implemente `dolar_collector.py`.

El resto de fuentes (BCV, OVF, World Bank, OPEP, encuestas Google) no tienen
restricción geográfica y funcionan desde cualquier región.

---

**Base de conocimiento actualizada: Agosto 2026**
**Última revisión: Fuentes institucionales nacionales e internacionales + Encuestas Google (Fase B) + Despliegue Railway/Binance**
