# Simulación de colas

Proyecto de simulación de eventos discretos para dos sistemas de líneas de espera:

1. **Servidor CI/CD M/M/1:** un único servidor con llegadas Poisson, servicio exponencial, disciplina FIFO y cola infinita.
2. **Centro de Triaje de Incidentes (SOC):** tres analistas en paralelo, dos clases de alertas con prioridad no expropiativa, servicios no exponenciales y buffer finito de 8 espacios.

El proyecto incluye el motor de simulación, los experimentos estadísticos, los escenarios de capacidad solicitados y un informe técnico en LaTeX compilado a PDF que explica el modelo de colas propuesto y responde las situaciones hipotéticas de la profesora.

## Estado actual

- [x] Preparación del repositorio, licencia y documentación de trabajo.
- [x] Motor de eventos discretos, distribuciones y estadística.
- [x] Modelo M/M/1 y validación analítica.
- [x] Simulador del SOC.
- [x] Experimentos y escenarios A/B.
- [x] Informe técnico en LaTeX y PDF.
- [x] Calidad, documentación final y publicación de la versión `v1.0.0`.

El avance detallado se mantiene en [`PLAN.md`](PLAN.md). Para consultar solo lo pendiente, revisa [`TODO.md`](TODO.md). El informe final está en [`docs/informe/main.pdf`](docs/informe/main.pdf).

## Requisitos

- Python 3.12 o superior.
- Git.
- GitHub CLI, solo para publicar el repositorio y crear el release.
- MiKTeX o una instalación equivalente de LaTeX, para compilar el informe.
- Perl, requerido por `latexmk`.

### Entorno validado

- Python 3.14.6
- Git 2.56.1
- GitHub CLI 2.105.0
- pytest 9.2.0
- MiKTeX 25.12 con `pdflatex` verificado
- Strawberry Perl 5.42.3.1
- `latexmk` 4.89 compilando correctamente en español

### Instalación de LaTeX en Windows

Si `pdflatex` no está disponible, instala MiKTeX, Strawberry Perl y GitHub CLI
con `winget`:

```powershell
winget install --id MiKTeX.MiKTeX --exact --accept-package-agreements --accept-source-agreements
winget install --id StrawberryPerl.StrawberryPerl --exact --accept-package-agreements --accept-source-agreements
winget install --id GitHub.cli --exact --accept-package-agreements --accept-source-agreements
```

Cierra y abre una terminal nueva para que se actualice el `PATH`. Verifica con
`pdflatex --version`, `latexmk --version` y `gh --version`.

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

## Uso

El modelo M/M/1 se ejecuta con el subcomando `mm1`. Por defecto usa 50 réplicas,
un warm-up de 1.000 minutos, un horizonte de 30.000 minutos y semillas 1 a 50.

```powershell
python -m simulacion_colas mm1
```

También queda disponible el comando instalado:

```powershell
simulacion-colas mm1
```

Opciones principales:

```text
--replications N    número de réplicas (por defecto 50)
--warmup MIN        warm-up en minutos (por defecto 1000)
--horizon MIN       horizonte por réplica en minutos (por defecto 30000)
--seed N            semilla base; las réplicas usan N, N+1, ...
--skip-pilot        omite el piloto de warm-up
--results-dir DIR   carpeta de salida (por defecto results/)
```

La ejecución escribe:

- `results/mm1_replicas.csv`: métricas por réplica.
- `results/mm1_summary.csv`: resumen por métrica con IC95 %.
- `results/mm1_summary.json`: resumen completo y comparación analítica.
- `results/mm1_warmup_pilot.csv`: piloto que justifica el warm-up.

El modelo del Centro de Triaje (SOC) y sus escenarios se ejecutan con:

```powershell
python -m simulacion_colas soc
python -m simulacion_colas scenarios
python -m simulacion_colas figures
python -m simulacion_colas report
python -m simulacion_colas all
```

Opciones principales de `soc` y `scenarios`:

```text
--replications / --reps N   número de réplicas (por defecto 30)
--warmup-days D             warm-up en días (por defecto 1 = 1.440 min)
--days D                    días de operación medida tras el warm-up (por defecto 30 = 43.200 min)
--warmup / --warmup-min M   warm-up explícito en minutos
--horizon / --horizon-min M horizonte total en minutos
--seed N                    semilla base (por defecto 1)
--no-drain                  desactiva el drenaje al final del horizonte
--results-dir DIR           carpeta de salida (por defecto results/)
--figures-dir DIR           carpeta de figuras (por defecto figures/, en scenarios y figures)
--tables-dir DIR            carpeta de tablas LaTeX (por defecto docs/informe/tables/, en report y all)
--skip-figures              omite la generación de figuras al final de scenarios/all
```

Archivos generados por el SOC, los escenarios y el informe:

- `results/soc_base_replicas.csv`, `results/soc_base_summary.csv`, `results/soc_base_summary.json`.
- `results/soc_scenarios_replicas.csv`, `results/soc_scenarios_summary.csv`, `results/soc_scenarios_comparisons.csv`, `results/soc_scenarios_summary.json`.
- `figures/mm1_validation.{pdf,png}`, `figures/soc_base.{pdf,png}`, `figures/soc_scenario_a.{pdf,png}`, `figures/soc_scenario_b.{pdf,png}`.
- `docs/informe/tables/*.tex` y `docs/informe/main.pdf`.

## Modelo M/M/1

El servidor CI/CD tiene llegadas Poisson con `λ = 0,25` trabajos/minuto, un
único servidor con servicio exponencial de media `3` minutos (`μ = 1/3`),
disciplina FIFO y cola infinita. Por tanto:

