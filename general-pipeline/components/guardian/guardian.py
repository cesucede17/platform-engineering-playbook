#!/usr/bin/env python3
"""guardian: vigilante PreToolUse de Claude Code. Ver README.md (instalado como guardian_README.md)."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

try:
    from guardian_lib import registro
    from guardian_lib.archivos import evaluar_archivo
    from guardian_lib.comandos import evaluar_comando
    from guardian_lib.nucleo import DESACTIVABLES, Contexto, Veredicto, resolver
except Exception as error:  # instalación rota: ante la duda, quieto
    sys.stderr.write(f"[guardian] no puede cargarse ({error}); por precaución se bloquea la acción.\n")
    sys.exit(2)

HERRAMIENTAS_ARCHIVO = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
HERRAMIENTAS_COMANDO = {"Bash", "PowerShell"}
AVISOS_UV = (("pip install", "uv add (o uv pip install)"), ("pip3 install", "uv add (o uv pip install)"),
             ("python -m pytest", "uv run pytest"))


def evaluar(entrada: dict, reglas: dict, ahora: float) -> list[Veredicto]:
    herramienta = entrada.get("tool_name", "")
    datos = entrada.get("tool_input") or {}
    ctx = Contexto.crear(reglas, entrada.get("cwd") or os.getcwd(), ahora)
    if herramienta in HERRAMIENTAS_ARCHIVO:
        veredictos = evaluar_archivo(herramienta, datos, ctx)
    elif herramienta in HERRAMIENTAS_COMANDO:
        shell = "powershell" if herramienta == "PowerShell" else "bash"
        veredictos = evaluar_comando(datos.get("command", ""), ctx, shell)
    else:
        veredictos = []
    resueltos = [resolver(v, ctx) for v in veredictos]
    desactivadas = set(reglas.get("desactivadas", [])) & DESACTIVABLES
    return [v for v in resueltos if v.regla not in desactivadas]


def mensaje(v: Veredicto, horas: float) -> str:
    texto = f"[guardian] BLOQUEADO [{v.regla}]: {v.motivo}."
    if v.regla == "reglas-calidad":
        texto += " Corrige el código en vez de cambiar las reglas de calidad."
    carpeta = v.carpeta_sugerida()
    if v.desbloqueable and carpeta:
        texto += (f" Si de verdad hace falta, explica al usuario por qué y pídele que cree a mano un fichero"
                  f" .claude-unlock en {carpeta} (caduca en {horas:g} h). No intentes crearlo ni esquivar el bloqueo.")
    else:
        texto += " Esta acción no se puede desbloquear."
    return texto


def avisos_uv(comando: str) -> list[str]:
    if "uv " in comando:
        return []
    return [f"Sugerencia: considera usar '{bueno}' en vez de '{malo}'." for malo, bueno in AVISOS_UV if malo in comando]


def main(texto_entrada: str, ruta_reglas: Path, ruta_log: Path, ahora: float | None = None) -> tuple[int, str]:
    """Devuelve (código de salida, texto para stderr). 0 = permitir, 2 = bloquear."""
    ahora = time.time() if ahora is None else ahora
    modo, herramienta, resumen, carpeta = "activo", "?", "", ""
    try:
        reglas = json.loads(ruta_reglas.read_text(encoding="utf-8"))
        modo = reglas.get("modo", "activo")
        entrada = json.loads(texto_entrada)
        herramienta = entrada.get("tool_name", "?")
        datos = entrada.get("tool_input") or {}
        resumen = datos.get("command") or datos.get("file_path") or datos.get("notebook_path") or ""
        carpeta = entrada.get("cwd", "")
        veredictos = evaluar(entrada, reglas, ahora)
    except Exception as error:
        registro.escribir(ruta_log, "ERROR", herramienta, f"{type(error).__name__}: {error} | {resumen}",
                          carpeta, "fallo-guardian", ahora)
        if modo == "prueba":
            return 0, ""
        return 2, (f"[guardian] error interno ({type(error).__name__}: {error}). Por precaución se bloquea la"
                   " acción; avisa al usuario.")

    for v in veredictos:
        if not v.bloquea:
            registro.escribir(ruta_log, "DESBLOQUEO USADO", herramienta, resumen, v.desbloqueado_en or "", v.regla,
                              ahora)
    bloqueos = [v for v in veredictos if v.bloquea]
    duros = [v for v in bloqueos if v.siempre or modo != "prueba"]
    for v in bloqueos:
        tipo = "BLOQUEADO" if v in duros else "HABRÍA BLOQUEADO"
        registro.escribir(ruta_log, tipo, herramienta, resumen, carpeta, v.regla, ahora)
    if duros:
        horas = float(reglas.get("caducidad_desbloqueo_horas", 2))
        return 2, "\n".join(mensaje(v, horas) for v in duros)
    if herramienta in HERRAMIENTAS_COMANDO:
        return 0, "\n".join(avisos_uv(str(resumen)))
    return 0, ""


if __name__ == "__main__":
    codigo, salida = main(sys.stdin.buffer.read().decode("utf-8", errors="replace"),
                          AQUI / "guardian_reglas.json", AQUI / "guardian.log")
    if salida:
        sys.stderr.buffer.write((salida + "\n").encode("utf-8"))
    sys.exit(codigo)
