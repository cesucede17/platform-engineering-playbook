#!/usr/bin/env python3
"""Arranque de sesión de Claude Code: dónde lo dejé, tareas y git de la carpeta actual.

Uso como hook SessionStart (lee JSON por stdin). Subcomandos sin stdin:
  proyecto  → etiqueta de tarea de la carpeta actual (nombre del proyecto o "general")
  ruta      → carpeta del proyecto
  ahora     → fecha y hora local (AAAA-MM-DD HH:MM), igual en Bash y PowerShell
  sesion    → id de la sesión en curso (CLAUDE_CODE_SESSION_ID; si no, transcripción más reciente)
  journal   → carpeta del journal de la carpeta actual (central si está configurada, si no <ruta>/docs/journal)
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

from continuidad_lib import git, journal, tareas as mod_tareas, transcripciones, vista  # noqa: E402
from continuidad_lib.config import cargar  # noqa: E402
from continuidad_lib.proyecto import listar_proyectos, proyecto_de  # noqa: E402

CLAUDE = Path.home() / ".claude"


def _seguro(nombre, funcion, defecto, errores: list[str]):
    try:
        return funcion()
    except Exception as error:  # una sección rota no debe tumbar el arranque
        errores.append(f"(no se pudo leer {nombre}: {type(error).__name__}: {error})")
        return defecto


def _panorama(p, todas, hoy, config, errores) -> list[str]:
    def filas() -> list[str]:
        datos = []
        for q in listar_proyectos(config["raices"], config["excluidos"]):
            s = journal.ultima_sesion(journal.carpeta(q.ruta, q.etiqueta, config))
            propias = mod_tareas.de_proyecto(todas, q.etiqueta)
            if s or propias:
                datos.append((q, s, propias))
        datos.sort(key=lambda d: (d[1].fecha, d[1].hora) if d[1] else ("", ""), reverse=True)
        datos.sort(key=lambda d: 0 if any(t.vencida(hoy) for t in d[2]) else 1)
        return [vista.linea_panorama(q, s, propias, hoy) for q, s, propias in datos]

    return _seguro("proyectos", filas, [], errores)


def arranque(cwd, session_id, config: dict, ruta_tareas: Path, dir_projects: Path, hoy: str,
             source: str | None = None) -> list[str]:
    errores: list[str] = []
    p = proyecto_de(cwd, config["raices"], config["solo_lectura"])
    secciones = config["secciones"]
    todas = _seguro("tareas", lambda: mod_tareas.leer_tareas(ruta_tareas), [], errores)
    sesiones = _seguro("journal", lambda: journal.sesiones(journal.carpeta(p.ruta, p.etiqueta, config)),
                       [], errores)
    ultima = sesiones[-1] if sesiones else None
    ids = {s.session_id for s in sesiones if s.session_id}
    rescate = None
    if source != "clear":  # tras /clear la sesión anterior es la misma conversación del usuario
        rescate = _seguro("transcripciones", lambda: transcripciones.pendiente_de_rescate(
            p.ruta, dir_projects, p.en_raiz, session_id, ultima, ids, config["min_mensajes_rescate"]),
            None, errores)

    if p.es_raiz:
        cuerpo = [f"=== {p.nombre} — panorama ==="]
        if "panorama" in secciones:
            cuerpo += _panorama(p, todas, hoy, config, errores)
        if ultima and "sesion" in secciones:
            siguiente = ultima.vinetas("Siguiente paso")
            cuerpo.append(f"Última sesión desde {p.nombre}: {ultima.fecha}"
                          + (f" — siguiente: {vista.recortar(siguiente[0], 80)}" if siguiente else ""))
        if "tareas" in secciones:
            generales = mod_tareas.de_proyecto(todas, "general")
            vencidas = sum(1 for t in generales if t.vencida(hoy))
            cuerpo.append(f"Tareas [general]: {len(generales)}" + (f" (⚠{vencidas})" if vencidas else ""))
    else:
        cuerpo = [f"=== {p.nombre} — retomando ==="]
        if "sesion" in secciones:
            cuerpo += vista.lineas_sesion(ultima, hoy)
        propias = mod_tareas.de_proyecto(todas, p.etiqueta)
        if "tareas" in secciones:
            cuerpo += vista.lineas_tareas(p.nombre, propias, hoy, config["max_tareas"])
        if "git" in secciones:
            cuerpo.append(_seguro("git", lambda: git.estado_git(p.ruta), "Git: (no disponible)", errores))
        otras = [t for t in todas if t.proyecto.lower() != p.etiqueta.lower()]
        if "otras" in secciones and otras:
            vencidas = sum(1 for t in otras if t.vencida(hoy))
            cuerpo.append(f"(Otras carpetas: {len(otras)} tareas, {vencidas} vencidas → /tasks-list)")

    final = vista.lineas_rescate(rescate) + errores + ([f"(sesión: {session_id})"] if session_id else [])
    return vista.limitar(cuerpo, final, config["max_lineas"])


def main(argv: list[str], entrada: str, ruta_config: Path, ruta_tareas: Path, dir_projects: Path,
         hoy: str | None = None) -> tuple[int, str]:
    """Devuelve (código de salida, texto). El código es siempre 0: el arranque nunca bloquea."""
    try:
        if argv[:1] == ["ahora"]:
            return 0, datetime.now().strftime("%Y-%m-%d %H:%M")
        config = cargar(ruta_config)
        if argv[:1] == ["proyecto"]:
            return 0, proyecto_de(os.getcwd(), config["raices"], config["solo_lectura"]).etiqueta
        if argv[:1] == ["ruta"]:
            return 0, str(proyecto_de(os.getcwd(), config["raices"], config["solo_lectura"]).ruta)
        if argv[:1] == ["sesion"]:
            return 0, (os.environ.get("CLAUDE_CODE_SESSION_ID")
                       or transcripciones.sesion_actual(os.getcwd(), dir_projects) or "")
        if argv[:1] == ["journal"]:
            p = proyecto_de(os.getcwd(), config["raices"], config["solo_lectura"])
            return 0, str(journal.carpeta(p.ruta, p.etiqueta, config))
        try:
            datos = json.loads(entrada) if entrada.strip() else {}
        except json.JSONDecodeError:
            datos = {}
        if not isinstance(datos, dict):
            datos = {}
        cwd = datos.get("cwd") or os.getcwd()
        lineas = arranque(cwd, datos.get("session_id"), config, ruta_tareas, dir_projects,
                          hoy or date.today().isoformat(), datos.get("source"))
        return 0, "\n".join(lineas)
    except Exception as error:
        return 0, f"(continuidad: error inesperado: {type(error).__name__}: {error})"


if __name__ == "__main__":
    try:
        argumentos = sys.argv[1:]
        texto = "" if argumentos else sys.stdin.buffer.read().decode("utf-8", errors="replace")
        _, salida = main(argumentos, texto, AQUI / "continuidad.json", CLAUDE / "TASKS.md", CLAUDE / "projects")
    except Exception as error:  # el arranque nunca debe terminar con código distinto de 0
        salida = f"(continuidad: error inesperado: {type(error).__name__}: {error})"
    if salida:
        sys.stdout.buffer.write((salida + "\n").encode("utf-8"))
    sys.exit(0)
