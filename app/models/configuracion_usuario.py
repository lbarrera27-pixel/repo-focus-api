from sqlalchemy import Column, DateTime, ForeignKey, Integer, UnicodeText

from app.database import Base
from app.models._comun import ahora


class ConfiguracionUsuario(Base):
    """Preferencias del portal web de un usuario, guardadas como un JSON libre (una fila por usuario)."""

    __tablename__ = "configuracion_usuario"

    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=False, unique=True, index=True)
    datos = Column(UnicodeText, nullable=False, default="{}")   # JSON serializado
    actualizado = Column(DateTime, nullable=False, default=ahora, onupdate=ahora)
