"""
Riesgo de recaída del usuario (pieza 2 de la IA).

Toma la última semana con ajuste del plan activo, calcula las mismas 7 variables
con las que se entrenó el modelo (app/utils/riesgo.py) y devuelve la probabilidad
de que la semana siguiente se pase de su límite.
"""
from app.repositories.ajuste_repository import AjusteRepository
from app.repositories.evento_repository import EventoRepository
from app.repositories.pausa_repository import PausaRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.sesion_repository import SesionRepository
from app.services.plan_service import rango_semana
from app.utils.errores import NoEncontrado
from app.models._comun import ahora
from app.utils.riesgo import UMBRAL_ALTO, UMBRAL_CUMPLE, cargar_modelo, predecir, recomendar

HORA_NOCHE, HORA_MANANA = 22, 6   # uso nocturno: de 22:00 a 05:59
SEMANAS_HISTORIAL = 8


def _proporcion(parte: float, total: float) -> float:
    return parte / total if total else 0.0


class RiesgoService:
    def __init__(self, db):
        self.planes = PlanRepository(db)
        self.ajustes = AjusteRepository(db)
        self.pausas = PausaRepository(db)
        self.sesiones = SesionRepository(db)
        self.eventos = EventoRepository(db)

    def variables(self, plan, ajustes) -> dict[str, float]:
        actual = ajustes[-1]
        desde, hasta = rango_semana(plan, actual.semana)
        pausas, ignoradas = self.pausas.contar_entre(plan.usuario_id, desde, hasta)
        sesiones, completadas = self.sesiones.contar_entre(plan.usuario_id, desde, hasta)
        eventos = self.eventos.listar_filtrado(plan.usuario_id, None, None, desde, hasta)
        nocturno = sum(e.duracion_seg for e in eventos
                       if e.inicio.hour >= HORA_NOCHE or e.inicio.hour < HORA_MANANA)
        racha = 0
        for ajuste in reversed(ajustes):
            if ajuste.adherencia < UMBRAL_CUMPLE:
                break
            racha += 1
        return {
            "adherencia": actual.adherencia,
            "tendencia": actual.adherencia - ajustes[-2].adherencia if len(ajustes) > 1 else 0.0,
            "pct_ignoradas": _proporcion(ignoradas, pausas),
            "pct_nocturno": _proporcion(nocturno, sum(e.duracion_seg for e in eventos)),
            "pct_foco_completadas": _proporcion(completadas, sesiones),
            "cambio_pct": actual.cambio_pct,
            "racha": float(racha),
        }

    def calcular(self, usuario_id: int) -> dict:
        plan = self.planes.activo(usuario_id)
        if plan is None:
            raise NoEncontrado("El usuario no tiene un plan activo")
        ajustes = self.ajustes.listar(plan)
        modelo = cargar_modelo()
        base = {"plan": plan.numero, "umbral": modelo["umbral"], "umbral_alto": max(UMBRAL_ALTO, modelo["umbral"]),
                "metricas": modelo.get("prueba")}
        if not ajustes:
            # Aún no cierra su primera semana: 200 con el avance, no 404 (la pantalla muestra cuánto falta)
            dias = min(7, max(0, (ahora().date() - plan.fecha_inicio).days))
            return {**base, "estado": "insuficiente",
                    "progreso": {"dias": {"actual": dias, "requeridos": 7}, "semanas": {"actual": 0, "requeridos": 1}}}
        variables = self.variables(plan, ajustes)
        # Riesgo que se habría estimado al cierre de cada una de las últimas semanas
        historial = [
            {"semana": ajustes[k - 1].semana,
             "probabilidad": predecir(self.variables(plan, ajustes[:k]))["probabilidad"]}
            for k in range(max(1, len(ajustes) - SEMANAS_HISTORIAL + 1), len(ajustes) + 1)
        ]
        prediccion = predecir(variables)
        return {**base, **prediccion, "estado": "listo", "semana": ajustes[-1].semana, "variables": variables,
                "recomendaciones": recomendar(prediccion["factores"]), "historial": historial}
