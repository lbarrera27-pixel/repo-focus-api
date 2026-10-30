from sqlalchemy import Boolean, Column, Date, Integer
from sqlalchemy.orm import relationship

from app.database import Base
from app.models._comun import DelUsuarioMixin, fk_usuario
from app.utils.reglas_plan import limite_vigente


class Plan(DelUsuarioMixin, Base):
    """Plan de reducción gradual del tiempo en pantalla."""

    __tablename__ = "plan"
    __table_args__ = (DelUsuarioMixin.restriccion_numero("plan"),)

    usuario_id = fk_usuario()
    fecha_inicio = Column(Date, nullable=False)
    limite_base = Column(Integer, nullable=False)          # minutos diarios
    semana_actual = Column(Integer, nullable=False, default=1)
    activo = Column(Boolean, nullable=False, default=True)

    ajustes = relationship(
        "AjustePlan", back_populates="plan",
        cascade="all, delete-orphan", order_by="AjustePlan.semana",
    )

    @property
    def limite_actual_min(self) -> float:
        """Límite diario de hoy: el base con todos los ajustes semanales aplicados."""
        return round(limite_vigente(self, self.ajustes), 1)
