[x] Mapear arquitectura actual: main.py, scheduler, config, docker-compose, .env → §II (A-C)
[x] Auditar fallas silenciosas (except/try vacíos, fallbacks ocultos) → §III (101-138)
[x] Auditar valores hardcoded que afectan resultados → §I (1-100)
[x] Revisar dependencia Railway y cómo reemplazarla por n8n local → §IV
[x] Revisar seguridad/privacidad local (secretos, exposición de puertos) → §II-C
[x] Proponer plan de mejora concreto → §V

Estado: investigación cerrada el 04-11-2026. n8n verificado activo (2.39.7, `/healthz` = 200, publicado en 0.0.0.0:5678). No se modificó código fuente; solo este informe.




Informe: valores HARDCODED que pueden afectar los resultados
Alcance: src/, main.py, .env / .env.example / src/config.py. Solo lectura. Rutas relativas al repo C:\Users\DeadW\dev\economia-venezuela.
1. FALLBACKS / VALORES DUMMY que sustituyen datos reales → ALTA
#	Archivo:línea	Valor	Por qué sesga
1	src/dashboard/macro_data.py:393	return 70.0  # Fallback razonable	Si el CSV Brent y OPEP fallan, todo el análisis de balanza de pagos/escenarios usa Brent=70 sin avisar en la UI
2	src/dashboard/macro_data.py:409	return 1.08 (producción mbd)	Índice de riesgo soberano y deuda/PIB dependen de este valor ficticio
3	src/dashboard/macro_data.py:425	return 12.7e9 (reservas)	Feed _reserves de deuda/cobertura
4	src/dashboard/macro_data.py:439	return 2.0e9 (importaciones/mes)	Calcula meses de cobertura de reservas
5	src/dashboard/macro_data.py:453	return 5.8 (% déficit PIB)	Entra a informes periódicos
6	src/dashboard/macro_data.py:472	return 94e9 (PIB)	Denominador de deuda/PIB y de ratios regionales
7	src/dashboard/macro_data.py:486	return 150e9 (deuda total)	Dispara/neutraliza alertas de sostenibilidad
8	src/analyzers/reports/periodic.py:515-517	70.0, 1.08 / 12.7e9, 2.0e9 / 94e9, 150e9, 5.8	Duplica los defaults de macro_data dentro de un except Exception: silencioso; el informe PDF/MD se publica con cifras de "cierre 3T 2026" sin señal de proveniencia
9	src/analyzers/reports/periodic.py:521	_brecha = 30.0  # Default	Brecha cambiaria del informe = 30% si la DB está caída
10	src/analyzers/reports/periodic.py:531	_inflation = 10.0  # Default mensual	Inflación mensual inventada alimenta IntegratedForecaster
11	src/dashboard/components/sustainability_panel.py:110	spread = 30.0	Igual 30% pero en otro módulo → puede divergir del informe
12	src/dashboard/app.py:1364-1366	sentiment_score = 50; news_score = 50	"Neutral" hardcodeado entra al índice de riesgo cuando faltan datos
13	src/dashboard/app.py:1060,1076	_volatility = 0.0, _sent_vol, _survey_disp, _forecast_err = 0.0,...	Volatilidad 0 ⇒ índice de riesgo subestimado silenciosamente
14	src/analyzers/nowcasting.py:178,279	fillna(0) sobre features	Imputa 0 a rezagos faltantes → sesga RandomForest y predicción de inflación/PIB
2. PESOS, COEFICIENTES Y FACTORES DE NEGOCIO escondidos en funciones → ALTA / MEDIA
#	Archivo:línea	Valor	Sesgo
15	src/analyzers/iae.py:45-49	pesos IAE: 0.30 / 0.25 / 0.20 / 0.15 / 0.10	Define por completo el Índice de Actividad Económica; no configurable ni documentado en env
16	src/analyzers/sovereign_risk.py:50-59	9 pesos (.18 .10 .18 .10 .10 .07 .08 .07 .12)	Compone el Riesgo Soberano; default_weights.get(col, 0.1) en :199 y :414 es otro default oculto
17	src/analyzers/sovereign_risk.py:234,255-261	escalas piecewise (30+(infl-10)*0.7, 20+(d/g-50)*0.6, …)	Transformación de inflación/deuda a score 0-100 completamente arbitraria
18	src/analyzers/sovereign_risk.py:314,334,358	mezclas 0.6/0.4, 0.4/0.3/0.3, 0.3/0.3/0.4	Sub-índices compuestos
19	src/analyzers/sovereign_risk.py:133	abs(sentiment)*0.5 + 0.2 (cap 1.0)	Volatilidad sintética derivada del sentimiento
20	src/analyzers/sovereign_risk.py:263,367	baseline: float = 1.5 mbd	Normaliza producción petrolera
21	src/dashboard/app.py:1197,1201-1203	0.75 externa, 0.25/0.42/0.33 cortes	Reparte la deuda total sin fuente; alimenta DebtResult
22	src/dashboard/components/sustainability_panel.py:102	total_debt * 0.7	Contradice el 0.75 del #21 → dos dashboards muestran deuda externa distinta
23	src/analyzers/public_debt.py:208-209	medium*0.6, long*0.3 → "próximos 3y/5y"	Profilaxis de vencimientos con factor inventado
24	src/analyzers/public_debt.py:263,505-530	interest_rate 0.05/0.04/0.08/0.10, oil*1.3/*0.6, gdp 3/8/-2/-5	Escenarios de deuda determinísticos
25	src/analyzers/integrated_forecast.py:63-67,126-131	oil 60.0, gdp 3.0, infl 50.0, spread 30.0, TC 500.0, shock 20.0	Bases de todos los escenarios de pronóstico
26	src/analyzers/integrated_forecast.py:83-93,117-118	*0.3, *0.1, *0.5, ±0.8/1.2, ±0.85/1.15	Elasticidades y anchos de banda arbitrarios
27	src/analyzers/reports/periodic.py:627,631-633	otra vez 0.75 / 0.25/0.42/0.33	Tercera copia del reparto de deuda
28	src/analyzers/reports/periodic.py:660-662	base_gdp=3.0, base_exchange=_brecha+100 or 500	Proxy de TC ad-hoc (brecha+100) que cambia el pronóstico
29	src/analyzers/balance_of_payments.py:326-329,503	15.0 USD/barril, 33% regalía, 50% impuesto, 0.3 mbd	Define utilidad petrolera del Estado
30	src/analyzers/relevance.py:85-89,92	fuerte=3, débil=1, min_strong=1, min_weak=2	Decide qué noticias entran al pipeline (filtrado de datos)
31	src/collectors/surveys/utils.py:59-60	if 0 < num <= 1: num*100	Heurística: cualquier respuesta "0.8" se vuelve 80% → cambia KPIs de encuestas
3. UMBRALES DE CALIDAD / FILTROS en parsers y analizadores → ALTA / MEDIA
#	Archivo:línea	Valor	Sesgo
32	src/config.py:81 vs uso	SURVEY_QUALITY_THRESHOLD = 0.5 — 0 usos en el código (grep = 0 fuera de config)	El umbral documentado en .env.example:60 nunca se aplica: survey_collector.py:224 calcula quality_score pero no filtra → respuestas parciales entran a los KPIs
33	src/analyzers/reports/weekly.py:27,49	MAX_RATE_DEVIATION = 0.30	Filtra picos P2P >30% de la mediana; en semanas volátiles borra datos reales
34	src/analyzers/sentiment.py:107-109	±0.15 para positive/negative	Umbral de clasificación de sentimiento
35	src/analyzers/reports/pdf_report.py:527	±0.05 (¡otro umbral!)	PDF usa 0.05, dashboard app.py:833-834 y periodic.py:1070 usan 0.15 → etiquetas distintas para el mismo score
36	src/analyzers/surveys/contrast.py:17	tolerance: float = 5.0 pp	Decide si hay "brecha percepción vs realidad"
37	src/analyzers/surveys/indicators.py:196	min_responses: int = 1	Publica series semanales con 1 respuesta (el docstring recomienda ≥5)
38	src/dashboard/surveys_data.py:34	MIN_RESPONSES_SERIES = 3	Otra vez distinto (3 vs 1 vs 5)
39	src/analyzers/market_integration.py:26-27	MIN_RATE_POINTS = 20, MIN_INFLATION_POINTS = 12	Corta el forecast con poco histórico
40	src/analyzers/market_integration.py:86-87	rate_periods=30, inflation_periods=6	Horizonte de pronóstico fijo
41	src/analyzers/econometric/diagnostics.py:104	clean_resid[:5000]	Trunca residuos para normalidad
42	src/analyzers/econometric/diagnostics.py:162-171,204	DW "bueno" ∈ [1.5, 2.5]	Clasificación de autocorrelación
43	src/analyzers/econometric/volatility.py:237-241,320-324,355-361	cortes 20/50/100, 0.8/1.2/1.5, 20/40/60/80	Etiquetas de volatilidad/nerviosismo
44	src/alerts/manager.py:84-106	20%/50%, 30%/50%, 20%/50%, 5%/10%	Disparan alertas; no hay env para ellos
45	src/dashboard/theme.py:44	threshold_low=40.0, threshold_high=60.0	Colores KPI
46	src/analyzers/phillips.py:346-347	inflation_threshold=20.0, unemployment_threshold=10.0	Define "episodios de estanflación"
47	src/collectors/fiscal/gaceta_ocr.py:209	total_keywords * 0.1	Fórmula de "confianza" OCR arbitraria
48	src/analyzers/reports/periodic.py:762-764	±2% week vs month	Heurística de tendencia del informe
49	src/analyzers/reports/periodic.py:474	idx > len(t)*0.3	Recorte de texto LLM
4. PARÁMETROS DE MODELOS / SEEDS → MEDIA
#	Archivo:línea	Valor	Sesgo
50	src/analyzers/nowcasting.py:156	RandomForest(n_estimators=100, max_depth=5, random_state=42)	Hiperparámetros fijos, sin búsqueda; 42 es el único seed del repo
51	src/analyzers/nowcasting.py:265	n_estimators=50, max_depth=3, random_state=42	Otro conjunto distinto para PIB
52	src/analyzers/svar.py:172,204	n_boot=100, np.random.normal(0, 0.1, …) sin seed	La IRF del SVAR no es reproducible entre corridas → intervalos cambian en cada ejecución
53	src/analyzers/econometric/forecasting.py:68-69,326	order=(1,1,1), seasonal=(1,1,1,12)	SARIMA por defecto sin selección automática (salvo búsqueda parcial en :189)
54	src/analyzers/econometric/forecasting.py:299	z = 1.96 / 1.645 / 1.28	Solo 3 niveles; cualquier otro nivel cae a 1.28
55	src/analyzers/econometric/regression.py:72,455 / causality.py:85,252,405 / diagnostics.py:74	significance_level=0.05, maxlags=4, max_lags=10 (causality.py:92,450)	Umbral de significancia y rezagos fijos en cada analizador
56	src/analyzers/econometric/regression.py:125-126	1.96 * robust_se	IC 95% fijo (no usa significance_level)
57	src/analyzers/phillips.py:85,164,238,303	mínimos 10/10/15/20 filas; intercept=0.0 en :334	Modelo sin intercepto ⇒ pendiente potencialmente sesgada
58	src/analyzers/llm.py:81,162 + collectors/news/llm_news_collector.py:258 + analyzers/surveys/report.py:159	temperature 0.0 / 0.1 / 0.3, max_tokens 300 / 2000 / 250	Salidas narrativas no comparables entre módulos
5. FECHAS Y AÑOS fijos → ALTA / MEDIA
#	Archivo:línea	Valor	Sesgo
59	src/analyzers/debt_parser.py:23	OCR_DIR = …/"data"/"ocr"/"bvc"/"2026"	En 2027 deja de leer la deuda (silenciosamente devuelve vacío)
60	src/dashboard/bvc_capitalization.py:19	igual …/"bvc"/"2026"	Ídem
61	src/dashboard/bvc_capitalization.py:161-171	ENERO→"2026-01" … JUNIO→"2026-06"	Cualquier CAPITALIZACION*.md de 2027 se etiqueta 2026 → serie histórica falsa y orden de meses roto
62	src/dashboard/fiscal_data.py:91,148	"gacetas"/"2026", "bvc"/"2026"	Panel fiscal vacío tras el cambio de año
63	src/analyzers/regional.py:101	time=range(2020, 2027)	Trunca datos CEPAL del 2027 en adelante
64	src/analyzers/regional.py:132,225	year: int = 2025	Comparación regional por defecto en año vencido
65	src/analyzers/reports/periodic.py:514	comentario "cierre 3T 2026" (ver #8)	Snapshot congelado que envejece
6. TIMEZONES → ALTA / MEDIA
#	Archivo:línea	Problema	Sesgo
66	src/collectors/surveys/survey_collector.py:47-53,71	Parsea "19/08/2026 14:30:00" (hora Caracas de Google Forms) a datetime naive	Luego surveys_data.py:101-103 _as_utc() hace replace(tzinfo=UTC) → +4 h de error: respuestas de las 20:00-23:59 de Caracas caen al día siguiente UTC y se asignan a otra semana/período
67	src/collectors/market/bcv_collector.py:71,96	datetime.now() naive como fecha de la tasa BCV	Fechas de la serie diaria dependen de la TZ de la máquina
68	src/cache/manager.py:337 (aware) vs :388 (datetime.now() naive)	Mezcla aware/naive en el mismo módulo	gc_cache y expiración pueden desalinearse en 1 h
69	src/analyzers/reports/weekly.py:531, periodic.py:1261, pdf_report.py:361	datetime.now() naive para nombrar weekly_YYYY-Www.md / cadence_YYYY-MM-DD.md	El informe semanal se rotura en frontera de semana (lunes 00:00 local vs UTC)
70	src/dashboard/app.py:66-70,113-119	date pickers con datetime.now() (local) y luego combinados con UTC en reports_section.py:171-179	Ventana de consulta desfasada 4-6 h
—	(no hay "America/Caracas" ni offset -04:00 en todo src/)	La TZ de negocio está implícita en la máquina	Toda corrección de día/semana es frágil
7. src/config.py vs .env.example vs .env → ALTA / MEDIA
#	Hallazgo	Detalle
71	Config muerta	SURVEY_QUALITY_THRESHOLD (config.py:81), SENTIMENT_ANALYSIS_HOUR (:74), DOLLAR_COLLECT_INTERVAL_MINUTES (:72), BCV_RATE_LIMIT/BINANCE_RATE_LIMIT/NEWS_API_RATE_LIMIT (:130-132), BCV_API_KEY (:26) → 0 referencias en el código. Se configuran en .env/.env.example:76-92 pero no hacen nada (el dólar se recolecta cada MARKET_COLLECT_INTERVAL_MINUTES, no cada 5)
72	config.py:89 MARKET_COLLECT_INTERVAL_MINUTES = 30	No existe ni en .env ni en .env.example (solo en readme.md:324) → cambiarlo por env no es posible sin leer docs
73	config.py:114-120 RSS_FEEDS, :92-108 (26 URLs base), :66 ZERNIO_API_KEY, :50-58 LLM5-8_*	Presentes en código, ausentes en .env.example
74	.env:56 GOOGLE_CREDENTIALS_PATH=C:\Users\DeadW\...json	Ruta absoluta de máquina en un env compartible
75	.env vs .env.example	.env lleva claves reales (Binance :21-22, OpenRouter :31, Z.AI :41, Gemini :46, Railway DB password :12, Context7 :97) y .env.example trae LLM1-4 pero no LLM5-8 ni MARKET_COLLECT_*
76	config.py:161-163	base_url="https://api.deepseek.com", model="deepseek-chat" hardcodeados en llm_providers()
77	config.py:75-76 vs src/scheduler/jobs.py:200-205	Horas de informes periódicos (diario 7h, semanal lun 8h, mensual 9h, trimestral 10h, semestral 11h, anual 12h) no pasan por settings, aunque el comentario dice "sobrescribible por settings"
8. URLs / endpoints hardcodeados en src/ (fuera de config.py) → MEDIA / BAJA
#	Archivo:línea	URL
78	src/collectors/news/llm_news_collector.py:32-40	9 queries RSS de Google News (venezuela+economía, +inflación, +dólar, …) → definen el universo de noticias; :44-45 DuckDuckGo; :60 FETCH_TIMEOUT = 20.0; :61 MAX_ARTICLES_PER_SOURCE = 20
79	src/collectors/social/reddit_collector.py:77,155,176,234,278	reddit.com/r/{sub}/…, api.zernio.com/reddit/…; :28-48 DEFAULT_SUBREDDITS/_SEARCH_SUBREDDITS (canal social hardcodeado); :66 FETCH_TIMEOUT = 15.0
80	src/collectors/market/ibc_history.py:18-19, ibc_components_collector.py:19, ibc_full_collector.py:90,221, ibc_components_yahoo.py:100,200	investing.com / datosmacro.expansion / es.finance.yahoo.com
81	src/collectors/market/consumo_collector.py:14,28-29, fiscal/cendas_collector.py:10,26, fiscal/an_collector.py:29,36,42	ansaes.com, atenasgc.com, cendas.org.ve, asambleanacional.gob.ve
82	src/scripts/backfill_rates.py:36-37	DEFAULT_CSV_URL = "https://www.usdt.com.ve/data/usdt-ves-historical.csv", DEFAULT_DAYS = 180 → fuente de backfill de la serie cambiaria
83	src/collectors/international/unsceb_collector.py:25	EXPENSES_CSV = "/assets/data/FS/…" (ruta interna de terceros)
84	src/collectors/http.py:25-26,39-40	DEFAULT_TIMEOUT = 15.0, stop_after_attempt(3), wait_exponential(0.5, max=4) — no usa settings.*_RATE_LIMIT
9. Límites de filas, ventanas y redondeos → MEDIA / BAJA
#	Archivo:línea	Valor
85	src/dashboard/app.py:1328,1475,1536	gates len(rates) >= 20 / 50 / 100
86	src/dashboard/app.py:1337,1483,1545	>= 10 / 20 / 50 filas
87	src/analyzers/reports/periodic.py:557,694,878	limit=200 / 200 / 5000; :340 limit=100
88	src/analyzers/reports/weekly.py:422-423	limit=50, limit=12 (IPC)
89	src/db/repositories.py:632,649,701	limit: int = 50/50/100
90	src/analyzers/econometric/forecasting.py:228,444	models[:10], [:5]
91	src/dashboard/surveys_data.py:32-33	DEFAULT_FREQ = "W", DEFAULT_DAYS = 90
92	src/dashboard/macro_data.py:18,32,88,120	CACHE_MAX_AGE_HOURS = 24, cache memoria 300 s, ttl_hours=24
93	src/analyzers/llm.py:29-30	DEFAULT_TIMEOUT_SECONDS = 60.0, CACHE_TTL_SECONDS = 3600
94	src/collectors/market/ibc_full_collector.py:87	datetime.now() - timedelta(days=30*months_ago)
95	src/collectors/market/ibc_stocks_collector.py:69-70,82	ventana -3/+1 días, best_diff = timedelta(days=999)
96	src/analyzers/balance_of_payments.py:471	imports_monthly * 12
97	src/analyzers/debt_parser.py:57-77	devuelve 0.0 cuando no parsea monto
10. Archivos de datos cacheados usados como fallback → MEDIA
#	Hallazgo	Detalle
98	src/dashboard/macro_data.py:363	Lee data/cvs.xls/Datos históricos Petróleo Brent.csv (no está en git: .gitignore:110 data/; git ls-files data/ = 0, pero hay 716 MB locales) → en otro equipo/contenedor el precio Brent cae directo al 70.0 del #1
99	src/analyzers/reports/periodic.py:736-738	Mismo CSV duplicado con dos nombres (uno con é escapada)
100	data/ocr/bvc/*.md, data/ocr/gacetas/*.md, data/cache/api/macro_*.json	Fuente de capitalización BVC, deuda (debt_parser.py:255,264,273,293), gacetas y macro; cache/manager.py:335 ttl_hours=24 pero macro_data y OCR no expiran por fecha → informes con datos congelados
Priorización resumida
- ALTA (corrige primero): #1-#14 (fallbacks numéricos silenciosos), #32 (umbral de calidad nunca aplicado), #66-#67 (timezone de encuestas/BCV), #59-#62 (año 2026 fijo), #71 (config muerta que hace creer que se controla intervalos/umbrales), #21-#22 (0.75 vs 0.7 contradictorios), #15-#16 (pesos de índices).
- MEDIA: pesos/coeficientes restantes (#17-#31), umbrales (#33-#49), parámetros econométricos y seed faltante (#50-#58), URLs y ventanas (#78-#97), datos cacheados (#98-#100).
- BAJA (cosmético/inflexibilidad): #45, #49, #88-#90, colores y max_tokens.


Informe de investigación — Orquestación actual (economia-venezuela) + n8n
Repositorio A: C:\Users\DeadW\dev\economia-venezuela (citas relativas al repo)
Repositorio B: C:\Users\DeadW\dev\n8n
A) economia-venezuela
1. Mapa de jobs / orquestación actual
Entrada: python main.py → main.py:81-109 (init DB, luego start_scheduler() main.py:50-78, y loop infinito while True: time.sleep(1) main.py:104-105; no levanta servidor HTTP). APScheduler BackgroundScheduler (main.py:61). Los 5 registradores se llaman en main.py:62-66. Scheduler NO se inicia si ENVIRONMENT == "test" (main.py:97).
Job (id)	Intervalo / cron
collect_market	intervalo MARKET_COLLECT_INTERVAL_MINUTES = 30 (default src/config.py:89; NO está en .env)
collect_surveys	intervalo SURVEY_COLLECT_INTERVAL_MINUTES (default 60 config.py:80; .env = 2 dígitos)
collect_news	NEWS_COLLECT_INTERVAL_HOURS * 60 (default 6 h config.py:73; .env = 1 dígito)
weekly_report	cron: WEEKLY_REPORT_DAY (.env = "sunday") + WEEKLY_REPORT_HOUR (.env = 1 dígito, default 8 config.py:75-76)
report_diario	cron 07:00 (_PERIODIC_CRON jobs.py:199-206)
report_semanal	cron lun 08:00 (jobs.py:201)
report_mensual	cron día 1 09:00 (jobs.py:202)
report_trimestral	cron meses 1,4,7,10 día 1 10:00 (jobs.py:203)
report_semestral	cron meses 1,7 día 1 11:00 (jobs.py:204)
report_anual	cron 1 ene 12:00 (jobs.py:205)
- Total: 10 jobs (3 interval + 7 cron). Todos con max_instances=1, coalesce=True, replace_existing=True + borrado previo explícito (jobs.py:109-111 etc.).
- Configuración muerta (sin job): DOLLAR_COLLECT_INTERVAL_MINUTES (config.py:72) y SENTIMENT_ANALYSIS_HOUR (config.py:74) — ninguna referencia en main.py ni jobs.py.
- Informes salen a data/reports/ (default): src/analyzers/reports/periodic.py:1263, src/analyzers/reports/weekly.py:534.
- Existe además un gatillador manual dentro del dashboard (ver §5).
2. docker-compose.yml / docker-compose.dev.yml
docker-compose.yml (producción):
- app build ., ports "8000:8000" (:8-9), command default del Dockerfile (python main.py), volúmenes ./src, ./data (:14-15), red bridge economia-network.
- dashboard command streamlit run src/dashboard/app.py --server.port=8501 (:26), ports "8501:8501" (:28).
- db TimescaleDB pg14, POSTGRES_PASSWORD: password (:48), ports "5432:5432" (0.0.0.0) (:49-50), volumen postgres_data.
- redis alpine, ports "6379:6379" (0.0.0.0) (:60-61), volumen redis_data.
- prometheus ports "9090:9090" (:71-72) montando ./config/prometheus.yml (:74) → el directorio config/ NO existe en el repo (verificado) ⇒ este servicio fallará.
- grafana ports "3000:3000" (:83-84) con GF_SECURITY_ADMIN_PASSWORD=admin hardcodeado (:86).
- Sin healthchecks en ningún servicio. Sin expose/127.0.0.1:: todo publicado en todas las interfaces.
docker-compose.dev.yml:
- Solo db (5432:5432 :12-13), redis (6379:6379 :23-24), app (python main.py, 8000:8000 :32,38-39), dashboard (8501:8501 con --server.runOnSave=true :53,59-60). Red economia-network-dev.
- Mismos password hardcodeado (:11, :34), tampoco hay healthchecks, también publica DB/Redis a 0.0.0.0.
3. Dockerfile raíz
Dockerfile: base python:3.10-slim (:1), instala gcc/libpq (:7-10), pip install -r requirements.txt (:14), COPY . . (:17) — copia el .env dentro de la imagen (no hay .dockerignore; verificar antes de build), EXPOSE 8000 8501 (:20), CMD ["python","main.py"] (:23).
4. Referencias a Railway
- .env.example:37 → LLM2_BASE_URL=https://omniroute-production-a409.up.railway.app/v1.
- .env real: LLM2_BASE_URL tiene exactamente 51 caracteres = la misma URL de Railway (confirmado por longitud; además DATABASE_URL contiene host "railway" y sslmode).
- readme.md:154 → "Base de Datos: PostgreSQL (Railway)".
- docs/review.md:316 y :338 → "Despliegue en Railway… 24/7".
- knowledge.md:683, 720, 742-755 → notas de red/geo-blocking asumiendo scheduler en Railway (Binance P2P bloqueado por IP de EE.UU.).
- reports/CODE_HEALTH_AUDIT_2026-08-21.md:101-102,178,203; reports/INFORME_ESTADO_PROYECTO_2026-08-21.md:44,110,116; reports/INFORME_3T_2026...:354 (caída de DB Railway ⇒ fallback SQLite local).
- opencode.jsonc:27-33 → MCP server railway habilitado (railway mcp).
- No hay CI (no existe .github/workflows) ni railway.toml/railway.json.
5. Dashboard Streamlit — exposición y autenticación
- Arranque: streamlit run src/dashboard/app.py (readme.md:200), puertos por config: DASHBOARD_PORT=8501/API_PORT=8000 (config.py:123-124).
- NO hay autenticación: cero coincidencias de st.secrets, password, login, auth en src/dashboard/app.py (grep); no existe directorio .streamlit/ (ni secrets.toml); src/security/__init__.py está vacío (0 líneas).
- st.set_page_config sin nada de seguridad (app.py:45-51).
- Bind: no se fija server.address en ningún lado ⇒ por defecto de Streamlit (1.62 instalado) server.address = None ⇒ escucha en todas las interfaces, y el compose publica 8501:8501 ⇒ accesible desde la LAN.
- Riesgo añadido: panel "⚡ Recolectores" en el sidebar ejecuta procesos con un botón, sin auth:
- mapa de comandos app.py:92-100 (collect_market, collect_news, backfill_ibc, collect_surveys, collect_gacetas, refresh_macro, generate_report);
- subprocess.run([sys.executable, "-m", f"src.scripts.{script}", ...], timeout=120) en app.py:127-143.
- collect_gacetas no existe (src/scripts/collect_gacetas.py ausente) ⇒ ese botón siempre falla (app.py:97).
- XSRF/CORS de Streamlit quedan en default (activados); no hay capa de login.
6. .env real (solo nombres/estado; sin valores)
Está gitignored (.gitignore:54 y :74) y no trackeado por git (git ls-files --error-unmatch .env → error). 97 líneas.
- Llenos (parecen reales): APP_NAME, APP_VERSION, ENVIRONMENT, DEBUG, DATABASE_URL (111 chars, host Railway + sslmode), REDIS_URL, BINANCE_API_KEY (64), BINANCE_API_SECRET (64), LLM1_API_KEY/BASE_URL/MODEL, LLM2_API_KEY/BASE_URL(URL Railway)/MODEL, LLM3_*, LLM4_*, GOOGLE_CREDENTIALS_PATH (ruta local a …\.config\economia-venezuela-….json), SURVEY_COLLECT_INTERVAL_MINUTES, SURVEY_QUALITY_THRESHOLD, los 4 SURVEY_*_FORM_ID/SHEET_ID, REDDIT_USER_AGENT, DOLLAR_COLLECT_INTERVAL_MINUTES, NEWS_COLLECT_INTERVAL_HOURS, SENTIMENT_ANALYSIS_HOUR, WEEKLY_REPORT_DAY, WEEKLY_REPORT_HOUR, DASHBOARD_PORT, API_PORT, LOG_LEVEL, BCV/BINANCE/NEWS_RATE_LIMIT, CONTEXT7_API_KEY (43).
- Vacíos: BCV_API_KEY, DEEPSEEK_API_KEY, NEWS_API_KEY, REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, TWITTER_BEARER_TOKEN.
- No definidos en .env (usan default): MARKET_COLLECT_INTERVAL_MINUTES (30), LLM5..LLM8_*, ZERNIO_API_KEY.
- .env.example añade CONTEXT7_API_KEY vacío (:96); LLM5-8 solo existen en config.py:47-58.
7. Entry points CLI invocables (para n8n)
Principales (los usa el propio scheduler ⇒ son los candidatos naturales de n8n):
Comando exacto
python -m src.scripts.collect_market [--period 2026-08]
python -m src.scripts.collect_news [--feeds ... --per-feed-limit N --reddit-limit N]
`python -m src.scripts.collect_surveys [--segment persona_comun
python -m src.scripts.generate_report --cadence diario|semanal|mensual|trimestral|semestral|anual --format md,pdf [--no-ai] [--since] [--until] [--output-dir]
python -m src.scripts.backfill_ibc [--days N | --since --until]
python -m src.scripts.backfill_rates [--days N --csv RUTA --no-save]
python -m src.scripts.refresh_macro [--force]
python -m src.scripts.cache_manager …
Todos requieren DB (session_scope) salvo cache_manager. El informe semanal del job usa generate_weekly_report() (lib, src/analyzers/reports/weekly.py:540) — CLI equivalente: python scripts/generate_weekly_report.py (scripts/generate_weekly_report.py:13) pero tiene sys.path.insert(0, "C:\\Users\\DeadW\\dev\\economia-venezuela") hardcodeado en la línea 4.
Secundarios / one-shot en scripts/ (todos con sys.path implícito, correr desde la raíz):
run_periodic_report.py (prueba del snapshot semanal, sin __main__ — se ejecuta importando), run_llm_news_collector.py (collector LLM de noticias → BD, :11), analyze_news_sentiment.py (sentimiento sobre BD, :14), parse_ibc_history.py (histórico IBC → BD, :32), download_all.py/download_all_v2.py/download_known.py/download_playwright.py (descarga masiva de fuentes oficiales), crawl_sources.py/quick_crawl.py (crawl de gacetas/INE), extract_fusioncharts.py, check_indexmundi*.py (ad-hoc, sin __main__).
Dashboard: streamlit run src/dashboard/app.py (readme.md:200).
8. Tests
- Ejecución: pytest (o pytest -v, pytest tests/<archivo>.py, --cov=src) — CONTRIBUTING.md:28-43. No hay pytest.ini/pyproject.toml/setup.cfg/tox.ini. pytest 7.4.4 en requirements.txt.
- ~341 tests (readme.md:3, :314), 20 archivos tests/test_*.py.
- tests/conftest.py:7-14: único fixture autouse = limpiar caché de LLM. Sin fixtures de red/DB real.
- Red: mockeada con monkeypatch de httpx.get/post (p. ej. tests/test_backfill_rates.py:99, tests/test_llm.py:41-58); todos los test_collectors_*/test_*_pipeline contienen mock/monkeypatch.
- DB: SQLite en memoria/tmp_path (tests/test_db_surveys.py:29-30, tests/test_market_data.py:28, tests/test_news_pipeline.py:39, tests/test_cli_surveys.py:57), y session_scope monkeypatcheado (tests/test_market_data.py:162).
- Sin pytest.mark (no hay markers/skips de red).
- ⇒ Los tests corren offline, aptos para un paso de CI/pre-flight de n8n.
B) n8n (C:\Users\DeadW\dev\n8n)
1. docker-compose.yml
- Imagen docker.n8n.io/n8nio/n8n (docker-compose.yml:3), container_name: n8n.
- ports: "5678:5678" ⇒ publicado en 0.0.0.0 (confirmado con docker ps: 0.0.0.0:5678->5678/tcp, contenedor Up).
- Volumen n8n_data:/home/node/.n8n external: true (:7-8, 26-28) — ya existe (docker volume ls).
- Variables: N8N_UNVERIFIED_PACKAGES_ENABLED=true (:11), N8N_RUNNERS_MODE=internal + timeout 300 (:13-14), límites de compresión (:16-17), AGNES_API_KEY=${AGNES_API_KEY} (:20), N8N_BLOCK_ENV_ACCESS_IN_NODE=false (:23).
- Sin N8N_ENCRYPTION_KEY, sin N8N_HOST/PORT/PROTOCOL, sin flags de auth, sin healthcheck, restart: unless-stopped (:24). Credenciales cifradas con la key generada dentro del volumen (si se pierde el volumen se pierden las credenciales).
- .env: solo AGNES_API_KEY (len 51 ⇒ real). .env en .gitignore del folder; la carpeta n8n NO es repo git.
2. workflows/
Archivo	Nombre
workflows/tiktok-tech-v7.json	"TikTok Tech v7 - Omnimargen"
workflows/flow-tog-admin-completo.json	"Flow TOG Admin - Completo"
Ningún workflow relacionado con economía de Venezuela (0 workflows para este proyecto).
3. README / arranque (.bat)
- iniciar-n8n.bat: verifica/abre Docker Desktop → docker compose up -d → http://localhost:5678 (solo n8n; no levanta Ollama ni servicios).
- iniciar.bat: levanta 7 servicios: Ollama (OLLAMA_HOST=0.0.0.0, :11434), tikvid (:8000), n8n (:5678), Video Composer (:3002), Video Downloader (:3001), Telegram Bot (:3000), Flow Publisher (:3003).
- iniciar-flow.bat: solo n8n + Telegram Bot + Flow Publisher. detener.bat / detener-flow.bat (docker compose down + taskkill). start.bat = alias de iniciar.bat.
- README documenta export/import de workflows vía docker exec n8n n8n export:workflow|import:workflow (README.md:82-90) y MCP de n8n con token Bearer en opencode.json (README.md:97-112).
- Nota operativa clave (README.md:126-129): desde el contenedor, los servicios del host se llaman con host.docker.internal (no 172.17.0.1).
C) Exposiciones de red / seguridad encontradas
economia-venezuela
1. docker-compose.yml: DB 5432 (:50), Redis 6379 (:61), Prometheus 9090 (:72), Grafana 3000 (:84) y dashboard 8501 (:28) publicados en 0.0.0.0; idem dev (docker-compose.dev.yml:13,24,39,60). Sin auth en DB/Redis.
2. Password de Postgres password hardcodeado (docker-compose.yml:11,30,48; dev.yml:11,34,55; default config.py:20); Grafana admin (docker-compose.yml:86).
3. Dashboard Streamlit sin autenticación (ver §5) + ejecuta subprocess de recolectores con un botón (app.py:123-152).
4. Sin healthchecks en ningún compose; servicio app publica 8000 pero main.py no abre puerto (no hay instancia FastAPI en src/) ⇒ puerto muerto; Prometheus monta ./config/prometheus.yml inexistente.
5. .env (gitignored, ok) pero con DB en Railway y LLM2 en Railway (dependencia cloud); GOOGLE_CREDENTIALS_PATH con ruta absoluta local (C:\Users\DeadW\...).
6. MCP railway habilitado en opencode.jsonc:27-33.
7. src/security/__init__.py vacío: la "capa de seguridad" del proyecto es un placeholder.
8. No hay .dockerignore ⇒ .env se copia a la imagen (Dockerfile:17).
n8n
1. 5678 publicado en 0.0.0.0 (docker-compose.yml:5-6), sin N8N_ENCRYPTION_KEY ni configuración de acceso/contraseña en compose.
2. N8N_BLOCK_ENV_ACCESS_IN_NODE=false (:23) permite leer $env desde nodos (el workflow usa {{ $env.AGNES_API_KEY }}).
3. Token MCP Bearer en texto plano en n8n/opencode.json (JWT con exp implícito), con permisos de modificar workflows.
4. Colisiones de puerto con el stack de economía si ambos composes están arriba: 8000 (tikvid vs app) y 3000 (Telegram bot vs Grafana); además Ollama en 11434.
D) Estado de huecos para operar local/privado sin Railway
1. DB: cambiar DATABASE_URL (hoy host Railway + sslmode) por postgresql://postgres:password@localhost:5432/economia_ve (o sqlite:///data/economia_ve.db, soportado según src/db/session.py:10-12). También decidir REDIS_URL local.
2. LLM: LLM2_BASE_URL = URL Railway (.env.example:37) ⇒ reemplazar por endpoint local (p. ej. Ollama http://localhost:11434/v1 del stack n8n) o eliminar LLM2; revisar knowledge.md:742-755 (asume Railway para geo).
3. Privatizar puertos: publicar solo en 127.0.0.1 (db/redis/dashboard/n8n), quitar o arreglar prometheus/grafana (falta config/prometheus.yml).
4. Auth del dashboard: crear .streamlit/secrets.toml/login o ponerlo detrás de algo con auth (hoy src/security/ está vacío y el panel dispara subprocess).
5. Orquestador: migrar los 10 jobs de jobs.py a workflows n8n (tabla §A1) y dejar main.py sin scheduler (o solo init_db); n8n debe invocar los CLIs de §A7 — desde el contenedor: docker exec o red compartida + host.docker.internal (patrón ya usado en n8n/README.md:128-129).
6. Puerto API: API_PORT=8000 choca con tikvid (n8n); además no hay servidor que escuche en 8000 ni endpoints /health /ready (solo recomendados en reports/CODE_HEALTH_AUDIT_2026-08-21.md:178).
7. n8n hardening: fijar N8N_ENCRYPTION_KEY (+ backup de n8n_data), bind 127.0.0.1:5678, owner/auth activo, rotar el token MCP de opencode.json, valorar re-activar N8N_BLOCK_ENV_ACCESS_IN_NODE.
8. Fix menores: collect_gacetas inexistente en el panel (app.py:97); scripts/generate_weekly_report.py:4 con ruta absoluta hardcodeada; falta .dockerignore; sin CI (.github/workflows ausente) — pytest sirve como paso offline.
9. Volúmenes/datos: informes a data/reports/ (gitignored), volúmenes ./src,./data montados en ambos compose; verificar que el volumen externo n8n_data y los credentials sobrevivan al rediseño.
Nota: según AGENTS.md se usó graphify query (grafo graphify-out/graph.json, 2845 nodos) como primera pasada; el detalle de líneas salió de lectura directa. 

---

III) AUDITORÍA DE FALLAS SILENCIOSAS (101-138)
Alcance: todo `src/` + `main.py`. Método: conteo de `except` por archivo (≈235 líneas con la palabra `except`, incluye comentarios), lectura de cada bloque que devuelve un valor por defecto y clasificación por efecto: (a) el error se convierte en dato, (b) se convierte en "sin datos", (c) produce un modelo aparentemente válido, (d) desaparece de la observabilidad. Todo lo de esta sección es adicional a los fallbacks numéricos de §I: aquí el problema no es *qué* valor se usa, sino que **el fallo no deja rastro ni en el log ni en el resultado**.

