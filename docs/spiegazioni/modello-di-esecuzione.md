# Il modello di esecuzione

Questa pagina descrive che cosa succede durante una simulazione, e perché: le scelte di modello
dietro ogni azione. Il principio che le regge tutte è uno: **il piano decide quando partono le
azioni e dove vanno i dati; tutto il resto lo decide il modello del simulatore**. Le durate, le
dimensioni, le capacità e le finestre vengono dal dominio, mai dal piano. In questa versione il
modello reale e quello del pianificatore coincidono, quindi un piano ammissibile è eseguito
esattamente; ma l'architettura permette di far divergere la realtà, ed è ciò che il simulatore
serve a misurare.

## Il ciclo di vita di una richiesta

```{mermaid}
stateDiagram-v2
    [*] --> ARRIVED : arriva a terra
    ARRIVED --> QUEUED : in coda per la prossima epoca
    QUEUED --> ACCEPTED : il pianificatore la accetta
    QUEUED --> REJECTED : il pianificatore la rifiuta
    ACCEPTED --> DELIVERED_ON_TIME : output a terra entro la scadenza
    ACCEPTED --> DELIVERED_LATE : output a terra dopo la scadenza
    ACCEPTED --> FAILED : una violazione
    ARRIVED --> UNFINISHED : fine della simulazione
    QUEUED --> UNFINISHED : fine della simulazione
    ACCEPTED --> UNFINISHED : fine della simulazione
    REJECTED --> [*]
    DELIVERED_ON_TIME --> [*]
    DELIVERED_LATE --> [*]
    FAILED --> [*]
    UNFINISHED --> [*]
```

Le transizioni sono in una tabella (`domain/lifecycle.py`): una transizione che non c'è è un
difetto del simulatore, non un evento possibile. Il rifiuto è definitivo.

## Le epoche

Il segmento di terra calcola un piano a ogni **epoca**, `lead_time_s` secondi prima
dell'apertura di un contatto COM-Terra; le aperture simultanee condividono un'epoca, e
un'apertura troppo vicina all'inizio, per cui il calcolo non farebbe in tempo, non ne ha. Il
piano è pronto all'apertura.

```{mermaid}
sequenceDiagram
    participant T as GroundRuntime
    participant R as RollingPlanner
    participant P as Planner
    participant I as PlanInstaller
    participant S as Satellite s
    Note over T: inizio dell'epoca k, t_k
    T->>T: attesa di durata zero, gli arrivi di t_k entrano
    T->>R: plan_epoch(epoca, arrivi)
    R->>P: plan(snapshot)
    P-->>R: decisione
    R-->>T: decisione
    T->>T: ACCEPTED o REJECTED, un RequestRuntime per accettata
    T->>I: install(piano, T_k_s)
    Note over I,S: a T_k_s il piano raggiunge s
    I->>S: avvia le azioni di s
```

- **La fotografia** (`PlanningSnapshot`) contiene le richieste in coda, in ordine FIFO per classe,
  gli **impegni** (le accettate non ancora concluse, con le loro azioni fisse) e l'istante in cui
  il piano raggiunge ogni satellite.
- **Gli arrivi dello stesso istante** entrano nella fotografia: prima di scattarla il segmento di
  terra attende un intervallo di durata zero, così tutti i processi dell'istante sono già passati.
- **Il rilascio visto dall'epoca** è `max(b_r, t_k)`: nessuna azione di una richiesta nuova può
  cominciare prima che sia decisa.
- **Se il pianificatore fallisce**, le richieste restano in coda per l'epoca successiva.

### La propagazione del piano

Il piano parte dalla terra quando è pronto e raggiunge ogni satellite attraversando i link: è una
lista di comandi, quindi non occupa banda, ma paga la latenza di ogni link e, per i link a
finestre, attende che si aprano. L'istante di arrivo $T^k_s$ su ogni satellite è il cammino minimo
di un **Dijkstra con il tempo**, con attesa nei nodi: arrivare prima a un nodo non fa mai arrivare
dopo il resto, quindi il primo arrivo registrato è il migliore. Un satellite che il piano non può
raggiungere ha $T^k_s = \infty$.

Un satellite conosce le sue azioni solo da $T^k_s$. Un'azione pianificata prima di
$T^k_s - \varepsilon$ non può partire: è la violazione *piano non ancora arrivato*, all'istante
pianificato dell'azione. Il MILP lo impedisce con i vincoli (30)-(31) del modello finale;
l'esecuzione lo controlla.

## Il raw

