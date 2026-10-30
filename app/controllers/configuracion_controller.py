"""CONFIGURACION_USUARIO: ajustes del portal web guardados como un JSON por usuario."""
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import usuario_actual
from app.models import Usuario
from app.repositories.configuracion_repository import ConfiguracionRepository
from app.schemas.configuracion import ConfiguracionDatos
from app.services.configuracion_service import ConfiguracionService

router = APIRouter(prefix="/configuracion", tags=["Configuración"])


def get_service(db: Session = Depends(get_db)) -> ConfiguracionService:
    return ConfiguracionService(ConfiguracionRepository(db))


@router.get("/me", response_model=dict[str, Any])
def obtener_configuracion(u: Usuario = Depends(usuario_actual), service: ConfiguracionService = Depends(get_service)):
    """Devuelve los ajustes guardados del usuario, o `{}` si nunca ha guardado."""
    return service.obtener(u.id)


@router.put("/me", response_model=dict[str, Any])
def reemplazar_configuracion(datos: ConfiguracionDatos, u: Usuario = Depends(usuario_actual),
                             service: ConfiguracionService = Depends(get_service)):
    """Reemplaza el JSON completo de ajustes (objeto de máximo ~20 KB)."""
    return service.reemplazar(u.id, datos.root)
