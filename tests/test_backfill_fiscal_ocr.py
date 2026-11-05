"""
Tests del OCR histórico de gacetas
==================================

Sin red ni PDFs reales: se crean ficheros vacíos en un ``tmp_path`` y se
monkeypatchea ``process_and_save_ocr`` / ``load_manifest`` del cache manager.
"""

import pytest

from src.scripts import backfill_fiscal_ocr as job


def _pdf(tmp_path, year, stem):
    d = tmp_path / "pdfs" / "gacetas" / str(year)
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{stem}.pdf"
    path.write_bytes(b"%PDF-1.4 fake")
    return path


def _md(tmp_path, year, stem):
    d = tmp_path / "ocr" / "gacetas" / str(year)
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{stem}.md"
    path.write_text("---\nsource: gacetas\n---\n", encoding="utf-8")
    return path


def _patch(monkeypatch, calls, fail_on=None):
    def fake_ocr(pdf_bytes, **kwargs):
        if fail_on and kwargs["filename"] == fail_on:
            raise RuntimeError("PDF corrupto")
        calls.append(kwargs["filename"])
        return f"data/ocr/gacetas/{kwargs['year']}/{kwargs['filename']}.md"

    monkeypatch.setattr("src.cache.manager.load_manifest", lambda: {})
    monkeypatch.setattr("src.cache.manager.process_and_save_ocr", fake_ocr)


class TestMetadata:
    def test_stem_completo(self):
        assert job._metadata_from_stem("43437-2026-08-14-ORDINARIA") == {
            "number": "43437", "date": "2026-08-14", "type": "ORDINARIA",
        }

    def test_stem_antiguo_sin_fecha(self):
        assert job._metadata_from_stem("43382") == {
            "number": "43382", "date": "", "type": "",
        }


class TestBackfillOcr:
    def test_solo_procesa_los_que_faltan(self, tmp_path, monkeypatch):
        _pdf(tmp_path, 2026, "43382-2026-05-25-ORDINARIA")
        _pdf(tmp_path, 2026, "43437-2026-08-14-ORDINARIA")
        _md(tmp_path, 2026, "43382")  # nombre histórico, mismo número
        calls = []
        _patch(monkeypatch, calls)

        summary = job.backfill_ocr(
            pdf_root=tmp_path / "pdfs", ocr_root=tmp_path / "ocr"
        )

        assert summary == {"pdfs": 2, "missing": 1, "processed": 1,
                           "skipped": 1, "failed": 0}
        assert calls == ["43437-2026-08-14-ORDINARIA"]

    def test_respeta_limit(self, tmp_path, monkeypatch):
        for i in range(4):
            _pdf(tmp_path, 2026, f"4300{i}-2026-07-0{i + 1}-ORDINARIA")
        calls = []
        _patch(monkeypatch, calls)

        summary = job.backfill_ocr(
            limit=2, pdf_root=tmp_path / "pdfs", ocr_root=tmp_path / "ocr"
        )

        assert summary["missing"] == 4
        assert summary["processed"] == 2
        assert len(calls) == 2

    def test_force_reprocesa_aunque_exista(self, tmp_path, monkeypatch):
        _pdf(tmp_path, 2026, "43382-2026-05-25-ORDINARIA")
        _md(tmp_path, 2026, "43382")
        calls = []
        _patch(monkeypatch, calls)

        summary = job.backfill_ocr(
            force=True, pdf_root=tmp_path / "pdfs", ocr_root=tmp_path / "ocr"
        )

        assert summary["missing"] == 1
        assert summary["processed"] == 1

    def test_pdf_roto_cuenta_como_fallo(self, tmp_path, monkeypatch):
        _pdf(tmp_path, 2026, "43382-2026-05-25-ORDINARIA")
        calls = []
        _patch(monkeypatch, calls, fail_on="43382-2026-05-25-ORDINARIA")

        summary = job.backfill_ocr(
            pdf_root=tmp_path / "pdfs", ocr_root=tmp_path / "ocr"
        )

        assert summary["failed"] == 1
        assert summary["processed"] == 0

    def test_archivo_completo_no_hace_nada(self, tmp_path, monkeypatch):
        _pdf(tmp_path, 2026, "43382-2026-05-25-ORDINARIA")
        _md(tmp_path, 2026, "43382-2026-05-25-ORDINARIA")
        calls = []
        _patch(monkeypatch, calls)

        summary = job.backfill_ocr(
            pdf_root=tmp_path / "pdfs", ocr_root=tmp_path / "ocr"
        )

        assert summary == {"pdfs": 1, "missing": 0, "processed": 0,
                           "skipped": 1, "failed": 0}
        assert calls == []

    def test_sin_archivo_devuelve_ceros(self, tmp_path, monkeypatch):
        _patch(monkeypatch, [])
        summary = job.backfill_ocr(
            pdf_root=tmp_path / "nada", ocr_root=tmp_path / "ocr"
        )
        assert summary["pdfs"] == 0
        assert summary["missing"] == 0

    def test_main_sale_con_error_si_algo_falla(self, tmp_path, monkeypatch):
        _pdf(tmp_path, 2026, "43382-2026-05-25-ORDINARIA")
        monkeypatch.setattr(job, "backfill_ocr", lambda **k: {
            "pdfs": 1, "missing": 1, "processed": 0, "skipped": 0, "failed": 1})
        monkeypatch.setattr("builtins.print", lambda *a, **k: None)
        assert job.main([]) == 1

    def test_main_sale_limpio_si_todo_ok(self, monkeypatch):
        monkeypatch.setattr(job, "backfill_ocr", lambda **k: {
            "pdfs": 3, "missing": 0, "processed": 0, "skipped": 3, "failed": 0})
        monkeypatch.setattr("builtins.print", lambda *a, **k: None)
        assert job.main([]) == 0
