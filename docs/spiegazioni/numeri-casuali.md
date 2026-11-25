# I numeri casuali

Il generatore è quello di Leemis e Park, *Discrete-Event Simulation: A First Course*: il
generatore di Lehmer a 256 stream (`rngs`), le variate (`rvgs`) e le funzioni di distribuzione
(`rvms`), nella traduzione Python di Philip Steele (licenza MIT).

## Il generatore di Lehmer

$$x_{i+1} = a \cdot x_i \bmod m, \qquad m = 2^{31} - 1, \quad a = 48271$$

$m$ è primo e $a$ è un moltiplicatore a periodo pieno: gli $m - 1$ stati formano **un unico
ciclo**, e il numero restituito è $x / m$, tra $1/m$ e $1 - 1/m$. Il prodotto è calcolato con il
metodo di Schrage, come nell'originale.

## Gli stream: tratti disgiunti dell'anello

Il ciclo è diviso in **256 stream**, tratti consecutivi di 8 367 782 stati. Lo stato iniziale
dello stream $j$ è quello dello stream $j-1$ per il moltiplicatore di salto $a^{8367782} \bmod m =
22925$: gli stream non condividono mai un numero.

```{mermaid}
flowchart LR
    s0((stream 0<br/>seed)) -->|8 367 782 numeri| s1((stream 1))
    s1 -->|8 367 782 numeri| s2((stream 2))
    s2 -.-> s255((stream 255))
    s255 -.->|il resto del ciclo| s0
```

Nel simulatore ogni grandezza casuale ha il suo stream (`Quantity`): gli arrivi lo 0, la classe
l'1, il ritardo di acquisizione il 2, e così via.

## Nessun numero si ripete

- **Dentro una run** ogni grandezza estrae solo dal suo stream.
- **Tra le repliche** il seed è esplicito solo per la prima: le repliche usano la stessa istanza
  del generatore, quindi ognuna riprende ogni stream dove la precedente l'aveva lasciato, e
  percorre un tratto nuovo.
- **Uno stream che arriva in fondo al suo tratto** solleva un errore invece di invadere quello
  successivo.

## Differenze dall'originale

| Originale | Qui | Perché |
| --- | --- | --- |
| stato e stream corrente globali | ogni generatore ha i suoi stream | due generatori nello stesso processo non si disturbano |
| le variate estraggono dallo stream corrente | ogni variata riceve lo stream da cui estrarre | una variata non cambia lo stream di un'altra |
| seed dall'orologio o da tastiera | sempre esplicito | ogni run è riproducibile |
| nessun controllo di sovrapposizione | errore a fine stream | l'indipendenza delle repliche è garantita |

## Come è verificato

I test usano i valori di controllo delle librerie originali: lo stato dopo 10 000 estrazioni dal
seed 1 (`399268537`), lo stato dello stream 1 dopo aver piantato il seed 1 (il moltiplicatore di
salto), e i quantili verificati di Student e della normale (per esempio
$t_{10, 0.975} = 2.228139$). Le variate sono controllate su valori dati a mano e sui momenti di
50 000 estrazioni.
