import json
from typing import Any

from pydantic import RootModel, model_validator

TAMANO_MAXIMO = 20 * 1024   # bytes del JSON serializado


class ConfiguracionDatos(RootModel[dict[str, Any]]):
    """Objeto JSON libre con los ajustes del usuario (máximo ~20 KB)."""

    @model_validator(mode="after")
    def validar_tamano(self):
        if len(json.dumps(self.root, ensure_ascii=False).encode("utf-8")) > TAMANO_MAXIMO:
            raise ValueError(f"La configuración supera los {TAMANO_MAXIMO // 1024} KB")
        return self
