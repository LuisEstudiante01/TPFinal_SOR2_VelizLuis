# 5. Metodología y stack tecnológico

## 5.1. Tipo de diseño

El trabajo adopta un diseño experimental cuantitativo y controlado: se manipula una variable independiente por vez sobre una misma plataforma y se mide su efecto sobre TTFT, tokens por segundo y su variabilidad. El diseño es factorial por etapas: cada etapa corresponde a un objetivo específico y agrega un factor a la anterior.

O1 compara Ollama en el host con Ollama en Docker sin límites; O2 aplica cuotas de `cpu.max` (cgroups v2); O3 introduce competidores `stress-ng` con distintos valores de `nice`; O4 no agrega un factor, sino que relaciona lo anterior con el throttling de `cpu.stat` y con métricas del scheduler. El único cruce de factores es `nice` 19 con cuota de 2 CPUs, para contrastar la hipótesis H3. O1 a O3 tienen referencia propia; O4 se apoya en ellas.

## 5.2. Entorno de ejecución

Todas las mediciones se realizaron en Linux nativo, en una PC dedicada accedida por SSH. WSL2 se usó solo como cliente SSH y para lanzar las corridas en `tmux`; no se midió nada sobre WSL2 ni Windows, por lo que no se compara Ollama de Windows con Ollama en un contenedor Linux. La Tabla 5.1 resume la configuración.

**Tabla 5.1. Configuración del equipo de medición.**

| Elemento | Valor |
|---|---|
| Sistema operativo | Ubuntu Server 26.04.1 LTS |
| Kernel | 7.0.0-43-generic |
| Scheduler | EEVDF (`base_slice_ns` = 2 800 000 ns, es decir 2,8 ms) |
| cgroups | v2; `stat -fc %T /sys/fs/cgroup` = `cgroup2fs`; controladores `cpuset cpu io memory hugetlb pids rdma misc dmem` |
| CPU | AMD Ryzen 9 9900X, 12 núcleos / 24 hilos, SMT y boost activados |
| Memoria | 29 GiB de RAM, 8 GiB de swap |
| Governor | `performance` en todas las CPUs |
| Docker | 29.10.0, driver de cgroups `systemd`, cgroups v2 |
| Ollama | 0.40.16 (host y contenedor, solo CPU) |
| Python | 3.14.4 (scipy 1.16.3, pandas 2.3.3, matplotlib 3.10.7) |
| `perf` / `pidstat` / `stress-ng` | 7.0.14 / sysstat 12.7.7 / 0.20.01 |

Fuente: elaboración propia a partir de `experiments/env/environment.txt`.

La ausencia de `min_granularity_ns` y `latency_ns` de CFS, reemplazados por `base_slice_ns` en `/sys/kernel/debug/sched/`, evidencia, junto con la versión del kernel, que el planificador es EEVDF. Cgroups v2 se verificó con `stat -fc %T /sys/fs/cgroup` (`cgroup2fs`) y con `cgroup.controllers`.

## 5.3. Modelo, parámetros de inferencia y prompts

Se utiliza `llama3.2:3b` con la cuantización por defecto de Ollama (Q4), cuyo `model_digest` se guarda en cada serie. Los parámetros son idénticos en las 15 condiciones: `temperature` 0, `seed` 1, `num_predict` 128 y `num_ctx` 4096, fijados junto con los prompts por `experiments/run_protocol.py`, de modo que solo cambia la condición bajo prueba.

Se emplean dos prompts en inglés. El corto (47 tokens) pide explicar qué hace un planificador de CPU; con él el TTFT mide casi solo la latencia de arranque. El largo (516 tokens), elaborado para este trabajo, es un pasaje sobre planificación, CFS, EEVDF y cgroups con la instrucción de resumirlo; con él el TTFT refleja el costo de CPU de procesar el prompt (`prompt_eval_count` fue 47 y 516 en todas las corridas). Los textos completos figuran en el Anexo A.

Cada pedido antepone un identificador único (`[request NNNN]`) para impedir que Ollama reutilice la caché del prompt anterior; sin él, el TTFT del prompt largo caía casi a cero. Por ello, en el prompt largo algunas respuestas terminan en 113 tokens en lugar de 128 (8 de 30 con N = 30 y 2 de 10 con N = 10), siempre en las mismas repeticiones, sin efecto sobre las comparaciones: tokens/s se calcula por token y el TTFT no depende del largo de la respuesta.

