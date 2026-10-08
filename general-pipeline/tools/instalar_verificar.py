"""Comprobaciones de `instalar.py verificar`. Solo biblioteca estándar.

Los hooks se ejecutan como los lanzará Claude Code: con la orden exacta (`command`) de settings.json,
mediante `bash -c` si hay bash, o con el lanzador del perfil si no lo hay. Siempre con HOME y
USERPROFILE apuntando a la carpeta personal que se verifica.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import instalar_lib as lib

SKILLS_Y_COMANDOS = ("skills/journal/SKILL.md", "skills/mejorar-pipeline/SKILL.md", "commands/tasks.md",
                     "commands/tasks-list.md", "commands/tasks-done.md", "commands/tasks-edit.md",
                     "commands/explica.md")


def entorno(home: Path) -> dict:
    datos = dict(os.environ, HOME=str(home), USERPROFILE=str(home), PYTHONDONTWRITEBYTECODE="1",
                 PYTHONIOENCODING="utf-8")
    datos.pop("CLAUDE_CODE_SESSION_ID", None)
    return datos


def bash() -> str | None:
    """bash utilizable para los hooks. En Windows se descarta el bash de WSL (System32/WindowsApps)."""
    ruta = shutil.which("bash")
    if ruta and os.name == "nt" and any(x in ruta.lower() for x in ("system32", "windowsapps")):
        return None
    return ruta


def _comando(settings: dict, evento: str, fragmento: str) -> str | None:
    hooks = settings.get("hooks") if isinstance(settings.get("hooks"), dict) else {}
    for entrada in hooks.get(evento) or []:
        for hook in (entrada.get("hooks") or []) if isinstance(entrada, dict) else []:
            if isinstance(hook, dict) and fragmento in str(hook.get("command", "")):
                return str(hook["command"])
    return None


class Verificador:
    def __init__(self, home: Path, python: str):
        self.home, self.python = home, python
        self.claude = home / ".claude"
        try:
            _, self.settings = lib.leer_settings(self.claude / "settings.json")
            self.error_settings = ""
        except lib.ErrorInstalacion as error:
            self.settings, self.error_settings = {}, str(error)

    def _ejecutar(self, evento: str, fragmento: str, script: Path, entrada: str):
        """(proceso, None) o (None, motivo del fallo)."""
        comando = _comando(self.settings, evento, fragmento)
        if comando is None:
            return None, f"settings.json no tiene el hook de {fragmento}"
        lanzador = shutil.which(self.python)
        if not lanzador:
            return None, (f"no encuentro el lanzador de Python '{self.python}' que usan los hooks; "
                          "revisa la clave \"python\" del perfil")
        if not script.is_file():
            return None, f"falta {script}"
        orden = [bash(), "-c", comando] if bash() else [lanzador, str(script)]
        try:
            proceso = subprocess.run(orden, input=entrada.encode("utf-8"), capture_output=True,
                                     env=entorno(self.home), cwd=str(self.home), timeout=60)
        except (OSError, subprocess.SubprocessError) as error:
            return None, f"no se pudo ejecutar '{comando}': {error}"
        return proceso, None

    def guardian(self) -> tuple[bool, str]:
        log = self.claude / "hooks" / "guardian.log"
        try:
            reglas = json.loads((self.claude / lib.CONFIG_GUARDIAN).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            return False, f"no se pueden leer las reglas de guardian ({error})"
        antes = len(log.read_bytes().splitlines()) if log.exists() else 0
        entrada = json.dumps({"tool_name": "Bash", "tool_input": {"command": "git reset --hard"},
                              "cwd": str(self.home)})
        proceso, fallo = self._ejecutar("PreToolUse", "guardian.py", self.claude / "hooks" / "guardian.py", entrada)
        if fallo:
            return False, f"guardian: {fallo}"
        despues = len(log.read_bytes().splitlines()) if log.exists() else 0
        esperado = 0 if reglas.get("modo") == "prueba" else 2
        if proceso.returncode != esperado:
            return False, (f"guardian salió con {proceso.returncode} (se esperaba {esperado}): "
                           f"{proceso.stderr.decode('utf-8', 'replace').strip()}")
        if "git-destructivo" in reglas.get("desactivadas", []):
            return True, "guardian responde (git-destructivo está desactivada: no se espera línea en el log)"
        if despues <= antes:
            return False, "guardian no ha escrito en guardian.log"
        return True, f"guardian responde en modo {reglas.get('modo')} y anota en guardian.log"

    def continuidad(self) -> tuple[bool, str]:
        script = self.claude / "scripts" / "continuidad" / "continuidad.py"
        proceso, fallo = self._ejecutar("SessionStart", "continuidad.py", script, "{}")
        if fallo:
            return False, f"continuidad: {fallo}"
        texto = proceso.stdout.decode("utf-8", "replace")
        if proceso.returncode == 0 and "===" in texto and "error inesperado" not in texto:
            return True, "continuidad muestra el resumen de arranque"
        return False, ("continuidad no muestra el resumen: "
                       f"{texto.strip() or proceso.stderr.decode('utf-8', 'replace').strip()}")

    def ficheros(self) -> tuple[bool, str]:
        faltan = [rel for rel in SKILLS_Y_COMANDOS if not (self.claude / rel).is_file()]
        return not faltan, "skills y comandos instalados" if not faltan else f"faltan: {', '.join(faltan)}"

    def hooks(self) -> tuple[bool, str]:
        if self.error_settings:
            return False, self.error_settings
        ok = bool(_comando(self.settings, "PreToolUse", "guardian.py")) and \
            bool(_comando(self.settings, "SessionStart", "continuidad.py"))
        return ok, "settings.json tiene los hooks de guardian y continuidad" if ok else \
            "a settings.json le falta algún hook (guardian en PreToolUse, continuidad en SessionStart)"

    def plugins(self) -> tuple[bool, str]:
        activos = self.settings.get("enabledPlugins") if isinstance(self.settings.get("enabledPlugins"), dict) else {}
        if not any(k.startswith("superpowers@") and v is True for k, v in activos.items()):
            return False, "superpowers no está activado en enabledPlugins de settings.json"
        claude_cli = shutil.which("claude")
        if not claude_cli:
            return False, "no encuentro el programa 'claude' para comprobar los plugins"
        try:
            r = subprocess.run([claude_cli, "plugin", "list"], capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=120, env=entorno(self.home))
        except (OSError, subprocess.SubprocessError) as error:
            return False, f"no se pudo ejecutar 'claude plugin list': {error}"
        ok = "superpowers" in r.stdout
        return ok, "el plugin superpowers está instalado y activado" if ok else \
            "el plugin superpowers no aparece en 'claude plugin list'"

    def todo(self, con_plugins: bool) -> list[tuple[bool, str]]:
        resultados = [self.guardian(), self.continuidad(), self.ficheros(), self.hooks()]
        if con_plugins:
            resultados.append(self.plugins())
        return resultados
