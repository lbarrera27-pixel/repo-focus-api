"""
Red neuronal: pronóstico de los minutos de pantalla del día siguiente.

Regresión con un perceptrón multicapa (MLPRegressor de scikit-learn, 2 capas ocultas
de 32 y 16 neuronas con ReLU, optimizador Adam y paro temprano).

Entrada: los minutos de los últimos 7 días y el día de la semana que se va a pronosticar.
Como cada usuario usa el celular en una escala distinta (90 min o 400 min), los 7 días se
dividen entre su promedio y la red predice ese cociente para el día siguiente; al final se
multiplica de vuelta. Así la red aprende la forma (fin de semana, rachas) y no la escala.

Se compara contra tres líneas base sin aprendizaje:
- ayer: mañana se usará lo mismo que hoy.
- promedio_7: el promedio de la última semana.
- mismo_dia_semana_pasada: lo que se usó hace 7 días.

Ver el reporte:
    python -m app.ia.modelo_uso
"""
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from sklearn.model_selection import GroupShuffleSplit
from sklearn.neural_network import MLPRegressor

from app.ia.simulador import simular_uso_diario

VENTANA = 7


def vectorizar(ultimos: list[float], dia_semana: int) -> tuple[list[float], float]:
    """Regresa (atributos, escala). La escala es el promedio de la ventana."""
    escala = sum(ultimos) / len(ultimos)
    relativos = [m / escala for m in ultimos] if escala > 0 else [0.0] * len(ultimos)
    return relativos + [1.0 if dia_semana == d else 0.0 for d in range(7)], escala


def ejemplos(filas: list[dict]) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Ventanas deslizantes por usuario: (X, y_relativo, escala, y_minutos, usuario)."""
    por_usuario: dict[int, list[dict]] = {}
    for f in filas:
        por_usuario.setdefault(f["usuario"], []).append(f)
    X, y, escalas, reales, grupos = [], [], [], [], []
    for usuario, dias in por_usuario.items():
        minutos = [d["minutos"] for d in dias]
        for i in range(VENTANA, len(dias)):
            x, escala = vectorizar(minutos[i - VENTANA:i], dias[i]["dia_semana"])
            X.append(x)
            y.append(minutos[i] / escala)
            escalas.append(escala)
            reales.append(minutos[i])
            grupos.append(usuario)
    return np.array(X), np.array(y), np.array(escalas), np.array(reales), np.array(grupos)


def _errores(real: np.ndarray, pred: np.ndarray) -> dict:
    return {
        "mae_min": round(float(np.mean(np.abs(real - pred))), 1),
        "rmse_min": round(float(np.sqrt(np.mean((real - pred) ** 2))), 1),
        "mape_pct": round(float(np.mean(np.abs(real - pred) / real) * 100), 1),
    }


@dataclass
class ModeloUso:
    red: MLPRegressor
    reporte: dict

    def pronosticar(self, ultimos: list[float], dia_semana: int) -> float:
        x, escala = vectorizar(ultimos[-VENTANA:], dia_semana)
        if escala == 0:
            return 0.0
        return max(0.0, float(self.red.predict(np.array([x]))[0]) * escala)


def entrenar(usuarios: int = 300, dias: int = 120, semilla: int = 11) -> ModeloUso:
    X, y, escalas, reales, grupos = ejemplos(simular_uso_diario(usuarios, dias, semilla))
    corte = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=semilla)
    i_ent, i_pru = next(corte.split(X, y, grupos))

    red = MLPRegressor(hidden_layer_sizes=(32, 16), activation="relu", solver="adam", learning_rate_init=0.003,
                       max_iter=200, early_stopping=True, n_iter_no_change=10, random_state=semilla)
    red.fit(X[i_ent], y[i_ent])

    real = reales[i_pru]
    ventana = X[i_pru, :VENTANA] * escalas[i_pru, None]    # minutos de los 7 días previos
    resultados = {
        "red_neuronal": _errores(real, np.maximum(red.predict(X[i_pru]), 0) * escalas[i_pru]),
        "ayer": _errores(real, ventana[:, -1]),
        "promedio_7": _errores(real, ventana.mean(axis=1)),
        "mismo_dia_semana_pasada": _errores(real, ventana[:, 0]),
    }
    reporte = {
        "arquitectura": {"entradas": X.shape[1], "capas_ocultas": list(red.hidden_layer_sizes), "salidas": 1,
                         "activacion": "relu", "epocas": red.n_iter_},
        "ejemplos": {"entrenamiento": len(i_ent), "prueba": len(i_pru), "usuarios_prueba": len(set(grupos[i_pru]))},
        "resultados": resultados,
        # Error en validación por época (para graficar la curva de aprendizaje)
        "curva_validacion_r2": [round(float(v), 4) for v in red.validation_scores_],
    }
    return ModeloUso(red, reporte)


@lru_cache(maxsize=1)
def modelo() -> ModeloUso:
    return entrenar()


if __name__ == "__main__":
    import json

    print(json.dumps(modelo().reporte, indent=2, ensure_ascii=False))
