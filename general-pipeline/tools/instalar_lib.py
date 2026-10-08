"""Piezas de instalar.py: plan de ficheros, fusión de settings.json, bloque de CLAUDE.md, TASKS.md,
copias de seguridad con manifiesto, deshacer y detección del equipo. Solo biblioteca estándar.

Todas las rutas relativas (`rel`) son relativas a `<home>/.claude` y usan `/`.
"""
from __future__ import annotations

import difflib
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

import plantillas

MARCA_INICIO = "<!-- pipeline:inicio -->"
MARCA_FIN = "<!-- pipeline:fin -->"
MATCHER_GUARDIAN = "Bash|PowerShell|Edit|Write|MultiEdit|NotebookEdit"
MATCHER_CONTINUIDAD = "startup|clear"
LANZADOR = 'python "$HOME/.claude/'
CONFIG_GUARDIAN = "hooks/guardian_reglas.json"
CONFIG_CONTINUIDAD = "scripts/continuidad/continuidad.json"
# Mismo contrato que guardian/instalar.py y guardian_lib/nucleo.py: una vez guardian está
# instalado, instalar/deshacer no tocan nada sin un desbloqueo vigente (guardian_lib/comandos.py
# exime "instalar.py" de su autoprotección precisamente porque esto lo comprueba él mismo).
NOMBRE_DESBLOQUEO = ".claude-unlock"
CADUCIDAD_DESBLOQUEO_POR_DEFECTO = 2.0
AVISO_DESBLOQUEO = (
    'guardian ya está instalado. Para actualizar esta instalación o deshacerla, la PERSONA (nunca '
    'Claude) debe crear a mano el fichero de desbloqueo ".claude-unlock" en ~/.claude/ (ver '
    'hooks/guardian_README.md). Claude no debe crear ese fichero por su cuenta.'
)
# Carpetas de código que se sustituyen enteras: lo que sobre de una versión anterior se borra.
CARPETAS_CODIGO = {"guardian/guardian_lib": "hooks/guardian_lib",
                   "continuidad/continuidad_lib": "scripts/continuidad/continuidad_lib"}
# Ficheros sueltos: origen dentro de componentes/ -> destino dentro de .claude.
FICHEROS = {
    "guardian/guardian.py": "hooks/guardian.py",
    "guardian/README.md": "hooks/guardian_README.md",
    "continuidad/continuidad.py": "scripts/continuidad/continuidad.py",
    "continuidad/rescate.py": "scripts/continuidad/rescate.py",
    "continuidad/README.md": "scripts/continuidad/README.md",
    "continuidad/skill_journal/SKILL.md": "skills/journal/SKILL.md",
    "continuidad/comandos/tasks.md": "commands/tasks.md",
    "continuidad/comandos/tasks-list.md": "commands/tasks-list.md",
    "continuidad/comandos/tasks-done.md": "commands/tasks-done.md",
    "continuidad/comandos/tasks-edit.md": "commands/tasks-edit.md",
    "explica/explica.md": "commands/explica.md",
    "mejorar_pipeline/SKILL.md": "skills/mejorar-pipeline/SKILL.md",
}


class ErrorInstalacion(Exception):
    """Error con un mensaje sencillo para la persona que instala."""


def _ignorable(ruta: Path) -> bool:
    return "__pycache__" in ruta.parts or ruta.suffix == ".pyc" or ruta.suffix == ".log"


# ---------------------------------------------------------------- plantillas y componentes

