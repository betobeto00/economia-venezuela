@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo  Economia Venezuela - Iniciando stack
echo ========================================
echo.
echo Servicios: PostgreSQL + Redis + runner HTTP (8090) + dashboard (8501)
echo n8n NO se arranca aqui: usa C:\Users\DeadW\dev\n8n\iniciar.bat
echo.

REM ---------------------------------------------------------------
REM [1/5] Docker Desktop. Sin parentesis alrededor del loop: un goto
REM dentro de un bloque if (...) rompe cmd y cierra la ventana.
REM ---------------------------------------------------------------
echo [1/5] Verificando Docker Desktop...
docker info >nul 2>&1
if %errorlevel%==0 goto docker_ok

echo Docker no esta corriendo. Abriendo Docker Desktop...
start "" "C:\Users\DeadW\AppData\Local\Programs\DockerDesktop\Docker Desktop.exe"
echo Esperando a que Docker este listo (puede tardar hasta 2 min)...

:esperar_docker
timeout /t 5 /nobreak >nul
docker info >nul 2>&1
if %errorlevel% neq 0 goto esperar_docker

:docker_ok
echo [OK] Docker esta listo.

REM ---------------------------------------------------------------
REM [2/5] Contenedores. Idempotente: si ya corren, no los reinicia.
REM Incluye el dashboard, que antes quedaba fuera del .bat.
REM ---------------------------------------------------------------
echo.
echo [2/5] Levantando db + redis + runner + dashboard...
docker compose up -d db redis runner dashboard
if errorlevel 1 (
    echo [ERROR] Docker no pudo levantar el stack.
    echo Revisa: docker compose logs --tail=50
    pause
    exit /b 1
)

REM ---------------------------------------------------------------
REM [3/5] Runner HTTP (lo invoca n8n)
REM ---------------------------------------------------------------
echo.
echo [3/5] Esperando el runner en 8090...
set /a INTENTOS=0

:esperar_runner
curl -s -m 3 -o nul http://127.0.0.1:8090/health >nul 2>&1
if %errorlevel%==0 goto runner_ok
set /a INTENTOS+=1
if %INTENTOS% geq 24 goto runner_timeout
timeout /t 5 /nobreak >nul
goto esperar_runner

:runner_ok
echo [OK] Runner en http://127.0.0.1:8090/health
goto esperar_dashboard

:runner_timeout
echo [AVISO] El runner no respondio tras 2 min.
echo         Revisa: docker compose logs --tail=50 runner

REM ---------------------------------------------------------------
REM [4/5] Dashboard Streamlit
REM ---------------------------------------------------------------
:esperar_dashboard
echo.
echo [4/5] Esperando el dashboard en 8501...
set /a INTENTOS=0

:esperar_dashboard_loop
curl -s -m 3 -o nul http://127.0.0.1:8501 >nul 2>&1
if %errorlevel%==0 goto dashboard_ok
set /a INTENTOS+=1
if %INTENTOS% geq 24 goto dashboard_timeout
timeout /t 5 /nobreak >nul
goto esperar_dashboard_loop

:dashboard_ok
echo [OK] Dashboard en http://127.0.0.1:8501
goto abrir_chrome

:dashboard_timeout
echo [AVISO] El dashboard no respondio tras 2 min.
echo         Revisa: docker compose logs --tail=50 dashboard
goto resumen

REM ---------------------------------------------------------------
REM [5/5] Chrome con el dashboard
REM ---------------------------------------------------------------
:abrir_chrome
echo.
echo [5/5] Abriendo el dashboard en Chrome...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" http://127.0.0.1:8501

:resumen
echo.
echo ========================================
echo  Stack listo
echo ========================================
echo.
echo  Dashboard:  http://127.0.0.1:8501   (8 tabs)
echo  Runner:     http://127.0.0.1:8090/health
echo  Postgres:   127.0.0.1:5432
echo  Redis:      127.0.0.1:6380
echo.
echo  Los jobs (mercado, noticias, informes, gacetas) los
echo  dispara n8n: C:\Users\DeadW\dev\n8n\iniciar.bat
echo  Para apagar todo: detener.bat
echo ========================================
echo.
pause
