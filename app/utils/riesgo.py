"""
Riesgo de recaída de Focus! (regresión logística).

Recaída: la semana siguiente el usuario vuelve a pasarse de su límite
(adherencia menor a UMBRAL_CUMPLE).

    p = sigmoide(w · z + b),   z = (x - media) / desviación

El modelo se entrena desde cero con NumPy en ia/entrenar.py y sus parámetros
se guardan en modelo_riesgo.json. Aquí solo se aplica, en Python puro, para que
la API no necesite NumPy.
"""
import json
import math
from functools import lru_cache
from pathlib import Path

RUTA_MODELO = Path(__file__).with_name("modelo_riesgo.json")

# Una semana "se cumple" si el uso no pasó más de 10 % de la meta.
UMBRAL_CUMPLE = 0.9

# Desde aquí el nivel es "alto" (si el umbral del modelo es mayor, manda el umbral).
UMBRAL_ALTO = 0.6

# Orden de las variables: el mismo en el generador, el entrenamiento y la API.
VARIABLES = [
    "adherencia",            # 0-1, de ajuste_plan
    "tendencia",             # adherencia - adherencia de la semana anterior
    "pct_ignoradas",         # pausas ignoradas / pausas mostradas
    "pct_nocturno",          # uso entre 22:00 y 06:00 / uso total
    "pct_foco_completadas",  # sesiones de foco completadas / iniciadas
    "cambio_pct",            # cambio del límite que decidió la lógica difusa
    "racha",                 # semanas seguidas cumpliendo
]

DESCRIPCION = {
    "adherencia": "Adherencia de la semana",
    "tendencia": "Tendencia de la adherencia",
    "pct_ignoradas": "Pausas ignoradas",
    "pct_nocturno": "Uso nocturno",
    "pct_foco_completadas": "Sesiones de foco completadas",
    "cambio_pct": "Recorte del límite",
    "racha": "Semanas seguidas cumpliendo",
}


# Qué hacer cuando una variable sube el riesgo (tabla fija, sin LLM)
RECOMENDACIONES = {
    "adherencia": ("Acércate a tu meta diaria", "Cumplir tu límite es lo que más baja el riesgo."),
    "tendencia": ("Recupera tu ritmo", "Tu adherencia bajó respecto a la semana pasada."),
    "pct_ignoradas": ("No saltes las pausas", "Cada pausa que respetas baja el riesgo."),
    "pct_nocturno": ("Baja el uso de noche", "Deja el teléfono fuera de la cama a partir de las 22:00."),
    "pct_foco_completadas": ("Termina tus sesiones de foco", "Cada sesión completada baja el riesgo."),
    "cambio_pct": ("Ve paso a paso", "Un recorte más suave es más fácil de cumplir."),
    "racha": ("Encadena semanas cumpliendo", "Las rachas largas bajan el riesgo."),
}


def recomendar(factores: list[dict], maximo: int = 2) -> list[dict]:
    """Consejos para los factores que más SUBEN el riesgo (vienen ordenados por peso)."""
    return [
        {"factor": f["variable"], "titulo": RECOMENDACIONES[f["variable"]][0], "texto": RECOMENDACIONES[f["variable"]][1]}
        for f in factores if f["efecto"] == "sube"
    ][:maximo]


def sigmoide(z: float) -> float:
    # Forma estable para z muy negativos (evita overflow de exp)
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


def nivel(p: float, umbral: float) -> str:
    """Debajo del umbral del modelo es "bajo"; de ahí a UMBRAL_ALTO, "medio"; arriba, "alto"."""
    if p < umbral:
        return "bajo"
    if p < max(UMBRAL_ALTO, umbral):
        return "medio"
    return "alto"


@lru_cache(maxsize=1)
def cargar_modelo() -> dict:
    return json.loads(RUTA_MODELO.read_text(encoding="utf-8"))


def predecir(x: dict[str, float], modelo: dict | None = None) -> dict:
    """Probabilidad de recaída y cuánto aporta cada variable al logit.

    La contribución de la variable j es w_j * z_j: positiva sube el riesgo,
    negativa lo baja (respecto a un usuario promedio, z = 0).
    """
    modelo = modelo or cargar_modelo()
    contribuciones = {}
    for nombre, w, media, desv in zip(VARIABLES, modelo["w"], modelo["media"], modelo["desviacion"]):
        contribuciones[nombre] = w * (x[nombre] - media) / desv
    p = sigmoide(sum(contribuciones.values()) + modelo["b"])
    factores = sorted(contribuciones.items(), key=lambda kv: abs(kv[1]), reverse=True)
    return {
        "probabilidad": round(p, 4),
        "nivel": nivel(p, modelo["umbral"]),
        "umbral": modelo["umbral"],
        "factores": [
            {
                "variable": nombre,
                "descripcion": DESCRIPCION[nombre],
                "valor": round(x[nombre], 4),
                "contribucion": round(c, 4),
                "efecto": "sube" if c > 0 else "baja",
            }
            for nombre, c in factores
        ],
    }