def rellenar_plantillas(dir_plantillas: Path, perfil: dict) -> dict[str, str]:
    """Las 4 plantillas rellenadas: {nombre: texto}. Lanza ErrorInstalacion si algo falla."""
    try:
        valores = plantillas.valores_desde_perfil(perfil)
    except (KeyError, ValueError) as error:
        raise ErrorInstalacion(f"el perfil no es válido: {error}") from error
    resultado = {}
    for nombre in ("guardian_reglas.json", "continuidad.json", "TASKS.md", "bloque_claude.md"):
        ruta = dir_plantillas / nombre
        if not ruta.is_file():
            raise ErrorInstalacion(f"no encuentro la plantilla {ruta}")
        try:
            texto = plantillas.rellenar(ruta.read_text(encoding="utf-8"), valores,
                                        json_strings=nombre.endswith(".json"))
        except KeyError as error:
            raise ErrorInstalacion(f"a la plantilla {nombre} le falta el valor {error}") from error
        if nombre.endswith(".json"):
            try:
                json.loads(texto)
            except json.JSONDecodeError as error:
                raise ErrorInstalacion(f"la plantilla {nombre} rellenada no es JSON válido: {error}") from error
        resultado[nombre] = texto
    return resultado


def ficheros_componentes(componentes: Path, python: str) -> dict[str, bytes]:
    """{rel destino: contenido} de todos los componentes, con el lanzador ya sustituido en los .md."""
    resultado: dict[str, bytes] = {}
    for origen, destino in FICHEROS.items():
        ruta = componentes / origen
        if not ruta.is_file():
            raise ErrorInstalacion(f"falta el componente {ruta}")
        datos = ruta.read_bytes()
        if destino.endswith(".md") and python != "python":
            datos = datos.replace(LANZADOR.encode(), f'{python} "$HOME/.claude/'.encode())
        resultado[destino] = datos
    for origen, destino in CARPETAS_CODIGO.items():
        carpeta = componentes / origen
        if not carpeta.is_dir():
            raise ErrorInstalacion(f"falta la carpeta de componentes {carpeta}")
        for ruta in sorted(carpeta.rglob("*")):
            if ruta.is_file() and not _ignorable(ruta):
                resultado[f"{destino}/{ruta.relative_to(carpeta).as_posix()}"] = ruta.read_bytes()
    return resultado


def guardian_reglas_con_modo_conservado(ruta: Path, nuevo: str) -> tuple[str, str | None]:
    """Al reconfigurar, `nuevo` (recién generado desde la plantilla) trae "modo": "prueba". Si
    `ruta` (el guardian_reglas.json ya instalado) tiene un "modo" legible, se mantiene en el
    resultado (el resto del fichero sí se regenera desde la plantilla). Si `ruta` no se puede
    leer o no es JSON válido, se usa `nuevo` tal cual. Devuelve (texto final, modo conservado o
    None si no había nada que conservar)."""
    try:
        actual = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return nuevo, None
    if not isinstance(actual, dict) or not isinstance(actual.get("modo"), str):
        return nuevo, None
    datos_nuevo = json.loads(nuevo)
    datos_nuevo["modo"] = actual["modo"]
    return json.dumps(datos_nuevo, indent=2, ensure_ascii=False) + "\n", actual["modo"]


def sobrantes_codigo(claude: Path, nuevos: dict[str, bytes]) -> list[str]:
    """Ficheros de una instalación anterior en las carpetas de código que ya no vienen."""
    sobran = []
    for destino in CARPETAS_CODIGO.values():
        carpeta = claude / destino
        if carpeta.is_dir():
            for ruta in sorted(carpeta.rglob("*")):
                rel = ruta.relative_to(claude).as_posix()
                if ruta.is_file() and not _ignorable(ruta) and rel not in nuevos:
                    sobran.append(rel)
    return sobran


# ---------------------------------------------------------------- settings.json

def comando_hook(python: str, script: str) -> str:
    return f'{python} "$HOME/.claude/{script}"'


def leer_settings(ruta: Path) -> tuple[str, dict]:
    if not ruta.exists():
        return "", {}
    texto = ruta.read_text(encoding="utf-8-sig")
    try:
        datos = json.loads(texto) if texto.strip() else {}
    except json.JSONDecodeError as error:
        raise ErrorInstalacion(f"{ruta} no es JSON válido ({error}); corrígelo antes de instalar") from error
    if not isinstance(datos, dict):
        raise ErrorInstalacion(f"{ruta} no contiene un objeto JSON; corrígelo antes de instalar")
    return texto, datos


