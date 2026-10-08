"""Lectura de docs/journal/AAAA-MM-DD.md."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

SECCIONES = ("Hecho", "Decisiones", "A no olvidar", "Siguiente paso", "Abierto")
_FICHERO = re.compile(r"^(\d{4}-\d{2}-\d{2})\.md$")
_SESION = re.compile(r"^##\s+Sesi[oó]n\s+(\d{1,2}:\d{2})\s*(\(reconstruida\))?\s*$", re.IGNORECASE)
_SECCION = re.compile(r"^###\s+(.+?)\s*$")
_ID = re.compile(r"<!--\s*sesion:\s*([0-9a-fA-F-]+)\s*-->")


@dataclass
class Sesion:
    fecha: str
    hora: str
    reconstruida: bool = False
    session_id: str | None = None
    secciones: dict[str, list[str]] = field(default_factory=dict)

    def momento(self) -> float:
        return datetime.strptime(f"{self.fecha} {self.hora}", "%Y-%m-%d %H:%M").timestamp()

    def vinetas(self, seccion: str) -> list[str]:
        return self.secciones.get(seccion, [])


def leer_fichero(ruta: Path) -> list[Sesion]:
    m = _FICHERO.match(ruta.name)
    if not m:
        return []
    fecha = m.group(1)
    leidas: list[Sesion] = []
    actual: Sesion | None = None
    seccion: str | None = None
    for linea in ruta.read_text(encoding="utf-8", errors="replace").splitlines():
        ms = _SESION.match(linea)
        if ms:
            actual = Sesion(fecha, ms.group(1).zfill(5), bool(ms.group(2)))
            leidas.append(actual)
            seccion = None
            continue
        if actual is None:
            continue
        mi = _ID.search(linea)
        if mi:
            actual.session_id = mi.group(1).lower()
            continue
        mc = _SECCION.match(linea)
        if mc:
            seccion = next((s for s in SECCIONES if s.lower() == mc.group(1).lower()), None)
            continue
        texto = linea.strip()
        if seccion and texto.startswith("- "):
            vineta = texto[2:].strip()
            if vineta and vineta.lower() != "(nada)":
                actual.secciones.setdefault(seccion, []).append(vineta)
    return leidas


def carpeta(ruta_proyecto: Path, etiqueta: str, config: dict) -> Path:
    """Carpeta donde vive el journal: la central (si está configurada) o la del proyecto."""
    central = config.get("journal_central") or ""
    if central:
        return Path(central) / etiqueta
    return Path(ruta_proyecto) / "docs" / "journal"


def sesiones(carpeta: Path) -> list[Sesion]:
    carpeta = Path(carpeta)
    if not carpeta.is_dir():
        return []
    todas = [s for f in carpeta.iterdir() if f.is_file() for s in leer_fichero(f)]
    return sorted(todas, key=lambda s: (s.fecha, s.hora))


def ultima_sesion(carpeta: Path) -> Sesion | None:
    todas = sesiones(carpeta)
    return todas[-1] if todas else None
