"""
Subida de fotos de perfil a Azure Blob Storage.

Requiere AZURE_STORAGE_CONNECTION_STRING. El contenedor (por defecto "fotos")
se crea solo si no existe.

- AZURE_STORAGE_PUBLICO=true  -> el contenedor es público y se guarda la URL "limpia".
- AZURE_STORAGE_PUBLICO=false (por defecto) -> la URL lleva un token SAS de solo
  lectura válido por un año. Funciona aunque la cuenta no permita acceso anónimo,
  que es lo normal en Azure for Students.
"""
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote, urlparse

from app.config import AZURE_STORAGE_CONNECTION_STRING, AZURE_STORAGE_CONTAINER

logging.getLogger("azure").setLevel(logging.WARNING)

TIPOS_PERMITIDOS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
TAMANO_MAXIMO = 5 * 1024 * 1024  # 5 MB


class AlmacenamientoNoConfigurado(Exception):
    pass


def subir_foto(usuario_id: int, contenido: bytes, content_type: str) -> str:
    if not AZURE_STORAGE_CONNECTION_STRING:
        raise AlmacenamientoNoConfigurado("Falta AZURE_STORAGE_CONNECTION_STRING")

    from azure.core.exceptions import ResourceExistsError
    from azure.storage.blob import BlobSasPermissions, BlobServiceClient, ContentSettings, generate_blob_sas

    servicio = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    contenedor = servicio.get_container_client(AZURE_STORAGE_CONTAINER)
    try:
        contenedor.create_container()
    except ResourceExistsError:
        pass

    extension = TIPOS_PERMITIDOS[content_type]
    nombre = f"usuario-{usuario_id}/{uuid.uuid4().hex}.{extension}"
    blob = contenedor.get_blob_client(nombre)
    blob.upload_blob(contenido, overwrite=True, content_settings=ContentSettings(content_type=content_type))

    if os.getenv("AZURE_STORAGE_PUBLICO", "false").lower() == "true":
        return blob.url

    sas = generate_blob_sas(
        account_name=servicio.account_name,
        container_name=AZURE_STORAGE_CONTAINER,
        blob_name=nombre,
        account_key=servicio.credential.account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.now(timezone.utc) + timedelta(days=365),
    )
    return f"{blob.url}?{sas}"


def borrar_foto(url: str) -> bool:
    """Borra el blob si la URL es de nuestro contenedor. True si lo borró.

    No lanza errores: si el blob ya no existe o la URL es externa (POST /usuarios/me/foto),
    basta con quitar la URL del perfil.
    """
    if not AZURE_STORAGE_CONNECTION_STRING:
        return False
    ruta = unquote(urlparse(url).path).lstrip("/")
    prefijo = f"{AZURE_STORAGE_CONTAINER}/"
    if not ruta.startswith(prefijo):
        return False
    try:
        from azure.storage.blob import BlobServiceClient

        servicio = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        if urlparse(url).hostname != urlparse(servicio.url).hostname:
            return False
        servicio.get_blob_client(AZURE_STORAGE_CONTAINER, ruta[len(prefijo):]).delete_blob()
        return True
    except Exception as e:  # noqa: BLE001  (el perfil se limpia aunque el blob falle)
        logging.getLogger("focus.api").warning("No se pudo borrar la foto %s: %s", ruta, e)
        return False
