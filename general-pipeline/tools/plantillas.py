"""Plantillas: huecos {{clave}} para generar la configuración personal de alguien a partir de
`perfil_pipeline.json`. Sin dependencias externas (solo biblioteca estándar).
"""
from __future__ import annotations

import json
import re
from datetime import date, timedelta

_PATRON = re.compile(r"\{\{(\w+)\}\}")

# Mismo conjunto que guardian_lib.nucleo.DESACTIVABLES: las únicas reglas que se pueden apagar
# desde "desactivadas". "autoproteccion", "ruta-protegida" y "desbloqueo" nunca pueden aparecer
# ahí (si se pudieran, Claude podría apagar el propio vigilante).
DESACTIVABLES = {"borrado-masivo", "git-destructivo", "docker-datos", "reglas-calidad", "servidor"}


def huecos(texto: str) -> set[str]:
    """Nombres de los huecos `{{clave}}` presentes en el texto, sin repetir."""
    return set(_PATRON.findall(texto))


def rellenar(texto: str, valores: dict, json_strings: bool = False) -> str:
    """Sustituye cada `{{clave}}` de `texto` por `valores[clave]`.

    - Una lista o un dict se insertan como JSON compacto: sirve para un hueco que es el valor
      completo de una clave JSON, p. ej. `"rutas_protegidas": {{rutas_protegidas}}`.
    - El resto de valores se insertan como texto plano, salvo que `json_strings=True`
      (plantillas `.json`, donde el hueco ya vive dentro de las comillas de la plantilla, p. ej.
      `"home": "{{home}}"`): entonces una cadena se JSON-escapa (comillas y barras invertidas)
      antes de insertarse, para que el resultado siga siendo JSON válido aunque el valor las
      contenga. Las rutas del perfil usan `/`, así que normalmente no hace falta escapar nada.
    - Lanza `KeyError` si queda un hueco sin valor en `valores`.
    """

    def _sub(coincidencia: re.Match) -> str:
        clave = coincidencia.group(1)
        valor = valores[clave]
        if isinstance(valor, (list, dict)):
            return json.dumps(valor, ensure_ascii=False)
        if json_strings and isinstance(valor, str):
            # json.dumps('texto') -> '"texto"'; quitamos las comillas que ya pone la plantilla.
            return json.dumps(valor, ensure_ascii=False)[1:-1]
        return str(valor)

    return _PATRON.sub(_sub, texto)


def _bloque_explicaciones(nivel: str) -> str:
    if nivel == "poca":
        return (
            "Explica cada término técnico (de desarrollo, de machine learning, de estadística o "
            "de plataformas) la primera vez que aparezca en la conversación o en un informe: "
            "lenguaje llano, sin jerga, con una analogía de la vida cotidiana y un ejemplo de tus "
            "propios proyectos. Si el término se repite en la misma conversación, no hace falta "
            "explicarlo otra vez. El comando `/explica <término>` da la versión larga en cualquier "
            "momento."
        )
    if nivel == "media":
        return (
            "Explica en 1-2 frases, con un ejemplo de tus propios proyectos, los términos que no "
            "sean de uso común (de desarrollo, de machine learning, de estadística o de "
            "plataformas). Los términos habituales no hace falta explicarlos. El comando "
            "`/explica <término>` da la versión larga en cualquier momento."
        )
    if nivel == "mucha":
        return (
            "Explica solo los términos poco frecuentes o ambiguos, en una frase breve. El comando "
            "`/explica <término>` da la versión larga si hace falta."
        )
    raise ValueError(f"nivel desconocido: {nivel!r}")


def _bloque_journal(journal_cierre: str) -> str:
    if journal_cierre == "automatico":
        return (
            'Cuando digas que terminas la sesión por hoy ("acabo por hoy", "termino por hoy", '
            '"cerramos por hoy", "fin de la jornada"), usa la skill `journal`: escribe '
            "directamente el resumen de la sesión, sin pedir confirmación, enséñalo con su ruta y "
            "propón como tareas los puntos de «Abierto»."
        )
    if journal_cierre == "preguntando":
        return (
            "Cuando digas que terminas la sesión por hoy, pregunta primero si quieres el resumen "
            "de la skill `journal`. Si dices que sí, escríbelo, enséñalo con su ruta y propón como "
            "tareas los puntos de «Abierto»."
        )
    if journal_cierre == "no":
        return (
            "No escribas resúmenes de sesión por tu cuenta. Si alguna vez quieres uno, pide la "
            "skill `journal` explícitamente."
        )
    raise ValueError(f"journal_cierre desconocido: {journal_cierre!r}")