Conteo de `except` por archivo (top): `reports/periodic.py` 25; `dashboard/macro_data.py` 17; `dashboard/app.py` 11; `scheduler/jobs.py` 10; `collectors/http.py` 8; `dashboard/ibc_data.py`, `dashboard/fiscal_data.py`, `social/reddit_collector.py`, `market/ibc_full_collector.py`, `market/ibc_components_yahoo.py` 7; `analyzers/svar.py`, `scripts/collect_market.py`, `news/llm_news_collector.py`, `db/repositories.py` 6.

3.1 El error se convierte en DATO (101-112)
| # | Archivo:línea | Qué se traga | Efecto |
|---|---|---|---|
| 101 | `analyzers/reports/periodic.py:512-517` | `except Exception:` **sin log** alrededor de los 7 fetchers macro | Sustituye 7 cifras (70.0 / 1.08 / 12.7e9 / 2.0e9 / 94e9 / 150e9 / 5.8) y el MD/PDF se publica como si fueran observadas. Es el único `except` del repo que no loguea nada y el de mayor impacto |
| 102 | `periodic.py:527-528` | `except Exception: pass` al leer la brecha | `_brecha = 30.0`; entra a riesgo soberano y a todos los escenarios |
| 103 | `periodic.py:537-538` | `except Exception: pass` al leer inflación | `_inflation = 10.0` mensual, que luego se anualiza ×12 (`:576`) |
| 104 | `periodic.py:560-561` | `pass` al calcular volatilidad | `_volatility = 0.0` ⇒ riesgo subestimado |
| 105 | `periodic.py:572-573` | `pass` al calcular incertidumbre | `_sent_vol/_survey_disp/_forecast_err = 0.0` |
| 106 | `dashboard/app.py:1056-1058` | `pass` al cargar capitalización BVC | `cap_for_risk = {}` ⇒ market_cap 0 en el índice |
| 107 | `app.py:1071-1073` | `pass` al calcular volatilidad | `_volatility = 0.0` |
| 108 | `app.py:1084-1086` | `pass` al calcular incertidumbre | 0.0 en los tres componentes |
| 109 | `app.py:1361-1366` | `sentiment_score = 50`, `news_score = 50` ("Neutral por defecto") y `iae.calculate_oil_component(1.08, 1.0)` | El IAE se compone con dos 50 fijos y producción fija; el score parece calculado |
| 110 | `dashboard/macro_data.py:125-131` (`_safe_fetch`) y 17 `except` más (`:57-59`, `:74-75`, `:88-90`, `:114-116`, `:121-123`, `:155-156`, `:172-173`, `:198-199`, `:215-216`, `:241-242`, `:258-259`, `:283-284`, `:308-309`, `:381-383`, `:390-391`) | Todas devuelven `None`/`pass`; 8 solo con `logger.debug` | Todo §I#1-#7 (Brent 70, 1.08 mbd, 12.7e9, 2.0e9, 94e9, 150e9, 5.8) entra sin que quede traza visible |
| 111 | `analyzers/sovereign_risk.py:113-115` | `except Exception: return 0.0` en `compute_volatility_from_rates` | Volatilidad 0 se suma como componente real del índice |
| 112 | `analyzers/debt_parser.py:74-77` y `dashboard/bvc_capitalization.py:46-49` | `except ValueError: return 0.0` | Monto no parseado se suma como 0 ⇒ total de deuda/capitalización subestimado sin aviso (ver §I#97) |

3.2 El error se convierte en "SIN DATOS" (113-126)
| # | Archivo:línea | Qué se traga | Efecto |
|---|---|---|---|
| 113 | `periodic.py:80-96, 130-171, 235-237, 250-252, 265-267, 330-332` | `logger.warning` + `{}`/`[]` | El informe se publica con secciones ausentes; el lector no distingue "no hay datos" de "la fuente falló" (sin provenance) |
| 114 | `periodic.py:408-410, 437-439` | IA no disponible ⇒ `""` | Informe sin resumen ni proyección, sin marca de degradación |
| 115 | `analyzers/reports/weekly.py:383-385` | ídem informe semanal | Mismo efecto, sin bandera en el resultado |
| 116 | `analyzers/surveys/report.py:134-136, 162-164` | ídem informes de encuestas | Mismo efecto |
| 117 | `analyzers/public_debt.py:380-383` | `logger.debug` + `return {}` | Con `LOG_LEVEL=INFO` es invisible: la deuda cae a defaults sin alerta |
| 118 | `dashboard/fiscal_data.py:40-42, 63-65, 84-86, 140-142, 197-199` | `logger.debug` + `[]` | Panel fiscal vacío indistinguible de "no hay gacetas/leyes" |
| 119 | `periodic.py:719-721, 729-731, 780-782` | `logger.debug` en nowcasting, comparativa regional y outlook petrolero | Tres secciones del informe pueden desaparecer sin un solo warning |
| 120 | `analyzers/regional.py:110-127` | `except ImportError` (warning) y `except Exception: continue` por indicador | Comparativa parcial sin declarar cobertura; luego `DataFrame()` vacío |
| 121 | `analyzers/llm.py:185-186` | `except LLMError: return None` | El llamador no distingue "LLM caído" de "sin contenido"; idéntico patrón en `weekly.py:383`, `surveys/report.py:162`, `periodic.py:408/437` |
| 122 | `dashboard/social_data.py:55-57, 129-135, 167-169, 197-199`; `news_data.py:32-35, 46-48, 59-61`; `market_data.py:40-42, 56-58, 69-71, 130-132`; `ibc_data.py` (7 funciones) | ~20 funciones: `logger.warning` + `[]`/`{}`/`None`/`DataFrame()` | El dashboard no distingue DB caída de serie vacía. Solo `components/news_section.py:66-70` y `components/survey_section.py:116-120` avisan al usuario; el resto pinta 0 |
| 123 | `dashboard/app.py:1585-1587` | `except Exception: st.info("Módulo regional disponible pero sin datos aún")` | Un error real se presenta como "sin datos" |
| 124 | `dashboard/components/reports_section.py:44-46` | `except Exception: return "*No se pudo leer {archivo}*"` | Sin log; el informe existe pero el panel dice que no se pudo leer |
| 125 | `cache/manager.py:172-175` | `return None` | Igual retorno para "no descargado" y "descarga falló" |
| 126 | `analyzers/econometric/diagnostics.py:332-337` | CUSUM falla ⇒ `DiagnosticResult(statistic=0)` | Se reporta un estadístico 0 como si el test hubiera corrido |

3.3 El error se convierte en MODELO VÁLIDO (127-132)
| # | Archivo:línea | Qué se traga | Efecto |
|---|---|---|---|
| 127 | `analyzers/econometric/forecasting.py:183-185, 214-216` | `except: continue` (bare) en la grilla ARIMA/SARIMA | Si todos los ajustes fallan, `models = []` y `best_aic=None` sin warning; el llamador no distingue "sin modelos" de "datos insuficientes". Además el `except` desnudo se traga `KeyboardInterrupt`/`SystemExit` |
| 128 | `analyzers/econometric/volatility.py:173-178` | `except:` (bare) al ajustar EGARCH | `egarch_result=None`, `has_leverage=False` ⇒ se informa "no hay efecto apalancamiento" cuando en realidad el modelo no ajustó |
| 129 | `analyzers/svar.py:105-108` | `except Exception: optimal_lags = 1` | El criterio de rezagos cae a 1 en silencio y todo el SVAR se estima con ese valor |
| 130 | `analyzers/svar.py:205-208, 365-368` | `except: continue` dentro del bootstrap/IRF | Descarta iteraciones: los intervalos se calculan con menos de las `n_boot=100` declaradas, sin reportarlo |
| 131 | `analyzers/econometric/forecasting.py:297-300` | `z` por defecto 1.28 para niveles no contemplados | Un IC 90% se etiqueta con el nivel pedido (ver §I#54) |
| 132 | `analyzers/phillips.py:334` | `intercept=0.0` forzado | La regresión se presenta como resultado válido aunque la pendiente esté sesgada (§I#57) |

3.4 El error desaparece de la observabilidad (133-138)
| # | Archivo:línea | Hallazgo | Efecto |
|---|---|---|---|
| 133 | `main.py:20-43` vs scripts | `LOG_LEVEL` solo se aplica en `main.py`; los CLIs fijan `logging.basicConfig(level=logging.INFO)` en código (`collect_market.py:131`, `collect_news.py:189`, `collect_surveys.py:138`, `generate_report.py:16`, `backfill_rates.py:158`, `backfill_ibc.py:130`, `refresh_macro.py:18`, `cache_manager.py:130`) | `.env LOG_LEVEL=DEBUG` no aplica a los jobs: todos los `logger.debug` de 3.1/3.2 son inalcanzables en la práctica |
| 134 | `main.py:89-95` | `init_db()` falla ⇒ solo `logger.warning` y el proceso sigue; `main.py:97` arranca el scheduler igual | El sistema corre contra una DB inexistente y falla en bucle cada 30 min |
| 135 | `scheduler/jobs.py:21-104` | Los 5 jobs hacen `logger.exception` + `return {}`; el `BackgroundScheduler` no tiene listener de errores, ni job store persistente, ni estado de última corrida | Un job roto es visible solo leyendo `economia_ve.log`; nadie se entera |
| 136 | (transversal) | Sin `sys.excepthook`, sin logging estructurado, sin `run_id` | No se puede trazar un informe publicado hasta la corrida que lo generó |
| 137 | `analyzers/market_integration.py:110-115` | Excepción al armar el texto ⇒ `"Sin pronósticos generados."` | Se niega el pronóstico aunque sí se haya calculado |
| 138 | `dashboard/app.py:123-152` | El panel de recolectores captura stdout/stderr pero muestra solo 200 caracteres y **no loguea** | Único disparador manual sin traza; `collect_gacetas` no existe (`app.py:97`) ⇒ ese botón falla siempre y en silencio |

3.5 Patrones correctos (no romper al corregir)
- `db/session.py:88-105` `session_scope`: rollback + `raise`. Es el patrón a replicar.
- `collectors/http.py`: 3 intentos con backoff y `raise CollectorError` (`:38-43`, `:50-90`). El problema está en los llamadores que convierten `CollectorError` en "sin datos".
- `db/repositories.py`: `IntegrityError` ⇒ rollback + `logger.info("duplicado omitido")` es correcto (dato repetido, no fallo).
- `components/news_section.py:66-70` y `components/survey_section.py:116-120`: muestran el fallo al usuario. Es el patrón a generalizar.

3.6 Señal de deuda medible (para el criterio de aceptación de §V)
| Comprobación | Hoy | Objetivo |
|---|---|---|
| `grep -rn "except Exception:\s*pass" src/` | 23 bloques (11 `macro_data.py`, 4 `periodic.py`, 3 `app.py`, 5 collectors IBC) | 0 |
| `grep -rn "^\s*except:\s*$" src/` | 3 (forecasting ×2, volatility ×1) | 0 |
| `except` sin log en `reports/periodic.py` (bloque macro) | 1 (7 cifras) | 0 |
| Funciones que devuelven `None/[]/{}` sin `degraded`/`source` | ~30 | 0 en analizadores que alimentan informes |
| Informes con bloque "Proveniencia" | 0 | 100% |

---

IV) MIGRACIÓN RAILWAY → STACK LOCAL CON n8n

IV.1 Dependencias cloud y su reemplazo
| Dependencia | Dónde está hoy | Reemplazo local | Verificación |
|---|---|---|---|
| PostgreSQL | `DATABASE_URL` con host Railway + `sslmode` | `postgresql://postgres:<pass>@db:5432/economia_ve` sobre el servicio `db` del compose (o `sqlite:///data/economia_ve.db` para emergencia) | `python -c "from src.config import settings; print(settings.DATABASE_URL.split('@')[-1])"` y `python -m src.scripts.collect_market` |
| Redis | `REDIS_URL` | `redis://redis:6379` del compose | `redis-cli -h 127.0.0.1 ping` |
| LLM2 | `LLM2_BASE_URL=https://omniroute-production-a409.up.railway.app/v1` (`.env.example:37`) | Ollama local `http://localhost:11434/v1` o eliminar LLM2 (LLM1/3/4 bastan) | `python -c "from src.config import settings; print([p['base_url'] for p in settings.llm_providers()])"` |
| Scheduler | `main.py:97` | n8n (ver IV.2/IV.3) | `executions` de n8n sin huecos |
| MCP Railway | `opencode.jsonc:27-33` | deshabilitar | revisión manual |

IV.2 Cómo invoca n8n los CLIs: decisión
Estado verificado de n8n: contenedor `n8n` **Up**, imagen `docker.n8n.io/n8nio/n8n` **2.39.7**, `/healthz` = **200**, puerto `0.0.0.0:5678`.

| Opción | Mecánica | Requisitos | Riesgo | Veredicto |
|---|---|---|---|---|
| A. `Execute Command` + `docker exec` | n8n ejecuta `docker exec economia-app python -m src.scripts...` | montar `/var/run/docker.sock` en n8n + binario docker | **Alto**: el socket da control root del host a un contenedor sin auth y expuesto en 0.0.0.0 | Rechazada |
| B. Runner HTTP mínimo | n8n llama `POST /run/{job}` a un servicio FastAPI del repo | nuevo `src/api/runner.py` (~150 líneas) + servicio en compose | Bajo: token, allowlist, sin socket | **Recomendada** |
| C. Nodo SSH al host | n8n ejecuta `python -m ...` por SSH en Windows/Linux | OpenSSH server + credencial | Medio: credencial de shell del host guardada en n8n | Solo transitorio |
| D. Python dentro del contenedor n8n | montar el repo y ejecutar python en la imagen n8n | imagen n8n no trae Python ni las 60+ dependencias | Alto acoplamiento, imagen enorme | Descartada |

Especificación del runner (opción B, para implementar en §V-P17):
- `POST /run/{job}` con allowlist: `collect_market`, `collect_news`, `collect_surveys`, `refresh_macro`, `backfill_rates`, `backfill_ibc`, `generate_report`, `pytest`.
- Autenticación `X-Runner-Token` (valor en `.env`, nunca en el compose), body JSON con args validados (p. ej. `{"cadence":"diario","formats":["md","pdf"]}`).
- Ejecuta `subprocess.run([sys.executable, "-m", f"src.scripts.{job}", *args], capture_output=True, text=True, timeout=...)` con timeout por job (collectores 900 s, informes 1800 s).
- Respuesta estructurada: `{job, started_at, duration_s, exit_code, stdout_tail, stderr_tail, degraded}` — n8n ramifica sobre `exit_code`/`degraded` sin parsear texto.
- `GET /health`: ping a DB, última corrida por job (`{job: {at, exit_code, duration_s}}`) y frescura de datos (`max(collected_at)` por fuente).
- Puerto **8090** (no 8000: colisiona con tikvid del stack n8n-adyacente; `API_PORT=8000` ya es un puerto muerto, §II-C4).
- Red: crear red externa `economia-net` y unir n8n a ella ⇒ `http://runner:8090` sin publicar el runner en el host. Si no se quiere tocar el compose de n8n, `host.docker.internal:8090` con bind `127.0.0.1` (patrón ya documentado en `n8n/README.md:128-129`).

IV.3 Mapa job → workflow de n8n
| Workflow | Trigger | Acción | Timeout / retry | Alerta |
|---|---|---|---|---|
| `wf-eco-collect-market` | Schedule cada 30 min | `POST /run/collect_market` | 900 s / 2 | exit≠0 ⇒ Telegram/email |
| `wf-eco-collect-news` | Schedule cada 1 h (`NEWS_COLLECT_INTERVAL_HOURS`) | `POST /run/collect_news` | 900 s / 2 | exit≠0 |
| `wf-eco-collect-surveys` | Schedule cada 60 min | `POST /run/collect_surveys` | 900 s / 2 | exit≠0 |
| `wf-eco-reports` | 6 Schedule Triggers → `Set {cadence}` | `POST /run/generate_report` | 1800 s / 1 | exit≠0 o PDF ausente |
| `wf-eco-refresh` | Domingo 03:00 | `backfill_rates` → `refresh_macro` → `backfill_ibc` | 900 s / 2 | exit≠0 en cualquier paso |
| `wf-eco-watchdog` | cada 15 min | `GET /health` | 60 s / 3 | frescura > 2× intervalo o `degraded` |
| `wf-eco-preflight` | manual / pre-deploy | `POST /run/pytest` | 900 s / 0 | exit≠0 bloquea el despliegue |

Cadencias de `wf-eco-reports` (idénticas a `src/scheduler/jobs.py:199-206`): diario 07:00; semanal lun 08:00; mensual día 1 09:00; trimestral 1/4/7/10 día 1 10:00; semestral 1/7 día 1 11:00; anual 1 ene 12:00.

Detalles que deben quedar fijados en el workflow, no en la cabeza del operador:
- **Zona horaria**: `GENERIC_TIMEZONE=America/Caracas` y `TZ=America/Caracas` en el compose de n8n, y `settings.timezone` en cada workflow. Sin esto, los cron se desplazan 4 h respecto al scheduler actual y se repite el problema de §I#66-#70.
- **`Continue On Fail` desactivado** y `Retry On Fail` explícito: el objetivo del rediseño es que un fallo se *vea*.
- **Sin solapamiento**: `max_instances=1`/`coalesce` del APScheduler se traduce en una compuerta en el runner (rechaza `409` si el job ya está corriendo).
- **Doble programación**: `weekly_report` (domingo 01:00, `generate_weekly_report.py`) y `report_semanal` (lunes 08:00) se solapan hoy. Decidir uno (recomendado: conservar el lunes 08:00 y retirar el domingo).

IV.4 Qué se retira y cómo se revierte
- `main.py:97` (llamada a `start_scheduler()`) y `main.py:62-66` (registradores). `src/scheduler/jobs.py` se conserva sin usar hasta validar 2 semanas; luego se borra.
- El servicio `app` deja de correr `python main.py` en bucle: pasa a ser `runner` (uvicorn) con `init_db()` al arrancar.
- Rollback: bandera `ENABLE_LEGACY_SCHEDULER=true` que restaura `start_scheduler()`; los 10 jobs siguen existiendo en `jobs.py` durante la transición. Si n8n cae, se levanta la bandera y el sistema vuelve al estado actual sin cambios de datos.
- n8n hardening previo (obligatorio antes de darle el control): `N8N_ENCRYPTION_KEY` fija + backup de `n8n_data`, bind `127.0.0.1:5678`, cuenta owner activa, rotar el token MCP de `n8n/opencode.json`, revisar `N8N_BLOCK_ENV_ACCESS_IN_NODE=false`.

---

V) PLAN DE MEJORA CONCRETO
Ordenado por impacto/riesgo. Cada fase es desplegable por separado y deja el sistema funcionando. Esfuerzo en días de trabajo efectivo.

Fase 0 — Baseline y red de seguridad (0.5 día)
| Paso | Acción | Verificación |
|---|---|---|
| P0.1 | `pg_dump` de la DB Railway a `data/backup/` + backup del volumen `n8n_data` + tag git | dump restaurado en local con conteos por tabla iguales |
| P0.2 | Guardar 3 informes actuales (diario, semanal, mensual) como referencia de diff | archivos en `data/reports/baseline/` |

Fase 1 — Sesgo y trazabilidad, sin tocar la orquestación (2-3 días)
| Paso | Cambio | Archivos | Verificación |
|---|---|---|---|
| P1 | Un solo módulo de fallbacks con log WARNING y bandera `degraded`; elimina la triple copia de defaults | nuevo `src/analyzers/macro_defaults.py`; `macro_data.py`, `reports/periodic.py`, `components/sustainability_panel.py`, `dashboard/app.py` | `grep -c "Fallback razonable" src/` = 0; cada fallback deja `WARNING` en log |
| P2 | Provenance por sección: `{value, source, as_of, is_fallback}` + bloque "Proveniencia" en MD/PDF y marca ⚠️ en cifras de referencia | `reports/periodic.py`, `reports/pdf_report.py`, `reports/weekly.py` | informe generado lista fuente y fecha por sección; test que falla si hay fallback sin marca |
| P3 | Unificar el reparto de deuda (0.75 vs 0.7 vs 0.75) en una función documentada | `dashboard/app.py:1197-1203`, `components/sustainability_panel.py:102`, `periodic.py:627-633` | ambos paneles muestran el mismo valor para el mismo dato |
| P4 | Aplicar `SURVEY_QUALITY_THRESHOLD` y unificar `min_responses` a 5 | `collectors/surveys/survey_collector.py:224`, `analyzers/surveys/indicators.py:196`, `dashboard/surveys_data.py:34` | respuestas con `quality_score < 0.5` no entran a KPIs; test dedicado |
| P5 | Helper de TZ Caracas y uso en todo el pipeline | nuevo `src/utils/timeutil.py`; `survey_collector.py:47-71`, `bcv_collector.py:71-96`, `cache/manager.py:337/388`, `reports/weekly.py:531`, `periodic.py:1261`, `pdf_report.py:361`, `dashboard/app.py:66-70/113-119` | encuesta de 22:00 Caracas cae en el día/semana correctos; test con fecha límite 20:00-23:59 |
| P6 | Años derivados de la fecha, no literales | `analyzers/debt_parser.py:23`, `dashboard/bvc_capitalization.py:19/161-171`, `dashboard/fiscal_data.py:91/148`, `analyzers/regional.py:101/132/225` | con fecha simulada 2027 los paneles siguen leyendo datos |
| P7 | Bare `except` → `except Exception as exc` con warning; seed en SVAR | `econometric/forecasting.py:183-185/214-216`, `econometric/volatility.py:173-178`, `svar.py:105-108` | `grep -rn "^\s*except:\s*$" src/` = 0; dos corridas del SVAR dan los mismos intervalos |
| P8 | Umbral de sentimiento único (±0.15) para dashboard, informe y PDF | `analyzers/sentiment.py:107-109`, `reports/pdf_report.py:527`, `dashboard/app.py:833-834`, `periodic.py:1070` | un mismo score produce la misma etiqueta en los tres sitios |
| P9 | Pesos IAE y de riesgo soberano a config documentada | `analyzers/iae.py:45-49`, `analyzers/sovereign_risk.py:50-59`, `:199/414` | pesos visibles en un YAML/env y citados en docs |
| P10 | Resolver config muerta y completar `.env.example` | `src/config.py`, `.env.example`, `readme.md` | cada variable de `config.py` tiene uso o se elimina; `MARKET_COLLECT_INTERVAL_MINUTES` y `LLM5-8` documentadas |

Fase 2 — Local y privado, sin Railway (1-2 días)
| Paso | Cambio | Verificación |
|---|---|---|
| P11 | `DATABASE_URL`/`REDIS_URL` locales sobre `docker compose up db redis` | `python -m src.scripts.collect_market` escribe en la DB local |
| P12 | Retirar LLM2-Railway (Ollama local o eliminar) | `llm_providers()` sin URLs de Railway |
| P13 | Compose: bind `127.0.0.1` en db/redis/dashboard/grafana, healthchecks, quitar Prometheus o crear `config/prometheus.yml`, puerto API 8000→8090 | `docker ps` sin `0.0.0.0` en servicios internos; `docker compose up` sin servicios en crash-loop |
| P14 | `.dockerignore` y `.env` fuera de la imagen; password de Postgres por `env_file` | `docker run --rm imagen ls -a /app` no muestra `.env` |
| P15 | Dashboard: `server.address=127.0.0.1` + auth por `secrets.toml`, o retirar el panel de recolectores hasta tener runner | `curl` desde otra máquina de la LAN no responde |
| P16 | n8n: `N8N_ENCRYPTION_KEY`, owner, bind local, rotar token MCP, backup de volumen | `docker compose config` muestra la key; login del owner activo |

Fase 3 — n8n como orquestador (2-3 días)
| Paso | Cambio | Verificación |
|---|---|---|
| P17 | Implementar `src/api/runner.py` según §IV.2 + tests | `POST /run/collect_market` devuelve JSON con `exit_code`; test de allowlist y token |
| P18 | Crear los 7 workflows de §IV.3 como JSON versionados en `n8n/workflows/` | `docker exec n8n n8n import:workflow --input=...` y ejecución manual verde |
| P19 | TZ `America/Caracas` en n8n y en logs del runner | ejecución de las 07:00 aparece a las 07:00 de Caracas |
| P20 | Retirar `start_scheduler()` de `main.py` (bandera de rollback activa) | `python main.py` ya no registra jobs; reportes siguen saliendo desde n8n |
| P21 | Watchdog + alertas (Telegram/email) sobre frescura y `exit_code` | apagar `runner` 10 min ⇒ llega alerta |

Fase 4 — Calidad de datos y CI (continuo)
| Paso | Cambio | Verificación |
|---|---|---|
| P22 | Versionar/descargar en job las fuentes hoy locales (`data/cvs.xls/...Brent.csv`, `data/ocr/**`) o sembrarlas explícitamente | informe en un contenedor limpio no cae a 70.0 |
| P23 | Tests de regresión de sesgo: TZ, `quality_threshold`, provenance, años dinámicos | `pytest -q` verde y fallando si se reintroduce el literal |
| P24 | CI con `pytest -q` (offline) como pre-flight | job `wf-eco-preflight` en rojo bloquea el despliegue |

Esfuerzo total estimado: 6-9 días efectivos. Ruta mínima de mayor impacto: P0 → P1 → P2 → P4 → P5 → P7 (≈2 días) corrige los sesgos que hoy se publican en los informes; la migración a n8n puede esperar sin empeorar nada.

Decisiones abiertas (requieren tu criterio)
- D1: PostgreSQL local (recomendado, ya está en compose y el esquema usa Timescale) vs SQLite de emergencia.
- D2: consolidar `weekly_report` (domingo 01:00) y `report_semanal` (lunes 08:00) en uno (recomendado) o mantener ambos.
- D3: runner HTTP propio (recomendado) vs nodo SSH transitorio.
- D4: exponer n8n solo en `127.0.0.1` antes de darle control del pipeline, o dejarlo en LAN con owner/auth.
- D5: runner en red compartida `economia-net` (recomendado, cero exposición) vs `host.docker.internal`.

Criterio de aceptación global
1. `pytest -q` verde (≈341 tests, corren offline).
2. `grep -rn "except Exception:\s*pass" src/` = 0 y `grep -rn "^\s*except:\s*$" src/` = 0.
3. Todo informe generado incluye bloque "Proveniencia" y marca las cifras de referencia.
4. 7 días consecutivos de ejecuciones en n8n sin huecos y con alerta efectiva ante fallo simulado.
5. Ningún servicio interno publicado en `0.0.0.0` y ningún proceso dependiendo de `railway.app`.

Nota de esta revisión: se completaron los dos puntos que quedaban abiertos del checklist (auditoría de fallas silenciosas y plan concreto). No se modificó código fuente; el único archivo tocado es este informe. La verificación de n8n se hizo con `docker ps`, `curl /healthz` y `n8n --version` (2.39.7).

---

VI) ESTADO DE IMPLEMENTACIÓN (04-11-2026)
| Punto del plan | Estado | Dónde |
|---|---|---|
| P1 fallbacks centrales con log + bandera `degraded` | ✅ | `src/analyzers/reference_values.py`; consumido por `macro_data.py`, `reports/periodic.py`, `dashboard/app.py`, `sustainability_panel.py` |
| P2 provenance en MD y PDF | ✅ | `periodic.provenance_block()` + snapshot `_degraded`; `pdf_report._proveniencia()` |
| P3 reparto de deuda único (0.75) | ✅ | `reference_values.EXTERNAL_DEBT_SHARE` en los 3 módulos (antes 0.75 / 0.7 / 0.75) |
| P7 bare `except` | ✅ | `econometric/forecasting.py` (2), `econometric/volatility.py` (1); los 23 `except Exception: pass` de resultados ahora dejan traza |
| P11 DB/Redis locales | ✅ código, ⏳ datos | `.env` + ambos compose; esquema creado en Postgres local; falta `pg_dump`/restore de Railway |
| P12 LLM2 sin Railway | ✅ | `.env` (LLM2 comentado), `.env.example` apunta a Ollama local |
| P13 puertos en loopback + healthchecks | ✅ | 8090 runner, 8501 dashboard, 5432 db, 6380 redis, 9090/3000 monitoring, todos en `127.0.0.1` |
| P14 `.dockerignore` | ✅ | excluye `.env`, `data/`, `.git`, caches |
| P17 runner HTTP | ✅ | `src/api/runner.py` + `tests/test_api_runner.py` (11 tests) |
| P18 workflows versionados | ✅ | `n8n/workflows/*.json` (7) + `n8n/README.md`; importados en n8n 2.39.7 **inactivos** |
| P19 zona horaria | ✅ en workflows | `settings.timezone = America/Caracas`; falta `GENERIC_TIMEZONE` en el compose de n8n |
| P20 retirar scheduler | ⏳ no | `main.py` sigue registrando APScheduler; los workflows quedan inactivos para no duplicar jobs |
| P21 watchdog | ✅ workflow | `wf-eco-watchdog` consulta `/health` (503 si la DB falla) |

