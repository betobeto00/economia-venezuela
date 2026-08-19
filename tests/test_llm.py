"""
Tests de la cadena de LLMs con fallback (punto 25)
===================================================

- ``chat_completion`` prueba proveedores en orden y usa el primero que responde.
- Ante error HTTP, timeout o respuesta vacía, pasa al siguiente.
- ``settings.llm_providers()`` respeta el orden LLM1..LLM8 y cae a DeepSeek.
- El informe de encuestas usa la cadena (monkeypatch de httpx).
"""

import pytest

from src.analyzers.llm import LLMError, chat_completion, summarize
from src.config import Settings, settings


def _providers(keys=("p1", "p2")):
    return [
        {"api_key": k, "base_url": f"https://{k}.test/v1", "model": f"m-{k}"}
        for k in keys
    ]


class FakeResponse:
    def __init__(self, status=200, content="ok"):
        self.status_code = status
        self._content = content
        self.is_success = 200 <= status < 300

    def json(self):
        if not self.is_success:
            raise ValueError("no json on error")
        return {"choices": [{"message": {"content": self._content}}]}

    @property
    def text(self):
        return self._content


class FakePost:
    """Monkeypatch de httpx.post con respuestas por llamada."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def __call__(self, url, **kwargs):
        self.calls.append((url, kwargs))
        resp = self._responses.pop(0)
        if isinstance(resp, Exception):
            raise resp
        return resp


class TestChatCompletion:
    def test_usa_el_primero(self, monkeypatch):
        fake = FakePost([FakeResponse(content="respuesta")])
        monkeypatch.setattr("httpx.post", fake)
        out = chat_completion([{"role": "user", "content": "hola"}], providers=_providers())
        assert out == "respuesta"
        assert len(fake.calls) == 1
        url, kwargs = fake.calls[0]
        assert url == "https://p1.test/v1/chat/completions"
        assert kwargs["headers"]["Authorization"] == "Bearer p1"
        assert kwargs["json"]["model"] == "m-p1"
        assert kwargs["json"]["temperature"] == 0.0

    def test_fallback_al_segundo(self, monkeypatch):
        fake = FakePost([
            FakeResponse(status=429, content="rate limit"),
            FakeResponse(content="backup"),
        ])
        monkeypatch.setattr("httpx.post", fake)
        out = chat_completion([{"role": "user", "content": "x"}], providers=_providers())
        assert out == "backup"
        assert len(fake.calls) == 2

    def test_fallback_ante_error_de_red(self, monkeypatch):
        fake = FakePost([
            RuntimeError("connection reset"),
            FakeResponse(content="ok2"),
        ])
        monkeypatch.setattr("httpx.post", fake)
        out = chat_completion([{"role": "user", "content": "x"}], providers=_providers())
        assert out == "ok2"

    def test_todos_fallan_lanza_llmerror(self, monkeypatch):
        fake = FakePost([FakeResponse(status=500, content="boom"), RuntimeError("red")])
        monkeypatch.setattr("httpx.post", fake)
        with pytest.raises(LLMError):
            chat_completion([{"role": "user", "content": "x"}], providers=_providers())

    def test_respuesta_vacia_pasa_al_siguiente(self, monkeypatch):
        fake = FakePost([
            FakeResponse(content=""),
            FakeResponse(content="real"),
        ])
        monkeypatch.setattr("httpx.post", fake)
        out = chat_completion([{"role": "user", "content": "x"}], providers=_providers())
        assert out == "real"
        assert len(fake.calls) == 2

    def test_sin_proveedores_retorna_none(self, monkeypatch):
        assert chat_completion([{"role": "user", "content": "x"}], providers=[]) is None

    def test_base_url_sin_slash_final(self, monkeypatch):
        fake = FakePost([FakeResponse(content="y")])
        monkeypatch.setattr("httpx.post", fake)
        providers = [{"api_key": "k", "base_url": "https://x.test/v1/", "model": "m"}]
        chat_completion([{"role": "user", "content": "x"}], providers=providers)
        assert fake.calls[0][0] == "https://x.test/v1/chat/completions"


class TestSummarize:
    def test_resume_con_cadena(self, monkeypatch):
        fake = FakePost([FakeResponse(content="resumen")])
        monkeypatch.setattr("httpx.post", fake)
        out = summarize("rol", "texto")
        assert out == "resumen"
        body = fake.calls[0][1]["json"]
        assert body["messages"][0]["role"] == "system"
        assert body["messages"][1]["content"] == "texto"
        assert body["max_tokens"] == 300

    def test_falla_devuelve_none(self, monkeypatch):
        fake = FakePost([RuntimeError("boom")])
        monkeypatch.setattr("httpx.post", fake)
        assert summarize("rol", "texto", providers=_providers(["a"])) is None


class TestSettingsProviders:
    def _clear_all(self, monkeypatch):
        for i in range(1, 9):
            for attr in ("API_KEY", "BASE_URL", "MODEL"):
                monkeypatch.setattr(settings, f"LLM{i}_{attr}", None)
        monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", None)

    def test_llm_providers_respeta_orden(self, monkeypatch):
        # Simula un .env con LLM1..LLM4 en orden distinto al de ejemplo.
        self._clear_all(monkeypatch)
        monkeypatch.setattr(settings, "LLM1_API_KEY", "k1")
        monkeypatch.setattr(settings, "LLM1_BASE_URL", "https://p1/v1")
        monkeypatch.setattr(settings, "LLM1_MODEL", "nemotron")
        monkeypatch.setattr(settings, "LLM2_API_KEY", "k2")
        monkeypatch.setattr(settings, "LLM2_BASE_URL", "https://p2/v1")
        monkeypatch.setattr(settings, "LLM2_MODEL", "auto/best-reasoning")
        monkeypatch.setattr(settings, "LLM3_API_KEY", "k3")
        monkeypatch.setattr(settings, "LLM3_BASE_URL", "https://p3/v1")
        monkeypatch.setattr(settings, "LLM3_MODEL", "glm-5-turbo")
        monkeypatch.setattr(settings, "LLM4_API_KEY", "k4")
        monkeypatch.setattr(settings, "LLM4_BASE_URL", "https://p4/v1")
        monkeypatch.setattr(settings, "LLM4_MODEL", "gemini-2.5-flash")
        providers = settings.llm_providers()
        models = [p["model"] for p in providers]
        assert models == ["nemotron", "auto/best-reasoning", "glm-5-turbo", "gemini-2.5-flash"]

    def test_solo_provider_completo(self, monkeypatch):
        self._clear_all(monkeypatch)
        monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "ds-key")
        providers = settings.llm_providers()
        assert providers == [{
            "api_key": "ds-key",
            "base_url": "https://api.deepseek.com",
            "model": "deepseek-chat",
        }]

    def test_sin_configuracion_vacia(self, monkeypatch):
        self._clear_all(monkeypatch)
        assert settings.llm_providers() == []


class TestSurveyReportUsaCadena:
    def test_resumen_ia_via_cadena(self, monkeypatch):
        from src.analyzers.llm import LLMError
        from src.analyzers.surveys.report import SurveyReport

        fake = FakePost([FakeResponse(content="Resumen IA semanal")])
        monkeypatch.setattr("httpx.post", fake)

        kpis = {}
        report = SurveyReport(ai_enabled=True)
        out = report.generate("persona_comun", kpis, n_responses=10, period="Semana 1")
        assert "## Resumen IA" in out
        assert "Resumen IA semanal" in out

    def test_ia_falla_devuelve_base(self, monkeypatch):
        from src.analyzers.llm import LLMError
        from src.analyzers.surveys.report import SurveyReport

        def boom(*args, **kwargs):
            raise LLMError("todo caído")

        monkeypatch.setattr("src.analyzers.llm.chat_completion", boom)
        report = SurveyReport(ai_enabled=True)
        out = report.generate("comerciante", {}, n_responses=0, period="Semana 1")
        assert "## Resumen IA" not in out
        assert "Informe Ejecutivo de Encuestas" in out