## 5.4. Protocolo de medición y separación de la carga inicial

Cada condición ejecuta: (1) descarga del modelo, confirmada con `/api/ps`; (2) una corrida en frío con el prompt corto, cuyo `load_s` se informa aparte; (3) un calentamiento por prompt, descartado; y (4) N corridas medidas por prompt, intercaladas para repartir la deriva térmica. La carga en frío fue de entre 1,03 s y 6,89 s en 14 condiciones y de 38,80 s en `exp4_nice19_cpus2` (2 CPUs y 12 competidores activos).

## 5.5. Repeticiones y condiciones

El N por defecto es 30 repeticiones por condición y por prompt, con el que el P95 es razonable. Con dos o más competidores Ollama cae por debajo de 1 token/s (0,74 con dos, 0,53 con tres y 0,47 en `exp4_nice0`) y una condición con N = 30 tardaba entre 3 y 6 horas; por eso, con aprobación del autor (2026-11-19), `exp3_comp2`, `exp3_comp3` y `exp4_nice0` se corren con **N = 10**. El efecto es enorme (unos 24 tokens/s sin competencia contra 0,5 a 0,75, entre 30 y 50 veces más lento), y 10 corridas bastan para distinguirlo. El margen de error de la media es unas 1,7 veces mayor (√30/√10), pero el CV de tokens/s fue de 5,1 % y 7,5 % en `exp3_comp2` y de 3,7 % y 1,7 % en `exp3_comp3` (prompt corto y largo, en ese orden) y 0,13 % en ambos prompts de `exp4_nice0`, con intervalos angostos. Lo que se pierde es precisión en el P95, que con N = 10 es casi el máximo: **el P95 de esas tres condiciones (†) es orientativo**. Las diferencias pequeñas (host contra Docker) mantienen N = 30. En total se midieron 780 corridas (12 condiciones × 30 × 2 prompts más 3 × 10 × 2).

La Tabla 5.2 lista las 15 condiciones († = N 10, P95 orientativo). El cpuset de los Experimentos 3 y 4 son las CPUs lógicas `6-11,18-23` (núcleos físicos 6 a 11 con sus hilos SMT): Ollama lanza 12 hilos y con menos CPUs que hilos la sincronización de llama.cpp se traba (incidencia I3). Se evita el núcleo 0 por sus interrupciones.

**Tabla 5.2. Matriz de condiciones experimentales.**

| Condición | Exp. (objetivo) | Destino | Cuota `cpu.max` | cpuset | Competidores (`nice`) | N por prompt |
|---|---|---|---|---|---|---|
| `exp1_host` | 1 (O1) | Host | sin límite | 0-23 | 0 | 30 |
| `exp1_docker` | 1 (O1) | Docker | sin límite | 0-23 | 0 | 30 |
| `exp2_nolimit` | 2 (O2) | Docker | sin límite | 0-23 | 0 | 30 |
| `exp2_cpus8` | 2 (O2) | Docker | 8 CPUs | 0-23 | 0 | 30 |
| `exp2_cpus4` | 2 (O2) | Docker | 4 CPUs | 0-23 | 0 | 30 |
| `exp2_cpus2` | 2 (O2) | Docker | 2 CPUs | 0-23 | 0 | 30 |
| `exp2_cpus1` | 2 (O2) | Docker | 1 CPU | 0-23 | 0 | 30 |
| `exp3_comp0` | 3 (O3) | Docker | sin límite | 6-11,18-23 | 0 | 30 |
| `exp3_comp1` | 3 (O3) | Docker | sin límite | 6-11,18-23 | 1 (0) | 30 |
| `exp3_comp2` | 3 (O3) | Docker | sin límite | 6-11,18-23 | 2 (0) | 10 † |
| `exp3_comp3` | 3 (O3) | Docker | sin límite | 6-11,18-23 | 3 (0) | 10 † |
| `exp4_nice0` | 4 (O3) | Docker | sin límite | 6-11,18-23 | 12 (0) | 10 † |
| `exp4_nice10` | 4 (O3) | Docker | sin límite | 6-11,18-23 | 12 (10) | 30 |
| `exp4_nice19` | 4 (O3) | Docker | sin límite | 6-11,18-23 | 12 (19) | 30 |
| `exp4_nice19_cpus2` | 4 (O3) | Docker | 2 CPUs | 6-11,18-23 | 12 (19) | 30 |

Fuente: elaboración propia a partir de `experiments/run_matrix.py`.

