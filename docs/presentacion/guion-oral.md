# Guion para el oral (15 diapositivas, 10 min)

Presentación: `TPFinal_SOR2_2026_2s_VelizLuis_presentacion.pptx`. Hablás en primera persona y con frases cortas. Entre corchetes va lo que conviene señalar en la pantalla.

Orden de la charla: la pregunta, por qué importa, con qué trabajamos y por qué, la teoría (carrera por la CPU, por qué EEVDF, cuotas), qué hice, los resultados (O1 a O4) y las conclusiones.

| # | Diapositiva | Tiempo |
|---|---|---|
| 1 | Portada | 20 s |
| 2 | La pregunta | 50 s |
| 3 | Por qué importa | 40 s |
| 4 | Con qué trabajamos y por qué | 35 s |
| 5 | Stack tecnológico | 30 s |
| 6 | La carrera por la CPU | 45 s |
| 7 | Por qué EEVDF | 35 s |
| 8 | El límite de CPU: cgroups v2 | 55 s |
| 9 | Qué hice | 35 s |
| 10 | O1: host y Docker, medias cercanas | 30 s |
| 11 | O2: la cuota se paga en velocidad | 45 s |
| 12 | O3: un solo rival hunde el rendimiento | 45 s |
| 13 | O3: nice ayuda, pero la cuota manda | 50 s |
| 14 | O4: qué registra el scheduler | 45 s |
| 15 | Conclusiones | 40 s |

Total: 10 min (600 s).

## 1. Portada (~20 s)
**Qué es:** abre la charla con el título y la autoría; la grilla de cuadrados anticipa los 12 hilos del modelo.

«Buenas. Mi trabajo se llama *Planificación de CPU en Linux: cuotas, competencia y prioridades en un LLM local*. Estudié cómo el sistema operativo reparte la CPU cuando un modelo de lenguaje comparte la máquina.»

[Señalá la grilla] «Estos 12 cuadrados son los 12 hilos del modelo. Uno está resaltado: el más lento.»

## 2. La pregunta (~50 s)
**Qué es:** plantea la pregunta de investigación, las dos métricas (TTFT y tokens/s) y las tres hipótesis.

«Hoy es común correr un LLM, un modelo de lenguaje, en la propia máquina con **Ollama**. Pero rara vez está sola: otras tareas compiten por la CPU.»

[Señalá la pregunta, debajo del título] «La pregunta es: ¿en qué medida los límites de CPU con cgroups v2 y la competencia entre procesos afectan la inferencia de Ollama, y cuándo cambia algo ajustar la prioridad del scheduler?»

[Señalá TTFT y tokens/s a la derecha] «Medí dos métricas:

- **TTFT**, *time to first token*: cuánto tarda en aparecer la primera palabra.
- **Tokens por segundo**: qué tan rápido sigue escribiendo. Un *token* es un pedazo de palabra.»

[Señalá las tres tarjetas de abajo] «Planteé tres hipótesis:

- **H1:** limitar la CPU aumenta la demora y baja la velocidad.
- **H2:** tener procesos compitiendo aumenta la demora y la vuelve más variable.
- **H3:** bajarles la prioridad a los competidores con `nice` reduce la interferencia, pero no compensa un límite estricto de CPU.»

## 3. Por qué importa (~40 s)
**Qué es:** justifica el problema con tres datos y marca el vacío que cubre el trabajo.

«¿Por qué medir esto? Por tres razones y un vacío.»

[Señalá la tarjeta celeste, 51,1 %] «Primero: correr LLM locales es común. En la encuesta de Stack Overflow 2025, el **51,1 %** de quienes respondieron marcó Ollama. Es un dato de quienes respondieron.»

[Señalá la tarjeta amarilla, «Sin tope»] «Segundo: **Docker no pone límites por defecto**. Hay que pedirlos.»

[Señalá la tarjeta roja, × 5] «Tercero: los límites de CPU pueden dañar la latencia. En otro trabajo limitaron **1 de 19 pods** y la latencia de cola se multiplicó **por cinco**. No es un LLM, pero es una alerta.»

[Señalá la franja violeta de abajo] «Y el vacío: no encontré mediciones del efecto conjunto de cuotas, competencia y `nice` sobre un LLM en CPU. Eso aporto.»

## 4. Con qué trabajamos y por qué (~35 s)
**Qué es:** presenta las cuatro elecciones de diseño, cada una con su razón corta.