def tiene_hook(entradas: list, fragmento: str) -> bool:
    for entrada in entradas:
        for hook in (entrada.get("hooks") or []) if isinstance(entrada, dict) else []:
            if isinstance(hook, dict) and fragmento in str(hook.get("command", "")):
                return True
    return False


def fusionar_settings(datos: dict, python: str) -> tuple[dict, bool]:
    """Añade los dos hooks si no están. Devuelve (datos nuevos, si ha cambiado algo)."""
    nuevos = json.loads(json.dumps(datos))
    hooks = nuevos.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ErrorInstalacion('en settings.json, "hooks" no es un objeto; corrígelo antes de instalar')
    cambiado = False
    for evento, matcher, script, fragmento in (
            ("PreToolUse", MATCHER_GUARDIAN, "hooks/guardian.py", "guardian.py"),
            ("SessionStart", MATCHER_CONTINUIDAD, "scripts/continuidad/continuidad.py", "continuidad.py")):
        entradas = hooks.setdefault(evento, [])
        if not isinstance(entradas, list):
            raise ErrorInstalacion(f'en settings.json, "hooks.{evento}" no es una lista; corrígelo antes de instalar')
        if not tiene_hook(entradas, fragmento):
            entradas.append({"matcher": matcher,
                             "hooks": [{"type": "command", "command": comando_hook(python, script)}]})
            cambiado = True
    return nuevos, cambiado


def texto_settings(datos: dict) -> str:
    return json.dumps(datos, indent=2, ensure_ascii=False) + "\n"


def diferencia(antes: str, despues: str, nombre: str) -> str:
    lineas = difflib.unified_diff(antes.splitlines(keepends=True), despues.splitlines(keepends=True),
                                  fromfile=f"{nombre} (ahora)", tofile=f"{nombre} (después)")
    return "".join(lineas)


# ---------------------------------------------------------------- CLAUDE.md y TASKS.md

def fusionar_claude_md(actual: str | None, bloque: str) -> str:
    """Sustituye el bloque entre marcas, o lo añade al final si no está."""
    bloque = bloque.strip("\n")
    if actual is None or not actual.strip():
        return bloque + "\n"
    salto = "\r\n" if "\r\n" in actual else "\n"
    bloque = bloque.replace("\n", salto)
    inicio, fin = actual.find(MARCA_INICIO), actual.find(MARCA_FIN)
    if inicio == -1 and fin == -1:
        separador = "" if actual.endswith(salto) else salto
        return actual + separador + salto + bloque + salto
    if inicio == -1 or fin == -1 or fin < inicio:
        raise ErrorInstalacion("CLAUDE.md tiene solo una de las marcas del bloque (o en mal orden); "
                               "arréglalo a mano antes de instalar")
    return actual[:inicio] + bloque + actual[fin + len(MARCA_FIN):]


def _tarea_guardian(plantilla_tasks: str) -> str:
    for linea in plantilla_tasks.splitlines():
        if linea.startswith("- [") and "guardian.log" in linea:
            return linea
    raise ErrorInstalacion("la plantilla TASKS.md no tiene la tarea de guardian")


def fusionar_tasks(actual: str | None, plantilla_tasks: str) -> str:
    if actual is None:
        return plantilla_tasks
    if "guardian.log" in actual:
        return actual
    salto = "\r\n" if "\r\n" in actual else "\n"
    separador = "" if not actual or actual.endswith(("\n", "\r\n")) else salto
    return actual + separador + _tarea_guardian(plantilla_tasks) + salto


# ---------------------------------------------------------------- lectura

def leer_texto(ruta: Path) -> str | None:
    return ruta.read_bytes().decode("utf-8") if ruta.is_file() else None


# ---------------------------------------------------------------- desbloqueo de guardian

def guardian_instalado(claude: Path) -> bool:
    return (claude / "hooks" / "guardian.py").is_file()


