"""Instala el pipeline personal de Claude Code a partir de `perfil_pipeline.json`.

Uso: python instalar.py <orden> [--home H] [--perfil P] [--componentes C] [--plantillas T]
                                 [--raiz R ...] [--sin-plugins] [--reconfigurar] [--si]

Órdenes:
  detectar   muestra en JSON lo que hay en el equipo (python, git, docker, ~/.claude, proyectos…).
  generar    rellena las plantillas en ~/.claude/copias_pipeline/preparacion/ para revisarlas.
  instalar   hace una copia de seguridad y copia todo a ~/.claude. Sin --si solo enseña los cambios.
  verificar  comprueba que la instalación funciona (OK / FALLO).
  deshacer   vuelve a dejar ~/.claude como estaba antes de la última instalación (con --si).

Códigos de salida: 0 bien; 1 error; 2 la verificación falla; 3 hace falta aprobación (--si);
4 guardian ya está instalado y no hay un ".claude-unlock" vigente en ~/.claude/ (instalar y
deshacer no escriben nada; lo crea la persona a mano, nunca Claude; ver hooks/guardian_README.md).
Solo biblioteca estándar; Python 3.10 o superior; Windows y Linux.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True  # no dejes __pycache__ en herramientas/ al ejecutar el instalador empaquetado

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

import instalar_copias as copias  # noqa: E402
import instalar_lib as lib  # noqa: E402
import instalar_verificar as verif  # noqa: E402

PLUGINS = (["plugin", "marketplace", "add", "obra/superpowers-marketplace"],
           ["plugin", "install", "superpowers@superpowers-marketplace", "--scope", "user"])


def _plantillas_por_defecto() -> Path:
    propia = AQUI / "templates"
    return propia if propia.is_dir() else AQUI.parent / "templates"


def _argumentos(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="instalar.py", description="Instala el pipeline personal de Claude Code.",
        epilog="Códigos de salida: 0 bien; 1 error; 2 la verificación falla; 3 hace falta aprobación (--si); "
               '4 falta un desbloqueo (fichero ".claude-unlock") vigente en ~/.claude/, porque guardian ya '
               "está instalado: instalar/deshacer no escriben nada; lo crea la persona a mano, nunca Claude.")
    p.add_argument("orden", choices=["detectar", "generar", "instalar", "verificar", "deshacer"])
    p.add_argument("--home", type=Path, default=Path.home(), help="carpeta personal (por defecto, la tuya)")
    p.add_argument("--perfil", type=Path, help="ruta de perfil_pipeline.json")
    p.add_argument("--componentes", type=Path, default=AQUI.parent / "components")
    p.add_argument("--plantillas", type=Path, default=_plantillas_por_defecto())
    p.add_argument("--raiz", type=Path, action="append", default=[], help="carpeta donde buscar proyectos")
    p.add_argument("--sin-plugins", action="store_true", help="no instala ni comprueba plugins")
    p.add_argument("--reconfigurar", action="store_true", help="sobrescribe las configuraciones existentes")
    p.add_argument("--si", action="store_true", help="aprobación dada: aplica los cambios")
    return p.parse_args(argv)


def _cargar_perfil(args: argparse.Namespace) -> tuple[dict, bytes]:
    candidatos = [args.perfil] if args.perfil else [args.home / ".claude" / "perfil_pipeline.json",
                                                    Path.cwd() / "perfil_pipeline.json"]
    for ruta in candidatos:
        if ruta.is_file():
            datos = ruta.read_bytes()
            try:
                perfil = json.loads(datos.decode("utf-8-sig"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise lib.ErrorInstalacion(f"{ruta} no es JSON válido: {error}") from error
            if not isinstance(perfil, dict) or perfil.get("formato") != 1:
                raise lib.ErrorInstalacion(f"{ruta} no es un perfil de formato 1")
            return perfil, datos
    raise lib.ErrorInstalacion("no encuentro perfil_pipeline.json; indícalo con --perfil")


def _plan(args: argparse.Namespace) -> dict:
    """Calcula todo lo que se escribiría, sin tocar nada."""
    perfil, perfil_bytes = _cargar_perfil(args)
    python = perfil.get("python") or "python"
    claude = args.home / ".claude"
    rellenas = lib.rellenar_plantillas(args.plantillas, perfil)
    escribir: dict[str, bytes] = dict(lib.ficheros_componentes(args.componentes, python))
    conservados = []
    modo_guardian_conservado = None
    for rel, nombre in ((lib.CONFIG_GUARDIAN, "guardian_reglas.json"), (lib.CONFIG_CONTINUIDAD, "continuidad.json")):
        existe = (claude / rel).exists()
        if existe and not args.reconfigurar:
            conservados.append(rel)
        elif rel == lib.CONFIG_GUARDIAN and existe:
            # Al reconfigurar no se baja a quien ya hubiera pasado guardian a "activo": se
            # conserva el modo instalado y se regenera el resto desde la plantilla.
            texto, modo_guardian_conservado = lib.guardian_reglas_con_modo_conservado(claude / rel, rellenas[nombre])
            escribir[rel] = texto.encode("utf-8")
        else:
            escribir[rel] = rellenas[nombre].encode("utf-8")
    settings_antes, datos = lib.leer_settings(claude / "settings.json")
    datos_nuevos, cambia = lib.fusionar_settings(datos, python)
    settings_despues = lib.texto_settings(datos_nuevos)
    if cambia:
        escribir["settings.json"] = settings_despues.encode("utf-8")
    claude_md = lib.fusionar_claude_md(lib.leer_texto(claude / "CLAUDE.md"), rellenas["bloque_claude.md"])
    escribir["CLAUDE.md"] = claude_md.encode("utf-8")
    tasks = lib.fusionar_tasks(lib.leer_texto(claude / "TASKS.md"), rellenas["TASKS.md"])
    escribir["TASKS.md"] = tasks.encode("utf-8")
    escribir["perfil_pipeline.json"] = perfil_bytes
    return {"claude": claude, "perfil": perfil, "escribir": escribir, "conservados": conservados,
            "sobran": lib.sobrantes_codigo(claude, escribir), "rellenas": rellenas, "cambia_settings": cambia,
            "settings_antes": settings_antes, "settings_despues": settings_despues,
            "modo_guardian_conservado": modo_guardian_conservado}


def _resumen(plan: dict) -> list[str]:
    claude = plan["claude"]
    lineas = []
    for rel, datos in plan["escribir"].items():
        ruta = claude / rel
        if not ruta.exists():
            lineas.append(f"  nuevo      {rel}")
        elif not ruta.is_file() or ruta.read_bytes() != datos:
            lineas.append(f"  cambia     {rel}")
    lineas += [f"  se conserva {rel} (para cambiarlo, usa --reconfigurar)" for rel in plan["conservados"]]
    lineas += [f"  se quita   {rel} (sobra de una versión anterior)" for rel in plan["sobran"]]
    if plan.get("modo_guardian_conservado"):
        lineas.append(f'  se conserva el "modo": "{plan["modo_guardian_conservado"]}" de guardian_reglas.json '
                      "(--reconfigurar cambia el resto)")
    return lineas or ["  nada que cambiar"]


def orden_detectar(args: argparse.Namespace) -> int:
    print(json.dumps(lib.detectar(args.home, args.raiz), indent=2, ensure_ascii=False))
    return 0


def orden_generar(args: argparse.Namespace) -> int:
    plan = _plan(args)
    claude, rellenas = plan["claude"], plan["rellenas"]
    prep = claude / "copias_pipeline" / "preparacion"
    prep.mkdir(parents=True, exist_ok=True)
    def config(nombre: str, rel: str) -> tuple[str, str]:
        # Lo que instalar escribirá (al reconfigurar, con el modo de guardian conservado); si se
        # conserva, la plantilla queda en preparacion/ solo para comparar.
        datos = plan["escribir"].get(rel)
        return (datos.decode("utf-8") if datos is not None else rellenas[nombre]), rel

    salida = {
        "guardian_reglas.json": config("guardian_reglas.json", lib.CONFIG_GUARDIAN),
        "continuidad.json": config("continuidad.json", lib.CONFIG_CONTINUIDAD),
        "TASKS.md": (plan["escribir"]["TASKS.md"].decode("utf-8"), "TASKS.md"),
        "CLAUDE.md": (plan["escribir"]["CLAUDE.md"].decode("utf-8"), "CLAUDE.md"),
        "settings.json": (plan["settings_despues"], "settings.json"),
    }
    print(f"Ficheros preparados en {prep}:")
    for nombre, (texto, rel) in salida.items():
        (prep / nombre).write_bytes(texto.encode("utf-8"))
        actual = claude / rel
        if rel in plan["conservados"]:  # lo mismo que dirá el plan de instalar
            estado = "se conserva el instalado (para cambiarlo, usa --reconfigurar)"
        elif not actual.exists():
            estado = "nuevo"
        else:
            diff = lib.diferencia(actual.read_bytes().decode("utf-8", "replace"), texto, rel).splitlines()
            mas = sum(1 for x in diff if x.startswith("+") and not x.startswith("+++"))
            menos = sum(1 for x in diff if x.startswith("-") and not x.startswith("---"))
            estado = "igual que el instalado" if not diff else f"cambia (+{mas} / -{menos} líneas)"
        print(f"  {nombre}: {estado}")
    print("Revísalos y, cuando estés de acuerdo, ejecuta: instalar.py instalar --si")
    return 0


def _plugins(home: Path) -> None:
    """Instala superpowers con el CLI de Claude, para la carpeta personal `home`."""
    claude_cli = shutil.which("claude")
    if not claude_cli:
        print("AVISO: no encuentro el programa 'claude'; los plugins no se han instalado.")
        return
    for orden in PLUGINS:
        try:
            r = subprocess.run([claude_cli, *orden], capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=300, env=verif.entorno(home))
            if r.returncode != 0:
                print(f"AVISO: 'claude {' '.join(orden)}' terminó con error: {(r.stderr or r.stdout).strip()}")
        except (OSError, subprocess.SubprocessError) as error:
            print(f"AVISO: no se pudo ejecutar 'claude {' '.join(orden)}': {error}")


def _escribir_settings(claude: Path, python: str) -> bool:
    """Fusiona los hooks en el settings.json que hay AHORA (p. ej. con lo que añadió el plugin)."""
    _, datos = lib.leer_settings(claude / "settings.json")
    nuevos, cambia = lib.fusionar_settings(datos, python)
    if cambia:
        (claude / "settings.json").write_bytes(lib.texto_settings(nuevos).encode("utf-8"))
    return cambia


def orden_instalar(args: argparse.Namespace) -> int:
    plan = _plan(args)
    claude = plan["claude"]
    print("Cambios que se harán en", claude)
    print("\n".join(_resumen(plan)))
    if plan["cambia_settings"]:
        print("\nDiferencia en settings.json:")
        print(lib.diferencia(plan["settings_antes"], plan["settings_despues"], "settings.json"))
    else:
        print("\nsettings.json ya tiene los dos hooks: no cambia.")
    requiere_desbloqueo = lib.requiere_desbloqueo(claude)
    if requiere_desbloqueo:
        print(f"\n{lib.AVISO_DESBLOQUEO}")
    if not args.si:
        print("No se ha cambiado nada. Si estás de acuerdo, repite la orden añadiendo --si")
        return 3
    if requiere_desbloqueo:
        return 4

    # Solo se escribe lo que cambia; settings.json se fusiona al final, sobre lo que haya entonces.
    escribir = {rel: datos for rel, datos in plan["escribir"].items()
                if not ((claude / rel).is_file() and (claude / rel).read_bytes() == datos)}
    toca_settings = "settings.json" in escribir or not args.sin_plugins
    escribir.pop("settings.json", None)
    afectados = list(escribir) + (["settings.json"] if toca_settings else [])
    creados = [rel for rel in afectados if not (claude / rel).exists()]
    manifiesto = {
        "tipo": "instalacion", "momento": time.time(), "home": str(args.home), "creados": creados,
        "sobrescritos": [rel for rel in afectados if rel not in creados], "borrados": plan["sobran"],
        "carpetas_creadas": copias.carpetas_nuevas(claude, creados),
        "escritos": {rel: copias.sha(datos) for rel, datos in escribir.items()}}
    claude.mkdir(parents=True, exist_ok=True)
    copia = copias.nueva_copia(claude)
    copias.escribir_manifiesto(copia, manifiesto)
    print(f"\nCopia de seguridad hecha en {copia}")
    try:
        if not args.sin_plugins:
            _plugins(args.home)
        for rel, datos in escribir.items():
            (claude / rel).parent.mkdir(parents=True, exist_ok=True)
            (claude / rel).write_bytes(datos)
        for rel in plan["sobran"]:
            (claude / rel).unlink()
        if toca_settings:
            _escribir_settings(claude, plan["perfil"].get("python") or "python")
            if (claude / "settings.json").is_file():
                manifiesto["escritos"]["settings.json"] = copias.sha((claude / "settings.json").read_bytes())
            copias.escribir_manifiesto(copia, manifiesto)
    except (OSError, lib.ErrorInstalacion) as error:
        print(f"ERROR al escribir: {error}\nPara volver a como estaba: instalar.py deshacer --si")
        return 1
    print("Instalación terminada. Comprueba que todo va bien con: instalar.py verificar")
    print("Si algo no te convence, vuelve atrás con: instalar.py deshacer --si")
    return 0


def orden_verificar(args: argparse.Namespace) -> int:
    try:
        python = _cargar_perfil(args)[0].get("python") or "python"
    except lib.ErrorInstalacion:
        python = "python"
    resultados = verif.Verificador(args.home, python).todo(con_plugins=not args.sin_plugins)
    for ok, texto in resultados:
        print(f"{'OK   ' if ok else 'FALLO'} {texto}")
    todo = all(ok for ok, _ in resultados)
    print("Todo correcto." if todo else "Hay comprobaciones que fallan (FALLO). Puedes volver atrás con: "
          "instalar.py deshacer --si")
    return 0 if todo else 2


def orden_deshacer(args: argparse.Namespace) -> int:
    claude = args.home / ".claude"
    par, avisos = copias.copia_pendiente(claude)
    for aviso in avisos:
        print(aviso)
    if par is None:
        print("No hay ninguna instalación que deshacer (no encuentro copias en copias_pipeline/).")
        return 1
    copia, manifiesto = par
    print(f"Se volverá al estado guardado en {copia}:")
    print(f"  se quitan {len(manifiesto.get('creados', []))} ficheros nuevos y se restauran "
          f"{len(manifiesto.get('sobrescritos', [])) + len(manifiesto.get('borrados', []))}.")
    cambiados = copias.modificados(claude, copia, manifiesto)
    if cambiados:
        print("  OJO: estos ficheros han cambiado después de instalar y esos cambios se perderán aquí "
              "(se guardan antes en una copia):")
        print("\n".join(f"    {rel}" for rel in cambiados))
    requiere_desbloqueo = lib.requiere_desbloqueo(claude)
    if requiere_desbloqueo:
        print(f"\n{lib.AVISO_DESBLOQUEO}")
    if not args.si:
        print("No se ha cambiado nada. Si estás de acuerdo, repite la orden añadiendo --si")
        return 3
    if requiere_desbloqueo:
        return 4
    previa = copias.copia_pre_deshacer(claude, copia)
    print(f"Copia del estado actual (antes de deshacer) en {previa}")
    hechos, fallos = copias.deshacer(claude, copia, manifiesto)
    for hecho in hechos:
        print(f"  {hecho}")
    if fallos:
        print("No se ha podido deshacer todo. Fallos:")
        print("\n".join(f"  {fallo}" for fallo in fallos))
        print("Corrige la causa (p. ej. cierra el programa que tenga abierto el fichero) y repite: "
              "instalar.py deshacer --si")
        return 1
    print("Hecho: ~/.claude está como antes de esa instalación. Las copias se conservan por si acaso.")
    return 0


def main(argv: list[str]) -> int:
    args = _argumentos(argv)
    ordenes = {"detectar": orden_detectar, "generar": orden_generar, "instalar": orden_instalar,
               "verificar": orden_verificar, "deshacer": orden_deshacer}
    try:
        return ordenes[args.orden](args)
    except lib.ErrorInstalacion as error:
        print(f"ERROR: {error}")
        return 1
    except UnicodeDecodeError as error:
        print(f"ERROR: un fichero de ~/.claude no está en UTF-8 ({error}); guárdalo en UTF-8 y repite")
        return 1
    except OSError as error:
        print(f"ERROR: {error}")
        return 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
