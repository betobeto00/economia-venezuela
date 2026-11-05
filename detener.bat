@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo  Economia Venezuela - Deteniendo stack
echo ========================================
echo.

echo [1/4] Deteniendo dashboard...
docker compose stop dashboard >nul 2>&1
echo [OK] dashboard detenido

echo [2/4] Deteniendo runner...
docker compose stop runner >nul 2>&1
echo [OK] runner detenido

echo [3/4] Deteniendo redis...
docker compose stop redis >nul 2>&1
echo [OK] redis detenido

echo [4/4] Deteniendo db...
docker compose stop db >nul 2>&1
echo [OK] db detenida

echo.
echo ========================================
echo  Servicios detenidos
echo ========================================
echo.
echo  Se usa "stop", no "down": los contenedores y los volumenes
echo  (postgres_data, redis_data) se conservan y el proximo
echo  iniciar.bat arranca en segundos.
echo.
echo  n8n sigue corriendo: para apagarlo usa
echo  C:\Users\DeadW\dev\n8n\detener.bat
echo ========================================
echo.
pause
