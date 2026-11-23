# Plan de implementación — Simulación de colas

> **Proyecto:** Simulación de un servidor CI/CD M/M/1 y un SOC con prioridades y buffer finito<br>
> **Repositorio:** `AngBan2x/simulacion-colas` (público)<br>
> **Documento de referencia:** `Proyecto_simulacion.md`<br>
> **Estado global:** 19,0 % — F0 completada, F1 en curso (6/17), preparación de LaTeX iniciada<br>
> **Fase actual:** F1 — Motor de eventos discretos<br>
> **Vista rápida de pendientes:** [`TODO.md`](TODO.md)<br>
> **Última actualización:** 2026-11-23<br>
> **Licencia:** MIT<br>
> **Informe:** LaTeX compilado a PDF (MiKTeX 25.12 instalado; `pdflatex` y `latexmk` verificados)<br>
> **Objetivo de este archivo:** ser la fuente única de verdad del avance del proyecto. Debe actualizarse al comenzar y al terminar cada tarea, y al cerrar cada fase.

---

## 1. Decisiones confirmadas

- [x] El repositorio será **público** y se llamará `simulacion-colas`.
- [x] El propietario del repositorio será la cuenta de GitHub **AngBan2x**.
- [x] El proyecto se implementará en **Python 3.14**.
- [x] Se implementará un motor de eventos discretos propio con `heapq`; no se usará SimPy.
- [x] Las unidades de tiempo serán **minutos**.
- [x] El informe se escribirá en **LaTeX** y se compilará a **PDF**.
- [x] El archivo `Proyecto_simulacion.md` se incluirá dentro del repositorio.
- [x] Se agregará una licencia **MIT**.
- [x] Se creará un archivo **`PLAN.md`** en la raíz del repositorio para el seguimiento del avance.
- [x] Se creará un archivo **`AGENTS.md`** en la raíz con las reglas de trabajo para el equipo y los agentes.
- [x] **MiKTeX 25.12** instalado; `pdflatex` y `latexmk` verificados para el informe.
- [x] Los resultados resumidos y las figuras se versionarán en Git.
- [x] Las trazas crudas, entornos virtuales y archivos temporales no se versionarán.

### Supuestos técnicos

- `K = 8` es la capacidad de **cola**, por lo que la capacidad total del SOC es `s + K = 11` (3 analistas + 8 espacios de espera).
- Las llegadas de ambos tipos de alerta son procesos Poisson independientes.
- La prioridad es **no expropiativa**: ninguna alerta interrumpe un servicio en curso.
- Dentro de cada tipo de alerta se respeta FIFO.
- Una alerta crítica también puede ser bloqueada si la cola de 8 espacios está llena.
- El servicio Tipo 2 se modela como `Weibull(k=1,5, escala=12)`. La media es `12·Γ(1 + 1/1,5) ≈ 10,8329 min`, no 12.
- Los gráficos y tablas del informe se generarán desde los resultados de la simulación; no se escribirán números a mano.

---

## 2. Protocolo de actualización de este plan

### Leyenda de estados

- `[ ]` Pendiente
- `[~]` En curso
- `[x]` Completada
- `[!]` Bloqueada

### Reglas

1. Antes de empezar una tarea, cambiar `[ ]` a `[~]`, registrar la fecha y el responsable.
2. Al terminarla, cambiar a `[x]` y agregar una evidencia breve: archivo creado, prueba ejecutada, resultado o commit.
3. Si no se puede continuar, marcar `[!]` e indicar el bloqueo y el siguiente paso.
4. No marcar una fase como completada si sus criterios de aceptación no se cumplen.
5. Actualizar la tabla de progreso y el registro de avances al terminar cada subfase.
6. Cada commit relevante debe incluir la actualización correspondiente de `PLAN.md`.
7. Al finalizar el proyecto, todas las tareas deben estar en `[x]` o justificadas como fuera de alcance.

### Fórmula de progreso

- Progreso de una fase: `tareas completadas / tareas totales × 100`.
- Progreso global: promedio ponderado por cantidad de tareas de todas las fases.
- Una fase solo cuenta como completada al 100 % cuando todas sus tareas y su criterio de aceptación están cumplidos.

