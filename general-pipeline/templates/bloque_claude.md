<!-- pipeline:inicio -->
## Pipeline personal (generado por guia_general)

Responde siempre en {{idioma}}, salvo que se pida lo contrario.

### Explicaciones didácticas

{{bloque_explicaciones}}

### Journal al cerrar el día

{{bloque_journal}}

Si dices «apúntame», «recuérdame», «añade una tarea» o «que no se me olvide», sigue el
procedimiento de `/tasks`.

### Vigilante (guardian)

Hay un hook que se ejecuta antes de cada acción que edita ficheros o lanza comandos, y bloquea
rutas protegidas, cambios en las reglas de calidad, borrados masivos, git destructivo, Docker con
pérdida de volúmenes, cambios en el servidor y cambios en la configuración de Claude Code. Son
bloqueos duros, no avisos: si alguno salta, no lo esquives (tampoco con un script). Explica por qué
hace falta la acción y pide que se cree a mano el fichero de desbloqueo en la carpeta que indique
el mensaje. Esa carpeta queda libre durante 2 horas; pasado ese tiempo deja de valer.

{{aviso_servidores}}

### Modo de ejecución

{{bloque_ejecucion}}
<!-- pipeline:fin -->
