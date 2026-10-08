"""Texto que se enseña al arrancar."""
from __future__ import annotations

from datetime import date, datetime

from continuidad_lib.tareas import Tarea, ordenar


def hace(fecha: str, hoy: str) -> str:
    try:
        dias = (date.fromisoformat(hoy) - date.fromisoformat(fecha)).days
    except ValueError:
        return ""
    if dias == 0:
        return "hoy"
    if dias == 1:
        return "ayer"
    return f"hace {dias} días"


def recortar(texto: str, n: int) -> str:
    return texto if len(texto) <= n else texto[: n - 1] + "…"


def lineas_sesion(sesion, hoy: str) -> list[str]:
    if sesion is None:
        return ["Sin resumen todavía (se creará al cerrar la jornada)"]
    marca = " (reconstruida)" if sesion.reconstruida else ""
    lineas = [f"Última sesión: {sesion.fecha} {sesion.hora}{marca} ({hace(sesion.fecha, hoy)})"]
    for seccion, maximo in (("Hecho", 3), ("Siguiente paso", None), ("A no olvidar", None), ("Decisiones", 3)):
        vinetas = sesion.vinetas(seccion)[:maximo] if maximo else sesion.vinetas(seccion)
        if vinetas:
            lineas.append(f"  {seccion}: " + "; ".join(vinetas))
    return lineas


def _vencidas(tareas: list[Tarea], hoy: str) -> int:
    return sum(1 for t in tareas if t.vencida(hoy))


def lineas_tareas(nombre: str, tareas: list[Tarea], hoy: str, maximo: int) -> list[str]:
    if not tareas:
        return [f"Tareas de {nombre}: ninguna"]
    vencidas = _vencidas(tareas, hoy)
    aviso = f": ⚠ {vencidas} vencida{'s' if vencidas != 1 else ''}" if vencidas else ""
    lineas = [f"Tareas de {nombre} ({len(tareas)}){aviso}"]
    lineas += ["  " + recortar(t.linea(), 140) for t in ordenar(tareas, hoy)[:maximo]]
    if len(tareas) > maximo:
        lineas.append(f"  … y {len(tareas) - maximo} más (/tasks-list)")
    return lineas


def lineas_rescate(transcripcion) -> list[str]:
    if transcripcion is None:
        return []
    fecha = datetime.fromtimestamp(transcripcion.mtime).strftime("%Y-%m-%d")
    return [f"⚠ La sesión del {fecha} (id {transcripcion.session_id[:8]}) no dejó resumen.",
            f"Claude: reconstrúyela con la skill journal (modo rescate) antes de seguir: {transcripcion.ruta}"]


def linea_panorama(proyecto, sesion, tareas: list[Tarea], hoy: str) -> str:
    fecha = sesion.fecha if sesion else "—"
    if sesion and sesion.vinetas("Siguiente paso"):
        siguiente = "sig.: " + recortar(sesion.vinetas("Siguiente paso")[0], 60)
    elif sesion:
        siguiente = "sin siguiente paso"
    else:
        siguiente = "sin resumen todavía"
    vencidas = _vencidas(tareas, hoy)
    cuenta = f"tareas {len(tareas)}" + (f" (⚠{vencidas})" if vencidas else "")
    return f"{recortar(proyecto.nombre, 16):<17}{fecha:<12}{siguiente:<68}{cuenta}"


def limitar(cuerpo: list[str], final: list[str], maximo: int) -> list[str]:
    """Recorta el cuerpo para que, con el final (avisos y errores), quepa en `maximo`.

    El resultado nunca supera `maximo` líneas: si `final` por sí solo ya lo alcanza o
    supera, también se recorta (quedándose con sus primeras líneas) y el cuerpo se omite.
    """
    maximo = max(maximo, 0)
    if len(final) >= maximo:
        return final[:maximo]
    hueco = maximo - len(final)
    if len(cuerpo) > hueco:
        cuerpo = cuerpo[: hueco - 1] + ["…"] if hueco > 0 else []
    return cuerpo + final
