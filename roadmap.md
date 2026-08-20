# Roadmap - Economía Venezuela

## 🗺️ Hoja de Ruta del Proyecto

---

## 📅 Estado Actual

```
FASE 1: Fundamentos    ████████████████████ 100% ✅
FASE 2: Recolección    ████████████████████  95% ✅
FASE 3: Análisis       ████████████████████ 100% ✅
FASE 4: Visualización  ███████████████████░  90% ✅
FASE 5: Automatización ████████████████░░░░  80% ✅
FASE 6: Macro Avanzado ███████████████░░░░░  75% ✅
FASE 7: Datos & Polis  ███░░░░░░░░░░░░░░░░░  15% 🆕

TOTAL: 78%
```

---

## 📦 Fase 7: Recolección de Datos Masiva & Polishing 🆕

### 🔴 7.1 Datos IBC (Prioridad MÁXIMA)

| # | Tarea | Fuente | Método | Estado |
|---|-------|--------|--------|--------|
| 47 | **Componentes IBC 6 meses** — histrico completo de las 9 componentes | Yahoo Finance (`IBC.CR`) + Investing.com | Playwright | ⏳ |
| 48 | **IBC-components collector** — scrapeo automático con Playwright | Yahoo Finance | Playwright | ⏳ |
| 49 | **Historial por ticker venezolano** — OHLC 6 meses para top/bottom | Yahoo Finance | yfinance | ⏳ |

**Acción:** Crear `src/collectors/ibc_components_playwright.py` que descargue los datos históricos de cada componente del IBC desde Yahoo Finance/Investing.com con Playwright.

### 🔴 7.2 Gacetas Oficiales Recientes

| # | Tarea | Fuente | Método | Estado |
|---|-------|--------|--------|--------|
| 50 | **Ubicar gacetas últimos 7 días** — descargar PDFs | Gaceta Oficial | API/HTML | ⏳ |
| 51 | **OCR masivo** — procesar todas las gacetas pendientes | PDFs | PyMuPDF + Tesseract | ⏳ |

### 🔴 7.3 Noticias con Playwright

| # | Tarea | Fuente | Método | Estado |
|---|-------|--------|--------|--------|
| 52 | **Noticias IBC** — scraping Yahoo Finance `IBC.CR` | Yahoo Finance | Playwright | ⏳ |
| 53 | **Playwright collector general** — donde sea posible, reemplazar requests | Múltiples | Playwright | ⏳ |

### 🟡 7.4 Riesgo Soberano — Verificar Factores

| # | Tarea | Fuente | Método | Estado |
|---|-------|--------|--------|--------|
| 54 | **Revisar factores de Riesgo Soberano** — cuánta data tiene cada componente | DB | Query | ⏳ |
| 55 | **Calibrar ponderaciones** — validar con datos reales | Análisis | Code | ⏳ |

### 🟡 7.5 SVAR — Recolectar Datos de Alta Frecuencia

| # | Tarea | Fuente | Método | Estado |
|---|-------|--------|--------|--------|
| 56 | **Descargar datos mensuales FRED** — Petróleo WTI/Brent, IPC global, tasas | FRED API | API REST | ⏳ |
| 57 | **Descargar datos trimestrales Banco Mundial/FMI** — PIB, balanza, inflación | World Bank DataBank / IMF | API | ⏳ |
| 58 | **Series históricas BCV** — PIB trimestral desde 1997, IPC mensual | BCV | Scraping | ⏳ |
| 59 | **OVF datos mensuales** — inflación y actividad continua | OVF | Scraping | ⏳ |
| 60 | **Consolidar base SVAR** — mínimo 50 observaciones mensuales | Unión fuentes | pandas | ⏳ |
| 61 | **Ejecutar SVAR** — ajustar modelo con datos reales + Cholesky restrictions | statsmodels | Code | ⏳ |

**Estructura de datos requerida para SVAR:**
```
Fecha (Index)  |  PIB/Actividad  |  Inflación IPC  |  Tipo de Cambio  |  Petróleo (exog)
2013-Q1        |  100.5          |  2.1%            |  6.30            |  105.2
2013-Q2        |  102.1          |  2.5%            |  6.30            |  98.4
...
2026-Q2        |  115.4          |  19.9%           |  36.80           |  72.1
```

### 🟡 7.6 Comparación Regional

