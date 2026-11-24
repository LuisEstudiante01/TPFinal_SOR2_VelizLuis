# 11. Anexos

Los anexos reúnen el material de apoyo del desarrollo descrito en el capítulo 7: los prompts (Anexo A), extractos comentados del código fuente de los scripts de medición (Anexos B y C) y de análisis (Anexo D), y los pasos para reproducir el experimento (Anexo E). El código completo está en el directorio `experiments/` del repositorio del proyecto.

**Convención de los listados.** Las líneas que comienzan con `# [comentario]` fueron agregadas para este informe y explican cada paso; el resto es código copiado sin modificaciones del archivo indicado, y la fuente de cada listado indica sus líneas. Donde se omiten líneas intermedias se marca con un comentario `(…)`. Los comentarios originales del código están en inglés.

## Anexo A. Prompts utilizados

Todas las condiciones usan los mismos dos prompts, definidos en `run_protocol.py` (constantes `SHORT` y `LONG`). Se reproducen con su texto exacto, que se envía en inglés. A cada pedido se le antepone un identificador único con el formato `[request NNNN] ` (por ejemplo, `[request 0002] `) para impedir que Ollama reutilice la caché del prompt anterior (sección 5.3). El prompt corto tiene 47 tokens y el largo 516 (`prompt_eval_count` informado por Ollama).

**Listado A.1. Prompt corto (`SHORT`).**

> Explain what a CPU scheduler does in an operating system, and why fairness matters.

Fuente: experiments/run_protocol.py (línea 36).

**Listado A.2. Prompt largo (`LONG`).**

> Read the following passage about process scheduling and then follow the instruction at the end.
>
> A CPU scheduler is the part of an operating system kernel that decides which runnable task gets to use a processor core and for how long. Because there are usually many more runnable tasks than cores, the scheduler must divide processor time among them while keeping the system responsive. Early schedulers used simple policies such as first come first served or round robin with a fixed time slice. Modern general purpose kernels aim for something harder: they try to be fair, to keep latency low for interactive work, to use every core efficiently and to waste as little energy as possible, all at the same time. These goals often conflict, so every design is a compromise.
>
> For many years the Linux kernel used the Completely Fair Scheduler, usually called CFS. CFS keeps the runnable tasks in a red black tree ordered by virtual runtime, which is the amount of processor time a task has received scaled by its weight. The task with the smallest virtual runtime is always picked next, so tasks that have received less time are favoured. The weight comes from the nice value: a lower nice value gives a larger weight and therefore a larger share of the processor. To reduce latency, CFS also relied on a set of heuristics and tunable parameters, such as the minimum granularity and the wakeup preemption rules, which made its behaviour hard to reason about.
>
> Starting with kernel 6.6 the fair class uses EEVDF, which stands for Earliest Eligible Virtual Deadline First. Each task has a lag that measures how much service it is owed compared with an ideal fluid system. A task is eligible when its lag is not negative, and among the eligible tasks the scheduler picks the one with the earliest virtual deadline. Tasks that ask for shorter time slices receive earlier deadlines and so are served sooner, which gives latency sensitive work a principled way to get low delay without extra heuristics.
>
> Control groups add another layer. With cgroups version two, the cpu controller can limit a group of processes with cpu.max, which sets a quota of runtime allowed in every period. When the group uses up its quota before the period ends, its tasks are throttled until the next period starts, and the counters nr_throttled and throttled_usec in cpu.stat record how often and for how long that happened.
>
> Instruction: summarize the passage above in exactly three short bullet points.

Fuente: experiments/run_protocol.py (líneas 38-65; en el código el texto está dividido en cadenas literales consecutivas que Python concatena, y el prompt lleva saltos de línea entre párrafos).

**Listado A.3. Modelo, parámetros de inferencia e identificador de pedido.**

