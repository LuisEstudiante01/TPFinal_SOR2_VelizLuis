# Guion para el oral (15 diapositivas, ~12 min)

Presentación: `TPFinal_SOR2_2026_2s_VelizLuis_presentacion.pptx`. Hablás en primera persona y con frases cortas. Entre corchetes va lo que conviene señalar en la pantalla.

Orden de la charla: la pregunta, por qué importa, con qué trabajamos y por qué, la teoría (carrera por la CPU, por qué EEVDF, cuotas), qué hice, los resultados (O1 a O4) y las conclusiones.

| # | Diapositiva | Tiempo |
|---|---|---|
| 1 | Portada | 20 s |
| 2 | La pregunta | 1 min |
| 3 | Por qué importa | 50 s |
| 4 | Con qué trabajamos y por qué | 50 s |
| 5 | Stack tecnológico | 40 s |
| 6 | La carrera por la CPU | 50 s |
| 7 | Por qué EEVDF | 50 s |
| 8 | El límite de CPU: cgroups v2 | 1 min |
| 9 | Qué hice | 40 s |
| 10 | O1: Docker rinde igual que el host | 45 s |
| 11 | O2: la cuota se paga en velocidad | 1 min |
| 12 | O3: un solo rival hunde el rendimiento | 1 min |
| 13 | O3: nice ayuda, pero la cuota manda | 1 min |
| 14 | O4: el scheduler muestra el mecanismo | 1 min |
| 15 | Conclusiones | 45 s |

Total: ≈ 12 min 20 s.

## 1. Portada (~20 s)
**Qué es:** abre la charla con el título y la autoría; la grilla de cuadrados anticipa los 12 hilos del modelo.

«Buenas. Mi trabajo se llama *Planificación de CPU en Linux: cuotas, competencia y prioridades en un LLM local*. Estudié cómo el sistema operativo reparte la CPU cuando un modelo de lenguaje corre en una computadora compartida con otras tareas.»

[Señalá la grilla] «Estos 12 cuadrados son los 12 hilos con los que trabaja el modelo. Uno está resaltado: el más lento. Van a ser importantes más adelante.»

## 2. La pregunta (~1 min)
**Qué es:** plantea la pregunta de investigación, las dos métricas (TTFT y tokens/s) y las tres hipótesis.

«Hoy es común correr un modelo de lenguaje, un LLM, en la propia máquina con una herramienta como **Ollama**. Pero esa máquina rara vez está sola: hay otras tareas compitiendo por la CPU, y el sistema operativo decide quién usa el procesador y cuánto.»

[Señalá la pregunta, debajo del título] «La pregunta que me planteó el profesor es: ¿en qué medida los límites de CPU con cgroups v2 y la competencia entre procesos afectan la inferencia de Ollama, y cuándo cambia algo ajustar la prioridad del scheduler?»

[Señalá el esquema: LLM local y otras tareas, hacia la CPU] «Dicho simple: qué le pasa al LLM cuando comparte la CPU.»

[Señalá TTFT y tokens/s a la derecha] «Para medir el impacto usé dos métricas:

- **TTFT**, *time to first token*: cuánto tarda en aparecer la primera palabra. Es la sensación de espera del usuario.
- **Tokens por segundo**: qué tan rápido sigue escribiendo. Un *token* es un pedazo de palabra.»

[Señalá las tres tarjetas de abajo] «Planteé tres hipótesis:

- **H1:** limitar la CPU aumenta la demora y baja la velocidad.
- **H2:** tener procesos compitiendo aumenta la demora y la vuelve más variable.
- **H3:** bajarles la prioridad a los competidores con `nice` reduce la interferencia, pero no compensa un límite estricto de CPU.»

## 3. Por qué importa (~50 s)
**Qué es:** justifica el problema con tres datos y marca el vacío que cubre el trabajo.

«¿Por qué vale la pena medir esto? Por tres razones y un vacío.»

[Señalá la tarjeta celeste, 51,1 %] «Primero: correr LLM locales es común. En la encuesta de Stack Overflow 2025, sobre herramientas para desarrollar agentes, el **51,1 %** de quienes respondieron marcó Ollama. Ojo: describe a quienes respondieron, no a toda la comunidad.»

