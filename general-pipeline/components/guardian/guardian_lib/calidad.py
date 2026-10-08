"""Reglas de calidad: impide cambiar la configuración de linters/tests para que un check 'pase'."""
from __future__ import annotations

import fnmatch
import ntpath
import os
import re

from guardian_lib.nucleo import Contexto, Veredicto

PATRONES = ("ruff.toml", ".ruff.toml", "pytest.ini", "mypy.ini", ".mypy.ini", ".coveragerc",
            ".pre-commit-config.yaml", "tsconfig*.json", ".eslintrc*", "eslint.config.*",
            ".prettierrc*", "prettier.config.*")
SECCIONES = ("tool.ruff", "tool.pytest", "tool.mypy", "tool.coverage")
_CABECERA = re.compile(r"^\s*\[\[?\s*([^\]]+?)\s*\]\]?\s*(#.*)?$")


def es_fichero_de_reglas(ruta: str) -> bool:
    nombre = ntpath.basename(ruta).lower()
    return any(fnmatch.fnmatchcase(nombre, patron) for patron in PATRONES)


def secciones_calidad(texto: str) -> dict[str, list[str]]:
    """Secciones [tool.ruff*], [tool.pytest*], [tool.mypy*], [tool.coverage*] con sus líneas no vacías."""
    resultado: dict[str, list[str]] = {}
    actual = None
    for linea in texto.splitlines():
        m = _CABECERA.match(linea)
        if m:
            nombre = m.group(1).strip().lower()
            es_calidad = any(nombre == s or nombre.startswith(s + ".") for s in SECCIONES)
            actual = nombre if es_calidad else None
            if actual:
                resultado.setdefault(actual, [])
        elif actual and linea.strip():
            resultado[actual].append(linea.strip())
    return resultado


def _aplicar(texto: str | None, viejo: str, nuevo: str, todas: bool) -> str | None:
    if texto is None or viejo not in texto:
        return None
    return texto.replace(viejo, nuevo) if todas else texto.replace(viejo, nuevo, 1)


def _texto_resultante(herramienta: str, entrada: dict, actual: str) -> str | None:
    if herramienta == "Write":
        return entrada.get("content", "")
    if herramienta == "Edit":
        return _aplicar(actual, entrada.get("old_string", ""), entrada.get("new_string", ""),
                        bool(entrada.get("replace_all")))
    if herramienta == "MultiEdit":
        texto: str | None = actual
        for e in entrada.get("edits", []):
            texto = _aplicar(texto, e.get("old_string", ""), e.get("new_string", ""), bool(e.get("replace_all")))
        return texto
    return None


def fichero_de_calidad_existente(ruta: str) -> Veredicto | None:
    """Para comandos (sed -i, rm, >>, cp…): no se puede saber qué cambiará, así que basta con que el fichero
    exista y sea de reglas, o sea un pyproject.toml con secciones de calidad."""
    if not os.path.isfile(ruta):
        return None
    if es_fichero_de_reglas(ruta):
        return Veredicto("reglas-calidad", f"{ntpath.basename(ruta)} contiene reglas de calidad (linter/tests)",
                         ruta_ref=ruta)
    if ntpath.basename(ruta) == "pyproject.toml":
        with open(ruta, encoding="utf-8", errors="replace") as f:
            if secciones_calidad(f.read()):
                return Veredicto("reglas-calidad", "pyproject.toml tiene secciones [tool.ruff/pytest/mypy/coverage]"
                                 " y un comando puede cambiarlas sin que se vea qué", ruta_ref=ruta)
    return None


def comprobar_reglas_calidad(herramienta: str, entrada: dict, ruta: str, ctx: Contexto) -> Veredicto | None:
    if not os.path.isfile(ruta):
        return None  # crear la configuración por primera vez está permitido
    if es_fichero_de_reglas(ruta):
        return Veredicto("reglas-calidad", f"{ntpath.basename(ruta)} contiene reglas de calidad (linter/tests)",
                         ruta_ref=ruta)
    if ntpath.basename(ruta) == "pyproject.toml":
        with open(ruta, encoding="utf-8", errors="replace") as f:
            actual = f.read()
        nuevo = _texto_resultante(herramienta, entrada, actual)
        if nuevo is not None and secciones_calidad(actual) != secciones_calidad(nuevo):
            return Veredicto("reglas-calidad",
                             "cambia secciones [tool.ruff/pytest/mypy/coverage] de pyproject.toml", ruta_ref=ruta)
    return None