```python
# [comentario] Modelo único para todas las condiciones.
MODEL = "llama3.2:3b"
# [comentario] Parámetros de inferencia fijos: salida determinista (temperature 0, seed 1), 128 tokens y contexto de 4096.
OPTIONS = {"temperature": 0, "seed": 1, "num_predict": 128, "num_ctx": 4096}
# [comentario] (…) se omiten líneas que no son esenciales para este listado.
    # [comentario] Hasta dos intentos por pedido.
    for attempt in (1, 2):
        # [comentario] Un reintento usa otro identificador para no reutilizar la caché del prompt fallido.
        used = nonce if attempt == 1 else nonce + RETRY_NONCE_OFFSET
        # [comentario] Identificador único antepuesto al prompt: sin él, el TTFT del prompt largo caería casi a cero.
        prompt = "[request %04d] %s" % (used, PROMPTS[prompt_name])
```

Fuente: experiments/run_protocol.py (líneas 33-34, 263-265).

## Anexo B. Extractos comentados de `run_protocol.py`

`run_protocol.py` es el protocolo único de medición: fija modelo, prompts y parámetros y, para cada condición, separa la corrida en frío, el calentamiento y las corridas medidas. Los listados cubren la medición del TTFT con transmisión, la lectura de `cpu.stat` y la separación de la carga inicial.

**Listado B.1. Generación con transmisión y medición del TTFT.**

```python
def generate(port, prompt):
    """One streamed generation. Returns the final stats plus client-side timings."""
    # [comentario] Pedido con stream=True: Ollama envía un fragmento JSON por línea a medida que genera cada token.
    body = {"model": MODEL, "prompt": prompt, "stream": True, "keep_alive": "10m", "options": OPTIONS}
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=900)
    # [comentario] Reloj monotónico del cliente: el TTFT se mide desde antes de enviar el pedido.
    t0 = time.perf_counter()
    conn.request("POST", "/api/generate", json.dumps(body), {"Content-Type": "application/json"})
    resp = conn.getresponse()
    if resp.status != 200:
        raw = resp.read()
        conn.close()
        raise RuntimeError("HTTP %d from /api/generate: %s" % (resp.status, raw[:200]))
    # [comentario] ttft guardará el instante del primer token; final, el último fragmento (estadísticas del servidor).
    ttft, final = None, None
    while True:
        line = resp.readline()
        if not line:
            break
        if not line.strip():
            continue
        chunk = json.loads(line)
        # [comentario] TTFT = tiempo hasta el primer fragmento con texto (response no vacío), medido en el cliente.
        if ttft is None and chunk.get("response"):
            ttft = time.perf_counter() - t0
        # [comentario] El fragmento final (done) trae eval_count, eval_duration, load_duration, etc.
        if chunk.get("done"):
            final = chunk
    # [comentario] Tiempo total de pared del pedido, también medido en el cliente.
    wall = time.perf_counter() - t0
    conn.close()
    if final is None:
        raise RuntimeError("stream ended without a final chunk")
    return final, ttft, wall
```

Fuente: experiments/run_protocol.py (líneas 99-126).

**Listado B.2. Lectura de `cpu.stat` del cgroup.**

```python
def read_cpu_stat(cgroup):
    # [comentario] Tres contadores acumulativos de cpu.stat del cgroup medido: períodos limitados, tiempo limitado y CPU consumida.
    stat = {"nr_throttled": "", "throttled_usec": "", "usage_usec": ""}
    if not cgroup:
        return stat
    try:
        # [comentario] Cada línea de cpu.stat tiene la forma «clave valor»; se conservan solo las tres claves de interés.
        with open(os.path.join(cgroup, "cpu.stat")) as f:
            for line in f:
                key, _, val = line.partition(" ")
                if key in stat:
                    stat[key] = int(val)
    except OSError:
        pass
    return stat
```

Fuente: experiments/run_protocol.py (líneas 129-141).

**Listado B.3. Una corrida: `cpu.stat` antes y después del pedido.**

