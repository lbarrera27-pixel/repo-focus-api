"""
Aprendizaje supervisado: ¿el usuario va a ignorar esta pausa?

Problema de clasificación binaria. Cada ejemplo es una pausa con su contexto y la
etiqueta `ignorada`, la misma columna que guarda la tabla PAUSA.

Atributos (todos se pueden sacar de las tablas PAUSA, APP y EVENTO_USO):
- categoria de la app (one-hot), tipo de pausa (one-hot)
- hora del día (cruda para el árbol; seno y coseno para que la regresión vea que 23 h y 0 h están juntas)
- fin_de_semana, uso_previo_min (minutos en la app ese día), pausas_previas_hoy

Se comparan dos modelos de scikit-learn:
- Regresión logística (lineal, sus coeficientes se interpretan como factores de riesgo).
- Árbol de decisión (no lineal, capta la "joroba" de la noche sin que se la digan).

La partición entrenamiento/prueba es por usuario (75 % / 25 %): los usuarios de prueba
nunca se vieron al entrenar, igual que pasará con un usuario nuevo de la app.
Se sirve el modelo con mejor AUC en prueba.

Ver el reporte completo:
    python -m app.ia.modelo_pausas
"""
import math
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from app.ia.simulador import CATEGORIAS, TIPOS, simular

ATRIBUTOS = (
    [f"categoria_{c}" for c in CATEGORIAS]
    + [f"tipo_{t}" for t in TIPOS]
    + ["hora", "hora_sen", "hora_cos", "fin_de_semana", "uso_previo_min", "pausas_previas_hoy"]
)
UMBRAL = 0.5
USO_MAXIMO = 120      # el simulador deja de sumar efecto después de 120 min y 12 pausas
PAUSAS_MAXIMAS = 12


def vectorizar(categoria: str, tipo: str, hora: int, dia_semana: int,
               uso_previo_min: float, pausas_previas_hoy: int) -> list[float]:
    categoria = categoria if categoria in CATEGORIAS else "otros"
    # Fuera del rango de entrenamiento la regresión extrapolaría sin límite
    uso_previo_min = min(uso_previo_min, USO_MAXIMO)
    pausas_previas_hoy = min(pausas_previas_hoy, PAUSAS_MAXIMAS)
    angulo = 2 * math.pi * hora / 24
    return (
        [1.0 if categoria == c else 0.0 for c in CATEGORIAS]
        + [1.0 if tipo == t else 0.0 for t in TIPOS]
        + [float(hora), math.sin(angulo), math.cos(angulo), 1.0 if dia_semana >= 5 else 0.0,
           float(uso_previo_min), float(pausas_previas_hoy)]
    )


def matriz(filas: list[dict]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    X = np.array([vectorizar(f["categoria"], f["tipo"], f["hora"], f["dia_semana"],
                             f["uso_previo_min"], f["pausas_previas_hoy"]) for f in filas])
    y = np.array([f["ignorada"] for f in filas], dtype=int)
    grupos = np.array([f["usuario"] for f in filas])
    return X, y, grupos


def metricas(y_real: np.ndarray, prob: np.ndarray) -> dict:
    pred = (prob >= UMBRAL).astype(int)
    (vn, fp), (fn, vp) = confusion_matrix(y_real, pred, labels=[0, 1])
    return {
        "exactitud": round(accuracy_score(y_real, pred), 3),
        "precision": round(precision_score(y_real, pred, zero_division=0), 3),
        "sensibilidad": round(recall_score(y_real, pred, zero_division=0), 3),
        "f1": round(f1_score(y_real, pred, zero_division=0), 3),
        "auc": round(roc_auc_score(y_real, prob), 3),
        "matriz_confusion": {"verdaderos_negativos": int(vn), "falsos_positivos": int(fp),
                             "falsos_negativos": int(fn), "verdaderos_positivos": int(vp)},
    }


@dataclass
class ModeloPausas:
    nombre: str
    clasificador: object
    reporte: dict

    def probabilidad(self, **contexto) -> float:
        x = np.array([vectorizar(**contexto)])
        return float(self.clasificador.predict_proba(x)[0, 1])


def entrenar(usuarios: int = 200, dias: int = 28, semilla: int = 7) -> ModeloPausas:
    X, y, grupos = matriz(simular(usuarios, dias, semilla))
    corte = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=semilla)
    i_ent, i_pru = next(corte.split(X, y, grupos))

    candidatos = {
        "regresion_logistica": make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)),
        "arbol_decision": DecisionTreeClassifier(max_depth=6, min_samples_leaf=50, random_state=semilla),
    }
    resultados = {}
    for nombre, modelo in candidatos.items():
        modelo.fit(X[i_ent], y[i_ent])
        resultados[nombre] = metricas(y[i_pru], modelo.predict_proba(X[i_pru])[:, 1])

    # Línea base: siempre predecir la clase más frecuente del entrenamiento
    mayoritaria = int(y[i_ent].mean() >= 0.5)
    resultados["linea_base"] = {"exactitud": round(float((y[i_pru] == mayoritaria).mean()), 3)}

    logistica = candidatos["regresion_logistica"][-1]
    arbol = candidatos["arbol_decision"]
    elegido = max(("regresion_logistica", "arbol_decision"), key=lambda n: resultados[n]["auc"])
    reporte = {
        "modelo_elegido": elegido,
        "ejemplos": {"entrenamiento": len(i_ent), "prueba": len(i_pru),
                     "usuarios_prueba": len(set(grupos[i_pru])), "pct_ignoradas": round(float(y.mean()), 3)},
        "resultados": resultados,
        # Coeficientes sobre atributos estandarizados: positivo = sube la probabilidad de ignorar
        "coeficientes_logistica": _ordenar(dict(zip(ATRIBUTOS, logistica.coef_[0]))),
        "importancia_arbol": _ordenar(dict(zip(ATRIBUTOS, arbol.feature_importances_))),
    }
    return ModeloPausas(elegido, candidatos[elegido], reporte)


def _ordenar(valores: dict) -> dict:
    return {k: round(float(v), 3) for k, v in sorted(valores.items(), key=lambda kv: -abs(kv[1]))}


@lru_cache(maxsize=1)
def modelo() -> ModeloPausas:
    """Se entrena una sola vez por proceso (tarda un par de segundos) y se reutiliza."""
    return entrenar()


if __name__ == "__main__":
    import json

    print(json.dumps(modelo().reporte, indent=2, ensure_ascii=False))
