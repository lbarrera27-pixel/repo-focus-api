from datetime import datetime

from sqlalchemy import func

from app.models import EventoUso
from app.repositories.base import RepositorioPorUsuario


class EventoRepository(RepositorioPorUsuario[EventoUso]):
    modelo = EventoUso

    def listar_filtrado(self, usuario_id: int, app_id: int | None, franja_id: int | None,
                        desde: datetime | None, hasta: datetime | None) -> list[EventoUso]:
        consulta = self._consulta(usuario_id)
        if app_id is not None:
            consulta = consulta.filter(EventoUso.app_id == app_id)
        if franja_id is not None:
            consulta = consulta.filter(EventoUso.franja_id == franja_id)
        if desde is not None:
            consulta = consulta.filter(EventoUso.inicio >= desde)
        if hasta is not None:
            consulta = consulta.filter(EventoUso.inicio < hasta)
        return consulta.order_by(EventoUso.numero).all()

    def resumen(self, usuario_id: int, desde: datetime | None, hasta: datetime | None) -> tuple[int, int]:
        consulta = self.db.query(func.count(EventoUso.id), func.coalesce(func.sum(EventoUso.duracion_seg), 0)) \
            .filter(EventoUso.usuario_id == usuario_id)
        if desde is not None:
            consulta = consulta.filter(EventoUso.inicio >= desde)
        if hasta is not None:
            consulta = consulta.filter(EventoUso.inicio < hasta)
        total, segundos = consulta.one()
        return int(total), int(segundos)

    def aperturas_por_app(self, usuario_id: int, desde: datetime, hasta: datetime) -> dict[int, int]:
        """{app_id: eventos que iniciaron en [desde, hasta)}. Cada evento es una apertura."""
        filas = self.db.query(EventoUso.app_id, func.count(EventoUso.id)) \
            .filter(EventoUso.usuario_id == usuario_id, EventoUso.inicio >= desde, EventoUso.inicio < hasta) \
            .group_by(EventoUso.app_id).all()
        return {app_id: int(total) for app_id, total in filas}
