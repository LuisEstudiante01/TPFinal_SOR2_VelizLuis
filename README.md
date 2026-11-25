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
| **O1:** host frente a Docker | Sin cuotas adicionales ni competidores, las medias de TTFT y tokens/s difirieron menos del 1 % en este ensayo (26,84 frente a 26,81 tokens/s para el prompt largo). No se demuestra equivalencia. |
| **O2:** cuotas con `cpu.max` | Media cuota, media velocidad: de 26,78 tokens/s sin límite a 1,77 tokens/s con 1 CPU (−93 %). |
| **O3:** competidores | Un solo competidor de igual prioridad baja el rendimiento de 23,74 a 2,45 tokens/s (−90 %). |
| **O3:** `nice` | Con 12 competidores a `nice` 19, agregar una cuota equivalente a 2 CPUs sin cambiar las CPUs disponibles ni los rivales reduce la media de 20,59 a 2,83 tokens/s. |
| **O4:** métricas del scheduler | En la captura de 20 s con un competidor sin cuota, el rival usó 0,91 CPUs en promedio y Ollama pasó en cola el 7,7 % de su tiempo ejecutable (ejecución más espera). La caída cercana al 90 % se midió en corridas aparte. |

El contraste entre `exp2_cpus2` (3,61 tokens/s) y `exp4_nice19_cpus2` (2,83) no aísla el efecto de los competidores: con la misma cuota también cambia el conjunto de CPUs lógicas (`0–23` frente a `6–11,18–23`). La sincronización entre hilos de `llama.cpp` es una hipótesis para el colapso, no una causa demostrada.

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

### 1. Regenerar los resultados publicados (sin Ollama ni Docker)

Desde una copia nueva del repositorio, con Python **3.15** disponible como `python3`:

```bash
git clone https://github.com/LuisEstudiante01/TPFinal_SOR2_VelizLuis.git
cd TPFinal_SOR2_VelizLuis
python3 -m venv .venv
.venv/bin/python -m pip install -r experiments/requirements.txt
.venv/bin/python experiments/analyze.py --results experiments/results --out experiments/analysis
.venv/bin/python experiments/analyze_rt.py --results experiments/results_rt --base experiments/results --out experiments/analysis_rt
.venv/bin/python experiments/plot_figures.py
```

Se regeneran las tablas y comparaciones de los experimentos 1–4 en [`experiments/analysis/`](experiments/analysis/), el análisis descriptivo del experimento exploratorio 5 en [`experiments/analysis_rt/`](experiments/analysis_rt/) y las seis figuras de resultados en PNG y PDF en [`docs/informe/figuras/resultados/`](docs/informe/figuras/resultados/). Los comandos sobrescriben esas **salidas derivadas** en la copia, no los datos originales. Diferencias de fuentes o metadatos de exportación pueden cambiar los archivos de imagen o PDF sin cambiar los números.

| Evidencia original | Contenido |
|---|---|
| [`experiments/results/`](experiments/results/) | 15 CSV de medición, 15 archivos `.meta.json`, [`night.log`](experiments/results/night.log) y [`watch_competitors.csv`](experiments/results/watch_competitors.csv). El log registra la cuota y el conjunto de CPUs de cada condición de la campaña principal. |
| [`experiments/sched/`](experiments/sched/) y [`experiments/sched_extra/`](experiments/sched_extra/) | Capturas independientes de 20 s: resúmenes, `schedstat`, `pidstat` y salidas de `perf sched latency`. |
| [`experiments/env/environment.txt`](experiments/env/environment.txt) y [`experiments/results_rt/`](experiments/results_rt/) | Entorno original y datos de la extensión exploratoria de tiempo real. |

### 2. Repetir las mediciones en Linux nativo (opcional)

Esto genera **datos nuevos**, no resultados idénticos. El banco original usó cgroups v2, Docker con el controlador de cgroups `systemd`, Ollama 0.40.16, `stress-ng` 0.20.01 y governor `performance`. Usá un equipo dedicado: los scripts cambian la cuota y la afinidad del contenedor y lanzan procesos de carga. La cuenta del laboratorio necesita los permisos no interactivos de `sudo -n` que usan los scripts; no habilites permisos amplios en un equipo compartido. Para las capturas adicionales hacen falta `perf` y `pidstat` (`sysstat`).

1. Prepará Ollama como servicio de systemd `ollama.service` en el host (`127.0.0.1:11434`, cgroup `/sys/fs/cgroup/system.slice/ollama.service`) y un contenedor llamado `ollama-docker` (`127.0.0.1:11435` → `11434`). El protocolo mide solo CPU. Para el contenedor, usá una imagen que corresponda a Ollama 0.40.16, no la etiqueta móvil `latest` como garantía de versión; el ensayo original no registró un digest de la imagen de Docker. Un comando de preparación, con la referencia de imagen verificada en `OLLAMA_IMAGE`, es:

   ```bash
   sudo -n docker run -d --name ollama-docker \
     -p 127.0.0.1:11435:11434 -v ollama-docker-models:/root/.ollama "$OLLAMA_IMAGE"
   ```