Verificaciones ejecutadas: `pytest tests/test_api_runner.py tests/test_reports_periodic.py` → 39 passed; `docker compose config -q` en prod y dev; runner real `GET /health` → 200 con `db.ok=true`; `POST /run/collect_market` sin token → 401; esquema creado en Postgres local; los 7 workflows importan en n8n.

Pendiente / decisiones que requieren tu criterio
1. Restaurar datos: `pg_dump` de Railway → `psql` local (no ejecutado: requiere credenciales de Railway).
2. Activar los workflows solo después de retirar `main.py` (P20).
3. Añadir `RUNNER_TOKEN` al compose de n8n (mismo valor que `.env`) y `GENERIC_TIMEZONE=America/Caracas`. **No** fijar `N8N_ENCRYPTION_KEY` a ciegas en una instancia existente: invalidaría las credenciales guardadas; primero hay que exportar la del volumen.
4. Redis se publica en 6380 porque Windows bloquea el 6379 (rango reservado); dentro de la red Docker sigue siendo `redis:6379`.
5. Prometheus sigue sin `config/prometheus.yml`, así que ese servicio no arranca.

---

VII) SEGUNDA TANDA (04-11-2026, tarde)

**Datos: Railway se dio de baja.** El proyecto en Railway fue eliminado, así que
no existe dump que restaurar: no hay recuperación posible de ese histórico. En
lugar de un `pg_dump` se reconstruyó la base local desde las fuentes con los
colectores, y se añadió `src/scripts/verify_data.py` para auditar qué hay
tras cada corrida (filas, rango de fechas, registros de los últimos N días;
`--fail-on-empty` sale con 1 si falta una tabla esencial).

