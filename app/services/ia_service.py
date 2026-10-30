"""
Conecta los modelos de app/ia/ con los datos del usuario en la BD.

La app Android solo dice qué app y qué tipo de pausa; el contexto (categoría, minutos de hoy,
pausas previas, últimos 7 días) se arma aquí con las tablas APP, EVENTO_USO, PAUSA y PLAN.
"""
from datetime import datetime, time, timedelta

from app.config import UTC_OFFSET_HORAS
from app.ia import modelo_pausas, modelo_uso
from app.ia.simulador import TIPOS
from app.models._comun import ahora
from app.repositories.app_repository import AppRepository
from app.repositories.evento_repository import EventoRepository
from app.repositories.pausa_repository import PausaRepository
from app.repositories.plan_repository import PlanRepository
from app.utils.errores import NoEncontrado

OFFSET = timedelta(hours=UTC_OFFSET_HORAS)


def predecir_pausa(contexto: dict) -> dict:
    m = modelo_pausas.modelo()
    probabilidad = m.probabilidad(**contexto)
    por_tipo = {t: round(m.probabilidad(**{**contexto, "tipo": t}), 3) for t in TIPOS}
    return {
        "probabilidad_ignorar": round(probabilidad, 3),
        "ignorara": probabilidad >= modelo_pausas.UMBRAL,
        "modelo": m.nombre,
        "probabilidad_por_tipo": por_tipo,
        "tipo_recomendado": min(por_tipo, key=por_tipo.get),
        "contexto": contexto,
    }


def pronosticar(ultimos_dias: list[float], dia_semana: int) -> float:
    return round(modelo_uso.modelo().pronosticar(ultimos_dias, dia_semana), 1)


class IAService:
    def __init__(self, db):
        self.apps = AppRepository(db)
        self.eventos = EventoRepository(db)
        self.pausas = PausaRepository(db)
        self.planes = PlanRepository(db)

    @staticmethod
    def _hoy_local() -> tuple[datetime, datetime]:
        """(hora local actual, medianoche local de hoy expresada en UTC como la guarda la BD)."""
        local = ahora() + OFFSET
        return local, datetime.combine(local.date(), time.min) - OFFSET

    def prob_ignorar(self, usuario_id: int, app_numero: int, tipo: str) -> dict:
        app = self.apps.obtener(usuario_id, app_numero)
        if app is None:
            raise NoEncontrado(f"No existe la app {app_numero} para este usuario")
        local, medianoche = self._hoy_local()
        _, segundos = self.eventos.resumen(usuario_id, medianoche, None, app_id=app.id)
        pausas_hoy, _ = self.pausas.contar_entre(usuario_id, medianoche, ahora() + timedelta(seconds=1))
        return predecir_pausa({
            "categoria": app.categoria or "otros",
            "tipo": tipo,
            "hora": local.hour,
            "dia_semana": local.weekday(),
            "uso_previo_min": round(segundos / 60, 1),
            "pausas_previas_hoy": pausas_hoy,
        })

    def pronostico_hoy(self, usuario_id: int) -> dict:
        """Pronóstico de hoy con los 7 días completos anteriores (de EVENTO_USO)."""
        local, medianoche = self._hoy_local()
        ultimos = []
        for d in range(modelo_uso.VENTANA, 0, -1):
            desde = medianoche - timedelta(days=d)
            _, segundos = self.eventos.resumen(usuario_id, desde, desde + timedelta(days=1))
            ultimos.append(round(segundos / 60, 1))
        plan = self.planes.activo(usuario_id)
        pronostico = pronosticar(ultimos, local.weekday())
        return {
            "fecha": local.date(),
            "dia_semana": local.weekday(),
            "ultimos_dias": ultimos,
            "pronostico_min": pronostico,
            "limite_plan_min": plan.limite_base if plan else None,
            "excedera_limite": pronostico > plan.limite_base if plan else None,
        }
