# 4. Marco teórico

## 4.1. Planificación de CPU en Linux: CFS, EEVDF, SCHED_FIFO y SCHED_RR

Esta sección explica por qué el trabajo estudia el scheduler por defecto de Linux, EEVDF, y deja SCHED_FIFO y SCHED_RR como una prueba exploratoria. La justificación es teórica; la prueba de la sección 4.1.7 solo ilustra sus consecuencias y no aporta conclusiones fuertes.

### 4.1.1. Clases de planificación

El scheduler de Linux organiza las tareas en clases ordenadas por prioridad: *stop*, *deadline* (SCHED_DEADLINE), *tiempo real* (SCHED_FIFO y SCHED_RR), *fair* (SCHED_OTHER, SCHED_BATCH y SCHED_IDLE) e *idle* (Kerrisk, s. f.-e; The Linux Kernel documentation, s. f.-a). En cada CPU se elige siempre una tarea de la clase más alta que tenga alguna lista para ejecutar. Por eso una tarea de tiempo real lista desplaza a cualquier tarea de la clase *fair*, sin importar su valor de `nice`.

Ollama, `stress-ng` y casi todos los procesos de un servidor corren en la clase *fair* con la política SCHED_OTHER. Es la clase que se mide en los experimentos 1 a 4.

### 4.1.2. La clase fair: de CFS a EEVDF

**CFS** (*Completely Fair Scheduler*) fue el algoritmo de la clase *fair* desde el kernel 2.6.23 hasta el 6.5 (The Linux Kernel documentation, s. f.-a; Corbet, 2023a). CFS ordena las tareas listas en un árbol rojo-negro según su *vruntime*: el tiempo de CPU recibido, escalado por el peso de la tarea. Siempre elige la de menor *vruntime*. El peso sale del valor de `nice`: 1024 para `nice` 0, 110 para `nice` 10 y 15 para `nice` 19 (Kerrisk, s. f.-e; Linux Kernel Developers, 2026). Cada paso de `nice` cambia la proporción de CPU en alrededor de un 10 %. Para controlar la latencia, CFS dependía de parámetros heurísticos como `sched_min_granularity_ns`, `sched_latency_ns` y las reglas de expropiación al despertar.

**EEVDF** (*Earliest Eligible Virtual Deadline First*) reemplazó a CFS en el kernel 6.6 (The Linux Kernel documentation, s. f.-c; Larabel, 2023; Stoica y Abdel-Wahab, 1995). Conserva el reparto proporcional por pesos, pero lo formaliza con dos conceptos:

- **Lag**: la diferencia entre el servicio que la tarea debería haber recibido en un sistema ideal, perfectamente equitativo, y el que recibió de verdad. Una tarea es *elegible* cuando su lag no es negativo, es decir, cuando no recibió más de lo que le corresponde.
- **Deadline virtual**: el instante virtual en el que la tarea terminaría su porción de tiempo (*slice*). Es el inicio elegible más la porción dividida por el peso.

Entre las tareas elegibles, EEVDF elige la de deadline virtual más temprano. La latencia deja de depender de heurísticas: queda determinada por la porción pedida. En el equipo de medición la porción base es `base_slice_ns` = 2,8 ms, y no existen los parámetros de CFS (sección 7.2).

En los dos casos el reparto es **proporcional y equitativo**: ninguna tarea *fair* lista se queda sin CPU indefinidamente, y `nice` cambia cuánta CPU recibe cada una, no si la recibe.

### 4.1.3. Las políticas de tiempo real: SCHED_FIFO y SCHED_RR

SCHED_FIFO y SCHED_RR son las políticas de tiempo real de POSIX (Kerrisk, s. f.-e). Usan **prioridades estáticas** de 1 a 99, independientes de `nice`, y se aplican con `chrt`:

- **SCHED_FIFO**: la tarea de mayor prioridad corre hasta que se bloquea, cede la CPU o la desplaza otra de prioridad mayor. No tiene porción de tiempo.
- **SCHED_RR**: es igual que FIFO, pero las tareas **de la misma prioridad** se turnan cada `sched_rr_timeslice_ms` (100 ms por defecto). Contra tareas de otra prioridad o de la clase *fair*, se comporta igual que FIFO.

