"""
Búsqueda A*: la ruta semanal para bajar el límite diario de pantalla hasta la meta.

Estado: (semana, límite en minutos). Inicio: (0, límite actual). Meta: límite ≤ meta.
Acciones: cada semana se reduce el límite 5, 10, 15 o 20 % (redondeado a múltiplos de 5 min).

Costo de una semana = 1 + (reducción / 10 %)²
- El 1 premia terminar en menos semanas.
- El cuadrado castiga los recortes bruscos: bajar 20 % cuesta 5, dos semanas de 10 % cuestan 4.
  Es lo mismo que busca la lógica difusa del ajuste semanal: cambios graduales que sí se cumplen.

Heurística h(n) = 1.25 × (mínimo de semanas que faltan si cada semana bajara lo máximo posible).
Es admisible porque ninguna semana cuesta menos de 1.25 (la reducción mínima de 5 %) y no se
puede llegar en menos semanas, así que nunca sobreestima y A* encuentra la ruta óptima.
Para comparar se corre también búsqueda de costo uniforme (h = 0) y se cuentan nodos expandidos.
"""
import heapq
import math

REDUCCIONES = (5, 10, 15, 20)
PASO_MIN = 5
COSTO_MINIMO = 1 + (min(REDUCCIONES) / 10) ** 2
# Con el redondeo a 5 min una semana puede bajar un poco más del 20 %; 25 % es una cota segura.
FACTOR_MAXIMO = 0.75


def costo(reduccion_pct: int) -> float:
    return 1 + (reduccion_pct / 10) ** 2


def siguiente_limite(limite: int, reduccion_pct: int) -> int:
    bajada = max(PASO_MIN, round(limite * reduccion_pct / 100 / PASO_MIN) * PASO_MIN)
    return limite - bajada


def heuristica(limite: int, meta: int) -> float:
    if limite <= meta:
        return 0.0
    return COSTO_MINIMO * math.ceil(math.log(meta / limite) / math.log(FACTOR_MAXIMO))


def buscar(limite_actual: int, meta: int, max_semanas: int = 12, usar_heuristica: bool = True) -> dict | None:
    """Regresa la ruta óptima o None si no se llega a la meta en max_semanas."""
    h = (lambda lim: heuristica(lim, meta)) if usar_heuristica else (lambda lim: 0.0)
    inicio = (0, limite_actual)
    frontera = [(h(limite_actual), 0.0, inicio)]
    mejor_g = {inicio: 0.0}
    padre: dict[tuple, tuple] = {}
    expandidos = 0
    while frontera:
        _, g, estado = heapq.heappop(frontera)
        if g > mejor_g[estado]:
            continue                      # entrada vieja de la cola
        semana, limite = estado
        if limite <= meta:
            return {"ruta": _reconstruir(estado, padre, limite_actual), "costo": round(g, 2), "expandidos": expandidos}
        expandidos += 1
        if semana == max_semanas:
            continue
        for pct in REDUCCIONES:
            nuevo = siguiente_limite(limite, pct)
            if nuevo <= 0:
                continue
            hijo = (semana + 1, nuevo)
            g_hijo = g + costo(pct)
            if g_hijo < mejor_g.get(hijo, math.inf):
                mejor_g[hijo] = g_hijo
                padre[hijo] = (estado, pct)
                heapq.heappush(frontera, (g_hijo + h(nuevo), g_hijo, hijo))
    return None


def _reconstruir(estado: tuple, padre: dict, limite_actual: int) -> list[dict]:
    pasos = []
    while estado in padre:
        anterior, pct = padre[estado]
        pasos.append({"semana": estado[0], "limite_min": estado[1], "reduccion_pct": pct})
        estado = anterior
    return [{"semana": 0, "limite_min": limite_actual, "reduccion_pct": 0}] + pasos[::-1]
