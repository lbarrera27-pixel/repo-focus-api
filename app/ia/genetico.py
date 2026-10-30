"""
Algoritmo genético: ¿a qué horas y de qué tipo poner las pausas del día?

Cromosoma: 24 genes, uno por hora. Cada gen vale 0 (sin pausa), 1 (leve), 2 (media) o 3 (alta).
Hay 4^24 ≈ 2.8 × 10^14 horarios posibles, demasiados para probarlos todos.

Aptitud = minutos de pantalla que se espera ahorrar − molestia de las pausas.
- Una pausa respetada recorta un porcentaje del uso de esa hora (leve 15 %, media 30 %, alta 50 %).
- Si el usuario la ignora no ahorra nada. La probabilidad de ignorarla la da el modelo de
  ML de pausas (app/ia/modelo_pausas.py) con la hora, el tipo, los minutos acumulados y las
  pausas que ya hubo antes ese día: poner muchas pausas hace que las siguientes se ignoren más.
- Cada pausa molesta (leve 0.3, media 0.8, alta 1.5 minutos equivalentes).
- Pasarse de `max_pausas` se castiga fuerte.

Operadores: selección por torneo (3), cruce de un punto (90 %), mutación por gen (4 %)
(la mitad de las veces quita la pausa, si no pone un tipo al azar)
y elitismo (los 2 mejores pasan intactos). Se compara contra un horario "a mano":
pausas medias en las horas de más uso.
"""
import random

import numpy as np

from app.ia import modelo_pausas
from app.ia.simulador import TIPOS

REDUCCION = {"leve": 0.15, "media": 0.30, "alta": 0.50}
MOLESTIA = {"leve": 0.3, "media": 0.8, "alta": 1.5}
CASTIGO_EXCESO = 50.0


def tabla_probabilidades(categoria: str, dia_semana: int, uso_por_hora: list[float]) -> np.ndarray:
    """P[hora, tipo, pausas_previas]: se calcula una sola vez para que la aptitud sea rápida."""
    acumulado = np.cumsum(uso_por_hora)
    contextos = [
        modelo_pausas.vectorizar(categoria, tipo, hora, dia_semana, float(acumulado[hora]), previas)
        for hora in range(24) for tipo in TIPOS for previas in range(24)
    ]
    prob = modelo_pausas.modelo().clasificador.predict_proba(np.array(contextos))[:, 1]
    return prob.reshape(24, len(TIPOS), 24)


def evaluar(cromosoma: list[int], uso_por_hora: list[float], P: np.ndarray, max_pausas: int) -> float:
    aptitud, previas = 0.0, 0
    for hora, gen in enumerate(cromosoma):
        if gen == 0:
            continue
        tipo = TIPOS[gen - 1]
        aptitud += uso_por_hora[hora] * REDUCCION[tipo] * (1 - P[hora, gen - 1, previas]) - MOLESTIA[tipo]
        previas += 1
    return aptitud - CASTIGO_EXCESO * max(0, previas - max_pausas)


def horario_a_mano(uso_por_hora: list[float], max_pausas: int) -> list[int]:
    horas = sorted(range(24), key=lambda h: -uso_por_hora[h])[:max_pausas]
    return [2 if h in horas and uso_por_hora[h] > 0 else 0 for h in range(24)]


def optimizar(categoria: str, dia_semana: int, uso_por_hora: list[float], max_pausas: int = 8,
              poblacion: int = 60, generaciones: int = 150, semilla: int = 7) -> dict:
    rng = random.Random(semilla)
    P = tabla_probabilidades(categoria, dia_semana, uso_por_hora)

    def aptitud(c):
        return evaluar(c, uso_por_hora, P, max_pausas)

    def torneo(pob, apt):
        return pob[max(rng.sample(range(len(pob)), 3), key=lambda i: apt[i])]

    # Población inicial: horarios al azar con pocas pausas (cada hora 20 % de probabilidad de tener una)
    pob = [[rng.randint(1, 3) if rng.random() < 0.2 else 0 for _ in range(24)] for _ in range(poblacion)]
    pob[0] = horario_a_mano(uso_por_hora, max_pausas)
    historial = []
    for _ in range(generaciones):
        apt = [aptitud(c) for c in pob]
        orden = sorted(range(poblacion), key=lambda i: -apt[i])
        historial.append(round(apt[orden[0]], 2))
        nueva = [pob[i][:] for i in orden[:2]]                       # elitismo
        while len(nueva) < poblacion:
            a, b = torneo(pob, apt), torneo(pob, apt)
            if rng.random() < 0.9:                                    # cruce de un punto
                corte = rng.randint(1, 23)
                a, b = a[:corte] + b[corte:], b[:corte] + a[corte:]
            for hijo in (a, b):
                hijo = [_mutar(rng) if rng.random() < 0.04 else g for g in hijo]
                nueva.append(hijo)
        pob = nueva[:poblacion]

    mejor = max(pob, key=aptitud)
    a_mano = horario_a_mano(uso_por_hora, max_pausas)
    return {
        "horario": _describir(mejor, P),
        "aptitud": round(aptitud(mejor), 2),
        "minutos_ahorrados_esperados": round(_ahorro(mejor, uso_por_hora, P), 1),
        "horario_a_mano": _describir(a_mano, P),
        "aptitud_a_mano": round(aptitud(a_mano), 2),
        "minutos_ahorrados_a_mano": round(_ahorro(a_mano, uso_por_hora, P), 1),
        "mejor_aptitud_por_generacion": historial,
    }


def _mutar(rng: random.Random) -> int:
    return 0 if rng.random() < 0.5 else rng.randint(1, 3)


def _describir(cromosoma: list[int], P: np.ndarray) -> list[dict]:
    pausas, previas = [], 0
    for hora, gen in enumerate(cromosoma):
        if gen:
            pausas.append({"hora": hora, "tipo": TIPOS[gen - 1],
                           "prob_ignorar": round(float(P[hora, gen - 1, previas]), 3)})
            previas += 1
    return pausas


def _ahorro(cromosoma: list[int], uso_por_hora: list[float], P: np.ndarray) -> float:
    return sum(uso_por_hora[p["hora"]] * REDUCCION[p["tipo"]] * (1 - p["prob_ignorar"])
               for p in _describir(cromosoma, P))
