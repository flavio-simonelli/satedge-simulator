# satedge-simulator

**satedge-simulator** simula, evento dopo evento, una costellazione di satelliti in orbita bassa
che elabora a bordo le immagini che acquisisce. Le richieste nascono a terra; un pianificatore
centralizzato decide, a ogni contatto con la costellazione, quali accettare, su quali satelliti
eseguire i task delle loro pipeline e per quali link far passare i dati; il simulatore esegue quel
piano nel tempo e misura come va.

Il pianificatore è [satedge-workflow-scheduler](https://github.com/flavio-simonelli/satedge-workflow-scheduler),
con il modello MILP o con la sua euristica sequenziale. Il simulatore ha però un **modello fisico
proprio**: il piano decide solo *quando* partono le azioni e *dove* vanno i dati, mentre durate,
dimensioni, finestre e capacità vengono dal modello del simulatore. Così l'esecuzione può
discostarsi dal piano, e il simulatore lo vede.

```{mermaid}
flowchart LR
    U([Utenti]) -->|richieste| G[Segmento di terra]
    G -->|snapshot di un'epoca| P[[Pianificatore<br/>MILP o euristica]]
    P -->|piano| G
    G -->|piano, via i COM| C[Costellazione<br/>HPC, PLMM, link]
    C -->|output finale| G
    C -.->|notifiche| M[Metriche, log,<br/>analisi dell'output]
```

## Da dove cominciare

| Se vuoi... | Leggi |
| --- | --- |
| eseguire la prima simulazione | il [tutorial](tutorial/prima-simulazione.md) |
| descrivere costellazione e contatti | la guida [descrivere la rete](guide/rete.md) |
| descrivere il carico, da file o stocastico | la guida [descrivere il carico](guide/carico.md) |
| scegliere tra euristica e MILP | la guida [scegliere il pianificatore](guide/pianificatore.md) |
| stimare le prestazioni con intervalli di confidenza | la guida [analizzare l'output](guide/analisi.md) |
| conoscere ogni chiave dei file e ogni comando | il [riferimento](riferimento/file-di-input.md) |
| capire come funziona dentro | l'[architettura](spiegazioni/architettura.md) e il [modello di esecuzione](spiegazioni/modello-di-esecuzione.md) |
| modificare o estendere il codice | la sezione [sviluppo](sviluppo/ambiente.md) |

```{toctree}
:caption: Tutorial
:maxdepth: 1
:hidden:

tutorial/prima-simulazione
```

```{toctree}
:caption: Guide pratiche
:maxdepth: 1
:hidden:

guide/rete
guide/carico
guide/pianificatore
guide/analisi
```

```{toctree}
:caption: Riferimento
:maxdepth: 1
:hidden:

riferimento/cli
riferimento/file-di-input
riferimento/risultati
riferimento/errori
riferimento/api
riferimento/glossario
```

```{toctree}
:caption: Spiegazioni
:maxdepth: 1
:hidden:

spiegazioni/architettura
spiegazioni/modello-di-esecuzione
spiegazioni/carico-stocastico
spiegazioni/numeri-casuali
spiegazioni/analisi-statistica
spiegazioni/verifica
spiegazioni/decisioni
```

```{toctree}
:caption: Sviluppo
:maxdepth: 1
:hidden:

sviluppo/ambiente
sviluppo/test-e-qualita
sviluppo/estendere
```
