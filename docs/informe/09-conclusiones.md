# 9. Conclusiones y trabajo futuro

Este capítulo responde la pregunta de investigación, resume lo logrado en cada objetivo y explica a qué se debe el comportamiento observado, delimita lo que los datos permiten afirmar y propone mejoras. Las cifras provienen del capítulo 8, donde están las tablas completas; aquí no se repiten.

## 9.1. Respuesta a la pregunta de investigación

La pregunta fue: «¿En qué medida los límites de CPU impuestos mediante cgroups v2 y la competencia entre procesos afectan el tiempo hasta el primer token (TTFT), el throughput y la variabilidad de la inferencia de Ollama, y bajo qué condiciones el ajuste de prioridades del scheduler de Linux modifica ese comportamiento?»

En el equipo medido (Ryzen 9 9900X, kernel 7.0 con EEVDF, `llama3.2:3b` en CPU), **ambos factores degradan la inferencia de forma muy marcada y la prioridad solo la corrige cuando no hay una cuota estricta de por medio**. Una cuota de `cpu.max` reduce el rendimiento casi en proporción a la CPU retirada y multiplica el TTFT con una variabilidad baja; un único competidor de igual prioridad, aunque no haya cuota ni throttling, hunde el rendimiento en torno al 90 % y vuelve irregular la latencia. Bajar la prioridad de los competidores con `nice` recupera casi todo el rendimiento, pero no ayuda si lo que limita a Ollama es una cuota del cgroup que comparte con ellos.

## 9.2. Veredicto sobre las hipótesis

- **H1 (cuota y throttling): se confirma.** Con 8, 4, 2 y 1 CPUs los tokens/s caen −35,6 %, −69,3 %, −86,4 % y −93,1 % (prompt corto) y el TTFT del prompt largo pasa de 0,952 s a 15,125 s, con 86 a 853 *throttles* por corrida y un CV de tokens/s inferior a 1 %. La caída es algo peor que proporcional: el rendimiento por CPU usada baja de 2,23 a 1,77 tokens/s (secciones 8.3 y 8.6).
- **H2 (competencia): se confirma, con un efecto mayor al esperado.** Con 1, 2 y 3 competidores los tokens/s caen −89,7 %, −96,9 % y −97,8 %, el CV de tokens/s pasa de 0,1 % a 10,1 % (prompt largo) y el del TTFT corto de 2,7 % a 62,9 % (sección 8.4.1). La variabilidad no crece de forma monótona con el número de competidores, y las condiciones con 2 y 3 tienen N = 10.
- **H3 (`nice` y cuota estricta): se confirma en sus dos partes.** Con `nice` 19 en los competidores, Ollama pasa de 0,47 a 20,59 tokens/s (prompt largo), el 87 % del rendimiento sin competencia (23,74). Con una cuota de 2 CPUs, en cambio, rinde 2,83 tokens/s, menos que con esa cuota sin competidores (3,61), con 703 *throttles* por corrida (sección 8.4.2).

## 9.3. Logro de los objetivos específicos

- **O1.** El host y Docker son equivalentes sin límites: las diferencias de medias fueron de −0,1 % y +0,7 % en el TTFT y de +0,0 % y −0,1 % en tokens/s, sin diferencia según Welch en ninguna de las cuatro métricas; Mann-Whitney detecta ordenamientos en tokens/s y TTFT largo, de centésimas y sin consecuencia práctica. Esto justifica usar el contenedor como vehículo de las cuotas (sección 8.2), en línea con los costos bajos de los contenedores frente a *bare-metal* (Giallorenzo et al., 2021).
- **O2.** Se midieron cuatro cuotas (8, 4, 2 y 1 CPUs) frente a una referencia sin límite, con TTFT, tokens/s, P95 y throttling por corrida; el cgroup consumió exactamente la cuota asignada (sección 8.3).
- **O3.** Se cuantificó el efecto de 1 a 3 competidores y de 12 competidores con `nice` 0, 10 y 19, con la verificación de que comparten cgroup, CPUs y `nice` (secciones 5.6 y 8.4).
- **O4.** El throttling de `cpu.stat` y las métricas de `schedstat`, `perf sched` y `pidstat` permitieron explicar el mecanismo de cada resultado (sección 8.5), aunque en ventanas de captura separadas de la medición.

## 9.4. Por qué ocurre

Tres mecanismos explican los datos.

1. **Cuota por período.** `cpu.max` concede un presupuesto de tiempo de CPU por período de 100 ms para todo el cgroup y detiene a todas sus tareas cuando se agota hasta el período siguiente (The Linux Kernel documentation, s. f.-b). Con cuotas de 4, 2 y 1 CPUs se registraron 10 *throttles* por segundo y demoras máximas en cola de 71,5 a 94,6 ms, casi un período. Que un límite de CPU degrade a una aplicación sensible a la latencia concuerda con lo señalado por Shetty et al. (2025) y con el costo de la contabilidad del *bandwidth control* descrito por Ugedal y Kumar (2022).
2. **Pesos de EEVDF.** Con `nice` 0, 10 y 19 los pesos son 1024, 110 y 15 (Kerrisk, s. f.-e; Linux Kernel Developers, 2026), por lo que, frente a 12 competidores, Ollama obtendría teóricamente el 50 %, 90 % y 98,6 % de la CPU; las capturas lo confirman (6,00, 10,78 y 11,82 de 12 CPUs). Ese reparto es proporcional a los pesos entre tareas del mismo grupo de planificación, pero no lo es entre un cgroup y su límite: con `nice` 19 y cuota de 2 CPUs los competidores igualmente se llevan 0,67 CPUs de las 2.
3. **Sincronización de hilos.** El rendimiento es mucho menor que la fracción de CPU recibida (0,47 tokens/s con la mitad de la CPU en `nice` 0; 2,45 tokens/s con un competidor que apenas hace esperar a los hilos el 7,7 % del tiempo). Es coherente con que los 12 hilos de inferencia se sincronicen en cada paso y que uno solo demorado frene a los demás, tal como describen Jeffery et al. (2024) para la sobreasignación de hilos bajo cuota o vecinos. **Esto es una hipótesis**: no se aisló variando el número de hilos.

