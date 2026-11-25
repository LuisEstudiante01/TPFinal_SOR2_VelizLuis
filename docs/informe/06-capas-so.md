# 6. Análisis según capas del sistema operativo

Este capítulo ubica el banco de pruebas en las cuatro capas que pide la consigna (hardware, kernel, servicios y aplicaciones). Para cada una indica qué componente del banco la ocupa, qué mecanismo del sistema operativo se usa (espacios de nombres, grupos de control y llamadas al sistema) y qué política de seguridad aplica. La arquitectura se muestra en la Figura 7.1 del capítulo 7 y no se repite aquí. Lo que no está documentado ni se pudo comprobar se declara como no verificado, en lugar de suponerse configurado.

## 6.1. Visión general

La Tabla 6.1 resume el análisis; las secciones siguientes desarrollan cada fila.

**Tabla 6.1. Capas del banco de pruebas, mecanismos y políticas de seguridad.**

| Capa | Componente del banco | Mecanismo del SO | Qué se mide o controla | Política de seguridad |
|---|---|---|---|---|
| Hardware | AMD Ryzen 9 9900X, 12 núcleos y 24 CPUs lógicas (SMT), 29 GiB de RAM | Topología de CPU, governor `performance`, boost | Los núcleos compartidos por Ollama y los competidores; la frecuencia fija | Mitigaciones de CPU informadas por `lscpu`; SMT activo |
| Kernel | Linux 7.0.0-43, scheduler EEVDF, cgroups v2 (`cpu`, `cpuset`) | `cpu.max`, `cpu.stat`, `cpuset.cpus`, `nice`, afinidad, espacios de nombres de Docker | Cuota, throttling, reparto de CPU entre tareas | Aislamiento por espacios de nombres y cgroups; `perf` restringido (`perf_event_paranoid` = 4) |
| Servicios | `dockerd`/containerd, systemd, Ollama (host y contenedor) | Cgroups gestionados por systemd (`system.slice/docker-<id>.scope`, `ollama.service`), publicación de puertos | Dónde se aplican los límites y qué cgroup se lee | Puertos 11434 y 11435 solo en loopback; SSH con clave (contraseña aún habilitada); sin firewall de host; `sudo -n` para operaciones privilegiadas |
| Aplicaciones | `llama-server` (12 hilos), `stress-ng`, scripts de medición | Procesos e hilos, `/proc`, `/sys`, sockets de loopback | TTFT, tokens/s, `cpu.stat`, `schedstat` | Sin autenticación en la API de Ollama; scripts ejecutados con privilegios |

Fuente: elaboración propia a partir de `experiments/env/environment.txt`, `experiments/run_matrix.py`, `experiments/run_protocol.py` y la verificación de solo lectura del servidor del 22 de noviembre de 2026 (sección 6.6).

## 6.2. Capa de hardware

El hardware es una PC dedicada con un AMD Ryzen 9 9900X de 12 núcleos y 24 CPUs lógicas, un único socket y un único nodo NUMA, con 29 GiB de RAM y 8 GiB de swap (`environment.txt`, líneas 37, 40, 55 y 79-80). El governor es `performance` y el boost está activo (líneas 83-86); el protocolo aborta si algún governor no es `performance` (`run_protocol.py`, líneas 317-319). El procesador informa virtualización AMD-V (`environment.txt`, línea 50), pero no se usa: el banco corre en Linux nativo y WSL2 es solo el cliente SSH (sección 7.1).

El mecanismo de hardware que más condiciona el diseño es la topología SMT. Los Experimentos 3 y 4 fijan el cpuset `6-11,18-23`, es decir, seis núcleos físicos con sus hilos hermanos, sin el núcleo 0 (`run_matrix.py`, línea 31; sección 5.5). Así, Ollama y los competidores comparten los mismos núcleos físicos, que es lo que el trabajo quiere evaluar. El hardware también aporta la medición térmica: `run_matrix.py` lee el sensor `k10temp` de `/sys/class/hwmon` (líneas 95-103) y la corrida completa registró entre 42,1 °C y 67,8 °C (sección 5.9).

