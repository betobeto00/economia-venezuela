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

## 📦 Fase 2: Recolección de Datos

### Coletores por Categoría

#### 🏛️ 2.1 Fuentes Oficiales Nacionales

| Collector | Fuente | Datos | Método | Prioridad |
|-----------|--------|-------|--------|-----------|
| `bcv_collector.py` | BCV | Tasas, IPC, PIB | API comunitaria | 1️⃣ |
| `ine_collector.py` | INE | Empleo, Pobreza | Scraping | 2️⃣ |
| `mppef_collector.py` | MPPEF | Presupuesto, Deuda | Scraping | 2️⃣ |
| `seniat_collector.py` | SENIAT | Recaudación fiscal | Scraping | 3️⃣ |
| `sunaval_collector.py` | SUNAVAL | Mercado capitales | Scraping | 2️⃣ |

#### 💰 2.2 Fuentes Fiscales Gubernamentales (NUEVO)

| Collector | Fuente | Datos | Método | Prioridad |
|-----------|--------|-------|--------|-----------|
| `onapre_collector.py` | ONAPRE | Ejecución presupuestaria | Scraping + PDF | 1️⃣ |
| `cgr_collector.py` | CGR | Informes de gestión | Scraping + PDF | 1️⃣ |
| `an_collector.py` | AN | Leyes de presupuesto | Scraping | 2️⃣ |
| `caracas_collector.py` | Alcaldía | Gestión municipal | Scraping | 3️⃣ |

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

| Collector | Fuente | Datos | Método | Prioridad |
|-----------|--------|-------|--------|-----------|
| `worldbank_collector.py` | Banco Mundial | PIB, Desarrollo | API wbgapi | 1️⃣ |
| `imf_collector.py` | FMI | Proyecciones | API IMF | 1️⃣ |
| `cepal_collector.py` | CEPAL | Estadísticas regionales | Scraping | 2️⃣ |

#### 🔬 2.4 Observatorios Independientes

| Collector | Fuente | Datos | Método | Prioridad |
|-----------|--------|-------|--------|-----------|
| `ovf_collector.py` | OVF | Inflación independiente | Scraping | 1️⃣ |
| `ove_collector.py` | OVE | Análisis sectorial | Scraping | 2️⃣ |
| `ucab_collector.py` | UCAB IIES | Proyecciones | Scraping | 2️⃣ |

#### 🛢️ 2.5 Sector Energético

| Collector | Fuente | Datos | Método | Prioridad |
|-----------|--------|-------|--------|-----------|
| `pdvsa_collector.py` | PDVSA | Producción oficial | Scraping | 1️⃣ |
| `opec_collector.py` | OPEP | Producción secundaria | API/Scraping | 1️⃣ |
| `eia_collector.py` | EIA | Estimaciones | API/Scraping | 2️⃣ |

#### 💹 2.6 Mercados Financieros

| Collector | Fuente | Datos | Método | Prioridad |
|-----------|--------|-------|--------|-----------|
| `bvc_collector.py` | BVC/Yahoo | IBC, Acciones | yfinance | 1️⃣ |
| `dolar_collector.py` | Monitores | Tasa paralelo | pydolarvenezuela | 1️⃣ |
| `binance_collector.py` | Binance | Precio USDT/VES | API oficial | 1️⃣ |

#### 📰 2.7 Noticias y Redes Sociales

| Collector | Fuente | Datos | Método | Prioridad |
|-----------|--------|-------|--------|-----------|
| `rss_collector.py` | Portales VE | Noticias económicas | RSS | 2️⃣ |
| `reddit_collector.py` | Reddit | Sentimiento | API OAuth2 | 2️⃣ |
| `twitter_collector.py` | Twitter/X | Sentimiento | API v2 | 3️⃣ |

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

## 📊 Dependencias Adicionales

```txt
# Para procesamiento de PDFs
pdfplumber==0.10.3
PyPDF2==3.0.1

# Para extracción con IA
openai==1.10.0  # DeepSeek API
```

---

## 📋 Próximos Pasos Inmediatos

### Semana 5 (Actual) - Prioridades

1. **Implementar `bcv_collector.py`**
2. **Implementar `onapre_collector.py`** (NUEVO)
3. **Implementar `ovf_collector.py`**
4. **Implementar `worldbank_collector.py`**

### Semana 6

5. **Implementar `cgr_collector.py`** (NUEVO)
6. **Implementar `bvc_collector.py`**
7. **Implementar `binance_collector.py`**

### Semana 7

8. **Implementar `ine_collector.py`**
9. **Implementar `opec_collector.py`**
10. **Tests para colectores principales**

### Semana 8

11. **Implementar `rss_collector.py`**
12. **Implementar `reddit_collector.py`**
13. **Integración con modelos econométricos**

---

## 📈 Métricas de Progreso

| KPI | Meta | Actual | Estado |
|-----|------|--------|--------|
| Collectors implementados | 20 | 0 | ⏳ |
| Collectors fiscales | 4 | 0 | ⏳ |
| Tests unitarios | > 80% | ~20% | 🟡 |
| Cobertura de fuentes | 15+ | 0 | ⏳ |

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

### Éxito de Análisis
- [ ] Análisis fiscal completo
- [ ] Efecto del gasto público cuantificado
- [ ] Sostenibilidad fiscal evaluada

---

**Roadmap actualizado: Agosto 2025**
**Versión: 5.0**
**Incluye: Fuentes fiscales gubernamentales**
