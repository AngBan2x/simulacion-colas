"""Genera una vista de pendientes a partir de PLAN.md.

PLAN.md sigue siendo la fuente única de verdad. Este script únicamente extrae
las tareas de las fases y las presenta en TODO.md, agrupadas por fase y
subfase, omitiendo las tareas ya completadas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "PLAN.md"
TODO_PATH = ROOT / "TODO.md"

PHASE_RE = re.compile(r"^## (F\d+) — (.+)$")
SUBPHASE_RE = re.compile(r"^### (F\d+\.\d+) — (.+)$")
TASK_RE = re.compile(r"^- \[([ ~x!])\] (.+)$")

STATUS_LABELS = {
    " ": "pendiente",
    "~": "en curso",
    "!": "bloqueada",
    "x": "completada",
}


@dataclass
class Task:
    status: str
    text: str
    subphase_code: str
    subphase_title: str


@dataclass
class Phase:
    code: str
    title: str
    tasks: list[Task] = field(default_factory=list)

    @property
    def completed(self) -> int:
        return sum(task.status == "x" for task in self.tasks)

    @property
    def pending(self) -> int:
        return len(self.tasks) - self.completed


def parse_plan() -> list[Phase]:
    content = PLAN_PATH.read_text(encoding="utf-8")
    start = content.index("## 4. Fases, subfases y tareas")
    end = content.index("## 5. Registro de avances")
    section = content[start:end]

    phases: list[Phase] = []
    phase: Phase | None = None
    subphase_code = ""
    subphase_title = ""

    for line in section.splitlines():
        phase_match = PHASE_RE.match(line)
        if phase_match:
            phase = Phase(
                code=phase_match.group(1),
                title=phase_match.group(2),
            )
            phases.append(phase)
            subphase_code = ""
            subphase_title = ""
            continue

        subphase_match = SUBPHASE_RE.match(line)
        if subphase_match:
            subphase_code = subphase_match.group(1)
            subphase_title = subphase_match.group(2)
            continue

        task_match = TASK_RE.match(line)
        if task_match and phase is not None:
            phase.tasks.append(
                Task(
                    status=task_match.group(1),
                    text=task_match.group(2),
                    subphase_code=subphase_code,
                    subphase_title=subphase_title,
                )
            )

    return phases


def render_todo(phases: list[Phase]) -> str:
    total_tasks = sum(len(phase.tasks) for phase in phases)
    total_completed = sum(phase.completed for phase in phases)
    total_pending = total_tasks - total_completed
    percentage = total_completed / total_tasks * 100 if total_tasks else 0.0
    percentage_text = f"{percentage:.1f}".replace(".", ",")
    today = date.today().isoformat()

    lines = [
        "# TODO — Pendientes del proyecto",
        "",
        f"> Vista generada desde [`PLAN.md`](PLAN.md) el {today}.",
        f"> Progreso: **{total_completed}/{total_tasks} tareas ({percentage_text} %)**. "
        f"Pendientes: **{total_pending}**.",
        "> No editar este archivo a mano: actualizar `PLAN.md` y ejecutar "
        "`python scripts/sync_todos.py`.",
        "",
        "## Resumen por fase",
        "",
        "| Fase | Tareas | Completadas | Pendientes |",
        "|---|---:|---:|---:|",
    ]

    for phase in phases:
        lines.append(
            f"| {phase.code} — {phase.title} | {len(phase.tasks)} | "
            f"{phase.completed} | {phase.pending} |"
        )

    lines.extend(
        [
            f"| **Total** | **{total_tasks}** | **{total_completed}** | "
            f"**{total_pending}** |",
            "",
            "## Pendientes por fase",
            "",
        ]
    )

    pending_by_phase = [phase for phase in phases if phase.pending]
    if not pending_by_phase:
        lines.append("No quedan tareas pendientes. El proyecto está completo.")
    else:
        for phase in pending_by_phase:
            lines.append(
                f"### {phase.code} — {phase.title} "
                f"({phase.pending} pendientes de {len(phase.tasks)})"
            )
            lines.append("")

            current_subphase = ""
            for task in phase.tasks:
                if task.status == "x":
                    continue

                if task.subphase_code != current_subphase:
                    current_subphase = task.subphase_code
                    if lines and lines[-1] != "":
                        lines.append("")
                    lines.append(
                        f"#### {task.subphase_code} — {task.subphase_title}"
                    )
                    lines.append("")

                marker = "~" if task.status == "~" else "!" if task.status == "!" else " "
                suffix = ""
                if task.status == "~":
                    suffix = " — **en curso**"
                elif task.status == "!":
                    suffix = " — **bloqueada**"
                lines.append(f"- [{marker}] {task.text}{suffix}")

            lines.append("")

    lines.extend(
        [
            "## Cómo actualizar",
            "",
            "1. Actualizar el estado de la tarea en `PLAN.md`.",
            "2. Ejecutar `python scripts/sync_todos.py`.",
            "3. Hacer commit de `PLAN.md` y `TODO.md`.",
            "",
            "Los estados permitidos son `[ ]` pendiente, `[~]` en curso, "
            "`[x]` completada y `[!]` bloqueada.",
            "",
        ]
    )

    return "\n".join(lines)


def main() -> None:
    phases = parse_plan()
    if not phases:
        raise RuntimeError("No se encontraron fases en PLAN.md.")
    with TODO_PATH.open("w", encoding="utf-8", newline="\n") as file:
        file.write(render_todo(phases))
    total = sum(len(phase.tasks) for phase in phases)
    completed = sum(phase.completed for phase in phases)
    print(f"TODO.md actualizado: {completed}/{total} tareas completadas.")


if __name__ == "__main__":
    main()
