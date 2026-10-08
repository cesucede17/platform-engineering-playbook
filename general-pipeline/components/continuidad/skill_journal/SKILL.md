---
name: journal
description: Escribe el resumen de la sesión en docs/journal/ del proyecto. Úsala cuando el usuario cierre la jornada ("acabo por hoy", "termino por hoy", "cerramos por hoy", "fin de la jornada", "lo dejamos aquí por hoy") o cuando el arranque avise de que una sesión anterior no dejó resumen (modo rescate).
---

# Journal de sesión

El journal es lo que lee el arranque de Claude Code para enseñar «dónde lo dejé». Los títulos son
fijos: el script los lee. Escribe en castellano, con viñetas cortas y concretas. Nunca copies
secretos ni contenido de `.env`. No hagas commit del journal salvo que el usuario lo pida.

## Datos que necesitas

Estos comandos funcionan igual en Bash y en PowerShell (no uses `~` ni `date`):

```
python "$HOME/.claude/scripts/continuidad/continuidad.py" ruta     # carpeta del proyecto
python "$HOME/.claude/scripts/continuidad/continuidad.py" sesion   # id de la sesión en curso
python "$HOME/.claude/scripts/continuidad/continuidad.py" ahora    # fecha y hora: AAAA-MM-DD HH:MM
python "$HOME/.claude/scripts/continuidad/continuidad.py" journal  # carpeta donde va el journal
```

El arranque también deja en el contexto una línea `(sesión: <id>)`; si está, ese es el id.

Fichero: `<carpeta del comando journal de arriba>/<AAAA-MM-DD>.md`. Por defecto es
`<ruta>/docs/journal/<AAAA-MM-DD>.md`, salvo que `continuidad.json` tenga configurado un journal
central, en cuyo caso cambia de carpeta pero el formato es el mismo. Si no existe, créalo con la
línea `# Journal <AAAA-MM-DD>` y una línea en blanco. Si existe, añade la sesión al final.

## Plantilla de una sesión

```markdown
## Sesión HH:MM
<!-- sesion: <id> -->
### Hecho
- …
### Decisiones
- …
### A no olvidar
- …
### Siguiente paso
- …
### Abierto
- …
```

- Una sección vacía lleva `- (nada)`.
- **Hecho:** lo que quedó terminado y comprobado en esta sesión, no lo que se intentó.
- **Decisiones:** lo que se decidió y por qué, en una línea.
- **A no olvidar:** avisos con consecuencias (p. ej. «no desplegar sin coordinar con X», «el
  dataset bueno es V6»).
- **Siguiente paso:** la primera acción concreta de la próxima sesión.
- **Abierto:** lo pendiente que no es el siguiente paso.

## Modo cierre

1. Escribe la sesión con la plantilla, **sin pedir confirmación**, con la herramienta Write o Edit.
   Si en el fichero de hoy ya hay una sesión con este mismo id (`<!-- sesion: <id> -->`),
   sustitúyela en lugar de añadir otra.
2. Enseña al usuario el texto escrito y la ruta del fichero.
3. Si «Abierto» tiene puntos, pregunta: «¿Apunto estas N como tareas?». Si dice que sí, añádelas
   siguiendo el procedimiento de `~/.claude/commands/tasks.md`. La etiqueta del proyecto sale de
   `python "$HOME/.claude/scripts/continuidad/continuidad.py" proyecto`.

## Modo rescate

Cuando el arranque diga «La sesión del … no dejó resumen» con la ruta de una transcripción `.jsonl`:

1. `python "$HOME/.claude/scripts/continuidad/rescate.py" "<ruta.jsonl>"` imprime la ruta de un texto
   condensado de esa conversación.
2. Lee ese fichero.
3. Escribe la sesión en el journal de **la fecha de «Última actividad»**, con el título
   `## Sesión HH:MM (reconstruida)` (la hora de «Última actividad») y
   `<!-- sesion: <id> -->`, donde el id es el nombre del `.jsonl` sin extensión.
4. Enseña lo que has escrito. No añadas tareas sin preguntar.
5. Después sigue con lo que el usuario haya pedido.

## Tareas en conversación

Si el usuario dice «apúntame…», «recuérdame…», «añade una tarea…» o «que no se me olvide…», sigue
los pasos de `~/.claude/commands/tasks.md` y enseña la línea añadida.
