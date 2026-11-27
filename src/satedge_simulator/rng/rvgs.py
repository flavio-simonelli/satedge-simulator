"""Random variate generators (rvgs): random variates from the uniforms of one stream.

Each generator takes the stream it draws from, instead of reading a global current stream as
the original libraries do: a variate that needs several uniforms draws them all from the same
stream, and no generator changes what another one draws.

Discrete:   Bernoulli(p), Binomial(n, p), Equilikely(a, b), Geometric(p), Pascal(n, p),
            Poisson(m).
Continuous: Uniform(a, b), Exponential(m), Erlang(n, b), Normal(m, s), Lognormal(a, b),
            Chisquare(n), Student(n), Hyperexponential(p, m1, m2).

The algorithms are the ones of rvgs.c by Steve Park and Dave Geyer (10-28-98), as translated to
Python by Philip Steele (2014, MIT License): inversion for the most, the Odeh and Evans
approximation of the normal idf, sums for Erlang, Pascal and chi-square. The hyperexponential
with balanced means is added for workloads more variable than the exponential.
"""

from __future__ import annotations

import math
from typing import Protocol

from satedge_simulator.errors import RandomParameterError


class UniformSource(Protocol):
    """A source of uniform random numbers in ``(0, 1)``, such as a stream of the generator."""

    def random(self) -> float: ...


def bernoulli(source: UniformSource, p: float) -> int:
    """1 with probability ``p``, 0 otherwise. Mean ``p``."""
    _require(0.0 < p < 1.0, f"Bernoulli: serve 0 < p < 1, invece p = {p}")
    return 0 if source.random() < 1.0 - p else 1


def binomial(source: UniformSource, n: int, p: float) -> int:
    """Successes in ``n`` Bernoulli trials. Mean ``n·p``."""
    _require(n > 0, f"Binomial: serve n > 0, invece n = {n}")
    return sum(bernoulli(source, p) for _ in range(n))


def equilikely(source: UniformSource, a: int, b: int) -> int:
    """An integer between ``a`` and ``b`` inclusive, each equally likely. Mean ``(a + b)/2``."""
    _require(a <= b, f"Equilikely: serve a <= b, invece a = {a}, b = {b}")
    return a + int((b - a + 1) * source.random())


def geometric(source: UniformSource, p: float) -> int:
    """A non-negative integer, geometric. Mean ``p/(1 − p)``."""
    _require(0.0 < p < 1.0, f"Geometric: serve 0 < p < 1, invece p = {p}")
    return int(math.log(1.0 - source.random()) / math.log(p))


def pascal(source: UniformSource, n: int, p: float) -> int:
    """A non-negative integer, the sum of ``n`` geometric. Mean ``n·p/(1 − p)``."""
    _require(n > 0, f"Pascal: serve n > 0, invece n = {n}")
    return sum(geometric(source, p) for _ in range(n))


def poisson(source: UniformSource, m: float) -> int:
    """A non-negative integer, Poisson of mean ``m``."""
    _require(m > 0.0, f"Poisson: serve m > 0, invece m = {m}")
    t = 0.0
    x = 0
    while t < m:
        t += exponential(source, 1.0)
        x += 1
    return x - 1


def uniform(source: UniformSource, a: float, b: float) -> float:
    """A real number between ``a`` and ``b``. Mean ``(a + b)/2``."""
    _require(a < b, f"Uniform: serve a < b, invece a = {a}, b = {b}")
    return a + (b - a) * source.random()


def exponential(source: UniformSource, m: float) -> float:
    """A positive real number, exponential of mean ``m``."""
    _require(m > 0.0, f"Exponential: serve m > 0, invece m = {m}")
    return -m * math.log(1.0 - source.random())


def erlang(source: UniformSource, n: int, b: float) -> float:
    """A positive real number, the sum of ``n`` exponential of mean ``b``. Mean ``n·b``."""
    _require(n > 0, f"Erlang: serve n > 0, invece n = {n}")
    return sum(exponential(source, b) for _ in range(n))


# Odeh and Evans, J. Applied Statistics, 1974, vol 23, pp 96-97.
_P = (0.322232431088, 1.0, 0.342242088547, 0.204231210245e-1, 0.453642210148e-4)
_Q = (0.099348462606, 0.588581570495, 0.531103462366, 0.103537752850, 0.385607006340e-2)


def normal(source: UniformSource, m: float, s: float) -> float:
    """A real number, normal of mean ``m`` and standard deviation ``s``."""
    _require(s > 0.0, f"Normal: serve s > 0, invece s = {s}")
    u = source.random()
    t = math.sqrt(-2.0 * math.log(u if u < 0.5 else 1.0 - u))
    p = _P[0] + t * (_P[1] + t * (_P[2] + t * (_P[3] + t * _P[4])))
    q = _Q[0] + t * (_Q[1] + t * (_Q[2] + t * (_Q[3] + t * _Q[4])))
    z = p / q - t if u < 0.5 else t - p / q
    return m + s * z


def lognormal(source: UniformSource, a: float, b: float) -> float:
    """A positive real number whose log is normal of mean ``a`` and deviation ``b``.

    Mean ``exp(a + b²/2)``, variance ``(exp(b²) − 1)·exp(2a + b²)``.
    """
    _require(b > 0.0, f"Lognormal: serve b > 0, invece b = {b}")
    return math.exp(a + b * normal(source, 0.0, 1.0))


def chisquare(source: UniformSource, n: int) -> float:
    """A positive real number, chi-square with ``n`` degrees of freedom. Mean ``n``."""
    _require(n > 0, f"Chisquare: serve n > 0, invece n = {n}")
    return sum(normal(source, 0.0, 1.0) ** 2 for _ in range(n))


def student(source: UniformSource, n: int) -> float:
    """A real number, Student's t with ``n`` degrees of freedom. Mean 0 for ``n > 1``."""
    return normal(source, 0.0, 1.0) / math.sqrt(chisquare(source, n) / n)


def hyperexponential(source: UniformSource, p: float, m1: float, m2: float) -> float:
    """Exponential of mean ``m1`` with probability ``p``, of mean ``m2`` otherwise.

    Mean ``p·m1 + (1 − p)·m2``. Both uniforms come from ``source``.
    """
    branch = bernoulli(source, p)
    return exponential(source, m1 if branch == 1 else m2)


def balanced_hyperexponential(mean: float, cv: float) -> tuple[float, float, float]:
    """The parameters ``(p, m1, m2)`` of the hyperexponential with balanced means.

    Balanced means: ``p·m1 = (1 − p)·m2 = mean / 2``. With the coefficient of variation ``cv``,
    ``p = (1 − sqrt((cv² − 1)/(cv² + 1))) / 2``.

    Raises:
        RandomParameterError: If the mean is not positive or ``cv <= 1``: a hyperexponential is more
            variable than the exponential.
    """
    _require(mean > 0.0, f"iperesponenziale: serve media > 0, invece è {mean}")
    _require(
        cv > 1.0,
        f"iperesponenziale: serve un coefficiente di variazione > 1, invece è {cv}",
    )
    c2 = cv * cv
    p = (1.0 - math.sqrt((c2 - 1.0) / (c2 + 1.0))) / 2.0
    return p, mean / (2.0 * p), mean / (2.0 * (1.0 - p))


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RandomParameterError(message)