Ninguna de las dos busca equidad: optimizan la **previsibilidad** de las tareas más prioritarias, a costa de las demás. Una tarea de tiempo real que nunca se bloquea, como un bucle de cálculo, monopoliza su CPU frente a toda la clase *fair*: servicios del sistema, `sshd` y la mayoría de los hilos del kernel.

### 4.1.4. Restricciones técnicas y riesgo para la estabilidad

Estas son las razones de la recomendación del docente de dejar SCHED_FIFO y SCHED_RR «como extensión opcional, por sus restricciones técnicas y posibles efectos sobre la estabilidad»:

1. **Inanición de la clase fair.** Como describe la sección 4.1.3, una tarea de tiempo real en bucle deja sin CPU a las tareas *fair* de esa CPU. El kernel lo mitiga con dos mecanismos. Su configuración en el equipo de medición se leyó al correr la prueba exploratoria:
   - El *throttling* de tiempo real: `sched_rt_runtime_us` = 950 000 sobre `sched_rt_period_us` = 1 000 000. La clase de tiempo real puede usar como mucho el 95 % de cada segundo (The Linux Kernel documentation, s. f.-d).
   - El *fair server*, un servidor de deadline que reserva a la clase *fair* 50 ms de cada 1000 ms por CPU (`/sys/kernel/debug/sched/fair_server/cpuN/runtime` y `period`) (Corbet, 2023b, 2024).

   Estos mecanismos evitan que el sistema se cuelgue, pero dejan a las tareas *fair* con alrededor de un 5 % de la CPU afectada: es inanición acotada, no reparto equitativo.
2. **Inversión de prioridad.** Si una tarea de baja prioridad tiene un recurso que espera otra de prioridad alta, una tercera de prioridad media puede retrasar indefinidamente a la de prioridad alta. El kernel lo resuelve con herencia de prioridad solo en algunos mecanismos de sincronización (los *rt_mutex*) (The Linux Kernel documentation, s. f.-e).
3. **Privilegios.** Para pasar una tarea a tiempo real hace falta `CAP_SYS_NICE` o un `RLIMIT_RTPRIO` mayor que cero. Un contenedor Docker no tiene esa capacidad por defecto: requiere `--cap-add SYS_NICE` o `--ulimit rtprio`, y para limitar su tiempo real, `--cpu-rt-runtime`. En este trabajo la política se aplicó desde el host con `sudo chrt`, sin dar más privilegios al contenedor.

### 4.1.5. Incompatibilidad con `cpu.max` de cgroups v2

El control de CPU de los experimentos 2 y 4 usa `cpu.max`, el *bandwidth control* de la clase *fair*: el kernel descuenta de la cuota del cgroup el tiempo de sus tareas *fair* y las *throttlea* cuando se agota (sección 4.2). Las tareas de tiempo real no pertenecen a esa clase y **no las limita `cpu.max`** (The Linux Kernel documentation, s. f.-b).

Para limitar tiempo real por grupo existe otro mecanismo, *RT group scheduling* (`cpu.rt_runtime_us`), pero es parte de cgroups v1. La documentación de cgroups v2 indica que todavía no soporta el control de procesos de tiempo real. Si el kernel se compila con `CONFIG_RT_GROUP_SCHED`, el controlador cpu solo se puede activar cuando todos los procesos de tiempo real están en el cgroup raíz (The Linux Kernel documentation, s. f.-b). En el equipo de medición, `CONFIG_RT_GROUP_SCHED` no está activado: los procesos de tiempo real pueden estar dentro del cgroup del contenedor, pero su cuota no los limita.

Por eso SCHED_FIFO y SCHED_RR no se pueden combinar con la herramienta central de este trabajo. Una tarea de tiempo real dentro de un contenedor con `--cpus 2` se saltea la cuota, y uno de sus competidores de tiempo real no respeta el reparto que `nice` le asigna a la clase *fair*.

### 4.1.6. Comparación y elección

**Tabla 4.1. Comparación de los algoritmos y políticas de planificación de Linux.**

