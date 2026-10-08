"""Acciones contra el servidor de la plataforma: solo se permite mirar y el git push al repo bare."""
from __future__ import annotations

import re

from guardian_lib.nucleo import Contexto, Veredicto

_SSH_OPCIONES_CON_VALOR = {"-p", "-i", "-o", "-l", "-F", "-J", "-L", "-R", "-D", "-b", "-c", "-e", "-m",
                           "-S", "-W", "-E", "-Q", "-w", "-B"}
_SCP_RSYNC_OPCIONES_CON_VALOR = {"-e", "-P", "-i", "-o", "-F"}
_COMPUESTOS = (";", "&&", "&", "||", ">", "`", "$(", "\n", "\r")
_OPCIONES_A_QUITAR = {"-C", "-f", "-p", "--project-directory", "--file", "--project-name"}
_ESQUEMAS = ("rsync://", "ssh://")
_CLAVES_O_PELIGROSAS = ("hostname", "proxycommand", "proxyjump")


def _es_host(token: str, hosts: set[str]) -> bool:
    t = token.lower()
    for esquema in _ESQUEMAS:
        if t.startswith(esquema):
            t = t[len(esquema):]
            break
    if "@" in t:
        t = t.split("@", 1)[1]
    t = t.split("/", 1)[0]  # quita la ruta/módulo tras el host, p.ej. en rsync://host/modulo/...
    return t.split(":", 1)[0] in hosts


def _clave_opcion_o(valor: str) -> str:
    return re.split(r"[=\s]", valor.strip(), maxsplit=1)[0].lower()


def _letras_cortas(arg: str) -> tuple[str, bool]:
    """Letras de un grupo de opciones cortas de ssh (-fNL) y si la última se come el argumento siguiente."""
    letras = ""
    for j, letra in enumerate(arg[1:], start=1):
        letras += letra
        if "-" + letra in _SSH_OPCIONES_CON_VALOR:
            return letras, j == len(arg) - 1  # -Fcfg lleva el valor pegado; -fNL lo lleva en el siguiente
    return letras, False


def _es_grupo_corto(arg: str) -> bool:
    return arg.startswith("-") and not arg.startswith("--") and len(arg) > 1


def _tiene_redireccion_oculta(args: list[str], cmd: str = "ssh") -> bool:
    """-o HostName/ProxyCommand/ProxyJump, -J o -F (otro ssh_config) pueden hacer que el host real sea el
    servidor aunque el host "visible" en la orden sea un alias señuelo; no se puede verificar su valor con
    garantías (alias de DNS, /etc/hosts, etc.), así que se bloquea su sola presencia. En rsync las opciones
    de ssh van dentro de -e/--rsh (y su -F es un filtro, no una configuración de ssh)."""
    if cmd == "rsync":
        for i, a in enumerate(args):
            if a in ("-e", "--rsh") and i + 1 < len(args):
                valor = args[i + 1]
            elif a.startswith("--rsh="):
                valor = a[len("--rsh="):]
            elif a.startswith("-e") and len(a) > 2:
                valor = a[2:]
            else:
                continue
            if _tiene_redireccion_oculta(valor.split()[1:]):
                return True
        return False
    i = 0
    while i < len(args):
        a = args[i]
        if a == "-o" and i + 1 < len(args):
            if _clave_opcion_o(args[i + 1]) in _CLAVES_O_PELIGROSAS:
                return True
            i += 2
            continue
        if a.startswith("-o") and not a.startswith("--") and len(a) > 2:
            if _clave_opcion_o(a[2:]) in _CLAVES_O_PELIGROSAS:
                return True
            i += 1
            continue
        if a == "-J" or a.startswith("--proxyjump"):
            return True
        if _es_grupo_corto(a) and ("F" in _letras_cortas(a)[0] or "J" in _letras_cortas(a)[0]):
            return True
        i += 1
    return False


def _sin_orden_remota(args: list[str]) -> bool:
    """ssh -N (p. ej. un túnel -L): no ejecuta nada en el servidor."""
    return any(_es_grupo_corto(a) and "N" in _letras_cortas(a)[0] for a in args)


def _posicionales_scp_rsync(args: list[str]) -> list[str]:
    posicionales, i = [], 0
    while i < len(args):
        a = args[i]
        if a in _SCP_RSYNC_OPCIONES_CON_VALOR:
            i += 2
            continue
        if a.startswith("-"):
            i += 1
            continue
        posicionales.append(a)
        i += 1
    return posicionales


def _es_solo_mirar(orden: str, permitidas: list[str]) -> bool:
    palabras = orden.split()
    limpias: list[str] = []
    i = 0
    while i < len(palabras):
        if palabras[i] in _OPCIONES_A_QUITAR and limpias and limpias[0] in ("git", "docker"):
            i += 2
            continue
        limpias.append(palabras[i])
        i += 1
    return any(limpias[:len(p.split())] == p.split() for p in permitidas)


def _bloqueo(motivo: str, ctx: Contexto) -> Veredicto:
    return Veredicto("servidor", motivo, ruta_ref=ctx.cwd)


def _evaluar_orden_remota(orden: str, ctx: Contexto) -> Veredicto | None:
    conf = ctx.reglas.get("servidor", {})
    if any(s in orden for s in _COMPUESTOS):
        return _bloqueo(f"orden compuesta en el servidor ({orden[:80]})", ctx)
    partes = [p.strip() for p in orden.split("|")]
    if not _es_solo_mirar(partes[0], conf.get("solo_mirar", [])):
        return _bloqueo(f"'{partes[0][:80]}' cambia o puede cambiar el servidor", ctx)
    for parte in partes[1:]:
        if not parte or parte.split()[0] not in conf.get("tras_tuberia", []):
            return _bloqueo(f"'{parte[:80]}' tras una tubería en el servidor", ctx)
    return None


def evaluar_servidor(cmd: str, args: list[str], ctx: Contexto) -> Veredicto | None:
    if _tiene_redireccion_oculta(args, cmd):
        return _bloqueo(f"{cmd} con una opción que puede fijar el host real sin poder verificarlo", ctx)
    hosts = {h.lower() for h in ctx.reglas.get("servidor", {}).get("hosts", [])}
    if cmd in ("scp", "rsync"):
        posicionales = _posicionales_scp_rsync(args)
        if posicionales and ":" in posicionales[-1] and _es_host(posicionales[-1], hosts):
            return _bloqueo(f"copiar ficheros al servidor con {cmd}", ctx)
        return None
    if cmd == "sftp":
        return _bloqueo("sesión sftp con el servidor", ctx) if any(_es_host(a, hosts) for a in args) else None
    i, indice_host = 0, None
    while i < len(args):
        if args[i].startswith("-"):
            i += 2 if _es_grupo_corto(args[i]) and _letras_cortas(args[i])[1] else 1
            continue
        indice_host = i
        break
    if indice_host is None or not _es_host(args[indice_host], hosts):
        return None
    orden = " ".join(args[indice_host + 1:]).strip()
    if not orden and _sin_orden_remota(args[:indice_host]):
        return None
    if not orden:
        return _bloqueo("sesión interactiva en el servidor (no se puede vigilar)", ctx)
    return _evaluar_orden_remota(orden, ctx)