[Señalá la tarjeta amarilla, «Sin tope»] «Segundo: esos modelos comparten el equipo con otras tareas, y **Docker no pone límites por defecto**. Hay que pedirlos, y el kernel los aplica.»

[Señalá la tarjeta roja, × 5] «Tercero: los límites de CPU pueden dañar la latencia. En otro trabajo, limitaron **1 de 19 pods** de una aplicación de microservicios y la latencia de cola se multiplicó **por cinco**. No es un LLM, pero es la señal de alerta.»

[Señalá la franja violeta de abajo] «Y el vacío: entre las fuentes que consulté, nadie midió el efecto conjunto de cuotas, competencia y `nice` sobre un LLM en CPU. Eso es lo que aporto.»

## 4. Con qué trabajamos y por qué (~50 s)
**Qué es:** presenta las cuatro elecciones de diseño, cada una con su razón corta.

«Estas son las cuatro elecciones y por qué las hice. El detalle frente a las alternativas está en la Tabla 5.4 del informe.»

[Señalá la tarjeta de Ollama] «**Ollama con llama3.2 de 3 mil millones de parámetros.** Ollama lo pide el objetivo del trabajo. Y el modelo es liviano: me deja hacer más repeticiones. Uno más grande volvería muy lentas las cuotas estrictas.»

[Señalá el chip] «**Solo CPU.** Es una decisión de alcance: lo que estudio es cómo el scheduler reparte la CPU.»

[Señalá la ballena] «**Docker.** Aplica las cuotas con cgroups y comparte el kernel con el host, así que no es una máquina virtual.»

[Señalá el logo de Ubuntu] «**Ubuntu Server 26.04, con kernel 7.0.** Trae EEVDF y cgroups v2 de forma nativa.»

## 5. Stack tecnológico (~40 s)
**Qué es:** muestra por capas todas las herramientas usadas, con logos y nombres cortos.

«Este es el stack completo, por capas.»

[Recorré las columnas de izquierda a derecha]
- «**Plataforma:** una PC dedicada con Ubuntu Server 26.04, kernel 7.0 con el scheduler EEVDF y un Ryzen 9 de 12 núcleos. Todo en Linux nativo.»
- «**Inferencia:** Ollama con el modelo llama3.2 de 3 mil millones de parámetros, solo con CPU.»
- «**Control:** Docker, que por debajo escribe `cpu.max` de cgroups v2, y `nice` para la prioridad.»
- «**Carga y medición:** `stress-ng` genera los procesos rivales; `perf sched` y `cpu.stat` muestran qué hace el kernel.»
- «**Análisis:** Python con pandas y SciPy.»
- «**Organización:** Notion para las tareas y Obsidian para las notas.»
- «**IA:** dos asistentes con roles separados: **Claude Opus 5.5** como orquestador, que planifica y escribe, y **Gemini 4 Neon** como auditor, que solo lee y verifica contra la especificación. Los dos trabajaron dentro del ecosistema **Gentle AI**, que organiza el flujo de trabajo: tareas, subagentes, memoria entre sesiones y revisión. Las decisiones y las mediciones son mías.»

## 6. La carrera por la CPU (~50 s)
**Qué es:** explica que hay más hilos que CPUs, que el scheduler decide quién corre y que `nice` es un peso, no un interruptor.

«Casi siempre hay más hilos listos que CPUs. Entonces compiten: es una carrera por la CPU.»

[Señalá los cuadrados grises y la CPU, arriba] «Los hilos esperan en una cola. El **scheduler**, o planificador, es la parte del kernel que elige cuál corre. En Linux actual se llama **EEVDF**. Los que no corren, esperan.»

[Señalá la franja A, B, C] «Acá hay una CPU y tres tareas. Cada una recibe un turno corto, de unos 2,8 ms en este equipo, y después le toca a la siguiente.»

[Señalá el círculo naranja de la izquierda] «Con **`nice`** no se prende ni se apaga un proceso: se le da un **peso**. nice 0 es lo normal y pesa 1024; nice 10 pesa 110; nice 19 pesa 15, casi nada.»