| Aspecto | CFS (≤ 6.5) | EEVDF (≥ 6.6) | SCHED_FIFO | SCHED_RR |
|---|---|---|---|---|
| Clase | *fair* | *fair* | tiempo real | tiempo real |
| Criterio de elección | menor *vruntime* | deadline virtual más temprano entre las elegibles (lag ≥ 0) | mayor prioridad estática; FIFO dentro de cada prioridad | igual que FIFO, con turnos entre tareas de igual prioridad |
| Equidad | proporcional al peso (`nice`) | proporcional al peso, formalizada por el lag | no | solo entre tareas de igual prioridad |
| Porción de tiempo | dinámica, por heurísticas | `base_slice_ns` (2,8 ms en el equipo) | ninguna | `sched_rr_timeslice_ms` (100 ms) |
| Efecto de `nice` | cambia el peso | cambia el peso | ninguno | ninguno |
| Limitada por `cpu.max` | sí | sí | no | no |
| Privilegios | ninguno | ninguno | `CAP_SYS_NICE` o `RLIMIT_RTPRIO` | `CAP_SYS_NICE` o `RLIMIT_RTPRIO` |
| Riesgo para el sistema | bajo | bajo | inanición de la clase *fair*, acotada por el throttling | igual que FIFO |
| Disponible en el kernel 7.0 | no (reemplazado) | sí, por defecto | sí | sí |

Fuente: elaboración propia a partir de Kerrisk (s. f.-e), The Linux Kernel documentation (s. f.-b, s. f.-c) y Larabel (2023) y de la configuración del equipo (sección 5.2).

De la tabla salen tres argumentos para la elección de EEVDF:

1. **CFS ya no existe en el kernel medido.** Medir CFS exigiría otro kernel (6.5 o anterior), y eso cambiaría a la vez el scheduler, los drivers y el resto del sistema: la comparación quedaría confundida. Por eso CFS se trata solo en la teoría.
2. **FIFO y RR responden a otro problema.** Están pensados para tareas con plazos estrictos y acotadas en duración, no para repartir la CPU entre cargas que compiten, como la inferencia de un LLM y otros servicios en un mismo servidor. Tampoco permiten graduar la prioridad con `nice` ni limitar con `cpu.max`, que son las variables que estudian los experimentos 2 a 4.
3. **EEVDF es lo que usa la inferencia en la práctica.** Ollama corre por defecto con SCHED_OTHER, y un despliegue en contenedores se limita con cgroups v2. Las conclusiones del trabajo son útiles justamente para esa configuración.

No se afirma que SCHED_FIFO o SCHED_RR sean «lentos» o «peores»: para lo que fueron diseñados son la opción correcta. Lo que se argumenta es que no encajan con la pregunta de investigación ni con las herramientas de control de este trabajo.

### 4.1.7. Evidencia exploratoria

Para ilustrar las secciones 4.1.3 a 4.1.5 se corrió una prueba exploratoria (Exp 5) con el mismo protocolo, modelo y prompts que los experimentos 1 a 4 (capítulo 5), pero con N = 5 por prompt. Por ser exploratoria se informa solo estadística descriptiva, sin tests de hipótesis ni P95. Se probaron dos situaciones:

- **Competidor de tiempo real.** Un worker de `stress-ng` con SCHED_FIFO o SCHED_RR (prioridad 1), en el mismo `cpuset` de 12 CPUs que Ollama. Ollama sigue en SCHED_OTHER. Referencia: `exp3_comp1`, con el mismo competidor en SCHED_OTHER (N = 30).
- **Ollama de tiempo real con cuota.** Todos los hilos de llama-server pasan a SCHED_RR (prioridad 1, `chrt -a`) dentro del contenedor con `--cpus 2`. Referencia: la misma cuota en SCHED_OTHER, medida en la misma sesión (`exp5_cpus2`).

Las políticas se aplicaron desde el host y se verificaron hilo por hilo en `/proc`: el worker y los 39 hilos de llama-server, al principio y al final de la serie. Durante la prueba, `sched_rt_runtime_us` valía 950 000 de 1 000 000 y el *fair server* reservaba 50 ms de cada 1000 ms. El servidor siguió respondiendo por SSH en todo momento. La Tabla 4.2 resume los resultados.

