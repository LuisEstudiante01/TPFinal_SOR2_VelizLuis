# 2. Planteamiento del problema

## 2.1. Contexto: inferencia local de LLM en máquinas compartidas

La inteligencia artificial generativa forma parte del trabajo cotidiano de quienes desarrollan software. En la encuesta de desarrolladores de Stack Overflow (2025a), el 84 % de quienes respondieron la pregunta sobre adopción declaró que usa o planea usar herramientas de IA en su trabajo. En la pregunta sobre herramientas para desarrollar agentes, 1920 de 3758 participantes marcaron Ollama (51,1 %) y 1238 marcaron LangChain (32,9 %); podían marcar más de una opción. La encuesta reunió 49 009 respuestas en total y reclutó principalmente a través de canales de Stack Overflow (2025b). Estas cifras describen a quienes respondieron, no la adopción en toda la comunidad ni el rendimiento de las herramientas. Ollama permite ejecutar modelos de lenguaje en el equipo propio, y esa modalidad interesa, entre otras razones, por la privacidad: Tyndall et al. (2025) evalúan la factibilidad de LLM seguros y fuera de línea, con recuperación aumentada (RAG), en hardware de consumo que solo dispone de CPU, y el trabajo sobre modelos pequeños para dispositivos de borde considera modelos de entre 100 millones y 5 mil millones de parámetros (Lu et al., 2025).

Estos modelos rara vez se ejecutan en una máquina dedicada. Comparten el equipo con otros procesos y, cada vez más, se empaquetan en contenedores. Docker no impone restricciones de recursos por defecto; los límites se piden explícitamente (`--cpus`, `--cpuset-cpus`) y el kernel los aplica mediante cgroups (Docker, s. f.-d). Es el sistema operativo, entonces, quien decide cuánta CPU recibe la inferencia: el scheduler reparte el tiempo entre tareas (en el kernel 7.0 de este trabajo, EEVDF), `nice` modifica el peso de cada proceso y `cpu.max` de cgroups v2 fija un tope por período.

## 2.2. El problema: cuotas, competencia y prioridades sobre una carga de CPU

Que estos mecanismos pueden degradar el rendimiento de servicios sensibles a la latencia está documentado fuera de la inferencia de LLM. Shetty et al. (2025) aplicaron un límite de CPU a uno de los 19 pods de la aplicación HotelReservation. La latencia de cola de extremo a extremo se multiplicó por cinco, aun sin intentar reducir la utilización de CPU de ese pod. En otra medición del mismo benchmark, retirar los límites redujo en promedio un 38 % los recursos de CPU necesarios para cumplir el objetivo de latencia de 20 ms. Ugedal y Kumar (2022) muestran que el control de ancho de banda de CFS puede frenar (*throttling*) a los procesos sin necesidad, incluso cuando la cuota no está realmente agotada.

**Tabla 2.1. Datos cuantitativos que motivan el problema.**

| Ámbito | Dato | Fuente |
|---|---|---|
| Adopción de IA | 84 % de quienes respondieron la pregunta usa o planea usar herramientas de IA | Stack Overflow (2025a) |
| Herramientas para agentes | Ollama: 51,1 % y LangChain: 32,9 % de las 3758 personas que respondieron la pregunta | Stack Overflow (2025a) |
| Límites de CPU en contenedores | Un límite en 1 de 19 pods multiplicó por 5 la latencia de cola de extremo a extremo | Shetty et al. (2025) |
| Límites de CPU en contenedores | Retirar los límites redujo en promedio un 38 % los recursos de CPU necesarios para cumplir el objetivo de latencia de 20 ms en HotelReservation | Shetty et al. (2025) |

Fuente: elaboración propia a partir de Stack Overflow (2025a) y Shetty et al. (2025).

Esos resultados provienen de microservicios, no de inferencia de LLM. Esta tiene un perfil distinto: el procesamiento del prompt y la generación de cada token ocupan varios hilos que deben sincronizarse en cada paso, de modo que cuando el scheduler o una cuota frenan a uno solo, los demás podrían esperarlo. Si eso ocurre, la cuota de CPU, un proceso competidor o la prioridad afectarían el tiempo hasta el primer token (TTFT), el throughput y su variabilidad. La sección 8.4.1 muestra una primera señal de que el efecto puede ser grande: con un solo competidor de igual prioridad, Ollama bajó de 23,74 a 2,45 tokens/s con el prompt largo (datos propios).

## 2.3. Vacío que motiva el trabajo

Las fuentes consultadas estudian la factibilidad de ejecutar LLM en CPU (Tyndall et al., 2025), el tamaño de los modelos para el borde (Lu et al., 2025) y el costo de los límites de CPU en otras cargas (Shetty et al., 2025; Ugedal y Kumar, 2022). No se encontró entre ellas una medición del efecto conjunto de cuotas de cgroups v2, competidores y `nice` sobre TTFT, tokens por segundo y variabilidad de la inferencia de Ollama, ni una comparación entre ejecutarlo directo en Linux y dentro de Docker bajo esas condiciones. Esa falta no demuestra que no exista literatura al respecto; delimita lo que este trabajo busca aportar.

El problema tiene consecuencias prácticas para usuarios y organizaciones pequeñas que ejecutan modelos locales por privacidad o para no depender de servicios externos y comparten el equipo con otros servicios. Sin datos, la configuración de límites y prioridades se decide a ciegas: un límite de CPU puede parecer inocuo y degradar la inferencia de manera desproporcionada. De allí surge la pregunta de investigación del capítulo 3.