```python
def run_once(args, cgroup, writer, run_type, prompt_name, rep, nonce):
    for attempt in (1, 2):
        used = nonce if attempt == 1 else nonce + RETRY_NONCE_OFFSET
        prompt = "[request %04d] %s" % (used, PROMPTS[prompt_name])
        # [comentario] cpu.stat ANTES del pedido.
        before = read_cpu_stat(cgroup)
        try:
            # [comentario] Pedido con streaming (Listado B.1).
            final, ttft, wall = generate(args.port, prompt)
            break
        except (OSError, RuntimeError, ValueError) as exc:
            if attempt == 2:
                raise
            print("request failed (%s), retrying once with a new request id" % exc, flush=True)
            time.sleep(5)
    # [comentario] cpu.stat DESPUÉS del pedido: la diferencia de nr_throttled y throttled_usec es el throttling de esta corrida.
    after = read_cpu_stat(cgroup)
    # [comentario] Duración de la generación según el servidor, en segundos; tokens/s = eval_count / eval_s.
    eval_s = final.get("eval_duration", 0) / 1e9
    # [comentario] CPU consumida por todo el cgroup durante el pedido (diferencia de usage_usec).
    delta = (after["usage_usec"] - before["usage_usec"]) if before["usage_usec"] != "" and after["usage_usec"] != "" else ""
# [comentario] (…) se omiten líneas que no son esenciales para este listado.
    # [comentario] Una fila por corrida en el CSV (se vuelca de inmediato para no perder datos si la serie se interrumpe).
    writer.writerow(row)
    args.fh.flush()
```

Fuente: experiments/run_protocol.py (líneas 262-277, 292-293).

**Listado B.4. Descarga confirmada del modelo.**

```python
def unload(port, timeout=15):
    """Unload the model and wait until /api/ps confirms it (X3: the cold run needs a real load)."""
    # [comentario] keep_alive=0 pide a Ollama que descargue el modelo de la memoria.
    http_json(port, "POST", "/api/generate", {"model": MODEL, "keep_alive": 0, "stream": False})
    deadline = time.time() + timeout
    # [comentario] Se consulta /api/ps hasta confirmar que el modelo ya no está cargado: la corrida en frío necesita una carga real.
    while loaded_models(port):
        if time.time() > deadline:
            raise RuntimeError("model still loaded on port %d after unload" % port)
        time.sleep(0.5)
```

Fuente: experiments/run_protocol.py (líneas 82-89).

**Listado B.5. Secuencia de una serie: frío, calentamiento y corridas medidas.**

```python
    # [comentario] Se descarga el modelo antes de empezar la serie (separación de la carga inicial).
    unload(args.port)
    with open(base + ".csv", "w", newline="") as fh:
        args.fh = fh
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        writer.writeheader()
        # [comentario] Corrida en frío: incluye la carga del modelo; su load_s se informa aparte y no entra en las estadísticas.
        run_once(args, cgroup, writer, "cold", "short", 0, 0)
        # [comentario] Solo en el Exp 5: asigna política de tiempo real a los hilos del servidor de inferencia, que existe recién tras la corrida en frío.
        if args.runner_policy != "other":
            # the runner exists only after the cold run; warmup and measured runs use the new policy
            pid, threads = set_runner_policy(cgroup, args.runner_policy)
            print("llama-server %s: %d threads set to %s priority %d" % (
                pid, threads, POLICY_NAME[args.runner_policy], RT_PRIO), flush=True)
        # [comentario] Calentamiento: una corrida por prompt, descartada de las estadísticas.
        for name in PROMPTS:
            run_once(args, cgroup, writer, "warmup", name, 0, 1)
        # [comentario] El contador de identificadores continúa desde 2 (0 y 1 se usaron en las corridas en frío y de calentamiento).
        nonce = 2
        # [comentario] N corridas medidas por prompt, intercaladas corto/largo para repartir la deriva térmica.
        for rep in range(1, args.n + 1):
            for name in PROMPTS:
                # [comentario] Corrida medida (run_type = measured): es la única que usa el análisis.
                run_once(args, cgroup, writer, "measured", name, rep, nonce)
                nonce += 1
```

Fuente: experiments/run_protocol.py (líneas 357-374).

## Anexo C. Extractos comentados de `run_matrix.py`

`run_matrix.py` define la matriz de condiciones, configura el contenedor para cada una, lanza los competidores dentro de su cgroup, invoca el protocolo y deja todo restaurado.

**Listado C.1. Matriz de condiciones (Exp 1 a 4).**

