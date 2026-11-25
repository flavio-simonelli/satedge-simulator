# Glossario

**Anticipo del calcolo** (`lead_time_s`, $\Delta_{calc}$)
: quanto prima dell'apertura di un contatto COM-Terra il segmento di terra comincia a calcolare il
  piano. Il piano è pronto all'apertura.

**As-run**
: il calendario eseguito davvero, con gli istanti effettivi di ogni task e trasmissione.

**Batch means**
: stima a orizzonte infinito: una run lunga, tagliata dopo il riscaldamento in batch le cui medie
  sono circa indipendenti.

**COM**
: il satellite di un piano che comunica con gli altri piani e con la terra.

**Epoca**
: un istante di pianificazione: il segmento di terra decide le richieste in coda e calcola il
  piano, che vale da quando raggiunge ogni satellite.

**Finestra di calcolo**
: l'intervallo in cui l'HPC di un satellite è acceso: 5 minuti per periodo orbitale nel caso
  studio.

**Finestra di visibilità**
: l'intervallo in cui un link COM-COM o COM-Terra può trasmettere.

**HPC**
: il modulo di calcolo di un satellite: esegue un task alla volta, solo nelle sue finestre.

**Impegno**
: una richiesta accettata e non ancora consegnata o fallita: le sue azioni sono fisse e il
  pianificatore non può sovrapporvi quelle nuove.

**Orizzonte del mondo**
: fin dove arrivano finestre e contatti: oltre la fine della simulazione, fino all'ultima scadenza
  possibile, perché la costellazione non smette di esistere quando smettiamo di osservarla.

**Pipeline**
: la sequenza dei task di una richiesta: L0→L1 scomposta in uno o più stadi.

**PLMM**
: la memoria di massa di un satellite: tiene l'input e l'output dei task e i dati in transito.

**Raw**
: l'immagine acquisita, l'input del primo task. È disponibile dal suo rilascio $b_r$.

**Replica**
: una run indipendente dello stesso scenario, su un tratto di numeri casuali che nessun'altra
  replica usa.

**Riscaldamento** (*warm-up*)
: la parte iniziale di una run, influenzata dallo stato iniziale, che si scarta per stimare il
  regime.

**Stream**
: un tratto dell'anello del generatore di Lehmer, riservato a una sola grandezza casuale.

**Tolleranza** ($\varepsilon$, `tolerance_s`)
: quanto un'azione può attendere le sue precondizioni oltre l'istante pianificato; oltre, è una
  violazione.

**Violazione**
: un'azione del piano che non è potuta partire come previsto.
