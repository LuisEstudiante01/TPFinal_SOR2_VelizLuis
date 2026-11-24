const pptxgen = require("pptxgenjs");
const React = require("react");
const RDS = require("react-dom/server");
const sharp = require("sharp");
const si = require("react-icons/si");
const lu = require("react-icons/lu");
const pres = new pptxgen();
pres.layout = "LAYOUT_16x9"; // 10 x 5.625
pres.author = "Luis Veliz";
pres.company = "UNGS - Sistemas Operativos y Redes 2";
pres.subject = "Presentación oral del TP final de SOR2 (2026, 2.º semestre)";
pres.title = "Planificación de CPU en Linux: cuotas, competencia y prioridades en un LLM local";
pres.theme = { headFontFace: "Cambria", bodyFontFace: "Calibri" };

// Tema oscuro (proyector sobre pared blanca): fondo azul noche, texto claro, acentos saturados.
// Motivo visual: íconos dentro de círculos de color. El detalle va en las notas del orador.
const BG = "0F1E2A", CARD = "182C3B", CARD_LINE = "2A4558", STRONG = "1F4A66",
  TEXT = "F2F5F7", MUTED = "A9BAC6", PALE = "C9D7E0", GRID = "2A3F4F",
  TEAL = "2FA4BF", AMBER = "F2B45A", RED = "F06A5A", GREEN = "4CC38A", VIOLET = "A98BF0", GREY = "7D8E99", WHITE = "FFFFFF";
const HF = "Cambria", BF = "Calibri";

pres.defineSlideMaster({
  title: "MAIN", background: { color: BG },
  slideNumber: { x: 9.2, y: 5.25, w: 0.5, h: 0.25, fontFace: BF, fontSize: 10, color: MUTED, align: "right" },
  objects: [{ text: { text: "Planificación de CPU en Linux · SOR2 · 2026", options: { x: 0.5, y: 5.25, w: 5, h: 0.25, fontFace: BF, fontSize: 10, color: MUTED, margin: 0 } } }],
});
pres.defineSlideMaster({ title: "COVER", background: { color: BG } });

function title(s, t, sub) {
  s.addText(t, { x: 0.5, y: 0.3, w: 9, h: 0.65, fontFace: HF, fontSize: 30, bold: true, color: WHITE, margin: 0, valign: "middle", isTextBox: true });
  if (sub) s.addText(sub, { x: 0.5, y: 0.95, w: 9, h: 0.35, fontFace: BF, fontSize: 16, color: MUTED, margin: 0, isTextBox: true });
}
function card(s, x, y, w, h, fill = CARD, name) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: fill }, line: { color: fill === CARD ? CARD_LINE : fill, width: 0.75 }, objectName: name });
}
function txt(s, t, o) { s.addText(t, Object.assign({ fontFace: BF, fontSize: 14, color: TEXT, margin: 0, isTextBox: true }, o)); }
function arrow(s, x1, y, x2, color = MUTED) {
  s.addShape(pres.shapes.LINE, { x: x1, y, w: x2 - x1, h: 0, line: { color, width: 2, endArrowType: "triangle" } });
}
// Flecha diagonal de (x1, y1) a (x2, y2), con x2 > x1.
function diag(s, x1, y1, x2, y2, color = MUTED) {
  const up = y2 < y1;
  s.addShape(pres.shapes.LINE, { x: x1, y: Math.min(y1, y2), w: x2 - x1, h: Math.abs(y2 - y1), flipV: up, line: { color, width: 2, endArrowType: "triangle" } });
}
const iconCache = new Map();
async function png(Comp, color) {
  const key = Comp.name + color;
  if (!iconCache.has(key)) {
    const svg = RDS.renderToStaticMarkup(React.createElement(Comp, { color: "#" + color, size: "256" }));
    const buf = await sharp(Buffer.from(svg)).resize(256, 256).png().toBuffer();
    iconCache.set(key, "image/png;base64," + buf.toString("base64"));
  }
  return iconCache.get(key);
}
// Ícono oscuro dentro de un círculo de color (motivo de toda la presentación).
async function badge(s, Comp, x, y, d, fill, name, iconColor = BG) {
  s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fill }, line: { color: fill }, objectName: name });
  const k = d * 0.56;
  s.addImage({ data: await png(Comp, iconColor), x: x + (d - k) / 2, y: y + (d - k) / 2, w: k, h: k, altText: name, objectName: "Ícono " + name });
}
const chartBase = (extra) => Object.assign({
  catAxisLabelFontFace: BF, valAxisLabelFontFace: BF, dataLabelFontFace: BF,
  catAxisLabelFontSize: 12, valAxisLabelFontSize: 11, dataLabelFontSize: 13,
  catAxisLabelColor: TEXT, valAxisLabelColor: MUTED, dataLabelColor: TEXT,
  catAxisLineColor: GREY, valAxisLineShow: false,
  valGridLine: { color: GRID, size: 0.5 }, catGridLine: { style: "none" },
  showLegend: false, showValue: true, dataLabelFormatCode: "#,##0.00", dataLabelPosition: "outEnd",
  titleFontFace: BF, titleFontSize: 13, titleColor: MUTED, showTitle: true, barGapWidthPct: 45,
}, extra);

(async () => {

// 1 — Title
{
  const s = pres.addSlide({ masterName: "COVER" });
  for (let i = 0; i < 12; i++) {
    const c = i % 4, r = Math.floor(i / 4);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 6.9 + c * 0.7, y: 1.5 + r * 0.7, w: 0.55, h: 0.55, rectRadius: 0.08,
      fill: { color: i === 5 ? AMBER : TEAL }, line: { color: i === 5 ? AMBER : TEAL, width: 0.5 }, objectName: "Hilo " + (i + 1) });
  }
  txt(s, "12 hilos de un LLM repartiéndose la CPU", { x: 6.9, y: 4.3, w: 2.8, h: 0.5, fontSize: 12, color: MUTED });
  txt(s, "Planificación de CPU en Linux", { x: 0.6, y: 1.2, w: 6.2, h: 0.6, fontFace: HF, fontSize: 28, bold: true, color: WHITE });
  txt(s, "cuotas, competencia y prioridades en un LLM local", { x: 0.6, y: 1.9, w: 5.9, h: 1.0, fontFace: HF, fontSize: 24, color: AMBER, valign: "top" });
  txt(s, [
    { text: "Luis Veliz", options: { bold: true, breakLine: true } },
    { text: "Sistemas Operativos y Redes 2 · UNGS", options: { breakLine: true } },
    { text: "Segundo semestre 2026" },
  ], { x: 0.6, y: 3.6, w: 5.8, h: 1.1, fontSize: 16, color: PALE, valign: "top" });
  s.addNotes("Presentación del trabajo final de Sistemas Operativos y Redes 2 (Universidad Nacional de General Sarmiento, Instituto de Industria, Licenciatura en Sistemas; docente Benjamín Chuquimango). El tema: cómo el planificador de CPU de Linux (EEVDF) y los cgroups v2 afectan a un modelo de lenguaje que corre local con Ollama. Los doce cuadrados representan los 12 hilos que lanza Ollama; el resaltado es el hilo más lento, idea que se retoma en los resultados.");
}

