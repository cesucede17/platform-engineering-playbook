# guardian: el vigilante de Claude Code

guardian es un pequeño programa que Claude Code ejecuta **antes** de cada acción de Claude que
edita ficheros o lanza comandos (Bash o PowerShell). Mira qué va a hacer y decide entre dejarla
pasar o bloquearla.

## Qué bloquea

| Regla | Ejemplo |
|---|---|
| `ruta-protegida` | Editar o borrar algo en las rutas protegidas que elegiste en la entrevista (por ejemplo, una carpeta `OBSOLETO` o un repo externo de solo lectura) o en los segmentos protegidos, como cualquier `data/raw/` |
| `reglas-calidad` | Cambiar `ruff.toml`, `pytest.ini`, `tsconfig.json`… o las secciones `[tool.ruff]`/`[tool.pytest]`/`[tool.mypy]`/`[tool.coverage]` de `pyproject.toml` (crearlos por primera vez sí se permite). Por comando (`sed -i`, `rm`, `>>`, `cp`…) basta con que el fichero exista |
| `borrado-masivo` | `rm -rf un_proyecto`, `Remove-Item -Recurse -Force` sobre una de tus raíces de proyectos, `rm -rf *` en un proyecto |
| `git-destructivo` | `git push --force`, `git reset --hard`, `git clean -fdx`, `git branch -D` |
| `docker-datos` | `docker compose down -v`, `docker volume rm`, `docker system prune` |
| `servidor` | Cualquier cosa en los servidores compartidos que indicaste en la entrevista (por nombre o por IP) que no sea mirar (`docker ps`, logs, `git log`…). `git push mi-servidor:…` sí se permite |
| `autoproteccion` | Tocar `~/.claude/settings.json`, `settings.local.json`, `~/.claude/hooks/` o el `.claude/settings.json` de un proyecto (también borrar o mover las carpetas que los contienen) |
| `desbloqueo` | Que Claude cree, edite o borre un fichero `.claude-unlock` (nunca se permite) |

## Cómo desbloquear

1. Crea **tú, a mano**, un fichero vacío llamado `.claude-unlock` en la carpeta que quieras liberar
   (con el explorador de archivos, o desde Claude Code con `! touch .claude-unlock` en Linux o `! New-Item .claude-unlock` en Windows).
2. Libera esa carpeta y todo lo que contiene durante **2 horas**. Después deja de valer solo.
3. Excepciones: para `~/.claude/settings.json` y `hooks/` tiene que estar en `~/.claude/`, y
   para el `.claude/settings.json` de un proyecto, en la carpeta de ese proyecto.

## Reglas desactivables

En `guardian_reglas.json` puedes añadir una clave `"desactivadas": [...]` con los nombres de las
reglas que no quieres que bloqueen: `borrado-masivo`, `git-destructivo`, `docker-datos`,
`reglas-calidad`, `servidor`. Si la clave no está, el comportamiento es el de siempre (todas
activas). `autoproteccion`, `ruta-protegida` y `desbloqueo` **no se pueden desactivar** aunque
aparezcan en la lista: si se pudieran, Claude podría apagar el propio vigilante.

## Modo prueba y modo activo

En `~/.claude/hooks/guardian_reglas.json`:

- `"modo": "prueba"`: no bloquea nada (salvo la autoprotección); apunta en el log lo que
  *habría* bloqueado.
- `"modo": "activo"`: bloquea.

Para cambiar de modo, edita ese fichero a mano. Claude no puede hacerlo.

## El registro

`~/.claude/hooks/guardian.log`, una línea por evento: fecha, tipo (`BLOQUEADO`, `HABRÍA BLOQUEADO`,
`DESBLOQUEO USADO`, `ERROR`), herramienta, acción, carpeta y regla.

## Detalles que conviene saber

- **El nombre del fichero de desbloqueo no se puede ni mencionar.** Cualquier comando de Bash o
  PowerShell cuyo texto contenga `.claude-unlock` se bloquea siempre, sea lo que sea: también un
  `grep`, un `cat` o un `git commit -m "…"` que lo cite. Si hace falta hablar de él en un mensaje de
  commit, escríbelo de otra forma («fichero de desbloqueo»).
- **Las rutas de `~/.claude/hooks` y de los `settings` también.** Un comando que mencione
  `.claude/hooks` o `.claude/settings…` (con `/` o `\`) se bloquea siempre, salvo que sea de solo
  lectura: `cat`, `type`, `ls`, `dir`, `head`, `tail`, `grep`, `rg`, `findstr`, `wc`, `Get-Content`,
  `Get-ChildItem`, `Get-Item`, `Select-String`, `Test-Path`, `cd`/`Set-Location`, y `python …guardian.py`
  o `python …instalar.py`. Así, por ejemplo, un `git commit -m "toca .claude/settings"` o un
  `ssh mi-servidor "cat ~/.claude/settings.json"` se bloquean. Lo mismo si el comando trabaja dentro de
  `~/.claude/hooks` (tras un `cd`, o con `git -C`).
- **`settings.local.json` está protegido** igual que `settings.json`, tanto el global como el de
  cada proyecto.
- **Si guardian no puede cargarse** (instalación rota, un fichero que falta), bloquea **siempre**,
  también en modo prueba.
- **Un modo desconocido** en `guardian_reglas.json` (una errata como `"pruebas"`) equivale a
  `"activo"`.
- **El log guarda los comandos en claro** (recortados a 200 caracteres). Si un comando lleva una
  contraseña o un token, quedará escrito en `guardian.log`.

## Límites conocidos

guardian lee el **texto** de los comandos. Si Claude escribiera un script que borra ficheros y lo
ejecutara, guardian vería «ejecutar un script», no el borrado. Protege contra errores y atajos, no
contra una evasión deliberada.

Todavía **no analiza lo que va dentro de envoltorios**: `bash -c "…"`, `cmd /c …`,
`powershell -Command "…"`, `find … -delete` / `-exec rm`, `xargs rm` o tuberías hacia
`Remove-Item` (`Get-ChildItem … | Remove-Item`). Tenlo en cuenta al decidir si pasas a modo activo.

Tampoco reconoce el nombre del fichero de desbloqueo si se construye por partes (por ejemplo,
concatenando dos trozos en un script): solo lo detecta escrito tal cual.

## Instalación y actualización

Estas piezas las instaló la guía `guia_general`. Para actualizarlas o reconfigurarlas, vuelve a
seguir el `PROMPT_INSTALAR.md` de esa guía (o ejecuta `instalar.py instalar --reconfigurar` desde
su carpeta `herramientas/`). Antes, crea tú a mano el fichero de desbloqueo en `~/.claude/`
(Claude no puede crearlo). Para cambiar solo las reglas, edita a mano
`~/.claude/hooks/guardian_reglas.json` o repite la entrevista de la guía.
