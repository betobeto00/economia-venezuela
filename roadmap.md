# Roadmap - Economía Venezuela

## 🗺️ Hoja de Ruta del Proyecto

---

## 📅 Estado Actual

```
FASE 1: Fundamentos    ████████████████████ 100% ✅
FASE 2: Recolección    ████████████████████  95% ✅
FASE 3: Análisis       ████████████████████ 100% ✅
FASE 4: Visualización  ███████████░░░░░░░░░  55% ✅
FASE 5: Automatización ████████████████░░░░  80% ✅

TOTAL: 86%
```

---

## 📦 Fase 2: Recolección de Datos

### Coletores por Categoría

#### 🏛️ 2.1 Fuentes Oficiales Nacionales

| Collector | Fuente | Datos | Método | Prioridad | Estado |
|-----------|--------|-------|--------|-----------|--------|
| `bcv_collector.py` | BCV | Tasas, IPC, PIB | API comunitaria | 1️⃣ | ✅ |
| `ine_collector.py` | INE | Empleo, Pobreza | Scraping | 2️⃣ | ✅ |
| `mppef_collector.py` | MPPEF | Presupuesto, Deuda | Scraping | 2️⃣ | ⏳ |
| `seniat_collector.py` | SENIAT | Recaudación fiscal | Scraping | 3️⃣ | ⏳ |
| `sunaval_collector.py` | SUNAVAL | Mercado capitales | Scraping | 2️⃣ | ⏳ |

#### 💰 2.2 Fuentes Fiscales Gubernamentales (NUEVO)

| Collector | Fuente | Datos | Método | Prioridad | Estado |
|-----------|--------|-------|--------|-----------|--------|
| `onapre_collector.py` | ONAPRE | Ejecución presupuestaria | Scraping + PDF | 1️⃣ | ✅ |
| `cgr_collector.py` | CGR | Informes de gestión | Scraping + PDF | 1️⃣ | ✅ |
| `gaceta_collector.py` | Gaceta Oficial | Gacetas (índice + PDF) | API + HTML | 1️⃣ | ✅ |
| `an_collector.py` | AN | Leyes de presupuesto | Scraping | 2️⃣ | ✅ |
| `caracas_collector.py` | Alcaldía | Gestión municipal | Scraping | 3️⃣ | ⏳ |

**Estructura:**
```
src/collectors/fiscal/
├── __init__.py
├── onapre_collector.py     # Oficina Nacional de Presupuesto
├── cgr_collector.py        # Contraloría General
├── an_collector.py         # Asamblea Nacional
├── mppef_collector.py      # Ministerio de Economía
├── caracas_collector.py    # Alcaldía de Caracas
├── pdf_extractor.py        # Extracción de PDFs
└── utils.py                # Funciones comunes
```

#### 🌍 2.3 Organismos Internacionales

| Collector | Fuente | Datos | Método | Prioridad | Estado |
|-----------|--------|-------|--------|-----------|--------|
| `worldbank_collector.py` | Banco Mundial | PIB, Desarrollo | API REST | 1️⃣ | ✅ |
| `imf_collector.py` | FMI | Proyecciones | API IMF (SDMX) | 1️⃣ | ✅ |
| `cepal_collector.py` | CEPAL | Estadísticas regionales | API CEPALSTAT | 2️⃣ | ✅ |
| `unsceb_collector.py` | UNSCEB | Gasto ONU por país | CSV | 2️⃣ | ✅ |

#### 🔬 2.4 Observatorios Independientes

| Collector | Fuente | Datos | Método | Prioridad | Estado |
|-----------|--------|-------|--------|-----------|--------|
| `ovf_collector.py` | OVF | Inflación independiente | Scraping | 1️⃣ | ✅ |
| `ove_collector.py` | OVE | Análisis sectorial | Scraping | 2️⃣ | ⏳ |
| `ucab_collector.py` | UCAB IIES | Proyecciones | Scraping | 2️⃣ | ⏳ |