// 2 — Question
{
  const s = pres.addSlide({ masterName: "MAIN" });
  title(s, "La pregunta", "¿Cuánto afectan las cuotas, la competencia y las prioridades de CPU a un LLM local?");
  const D = 0.95;
  await badge(s, lu.LuBrain, 0.85, 1.45, D, TEAL, "LLM local");
  txt(s, "LLM local", { x: 0.3, y: 2.43, w: 2.05, h: 0.35, fontSize: 16, bold: true, color: TEAL, align: "center" });
  await badge(s, lu.LuCog, 0.85, 2.95, D, RED, "Otras tareas");
  txt(s, "Otras tareas", { x: 0.3, y: 3.93, w: 2.05, h: 0.35, fontSize: 16, bold: true, color: RED, align: "center" });
  diag(s, 1.95, 1.92, 4.1, 2.4); diag(s, 1.95, 3.42, 4.1, 2.95);
  await badge(s, lu.LuCpu, 4.25, 1.9, 1.5, PALE, "CPU");
  txt(s, "Linux reparte", { x: 3.8, y: 3.47, w: 2.4, h: 0.35, fontSize: 16, bold: true, color: WHITE, align: "center" });
  diag(s, 5.9, 2.4, 7.2, 1.92); diag(s, 5.9, 2.95, 7.2, 3.42);
  await badge(s, lu.LuTimer, 7.35, 1.45, D, AMBER, "TTFT");
  txt(s, [{ text: "TTFT", options: { bold: true, color: AMBER, breakLine: true } }, { text: "primera palabra", options: { fontSize: 12, color: MUTED } }],
    { x: 8.35, y: 1.5, w: 1.4, h: 0.85, fontSize: 16, valign: "middle" });
  await badge(s, lu.LuGauge, 7.35, 2.95, D, GREEN, "tokens/s");
  txt(s, [{ text: "tokens/s", options: { bold: true, color: GREEN, breakLine: true } }, { text: "velocidad", options: { fontSize: 12, color: MUTED } }],
    { x: 8.35, y: 3.0, w: 1.4, h: 0.85, fontSize: 16, valign: "middle" });
  const hyp = [["H1", "Menos cuota → más latencia y menos velocidad", TEAL], ["H2", "Competir → más latencia y variabilidad", RED], ["H3", "nice reduce la interferencia, no compensa una cuota", GREEN]];
  hyp.forEach((h, i) => {
    const x = 0.5 + i * 3.05;
    card(s, x, 4.5, 2.9, 0.55, CARD, "Hipótesis " + h[0]);
    s.addShape(pres.shapes.OVAL, { x: x + 0.12, y: 4.56, w: 0.43, h: 0.43, fill: { color: h[2] }, line: { color: h[2] } });
    txt(s, h[0], { x: x + 0.12, y: 4.56, w: 0.43, h: 0.43, fontSize: 13, bold: true, color: BG, align: "center", valign: "middle" });
    txt(s, h[1], { x: x + 0.68, y: 4.5, w: 2.15, h: 0.55, fontSize: 12, valign: "middle" });
  });
  s.addNotes("La motivación: cada vez más gente corre un modelo de lenguaje en su propia máquina, que además hace otras cosas. Un LLM usa muchos hilos de CPU a la vez, y el sistema operativo tiene que repartirlos con el resto. Dos métricas cuentan la experiencia: el TTFT (time to first token), o sea cuánto esperás hasta ver la primera palabra, y los tokens por segundo, que es la velocidad con que sigue escribiendo. Estudié tres factores que Linux ofrece para repartir CPU: cuotas con cgroups, procesos competidores y prioridades con nice. Solo CPU, sin GPU, por decisión de alcance. Al pie están las tres hipótesis que guían el trabajo, y que se retoman con su veredicto en los resultados. H1: «La reducción de la cuota de CPU incrementa la latencia y disminuye el rendimiento de inferencia cuando se produce throttling.» H2: «La competencia por CPU incrementa la latencia y su variabilidad respecto de una ejecución sin competencia.» H3: «Ajustar la prioridad mediante nice puede reducir la interferencia de procesos competidores, pero no necesariamente compensar las limitaciones impuestas por una cuota estricta de CPU.» En pantalla figuran resumidas.");
}

// NEW — Por qué importa
{
  const s = pres.addSlide({ masterName: "MAIN" });
  title(s, "Por qué importa");
  const cols = [
    [lu.LuUsers, "51,1 %", "LLM locales comunes", "Ollama, encuesta Stack Overflow 2025", TEAL],
    [lu.LuShare2, "Sin tope", "Equipo compartido", "Docker no limita por defecto", AMBER],
    [lu.LuTrendingDown, "× 5", "Límites dañan latencia", "1 de 19 pods: latencia de cola", RED],
  ];
  for (let i = 0; i < cols.length; i++) {
    const c = cols[i], x = 0.5 + i * 3.1;
    card(s, x, 1.15, 2.85, 2.95, CARD, "Motivo " + (i + 1));
    await badge(s, c[0], x + 0.95, 1.3, 0.95, c[4], c[2]);
    txt(s, c[1], { x, y: 2.3, w: 2.85, h: 0.7, fontFace: HF, fontSize: 34, bold: true, color: c[4], align: "center", valign: "middle" });
    txt(s, c[2], { x: x + 0.1, y: 3.0, w: 2.65, h: 0.4, fontSize: 16, bold: true, color: WHITE, align: "center", valign: "middle" });
    txt(s, c[3], { x: x + 0.15, y: 3.4, w: 2.55, h: 0.55, fontSize: 12, color: MUTED, align: "center", valign: "top" });
  }
  card(s, 0.5, 4.3, 9.0, 0.8, STRONG, "Vacío");
  await badge(s, lu.LuSearch, 0.7, 4.4, 0.6, VIOLET, "Vacío");
  txt(s, [{ text: "El vacío: ", options: { bold: true, color: VIOLET } }, { text: "no encontré mediciones de cuota + rivales + nice en un LLM con CPU", options: { color: WHITE } }],
    { x: 1.5, y: 4.3, w: 7.9, h: 0.8, fontSize: 17, valign: "middle" });
  s.addNotes("Por qué vale la pena medir esto. Primero, correr un LLM en la propia máquina es común: en la encuesta de desarrolladores de Stack Overflow 2025, en la pregunta sobre herramientas para desarrollar agentes, 1920 de 3758 personas marcaron Ollama, el 51,1 %. Ojo: describe a quienes respondieron, no a toda la comunidad. Segundo, esos modelos rara vez corren en una máquina dedicada: comparten el equipo con otros procesos y cada vez más se empaquetan en contenedores, y Docker no impone límites de recursos por defecto; hay que pedirlos, y el kernel los aplica con cgroups. Tercero, hay evidencia de que los límites de CPU pueden dañar la latencia, aunque en otra carga: Shetty y colaboradores (2025) pusieron un límite a uno solo de los 19 pods de una aplicación de microservicios y la latencia de cola de extremo a extremo se multiplicó por cinco. Eso no es inferencia de LLM, es el motivo para sospechar. Abajo, el vacío: entre las fuentes que consulté no encontré una medición del efecto conjunto de cuotas de cgroups v2, competidores y nice sobre un LLM de Ollama en CPU. Eso no prueba que no exista literatura; delimita lo que este trabajo busca aportar.");
}

