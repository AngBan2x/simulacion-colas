# TODO — Pendientes del proyecto

> Vista generada desde [`PLAN.md`](PLAN.md) el 2026-11-23.
> Progreso: **53/142 tareas (37,3 %)**. Pendientes: **89**.
> No editar este archivo a mano: actualizar `PLAN.md` y ejecutar `python scripts/sync_todos.py`.

## Resumen por fase

| Fase | Tareas | Completadas | Pendientes |
|---|---:|---:|---:|
| F0 — Preparación del repositorio | 19 | 19 | 0 |
| F1 — Motor de eventos discretos | 17 | 17 | 0 |
| F2 — Modelo M/M/1 | 15 | 15 | 0 |
| F3 — Simulador del SOC | 24 | 0 | 24 |
| F4 — Experimentos y escenarios | 23 | 0 | 23 |
| F5 — Informe técnico en LaTeX y PDF | 23 | 2 | 21 |
| F6 — Pruebas y aseguramiento de calidad | 8 | 0 | 8 |
| F7 — Documentación final | 7 | 0 | 7 |
| F8 — Publicación en GitHub y cierre | 6 | 0 | 6 |
| **Total** | **142** | **53** | **89** |

## Pendientes por fase

### F3 — Simulador del SOC (24 pendientes de 24)

#### F3.1 — Configuración y llegadas

- [ ] Implementar `s = 3` y `K = 8`.
- [ ] Implementar llegadas Tipo 1 con `λ1 = 0,05/min`.
- [ ] Implementar llegadas Tipo 2 con `λ2 = 0,10/min`.
- [ ] Implementar servicio Tipo 1 uniforme entre 15 y 25 minutos.
- [ ] Implementar servicio Tipo 2 Weibull con forma 1,5 y escala 12.

#### F3.2 — Lógica de admisión y servicio

- [ ] Implementar inicio inmediato de servicio si hay analista libre.
- [ ] Implementar encolado si hay espacio.
- [ ] Implementar rechazo inmediato si la cola está llena.
- [ ] Implementar dos colas FIFO separadas.
- [ ] Implementar selección de crítica más antigua al liberarse un analista.
- [ ] Implementar selección de preventiva más antigua si no hay críticas.
- [ ] Garantizar que no haya expropiación.

#### F3.3 — Métricas

- [ ] Registrar `W1`, `Wq1`, `W2`, `Wq2` solo para alertas admitidas.
- [ ] Registrar `Lq` global y por tipo como métrica de apoyo.
- [ ] Registrar utilización conjunta de los tres analistas.
- [ ] Registrar `P_loss`, `P_loss1` y `P_loss2`.
- [ ] Registrar conteos de llegadas, admitidas, bloqueadas, completadas y remanentes.

#### F3.4 — Pruebas específicas

- [ ] Probar que no haya más de 3 servicios simultáneos.
- [ ] Probar el bloqueo con 3 servidores ocupados y 8 en cola.
- [ ] Probar el bloqueo de una alerta crítica cuando la cola está llena.
- [ ] Probar la prioridad de una crítica sobre una preventiva.
- [ ] Probar la no expropiación.
- [ ] Probar FIFO dentro de cada clase.
- [ ] Probar las invariantes de conservación.

### F4 — Experimentos y escenarios (23 pendientes de 23)

#### F4.1 — Configuración experimental

- [ ] Definir las semillas y los flujos aleatorios.
- [ ] Definir warm-up y horizontes.
- [ ] Configurar 30 réplicas para el SOC.
- [ ] Configurar semillas comunes para comparaciones pareadas.
- [ ] Implementar el drenaje de alertas admitidas al final del horizonte, si se usa para evitar censura.

#### F4.2 — SOC base

- [ ] Ejecutar 30 días de operación después de 1 día de warm-up.
- [ ] Reportar `W1`, `Wq1`, `W2`, `Wq2`, `Lq`, utilización y `P_loss`.
- [ ] Reportar IC95 %.
- [ ] Guardar resultados por réplica y resumen.

#### F4.3 — Escenario A

- [ ] Cambiar `λ2` a `0,14/min` (8,4/hora).
- [ ] Ejecutar las réplicas correspondientes.
- [ ] Calcular aumento absoluto y relativo de `P_loss`.
- [ ] Calcular utilización y tiempos de espera.
- [ ] Evaluar si los analistas se saturan.