```python
# [comentario] Los 24 hilos del procesador (12 núcleos con SMT) para los Exp 1 y 2.
ALL_CPUS = "0-23"
HOST_CGROUP = "/sys/fs/cgroup/system.slice/ollama.service"
# [comentario] Conjunto de 12 CPUs lógicas (núcleos 6 a 11 y sus hermanos SMT) para los Exp 3 y 4; evita el núcleo 0.
PINNED = "6-11,18-23"  # 6 physical cores = 12 logical CPUs (N and N+12 are SMT siblings), avoids core 0.
# [comentario] (…) se omiten líneas que no son esenciales para este listado.
# [comentario] Cada fila es una condición: nombre, experimento, destino, cuota en CPUs (None = sin límite), cpuset, competidores, su nice y N por prompt.
# name, experiment, target, cpus quota (None = no limit), cpuset, competitors, competitor nice, N
# N per condition (decision 2026-11-19, option A): 30 by default; 10 where Ollama
# collapses under competition (~0.5 tokens/s), otherwise one condition takes 5+ hours.
CONDITIONS = [
    ("exp1_host",            "exp1", "host",   None, ALL_CPUS, 0,  0,  30),
    ("exp1_docker",          "exp1", "docker", None, ALL_CPUS, 0,  0,  30),
    ("exp2_nolimit",         "exp2", "docker", None, ALL_CPUS, 0,  0,  30),
    ("exp2_cpus8",           "exp2", "docker", 8,    ALL_CPUS, 0,  0,  30),
    ("exp2_cpus4",           "exp2", "docker", 4,    ALL_CPUS, 0,  0,  30),
    ("exp2_cpus2",           "exp2", "docker", 2,    ALL_CPUS, 0,  0,  30),
    ("exp2_cpus1",           "exp2", "docker", 1,    ALL_CPUS, 0,  0,  30),
    ("exp3_comp0",           "exp3", "docker", None, PINNED,   0,  0,  30),
    ("exp3_comp1",           "exp3", "docker", None, PINNED,   1,  0,  30),
    ("exp3_comp2",           "exp3", "docker", None, PINNED,   2,  0,  10),
    ("exp3_comp3",           "exp3", "docker", None, PINNED,   3,  0,  10),
    ("exp4_nice0",           "exp4", "docker", None, PINNED,   12, 0,  10),
    ("exp4_nice10",          "exp4", "docker", None, PINNED,   12, 10, 30),
    ("exp4_nice19",          "exp4", "docker", None, PINNED,   12, 19, 30),
    # [comentario] Última condición del Exp 4: cuota de 2 CPUs con competidores en nice 19.
    ("exp4_nice19_cpus2",    "exp4", "docker", 2,    PINNED,   12, 19, 30),
# [comentario] (…) se omiten líneas que no son esenciales para este listado.
]
```

Fuente: experiments/run_matrix.py (líneas 29-31, 34-52 y 58).

**Listado C.2. Cuota y `cpuset` con `docker update`, y verificación en el cgroup.**

```python
def container_cgroup():
    # [comentario] Con el driver systemd, el cgroup del contenedor es system.slice/docker-<id>.scope.
    cid = sh(["sudo", "-n", "docker", "inspect", "-f", "{{.Id}}", CONTAINER])
    return "/sys/fs/cgroup/system.slice/docker-%s.scope" % cid


def configure_container(quota, cpuset):
    # Limits use --cpus (writes cpu.max). To REMOVE a limit, "--cpus 0" does not
    # work (cpu.max keeps the old quota); "--cpu-quota -1" does. cpu.max is
    # checked below, so a wrong state aborts the run.
    # [comentario] docker update escribe cpu.max y cpuset.cpus en el cgroup del contenedor.
    d = ["sudo", "-n", "docker", "update"]
    # [comentario] Primero se quita cualquier límite previo (--cpu-quota -1) y se fija el cpuset.
    sh(d + ["--cpu-quota", "-1", "--cpuset-cpus", cpuset, CONTAINER])
    # [comentario] --cpus N escribe cpu.max = N × 100000 con período de 100 ms.
    if quota:
        sh(d + ["--cpus", str(quota), CONTAINER])
    cg = container_cgroup()
    # [comentario] Se lee de vuelta lo que el kernel tiene realmente aplicado.
    cpu_max = read_text(os.path.join(cg, "cpu.max"))
    cpus = read_text(os.path.join(cg, "cpuset.cpus"))
    # [comentario] Valor esperado de cpu.max: «max 100000» sin límite o «cuota 100000».
    expected = "max 100000" if not quota else "%d 100000" % int(quota * 100000)
    # [comentario] Verificación: si el estado no coincide, se aborta en lugar de medir con una configuración equivocada.
    if cpu_max != expected:
        sys.exit("cpu.max is %r, expected %r" % (cpu_max, expected))
    if cpus != cpuset:
        sys.exit("cpuset.cpus is %r, expected %r" % (cpus, cpuset))
    return cg, cpu_max, cpus
```