Estado real de la base local tras la reconstrucción:

| Tabla | Filas | Cobertura |
|---|---|---|
| `exchange_rates` | 8 | 2026-11-04 (BCV, Binance y bancos del día) |
| `venezuelan_tickers` | 1220 | 2026-09-05 → 2026-11-04 (backfill IBC 61 días) |
| `ibc_index` | 2 | 2026-11-04 |
| `news_articles` | 8 | 2026-11-04 (RSS) |
| `social_posts` | 6 | 2026-11-04 (Reddit) |
| `sentiment_scores` | 7 | 2026-11-04 |
| `inflation_points` | 1 | 2026-11 |
| `macro_indicators` | 0 | — |
| `survey_responses` | 0 | — (sin IDs de Google Forms) |
| `ibc_components` | 0 | — |

Las series históricas quedan cortas porque las fuentes gratuitas solo publican
el dato del día (el dataset de usdt.com.ve devolvió 0 promedios). Para tener
histórico real hay que programar backfills por fuente, no basta con recolectar.

**Scheduler retirado (P20).** `main.py` ya no importa APScheduler: hace
bootstrap del esquema, comprueba la base y sale con 0/1. Se eliminó el servicio
`app` de `docker-compose.yml` y `docker-compose.dev.yml`. `src/scheduler/jobs.py`
se conserva como referencia de las cadencias hasta validar dos semanas de n8n.

