from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.schemas._comun import Respuesta


class PlanCrear(BaseModel):
    fecha_inicio: date = Field(..., examples=["2026-10-19"])
    limite_base: int = Field(..., gt=0, description="Minutos diarios de pantalla", examples=[240])


class PlanActualizar(BaseModel):
    limite_base: Optional[int] = Field(None, gt=0)
    semana_actual: Optional[int] = Field(None, ge=1)
    activo: Optional[bool] = None


class PlanRespuesta(Respuesta):
    numero: int
    fecha_inicio: date
    limite_base: int
    limite_actual_min: float       # limite_base con todos los ajustes aplicados
    semana_actual: int
    activo: bool


# ---------- lógica difusa del plan ----------
class ReglaExplicada(BaseModel):
    si_adherencia: str
    y_ignoradas: Optional[str] = None      # None = cualquier valor
    entonces: str
    salida_pct: float                      # centro del conjunto de salida
    fuerza: float                          # 0 a 1: qué tanto se activó la regla


class SalidaDifusa(BaseModel):
    centroide_pct: float
    nivel_adherencia: str
    conjunto_agregado: list[tuple[float, float]]   # (cambio %, membresía) para graficar


class LimiteAntesDespues(BaseModel):
    antes_min: float
    despues_min: float


class ExplicacionAjuste(BaseModel):
    semana: int
    entradas: dict[str, float]
    membresias: dict[str, dict[str, float]]
    reglas: list[ReglaExplicada]
    salida: SalidaDifusa
    cambio_aplicado_pct: float
    manual: bool                           # el cambio guardado no es el que da la lógica difusa
    limite: LimiteAntesDespues


Perfil = Literal["suave", "normal", "estricta"]


class SimulacionEntrada(BaseModel):
    perfiles: list[Perfil] = Field(["suave", "normal", "estricta"], min_length=1)
    semanas: int = Field(4, ge=1, le=12)
    adherencia: Optional[float] = Field(None, ge=0, le=1, description="Si no se envía, la del último ajuste")
    pct_ignoradas: Optional[float] = Field(None, ge=0, le=1, description="Si no se envía, la de la última semana")
    meta_min: Optional[float] = Field(None, gt=0, description="Minutos diarios meta, para calcular semana_meta")


class Supuesto(BaseModel):
    adherencia: float
    pct_ignoradas: float
    origen: Literal["ultimo_ajuste", "por_defecto"]


class SemanaSimulada(BaseModel):
    semana: int
    cambio_pct: float
    limite_min: float


class PerfilSimulado(BaseModel):
    perfil: Perfil
    semanas: list[SemanaSimulada]
    semana_meta: Optional[int] = None      # primera semana con el límite en la meta o abajo


class SimulacionRespuesta(BaseModel):
    supuesto: Supuesto
    limite_actual_min: float
    perfiles: list[PerfilSimulado]


class ProyeccionRespuesta(BaseModel):
    semana: int                            # semana que se cerrará con el próximo ajuste
    proximo_ajuste: date
    limite_actual_min: float
    cambio_pct: float
    limite_proyectado_min: float
    supuesto: Supuesto