**Tabla 4.2. Prueba exploratoria de políticas de tiempo real (medias, N = 5 por prompt; pares corto / largo).**

| Condición | Competidor | Ollama | Cuota | TTFT (s) | tokens/s | CPUs usadas | Throttles por corrida |
|---|---|---|---|---|---|---|---|
| `exp3_comp1` (ref., N = 30) | SCHED_OTHER | SCHED_OTHER | sin límite | 0,849 / 2,790 | 2,54 / 2,45 | 12,00 | 0 |
| `exp5_comp1_fifo` | SCHED_FIFO | SCHED_OTHER | sin límite | 2,106 / 3,102 | 0,48 / 0,48 | 12,00 | 0 |
| `exp5_comp1_rr` | SCHED_RR | SCHED_OTHER | sin límite | 2,112 / 3,294 | 0,61 / 0,56 | 12,00 | 0 |
| `exp5_cpus2` (ref.) | — | SCHED_OTHER | 2 CPUs | 0,577 / 6,800 | 3,76 / 3,53 | 2,00 | 346 / 430 |
| `exp5_cpus2_rr` | — | SCHED_RR | 2 CPUs | 0,080 / 0,955 | 27,69 / 26,60 | 12,01 | 0 |

Fuente: elaboración propia a partir de `experiments/analysis_rt/summary.md` (datos en `experiments/results_rt/`). «Competidor» y «Ollama» indican la política de planificación de cada uno. En las filas con competidor, `CPUs usadas` incluye al competidor.

![Figura 4.1. Prueba exploratoria de políticas de tiempo real. A: velocidad de Ollama según la política del competidor. B: velocidad al cambiar la política de Ollama con una cuota de 2 CPUs. C: consumo de CPU y frenadas en esas mismas condiciones; la línea roja indica la cuota. Fuente: elaboración propia a partir de experiments/results_rt/.](figuras/resultados/exp5_tiempo_real.png)

Los datos ilustran los dos argumentos de la sección 4.1.6:

1. **Sin equidad.** Con un solo competidor de tiempo real, Ollama genera entre 0,48 y 0,61 tokens/s, alrededor de una quinta parte de lo que logra frente al mismo competidor en SCHED_OTHER (2,45 a 2,54). Con EEVDF el competidor comparte su CPU con el hilo de Ollama que le toca; con FIFO o RR la ocupa casi entera, y ese hilo queda limitado a lo que deja el *fair server*. La explicación del colapso es compatible con la sincronización por paso de los 12 hilos de inferencia que se discute en el capítulo 8, pero esta prueba no lo demuestra porque no se capturaron métricas del scheduler. FIFO y RR dan valores casi iguales, como predice la teoría: con un único proceso de tiempo real, los turnos de RR entre tareas de igual prioridad no aparecen. La mayor variación de RR (CV de 30,6 % en el prompt corto) no se interpreta con N = 5.
2. **Fuera de `cpu.max`.** Con los hilos de llama-server en SCHED_RR, el contenedor limitado a 2 CPUs usa 12,01 CPUs, el 601 % (prompt corto) y el 600 % (prompt largo) de su cuota, y no registra ningún *throttle*. Ollama genera 26,6 a 27,7 tokens/s, prácticamente lo mismo que sin límite en el experimento 2 (27,88 en el prompt corto, capítulo 8). La misma cuota con SCHED_OTHER mantiene el consumo en 2,00 CPUs y throttlea entre 346 y 430 veces por corrida. La cuota existe, pero las tareas de tiempo real no la consumen.

Estos resultados no indican que una política sea «mejor»: el segundo caso muestra que una carga de tiempo real puede rendir más justamente porque se saltea los controles del sistema. Lo que confirman, para el equipo y la versión de kernel medidos, es que SCHED_FIFO y SCHED_RR rompen tanto el reparto proporcional como el límite de `cpu.max` que este trabajo estudia. Por eso quedan fuera del diseño principal, como recomendó el docente, y en el trabajo futuro (sección 9.7).

