---
description: Marca una o varias tareas como completadas
argument-hint: <parte del texto de la tarea a completar, o "todas las de hoy", o un número>
allowed-tools: Read, Edit, Bash
---
El usuario quiere completar: $ARGUMENTS

1. Lee ~/.claude/TASKS.md.
2. Busca todas las tareas pendientes (`- [ ]`) cuyo texto coincida parcialmente
   con lo que el usuario escribió (búsqueda case-insensitive).
   - Si dice "todas las de hoy" o "las de hoy", marca todas las de la fecha actual.
   - Si dice un número (ej. "3"), numera las pendientes en orden y marca la nº3.
3. Si hay UNA coincidencia: cambia `- [ ]` por `- [x]` y confirma.
4. Si hay VARIAS coincidencias: lista las coincidencias numeradas y pregunta cuál(es) marcar.
5. Si hay CERO coincidencias: di que no encontraste ninguna tarea que coincida y sugiere `/tasks-list`.