Las cuotas se aplican con `docker update --cpus`, que escribe `cpu.max` (p. ej. `200000 100000` para 2 CPUs, período de 100 ms); para quitarlas se usa `--cpu-quota -1`, porque `--cpus 0` no lo hace (incidencia I2).

## 5.6. Verificación de que los competidores comparten la CPU

Con cgroups v2 el scheduler reparte la CPU primero entre cgroups (`cpu.weight`) y luego entre los procesos de cada uno (`nice`). Si `stress-ng` corriera en otro cgroup, su `nice` no alteraría el reparto frente a Ollama y el Experimento 4 sería inválido. Por eso el competidor (`stress-ng --cpu N --cpu-method matrixprod`) se incorpora al `cgroup.procs` del contenedor de Ollama y se lanza con `nice` y `taskset -c` sobre el mismo cpuset; en consecuencia, `cpu.stat` suma a ambos en los Experimentos 3 y 4.

La verificación de que Ollama y los competidores comparten CPU tiene cuatro niveles: (1) a los 3 s del lanzamiento se cuentan los `stress-ng-cpu` del cgroup y se comprueban `nice` y afinidad; (2) al terminar cada condición se registra `competitors_alive`; (3) un vigilante de solo lectura (`experiments/watch_competitors.sh`) anotó cada 15 s el estado, con 2 353 muestras entre 07:20:20 y 17:09:42 UTC, constantes en los Experimentos 3 y 4; (4) el consumo medio del cgroup (`cpu_usec_delta` sobre el tiempo de la corrida) fue de 12,00 CPUs sin cuota y de 2,00 con cuota de 2 CPUs.

## 5.7. Métricas y forma de medición

La Tabla 5.3 detalla cada métrica. El TTFT se mide del lado del cliente con `time.perf_counter()`, del envío del pedido al primer fragmento no vacío en streaming. Tokens/s es `eval_count / eval_s` con los campos crudos de Ollama, no el CSV redondeado, que a unos 0,47 tokens/s ocultaba la variabilidad (incidencia I7). El throttling es la diferencia de `nr_throttled` y `throttled_usec` de `cpu.stat` antes y después de cada corrida, del cgroup del contenedor (`docker-<id>.scope`) o, en el host, de `ollama.service`.

**Tabla 5.3. Métricas, definición y fuente.**

| Métrica | Cómo se obtiene | Fuente |
|---|---|---|
| TTFT (s) | Tiempo al primer fragmento con texto, del lado del cliente | Streaming de `/api/generate` |
| tokens/s | `eval_count / eval_s` | Estadísticas finales de Ollama |
| Carga en frío (s) | `load_duration` de la corrida en frío | Ollama |
| Throttling | Delta de `nr_throttled` y `throttled_usec` por corrida | `cpu.stat` del cgroup |
| CPUs usadas | `cpu_usec_delta` / tiempo de la corrida | `usage_usec` de `cpu.stat` |
| Tiempo corriendo y esperando por hilo | Delta de `schedstat` por hilo en una ventana de 20 s | `/proc/<pid>/task/<tid>/schedstat` |
| Demora de scheduling y cambios de contexto | `perf sched record/latency`; `pidstat -u -w -t` | `perf`, `sysstat` |

Fuente: elaboración propia a partir de `experiments/run_protocol.py` y `experiments/sched_capture.py`.

Las métricas del scheduler (O4) se capturan en una corrida separada, porque `perf` agrega carga: durante 20 s, con Ollama generando sin pausa con el prompt largo, `experiments/sched_capture.py` registra tiempo en cola, demora de scheduling, cambios de contexto y throttles. Se capturaron 10 condiciones: 8 iniciales y 2 agregadas tras una revisión técnica posterior (`exp2_cpus2` y `exp4_nice0`).

## 5.8. Análisis estadístico

El análisis (`experiments/analyze.py`) usa solo corridas `measured`. Por condición y prompt calcula N, media, desvío, CV, mediana, P5, P95, mínimo, máximo e IC del 95 % (t de Student). Como el P95 de tokens/s representa el 5 % más rápido, se informan también P5 y mediana, necesarios con cola lenta: en `exp4_nice19_cpus2` tres bloqueos (102 s, 600 s y 1 261 s, frente a unos 45 s normales) desplazan la media.

