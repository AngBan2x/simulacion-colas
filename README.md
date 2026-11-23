# Simulación de colas

Proyecto de simulación de eventos discretos para dos sistemas de líneas de espera:

1. **Servidor CI/CD M/M/1:** un único servidor con llegadas Poisson, servicio exponencial, disciplina FIFO y cola infinita.
2. **Centro de Triaje de Incidentes (SOC):** tres analistas en paralelo, dos clases de alertas con prioridad no expropiativa, servicios no exponenciales y buffer finito de 8 espacios.

El proyecto incluye el motor de simulación, los experimentos estadísticos, los escenarios de capacidad solicitados y un informe técnico en LaTeX compilado a PDF que explica el modelo de colas propuesto y responde las situaciones hipotéticas de la profesora.

## Estado actual

- [x] Preparación del repositorio, licencia y documentación de trabajo.
- [ ] Motor de eventos discretos: base implementada; distribuciones y estadística pendientes.
- [ ] Modelo M/M/1 y validación analítica.
- [ ] Simulador del SOC.
- [ ] Experimentos y escenarios A/B.
- [ ] Informe técnico en LaTeX y PDF.

El avance detallado se mantiene en [`PLAN.md`](PLAN.md). Para consultar solo lo pendiente, revisa [`TODO.md`](TODO.md).

## Requisitos

- Python 3.12 o superior.
- Git.
- GitHub CLI, solo para publicar el repositorio.
- MiKTeX o una instalación equivalente de LaTeX, para compilar el informe. La instalación de MiKTeX fue autorizada y se realizará en la fase del informe.

### Entorno validado

- Python 3.14.7
- Git 2.56.1
- GitHub CLI 2.97.0
- pytest 9.2.0
- MiKTeX 25.12 con `pdflatex` y `latexmk` verificados
- `latexmk` requiere Perl; se verificó con el Perl disponible en el entorno

## Instalación

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Las dependencias de análisis y gráficos se instalan con:

```powershell
python -m pip install -e ".[analysis]"
```

## Pruebas

```powershell
pytest -q
```

## Estructura del proyecto

```text
simulacion-colas/
├── Proyecto_simulacion.md   # Enunciado original
├── README.md
├── PLAN.md                  # Plan y seguimiento de avance
├── TODO.md                  # Vista generada de tareas pendientes
├── AGENTS.md                # Reglas para el equipo y agentes
├── LICENSE                  # Licencia MIT
├── pyproject.toml
├── src/
│   └── simulacion_colas/
├── tests/
├── scripts/
│   └── sync_todos.py        # Regenera TODO.md desde PLAN.md
├── results/                 # Resultados resumidos generados
├── figures/                 # Figuras generadas
└── docs/
    └── informe/             # Fuente LaTeX y PDF final
```

## Documentación

- [`Proyecto_simulacion.md`](Proyecto_simulacion.md): enunciado y alcance.
- [`PLAN.md`](PLAN.md): fases, tareas y estado de avance.
- [`TODO.md`](TODO.md): vista rápida de las tareas pendientes.
- [`AGENTS.md`](AGENTS.md): reglas de contribución para personas y agentes.
- `docs/informe/main.pdf`: informe técnico final, pendiente de generar.

Para actualizar la vista de pendientes después de cambiar `PLAN.md`:

```powershell
python scripts/sync_todos.py
```

## Licencia

Este proyecto se distribuye bajo la licencia MIT. Consulta [`LICENSE`](LICENSE).
