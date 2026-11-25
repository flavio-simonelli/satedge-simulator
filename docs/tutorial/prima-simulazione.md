# La prima simulazione

In questo tutorial esegui il caso studio, leggi il riepilogo e guardi i file che la simulazione
lascia. Servono una decina di minuti e nessuna licenza: si usa l'euristica sequenziale dello
scheduler.

## 1. Installa

Dalla cartella del progetto:

```bash
uv sync
```

`uv` crea l'ambiente virtuale e installa il simulatore, SimPy e satedge-workflow-scheduler.

## 2. Guarda lo scenario

Uno scenario è un file YAML che nomina gli altri file e dice come eseguire la simulazione.
Quello del caso studio è `examples/casostudio/scenario.yaml`:

```yaml
schema_version: "1.0.0"
topology: topology.yaml          # 2 piani da 9 satelliti e una stazione a terra
contact_plan: contact_plan.yaml  # le finestre COM-COM e COM-Terra
workload: workload.yaml          # 8 richieste
planner:
  solver: solver.yaml            # l'euristica sequenziale dello scheduler
  lead_time_s: 60                # il piano si calcola 60 s prima di ogni contatto
simulation:
  end_s: 28800                   # 8 ore
  tolerance_s: 1.0e-4
  strict: false
```

I percorsi sono relativi al file dello scenario.

## 3. Esegui

```console
$ uv run satedge-simulator run examples/casostudio/scenario.yaml -o output/casostudio
Simulazione conclusa a 28800 s.
Richieste urgenti: 4 arrivate, 4 accettate, 0 rifiutate; 4 consegnate in tempo, 0 in ritardo, 0 fallite, 0 non concluse.
Richieste non urgenti: 4 arrivate, 4 accettate, 0 rifiutate; 4 consegnate in tempo, 0 in ritardo, 0 fallite, 0 non concluse.
Violazioni del piano: nessuna.
Verifica dell'esecuzione con il modello: superata.
Risultati in output/casostudio.
```

Il riepilogo dice tre cose:

- **come sono andate le richieste**, per classe di priorità;
- **se il piano è stato eseguito come previsto**: una *violazione* è un'azione che non è potuta
  partire, per esempio perché il dato non era ancora arrivato;
- **se l'esecuzione rispetta il modello**: ciò che il simulatore ha consegnato è stato
  controllato con il verificatore di ammissibilità dello scheduler.

## 4. Leggi i risultati

La cartella `output/casostudio` contiene due file.

`events.jsonl` è il registro di tutto ciò che è successo, una notifica per riga:

```json
{"type": "RequestArrived", "time": 0.0, "request_id": "R1"}
{"type": "PlmmChanged", "time": 0.0, "satellite": "P1-S3", "level_gb": 8.0}
{"type": "RequestAccepted", "time": 2340.0, "request_id": "R1", "epoch": 0}
```

`metrics.json` raccoglie le metriche: per ogni classe i conteggi e i tempi di risposta (media,
mediana, 95° percentile, massimo), l'utilizzo di ogni HPC e di ogni link, l'occupazione di ogni
PLMM, le epoche di pianificazione, le violazioni e l'esito della verifica. Il significato di ogni
campo è nel [riferimento dei risultati](../riferimento/risultati.md).

## 5. Prova un carico stocastico

Lo scenario `scenario-stocastico.yaml` non legge le richieste da un file: le genera durante la
simulazione, con arrivi di Poisson e le altre grandezze casuali.

```bash
uv run satedge-simulator run examples/casostudio/scenario-stocastico.yaml
```

Con lo stesso `seed` ottieni sempre la stessa run. Cambialo in `simulation.seed` e il carico
cambia. Una sola run, però, è un solo campione: per stimare le prestazioni con un intervallo di
confidenza servono le repliche.

```bash
uv run satedge-simulator replicate examples/casostudio/scenario-stocastico.yaml -n 30 -o output/repliche
```

## Per proseguire

- Per descrivere una tua costellazione: [descrivere la rete](../guide/rete.md).
- Per cambiare il carico: [descrivere il carico](../guide/carico.md).
- Per l'analisi statistica completa: [analizzare l'output](../guide/analisi.md).