---

## 3. Resumen de progreso

| Fase | Descripción | Estado | Tareas | Completadas | Progreso |
|---|---|---|---:|---:|---:|
| F0 | Preparación del repositorio | Completada | 19 | 19 | 100 % |
| F1 | Motor de eventos discretos | En curso | 17 | 6 | 35,3 % |
| F2 | Modelo M/M/1 | Pendiente | 15 | 0 | 0 % |
| F3 | Simulador del SOC | Pendiente | 24 | 0 | 0 % |
| F4 | Experimentos y escenarios | Pendiente | 23 | 0 | 0 % |
| F5 | Informe técnico en LaTeX y PDF | En curso | 23 | 2 | 8,7 % |
| F6 | Pruebas y aseguramiento de calidad | Pendiente | 8 | 0 | 0 % |
| F7 | Documentación final | Pendiente | 7 | 0 | 0 % |
| F8 | Publicación en GitHub y cierre | Pendiente | 6 | 0 | 0 % |
| **Total** |  |  | **142** | **27** | **19,0 %** |

---

## 4. Fases, subfases y tareas

## F0 — Preparación del repositorio

**Objetivo:** dejar un proyecto reproducible, con entorno virtual, estructura inicial, licencia, plan y reglas de trabajo.

### F0.1 — Verificación del entorno

- [x] Confirmar versiones de Python, Git, GitHub CLI y pytest.
- [x] Verificar autenticación de `gh` y cuenta activa.
- [x] Verificar disponibilidad inicial de LaTeX: no estaba instalado; se autorizó MiKTeX y se completó su instalación en F5.1.
- [x] Registrar las versiones en el README.

### F0.2 — Entorno de Python

- [x] Crear `.venv` con `python -m venv .venv`.
- [x] Actualizar `pip` a la versión 26.3.
- [x] Crear `pyproject.toml` con metadatos, dependencias y configuración de pytest.
- [x] Instalar el paquete en modo editable.
- [x] Verificar que los comandos base funcionen.

### F0.3 — Estructura y archivos base

- [x] Crear `src/simulacion_colas/` y `tests/`.
- [x] Crear `.gitignore`.
- [x] Crear `.gitattributes`.
- [x] Crear `LICENSE` con texto MIT y titular del copyright.
- [x] Crear `README.md` inicial en español.
- [x] Crear `PLAN.md` en la raíz a partir de este documento.
- [x] Crear `AGENTS.md` con las reglas del equipo.

### F0.4 — Publicación inicial

- [x] Crear el repositorio público con `gh repo create`.
- [x] Configurar `origin` y subir la rama `main`.
- [x] Verificar que el repositorio remoto sea accesible y que el primer commit esté publicado.

**Criterio de aceptación F0:** el repositorio local existe, el entorno virtual funciona, los archivos base están creados y `git status` no incluye archivos temporales ni secretos. El repositorio remoto está creado y accesible.

---

## F1 — Motor de eventos discretos

**Objetivo:** implementar la infraestructura común de simulación, independiente de los modelos concretos.

### F1.1 — Cola de eventos

- [x] Implementar `Event` con tiempo, tipo, prioridad y secuencia (`src/simulacion_colas/engine.py`).
- [x] Implementar `EventQueue` con `heapq` (`src/simulacion_colas/engine.py`).
- [x] Definir y documentar la regla de desempate para eventos simultáneos (tiempo → prioridad → secuencia FIFO).
- [x] Implementar el reloj de simulación y el bucle principal (`Simulation.run`).

### F1.2 — Generadores aleatorios

- [ ] Implementar muestreo exponencial reproducible.
- [ ] Implementar muestreo uniforme reproducible.
- [ ] Implementar muestreo Weibull con forma y escala.
- [ ] Separar los flujos aleatorios de llegadas y servicios.
- [ ] Documentar la convención de unidades en minutos.

### F1.3 — Acumuladores y estadística

- [ ] Implementar acumuladores de área para promedios ponderados por tiempo.
- [ ] Implementar medias, desviación estándar e IC95 % con distribución t.
- [ ] Implementar error relativo y ratios de Little.
- [ ] Implementar comparación de diferencias pareadas entre escenarios.

