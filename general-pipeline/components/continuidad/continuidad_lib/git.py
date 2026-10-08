"""Estado de git de una carpeta, en una línea."""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

PRESUPUESTO_SEGUNDOS = 4.0  # tiempo máximo total para todas las llamadas a git, no por llamada


def _git(ruta: Path, *args: str, limite: float) -> subprocess.CompletedProcess:
    tiempo = limite - time.monotonic()
    if tiempo <= 0:
        raise subprocess.TimeoutExpired(cmd=["git", *args], timeout=0)
    return subprocess.run(["git", "-C", str(ruta), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=tiempo)


def estado_git(ruta: Path) -> str:
    limite = time.monotonic() + PRESUPUESTO_SEGUNDOS
    try:
        dentro = _git(ruta, "rev-parse", "--is-inside-work-tree", limite=limite)
        if dentro.returncode != 0 or dentro.stdout.strip() != "true":
            return "Git: sin repositorio"
        rama = _git(ruta, "branch", "--show-current", limite=limite).stdout.strip() or "(sin rama)"
        cambios = sum(1 for l in _git(ruta, "status", "--porcelain", limite=limite).stdout.splitlines() if l.strip())
        ultimo = _git(ruta, "log", "-1", "--date=short", "--format=%cd: «%s»", limite=limite).stdout.strip() or "sin commits"
        return f"Git: rama {rama} | {cambios} cambios sin guardar | último commit {ultimo}"
    except subprocess.TimeoutExpired:
        return "Git: (no disponible: tiempo agotado)"
