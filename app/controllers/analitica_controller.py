"""Analítica de uso para las gráficas del portal. Sin fechas: los últimos 7 días contando hoy."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import usuario_actual
from app.models import Usuario
from app.schemas.analitica import (
    HeatmapRespuesta, UsoDiarioRespuesta, UsoPorAppRespuesta, UsoPorCategoriaRespuesta,
)
from app.services.analitica_service import AnaliticaService

router = APIRouter(prefix="/analitica", tags=["Analítica"])


def get_service(db: Session = Depends(get_db)) -> AnaliticaService:
    return AnaliticaService(db)


@router.get("/uso-por-app", response_model=UsoPorAppRespuesta)
def uso_por_app(desde: Optional[date] = None, hasta: Optional[date] = None,
                limite: Optional[int] = Query(None, ge=1, le=100, description="Solo las N apps más usadas"),
                u: Usuario = Depends(usuario_actual), service: AnaliticaService = Depends(get_service)):
    """Minutos por app y su variación contra el periodo anterior de la misma duración."""
    return service.uso_por_app(u.id, desde, hasta, limite)


@router.get("/uso-por-categoria", response_model=UsoPorCategoriaRespuesta)
def uso_por_categoria(desde: Optional[date] = None, hasta: Optional[date] = None,
                      u: Usuario = Depends(usuario_actual), service: AnaliticaService = Depends(get_service)):
    return service.uso_por_categoria(u.id, desde, hasta)


@router.get("/uso-diario", response_model=UsoDiarioRespuesta)
def uso_diario(desde: Optional[date] = None, hasta: Optional[date] = None,
               u: Usuario = Depends(usuario_actual), service: AnaliticaService = Depends(get_service)):
    """Uso de cada día contra el límite del plan que regía ese día."""
    return service.uso_diario(u.id, desde, hasta)


@router.get("/heatmap", response_model=HeatmapRespuesta)
def heatmap(desde: Optional[date] = None, hasta: Optional[date] = None,
            u: Usuario = Depends(usuario_actual), service: AnaliticaService = Depends(get_service)):
    """Minutos por día de la semana × hora. Los eventos que cruzan de hora se reparten."""
    return service.heatmap(u.id, desde, hasta)