// NEW — Con qué trabajamos y por qué
{
  const s = pres.addSlide({ masterName: "MAIN" });
  title(s, "Con qué trabajamos y por qué");
  const cols = [
    [si.SiOllama, "Ollama", "llama3.2:3b", "Liviano: más repeticiones", TEAL],
    [lu.LuCpu, "Solo CPU", "sin GPU", "El scheduler reparte CPU", AMBER],
    [si.SiDocker, "Docker", "cuotas con cgroups", "Mismo kernel que el host", GREEN],
    [si.SiUbuntu, "Ubuntu Server 26.04", "kernel 7.0", "EEVDF y cgroups v2 nativos", VIOLET],
  ];
  const CW = 2.1;
  for (let i = 0; i < cols.length; i++) {
    const c = cols[i], x = 0.5 + i * (CW + 0.2);
    card(s, x, 1.2, CW, 3.7, CARD, "Elección " + (i + 1));
    await badge(s, c[0], x + (CW - 1.1) / 2, 1.4, 1.1, c[4], c[1]);
    txt(s, c[1], { x: x + 0.05, y: 2.65, w: CW - 0.1, h: 0.65, fontSize: 17, bold: true, color: WHITE, align: "center", valign: "middle" });
    txt(s, c[2], { x: x + 0.05, y: 3.3, w: CW - 0.1, h: 0.35, fontSize: 13, color: c[4], bold: true, align: "center", valign: "middle" });
    txt(s, c[3], { x: x + 0.15, y: 3.85, w: CW - 0.3, h: 0.85, fontSize: 15, color: PALE, align: "center", valign: "top" });
  }
  s.addNotes("Cuatro elecciones y la razón de cada una; la justificación completa, frente a sus alternativas, está en la Tabla 5.4 del informe. Uno: Ollama con el modelo llama3.2:3b. Ollama lo pide el objetivo general del trabajo, y además gestiona la carga del modelo, la API y los tiempos que alimentan las métricas. El modelo de 3 mil millones de parámetros, cuantizado, pesa unos 2 GB y anda en las decenas de tokens por segundo (unos 28 en una prueba de humo de 2 corridas), así que permite hacer más repeticiones; uno de 7 u 8 mil millones haría muy lentas las cuotas más estrictas, según una estimación mía. El trabajo mide latencia, no calidad de respuesta. Dos: solo CPU, por alcance: lo que estudio es cómo el scheduler reparte la CPU. Tres: Docker, porque el objetivo O1 pide compararlo y porque escribe los límites de cgroups con --cpus; como un contenedor comparte el kernel con el host, no es una máquina virtual. Cuatro: Ubuntu Server 26.04 con kernel 7.0, que trae EEVDF y cgroups v2 de forma nativa; todo en Linux nativo, sin máquina virtual.");
}

// 6 — Stack tecnológico: logos y nombres cortos
{
  const s = pres.addSlide({ masterName: "MAIN" });
  title(s, "Stack tecnológico");
  const cols = [
    ["Plataforma", TEAL, [[si.SiUbuntu, "Ubuntu 26.04"], [si.SiLinux, "Kernel 7.0"], [si.SiAmd, "Ryzen 9"]]],
    ["Inferencia", AMBER, [[si.SiOllama, "Ollama"], [si.SiMeta, "llama3.2:3b"]]],
    ["Control", GREEN, [[si.SiDocker, "Docker"], [lu.LuBoxes, "cgroups v2"], [lu.LuScale, "nice"]]],
    ["Carga y medición", RED, [[lu.LuFlame, "stress-ng"], [lu.LuActivity, "perf sched"], [lu.LuChartBar, "cpu.stat"]]],
    ["Análisis", TEAL, [[si.SiPython, "Python"], [si.SiPandas, "pandas"], [si.SiScipy, "SciPy"]]],
    ["Organización", AMBER, [[si.SiNotion, "Notion"], [si.SiObsidian, "Obsidian"]]],
    ["IA", VIOLET, [[si.SiClaude, "Claude Opus 5.5", "orquestador"], [si.SiGooglegemini, "Gemini 4 Neon", "auditor"], [lu.LuSparkles, "Gentle AI", "ecosistema"]]],
  ];
  const CW = 9.0 / cols.length, D = 0.66;
  for (let c = 0; c < cols.length; c++) {
    const [name, color, items] = cols[c];
    const x = 0.5 + c * CW;
    card(s, x + 0.04, 1.2, CW - 0.08, 3.9, CARD, "Columna " + name);
    txt(s, name, { x: x + 0.04, y: 1.28, w: CW - 0.08, h: 0.4, fontSize: 12, bold: true, color, align: "center", valign: "middle" });
    for (let k = 0; k < items.length; k++) {
      const [Comp, label, role] = items[k];
      const y = 1.8 + k * 1.1;
      await badge(s, Comp, x + (CW - D) / 2, y, D, color, label);
      txt(s, role ? [{ text: label, options: { breakLine: true } }, { text: role, options: { color, bold: true } }] : label,
        { x: x + 0.06, y: y + D + 0.04, w: CW - 0.12, h: role ? 0.42 : 0.26, fontSize: role ? 10 : 11, color: TEXT, align: "center", valign: "top" });
    }
  }
  s.addNotes("Este es el stack, de abajo hacia arriba. La plataforma es una PC dedicada con Ubuntu Server 26.04 LTS, kernel 7.0 con el scheduler EEVDF y un Ryzen 9 9900X de 12 núcleos; todo se midió en Linux nativo, sin máquina virtual. Para la inferencia usé Ollama 0.40.16 con el modelo llama3.2:3b cuantizado (Q4), solo CPU. Docker 29.10.0 aísla a Ollama y escribe los límites de cgroups v2 (cpu.max); nice ajusta la prioridad. La carga competidora la genera stress-ng 0.20.01 con matrixprod, fijado a las mismas CPUs. Para medir, la API de Ollama devuelve los tiempos con los que calculo TTFT y tokens por segundo, y cpu.stat, perf sched, pidstat y schedstat muestran lo que hace el kernel. El análisis está en Python con pandas, scipy y matplotlib. Para organizar el trabajo usé Notion para las tareas y Obsidian para las notas. Además trabajé con dos asistentes de IA con roles separados: Claude Opus 5.5 como orquestador, que ayuda a organizar las tareas y redacta borradores de código y texto que yo dirijo, reviso y apruebo, y Gemini 4 Neon como auditor, que solo lee y verifica que lo entregado cumpla la especificación, con evidencia. Los dos trabajaron dentro del ecosistema Gentle AI, que organiza el flujo de trabajo: tareas, agentes auxiliares, memoria entre sesiones y revisión. Las decisiones y las mediciones son mías. La justificación de cada elección frente a sus alternativas está en la Tabla 5.4 del informe.");
}

