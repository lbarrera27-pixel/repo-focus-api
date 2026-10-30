"""
Simulador de usuarios de Focus! para generar pausas con etiqueta (ignorada o no).

Todavía no hay usuarios reales con semanas de historial, así que el modelo se entrena
con datos sintéticos. Cada usuario simulado tiene un rasgo oculto de disciplina y un
conjunto de apps; cada día recibe varias pausas y la probabilidad de ignorar cada una
sale de un modelo logístico con estos supuestos:

- Redes, video y juegos enganchan más que mensajería o productividad.
- Una pausa leve (10 s) se ignora más fácil que una media (30 s) o alta (60 s).
- De noche (22:00 a 01:59) se ignoran más; temprano (6:00 a 8:59) menos.
- El fin de semana se ignoran un poco más.
- Entre más minutos lleva en la app y más pausas ha recibido ese día, más las ignora (fatiga).

El modelo de ML no conoce estos supuestos ni la disciplina: tiene que descubrirlos
a partir de los ejemplos, y la disciplina queda como ruido que no puede explicar.

Generar un CSV para revisarlo en Excel:
    python -m app.ia.simulador --usuarios 200 --dias 28 --salida pausas_simuladas.csv
"""
import argparse
import csv
import math
from datetime import date, datetime, timedelta

import numpy as np

CATEGORIAS = ["redes", "video", "juegos", "mensajeria", "productividad", "otros"]
TIPOS = ["leve", "media", "alta"]
DURACION_TIPO = {"leve": 10, "media": 30, "alta": 60}

# Efectos "reales" en escala logit (log-momios). Solo los usa el simulador.
EFECTO_CATEGORIA = {"redes": 0.8, "video": 0.6, "juegos": 0.7, "mensajeria": 0.0, "productividad": -0.9, "otros": -0.2}
EFECTO_TIPO = {"leve": 0.5, "media": 0.0, "alta": -0.7}
INTERCEPTO = -2.2

PESO_CATEGORIA = [0.30, 0.20, 0.12, 0.20, 0.10, 0.08]
PESO_TIPO = [0.50, 0.35, 0.15]
# Uso del celular por hora del día (más en la tarde y la noche)
PESO_HORA = np.array([2, 1, 0.5, 0.2, 0.2, 0.3, 1, 2, 3, 3, 3, 3, 4, 4, 3, 3, 4, 5, 5, 6, 6, 6, 5, 4], dtype=float)
PESO_HORA /= PESO_HORA.sum()


def efecto_hora(hora: int) -> float:
    if hora >= 22 or hora < 2:
        return 0.9
    if 6 <= hora < 9:
        return -0.4
    return 0.0


def probabilidad_ignorar(categoria: str, tipo: str, hora: int, dia_semana: int,
                         uso_previo_min: float, pausas_previas_hoy: int, disciplina: float = 0.0) -> float:
    z = (INTERCEPTO + EFECTO_CATEGORIA[categoria] + EFECTO_TIPO[tipo] + efecto_hora(hora)
         + (0.3 if dia_semana >= 5 else 0.0)
         + 0.02 * min(uso_previo_min, 120)
         + 0.12 * min(pausas_previas_hoy, 12)
         - disciplina)
    return 1 / (1 + math.exp(-z))


def simular(usuarios: int = 200, dias: int = 28, semilla: int = 7, inicio: date = date(2026, 9, 7)) -> list[dict]:
    """Regresa una lista de pausas simuladas (un dict por pausa), ordenadas por usuario y fecha."""
    rng = np.random.default_rng(semilla)
    filas = []
    for usuario in range(1, usuarios + 1):
        disciplina = rng.normal(0, 0.8)
        n_apps = int(rng.integers(3, 7))
        apps = list(rng.choice(CATEGORIAS, size=n_apps, p=PESO_CATEGORIA))
        for d in range(dias):
            fecha = inicio + timedelta(days=d)
            dia_semana = fecha.weekday()
            n_pausas = int(rng.poisson(8 if dia_semana >= 5 else 6))
            horas = np.sort(rng.choice(24, size=n_pausas, p=PESO_HORA))
            uso_por_app: dict[str, float] = {}
            for previas, hora in enumerate(horas):
                hora = int(hora)
                categoria = str(rng.choice(apps))
                tipo = str(rng.choice(TIPOS, p=PESO_TIPO))
                # Minutos que lleva hoy en esa categoría antes de la pausa
                uso_por_app[categoria] = uso_por_app.get(categoria, 0.0) + float(rng.gamma(2.0, 8.0))
                uso_previo = round(uso_por_app[categoria], 1)
                p = probabilidad_ignorar(categoria, tipo, hora, dia_semana, uso_previo, previas, disciplina)
                filas.append({
                    "usuario": usuario,
                    "fecha": datetime.combine(fecha, datetime.min.time()) + timedelta(hours=hora, minutes=int(rng.integers(60))),
                    "categoria": categoria,
                    "tipo": tipo,
                    "duracion_seg": DURACION_TIPO[tipo],
                    "hora": hora,
                    "dia_semana": dia_semana,
                    "uso_previo_min": uso_previo,
                    "pausas_previas_hoy": previas,
                    "ignorada": bool(rng.random() < p),
                })
    return filas


# Uso relativo por día de la semana (lunes … domingo): el fin de semana se usa más el celular
PATRON_SEMANA = [1.0, 0.95, 0.95, 1.0, 1.1, 1.3, 1.25]


def simular_uso_diario(usuarios: int = 300, dias: int = 120, semilla: int = 11,
                       inicio: date = date(2026, 6, 1)) -> list[dict]:
    """Minutos de pantalla por día de cada usuario simulado (para la red neuronal).

    minutos = base del usuario × patrón del día × tendencia × e^(choque), donde el choque
    sigue un proceso AR(1): un día de mucho uso suele seguir de otro día de mucho uso.
    La tendencia baja poco a poco (el usuario ya usa Focus!).
    """
    rng = np.random.default_rng(semilla)
    filas = []
    for usuario in range(1, usuarios + 1):
        base = rng.uniform(120, 360)
        peso_finde = rng.uniform(0.5, 1.5)      # a unos les cambia más el fin de semana que a otros
        baja_diaria = rng.uniform(0.0, 0.004)
        choque = 0.0
        for d in range(dias):
            fecha = inicio + timedelta(days=d)
            patron = 1 + (PATRON_SEMANA[fecha.weekday()] - 1) * peso_finde
            choque = 0.6 * choque + rng.normal(0, 0.15)
            minutos = base * patron * (1 - baja_diaria) ** d * math.exp(choque)
            filas.append({"usuario": usuario, "fecha": fecha, "dia_semana": fecha.weekday(),
                          "minutos": round(minutos, 1)})
    return filas


def guardar_csv(filas: list[dict], ruta: str) -> None:
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=list(filas[0]))
        escritor.writeheader()
        escritor.writerows(filas)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Genera pausas simuladas de Focus!")
    parser.add_argument("--usuarios", type=int, default=200)
    parser.add_argument("--dias", type=int, default=28)
    parser.add_argument("--semilla", type=int, default=7)
    parser.add_argument("--salida", default="pausas_simuladas.csv")
    args = parser.parse_args()
    datos = simular(args.usuarios, args.dias, args.semilla)
    guardar_csv(datos, args.salida)
    ignoradas = sum(f["ignorada"] for f in datos)
    print(f"{len(datos)} pausas de {args.usuarios} usuarios en {args.dias} días -> {args.salida}")
    print(f"Ignoradas: {ignoradas} ({ignoradas / len(datos):.1%})")
