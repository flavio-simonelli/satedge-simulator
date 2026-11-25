# Scegliere il pianificatore

A ogni epoca il segmento di terra chiede al pianificatore un piano per le richieste in coda. Il
pianificatore è satedge-workflow-scheduler, configurato dal file `solver.yaml` che lo scenario
nomina in `planner.solver`.

## L'euristica sequenziale

```yaml
schema_version: "1.0.0"
method: sequential
deadline: hard
```

Pianifica le richieste una alla volta, prima le urgenti, poi per scadenza (EDF). È veloce e non
richiede licenze: è la scelta per le repliche e per le run lunghe.

## Il MILP

```yaml
schema_version: "1.0.0"
method: milp
deadline: hard
milp:
  level: 6              # il modello completo, con la capacità della PLMM
  warm_start: true      # parte dalla soluzione dell'euristica
limits:
  time_limit_s: 60
```

Richiede Gurobi con una licenza valida:

```bash
uv sync --extra gurobi
```

Il formato completo di `solver.yaml` è quello dello scheduler.

## L'anticipo del calcolo

Il piano di un'epoca si calcola `lead_time_s` secondi prima dell'apertura di un contatto
COM-Terra, e deve essere pronto all'apertura. Lo scenario lo indica in `planner.lead_time_s`; se
vale `null`, si usa il limite di tempo del solver, che solo il MILP ha. Con l'euristica,
`lead_time_s` è obbligatorio.

Se il solver ci mette più dell'anticipo, la simulazione non ritarda il piano, ma le metriche
contano l'epoca come *sforamento*.

## Scadenze hard o soft

Con `deadline: hard` una richiesta che non può essere consegnata in tempo è rifiutata. Con
`deadline: soft` tutte sono accettate e il pianificatore minimizza il ritardo. Il simulatore
registra in entrambi i casi se ogni consegna è avvenuta entro la scadenza.

## Un pianificatore tuo

Il simulatore dipende dal pianificatore solo attraverso la porta `Planner`: per provare un altro
algoritmo basta implementarla. Vedi [estendere il simulatore](../sviluppo/estendere.md).
