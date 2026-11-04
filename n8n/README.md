# Workflows de n8n — Economía Venezuela

Orquestación de los jobs que antes corría APScheduler (`src/scheduler/jobs.py`).
n8n **no** ejecuta código del proyecto directamente: llama al runner HTTP
(`src/api/runner.py`), que valida el job y sus argumentos contra una allowlist.

## Requisitos

1. Runner levantado y accesible desde el contenedor de n8n:

   ```bash
   docker compose up -d db redis runner   # desde economia-venezuela/
   curl -s http://127.0.0.1:8090/health
   ```

2. n8n con acceso al host. En Docker Desktop, `host.docker.internal` resuelve al
   host; las URLs de los workflows ya lo usan.
3. `RUNNER_TOKEN` presente en **ambos** lados:
   - `.env` de economia-venezuela (lo lee el runner).
   - `environment:` del compose de n8n (los workflows lo leen con
     `{{ $env.RUNNER_TOKEN }}`, y ese contenedor ya tiene
     `N8N_BLOCK_ENV_ACCESS_IN_NODE=false`).

   El runner y n8n deben compartir el mismo valor. Si `RUNNER_TOKEN` está vacío,
   el runner acepta cualquier llamada: úsalo solo en localhost.

## Importar

```bash
# Copiar los JSON al contenedor y luego importarlos
docker cp n8n/workflows n8n:/tmp/workflows
docker exec n8n n8n import:workflow --separate --input=/tmp/workflows
```

Los workflows se importan **inactivos** (`"active": false`): actívalos desde la
UI solo después de retirar el scheduler legado (`python main.py`), si no los
jobs se ejecutarían dos veces.

## Zona horaria

Los cron asumen `America/Caracas` (definido en `settings.timezone` de cada
workflow). Para que la UI y las ejecuciones coincidan, añade al compose de n8n:

```yaml
environment:
  - GENERIC_TIMEZONE=America/Caracas
  - TZ=America/Caracas
```

## Workflows

| Archivo | Cadencia | Job |
|---|---|---|
| `wf-eco-collect-market.json` | cada 30 min | `collect_market` |
| `wf-eco-collect-news.json` | cada hora | `collect_news` |
| `wf-eco-collect-surveys.json` | cada 60 min | `collect_surveys` |
| `wf-eco-reports.json` | 6 cron (diario→anual) | `generate_report` |
| `wf-eco-refresh.json` | domingo 03:00 | `backfill_rates` → `refresh_macro` → `backfill_ibc` |
| `wf-eco-watchdog.json` | cada 15 min | `GET /health` |
| `wf-eco-preflight.json` | manual | `pytest` |

## Códigos de respuesta del runner

| Código | Significado | Efecto en n8n |
|---|---|---|
| 200 | job OK (`exit_code == 0`) | verde |
| 502 | el job falló (`exit_code != 0`) | ejecución en rojo |
| 504 | timeout del job | ejecución en rojo |
| 409 | el job ya está corriendo | ejecución en rojo (sin solaparse) |
| 401 | token inválido | ejecución en rojo |
| 422 | argumento no aplicable al job | ejecución en rojo |
| 404 | job fuera de la allowlist | ejecución en rojo |

Un fallo nunca queda silencioso: el workflow se detiene con error y la ejecución
queda registrada en n8n.
