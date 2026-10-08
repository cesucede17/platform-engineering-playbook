"""Evaluación de comandos de Bash y PowerShell."""
from __future__ import annotations

import ntpath
import os
import re
from dataclasses import replace

from guardian_lib.calidad import fichero_de_calidad_existente
from guardian_lib.nucleo import (NOMBRE_DESBLOQUEO, Contexto, Veredicto, amenaza_autoproteccion, contiene_protegido,
                                 dentro, es_carpeta_grande, raiz_autoprotegida, ruta_protegida, variable_conocida)
from guardian_lib.servidor import evaluar_servidor

_REDIRECCIONES = {">", ">>", "1>", "1>>", "2>", "2>>", "*>", "*>>"}
_ESCAPABLES = ";&|<> \t'\""


def trocear(comando: str, shell: str = "bash") -> list[list[str]]:
    """Divide en segmentos (; && || | & y saltos de línea) y tokens, respetando comillas. Solo en bash la barra
    invertida escapa el carácter siguiente; en PowerShell es el separador de carpetas (una carpeta acabada
    en barra invertida seguida de espacio no debe pegarse al argumento siguiente)."""
    segmentos: list[list[str]] = [[]]
    token, hay_token, comilla, i = "", False, None, 0

    def soltar() -> None:
        nonlocal token, hay_token
        if hay_token:
            segmentos[-1].append(token)
        token, hay_token = "", False

    while i < len(comando):
        c = comando[i]
        if comilla:
            if c == comilla:
                comilla = None
            else:
                token += c
            i += 1
            continue
        if c in "'\"":
            comilla, hay_token = c, True
            i += 1
            continue
        dos = comando[i:i + 2]
        if shell == "bash" and c == "\\" and i + 1 < len(comando) and comando[i + 1] in _ESCAPABLES:
            # '\;' de bash (p. ej. find -exec … \;) es un carácter literal, no un separador. No se trata '\'
            # como escape en general: las rutas de Windows lo usan como separador de carpetas.
            token += comando[i + 1]
            hay_token = True
            i += 2
            continue
        if dos in ("&&", "||") or c in ";|&\n":  # '&' suelto: segundo plano (bash) u operador de llamada (PS)
            soltar()
            if segmentos[-1]:
                segmentos.append([])
            i += 2 if dos in ("&&", "||") else 1
            continue
        if c == ">":
            prefijo = token if token in ("1", "2", "*") else ""
            if prefijo:
                token, hay_token = "", False
            else:
                soltar()
            op = ">>" if dos == ">>" else ">"
            i += len(op)
            if comando[i:i + 2] in ("&1", "&2"):
                op += comando[i:i + 2]
                i += 2
            segmentos[-1].append(prefijo + op)
            continue
        if c.isspace():
            soltar()
            i += 1
            continue
        token += c
        hay_token = True
        i += 1
    soltar()
    return [s for s in segmentos if s]


def nombre_comando(token: str) -> str:
    nombre = ntpath.basename(token.replace("\\", "/")).lower()
    return nombre[:-4] if nombre.endswith(".exe") else nombre


def separar_redirecciones(segmento: list[str]) -> tuple[list[str], list[str]]:
    """Separa los argumentos de los ficheros destino de > y >> (ignora 2>&1)."""
    args, destinos, i = [], [], 0
    while i < len(segmento):
        t = segmento[i]
        if t in _REDIRECCIONES:
            if i + 1 < len(segmento):
                destinos.append(segmento[i + 1])
            i += 2
            continue
        if ">" in t and t.endswith(("&1", "&2")):
            i += 1
            continue
        args.append(t)
        i += 1
    return args, destinos


_GIT_GLOBALES_CON_VALOR = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--super-prefix"}


def _corto_con(arg: str, letra: str) -> bool:
    return arg.startswith("-") and not arg.startswith("--") and letra in arg[1:]