def _bloque_ejecucion(ejecucion: str) -> str:
    if ejecucion == "subagentes":
        return (
            "Para tareas grandes, divide el trabajo por fases, usa subagentes y revisa cada fase "
            "antes de seguir con la siguiente."
        )
    if ejecucion == "paso_a_paso":
        return "Para tareas grandes, ve paso a paso y pregunta antes de seguir con el siguiente."
    raise ValueError(f"ejecucion desconocido: {ejecucion!r}")


def _aviso_servidores(servidores: list[dict]) -> str:
    if not servidores:
        return ""
    compartidos: list[str] = []
    for servidor in servidores:
        nombre = servidor.get("compartido_con")
        if nombre and nombre not in compartidos:
            compartidos.append(nombre)
    quien = ", ".join(compartidos) if compartidos else "quien lo comparte"
    return (
        "### Servidores compartidos\n\n"
        "Los servidores configurados son de solo lectura: no despliegues ni reinicies nada en "
        f"ellos sin avisar antes a {quien}. Esto no es solo cortesía: guardian bloquea en duro "
        "cualquier cambio en el servidor que no sea de solo mirar, así que avisar antes es lo que "
        "evita llegar a pedir el desbloqueo."
    )


def valores_desde_perfil(perfil: dict) -> dict:
    """Valores que usan las plantillas de `general/plantillas/`, calculados a partir de un
    `perfil_pipeline.json` (formato 1). Las claves del resultado son exactamente los nombres de
    los huecos `{{clave}}` que usan las plantillas.
    """
    raices = list(perfil["raices"])
    servidores = perfil.get("servidores", [])
    hosts = [host for servidor in servidores for host in servidor.get("hosts", [])]
    fecha_instalacion = date.fromisoformat(perfil["fecha_instalacion"])
    fecha_revision_guardian = (fecha_instalacion + timedelta(days=7)).isoformat()

    desactivadas = list(perfil["desactivadas"])
    no_permitidas = [d for d in desactivadas if d not in DESACTIVABLES]
    if no_permitidas:
        raise ValueError(
            f"'desactivadas' no puede incluir {no_permitidas!r}: solo se puede desactivar una "
            f"regla de {sorted(DESACTIVABLES)}; autoproteccion, ruta-protegida y desbloqueo "
            "nunca se pueden desactivar."
        )

    return {
        # guardian
        "home": perfil["home"],
        "rutas_protegidas": list(perfil["rutas_protegidas"]),
        "segmentos_protegidos": list(perfil["segmentos_protegidos"]),
        "raices_proyectos": raices,
        "desactivadas": desactivadas,
        "hosts": hosts,
        # continuidad
        "raices": raices,
        "excluidos": list(perfil["excluidos"]),
        "solo_lectura": list(perfil["solo_lectura"]),
        "secciones": list(perfil["secciones_arranque"]),
        "journal_central": perfil["journal_central"],
        # TASKS.md
        "fecha_revision_guardian": fecha_revision_guardian,
        # bloque_claude.md
        "idioma": perfil["idioma"],
        "bloque_explicaciones": _bloque_explicaciones(perfil["nivel"]),
        "bloque_journal": _bloque_journal(perfil["journal_cierre"]),
        "bloque_ejecucion": _bloque_ejecucion(perfil["ejecucion"]),
        "aviso_servidores": _aviso_servidores(servidores),
        # uso general (no es un hueco de ninguna plantilla de hoy, pero lo puede necesitar
        # ENTREVISTA.md / instalar.py: "tus proyectos viven bajo <raiz_principal>")
        "raiz_principal": raices[0],
    }