### F1.4 — Pruebas iniciales

- [x] Probar el orden de eventos (`tests/test_engine.py`).
- [x] Probar el desempate determinista (`tests/test_engine.py`).
- [ ] Probar reproducibilidad con semillas.
- [ ] Probar que las medias muestrales de las distribuciones sean razonables.

**Criterio de aceptación F1:** el motor procesa eventos en orden, es reproducible y sus utilidades estadísticas están cubiertas por pruebas.

---

## F2 — Modelo M/M/1

**Objetivo:** implementar el simulador del servidor CI/CD y validarlo contra las fórmulas analíticas.

### F2.1 — Parámetros y fórmulas

- [ ] Implementar `λ = 0,25/min`, `μ = 1/3/min` y `ρ = 0,75`.
- [ ] Implementar `L`, `Lq`, `W` y `Wq` analíticos.
- [ ] Documentar la justificación del modelo M/M/1.

### F2.2 — Simulador

- [ ] Implementar llegadas exponenciales.
- [ ] Implementar servicio exponencial.
- [ ] Implementar cola FIFO infinita.
- [ ] Registrar tiempos de llegada, inicio de servicio y salida.
- [ ] Medir `L`, `Lq`, `W` y `Wq`.
- [ ] Implementar warm-up configurable.

### F2.3 — CLI y validación

- [ ] Implementar el subcomando `mm1`.
- [ ] Ejecutar un piloto para justificar el warm-up.
- [ ] Ejecutar 50 réplicas de 30.000 minutos después del warm-up.
- [ ] Calcular IC95 % y errores relativos.
- [ ] Calcular y reportar ratios de Little.
- [ ] Exportar resultados a CSV/JSON.

**Criterio de aceptación F2:** los IC95 % contienen los valores analíticos, los ratios de Little son cercanos a 1 y el error relativo es razonable para un horizonte de 30.000 minutos.

---

## F3 — Simulador del SOC

**Objetivo:** modelar tres analistas, dos clases de alertas, prioridad no expropiativa y buffer finito de 8.

### F3.1 — Configuración y llegadas

- [ ] Implementar `s = 3` y `K = 8`.
- [ ] Implementar llegadas Tipo 1 con `λ1 = 0,05/min`.
- [ ] Implementar llegadas Tipo 2 con `λ2 = 0,10/min`.
- [ ] Implementar servicio Tipo 1 uniforme entre 15 y 25 minutos.
- [ ] Implementar servicio Tipo 2 Weibull con forma 1,5 y escala 12.

### F3.2 — Lógica de admisión y servicio

- [ ] Implementar inicio inmediato de servicio si hay analista libre.
- [ ] Implementar encolado si hay espacio.
- [ ] Implementar rechazo inmediato si la cola está llena.
- [ ] Implementar dos colas FIFO separadas.
- [ ] Implementar selección de crítica más antigua al liberarse un analista.
- [ ] Implementar selección de preventiva más antigua si no hay críticas.
- [ ] Garantizar que no haya expropiación.

### F3.3 — Métricas

- [ ] Registrar `W1`, `Wq1`, `W2`, `Wq2` solo para alertas admitidas.
- [ ] Registrar `Lq` global y por tipo como métrica de apoyo.
- [ ] Registrar utilización conjunta de los tres analistas.
- [ ] Registrar `P_loss`, `P_loss1` y `P_loss2`.
- [ ] Registrar conteos de llegadas, admitidas, bloqueadas, completadas y remanentes.

### F3.4 — Pruebas específicas

- [ ] Probar que no haya más de 3 servicios simultáneos.
- [ ] Probar el bloqueo con 3 servidores ocupados y 8 en cola.
- [ ] Probar el bloqueo de una alerta crítica cuando la cola está llena.
- [ ] Probar la prioridad de una crítica sobre una preventiva.
- [ ] Probar la no expropiación.
- [ ] Probar FIFO dentro de cada clase.
- [ ] Probar las invariantes de conservación.

