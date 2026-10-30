"""Pruebas de la red neuronal, el algoritmo genético y la búsqueda A* (app/ia/)."""
import pytest

from app.ia import busqueda, genetico
from app.ia.modelo_uso import modelo

USO = [8, 3, 0, 0, 0, 0, 2, 10, 12, 10, 8, 8, 15, 12, 8, 8, 12, 18, 22, 25, 30, 30, 25, 15]


def test_red_neuronal_supera_las_lineas_base():
    r = modelo().reporte["resultados"]
    red = r["red_neuronal"]["mae_min"]
    assert all(red < r[base]["mae_min"] for base in ("ayer", "promedio_7", "mismo_dia_semana_pasada"))


def test_red_neuronal_aprende_el_fin_de_semana():
    semana = [200.0] * 7
    assert modelo().pronosticar(semana, 5) > modelo().pronosticar(semana, 1)


def test_genetico_supera_el_horario_a_mano_y_es_reproducible():
    r = genetico.optimizar("redes", 5, USO, max_pausas=8)
    assert r["aptitud"] > r["aptitud_a_mano"]
    assert r["minutos_ahorrados_esperados"] > r["minutos_ahorrados_a_mano"]
    assert len(r["horario"]) <= 8
    historial = r["mejor_aptitud_por_generacion"]
    assert all(b >= a for a, b in zip(historial, historial[1:]))   # el elitismo nunca pierde al mejor
    assert genetico.optimizar("redes", 5, USO, max_pausas=8) == r


def test_genetico_no_pone_pausas_sin_uso():
    r = genetico.optimizar("video", 2, [0.0] * 20 + [40.0] * 4, max_pausas=4)
    assert all(p["hora"] >= 20 for p in r["horario"])


@pytest.mark.parametrize("limite, meta, semanas", [(300, 120, 12), (240, 180, 12), (400, 90, 16), (300, 120, 4)])
def test_astar_encuentra_el_optimo_con_menos_nodos(limite, meta, semanas):
    astar = busqueda.buscar(limite, meta, semanas)
    uniforme = busqueda.buscar(limite, meta, semanas, usar_heuristica=False)
    assert astar["costo"] == uniforme["costo"]
    assert astar["expandidos"] <= uniforme["expandidos"]
    assert busqueda.heuristica(limite, meta) <= astar["costo"]       # admisible
    ruta = astar["ruta"]
    assert ruta[0]["limite_min"] == limite and ruta[-1]["limite_min"] <= meta and len(ruta) - 1 <= semanas


def test_astar_prefiere_cambios_graduales():
    pasos = [p["reduccion_pct"] for p in busqueda.buscar(300, 120, 12)["ruta"][1:]]
    assert max(pasos) < 20


def test_astar_sin_solucion():
    assert busqueda.buscar(300, 120, 2) is None
