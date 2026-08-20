"""
Sección de Informes del dashboard (Streamlit)
==============================================

Permite generar informes económicos periódicos (diario→anual) en Markdown y PDF
con rango de fechas personalizado. Muestra el último informe generado y permite
descargar nuevos informes.
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st

from src.dashboard import theme

logger = logging.getLogger(__name__)

CADENCIAS = {
    "diario": "📅 Diario",
    "semanal": "📆 Semanal",
    "mensual": "🗓️ Mensual",
    "trimestral": "📊 Trimestral",
    "semestral": "📈 Semestral",
    "anual": "📉 Anual",
}

REPORTS_DIR = Path("data/reports")


def _list_existing_reports() -> list:
    """Lista informes ya generados en data/reports/."""
    if not REPORTS_DIR.exists():
        return []
    files = sorted(REPORTS_DIR.glob("*.md"), reverse=True) + \
            sorted(REPORTS_DIR.glob("*.pdf"), reverse=True)
    return files[:20]  # últimos 20


def _read_report(path: Path) -> str:
    """Lee un informe Markdown para mostrarlo."""
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return f"*No se pudo leer {path.name}*"


def render_reports_section() -> None:
    """Renderiza la sección completa de informes."""
    st.subheader("📊 Generador de Informes Económicos")
    st.caption(
        "Genera informes en Markdown y PDF con datos de mercado, inflación, "
        "encuestas, sentimiento y documentos fiscales."
    )

    # ---- Formulario de generación ----
    with st.expander("⚙️ Configurar Informe", expanded=True):
        c1, c2 = st.columns(2)

        with c1:
            cadence = st.selectbox(
                "Cadencia",
                options=list(CADENCIAS.keys()),
                format_func=lambda k: CADENCIAS[k],
                index=1,  # semanal por defecto
                key="report_cadence",
            )

            formats = st.multiselect(
                "Formatos",
                options=["md", "pdf"],
                default=["md", "pdf"],
                key="report_formats",
            )

        with c2:
            today = datetime.now().date()
            use_custom_range = st.checkbox(
                "Rango personalizado",
                value=False,
                key="report_custom_range",
            )

            if use_custom_range:
                col_since, col_until = st.columns(2)
                with col_since:
                    since_date = st.date_input(
                        "Desde",
                        value=today - timedelta(days=7),
                        key="report_since",
                    )
                with col_until:
                    until_date = st.date_input(
                        "Hasta",
                        value=today,
                        key="report_until",
                    )
            else:
                since_date = None
                until_date = None

        no_ai = st.checkbox(
            "Omitir resumen IA (más rápido)",
            value=False,
            key="report_no_ai",
        )

        # ---- Botón generar ----
        can_generate = len(formats) > 0
        if st.button(
            "🚀 Generar Informe",
            type="primary",
            disabled=not can_generate,
            key="report_generate_btn",
        ):
            _generate_report(cadence, formats, since_date, until_date, no_ai)

    # ---- Último informe generado ----
    st.markdown("---")
    st.subheader("📄 Informes Generados")

    reports = _list_existing_reports()
    if not reports:
        st.info(
            "📭 No hay informes generados aún. Usa el generador de arriba "
            "para crear tu primer informe."
        )
        return

    # Selector de informe
    report_names = [f.name for f in reports]
    selected = st.selectbox(
        "Seleccionar informe",
        options=report_names,
        key="report_select",
    )

    if selected:
        report_path = REPORTS_DIR / selected
        if selected.endswith(".md"):
            content = _read_report(report_path)
            st.markdown(content)
        elif selected.endswith(".pdf"):
            st.info(f"📄 PDF generado: **{selected}**")
            # Ofrecer descarga
            with open(report_path, "rb") as f:
                st.download_button(
                    label="⬇️ Descargar PDF",
                    data=f.read(),
                    file_name=selected,
                    mime="application/pdf",
                    key="report_download",
                )


def _generate_report(
    cadence: str,
    formats: list,
    since_date,
    until_date,
    no_ai: bool,
) -> None:
    """Ejecuta la generación del informe y muestra el resultado."""
    from src.analyzers.reports.periodic import generate_periodic_report

    with st.spinner(f"Generando informe {cadence}... esto puede tomar unos segundos"):
        try:
            kwargs = {}
            if since_date:
                from datetime import timezone
                kwargs["since"] = datetime.combine(
                    since_date, datetime.min.time()
                ).replace(tzinfo=timezone.utc)
            if until_date:
                from datetime import timezone
                kwargs["until"] = datetime.combine(
                    until_date, datetime.max.time()
                ).replace(tzinfo=timezone.utc)

            result = generate_periodic_report(
                cadence=cadence,
                formats=tuple(formats),
                with_ai=not no_ai,
                **kwargs,
            )

            paths = result.get("paths", {})
            period = result.get("snapshot", {}).get("period", "")

            st.success(f"✅ Informe generado para el período: **{period}**")

            # Mostrar rutas
            for fmt, path in paths.items():
                st.info(f"[{fmt.upper()}] {path}")

            # Si se generó MD, mostrarlo
            if "md" in paths:
                md_path = Path(paths["md"])
                if md_path.exists():
                    st.markdown("---")
                    st.subheader("Vista previa del informe")
                    st.markdown(_read_report(md_path))

        except Exception as exc:
            st.error(f"❌ Error al generar el informe: {exc}")
            logger.exception("Error en generate_report del dashboard: %s", exc)
