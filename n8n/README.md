# Workflows de n8n — Economía Venezuela

Orquestación de los jobs que antes corría APScheduler. n8n **no** ejecuta código
del proyecto: llama al runner HTTP (`src/api/runner.py`), que valida el job y sus
argumentos contra una allowlist.

Desde el 2026-11-04 el scheduler de `main.py` está retirado: `python main.py`
solo prepara el esquema y verifica la base. El calendario vive aquí.

## Requisitos

1. Runner levantado y accesible desde el contenedor de n8n:

   ```bash
   docker compose up -d db redis runner   # desde economia-venezuela/
   curl -s http://127.0.0.1:8090/health
   ```

   Sin Docker para el runner también sirve `python -m src.api.runner`.

2. n8n con acceso al host. En Docker Desktop, `host.docker.internal` resuelve al
   host; las URLs de los workflows ya lo usan.

## Token del runner (credencial, no `$env`)

Los workflows autentican con la credencial **HTTP Header Auth** llamada
`Economía VE - Runner token` (id `eco-runner-token`), que envía el header
`X-Runner-Token`. No se usa `{{ $env.RUNNER_TOKEN }}` porque el contenedor de
n8n no tiene esa variable en su entorno.

Crear/actualizar la credencial desde el `.env` del proyecto:

```bash
TOKEN=$(grep -E '^RUNNER_TOKEN=' .env | cut -d= -f2-)
mkdir -p data/tmp && python - "$TOKEN" <<'PY'
import json, sys, pathlib
pathlib.Path("data/tmp/cred.json").write_text(json.dumps([{
    "id": "eco-runner-token",
    "name": "Economía VE - Runner token",
    "type": "httpHeaderAuth",
    "data": {"name": "X-Runner-Token", "value": sys.argv[1]},
}]), encoding="utf-8")
PY
docker cp data/tmp/cred.json n8n:/tmp/cred.json
MSYS_NO_PATHCONV=1 docker exec n8n n8n import:credentials --input=/tmp/cred.json
rm data/tmp/cred.json
```

El id `eco-runner-token` debe coincidir con el que referencian los nodos HTTP de
los workflows (campo `credentials.httpHeaderAuth.id`).

## Importar y publicar

```bash
docker cp n8n/workflows/. n8n:/tmp/workflows
MSYS_NO_PATHCONV=1 docker exec n8n n8n import:workflow --separate --input=/tmp/workflows
MSYS_NO_PATHCONV=1 docker exec n8n n8n publish:workflow --id=<id>
docker restart n8n          # publicar no recarga los triggers en caliente
```

Notas de n8n 2.39:

- `update:workflow --all --active=true` ya no publica: hay que usar
  `publish:workflow --id=<id>` (o `unpublish:workflow`).
- No existe comando de borrado. Para reemplazar un workflow conservando su id,
  añade `"id": "<id>"` al JSON e impórtalo: hace upsert sobre ese id.
- Un workflow necesita al menos un trigger (schedule, webhook, manual) para
  poder publicarse; si no, n8n reintenta la activación y la deja inactiva.

## Estado actual (2026-11-04)

| Archivo | Cadencia | Job | Estado |
|---|---|---|---|
| `wf-eco-collect-market.json` | cada 30 min | `collect_market` | activo |
| `wf-eco-collect-news.json` | cada hora | `collect_news` | activo |
| `wf-eco-reports.json` | 6 cron (diario→anual) | `generate_report` | activo |
| `wf-eco-refresh.json` | domingo 03:00 | `backfill_rates` → `refresh_macro` → `backfill_ibc` | activo |
| `wf-eco-watchdog.json` | cada 15 min | `GET /health` | activo |
| `wf-eco-preflight.json` | lunes 06:00 | `pytest` | activo |
| `wf-eco-collect-surveys.json` | cada 60 min | `collect_surveys` | **inactivo**: sin `SURVEY_*_FORM_ID`/`SHEET_ID` no recolecta nada |

Los dos primeros ciclos reales ya quedaron registrados en n8n: watchdog y
collect_market en `success` a las 14:30 del 2026-11-04.

## Zona horaria

Cada workflow fija `settings.timezone = America/Caracas`. Si además quieres que
la UI y las ejecuciones usen esa zona, añade al compose de n8n:

```yaml
environment:
  - GENERIC_TIMEZONE=America/Caracas
  - TZ=America/Caracas
```

## Códigos de respuesta del runner

| Código | Significado | Efecto en n8n |
|---|---|---|
| 200 | job OK (`exit_code == 0`) | verde |
| 502 | el job falló (`exit_code != 0`) | ejecución en rojo |
| 504 | timeout del job | ejecución en rojo |
| 409 | el job ya está corriendo | ejecución en rojo (sin solaparse) |
| 401 | token inválido o ausente | ejecución en rojo |
| 422 | argumento no aplicable al job | ejecución en rojo |
| 404 | job fuera de la allowlist | ejecución en rojo |

Un fallo nunca queda silencioso: el workflow se detiene con error y la ejecución
queda registrada en n8n.
