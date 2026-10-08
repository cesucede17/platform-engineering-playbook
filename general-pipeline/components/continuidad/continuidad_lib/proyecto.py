"""Qué proyecto corresponde a una carpeta de trabajo."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Proyecto:
    nombre: str
    ruta: Path
    es_raiz: bool
    en_raiz: bool = False  # hijo de una raíz (y no proyecto suelto fuera de ellas)

    @property
    def etiqueta(self) -> str:
        return "general" if self.es_raiz else self.nombre


def real(ruta: str | Path) -> Path:
    """Ruta absoluta con el nombre real de cada carpeta (expande nombres cortos 8.3)."""
    return Path(os.path.realpath(str(ruta)))


def _clave(ruta: Path) -> str:
    return os.path.normcase(str(ruta)).rstrip("\\/")


def _dentro(clave: str, clave_base: str) -> bool:
    return clave == clave_base or clave.startswith(clave_base + os.sep)


def _raiz_de_solo_lectura(actual: Path, raices: list[str], solo_lectura: list[str]) -> Proyecto | None:
    """Una carpeta dentro de un repo de solo lectura cuenta como la raíz que lo contiene."""
    clave = _clave(actual)
    for ruta in (real(s) for s in solo_lectura):
        if not _dentro(clave, _clave(ruta)):
            continue
        for raiz in sorted((real(r) for r in raices), key=lambda r: -len(str(r))):
            if _clave(ruta).startswith(_clave(raiz) + os.sep):
                return Proyecto(raiz.name, raiz, True)
        return Proyecto(ruta.parent.name, ruta.parent, True)  # sin raíz: su carpeta madre
    return None


def proyecto_de(cwd: str | Path, raices: list[str], solo_lectura: list[str] = ()) -> Proyecto:
    actual = real(cwd)
    clave = _clave(actual)
    protegido = _raiz_de_solo_lectura(actual, raices, list(solo_lectura))
    if protegido:
        return protegido
    for raiz in sorted((real(r) for r in raices), key=lambda r: -len(str(r))):
        clave_raiz = _clave(raiz)
        if clave == clave_raiz:
            return Proyecto(raiz.name, raiz, True)
        if clave.startswith(clave_raiz + os.sep):
            ruta = Path(*actual.parts[: len(raiz.parts) + 1])
            return Proyecto(ruta.name, ruta, False, True)
    for carpeta in (actual, *actual.parents):
        if (carpeta / ".git").exists():
            return Proyecto(carpeta.name, carpeta, False)
    return Proyecto(actual.name, actual, False)


def listar_proyectos(raices: list[str], excluidos: list[str]) -> list[Proyecto]:
    claves_raiz = {_clave(real(r)) for r in raices}
    fuera = {e.lower() for e in excluidos}
    proyectos: list[Proyecto] = []
    for raiz in (real(r) for r in raices):
        if not raiz.is_dir():
            continue
        for hijo in sorted(raiz.iterdir(), key=lambda p: p.name.lower()):
            if (not hijo.is_dir() or hijo.name.startswith(".") or hijo.name.lower() in fuera
                    or _clave(hijo) in claves_raiz):
                continue
            proyectos.append(Proyecto(hijo.name, hijo, False))
    return proyectos