| # | Tarea | Fuente | Método | Estado |
|---|-------|--------|--------|--------|
| 62 | **Integrar wbgapi en dashboard** — mostrar Venezuela vs LatAm | World Bank | wbgapi | ⏳ |
| 63 | **Activar tab Regional** — PIB, inflación, desempleo comparado | World Bank + CEPAL | Code | ⏳ |

### 🟡 7.7 Huecos de Información — Fill Gaps

| # | Tarea | Fuente | Método | Estado |
|---|-------|--------|--------|--------|
| 64 | **IAE Alert: inflación = 0** — revisar por qué sale en 0 | DB + IAE analyzer | Debug | ⏳ |
| 65 | **Macro indicators lentos** — cachear mejor en DB | World Bank, IMF, CEPAL | Code | ⏳ |
| 66 | **Recopilar más data de todas las fuentes** — ejecutar todos los collectors 7+ días | Todos | Scripts | ⏳ |

### 🟢 7.8 Noticias & Social Expandido

| # | Tarea | Fuente | Método | Estado |
|---|-------|--------|--------|--------|
| 67 | **Expandir subreddits** — r/economics, r/worldnews, r/investing, r/latam | Reddit | RSS/API | ⏳ |
| 68 | **Keywords Venezuela economy** — búsqueda por término | Reddit | Search | ⏳ |
| 69 | **Rate limiting** — evitar 429 Too Many Requests | Reddit/Zernio | Code | ⏳ |

### 🔴 7.9 Integrar Todo en Informes

| # | Tarea | Archivo | Estado |
|---|-------|---------|--------|
| 70 | **Social** — Reddit posts + sentimiento en informe | `periodic.py` | ✅ |
| 71 | **Fiscal** — Gacetas OCR + categorías en informe | `periodic.py` | ✅ |
| 72 | **IBC stocks** — componentes + tickers en informe | `periodic.py` | ✅ |
| 73 | **Macro analytics** — Riesgo, BOP, Deuda, Pronóstico | `periodic.py` | ✅ |

---

## 🔬 Fase 8: Modelos Econométricos Avanzados

### 8.1 Modelos de Cambio de Régimen

| # | Tarea | Descripción | Prioridad | Estado |
|---|-------|-------------|-----------|--------|
| 74 | **Markov-Switching (MS)** — MS-ARIMA para identificar regímenes de inflación |statsmodels.tsa.regime_switching | Alta | ⏳ |
| 75 | **TAR/SETAR** — Modelos de Umbral (brecha cambiaria como variable umbral) | Code | Media | ⏳ |
| 76 | **TVECM** — Corrección de Error con Umbral (no lineal, velocidad de corrección variable) | statsmodels | Alta | ⏳ |

### 8.2 Modelos Multivariados Avanzados

| # | Tarea | Descripción | Prioridad | Estado |
|---|-------|-------------|-----------|--------|
| 77 | **GARCH Multivariado (DCC-GARCH)** — transmisión de volatilidad entre mercados | arch o ccgarch | Alta | ⏳ |
| 78 | **SVAR con restricciones estructurales** — shocks de oferta/demanda identificados | statsmodels.svar | Alta | ⏳ |
| 79 | **Cointegración con quiebres estructurales** — Gregory-Hansen test | statsmodels | Media | ⏳ |

### 8.3 ML Híbridos

| # | Tarea | Descripción | Prioridad | Estado |
|---|-------|-------------|-----------|--------|
| 80 | **ARIMA + ML (híbrido)** — SARIMA para lineal + XGBoost para residuos | sklearn + statsmodels | Alta | ⏳ |
| 81 | **LSTM para series temporales** — Deep Learning para inflación/tipo de cambio | tensorflow/keras | Media | ⏳ |
| 82 | **XGBoost + SHAP** — interpretabilidad de nowcasting | shap | Media | ⏳ |

### 8.4 Descomposición y Filtrado

| # | Tarea | Descripción | Prioridad | Estado |
|---|-------|-------------|-----------|--------|
| 83 | **Filtro HP** — tendencia vs ciclo del PIB | statsmodels | Alta | ⏳ |
| 84 | **Filtro de Kalman** — espacio de estados macro | statsmodels | Media | ⏳ |
| 85 | **Descomposición estacional (X-13ARIMA)** — series ajustadas | statsmodels | Media | ⏳ |

### 8.5 Causalidad y Panel

| # | Tarea | Descripción | Prioridad | Estado |
|---|-------|-------------|-----------|--------|
| 86 | **Granger en dominio frecuencia** — causalidad a corto/largo plazo | statsmodels | Media | ⏳ |
| 87 | **Datos de panel** — inflación regional por estados/ciudades | statsmodels | Baja | ⏳ |

