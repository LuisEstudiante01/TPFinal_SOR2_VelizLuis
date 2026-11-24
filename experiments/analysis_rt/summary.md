# Exp 5 exploratoria: políticas de tiempo real (generado por analyze_rt.py)

Solo corridas `measured`. Exp 5 tiene N = 5 por prompt: estadística descriptiva, sin tests ni P95. Las condiciones de referencia (`exp3_comp1`, `exp2_cpus2`) vienen de la corrida principal (N = 30). `CPUs usadas` = `usage_usec` del cgroup / tiempo de pared (incluye a los competidores). `% de la cuota` = CPUs usadas / CPUs de `cpu.max`.

| Condición | Competidor | Runner | Prompt | N | TTFT media (s) | TTFT mediana (s) | TTFT máx. (s) | tokens/s media | tokens/s mín. | tokens/s máx. | tokens/s CV | CPUs usadas | Throttles/corrida | Throttled/corrida (s) | % de la cuota |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| exp3_comp1 | SCHED_OTHER | SCHED_OTHER | short | 30 | 0.849 | 0.929 | 1.968 | 2.54 | 1.95 | 2.97 | 10.3% | 12.00 | 0 | 0.0 | - |
| exp3_comp1 | SCHED_OTHER | SCHED_OTHER | long | 30 | 2.790 | 2.816 | 2.991 | 2.45 | 2.06 | 3.08 | 10.1% | 12.00 | 0 | 0.0 | - |
| exp5_comp1_fifo | SCHED_FIFO | SCHED_OTHER | short | 5 | 2.106 | 2.103 | 2.119 | 0.48 | 0.48 | 0.48 | 0.1% | 12.00 | 0 | 0.0 | - |
| exp5_comp1_fifo | SCHED_FIFO | SCHED_OTHER | long | 5 | 3.102 | 3.122 | 3.159 | 0.48 | 0.48 | 0.48 | 0.1% | 12.00 | 0 | 0.0 | - |
| exp5_comp1_rr | SCHED_RR | SCHED_OTHER | short | 5 | 2.112 | 2.112 | 2.349 | 0.61 | 0.50 | 0.94 | 30.6% | 12.00 | 0 | 0.0 | - |
| exp5_comp1_rr | SCHED_RR | SCHED_OTHER | long | 5 | 3.294 | 3.228 | 3.675 | 0.56 | 0.49 | 0.61 | 8.9% | 12.00 | 0 | 0.0 | - |
| exp2_cpus2 | SCHED_OTHER | SCHED_OTHER | short | 30 | 0.565 | 0.592 | 0.694 | 3.78 | 3.71 | 3.84 | 0.8% | 2.00 | 344 | 344.1 | 100% |
| exp2_cpus2 | SCHED_OTHER | SCHED_OTHER | long | 30 | 6.710 | 6.657 | 6.991 | 3.61 | 3.53 | 3.68 | 0.8% | 2.00 | 411 | 410.8 | 100% |
| exp5_cpus2 | SCHED_OTHER | SCHED_OTHER | short | 5 | 0.577 | 0.594 | 0.599 | 3.76 | 3.73 | 3.77 | 0.4% | 2.00 | 346 | 346.5 | 100% |
| exp5_cpus2 | SCHED_OTHER | SCHED_OTHER | long | 5 | 6.800 | 6.800 | 6.891 | 3.53 | 3.52 | 3.55 | 0.3% | 2.00 | 430 | 430.2 | 100% |
| exp5_cpus2_rr | SCHED_OTHER | SCHED_RR | short | 5 | 0.080 | 0.079 | 0.087 | 27.69 | 27.56 | 27.73 | 0.3% | 12.01 | 0 | 0.0 | 601% |
| exp5_cpus2_rr | SCHED_OTHER | SCHED_RR | long | 5 | 0.955 | 0.955 | 0.957 | 26.60 | 26.29 | 26.69 | 0.7% | 12.01 | 0 | 0.0 | 600% |

## Contra la referencia

| Condición | Referencia | Prompt | TTFT | tokens/s |
|---|---|---|---|---|
| exp5_comp1_fifo | exp3_comp1 | short | ×2.48 | ×0.19 |
| exp5_comp1_fifo | exp3_comp1 | long | ×1.11 | ×0.20 |
| exp5_comp1_rr | exp3_comp1 | short | ×2.49 | ×0.24 |
| exp5_comp1_rr | exp3_comp1 | long | ×1.18 | ×0.23 |
| exp5_cpus2 | exp2_cpus2 | short | ×1.02 | ×0.99 |
| exp5_cpus2 | exp2_cpus2 | long | ×1.01 | ×0.98 |
| exp5_cpus2_rr | exp5_cpus2 | short | ×0.14 | ×7.37 |
| exp5_cpus2_rr | exp5_cpus2 | long | ×0.14 | ×7.53 |

## Entorno de tiempo real

- `exp5_comp1_fifo`: sched_rt_runtime_us = 950000, sched_rt_period_us = 1000000, fair_server = 50000000/1000000000 ns, prioridad RT = 1, hilos de llama-server verificados = -, kernel 7.0.0-43-generic.
- `exp5_comp1_rr`: sched_rt_runtime_us = 950000, sched_rt_period_us = 1000000, fair_server = 50000000/1000000000 ns, prioridad RT = 1, hilos de llama-server verificados = -, kernel 7.0.0-43-generic.
- `exp5_cpus2_rr`: sched_rt_runtime_us = 950000, sched_rt_period_us = 1000000, fair_server = 50000000/1000000000 ns, prioridad RT = 1, hilos de llama-server verificados = 39, kernel 7.0.0-43-generic.
