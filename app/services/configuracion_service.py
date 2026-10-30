import json
from typing import Any

from app.repositories.configuracion_repository import ConfiguracionRepository


class ConfiguracionService:
    def __init__(self, repo: ConfiguracionRepository):
        self.repo = repo

    def obtener(self, usuario_id: int) -> dict[str, Any]:
        config = self.repo.obtener(usuario_id)
        return json.loads(config.datos) if config else {}

    def reemplazar(self, usuario_id: int, datos: dict[str, Any]) -> dict[str, Any]:
        config = self.repo.guardar(usuario_id, json.dumps(datos, ensure_ascii=False))
        return json.loads(config.datos)