// 3 — EEVDF y nice
{
  const s = pres.addSlide({ masterName: "MAIN" });
  title(s, "La carrera por la CPU");
  // Cola de espera -> CPU
  for (let i = 0; i < 6; i++) {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.5 + i * 0.52, y: 1.5, w: 0.42, h: 0.42, rectRadius: 0.06, fill: { color: GREY }, line: { color: GREY, width: 0.5 }, objectName: "Hilo en cola " + (i + 1) });
  }
  txt(s, "cola de espera", { x: 0.5, y: 1.97, w: 3.1, h: 0.25, fontSize: 11, color: MUTED });
  arrow(s, 3.7, 1.71, 4.35);
  await badge(s, lu.LuCpu, 4.45, 1.38, 0.66, PALE, "CPU");
  txt(s, "Más hilos que CPUs: solo corren los que el scheduler elige. El resto espera.", { x: 5.35, y: 1.38, w: 4.15, h: 0.66, fontSize: 18, color: WHITE, valign: "middle" });

  const cols = [TEAL, AMBER, GREEN]; const names = ["A", "B", "C"];
  for (let i = 0; i < 9; i++) {
    s.addShape(pres.shapes.RECTANGLE, { x: 0.5 + i * 1.0, y: 2.45, w: 0.96, h: 0.5, fill: { color: cols[i % 3] }, line: { color: BG, width: 1 }, objectName: "Turno " + (i + 1) });
    txt(s, names[i % 3], { x: 0.5 + i * 1.0, y: 2.45, w: 0.96, h: 0.5, fontSize: 18, bold: true, color: BG, align: "center", valign: "middle" });
  }
  arrow(s, 0.5, 3.07, 9.48, GREY);
  txt(s, "turnos de ≈ 2,8 ms", { x: 0.5, y: 3.12, w: 9, h: 0.28, fontSize: 13, color: PALE });

  await badge(s, lu.LuScale, 0.6, 3.75, 1.0, AMBER, "nice como peso");
  txt(s, [{ text: "nice = peso", options: { fontSize: 24, bold: true, color: AMBER, breakLine: true } },
    { text: "más nice → menos CPU", options: { fontSize: 24, color: PALE } }],
    { x: 1.8, y: 3.75, w: 2.6, h: 1.0, valign: "middle" });

  card(s, 4.6, 3.5, 4.9, 1.65);
  txt(s, "CPU de Ollama frente a 12 rivales", { x: 4.8, y: 3.55, w: 4.5, h: 0.3, fontSize: 13, bold: true, color: WHITE });
  const share = [["rivales nice 0", 50, RED, "50 %"], ["rivales nice 10", 90, AMBER, "90 %"], ["rivales nice 19", 98.6, GREEN, "98,6 %"]];
  share.forEach((r, i) => {
    const y = 3.88 + i * 0.4, BW = 2.2, bw = BW * r[1] / 100;
    txt(s, r[0], { x: 4.8, y, w: 1.45, h: 0.34, fontSize: 13, color: PALE, valign: "middle" });
    s.addShape(pres.shapes.RECTANGLE, { x: 6.3, y: y + 0.04, w: BW, h: 0.26, fill: { color: GRID }, line: { color: GRID, width: 0.5 }, objectName: "Total " + r[0] });
    s.addShape(pres.shapes.RECTANGLE, { x: 6.3, y: y + 0.04, w: bw, h: 0.26, fill: { color: r[2] }, line: { color: r[2], width: 0.5 }, objectName: "Porción " + r[0] });
    txt(s, r[3], { x: 8.6, y, w: 0.85, h: 0.34, fontSize: 15, bold: true, valign: "middle" });
  });
  s.addNotes("Hay más hilos listos que CPUs, así que compiten: es una carrera por la CPU. El scheduler decide quién corre en cada momento y el resto espera en la cola de ejecución (los cuadrados grises). EEVDF (Earliest Eligible Virtual Deadline First) es el planificador de Linux desde el kernel 6.6, reemplazó a CFS. Cuando hay más tareas listas que CPUs, las turna con porciones cortas; en el equipo de medición la porción base es de 2,8 ms. El comando nice no da prioridad absoluta sino un peso: nice 0 pesa 1024, nice 10 pesa 110 y nice 19 pesa apenas 15. La CPU se reparte en proporción a esos pesos. Por eso, frente a 12 competidores con nice 0, a Ollama le toca la mitad (50 %); si los competidores pasan a nice 10, le toca el 90 %, y con nice 19, el 98,6 %. Esas cifras son la porción teórica y las verifiqué con capturas del scheduler. Más adelante se ve que el rendimiento real queda por debajo de esa porción.");
}

// NEW — Por qué EEVDF
{
  const s = pres.addSlide({ masterName: "MAIN" });
  title(s, "Por qué EEVDF", "Tres candidatos para repartir la CPU");
  const cols = [
    [lu.LuHistory, "CFS", GREY, "Solo teoría", ["Reemplazado por EEVDF en el kernel 6.6", "Medirlo exige otro kernel"], false],
    [lu.LuScale, "EEVDF", TEAL, "Elegido", ["Es el default de Ollama (SCHED_OTHER)", "Equitativo y compatible con cpu.max"], true],
    [lu.LuZap, "SCHED_FIFO / RR", AMBER, "Solo exploración", ["Tiempo real, sin equidad", "Rompen el reparto y cpu.max"], false],
  ];
  for (let i = 0; i < cols.length; i++) {
    const c = cols[i], x = 0.5 + i * 3.1, hl = c[5];
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.45, w: 2.85, h: 3.6, rectRadius: 0.12, fill: { color: hl ? STRONG : CARD }, line: { color: hl ? c[2] : CARD_LINE, width: hl ? 2.5 : 0.75 }, objectName: "Columna " + c[1] });
    await badge(s, c[0], x + 0.9, 1.65, 1.05, c[2], c[1]);
    txt(s, c[1], { x: x + 0.1, y: 2.85, w: 2.65, h: 0.45, fontSize: 19, bold: true, color: WHITE, align: "center", valign: "middle" });
    txt(s, c[3], { x: x + 0.1, y: 3.3, w: 2.65, h: 0.32, fontSize: 14, bold: true, color: c[2] === GREY ? PALE : c[2], align: "center", valign: "middle" });
    c[4].forEach((t, k) => txt(s, t, { x: x + 0.2, y: 3.75 + k * 0.62, w: 2.45, h: 0.55, fontSize: 13, color: PALE, align: "center", valign: "middle" }));
  }
  s.addNotes("Por qué EEVDF y no otro scheduler. Se argumenta en la sección 4.1.6 del informe. CFS, el planificador anterior, fue reemplazado por EEVDF desde el kernel 6.6; en el kernel 7.0 que uso ya no existe. Medir CFS exigiría otro kernel, 6.5 o anterior, y eso cambiaría a la vez el scheduler, los drivers y el resto del sistema: la comparación quedaría confundida. Por eso CFS lo trato solo en la teoría. EEVDF es lo que usa la inferencia en la práctica: Ollama corre por defecto con SCHED_OTHER, que es la clase normal, equitativa; reparte según el peso de nice y es compatible con el límite cpu.max de cgroups v2, que son justo las variables que estudio. SCHED_FIFO y SCHED_RR son políticas de tiempo real, pensadas para tareas con plazos estrictos: no son equitativas, no responden a nice y escapan a cpu.max. En una prueba exploratoria corta (Exp 5, N = 5 por prompt, sin tests de hipótesis) vi las dos cosas: con un competidor de tiempo real Ollama bajó a 0,48 a 0,61 tokens/s, contra 2,45 a 2,54 con un competidor normal; y con los hilos de Ollama en SCHED_RR, el contenedor limitado a 2 CPUs usó 12,01 CPUs y no tuvo ningún throttle. No digo que sean peores: para lo que fueron diseñados son la opción correcta, simplemente no encajan con la pregunta ni con las herramientas de control. Quedan como trabajo futuro, como recomendó el docente.");
}

