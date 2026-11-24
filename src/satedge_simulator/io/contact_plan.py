"""Contact plan: the visibility windows of the links that are not always available."""

from __future__ import annotations

from collections.abc import Mapping

from satedge_simulator.domain.intervals import WindowSet
from satedge_simulator.domain.topology import NodeId
from satedge_simulator.errors import ScenarioError


class ContactPlan:
    """Visibility windows of node pairs, looked up regardless of the order of the pair.

    Attributes are not exposed: a pair without windows is an error, because a windowed link
    without visibility would be silently unusable.
    """

    __slots__ = ("_windows",)

    def __init__(self, windows: Mapping[tuple[NodeId, NodeId], WindowSet]) -> None:
        self._windows: dict[frozenset[NodeId], WindowSet] = {}
        for (a, b), window_set in windows.items():
            if a == b:
                raise ScenarioError(f"contact plan: {a} is in contact with itself")
            pair = frozenset((a, b))
            if pair in self._windows:
                raise ScenarioError(f"contact plan: {a}-{b} is declared more than once")
            self._windows[pair] = window_set

    def windows_of(self, a: NodeId, b: NodeId) -> WindowSet:
        """Visibility windows between ``a`` and ``b``."""
        try:
            return self._windows[frozenset((a, b))]
        except KeyError:
            raise ScenarioError(f"contact plan has no windows for {a}-{b}") from None
