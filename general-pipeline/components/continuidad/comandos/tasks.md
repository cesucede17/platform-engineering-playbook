---
description: Añade una tarea a tu lista global. Escribe en lenguaje natural qué hay que hacer, para cuándo y de qué proyecto.
argument-hint: <descripción — puedes decir "para el viernes", "mañana", "proyecto X", "urgente">
allowed-tools: Read, Edit, Bash
---
El usuario quiere registrar esta tarea: $ARGUMENTS

Pasos obligatorios:
1. Corre `date +%Y-%m-%d` (o `Get-Date -Format yyyy-MM-dd` en PowerShell) para saber la fecha actual
   y resolver expresiones relativas ("mañana", "el viernes", "en 3 días", "fin de mes") a YYYY-MM-DD.
2. Detecta el proyecto: si el usuario nombra uno, usa ese nombre de carpeta entre corchetes. Si no,
   ejecuta `python "$HOME/.claude/scripts/continuidad/continuidad.py" proyecto` y usa su salida entre
   corchetes (`general` en una raíz de proyectos).
3. Detecta prioridad:
   - "urgente", "importante", "crítico", "ya" → #alta
   - nada mencionado → #media
   - "cuando pueda", "baja prioridad", "no urge" → #baja
4. Si no hay fecha explícita ni relativa en el texto, usa (sin-fecha).
5. Añade UNA línea nueva al FINAL de ~/.claude/TASKS.md justo antes de cualquier línea vacía final,
   con el formato exacto: - [ ] (FECHA) [proyecto] Descripción limpia #prioridad
6. No dupliques la tarea si ya existe una línea idéntica.
7. Muestra al usuario la línea exacta que añadiste y confirma.