En seguridad, el único dato documentado es el que informa `lscpu`: vulnerabilidades como Meltdown o Retbleed figuran «Not affected» y otras, como Spectre v2, con mitigación (`environment.txt`, líneas 57-75). No se evaluó si SMT activo es aceptable desde el punto de vista del aislamiento entre contenedores; se mantuvo porque es parte de la configuración que se estudia. Tampoco se documentan ajustes de firmware.

## 6.3. Capa del kernel

El kernel es Linux 7.0.0-43-generic con cgroups v2 (`stat -fc %T /sys/fs/cgroup` devuelve `cgroup2fs`) y los controladores `cpuset cpu io memory hugetlb pids rdma misc dmem` (`environment.txt`, líneas 17 y 20). El scheduler es EEVDF: `/sys/kernel/debug/sched/` expone `base_slice_ns` = 2 800 000 ns (2,8 ms) y no los parámetros de CFS (líneas 25-26). EEVDF es la implementación vigente de la clase *fair* y, según la documentación del kernel, reemplazó a CFS (The Linux Kernel documentation, s. f.-c); el capítulo 4 desarrolla esa diferencia.

**Grupos de control.** El kernel expone cgroups v2 como un sistema de archivos. El controlador `cpu` aporta `cpu.max` (cuota y período), `cpu.stat` (`nr_throttled`, `throttled_usec`, `usage_usec`) y `cpu.weight`; el controlador `cpuset` aporta `cpuset.cpus` (The Linux Kernel documentation, s. f.-b; Kerrisk, s. f.-b). El banco usa estas interfaces de la siguiente forma:

- Escribe la cuota con `docker update --cpus N`, que fija `cpu.max` (por ejemplo `200000 100000` para 2 CPUs), y la quita con `--cpu-quota -1`; el cpuset se fija con `--cpuset-cpus` (`run_matrix.py`, líneas 111-118). Después lee `cpu.max` y `cpuset.cpus` del cgroup y aborta si difieren de lo esperado (líneas 119-126). Esta verificación evitó la incidencia I2 (sección 7.4).
- Lee `cpu.stat` antes y después de cada pedido (`run_protocol.py`, líneas 129-140 y 262-275) y guarda `cpu.max` y `cpuset.cpus` en el `.meta.json` (líneas 344-346).
- Incorpora los competidores `stress-ng` al `cgroup.procs` del contenedor (`run_matrix.py`, líneas 177-183), porque con cgroups v2 el reparto es primero entre cgroups y luego entre procesos (sección 5.6).

**Interfaces de prioridad y afinidad.** Los scripts no invocan llamadas al sistema desde Python; delegan en utilidades que las ejercen:

- `nice -n` ajusta la prioridad de la clase *fair* de los competidores, lo que corresponde a la familia de llamadas descrita en `setpriority(2)` (Kerrisk, s. f.-g). Los pesos asociados son 1024, 110 y 15 para `nice` 0, 10 y 19 (sección 7.3).
- `taskset -c` fija la afinidad de CPU de cada competidor al cpuset de la condición, y `taskset -cp` la verifica a los 3 s (`run_matrix.py`, líneas 181 y 191). La afinidad y las políticas de planificación se describen en `sched(7)` (Kerrisk, s. f.-e).
- `chrt` asigna SCHED_FIFO o SCHED_RR en el Experimento 5, exploratorio, tanto a los competidores (`run_matrix.py`, línea 180) como a los hilos de `llama-server` (`run_protocol.py`, líneas 205-216); es una interfaz a las llamadas de `sched_setattr(2)` (Kerrisk, s. f.-f). Por indicación del docente queda fuera del alcance obligatorio y no integra los Experimentos 1 a 4.
- La política efectiva se lee del campo 41 de `/proc/<pid>/stat` (`run_matrix.py`, líneas 166-168; `run_protocol.py`, líneas 187-191), y el tiempo en cola por hilo, de `/proc/<pid>/task/<tid>/schedstat` (`sched_capture.py`, línea 49; The Linux Kernel documentation, s. f.-f).