// 4 — cgroups cpu.max
{
  const s = pres.addSlide({ masterName: "MAIN" });
  title(s, "El límite de CPU: cgroups v2", "cpu.max: un presupuesto que se recarga cada 100 ms");
  const steps = [
    [lu.LuBatteryFull, "Recarga", "200 ms de CPU", GREEN],
    [lu.LuFlame, "Gasto", "12 hilos a la vez", AMBER],
    [lu.LuOctagonX, "Frenado", "a los 16,7 ms", RED],
  ];
  for (let i = 0; i < steps.length; i++) {
    const st = steps[i], cx = 1.75 + i * 3.25;
    await badge(s, st[0], cx - 0.45, 1.4, 0.9, st[3], st[1]);
    txt(s, st[1], { x: cx - 1.4, y: 2.36, w: 2.8, h: 0.35, fontSize: 18, bold: true, color: st[3], align: "center" });
    txt(s, st[2], { x: cx - 1.4, y: 2.7, w: 2.8, h: 0.3, fontSize: 14, color: PALE, align: "center" });
    if (i < 2) arrow(s, cx + 0.65, 1.85, cx + 2.6);
  }
  const X0 = 0.5, W = 9.0, run = W * 16.7 / 100;
  s.addShape(pres.shapes.RECTANGLE, { x: X0, y: 3.3, w: run, h: 0.6, fill: { color: GREEN }, line: { color: GREEN }, objectName: "Corre" });
  s.addShape(pres.shapes.RECTANGLE, { x: X0 + run, y: 3.3, w: W - run, h: 0.6, fill: { color: RED }, line: { color: RED }, objectName: "Frenado" });
  txt(s, "corre", { x: X0, y: 3.3, w: run, h: 0.6, fontSize: 15, bold: true, color: BG, align: "center", valign: "middle" });
  txt(s, "frenado ≈ 83 ms, aunque haya CPUs libres", { x: X0 + run, y: 3.3, w: W - run, h: 0.6, fontSize: 15, bold: true, color: BG, align: "center", valign: "middle" });
  txt(s, "0", { x: X0, y: 3.95, w: 0.6, h: 0.25, fontSize: 11, color: MUTED });
  txt(s, "16,7 ms", { x: X0 + run - 0.4, y: 3.95, w: 0.8, h: 0.25, fontSize: 11, color: MUTED, align: "center" });
  txt(s, "100 ms", { x: X0 + W - 1.0, y: 3.95, w: 1.0, h: 0.25, fontSize: 11, color: MUTED, align: "right" });
  txt(s, "Throttling", { x: 4.45, y: 3.86, w: 5.0, h: 0.4, fontSize: 18, color: PALE }); // agregado por Luis en PowerPoint
  await badge(s, lu.LuCreditCard, 0.5, 4.4, 0.55, VIOLET, "Tarjeta prepaga");
  txt(s, "Una tarjeta prepaga que 12 hilos gastan a la vez", { x: 1.2, y: 4.4, w: 8.3, h: 0.55, fontSize: 16, color: WHITE, valign: "middle" });
  s.addNotes("Los cgroups v2 permiten limitar la CPU de un grupo de procesos con el archivo cpu.max: se define un presupuesto de tiempo de CPU por período de 100 ms. Una cuota de 2 CPUs equivale a 200 ms de CPU por período. El presupuesto es del grupo entero: como Ollama usa 12 hilos en paralelo, gasta 12 ms de CPU por cada milisegundo real y agota los 200 ms en unos 16,7 ms (200 / 12). Entonces el kernel frena al grupo completo (throttling) hasta que empieza el siguiente período, unos 83 ms después, aunque haya CPUs libres. La barra del medio está a escala. En las mediciones se vio exactamente eso: 10 throttles por segundo con cuotas de 4, 2 y 1 CPUs, y la demora máxima en cola llegó casi a 100 ms. Docker usa este mismo mecanismo para sus límites de CPU.");
}

// 5 — What I did
{
  const s = pres.addSlide({ masterName: "MAIN" });
  title(s, "Qué hice", "Un banco de pruebas, un único protocolo");
  const steps = [
    [lu.LuServer, "Ollama", "host y Docker", TEAL],
    [lu.LuSlidersHorizontal, "Condiciones", "cuota · rivales · nice", AMBER],
    [lu.LuTimer, "Medición", "TTFT · tokens/s", GREEN],
  ];
  for (let i = 0; i < steps.length; i++) {
    const st = steps[i], cx = 1.85 + i * 3.15;
    await badge(s, st[0], cx - 0.5, 1.45, 1.0, st[3], st[1]);
    txt(s, st[1], { x: cx - 1.4, y: 2.5, w: 2.8, h: 0.38, fontSize: 18, bold: true, color: WHITE, align: "center" });
    txt(s, st[2], { x: cx - 1.4, y: 2.88, w: 2.8, h: 0.3, fontSize: 14, color: MUTED, align: "center" });
    if (i < 2) arrow(s, cx + 0.7, 1.95, cx + 2.45);
  }
  const stats = [["780", "corridas"], ["15", "condiciones"], ["4", "experimentos"], ["10 h", "de mediciones"]];
  stats.forEach((st, i) => {
    const x = 0.5 + i * 2.27;
    txt(s, st[0], { x, y: 3.55, w: 2.2, h: 0.8, fontFace: HF, fontSize: 44, bold: true, color: AMBER, align: "center", valign: "middle" });
    txt(s, st[1], { x, y: 4.35, w: 2.2, h: 0.35, fontSize: 14, color: MUTED, align: "center" });
  });
  s.addNotes("El banco de pruebas corre en Ubuntu Server en Linux nativo (no una máquina virtual), con kernel 7.0.0-43-generic (scheduler EEVDF) y cgroups v2 (sistema de archivos cgroup2fs) y un procesador Ryzen 9 9900X de 12 núcleos, con el modelo llama3.2:3b. Un protocolo único fija modelo, prompts y parámetros (temperatura 0, semilla fija, 128 tokens), de modo que solo cambia la condición bajo prueba. Hay cuatro experimentos: O1 compara Ollama en el host con Ollama en Docker; O2 aplica cuotas de CPU; O3 agrega procesos competidores con stress-ng; y en el cuarto se varía el nice de los competidores. En total 15 condiciones y 780 corridas (12 condiciones con 30 repeticiones y 3 con 10, por dos prompts). Hay además un objetivo O4 que relaciona los resultados con cpu.stat y las métricas del scheduler, medido en corridas aparte. Las 780 corridas se midieron de un tirón, sin cortes entre condiciones: 10 h 15 min, de 06:55 a 17:09 UTC del 19 de noviembre (experiments/results/night.log). Sumando las pruebas exploratorias con SCHED_FIFO y SCHED_RR y las capturas del scheduler, las mediciones llegan a unas 13 horas.");
}

