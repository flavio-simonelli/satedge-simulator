# Architettura

Il simulatore è diviso in pacchetti con una responsabilità ciascuno, e le dipendenze vanno in una
sola direzione: dall'esterno (la riga di comando) verso il dominio, che non dipende da niente. Due
regole sono controllate da un test di architettura, `tests/test_architecture.py`:

- solo `runtime` importa SimPy: la logica decisionale e il modello fisico sono Python puro;
- solo `planning/adapters/scheduler` importa satedge-workflow-scheduler: il resto del simulatore
  non sa che pianificatore c'è dietro la porta.

## I pacchetti

```{mermaid}
flowchart TB
    cli[cli<br/>riga di comando] --> api[api<br/>facciata]
    api --> io[io<br/>file di input e risultati]
    api --> analysis[analysis<br/>repliche, batch means]
    api --> adapter[planning.adapters.scheduler<br/>anti-corruption layer]
    analysis --> runtime
    api --> runtime[runtime<br/>esecuzione con SimPy]
    runtime --> planning[planning<br/>segmento di terra]
    runtime --> generation[generation<br/>carico stocastico]
    runtime --> metrics[metrics<br/>collettori]
    runtime --> observe[observe<br/>notifiche e bus]
    metrics --> observe
    generation --> rng[rng<br/>Lehmer, variate, modelli]
    analysis --> rng
    adapter --> planning
    adapter --> scheduler[(satedge-workflow-scheduler)]
    planning --> domain[domain<br/>modello fisico]
    runtime --> domain
    io --> domain
    observe --> domain
    generation --> domain
    domain -.-> rng
```

| Pacchetto | Responsabilità |
| --- | --- |
| `domain` | il modello fisico: rete, finestre, richieste, piano, ciclo di vita, violazioni, scenario |
| `planning` | il segmento di terra: epoche, propagazione del piano, impegni tra un'epoca e l'altra, la porta del pianificatore |
| `planning.adapters.scheduler` | la traduzione da e verso satedge-workflow-scheduler, la lettura del solver, la verifica dell'as-run |
| `runtime` | l'esecuzione nel tempo con SimPy: satelliti, link, azioni, richieste, terra, composition root |
| `observe` | le notifiche di ciò che succede e il bus che le consegna |
| `metrics` | i collettori delle metriche di una run |
| `generation` | il generatore delle richieste del modello stocastico |
| `rng` | numeri casuali: il generatore di Lehmer a 256 stream, le variate, le funzioni di distribuzione |
| `analysis` | l'analisi dell'output: stimatori, osservazioni, repliche, batch means, autocorrelazione |
| `io` | la lettura dei file di input e la scrittura dei risultati |
| `api`, `cli` | la facciata e la riga di comando |

## Il dominio

Il dominio descrive la realtà simulata, con dati immutabili validati alla costruzione.

```{mermaid}
classDiagram
    class Scenario {
        +requests: tuple~RequestSpec~
        +lead_time_s: float
        +world_horizon_s() float
    }
    class SimulationSettings {
        +end_s: float
        +tolerance_s: float
        +strict: bool
        +seed: int
    }
    class Constellation {
        +satellite(node) Satellite
        +link_between(x, y) Link
    }
    class Plane {
        +id: int
        +com: NodeId
    }
    class Satellite {
        +plmm_capacity_gb: float
        +hpc_rate_gbps: float
        +hpc_io_time(size_gb) float
    }
    class GroundStation
    class Link {
        +capacity_gbps: float
        +latency_s: float
        +transmission_time(size_gb) float
    }
    class Availability {
        <<union>>
    }
    class AlwaysAvailable
    class WindowedAvailability
    class WindowSet {
        +periodic(first, period, duration, horizon)$ WindowSet
        +containing(t, eps) Window
    }
    class Window {
        +start: float
        +end: float
    }
    class RequestSpec {
        +priority: Priority
        +origin: NodeId
        +arrival_s: float
        +release_s: float
        +deadline_s: float
        +raw_size_gb: float
    }
    class TaskSpec {
        +execution_s: float
        +output_size_gb: float
    }
    class WorkloadModel {
        +arrivals_per_hour: float
        +longest_life_s() float
    }
    Scenario *-- SimulationSettings
    Scenario *-- Constellation
    Scenario o-- RequestSpec
    Scenario o-- WorkloadModel
    Constellation *-- Plane
    Constellation *-- GroundStation
    Constellation *-- Link
    Plane *-- Satellite
    Satellite --> WindowSet : finestre di calcolo
    Link --> Availability
    Availability <|.. AlwaysAvailable
    Availability <|.. WindowedAvailability
    WindowedAvailability --> WindowSet
    WindowSet *-- Window
    RequestSpec *-- TaskSpec
```

