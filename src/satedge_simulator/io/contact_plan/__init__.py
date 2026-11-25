"""Contact plan: the visibility windows of the links that are not always available.

A contact plan file gives its windows in one of two kinds, chosen by its ``kind`` field:
``windows`` (every window, the default) or ``periodic`` (first opening, period and duration of
each link).
"""

from satedge_simulator.io.contact_plan.loading import ContactPlanKind, load_contact_plan
from satedge_simulator.io.contact_plan.table import ContactPlan

__all__ = ["ContactPlan", "ContactPlanKind", "load_contact_plan"]
