# Test e qualità

```bash
uv run pytest                     # tutti i test
uv run ruff check                 # stile ed errori comuni
uv run ruff format --check        # formattazione
uv run mypy src tests             # tipi
```

## Che cosa provano i test

| Area | Che cosa si prova |
| --- | --- |
| `tests/domain` | validazione dei dati, finestre, ciclo di vita, modello del carico |
| `tests/io` | lettura di ogni file, i loro errori, i risultati |
| `tests/planning` | epoche, propagazione, impegni, traduzione verso lo scheduler, verifica dell'as-run |
| `tests/runtime` | ogni azione con istanti esatti: precondizioni, tolleranza, finestre, PLMM, interruzioni, fallimenti, notifiche |
| `tests/metrics`, `tests/observe` | collettori, bus, registro degli eventi |
| `tests/rng` | valori di controllo del generatore, variate, quantili |
| `tests/generation` | generatore delle richieste: intervalli, stream, scomposizione nelle finestre |
| `tests/analysis` | stimatori e i tre studi |
| `tests/test_*.py` | facciata, riga di comando, carico stocastico, architettura |

I test di esecuzione usano un pianificatore scritto a mano, che produce i piani voluti, anche
sbagliati, per provare ogni violazione. I test end-to-end eseguono il caso studio con l'euristica
dello scheduler, e il controllo di ammissibilità dello scheduler fa da oracolo. Il test del MILP
è saltato dove Gurobi non è installato.

## Il test di architettura

`tests/test_architecture.py` legge gli import di ogni file e controlla le regole dei livelli:
solo `runtime` importa SimPy, solo l'adattatore importa lo scheduler, il dominio non dipende
dall'I/O. Un import nel posto sbagliato fa fallire i test.
