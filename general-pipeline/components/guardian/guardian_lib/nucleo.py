"""Piezas comunes de guardian: rutas normalizadas, rutas protegidas, desbloqueos y veredictos."""
from __future__ import annotations

import fnmatch
import ntpath
import os
import posixpath
import re
import tempfile
from dataclasses import dataclass

NOMBRE_DESBLOQUEO = ".claude-unlock"
DESACTIVABLES = {"borrado-masivo", "git-destructivo", "docker-datos", "reglas-calidad", "servidor"}
_PREFIJOS_HOME = ("$env:userprofile", "${env:userprofile}", "$userprofile", "${userprofile}", "$home", "${home}",
                  "~")
# Variables de la carpeta temporal: se resuelven con el entorno del propio vigilante.
_PREFIJOS_TEMPORAL = {
    "$env:temp": "TEMP", "${env:temp}": "TEMP", "$env:tmp": "TMP", "${env:tmp}": "TMP",
    "$tmpdir": "TMPDIR", "${tmpdir}": "TMPDIR", "$temp": "TEMP", "${temp}": "TEMP", "$tmp": "TMP", "${tmp}": "TMP",
}
_UNIDAD_GITBASH = re.compile(r"^/([a-zA-Z])(?=/|$)")
_ABSOLUTA = re.compile(r"^[a-zA-Z]:/")


def _prefijo(r: str, prefijos) -> str | None:
    rl = r.lower()
    for prefijo in prefijos:
        if rl.startswith(prefijo) and (len(r) == len(prefijo) or r[len(prefijo)] in "/\\"):
            return prefijo
    return None


def variable_conocida(bruta: str) -> bool:
    """¿Empieza por una variable que sabemos resolver ($HOME, $env:USERPROFILE, $env:TEMP, $TMPDIR…)?"""
    r = bruta.strip().strip("'\"")
    return bool(_prefijo(r, _PREFIJOS_HOME) or _prefijo(r, _PREFIJOS_TEMPORAL))


def _temporal(variable: str) -> str:
    return os.environ.get(variable) or tempfile.gettempdir()


def normalizar(ruta: str, cwd: str, home: str, _posix: bool | None = None) -> str:
    """Ruta absoluta, en minúsculas, con '/' y sin barra final (Windows no distingue mayúsculas).

    En Linux (`os.name != "nt"`) no pasa a minúsculas ni usa `ntpath` (sí distingue mayúsculas).
    `_posix` fuerza esa rama explícitamente, para poder probarla también en Windows.
    """
    posix = (os.name != "nt") if _posix is None else _posix
    r = ruta.strip().strip("'\"")
    prefijo = _prefijo(r, _PREFIJOS_HOME)
    if prefijo:
        r = home + r[len(prefijo):]
    else:
        prefijo = _prefijo(r, _PREFIJOS_TEMPORAL)
        if prefijo:
            r = _temporal(_PREFIJOS_TEMPORAL[prefijo]) + r[len(prefijo):]
    r = r.replace("\\", "/")
    if not posix:
        m = _UNIDAD_GITBASH.match(r)
        if m:
            r = f"{m.group(1)}:" + (r[m.end():] or "/")
    if not _ABSOLUTA.match(r) and not r.startswith("/") and cwd:
        r = cwd.rstrip("/") + "/" + r
    r = _limpiar_componentes(r)
    if posix:
        # En Linux real, realpath SIN normpath previo: así '..' se resuelve en disco, componente a
        # componente, después de seguir cada enlace ('L/../settings.json' con L -> ~/.claude/plugins
        # es ~/.claude/settings.json). Un normpath antes quitaría 'L/..' a mano y daría otra ruta.
        # Con `_posix` forzado en Windows (pruebas) o sin ruta absoluta, solo normpath, como siempre.
        r = _real_posix(r) if (os.name != "nt" and r.startswith("/")) else posixpath.normpath(r)
    else:
        r = ntpath.normpath(r).replace("\\", "/")
    if _ABSOLUTA.match(r):
        r = _ruta_real(r)
    if not posix:
        r = r.lower()
    return r.rstrip("/") if len(r) > 3 else r


