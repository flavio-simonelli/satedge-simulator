# Descrivere il carico

Il carico sono le richieste: ognuna chiede di elaborare con una pipeline un'immagine acquisita
da un satellite e di consegnarne il risultato a terra entro una scadenza. Si può dare in due
modi, anche insieme: un **file di richieste**, per scenari deterministici e ripetibili a mano, o
un **modello stocastico**, che genera le richieste durante la simulazione.

## Un file di richieste

```yaml
schema_version: "1.0.0"
requests:
- id: R1
  priority: urgent          # urgent o non_urgent
  origin: P1-S3             # il satellite che ha l'immagine
  release_s: 0              # quando l'immagine è disponibile a bordo
  raw_size_gb: 8
  tasks:                    # la pipeline, in ordine
  - {execution_s: 120, output_size_gb: 0.5}
  - {execution_s: 90, output_size_gb: 0.001}
```

- `arrival_s`, l'arrivo della richiesta a terra, vale di default `release_s`.
- `deadline_s` vale di default `release_s` più 2 ore per le urgenti e 7 ore per le non urgenti.
- `execution_s` è il solo calcolo: la lettura dell'input e la scrittura dell'output dalla PLMM
  si aggiungono, alla velocità `hpc_rate_gbps` della topologia.

Le richieste della stessa classe sono servite in ordine FIFO.

## Un modello stocastico

Nello scenario, la sezione `workload_model` al posto di (o insieme a) `workload`:

```yaml
workload_model:
  arrivals_per_hour: 4
```

Solo il tasso di arrivo è obbligatorio; ogni altro parametro ha un default scelto per il caso
studio, e si cambia scrivendolo:

| Parametro | Default | Significato |
| --- | --- | --- |
| `arrivals_per_hour` | — | tasso degli arrivi di Poisson a terra |
| `urgent_probability` | 0.5 | probabilità che una richiesta sia urgente |
| `acquisition_delay_s` | `[0, 5640]` | dall'arrivo al raw disponibile a bordo |
| `origins` | tutti tranne i COM | i satelliti che acquisiscono immagini |
| `raw_size_gb` | `[2, 12]` | dimensione del raw |
| `stages` | `[1, 3]` | stadi della pipeline L0→L1 |
| `work_s_per_gb` | `[12, 24]` | calcolo dell'intera pipeline per Gb di raw |
| `intermediate_ratio` | `[0.8, 1.2]` | output intermedio rispetto al suo input |
| `final_output_gb` | `[0.0001, 0.001]` | output finale, sotto 1 Mb |
| `deadline_after_release_s` | `{urgent: 7200, non_urgent: 25200}` | scadenza dopo il rilascio |

Un intervallo `[a, b]` è una distribuzione uniforme; `[a, a]` è una costante. Perché queste
distribuzioni e non altre è spiegato in [il carico stocastico](../spiegazioni/carico-stocastico.md).

**Ogni task sta in una finestra di calcolo.** Se con il numero di stadi estratto un task potrebbe
non stare nei 5 minuti, la pipeline si scompone più finemente; se con questi parametri nemmeno il
numero massimo di stadi basta, lo scenario viene rifiutato all'avvio.

### Il seed

```yaml
simulation:
  seed: 123456789
```

Il seed è lo stato iniziale del generatore. Con lo stesso seed due run generano lo stesso carico,
anche con pianificatori diversi: ogni grandezza casuale ha il suo stream, quindi il confronto tra
euristica e MILP avviene sulle stesse richieste. Vedi [i numeri casuali](../spiegazioni/numeri-casuali.md).

## Che cosa scegliere

- Per **capire un comportamento** o riprodurre un caso preciso: un file di richieste.
- Per **stimare le prestazioni**: il modello stocastico, con le
  [repliche o i batch means](analisi.md).
