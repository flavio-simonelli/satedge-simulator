# File di input

Tutti i file sono YAML e cominciano con `schema_version`, che deve avere la forma `1.x`. Le chiavi
sconosciute sono errori, non vengono ignorate. I tempi sono in secondi, le dimensioni in Gb, le
velocità in Gbps. I percorsi sono relativi al file che li contiene.

## Scenario

| Chiave | Tipo | Default | Significato |
| --- | --- | --- | --- |
| `topology` | percorso | obbligatoria | il file della topologia |
| `contact_plan` | percorso | obbligatoria | il file del contact plan |
| `workload` | percorso | — | il file delle richieste |
| `workload_model` | sezione | — | il modello stocastico del carico |
| `planner.solver` | percorso | obbligatoria | il `solver.yaml` dello scheduler |
| `planner.lead_time_s` | numero o `null` | `null` | anticipo del calcolo sul contatto; `null` usa il limite di tempo del solver |
| `simulation.end_s` | numero > 0 | obbligatoria | fine della simulazione |
| `simulation.tolerance_s` | numero ≥ 0 | `1.0e-4` | quanto un'azione può attendere le sue precondizioni |
| `simulation.strict` | booleano | `false` | se la prima violazione ferma la simulazione |
| `simulation.seed` | intero | `123456789` | stato iniziale del generatore, tra 1 e 2147483646 |

Serve almeno uno tra `workload` e `workload_model`.

## Topologia (`kind: ring_constellation`)

| Chiave | Default | Significato |
| --- | --- | --- |
| `ground_station` | `GS` | nome della stazione di terra |
| `planes` | 2 | numero di piani orbitali |
| `satellites_per_plane` | 9 | satelliti per piano |
| `com_index` | 0 | posizione del COM nel piano |
| `horizon_s` | orizzonte del mondo | fin dove generare le finestre di calcolo |
| `plmm_capacity_gb` | obbligatoria | capacità netta della PLMM |
| `plmm_overrides_gb` | `{}` | capacità diverse per singoli satelliti |
| `hpc_rate_gbps` | 1.0 | velocità tra HPC e router, in lettura e in scrittura |
| `hpc.period_s` | 5640 | periodo delle finestre di calcolo |
| `hpc.duration_s` | 300 | durata di una finestra, avvio compreso |
| `hpc.startup_s` | 0 | avvio dei container, all'inizio della finestra |
| `hpc_phases_s` | `{}` | fase della prima finestra per singoli satelliti; gli altri sono sfasati in modo uniforme |
| `intra_link`, `inter_link`, `ground_link` | `{capacity_gbps: 1, latency_s: 0.015}` | capacità e latenza dei link nel piano, tra COM, COM-Terra |

## Contact plan

### `kind: windows` (default)

| Chiave | Significato |
| --- | --- |
| `links[].a`, `links[].b` | i due nodi |
| `links[].windows[].start_s`, `end_s` | una finestra di visibilità |

### `kind: periodic`

| Chiave | Significato |
| --- | --- |
| `links[].a`, `links[].b` | i due nodi |
| `links[].first_start_s` | la prima apertura |
| `links[].period_s` | ogni quanto si apre |
| `links[].duration_s` | quanto resta aperto, meno del periodo |

## Richieste (`workload`)

| Chiave | Default | Significato |
| --- | --- | --- |
| `requests[].id` | obbligatoria | identificativo, unico |
| `requests[].priority` | obbligatoria | `urgent` o `non_urgent` |
| `requests[].origin` | obbligatoria | il satellite che ha il raw |
| `requests[].release_s` | obbligatoria | quando il raw è disponibile a bordo |
| `requests[].arrival_s` | `release_s` | quando la richiesta arriva a terra |
| `requests[].deadline_s` | rilascio + 7200 o 25200 | scadenza assoluta di consegna a terra |
| `requests[].raw_size_gb` | obbligatoria | dimensione del raw |
| `requests[].tasks[].execution_s` | obbligatoria | calcolo del task, lettura e scrittura escluse |
| `requests[].tasks[].output_size_gb` | obbligatoria | dimensione dell'output del task |

## Modello del carico (`workload_model`)

Vedi la tabella nella guida [descrivere il carico](../guide/carico.md#un-modello-stocastico): solo
`arrivals_per_hour` è obbligatorio. Gli intervalli si scrivono `[a, b]`; `origins` è una lista di
satelliti o `null`; `deadline_after_release_s` ha le chiavi `urgent` e `non_urgent`.

## Solver (`solver.yaml`)

È il file di configurazione di satedge-workflow-scheduler: `method` (`sequential` o `milp`),
`deadline` (`hard` o `soft`), per il MILP `milp.level` e `limits.time_limit_s`. Vedi la guida
[scegliere il pianificatore](../guide/pianificatore.md).
