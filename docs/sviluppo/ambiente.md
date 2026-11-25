# L'ambiente di sviluppo

## Requisiti

- Python 3.13;
- [uv](https://docs.astral.sh/uv/);
- per il MILP, Gurobi 13 con una licenza (una licenza accademica va bene).

```bash
uv sync                          # dipendenze e strumenti di sviluppo
uv sync --extra gurobi           # anche gurobipy
uv sync --group docs             # anche Sphinx, per la documentazione
```

`uv sync` senza `--extra gurobi` rimuove gurobipy dall'ambiente: se usi il MILP, aggiungi sempre
l'extra.

## La struttura del repository

| Percorso | Contenuto |
| --- | --- |
| `src/satedge_simulator/` | il codice, un pacchetto per responsabilità (vedi [l'architettura](../spiegazioni/architettura.md)) |
| `tests/` | i test, con la stessa struttura del codice |
| `examples/casostudio/` | gli scenari del caso studio |
| `docs/` | questa documentazione |
| `THIRD_PARTY_NOTICES.md` | le licenze del codice di terzi |

## Le convenzioni

- **Lingua**: codice, commenti e docstring in inglese; messaggi per l'utente (errori, riga di
  comando) e documentazione in italiano. Le chiavi dei file YAML e JSON restano in inglese.
- **Docstring** in stile Google, con `Args`, `Returns` e `Raises`.
- **Una responsabilità** per file e per classe; i pattern di progetto dove servono.
- **Tipi** completi, controllati da mypy.
- **Commit** in stile `Feature: …`, `Refactor: …`, `Fix: …`, `Test: …`.

## La documentazione

```bash
uv run --group docs sphinx-build -W -b html docs docs/_build/html
```

`-W` fa fallire la compilazione a ogni avviso, per esempio un link interno rotto. Le pagine sono
in Markdown (MyST) e i diagrammi in Mermaid, quindi si leggono anche direttamente nel
repository.
