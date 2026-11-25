# Analizzare l'output

Con un carico stocastico una run è un solo campione: cambiando il seed cambiano tutti i numeri.
Per dire "il tempo di risposta medio è 2180 ± 120 s al 95 %" servono più run, eseguite e
combinate nel modo giusto. Il simulatore offre tre studi; la teoria dietro ognuno è in
[l'analisi statistica](../spiegazioni/analisi-statistica.md).

| Domanda | Studio | Comando |
| --- | --- | --- |
| Com'è andato, in media, un periodo di durata fissata partendo da vuoto? | orizzonte finito | `replicate` |
| Quanto ci mette il sistema a stabilizzarsi? | transitorio | `replicate` |
| Come si comporta a regime, indipendentemente dallo stato iniziale? | orizzonte infinito | `batch` |
| Quanto devono essere lunghi i batch? | autocorrelazione | `autocorrelation` |

Le statistiche sono le stesse per tutti gli studi:

| Statistica | Che cosa misura | Quando si osserva |
| --- | --- | --- |
| tempo di risposta | consegna meno rilascio del raw | alla consegna |
| frazione accettata | 1 se accettata, 0 se rifiutata | alla decisione |
| frazione in tempo | delle accettate, 1 se consegnata entro la scadenza | alla fine della richiesta |
| utilizzo degli HPC | tempo occupato sul tempo di finestra | nel tempo |
| occupazione delle PLMM | memoria occupata in tutte le PLMM | nel tempo |

## Orizzonte finito: le repliche

```bash
uv run satedge-simulator replicate examples/casostudio/scenario-stocastico.yaml -n 30 -o output/repliche
```

Esegue 30 repliche dello scenario, dall'inizio alla fine. Ognuna riprende il generatore dove si
era fermata la precedente, quindi le repliche sono indipendenti. Per ogni statistica stampa la
media sulle repliche con il suo intervallo; per esempio, con `-n 10`:

```text
Orizzonte finito: 10 repliche dal seed 123456789, intervalli al 95%.
  tempo di risposta dal rilascio (s): 2277.39 ± 227 (10 repliche)
  utilizzo degli HPC: 0.157266 ± 0.0244 (10 repliche)
  …
```

Quante repliche? L'intervallo si stringe come `1/√n`: per dimezzarlo servono quattro volte le
repliche. 30 è un buon punto di partenza.

## Il transitorio

Lo stesso comando scrive `transient.csv`: per ogni statistica e ogni cella della griglia
(`--cell`, di default mezzo periodo orbitale) la media sulle repliche, il suo intervallo e la
media mobile di Welch (`--welch`, in celle):

```text
statistic,start_s,end_s,mean,half_width,count,welch
response_s,0.0,2820.0,1422.33,,1,
response_s,2820.0,5640.0,2771.18,854.67,3,
```

Disegna `mean` e `welch` in funzione di `start_s`: il punto in cui la curva di Welch smette di
salire o scendere è la fine del **riscaldamento**. Per vederlo bene servono uno scenario lungo
quanto basta a stabilizzarsi e molte repliche.

## Orizzonte infinito: i batch means

Serve uno scenario lungo, con i contatti periodici: `scenario-regime.yaml` dura 7 giorni.

```bash
uv run satedge-simulator batch examples/casostudio/scenario-regime.yaml --warmup 86400 -b 32 -o output/batch
```

Esegue una sola run, scarta il riscaldamento (`--warmup`, in secondi) e taglia il resto in
batch:

- le statistiche per richiesta in batch di `-b` richieste consecutive;
- quelle nel tempo in batch di `--batch-duration` secondi, di default un periodo orbitale.

L'intervallo è calcolato sulle medie dei batch. Per ogni statistica il comando stampa anche
l'**autocorrelazione a lag 1 delle medie dei batch**, e avverte quando supera 0.2:

```text
  tempo di risposta dal rilascio (s): 2178.11 ± 119 (36 batch), autocorrelazione dei batch 0.093
  occupazione totale delle PLMM (Gb): 27.16 ± 2.09 (91 batch), autocorrelazione dei batch 0.335 (troppo alta: allungare i batch)
```

Sopra 0.2 i batch non sono abbastanza lunghi da essere indipendenti, e l'intervallo sarebbe
troppo stretto: allunga i batch (`-b` o `--batch-duration`) finché l'avviso sparisce. Per le
statistiche nel tempo usa un **multiplo del periodo orbitale**, perché finestre e contatti si
ripetono con quel periodo.

## Scegliere la dimensione dei batch

```bash
uv run satedge-simulator autocorrelation examples/casostudio/scenario-regime.yaml --warmup 86400 --max-lag 50
```

Misura l'autocorrelazione delle statistiche per richiesta e dice da quale lag scende sotto 0.2.
Una dimensione dei batch ben oltre quel lag, per esempio cinque volte, dà medie dei batch circa
indipendenti. `autocorrelation.csv` ha la funzione intera, lag per lag.

## Il flusso consigliato

```{mermaid}
flowchart TD
    A[replicate su uno scenario lungo] --> B{Welch: dove si stabilizza?}
    B -->|riscaldamento W| C[autocorrelation con --warmup W]
    C --> D{da quale lag j la correlazione è sotto 0.2?}
    D -->|b molto oltre j| E[batch con --warmup W e -b b]
    E --> F{autocorrelazione dei batch sotto 0.2?}
    F -->|no| G[batch più lunghi] --> E
    F -->|sì| H[stime a regime con intervallo]
```

Se invece la domanda è a orizzonte finito ("una giornata"), le repliche bastano: il transitorio
fa parte di ciò che si vuole misurare, e non va scartato.