«Cuatro elecciones; las alternativas están en la Tabla 5.4 del informe.»

[Señalá la tarjeta de Ollama] «**Ollama con llama3.2 de 3 mil millones de parámetros.** Es liviano: permite más repeticiones.»

[Señalá el chip] «**Solo CPU.** Lo que estudio es cómo el scheduler reparte la CPU.»

[Señalá la ballena] «**Docker.** Aplica las cuotas con cgroups y comparte el kernel con el host: no es una máquina virtual.»

[Señalá el logo de Ubuntu] «**Ubuntu Server 26.04, con kernel 7.0.** Trae EEVDF y cgroups v2 de forma nativa.»

## 5. Stack tecnológico (~30 s)
**Qué es:** muestra por capas todas las herramientas usadas, con logos y nombres cortos.

«Este es el stack completo, por capas.»

[Recorré las columnas de izquierda a derecha]
- «**Plataforma:** una PC dedicada con Ubuntu Server 26.04, kernel 7.0 y un Ryzen 9 de 12 núcleos.»
- «**Inferencia:** Ollama con llama3.2 de 3 mil millones de parámetros, solo CPU.»
- «**Control:** Docker, que escribe `cpu.max` de cgroups v2, y `nice`.»
- «**Carga y medición:** `stress-ng` genera los rivales; `perf sched` y `cpu.stat` muestran qué hace el kernel.»
- «**Análisis:** Python con pandas y SciPy.»
- «**IA:** **Claude Opus 5.5** como orquestador y **Gemini 4 Neon** como auditor, dentro del ecosistema **Gentle AI**. Las decisiones y mediciones son mías.»

## 6. La carrera por la CPU (~45 s)
**Qué es:** explica que hay más hilos que CPUs, que el scheduler decide quién corre y que `nice` es un peso, no un interruptor.

«Casi siempre hay más hilos listos que CPUs. Compiten.»

[Señalá los cuadrados grises y la CPU, arriba] «El **scheduler** es la parte del kernel que elige cuál corre. Hoy se llama **EEVDF**.»

[Señalá la franja A, B, C] «Una CPU, tres tareas: cada una recibe un turno de unos 2,8 ms.»

[Señalá el círculo naranja de la izquierda] «Con **`nice`** no se prende ni se apaga un proceso: se le da un **peso**. nice 0 pesa 1024; nice 10, 110; nice 19, 15, casi nada.»

[Señalá las barras de la derecha] «Ollama queda en nice 0 y tiene 12 competidores. Si ellos están en nice 0, a Ollama le toca la mitad de la CPU. Con nice 10, el 90 %. Con nice 19, el 98,6 %.»

## 7. Por qué EEVDF (~35 s)
**Qué es:** compara los tres candidatos de scheduler y justifica por qué se midió EEVDF.

«¿Por qué EEVDF y no otro scheduler? Hay tres candidatos.»

[Señalá la columna gris, CFS] «**CFS** fue reemplazado por EEVDF desde el kernel 6.6, así que en el 7.0 ya no existe. Medirlo exigiría otro kernel y confundiría la comparación.»

[Señalá la columna resaltada, EEVDF] «**EEVDF** es el que usa Ollama por defecto, con la política SCHED_OTHER. Es equitativo y compatible con `cpu.max`: justo lo que estudio.»

[Señalá la columna de la derecha] «**SCHED_FIFO y SCHED_RR** son de tiempo real: sin equidad, y rompen el reparto y `cpu.max`. Las probé solo como exploración.»

## 8. El límite de CPU: cgroups v2 (~55 s)
**Qué es:** explica cómo funciona el límite `cpu.max` y por qué frena a los 12 hilos a la vez.

«Los **cgroups** agrupan procesos y les ponen límites; Docker los usa por debajo. El límite de CPU es **`cpu.max`**, y no dice "usá 2 CPUs": da un **presupuesto de tiempo de CPU que se recarga cada 100 ms**.»

[Señalá los tres pasos, de izquierda a derecha]
«1. **Recarga:** con una cuota de 2 CPUs, cada 100 ms el grupo recibe 200 ms de CPU.
2. **Gasto:** el presupuesto lo comparten los 12 hilos de Ollama. Por cada milisegundo real gastan 12.
3. **Frenado:** a los 16,7 ms el presupuesto se acaba y el kernel **frena a todo el grupo** hasta la próxima recarga.»