## 4.2. cgroups v2 y control de ancho de banda de CPU

Los *control groups* (cgroups) son el mecanismo del kernel para agrupar procesos en una jerarquía y aplicarles límites y contabilidad de recursos. La versión 2 expone una única jerarquía unificada, montada en `/sys/fs/cgroup`, donde cada directorio es un cgroup y cada archivo es una interfaz de un controlador (The Linux Kernel documentation, s. f.-b; Kerrisk, s. f.-b). Para este trabajo importan tres interfaces: `cpu.max`, `cpu.stat` y el controlador `cpuset`.

**`cpu.max`** implementa el *bandwidth control* de la clase *fair*. Contiene dos valores, una cuota y un período, ambos en microsegundos (`$CUOTA $PERÍODO`). En cada período el grupo puede consumir, sumando el tiempo de todos sus hilos en todas las CPUs, hasta `CUOTA` µs de CPU. El valor por defecto es `max 100000`, sin límite (The Linux Kernel documentation, s. f.-b). Una cuota de `200000` con período `100000` equivale entonces a 2 CPUs de tiempo por cada 100 ms, y es lo que produce la opción `--cpus 2` de Docker (sección 4.3).

El límite es de **tiempo total**, no de cantidad de CPUs. Un grupo con cuota de 2 CPUs y 12 hilos listos corre los 12 hilos a la vez y agota la cuota en un sexto del período (200 ms de CPU repartidos en 12 CPUs equivalen a unos 16,7 ms de reloj); durante el resto del período sus hilos no pueden ejecutarse. Esa suspensión forzada es el *throttling*. El kernel la registra en **`cpu.stat`**, junto con el consumo del grupo (`usage_usec`):

- `nr_periods`: cantidad de períodos transcurridos con el grupo activo.
- `nr_throttled`: cantidad de períodos en los que el grupo agotó su cuota y fue detenido.
- `throttled_usec`: tiempo total, en microsegundos, que los hilos del grupo estuvieron detenidos por esta causa (The Linux Kernel documentation, s. f.-b).

Estos contadores son acumulativos; el trabajo los lee antes y después de cada pedido para obtener los *throttles* por corrida (capítulo 5). La consecuencia para la latencia es directa: el tiempo que un hilo pasa detenido hasta el siguiente período se suma al tiempo de respuesta, aunque el sistema tenga CPUs libres.

El throttling puede aparecer incluso cuando el grupo no usa toda su cuota. Ugedal y Kumar (2022) mostraron que la contabilidad del tiempo de ejecución del *bandwidth control* puede limitar procesos innecesariamente, lo que degrada el rendimiento de las aplicaciones. Además de analizar la causa, propusieron mecanismos que reducen el throttling y su sobrecosto. Es una de las razones para leer `nr_throttled` y `throttled_usec` en lugar de suponer que una cuota se comporta como una CPU más lenta.

**`cpuset`** es un controlador distinto: restringe **en qué CPUs** pueden correr las tareas del grupo (`cpuset.cpus`), no cuánto tiempo pueden usar (The Linux Kernel documentation, s. f.-b). Los dos mecanismos son independientes y se combinan: `cpuset` fija el conjunto de CPUs disponibles y `cpu.max` el tiempo total que el grupo puede consumir en ellas. En los experimentos, el contenedor y los competidores comparten el mismo `cpuset` de 12 CPUs y la restricción de CPU se aplica con `cpu.max` (capítulo 5).

Por último, `cpu.max` solo alcanza a la clase *fair*, como se vio en la sección 4.1.5. El reparto *relativo* entre cgroups hermanos se controla con otra interfaz, `cpu.weight`, que no se usa en este trabajo.

## 4.3. Contenedores: namespaces, cgroups y Docker

Un contenedor de Linux no es una máquina virtual: es un conjunto de procesos del propio kernel anfitrión, aislados mediante dos mecanismos. Los ***namespaces*** limitan lo que un proceso *ve*: sus identificadores de proceso, las interfaces de red, los puntos de montaje, el nombre de host, los usuarios y otros recursos (Kerrisk, s. f.-d). Los ***cgroups*** limitan lo que un proceso *consume* (sección 4.2). Docker combina ambos, y agrega un sistema de archivos propio, para presentar cada contenedor como un entorno separado (Docker, s. f.-b).

