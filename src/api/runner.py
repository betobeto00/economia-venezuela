"""Runner HTTP para orquestación externa (n8n)
================================================

Expone los CLIs de ``src/scripts`` por HTTP para que n8n (u otro orquestador)
los ejecute sin acceso al socket de Docker ni al shell del host.

Diseño:
- Allowlist de jobs y de argumentos: nunca se ejecuta un comando arbitrario.
- Token compartido en el header ``X-Runner-Token`` (``RUNNER_TOKEN``).
- Una sola instancia por job (``409`` si ya está corriendo).
- Códigos HTTP: ``200`` éxito, ``502`` el job falló, ``504`` timeout,
  ``409`` ocupado, ``401`` token inválido, ``404`` job desconocido,
  ``422`` argumentos inválidos. n8n marca la ejecución en rojo con cualquier
  ``>=400``, así que un fallo no queda oculto.
- ``GET /health`` informa el estado de la DB y la última corrida por job.

Uso:
    uvicorn src.api.runner:app --host 127.0.0.1 --port 8090
"""

from __future__ import annotations

import logging
import os
import re
import secrets
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.config import settings

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CADENCES = ("diario", "semanal", "mensual", "trimestral", "semestral", "anual")
FORMATS = ("md", "pdf", "md,pdf")
SEGMENTS = ("persona_comun", "comerciante")

#: Timeout por job, en segundos.
TIMEOUTS: Dict[str, int] = {
    "collect_market": 900,
    "collect_news": 900,
    "collect_surveys": 900,
    "refresh_macro": 900,
    "backfill_rates": 900,
    "backfill_ibc": 900,
    "backfill_inflation": 900,
    "collect_fiscal": 1800,
    "backfill_fiscal_ocr": 1800,
    "generate_report": 1800,
    "verify_data": 300,
    "pytest": 900,
}

JOBS = tuple(TIMEOUTS)

#: Campos de :class:`RunRequest` que acepta cada job. Cualquier otro campo
#: con valor se rechaza con 422 para no ejecutar flags inesperados.
_ALLOWED_FIELDS: Dict[str, Set[str]] = {
    "collect_market": {"period"},
    "collect_news": {"per_feed_limit", "reddit_limit"},
    "collect_surveys": {"segment"},
    "refresh_macro": {"force"},
    "backfill_rates": {"days", "no_save"},
    "backfill_ibc": {"days"},
    "backfill_inflation": {"pages"},
    "collect_fiscal": {"days", "limit", "force"},
    "backfill_fiscal_ocr": {"limit", "force"},
    "generate_report": {"cadence", "format", "no_ai"},
    "verify_data": set(),
    "pytest": set(),
}

MAX_OUTPUT_CHARS = 4000