[Señalá la barra verde y roja] «La barra está a escala: un período de 100 ms. Ollama corre 16,7 ms (verde) y pasa los otros 83 ms frenado, aunque haya CPUs libres.»

[Señalá la etiqueta «Throttling», debajo de la barra roja] «Ese frenado se llama ***throttling***.»

[Señalá la línea de abajo, con el ícono de tarjeta] «Es como una tarjeta prepaga que se recarga cada 100 ms y la gastan 12 personas a la vez: se la funden y esperan.»

## 9. Qué hice (~35 s)
**Qué es:** resume el banco de pruebas en tres pasos y cuatro números: 780 corridas, 15 condiciones, 4 experimentos y unas 10 horas de mediciones.

«Armé un banco de pruebas en una PC con Linux nativo.»

[Señalá los tres íconos, de izquierda a derecha] «Tres pasos:

1. **Ollama:** lo instalé en Linux y también en un contenedor Docker.
2. **Condiciones:** apliqué cuotas de CPU, competidores con `stress-ng` y distintos `nice`.
3. **Medición:** TTFT y tokens por segundo, con el mismo modelo, las mismas preguntas y el mismo script.»

[Señalá los cuatro números grandes] «En total, **780 corridas, 15 condiciones y 4 experimentos**, medidos en **10 horas y cuarto**. Cada condición se repitió 30 veces, o 10 en tres casos muy lentos.»

## 10. O1: host y Docker, medias cercanas (~30 s)
**Qué es:** resultado del objetivo 1; compara Ollama en el host contra Ollama en Docker, sin límites.

«El primer objetivo: comparar Ollama en Linux con Ollama en Docker, sin límites.»

[Señalá el número «< 1 %» y el gráfico] «Comparé medias de 30 corridas cada una: 26,84 contra 26,81 tokens por segundo. En este montaje las medias medidas son muy cercanas; no digo que el costo sea cero.»

«Un contenedor **no es una máquina virtual**: son procesos del mismo kernel. Por eso pude usar Docker para aplicar las cuotas. Otros costos, como red o disco, no los medí.»

## 11. O2: la cuota se paga en velocidad (~45 s)
**Qué es:** resultado del objetivo 2; muestra cómo cae la velocidad al bajar la cuota de CPU.

«El segundo objetivo: limitar la CPU con `cpu.max`.»

[Señalá el subtítulo y recorré las barras] «Ojo: la cuota es tiempo de CPU equivalente, no cuántas CPUs puede usar. Medias de 30 corridas: sin cuota, 26,8 tokens por segundo; con 8 CPUs equivalentes, 17,3; con 4, 8,3; con 2, 3,6; con 1, 1,8.»

[Señalá el «÷ 2» y el «−93 %»] «Con 4 CPUs o menos, cada vez que la cuota se reduce a la mitad, la velocidad cae aproximadamente a la mitad. Con 1 CPU equivalente cae un **93 %** y la espera media hasta la primera palabra se multiplica por 16: de casi 1 segundo a **15 segundos**.»

«El kernel registra *throttling* en todas las cuotas. **Confirma H1**.»

## 12. O3: un solo rival hunde el rendimiento (~45 s)
**Qué es:** resultado del objetivo 3 (competencia); un único proceso competidor ya reduce la velocidad un 90 %, y se muestra la hipótesis de sincronización.

«El tercer objetivo: la competencia. Agregué procesos que consumen CPU, con la misma prioridad que Ollama.»

[Señalá el «−90 %» y el gráfico] «Con un solo competidor la velocidad media cae un **90 %**: de 23,7 a 2,5 tokens por segundo. Con 2 y 3 competidores baja a 0,7 y 0,5, con 10 corridas en cada una.»

«Es mucho más de lo esperable: el competidor solo le saca una pequeña parte de la CPU.»

[Señalá el diagrama de barras: el hilo rojo largo y los hilos que esperan] «Una **hipótesis**, que no probé, es que los 12 hilos se sincronizan en cada paso: si uno comparte su CPU con el competidor, los otros 11 podrían esperarlo. Es una idea para probar variando los hilos, no una explicación establecida.»

«Además la variabilidad crece mucho. **Respalda H2**.»

## 13. O3: nice ayuda, pero la cuota manda (~50 s)
**Qué es:** completa el objetivo 3 con la prioridad; compara los distintos `nice` de 12 competidores y el caso con cuota.