// 7 — O1
{
  const s = pres.addSlide({ masterName: "MAIN" });
  title(s, "O1: Docker rinde igual que el host");
  card(s, 0.5, 1.4, 4.1, 3.5, STRONG);
  await badge(s, si.SiLinux, 1.0, 1.7, 1.0, TEAL, "Host");
  txt(s, "=", { x: 2.0, y: 1.7, w: 1.1, h: 1.0, fontFace: HF, fontSize: 40, bold: true, color: WHITE, align: "center", valign: "middle" });
  await badge(s, si.SiDocker, 3.1, 1.7, 1.0, AMBER, "Docker");
  txt(s, "Host", { x: 0.75, y: 2.75, w: 1.5, h: 0.3, fontSize: 14, color: PALE, align: "center" });
  txt(s, "Docker", { x: 2.85, y: 2.75, w: 1.5, h: 0.3, fontSize: 14, color: PALE, align: "center" });
  txt(s, "< 1 %", { x: 0.5, y: 3.1, w: 4.1, h: 1.1, fontFace: HF, fontSize: 64, bold: true, color: AMBER, align: "center", valign: "middle" });
  txt(s, "de diferencia", { x: 0.5, y: 4.2, w: 4.1, h: 0.4, fontSize: 16, color: WHITE, align: "center" });
  s.addChart(pres.charts.BAR, [{ name: "tokens/s", labels: ["Host", "Docker"], values: [26.84, 26.81] }],
    chartBase({ x: 4.9, y: 1.4, w: 4.6, h: 3.5, barDir: "col", chartColors: [TEAL, AMBER], valAxisMinVal: 0, valAxisMaxVal: 35, valAxisMajorUnit: 5,
      title: "Tokens/s (prompt largo, sin límites)", dataLabelFormatCode: "#,##0.00" }));
  s.addNotes("Primer objetivo: ¿cuesta CPU correr Ollama dentro de Docker? Sin límites, no. En el prompt largo, el host rindió 26,84 tokens/s y Docker 26,81; el TTFT fue 0,950 s contra 0,957 s. La diferencia es menor al 1 % (−0,1 % a +0,7 %). Es lo esperado: un contenedor no es una máquina virtual, son procesos del mismo kernel aislados con namespaces y limitados con cgroups. El costo de Docker aparece en otras capas (red, disco, arranque), que esta medición no ejercita. Esto justifica usar el contenedor, porque ahí se pueden imponer cuotas con docker update.");
}

// 8 — O2 quota
{
  const s = pres.addSlide({ masterName: "MAIN" });
  title(s, "O2: la cuota se paga en velocidad");
  s.addChart(pres.charts.BAR, [{ name: "tokens/s", labels: ["Sin límite", "8 CPUs", "4 CPUs", "2 CPUs", "1 CPU"], values: [26.78, 17.28, 8.26, 3.61, 1.77] }],
    chartBase({ x: 0.5, y: 1.4, w: 6.0, h: 3.6, barDir: "col", chartColors: [GREY, TEAL, TEAL, TEAL, TEAL], valAxisMinVal: 0, valAxisMaxVal: 30, valAxisMajorUnit: 10,
      title: "Tokens/s según la cuota (prompt largo)" }));
  card(s, 6.8, 1.4, 2.7, 1.6, STRONG);
  txt(s, "÷ 2", { x: 6.8, y: 1.5, w: 2.7, h: 0.9, fontFace: HF, fontSize: 54, bold: true, color: AMBER, align: "center", valign: "middle" });
  txt(s, "media cuota, media velocidad", { x: 6.9, y: 2.4, w: 2.5, h: 0.5, fontSize: 13, color: WHITE, align: "center", valign: "top" });
  card(s, 6.8, 3.2, 2.7, 1.8);
  txt(s, "−93 %", { x: 6.8, y: 3.3, w: 2.7, h: 0.8, fontFace: HF, fontSize: 40, bold: true, color: RED, align: "center", valign: "middle" });
  txt(s, "con 1 CPU", { x: 6.9, y: 4.1, w: 2.5, h: 0.35, fontSize: 14, color: TEXT, align: "center" });
  txt(s, "TTFT × 16", { x: 6.9, y: 4.45, w: 2.5, h: 0.35, fontSize: 14, bold: true, color: AMBER, align: "center" });
  s.addNotes("Segundo objetivo: cuotas de CPU con cgroups v2. Prompt largo: sin límite 26,78 tokens/s; con 8 CPUs 17,28; con 4, 8,26; con 2, 3,61; y con 1 CPU, 1,77. Cada vez que la cuota se reduce a la mitad, la velocidad cae más o menos a la mitad y el TTFT largo aproximadamente se duplica (de 0,952 s a 15,125 s con 1 CPU). La cuota se cumple de forma exacta (el cgroup consumió 8,00, 4,00, 2,00 y 1,00 CPUs). La caída es incluso algo peor que proporcional: por CPU usada se pasa de 2,23 a 1,77 tokens/s. Hipótesis, no aislada experimentalmente: los 12 hilos se sincronizan en cada paso, así que cuando el throttling frena a uno, los demás esperan y desperdician su parte de la cuota. Se confirma la hipótesis H1. Nota: los decimales del gráfico se muestran con la configuración regional de quien abra el archivo.");
}

