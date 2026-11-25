# Risultati

## `events.jsonl`

Una notifica per riga, con il suo tipo e il suo istante:

```json
{"type": "TaskStarted", "time": 2506.6666666666665, "request_id": "R1", "task_index": 0, "satellite": "P1-S8"}
```

| Tipo | Campi | Quando |
| --- | --- | --- |
| `RequestArrived` | `request_id` | la richiesta arriva a terra |
| `RequestAccepted` | `request_id`, `epoch` | il pianificatore la accetta |
| `RequestRejected` | `request_id`, `epoch`, `reason` | il pianificatore la rifiuta |
| `EpochPlanned` | `epoch`, `ready_s`, `new`, `accepted`, `rejected`, `solver_time_s`, `unreachable` | un'epoca è decisa |
| `PlanInstalled` | `epoch`, `satellite` | il piano raggiunge un satellite che vi ha azioni |
| `TaskStarted` | `request_id`, `task_index`, `satellite` | il task prende l'HPC |
| `TaskEnded` | come sopra, `completed` | il task rilascia l'HPC |
| `TransferStarted` | `request_id`, `data_index`, `source`, `target` | la trasmissione prende il canale |
| `TransferEnded` | come sopra, `completed` | la trasmissione rilascia il canale |
| `TransferReceived` | come sopra | l'ultimo bit arriva al nodo di destinazione |
| `PlmmChanged` | `satellite`, `level_gb` | l'occupazione di una PLMM cambia |
| `ViolationRaised` | `request_id`, `kind`, `node` | un'azione non può partire come pianificato |
| `RequestFailed` | `request_id` | la richiesta fallisce |
| `RequestDelivered` | `request_id`, `on_time` | l'output finale è a terra |

## `metrics.json`

| Chiave | Contenuto |
| --- | --- |
| `requests[]` | per classe: `arrived`, `accepted`, `rejected`, `delivered_on_time`, `delivered_late`, `failed`, `unfinished` e le distribuzioni `response_from_release_s`, `response_from_arrival_s`, `tardiness_s` |
| `hpcs` | per satellite: `busy_s`, `available_s`, `utilization` |
| `arcs` | per verso di link (`"A->B"`): `busy_s`, `available_s`, `utilization` |
| `plmms` | per satellite: `capacity_gb`, `peak_gb`, `mean_gb`, `peak_ratio` |
| `epochs` | `epochs`, `new`, `accepted`, `rejected`, `solver_time_s`, `overruns`, `max_unreachable` |
| `violations` | numero di violazioni per tipo |
| `deviation_s` | scostamento tra inizio eseguito e inizio pianificato delle azioni |
| `lost_raw` | raw che non sono entrati nella PLMM all'acquisizione |
| `verification` | `passed` e l'elenco `findings` della verifica con il modello |
| `outcomes` | per richiesta: `status` finale e `history`, le coppie `[istante, stato]` |

Ogni distribuzione ha `count`, `mean`, `p50`, `p95` e `max`. L'utilizzo è il tempo occupato
diviso il tempo di finestra fino alla fine; per un link sempre disponibile, la durata della
simulazione.

## Risultati dell'analisi

| Studio | JSON | CSV |
| --- | --- | --- |
| `replicate` | `replications.json`: `estimates` e `per_replication` di ogni statistica | `transient.csv`: `statistic`, `start_s`, `end_s`, `mean`, `half_width`, `count`, `welch` |
| `batch` | `batch_means.json`: per statistica `interval`, `batches`, `lag1` | `batches.csv`: `statistic`, `batch`, `mean` |
| `autocorrelation` | `autocorrelation.json`: `observations` e `autocorrelation` | `autocorrelation.csv`: `statistic`, `lag`, `r` |

Un intervallo è `{mean, half_width, count, level}`; `half_width` è `null` con un solo valore.
