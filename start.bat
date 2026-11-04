@echo off
REM Arranca el stack que n8n necesita (base, cache y runner HTTP).
REM Igual que el .bat de n8n: lanza los contenedores y sale, no deja ventanas.
REM Con `restart: unless-stopped`, al encender Docker vuelven a subir solos.
cd /d "%~dp0"
docker compose up -d db redis runner
docker compose ps