def _limpiar_componentes(r: str) -> str:
    """Como hace Windows: quita el flujo alternativo (`fichero::$DATA`, `fichero:flujo`) y los puntos y
    espacios finales de cada componente (`settings.json.` es `settings.json`)."""
    partes = r.split("/")
    for i, parte in enumerate(partes):
        if i == 0 and re.fullmatch(r"[a-zA-Z]:", parte):
            continue
        if ":" in parte:
            parte = parte.split(":", 1)[0]
        if parte not in ("", ".", ".."):
            parte = parte.rstrip(". ") or "."
        partes[i] = parte
    return "/".join(partes)


def _real_posix(r: str) -> str:
    """En Linux resuelve los enlaces simbólicos (un enlace a ~/.claude o a una ruta protegida no la
    esquiva). Sin `strict`: vale para rutas que aún no existen. En Windows (también con `_posix`
    forzado en las pruebas) no hace nada: allí ya resuelve `_ruta_real`."""
    if os.name == "nt" or not r.startswith("/"):
        return r
    try:
        return os.path.realpath(r)
    except (OSError, ValueError):
        return posixpath.normpath(r)


def _ruta_real(r: str) -> str:
    """Resuelve nombres cortos 8.3 (C:/Users/NOMBRE~1), enlaces y uniones; si falla, deja la ruta como está."""
    try:
        real = os.path.realpath(r)
    except (OSError, ValueError):
        return r
    if real.startswith("\\\\?\\"):
        real = real[4:]
    real = real.replace("\\", "/")
    return real if _ABSOLUTA.match(real) else r


def dentro(ruta: str, raiz: str) -> bool:
    raiz = raiz.rstrip("/")
    return ruta == raiz or ruta.startswith(raiz + "/")


@dataclass
class Contexto:
    reglas: dict
    cwd: str
    home: str
    ahora: float

    @classmethod
    def crear(cls, reglas: dict, cwd: str, ahora: float) -> "Contexto":
        home = normalizar(reglas.get("home") or os.path.expanduser("~"), "", "")
        return cls(reglas, normalizar(cwd, "", home), home, ahora)

    def ruta(self, bruta: str) -> str:
        return normalizar(bruta, self.cwd, self.home)

    @property
    def claude(self) -> str:
        """La carpeta de configuración de Claude Code, comparable con `ruta()`. En Windows es
        `home + "/.claude"` tal cual; en Linux, resuelta (dotfiles: ~/.claude puede ser un enlace)."""
        return _real_posix(self.home + "/.claude")

    def lista(self, clave: str) -> list[str]:
        return [self.ruta(r) for r in self.reglas.get(clave, [])]


def ruta_protegida(ruta: str, ctx: Contexto) -> str | None:
    for raiz in ctx.lista("rutas_protegidas"):
        if dentro(ruta, raiz):
            return raiz
    for segmento in ctx.reglas.get("segmentos_protegidos", []):
        if "/" + segmento.strip("/").lower() + "/" in ruta + "/":
            return segmento
    return None


def raiz_autoprotegida(ruta: str, ctx: Contexto) -> str | None:
    """Si la ruta es configuración de Claude Code, devuelve la única carpeta donde vale el desbloqueo."""
    claude = ctx.claude
    if ruta in (claude + "/settings.json", claude + "/settings.local.json") or dentro(ruta, claude + "/hooks"):
        return claude
    m = re.match(r"^(.+)/\.claude/settings(\.local)?\.json$", ruta)
    return m.group(1) if m else None


