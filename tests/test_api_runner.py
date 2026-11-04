"""Tests del runner HTTP (sin red y sin subprocesos reales)."""

import pytest
from fastapi.testclient import TestClient

from src.api import runner
from src.config import settings


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(settings, "RUNNER_TOKEN", "secret", raising=False)
    monkeypatch.setattr(runner, "_db_health", lambda: {"ok": True, "latency_ms": 1.0, "error": None})
    return TestClient(runner.app)


@pytest.fixture()
def token_headers():
    return {"X-Runner-Token": "secret"}


def test_run_requires_token(client):
    resp = client.post("/run/collect_market")
    assert resp.status_code == 401


def test_run_rejects_wrong_token(client):
    resp = client.post("/run/collect_market", headers={"X-Runner-Token": "otro"})
    assert resp.status_code == 401


def test_unknown_job_is_404(client, token_headers):
    resp = client.post("/run/borrame_el_disco", headers=token_headers)
    assert resp.status_code == 404


def test_arguments_not_applicable_are_422(client, token_headers):
    resp = client.post(
        "/run/collect_market", headers=token_headers, json={"cadence": "diario"}
    )
    assert resp.status_code == 422


def test_invalid_cadence_is_422(client, token_headers):
    resp = client.post(
        "/run/generate_report", headers=token_headers, json={"cadence": "cada_hora"}
    )
    assert resp.status_code == 422


def test_build_command_generate_report():
    cmd = runner.build_command(
        "generate_report",
        runner.RunRequest(cadence="mensual", format="md", no_ai=True),
    )
    assert cmd[1:] == [
        "-m", "src.scripts.generate_report",
        "--cadence", "mensual", "--format", "md", "--no-ai",
    ]


def test_build_command_pytest():
    assert runner.build_command("pytest", runner.RunRequest())[1:] == ["-m", "pytest", "-q"]


def test_successful_run_is_200(client, token_headers, monkeypatch):
    class _Proc:
        returncode = 0
        stdout = "ok"
        stderr = ""

    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **k: _Proc())
    resp = client.post("/run/collect_market", headers=token_headers, json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body["exit_code"] == 0
    assert body["job"] == "collect_market"
    assert runner._last_runs["collect_market"]["exit_code"] == 0


def test_failing_job_is_502(client, token_headers, monkeypatch):
    class _Proc:
        returncode = 2
        stdout = ""
        stderr = "boom"

    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **k: _Proc())
    resp = client.post("/run/collect_market", headers=token_headers, json={})
    assert resp.status_code == 502
    assert resp.json()["stderr"] == "boom"


def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_health_degraded_when_db_down(client, monkeypatch):
    monkeypatch.setattr(
        runner, "_db_health",
        lambda: {"ok": False, "latency_ms": None, "error": "sin conexión"},
    )
    resp = client.get("/health")
    assert resp.status_code == 503
    assert resp.json()["status"] == "degraded"