**n8n activo.** Los 7 workflows se importaron y publicaron (`publish:workflow`;
en 2.39 `update:workflow --all --active=true` ya no publica y no existe comando
de borrado). Como el contenedor de n8n no tiene `RUNNER_TOKEN` en su entorno, la
autenticación pasó de `{{ $env.RUNNER_TOKEN }}` a una credencial **HTTP Header
Auth** con id `eco-runner-token`, importada al contenedor. Quedan activos:
mercado (30 min), noticias (1 h), refresco (dom 03:00), informes (6 cron),
watchdog (15 min) y pre-flight (lun 06:00). Encuestas queda **inactivo** a
propósito: sin `SURVEY_*_FORM_ID`/`SHEET_ID` el job no recolecta nada.

Prueba real del ciclo: `collect_market` y el watchdog ejecutados por n8n a las
14:30 del 04-11 con estado `success`; el runner respondió 200 desde dentro del
contenedor y 401 sin token; `generate_report` (diario, MD + PDF) se generó por
el runner en 147 s con la sección de Proveniencia ya incluida.

**Sesgos de la Fase 1 corregidos.**

| Sesgo | Antes | Ahora |
|---|---|---|
| Zona horaria | `datetime.now()` y etiqueta "UTC" mezcladas | `src/utils/clock.py` (`America/Caracas`, fallback UTC-4) en informes, PDF, encuestas y dashboard |
| Años fijos | OCR `bvc/2026`, ONAPRE 2026, Banco Mundial 2025, query "2024 2025" | `src/utils/paths.latest_year_dir` + año actual en ONAPRE/regional/noticias |
| Calidad de encuestas | `SURVEY_QUALITY_THRESHOLD` con 0 usos | `SurveyIndicators._usable` filtra respuestas bajo el umbral antes de agregar |
| Mínimo de respuestas | 1 / 3 / 5 según el módulo | `SURVEY_MIN_RESPONSES=5` en serie, tarjetas y dashboard |
| Pesos | fijos en el código | `IAE_WEIGHTS` y `SOVEREIGN_RISK_WEIGHTS` (JSON) con validación y caída a defaults |

