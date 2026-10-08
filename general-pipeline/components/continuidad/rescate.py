#!/usr/bin/env python3
"""Extrae el texto de una conversación de Claude Code para reconstruir su resumen de sesión."""
from __future__ import annotations

import argparse
import sys
import tempfile
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

from continuidad_lib.config import cargar  # noqa: E402
from continuidad_lib.proyecto import proyecto_de  # noqa: E402
from continuidad_lib.transcripciones import eventos  # noqa: E402


def hora_local(ts: str) -> str:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone().strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return ""


def condensar(ruta: Path, maximo: int) -> str:
    partes: list[str] = []
    primero = ultimo = ""
    for rol, texto, ts in eventos(ruta):
        primero = primero or ts
        ultimo = ts or ultimo
        partes.append(("USUARIO" if rol == "user" else "CLAUDE") + ": " + texto)
    cuerpo = "\n\n".join(partes)
    if len(cuerpo) > maximo:
        cuerpo = "[… recortado: se muestran solo los últimos caracteres …]\n" + cuerpo[-maximo:]
    cabecera = (f"Sesión {Path(ruta).stem}\nInicio: {hora_local(primero)}\n"
                f"Última actividad: {hora_local(ultimo)}\n\n")
    return cabecera + cuerpo


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("transcripcion")
    p.add_argument("--max", type=int, default=40000)
    p.add_argument("--salida")
    args = p.parse_args(argv)
    ruta = Path(args.transcripcion)
    if args.salida:
        destino = Path(args.salida)
    else:
        config = cargar(AQUI / "continuidad.json")
        temporal = proyecto_de(Path.cwd(), config["raices"], config["solo_lectura"]).ruta / "temporal"
        destino = temporal if temporal.is_dir() else Path(tempfile.gettempdir())
    destino.mkdir(parents=True, exist_ok=True)
    salida = destino / f"rescate_{ruta.stem[:8]}.txt"
    salida.write_text(condensar(ruta, args.max), encoding="utf-8")
    print(salida)
    return 0


if __name__ == "__main__":
    sys.exit(main())
