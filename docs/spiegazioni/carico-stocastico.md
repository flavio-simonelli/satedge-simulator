# Il carico stocastico

Sul carico reale non ci sono dati: l'azienda ha fornito solo un esempio di pipeline, una L0→L1.
Le distribuzioni sono quindi scelte, ma non a caso: ognuna discende dal meccanismo che produce la
grandezza, e ogni parametro si cambia nello scenario quando arriveranno dati veri.

| Grandezza | Distribuzione | Giustificazione |
| --- | --- | --- |
| arrivi a terra | processo di Poisson, tasso $\lambda$ | molti utenti indipendenti, ciascuno con richieste rare: la loro sovrapposizione tende a un processo di Poisson (teorema di Palm-Khintchine) |
| classe di priorità | Bernoulli($p$) | una marcatura indipendente di un processo di Poisson dà due processi di Poisson indipendenti, uno per classe |
| ritardo di acquisizione | Uniforme$[0, T_{rev}]$ | il satellite acquisisce quando passa sul bersaglio; la fase dell'orbita all'istante della richiesta è casuale |
| satellite di origine | equiprobabile tra quelli che acquisiscono | bersagli distribuiti in modo uniforme, costellazione simmetrica; i COM in genere non acquisiscono |
| dimensione del raw | Uniforme$[2, 12]$ Gb | del raw si conoscono solo gli estremi del caso studio: l'uniforme è la distribuzione di massima entropia su un intervallo |
| numero di stadi | Equilikely$\{1, 2, 3\}$, aumentato se serve | la L0→L1 è scomponibile in più task sequenziali, come L1A, L1B, L1C |
| calcolo | $C$ secondi per Gb di raw, $C$ ~ Uniforme$[12, 24]$, diviso in parti uguali tra gli stadi | l'elaborazione L0→L1 è per pixel: cresce con l'immagine. Gli estremi danno in media una pipeline in una finestra, e le più grandi no, come prevede l'azienda |
| output intermedi | rapporto ~ Uniforme$[0.8, 1.2]$ dell'input | le correzioni radiometriche e geometriche trasformano l'immagine senza ridurla |
| output finale | Uniforme$[0.1, 1]$ Mb | l'informazione estratta, sotto 1 Mb nel caso studio |
| scadenza | 2 ore o 7 ore dal rilascio | le classi del caso studio; 7 ore è il centro dell'intervallo 6-8 |

## Ogni task sta in una finestra

L'azienda punta a completare almeno una pipeline per attivazione dell'HPC, e un task non può
essere interrotto: quindi **ogni task deve stare strettamente in una finestra di calcolo**,
lettura e scrittura comprese. La regola, in `StageSplitter`:

1. si estrae il numero di stadi;
2. se con quel numero un task potrebbe non stare nella finestra, si scompone più finemente, fino
   al minimo numero di stadi con cui ogni task ci sta;
3. il controllo usa il rapporto massimo degli intermedi e la velocità dell'HPC più lenta, quindi
   vale qualunque cosa venga estratta dopo;
4. se con i parametri dati nemmeno il numero massimo di stadi basta, lo scenario è rifiutato.

Con i default, un raw da 12 Gb a 24 s/Gb ha 288 s di calcolo: in un solo stadio, con la lettura,
supererebbe i 300 s della finestra, e diventa una pipeline di due stadi.

## Le richieste nascono a runtime

Un processo genera ogni richiesta al suo arrivo e la consegna al segmento di terra: nessuna
richiesta è nota prima di arrivare, come nel sistema reale. A ciò si aggiunge che ogni grandezza
ha il suo stream di numeri casuali: cambiare la distribuzione di una non cambia i numeri delle
altre, e due pianificatori diversi vedono le stesse richieste. Vedi
[i numeri casuali](numeri-casuali.md).