Fuente: experiments/run_matrix.py (líneas 106-127).

**Listado C.3. Competidores con `nice`, `taskset` y `chrt` dentro del cgroup, y su verificación.**

```python
def count_workers(cg):
    # [comentario] Cuenta los trabajadores de stress-ng que están dentro del cgroup del contenedor (compara con cgroup.procs).
    workers = sh(["pgrep", "-x", "stress-ng-cpu"], check=False).split()
    in_cg = set(read_text(os.path.join(cg, "cgroup.procs")).split())
    return [p for p in workers if p in in_cg]
# [comentario] (…) se omiten líneas que no son esenciales para este listado.
def start_competitors(cg, count, nice, cpuset, policy="other"):
    # The shell joins the container cgroup first; stress-ng and its workers inherit it.
    # With a real-time policy, chrt runs first: the workers inherit SCHED_FIFO/SCHED_RR.
    # [comentario] Solo Exp 5: chrt va primero para que los trabajadores hereden SCHED_FIFO o SCHED_RR.
    chrt = "chrt %s %d " % (CHRT_FLAG[policy], RT_PRIO) if policy != "other" else ""
    # [comentario] La shell se une al cgroup del contenedor (echo $$ > cgroup.procs) y hace exec: nice fija la prioridad, taskset el cpuset y stress-ng lanza los trabajadores. Todos heredan cgroup, nice y afinidad.
    script = "echo $$ > %s && exec %snice -n %d taskset -c %s stress-ng --cpu %d --cpu-method matrixprod --quiet" % (
        shlex.quote(os.path.join(cg, "cgroup.procs")), chrt, nice, shlex.quote(cpuset), count)
    # [comentario] Se lanza con sudo en segundo plano.
    proc = subprocess.Popen(["sudo", "-n", "sh", "-c", script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # [comentario] Espera 3 s a que arranquen los trabajadores.
    time.sleep(3)
    # [comentario] Verificación 1: la cantidad de trabajadores dentro del cgroup debe ser la esperada.
    workers = count_workers(cg)
    if len(workers) != count:
        stop_competitors(cg, proc)
        raise CompetitorError("%d stress-ng workers in the container cgroup, expected %d" % (len(workers), count))
    for pid in workers:
        # [comentario] Verificación 2: nice real (ps) y afinidad real (taskset) de cada trabajador.
        ni = sh(["ps", "-o", "ni=", "-p", pid], check=False).strip()
        aff = sh(["taskset", "-cp", pid], check=False).rsplit(":", 1)[-1].strip()
        # [comentario] Con tiempo real, ps no informa nice: se verifica la política desde /proc.
        if policy != "other":
            # ps shows nice "-" for real-time tasks: check the policy instead
            pol = thread_policy(pid)
            if pol != POLICY_NAME[policy] or aff != cpuset:
                stop_competitors(cg, proc)
                raise CompetitorError("worker %s has policy=%s affinity=%s, expected policy=%s affinity=%s" % (
                    pid, pol, aff, POLICY_NAME[policy], cpuset))
            continue
        # [comentario] Si algún trabajador no tiene el nice o la afinidad esperados, se detienen los competidores y la condición falla.
        if ni != str(nice) or aff != cpuset:
            stop_competitors(cg, proc)
            raise CompetitorError("worker %s has nice=%s affinity=%s, expected nice=%d affinity=%s" % (
                pid, ni, aff, nice, cpuset))
    return proc
```

