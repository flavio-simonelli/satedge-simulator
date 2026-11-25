# L'analisi statistica

Le osservazioni di una sola run non sono indipendenti: le richieste che si susseguono condividono
le stesse epoche, le stesse finestre, la stessa coda. Un intervallo di confidenza calcolato su di
esse sarebbe troppo stretto. Ogni metodo dell'analisi serve a ottenere **valori indipendenti** su
cui calcolare l'intervallo.

## L'intervallo di confidenza

Dati $n$ valori indipendenti e identicamente distribuiti, con media $\bar x$ e deviazione standard
campionaria $s$:

$$\bar x \pm t_{n-1,\, 1-\alpha/2} \, \frac{s}{\sqrt n}$$

Il quantile della $t$ di Student è `idf_student` di `rvms`. Media e varianza si calcolano in una
sola passata con l'algoritmo di Welford.

## Orizzonte finito: le repliche

Una simulazione **a orizzonte finito** ha un inizio e una fine naturali, per esempio "8 ore di
costellazione partendo con le PLMM vuote". Lo stato iniziale fa parte del modello.

Si eseguono $n$ repliche indipendenti; ognuna dà **un** valore per statistica, la sua media
sull'orizzonte, e l'intervallo si calcola sugli $n$ valori. Le repliche sono indipendenti perché
usano tratti disgiunti dell'anello del generatore.

## Il transitorio

Per vedere come il sistema evolve dallo stato iniziale si divide l'orizzonte in celle e, per ogni
cella, si calcola la **media d'insieme** sulle repliche, con il suo intervallo. Il **metodo di
Welch** smussa la curva con una media mobile di semiampiezza $w$:

$$\bar y_i(w) = \frac{1}{2w+1} \sum_{s=-w}^{w} \bar y_{i+s} \quad (i > w), \qquad
\bar y_i(w) = \frac{1}{2i+1} \sum_{s=-i}^{i} \bar y_{i+s} \quad (i \le w)$$

Il punto in cui la curva smussata si stabilizza è la fine del **riscaldamento**.

## Orizzonte infinito: i batch means

Per il comportamento **a regime**, indipendente dallo stato iniziale, si esegue una sola run
lunga, si scarta il riscaldamento e si divide il resto in $k$ batch. Se i batch sono abbastanza
lunghi le loro medie sono circa indipendenti e normali, e l'intervallo si calcola sulle $k$ medie
con $t_{k-1}$.

Le medie sono "abbastanza indipendenti" se l'**autocorrelazione a lag 1** delle medie dei batch
è piccola, sotto circa 0.2. Altrimenti i batch vanno allungati. L'autocorrelazione del campione è
lo stimatore di Leemis e Park:

$$r_j = \frac{c_j}{c_0}, \qquad c_j = \frac{1}{n} \sum_{i=0}^{n-1-j} (x_i - \bar x)(x_{i+j} - \bar x)$$

Lo studio `autocorrelation` misura $r_j$ sulle osservazioni per richiesta: una dimensione dei
batch ben oltre il lag in cui $r_j$ si spegne dà medie circa indipendenti.

## Due aspetti di questo sistema

**È periodico, non stazionario.** Le finestre di calcolo, i contatti e le epoche si ripetono con
il periodo orbitale: lo "stato stazionario" è un regime periodico. I batch nel tempo vanno presi
**multipli del periodo orbitale**, altrimenti ogni batch vede una fase diversa dell'orbita e le
medie sono distorte.

**Deve essere stabile.** Uno stato stazionario esiste solo se il carico offerto è sotto la
capacità: oltre, code e memorie crescono senza limite, e i batch means non convergono.

## Osservazioni per richiesta e nel tempo

Le statistiche per richiesta si osservano all'istante in cui si conoscono (la consegna, la
decisione), e i loro batch contano richieste. Le statistiche nel tempo (utilizzo degli HPC,
occupazione delle PLMM) sono medie temporali, e i loro batch sono intervalli di tempo. Una
richiesta ancora aperta alla fine non ha osservazioni: ciò che non è noto alla fine non è
osservato.