«Después repetí con 12 competidores, cambiando su prioridad.»

[Recorré las barras] «Primero, sin cuota y con 12 rivales. Medias:

- nice 0: 0,47 tokens por segundo (esta condición tiene 10 corridas);
- nice 10: 9,5;
- nice 19: **20,6**; la barra gris aparte es la referencia sin rivales, 23,7.

O sea, **`nice` ayuda mucho**.»

[Señalá la tarjeta de abajo a la derecha] «Segundo, la comparación controlada de la cuota: con el mismo conjunto de CPUs y los mismos rivales en nice 19, agregar la cuota de 2 CPUs bajó la media de 20,59 a **2,83 tokens/s**. Por eso la cuota manda sobre `nice`. Ojo: en el experimento 2, con la misma cuota, medí 3,61, pero con 24 CPUs lógicas en vez de 12 y sin rivales; **no puedo atribuir esa diferencia solo a la competencia**.»

## 14. O4: qué registra el scheduler (~45 s)
**Qué es:** resultado del objetivo 4; dos comparaciones separadas de lo que ve el kernel (tiempo en cola y frenadas), con una captura de 20 s por condición, aparte de las corridas de rendimiento.

«El cuarto objetivo: mirar adentro del scheduler. Con `perf` medí qué porción del tiempo ejecutable, corriendo más esperando, los hilos de Ollama pasan **en la cola**. Una captura de 20 segundos por condición, aparte de las corridas de velocidad.»

[Señalá el gráfico de la izquierda] «Exp. 2, solo cuota y sin rivales: sin cuota, casi 0 %; con 4, 2 y 1 CPUs equivalentes, 67 %, 83 % y 92 %. El kernel registra **10 frenos por segundo**, uno por período de 100 ms, como en la teoría.»

[Señalá el gráfico de la derecha y la tarjeta] «Exp. 3, sin cuota y en el mismo cpuset: de cero a un rival, la espera pasa de 0,07 % a **7,65 %**. El rival usa en promedio 0,91 CPU. La velocidad, medida aparte, cae de 23,74 a 2,45 tokens por segundo.»

«La espera medida es baja y la velocidad cae mucho. Eso es compatible con la hipótesis de sincronización, que sigue sin probarse.»

## 15. Conclusiones (~40 s)
**Qué es:** cierra con tres ideas y una cifra cada una; termina con la apertura a preguntas.

[Señalá las tres tarjetas, de izquierda a derecha] «Tres ideas:

1. **Docker ≈ host en CPU** (< 1 % entre medias): en este montaje rinden casi igual; no digo que el costo sea cero.
2. **La cuota se cumple y manda**: la velocidad cae aproximadamente en proporción, y un poco más.
3. **La competencia pesa mucho más de lo esperado** (−90 % con un solo rival): `nice` ayuda, pero un límite estricto de CPU manda sobre la prioridad.»

«Limitaciones: una máquina, un modelo, una configuración de hilos. Futuro: variar los hilos para probar la hipótesis de sincronización.»

[Señalá las tres etiquetas de abajo] «Se cumplió O1. Los resultados respaldan H1, H2 y H3, pero no aíslan el efecto de competir bajo la cuota de 2 CPUs.»

[Señalá «¿Preguntas?»] «Gracias. ¿Preguntas?»

---

## Glosario rápido
| Término | Qué es |
|---|---|
| **LLM / Ollama** | Modelo de lenguaje; Ollama es el programa que lo corre localmente. Usé `llama3.2:3b`, solo con CPU. |
| **Token** | Pedazo de palabra que genera el modelo. |
| **TTFT** | Tiempo hasta la primera palabra. |
| **Scheduler / EEVDF** | Parte del kernel que reparte la CPU. EEVDF reemplazó a CFS en Linux 6.6. |
| **SCHED_OTHER / FIFO / RR** | OTHER es la política normal (equitativa) y la que usa Ollama. FIFO y RR son de tiempo real: sin equidad y fuera de `cpu.max`. |
| **nice** | Prioridad de un proceso (0 normal, 19 mínima). Cambia su peso en el reparto. |
| **cgroups v2** | Mecanismo para agrupar procesos y ponerles límites. Docker los usa. |
| **cpu.max** | Cuota: tiempo de CPU permitido por período de 100 ms. |
| **Throttling** | Frenado del grupo cuando agota su cuota. |
| **cpu.stat** | Archivo del kernel donde se cuentan los frenos (`nr_throttled`) y el tiempo frenado. |
| **stress-ng** | Programa que genera carga de CPU; lo usé como competidor. |
| **P95 / CV** | P95: el valor que no supera el 95 % de las corridas (el caso «casi peor»). CV: cuánto varían los resultados. |