def caducidad_desbloqueo_horas(claude: Path) -> float:
    """Horas de vigencia del desbloqueo: las de `guardian_reglas.json` si se puede leer (mismo
    campo que usa guardian), si no las 2 horas de siempre."""
    try:
        datos = json.loads((claude / CONFIG_GUARDIAN).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return CADUCIDAD_DESBLOQUEO_POR_DEFECTO
    valor = datos.get("caducidad_desbloqueo_horas") if isinstance(datos, dict) else None
    try:
        return float(valor) if valor is not None else CADUCIDAD_DESBLOQUEO_POR_DEFECTO
    except (TypeError, ValueError):
        return CADUCIDAD_DESBLOQUEO_POR_DEFECTO


def desbloqueo_vigente(claude: Path) -> bool:
    fichero = claude / NOMBRE_DESBLOQUEO
    try:
        if not fichero.is_file():
            return False
        mtime = fichero.stat().st_mtime
    except OSError:
        return False
    return time.time() - mtime <= caducidad_desbloqueo_horas(claude) * 3600


def requiere_desbloqueo(claude: Path) -> bool:
    """True si guardian ya está instalado y no hay un `.claude-unlock` vigente: instalar/deshacer
    no deben escribir nada (la primera instalación, con guardian aún sin instalar, no entra aquí)."""
    return guardian_instalado(claude) and not desbloqueo_vigente(claude)


# ---------------------------------------------------------------- detectar

def _version_python(nombre: str) -> bool:
    ejecutable = shutil.which(nombre)
    if not ejecutable:
        return False
    try:
        salida = subprocess.run([ejecutable, "--version"], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return False
    coincidencia = re.search(r"Python (\d+)\.(\d+)", salida.stdout + salida.stderr)
    return salida.returncode == 0 and bool(coincidencia) and \
        (int(coincidencia.group(1)), int(coincidencia.group(2))) >= (3, 10)


def _ruta_larga(ruta: Path) -> str:
    """Forma larga de `ruta`, con `/`. En Windows, una ruta puede venir con un nombre corto 8.3
    (p. ej. `C:/Users/NOMBRE~1/...`, habitual bajo %TEMP%); `os.path.realpath` lo deshace, al
    contrario que `Path.resolve()`, que no lo toca."""
    return Path(os.path.realpath(ruta)).as_posix()


def _protegidos(raiz: Path, nivel: int, encontrados: list[str]) -> None:
    if nivel > 3:
        return
    try:
        hijas = sorted(p for p in raiz.iterdir() if p.is_dir())
    except OSError:
        return
    for hija in hijas:
        if hija.name.startswith(".") or hija.name in ("node_modules", "__pycache__"):
            continue
        if hija.name in ("OBSOLETO", "obsoleto") or (hija.name == "raw" and raiz.name == "data"):
            encontrados.append(_ruta_larga(hija))
            continue
        _protegidos(hija, nivel + 1, encontrados)


def detectar(home: Path, raices: list[Path]) -> dict:
    claude = home / ".claude"
    python = next((n for n in ("python3", "python", "py") if _version_python(n)), "")
    proyectos: list[str] = []
    protegidos: list[str] = []
    for raiz in raices:
        if raiz.is_dir():
            proyectos += [_ruta_larga(p) for p in sorted(raiz.iterdir()) if p.is_dir() and (p / ".git").exists()]
            _protegidos(raiz, 1, protegidos)
    return {
        "sistema": "windows" if os.name == "nt" else "linux",
        "python": python,
        "git": shutil.which("git") is not None,
        "docker": shutil.which("docker") is not None,
        "home": _ruta_larga(home),
        "claude_existente": sorted(p.name for p in claude.iterdir()) if claude.is_dir() else [],
        "tasks_existente": (claude / "TASKS.md").is_file(),
        "candidatos_proyecto": proyectos,
        "candidatos_protegidos": protegidos,
    }
