# Roadmap - Economía Venezuela

## 🗺️ Hoja de Ruta del Proyecto

---

## 📅 Vista General del Timeline

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

### Coletores por Categoría

#### 🏛️ 2.1 Fuentes Oficiales Nacionales

| Collector | Fuente | Datos | Método | Prioridad |
|-----------|--------|-------|--------|-----------|
| `bcv_collector.py` | BCV | Tasas, IPC, PIB, Reservas | API comunitaria + Scraping | 1️⃣ |
| `ine_collector.py` | INE | Empleo, Pobreza | Descarga Excel | 2️⃣ |
| `mppef_collector.py` | MPPEF | Presupuesto, Deuda | Scraping | 3️⃣ |
| `seniat_collector.py` | SENIAT | Recaudación fiscal | Scraping | 3️⃣ |
| `sunaval_collector.py` | SUNAVAL | Mercado de capitales | Scraping | 2️⃣ |

#### 🌍 2.2 Organismos Internacionales

| Collector | Fuente | Datos | Método | Prioridad |
|-----------|--------|-------|--------|-----------|
| `worldbank_collector.py` | Banco Mundial | PIB, Desarrollo | API wbgapi | 1️⃣ |
| `imf_collector.py` | FMI | Proyecciones | API IMF | 1️⃣ |
| `cepal_collector.py` | CEPAL | Estadísticas regionales | Scraping | 2️⃣ |

#### 🔬 2.3 Observatorios Independientes

| Collector | Fuente | Datos | Método | Prioridad |
|-----------|--------|-------|--------|-----------|
| `ovf_collector.py` | OVF | Inflación independiente | Scraping | 1️⃣ |
| `ove_collector.py` | OVE | Análisis sectorial | Scraping | 2️⃣ |
| `ucab_collector.py` | UCAB IIES | Proyecciones | Scraping | 2️⃣ |

#### 🛢️ 2.4 Sector Energético

| Collector | Fuente | Datos | Método | Prioridad |
|-----------|--------|-------|--------|-----------|
| `pdvsa_collector.py` | PDVSA | Producción oficial | Scraping | 1️⃣ |
| `opec_collector.py` | OPEP | Producción (secundaria) | API/Scraping | 1️⃣ |
| `eia_collector.py` | EIA | Estimaciones | API/Scraping | 2️⃣ |

#### 💰 2.5 Mercados Financieros

| Collector | Fuente | Datos | Método | Prioridad |
|-----------|--------|-------|--------|-----------|
| `bvc_collector.py` | BVC/Yahoo | IBC, Acciones | yfinance | 1️⃣ |
| `dolar_collector.py` | Monitores | Tasa paralelo | pydolarvenezuela | 1️⃣ |
| `binance_collector.py` | Binance | Precio USDT/VES | API oficial | 1️⃣ |

#### 📰 2.6 Noticias y Redes Sociales

| Collector | Fuente | Datos | Método | Prioridad |
|-----------|--------|-------|--------|-----------|
| `rss_collector.py` | Portales VE | Noticias económicas | RSS | 2️⃣ |
| `reddit_collector.py` | Reddit | Sentimiento | API OAuth2 | 2️⃣ |
| `twitter_collector.py` | Twitter/X | Sentimiento | API v2 | 3️⃣ |

---

### Estructura Completa de Collectors