Fuera de esas utilidades, las llamadas al sistema que usa el código Python son las de entrada y salida: `open` y lectura sobre `/sys` y `/proc`, sockets TCP hacia `127.0.0.1` con `http.client` (`run_protocol.py`, líneas 71 y 102) y creación de procesos con `subprocess`. `perf sched` y `pidstat` usan interfaces del kernel que no se inspeccionaron a ese nivel; solo se documenta que `perf` requiere `sudo` porque `perf_event_paranoid` vale 4 (sección 7.2, paso 4).

**Espacios de nombres.** Docker aísla cada contenedor con espacios de nombres del kernel y limita sus recursos con cgroups (Kerrisk, s. f.-b, s. f.-d); `clone(2)` es la llamada con la que se crean procesos en espacios de nombres nuevos (Kerrisk, s. f.-c). El repositorio no lista qué espacios de nombres usa `ollama-docker`, por lo que se asume la configuración por defecto de Docker, sin verificarla. Una consecuencia sí está documentada en el código: los competidores no se lanzan dentro del contenedor, sino que un `sh` del host, con `sudo`, escribe su PID en el `cgroup.procs` del contenedor (`run_matrix.py`, líneas 181-183). Pertenecen al cgroup del contenedor, y por eso comparten su cuota y su cpuset, pero no a sus espacios de nombres ni a su perfil de seguridad. Pertenecer a un cgroup y pertenecer a un espacio de nombres son relaciones independientes, y esa diferencia es una limitación del diseño (sección 6.6).

## 6.4. Capa de servicios

La capa de servicios es la que traduce las órdenes del usuario en configuración del kernel. Tiene tres componentes.

**Docker (`dockerd` y containerd).** Docker 29.10.0 usa cgroups v2 con el driver `systemd` (`docker info` informa `2/systemd`; `environment.txt`, líneas 92 y 95). Con ese driver, el cgroup del contenedor cuelga de la jerarquía de systemd como `system.slice/docker-<id>.scope`, que es la ruta que el banco resuelve con `docker inspect` (`run_matrix.py`, líneas 106-108; `run_protocol.py`, líneas 153-161). El demonio es el que escribe `cpu.max` y `cpuset.cpus` cuando el banco ejecuta `docker update`, según las opciones `--cpus` y `--cpuset-cpus` de las restricciones de recursos (Docker, s. f.-d). El contenedor se creó con `sudo docker run -d --name ollama-docker -p 127.0.0.1:11435:11434 -v ollama-docker-models:/root/.ollama ollama/ollama:latest`. No se pasó ningún dispositivo de GPU.

**systemd.** Gestiona la instancia de Ollama del host como `ollama.service`, con cgroup `system.slice/ollama.service` (`run_matrix.py`, línea 30). Esa instancia no tiene límites de CPU. systemd también deja el temporizador `sysstat-collect.timer`, que toma muestras cada unos 10 minutos y se identificó como fuente menor de ruido.

**Ollama.** Es el servidor que gestiona la carga del modelo, expone la API HTTP y lanza el motor de inferencia, `llama-server`. Hay dos instancias de la misma versión (0.40.16): el servicio del host en `127.0.0.1:11434` y el contenedor en `127.0.0.1:11435` (`environment.txt`, líneas 98 y 101). Se miden de a una: antes de cada serie, el protocolo descarga el modelo de la otra instancia (sección 7.2).

## 6.5. Capa de aplicaciones

**`llama-server`.** Es el proceso que calcula la inferencia. Arranca 12 hilos de cómputo (`n_threads = 12`). En el piloto se observó una caída de rendimiento al restringir las CPUs disponibles (I3) y también con un solo competidor de igual prioridad (I4, sección 7.4). La sincronización entre hilos podría amplificar el efecto de esas demoras, pero no se midieron las esperas en las barreras de `llama.cpp`.

**`stress-ng`.** Genera los competidores con `--cpu N --cpu-method matrixprod`, lanzados con `nice` y `taskset` (`run_matrix.py`, línea 181). Sus procesos se verifican a los 3 s, al final de cada condición y, durante la corrida completa, con el vigilante `watch_competitors.sh`, que los cuenta en `cgroup.procs` del contenedor cada 15 s (sección 5.6).