Verificación final: **354 tests passed** (5m39s), incluidos dos nuevos
(`test_calidad_baja_no_entra_a_kpis`, `test_compute_series_min_responses_por_defecto`).

Pendiente de esta tanda
1. El runner quedó como proceso de host para la prueba; para que sobreviva a un
   reinicio hay que levantarlo con `docker compose up -d runner` (implica build
   de la imagen) o como servicio de Windows.
2. Histórico: programar backfills por fuente (tasas, IPC, IBC) en lugar de
   depender del dato diario.
3. `macro_indicators` sigue vacío: `refresh_macro` escribe en caché de series,
   no en esa tabla.
4. Restaurar `eco-runner-token` si se recrea la base de n8n (ver `n8n/README.md`).
5. Respaldo de la SQLite de n8n en `data/tmp/n8n-db-backup/` (ignorado por git).

---

VIII) RUNNER EN DOCKER (04-11-2026)

El runner dejó de ser un proceso de terminal: ahora es un contenedor con
`restart: unless-stopped`, así que con Docker encendido el stack sube solo.
`start.bat` hace `docker compose up -d db redis runner` y sale.

**El build nunca había funcionado.** `requirements.txt` fijaba
`pydolarvenezuela==0.2.0`, versión que no existe en PyPI, y la base era
`python:3.10-slim` mientras las versiones reales de ese paquete exigen
Python ≥3.11. Se corrigió con una imagen de runtime propia:

