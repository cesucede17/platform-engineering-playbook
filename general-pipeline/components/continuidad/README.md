# continuidad: «¿por dónde lo dejé?»

Al abrir Claude Code, un pequeño programa (`continuidad.py`) mira en qué carpeta estás y enseña:

- **En un proyecto** (hijo directo de una de tus raíces de proyectos): el último resumen de
  sesión de ese proyecto, sus tareas, el estado de git y cuántas tareas hay en otras carpetas.
- **En una raíz de proyectos**: una línea por proyecto con su última sesión, el siguiente paso y
  las tareas.

Ese texto también le llega a Claude, que empieza la sesión sabiendo dónde lo dejaste.

## El journal

Los resúmenes viven en `docs/journal/AAAA-MM-DD.md` de cada proyecto. Los escribe Claude con la
skill `journal` cuando dices «acabo por hoy», «termino por hoy», «cerramos por hoy» o «fin de la
jornada». Si se te olvida, el arranque detecta la sesión sin resumen y Claude la reconstruye a
partir de la conversación guardada (sale marcada como «reconstruida»).

## Tareas

Sigue habiendo un único `~/.claude/TASKS.md`. La etiqueta de cada tarea es el nombre de la carpeta
del proyecto (`[nombre_proyecto]`, `[otro_proyecto]`), o `[general]` en la raíz. `/tasks` la pone sola, y
también funciona decirle a Claude «apúntame…» o «recuérdame…». `~/.claude/projects.txt` ya no se usa.

## Configuración

`~/.claude/scripts/continuidad/continuidad.json`: raíces de proyectos, carpetas excluidas del
panorama, máximo de líneas (40), de tareas (8), mensajes mínimos para el rescate (10) y
`solo_lectura`: repos externos que nunca se modifican (p. ej. un repo externo que solo consultas).
Dentro de ellos se trabaja como en una raíz de proyectos: etiqueta `[general]` y el journal va a
la carpeta `docs/journal/` de esa raíz.

Dos claves opcionales, pensadas para adaptar el arranque a otra persona sin tocar el código. Si no
aparecen en el JSON, el comportamiento es exactamente el de hoy:

- **`secciones`**: lista con un subconjunto de `["sesion", "tareas", "git", "otras", "panorama"]`;
  por defecto, las cinco. Controla qué bloques del arranque se enseñan: `sesion` (última sesión y
  sus viñetas), `tareas` (las del proyecto, o las de `[general]` en la raíz), `git` (la línea
  `Git:`), `otras` (el aviso de tareas en otras carpetas) y `panorama` (las filas de proyectos en la
  raíz). Las cabeceras (`=== … ===`), los avisos de rescate, los errores y la línea de sesión
  siempre se enseñan, estén o no en `secciones`.
- **`journal_central`**: ruta a una carpeta donde guardar el journal de todos los proyectos juntos,
  cada uno en su propia subcarpeta (`<journal_central>/<etiqueta>`). Vacío (el valor por defecto)
  significa que cada proyecto journalea en su propio `docs/journal/`. El subcomando
  `continuidad.py journal` imprime la carpeta que toca para la carpeta actual, y es lo que usa la
  skill `journal` para saber dónde escribir.

## Instalación y actualización

Estas piezas las instaló la guía `guia_general`. Para actualizarlas o reconfigurarlas, vuelve a
seguir el `PROMPT_INSTALAR.md` de esa guía (o ejecuta `instalar.py instalar --reconfigurar` desde
su carpeta `herramientas/`); antes, crea tú a mano el fichero de desbloqueo en `~/.claude/`. Para
cambiar solo la configuración, edita a mano `continuidad.json` o repite la entrevista de la guía.