// 9 — O3 competition
{
  const s = pres.addSlide({ masterName: "MAIN" });
  title(s, "O3: un solo rival hunde el rendimiento");
  s.addChart(pres.charts.BAR, [{ name: "tokens/s", labels: ["0", "1", "2 (N = 10)", "3 (N = 10)"], values: [23.74, 2.45, 0.74, 0.53] }],
    chartBase({ x: 0.5, y: 1.4, w: 4.5, h: 3.6, barDir: "col", chartColors: [GREY, RED, RED, RED], valAxisMinVal: 0, valAxisMaxVal: 28, valAxisMajorUnit: 7,
      title: "Tokens/s según nº de rivales (prompt largo)" }));
  await badge(s, lu.LuUsers, 5.3, 1.45, 0.85, RED, "Un rival");
  txt(s, "−90 %", { x: 6.3, y: 1.35, w: 3.2, h: 1.05, fontFace: HF, fontSize: 60, bold: true, color: RED, valign: "middle" });
  card(s, 5.3, 2.7, 4.2, 2.3);
  txt(s, "Cada paso espera al hilo más lento", { x: 5.5, y: 2.8, w: 3.85, h: 0.3, fontSize: 14, bold: true, color: WHITE });
  txt(s, "hipótesis", { x: 5.5, y: 3.1, w: 3.85, h: 0.25, fontSize: 11, color: MUTED });
  for (let i = 0; i < 4; i++) {
    const y = 3.5 + i * 0.32, slow = i === 3;
    s.addShape(pres.shapes.RECTANGLE, { x: 5.5, y, w: slow ? 2.4 : 1.2, h: 0.22, fill: { color: slow ? RED : TEAL }, line: { color: slow ? RED : TEAL }, objectName: "Hilo " + (i + 1) });
    if (!slow) s.addShape(pres.shapes.RECTANGLE, { x: 6.7, y, w: 1.2, h: 0.22, fill: { color: CARD }, line: { color: GREY, width: 0.75, dashType: "dash" }, objectName: "Espera " + (i + 1) });
  }
  txt(s, "espera", { x: 6.7, y: 3.5, w: 1.2, h: 0.22, fontSize: 10, color: MUTED, align: "center", valign: "middle" });
  s.addShape(pres.shapes.LINE, { x: 7.95, y: 3.45, w: 0, h: 1.3, line: { color: PALE, width: 1.5, dashType: "dash" } });
  txt(s, "siguiente paso", { x: 8.05, y: 3.95, w: 1.4, h: 0.5, fontSize: 11, color: MUTED });
  s.addNotes("Tercer objetivo: competencia. Se lanzan procesos stress-ng en las mismas CPUs de Ollama, con igual prioridad. Prompt largo: sin competidores 23,74 tokens/s; con 1, 2,45; con 2, 0,74; con 3, 0,53. O sea −89,7 %, −96,9 % y −97,8 %. Lo llamativo es que con un solo competidor los hilos de Ollama esperan en cola solo el 7,7 % del tiempo y aun así el rendimiento cae 90 %. Hipótesis: en cada paso de la generación los 12 hilos tienen que sincronizarse y esperan al más lento; basta que un hilo comparta CPU con el competidor para frenar a los otros 11. Es una inferencia coherente con los datos, no un resultado experimental: no se varió el número de hilos (queda como trabajo futuro). Se confirma H2, con un efecto mayor al esperado. Las condiciones con 2 y 3 competidores tienen N = 10.");
}

// 10 — nice
{
  const s = pres.addSlide({ masterName: "MAIN" });
  title(s, "O3: nice ayuda, pero la cuota manda");
  s.addChart(pres.charts.BAR, [{ name: "tokens/s", labels: ["nice 0 (N = 10)", "nice 10", "nice 19", "nice 19 + 2 CPUs", "Sin rivales"], values: [0.47, 9.53, 20.59, 2.83, 23.74] }],
    chartBase({ x: 0.5, y: 1.4, w: 6.2, h: 3.6, barDir: "col", chartColors: [RED, AMBER, GREEN, TEAL, GREY], valAxisMinVal: 0, valAxisMaxVal: 28, valAxisMajorUnit: 7,
      title: "Tokens/s con 12 rivales según su nice (prompt largo)", catAxisLabelFontSize: 11 }));
  card(s, 7.0, 1.4, 2.5, 1.65);
  await badge(s, lu.LuScale, 7.95, 1.5, 0.6, GREEN, "nice");
  txt(s, "0,47 → 20,59", { x: 7.0, y: 2.15, w: 2.5, h: 0.5, fontFace: HF, fontSize: 24, bold: true, color: GREEN, align: "center", valign: "middle" });
  txt(s, "tokens/s", { x: 7.0, y: 2.65, w: 2.5, h: 0.3, fontSize: 13, color: PALE, align: "center" });
  card(s, 7.0, 3.25, 2.5, 1.75, STRONG);
  await badge(s, lu.LuBatteryFull, 7.95, 3.35, 0.6, AMBER, "Cuota");
  txt(s, "2,83", { x: 7.0, y: 4.0, w: 2.5, h: 0.55, fontFace: HF, fontSize: 32, bold: true, color: AMBER, align: "center", valign: "middle" });
  txt(s, "nice 19 + 2 CPUs", { x: 7.0, y: 4.55, w: 2.5, h: 0.3, fontSize: 13, color: WHITE, align: "center" });
  s.addNotes("Cuarto experimento: hay 12 competidores y se varía su nice (Ollama queda en nice 0). Prompt largo: con nice 0 Ollama rinde 0,47 tokens/s, con nice 10 9,53 y con nice 19 20,59, contra 23,74 sin competencia (recupera el 87 %). Los pesos del kernel (1024, 110, 15) explican el reparto de CPU, pero el rendimiento es mucho menor que la porción teórica: con nice 0 tiene la mitad de la CPU y rinde apenas el 2 %. Eso es coherente con la hipótesis de sincronización: un scheduler justo no garantiza buen rendimiento a hilos fuertemente acoplados. Cuando se agrega una cuota estricta de 2 CPUs a nice 19, Ollama rinde 2,83 tokens/s, menos que con la misma cuota sin competidores (3,61): el límite se aplica al cgroup completo y la prioridad solo reparte lo que queda adentro. Se confirma H3 en sus dos partes. Ojo con lo que muestra el gráfico: son medias. En la condición de nice 19 con 2 CPUs la media es 2,83 tokens/s y la mediana 2,93, ambas menores que los 3,61 de la misma cuota sin competidores, así que H3 se sostiene aunque hubo tres episodios de bloqueo muy largos en esa condición, cuya causa no está demostrada. Aclaración: la condición nice 0 tiene N = 10 corridas, no 30.");
}