L'immagine acquisita esiste dal suo rilascio $b_r$, che la richiesta sia accettata o no: il
satellite l'ha già acquisita. Da $b_r$:

- il raw è **completo** sul satellite di origine e **occupa la sua PLMM**;
- lascia la PLMM quando lo consuma il primo task o lo trasmette il primo trasferimento, quando la
  richiesta è **rifiutata** (nessuno lo userà) o quando la richiesta fallisce;
- se a $b_r$ la richiesta è già rifiutata o fallita, non viene memorizzato;
- se la PLMM non lo contiene, è **perso**: se la richiesta viene accettata, il suo primo task
  troverà il dato mancante.

Un raw rilasciato prima che la sua richiesta arrivi a terra occupa memoria che i piani già
impegnati non conoscevano: può causare una PLMM piena che il pianificatore non aveva previsto.
È un effetto reale, che il simulatore deve poter mostrare.

## Un task

Un task occupa l'HPC del suo satellite per leggere l'input dalla PLMM, calcolare e scrivere
l'output nella PLMM. Con $\xi$ l'inizio effettivo, $r$ la velocità dell'HPC, $|i|$ e $|o|$ le
dimensioni di input e output e $e$ il calcolo:

```{mermaid}
gantt
    dateFormat X
    axisFormat %s
    section HPC
    lettura dell'input          :a, 0, 8
    calcolo                     :b, after a, 120
    scrittura dell'output       :c, after b, 1
    section PLMM
    input                       :d, 0, 129
    output                      :e, 128, 129
```

1. **All'istante pianificato** il task attende il suo input sul satellite e l'HPC, ciascuno per
   al più $\varepsilon$; se non arrivano, è una violazione (*dato non pronto*, *HPC occupato*).
2. Deve **partire in una finestra di calcolo**: altrimenti è *fuori dalla finestra di calcolo*.
3. **Legge e calcola** per $|i|/r + e$ secondi.
4. **Riserva la PLMM per l'output**, che la occupa solo mentre viene scritto, gli ultimi
   $|o|/r$ secondi. Se la memoria non si libera entro $\varepsilon$, è *PLMM piena*. Se si libera
   in ritardo, la scrittura comincia più tardi: è l'HPC che scrive, e aspetta.
5. **A fine scrittura** l'input lascia la PLMM, l'output è completo e l'HPC si libera.

Se l'input arriva in ritardo entro $\varepsilon$, l'intera esecuzione slitta dello stesso
ritardo, e con lei l'output: il ritardo si propaga a valle.

### La finestra come watchdog

Un controllo fatto all'inizio non basta: ritardi che si accumulano dopo, ciascuno entro la
tolleranza, possono portare il task oltre la finestra. Per questo l'occupazione dell'HPC è un
processo che **corre contro la chiusura della finestra**: vince il primo dei due. Se la finestra
si chiude prima, il task è interrotto, libera l'output che aveva riservato, e la violazione è
*fuori dalla finestra di calcolo*. La chiusura di ogni finestra è un solo evento, condiviso da
tutti i task di quella finestra.

```{mermaid}
sequenceDiagram
    participant A as run_task
    participant L as DataLedger
    participant H as HPC
    participant W as chiusura della finestra
    participant O as occupazione
    Note over A: istante pianificato
    A->>L: input completo? (al più ε)
    L-->>A: sì
    A->>H: request (al più ε)
    H-->>A: concesso
    A->>O: avvia lettura, calcolo, scrittura
    par
        O->>O: lettura e calcolo
        O->>O: riserva l'output, scrive
    and
        W-->>A: chiusura
    end
    alt l'occupazione finisce prima
        O-->>A: completato
        A->>L: output completo
    else la finestra si chiude prima
        A->>O: interrupt
        A->>A: violazione: fuori dalla finestra
    end
    A->>H: release
```

## Una trasmissione

Una trasmissione manda un dato su un verso di un link. Con $\xi$ l'inizio effettivo,
$D = |a| / c$ il tempo di trasmissione e $\lambda$ la latenza:

- il **canale** è occupato in $[\xi, \xi + D]$, e il mittente libera la sua copia a $\xi + D$;
- la **PLMM del ricevente** ospita il dato da $\xi + \lambda$, quando arrivano i primi bit;
- il dato è **completo** sul ricevente a $\xi + D + \lambda$;
- la **finestra di visibilità** deve durare fino all'arrivo dell'ultimo bit, $\xi + D + \lambda$:
  se si chiude prima, la trasmissione fallisce.