Cada condición se compara con la referencia de su experimento (`exp1_host`, `exp2_nolimit`, `exp3_comp0`, `exp4_nice0`), más los pares `exp4_nice19` contra `exp4_nice19_cpus2` y `exp3_comp0` contra `exp4_nice19`. Por par, prompt y métrica se calculan la diferencia relativa de medias, el test t de Welch, el U de Mann-Whitney (las distribuciones lentas no son normales) y el delta de Cliff (|d| > 0,47 = efecto grande); los p-valores se corrigen con Holm-Bonferroni sobre toda la familia.

## 5.9. Amenazas a la validez

- **Validez externa.** Una máquina, un modelo (`llama3.2:3b`), dos prompts y solo CPU; no se extrapola a otros procesadores, modelos ni GPU. Los 12 hilos de Ollama dependen del equipo y el colapso bajo competencia está ligado a esa configuración.
- **Configuración favorable.** Governor `performance`, boost y SMT reducen la variabilidad, pero no reproducen un servidor con gestión de energía por defecto.
- **Competidores en el mismo cgroup.** Necesario para que `nice` tenga efecto, pero no modela vecinos en otros cgroups y mezcla a Ollama con `stress-ng` en `cpu.stat`; `matrixprod` es carga de CPU pura, no una aplicación real.
- **N = 10 en tres condiciones.** El P95 es orientativo; CV e intervalos respaldan la conclusión sobre la media, no sobre la cola.
- **Scheduler medido aparte.** La ventana de 20 s no coincide en el tiempo con las corridas y no reprodujo los tres bloqueos de `exp4_nice19_cpus2`; la espera activa de hilos es una hipótesis, no una causa demostrada.
- **TTFT del lado del cliente.** Incluye la latencia HTTP local, pequeña y constante; se interpreta de forma comparativa. El prompt largo no es de un conjunto estándar.
- **Corrida única.** Las 15 condiciones se midieron en una sola corrida continua de 10 h 15 min (06:55 a 17:09 UTC), expuesta a derivas (temperaturas de 42,1 °C a 67,8 °C).
- **Instancias de Ollama.** En O1 el host usa el puerto 11434 y Docker el 11435, con el modelo de la otra instancia descargado antes de cada serie; versiones y digest son los mismos.

## 5.10. Justificación del stack tecnológico

La Tabla 5.4 justifica cada herramienta frente a sus alternativas; lo no medido en este trabajo son estimaciones del autor y se marca como tal.

**Tabla 5.4. Herramientas elegidas y alternativas consideradas.**

