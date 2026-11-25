"""How the estimates are written for the user."""

from __future__ import annotations

from satedge_simulator.analysis.statistics import ConfidenceInterval


def interval(i: ConfidenceInterval | None, unit: str) -> str:
    """``mean ± half-width (n units)``, or why there is no estimate.

    ``unit`` names what the interval is computed on, in the plural: the replications, the
    batches.
    """
    if i is None:
        return f"nessun valore ({unit}: 0)"
    if i.half_width is None:
        return f"{i.mean:.6g} (un solo valore, nessun intervallo)"
    return f"{i.mean:.6g} ± {i.half_width:.3g} ({i.count} {unit})"