class RunRequest(BaseModel):
    """Argumentos permitidos para un job (tipados, sin shell)."""

    model_config = ConfigDict(extra="forbid")

    period: Optional[str] = Field(default=None, description="YYYY-MM (collect_market)")
    days: Optional[int] = Field(default=None, ge=1, le=3650)
    limit: Optional[int] = Field(default=None, ge=1, le=50, description="collect_fiscal")
    pages: Optional[int] = Field(default=None, ge=1, le=20, description="backfill_inflation")
    segment: Optional[str] = None
    cadence: Optional[str] = None
    format: Optional[str] = None
    force: bool = False
    no_ai: bool = False
    no_save: bool = False
    per_feed_limit: Optional[int] = Field(default=None, ge=1, le=100)
    reddit_limit: Optional[int] = Field(default=None, ge=1, le=100)

    @field_validator("period")
    @classmethod
    def _valid_period(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", value):
            raise ValueError("period debe tener formato YYYY-MM")
        return value

    @field_validator("segment")
    @classmethod
    def _valid_segment(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in SEGMENTS:
            raise ValueError(f"segment debe ser uno de {SEGMENTS}")
        return value

    @field_validator("cadence")
    @classmethod
    def _valid_cadence(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in CADENCES:
            raise ValueError(f"cadence debe ser uno de {CADENCES}")
        return value

    @field_validator("format")
    @classmethod
    def _valid_format(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in FORMATS:
            raise ValueError(f"format debe ser uno de {FORMATS}")
        return value


app = FastAPI(title="Economía Venezuela Runner", version="1.0.0")

_lock = threading.Lock()
_running: Set[str] = set()
_last_runs: Dict[str, Dict] = {}


def _check_token(token: Optional[str]) -> None:
    """Valida el token compartido (si ``RUNNER_TOKEN`` está configurado)."""
    expected = settings.RUNNER_TOKEN
    if not expected:
        return
    if not token or not secrets.compare_digest(token, expected):
        raise HTTPException(status_code=401, detail="Token del runner inválido")


def _validate_for_job(job: str, request: RunRequest) -> None:
    """Rechaza argumentos que no corresponden al job solicitado."""
    used = {
        name for name in request.model_fields_set
        if getattr(request, name) not in (None, False)
    }
    extra = used - _ALLOWED_FIELDS[job]
    if extra:
        raise HTTPException(
            status_code=422,
            detail=f"Argumentos no aplicables a {job}: {sorted(extra)}",
        )


def build_command(job: str, request: RunRequest) -> List[str]:
    """Traduce la petición validada al argv del CLI (sin shell)."""
    if job == "pytest":
        return [sys.executable, "-m", "pytest", "-q"]

    cmd = [sys.executable, "-m", f"src.scripts.{job}"]
    if job == "collect_market" and request.period:
        cmd += ["--period", request.period]
    elif job == "collect_news":
        if request.per_feed_limit:
            cmd += ["--per-feed-limit", str(request.per_feed_limit)]
        if request.reddit_limit:
            cmd += ["--reddit-limit", str(request.reddit_limit)]
    elif job == "collect_surveys" and request.segment:
        cmd += ["--segment", request.segment]
    elif job == "refresh_macro" and request.force:
        cmd += ["--force"]
    elif job == "backfill_rates":
        if request.days:
            cmd += ["--days", str(request.days)]
        if request.no_save:
            cmd += ["--no-save"]
    elif job == "backfill_ibc" and request.days:
        cmd += ["--days", str(request.days)]
    elif job == "backfill_inflation" and request.pages:
        cmd += ["--pages", str(request.pages)]
    elif job == "collect_fiscal":
        if request.days:
            cmd += ["--days", str(request.days)]
        if request.limit:
            cmd += ["--limit", str(request.limit)]
        if request.force:
            cmd += ["--force"]
    elif job == "backfill_fiscal_ocr":
        if request.limit:
            cmd += ["--limit", str(request.limit)]
        if request.force:
            cmd += ["--force"]
    elif job == "generate_report":
        cmd += ["--cadence", request.cadence or "diario"]
        cmd += ["--format", request.format or "md,pdf"]
        if request.no_ai:
            cmd += ["--no-ai"]
    return cmd


def _text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _tail(value: str) -> str:
    text = _text(value).strip()
    return text[-MAX_OUTPUT_CHARS:]


def _execute(job: str, request: RunRequest) -> Dict:
    """Ejecuta el job en un subproceso y devuelve un resultado estructurado."""
    cmd = build_command(job, request)
    started = datetime.now(timezone.utc)
    start = time.perf_counter()
    timed_out = False
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=TIMEOUTS[job],
            env=os.environ.copy(),
        )
        exit_code = proc.returncode
        stdout, stderr = proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        exit_code = -1
        stdout, stderr = exc.stdout, exc.stderr
    except OSError as exc:  # intérprete/entorno roto
        exit_code = -1
        stdout, stderr = "", str(exc)

    duration = round(time.perf_counter() - start, 2)
    logger.info(
        "runner job=%s exit_code=%s duration_s=%s timed_out=%s",
        job, exit_code, duration, timed_out,
    )
    return {
        "job": job,
        "started_at": started.isoformat(),
        "duration_s": duration,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "cmd": cmd,
        "stdout": _tail(stdout or ""),
        "stderr": _tail(stderr or ""),
    }


def _db_health() -> Dict:
    """Ping a la base de datos configurada."""
    try:
        from sqlalchemy import text

        from src.db.session import get_engine

        start = time.perf_counter()
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return {
            "ok": True,
            "latency_ms": round((time.perf_counter() - start) * 1000, 1),
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001 - /health debe responder siempre
        return {"ok": False, "latency_ms": None, "error": str(exc)[:200]}


@app.get("/health")
def health() -> JSONResponse:
    """Estado del runner, la DB y la última corrida de cada job."""
    db = _db_health()
    payload = {
        "status": "ok" if db["ok"] else "degraded",
        "db": db,
        "last_runs": _last_runs,
        "running": sorted(_running),
        "version": settings.APP_VERSION,
    }
    return JSONResponse(payload, status_code=200 if db["ok"] else 503)


@app.post("/run/{job}")
def run_job(
    job: str,
    request: Optional[RunRequest] = None,
    x_runner_token: Optional[str] = Header(default=None),
) -> JSONResponse:
    """Ejecuta un job de la allowlist y devuelve su resultado."""
    _check_token(x_runner_token)
    if job not in TIMEOUTS:
        raise HTTPException(
            status_code=404,
            detail=f"Job desconocido: {job}. Disponibles: {list(JOBS)}",
        )

    request = request or RunRequest()
    _validate_for_job(job, request)

    with _lock:
        if job in _running:
            raise HTTPException(status_code=409, detail=f"{job} ya está en ejecución")
        _running.add(job)
    try:
        result = _execute(job, request)
    finally:
        with _lock:
            _running.discard(job)

    _last_runs[job] = {
        "at": result["started_at"],
        "exit_code": result["exit_code"],
        "duration_s": result["duration_s"],
    }
    status = 200
    if result["timed_out"]:
        status = 504
    elif result["exit_code"] != 0:
        status = 502
    return JSONResponse(result, status_code=status)


def main() -> None:
    """Arranca el runner con uvicorn (``python -m src.api.runner``)."""
    import uvicorn

    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    if not settings.RUNNER_TOKEN:
        logger.warning(
            "RUNNER_TOKEN vacío: el runner no exige token. Configúralo antes "
            "de exponerlo fuera de localhost."
        )
    uvicorn.run(app, host="0.0.0.0", port=settings.RUNNER_PORT)


if __name__ == "__main__":
    main()