[Señalá las barras de la derecha] «En mi experimento Ollama queda en nice 0 y tiene 12 competidores. Si ellos están en nice 0, a Ollama le toca la mitad de la CPU. Con nice 10, el 90 %. Con nice 19, el 98,6 %. Subirles el nice a los competidores le deja la CPU a Ollama.»

## 7. Por qué EEVDF (~50 s)
**Qué es:** compara los tres candidatos de scheduler y justifica por qué se midió EEVDF.

«Una duda razonable: ¿por qué EEVDF y no otro scheduler? Hay tres candidatos.»

[Señalá la columna gris, CFS] «**CFS** era el planificador anterior. Fue reemplazado por EEVDF desde el kernel 6.6, así que en el kernel 7.0 ya no existe. Medirlo exigiría otro kernel y cambiaría a la vez los drivers y el resto del sistema: la comparación quedaría confundida. Por eso lo trato solo en la teoría.»

[Señalá la columna resaltada, EEVDF] «**EEVDF** es el que usa Ollama por defecto, con la política normal, SCHED_OTHER. Es equitativo y compatible con `cpu.max`. Son justo las variables que estudio.»

[Señalá la columna de la derecha] «**SCHED_FIFO y SCHED_RR** son de tiempo real: sin equidad, y rompen tanto el reparto como `cpu.max`. Las probé solo como exploración corta. No digo que sean peores: están hechas para otro problema.»

## 8. El límite de CPU: cgroups v2 (~1 min)
**Qué es:** explica cómo funciona el límite `cpu.max` y por qué frena a los 12 hilos a la vez.

«Los **cgroups** son el mecanismo de Linux para agrupar procesos y ponerles límites; Docker los usa por debajo. El límite de CPU se llama **`cpu.max`**, y no funciona como uno se imagina: no dice "usá 2 CPUs", da un **presupuesto de tiempo de CPU que se recarga cada 100 ms**.»

[Señalá los tres pasos, de izquierda a derecha]
«1. **Recarga:** con una cuota de 2 CPUs, cada 100 ms el grupo recibe 200 ms de CPU.
2. **Gasto:** el presupuesto es compartido por los 12 hilos de Ollama, que corren a la vez. Por cada milisegundo real gastan 12.
3. **Frenado:** a los 16,7 ms el presupuesto se acaba y el kernel **frena a todo el grupo** hasta la próxima recarga. Ese frenado se llama ***throttling***.»

[Señalá la barra verde y roja] «Esta barra está a escala: un período de 100 ms. Ollama corre en la parte verde, 16,7 ms, y pasa los otros 83 ms frenado, aunque haya CPUs libres.»

[Señalá el recuadro de abajo] «Es como una tarjeta prepaga que se recarga cada 100 ms, compartida entre 12 personas que gastan a la vez: se la funden enseguida y esperan.»

## 9. Qué hice (~40 s)
**Qué es:** resume el banco de pruebas en tres pasos y cuatro números: 780 corridas, 15 condiciones, 4 experimentos y unas 10 horas de mediciones.

«Armé un banco de pruebas en una PC con Linux nativo, sin máquina virtual.»

[Señalá los tres íconos, de izquierda a derecha] «Tres pasos:

1. **Ollama:** lo instalé directamente en Linux y también dentro de un contenedor Docker.
2. **Condiciones:** le apliqué distintas cuotas de CPU, procesos competidores generados con `stress-ng` y distintos valores de `nice`.
3. **Medición:** medí TTFT y tokens por segundo siempre con el mismo modelo, las mismas preguntas y el mismo script.»

[Señalá los tres números grandes] «En total, **780 corridas, 15 condiciones y 4 experimentos**, medidos de un tirón en **10 horas y cuarto**. Con las pruebas exploratorias, las mediciones suman unas 13 horas. Repetí cada condición 30 veces, o 10 en tres casos muy lentos, para poder comparar con estadística.»

## 10. O1: Docker rinde igual que el host (~45 s)
**Qué es:** resultado del objetivo 1; compara Ollama en el host contra Ollama en Docker, sin límites.

«El primer objetivo fue comparar Ollama en Linux con Ollama en Docker, sin límites.»

