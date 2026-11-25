# 1. Resumen ejecutivo

Los modelos de lenguaje se ejecutan cada vez más localmente, sobre CPU y en máquinas compartidas, donde el sistema operativo reparte el procesador. Este trabajo evalúa experimentalmente cómo influyen los límites de CPU de cgroups v2, la competencia entre procesos y las prioridades del scheduler de Linux en la inferencia de un LLM local ejecutado con Ollama.

Se construyó un banco de pruebas sobre Ubuntu Server 26.04 con kernel 7.0 (scheduler EEVDF) y un procesador de 12 núcleos, con llama3.2:3b en el host y en Docker. Un protocolo único fijó modelo, prompts y parámetros, y midió el tiempo hasta el primer token (TTFT), los tokens por segundo y su variabilidad en 15 condiciones y 780 corridas y el throttling de `cpu.stat`.

En las condiciones evaluadas (sin límites ni competencia), las medias de TTFT y tokens por segundo en Docker difirieron menos del 1 % de las del host; no se prueba equivalencia general. Una cuota de 1 CPU redujo los tokens por segundo un 93,1 % y generó hasta 853 throttles por corrida. Un solo proceso competidor con la misma prioridad los redujo un 89,7 %. Con los competidores en `nice` 19 se recuperó el 87 % del rendimiento sin competencia; al agregar una cuota de 2 CPUs, cayó.

La cuota y la competencia degradaron la inferencia. La prioridad redujo la interferencia sin cuota, pero no amplió el presupuesto del cgroup. Se propone ajustar el número de hilos a la cuota y preferir pesos (`cpu.weight`) a cuotas estrictas.

<!-- Índice: va después del Resumen ejecutivo (orden R1). -->

```{=openxml}
<w:p><w:r><w:br w:type="page"/></w:r></w:p>
<w:p><w:pPr><w:pStyle w:val="TOCHeading"/></w:pPr><w:r><w:t>Índice</w:t></w:r></w:p>
<w:p><w:r><w:fldChar w:fldCharType="begin" w:dirty="true"/></w:r><w:r><w:instrText xml:space="preserve"> TOC \o "1-2" \h \z \u </w:instrText></w:r><w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t>Para ver el índice: clic derecho aquí y «Actualizar campo».</w:t></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>
```
