"""Random variable models (rvms): the distribution functions the output analysis needs.

The standard normal, the normal and Student's t, each with its pdf, cdf and idf (the inverse of
the cdf), and the special functions they rest on: log gamma, log beta, incomplete gamma and
incomplete beta. The idf are found by Newton-Raphson from the mean, as in the original.

From rvms.c by Steve Park and Dave Geyer, as translated to Python by Philip Steele (2014, MIT
License). The absolute error of the special functions is below 1e-10.
"""

from __future__ import annotations

import math

from satedge_simulator.errors import RandomParameterError

TINY = 1.0e-10
"""Convergence threshold of the iterations."""

SQRT2PI = 2.506628274631
"""``sqrt(2π)``."""


def pdf_standard(x: float) -> float:
    """Density of the standard normal."""
    return math.exp(-0.5 * x * x) / SQRT2PI


def cdf_standard(x: float) -> float:
    """Distribution function of the standard normal."""
    t = in_gamma(0.5, 0.5 * x * x)
    return 0.5 * (1.0 - t) if x < 0.0 else 0.5 * (1.0 + t)


def idf_standard(u: float) -> float:
    """Quantile of the standard normal, for ``0 < u < 1``."""
    _require_probability(u)
    x = 0.0
    while True:
        t = x
        x = t + (u - cdf_standard(t)) / pdf_standard(t)
        if abs(x - t) < TINY:
            return x


def pdf_normal(m: float, s: float, x: float) -> float:
    """Density of the normal of mean ``m`` and deviation ``s``."""
    return pdf_standard((x - m) / s) / s


def cdf_normal(m: float, s: float, x: float) -> float:
    """Distribution function of the normal of mean ``m`` and deviation ``s``."""
    return cdf_standard((x - m) / s)


def idf_normal(m: float, s: float, u: float) -> float:
    """Quantile of the normal of mean ``m`` and deviation ``s``, for ``0 < u < 1``."""
    return m + s * idf_standard(u)


def pdf_student(n: int, x: float) -> float:
    """Density of Student's t with ``n >= 1`` degrees of freedom."""
    _require_degrees(n)
    s = -0.5 * (n + 1) * math.log(1.0 + (x * x) / n)
    t = -log_beta(0.5, n / 2.0)
    return math.exp(s + t) / math.sqrt(n)


def cdf_student(n: int, x: float) -> float:
    """Distribution function of Student's t with ``n >= 1`` degrees of freedom."""
    _require_degrees(n)
    t = (x * x) / (n + x * x)
    s = in_beta(0.5, n / 2.0, t)
    return 0.5 * (1.0 + s) if x >= 0.0 else 0.5 * (1.0 - s)


def idf_student(n: int, u: float) -> float:
    """Quantile of Student's t with ``n >= 1`` degrees of freedom, for ``0 < u < 1``."""
    _require_degrees(n)
    _require_probability(u)
    x = 0.0
    while True:
        t = x
        x = t + (u - cdf_student(n, t)) / pdf_student(n, t)
        if abs(x - t) < TINY:
            return x


# --- special functions --------------------------------------------------------------------

_LANCZOS = (
    76.180091729406,
    -86.505320327112,
    24.014098222230,
    -1.231739516140,
    0.001208580030,
    -0.000005363820,
)


def log_gamma(a: float) -> float:
    """Natural log of the gamma function, for ``a > 0``.

    Lanczos' approximation (SIAM J. Numerical Analysis, B, vol 1, 1964), with a relative error
    below 2e-10.
    """
    total = 1.000000000178 + sum(c / (a + i) for i, c in enumerate(_LANCZOS))
    return (a - 0.5) * math.log(a + 4.5) - (a + 4.5) + math.log(SQRT2PI * total)


def log_beta(a: float, b: float) -> float:
    """Natural log of the beta function, for ``a, b > 0``."""
    return log_gamma(a) + log_gamma(b) - log_gamma(a + b)


def in_gamma(a: float, x: float) -> float:
    """Incomplete gamma function, for ``a > 0`` and ``x >= 0``.

    Algorithm AS 32 (J. Applied Statistics, 1970, G. P. Bhattacharjee): a series below
    ``a + 1`` (A&S 6.5.29), a continued fraction above (A&S 6.5.31).
    """
    factor = math.exp(-x + a * math.log(x) - log_gamma(a)) if x > 0.0 else 0.0
    if x < a + 1.0:
        t = a
        term = 1.0 / a
        total = term
        while term >= TINY * total:
            t += 1.0
            term *= x / t
            total += term
        return factor * total
    p = [0.0, 1.0, 0.0]
    q = [1.0, x, 0.0]
    f = p[1] / q[1]
    n = 0
    while True:
        g = f
        n += 1
        c = ((n + 1) / 2.0 - a, 1.0) if n % 2 else (n / 2.0, x)
        p[2] = c[1] * p[1] + c[0] * p[0]
        q[2] = c[1] * q[1] + c[0] * q[0]
        if q[2] != 0.0:  # rescale to avoid overflow
            p[0], q[0] = p[1] / q[2], q[1] / q[2]
            p[1], q[1] = p[2] / q[2], 1.0
            f = p[1]
        if abs(f - g) < TINY and q[1] == 1.0:
            return 1.0 - factor * f


def in_beta(a: float, b: float, x: float) -> float:
    """Incomplete beta function, for ``a, b > 0`` and ``0 <= x <= 1``.

    The continued fraction of A&S 26.5.8, with ``x`` complemented and ``a``, ``b`` swapped
    above the mean to speed up the convergence.
    """
    swap = x > (a + 1.0) / (a + b + 1.0)
    if swap:
        x, a, b = 1.0 - x, b, a
    factor = (
        math.exp(a * math.log(x) + b * math.log(1.0 - x) - log_beta(a, b)) / a
        if x > 0.0
        else 0.0
    )
    p = [0.0, 1.0, 0.0]
    q = [1.0, 1.0, 0.0]
    f = p[1] / q[1]
    n = 0
    while True:
        g = f
        n += 1
        if n % 2:
            t = (n - 1) / 2.0
            c = -(a + t) * (a + b + t) * x / ((a + n - 1.0) * (a + n))
        else:
            t = n / 2.0
            c = t * (b - t) * x / ((a + n - 1.0) * (a + n))
        p[2] = p[1] + c * p[0]
        q[2] = q[1] + c * q[0]
        if q[2] != 0.0:  # rescale to avoid overflow
            p[0], q[0] = p[1] / q[2], q[1] / q[2]
            p[1], q[1] = p[2] / q[2], 1.0
            f = p[1]
        if abs(f - g) < TINY and q[1] == 1.0:
            return 1.0 - factor * f if swap else factor * f


def _require_probability(u: float) -> None:
    if not 0.0 < u < 1.0:
        raise RandomParameterError(f"serve una probabilità 0 < u < 1, invece u = {u}")


def _require_degrees(n: int) -> None:
    if n < 1:
        raise RandomParameterError(f"servono almeno 1 grado di libertà, invece n = {n}")