[Señalá el número «< 1 %» y el gráfico] «La diferencia fue menor al 1 %: 26,84 contra 26,81 tokens por segundo.»

«Tiene sentido porque un contenedor **no es una máquina virtual**: son procesos del mismo kernel, aislados. No hay una capa que emule la CPU. Como rinden igual, pude usar Docker para aplicar las cuotas sin que el contenedor fuera un factor.»

## 11. O2: la cuota se paga en velocidad (~1 min)
**Qué es:** resultado del objetivo 2; muestra cómo cae la velocidad al bajar la cuota de CPU.

«El segundo objetivo fue limitar la CPU con `cpu.max`.»

[Recorré las barras] «Sin límite hay 26,8 tokens por segundo. Con 8 CPUs baja a 17,3, con 4 a 8,3, con 2 a 3,6 y con 1 a 1,8.»

[Señalá el «÷ 2» y el «−93 %»] «Con 4 CPUs o menos, cada vez que la cuota se reduce a la mitad, la velocidad también cae aproximadamente a la mitad. Con 1 CPU la velocidad cae un **93 %**, y la espera hasta la primera palabra se multiplica por 16: de casi 1 segundo a **15 segundos**.»

«En los registros del kernel aparece el *throttling* en todas las condiciones con cuota. Esto **confirma H1**.»

## 12. O3: un solo rival hunde el rendimiento (~1 min)
**Qué es:** resultado del objetivo 3 (competencia); un único proceso competidor ya reduce la velocidad un 90 %, y se muestra la hipótesis de sincronización.

«El tercer objetivo fue la competencia: agregué procesos que consumen CPU, con la misma prioridad que Ollama.»

[Señalá el «−90 %» y el gráfico] «Con un solo competidor la velocidad cae un **90 %**: de 23,7 a 2,5 tokens por segundo. Con 2 y 3 competidores baja a 0,7 y 0,5.»

«Es mucho más de lo esperable, porque el competidor solo le saca una pequeña parte de la CPU.»

[Señalá el diagrama de barras: el hilo rojo largo y los hilos que esperan] «Mi **hipótesis**, que no está demostrada, es que los 12 hilos del modelo se sincronizan en cada paso. Si uno solo comparte su CPU con el competidor, los otros 11 lo tienen que esperar. La cadena va al ritmo del eslabón más lento.»

«Además la variabilidad crece mucho. Esto **confirma H2**.»

## 13. O3: nice ayuda, pero la cuota manda (~1 min)
**Qué es:** completa el objetivo 3 con la prioridad; compara los distintos `nice` de 12 competidores y el caso con cuota.

«Después repetí con 12 competidores, cambiando su prioridad.»

[Recorré las barras] «Las barras muestran el promedio:

- competidores con nice 0: Ollama hace 0,47 tokens por segundo (esta condición tiene 10 corridas);
- con nice 10: 9,5;
- con nice 19: **20,6**, casi lo mismo que sin competencia, que son 23,7.

O sea, **`nice` ayuda mucho**.»

[Señalá la tarjeta de abajo a la derecha, 2,83] «Pero si además le pongo a Ollama una cuota de 2 CPUs, rinde solo **2,83**, menos que con esa misma cuota y sin competidores, que son 3,61. La cuota se aplica al **grupo entero**; la prioridad solo reparte lo que queda adentro de ese límite.»

«Hubo tres corridas anormalmente lentas en esa condición. Igual la mediana, 2,93, también queda debajo de 3,61. Esto **confirma H3**.»

## 14. O4: el scheduler muestra el mecanismo (~1 min)
**Qué es:** resultado del objetivo 4; relaciona lo medido con lo que ve el kernel (tiempo en cola y frenadas).

«El cuarto objetivo fue mirar adentro del scheduler. Con herramientas del kernel como `perf` medí cuánto tiempo pasan los hilos de Ollama **esperando en la cola** para usar la CPU.»

[Recorré las barras] «Sin límite, casi 0 %. Con cuota, entre 67 % y 92 % del tiempo esperando. Con nice 19 y 2 CPUs, 89 %.»

