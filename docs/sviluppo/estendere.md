# Estendere il simulatore

## Un pianificatore nuovo

Il segmento di terra dipende solo dalla porta `Planner` (`planning/ports.py`): un oggetto con un
nome e un metodo `plan`, che riceve la fotografia di un'epoca e restituisce una decisione.

```python
from satedge_simulator.domain.plan import EpochPlan
from satedge_simulator.planning.ports import PlanningDecision, PlanningSnapshot


class RejectAll:
    """Rejects every new request: a baseline for the metrics."""

    @property
    def name(self) -> str:
        return "reject-all"

    def plan(self, snapshot: PlanningSnapshot) -> PlanningDecision:
        return PlanningDecision(
            plan=EpochPlan(),
            rejected={r.id: "rejected by the baseline" for r in snapshot.new_requests},
        )
```

Si usa con la facciata, che esegue uno scenario con un pianificatore qualsiasi:

```python
from satedge_simulator.api import simulate
from satedge_simulator.io.scenario import load_scenario

scenario = load_scenario("examples/casostudio/scenario.yaml").scenario
outcome = simulate(scenario, RejectAll())
```

Il pianificatore deve rispettare gli impegni della fotografia: le loro azioni sono fisse, e
quelle nuove non devono sovrapporvisi. Le azioni nuove non possono cominciare prima dell'arrivo
del piano sul loro satellite (`snapshot.plan_arrival_s`).

## Un tipo di contact plan nuovo

1. Un modulo in `io/contact_plan/` con lo schema del file e una funzione
   `read(path, horizon_s) -> ContactPlan`.
2. Un valore in `ContactPlanKind` e una riga nella tabella `READERS` di
   `io/contact_plan/loading.py`.

Il resto del simulatore non cambia.

## Un iscritto al bus

Ogni notifica è un dataclass con il suo istante (`observe/notifications.py`). Per misurare
qualcosa di nuovo:

```python
from satedge_simulator.observe.bus import EventBus
from satedge_simulator.observe.notifications import RequestDelivered


class LateCounter:
    def __init__(self) -> None:
        self.late = 0

    def attach(self, bus: EventBus) -> None:
        bus.subscribe(RequestDelivered, self._delivered)

    def _delivered(self, n: RequestDelivered) -> None:
        if not n.on_time:
            self.late += 1
```

Passa il bus alla simulazione (`simulate(scenario, planner, bus=bus)`) dopo averci iscritto il
collettore.

## Una statistica nuova

Le statistiche dell'analisi sono in `analysis/observations.py`: aggiungi un valore a
`Statistic`, raccoglilo in `RunObservations` (per richiesta, dai record; nel tempo, da un
collettore) e dagli un nome italiano in `texts.py`. I tre studi la calcolano senza altre
modifiche.
