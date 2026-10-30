"""
Reglas de bloqueo de Focus!: qué hace el teléfono la próxima vez que se abre una app.

La fricción sube poco a poco en lugar de bloquear de golpe:
- Mientras no pase su límite de aperturas del día, la app se abre normal.
- Después, cada apertura extra muestra una pausa más larga (leve -> media -> alta).
- Con una sesión de foco activa o el límite diario del plan agotado, se bloquea.

Es Python puro (sin BD) para que el teléfono pueda copiar las mismas reglas y decidir sin conexión.
"""

# (aperturas extra desde las que aplica, nivel, segundos de pausa); de mayor a menor
NIVELES_PAUSA = [
    (5, "alta", 30),
    (3, "media", 15),
    (1, "leve", 5),
]


def accion_app(aperturas_hoy: int, limite_aperturas: int, bloqueo_total: bool) -> dict:
    """Acción para la SIGUIENTE apertura de la app."""
    if bloqueo_total:
        return {"accion": "bloquear", "nivel": None, "duracion_seg": 0}
    extra = aperturas_hoy + 1 - limite_aperturas
    for desde, nivel, segundos in NIVELES_PAUSA:
        if extra >= desde:
            return {"accion": "pausa", "nivel": nivel, "duracion_seg": segundos}
    return {"accion": "permitir", "nivel": None, "duracion_seg": 0}
