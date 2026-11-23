# AGENTS.md — Reglas de trabajo del proyecto

Este archivo define cómo deben trabajar las personas y los agentes que contribuyan al repositorio. Si eres un agente automatizado, estas reglas son obligatorias. Si eres una persona del equipo, úsalas como guía de contribución.

## 1. Contexto y fuentes de verdad

- **Alcance del proyecto:** [`Proyecto_simulacion.md`](Proyecto_simulacion.md). No se debe ampliar ni modificar el alcance sin aprobación del equipo.
- **Avance y tareas:** [`PLAN.md`](PLAN.md). Es la fuente única de verdad sobre qué está pendiente, en curso o terminado.
- **Vista de pendientes:** [`TODO.md`](TODO.md). Se genera desde `PLAN.md`; no se edita a mano.
- **Comandos y uso:** [`README.md`](README.md).
- **Informe:** `docs/informe/main.tex` y su PDF compilado. Es un informe técnico que debe explicar el modelo de colas y responder las preguntas y situaciones hipotéticas de la profesora.
- **Reglas del modelo:** las de este archivo y las del enunciado.

Antes de hacer cualquier cambio, lee `PLAN.md`, identifica una tarea pendiente y confirma que no esté siendo trabajada por otra persona.

## 2. Modelos y supuestos que no deben cambiarse sin justificación

- Todas las unidades de tiempo del proyecto están en **minutos**.
- Problema 1: M/M/1 con `λ = 0,25/min`, `μ = 1/3/min`, `ρ = 0,75`, FIFO y cola infinita.
- Problema 2: SOC con `s = 3` analistas y `K = 8` espacios de cola. La capacidad total es `s + K = 11`.
- Llegadas del SOC: procesos Poisson independientes con `λ1 = 0,05/min` y `λ2 = 0,10/min`.
- Servicio Tipo 1: uniforme entre 15 y 25 minutos.
- Servicio Tipo 2: Weibull con forma `k = 1,5` y escala `12` minutos. Su media es `12·Γ(1 + 1/1,5) ≈ 10,8329 min`.
- Disciplina de prioridad **no expropiativa**: una alerta crítica no interrumpe un servicio en curso.
- Al liberarse un analista: primero se atiende la crítica más antigua; si no hay críticas, la preventiva más antigua.
- FIFO dentro de cada tipo de alerta.
- Las alertas críticas también pueden bloquearse cuando la cola está llena.
- Los servicios y las llegadas deben usar generadores aleatorios independientes y semillas explícitas.

Cualquier cambio en estos supuestos debe actualizar simultáneamente el código, las pruebas, `PLAN.md` y el informe.

## 3. Flujo obligatorio de trabajo

1. Leer `PLAN.md` y elegir una tarea pendiente.
2. Cambiar la tarea de `[ ]` a `[~]` y registrar fecha y responsable.
3. Crear una rama para cambios no triviales, por ejemplo `feat/motor-eventos`.
4. Implementar el cambio con pruebas.
5. Ejecutar la verificación mínima antes de cerrar la tarea.
6. Actualizar resultados, documentación e informe si el comportamiento cambió.
7. Marcar la tarea como `[x]` y agregar evidencia: archivos, pruebas o commit.
8. Actualizar la tabla de progreso y el registro de avances de `PLAN.md`.
9. Ejecutar `python scripts/sync_todos.py` para regenerar `TODO.md`.
10. Hacer commit y subir los cambios.

No se deben mezclar cambios no relacionados en un mismo commit.

## 4. Protocolo de actualización de `PLAN.md`

Estados permitidos:

- `[ ]` pendiente
- `[~]` en curso
- `[x]` completada
- `[!]` bloqueada

Reglas:

- No marcar una tarea como completada si no cumple su criterio de aceptación.
- Al cerrar una fase, revisar todas sus tareas y su criterio de aceptación.
- Actualizar las fechas y el porcentaje de progreso.
- Si una tarea queda bloqueada, indicar el motivo y el siguiente paso.
- Regenerar `TODO.md` con `python scripts/sync_todos.py` después de cada cambio de estado.
- Al finalizar el proyecto, todas las tareas deben estar completadas o justificadas como fuera de alcance.

## 5. Calidad mínima antes de cerrar una tarea

```powershell
# Pruebas
pytest -q

# Verificación de importación del paquete
python -c "import simulacion_colas"

# Informe, cuando exista
latexmk -pdf -interaction=nonstopmode -halt-on-error docs/informe/main.tex
```

Además:

- Ejecutar el flujo completo de simulación cuando se modifique un modelo.
- Verificar que los resultados se puedan reproducir con las semillas documentadas.
- Revisar `git diff --check`.
- No dejar archivos temporales, trazas grandes ni secretos en el repositorio.

## 6. Convenciones de código

- El núcleo de simulación debe implementarse con la biblioteca estándar de Python; no usar SimPy.
- Mantener el motor separado de los modelos.
- Usar nombres técnicos claros en inglés y documentación/docstrings en español.
- Preferir funciones pequeñas, tipos explícitos y estructuras de datos simples.
- Las semillas y los flujos aleatorios deben ser explícitos y reproducibles.
- No introducir dependencias nuevas sin actualizar `pyproject.toml` y el README.

## 7. Resultados, figuras e informe

- Los resultados se generan con los scripts del proyecto; no se editan a mano.
- Las tablas del informe deben generarse desde los CSV cuando sea posible.
- Se versionan los resúmenes `CSV`/`JSON`, las figuras finales y el PDF.
- No se versionan trazas crudas ni resultados temporales.
- El informe se escribe en LaTeX y se compila a PDF.
- El informe es técnico: debe explicar el modelo de colas propuesto y analizar o responder todas las preguntas y situaciones hipotéticas de la profesora.
- Los números del informe deben coincidir con los resultados versionados.

## 8. Git y GitHub

- Repositorio público: `AngBan2x/simulacion-colas`.
- Licencia MIT.
- Rama principal: `main`.
- Usar mensajes de commit convencionales: `feat:`, `fix:`, `test:`, `docs:`, `chore:`.
- No subir `.venv`, `__pycache__`, `.pytest_cache`, archivos de cobertura, secretos ni credenciales.
- No reescribir el historial remoto ni hacer force-push a `main`.
- Antes de cada push, verificar `git status` y que las pruebas relevantes pasen.

## 9. Herramientas del entorno

- Python: 3.14.7 detectado al inicio.
- pytest: instalado en el entorno virtual.
- Git y GitHub CLI: disponibles.
- LaTeX/MiKTeX: MiKTeX 25.12 instalado; `pdflatex` y `latexmk` verificados.
- `latexmk` requiere Perl. Usar Strawberry Perl o el Perl incluido con Git, asegurando que `perl` esté en el `PATH`.

## 10. Definición de terminado

Una contribución está terminada cuando:

- el código funciona y está probado;
- `PLAN.md` refleja el estado real;
- la documentación necesaria está actualizada;
- los resultados se pueden reproducir;
- el informe y el PDF se actualizaron si corresponde;
- los cambios están commiteados y subidos.

Si una instrucción entra en conflicto con el enunciado o con `PLAN.md`, se debe detener el trabajo y pedir aclaración antes de continuar.
