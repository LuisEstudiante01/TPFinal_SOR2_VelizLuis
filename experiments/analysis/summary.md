# Resultados (generado por analyze.py)

Solo corridas `measured`. CV = coeficiente de variación. IC95 = intervalo de confianza del 95% de la media (t de Student). P5 = el 5% más lento en tokens/s. `Throttled` = tiempo total throttleado del cgroup por corrida (`throttled_usec`, suma de todas las CPUs). `CPUs usadas` = consumo medio del cgroup (en Exp 3 y 4 incluye a los competidores). † = N < 30: P95 y P5 orientativos. Cliff's delta = tamaño del efecto (de -1 a 1; |d| > 0.47 es grande). p Holm = p ajustado por comparaciones múltiples (Holm-Bonferroni).

## exp1

| Condición | Prompt | N | TTFT media (s) | TTFT mediana (s) | TTFT P95 (s) | TTFT CV | tokens/s media | tokens/s IC95 | tokens/s mediana | tokens/s P5 | tokens/s P95 | tokens/s mín. | tokens/s CV | Throttles/corrida | Throttled/corrida (s) | CPUs usadas | Carga en frío (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| exp1_host | long | 30 | 0.950 | 0.942 | 1.019 | 2.7% | 26.84 | 26.74 a 26.95 | 26.93 | 26.06 | 26.98 | 25.95 | 1.0% | 0 | 0.0 | 12.01 | 1.03 |
| exp1_host | short | 30 | 0.079 | 0.079 | 0.083 | 2.5% | 27.91 | 27.83 a 28.00 | 27.98 | 27.43 | 28.01 | 27.09 | 0.8% | 0 | 0.0 | 12.01 | 1.03 |
| exp1_docker | long | 30 | 0.957 | 0.957 | 0.961 | 0.3% | 26.81 | 26.80 a 26.83 | 26.82 | 26.77 | 26.87 | 26.62 | 0.2% | 0 | 0.0 | 12.01 | 1.03 |
| exp1_docker | short | 30 | 0.079 | 0.079 | 0.082 | 1.8% | 27.92 | 27.92 a 27.93 | 27.92 | 27.90 | 27.95 | 27.87 | 0.1% | 0 | 0.0 | 12.01 | 1.03 |

| Base | Condición | Prompt | Métrica | Diferencia | Cliff's delta | p (Welch) | p Holm (Welch) | p (Mann-Whitney) | p Holm (Mann-Whitney) |
|---|---|---|---|---|---|---|---|---|---|
| exp1_host | exp1_docker | short | TTFT (s) | -0.1% | -0.11 | 0.83 | 1 | 0.48 | 0.48 |
| exp1_host | exp1_docker | short | tokens/s | +0.0% | -0.77 | 0.86 | 1 | 2.8e-07 | 6.1e-06 |
| exp1_host | exp1_docker | long | TTFT (s) | +0.7% | +0.80 | 0.15 | 0.61 | 1.1e-07 | 2.5e-06 |
| exp1_host | exp1_docker | long | tokens/s | -0.1% | -0.79 | 0.55 | 1 | 1.7e-07 | 4e-06 |

## exp2

| Condición | Prompt | N | TTFT media (s) | TTFT mediana (s) | TTFT P95 (s) | TTFT CV | tokens/s media | tokens/s IC95 | tokens/s mediana | tokens/s P5 | tokens/s P95 | tokens/s mín. | tokens/s CV | Throttles/corrida | Throttled/corrida (s) | CPUs usadas | Carga en frío (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| exp2_nolimit | long | 30 | 0.952 | 0.952 | 0.954 | 0.2% | 26.78 | 26.77 a 26.79 | 26.77 | 26.76 | 26.82 | 26.75 | 0.1% | 0 | 0.0 | 12.01 | 1.11 |
| exp2_nolimit | short | 30 | 0.079 | 0.079 | 0.081 | 1.3% | 27.88 | 27.87 a 27.90 | 27.89 | 27.87 | 27.90 | 27.68 | 0.1% | 0 | 0.0 | 12.01 | 1.11 |
| exp2_cpus8 | long | 30 | 1.463 | 1.472 | 1.481 | 1.2% | 17.28 | 17.26 a 17.30 | 17.29 | 17.20 | 17.36 | 17.18 | 0.3% | 86 | 34.6 | 8.00 | 1.11 |
| exp2_cpus8 | short | 30 | 0.123 | 0.116 | 0.151 | 11.3% | 17.95 | 17.93 a 17.97 | 17.98 | 17.86 | 18.02 | 17.85 | 0.3% | 72 | 29.1 | 8.00 | 1.11 |
| exp2_cpus4 | long | 30 | 3.005 | 3.001 | 3.081 | 1.6% | 8.26 | 8.25 a 8.28 | 8.26 | 8.19 | 8.31 | 8.15 | 0.5% | 180 | 144.1 | 4.00 | 1.40 |
| exp2_cpus4 | short | 30 | 0.262 | 0.283 | 0.289 | 12.5% | 8.57 | 8.56 a 8.58 | 8.58 | 8.53 | 8.60 | 8.48 | 0.4% | 152 | 121.7 | 4.00 | 1.40 |
| exp2_cpus2 | long | 30 | 6.710 | 6.657 | 6.902 | 2.3% | 3.61 | 3.60 a 3.62 | 3.61 | 3.58 | 3.64 | 3.53 | 0.8% | 411 | 410.8 | 2.00 | 1.70 |
| exp2_cpus2 | short | 30 | 0.565 | 0.592 | 0.598 | 8.6% | 3.78 | 3.77 a 3.79 | 3.78 | 3.74 | 3.84 | 3.71 | 0.8% | 344 | 344.1 | 2.00 | 1.70 |
| exp2_cpus1 | long | 30 | 15.125 | 15.100 | 15.354 | 0.9% | 1.77 | 1.76 a 1.77 | 1.77 | 1.75 | 1.78 | 1.75 | 0.6% | 853 | 938.0 | 1.00 | 2.70 |
| exp2_cpus1 | short | 30 | 1.362 | 1.399 | 1.496 | 4.9% | 1.93 | 1.92 a 1.94 | 1.93 | 1.90 | 1.96 | 1.88 | 0.9% | 677 | 744.9 | 1.00 | 2.70 |

| Base | Condición | Prompt | Métrica | Diferencia | Cliff's delta | p (Welch) | p Holm (Welch) | p (Mann-Whitney) | p Holm (Mann-Whitney) |
|---|---|---|---|---|---|---|---|---|---|
| exp2_nolimit | exp2_cpus8 | short | TTFT (s) | +55.6% | +1.00 | 7.5e-17 | 8.2e-16 | 3e-11 | 1.5e-09 |
| exp2_nolimit | exp2_cpus8 | short | tokens/s | -35.6% | -1.00 | 1.6e-110 | 7.4e-109 | 3e-11 | 1.5e-09 |
| exp2_nolimit | exp2_cpus8 | long | TTFT (s) | +53.7% | +1.00 | 8e-45 | 2.7e-43 | 3e-11 | 1.5e-09 |
| exp2_nolimit | exp2_cpus8 | long | tokens/s | -35.5% | -1.00 | 1.1e-84 | 4.8e-83 | 3e-11 | 1.5e-09 |
| exp2_nolimit | exp2_cpus4 | short | TTFT (s) | +231.7% | +1.00 | 1.1e-23 | 2e-22 | 3e-11 | 1.5e-09 |
| exp2_nolimit | exp2_cpus4 | short | tokens/s | -69.3% | -1.00 | 1.7e-137 | 8.5e-136 | 3e-11 | 1.5e-09 |
| exp2_nolimit | exp2_cpus4 | long | TTFT (s) | +215.8% | +1.00 | 8.4e-49 | 3e-47 | 3e-11 | 1.5e-09 |
| exp2_nolimit | exp2_cpus4 | long | tokens/s | -69.1% | -1.00 | 3.7e-116 | 1.8e-114 | 3e-11 | 1.5e-09 |
| exp2_nolimit | exp2_cpus2 | short | TTFT (s) | +614.7% | +1.00 | 7.1e-31 | 1.6e-29 | 3e-11 | 1.5e-09 |
| exp2_nolimit | exp2_cpus2 | short | tokens/s | -86.4% | -1.00 | 2e-141 | 1e-139 | 3e-11 | 1.5e-09 |
| exp2_nolimit | exp2_cpus2 | long | TTFT (s) | +605.1% | +1.00 | 1.3e-47 | 4.3e-46 | 3e-11 | 1.5e-09 |
| exp2_nolimit | exp2_cpus2 | long | tokens/s | -86.5% | -1.00 | 1.5e-142 | 8e-141 | 3e-11 | 1.5e-09 |
| exp2_nolimit | exp2_cpus1 | short | TTFT (s) | +1623.1% | +1.00 | 4.1e-39 | 1.3e-37 | 2.9e-11 | 1.5e-09 |
| exp2_nolimit | exp2_cpus1 | short | tokens/s | -93.1% | -1.00 | 2.9e-108 | 1.3e-106 | 3e-11 | 1.5e-09 |
| exp2_nolimit | exp2_cpus1 | long | TTFT (s) | +1489.4% | +1.00 | 1.2e-59 | 5e-58 | 3e-11 | 1.5e-09 |
| exp2_nolimit | exp2_cpus1 | long | tokens/s | -93.4% | -1.00 | 1.1e-122 | 5.3e-121 | 3e-11 | 1.5e-09 |

## exp3

| Condición | Prompt | N | TTFT media (s) | TTFT mediana (s) | TTFT P95 (s) | TTFT CV | tokens/s media | tokens/s IC95 | tokens/s mediana | tokens/s P5 | tokens/s P95 | tokens/s mín. | tokens/s CV | Throttles/corrida | Throttled/corrida (s) | CPUs usadas | Carga en frío (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| exp3_comp0 | long | 30 | 1.381 | 1.381 | 1.383 | 0.1% | 23.74 | 23.73 a 23.74 | 23.73 | 23.71 | 23.77 | 23.70 | 0.1% | 0 | 0.0 | 12.00 | 1.11 |
| exp3_comp0 | short | 30 | 0.106 | 0.107 | 0.109 | 2.7% | 24.52 | 24.52 a 24.53 | 24.52 | 24.51 | 24.54 | 24.50 | 0.0% | 0 | 0.0 | 12.00 | 1.11 |
| exp3_comp1 | long | 30 | 2.790 | 2.816 | 2.975 | 4.5% | 2.45 | 2.36 a 2.54 | 2.37 | 2.12 | 2.90 | 2.06 | 10.1% | 0 | 0.0 | 12.00 | 2.12 |
| exp3_comp1 | short | 30 | 0.849 | 0.929 | 1.699 | 62.9% | 2.54 | 2.44 a 2.63 | 2.48 | 2.13 | 2.95 | 1.95 | 10.3% | 0 | 0.0 | 12.00 | 2.12 |
| exp3_comp2 | long | 10† | 3.156 | 3.194 | 3.225 | 2.4% | 0.74 | 0.70 a 0.78 | 0.72 | 0.68 | 0.83 | 0.66 | 7.5% | 0 | 0.0 | 12.00 | 5.40 |
| exp3_comp2 | short | 10† | 1.483 | 1.651 | 2.142 | 49.4% | 0.75 | 0.73 a 0.78 | 0.76 | 0.71 | 0.80 | 0.70 | 5.1% | 0 | 0.0 | 12.00 | 5.40 |
| exp3_comp3 | long | 10† | 3.319 | 3.303 | 3.397 | 1.6% | 0.53 | 0.52 a 0.53 | 0.53 | 0.52 | 0.54 | 0.51 | 1.7% | 0 | 0.0 | 12.00 | 3.62 |
| exp3_comp3 | short | 10† | 1.995 | 2.135 | 2.149 | 17.5% | 0.54 | 0.53 a 0.55 | 0.54 | 0.52 | 0.57 | 0.51 | 3.7% | 0 | 0.0 | 12.00 | 3.62 |

| Base | Condición | Prompt | Métrica | Diferencia | Cliff's delta | p (Welch) | p Holm (Welch) | p (Mann-Whitney) | p Holm (Mann-Whitney) |
|---|---|---|---|---|---|---|---|---|---|
| exp3_comp0 | exp3_comp1 | short | TTFT (s) | +700.6% | +1.00 | 2.1e-08 | 1.5e-07 | 3e-11 | 1.5e-09 |
| exp3_comp0 | exp3_comp1 | short | tokens/s | -89.7% | -1.00 | 8.8e-58 | 3.4e-56 | 3e-11 | 1.5e-09 |
| exp3_comp0 | exp3_comp1 | long | TTFT (s) | +102.1% | +1.00 | 2.2e-32 | 5.3e-31 | 3e-11 | 1.5e-09 |
| exp3_comp0 | exp3_comp1 | long | tokens/s | -89.7% | -1.00 | 2.3e-58 | 9.1e-57 | 3e-11 | 1.5e-09 |
| exp3_comp0 | exp3_comp2 | short | TTFT (s) | +1298.2% | +1.00 | 0.00022 | 0.0011 | 3e-06 | 6.3e-05 |
| exp3_comp0 | exp3_comp2 | short | tokens/s | -96.9% | -1.00 | 8.2e-28 | 1.6e-26 | 3e-06 | 6.3e-05 |
| exp3_comp0 | exp3_comp2 | long | TTFT (s) | +128.5% | +1.00 | 7.1e-14 | 5.7e-13 | 3e-06 | 6.3e-05 |
| exp3_comp0 | exp3_comp2 | long | tokens/s | -96.9% | -1.00 | 1.8e-26 | 3.4e-25 | 3e-06 | 6.3e-05 |
| exp3_comp0 | exp3_comp3 | short | TTFT (s) | +1780.7% | +1.00 | 3.7e-08 | 2.2e-07 | 3e-06 | 6.3e-05 |
| exp3_comp0 | exp3_comp3 | short | tokens/s | -97.8% | -1.00 | 1.8e-34 | 5e-33 | 3e-06 | 6.3e-05 |
| exp3_comp0 | exp3_comp3 | long | TTFT (s) | +140.3% | +1.00 | 1.6e-15 | 1.6e-14 | 3e-06 | 6.3e-05 |
| exp3_comp0 | exp3_comp3 | long | tokens/s | -97.8% | -1.00 | 8.5e-96 | 3.8e-94 | 3e-06 | 6.3e-05 |

## exp4

| Condición | Prompt | N | TTFT media (s) | TTFT mediana (s) | TTFT P95 (s) | TTFT CV | tokens/s media | tokens/s IC95 | tokens/s mediana | tokens/s P5 | tokens/s P95 | tokens/s mín. | tokens/s CV | Throttles/corrida | Throttled/corrida (s) | CPUs usadas | Carga en frío (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| exp4_nice0 | long | 10† | 4.210 | 4.202 | 4.298 | 1.3% | 0.47 | 0.47 a 0.47 | 0.47 | 0.47 | 0.47 | 0.47 | 0.1% | 0 | 0.0 | 12.00 | 6.89 |
| exp4_nice0 | short | 10† | 2.196 | 2.192 | 2.243 | 1.4% | 0.47 | 0.47 a 0.47 | 0.47 | 0.47 | 0.47 | 0.47 | 0.1% | 0 | 0.0 | 12.00 | 6.89 |
| exp4_nice10 | long | 30 | 2.142 | 2.157 | 2.440 | 8.6% | 9.53 | 8.76 a 10.29 | 8.99 | 6.97 | 13.23 | 6.24 | 21.5% | 0 | 0.0 | 12.00 | 2.45 |
| exp4_nice10 | short | 30 | 0.271 | 0.246 | 0.435 | 32.7% | 10.19 | 9.21 a 11.16 | 9.25 | 7.20 | 14.89 | 7.07 | 25.6% | 0 | 0.0 | 12.00 | 2.45 |
| exp4_nice19 | long | 30 | 1.506 | 1.505 | 1.529 | 0.9% | 20.59 | 20.52 a 20.66 | 20.61 | 20.29 | 20.84 | 20.22 | 0.9% | 0 | 0.0 | 12.00 | 2.50 |
| exp4_nice19 | short | 30 | 0.122 | 0.123 | 0.130 | 5.1% | 21.32 | 21.23 a 21.40 | 21.29 | 21.05 | 21.72 | 20.99 | 1.0% | 0 | 0.0 | 12.00 | 2.50 |
| exp4_nice19_cpus2 | long | 30 | 9.392 | 9.293 | 9.400 | 6.9% | 2.83 | 2.64 a 3.02 | 2.93 | 2.75 | 2.99 | 0.19 | 17.7% | 703 | 702.7 | 2.00 | 38.80 |
| exp4_nice19_cpus2 | short | 30 | 0.838 | 0.813 | 0.899 | 6.9% | 2.89 | 2.66 a 3.12 | 3.05 | 2.05 | 3.07 | 0.10 | 21.4% | 854 | 854.1 | 2.00 | 38.80 |

| Base | Condición | Prompt | Métrica | Diferencia | Cliff's delta | p (Welch) | p Holm (Welch) | p (Mann-Whitney) | p Holm (Mann-Whitney) |
|---|---|---|---|---|---|---|---|---|---|
| exp4_nice0 | exp4_nice10 | short | TTFT (s) | -87.6% | -1.00 | 1e-47 | 3.5e-46 | 3e-06 | 6.3e-05 |
| exp4_nice0 | exp4_nice10 | short | tokens/s | +2054.1% | +1.00 | 9.6e-19 | 1.3e-17 | 3e-06 | 6.3e-05 |
| exp4_nice0 | exp4_nice10 | long | TTFT (s) | -49.1% | -1.00 | 1.2e-37 | 3.5e-36 | 3e-06 | 6.3e-05 |
| exp4_nice0 | exp4_nice10 | long | tokens/s | +1913.5% | +1.00 | 8.6e-21 | 1.4e-19 | 3e-06 | 6.3e-05 |
| exp4_nice0 | exp4_nice19 | short | TTFT (s) | -94.5% | -1.00 | 2.4e-18 | 3.1e-17 | 3e-06 | 6.3e-05 |
| exp4_nice0 | exp4_nice19 | short | tokens/s | +4406.7% | +1.00 | 7e-59 | 2.9e-57 | 3e-06 | 6.3e-05 |
| exp4_nice0 | exp4_nice19 | long | TTFT (s) | -64.2% | -1.00 | 2.3e-17 | 2.7e-16 | 3e-06 | 6.3e-05 |
| exp4_nice0 | exp4_nice19 | long | tokens/s | +4251.5% | +1.00 | 1.8e-61 | 7.8e-60 | 3e-06 | 6.3e-05 |
| exp4_nice0 | exp4_nice19_cpus2 | short | TTFT (s) | -61.8% | -1.00 | 2.8e-38 | 8.3e-37 | 3e-06 | 6.3e-05 |
| exp4_nice0 | exp4_nice19_cpus2 | short | tokens/s | +510.7% | +0.93 | 2.7e-19 | 4e-18 | 1.3e-05 | 6.3e-05 |
| exp4_nice0 | exp4_nice19_cpus2 | long | TTFT (s) | +123.1% | +1.00 | 1e-28 | 2.1e-27 | 3e-06 | 6.3e-05 |
| exp4_nice0 | exp4_nice19_cpus2 | long | tokens/s | +497.9% | +0.93 | 1.6e-21 | 2.8e-20 | 1.3e-05 | 6.3e-05 |
| exp4_nice19 | exp4_nice19_cpus2 | short | TTFT (s) | +588.8% | +1.00 | 4.1e-34 | 1.1e-32 | 3e-11 | 1.5e-09 |
| exp4_nice19 | exp4_nice19_cpus2 | short | tokens/s | -86.4% | -1.00 | 7.7e-53 | 2.9e-51 | 3e-11 | 1.5e-09 |
| exp4_nice19 | exp4_nice19_cpus2 | long | TTFT (s) | +523.6% | +1.00 | 2.7e-33 | 6.8e-32 | 3e-11 | 1.5e-09 |
| exp4_nice19 | exp4_nice19_cpus2 | long | tokens/s | -86.3% | -1.00 | 4.4e-55 | 1.7e-53 | 3e-11 | 1.5e-09 |
| exp3_comp0 | exp4_nice19 | short | TTFT (s) | +14.7% | +0.99 | 2e-15 | 1.8e-14 | 4e-11 | 1.5e-09 |
| exp3_comp0 | exp4_nice19 | short | tokens/s | -13.1% | -1.00 | 1.9e-35 | 5.3e-34 | 3e-11 | 1.5e-09 |
| exp3_comp0 | exp4_nice19 | long | TTFT (s) | +9.1% | +1.00 | 1.3e-30 | 2.9e-29 | 3e-11 | 1.5e-09 |
| exp3_comp0 | exp4_nice19 | long | tokens/s | -13.3% | -1.00 | 1.2e-38 | 3.7e-37 | 3e-11 | 1.5e-09 |