---

## 🔧 Fase 9: Infraestructura & Calidad

### 9.1 Organización de Código

| # | Tarea | Descripción | Prioridad | Estado |
|---|-------|-------------|-----------|--------|
| 88 | **Dividir analyzers/** — separar en `analyzers/`, `ai/`, `reporting/` | Refactor | Media | ⏳ |
| 89 | **Config simplificada** — LLM chain como lista en vez de LLM1..LLM8 | Refactor | Media | ⏳ |
| 90 | **Revisar duplicidad src/alerts/** | Refactor | Baja | ⏳ |

### 9.2 Configuración & Seguridad

| # | Tarea | Descripción | Prioridad | Estado |
|---|-------|-------------|-----------|--------|
| 91 | **.env.example** — plantilla con todas las variables | Seguridad | Alta | ⏳ |
| 92 | **DATABASE_URL sin credenciales por defecto** | Seguridad | Alta | ⏳ |
| 93 | **robots.txt compliance** — verificar scrapers | Seguridad | Media | ⏳ |
| 94 | **Rate limiting en todos los collectors** | Seguridad | Media | ⏳ |

### 9.3 Manejo de Errores & Resiliencia

| # | Tarea | Descripción | Prioridad | Estado |
|---|-------|-------------|-----------|--------|
| 95 | **Retry con backoff exponencial** — decorator `@retry` para collectors | Resiliencia | Alta | ⏳ |
| 96 | **Reconexión DB con backoff** — no ocultar errores críticos | Resiliencia | Alta | ⏳ |
| 97 | **Modo offline/solo-lectura** — si DB no disponible | Resiliencia | Media | ⏳ |

### 9.4 Dependencias

| # | Tarea | Descripción | Prioridad | Estado |
|---|-------|-------------|-----------|--------|
| 98 | **Fijar versiones exactas** — requirements.txt con == | Reproducibilidad | Alta | ⏳ |
| 99 | **requirements-dev.txt** — separar dependencias de desarrollo | Organización | Media | ⏳ |
| 100 | **Evaluar poetry/uv** — gestión moderna de paquetes | Modernización | Baja | ⏳ |

### 9.5 CI/CD

| # | Tarea | Descripción | Prioridad | Estado |
|---|-------|-------------|-----------|--------|
| 101 | **GitHub Actions: tests** — ejecutar pytest en cada PR | CI/CD | Alta | ⏳ |
| 102 | **GitHub Actions: linting** — flake8/black en cada PR | CI/CD | Media | ⏳ |
| 103 | **GitHub Actions: typecheck** — mypy en cada PR | CI/CD | Media | ⏳ |

### 9.6 Documentación

| # | Tarea | Descripción | Prioridad | Estado |
|---|-------|-------------|-----------|--------|
| 104 | **CONTRIBUTING.md** — guía para contribuciones | Doc | Alta | ⏳ |
| 105 | **CODE_OF_CONDUCT.md** | Doc | Media | ⏳ |
| 106 | **CHANGELOG.md** — historial de cambios por versión | Doc | Media | ⏳ |
| 107 | **Diagrama ER de BD** — esquema visual | Doc | Media | ⏳ |
| 108 | **good-first-issue labels** — atraer contribuciones | Doc | Baja | ⏳ |

### 9.7 Dashboard Producción

| # | Tarea | Descripción | Prioridad | Estado |
|---|-------|-------------|-----------|--------|
| 109 | **Autenticación básica** — protección del dashboard | Producción | Media | ⏳ |
| 110 | **Caché Streamlit** — `@st.cache_data` en queries pesadas | Rendimiento | Alta | ⏳ |
| 111 | **Deploy con nginx proxy** | Producción | Media | ⏳ |

### 9.8 Docker

| # | Tarea | Descripción | Prioridad | Estado |
|---|-------|-------------|-----------|--------|
| 112 | **Dockerfile** — si no existe, crear para el proyecto | DevOps | Alta | ⏳ |
| 113 | **docker-compose.dev.yml** — entorno completo de desarrollo | DevOps | Media | ⏳ |

---

## 📋 Orden de Ejecución Recomendado

### Sprint 1: Datos IBC + Gacetas (Urgente)
1. #47 — Componentes IBC 6 meses (Playwright)
2. #50 — Ubicar gacetas últimos 7 días
3. #51 — OCR masivo de gacetas
4. #66 — Ejecutar collectors 7+ días

### Sprint 2: SVAR + Datos de Alta Frecuencia
5. #56-60 — Recolectar datos mensuales/trimestrales
6. #61 — Ajustar SVAR con datos reales
7. #64 — Fix IAE Alert inflación = 0
8. #54-55 — Verificar factores Riesgo Soberano

### Sprint 3: Modelos Avanzados
9. #74 — Markov-Switching
10. #77 — DCC-GARCH
11. #80 — ARIMA + ML híbrido
12. #83 — Filtro HP

### Sprint 4: Infraestructura
13. #91-92 — .env.example + DB segura
14. #95-96 — Retry + reconexión
15. #98-99 — Dependencias fijas
16. #101-103 — CI/CD

### Sprint 5: Documentación
17. #104 — CONTRIBUTING.md
18. #106 — CHANGELOG.md
19. #107 — Diagrama ER
20. #108 — good-first-issue

---

## 📦 Fase 2: Recolección de Datos (COMPLETADA)

### Coletores por Categoría

#### 🏛️ 2.1 Fuentes Oficiales Nacionales

| Collector | Fuente | Datos | Método | Estado |
|-----------|--------|-------|--------|--------|
| `bcv_collector.py` | BCV | Tasas, IPC, PIB | API comunitaria | ✅ |
| `ine_collector.py` | INE | Empleo, Pobreza | Scraping | ✅ |
| `mppef_collector.py` | MPPEF | Presupuesto, Deuda | Scraping | ⏳ |
| `seniat_collector.py` | SENIAT | Recaudación fiscal | Scraping | ⏳ |
| `sunaval_collector.py` | SUNAVAL | Mercado capitales | Scraping | ⏳ |

#### 💰 2.2 Fuentes Fiscales Gubernamentales

| Collector | Fuente | Datos | Método | Estado |
|-----------|--------|-------|--------|--------|
| `onapre_collector.py` | ONAPRE | Ejecución presupuestaria | Scraping + PDF | ✅ |
| `cgr_collector.py` | CGR | Informes de gestión | Scraping + PDF | ✅ |
| `gaceta_collector.py` | Gaceta Oficial | Gacetas (índice + PDF) | API + HTML | ✅ |
| `an_collector.py` | AN | Leyes de presupuesto | Scraping | ✅ |
| `caracas_collector.py` | Alcaldía | Gestión municipal | Scraping | ⏳ |

#### 🌍 2.3 Organismos Internacionales

| Collector | Fuente | Datos | Método | Estado |
|-----------|--------|-------|--------|--------|
| `worldbank_collector.py` | Banco Mundial | PIB, Desarrollo | API REST | ✅ |
| `imf_collector.py` | FMI | Proyecciones | API IMF (SDMX) | ✅ |
| `cepal_collector.py` | CEPAL | Estadísticas regionales | API CEPALSTAT | ✅ |
| `unsceb_collector.py` | UNSCEB | Gasto ONU por país | CSV | ✅ |

#### 🔬 2.4 Observatorios Independientes

| Collector | Fuente | Datos | Método | Estado |
|-----------|--------|-------|--------|--------|
| `ovf_collector.py` | OVF | Inflación independiente | Scraping | ✅ |
| `ove_collector.py` | OVE | Análisis sectorial | Scraping | ⏳ |
| `ucab_collector.py` | UCAB IIES | Proyecciones | Scraping | ⏳ |

#### 🛢️ 2.5 Sector Energético

| Collector | Fuente | Datos | Método | Estado |
|-----------|--------|-------|--------|--------|
| `pdvsa_collector.py` | PDVSA | Producción oficial | Scraping | ✅ |
| `opec_collector.py` | OPEP | Producción secundaria | API/Scraping | ✅ |
| `eia_collector.py` | EIA | Estimaciones | API/Scraping | ⏳ |

#### 💹 2.6 Mercados Financieros

| Collector | Fuente | Datos | Método | Estado |
|-----------|--------|-------|--------|--------|
| `bvc_collector.py` | BVC/Yahoo | IBC, Acciones | yfinance | ✅ |
| `binance_collector.py` | Binance | Precio USDT/VES | API P2P | ✅ |
| `dolar_paralelo_collector.py` | BCV Bancos | Tasas 12 bancos + BCV | pyDolarVenezuela | ✅ |
| `ibc_components_collector.py` | Investing.com | 8 componentes IBC | Web scraping | ✅ |
| `ibc_stocks_collector.py` | Yahoo Finance | Tickers venezolanos | yfinance | ✅ |

#### 📰 2.7 Noticias y Redes Sociales

| Collector | Fuente | Datos | Método | Estado |
|-----------|--------|-------|--------|--------|
| `rss_collector.py` | Portales VE | Noticias económicas | RSS | ✅ |
| `reddit_collector.py` | Reddit | Sentimiento | RSS público | ✅ |
| `twitter_collector.py` | Twitter/X | Sentimiento | API v2 | ⏳ |

#### 📋 2.8 Encuestas Ciudadanas

| Collector | Fuente | Datos | Método | Estado |
|-----------|--------|-------|--------|--------|
| `survey_collector.py` | Google Forms → Sheets | Respuestas de encuestas | gspread | ✅ |

---

## 📦 Fase 3: Análisis (COMPLETADA)

- [x] Módulo econométrico (SARIMA, VECM, GARCH)
- [x] Pruebas de estacionariedad
- [x] Diagnósticos de residuos
- [x] Regresión Newey-West

---

## 📦 Fase 6: Análisis Macro (COMPLETADA)

| # | Módulo | Archivo | Estado |
|---|--------|---------|--------|
| 31 | Nowcasting | `analyzers/nowcasting.py` | ✅ |
| 32 | Alertas | `alerts/manager.py` | ✅ |
| 33 | Regional | `analyzers/regional.py` | ✅ |
| 34 | Gráficos Avanzados | `dashboard/components/advanced_charts.py` | ✅ |
| 35 | IAE | `analyzers/iae.py` | ✅ |
| 36 | Cache Macro | `macro_indicators` + `refresh_macro.py` | ✅ |
| 37 | SVAR | `analyzers/svar.py` | ✅ |
| 38 | Phillips | `analyzers/phillips.py` | ✅ |
| 39 | Balanza Pagos | `analyzers/balance_of_payments.py` | ✅ |
| 40 | Riesgo País | `analyzers/sovereign_risk.py` | ✅ |
| 41 | Deuda Pública | `analyzers/public_debt.py` | ✅ |
| 42 | Pronóstico Integral | `analyzers/integrated_forecast.py` | ✅ |
| 43 | Panel Sostenibilidad | `dashboard/components/sustainability_panel.py` | ✅ |

---

## 📈 Métricas de Progreso

| KPI | Meta | Actual | Estado |
|-----|------|--------|--------|
| Collectors implementados | 28 | 28 ✅ | ✅ |
| Tests unitarios | > 300 | 341 ✅ | ✅ |
| Cobertura de fuentes | 24+ | 24+ | ✅ |
| Dashboard tabs | 8 | 8 ✅ | ✅ |
| Informes PDF | 6 cadencias | 6 ✅ | ✅ |
| Scheduler jobs | 11 | 11 ✅ | ✅ |
| Modelos macro | 8 | 8 ✅ | ✅ |

---

## 🏆 Criterios de Éxito

### Éxito Técnico
- [ ] Sistema ejecutándose 99% del tiempo
- [ ] Latencia de datos < 5 minutos
- [ ] Cobertura de tests > 80%
- [ ] Manejo de errores robusto (retry, backoff)

### Éxito de Datos
- [ ] 15+ fuentes de datos activas
- [ ] 4+ fuentes fiscales integradas
- [ ] Validación multi-fuente funcionando
- [ ] Datos actualizados diariamente/semanalmente
- [ ] 2+ encuestas activas con respuesta continua
- [ ] Componentes IBC con 6 meses de histórico
- [ ] Gacetas Oficiales OCR de últimos 7+ días

### Éxito de Análisis
- [ ] SVAR ajustado con datos reales (50+ observaciones)
- [ ] Markov-Switching implementado
- [ ] ARIMA + ML híbrido funcionando
- [ ] Filtro HP del PIB
- [ ] Cointegración con quiebres

### Éxito de Infraestructura
- [ ] CI/CD con GitHub Actions
- [ ] CONTRIBUTING.md publicado
- [ ] .env.example en repo
- [ ] Dockerfile funcional
- [ ] Rate limiting en collectors

---

**Roadmap actualizado: Agosto 2026**
**Versión: 9.0**
**Incluye: 28 collectors + Dashboard 8 tabs + 341 tests + 8 modelos macro + 113 tareas pendientes**