La consecuencia para este trabajo es que **el contenedor usa el mismo kernel y el mismo scheduler que el host**. Un proceso dentro de un contenedor es una tarea más de la clase *fair*, con su `nice`, su peso y su porción de EEVDF. Lo que cambia es el cgroup al que pertenece y, por lo tanto, los límites que se le aplican. Esto permite comparar el mismo servicio con y sin contenedor (O1) y atribuir las diferencias a los límites, no a otro planificador.

Docker traduce sus opciones de recursos a archivos de cgroups v2 (Docker, s. f.-d):

- `--cpus <n>` fija la cuota de `cpu.max` en `n` veces el período. Con el período por defecto de 100 ms, `--cpus 2` escribe `200000 100000`.
- `--cpuset-cpus <lista>` fija `cpuset.cpus`, es decir, las CPUs donde puede correr el contenedor.

La documentación de Docker advierte que, para limitar tiempo real, hacen falta opciones específicas y privilegios adicionales (sección 4.1.4).

**Overhead frente a ejecución nativa.** Giallorenzo et al. (2021) comparan contenedores y máquinas virtuales con ejecución directa sobre el hardware (*bare-metal*) para cuantificar el costo de la virtualización. Kuity y Peddoju (2023) estudian métricas de rendimiento de contenedores en entornos de cómputo de alto rendimiento. A diferencia de una máquina virtual, un contenedor no ejecuta un kernel invitado, por lo que cabe esperar un costo menor. Este trabajo no da por supuesto ese resultado: lo mide para su propia carga, con el objetivo O1 (sección 8.2).

## 4.4. Inferencia de LLM en CPU

**Motor.** `llama.cpp` es un motor de inferencia de modelos de lenguaje escrito en C/C++ que puede ejecutarse solo con CPU y usa modelos cuantizados en formato GGUF (ggml-org, s. f.; Malakhov, 2025). Ollama es un servidor que gestiona modelos y expone una API HTTP sobre ese motor (Ollama, s. f.-b). Es el sistema estudiado en este trabajo: un proceso servidor que lanza hilos de inferencia y que, en la configuración medida, corre con una política SCHED_OTHER.

**Prefill y decode.** La generación de una respuesta tiene dos fases con comportamientos distintos (Zhong et al., 2024):

- **Prefill**: el modelo procesa el prompt completo y produce el primer token. Cuanto más largo el prompt, más cálculo se necesita antes de responder.
- **Decode**: el modelo genera los tokens restantes de a uno; cada token depende del anterior, y el paso no puede saltearse ni paralelizarse a lo largo de la secuencia.

**Métricas.** Cada fase tiene su métrica de latencia habitual. El ***TTFT*** (*time to first token*) es el tiempo desde que se envía el pedido hasta que llega el primer token, y refleja la fase de prefill. El **tiempo por token de salida** (TPOT) refleja la fase de decode (Zhong et al., 2024; Wang et al., 2024). Su inversa es la tasa de generación, expresada en **tokens por segundo**: la cantidad de tokens generados dividida por el tiempo de generación. Ollama informa en cada respuesta la cantidad de tokens generados y las duraciones de carga, de evaluación del prompt y de generación (Ollama, s. f.-d); con ellos se calcula tokens/s (capítulo 5). Las definiciones concretas usadas en el trabajo se fijan en la sección 5.7.

**Hilos.** En CPU, el cálculo de cada paso se reparte entre varios hilos que trabajan en paralelo sobre las mismas capas del modelo y deben esperarse antes de seguir con el siguiente paso. Cuando un paso requiere sincronización, el retraso de un hilo podría demorar el avance de los demás. Una cuota de CPU o un competidor podría generar ese retraso; en este trabajo no se midió la espera en las barreras. Jeffery et al. (2024) muestran que la sobreasignación de hilos de un proceso respecto de las CPUs disponibles, ya sea por una cuota o por aplicaciones vecinas, eleva la latencia de cola. Esta idea sostiene la hipótesis de sincronización que se discute en el capítulo 8: no se la afirma como resultado de la literatura, sino como explicación compatible con los datos.

