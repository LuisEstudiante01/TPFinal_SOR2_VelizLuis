# 3. Pregunta de investigación y objetivos

## 3.1. Pregunta de investigación

«¿En qué medida los límites de CPU impuestos mediante cgroups v2 y la competencia entre procesos afectan el tiempo hasta el primer token (TTFT), el throughput y la variabilidad de la inferencia de Ollama, y bajo qué condiciones el ajuste de prioridades del scheduler de Linux modifica ese comportamiento?»

## 3.2. Objetivo general

«Evaluar experimentalmente el impacto de los límites de CPU, la competencia entre procesos y las prioridades de scheduling sobre el rendimiento de inferencia de un LLM local ejecutado con Ollama.»

## 3.3. Hipótesis

- **H1:** «La reducción de la cuota de CPU incrementa la latencia y disminuye el rendimiento de inferencia cuando se produce throttling.»
- **H2:** «La competencia por CPU incrementa la latencia y su variabilidad respecto de una ejecución sin competencia.»
- **H3:** «Ajustar la prioridad mediante nice puede reducir la interferencia de procesos competidores, pero no necesariamente compensar las limitaciones impuestas por una cuota estricta de CPU.»

## 3.4. Objetivos específicos

- **O1:** «Comparar Ollama ejecutado directamente en Linux y dentro de Docker, sin límites adicionales de CPU.»
- **O2:** «Evaluar distintos límites de CPU mediante cgroups v2, midiendo TTFT, tokens por segundo y latencia P95.»
- **O3:** «Analizar el efecto de procesos competidores con stress-ng y diferentes valores de nice.»
- **O4:** «Relacionar los resultados con el throttling registrado en cpu.stat y las métricas del scheduler.»

Cada objetivo es verificable con una medición concreta (TTFT, tokens por segundo, P95, `nr_throttled` y `throttled_usec` de `cpu.stat`, métricas de `perf sched`) y corresponde a una sección de desarrollo y a una de resultados, como indica la Tabla 3.1.

**Tabla 3.1. Correspondencia entre objetivos, hipótesis y secciones del informe.**

| Objetivo / hipótesis | Diseño y desarrollo | Resultados y respuesta |
|---|---|---|
| O1: host frente a Docker | 5.5 (Exp 1), 7.2, 7.3 | 8.2 |
| O2: límites de CPU con cgroups v2 | 5.5 (Exp 2), 7.3 | 8.3 |
| O3: competidores y `nice` | 5.5 (Exp 3 y 4), 5.6, 7.3 | 8.4 (8.4.1 y 8.4.2) |
| O4: throttling y métricas del scheduler | 5.7, 7.1 (`sched_capture.py`) | 8.5 |
| H1 (cuota, throttling) | 5.5 (Exp 2) | 8.3, 8.5 y 8.6 |
| H2 (competencia) | 5.5 (Exp 3) | 8.4.1 y 8.6 |
| H3 (nice y cuota estricta) | 5.5 (Exp 4, incluido `nice` 19 con 2 CPUs) | 8.4.2 y 8.6 |

Fuente: elaboración propia a partir de la estructura de los capítulos 5, 7 y 8.

## 3.5. Alcance

El alcance sigue las decisiones del profesor sobre el tema, que combina los ejes C2 y C5 del catálogo de la materia:

- Se trabaja únicamente con CPU; no se usa GPU.
- El trabajo se concentra en CPU, scheduling y cgroups. No se desarrollan las actividades de C2 y C5 ajenas a ese eje, como las pruebas de entrada/salida de disco o de red.
- Se utiliza EEVDF, el scheduler del kernel Linux 7.0 del equipo de medición. El marco teórico (capítulo 4) lo compara con CFS y justifica su elección.
- SCHED_FIFO y SCHED_RR no son un requisito: se tratan de forma teórica en el capítulo 4 y con una prueba exploratoria corta (sección 4.1.7), sin conclusiones fuertes.