| Cambio | Antes | Ahora |
|---|---|---|
| Dependencias | `requirements.txt` completo (torch, transformers, prophet, spacy, selenium) | `requirements-runtime.txt`, escaneado de los imports reales de `src/` |
| Base | `python:3.10-slim` | `python:3.12-slim` |
| Tamaño de imagen | no construía | 1.87 GB |
| Salud | sin healthcheck | `healthcheck` contra `/health` cada 30 s |
| Zona horaria | sin `TZ` | `TZ`/`TIMEZONE=America/Caracas` en runner y dashboard |
| Arranque | `python main.py` a mano | `restart: unless-stopped` + `start.bat` |

El dashboard usa la misma imagen recortada (streamlit y plotly sí están
incluidos; torch y compañía no se importan en ningún módulo del proyecto).

Verificación dentro del contenedor: `docker compose ps` → `economia-ve-runner
(healthy)`; `/health` 200 desde el host y desde el contenedor de n8n; 401 sin
token; y tres jobs reales por HTTP contra el runner en Docker:
`verify_data` (1.9 s), `collect_market` (15.2 s) y `generate_report` diario
MD + PDF (52.7 s), los tres con `exit_code=0` y sin errores de import.

El pre-flight (`pytest` vía runner) también corre en el contenedor: **354
passed** en 3m29s. Eso destapó dos tests (`test_llm.py`) que dependían del `.env`
del host para tener una cadena de LLMs; con la imagen no hay claves y fallaban.
Ahora inyectan sus providers explícitamente (`providers=` y `monkeypatch` de
`settings.LLM1_*`), así que pasan igual con o sin `.env`.

