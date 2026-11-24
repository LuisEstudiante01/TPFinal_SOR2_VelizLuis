# Planificación de CPU en Linux: cuotas, competencia y prioridades en un LLM local

Trabajo final de **Sistemas Operativos y Redes 2** (UNGS, Licenciatura en Sistemas, segundo semestre de 2026).
Autor: **Luis Veliz**. Docente: Benjamín Chuquimango.

El trabajo mide cómo el sistema operativo reparte la CPU cuando un modelo de lenguaje corre en una máquina compartida: qué le pasa a [Ollama](https://ollama.com) cuando tiene una cuota de CPU con cgroups v2, cuando otros procesos compiten por la CPU y cuando se ajusta la prioridad con `nice`.

## Entregables

| Qué | Archivo |
|---|---|
| Informe final (PDF) | [`docs/informe/TPFinal_SOR2_2026_2s_VelizLuis.pdf`](docs/informe/TPFinal_SOR2_2026_2s_VelizLuis.pdf) |
| Presentación del oral | [`docs/presentacion/TPFinal_SOR2_2026_2s_VelizLuis_presentacion.pdf`](docs/presentacion/TPFinal_SOR2_2026_2s_VelizLuis_presentacion.pdf) (también en `.pptx`) |
| Guion del oral | [`docs/presentacion/guion-oral.pdf`](docs/presentacion/guion-oral.pdf) |

## Pregunta de investigación

> ¿En qué medida los límites de CPU impuestos mediante cgroups v2 y la competencia entre procesos afectan el tiempo hasta el primer token (TTFT), el throughput y la variabilidad de la inferencia de Ollama, y bajo qué condiciones el ajuste de prioridades del scheduler de Linux modifica ese comportamiento?

Hipótesis:

- **H1:** la reducción de la cuota de CPU incrementa la latencia y disminuye el rendimiento de inferencia cuando se produce throttling.
- **H2:** la competencia por CPU incrementa la latencia y su variabilidad respecto de una ejecución sin competencia.
- **H3:** ajustar la prioridad mediante `nice` puede reducir la interferencia de procesos competidores, pero no necesariamente compensar las limitaciones impuestas por una cuota estricta de CPU.

## Resultados principales

Prompt largo, `llama3.2:3b`, solo CPU. El detalle y la estadística están en el capítulo 8 del informe.

| Objetivo | Resultado |
|---|---|
| **O1:** host frente a Docker | Diferencia menor al 1 % (26,84 frente a 26,81 tokens/s). Un contenedor no virtualiza la CPU. |
| **O2:** cuotas con `cpu.max` | Media cuota, media velocidad: de 26,78 tokens/s sin límite a 1,77 tokens/s con 1 CPU (−93 %). |
| **O3:** competidores | Un solo competidor de igual prioridad baja el rendimiento de 23,74 a 2,45 tokens/s (−90 %). |
| **O3:** `nice` | Con los competidores en `nice` 19, Ollama vuelve a 20,59 tokens/s; con una cuota de 2 CPUs se queda en 2,83 tokens/s: la cuota manda. |
| **O4:** métricas del scheduler | Con cuota hay 10 throttles por segundo; con un competidor los hilos esperan en cola solo el 7,7 % del tiempo y aun así el rendimiento cae 90 %. |

Se confirman H1, H2 y H3. La explicación de la caída con un competidor (los 12 hilos se esperan entre sí en cada paso) es una hipótesis, no una causa demostrada.

## Entorno de medición

- Ubuntu Server 26.04.1 LTS, kernel 7.0.0-43-generic, scheduler **EEVDF**, cgroups v2.
- AMD Ryzen 9 9900X (12 núcleos), Linux nativo por SSH; nada se midió sobre WSL2 ni Windows.
- Ollama 0.40.16 con `llama3.2:3b` (Q4), Docker 29.10.0, `stress-ng` 0.20.01.
- 780 corridas, 15 condiciones y 4 experimentos, medidos de corrido en 10 h 15 min (`experiments/results/night.log`).

## Estructura del repositorio

| Carpeta | Contenido |
|---|---|
| `docs/informe/` | Capítulos del informe en Markdown (`NN-*.md`), figuras y el script de armado. |
| `docs/presentacion/` | Generador de la presentación (`build_deck.js`), presentación y guion del oral. |
| `experiments/` | Protocolo de medición, corridas, resultados crudos, análisis y figuras. |

## Cómo reproducir

**Mediciones** (en un Linux con Docker, Ollama y `stress-ng`):

```bash
python3 experiments/run_matrix.py --n 1        # piloto: una repetición por condición
python3 experiments/run_matrix.py              # corrida completa (Exp 1 a 4)
python3 experiments/run_matrix.py --only exp2  # solo un experimento
python3 experiments/analyze.py --results experiments/results --out experiments/analysis  # tablas y estadística
python3 experiments/plot_figures.py            # figuras del informe
```

**Informe** (requiere Pandoc; el PDF final se exporta con Microsoft Word desde WSL):

```bash
bash docs/informe/build.sh          # DOCX y vista previa con LibreOffice
bash docs/informe/build.sh --word   # DOCX y PDF final con Word
```

**Presentación** (requiere Node.js):

```bash
cd docs/presentacion
npm install
node build_deck.js
```

## Uso de IA

El trabajo se hizo con dos asistentes de IA con roles separados, dentro del ecosistema [Gentle AI](https://github.com/Gentleman-Programming/gentle-shell):

- **Claude Opus 5.5**, orquestador: planifica las tareas y escribe el código y el texto a partir de la especificación del trabajo.
- **Gemini 4 Neon**, auditor: solo lee y verifica cada entrega contra la especificación, con evidencia.

El autor definió la especificación, tomó las decisiones y revisó los resultados. Las cifras salen de las corridas del banco de pruebas, no de los asistentes. El detalle está en la sección 5.10 del informe.

## Nota

Este repositorio público contiene el trabajo y sus resultados. Las notas personales, el seguimiento de tareas y los documentos internos de auditoría quedan en el repositorio privado de trabajo.