// 11 — O4 scheduler
{
  const s = pres.addSlide({ masterName: "MAIN" });
  title(s, "O4: el scheduler muestra el mecanismo");
  s.addChart(pres.charts.BAR, [{ name: "% del tiempo", labels: ["Sin límite", "4 CPUs", "2 CPUs", "1 CPU", "1 rival", "nice 19 + 2 CPUs"], values: [0.0, 66.7, 83.4, 91.7, 7.7, 88.9] }],
    chartBase({ x: 0.5, y: 1.4, w: 6.2, h: 3.6, barDir: "col", chartColors: [GREY, TEAL, TEAL, TEAL, RED, TEAL], valAxisMinVal: 0, valAxisMaxVal: 100, valAxisMajorUnit: 25,
      title: "% del tiempo esperando en cola (prompt largo)", dataLabelFormatCode: "#,##0.0", catAxisLabelFontSize: 11 }));
  card(s, 7.0, 1.4, 2.5, 1.65, STRONG);
  await badge(s, lu.LuOctagonX, 7.95, 1.5, 0.6, AMBER, "Throttles");
  txt(s, "10 / s", { x: 7.0, y: 2.15, w: 2.5, h: 0.5, fontFace: HF, fontSize: 28, bold: true, color: AMBER, align: "center", valign: "middle" });
  txt(s, "frenadas con cuota", { x: 7.0, y: 2.65, w: 2.5, h: 0.3, fontSize: 13, color: WHITE, align: "center" });
  card(s, 7.0, 3.25, 2.5, 1.75);
  await badge(s, lu.LuUsers, 7.95, 3.35, 0.6, RED, "Un rival");
  txt(s, "7,7 %", { x: 7.0, y: 4.0, w: 2.5, h: 0.55, fontFace: HF, fontSize: 28, bold: true, color: RED, align: "center", valign: "middle" });
  txt(s, "de espera, pero −90 %", { x: 7.0, y: 4.55, w: 2.5, h: 0.3, fontSize: 13, color: TEXT, align: "center" });
  s.addNotes("Cuarto objetivo: relacionar los resultados con lo que ve el kernel. Se midió, en ventanas de 20 segundos con el prompt largo, el archivo cpu.stat del cgroup y las capturas del scheduler (perf sched). Con cuotas de 4, 2 y 1 CPUs ocurren 10 throttles por segundo, uno por período de 100 ms, y los hilos de Ollama pasan 66,7 %, 83,4 % y 91,7 % del tiempo esperando en cola, con demoras máximas de hasta 94,6 ms, casi un período completo. Sin límite la espera es 0,0 %. Con nice 19 y cuota de 2 CPUs la espera es 88,9 %. El caso llamativo es el de un solo competidor: la espera es de apenas 7,7 % y sin throttling, pero el rendimiento cae 90 %, lo que respalda la hipótesis de que los hilos se esperan entre sí. Valores de las Tablas 8.3 y 8.5 del informe.");
}

// 12 — Conclusions
{
  const s = pres.addSlide({ masterName: "COVER" });
  txt(s, "Conclusiones", { x: 0.5, y: 0.35, w: 9, h: 0.7, fontFace: HF, fontSize: 34, bold: true, color: WHITE });
  const items = [
    [si.SiDocker, "≈ 0 %", "El contenedor no cuesta CPU", GREEN],
    [lu.LuBatteryFull, "÷ N", "La cuota es exacta y manda", AMBER],
    [lu.LuUsers, "−90 %", "Competir pesa más; nice ayuda", RED],
  ];
  for (let i = 0; i < items.length; i++) {
    const it = items[i], x = 0.5 + i * 3.1;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.25, w: 2.85, h: 2.95, rectRadius: 0.12, fill: { color: CARD }, line: { color: CARD_LINE, width: 0.75 }, objectName: "Conclusión " + (i + 1) });
    await badge(s, it[0], x + 1.0, 1.4, 0.85, it[3], "Conclusión " + (i + 1));
    txt(s, it[1], { x, y: 2.3, w: 2.85, h: 0.8, fontFace: HF, fontSize: 40, bold: true, color: it[3], align: "center", valign: "middle" });
    txt(s, it[2], { x: x + 0.2, y: 3.15, w: 2.45, h: 0.85, fontSize: 17, bold: true, color: WHITE, align: "center", valign: "top" });
  }
  const verdicts = [["O1", "cumplido", GREEN], ["H1", "confirmada", AMBER], ["H2 y H3", "confirmadas", RED]];
  verdicts.forEach((v, i) => {
    const x = 0.5 + i * 3.1;
    card(s, x, 4.3, 2.85, 0.48, CARD, "Veredicto " + v[0]);
    s.addShape(pres.shapes.OVAL, { x: x + 0.1, y: 4.35, w: 0.38, h: 0.38, fill: { color: v[2] }, line: { color: v[2] } });
    txt(s, "✓", { x: x + 0.1, y: 4.35, w: 0.38, h: 0.38, fontSize: 14, bold: true, color: BG, align: "center", valign: "middle" });
    txt(s, [{ text: v[0] + " ", options: { bold: true, color: v[2] } }, { text: v[1] }], { x: x + 0.58, y: 4.3, w: 2.2, h: 0.48, fontSize: 13, valign: "middle" });
  });
  txt(s, "¿Preguntas?", { x: 0.5, y: 4.88, w: 9, h: 0.4, fontSize: 16, color: AMBER, align: "center" });
  s.addNotes("Tres ideas para llevarse. Una: los contenedores no cuestan CPU; Docker y el host son equivalentes (diferencia menor al 1 %). Dos: la cuota de cgroups se cumple con precisión, pero es proporcional (y algo peor, por la sincronización de los hilos), y manda por sobre cualquier prioridad. Tres: la competencia por CPU, incluso de un solo proceso, pesa mucho más de lo esperado porque los hilos del LLM se esperan entre sí; nice ayuda mucho (de 0,47 a 20,59 tokens/s) pero no supera una cuota estricta. Limitaciones: una máquina, un modelo, una configuración de hilos, y N = 10 en tres condiciones; la explicación por sincronización es una hipótesis que queda por probar variando el número de hilos. Se confirmaron las tres hipótesis H1, H2 y H3 del trabajo.");
}

// Post-proceso: ids únicos por diapositiva, metadatos y Content_Types sin masters inexistentes
const JSZip = require("jszip");
const fs = require("fs");
const OUT = "TPFinal_SOR2_2026_2s_VelizLuis_presentacion.pptx";
await pres.writeFile({ fileName: OUT });
const zip = await JSZip.loadAsync(fs.readFileSync(OUT));
for (const name of Object.keys(zip.files)) {
  if (/^ppt\/slides\/slide\d+\.xml$/.test(name)) {
    let xml = await zip.file(name).async("string");
    const used = new Set(); let next = 1000;
    xml = xml.replace(/(<p:cNvPr\b[^>]*?\bid=")(\d+)(")/g, (m, a, id, b) => {
      if (!used.has(id)) { used.add(id); return m; }
      while (used.has(String(next))) next++;
      used.add(String(next)); return a + next + b;
    });
    zip.file(name, xml);
  }
}
const files = new Set(Object.keys(zip.files));
let ct = await zip.file("[Content_Types].xml").async("string");
ct = ct.replace(/<Override\b[^>]*PartName="(\/[^"]+)"[^>]*\/>/g, (m, part) => files.has(part.slice(1)) ? m : "");
zip.file("[Content_Types].xml", ct);
const flat = new JSZip(); // sin entradas de carpeta
for (const n of Object.keys(zip.files)) if (!zip.files[n].dir) flat.file(n, await zip.file(n).async("nodebuffer"), { createFolders: false });
fs.writeFileSync(OUT, await flat.generateAsync({ type: "nodebuffer", compression: "DEFLATE" }));
console.log("ok");

})().catch((e) => { console.error(e); process.exit(1); });
