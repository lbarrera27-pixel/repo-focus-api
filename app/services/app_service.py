from app.repositories.app_repository import AppRepository
from app.services.base import ServicioPorUsuario
from app.utils.errores import Conflicto


class AppService(ServicioPorUsuario):
    no_encontrado = "No existe la app {numero} para este usuario"
    campos_anulables = {"categoria"}
    repo: AppRepository

    def _revisar_paquete(self, usuario_id: int, paquete: str, propia=None) -> None:
        otra = self.repo.obtener_por_paquete(usuario_id, paquete)
        if otra and otra is not propia:
            raise Conflicto(f"Ya tienes registrada la app con paquete {paquete}")

    def preparar_creacion(self, usuario_id: int, datos: dict) -> dict:
        self._revisar_paquete(usuario_id, datos["paquete"])
        return datos

    def preparar_actualizacion(self, usuario_id: int, obj, cambios: dict) -> dict:
        if "paquete" in cambios:
            self._revisar_paquete(usuario_id, cambios["paquete"], obj)
        return cambios

    def antes_de_eliminar(self, app) -> None:
        # Integridad referencial: no se borra una app que ya tiene historial.
        if self.repo.tiene_historial(app):
            raise Conflicto("La app tiene eventos o pausas registradas; no se puede eliminar")