| Decisión | Elegida | Alternativas | Justificación |
|---|---|---|---|
| Motor de inferencia | Ollama 0.40.16 | llama.cpp directo; vLLM | El objetivo general exige Ollama, que gestiona la carga, la API y los tiempos (`load_duration`, `eval_duration`) que alimentan las métricas; llama.cpp directo exigiría instrumentarlos. vLLM está orientado a GPU y a muchos pedidos (estimación), fuera del alcance de solo CPU. |
| Modelo | `llama3.2:3b` (Q4) | `llama3.1:8b`; `mistral:7b` | Pesa unos 2 GB y ronda las decenas de tokens/s (~28 tokens/s en una prueba de humo, 2 corridas), lo que permite más repeticiones. El 8b (~4,7 GB, ~10 a 15 tokens/s, estimación) y el de mistral (~4,1 GB, estimación) volverían muy lentas las cuotas del Exp. 2. El trabajo mide latencia, no calidad de respuesta. |
| Aislamiento | Docker 29.10.0 | Podman, LXC, `systemd-run` | O1 pide comparar contra Docker, y es la herramienta del catálogo sugerido. Escribe `cpu.max` y `cpuset` mediante `--cpus` y `--cpuset-cpus`, y su cgroup es legible desde el host. No se evaluaron otros motores de contenedores. |
| Límite de CPU | `cpu.max` (cgroups v2) | `cpuset` / `taskset` | La pregunta de investigación pide cuotas con cgroups v2. `cpu.max` limita el tiempo de CPU y genera throttling observable en `cpu.stat`; `cpuset` y `taskset` limitan qué CPUs pueden usarse, pero no producen throttling. Se usan solo para fijar los núcleos compartidos en Exp. 3 y 4. |
| Competidores | `stress-ng` 0.20.01 (`matrixprod`) | Bucles propios (`yes`, scripts); otros generadores de carga | O3 lo exige explícitamente. Permite fijar el número de workers y se ejecuta bajo `nice` y `taskset`. Un bucle propio daría menos control (estimación). |
| Prioridad | `nice` | `chrt` (`SCHED_FIFO`, `SCHED_RR`) | `nice` actúa dentro de la clase fair y es compatible con `cpu.max`. `SCHED_FIFO` y `SCHED_RR` son de tiempo real, sin equidad, y se dejaron como extensión opcional. Se baja el `nice` de los competidores y no se sube el de Ollama, porque esto requeriría `nice` negativo, más invasivo. |
| Métricas del scheduler | `perf sched`, `pidstat`, `schedstat` | Solo `cpu.stat` | `cpu.stat` explica la cuota (Exp. 2), pero no la competencia sin throttling. `schedstat` da el tiempo en cola por hilo, `perf sched` la demora y los cambios de contexto por tarea, y `pidstat` el % de CPU. Se cruzan tres fuentes para validar la misma lectura. |
| Análisis | Python (pandas, scipy, matplotlib) | Hojas de cálculo; R | scipy está en el catálogo sugerido; permite Welch, Mann-Whitney y percentiles con un script reproducible y versionado. El protocolo de medición usa solo la biblioteca estándar, para correr en un Ubuntu Server recién instalado. |
| Seguimiento de tareas | Notion | Lista en un archivo de texto; tablero propio | Permite ver qué tareas faltan y marcarlas como Pendiente, En curso o Hecho, de modo que el avance del trabajo se consulta de un vistazo. Una lista en un archivo de texto no distingue estados con la misma claridad (estimación). |
| Notas y documentación | Obsidian | Documentos de Word o PDF sueltos; Notion | Permite separar cada tarea y cada sección del trabajo en archivos de texto Markdown (`.md`), lo que facilita la lectura rápida, tanto para el autor como para los asistentes de IA usados en el trabajo. |
| Asistente de IA orquestador | Claude Opus 5.5 (en el entorno pi) | Escribir todo sin asistencia; un solo asistente que escriba y revise | Coordina el trabajo y escribe el código, los scripts y el texto a partir de `docs/SPEC.md`, que funciona como fuente de verdad. Separar a quien escribe de quien revisa evita que un mismo asistente apruebe su propio trabajo. |
| Asistente de IA auditor | Gemini 4 Neon (en Antigravity) | Revisión solo del autor; el mismo asistente que escribe | Revisa en modo de solo lectura si lo entregado cumple `docs/SPEC.md` y deja cada informe, con evidencia, en `docs/auditorias/`. Al ser de otro proveedor, aporta una mirada independiente de la del orquestador (estimación). |
| Ecosistema de trabajo con IA | Gentle AI (Gentleman Programming, s. f.) | Usar los asistentes sin un flujo común; organizar a mano tareas y revisiones | Coordina a los dos asistentes dentro de un mismo flujo de trabajo: divide el trabajo en tareas, delega en subagentes, guarda memoria entre sesiones y agrega una revisión antes de cerrar cada cambio. Se reconoce como contribución al desarrollo del trabajo. |

Fuente: elaboración propia a partir de las decisiones de diseño del trabajo y de `experiments/env/environment.txt`.

Los dos asistentes de IA tienen roles separados. Claude Opus 5.5 actúa como orquestador: planifica las tareas y escribe el código y el texto. Gemini 4 Neon actúa como auditor: no edita archivos y contrasta cada entrega con `docs/SPEC.md`. El autor define el SPEC, decide qué hallazgos de la auditoría se aplican y revisa el resultado; ninguno de los dos asistentes puede cambiar el SPEC sin su aprobación. Ambos trabajaron dentro del ecosistema Gentle AI (Gentleman Programming, s. f.), cuya contribución fue organizar el flujo de trabajo con tareas, subagentes, memoria entre sesiones y revisión de cada cambio. Las cifras del capítulo 8 provienen de las corridas del banco de pruebas, no de los asistentes.

Los fundamentos de EEVDF, CFS, cgroups v2 y `nice` se desarrollan en el marco teórico (The Linux Kernel documentation, s. f.-b, s. f.-c; Kerrisk, s. f.-e), junto con la inferencia de LLM en CPU con llama.cpp (ggml-org, s. f.). El diseño de la medición de latencia se apoya en las definiciones de TTFT y de tiempo por token de salida (Wang et al., 2024; Zhong et al., 2024), y el análisis estadístico, en SciPy (Virtanen et al., 2020) y en los tests de Welch (1947) y de Mann y Whitney (1947), el delta de Cliff (1993) y la corrección de Holm (1979).