def amenaza_autoproteccion(ruta: str, ctx: Contexto) -> str | None:
    """Si borrar o mover `ruta` (que puede llevar comodines, p. ej. ~/* o ~/.cl*) se llevaría por delante
    configuración autoprotegida, devuelve la carpeta donde vale el desbloqueo."""
    partes = ruta.rstrip("/").split("/")
    for claude in dict.fromkeys((ctx.home + "/.claude", ctx.claude)):  # en Windows, una sola
        for critica in (claude + "/hooks", claude + "/settings.json", claude + "/settings.local.json"):
            trozos = critica.split("/")
            if len(partes) <= len(trozos) and all(fnmatch.fnmatchcase(t, p) for t, p in zip(trozos, partes)):
                return ctx.home + "/.claude"
    if partes[-1] == ".claude" and any(os.path.isfile(ruta + f) for f in ("/settings.json", "/settings.local.json")):
        return "/".join(partes[:-1])  # la carpeta .claude de un proyecto
    return None


def contiene_protegido(ruta: str, ctx: Contexto) -> bool:
    """¿Borrar esta carpeta entera se llevaría por delante algo protegido?"""
    criticas = ctx.lista("rutas_protegidas") + [c + f for c in dict.fromkeys((ctx.home + "/.claude", ctx.claude))
                                               for f in ("/hooks", "/settings.json")]
    if any(c.startswith(ruta.rstrip("/") + "/") for c in criticas):
        return True
    return os.path.isdir(ruta + "/data/raw") or (ruta.endswith("/data") and os.path.isdir(ruta + "/raw"))


def es_carpeta_grande(ruta: str, ctx: Contexto, _posix: bool | None = None) -> bool:
    posix = (os.name != "nt") if _posix is None else _posix
    if ruta == "/" or re.fullmatch(r"[a-z]:/?", ruta):
        return True
    raices = ctx.lista("raices_proyectos")
    if ruta in {ctx.home, ctx.home + "/desktop", *raices}:
        return True
    dirname = posixpath.dirname if (posix and ruta.startswith("/")) else ntpath.dirname
    return dirname(ruta) in raices


def desbloqueo_valido(carpeta: str, ctx: Contexto) -> bool:
    fichero = carpeta.rstrip("/") + "/" + NOMBRE_DESBLOQUEO
    if not os.path.isfile(fichero):  # una carpeta con ese nombre no es un desbloqueo
        return False
    try:
        mtime = os.path.getmtime(fichero)
    except OSError:
        return False
    return ctx.ahora - mtime <= float(ctx.reglas.get("caducidad_desbloqueo_horas", 2)) * 3600


def buscar_desbloqueo(ruta: str, ctx: Contexto) -> str | None:
    """Busca un .claude-unlock vigente en la ruta o en cualquiera de sus carpetas padre."""
    actual = ruta
    while True:
        if desbloqueo_valido(actual, ctx):
            return actual
        padre = ntpath.dirname(actual)
        if not padre or padre == actual:
            return None
        actual = padre


@dataclass
class Veredicto:
    regla: str
    motivo: str
    ruta_ref: str | None = None          # desde aquí se busca .claude-unlock subiendo carpetas
    carpeta_exacta: str | None = None    # el desbloqueo solo vale en esta carpeta
    desbloqueable: bool = True
    siempre: bool = False                # bloquea también en modo prueba
    desbloqueado_en: str | None = None

    @property
    def bloquea(self) -> bool:
        return self.desbloqueado_en is None

    def carpeta_sugerida(self) -> str | None:
        if self.carpeta_exacta:
            return self.carpeta_exacta
        if self.ruta_ref:
            return self.ruta_ref if os.path.isdir(self.ruta_ref) else ntpath.dirname(self.ruta_ref)
        return None


def resolver(v: Veredicto, ctx: Contexto) -> Veredicto:
    """Marca el veredicto como desbloqueado si hay un .claude-unlock vigente donde corresponde."""
    if v.desbloqueable:
        if v.carpeta_exacta:
            if desbloqueo_valido(v.carpeta_exacta, ctx):
                v.desbloqueado_en = v.carpeta_exacta
        elif v.ruta_ref:
            v.desbloqueado_en = buscar_desbloqueo(v.ruta_ref, ctx)
    return v