```text
ρ  = λ/μ                    = 0,75
L  = ρ/(1-ρ)                = 3
Lq = ρ²/(1-ρ)               = 2,25
W  = 1/(μ-λ)                = 12 min
Wq = ρ/(μ-λ)                = 9 min
```

Como `ρ < 1`, el sistema es estable y las fórmulas anteriores son válidas. La
justificación completa se desarrolla en el informe técnico de `docs/informe/`.

Todas las unidades de tiempo del proyecto están en **minutos**. Las
distribuciones de `simulacion_colas.distributions` reciben tasas por minuto y
devuelven duraciones en minutos.

## Centro de Triaje de Incidentes (SOC)

El SOC cuenta con `s = 3` analistas en paralelo y capacidad de cola finita
`K = 8` (capacidad total `11`), prioridad **no expropiativa** de alertas
críticas (Tipo 1) sobre preventivas (Tipo 2) y colas FIFO por clase:

- **Tipo 1 (críticas):** `λ1 = 0,05/min`, servicio `Uniforme(15, 25)` min (`E[S1] = 20 min`).
- **Tipo 2 (preventivas):** `λ2 = 0,10/min` (base) o `0,14/min` (Escenario A), servicio `Weibull(k = 1,5, escala = 12)` min (`E[S2] ≈ 10,8329 min`).

Resumen con 30 réplicas (1 día de warm-up + 30 días de operación, semillas comunes 1..30):

- **Base (`s=3, K=8, λ2=0,10`):** `P_loss = 0,385 %`, utilización `68,87 %`, `Wq1 = 2,267 min`, `Wq2 = 6,417 min`, `Lq = 0,750`.
- **Escenario A (`s=3, K=8, λ2=0,14`):** `P_loss = 2,220 %` (`+1,835 pp`, `+477,0 %` relativo), utilización efectiva `81,65 %` (`ρ_ofrecida = 0,8389 < 1`), `Wq1 = 3,074 min`, `Wq2 = 11,663 min`.
- **Escenario B (`s=3, K=16` vs `s=4, K=8`):** bajo demanda base ambas reducen `P_loss` en ~95 % (`0,019 %` vs `0,021 %`), pero `s=4` reduce `Wq1` (`0,659` vs `2,344 min`) y `Wq2` (`1,282` vs `7,183 min`). Bajo sobrecarga (`λ2=0,14`), `s=4` reduce `P_loss` a `0,129 %` frente a `0,395 %` con `K=16` y mantiene `Wq2 = 2,519 min` frente a `17,414 min`. Se recomienda contratar el 4.º analista (`s=4, K=8`).

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
│       ├── __init__.py
│       ├── __main__.py       # Punto de entrada python -m simulacion_colas
│       ├── engine.py         # Cola de eventos y reloj de simulación
│       ├── distributions.py  # Exponencial, uniforme y Weibull reproducibles
│       ├── stats.py          # Acumuladores, IC95 % y comparaciones
│       ├── mm1.py            # Modelo M/M/1 y validación analítica
│       ├── soc.py            # Simulador del SOC y escenarios A/B
│       ├── figures.py        # Generación de figuras PDF/PNG con matplotlib
│       ├── report.py         # Tablas LaTeX generadas desde results/
│       └── cli.py            # Subcomandos mm1, soc, scenarios, figures, report y all
├── tests/                    # 65 pruebas (motor, modelos, estadística, informe)
├── scripts/
│   └── sync_todos.py        # Regenera TODO.md desde PLAN.md
├── results/                 # Resultados resumidos generados
├── figures/                 # Figuras generadas
└── docs/
    └── informe/             # main.tex, secciones, tablas, PDF final
```

## Documentación

- [`Proyecto_simulacion.md`](Proyecto_simulacion.md): enunciado y alcance.
- [`PLAN.md`](PLAN.md): fases, tareas y estado de avance.
- [`TODO.md`](TODO.md): vista rápida de las tareas pendientes.
- [`AGENTS.md`](AGENTS.md): reglas de contribución para personas y agentes.
- [`docs/informe/main.tex`](docs/informe/main.tex): fuente LaTeX del informe.
- [`docs/informe/main.pdf`](docs/informe/main.pdf): informe técnico final (10 páginas).
- [`docs/informe/tables/`](docs/informe/tables): tablas generadas desde `results/`.

## Reproducción desde cero

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev,analysis]"
pytest -q
python -m simulacion_colas all
latexmk -pdf -interaction=nonstopmode -halt-on-error docs/informe/main.tex
```

Semillas y diseño:

- M/M/1: semilla base `1`, 50 réplicas con semillas `1..50`, warm-up `1.000 min`, horizonte `30.000 min`.
- SOC: semilla base `1`, 30 réplicas con semillas `1..30` y números aleatorios comunes entre escenarios, warm-up `1.440 min`, ventana medida `43.200 min` (30 días) y drenaje activo.
- Escenarios: base (`s=3, K=8, λ2=0,10`), A (`λ2=0,14`), B1 (`K=16`), B2 (`s=4`) y las dos sensibilidades de B bajo la demanda de A.

El comando `all` regenera `results/`, `figures/` y `docs/informe/tables/`. La
verificación de reproducibilidad confirmó hashes idénticos en los CSV, JSON y
tablas al repetir la campaña con las mismas semillas.

Para actualizar la vista de pendientes después de cambiar `PLAN.md`:

```powershell
python scripts/sync_todos.py
```

## Licencia

Este proyecto se distribuye bajo la licencia MIT. Consulta [`LICENSE`](LICENSE).