Fuente: experiments/run_matrix.py (líneas 140-143, 177-204).

**Listado C.4. Ciclo de una condición: configurar, competir, medir, verificar y restaurar.**

```python
    # [comentario] Al empezar se detiene cualquier stress-ng que haya quedado en el cgroup.
    stop_competitors()
    failed = []
    try:
        for i, (name, _exp, target, quota, cpuset, comp, nice, n) in enumerate(conds, 1):
            print("\n=== [%d/%d] %s === %s temp=%sC" % (i, len(conds), name, time.strftime("%H:%M:%S"), cpu_temp()), flush=True)
            # [comentario] Se aplican y verifican la cuota y el cpuset del contenedor (Listado C.2).
            cg, cpu_max, cpus = configure_container(quota, cpuset)
            print("container cpu.max=%s cpuset=%s" % (cpu_max, cpus), flush=True)
            proc = None
            comp_policy, runner_policy = policies(name)
            if comp:
                try:
                    # [comentario] Se lanzan y verifican los competidores (Listado C.3).
                    proc = start_competitors(cg, comp, nice, cpuset, comp_policy)
                # [comentario] Si no están como se esperaba, la condición se registra como fallida y se sigue con la siguiente.
                except CompetitorError as exc:
                    print("FAILED: %s (%s), continuing" % (name, exc), flush=True)
                    failed.append(name)
                    continue
                if comp_policy != "other":
                    print("started %d stress-ng workers, %s priority %d, in the container cgroup" % (
                        comp, POLICY_NAME[comp_policy], RT_PRIO), flush=True)
                else:
                    print("started %d stress-ng workers, nice %d, in the container cgroup" % (comp, nice), flush=True)
            # [comentario] Destino de la medición: Ollama del host (11434) o del contenedor (11435); la otra instancia se descarga.
            port, other = (HOST_PORT, DOCKER_PORT) if target == "host" else (DOCKER_PORT, HOST_PORT)
            measured_cg = HOST_CGROUP if target == "host" else cg
            # [comentario] El protocolo de medición (Anexo B) corre como proceso aparte para esta condición.
            res = subprocess.run([sys.executable, os.path.join(HERE, "run_protocol.py"), "--condition", name,
                                  "--port", str(port), "--other-port", str(other),
                                  "--n", str(args.n if args.n is not None else n),
                                  "--cgroup", measured_cg, "--competitors", str(comp), "--competitor-nice", str(nice),
                                  "--out", args.out] + rt_args(comp_policy, runner_policy))
# [comentario] (…) se omiten líneas que no son esenciales para este listado.
            # [comentario] Los competidores deben seguir vivos al terminar la condición; si no, la condición falla.
            alive = len(count_workers(cg)) if comp else 0
            # [comentario] Se detienen los competidores antes de pasar a la siguiente condición.
            stop_competitors(cg, proc)
            print("end %s %s temp=%sC competitors_alive=%d/%d" % (
                name, time.strftime("%H:%M:%S"), cpu_temp(), alive, comp), flush=True)
            # [comentario] Una condición fallida no detiene el resto de la corrida.
            if res.returncode != 0 or alive != comp:
                # keep going: one failed condition must not waste the rest of the night
                print("FAILED: %s (exit %d, competitors alive %d/%d), continuing" % (
                    name, res.returncode, alive, comp), flush=True)
                failed.append(name)
    # [comentario] Pase lo que pase, se detienen los competidores y se quitan los límites del contenedor.
    finally:
        try:
            stop_competitors()
        finally:
            # always remove the limits, even if the cleanup above failed
            configure_container(None, ALL_CPUS)
            print("\ncontainer restored to no limits", flush=True)
```

Fuente: experiments/run_matrix.py (líneas 236-263, 265-280).

## Anexo D. Extractos comentados del análisis (`analyze.py`)

`analyze.py` lee los CSV de las corridas `measured` y calcula las estadísticas por condición y prompt (media, desvío, CV, mediana, P95 e IC del 95 %) y las comparaciones contra la referencia de cada experimento (test t de Welch, U de Mann-Whitney, delta de Cliff y corrección de Holm-Bonferroni).

