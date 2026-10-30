from datetime import date
from typing import Optional

from pydantic import BaseModel


class UsoApp(BaseModel):
    app_numero: int
    nombre: str
    paquete: str
    categoria: str
    min: float
    variacion_pct: Optional[float] = None   # contra el mismo número de días justo antes


class UsoPorAppRespuesta(BaseModel):
    desde: date
    hasta: date
    total_min: float
    apps: list[UsoApp]                      # de la más usada a la menos usada


class UsoCategoria(BaseModel):
    categoria: str
    min: float
    pct: float


class UsoPorCategoriaRespuesta(BaseModel):
    desde: date
    hasta: date
    total_min: float
    categorias: list[UsoCategoria]


class UsoDia(BaseModel):
    fecha: date
    uso_min: float
    con_datos: bool                         # el teléfono mandó al menos un evento ese día
    limite_min: Optional[float] = None      # límite del plan que regía ese día
    cumplio: Optional[bool] = None          # None si no hay plan o el día aún no llega


class UsoDiarioRespuesta(BaseModel):
    desde: date
    hasta: date
    dias: list[UsoDia]
    promedio_min: float                     # solo entre los días con datos
    dias_con_datos: int
    dias_cumplidos: int


class CeldaPico(BaseModel):
    dia: str
    hora: int
    min: float


class HeatmapRespuesta(BaseModel):
    desde: date
    hasta: date
    dias: list[str]                         # lun ... dom
    horas: list[int]                        # 0 ... 23 (UTC)
    celdas: list[list[float]]               # minutos [día][hora]
    max_min: float
    pico: Optional[CeldaPico] = None
    top: list[CeldaPico]                    # las 3 horas con más uso