#### 🛢️ 2.5 Sector Energético

| Collector | Fuente | Datos | Método | Prioridad | Estado |
|-----------|--------|-------|--------|-----------|--------|
| `pdvsa_collector.py` | PDVSA | Producción oficial | Scraping | 1️⃣ | ✅ |
| `opec_collector.py` | OPEP | Producción secundaria | API/Scraping | 1️⃣ | ✅ |
| `eia_collector.py` | EIA | Estimaciones | API/Scraping | 2️⃣ | ⏳ |

#### 💹 2.6 Mercados Financieros

| Collector | Fuente | Datos | Método | Prioridad | Estado |
|-----------|--------|-------|--------|-----------|--------|
| `bvc_collector.py` | BVC/Yahoo | IBC, Acciones | yfinance | 1️⃣ | ✅ |
| `binance_collector.py` | Binance | Precio USDT/VES | API P2P | 1️⃣ | ✅ |
| `dolar_paralelo_collector.py` | BCV Bancos | Tasas 12 bancos + BCV | pyDolarVenezuela | 1️⃣ | ✅ |
| `ibc_components_collector.py` | Investing.com | 8 componentes IBC | Web scraping | 1️⃣ | ✅ |
| `ibc_stocks_collector.py` | Yahoo Finance | Tickers venezolanos | yfinance | 2️⃣ | ✅ |

#### 📰 2.7 Noticias y Redes Sociales

| Collector | Fuente | Datos | Método | Prioridad | Estado |
|-----------|--------|-------|--------|-----------|--------|
| `rss_collector.py` | Portales VE | Noticias económicas | RSS | 2️⃣ | ✅ |
| `reddit_collector.py` | Reddit | Sentimiento | API OAuth2 | 2️⃣ | ✅ |
| `twitter_collector.py` | Twitter/X | Sentimiento | API v2 | 3️⃣ | ⏳ |

#### 📋 2.8 Encuestas Ciudadanas y Comerciantes (NUEVO)

Recolección de datos primarios vía **Google Forms** para fortalecer el análisis microeconómico
y contrastar la percepción pública con los datos oficiales.

| Collector | Fuente | Datos | Método | Prioridad | Estado |
|-----------|--------|-------|--------|-----------|--------|
| `survey_collector.py` | Google Forms → Sheets | Respuestas de encuestas | gspread + Google Sheets API | 1️⃣ | ✅ |

**Tipos de encuesta (segmentos):**

| Tipo | Segmento | Datos Clave | Estado |
|------|----------|-------------|--------|
| `persona_comun` | Ciudadano promedio | Ingreso, gasto, percepción de inflación, canasta, ahorro, empleo | ✅ Implementado |
| `comerciante` | Comerciantes/negocios | Ventas, precios, inventario, demanda, métodos de pago, costos, crédito, empleo | ✅ Implementado |
| *(futuro)* `empresa` | Empresas/sector productivo | Inversión, producción, financiamiento | ⏳ |
| *(futuro)* `remesas` | Receptores de remesas | Flujo, uso, impacto | ⏳ |

**Estructura:**
```
src/collectors/surveys/
├── __init__.py
├── survey_collector.py     # Lee respuestas de Google Sheets (gspread)
├── form_registry.py        # Catálogo de formularios (form_id, sheet_id, versión)
└── utils.py                # Normalización y validación

src/analyzers/surveys/
├── __init__.py
├── indicators.py           # KPIs por segmento (percepción, clima de negocios)
├── contrast.py             # Contraste percepción vs datos oficiales
└── report.py               # Resumen ejecutivo (DeepSeek)
```

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
| **Análisis fiscal** | Efecto gasto público, sostenibilidad | Alta |

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
| **Panel fiscal** | Ejecución presupuestaria | ⏳ |

---