**Listado D.1. Carga de las corridas medidas y métricas derivadas.**

```python
        # [comentario] La carga en frío (load_s de la corrida cold) se guarda aparte.
        c = df[df.run_type == "cold"]
        cold[cond] = float(c.load_s.iloc[0]) if len(c) else np.nan
        # [comentario] Solo se analizan las corridas medidas con generación válida.
        m = df[(df.run_type == "measured") & (df.eval_s > 0)].copy()
        if m.empty:
            raise SystemExit("no valid measured rows in %s" % path)
        m["condition"] = cond
        m["experiment"] = cond.split("_")[0]
        # tokens/s from the raw columns: the CSV column is rounded to 2 decimals,
        # which hides the variability of the slow conditions (~0.47 tokens/s)
        # [comentario] tokens/s se recalcula con las columnas crudas porque el CSV lo redondea a 2 decimales.
        m["tokens_per_s"] = m.eval_count / m.eval_s
        # [comentario] Throttles de la corrida: diferencia de nr_throttled entre después y antes.
        m["throttles"] = m.nr_throttled_after - m.nr_throttled_before
        # [comentario] Tiempo throttleado de la corrida (de µs a ms).
        m["throttled_ms"] = (m.throttled_usec_after - m.throttled_usec_before) / 1000.0
        # [comentario] CPUs promedio usadas por el cgroup: CPU consumida / tiempo de pared.
        m["cpus_used"] = m.cpu_usec_delta / (m.wall_s * 1e6)
```

Fuente: experiments/analyze.py (líneas 63-75).

**Listado D.2. Estadística descriptiva por condición y prompt.**

```python
def describe(x):
    x = np.asarray(x, dtype=float)
    # [comentario] Media y desvío muestral (ddof = 1).
    n, mean, sd = len(x), x.mean(), x.std(ddof=1) if len(x) > 1 else 0.0
    # [comentario] Semiancho del IC del 95 % con la t de Student.
    half = stats.t.ppf(0.975, n - 1) * sd / np.sqrt(n) if n > 1 else np.nan
    # [comentario] CV = 100 × desvío / media; con N = 10 el P95 es casi el máximo.
    return {"n": n, "mean": mean, "sd": sd, "cv_pct": 100 * sd / mean if mean else np.nan,
            "median": np.median(x), "p5": np.percentile(x, 5), "p95": np.percentile(x, 95),
            "min": x.min(), "max": x.max(),
            "ci95_low": mean - half, "ci95_high": mean + half}
```

Fuente: experiments/analyze.py (líneas 83-90).

**Listado D.3. Delta de Cliff y corrección de Holm-Bonferroni.**

```python
def cliffs_delta(x, y):
    """Cliff's delta of y against x: P(y > x) - P(y < x), in [-1, 1] (effect size)."""
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    # [comentario] Pares (y, x) con y mayor que x.
    gt = (y[:, None] > x[None, :]).sum()
    # [comentario] Pares con y menor que x.
    lt = (y[:, None] < x[None, :]).sum()
    # [comentario] Delta de Cliff = P(y > x) − P(y < x), entre −1 y 1.
    return (gt - lt) / (len(x) * len(y))


def holm(pvalues):
    """Holm-Bonferroni adjusted p-values (same order as the input)."""
    p = np.asarray(pvalues, dtype=float)
    # [comentario] Holm: se ordenan los p de menor a mayor.
    order = np.argsort(p)
    adj = np.empty_like(p)
    running = 0.0
    for rank, i in enumerate(order):
        # [comentario] p ajustado = (m − rango) × p, forzado a ser creciente y con tope en 1.
        running = max(running, (len(p) - rank) * p[i])
        adj[i] = min(1.0, running)
    return adj
```

Fuente: experiments/analyze.py (líneas 112-129).

**Listado D.4. Comparaciones contra la referencia: Welch, Mann-Whitney, Cliff y Holm.**

