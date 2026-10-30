from app.models import Usuario
from app.repositories.usuario_repository import UsuarioRepository
from app.utils import blob_storage
from app.utils.errores import Conflicto
from app.utils.security import hashear_password, verificar_password


class CredencialesInvalidas(Exception):
    pass


class UsuarioService:
    def __init__(self, repo: UsuarioRepository):
        self.repo = repo

    def registrar(self, datos) -> Usuario:
        email = datos.email.strip().lower()
        if self.repo.obtener_por_email(email):
            raise Conflicto("El email ya está registrado")
        return self.repo.crear({
            "email": email,
            "nombre": datos.nombre,
            "seudonimo": datos.seudonimo,
            "password_hash": hashear_password(datos.password),
        })

    def login(self, email: str, password: str) -> Usuario:
        usuario = self.repo.obtener_por_email(email.strip())
        if not usuario or not usuario.activo or not verificar_password(password, usuario.password_hash):
            raise CredencialesInvalidas()
        return usuario

    def actualizar(self, usuario: Usuario, cambios) -> Usuario:
        datos = {k: v for k, v in cambios.model_dump(exclude_unset=True).items() if v is not None or k == "seudonimo"}
        if "password" in datos:
            datos["password_hash"] = hashear_password(datos.pop("password"))
        return self.repo.actualizar(usuario, datos) if datos else usuario

    def desactivar(self, usuario: Usuario) -> None:
        self.repo.actualizar(usuario, {"activo": False})

    def guardar_foto_url(self, usuario: Usuario, url: str) -> Usuario:
        return self.repo.actualizar(usuario, {"foto_url": url})

    def quitar_foto(self, usuario: Usuario) -> None:
        if usuario.foto_url:
            blob_storage.borrar_foto(usuario.foto_url)
            self.repo.actualizar(usuario, {"foto_url": None})

    def subir_foto(self, usuario: Usuario, contenido: bytes, content_type: str) -> Usuario:
        url = blob_storage.subir_foto(usuario.id, contenido, content_type)
        return self.repo.actualizar(usuario, {"foto_url": url})