## 📦 Fase 5: Automatización (Semanas 17-20)

### Estado: ⏳ PENDIENTE

---

## 🔧 Análisis Fiscales Habilitados

### Nuevos Análisis con Datos Fiscales

| Análisis | Datos Necesarios | Pregunta |
|----------|------------------|----------|
| **Efecto del Gasto Público** | Ejecución + PIB | ¿El gasto impulsa el crecimiento? |
| **Sostenibilidad Fiscal** | Ingresos vs Gastos | ¿El déficit se financia con emisión? |
| **Eficiencia del Gasto** | Inversión social vs indicadores | ¿Se correlaciona con mejoras? |
| **Nowcasting Económico** | Ejecución del gasto | ¿Se puede estimar PIB en curso? |

### Modelo de Datos Fiscal

```python
# src/models/fiscal.py
from pydantic import BaseModel
from datetime import date
from typing import Optional

class BudgetExecution(BaseModel):
    fiscal_year: int
    source: str  # "ONAPRE", "CGR", "MPPEF", "AN"
    document_url: str
    publication_date: date
    
    total_budget_approved: float
    total_budget_executed: float
    execution_percentage: float
    
    current_expenditure: float
    capital_expenditure: float
    social_investment: float
    
    notes: Optional[str] = None

class FiscalIndicators(BaseModel):
    fiscal_year: int
    deficit: float
    deficit_gdp_ratio: float
    debt_gdp_ratio: float
    primary_balance: float
    monetization: float
```

---

## 📋 Análisis con Datos de Encuestas (NUEVO)

### Nuevos Análisis con Encuestas

| Análisis | Datos Necesarios | Pregunta |
|----------|------------------|----------|
| **Índice de Percepción de Inflación** | Encuestas persona_comun | ¿La percepción ciudadana coincide con el IPC oficial/OVF? |
| **Índice de Poder Adquisitivo Percibido** | Ingreso vs gasto reportado | ¿Cuánto cubre el ingreso real de la canasta? |
| **Clima de Negocios** | Encuestas comerciante | ¿Los comerciantes perciben mejora o deterioro? |
| **Dinámica de Precios desde el Vendedor** | Fijación de precios, margen | ¿Quién ajusta primero: el comerciante o el mercado? |
| **Brecha Percepción vs Realidad** | Contraste con datos oficiales | ¿Hay sobre/subestimación de la inflación en la población? |
| **Medios de Pago y Dolarización** | Métodos de pago (efectivo, divisas, electrónico) | ¿Qué tan dolarizada está la economía de consumo? |

### Modelo de Datos de Encuestas

```python
# src/models/survey.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Any, Dict

class Survey(BaseModel):
    id: int
    survey_type: str        # "persona_comun", "comerciante"
    form_id: str            # ID del Google Form
    sheet_id: str           # ID de la Google Sheet vinculada
    form_version: int       # Versión del formulario (cambios de preguntas)
    name: str
    active: bool

class SurveyResponse(BaseModel):
    id: int
    survey_id: int
    submitted_at: datetime
    respondent_segment: str
    timezone: Optional[str]
    raw_answers: Dict[str, Any]        # Respuestas crudas (JSONB)
    kpis: Dict[str, float]             # KPIs derivados normalizados
    quality_score: Optional[float]     # Validación de respuesta
    source: str = "google_forms"
```

### Dependencias Adicionales

```txt
# Para encuestas Google
gspread==6.1.0              # Google Sheets API
google-auth==2.27.0         # Autenticación service account
google-auth-oauthlib==1.2.0
```

---

## 📊 Dependencias Adicionales

```txt
# Para procesamiento de PDFs
pdfplumber==0.10.3
PyPDF2==3.0.1

# Para extracción con IA
openai==1.10.0  # DeepSeek API

# Para encuestas Google
gspread==6.1.0              # Google Sheets API
google-auth==2.27.0         # Autenticación service account
google-auth-oauthlib==1.2.0
```