## Preguntas probables

- **«¿Por qué EEVDF y no CFS?»** CFS fue reemplazado por EEVDF desde el kernel 6.6; en el kernel 7.0 que medí ya no existe. Medirlo exigiría otro kernel (6.5 o anterior), y eso cambiaría a la vez el scheduler, los drivers y el resto del sistema: la comparación quedaría confundida. Por eso CFS se trata solo en la teoría (sección 4.1.6). Además EEVDF es lo que usa Ollama por defecto.
- **«¿Por qué no SCHED_FIFO o SCHED_RR?»** Son políticas de tiempo real: no reparten la CPU de forma equitativa, no responden a `nice` y escapan al límite de `cpu.max`, que son las variables que estudio. Las probé en una prueba exploratoria corta (N = 5, sin tests): un competidor en FIFO o RR dejó a Ollama en 0,48 a 0,61 tokens/s, contra 2,45 a 2,54 con uno normal; y con Ollama en RR y cuota de 2 CPUs, el contenedor usó 12,01 CPUs sin ningún throttle (sección 4.1.7). No digo que sean peores; para lo que fueron diseñadas son la opción correcta. Quedan como trabajo futuro, como recomendó el docente.
- **«¿Cómo sabés que la sincronización es la causa?»** No lo sé con certeza; es una hipótesis coherente con los datos. Con un competidor, los hilos esperan en cola solo el 7,65 % de su tiempo ejecutable (una captura de 20 s) y sin throttling, y aun así la velocidad media cae 90 %. Para probarla habría que variar la cantidad de hilos, y eso queda como trabajo futuro.
- **«¿Por qué solo CPU?»** Es una decisión de alcance: lo que estudio es cómo el scheduler de Linux reparte la CPU. Otros motores, como vLLM, están orientados a GPU y quedan fuera de ese alcance. Es una limitación: los resultados valen para inferencia en CPU.
- **«¿Por qué llama3.2:3b?»** Porque es liviano: pesa unos 2 GB y ronda los 28 tokens/s en una prueba de humo (2 corridas), lo que permite más repeticiones. Un modelo de 7 u 8 mil millones haría muy lentas las cuotas estrictas del experimento 2 (estimación mía). Mido latencia, no calidad de respuesta. Es una limitación: un solo modelo.
- **«¿Docker agrega overhead?»** En CPU, en este montaje no medí un costo apreciable: sin límites las medias difirieron menos del 1 % (26,84 contra 26,81 tokens/s en el prompt largo, N = 30; −0,1 % a +0,7 %), sin afirmar que el costo sea cero. Un contenedor son procesos del mismo kernel, no una máquina virtual. Sí puede haber costo en red, disco o arranque, pero eso no lo medí.
- **«¿Por qué N = 10 en algunas condiciones?»** Con dos o más competidores Ollama cae por debajo de 1 token/s y una condición con N = 30 tardaba entre 3 y 6 horas. Por eso, con aprobación mía, `exp3_comp2`, `exp3_comp3` y `exp4_nice0` se corrieron con N = 10: 12 condiciones con 30 repeticiones y 3 con 10, por dos prompts, son 780 corridas. El efecto es enorme (30 a 50 veces más lento) y 10 corridas bastan para distinguirlo, con intervalos angostos. Lo que se pierde es precisión en el P95, que en esas condiciones es orientativo. Está declarado como limitación.
- **«¿Qué hicieron las IA y qué hiciste vos?»** Usé dos asistentes con roles separados. Claude Opus 5.5 fue el orquestador: me ayudó a organizar las tareas y redactó borradores de código, scripts y texto que yo dirigí, revisé, corregí y aprobé. Gemini 4 Neon fue el auditor: solo leía y verificaba que lo entregado cumpliera la especificación del trabajo, y dejaba un informe con evidencia. Separarlos evita que el mismo asistente apruebe su propio trabajo. Los dos trabajaron dentro del ecosistema Gentle AI. Las decisiones, las mediciones y la responsabilidad del resultado son mías.
