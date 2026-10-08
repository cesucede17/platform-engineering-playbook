"""Kit de skills de los proyectos: selecciona, instala y comprueba.

Se ejecuta desde la carpeta del proyecto (solo librería estándar, Python >= 3.9):

    python <guia>/herramientas/kit.py seleccionar --tipo <ml|plataforma> --opciones api,gitlab
    python <guia>/herramientas/kit.py instalar
    python <guia>/herramientas/kit.py comprobar
    python <guia>/herramientas/kit.py tabla --escribir CLAUDE.md

- seleccionar: lee CATALOGO_SKILLS.json y escribe .claude/pipeline-skills.json (el manifiesto del
  proyecto), fusiona .claude/settings.json y copia las skills locales a .claude/skills/.
- instalar:    registra los marketplaces que falten e instala los plugins del manifiesto con
  --scope project (los marcados como desactivados se instalan y se desactivan).
- comprobar:   verifica que cada plugin está instalado y en el estado esperado PARA ESTE PROYECTO, que
  cada skill/agente/comando existe dentro de su plugin, que las skills locales tienen LICENSE y
  .upstream-commit, y que la tabla del CLAUDE.md coincide con el manifiesto. Sale con código 1 si algo falla.
- tabla:       genera la tabla fase -> skills del manifiesto; con --escribir la pone en el CLAUDE.md
  entre las marcas <!-- skills:inicio --> y <!-- skills:fin -->.

comprobar y tabla solo necesitan el manifiesto, así que este fichero se copia al proyecto como
scripts/verificar_skills.py y funciona sin la carpeta de guías.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

for _flujo in (sys.stdout, sys.stderr):
    if hasattr(_flujo, "reconfigure"):
        _flujo.reconfigure(encoding="utf-8")

MANIFIESTO = Path(".claude/pipeline-skills.json")
SETTINGS = Path(".claude/settings.json")
SKILLS_LOCALES = Path(".claude/skills")
MARCA_INICIO = "<!-- skills:inicio -->"
MARCA_FIN = "<!-- skills:fin -->"
SUBCARPETA = {"skill": ("skills", "{id}/SKILL.md"), "agente": ("agents", "{id}.md"), "comando": ("commands", "{id}.md")}


def guias_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def leer_json(ruta: Path) -> dict:
    return json.loads(ruta.read_text(encoding="utf-8"))


def escribir_json(ruta: Path, datos: dict) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def claude(*args: str) -> subprocess.CompletedProcess:
    exe = shutil.which("claude")
    if not exe:
        sys.exit("ERROR: no se encuentra el comando 'claude' en el PATH.")
    return subprocess.run([exe, *args], capture_output=True, text=True, encoding="utf-8", errors="replace")


# --------------------------------------------------------------------------- seleccionar

def aplica(cuando, opciones: set[str]) -> bool:
    if cuando == "siempre":
        return True
    return any(all(p in opciones for p in alternativa.split("+")) for alternativa in cuando)


def seleccionar(tipo: str, opciones: set[str]) -> None:
    catalogo = leer_json(guias_dir() / "CATALOGO_SKILLS.json")
    if tipo not in catalogo["fases"]:
        sys.exit(f"ERROR: este kit es para proyectos de tipo {', '.join(catalogo['fases'])}, no '{tipo}'.")
    desconocidas = opciones - set(catalogo["opciones"])
    if desconocidas:
        sys.exit(f"ERROR: opciones desconocidas {sorted(desconocidas)}. Válidas: {sorted(catalogo['opciones'])}")
    opciones |= set(catalogo["implicitas"].get(tipo, []))

    componentes = [c for c in catalogo["componentes"] if tipo in c["cuando"] and aplica(c["cuando"][tipo], opciones)]
    plugins: dict[str, bool] = {}
    for c in componentes:
        if c["plugin"] != "local":
            plugins[c["plugin"]] = plugins.get(c["plugin"], False) or c["tipo"] != "plugin-desactivado"
    usados = {p.split("@")[1] for p in plugins}

    manifiesto = {
        "generado_por": "herramientas/kit.py de la guía — no editar a mano; regenerar con 'seleccionar'",
        "catalogo_version": catalogo["version"],
        "tipo": tipo,
        "opciones": sorted(opciones),
        "fases": catalogo["fases"][tipo],
        "marketplaces": {m: r for m, r in catalogo["marketplaces"].items() if m in usados},
        "plugins": dict(sorted(plugins.items())),
        "componentes": [{k: c[k] for k in ("id", "tipo", "plugin")} | {"fases": [f for f in c["fases"] if f in catalogo["fases"][tipo]]} for c in componentes],
    }
    escribir_json(MANIFIESTO, manifiesto)

    settings = leer_json(SETTINGS) if SETTINGS.exists() else {}
    settings.setdefault("extraKnownMarketplaces", {}).update(
        {m: {"source": {"source": "github", "repo": r}} for m, r in manifiesto["marketplaces"].items()})
    settings.setdefault("enabledPlugins", {}).update(manifiesto["plugins"])
    escribir_json(SETTINGS, settings)

    for c in componentes:
        if c["plugin"] == "local":
            origen = guias_dir() / "vendored_skills" / c["id"]
            destino = SKILLS_LOCALES / c["id"]
            if not origen.exists():
                sys.exit(f"ERROR: falta la skill local {origen}")
            shutil.copytree(origen, destino, dirs_exist_ok=True)

    print(f"Tipo: {tipo} | opciones: {', '.join(sorted(opciones))}")
    print(f"{len(componentes)} componentes, {len(plugins)} plugins, "
          f"{sum(c['plugin'] == 'local' for c in componentes)} skills locales copiadas.")
    print(f"Escritos {MANIFIESTO} y {SETTINGS}. Siguiente: instalar.")


# --------------------------------------------------------------------------- instalar

def instalar() -> None:
    m = leer_json(MANIFIESTO)
    registrados = claude("plugin", "marketplace", "list").stdout
    for nombre, repo in m["marketplaces"].items():
        if repo not in registrados:
            print(f"+ marketplace {nombre} ({repo})")
            r = claude("plugin", "marketplace", "add", repo)
            if r.returncode:
                sys.exit(f"ERROR al añadir {repo}:\n{r.stdout}{r.stderr}")

    estado = estado_plugins()
    for pid, activo in m["plugins"].items():
        if pid not in estado:
            print(f"+ instalar {pid}")
            r = claude("plugin", "install", pid, "--scope", "project")
            if r.returncode:
                sys.exit(f"ERROR al instalar {pid}:\n{r.stdout}{r.stderr}")
        accion = None
        estado = estado_plugins()
        if pid in estado and estado[pid]["enabled"] != activo:
            accion = "enable" if activo else "disable"
            print(f"~ {accion} {pid}")
            r = claude("plugin", accion, pid, "--scope", "project")
            if r.returncode:
                sys.exit(f"ERROR en {accion} {pid}:\n{r.stdout}{r.stderr}")
    print("Instalación terminada. Siguiente: comprobar, y /reload-plugins en Claude Code.")


# --------------------------------------------------------------------------- comprobar

def mismo_dir(a: str | None) -> bool:
    return bool(a) and os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath("."))


def estado_plugins() -> dict[str, dict]:
    """Plugins que aplican a ESTE proyecto: ámbito user, o project/local de esta carpeta."""
    r = claude("plugin", "list", "--json")
    if r.returncode:
        sys.exit(f"ERROR en 'claude plugin list --json':\n{r.stderr}")
    salida: dict[str, dict] = {}
    for p in json.loads(r.stdout):
        if p.get("scope") == "user" or mismo_dir(p.get("projectPath")):
            previo = salida.get(p["id"])
            if previo is None or p.get("scope") != "user":   # el ámbito de proyecto manda sobre el de usuario
                salida[p["id"]] = {"enabled": bool(p.get("enabled")), "installPath": p.get("installPath", ""), "scope": p.get("scope")}
    return salida


def existe_en_plugin(install_path: str, tipo: str, cid: str) -> bool:
    carpeta, patron = SUBCARPETA[tipo]
    raiz = Path(install_path)
    if (raiz / carpeta / patron.format(id=cid)).exists():
        return True
    return any(raiz.glob(f"**/{carpeta}/{patron.format(id=cid)}"))


def tabla_markdown(m: dict) -> str:
    filas = ["| Fase | Skills, agentes y comandos |", "|---|---|"]
    for fase in m["fases"]:
        items = []
        for c in m["componentes"]:
            if fase in c["fases"]:
                nombre = {"comando": f"`/{c['id']}`", "agente": f"agente `{c['id']}`"}.get(c["tipo"], f"`{c['id']}`")
                if c["tipo"] == "plugin-desactivado":
                    nombre = f"`{c['id']}` (desactivado: solo con permiso expreso)"
                items.append(nombre)
        if items:
            filas.append(f"| {fase} | {', '.join(items)} |")
    return "\n".join(filas)


def bloque_claude_md(texto: str) -> str | None:
    if MARCA_INICIO not in texto or MARCA_FIN not in texto:
        return None
    return texto.split(MARCA_INICIO, 1)[1].split(MARCA_FIN, 1)[0].strip()


def comprobar(claude_md: Path) -> int:
    m = leer_json(MANIFIESTO)
    fallos: list[str] = []
    estado = estado_plugins()

    for pid, activo in m["plugins"].items():
        e = estado.get(pid)
        if e is None:
            fallos.append(f"plugin no instalado para este proyecto: {pid}")
        elif e["enabled"] != activo:
            fallos.append(f"plugin {pid}: enabled={e['enabled']}, esperado {activo}")

    settings = leer_json(SETTINGS) if SETTINGS.exists() else {}
    for pid, activo in m["plugins"].items():
        if settings.get("enabledPlugins", {}).get(pid) != activo:
            fallos.append(f".claude/settings.json no declara {pid}: {activo}")

    for c in m["componentes"]:
        if c["tipo"] == "plugin-desactivado":
            continue
        if c["plugin"] == "local":
            d = SKILLS_LOCALES / c["id"]
            for f in ("SKILL.md", "LICENSE", ".upstream-commit"):
                if not (d / f).exists():
                    fallos.append(f"skill local {c['id']}: falta {d / f}")
            continue
        e = estado.get(c["plugin"])
        if e and not existe_en_plugin(e["installPath"], c["tipo"], c["id"]):
            fallos.append(f"{c['tipo']} {c['id']} no existe en {c['plugin']} ({e['installPath']})")

    if claude_md.exists():
        bloque = bloque_claude_md(claude_md.read_text(encoding="utf-8"))
        if bloque is None:
            fallos.append(f"{claude_md} no tiene la tabla de skills entre {MARCA_INICIO} y {MARCA_FIN}")
        elif bloque != tabla_markdown(m):
            fallos.append(f"la tabla de skills de {claude_md} no coincide con el manifiesto (kit tabla --escribir)")
    else:
        fallos.append(f"no existe {claude_md}")

    total = len(m["plugins"]) + len(m["componentes"])
    if fallos:
        print(f"FALLOS ({len(fallos)}):")
        for f in fallos:
            print(f"  - {f}")
        return 1
    print(f"OK: {len(m['plugins'])} plugins y {len(m['componentes'])} componentes verificados ({total} comprobaciones).")
    print("Recuerda: tras instalar, /reload-plugins en Claude Code para que la sesión los cargue.")
    return 0


def tabla(escribir: Path | None) -> None:
    t = tabla_markdown(leer_json(MANIFIESTO))
    if not escribir:
        print(t)
        return
    texto = escribir.read_text(encoding="utf-8") if escribir.exists() else ""
    nuevo_bloque = f"{MARCA_INICIO}\n{t}\n{MARCA_FIN}"
    if bloque_claude_md(texto) is not None:
        antes = texto.split(MARCA_INICIO, 1)[0]
        despues = texto.split(MARCA_FIN, 1)[1]
        texto = antes + nuevo_bloque + despues
    else:
        texto = texto.rstrip() + "\n\n## Skills del pipeline\n\n" + nuevo_bloque + "\n"
    escribir.write_text(texto, encoding="utf-8")
    print(f"Tabla escrita en {escribir}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="orden", required=True)
    s = sub.add_parser("seleccionar")
    s.add_argument("--tipo", choices=["ml", "plataforma"], required=True)
    s.add_argument("--opciones", default="", help="separadas por comas, ver CATALOGO_SKILLS.json")
    sub.add_parser("instalar")
    c = sub.add_parser("comprobar")
    c.add_argument("--claude-md", default="CLAUDE.md", type=Path)
    t = sub.add_parser("tabla")
    t.add_argument("--escribir", type=Path)
    a = ap.parse_args()

    if a.orden == "seleccionar":
        seleccionar(a.tipo, {o.strip() for o in a.opciones.split(",") if o.strip()})
    elif not MANIFIESTO.exists():
        sys.exit(f"ERROR: no existe {MANIFIESTO}. Ejecuta antes 'seleccionar'.")
    elif a.orden == "instalar":
        instalar()
    elif a.orden == "comprobar":
        sys.exit(comprobar(a.claude_md))
    else:
        tabla(a.escribir)


if __name__ == "__main__":
    main()
