from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.schemas.pausa import TipoPausa


class ContextoPausa(BaseModel):
    categoria: str = Field(..., max_length=60, description="Categoría de la app; las desconocidas cuentan como 'otros'",
                           examples=["redes"])
    tipo: TipoPausa = Field(..., examples=["leve"])
    hora: int = Field(..., ge=0, le=23, examples=[23])
    dia_semana: int = Field(..., ge=0, le=6, description="0 = lunes … 6 = domingo", examples=[5])
    uso_previo_min: float = Field(0, ge=0, description="Minutos que lleva hoy en esa app", examples=[45])
    pausas_previas_hoy: int = Field(0, ge=0, description="Pausas que ya recibió hoy", examples=[4])


class TipoPausaEntrada(BaseModel):
    tipo: TipoPausa = Field("media", description="Tipo que la app piensa mostrar")


class PrediccionPausa(BaseModel):
    probabilidad_ignorar: float
    ignorara: bool
    modelo: str
    probabilidad_por_tipo: dict[str, float]
    tipo_recomendado: str
    contexto: ContextoPausa


class PronosticoEntrada(BaseModel):
    ultimos_dias: list[float] = Field(..., min_length=7, description="Minutos por día, del más viejo al más nuevo; "
                                      "se usan los últimos 7", examples=[[210, 190, 230, 250, 280, 320, 300]])
    dia_semana: int = Field(..., ge=0, le=6, description="Día que se pronostica (0 = lunes)", examples=[0])


class PronosticoRespuesta(BaseModel):
    pronostico_min: float
    dia_semana: int
    ultimos_dias: list[float]
    fecha: Optional[date] = None
    limite_plan_min: Optional[int] = None
    excedera_limite: Optional[bool] = None


class OptimizarPausasEntrada(BaseModel):
    categoria: str = Field(..., max_length=60, examples=["redes"])
    dia_semana: int = Field(..., ge=0, le=6, examples=[5])
    uso_por_hora: list[float] = Field(..., min_length=24, max_length=24,
                                      description="Minutos esperados de uso en cada hora (0 a 23)",
                                      examples=[[8, 3, 0, 0, 0, 0, 2, 10, 12, 10, 8, 8, 15, 12, 8, 8, 12, 18, 22, 25,
                                                 30, 30, 25, 15]])
    max_pausas: int = Field(8, ge=1, le=24)
    semilla: int = Field(7, description="Misma semilla = mismo resultado")


class RutaPlanEntrada(BaseModel):
    limite_actual: int = Field(..., ge=10, le=1440, description="Minutos diarios de hoy", examples=[300])
    meta: int = Field(..., ge=5, description="Minutos diarios a los que se quiere llegar", examples=[120])
    max_semanas: int = Field(12, ge=1, le=52)

    @model_validator(mode="after")
    def meta_menor(self):
        if self.meta >= self.limite_actual:
            raise ValueError("La meta debe ser menor que el límite actual")
        return self
