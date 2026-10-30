from datetime import datetime, timedelta

from sqlalchemy import func, true

from app.models import SesionFoco
from app.repositories.base import RepositorioPorUsuario


class SesionRepository(RepositorioPorUsuario[SesionFoco]):
    modelo = SesionFoco

    def minutos_completados(self, usuario_id: int) -> int:
        total = self.db.query(func.coalesce(func.sum(SesionFoco.duracion_min), 0)) \
            .filter(SesionFoco.usuario_id == usuario_id, SesionFoco.completada == true()).scalar()
        return int(total)

    def contar_entre(self, usuario_id: int, desde: datetime, hasta: datetime) -> tuple[int, int]:
        """(total, completadas) de las sesiones que iniciaron en [desde, hasta)."""
        sesiones = self._consulta(usuario_id).filter(SesionFoco.inicio >= desde, SesionFoco.inicio < hasta)
        return sesiones.count(), sesiones.filter(SesionFoco.completada == true()).count()

    def activa(self, usuario_id: int, momento: datetime) -> SesionFoco | None:
        """Sesión sin completar cuyo tiempo planeado aún no termina en `momento`."""
        for s in reversed(self.listar(usuario_id, completada=False)[-3:]):
            if s.fin is None and s.inicio <= momento < s.inicio + timedelta(minutes=s.duracion_min):
                return s
        return None
