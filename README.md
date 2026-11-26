# satedge-simulator

**satedge-simulator** è un simulatore a eventi discreti per lo scheduling di pipeline computazionali su una costellazione satellitare con calcolo a bordo (*edge computing* in orbita).
Esegue nel tempo il piano calcolato a terra da
[satedge-workflow-scheduler](https://github.com/flavio-simonelli/satedge-workflow-scheduler) e
misura come si comporta il sistema reale: richieste consegnate, rifiutate o fallite, tempi di
risposta, uso degli HPC, dei link e delle memorie di bordo (PLMM).

```console
$ uv run satedge-simulator run examples/casostudio/scenario.yaml -o output/casostudio
Simulazione conclusa a 28800 s.
Richieste urgenti: 4 arrivate, 4 accettate, 0 rifiutate; 4 consegnate in tempo, 0 in ritardo, 0 fallite, 0 non concluse.
Richieste non urgenti: 4 arrivate, 4 accettate, 0 rifiutate; 4 consegnate in tempo, 0 in ritardo, 0 fallite, 0 non concluse.
Violazioni del piano: nessuna.
Verifica dell'esecuzione con il modello: superata.
Risultati in output/casostudio.
```

## Cosa fa

- **Esegue il piano nel tempo** con [SimPy](https://simpy.readthedocs.io/): la pianificazione a
  epoche, la propagazione del piano ai satelliti, i task sugli HPC nelle finestre di calcolo, le
  trasmissioni sui link nelle finestre di visibilità, l'occupazione delle PLMM.
- **Controlla ogni azione**: un'azione che non può partire come pianificato (dato non pronto,
  risorsa occupata, finestra chiusa, memoria piena, piano non ancora arrivato) è una violazione.
- **Verifica l'esecuzione** con il controllo di ammissibilità dello scheduler: ciò che il
  simulatore ha consegnato deve rispettare tutti i vincoli del modello finale.
- **Genera il carico** a runtime da un modello stocastico, con il generatore di Lehmer a 256
  stream di Leemis e Park e seed esplicito.
- **Analizza l'output**: repliche indipendenti e transitorio a orizzonte finito, batch means e
  autocorrelazione a orizzonte infinito, con intervalli di confidenza.

## Installazione

Servono [uv](https://docs.astral.sh/uv/) e Python 3.13.

```bash
uv sync                    # dipendenze, euristica sequenziale compresa
uv sync --extra gurobi     # anche il MILP, con una licenza Gurobi
```

Senza Gurobi si usa l'euristica sequenziale dello scheduler, che non richiede licenze.

## Uso

| Comando | A cosa serve |
| --- | --- |
| `satedge-simulator run SCENARIO -o CARTELLA` | una simulazione, con la verifica contro il modello |
| `satedge-simulator replicate SCENARIO -n 30 -o CARTELLA` | orizzonte finito: repliche, intervalli di confidenza, transitorio |
| `satedge-simulator batch SCENARIO --warmup S -o CARTELLA` | orizzonte infinito: batch means su una run lunga |
| `satedge-simulator autocorrelation SCENARIO --warmup S` | autocorrelazione, per scegliere la dimensione dei batch |

Gli esempi in `examples/casostudio/` descrivono il caso studio, 2 piani orbitali da 9 satelliti:

| File | Scenario |
| --- | --- |
| `scenario.yaml` | 8 richieste da file, euristica sequenziale |
| `scenario-milp.yaml` | le stesse richieste, MILP con Gurobi |
| `scenario-stocastico.yaml` | 8 ore di carico generato, contatti periodici |
| `scenario-regime.yaml` | 7 giorni di carico generato, per l'orizzonte infinito |

## Documentazione

La documentazione è in `docs/`, in Markdown, e si legge anche direttamente nel repository. Per
compilarla in HTML:

```bash
uv run --group docs sphinx-build -W -b html docs docs/_build/html
```

| Per... | Pagina |
| --- | --- |
| la prima simulazione | [tutorial](docs/tutorial/prima-simulazione.md) |
| descrivere rete, carico e pianificatore | [guide](docs/guide/rete.md) |
| analizzare l'output | [guida all'analisi](docs/guide/analisi.md) |
| ogni chiave dei file e ogni comando | [riferimento](docs/riferimento/file-di-input.md) |
| capire architettura e modello | [spiegazioni](docs/spiegazioni/architettura.md) |
| sviluppare ed estendere | [sviluppo](docs/sviluppo/ambiente.md) |

## Sviluppo

```bash
uv run pytest                                      # i test
uv run ruff check && uv run ruff format --check    # stile
uv run mypy src tests                              # tipi
```

Il codice, i commenti e le docstring sono in inglese; i messaggi per l'utente e la
documentazione sono in italiano. Vedi [sviluppo](docs/sviluppo/ambiente.md).

## Licenza e riconoscimenti

Il generatore di numeri casuali segue le librerie `rngs`, `rvgs` e `rvms` di Steve Park e Dave
Geyer, nella traduzione Python di Philip Steele (licenza MIT): vedi
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
