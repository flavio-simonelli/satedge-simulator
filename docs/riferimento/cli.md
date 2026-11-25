# Riga di comando

```text
satedge-simulator [-h] comando ...
```

Ogni comando ha il suo aiuto con `-h`. Il codice di uscita è **0** se il comando è stato
eseguito, **1** se non è stato possibile (un file non valido, un parametro fuori intervallo) e
**2** se gli argomenti sono sbagliati. I messaggi d'errore cominciano con `errore:` e vanno su
standard error.

## `run`

```text
satedge-simulator run [-h] [-o CARTELLA] scenario
```

Esegue lo scenario una volta, con il pianificatore del suo `solver.yaml`, e verifica l'esecuzione
con il modello dello scheduler.

| Opzione | Significato |
| --- | --- |
| `scenario` | il file YAML dello scenario |
| `-o`, `--output` | la cartella in cui scrivere `events.jsonl` e `metrics.json` |

## `replicate`

```text
satedge-simulator replicate [-h] [-n N] [--cell SECONDI] [--welch CELLE] [--level LIVELLO] [-o CARTELLA] scenario
```

Orizzonte finito: repliche indipendenti dello scenario, intervalli di confidenza sulle loro
medie e transitorio.

| Opzione | Default | Significato |
| --- | --- | --- |
| `-n`, `--replications` | 30 | numero di repliche, almeno 2 |
| `--cell` | 2820 | ampiezza delle celle del transitorio, in secondi |
| `--welch` | 2 | semiampiezza della media mobile di Welch, in celle |
| `--level` | 0.95 | livello di confidenza |
| `-o`, `--output` | — | la cartella di `replications.json` e `transient.csv` |

## `batch`

```text
satedge-simulator batch [-h] --warmup SECONDI [-b RICHIESTE] [--batch-duration SECONDI] [--level LIVELLO] [-o CARTELLA] scenario
```

Orizzonte infinito: una run lunga, fino alla fine dello scenario, stimata con i batch means.

| Opzione | Default | Significato |
| --- | --- | --- |
| `--warmup` | obbligatorio | il riscaldamento da scartare, in secondi |
| `-b`, `--batch-size` | 32 | richieste per batch, per le statistiche per richiesta |
| `--batch-duration` | 5640 | secondi per batch, per le statistiche nel tempo |
| `--level` | 0.95 | livello di confidenza |
| `-o`, `--output` | — | la cartella di `batch_means.json` e `batches.csv` |

## `autocorrelation`

```text
satedge-simulator autocorrelation [-h] --warmup SECONDI [--max-lag LAG] [-o CARTELLA] scenario
```

L'autocorrelazione delle statistiche per richiesta di una run lunga, per scegliere `-b`.

| Opzione | Default | Significato |
| --- | --- | --- |
| `--warmup` | obbligatorio | il riscaldamento da scartare, in secondi |
| `--max-lag` | 50 | il lag massimo |
| `-o`, `--output` | — | la cartella di `autocorrelation.json` e `autocorrelation.csv` |

## Da Python

Gli stessi studi sono funzioni della facciata `satedge_simulator.api`: `simulate_file`,
`replicate_file`, `batch_means_file` e `autocorrelation_file`, oltre a `simulate`, che esegue uno
scenario già costruito con un pianificatore qualsiasi. Vedi l'[API](api.md).