```python
def compare(df):
    # [comentario] Cada condición contra la referencia de su experimento, más los pares adicionales.
    pairs = [(base, c) for exp, base in BASELINES.items()
             for c in ORDER if c.startswith(exp + "_") and c != base] + EXTRA_PAIRS
    present = set(df.condition)
    rows = []
    for a, b in pairs:
        if a not in present or b not in present:
            continue
        # [comentario] Por par, prompt y métrica (TTFT y tokens/s).
        for prompt in ("short", "long"):
            for col in METRICS:
                # [comentario] Muestras de la referencia (x) y de la condición (y).
                x = df[(df.condition == a) & (df.prompt == prompt)][col].astype(float)
                y = df[(df.condition == b) & (df.prompt == prompt)][col].astype(float)
                if len(x) < 2 or len(y) < 2 or x.mean() == 0:
                    continue
                rows.append({"baseline": a, "condition": b, "prompt": prompt, "metric": col,
                             "baseline_mean": x.mean(), "condition_mean": y.mean(),
                             # [comentario] Diferencia relativa de las medias.
                             "diff_pct": 100 * (y.mean() - x.mean()) / x.mean(),
                             # [comentario] t de Welch: no supone varianzas iguales.
                             "welch_p": stats.ttest_ind(x, y, equal_var=False).pvalue,
                             # [comentario] U de Mann-Whitney: no supone normalidad.
                             "mannwhitney_p": stats.mannwhitneyu(x, y).pvalue,
                             # [comentario] Tamaño del efecto.
                             "cliffs_delta": cliffs_delta(x, y)})
    out = pd.DataFrame(rows)
    if not out.empty:
        # correction for multiple comparisons over the whole family of tests
        # [comentario] Se ajustan ambos p sobre toda la familia de pruebas.
        out["welch_p_holm"] = holm(out.welch_p)
        out["mannwhitney_p_holm"] = holm(out.mannwhitney_p)
    return out
```

Fuente: experiments/analyze.py (líneas 132-157).

## Anexo E. Cómo reproducir el experimento

Los pasos suponen un equipo con Linux nativo, cgroups v2, Docker, Ollama en el host y en un contenedor, `stress-ng`, `perf`, `pidstat` y Python con pandas, scipy y matplotlib (capítulos 5 y 7). Los scripts se ejecutan desde el directorio `~/tp` del equipo de medición, que contiene los archivos de `experiments/`.

**Listado E.1. Secuencia de comandos.**

```bash
# 1. Verificar cgroups v2 (debe imprimir cgroup2fs) y fijar el governor
stat -fc %T /sys/fs/cgroup
sudo cpupower frequency-set -g performance

# 2. Contenedor de Ollama, publicado solo en loopback, sin GPU
sudo docker run -d --name ollama-docker -p 127.0.0.1:11435:11434 \
  -v ollama-docker-models:/root/.ollama ollama/ollama:latest

# 3. Descargar el modelo en ambas instancias (host y contenedor)
ollama pull llama3.2:3b
sudo docker exec ollama-docker ollama pull llama3.2:3b

# 4. Matriz de condiciones, dentro de tmux
cd ~/tp
tmux new -s night
python3 run_matrix.py --list                      # lista las condiciones
python3 run_matrix.py --n 1                       # piloto: una corrida medida por prompt
python3 run_matrix.py 2>&1 | tee ~/tp/night.log   # corrida completa (Exp 1 a 4)
python3 run_matrix.py --only exp5                 # opcional: políticas de tiempo real

# 5. Métricas del scheduler, en una corrida aparte (perf agrega carga)
python3 sched_capture.py --window 20 --out ~/tp/sched --raw ~/tp/sched_raw

# 6. Análisis estadístico
python3 analyze.py --results ~/tp/results --out ~/tp/analysis

# 7. Figuras del informe (entorno virtual aislado)
python3 -m venv /tmp/plotenv && /tmp/plotenv/bin/pip install matplotlib pandas numpy
/tmp/plotenv/bin/python experiments/plot_figures.py
```

Fuente: ejemplos de uso de `experiments/run_matrix.py`, `experiments/sched_capture.py`, `experiments/analyze.py` y `experiments/plot_figures.py`; el comando de `docker run` figura en la sección 6.4 y la descarga del modelo es la que exige el protocolo antes de medir (comprueba que `llama3.2:3b` esté instalado en el puerto indicado).