#### F4.4 — Escenario B

- [ ] Ejecutar la alternativa `s=3, K=16`.
- [ ] Ejecutar la alternativa `s=4, K=8`.
- [ ] Comparar `P_loss`, `W1`, `W2`, `Wq1`, `Wq2`, `Lq` y utilización.
- [ ] Repetir la comparación bajo la demanda del Escenario A como análisis de sensibilidad.
- [ ] Emitir una recomendación técnica.

#### F4.5 — Exportación

- [ ] Generar tablas CSV.
- [ ] Generar resumen JSON.
- [ ] Generar figuras.
- [ ] Verificar que las tablas del informe usen los resultados generados.

### F5 — Informe técnico en LaTeX y PDF (21 pendientes de 23)

#### F5.1 — Preparación de LaTeX

- [ ] Configurar la estructura de carpetas del informe.

#### F5.2 — Contenido

- [ ] Escribir resumen, introducción y objetivos.
- [ ] Explicar el modelo de colas propuesto y el marco teórico: M/M/1, Little, prioridades y buffers finitos.
- [ ] Describir el motor de eventos discretos.
- [ ] Documentar los parámetros y supuestos.
- [ ] Presentar la validación M/M/1 con tablas y gráficos.
- [ ] Presentar los resultados del SOC base.
- [ ] Analizar y responder al Escenario A, incluyendo el efecto sobre la saturación.
- [ ] Analizar, comparar y recomendar una alternativa en el Escenario B.
- [ ] Escribir limitaciones y conclusiones.
- [ ] Incluir referencias bibliográficas.
- [ ] Verificar que todas las preguntas y situaciones hipotéticas de la profesora tengan una respuesta explícita en el informe.

#### F5.3 — Tablas y figuras automáticas

- [ ] Generar tablas LaTeX desde los CSV.
- [ ] Generar gráficos en PDF/PNG.
- [ ] Insertar tablas y figuras con `\input` y `\includegraphics`.
- [ ] Verificar que los números del informe coincidan con los resultados.

#### F5.4 — Compilación y revisión

- [ ] Compilar con `latexmk -pdf` sin errores.
- [ ] Revisar advertencias de referencias y tablas.
- [ ] Revisar ortografía y redacción.
- [ ] Confirmar que el PDF final existe y se versiona.
- [ ] Agregar en el README el enlace al PDF.

### F6 — Pruebas y aseguramiento de calidad (8 pendientes de 8)

- [ ] Ejecutar `pytest -q` y lograr que todas las pruebas pasen.
- [ ] Ejecutar el flujo completo de simulación.
- [ ] Comprobar la conservación de trabajos/alertas.
- [ ] Comprobar la reproducibilidad con las mismas semillas.
- [ ] Probar la instalación en un entorno limpio.
- [ ] Verificar que no se versionen `.venv`, archivos temporales ni trazas grandes.
- [ ] Revisar `git diff --check`.
- [ ] Verificar que el README permita reproducir todos los resultados.

### F7 — Documentación final (7 pendientes de 7)

- [ ] Actualizar `README.md` con descripción, estructura, comandos, resultados y enlace al PDF.
- [ ] Revisar y completar `AGENTS.md`.
- [ ] Revisar que `PLAN.md` tenga todas las tareas cerradas o justificadas.
- [ ] Agregar instrucciones de instalación de LaTeX.
- [ ] Verificar la licencia MIT y el año.
- [ ] Documentar las semillas y comandos exactos de reproducción.
- [ ] Revisar que el informe y el repositorio usen los mismos resultados.

### F8 — Publicación en GitHub y cierre (6 pendientes de 6)

- [ ] Verificar el repositorio público, el remote `origin` y el README renderizado.
- [ ] Subir la versión final a `main`.
- [ ] Verificar el PDF en GitHub.
- [ ] Crear la etiqueta `v1.0.0`.
- [ ] Crear el release `v1.0.0` con notas.
- [ ] Actualizar `PLAN.md` y el registro de avances final; verificar `git status` limpio y registrar el hash final y la URL.

## Cómo actualizar

1. Actualizar el estado de la tarea en `PLAN.md`.
2. Ejecutar `python scripts/sync_todos.py`.
3. Hacer commit de `PLAN.md` y `TODO.md`.

Los estados permitidos son `[ ]` pendiente, `[~]` en curso, `[x]` completada y `[!]` bloqueada.