Il piano di un'epoca e lo stato di una richiesta:

```{mermaid}
classDiagram
    class EpochPlan {
        +plan_arrival_s: Mapping
        +tasks_of(satellite)
        +transfers_from(node)
    }
    class PlannedTask {
        +request_id: str
        +task_index: int
        +satellite: NodeId
        +start_s: float
        +end_s: float
    }
    class PlannedTransfer {
        +request_id: str
        +data_index: int
        +source: NodeId
        +target: NodeId
        +start_s: float
        +end_s: float
    }
    class RequestRecord {
        +status: RequestStatus
        +history: list
        +move(target, at_s)
    }
    class Violation {
        +at_s: float
        +kind: ViolationKind
        +request_id: str
        +node: NodeId
    }
    EpochPlan *-- PlannedTask
    EpochPlan *-- PlannedTransfer
```

## Il segmento di terra e la porta del pianificatore

Il segmento di terra dipende da una **porta**, `Planner`: riceve la fotografia di un'epoca e
restituisce una decisione. L'adattatore dello scheduler è un'implementazione; nei test lo è un
pianificatore scritto a mano, che può anche sbagliare apposta.

```{mermaid}
classDiagram
    class Planner {
        <<interface>>
        +name: str
        +plan(snapshot) PlanningDecision
    }
    class SchedulerPlanner {
        +plan(snapshot) PlanningDecision
    }
    class RollingPlanner {
        +pending
        +commitments
        +plan_epoch(epoch, arrived) PlanningDecision
        +on_delivered(request_id)
        +on_failed(request_id)
    }
    class PlanningSnapshot {
        +epoch: Epoch
        +new_requests
        +commitments
        +plan_arrival_s
    }
    class PlanningDecision {
        +plan: EpochPlan
        +rejected: Mapping
        +solver_time_s: float
    }
    class Commitment {
        +request: RequestSpec
        +tasks
        +transfers
    }
    Planner <|.. SchedulerPlanner
    RollingPlanner --> Planner : delega
    RollingPlanner ..> PlanningSnapshot : costruisce
    Planner ..> PlanningDecision : restituisce
    RollingPlanner o-- Commitment
    SchedulerPlanner ..> to_instance : traduce
    SchedulerPlanner ..> to_decision : ritraduce
```

`RollingPlanner` tiene lo stato che le epoche condividono: le richieste in coda e gli impegni.
Tutto il resto (le epoche, la propagazione del piano) si calcola senza stato.

## L'esecuzione

`Simulation` è la **composition root**: l'unico punto che costruisce gli oggetti dell'esecuzione
e ne inietta le dipendenze.

```{mermaid}
classDiagram
    class Simulation {
        +run() SimulationOutcome
    }
    class NetworkRuntime {
        +satellite(node) SatelliteRuntime
        +arc(source, target) LinkRuntime
        +receiver(node) SatelliteRuntime
    }
    class SatelliteRuntime {
        +hpc: Resource
        +plmm: Plmm
        +window_closing() Event
    }
    class LinkRuntime {
        +channel: Resource
        +window_closing() Event
    }
    class Plmm {
        +reserve(env, key, size, eps)
        +release(key)
        +release_request(request_id)
    }
    class WindowClosings {
        +closing() Event
    }
    class DataLedger {
        +complete_event(key) Event
        +mark_complete(key)
    }
    class GroundRuntime {
        +submit(spec)
        +records
        +decisions
    }
    class PlanInstaller {
        +install(plan, arrival_s, requests, epoch)
    }
    class RequestRuntime {
        +run(action) bool
        +report(violation)
        +fail()
    }
    Simulation *-- NetworkRuntime
    Simulation *-- DataLedger
    Simulation *-- GroundRuntime
    Simulation ..> PlanInstaller
    NetworkRuntime *-- SatelliteRuntime
    NetworkRuntime *-- LinkRuntime
    SatelliteRuntime *-- Plmm
    SatelliteRuntime *-- WindowClosings
    LinkRuntime *-- WindowClosings
    GroundRuntime --> RollingPlanner
    GroundRuntime --> PlanInstaller
    GroundRuntime *-- RequestRuntime
    PlanInstaller ..> run_task : avvia
    PlanInstaller ..> run_transfer : avvia
    RequestRuntime ..> OutcomeListener : notifica
```

