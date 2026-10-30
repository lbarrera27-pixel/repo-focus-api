"""Reglas de bloqueo que el teléfono aplica a cada app (el bloqueo ocurre en Android)."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import usuario_actual
from app.models import Usuario
from app.schemas.bloqueo import ReglasBloqueoRespuesta
from app.services.bloqueo_service import BloqueoService

router = APIRouter(prefix="/bloqueo", tags=["Bloqueo"])


@router.get("/reglas", response_model=ReglasBloqueoRespuesta)
def reglas(fecha: Optional[date] = None, u: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    """Qué hacer con cada app en su siguiente apertura (permitir, pausa o bloquear),
    los dominios a bloquear y cuánto queda del límite de hoy.
    `fecha` es el día local del teléfono; sin ella se usa el día actual en UTC."""
    return BloqueoService(db).reglas(u.id, fecha)
