"""Copias de seguridad, manifiesto y deshacer de instalar.py. Solo biblioteca estándar.

Una copia vive en `<home>/.claude/copias_pipeline/<AAAAMMDD_HHMMSS>[_n]/`:
- `contenido/`: toda `.claude` tal como estaba, EXCEPTO lo que la instalación nunca toca y no conviene
  duplicar: `projects/` (conversaciones), `plugins/`, `copias_pipeline/` (las propias copias),
  `file-history/`, `todos/`, `shell-snapshots/`, `debug/`, `statsig/` y `.credentials.json` (las
  credenciales no se duplican nunca).
- `manifiesto.json`: qué hizo la instalación. Claves: `tipo` ("instalacion" o "pre-deshacer"),
  `momento`, `creados`, `sobrescritos`, `borrados`, `carpetas_creadas`, `escritos` ({rel: sha256 de lo
  que escribió la instalación}) y, tras deshacer, `deshecha`.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import sys
import time
from datetime import datetime
from pathlib import Path

from instalar_lib import CARPETAS_CODIGO

EXCLUIDAS_COPIA = {"projects", "plugins", "copias_pipeline", "file-history", "todos", "shell-snapshots",
                   "debug", "statsig", ".credentials.json"}
# Lo que generan los hooks al usarse (no lo escribe instalar). deshacer NUNCA lo restaura ni lo quita:
# guardian.log es la prueba que se revisa antes de pasar guardian a modo activo.
SUBPRODUCTOS = ("hooks/guardian.log",)


def sha(datos: bytes) -> str:
    return hashlib.sha256(datos).hexdigest()


def _sha_fichero(ruta: Path) -> str | None:
    return sha(ruta.read_bytes()) if ruta.is_file() else None


def nueva_copia(claude: Path) -> Path:
    """Copia `.claude` (menos EXCLUIDAS_COPIA) en copias_pipeline/<sello>/contenido y devuelve la carpeta."""
    base = claude / "copias_pipeline"
    sello = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino, n = base / sello, 1
    while destino.exists():
        destino, n = base / f"{sello}_{n}", n + 1

    def ignorar(carpeta: str, nombres: list[str]) -> set[str]:
        return EXCLUIDAS_COPIA & set(nombres) if Path(carpeta) == claude else set()

    if claude.is_dir():
        shutil.copytree(claude, destino / "contenido", ignore=ignorar, symlinks=True)
    else:
        (destino / "contenido").mkdir(parents=True)
    return destino


def carpetas_nuevas(claude: Path, rels: list[str]) -> list[str]:
    """Carpetas (relativas) que habrá que crear para escribir `rels`, de la más profunda a la menos."""
    nuevas: set[str] = set()
    for rel in rels:
        for padre in Path(rel).parents:
            if str(padre) != "." and not (claude / padre).exists():
                nuevas.add(padre.as_posix())
    if not claude.exists():
        nuevas.add(".")
    return sorted(nuevas, key=lambda r: (-r.count("/"), r))


def escribir_manifiesto(copia: Path, manifiesto: dict) -> None:
    (copia / "manifiesto.json").write_text(json.dumps(manifiesto, indent=2, ensure_ascii=False) + "\n",
                                           encoding="utf-8")


def copias(claude: Path) -> tuple[list[tuple[Path, dict]], list[str]]:
    """(copias con manifiesto válido, de la más antigua a la más reciente; avisos de las que se saltan)."""
    base = claude / "copias_pipeline"
    resultado, avisos = [], []
    if base.is_dir():
        for carpeta in sorted(base.iterdir()):
            ruta = carpeta / "manifiesto.json"
            if not ruta.is_file():
                continue
            try:
                datos = json.loads(ruta.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
                avisos.append(f"AVISO: se salta la copia {carpeta}: su manifiesto está dañado ({error})")
                continue
            if not isinstance(datos, dict):
                avisos.append(f"AVISO: se salta la copia {carpeta}: su manifiesto no tiene el formato esperado")
                continue
            resultado.append((carpeta, datos))
    resultado.sort(key=lambda par: (par[1].get("momento", 0) if isinstance(par[1].get("momento"), (int, float))
                                    else 0, par[0].name))
    return resultado, avisos


def copia_pendiente(claude: Path) -> tuple[tuple[Path, dict] | None, list[str]]:
    """La instalación más reciente que aún no se ha deshecho (las copias pre-deshacer no cuentan)."""
    todas, avisos = copias(claude)
    pendientes = [par for par in todas
                  if par[1].get("tipo", "instalacion") == "instalacion" and not par[1].get("deshecha")]
    return (pendientes[-1] if pendientes else None), avisos


def modificados(claude: Path, copia: Path, manifiesto: dict) -> list[str]:
    """Ficheros que la instalación escribió y que alguien ha cambiado después (ni lo instalado ni lo de antes)."""
    contenido = copia / "contenido"
    cambiados = []
    escritos = manifiesto.get("escritos") if isinstance(manifiesto.get("escritos"), dict) else {}
    for rel, esperado in escritos.items():
        actual = _sha_fichero(claude / rel)
        if actual is not None and actual != esperado and actual != _sha_fichero(contenido / rel):
            cambiados.append(rel)
    return sorted(cambiados)


def copia_pre_deshacer(claude: Path, de: Path) -> Path:
    """Copia completa del estado actual antes de deshacer, para no perder nada."""
    copia = nueva_copia(claude)
    escribir_manifiesto(copia, {"tipo": "pre-deshacer", "momento": time.time(), "de": de.name})
    return copia


def _escribible(ruta: Path) -> None:
    if ruta.exists() and not os.access(ruta, os.W_OK):
        os.chmod(ruta, stat.S_IWRITE | stat.S_IREAD)


def _forzar(funcion, ruta, *_):
    os.chmod(ruta, stat.S_IWRITE | stat.S_IREAD)
    funcion(ruta)


def _rmtree(ruta: Path) -> None:
    if sys.version_info >= (3, 12):
        shutil.rmtree(ruta, onexc=_forzar)
    else:
        shutil.rmtree(ruta, onerror=_forzar)


def deshacer(claude: Path, copia: Path, manifiesto: dict) -> tuple[list[str], list[str]]:
    """Quita lo que creó la instalación y devuelve a su sitio lo que sobrescribió o borró.

    Sigue aunque falle algún fichero. Devuelve (hechos, fallos). Solo marca la copia como deshecha
    si no ha fallado nada, para poder repetir.
    """
    contenido = copia / "contenido"
    hechos: list[str] = []
    fallos: list[str] = []

    def intentar(descripcion: str, accion) -> None:
        try:
            if accion() is not False:
                hechos.append(descripcion)
        except OSError as error:
            fallos.append(f"{descripcion}: {error}")

    for rel in manifiesto.get("creados", []):
        ruta = claude / rel
        if rel not in SUBPRODUCTOS and ruta.is_file() and not (contenido / rel).exists():
            intentar(f"quitado {rel}", lambda r=ruta: (_escribible(r), r.unlink()))
    for rel in CARPETAS_CODIGO.values():
        if (claude / rel).is_dir():
            for cache in sorted((claude / rel).rglob("__pycache__")):
                if not (contenido / cache.relative_to(claude)).exists():
                    intentar(f"quitada la caché {cache.relative_to(claude).as_posix()}",
                             lambda c=cache: _rmtree(c))
    for rel in list(manifiesto.get("sobrescritos", [])) + list(manifiesto.get("borrados", [])):
        origen, destino = contenido / rel, claude / rel
        if rel in SUBPRODUCTOS or not origen.is_file():
            continue
        if destino.is_file() and destino.read_bytes() == origen.read_bytes():
            continue

        def restaurar(o=origen, d=destino):
            d.parent.mkdir(parents=True, exist_ok=True)
            _escribible(d)
            shutil.copy2(o, d)
        intentar(f"restaurado {rel}", restaurar)
    for rel in manifiesto.get("carpetas_creadas", []):
        ruta = claude / rel
        if rel != "." and ruta.is_dir():
            for cache in sorted(ruta.rglob("__pycache__"), reverse=True):
                shutil.rmtree(cache, ignore_errors=True)
            try:
                ruta.rmdir()
            except OSError:
                if any(ruta.iterdir()):
                    hechos.append(f"se deja la carpeta {rel}: tiene ficheros que no puso la instalación")
    if not fallos:
        manifiesto["deshecha"] = time.time()
        escribir_manifiesto(copia, manifiesto)
    return hechos, fallos
