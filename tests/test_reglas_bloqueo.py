"""Pruebas de la escalera de fricción (app/utils/reglas_bloqueo.py)."""
import pytest

from app.utils.reglas_bloqueo import accion_app


@pytest.mark.parametrize("aperturas, accion, nivel, segundos", [
    (0, "permitir", None, 0),
    (4, "permitir", None, 0),     # la 5.ª apertura todavía entra en el límite
    (5, "pausa", "leve", 5),
    (6, "pausa", "leve", 5),
    (7, "pausa", "media", 15),
    (8, "pausa", "media", 15),
    (9, "pausa", "alta", 30),
    (40, "pausa", "alta", 30),
])
def test_la_pausa_sube_con_las_aperturas_de_mas(aperturas, accion, nivel, segundos):
    assert accion_app(aperturas, 5, False) == {"accion": accion, "nivel": nivel, "duracion_seg": segundos}


def test_limite_cero_siempre_pide_pausa():
    assert accion_app(0, 0, False)["accion"] == "pausa"


def test_bloqueo_total_gana_sobre_todo():
    assert accion_app(0, 10, True) == {"accion": "bloquear", "nivel": None, "duracion_seg": 0}