**Scripts de medición.** `run_matrix.py` orquesta las condiciones; `run_protocol.py` envía los pedidos a `/api/generate` por HTTP local y lee `cpu.stat`; `sched_capture.py` captura aparte `perf sched`, `pidstat` y `schedstat` (sección 7.1). Para llamar a Docker, `chrt` o `kill` usan `sudo -n` (`run_matrix.py`, líneas 107, 115 y 183; `run_protocol.py`, líneas 155 y 212). La opción `-n` hace que `sudo` falle en lugar de pedir contraseña, lo que implica que el usuario del banco puede ejecutar esas órdenes sin ingresarla. La configuración de `sudoers` no está documentada en el repositorio.

## 6.6. Seguridad por capa y limitaciones del laboratorio

La Tabla 6.2 contrasta lo que está documentado con lo que no se verificó.

**Tabla 6.2. Seguridad por capa: medidas documentadas y limitaciones.**

| Capa | Medida documentada | Limitación o punto no verificado |
|---|---|---|
| Hardware | `lscpu` informa mitigaciones de CPU activas (`environment.txt`, líneas 57-75) | SMT activo; no se evaluó su efecto en el aislamiento ni se documentó el firmware |
| Kernel | Cgroups v2 y espacios de nombres aíslan recursos y vista de procesos; `perf_event_paranoid` = 4 obliga a usar `sudo` para `perf` | Los competidores están en el cgroup del contenedor pero no en sus espacios de nombres; no se documentó el estado de seccomp, AppArmor ni userns |
| Servicios | Contenedor publicado en `127.0.0.1:11435` tras corregir una publicación en `0.0.0.0`; Ollama del host en `127.0.0.1:11434`, confirmado el 22/11/2026; SSH con clave | `dockerd` se ejecuta como root; el comando usa `sudo docker` y la imagen `ollama/ollama:latest` (etiqueta móvil); `ufw` inactivo (sin firewall de host); SSH con `PasswordAuthentication yes` |
| Aplicaciones | La API se consulta solo por loopback | La API de Ollama no tiene autenticación; los scripts usan `sudo -n` |

Fuente: elaboración propia a partir de `experiments/env/environment.txt`, de las incidencias de la sección 7.4 y de la verificación de solo lectura del servidor del 22 de noviembre de 2026.

**Medidas efectivamente aplicadas.** La más concreta es la exposición de red. `docker run -p 11435:11434` publicaba el puerto en `0.0.0.0` y se recreó con `-p 127.0.0.1:11435:11434` (incidencia de la sección 7.2, paso 5); la publicación por defecto de Docker abre el puerto en todas las interfaces y la API de Ollama no autentica. La instancia del host escucha en `127.0.0.1:11434`, coherente con el comportamiento por defecto de Ollama, que se cambia con una variable de entorno (Ollama, s. f.-a). Otras medidas son de integridad de la medición y no de seguridad: el protocolo aborta si no puede leer `cpu.stat` y los scripts escapan las rutas con `shlex.quote`.

**Acceso remoto y red: verificación del 22 de noviembre de 2026.** El acceso al equipo se hace por SSH desde la estación de trabajo con WSL2, con autenticación por clave. Para comprobar la configuración se hizo una consulta de solo lectura (`sshd -T`, `ufw status` y `ss -ltn`) el 22 de noviembre de 2026. Esa verificación describe la configuración vigente ese día, posterior al período de medición, y no la de las corridas. Resultados:

- **SSH:** puerto 22, `PubkeyAuthentication yes`, `PasswordAuthentication yes` (el acceso por contraseña sigue habilitado), `PermitRootLogin prohibit-password` y `KbdInteractiveAuthentication no`.
- **Firewall:** `ufw` figura inactivo, es decir, no hay firewall de host gestionado con `ufw`. nftables tiene reglas cargadas, probablemente las cadenas que crea Docker; no se analizaron.
- **Sockets en escucha:** SSH en `0.0.0.0:22` y `[::]:22`; Ollama del host en `127.0.0.1:11434` (solo loopback); el resolvedor local en `127.0.0.53:53` y `127.0.0.54:53`. El puerto 11435 del contenedor no estaba escuchando en ese momento porque el contenedor estaba detenido, de modo que su publicación en loopback se apoya en el comando de creación (sección 6.4) y no en esta consulta.