[Señalá el «10 / s»] «Y el kernel registra **10 frenos por segundo**: uno por cada período de 100 ms, que es justo lo que vimos en la teoría.»

[Señalá el «7,7 %»] «Lo interesante es el caso de un competidor: los hilos esperan solo el **7,7 %** del tiempo y aun así la velocidad cae 90 %. No es que falte CPU, sino que los hilos se frenan entre sí. Eso refuerza la hipótesis de la sincronización.»

## 15. Conclusiones (~45 s)
**Qué es:** cierra con tres ideas y una cifra cada una; termina con la apertura a preguntas.

[Señalá las tres tarjetas, de izquierda a derecha] «Para cerrar, tres ideas:

1. **Los contenedores no cuestan CPU** (≈ 0 %): Docker rinde igual que Linux directo.
2. **La cuota se cumple con exactitud y manda**: la velocidad cae en proporción, y un poco más. Mi hipótesis es la sincronización de hilos.
3. **La competencia pesa mucho más de lo esperado** (−90 % con un solo rival): `nice` ayuda, pero un límite estricto de CPU manda sobre la prioridad.»

«Las limitaciones: una máquina, un modelo, una configuración de hilos. Como trabajo futuro propongo variar la cantidad de hilos del modelo para probar la hipótesis. Se confirmaron H1, H2 y H3.»

[Señalá las tres etiquetas de abajo] «Debajo de cada idea está lo que responde: O1 se cumplió, H1 se confirmó, y H2 y H3 también; H2 con un efecto mucho mayor del que esperaba.»

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
- **«¿Cómo sabés que la sincronización es la causa?»** No lo sé con certeza; es una hipótesis coherente con los datos. Con un competidor, los hilos esperan en cola solo el 7,7 % del tiempo y sin throttling, y aun así la velocidad cae 90 %. Para probarla habría que variar la cantidad de hilos, y eso queda como trabajo futuro.
- **«¿Por qué solo CPU?»** Es una decisión de alcance: lo que estudio es cómo el scheduler de Linux reparte la CPU. Otros motores, como vLLM, están orientados a GPU y quedan fuera de ese alcance. Es una limitación: los resultados valen para inferencia en CPU.
- **«¿Por qué llama3.2:3b?»** Porque es liviano: pesa unos 2 GB y ronda los 28 tokens/s en una prueba de humo (2 corridas), lo que permite más repeticiones. Un modelo de 7 u 8 mil millones haría muy lentas las cuotas estrictas del experimento 2 (estimación mía). Mido latencia, no calidad de respuesta. Es una limitación: un solo modelo.
- **«¿Docker agrega overhead?»** En CPU, no: sin límites la diferencia con el host fue menor al 1 % (26,84 contra 26,81 tokens/s en el prompt largo; −0,1 % a +0,7 %). Un contenedor son procesos del mismo kernel, no una máquina virtual. Sí puede haber costo en red, disco o arranque, pero eso no lo medí.
- **«¿Por qué N = 10 en algunas condiciones?»** Con dos o más competidores Ollama cae por debajo de 1 token/s y una condición con N = 30 tardaba entre 3 y 6 horas. Por eso, con aprobación mía, `exp3_comp2`, `exp3_comp3` y `exp4_nice0` se corrieron con N = 10: 12 condiciones con 30 repeticiones y 3 con 10, por dos prompts, son 780 corridas. El efecto es enorme (30 a 50 veces más lento) y 10 corridas bastan para distinguirlo, con intervalos angostos. Lo que se pierde es precisión en el P95, que en esas condiciones es orientativo. Está declarado como limitación.
- **«¿Qué hicieron las IA y qué hiciste vos?»** Usé dos asistentes con roles separados. Claude Opus 5.5 fue el orquestador: planificó y escribió código, scripts y texto a partir de `docs/SPEC.md`. Gemini 4 Neon fue el auditor: solo leía y verificaba que lo entregado cumpliera el SPEC, y dejó cada informe con evidencia en `docs/auditorias/`. Separarlos evita que el mismo asistente apruebe su propio trabajo. Las decisiones y las mediciones son mías, y yo apruebo cualquier cambio al SPEC.
