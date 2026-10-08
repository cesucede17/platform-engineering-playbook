"""Evaluación de las herramientas que escriben ficheros: Edit, Write, MultiEdit y NotebookEdit."""
from __future__ import annotations

import ntpath

from guardian_lib.calidad import comprobar_reglas_calidad
from guardian_lib.nucleo import NOMBRE_DESBLOQUEO, Contexto, Veredicto, raiz_autoprotegida, ruta_protegida


def evaluar_archivo(herramienta: str, entrada: dict, ctx: Contexto) -> list[Veredicto]:
    bruta = entrada.get("file_path") or entrada.get("notebook_path") or ""
    if not bruta:
        return []
    ruta = ctx.ruta(bruta)
    # Sin distinguir mayúsculas aunque Linux sí lo haga en el sistema de ficheros: ".CLAUDE-UNLOCK"
    # es igual de sospechoso que ".claude-unlock" y el bloqueo no depende de si llegaría a
    # funcionar como desbloqueo real.
    # Texto literal Y ruta resuelta: un enlace con ese nombre que apunte a otro sitio pierde el nombre al
    # resolverse, y un nombre corto 8.3 solo lo desvela la ruta real. Vale también como carpeta o con punto final.
    if NOMBRE_DESBLOQUEO in ruta.lower() or NOMBRE_DESBLOQUEO in bruta.lower():
        return [Veredicto("desbloqueo", "el fichero .claude-unlock solo lo gestiona el usuario a mano",
                          desbloqueable=False, siempre=True)]
    raiz = raiz_autoprotegida(ruta, ctx)
    if raiz:
        return [Veredicto("autoproteccion", f"{bruta} es configuración de Claude Code o del propio vigilante",
                          carpeta_exacta=raiz, siempre=True)]
    veredictos = []
    protegida = ruta_protegida(ruta, ctx)
    if protegida:
        veredictos.append(Veredicto("ruta-protegida", f"{bruta} está dentro de una ruta protegida ({protegida})",
                                    ruta_ref=ruta))
    calidad = comprobar_reglas_calidad(herramienta, entrada, ruta, ctx)
    if calidad:
        veredictos.append(calidad)
    return veredictos