2. Descargá el modelo en ambos entornos: `ollama pull llama3.2:3b` y `sudo -n docker exec ollama-docker ollama pull llama3.2:3b`. Comprobá con `/api/tags` en ambos puertos que el digest del modelo coincide con `model_digest` en los `.meta.json` originales. Si no coincide, la repetición no usa exactamente el mismo artefacto.
3. Revisá `lscpu -e=CPU,CORE,ONLINE` y `stat -fc %T /sys/fs/cgroup` (debe dar `cgroup2fs`). La matriz usa `0-23` y `6-11,18-23` tal como aparecen en el equipo original. Si tu topología es distinta, adaptá las máscaras con criterio y documentá la diferencia. Los prompts, parámetros y repeticiones por condición están fijados en [`run_protocol.py`](experiments/run_protocol.py) y [`run_matrix.py`](experiments/run_matrix.py).

Desde la raíz, después de completar ese entorno:

```bash
python3 experiments/run_matrix.py --list  # imprime la matriz sin ejecutar nada
run_dir=$(mktemp -d "$PWD/repeticion.XXXXXX")
set -o pipefail
# Piloto rápido y campaña completa en directorios distintos:
python3 experiments/run_matrix.py --only exp1 --n 1 --out "$run_dir/piloto" 2>&1 | tee "$run_dir/piloto.log"
python3 experiments/run_matrix.py --out "$run_dir/results" 2>&1 | tee "$run_dir/night.log"
.venv/bin/python experiments/analyze.py --results "$run_dir/results" --out "$run_dir/analysis"
```

La campaña principal original tardó unas 10 h 15 min. No mezcles distintas corridas en el mismo directorio de entrada del análisis. `--only exp2` permite acotar la matriz; `--only exp5` habilita por separado la prueba exploratoria de tiempo real, fuera de la campaña principal y con permisos y requisitos adicionales. Los metadatos de las corridas nuevas pueden tener campos que el esquema original no tenía; para la configuración original consultá `night.log`.

Las capturas del scheduler se hacen por separado para no incluir la sobrecarga de `perf` en las mediciones de rendimiento:

```bash
python3 experiments/sched_capture.py --window 20 --out "$run_dir/sched" --raw "$run_dir/sched_raw"
python3 experiments/sched_capture.py --window 20 --only exp2_cpus2,exp4_nice0 \
  --out "$run_dir/sched_extra" --raw "$run_dir/sched_extra_raw"
```

`watch_competitors.sh` es un monitor opcional para una campaña en `tmux`: recibe como argumentos la ruta al log y el nombre de la sesión, y requiere un único cgroup Docker activo. Los archivos binarios `perf.data` de nuevas capturas quedan en el directorio `--raw`; no forman parte de la evidencia publicada.

### 3. Generar los entregables

**Informe** (Pandoc y Python; LibreOffice es opcional y solo crea una vista previa):

```bash
bash docs/informe/build.sh          # DOCX en docs/informe/build/
bash docs/informe/build.sh --word   # exportación oficial desde WSL con Microsoft Word
```

Para regenerar los diagramas además de las figuras experimentales: `.venv/bin/python docs/informe/figuras/diagramas.py`.

**Presentación** (Node.js 26 y npm 11, usando el lockfile):

```bash
cd docs/presentacion
npm ci
node build_deck.js  # PPTX editable, en esta carpeta
```

Desde esa misma carpeta, en WSL con Microsoft PowerPoint y Word instalados, exportá la presentación y el guion:

```bash
name=TPFinal_SOR2_2026_2s_VelizLuis_presentacion
powershell.exe -NoProfile -File "$(wslpath -w "$PWD/ppt_export.ps1")" \
  -Pptx "$(wslpath -w "$PWD/$name.pptx")" -Pdf "$(wslpath -w "$PWD/$name.pdf")"
mkdir -p build
pandoc guion-oral.md --metadata lang=es-AR --reference-doc ../informe/build/reference.docx \
  -o build/guion-oral.docx
powershell.exe -NoProfile -File "$(wslpath -w "$PWD/../informe/word_export.ps1")" \
  -Docx "$(wslpath -w "$PWD/build/guion-oral.docx")" -Pdf "$(wslpath -w "$PWD/guion-oral.pdf")"
```

El archivo `reference.docx` del comando de Pandoc se genera en el paso **Informe**. Si Windows bloquea los scripts, abrí los editables en Office y exportá desde allí, sin cambiar la política de PowerShell. No uses un PDF de vista previa de LibreOffice como PDF oficial del informe.

## Uso de IA

El trabajo se hizo con dos asistentes de IA con roles separados, dentro del ecosistema [Gentle AI](https://github.com/Gentleman-Programming/gentle-shell):

- **Claude Opus 5.5**, orquestador: ayuda a organizar las tareas y redacta borradores de código, scripts y texto a partir de la especificación del trabajo, bajo la dirección del autor, que los revisa, corrige y aprueba.
- **Gemini 4 Neon**, auditor: solo lee y verifica cada entrega contra la especificación, con evidencia.

El autor definió la especificación, tomó las decisiones, revisó los resultados y es responsable del trabajo. Las cifras salen de las corridas del banco de pruebas, no de los asistentes. El detalle está en la sección 5.10 del informe.

## Nota

Este repositorio público contiene el trabajo y sus resultados. Las notas personales, el seguimiento de tareas y los documentos internos de auditoría quedan en el repositorio privado de trabajo.
