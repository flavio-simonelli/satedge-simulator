# Errori e violazioni

Il simulatore distingue due cose:

- un **errore** è un problema degli input o del simulatore: la simulazione non parte, o si
  ferma, e il comando esce con codice 1;
- una **violazione** è un risultato della simulazione: un'azione del piano non è potuta partire
  come previsto. La sua richiesta fallisce, le altre proseguono.

## Errori

```{mermaid}
classDiagram
    class SimulatorError
    class ScenarioError
    class DocumentError
    class PlannerError
    class PlanExecutionError
    class StateError
    class StreamExhaustedError
    SimulatorError <|-- ScenarioError
    ScenarioError <|-- DocumentError
    SimulatorError <|-- PlannerError
    SimulatorError <|-- PlanExecutionError
    SimulatorError <|-- StateError
    SimulatorError <|-- StreamExhaustedError
```

| Errore | Quando |
| --- | --- |
| `ScenarioError` | lo scenario è incoerente: un parametro fuori intervallo, un identificativo duplicato o sconosciuto |
| `DocumentError` | un file non si legge o non rispetta il suo schema; il messaggio nomina il file |
| `PlannerError` | il pianificatore non produce una decisione usabile; le richieste restano in coda |
| `PlanExecutionError` | in modalità `strict`, alla prima violazione |
| `StateError` | un'incoerenza interna: un difetto del simulatore, da segnalare |
| `StreamExhaustedError` | uno stream di numeri casuali ha esaurito il suo tratto: proseguire ripeterebbe i numeri di un altro |

Gli errori di validazione dei file sono elencati campo per campo:

```text
errore: scenario.yaml: il documento non è valido:
  workload_model.arrivals_per_hour: campo obbligatorio mancante
```

## Violazioni

| Tipo | Testo | L'azione non può partire perché |
| --- | --- | --- |
| `data_not_ready` | dato non pronto | il suo input non è completo sul nodo entro la tolleranza |
| `hpc_busy` | HPC occupato | l'HPC non si libera entro la tolleranza |
| `link_busy` | link occupato | il canale non si libera entro la tolleranza |
| `plmm_full` | PLMM piena | la memoria non si libera entro la tolleranza |
| `hpc_window` | fuori dalla finestra di calcolo | il task non parte in una finestra, o la finestra si chiude prima che finisca |
| `link_window` | fuori dalla finestra di visibilità | il link non è visibile, o la finestra si chiude prima dell'ultimo bit |
| `plan_not_arrived` | piano non ancora arrivato | il piano raggiunge il satellite dopo l'istante dell'azione |

Che cosa succede dopo una violazione è descritto in
[il modello di esecuzione](../spiegazioni/modello-di-esecuzione.md#il-fallimento-di-una-richiesta).