def evaluar_git(args: list[str], ctx: Contexto) -> Veredicto | None:
    i, carpeta = 0, ctx.cwd
    while i < len(args) and args[i].startswith("-"):
        if args[i] in _GIT_GLOBALES_CON_VALOR and i + 1 < len(args):
            if args[i] in ("-C", "--work-tree"):
                carpeta = ctx.ruta(args[i + 1])
            i += 2
        else:
            i += 1
    if i >= len(args):
        return None
    sub, resto = args[i].lower(), args[i + 1:]
    if sub == "push":
        peligro = any(a in ("--force", "--delete") or a.startswith(("--force-with-lease", "--force-if-includes", "+", ":"))
                      or _corto_con(a, "f") or _corto_con(a, "d") for a in resto)
    elif sub == "reset":
        peligro = "--hard" in resto
    elif sub == "clean":
        peligro = any(a == "--force" or _corto_con(a, "f") for a in resto)
    elif sub == "branch":
        peligro = any(_corto_con(a, "D") for a in resto) or ("--delete" in resto and ("--force" in resto or "-f" in resto))
    elif sub == "checkout":
        peligro = "." in resto
    elif sub == "restore":
        solo_staged = ("--staged" in resto or "-S" in resto) and not ("--worktree" in resto or "-W" in resto)
        peligro = "." in resto and not solo_staged
    elif sub == "stash":
        peligro = bool(resto) and resto[0].lower() in ("drop", "clear")
    else:
        peligro = False
    if not peligro:
        return None
    return Veredicto("git-destructivo", f"git {sub} {' '.join(resto)}".strip()[:120] + " puede perder trabajo",
                     ruta_ref=carpeta)


def evaluar_docker(cmd: str, args: list[str], ctx: Contexto) -> Veredicto | None:
    a = [x.lower() for x in args]
    if cmd == "docker-compose":
        a = ["compose", *a]
    palabras = [x for x in a if not x.startswith("-")]
    pares = set(zip(palabras, palabras[1:]))
    peligro = bool(pares & {("volume", "rm"), ("volume", "remove"), ("volume", "prune"), ("system", "prune")})
    if "compose" in palabras and "down" in a:
        tras_down = a[a.index("down") + 1:]
        peligro = peligro or any(x == "-v" or x.startswith("--volumes") for x in tras_down)
    if not peligro:
        return None
    return Veredicto("docker-datos", f"{cmd} {' '.join(args)}"[:120] + " borra volúmenes (datos)", ruta_ref=ctx.cwd)


BORRAR = {"rm", "del", "erase", "rd", "rmdir", "remove-item", "ri"}
MOVER = {"mv", "move", "move-item", "mi", "ren", "rename-item", "rni"}
COPIAR = {"cp", "copy", "copy-item", "cpi"}
ESCRIBIR_PRIMERO = {"set-content", "sc", "add-content", "ac", "out-file", "clear-content", "clc"}
ESCRIBIR_TODOS = {"new-item", "ni", "mkdir", "md", "touch", "tee", "tee-object"}
ANALIZADOS = BORRAR | MOVER | COPIAR | ESCRIBIR_PRIMERO | ESCRIBIR_TODOS | {"sed"}
_PARAMS_RUTA = {"-path", "-literalpath", "-lp", "-pspath", "-filepath"}
_PARAMS_CON_VALOR = {"-filter", "-include", "-exclude", "-erroraction", "-ea", "-value", "-itemtype",
                     "-type", "-encoding", "-name", "-inputobject"}
_NULOS = {"/dev/null", "$null", "nul", "nul:"}
_ADS_DATA = re.compile(r":[^:/\\]*:\$data$", re.I)
_CORTO_R = re.compile(r"^-[a-z]{0,3}r[a-z]{0,3}$")
_SED_INPLACE = re.compile(r"^(?:--in-place(?:=.*)?|-(?!-)[a-z]*i.*)$")  # -i, -ri, -i.bak, -ibak, -ni


def analizar_args(args: list[str]) -> tuple[list[str], str | None, list[str]]:
    """Devuelve (rutas posicionales, valor de -Destination, flags en minúsculas)."""
    posicionales: list[str] = []
    destino: str | None = None
    flags: list[str] = []
    i = 0
    while i < len(args):
        a = args[i]
        base, dos_puntos, _ = a.lower().partition(":")
        if a.startswith("-") and len(a) > 1:
            if base in _PARAMS_RUTA | {"-destination"} and dos_puntos:  # -Path:valor
                valor = a[len(base) + 1:]
                if base == "-destination":
                    destino = valor
                else:
                    posicionales.append(valor)
                i += 1
            elif base in _PARAMS_RUTA and i + 1 < len(args):
                posicionales.append(args[i + 1])
                i += 2
            elif base == "-destination" and i + 1 < len(args):
                destino = args[i + 1]
                i += 2
            elif base in _PARAMS_CON_VALOR:
                i += 2
            else:
                flags.append(a.lower())
                i += 1
            continue
        if len(a) == 2 and a[0] == "/" and a[1].isalpha():  # /s /q de cmd
            flags.append(a.lower())
        else:
            posicionales.append(a)
        i += 1
    return posicionales, destino, flags