**Debilidades del laboratorio.** Se reconocen las siguientes:

1. **Privilegios.** Los scripts operan con `sudo -n`, y el demonio de Docker corre con privilegios de root. Un usuario con acceso a Docker tiene en la práctica control total del host (Docker, s. f.-b). El laboratorio es un equipo dedicado de una sola persona, de modo que el riesgo es bajo, pero no es una configuración endurecida.
2. **Aislamiento no verificado.** Docker aplica por defecto un perfil seccomp y reduce las *capabilities* del contenedor (Docker, s. f.-e, s. f.-f; Kerrisk, s. f.-a); entre las ausentes por defecto está `CAP_SYS_NICE` (Docker, s. f.-e), y en el banco la política de tiempo real del Experimento 5 se aplica desde el host con `sudo`. También existen perfiles de AppArmor (Docker, s. f.-a) y el remapeo de usuarios con `userns-remap` (Docker, s. f.-c), que no está activo por defecto. El repositorio no documenta que se hayan comprobado ni modificado: se asume la configuración por defecto, sin verificar. Sin remapeo de usuarios, el root del contenedor equivale a root en el host.
3. **Competidores fuera de las restricciones del contenedor.** Como se explicó en la sección 6.3, `stress-ng` corre como proceso del host dentro del cgroup, no bajo el perfil del contenedor. Es una decisión metodológica necesaria para que `nice` tenga efecto, no un modelo de vecinos aislados (sección 5.9).
4. **API sin autenticación y exposición.** Ollama no autentica; basta que el puerto se exponga para que cualquiera de la red local lo use. Se mitigó con loopback, y la verificación del 22 de noviembre de 2026 confirma que el Ollama del host solo escucha en `127.0.0.1`. Sin embargo, no hay firewall de host (`ufw` inactivo) y en el piloto el puerto del contenedor estuvo expuesto un tiempo. El equipo estuvo conectado a la red de un router doméstico.
5. **Imagen sin versión fija.** El contenedor usa `ollama/ollama:latest`. Aunque ambas instancias informaron la versión 0.40.16 (`environment.txt`, líneas 98 y 101), la etiqueta no garantiza reproducibilidad ni procedencia verificada de la imagen. No se documenta la verificación de firmas ni del *digest* de la imagen.
6. **Acceso remoto sin endurecer.** SSH acepta contraseña (`PasswordAuthentication yes`) además de clave, escucha en todas las interfaces (`0.0.0.0:22` y `[::]:22`) y el equipo no tiene firewall de host. Con el equipo en una red doméstica el riesgo es acotado, pero el acceso por contraseña permite ataques de adivinación que la autenticación solo por clave evitaría.
7. **Gestión de cambios sobre el sistema vivo.** `docker update` modifica los límites del contenedor en caliente y la restauración final depende de la ejecución limpia de los scripts; el diseño actual la garantiza incluso ante fallas (sección 7.6), pero la corrida original usó scripts previos a esa corrección (sección 7.6).

En síntesis, las políticas de seguridad del banco se orientan a que la medición sea válida y a que el servicio no quede expuesto, y no a un modelo de amenazas formal. Las capas de hardware y kernel dependen de los valores por defecto de Ubuntu y de Docker; la de servicios tiene una corrección documentada de exposición de red; la de aplicaciones carece de autenticación. Como mejora concreta y fundamentada, conviene deshabilitar `PasswordAuthentication` (la clave ya está configurada, de modo que no se pierde acceso) y activar un firewall de host restringido a la red local y al puerto SSH, por ejemplo con `ufw` en política de entrada denegada por defecto y una regla que admita el puerto 22 solo desde la red del laboratorio; así se reduce la superficie expuesta sin afectar las mediciones, que usan solo loopback. Un trabajo futuro puede además verificar y documentar seccomp, AppArmor y `userns-remap`, analizar las reglas de nftables que agrega Docker, y fijar la imagen por *digest*.
