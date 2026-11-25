# Decisioni

Le scelte che danno forma al simulatore, con il loro perché. Ognuna si può rivedere; questa
pagina serve a farlo sapendo che cosa comporta.

## Un modello fisico proprio

**Decisione.** Il simulatore ha il suo modello della rete e delle richieste; lo scheduler è
importato solo dal suo adattatore, che traduce in un verso e nell'altro.

**Perché.** Il simulatore deve poter rappresentare una realtà diversa dal modello del MILP, e la
verifica deve essere indipendente. Con un modello condiviso, ogni errore del modello si
ripeterebbe nella sua verifica.

## Il piano decide solo quando e dove

**Decisione.** Durate, dimensioni, capacità e finestre vengono dal dominio; dal piano vengono
solo gli istanti di partenza delle azioni e i percorsi dei dati.

**Perché.** Se il runtime leggesse le durate dal piano, non potrebbe mai mostrare uno
scostamento tra piano e realtà, che è proprio ciò che serve misurare quando la realtà sarà
stocastica.

## SimPy, con le precondizioni come eventi

**Decisione.** L'esecuzione usa SimPy; le precondizioni sono eventi su cui si attende, le risorse
code di SimPy, e ogni attesa è limitata dalla tolleranza.

**Perché.** Il risultato non dipende dall'ordine in cui SimPy elabora gli eventi simultanei,
senza bisogno di una tabella di priorità tra i tipi di evento.

## Le finestre come watchdog

**Decisione.** Un task e una trasmissione corrono contro la chiusura della loro finestra, invece
di controllarla una volta all'inizio.

**Perché.** Ritardi che si accumulano dopo l'inizio, ciascuno entro la tolleranza, possono
superare la finestra; un solo controllo copre ogni ritardo presente e futuro, comprese le durate
stocastiche.

## La prima violazione fa fallire la richiesta

**Decisione.** Alla prima violazione la richiesta fallisce: le sue azioni sono interrotte e i suoi
dati lasciano le PLMM.

**Perché.** Una pipeline è sequenziale: senza un dato le azioni successive fallirebbero a catena,
generando rumore. Liberare le PLMM mantiene la realtà coerente con il pianificatore, che conta
libera la memoria dell'impegno rimosso.

## Il raw occupa la PLMM dal suo rilascio

**Decisione.** Il raw occupa la PLMM di origine da $b_r$, accettata o no la richiesta, e la
lascia se la richiesta è rifiutata o fallisce.

**Perché.** L'immagine esiste da quando il satellite l'ha acquisita, indipendentemente dalle
decisioni di terra.

## L'orizzonte del mondo va oltre la fine

**Decisione.** Finestre, contatti periodici e orizzonte del pianificatore arrivano fino all'ultima
scadenza possibile.

**Perché.** Senza, le richieste arrivate vicino alla fine sarebbero rifiutate solo perché le
finestre finiscono lì: in una run di 8 ore lo erano tutte le richieste rifiutate, e le stime a
orizzonte finito erano distorte.

## La consegna in tempo con un confronto stretto

**Decisione.** Una richiesta è in tempo se la consegna non supera la scadenza, senza tolleranza.

**Perché.** La tolleranza serve alle precondizioni delle azioni; il ritardo è una misura e deve
restare visibile.

## Un deterministico prima, lo stocastico dopo

**Decisione.** In questa versione la realtà coincide con il modello nominale; il carico può
essere stocastico, le durate reali no.

**Perché.** Prima si verifica che il simulatore esegua correttamente un piano ammissibile; poi le
perturbazioni stocastiche cambieranno solo i valori reali, lasciando al pianificatore quelli
nominali.

## Distribuzioni scelte senza dati, ma giustificate

**Decisione.** Le distribuzioni del carico discendono dal meccanismo di ogni grandezza (vedi
[il carico stocastico](carico-stocastico.md)), e ogni parametro è configurabile.

**Perché.** Non ci sono dati sul carico reale; una scelta motivata e documentata si può
discutere e sostituire quando arriveranno.

## Il generatore di Leemis e Park, senza stato globale

**Decisione.** Il generatore di Lehmer a 256 stream, con il seed esplicito, uno stream per
grandezza e un errore a fine stream.

**Perché.** È un generatore studiato e verificabile con valori di controllo noti; gli stream
disgiunti rendono le repliche indipendenti e i confronti tra pianificatori a parità di carico.
