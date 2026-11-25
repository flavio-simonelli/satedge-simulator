# La verifica dell'esecuzione

Il simulatore e lo scheduler hanno due modelli separati del sistema. La verifica li confronta:
ciò che il simulatore ha consegnato deve rispettare **tutti i vincoli del modello finale** del
MILP, controllati dal verificatore di ammissibilità dello scheduler (`feasibility.check`).

## Che cosa si controlla

Il controllo procede epoca per epoca. Per l'epoca $k$ si costruisce un'istanza dello scheduler
con:

- **le richieste nuove**: quelle accettate nell'epoca $k$ e consegnate, con il rilascio visto da
  quell'epoca, $\max(b_r, t_k)$;
- **il calendario impegnato**: l'as-run delle richieste consegnate accettate nelle epoche
  precedenti, così che la contesa su HPC, link e PLMM sia controllata anche tra le epoche;
- **il rilascio del piano**: gli istanti $T^k_s$ in cui il piano di quell'epoca raggiunge ogni
  satellite.

La soluzione da controllare è l'as-run di tutte, con le consegne effettive. Ogni violazione del
modello è riportata una volta sola, nella prima epoca in cui compare, con il nome italiano della
famiglia di vincoli, per esempio `(8)-(10) un task alla volta sull'HPC`.

## Che cosa non si controlla

Restano fuori le richieste fallite, eseguite a metà, i raw delle richieste rifiutate o ancora in
coda, e l'occupazione reale delle PLMM: il MILP non li vede. Il controllo dice che *ciò che è
stato consegnato* rispetta il modello, non che *tutta* la memoria reale sia nei limiti; questo lo
misurano le metriche e le violazioni *PLMM piena*.

## Che cosa significa il risultato

In questa versione il modello reale coincide con quello nominale, quindi su un piano ammissibile
la verifica deve passare: sul caso studio passa, con uno scostamento tra eseguito e pianificato
dell'ordine di $10^{-12}$ s, cioè gli arrotondamenti. Un controllo che fallisce indica un piano
sbagliato o un difetto del simulatore; un test sposta a mano un task di un secondo e controlla che
la verifica lo trovi.