def es_recursivo(flags: list[str]) -> bool:
    return "/s" in flags or any(f.startswith("-r") or f == "--recursive" or (len(f) <= 5 and _CORTO_R.match(f))
                                for f in flags)


def _desbloqueo() -> Veredicto:
    return Veredicto("desbloqueo", "el fichero .claude-unlock solo lo gestiona el usuario a mano",
                     desbloqueable=False, siempre=True)


def _autoproteccion(bruto: str, raiz: str) -> Veredicto:
    return Veredicto("autoproteccion", f"{bruto} es configuración de Claude Code o del propio vigilante",
                     carpeta_exacta=raiz, siempre=True)


def evaluar_destino(bruto: str, ctx: Contexto, recursivo: bool, accion: str = "escribir") -> Veredicto | None:
    """accion: 'borrar', 'origen' (lo que se mueve), 'destino' (donde queda lo copiado o movido) o 'escribir'."""
    if bruto.lower() in _NULOS:
        return None
    bruto = _ADS_DATA.sub("", bruto)  # fichero::$DATA es el propio fichero
    if ("$" in bruto and not variable_conocida(bruto)) or "%" in bruto:
        if recursivo:
            return Veredicto("borrado-masivo", f"borrado recursivo con destino no verificable ({bruto})",
                             ruta_ref=ctx.cwd)
        return None
    ruta = ctx.ruta(bruto)
    # Sin distinguir mayúsculas aunque Linux sí lo haga en el sistema de ficheros (igual que en
    # archivos.py): ".CLAUDE-UNLOCK" es igual de sospechoso que ".claude-unlock".
    # Texto literal Y ruta resuelta: el nombre corto 8.3 solo lo desvela la ruta real; un enlace con ese
    # nombre que apunte a otro sitio solo lo delata el texto literal.
    if NOMBRE_DESBLOQUEO in ruta.lower() or NOMBRE_DESBLOQUEO in bruto.lower():
        return _desbloqueo()
    claude = ctx.claude
    if accion in ("borrar", "origen"):
        raiz = amenaza_autoproteccion(ruta, ctx)  # borrar/mover ~, ~/.claude, ~/.cl*… se lleva hooks y settings
        if raiz:
            return _autoproteccion(bruto, raiz)
    elif accion == "destino" and (ruta == claude or ruta.endswith("/.claude")):
        return _autoproteccion(bruto, claude if ruta == claude else ntpath.dirname(ruta))  # sustituye la carpeta
    comodin = False
    partes = ruta.split("/")
    for i, parte in enumerate(partes):
        if "*" in parte or "?" in parte:
            ruta, comodin = "/".join(partes[:i]) or ruta, True
            break
    raiz = raiz_autoprotegida(ruta, ctx)
    if raiz:
        return _autoproteccion(bruto, raiz)
    protegida = ruta_protegida(ruta, ctx)
    if protegida:
        return Veredicto("ruta-protegida", f"{bruto} está dentro de una ruta protegida ({protegida})", ruta_ref=ruta)
    if not comodin:
        calidad = fichero_de_calidad_existente(ruta)
        if calidad:
            return calidad
    # El comodín solo cuenta como masivo al BORRAR: `mv *.csv data/` o `sed -i … *.py` no lo son.
    masivo = recursivo or (comodin and accion == "borrar")
    if masivo and (es_carpeta_grande(ruta, ctx) or contiene_protegido(ruta, ctx)):
        return Veredicto("borrado-masivo", f"borrado masivo de {bruto}", ruta_ref=ruta)
    return None


