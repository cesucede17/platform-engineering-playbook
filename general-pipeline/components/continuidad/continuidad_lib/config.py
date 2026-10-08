"""Configuración de continuidad (continuidad.json) con valores por defecto."""
from __future__ import annotations

import json
from pathlib import Path

DEFECTO = {
    "raices": [],
    "excluidos": ["OBSOLETO", "temporal", "docs", "claude", "guias"],
    "max_lineas": 40,
    "max_tareas": 8,
    "min_mensajes_rescate": 10,
    "solo_lectura": [],  # repos externos: dentro de ellos se usa la raíz (nunca se escribe en ellos)
    "secciones": ["sesion", "tareas", "git", "otras", "panorama"],  # bloques del arranque a enseñar
    "journal_central": "",  # vacío: el journal va en <proyecto>/docs/journal; si no, <journal_central>/<etiqueta>
}


def cargar(ruta: Path) -> dict:
    datos = dict(DEFECTO)
    try:
        cargado = json.loads(Path(ruta).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return datos  # sin configuración válida se usan los valores por defecto
    if isinstance(cargado, dict):
        datos.update(cargado)
    return datos  # un JSON válido mas no-objeto (p.ej. una lista) también usa los valores por defecto
