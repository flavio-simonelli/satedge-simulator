# API

La facciata `satedge_simulator.api` è il punto d'ingresso da Python; gli altri moduli sono
documentati qui per chi estende il simulatore. Le docstring sono in inglese, come il codice.

## Facciata

```{eval-rst}
.. automodule:: satedge_simulator.api
```

## Dominio

```{eval-rst}
.. automodule:: satedge_simulator.domain.scenario
.. automodule:: satedge_simulator.domain.topology
.. automodule:: satedge_simulator.domain.workload
.. automodule:: satedge_simulator.domain.workload_model
.. automodule:: satedge_simulator.domain.plan
.. automodule:: satedge_simulator.domain.lifecycle
.. automodule:: satedge_simulator.domain.violations
.. automodule:: satedge_simulator.domain.intervals
```

## Pianificazione

```{eval-rst}
.. automodule:: satedge_simulator.planning.ports
.. automodule:: satedge_simulator.planning.rolling_planner
.. automodule:: satedge_simulator.planning.epochs
.. automodule:: satedge_simulator.planning.propagation
.. automodule:: satedge_simulator.planning.adapters.scheduler.planner
.. automodule:: satedge_simulator.planning.adapters.scheduler.verification
```

## Esecuzione

```{eval-rst}
.. automodule:: satedge_simulator.runtime.simulation
.. automodule:: satedge_simulator.runtime.ground
.. automodule:: satedge_simulator.runtime.requests
.. automodule:: satedge_simulator.runtime.tasks
.. automodule:: satedge_simulator.runtime.transfers
```

## Osservazione e metriche

```{eval-rst}
.. automodule:: satedge_simulator.observe.notifications
.. automodule:: satedge_simulator.observe.bus
.. automodule:: satedge_simulator.metrics.summary
```

## Carico stocastico e numeri casuali

```{eval-rst}
.. automodule:: satedge_simulator.generation.generator
.. automodule:: satedge_simulator.generation.stages
.. automodule:: satedge_simulator.rng.rngs
.. automodule:: satedge_simulator.rng.rvgs
.. automodule:: satedge_simulator.rng.rvms
```

## Analisi dell'output

```{eval-rst}
.. automodule:: satedge_simulator.analysis.replications
.. automodule:: satedge_simulator.analysis.batch_means
.. automodule:: satedge_simulator.analysis.autocorrelation_study
.. automodule:: satedge_simulator.analysis.statistics
```
