"""Welch's moving average, to see where the transient of a series ends."""

from __future__ import annotations

from collections.abc import Sequence

from satedge_simulator.errors import ScenarioError


def welch_moving_average(series: Sequence[float], window: int) -> tuple[float, ...]:
    """The moving average of Welch's method over ``series``, with half-width ``window``.

    The point ``i`` (from 0) averages the ``2·window + 1`` points around it; near the start,
    where they are not there yet, it averages the ``2·i + 1`` points it has on both sides
    (Law and Kelton). The series is usually the ensemble mean over the replications; the
    average has ``len(series) − window`` points.

    Raises:
        ScenarioError: If the window is not between 1 and half the series.
    """
    n = len(series)
    if not 1 <= window <= (n - 1) // 2:
        raise ScenarioError(
            f"la finestra di Welch deve essere tra 1 e {(n - 1) // 2}, invece è {window}"
        )
    averages = []
    for i in range(n - window):
        half = min(i, window)
        points = series[i - half : i + half + 1]
        averages.append(sum(points) / len(points))
    return tuple(averages)
