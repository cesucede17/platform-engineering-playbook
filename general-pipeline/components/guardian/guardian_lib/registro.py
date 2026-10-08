"""Registro de bloqueos, desbloqueos y errores de guardian."""
from __future__ import annotations

import time
from pathlib import Path

MAX_BYTES = 1_000_000


def escribir(ruta_log: Path, tipo: str, herramienta: str, resumen: str, carpeta: str, regla: str,
             ahora: float) -> None:
    resumen = " ".join(str(resumen).split())[:200]
    fecha = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ahora))
    linea = f"{fecha} | {tipo} | {herramienta} | {resumen} | {carpeta} | {regla}\n"
    try:
        if ruta_log.exists() and ruta_log.stat().st_size > MAX_BYTES:
            ruta_log.replace(ruta_log.with_name(ruta_log.name + ".1"))
        with ruta_log.open("a", encoding="utf-8") as f:
            f.write(linea)
    except OSError:
        pass  # el log nunca debe impedir que el vigilante responda
