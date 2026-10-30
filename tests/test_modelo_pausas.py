"""Pruebas del simulador y del modelo de pausas ignoradas (app/ia/)."""
from app.ia.modelo_pausas import modelo
from app.ia.simulador import simular


def test_simulador_es_reproducible():
    assert simular(usuarios=5, dias=3, semilla=1) == simular(usuarios=5, dias=3, semilla=1)
    assert simular(usuarios=5, dias=3, semilla=1) != simular(usuarios=5, dias=3, semilla=2)


def test_simulador_tiene_ambas_clases():
    filas = simular(usuarios=30, dias=14)
    pct = sum(f["ignorada"] for f in filas) / len(filas)
    assert 0.2 < pct < 0.6


def test_modelo_supera_la_linea_base():
    resultados = modelo().reporte["resultados"]
    elegido = resultados[modelo().nombre]
    assert elegido["exactitud"] > resultados["linea_base"]["exactitud"] + 0.05
    assert elegido["auc"] > 0.7


def test_modelo_descubre_los_factores_del_simulador():
    coef = modelo().reporte["coeficientes_logistica"]
    assert coef["uso_previo_min"] > 0
    assert coef["pausas_previas_hoy"] > 0
    assert coef["categoria_productividad"] < 0
    assert coef["tipo_alta"] < coef["tipo_leve"]


def test_contexto_riesgoso_vs_tranquilo():
    m = modelo()
    riesgo = m.probabilidad(categoria="redes", tipo="leve", hora=23, dia_semana=5, uso_previo_min=60, pausas_previas_hoy=6)
    tranquilo = m.probabilidad(categoria="productividad", tipo="alta", hora=8, dia_semana=1, uso_previo_min=5,
                               pausas_previas_hoy=0)
    assert riesgo > 0.7 and tranquilo < 0.2