I task e le trasmissioni sono **processi** SimPy (`run_task`, `run_transfer`): funzioni
generatrici che attendono eventi. Le precondizioni sono eventi su cui si attende, non controlli
dello stato in un istante, quindi l'ordine in cui SimPy elabora gli eventi simultanei non cambia
il risultato. Il funzionamento è descritto in [il modello di esecuzione](modello-di-esecuzione.md).

## Osservazione, metriche e analisi

Il runtime pubblica notifiche su un `EventBus` e non sa chi ascolta (**Observer**). Metriche,
log e analisi sono iscritti al bus.

```{mermaid}
classDiagram
    class EventBus {
        +subscribe(kind, callback)
        +publish(notification)
    }
    class Notification {
        +time: float
    }
    class ResourceCollector
    class PlmmCollector
    class EpochCollector
    class AsRunCollector
    class JsonlEventLog
    class TimeSeriesCollector
    class RunObservations {
        +observations(statistic)
        +mean(statistic, start, end)
    }
    EventBus ..> Notification : consegna
    ResourceCollector ..> EventBus : iscritto
    PlmmCollector ..> EventBus : iscritto
    EpochCollector ..> EventBus : iscritto
    AsRunCollector ..> EventBus : iscritto
    JsonlEventLog ..> EventBus : iscritto
    TimeSeriesCollector ..> EventBus : iscritto
    RunObservations ..> TimeSeriesCollector : costruita da
```

I tre studi dell'analisi condividono la run osservata, `observe()`, che esegue una simulazione
con un `TimeSeriesCollector` sul bus e ne ricava le osservazioni. `replicate` ne esegue molte
sullo stesso generatore; `batch_means` e `autocorrelation_study` una sola, lunga.

## Il carico e i numeri casuali

```{mermaid}
classDiagram
    class MultiStreamRng {
        +seed: int
        +stream(index) Stream
        +states
    }
    class Stream {
        +random() float
        +drawn: int
        +remaining: int
    }
    class UniformSource {
        <<interface>>
        +random() float
    }
    class RequestGenerator {
        +next_interarrival_s() float
        +request(arrival_s) RequestSpec
    }
    class StageSplitter {
        +for_model(model, constellation)$ StageSplitter
        +stages(drawn, raw, work) int
    }
    class Quantity {
        <<enumeration>>
        ARRIVALS
        PRIORITY
        ACQUISITION
        ORIGIN
        RAW
        STAGES
        WORK
        RATIO
        FINAL
    }
    MultiStreamRng *-- Stream
    UniformSource <|.. Stream
    RequestGenerator --> StageSplitter
    RequestGenerator --> Stream : uno per Quantity
    RequestGenerator ..> Quantity
```

Le distribuzioni di `rvgs` ricevono la sorgente di uniformi da cui estrarre (`UniformSource`):
nel simulatore è uno stream, nei test una sequenza scritta a mano.

## La riga di comando

Ogni comando è un oggetto **Command** che dichiara i suoi argomenti ed esegue sé stesso; `main`
costruisce il parser dal registro dei comandi.

```{mermaid}
classDiagram
    class Command {
        <<interface>>
        +name: str
        +help: str
        +configure(parser)
        +execute(args, out)
    }
    class RunCommand
    class ReplicateCommand
    class BatchCommand
    class AutocorrelationCommand
    class ItalianParser
    Command <|.. RunCommand
    Command <|.. ReplicateCommand
    Command <|.. BatchCommand
    Command <|.. AutocorrelationCommand
    RunCommand ..> simulate_file
    ReplicateCommand ..> replicate_file
    BatchCommand ..> batch_means_file
    AutocorrelationCommand ..> autocorrelation_file
```

## I pattern

| Pattern | Dove | Perché |
| --- | --- | --- |
| Strategy | `Planner`, i lettori del contact plan (`READERS`), `UniformSource` | sostituire algoritmo, formato o sorgente senza toccare chi li usa |
| Adapter (anti-corruption layer) | `planning/adapters/scheduler` | tenere il modello dello scheduler fuori dal simulatore |
| Observer | `EventBus` e i suoi iscritti | separare chi produce gli eventi da chi li misura |
| Facade | `api` | un solo punto d'ingresso per la riga di comando e per Python |
| Command | `cli` | un oggetto per comando, aggiunti a un registro |
| Factory Method | `WindowSet.periodic`, `StageSplitter.for_model` | costruire oggetti validi con la loro regola, in un solo posto |
| State (tabella delle transizioni) | `RequestRecord` | rendere esplicite e controllate le transizioni del ciclo di vita |
| Composition root | `Simulation` | costruire e collegare le dipendenze in un solo punto |
