# 1. Resumen ejecutivo

Los modelos de lenguaje se ejecutan cada vez más localmente, sobre CPU y en máquinas compartidas, donde el sistema operativo decide cómo se reparte el procesador. Este trabajo evalúa experimentalmente cómo influyen los límites de CPU de cgroups v2, la competencia entre procesos y las prioridades del scheduler de Linux en la inferencia de un LLM local ejecutado con Ollama.

Se construyó un banco de pruebas sobre Ubuntu Server 26.04 con kernel 7.0 (scheduler EEVDF) y un procesador de 12 núcleos, con el modelo llama3.2:3b ejecutado en el host y dentro de Docker. Un protocolo único fijó el modelo, los prompts y los parámetros, y midió el tiempo hasta el primer token (TTFT), los tokens por segundo y su variabilidad en 15 condiciones y 780 corridas y el throttling de `cpu.stat`.

Ejecutar Ollama en Docker no cambió el rendimiento (diferencias menores al 1 %). Una cuota de 1 CPU redujo los tokens por segundo un 93,1 % y generó hasta 853 throttles por corrida. Un solo proceso competidor con la misma prioridad los redujo un 89,7 %. Bajar la prioridad del competidor a `nice` 19 recuperó el 87 % del rendimiento, pero no compensó una cuota estricta de 2 CPUs.

La cuota y la competencia degradan fuertemente la inferencia sobre CPU, y la prioridad solo ayuda cuando hay CPU libre para repartir. Se propone ajustar el número de hilos a la cuota y preferir pesos (`cpu.weight`) a cuotas estrictas.

<!-- Índice: va después del Resumen ejecutivo (orden R1). -->

```{=openxml}
<w:p><w:r><w:br w:type="page"/></w:r></w:p>
<w:p><w:pPr><w:pStyle w:val="TOCHeading"/></w:pPr><w:r><w:t>Índice</w:t></w:r></w:p>
<w:p><w:r><w:fldChar w:fldCharType="begin" w:dirty="true"/></w:r><w:r><w:instrText xml:space="preserve"> TOC \o "1-2" \h \z \u </w:instrText></w:r><w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t>Para ver el índice: clic derecho aquí y «Actualizar campo».</w:t></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>
```
