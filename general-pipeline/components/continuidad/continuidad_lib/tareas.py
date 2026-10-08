"""Lectura de ~/.claude/TASKS.md (formato: - [ ] (FECHA) [proyecto] Descripción #prioridad)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_LINEA = re.compile(r"^- \[ \] \((?P<fecha>[^)]*)\) \[(?P<proyecto>[^\]]+)\] (?P<texto>.*)$")
_PRIORIDAD = re.compile(r"\s*#(alta|media|baja)\s*$")


@dataclass
class Tarea:
    fecha: str
    proyecto: str
    texto: str
    prioridad: str

    def vencida(self, hoy: str) -> bool:
        return self.fecha != "sin-fecha" and self.fecha < hoy

    def linea(self) -> str:
        sufijo = f" #{self.prioridad}" if self.prioridad else ""
        return f"- [ ] ({self.fecha}) {self.texto}{sufijo}"


def leer_tareas(ruta: Path) -> list[Tarea]:
    ruta = Path(ruta)
    if not ruta.is_file():
        return []
    leidas = []
    for linea in ruta.read_text(encoding="utf-8", errors="replace").splitlines():
        m = _LINEA.match(linea.strip())
        if not m:
            continue
        texto = m.group("texto")
        mp = _PRIORIDAD.search(texto)
        prioridad = mp.group(1) if mp else ""
        if mp:
            texto = texto[: mp.start()]
        leidas.append(Tarea(m.group("fecha").strip(), m.group("proyecto").strip(), texto.strip(), prioridad))
    return leidas


def de_proyecto(tareas: list[Tarea], etiqueta: str) -> list[Tarea]:
    return [t for t in tareas if t.proyecto.lower() == etiqueta.lower()]


def ordenar(tareas: list[Tarea], hoy: str) -> list[Tarea]:
    def clave(t: Tarea) -> tuple[int, str]:
        if t.fecha == "sin-fecha":
            return (3, "")
        if t.fecha < hoy:
            return (0, t.fecha)
        if t.fecha == hoy:
            return (1, t.fecha)
        return (2, t.fecha)
    return sorted(tareas, key=clave)
