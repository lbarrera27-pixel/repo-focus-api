from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel


class ReglaApp(BaseModel):
    numero: int
    nombre: str
    paquete: str
    aperturas_hoy: int
    limite_aperturas: int
    accion: Literal["permitir", "pausa", "bloquear"]   # para la siguiente apertura
    nivel: Optional[Literal["leve", "media", "alta"]] = None
    duracion_seg: int


class ReglasBloqueoRespuesta(BaseModel):
    fecha: date
    generado: datetime                     # UTC; la app las guarda y las usa sin conexión
    limite_hoy_min: Optional[float] = None  # None si no hay plan activo
    usado_hoy_min: float
    restante_min: Optional[float] = None
    limite_excedido: bool
    sesion_foco_activa: bool
    sesion_foco_hasta: Optional[datetime] = None
    dominios: list[str]
    apps: list[ReglaApp]
