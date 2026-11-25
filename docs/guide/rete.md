# Descrivere la rete

La rete è descritta da due file: la **topologia** (satelliti, stazione di terra, link e finestre
di calcolo) e il **contact plan** (quando sono visibili i link che non lo sono sempre). Questa
guida mostra come scriverli; ogni chiave è nel
[riferimento dei file di input](../riferimento/file-di-input.md).

## La topologia: una costellazione ad anelli

Il tipo `ring_constellation` descrive piani orbitali in cui ogni satellite comunica solo con il
precedente e il successivo del suo piano, e un satellite per piano, il **COM**, fa da ponte verso
gli altri piani e verso terra:

```yaml
schema_version: "1.0.0"
kind: ring_constellation
ground_station: GS
planes: 2
satellites_per_plane: 9
com_index: 0                      # il primo satellite di ogni piano è il COM
plmm_capacity_gb: 2000            # capacità netta della PLMM, tolto l'archivio
hpc_rate_gbps: 1.0                # velocità tra HPC e router
hpc: {period_s: 5640, duration_s: 300, startup_s: 0}
intra_link: {capacity_gbps: 1, latency_s: 0.015}
inter_link: {capacity_gbps: 1, latency_s: 0.015}
ground_link: {capacity_gbps: 1, latency_s: 0.015}
```

I nodi si chiamano `COM<p>` e `P<p>-S<k>`: con 2 piani da 9 satelliti sono `COM1`, `P1-S1`, …,
`P1-S8`, `COM2`, `P2-S1`, … I link sono:

| Link | Disponibilità |
| --- | --- |
| tra satelliti vicini dello stesso piano | sempre |
| tra i COM di piani diversi | nelle finestre del contact plan |
| tra ogni COM e la stazione di terra | nelle finestre del contact plan |

Ogni link è full duplex: i due versi hanno la stessa capacità e sono indipendenti.

### Le finestre di calcolo

L'HPC di ogni satellite è acceso per `duration_s` secondi ogni `period_s`, e i primi `startup_s`
servono ad avviare i container: la finestra utile è `duration_s − startup_s`. Le finestre sono
sfasate tra i satelliti in modo uniforme sul periodo; per dare a un satellite una fase propria:

```yaml
hpc_phases_s: {P1-S3: 120, COM2: 4000}
```

Allo stesso modo `plmm_overrides_gb` assegna una capacità diversa a singoli satelliti.

Le finestre si generano fino all'**orizzonte del mondo**, che va oltre la fine della simulazione
(vedi [il modello di esecuzione](../spiegazioni/modello-di-esecuzione.md#lorizzonte-del-mondo)).
La chiave `horizon_s` è facoltativa; se la scrivi e non basta, lo scenario viene rifiutato.

## Il contact plan

Il campo `kind` sceglie come sono date le finestre.

### Finestre esplicite (`windows`)

Ogni finestra, con inizio e fine. È il default, e il formato adatto quando le finestre vengono da
un propagatore orbitale:

```yaml
schema_version: "1.0.0"
links:
  - {a: COM1, b: COM2, windows: [{start_s: 1500, end_s: 2100}, {start_s: 7140, end_s: 7740}]}
  - {a: COM1, b: GS, windows: [{start_s: 2400, end_s: 2580}]}
```

### Finestre periodiche (`periodic`)

Per ogni link la prima apertura, il periodo e la durata, come l'azienda descrive i contatti:
COM-COM una volta per periodo orbitale per circa 10 minuti, COM-Terra ogni metà periodo per circa
3 minuti.

```yaml
schema_version: "1.0.0"
kind: periodic
links:
  - {a: COM1, b: COM2, first_start_s: 1500, period_s: 5640, duration_s: 600}
  - {a: COM1, b: GS, first_start_s: 2400, period_s: 2820, duration_s: 180}
  - {a: COM2, b: GS, first_start_s: 3900, period_s: 2820, duration_s: 180}
```

Le finestre si generano per quanto dura la simulazione, quindi è il formato da usare per le run
lunghe dell'orizzonte infinito. Sul caso studio questo file genera esattamente le finestre del
contact plan esplicito: c'è un test che lo verifica.

:::{note}
Un terzo tipo, che legge le finestre calcolate con Orekit da `isl-windows-visibility`, verrà
aggiunto quando quello strumento sarà riscritto.
:::

## Errori frequenti

- **Un link senza finestre**: ogni link COM-COM e COM-Terra deve comparire nel contact plan.
- **Finestre sovrapposte o che si toccano**: due finestre dello stesso link che si toccano sono
  una finestra sola; scrivila così.
- **Un orizzonte della topologia più corto della simulazione**: togli `horizon_s`, così le
  finestre arrivano dove servono.
