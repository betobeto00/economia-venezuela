"""
Tests del job de ingesta fiscal (gacetas + OCR)
===============================================

Sin red: se inyecta un collector falso y se monkeypatchean ``download_pdf`` y
``process_and_save_ocr`` del módulo de caché.
"""

from datetime import date

import pytest

from src.models.market import FiscalDocument
from src.scripts import collect_fiscal as job


class FakeCollector:
    def __init__(self, docs=None, error=None):
        self._docs = docs or []
        self._error = error
        self.days = None

    def fetch_recientes(self, days=30):
        self.days = days
        if self._error:
            raise self._error
        return list(self._docs)


def _doc(number="43437", url=None):
    return FiscalDocument(
        source="gaceta",
        title=f"Gaceta N° {number} (ORDINARIA)",
        url=url or f"http://x/storage/2026/{number}-2026-08-14-ORDINARIA.pdf",
        year=2026,
        date=date(2026, 8, 14),
    )


class FakePath:
    def __init__(self, payload=b"%PDF-1.4 fake"):
        self._payload = payload

    def read_bytes(self):
        return self._payload


class TestHelpers:
    def test_filename_from_url(self):
        assert job._filename_from_url(
            "http://x/storage/2026/43437-2026-08-14-ORDINARIA.pdf"
        ) == "43437-2026-08-14-ORDINARIA"

    def test_metadata(self):
        meta = job._metadata(_doc(), "43437-2026-08-14-ORDINARIA")
        assert meta["number"] == "43437"
        assert meta["type"] == "ORDINARIA"
        assert meta["date"] == "2026-08-14"


class TestCollectFiscal:
    def test_procesa_y_cuenta(self, monkeypatch):
        calls = {"download": 0, "ocr": 0}

        monkeypatch.setattr("src.cache.manager.download_pdf",
                            lambda *a, **k: calls.__setitem__("download", calls["download"] + 1) or FakePath())
        monkeypatch.setattr("src.cache.manager.process_and_save_ocr",
                            lambda *a, **k: calls.__setitem__("ocr", calls["ocr"] + 1) or "data/ocr/gacetas/2026/43437.md")

        summary = job.collect_fiscal(days=7, limit=5, collector=FakeCollector([_doc()]))
        assert summary == {"found": 1, "downloaded": 1, "processed": 1,
                           "skipped": 0, "failed": 0}
        assert calls == {"download": 1, "ocr": 1}

    def test_respeta_limit(self, monkeypatch):
        monkeypatch.setattr("src.cache.manager.download_pdf", lambda *a, **k: FakePath())
        monkeypatch.setattr("src.cache.manager.process_and_save_ocr", lambda *a, **k: "md")
        docs = [_doc(str(43000 + i)) for i in range(5)]
        summary = job.collect_fiscal(days=7, limit=2, collector=FakeCollector(docs))
        assert summary["found"] == 5
        assert summary["processed"] == 2

    def test_fallo_de_descarga(self, monkeypatch):
        monkeypatch.setattr("src.cache.manager.download_pdf", lambda *a, **k: None)
        summary = job.collect_fiscal(days=7, limit=5, collector=FakeCollector([_doc()]))
        assert summary["failed"] == 1
        assert summary["processed"] == 0

    def test_fuente_caida_no_lanza(self, monkeypatch):
        summary = job.collect_fiscal(
            days=7, collector=FakeCollector(error=RuntimeError("sin red"))
        )
        assert summary["found"] == 0
        assert summary["processed"] == 0

    def test_sin_gacetas_sale_con_error(self, monkeypatch):
        """Un día sin publicaciones no debe reportarse como éxito."""
        monkeypatch.setattr(job, "collect_fiscal", lambda **k: {
            "found": 0, "downloaded": 0, "processed": 0, "skipped": 0, "failed": 0})
        monkeypatch.setattr("builtins.print", lambda *a, **k: None)
        assert job.main(["--days", "1"]) == 1