---

## 📋 Próximos Pasos Inmediatos

### Semana 5 ✅

1. ✅ **Implementar `bcv_collector.py`**
2. ✅ **Implementar `onapre_collector.py`** (NUEVO)
3. ✅ **Implementar `ovf_collector.py`**
4. ✅ **Implementar `worldbank_collector.py`**

### Semana 6 ✅

5. ✅ **Implementar `cgr_collector.py`** (NUEVO)
6. ✅ **Implementar `bvc_collector.py`**
7. ✅ **Implementar `binance_collector.py`**

### Semana 7 ✅

8. ✅ **Implementar `ine_collector.py`**
9. ✅ **Implementar `opec_collector.py`**
10. ✅ **Tests para colectores principales**

### Semana 8 ✅

11. ✅ **Implementar `rss_collector.py`**
12. ✅ **Implementar `reddit_collector.py`**
13. ✅ **Integración con modelos econométricos**

### Fase B: Encuestas Google (Código ✅ / Manual ⏳)

14. 🟡 **Diseñar y publicar Formulario Persona Común** (Google Forms) — *manual, pendiente*
15. 🟡 **Diseñar y publicar Formulario Comerciante** (Google Forms) — *manual, pendiente*
16. 🟡 **Crear service account de Google + vincular Forms → Sheets** — *manual, pendiente*
17. ✅ **Implementar `survey_collector.py`** (gspread, idempotente)
18. ✅ **Modelo de datos `surveys` / `survey_responses`** (PostgreSQL)
19. ✅ **Implementar `analyzers/surveys/`** (KPIs + contraste con datos oficiales)
20. ✅ **Sección de encuestas en el dashboard** + informe ejecutivo con IA
21. ✅ **Tests del pipeline de encuestas**

### Siguientes pasos (Semanas 9+)

22. ✅ **Formularios + service account** (pasos 14-16 manuales de Google)
23. ✅ **Persistencia del loop de mercado** — *verificado con Postgres real (Railway)*
24. ✅ **Ingesta de noticias/RSS + análisis de sentimiento**
25. ✅ **Informes semanales automatizados con IA** — cadena de 4 LLMs con fallback
26. 🔄 **Collectors restantes**: ✅ `seniat`, `mppef`, `pdvsa`, `imf`, `cepal`, `unsceb`, `gaceta`, `an` — ⏳ `caracas`, `twitter`
27. ✅ **Backfill histórico de tasas** (6 meses) — dataset abierto usdt.com.ve (CC-BY-4.0)
28. ✅ **Dashboard: Bybit + brecha cambiaria** — tarjetas, brecha y gráfico de 6 meses
29. 🔄 **Datos macro**: ✅ `unsceb` (`unsceb.org/data-download`) — ⏳ FMI `data.imf.org` (bloqueado 403 local; SDMX IFS ya integrado)
30. ✅ **Informes económicos en PDF** — diario/semanal/mensual/trimestral/semestral/anual con gráficos, tablas, datos y resumen IA (`generate_report.py`, scheduler)

### Fase 6: Análisis Macro Avanzado (NUEVO)

31. ✅ **Nowcasting** — `analyzers/nowcasting.py` (RandomForest + XGBoost para PIB/inflación en tiempo real)
32. ✅ **Sistema de Alertas** — `alerts/manager.py` (umbrales automáticos: brecha, inflación, IBC, volatilidad)
33. ✅ **Comparaciones Regionales** — `analyzers/regional.py` (Venezuela vs LatAm via World Bank)
34. ✅ **Gráficos Avanzados** — `dashboard/components/advanced_charts.py` (heatmaps, fan charts, waterfall)
35. ✅ **IAE** — `analyzers/iae.py` (Índice de Actividad Económica en tiempo real)
36. ✅ **Cache Macro en DB** — tabla `macro_indicators` + `scripts/refresh_macro.py`