**Cuantización.** Para reducir memoria y cálculo, los pesos se almacenan con menos bits (por ejemplo, 4 bits). El modelo usado, `llama3.2:3b` (Grattafiori et al., 2024), se distribuye en Ollama con una cuantización de 4 bits y un tamaño de unos 2 GB (Ollama, s. f.-c), lo que permite correrlo en CPU.

## 4.5. Trabajos relacionados

La literatura reciente aborda por separado los tres temas que este trabajo junta: los límites de CPU y su throttling, el rendimiento y la interferencia de los contenedores, y la inferencia de LLM en CPU. La Tabla 4.3 resume cada trabajo, qué aporta al planteamiento y qué no cubre.

**Tabla 4.3. Trabajos relacionados: aporte y limitación.**

| Trabajo | Qué aporta | Qué limita para este proyecto |
|---|---|---|
| Ugedal y Kumar (2022) | Explican por qué el *bandwidth control* de CFS puede *throttlear* sin necesidad y proponen cómo reducirlo y abaratarlo. Fundamenta el análisis de `cpu.max` y de `cpu.stat`. | Estudia el mecanismo del kernel, con CFS, y no una carga de inferencia de LLM. No evalúa EEVDF ni la interacción con competidores. |
| Shetty et al. (2025) | Aportan evidencia empírica de que los límites de CPU pueden empeorar el rendimiento de aplicaciones sensibles a la latencia, y proponen replantear su uso. Sostiene la hipótesis H1. | Se refiere a aplicaciones en la nube en general; no mide TTFT ni tokens/s de LLM ni el efecto de la cantidad de hilos del motor. |
| Jeffery et al. (2024) | Relacionan la latencia de cola con la sobreasignación de hilos bajo una cuota de CPU o con vecinos, y evalúan un *threadpool* que la evita. Es una explicación posible del colapso con cuota. | Su carga son servicios con *pools* de hilos, no un motor de inferencia con sincronización por paso; se usa solo como respaldo conceptual. |
| Giallorenzo et al. (2021) | Comparan el costo de contenedores y máquinas virtuales frente a *bare-metal*. Es la base del objetivo O1. | No usa LLM ni límites de cgroups; su carga y su hardware son distintos de los del trabajo, así que el resultado no se transfiere sin medirlo. |
| Volpert et al. (2024) | Analizan empíricamente la capacidad de aislamiento de rendimiento de los *runtimes* OCI comunes. Es referencia para O1 y H2. | Compara *runtimes* de contenedores, no políticas del scheduler ni `nice`. No considera inferencia de LLM. |
| HoseinyFarahabady y Zomaya (2024) | Tratan el control de la interferencia de rendimiento entre contenedores en entornos multiinquilino. Respalda la hipótesis H2 (vecino ruidoso). | Propone un control en el nivel de la plataforma; no mide a un único servicio de LLM frente a un competidor `stress-ng` ni el efecto de `nice`. |
| Tyndall et al. (2025) | Evalúan la viabilidad de un LLM seguro y sin conexión sobre CPU, caso de uso del planteamiento. | Evalúa la factibilidad de la inferencia en CPU, no la interferencia entre procesos ni el control del scheduler. |

Fuente: elaboración propia a partir de los trabajos citados.

Ninguno de los trabajos analizados mide, sobre un mismo servidor, cómo se comporta la inferencia de un LLM en CPU bajo cuotas de `cpu.max`, competidores y valores de `nice` con EEVDF. Los estudios sobre throttling (Ugedal y Kumar, 2022; Shetty et al., 2025) y sobre interferencia (HoseinyFarahabady y Zomaya, 2024; Volpert et al., 2024) dan los mecanismos y las hipótesis, pero con cargas distintas de la inferencia; el de Tyndall et al. (2025) muestra que la inferencia local en CPU es viable, pero no estudia la interferencia entre procesos. Este trabajo cubre esa intersección y deja a los antecedentes el papel de explicar y contrastar sus resultados, no de anticiparlos.
