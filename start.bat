@echo off
REM ---------------------------------------------------------------------------
REM start.bat queda como alias de iniciar.bat (el lanzador real), igual que en
REM n8n: mantener dos scripts de arranque es como se quedan desfasados (el
REM anterior solo levantaba db+redis+runner y dejaba el dashboard fuera).
REM ---------------------------------------------------------------------------

echo [AVISO] start.bat es un alias de iniciar.bat (el lanzador real).
echo.
call "%~dp0iniciar.bat"