def evaluar_escritura(cmd: str, args: list[str], ctx: Contexto) -> list[Veredicto]:
    if cmd not in ANALIZADOS:
        return []
    posicionales, destino, flags = analizar_args(args)
    # PowerShell admite varias rutas separadas por comas (a,b); en sed el primer posicional es la expresión.
    posicionales = posicionales[:1] + _partir_comas(posicionales[1:]) if cmd == "sed" else _partir_comas(posicionales)
    recursivo = False
    objetivos: list[tuple[str, str]] = []  # (ruta en bruto, acción)
    if cmd in BORRAR:
        recursivo = es_recursivo(flags)
        objetivos = [(p, "borrar") for p in posicionales]
    elif cmd in MOVER or cmd in COPIAR:
        if destino is None and len(posicionales) >= 2:
            posicionales, destino = posicionales[:-1], posicionales[-1]
        if cmd in MOVER:
            objetivos = [(p, "origen") for p in posicionales]
        if destino is not None:
            renombrar = cmd in ("ren", "rename-item", "rni")
            objetivos += [(d, "destino") for d in _destinos_efectivos(posicionales, destino, renombrar, ctx)]
    elif cmd in ESCRIBIR_PRIMERO:
        objetivos = [(p, "escribir") for p in posicionales[:1]]
    elif cmd in ESCRIBIR_TODOS:
        objetivos = [(p, "escribir") for p in posicionales]
    elif any(_SED_INPLACE.match(f) for f in flags):  # sed: el primer posicional es la expresión
        objetivos = [(p, "escribir") for p in posicionales[1:]]
    if recursivo and not objetivos:
        return [Veredicto("borrado-masivo", f"borrado recursivo sin destino explícito ({cmd})", ruta_ref=ctx.cwd)]
    veredictos = []
    for bruto, accion in objetivos:
        v = evaluar_destino(bruto, ctx, recursivo, accion)
        if v:
            veredictos.append(v)
    return veredictos


def _partir_comas(rutas: list[str]) -> list[str]:
    return [parte for r in rutas for parte in r.split(",") if parte]


def _destinos_efectivos(origenes: list[str], destino: str, renombrar: bool, ctx: Contexto) -> list[str]:
    """Dónde queda cada cosa copiada o movida: `cp x carpeta/` deja `carpeta/x`; `cp -r src/* carpeta`
    vuelca el contenido en `carpeta`; `Rename-Item a/x y` deja `a/y`."""
    if renombrar:
        if not origenes or "/" in destino or "\\" in destino:
            return [destino]
        origen = origenes[0].replace("\\", "/").rstrip("/")
        return [origen.rsplit("/", 1)[0] + "/" + destino] if "/" in origen else [destino]
    es_carpeta = destino.endswith(("/", "\\")) or destino in (".", "..") or (
        _verificable(destino) and os.path.isdir(ctx.ruta(destino)))
    if not es_carpeta or not origenes:
        return [destino]
    efectivos = []
    for origen in origenes:
        nombre = ntpath.basename(origen.replace("\\", "/").rstrip("/"))
        if not nombre or nombre in (".", "..") or "*" in nombre or "?" in nombre:
            efectivos.append(destino)
        else:
            efectivos.append(destino.rstrip("/\\") + "/" + nombre)
    return list(dict.fromkeys(efectivos))


CAMBIAR_CARPETA = {"cd", "chdir", "pushd", "set-location", "sl", "push-location"}
# Comandos que no escriben: pueden mencionar hooks/settings sin que salte la autoprotección.
SOLO_LECTURA = {"cat", "type", "ls", "dir", "head", "tail", "grep", "rg", "get-content", "gc", "get-childitem",
                "gci", "select-string", "sls", "test-path", "get-item", "gi", "findstr", "wc",
                "popd", "pop-location", "diff", "cmp", "sha256sum", "md5sum", "get-filehash", "compare-object",
                "fc"} | CAMBIAR_CARPETA
_PYTHON = {"python", "python3", "py"}
_SCRIPTS_PROPIOS = {"guardian.py", "instalar.py"}  # instalar.py comprueba él mismo el desbloqueo
_MENCION = re.compile(r"(?:\.claude|claude~\d+)/(?:hooks|settin)")


def _verificable(bruto: str) -> bool:
    """¿Se puede saber a qué ruta apunta sin ejecutar nada? ($var, %VAR%, `cd -`… no)."""
    return not (("$" in bruto and not variable_conocida(bruto)) or "%" in bruto or "`" in bruto or bruto == "-")


def _tras_cambiar_carpeta(cmd: str, resto: list[str], ctx: Contexto) -> Contexto:
    """Contexto de los segmentos que siguen a un cd/Set-Location (si su destino es verificable)."""
    posicionales, _, _ = analizar_args(resto)
    if not posicionales:
        return replace(ctx, cwd=ctx.home) if cmd in ("cd", "chdir") else ctx
    return replace(ctx, cwd=ctx.ruta(posicionales[0])) if _verificable(posicionales[0]) else ctx


