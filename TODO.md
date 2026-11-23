# TODO — Pendientes del proyecto

> Vista generada desde [`PLAN.md`](PLAN.md) el 2026-11-23.
> Progreso: **100/142 tareas (70,4 %)**. Pendientes: **42**.
> No editar este archivo a mano: actualizar `PLAN.md` y ejecutar `python scripts/sync_todos.py`.

## Resumen por fase

| Fase | Tareas | Completadas | Pendientes |
|---|---:|---:|---:|
| F0 — Preparación del repositorio | 19 | 19 | 0 |
| F1 — Motor de eventos discretos | 17 | 17 | 0 |
| F2 — Modelo M/M/1 | 15 | 15 | 0 |
| F3 — Simulador del SOC | 24 | 24 | 0 |
| F4 — Experimentos y escenarios | 23 | 23 | 0 |
| F5 — Informe técnico en LaTeX y PDF | 23 | 2 | 21 |
| F6 — Pruebas y aseguramiento de calidad | 8 | 0 | 8 |
| F7 — Documentación final | 7 | 0 | 7 |
| F8 — Publicación en GitHub y cierre | 6 | 0 | 6 |
| **Total** | **142** | **100** | **42** |

## Pendientes por fase

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