## 9.5. Limitaciones

- **Una máquina, un modelo, solo CPU.** Los valores absolutos (un Ryzen 9 9900X con SMT, `llama3.2:3b` en Q4 y 12 hilos de Ollama) no se extrapolan a otras CPU, modelos o motores. La GPU quedó fuera del alcance por decisión de diseño.
- **Tamaño de muestra.** Tres condiciones (`exp3_comp2`, `exp3_comp3` y `exp4_nice0`) tienen N = 10, por lo que su P95 es orientativo. La prueba exploratoria de políticas de tiempo real (Exp 5, sección 4.1.7) tiene N = 5 y solo estadística descriptiva.
- **Evidencia del mecanismo.** Las capturas del scheduler son ventanas de 20 s independientes de las corridas medidas y con pocas generaciones completadas; los tres episodios de bloqueo de `exp4_nice19_cpus2` son datos válidos pero su causa no está demostrada.
- **Diseño de la competencia.** Los competidores corren dentro del cgroup de Ollama, escenario menos habitual que el de contenedores vecinos; la medición no es extrapolable a una política de aislamiento multiinquilino.
- **Seguridad del laboratorio.** El banco es un equipo dedicado de una sola persona, con scripts que usan `sudo -n`, `dockerd` como root, imagen `ollama/ollama:latest` sin fijar y API sin autenticación; no se verificaron *seccomp*, AppArmor ni el remapeo de usuarios. La comprobación posterior del 22/11/2026 confirmó que UFW estaba inactivo y que SSH permitía autenticación por contraseña (sección 6.6). No afecta la validez de las mediciones de CPU, pero impide presentar el banco como una configuración endurecida.

## 9.6. Qué habría cambiado con otro enfoque

Poner a los competidores en un cgroup hermano con `cpu.weight` habría medido el aislamiento entre contenedores vecinos, a costa de que `nice` perdiera su efecto directo sobre Ollama (conjetura sin medir). Fijar el número de hilos de Ollama a la cuota o a las CPUs disponibles habría evitado la sobresuscripción del piloto y aislado el efecto de la sincronización; hacerlo en todas las condiciones habría impedido atribuirle a la cuota lo que podría ser un desajuste de hilos. Y N = 30 en las tres condiciones excepcionales habría dado P95 interpretables.

## 9.7. Trabajo futuro

Las mejoras siguientes se ordenan por la evidencia que las respalda.

1. **Igualar el número de hilos a la cuota.** Repetir la matriz de cuotas y de competidores con 4, 8 y 12 hilos de inferencia. Se justifica por la caída por CPU de 2,23 a 1,77 tokens/s y por el colapso con un solo competidor (secciones 8.3 y 8.4.1): si la sincronización por paso es la causa, el colapso debería disminuir con menos hilos (Jeffery et al., 2024). Es la prueba directa de la hipótesis de la sección 9.4.
2. **Reemplazar la cuota por pesos.** Medir `cpu.weight` entre cgroups hermanos en lugar de `cpu.max`, que no se usó en este trabajo (The Linux Kernel documentation, s. f.-b). Los datos muestran que con cuota estricta la prioridad solo reparte lo que queda dentro del límite (sección 8.4.2), y Shetty et al. (2025) sostienen que los límites de CPU perjudican a las aplicaciones sensibles a la latencia; un peso garantiza una proporción sin detener al grupo.
3. **Probar un período más largo o ráfagas.** Con `cpu.max` el corte es de 10 *throttles* por segundo (sección 8.5) y el TTFT corto de 8 y 4 CPUs tiene un CV de 11,3 % y 12,5 % (sección 8.3), probablemente por caer o no dentro de un período. Medir períodos mayores o la interfaz `cpu.max.burst` de cgroups v2 (The Linux Kernel documentation, s. f.-b) evaluaría si menos cortes reducen la penalización, en línea con las propuestas para reducir el throttling innecesario (Ugedal y Kumar, 2022). Es una predicción sin evidencia propia todavía.
4. **Instrumentar los episodios de bloqueo.** Repetir `exp4_nice19_cpus2` con N mayor y registro continuo de `schedstat` por hilo y de `cpu.stat`, sin `perf`, para capturar un episodio cuando ocurre y comprobar o descartar la espera activa.
5. **Políticas de tiempo real y GPU.** En la prueba exploratoria, SCHED_FIFO y SCHED_RR escaparon al límite de `cpu.max` (sección 4.1.7) y justifican un estudio específico con N mayor y capturas del scheduler. La inferencia con GPU, fuera del alcance de este trabajo, requeriría otro diseño porque el cuello de botella dejaría de ser la CPU.
