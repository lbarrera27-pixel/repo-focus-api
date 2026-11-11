"""Esquemas de las rutas /api/v1 que consumen la app Android y el portal web."""
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

from app.schemas.metricas import PATRON_PAQUETE


# ───────────── Apps vigiladas y límites ─────────────

class LimiteApp(BaseModel):
    paquete: str = Field(..., max_length=255, pattern=PATRON_PAQUETE, examples=["com.zhiliaoapp.musically"])
    nombre: str = Field(..., min_length=1, max_length=120, examples=["TikTok"])
    categoria: Optional[str] = Field(None, max_length=60, examples=["SOCIAL"])
    limite_minutos: Optional[int] = Field(None, ge=0, le=1440, description="Minutos al día; null = sin límite de tiempo",
                                          examples=[30])
    limite_aperturas: int = Field(10, ge=0, le=500, examples=[10])
    nivel: int = Field(2, ge=1, le=3, description="Fricción: 1 = pausa de 5 s, 2 = 10 s, 3 = 20 s")
    vigilada: bool = True


class LimitesEntrada(BaseModel):
    """Lista COMPLETA de apps vigiladas del usuario (el teléfono o la web manda todo su estado).

    - Las apps de la lista se crean o actualizan (por paquete).
    - Las que ya no vienen se marcan vigilada = false (no se borran: tienen historial).
    """

    apps: list[LimiteApp] = Field(..., max_length=200)
    version_base: Optional[datetime] = Field(
        None, description="'version' que el cliente leyó en el último GET; si otro dispositivo cambió algo "
                          "después, la API responde 409 para que el cliente vuelva a leer antes de pisarlo",
    )

    @model_validator(mode="after")
    def paquetes_unicos(self):
        paquetes = [a.paquete for a in self.apps]
        if len(paquetes) != len(set(paquetes)):
            raise ValueError("un paquete aparece repetido")
        return self


class LimiteRespuesta(LimiteApp):
    numero: int


class LimitesRespuesta(BaseModel):
    version: Optional[datetime] = Field(None, description="Última modificación (para version_base)")
    apps: list[LimiteRespuesta]


# ───────────── Resumen del usuario ─────────────

class AppHoy(BaseModel):
    paquete: str
    nombre: Optional[str] = None
    minutos: int
    aperturas: int
    limite_minutos: Optional[int] = None
    en_pausa: bool = Field(..., description="Llegó a su límite de minutos o aperturas")


class DiaResumen(BaseModel):
    fecha: date
    minutos: int
    cumple: Optional[bool] = Field(None, description="Dentro de la meta diaria; null si no hay meta")


class RiesgoResumen(BaseModel):
    nivel: Literal["bajo", "medio", "alto"]
    probabilidad: float
    semana: int


class SemanaPlan(BaseModel):
    semana: int
    uso_meta: float = Field(..., description="Límite diario de esa semana (minutos)")
    adherencia: float
    cambio_pct: float = Field(..., description="Cambio que las reglas difusas aplicaron al límite siguiente")


class PlanResumen(BaseModel):
    fecha_inicio: date
    semana_actual: int
    limite_actual: float = Field(..., description="Límite diario vigente (minutos), ya con los ajustes")
    semanas: list[SemanaPlan]


class ResumenRespuesta(BaseModel):
    fecha: date = Field(..., description="Día de FOCUS! consultado (empieza a las 06:00 hora local)")
    meta_diaria_minutos: Optional[int] = Field(None, description="Límite base del plan activo")
    minutos_hoy: int
    aperturas_hoy: int
    apps_hoy: list[AppHoy]
    apps_en_pausa: list[str]
    semana: list[DiaResumen] = Field(..., description="Los 7 días que terminan en 'fecha' (con o sin datos)")
    dias_con_datos: int
    racha_dias: int = Field(..., description="Días seguidos con datos dentro de la meta, hasta 'fecha'")
    pausas_respetadas: int
    pausas_ignoradas: int
    riesgo: Optional[RiesgoResumen] = Field(None, description="null mientras el modelo no tenga datos")
    riesgo_motivo: Optional[str] = Field(None, description="Por qué no hay riesgo todavía")
    semana_anterior_minutos: int = Field(0, description="Minutos de los 7 días anteriores a 'semana' (para comparar)")
    plan: Optional[PlanResumen] = None


# ───────────── Sesiones de uso (para el portal web) ─────────────

class SesionUso(BaseModel):
    paquete: str = Field(..., max_length=255, pattern=PATRON_PAQUETE, examples=["com.instagram.android"])
    inicio: datetime = Field(..., description="Hora local del teléfono", examples=["2026-11-09T19:05:00"])
    fin: datetime = Field(..., examples=["2026-11-09T19:32:00"])

    @model_validator(mode="after")
    def rango(self):
        if self.fin <= self.inicio:
            raise ValueError("fin debe ser posterior a inicio")
        if (self.fin - self.inicio).total_seconds() > 24 * 3600:
            raise ValueError("una sesión no puede durar más de un día")
        return self


class LoteSesiones(BaseModel):
    """Sesiones en primer plano de las apps vigiladas (las demás se ignoran)."""

    sesiones: list[SesionUso] = Field(..., max_length=5000)


class ResultadoSesiones(BaseModel):
    insertadas: int
    omitidas: int = Field(..., description="Ya existían o son de apps que el usuario no vigila")