```{mermaid}
sequenceDiagram
    participant X as run_transfer
    participant C as canale
    participant S as invio
    participant R as ricezione
    participant W as chiusura della finestra
    X->>C: request (al più ε)
    C-->>X: concesso
    par
        S->>S: trasmette per D
        S->>C: release a ξ+D
        S->>S: il mittente libera la sua copia
    and
        R->>R: a ξ+λ riserva la PLMM del ricevente
        R->>R: a ξ+D+λ il dato è completo
    end
    alt la ricezione finisce prima della chiusura
        R-->>X: ricevuto
    else la finestra si chiude prima dell'ultimo bit
        X->>S: interrupt
        X->>R: interrupt
        X->>X: violazione: fuori dalla finestra
    end
```

Invio e ricezione sono due processi perché la latenza può essere più corta o più lunga della
trasmissione. A differenza del task, **un'attesa della PLMM del ricevente non sposta l'arrivo**:
i bit li manda il mittente, e il ricevente non può rallentarli. L'attesa è ammessa solo entro la
tolleranza.

Un trasferimento verso la stazione di terra non ha PLMM: il dato completo a terra è la consegna.

## La tolleranza e gli eventi simultanei

Molti eventi cadono nello stesso istante: un dato completo e il task che lo usa, un HPC che si
libera e il task che lo prende. SimPy li elabora in un ordine che non deve cambiare il risultato.
Per questo:

- **le precondizioni sono eventi su cui si attende**, non controlli dello stato in un istante: un
  task attende l'evento "dato completo", e se il dato arriva nello stesso istante attende zero
  secondi;
- **le risorse sono code di SimPy**: un rilascio e una richiesta nello stesso istante li ordina
  la coda;
- **ogni attesa è limitata da $\varepsilon$** (`tolerance_s`, default $10^{-4}$ s): un evento
  dentro la tolleranza è in tempo, oltre è una violazione.

## Il fallimento di una richiesta

La prima violazione fa fallire la richiesta:

1. il suo stato diventa `FAILED`;
2. le sue azioni ancora vive sono interrotte, e ciascuna libera ciò che aveva preso: la richiesta
   dell'HPC o del canale ritirata dalla coda, l'output o la ricezione riservati;
3. dopo le interruzioni di quell'istante, i suoi dati lasciano **tutte** le PLMM, raw compreso;
4. le sue azioni non ancora avviate non partiranno;
5. il segmento di terra rimuove l'impegno.

Il passo 3 serve alla coerenza con il pianificatore: tolto l'impegno, il piano successivo conta
libera quella memoria, quindi deve esserlo davvero. Fallire subito, invece di lasciare proseguire
le altre azioni, evita una cascata di violazioni *dato non pronto* che sarebbero solo rumore.

In modalità `strict` la prima violazione ferma l'intera simulazione con un errore.

## La consegna

La richiesta è consegnata quando il suo output finale è completo sulla stazione di terra, cioè
all'arrivo dell'ultimo bit: è l'istante di consegna del vincolo (28) del modello finale. È **in
tempo** se non supera la scadenza, con un confronto stretto: la tolleranza vale per le
precondizioni delle azioni, non per la scadenza, e un ritardo deve restare visibile nelle
metriche.

## L'orizzonte del mondo

L'osservazione si ferma alla fine della simulazione, ma la costellazione no. Una richiesta che
arriva poco prima della fine va pianificata contro le finestre che vengono dopo, fino alla sua
scadenza: se le finestre finissero con la simulazione, il pianificatore la rifiuterebbe solo
perché "dopo non c'è più niente", e le stime a orizzonte finito sarebbero distorte. Per questo
finestre di calcolo, contatti periodici e orizzonte del pianificatore arrivano fino all'ultima
scadenza possibile:

- con un file di richieste, la scadenza più lontana;
- con il modello stocastico, la fine più il ritardo di acquisizione massimo più la scadenza più
  lunga.

Alla fine della simulazione le richieste ancora aperte diventano `UNFINISHED`.

## Che cosa resta fuori

- **L'interrompibilità dei task**: un task deve stare in una finestra, e non riprende da uno
  snapshot alla finestra successiva. È un lavoro futuro indicato dall'azienda.
- **La memoria dell'HPC**: i dati del task in esecuzione non sono contati a parte.
- **La comunicazione interna** tra HPC, router e PLMM non è modellata come latenza, come indicato
  dall'azienda: conta solo la velocità tra HPC e router.
- **La variabilità dei valori reali**: in questa versione le durate reali sono quelle nominali.
  Le perturbazioni stocastiche cambieranno solo i valori reali, lasciando al pianificatore quelli
  nominali.
