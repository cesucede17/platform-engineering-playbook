---
description: Muestra las tareas pendientes ordenadas por urgencia y fecha
allowed-tools: Read, Bash
---
Lee ~/.claude/TASKS.md. Obtén la fecha actual con `date +%Y-%m-%d` o PowerShell equivalente.

Muestra SOLO las tareas pendientes (las que tienen `- [ ]`, NO las que tienen `- [x]`).

Agrúpalas así, en este orden:
1. **🔴 VENCIDAS** — fecha anterior a hoy (resalta que están atrasadas)
2. **🟠 HOY** — fecha igual a hoy
3. **🟡 ESTA SEMANA** — fecha entre mañana y 7 días desde hoy
4. **🔵 PRÓXIMAS** — fecha posterior a esta semana
5. **⚪ SIN FECHA** — las que tienen (sin-fecha)

Dentro de cada grupo, ordena por prioridad: #alta primero, luego #media, luego #baja.

Al final muestra un conteo: "X tareas pendientes (Y vencidas, Z para hoy)".

Si no hay tareas pendientes, di "No hay tareas pendientes. Usa /tasks para añadir una."
