"""
Tema visual del dashboard
=========================

Paleta y helpers de estilo únicos para Economía Venezuela. Define los colores
en un solo lugar para mantener cohesión en todas las secciones (skill
frontend-visionary-artisan: paleta consistente + modo claro/oscuro).
"""

# Paleta principal (inspirada en la bandera y el color económico venezolano)
PALETTE = {
    "azul": "#0E7C86",      # azul institucional (BCV)
    "naranja": "#E4572E",   # naranja paralelo/mercado
    "verde": "#2CA58D",     # positivo / oficial
    "amarillo": "#F2C14E",  # alertas
    "rojo": "#C0392B",      # negativo / brechas
    "gris": "#8C8C8C",      # neutro
    "violeta": "#7B5EA7",   # encuestas
}

# Colores de series temporales en el orden de uso
SERIES_COLORS = [
    PALETTE["violeta"],
    PALETTE["azul"],
    PALETTE["naranja"],
    PALETTE["verde"],
    PALETTE["amarillo"],
    PALETTE["rojo"],
]


def plotly_template(theme: str = "light") -> str:
    """Template de Plotly según el tema de Streamlit.

    Args:
        theme: ``"light"`` (por defecto) o ``"dark"``.

    Returns:
        Nombre del template de Plotly.
    """
    return "plotly_dark" if theme == "dark" else "plotly_white"


def kpi_color(value: float, threshold_low: float = 40.0, threshold_high: float = 60.0) -> str:
    """Color semáforo para un KPI normalizado 0-100.

    Args:
        value: KPI normalizado.
        threshold_low / threshold_high: límites para rojo/amarillo/verde.

    Returns:
        Color hex (rojo si bajo, amarillo si medio, verde si alto).
    """
    if value < threshold_low:
        return PALETTE["rojo"]
    if value < threshold_high:
        return PALETTE["amarillo"]
    return PALETTE["verde"]


def apply_global_css() -> str:
    """CSS global inyectado vía st.markdown (refinamientos no expuestos por Streamlit).

    Returns:
        Cadena CSS para ``unsafe_allow_html=True``.
    """
    return """
    <style>
    .stMetric {
        background: rgba(124, 94, 167, 0.06);
        border-radius: 10px;
        padding: 12px 14px;
        border-left: 3px solid #7B5EA7;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 6px 16px;
        font-weight: 600;
    }
    </style>
    """