```
src/collectors/
├── __init__.py
├── oficial/
│   ├── __init__.py
│   ├── bcv_collector.py        # Banco Central de Venezuela
│   ├── ine_collector.py        # Instituto Nacional de Estadística
│   ├── mppef_collector.py      # Ministerio de Economía
│   ├── seniat_collector.py     # SENIAT (fiscal)
│   └── sunaval_collector.py    # Superintendencia de Valores
├── internacional/
│   ├── __init__.py
│   ├── worldbank_collector.py  # Banco Mundial
│   ├── imf_collector.py        # FMI
│   └── cepal_collector.py      # CEPAL
├── independiente/
│   ├── __init__.py
│   ├── ovf_collector.py        # Observatorio de Finanzas
│   ├── ove_collector.py        # Observatorio Venezolano
│   └── ucab_collector.py       # UCAB IIES
├── energetico/
│   ├── __init__.py
│   ├── pdvsa_collector.py      # PDVSA
│   ├── opec_collector.py       # OPEP
│   └── eia_collector.py        # EIA (EE.UU.)
├── mercado/
│   ├── __init__.py
│   ├── bvc_collector.py        # Bolsa de Valores
│   ├── dolar_collector.py      # Monitores de dólar
│   └── binance_collector.py    # Binance P2P
├── noticias/
│   ├── __init__.py
│   └── rss_collector.py        # RSS feeds
└── social/
    ├── __init__.py
    ├── reddit_collector.py     # Reddit
    └── twitter_collector.py    # Twitter/X
```

---

### Hitos Fase 2

#### Semana 5: Fuentes Oficiales
- [ ] Implementar `bcv_collector.py`
- [ ] Implementar `ine_collector.py`
- [ ] Tests y documentación

#### Semana 6: Organismos Internacionales
- [ ] Implementar `worldbank_collector.py`
- [ ] Implementar `imf_collector.py`
- [ ] Tests y documentación

#### Semana 7: Observatorios y Mercados
- [ ] Implementar `ovf_collector.py`
- [ ] Implementar `bvc_collector.py`
- [ ] Implementar `dolar_collector.py`

#### Semana 8: Energía, Noticias y Social
- [ ] Implementar `opec_collector.py`
- [ ] Implementar `rss_collector.py`
- [ ] Implementar `reddit_collector.py`

---

### Tabla de Fuentes por Indicador

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

### Dependencias Fase 2

```txt
# Venezuela
pydolarvenezuela==0.2.0
pyvenezuela==0.1.0
bcv-exchange==0.1.0

# Internacional
wbgapi==1.0.1          # Banco Mundial
yfinance==0.2.31       # Yahoo Finance
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
openpyxl==3.1.2        # Archivos Excel
```

---

## 📦 Fase 3: Análisis (Semanas 9-12)

### Estado: ✅ COMPLETADA

- [x] Módulo econométrico (SARIMA, VECM, GARCH)
- [x] Pruebas de estacionariedad
- [x] Diagnósticos de residuos
- [x] Regresión Newey-West

---

## 📦 Fase 4: Visualización (Semanas 13-16)

### Estado: ⏳ PENDIENTE

#### Dashboard con Multi-Fuentes

```python
# Ejemplo de visualización multi-fuente
st.subheader("📊 Inflación: Análisis Multi-Fuente")

# Gráfico de dispersión de fuentes
fig = go.Figure()

for source, value in inflation_data.items():
    fig.add_trace(go.Bar(
        name=source,
        x=[source],
        y=[value]
    ))

fig.update_layout(
    title="Inflación por Fuente",
    yaxis_title="% Anual"
)

st.plotly_chart(fig)

# Mostrar análisis de dispersión
st.info(f"""
**Análisis de Dispersión:**
- Rango: {min_value:.1f}% - {max_value:.1f}%
- Media: {mean_value:.1f}%
- Dispersión: {dispersion:.1f}%
- Confianza: {confidence}
""")
```

---

## 📦 Fase 5: Automatización (Semanas 17-20)

### Estado: ⏳ PENDIENTE

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

## 📋 Próximos Pasos

### Prioridad Alta
1. **Collector BCV** con pyDolarVenezuela
2. **Collector Banco Mundial** con wbgapi
3. **Collector OVF** (scraping)
4. **Collector BVC** con yfinance

### Prioridad Media
5. Collector OPEP
6. Collector Dólar Paralelo
7. Collector Noticias (RSS)

### Prioridad Baja
8. Collector Redes Sociales
9. Collector INE
10. Collector SENIAT

---

**Roadmap actualizado: Agosto 2025**
**Versión: 3.0**
**Incluye: Todas las fuentes institucionales**
