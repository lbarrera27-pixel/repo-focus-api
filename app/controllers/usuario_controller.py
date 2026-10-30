from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import usuario_actual
from app.models import Usuario
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.usuario import FotoUrlEntrada, UsuarioActualizar, UsuarioRespuesta
from app.services.usuario_service import UsuarioService
from app.utils.blob_storage import TAMANO_MAXIMO, TIPOS_PERMITIDOS, AlmacenamientoNoConfigurado

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


def get_service(db: Session = Depends(get_db)) -> UsuarioService:
    return UsuarioService(UsuarioRepository(db))


@router.get("/me", response_model=UsuarioRespuesta)
def obtener_perfil(usuario: Usuario = Depends(usuario_actual)):
    return usuario


@router.put("/me", response_model=UsuarioRespuesta)
def actualizar_perfil(cambios: UsuarioActualizar, usuario: Usuario = Depends(usuario_actual),
                      service: UsuarioService = Depends(get_service)):
    return service.actualizar(usuario, cambios)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def desactivar_cuenta(usuario: Usuario = Depends(usuario_actual),
                      service: UsuarioService = Depends(get_service)):
    service.desactivar(usuario)


@router.post("/me/foto", response_model=UsuarioRespuesta, status_code=status.HTTP_201_CREATED)
def guardar_foto_url(datos: FotoUrlEntrada, usuario: Usuario = Depends(usuario_actual),
                     service: UsuarioService = Depends(get_service)):
    """Guarda el enlace (URL) de la foto de perfil del usuario."""
    return service.guardar_foto_url(usuario, str(datos.url))


@router.post("/me/foto/archivo", response_model=UsuarioRespuesta, status_code=status.HTTP_201_CREATED)
async def subir_foto(archivo: UploadFile = File(..., description="Imagen JPG, PNG o WEBP de hasta 5 MB"),
                     usuario: Usuario = Depends(usuario_actual),
                     service: UsuarioService = Depends(get_service)):
    """Sube la imagen a Azure Blob Storage y guarda la URL resultante en foto_url."""
    if archivo.content_type not in TIPOS_PERMITIDOS:
        raise HTTPException(415, "Formato no permitido; usa JPG, PNG o WEBP")
    contenido = await archivo.read()
    if len(contenido) > TAMANO_MAXIMO:
        raise HTTPException(413, "La imagen supera los 5 MB")
    try:
        return service.subir_foto(usuario, contenido, archivo.content_type)
    except AlmacenamientoNoConfigurado:
        raise HTTPException(503, "Azure Blob Storage no está configurado en el servidor")


@router.delete("/me/foto", status_code=status.HTTP_204_NO_CONTENT)
def quitar_foto(usuario: Usuario = Depends(usuario_actual), service: UsuarioService = Depends(get_service)):
    """Quita la foto de perfil (y borra la imagen si estaba en nuestro Blob Storage)."""
    service.quitar_foto(usuario)
