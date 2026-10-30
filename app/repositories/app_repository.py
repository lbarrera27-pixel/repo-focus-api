from app.models import App, EventoUso, Pausa
from app.repositories.base import RepositorioPorUsuario


class AppRepository(RepositorioPorUsuario[App]):
    modelo = App

    def tiene_historial(self, app: App) -> bool:
        """True si la app ya tiene eventos o pausas que dependen de ella."""
        eventos = self.db.query(EventoUso.id).filter(EventoUso.app_id == app.id).first()
        pausas = self.db.query(Pausa.id).filter(Pausa.app_id == app.id).first()
        return bool(eventos or pausas)

    def obtener_por_paquete(self, usuario_id: int, paquete: str) -> App | None:
        return self._consulta(usuario_id).filter(App.paquete == paquete).first()
