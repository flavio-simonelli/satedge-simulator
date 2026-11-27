"""Sample autocorrelation of a series of observations."""

from __future__ import annotations

from collections.abc import Sequence

from satedge_simulator.errors import InputError


def autocorrelation(series: Sequence[float], max_lag: int) -> tuple[float, ...]:
    """The sample autocorrelation ``r_1, …, r_max_lag`` of ``series``.

    ``r_j = c_j / c_0`` with ``c_j = (1/n) · Σ_{i < n−j} (x_i − x̄)(x_{i+j} − x̄)``, the estimator of
    Leemis and Park. A constant series has no autocorrelation: every ``r_j`` is 0.

    Raises:
        InputError: If the lag is not between 1 and ``n − 1``.
    """
    n = len(series)
    if not 1 <= max_lag < n:
        raise InputError(
            f"il lag massimo deve essere tra 1 e {n - 1}, invece è {max_lag}"
        )
    # A constant series is recognised on its values, not on c_0: the rounding of the mean
    # leaves a tiny c_0 > 0 (``[0.1] * 3``), and every r_j would be noise over noise.
    if len(set(series)) == 1:
        return tuple(0.0 for _ in range(max_lag))
    mean = sum(series) / n
    centred = [x - mean for x in series]
    c0 = sum(d * d for d in centred) / n
    return tuple(
        sum(centred[i] * centred[i + j] for i in range(n - j)) / n / c0
        for j in range(1, max_lag + 1)
    )
