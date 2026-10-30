from typing import Literal

from pydantic import BaseModel


class FactorRiesgo(BaseModel):
    variable: str
    descripcion: str
    valor: float
    contribucion: float            # w_j * z_j: aporte al logit
    efecto: Literal["sube", "baja"]


class RiesgoSemana(BaseModel):
    semana: int
    probabilidad: float


class MetricasModelo(BaseModel):
    """Desempeño del modelo con usuarios que no vio al entrenar (ia/resultados/metricas.json)."""
    exactitud: float | None = None   # de cada 100 semanas, cuántas acierta
    auc_roc: float
    precision: float              # de cada alerta, qué fracción acierta
    recall: float


class Recomendacion(BaseModel):
    factor: str
    titulo: str
    texto: str


class Avance(BaseModel):
    actual: int
    requeridos: int


class ProgresoRiesgo(BaseModel):
    """Cuánto falta para el primer cálculo (estado "insuficiente")."""
    dias: Avance                   # días de la semana 1 que ya pasaron
    semanas: Avance                # semanas cerradas con ajuste


class RiesgoRespuesta(BaseModel):
    estado: Literal["listo", "insuficiente"] = "listo"
    plan: int
    umbral: float                  # desde aquí el modelo considera que habrá recaída
    umbral_alto: float             # desde aquí el nivel es "alto"
    metricas: MetricasModelo | None = None
    # Con estado "insuficiente" (el plan aún no tiene ajustes) solo viene progreso
    progreso: ProgresoRiesgo | None = None
    semana: int | None = None      # última semana con ajuste; se predice la siguiente
    probabilidad: float | None = None   # P(recaída la semana siguiente)
    nivel: Literal["bajo", "medio", "alto"] | None = None
    variables: dict[str, float] = {}
    factores: list[FactorRiesgo] = []   # ordenados del que más pesa al que menos
    recomendaciones: list[Recomendacion] = []   # para los 2 factores que más suben el riesgo
    historial: list[RiesgoSemana] = []   # probabilidad al cierre de cada una de las últimas 8 semanas
