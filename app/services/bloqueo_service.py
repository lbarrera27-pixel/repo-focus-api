"""
Reglas de bloqueo del día para el teléfono.

La API no bloquea nada: junta el plan, el uso de hoy, la sesión de foco y los dominios,
y le dice al teléfono qué hacer con cada app. El teléfono las guarda y decide sin conexión.
"""
from datetime import date, datetime, time, timedelta

from app.models._comun import ahora
from app.repositories.ajuste_repository import AjusteRepository
from app.repositories.app_repository import AppRepository
from app.repositories.dominio_repository import DominioRepository
from app.repositories.evento_repository import EventoRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.sesion_repository import SesionRepository
from app.services.plan_service import limite_vigente
from app.utils.reglas_bloqueo import accion_app


class BloqueoService:
    def __init__(self, db):
        self.apps = AppRepository(db)
        self.eventos = EventoRepository(db)
        self.planes = PlanRepository(db)
        self.ajustes = AjusteRepository(db)
        self.sesiones = SesionRepository(db)
        self.dominios = DominioRepository(db)

    def reglas(self, usuario_id: int, fecha: date | None) -> dict:
        momento = ahora()
        fecha = fecha or momento.date()
        desde = datetime.combine(fecha, time.min)
        hasta = desde + timedelta(days=1)

        _, segundos = self.eventos.resumen(usuario_id, desde, hasta)
        usado = round(segundos / 60, 1)
        plan = self.planes.activo(usuario_id)
        limite = round(limite_vigente(plan, self.ajustes.listar(plan)), 1) if plan else None
        excedido = limite is not None and usado >= limite
        sesion = self.sesiones.activa(usuario_id, momento)

        aperturas = self.eventos.aperturas_por_app(usuario_id, desde, hasta)
        apps = []
        for app in self.apps.listar(usuario_id):
            hoy = aperturas.get(app.id, 0)
            apps.append({
                "numero": app.numero, "nombre": app.nombre, "paquete": app.paquete,
                "aperturas_hoy": hoy, "limite_aperturas": app.limite_aperturas,
                **accion_app(hoy, app.limite_aperturas, excedido or sesion is not None),
            })
        return {
            "fecha": fecha,
            "generado": momento,
            "limite_hoy_min": limite,
            "usado_hoy_min": usado,
            "restante_min": max(round(limite - usado, 1), 0.0) if limite is not None else None,
            "limite_excedido": excedido,
            "sesion_foco_activa": sesion is not None,
            "sesion_foco_hasta": sesion.inicio + timedelta(minutes=sesion.duracion_min) if sesion else None,
            "dominios": [d.dominio for d in self.dominios.listar(usuario_id, activo=True)],
            "apps": apps,
        }
