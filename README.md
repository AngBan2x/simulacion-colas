# Simulación de colas

Proyecto de simulación de eventos discretos para dos sistemas de líneas de espera:

1. **Servidor CI/CD M/M/1:** un único servidor con llegadas Poisson, servicio exponencial, disciplina FIFO y cola infinita.
2. **Centro de Triaje de Incidentes (SOC):** tres analistas en paralelo, dos clases de alertas con prioridad no expropiativa, servicios no exponenciales y buffer finito de 8 espacios.

El proyecto incluye el motor de simulación, los experimentos estadísticos, los escenarios de capacidad solicitados y un informe técnico en LaTeX compilado a PDF que explica el modelo de colas propuesto y responde las situaciones hipotéticas de la profesora.

## Estado actual

- [x] Preparación del repositorio, licencia y documentación de trabajo.
- [x] Motor de eventos discretos, distribuciones y estadística.
- [x] Modelo M/M/1 y validación analítica.
- [ ] Simulador del SOC.
- [ ] Experimentos y escenarios A/B.
- [ ] Informe técnico en LaTeX y PDF.

El avance detallado se mantiene en [`PLAN.md`](PLAN.md). Para consultar solo lo pendiente, revisa [`TODO.md`](TODO.md).

## Requisitos

- Python 3.12 o superior.
- Git.
- GitHub CLI, solo para publicar el repositorio.
- MiKTeX o una instalación equivalente de LaTeX, para compilar el informe.
- Perl, requerido por `latexmk`.

### Entorno validado

- Python 3.14.7
- Git 2.56.1
- GitHub CLI 2.97.0
- pytest 9.2.0
- MiKTeX 25.12 con `pdflatex` verificado
- Strawberry Perl 5.42.3
- `latexmk` 4.89 compilando correctamente en español

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
python -m simulacion_colas.cli mm1
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
│       ├── engine.py         # Cola de eventos y reloj de simulación
│       ├── distributions.py  # Exponencial, uniforme y Weibull reproducibles
│       ├── stats.py          # Acumuladores, IC95 % y comparaciones
│       ├── mm1.py            # Modelo M/M/1 y validación analítica
│       └── cli.py            # Subcomando mm1 y exportación de resultados
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