**Criterio de aceptación F3:** todas las pruebas de capacidad, prioridad y conservación pasan y el modelo puede ejecutar 30 días simulados.

---

## F4 — Experimentos y escenarios

**Objetivo:** generar los resultados que responden al enunciado, con incertidumbre estadística.

### F4.1 — Configuración experimental

- [ ] Definir las semillas y los flujos aleatorios.
- [ ] Definir warm-up y horizontes.
- [ ] Configurar 30 réplicas para el SOC.
- [ ] Configurar semillas comunes para comparaciones pareadas.
- [ ] Implementar el drenaje de alertas admitidas al final del horizonte, si se usa para evitar censura.

### F4.2 — SOC base

- [ ] Ejecutar 30 días de operación después de 1 día de warm-up.
- [ ] Reportar `W1`, `Wq1`, `W2`, `Wq2`, `Lq`, utilización y `P_loss`.
- [ ] Reportar IC95 %.
- [ ] Guardar resultados por réplica y resumen.

### F4.3 — Escenario A

- [ ] Cambiar `λ2` a `0,14/min` (8,4/hora).
- [ ] Ejecutar las réplicas correspondientes.
- [ ] Calcular aumento absoluto y relativo de `P_loss`.
- [ ] Calcular utilización y tiempos de espera.
- [ ] Evaluar si los analistas se saturan.

### F4.4 — Escenario B

- [ ] Ejecutar la alternativa `s=3, K=16`.
- [ ] Ejecutar la alternativa `s=4, K=8`.
- [ ] Comparar `P_loss`, `W1`, `W2`, `Wq1`, `Wq2`, `Lq` y utilización.
- [ ] Repetir la comparación bajo la demanda del Escenario A como análisis de sensibilidad.
- [ ] Emitir una recomendación técnica.

### F4.5 — Exportación

- [ ] Generar tablas CSV.
- [ ] Generar resumen JSON.
- [ ] Generar figuras.
- [ ] Verificar que las tablas del informe usen los resultados generados.

**Criterio de aceptación F4:** existen resultados reproducibles para el caso base, A y B, con IC95 % y comparaciones pareadas.

---

## F5 — Informe técnico en LaTeX y PDF

**Objetivo:** producir `docs/informe/main.tex` y `docs/informe/main.pdf` como un informe técnico que explique el modelo de colas propuesto, documente la simulación y analice o responda todas las preguntas y situaciones hipotéticas de la profesora.

### F5.1 — Preparación de LaTeX

- [x] Instalar MiKTeX o verificar que `pdflatex` y `latexmk` estén disponibles. MiKTeX 25.12 y Strawberry Perl 5.42.3 instalados; `pdflatex` y `latexmk` 4.89 verificados.
- [x] Verificar compilación de un documento mínimo en español; PDF de prueba generado correctamente.
- [ ] Configurar la estructura de carpetas del informe.

### F5.2 — Contenido

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

### F5.3 — Tablas y figuras automáticas

- [ ] Generar tablas LaTeX desde los CSV.
- [ ] Generar gráficos en PDF/PNG.
- [ ] Insertar tablas y figuras con `\input` y `\includegraphics`.
- [ ] Verificar que los números del informe coincidan con los resultados.

### F5.4 — Compilación y revisión

- [ ] Compilar con `latexmk -pdf` sin errores.
- [ ] Revisar advertencias de referencias y tablas.
- [ ] Revisar ortografía y redacción.
- [ ] Confirmar que el PDF final existe y se versiona.
- [ ] Agregar en el README el enlace al PDF.

**Criterio de aceptación F5:** el PDF compila desde cero, explica el modelo de colas propuesto, contiene todos los resultados y responde explícitamente las preguntas y situaciones hipotéticas de la profesora.

---

## F6 — Pruebas y aseguramiento de calidad

**Objetivo:** garantizar que el proyecto se pueda ejecutar y validar desde cero.