def _carpeta_de_trabajo(cmd: str, resto: list[str], ctx: Contexto) -> str:
    """Carpeta donde actúa el comando: la actual o la de `git -C`."""
    carpeta = ctx.cwd
    if cmd == "git":
        for i, a in enumerate(resto[:-1]):
            if not a.startswith("-"):
                break
            if a == "-C" and _verificable(resto[i + 1]):
                carpeta = ctx.ruta(resto[i + 1])
    return carpeta


def _texto_ruta(texto: str) -> str:
    texto = re.sub(r"/+", "/", texto.lower().replace("\\", "/"))
    return re.sub(r"/(?:\./)+", "/", texto)


def autoproteccion_por_mencion(segmento: list[str], args: list[str], ctx: Contexto) -> list[Veredicto]:
    """La lista de comandos que escriben nunca está completa (perl -pi, dd of=, tar -C, [IO.File]…): si un
    comando que no es de solo lectura menciona hooks/settings de Claude Code, se bloquea siempre."""
    if not args:
        return []
    cmd = nombre_comando(args[0])
    if cmd in SOLO_LECTURA or (cmd in _PYTHON and len(args) > 1 and nombre_comando(args[1]) in _SCRIPTS_PROPIOS):
        return []
    if cmd == "jq" and not any(a == "-o" or a.startswith("--output") for a in args[1:]):
        return []  # jq solo escribe con --output (o con una redirección, que se mira aparte)
    claude = ctx.claude
    analizado = cmd in ANALIZADOS  # sus destinos ya se miran con precisión (cp x ~/.claude/ es válido)
    raices: set[str] = set()
    for token in segmento:
        mencion = bool(_MENCION.search(_texto_ruta(token)))
        valor = token.split("=")[-1]  # of=…, --output=…: la ruta es lo que va tras el '='
        candidatos = {valor, *valor.split(",")}
        explicada = False
        for c in candidatos:
            if not c or not _verificable(c) or any(x.isspace() for x in c):
                continue
            ruta = ctx.ruta(c)
            raiz = claude if ruta == claude and not analizado else raiz_autoprotegida(ruta, ctx)
            if raiz:
                raices.add(raiz)
                explicada = True
        if mencion and not explicada:
            raices.add(claude)
    carpeta = _carpeta_de_trabajo(cmd, args[1:], ctx)
    texto = _texto_ruta(" ".join(segmento))
    if dentro(carpeta, claude + "/hooks") or (carpeta == claude and re.search(r"settin|hooks", texto)):
        raices.add(claude)
    return [Veredicto("autoproteccion", f"'{cmd}' menciona configuración de Claude Code o del propio vigilante"
                      " y puede escribir en ella", carpeta_exacta=r, siempre=True) for r in sorted(raices)]


def evaluar_comando(comando: str, ctx: Contexto, shell: str = "bash") -> list[Veredicto]:
    """shell: 'bash' o 'powershell' (cambia cómo se trata la barra invertida al trocear)."""
    if NOMBRE_DESBLOQUEO in comando.lower():
        return [_desbloqueo()]
    veredictos: list[Veredicto] = []
    for segmento in trocear(comando, shell):
        args, redirecciones = separar_redirecciones(segmento)
        propios = [v for v in (evaluar_destino(d, ctx, recursivo=False) for d in redirecciones) if v]
        if args:
            cmd, resto = nombre_comando(args[0]), args[1:]
            if cmd in CAMBIAR_CARPETA:
                ctx = _tras_cambiar_carpeta(cmd, resto, ctx)  # los segmentos siguientes trabajan allí
            elif cmd == "git":
                propios.append(evaluar_git(resto, ctx))
            elif cmd in ("docker", "docker-compose"):
                propios.append(evaluar_docker(cmd, resto, ctx))
            elif cmd in ("ssh", "scp", "rsync", "sftp"):
                propios.append(evaluar_servidor(cmd, resto, ctx))
            else:
                propios += evaluar_escritura(cmd, resto, ctx)
        propios = [v for v in propios if v]
        ya = {v.carpeta_exacta for v in propios if v.regla == "autoproteccion"}
        propios += [v for v in autoproteccion_por_mencion(segmento, args, ctx) if v.carpeta_exacta not in ya]
        veredictos += propios
    return veredictos