~~Limitación conocida: el OCR de gacetas (`pdfplumber`, `pymupdf`) se importa de
forma perezosa y no está en la imagen.~~ **Resuelto en la sección IX**: ambas
librerías y los binarios `tesseract-ocr`/`poppler-utils` están en la imagen.

~~Nota: `requirements.txt` conserva los pines viejos de desarrollo.~~
**Resuelto en la sección IX**: `requirements.txt` ahora es
`-r requirements-runtime.txt` + black/flake8.
---

IX) BACKFILLS POR FUENTE, DEPS UNIFICADAS Y OCR FISCAL (05-11-2026)

Cierra los tres pendientes de la sección VII y responde a "¿cuándo está activo
el dashboard?".

IX.1 Un juego de dependencias

`requirements.txt` era una copia desfasada de los pines de runtime: mantenía
torch/transformers/prophet/spacy (que ningún módulo importa) y el
`pydolarvenezuela==0.2.0` inexistente. Ahora:

| Fichero | Contenido |
|---|---|
| `requirements-runtime.txt` | pines reales de la imagen (Python 3.12) |
| `requirements.txt` | `-r requirements-runtime.txt` + black/flake8 |

Lo que instala el entorno local y lo que instala la imagen ya no puede divergir.

IX.2 Backfill por fuente

| Fuente | Comando | Resultado real (05-11) |
|---|---|---|
| Tasas | `backfill_rates --days 180` (`--all`) | 183 días, 2026-01-17 → 2026-03-18 (201 filas en `exchange_rates`) |
| IPC | `backfill_inflation --pages 5` | 138 posts → 28 aceptados / 37 rechazados / 72 sin período; serie 2020-09 → 2025-05 |
| IBC | `backfill_ibc --days 30` | ya funcionaba; encadenado en el refresco semanal |

El dataset de usdt.com.ve está congelado desde marzo: pedir una ventana reciente
devolvía 0 filas sin explicar por qué. Ahora `backfill_rates` avisa y cae al
dataset completo (o `--all`).

Bugs de datos encontrados al backfillear (y corregidos):

1. **`save_inflation` descartaba duplicados.** Un punto mal parseado quedaba
   congelado para siempre. Ahora es upsert por `(source, period)`: re-colectar
   corrige las tasas.
2. **El regex de OVF tomaba la acumulada como mensual.** El boletín de mayo-2025
   dice "inflación mensual 26% … acumulada 105,5% … anualizada 229%"; el regex
   se quedaba con 105,5%. Ahora exige "inflación mensual" y acepta
   "interanual|anualizada|anual" para la interanual.
3. **`fetch_ipc` etiquetaba el boletín con el mes en curso.** Ese punto entró
   como `2026-11`. El período ahora se deduce del título con la fecha de
   publicación del post (`article:published_time`): 2025-05.
4. `period_from_title` estaba duplicado (script y collector); ahora vive solo en
   `ovf_collector` y el backfill lo importa.

Verificación: `fetch_posts` + `build_points` sobre el archivo real → 28 puntos,
mayo-2025 = 26,0 % / 229 %. En Postgres: 28 puntos guardados y la fila espuria
`2026-11` eliminada.

IX.3 OCR fiscal en la imagen y en n8n

- Imagen: `pdfplumber` y `pymupdf` (runtime) + `tesseract-ocr`,
  `tesseract-ocr-spa` y `poppler-utils` (apt). Antes el OCR era perezoso y no
  existía en el contenedor.
- `collect_fiscal.py`: `fetch_recientes(days)` → `download_pdf` →
  `process_and_save_ocr`; respeta `--limit` y sale con 1 si no encontró nada
  (un día sin publicaciones no es un éxito).
- Runner: `collect_fiscal` (`days`, `limit`, `force`) y `backfill_inflation`
  (`pages`) en la allowlist, con sus timeouts.
- n8n: nodo **Backfill IPC** en el refresco semanal y workflow nuevo
  `wf-eco-collect-fiscal.json` (diario 05:30, `{"days":2,"limit":5}`).

Estado de la Gaceta: el sitio solo responde por HTTP
(`http://www.gacetaoficial.gob.ve`; HTTPS da 000) y `/gacetas/dia` devuelve `[]`
para 2026-11-03 — no hay publicaciones recientes. El archivo sí tiene 40 `.md`
de 2026 y 64 entradas en `data/ocr/index.json`.

IX.4 ¿Cuándo está activo el dashboard?

El dashboard es un **contenedor aparte** (`economia-ve-dashboard`, Streamlit en
`127.0.0.1:8501`), no un proceso de `main.py`. Hasta ahora `start.bat` solo
levantaba `db redis runner`: el dashboard únicamente aparecía si alguien hacía
`docker compose up -d dashboard` o si ya estaba corriendo cuando se encendió
Docker (`restart: unless-stopped` lo revive, pero no lo crea).

Lanzadores, alineados con el resto de los proyectos:

| Script | Qué hace |
|---|---|
| `iniciar.bat` | Espera/abre Docker Desktop, `docker compose up -d db redis runner dashboard`, sondea `/health` (8090) y el 8501, abre Chrome en el dashboard |
| `start.bat` | alias de `iniciar.bat` (evita dos arranques desfasados) |
| `detener.bat` | `docker compose stop` de los cuatro servicios (volúmenes intactos) |

Corregido además el bind de Streamlit: dentro del contenedor debe escuchar
`0.0.0.0`; con `--server.address=127.0.0.1` el `publish` de Docker no llegaba y
el 8501 quedaba inaccesible desde el host (el puerto publicado sigue en
loopback).

IX.5 Verificación (05-11-2026)

- `python -m pytest -q` → **375 passed** en 5m26s (host).
- Imagen reconstruida (`docker compose build` OK). Dentro del runner:
  `tesseract 5.5.0`, `pdftoppm 25.03.0` e `import pdfplumber, pymupdf` correctos.
- Runner en contenedor `healthy` y tres jobs reales por HTTP con token:
  - `backfill_inflation {"pages":5}` → 28 guardados por upsert en 9,1 s.
  - `backfill_rates {"days":90}` → 0 nuevos en 2,5 s (dataset congelado: todo
    duplicado, sin error).
  - `collect_fiscal {"days":7,"limit":5}` → 0 gacetas, exit 1 (no hay
    publicaciones recientes; el job no finge éxito).
- Dashboard: `curl 127.0.0.1:8501` → **200** (antes 000 por el bind a 127.0.0.1).
- n8n: 8 workflows, 7 activos. El refresco exporta el nodo "Backfill IPC" y
  `Economía VE - Gacetas y OCR fiscal` quedó publicado como `ecoFiscal0000001`.
  Encuestas sigue inactiva a propósito.
- `verify_data` en el contenedor: `exchange_rates` 211, `inflation_points` 28,
  `news_articles` 30, `social_posts` 9, `sentiment_scores` 15,
  `venezuelan_tickers` 1220, `ibc_index` 2, `surveys` 2. `macro_indicators`
  sigue en 0 (pendiente conocido).

Nota de n8n: esta versión exige `id` en el JSON de import, así que el workflow
nuevo se importó con `id: ecoFiscal0000001`; los ficheros del repo siguen sin
`id`, igual que los demás.