- [ ] Ejecutar `pytest -q` y lograr que todas las pruebas pasen.
- [ ] Ejecutar el flujo completo de simulación.
- [ ] Comprobar la conservación de trabajos/alertas.
- [ ] Comprobar la reproducibilidad con las mismas semillas.
- [ ] Probar la instalación en un entorno limpio.
- [ ] Verificar que no se versionen `.venv`, archivos temporales ni trazas grandes.
- [ ] Revisar `git diff --check`.
- [ ] Verificar que el README permita reproducir todos los resultados.

**Criterio de aceptación F6:** pruebas en verde, resultados reproducibles, sin archivos basura ni secretos.

---

## F7 — Documentación final

**Objetivo:** dejar el repositorio listo para consulta y entrega.

- [ ] Actualizar `README.md` con descripción, estructura, comandos, resultados y enlace al PDF.
- [ ] Revisar y completar `AGENTS.md`.
- [ ] Revisar que `PLAN.md` tenga todas las tareas cerradas o justificadas.
- [ ] Agregar instrucciones de instalación de LaTeX.
- [ ] Verificar la licencia MIT y el año.
- [ ] Documentar las semillas y comandos exactos de reproducción.
- [ ] Revisar que el informe y el repositorio usen los mismos resultados.

**Criterio de aceptación F7:** una persona o agente puede clonar el repositorio, instalar dependencias, ejecutar las pruebas, regenerar resultados y compilar el PDF siguiendo el README.

---

## F8 — Publicación en GitHub y cierre

**Objetivo:** publicar la versión final y dejar un cierre verificable. La creación inicial del repositorio se realiza en F0.4.

- [ ] Verificar el repositorio público, el remote `origin` y el README renderizado.
- [ ] Subir la versión final a `main`.
- [ ] Verificar el PDF en GitHub.
- [ ] Crear la etiqueta `v1.0.0`.
- [ ] Crear el release `v1.0.0` con notas.
- [ ] Actualizar `PLAN.md` y el registro de avances final; verificar `git status` limpio y registrar el hash final y la URL.

**Criterio de aceptación F8:** el repositorio está público, contiene todo el proyecto, el PDF y el plan finalizado, y la etiqueta de entrega apunta al commit final.

---

## 5. Registro de avances

| Fecha | Fase / tarea | Cambio | Responsable | Evidencia / commit |
|---|---|---|---|---|
| 2026-11-22 | Planificación | Plan aprobado y decisiones confirmadas | Equipo | Este documento |
| 2026-11-22 | F0.1–F0.2 | Entorno virtual, dependencias y verificación inicial | Equipo | `e93abbc` |
| 2026-11-22 | F0.3 | Estructura, README, `PLAN.md`, `AGENTS.md`, licencia y configuración | Equipo | `e93abbc` |
| 2026-11-22 | F0.4 | Repositorio público creado y primer push | Equipo | https://github.com/AngBan2x/simulacion-colas |
| 2026-11-23 | F1.1, F1.4 | Motor base de eventos discretos y pruebas de orden/desempate | Equipo | `engine.py`, `tests/test_engine.py`; 9 pruebas en verde |
| 2026-11-23 | F5.1 | MiKTeX 25.12 y Strawberry Perl 5.42.3 instalados; compilación mínima en español verificada | Equipo | `pdflatex`, `latexmk` 4.89; PDF de prueba |
| 2026-11-23 | F5 | Se incorpora el requisito del informe técnico y de responder todas las preguntas de la profesora | Equipo | `PLAN.md`, `AGENTS.md`; pendientes en `TODO.md` |
|  |  |  |  |  |

---

## 6. Contenido obligatorio de `AGENTS.md`

El archivo `AGENTS.md` de la raíz debe incluir, como mínimo:

1. **Contexto del proyecto:** dos simuladores, Python y estructura del repositorio.
2. **Jerarquía documental:** `Proyecto_simulacion.md` define el alcance; `PLAN.md` es la fuente de verdad del avance; `README.md` contiene los comandos; `docs/informe/main.tex` contiene el informe.
3. **Regla de inicio:** todo integrante o agente debe leer `PLAN.md`, elegir una tarea pendiente, marcarla `[~]`, registrar fecha y responsable.
4. **Flujo de trabajo:** crear rama para cambios no triviales, implementar, probar, actualizar resultados, actualizar documentación y cerrar la tarea en `PLAN.md`.
5. **Protocolo de progreso:** usar `[ ]`, `[~]`, `[x]`, `[!]`; no marcar tareas completadas sin evidencia; actualizar la tabla de progreso.
6. **Calidad mínima:** ejecutar `pytest -q`, generar resultados reproducibles y compilar el informe antes de cerrar una fase.
7. **Reglas del modelo:** unidades en minutos; `K=8` es cola; prioridad no expropiativa; FIFO por clase; no cambiar supuestos sin actualizar pruebas, plan e informe.
8. **Convenciones de código:** motor propio, núcleo con biblioteca estándar, semillas explícitas, docstrings y nombres técnicos claros.
9. **Resultados y figuras:** no editar números a mano; regenerar desde los CSV; no versionar trazas crudas.
10. **Git:** commits convencionales, no subir `.venv`, no secretos, rama `main` estable, repositorio público, licencia MIT.
11. **Informe:** LaTeX como fuente, PDF compilado y versionado; tablas generadas desde resultados.
12. **Definición de terminado:** código, pruebas, documentación, resultados, PDF y `PLAN.md` actualizados.

---

## 7. Definición global de terminado

El proyecto se considerará terminado cuando:

- [ ] `pytest -q` pase completamente.
- [ ] El comando de reproducción genere todos los resultados.
- [ ] M/M/1 esté validado contra las fórmulas analíticas con IC95 %.
- [ ] Se demuestre numéricamente la Ley de Little.
- [ ] El SOC respete capacidad, prioridad, no expropiación y bloqueo.
- [ ] Se hayan respondido los Escenarios A y B con resultados e incertidumbre.
- [ ] El informe LaTeX compile a PDF sin errores.
- [ ] El README permita reproducir el proyecto desde cero.
- [ ] `PLAN.md` y `AGENTS.md` estén completos.
- [ ] El repositorio público esté actualizado con la etiqueta `v1.0.0`.

---

## 8. Comandos de referencia

```powershell
# Entorno
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"

# Pruebas
pytest -q

# Simulaciones
python -m simulacion_colas mm1 --reps 50 --warmup-min 2000 --horizon-min 30000
python -m simulacion_colas soc --reps 30 --warmup-days 1 --days 30
python -m simulacion_colas scenarios --reps 30
python -m simulacion_colas all

# Informe
latexmk -pdf -interaction=nonstopmode -halt-on-error docs/informe/main.tex

# Git
git init -b main
git add .
git commit -m "chore: inicializa estructura del proyecto"
gh repo create AngBan2x/simulacion-colas --public --source=. --remote=origin --push

# Cierre
git tag -a v1.0.0 -m "Entrega final"
git push origin v1.0.0
gh release create v1.0.0 --generate-notes
```

---

## 9. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| LaTeX no está instalado actualmente. | Instalar MiKTeX; si falla, compilar en Overleaf y descargar el PDF. |
| Confundir la escala de Weibull con su media. | Documentar y probar `E[S2] ≈ 10,8329`. |
| Interpretar `K` como capacidad total. | Usar `K=8` de cola y capacidad total `11`; dejarlo explícito en el informe. |
| Sesgo por horizonte finito. | Usar warm-up, horizonte largo, drenaje opcional y reportar censura. |
| `P_loss` base pequeña. | Reportar puntos porcentuales, conteos e IC además del cambio relativo. |
| Dependencias incompatibles con Python 3.14. | Mantener el núcleo en biblioteca estándar y aislar scipy/matplotlib. |
| Eventos simultáneos. | Definir desempate y probarlo. |
| Resultados del informe desactualizados. | Generar tablas LaTeX desde los CSV y no editar números manualmente. |

---

## 10. Criterios para aprobar este plan

- [ ] El alcance, los supuestos y las decisiones están confirmados.
- [ ] La estructura del repositorio es aceptada.
- [ ] El formato del informe y la estrategia de compilación son aceptados.
- [ ] Las reglas de `PLAN.md` y `AGENTS.md` son aceptadas.
- [ ] El plan puede ejecutarse sin decisiones pendientes que bloqueen la implementación.
