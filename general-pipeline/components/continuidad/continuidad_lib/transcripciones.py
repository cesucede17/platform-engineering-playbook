"""Transcripciones de Claude Code en ~/.claude/projects/<slug>/<session_id>.jsonl."""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from continuidad_lib.proyecto import real

_NO_SLUG = re.compile(r"[^A-Za-z0-9]")  # regla de Claude Code: todo lo demás (tildes incluidas) → "-"
_RUIDO_USUARIO = ("<command-", "<local-command", "<system-reminder")
_RECORDATORIO_SISTEMA = re.compile(r"<system-reminder>.*?</system-reminder>", re.DOTALL)
MARGEN_SEGUNDOS = 3600  # la sesión sigue viva un rato después de escribir su resumen
RECIENTE_SEGUNDOS = 900  # modificada hace menos: probablemente abierta en otra ventana
RESCATE_MAX_DIAS = 14  # sin journal (primera instalación) no se rescata nada más antiguo


@dataclass
class Transcripcion:
    ruta: Path
    session_id: str
    mtime: float


def slug(ruta: Path | str) -> str:
    """Nombre de carpeta que usa Claude Code para las transcripciones de una ruta."""
    return _NO_SLUG.sub("-", str(ruta))


def _hermanos_con_prefijo(ruta_proyecto: Path, base: str) -> list[str]:
    """Slugs de las carpetas hermanas cuyo slug empieza por el del proyecto + "-"."""
    try:
        hermanas = [h for h in ruta_proyecto.parent.iterdir() if h.is_dir()]
    except OSError:
        return []
    slugs = (slug(h).lower() for h in hermanas if h.name.lower() != ruta_proyecto.name.lower())
    return [s for s in slugs if s.startswith(base + "-")]


def transcripciones(ruta_proyecto: Path, dir_projects: Path, con_subcarpetas: bool) -> list[Transcripcion]:
    base = slug(ruta_proyecto).lower()
    encontradas: list[Transcripcion] = []
    if not Path(dir_projects).is_dir():
        return encontradas
    otros = _hermanos_con_prefijo(Path(ruta_proyecto), base) if con_subcarpetas else []
    for carpeta in Path(dir_projects).iterdir():
        nombre = carpeta.name.lower()
        if not carpeta.is_dir():
            continue
        if not (nombre == base or (con_subcarpetas and nombre.startswith(base + "-"))):
            continue
        if nombre != base and any(nombre == o or nombre.startswith(o + "-") for o in otros):
            continue  # es de otro proyecto (p. ej. "proyecto-extra" respecto a "proyecto")
        for f in carpeta.glob("*.jsonl"):
            encontradas.append(Transcripcion(f, f.stem.lower(), f.stat().st_mtime))
    return encontradas


def _bloques(mensaje: object) -> list[dict]:
    contenido = mensaje.get("content") if isinstance(mensaje, dict) else None
    if isinstance(contenido, str):
        return [{"type": "text", "text": contenido}]
    if isinstance(contenido, list):
        return [b for b in contenido if isinstance(b, dict)]
    return []


def eventos(ruta: Path) -> Iterator[tuple[str, str, str]]:
    """(rol, texto, timestamp) de cada mensaje con texto, sin herramientas ni avisos del sistema."""
    with Path(ruta).open(encoding="utf-8", errors="replace") as f:
        for linea in f:
            try:
                obj = json.loads(linea)
            except json.JSONDecodeError:
                continue
            if not isinstance(obj, dict):
                continue
            tipo = obj.get("type")
            if tipo not in ("user", "assistant") or obj.get("isMeta"):
                continue
            bloques = _bloques(obj.get("message"))
            if any(b.get("type") == "tool_result" for b in bloques):
                continue
            texto = "\n".join(str(b.get("text", "")) for b in bloques if b.get("type") == "text").strip()
            texto = _RECORDATORIO_SISTEMA.sub("", texto).strip()
            if not texto or (tipo == "user" and texto.startswith(_RUIDO_USUARIO)):
                continue
            yield tipo, texto, str(obj.get("timestamp", ""))


def mensajes_usuario(ruta: Path, hasta: int | None = None) -> int:
    """Cuenta mensajes de usuario; si se da `hasta`, se detiene en cuanto se alcanza (sin leer el resto)."""
    contador = 0
    for rol, _, _ in eventos(ruta):
        if rol == "user":
            contador += 1
            if hasta is not None and contador >= hasta:
                break
    return contador


def pendiente_de_rescate(ruta_proyecto: Path, dir_projects: Path, con_subcarpetas: bool,
                         session_actual: str | None, ultima, ids_registrados: set[str],
                         min_mensajes: int, ahora: float | None = None) -> Transcripcion | None:
    ahora = time.time() if ahora is None else ahora
    actual = (session_actual or "").lower()
    candidatas = [t for t in transcripciones(ruta_proyecto, dir_projects, con_subcarpetas)
                  if t.session_id != actual and t.mtime <= ahora - RECIENTE_SEGUNDOS]
    if not candidatas:
        return None
    t = max(candidatas, key=lambda x: x.mtime)
    if t.session_id in {i.lower() for i in ids_registrados}:
        return None
    if ultima is not None:
        return t if t.mtime > ultima.momento() + MARGEN_SEGUNDOS else None
    if t.mtime < ahora - RESCATE_MAX_DIAS * 86400:
        return None
    return t if mensajes_usuario(t.ruta, min_mensajes) >= min_mensajes else None


def sesion_actual(cwd: Path | str, dir_projects: Path) -> str | None:
    """Id de la transcripción más reciente de esa carpeta exacta (la de la sesión en curso)."""
    propias = transcripciones(real(cwd), dir_projects, False)
    return max(propias, key=lambda x: x.mtime).session_id if propias else None
