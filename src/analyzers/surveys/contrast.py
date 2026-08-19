"""
Contraste Percepción vs Realidad
================================

Compara la inflación percibida por la población (encuestas) con las
mediciones oficiales (BCV) e independientes (OVF), y genera la
interpretación ejecutiva del diferencial.
"""

from typing import Optional


def contrast_perception_inflation(
    perceived: float,
    official: Optional[float],
    ovf: Optional[float] = None,
    tolerance: float = 5.0,
) -> dict:
    """Compara la inflación percibida con la medición oficial e independiente.

    Args:
        perceived: Inflación percibida (promedio de la encuesta, %).
        official: IPC oficial BCV (%).
        ovf: Estimación independiente OVF (%) (opcional).
        tolerance: Umbral de puntos para considerar que hay brecha.

    Returns:
        Dict con perceived, official, ovf, brechas y la interpretación.
    """
    gap_official = (perceived - official) if official is not None else None
    gap_ovf = (perceived - ovf) if ovf is not None else None

    if official is not None and abs(gap_official) > tolerance:
        interpretation = (
            f"La población percibe {perceived:.1f}% vs {official:.1f}% oficial"
            + (f" y {ovf:.1f}% OVF" if ovf is not None else "")
            + f". Brecha de {gap_official:.1f} puntos vs lo oficial."
        )
    elif official is not None:
        interpretation = (
            "La percepción ciudadana coincide con las mediciones oficiales "
            f"({perceived:.1f}% vs {official:.1f}%)."
        )
    else:
        interpretation = (
            f"Percepción de inflación registrada: {perceived:.1f}%. "
            "Sin medición oficial disponible para contrastar."
        )

    return {
        "perceived": round(perceived, 2),
        "official": round(official, 2) if official is not None else None,
        "ovf": round(ovf, 2) if ovf is not None else None,
        "gap_vs_official": round(gap_official, 2) if gap_official is not None else None,
        "gap_vs_ovf": round(gap_ovf, 2) if gap_ovf is not None else None,
        "interpretation": interpretation,
    }