### Pendientes del Análisis Macro

37. ⏳ **SVAR** — Modelo Estructural de Vectores Autorregresivos para shocks estructurales
38. ⏳ **Curva de Phillips** — Relación inflación vs brecha del producto
39. ⏳ **Balanza de Pagos** — Dinámica de reservas internacionales
40. ⏳ **Riesgo País** — EMBI+ o índice propio de riesgo
41. ⏳ **Deuda Pública desglosada** — Bonos, deuda externa/interna, China/Rusia
42. ⏳ **ENCOVI** — Encuesta de Condiciones de Vida (cuando se publique)
43. ⏳ **Integrar Nowcasting/Alertas/IAE en el dashboard**
44. ⏳ **Tests para nuevos módulos** (nowcasting, alerts, regional, iae)

### Nice to have
- ⏳ **Redes sociales**: Facebook e Instagram (requiere tokens de Graph API o scraping frágil)
- ⏳ **Notebooks Jupyter**: Análisis exploratorio con visualizaciones interactivas
- ⏳ **Glosario macroeconómico**: Términos y definiciones para audiencias no técnicas

---

## 📈 Métricas de Progreso

| KPI | Meta | Actual | Estado |
|-----|------|--------|--------|
| Collectors implementados | 20 | 28 ✅ | ✅ |
| Collectors fiscales | 4 | 7 ✅ (SENIAT, MPPEF, ONAPRE, CGR, Gaceta+OCR, AN, Cendas) | ✅ |
| Collectors consumo | 2 | 2 ✅ (ANSA, Atenas) | ✅ |
| Collectors internacionales | 3 | 6 ✅ (WorldBank, IMF, CEPAL, UNSCEB, OPEC, PDVSA) | ✅ |
| Formularios de encuesta activos | 2+ | 2 ✅ | ✅ |
| Respuestas de encuesta procesadas | 500+ | 2 | ⏳ |
| Tests unitarios | > 80% | 299 tests ✅ | ✅ |
| Cobertura de fuentes | 15+ | 24+ | ✅ |
| Dashboard con métricas en vivo | — | ✅ 3 tabs (Inicio + Noticias + Encuestas) | ✅ |
| Informes PDF automáticos | 6 cadencias | ✅ diario a anual (MD + PDF) | ✅ |
| Scheduler automático | — | ✅ 11 jobs (mercado, encuestas, noticias, semanal, 6 periódicos) | ✅ |

**Código implementado**: Fases 2 (recolección: 24 collectors), 3 (análisis), dashboard Fase 4 (3 tabs) y scheduler
Fase 5 (11 jobs: mercado, encuestas, noticias, informe semanal + 6 informes periódicos). Pendiente: collectors de menor prioridad (caracas, twitter) y pasos de despliegue (Railway).

---

## 🏆 Criterios de Éxito

### Éxito Técnico
- [ ] Sistema ejecutándose 99% del tiempo
- [ ] Latencia de datos < 5 minutos
- [ ] Cobertura de tests > 80%
- [ ] Manejo de errores robusto

### Éxito de Datos
- [ ] 15+ fuentes de datos activas
- [ ] 4+ fuentes fiscales integradas
- [ ] Validación multi-fuente funcionando
- [ ] Datos actualizados diariamente/semanalmente
- [ ] 2+ encuestas activas con respuesta continua

### Éxito de Análisis
- [ ] Análisis fiscal completo
- [ ] Efecto del gasto público cuantificado
- [ ] Sostenibilidad fiscal evaluada
- [ ] Índice de percepción de inflación vs datos oficiales
- [ ] Clima de negocios con tendencia temporal

---

**Roadmap actualizado: Agosto 2026**
**Versión: 8.0**
**Incluye: 24 collectors (fiscales + internacionales + IBC + bancos) + Dashboard 3 tabs + 11 jobs scheduler + 299 tests**
