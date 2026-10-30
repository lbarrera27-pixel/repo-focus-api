import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas._comun import Respuesta

PATRON_DOMINIO = r"^[a-z0-9][a-z0-9-]*(\.[a-z0-9-]+)+$"


def normalizar_dominio(valor):
    """"https://www.YouTube.com/watch?v=1" -> "youtube.com" (quita esquema, www., puerto y ruta; IDNA)."""
    if not isinstance(valor, str):
        return valor
    d = re.sub(r"^[a-z][a-z0-9+.-]*://", "", valor.strip().lower())
    d = re.split(r"[/?#]", d, maxsplit=1)[0].rsplit("@", 1)[-1].split(":", 1)[0].rstrip(".")
    d = d.removeprefix("www.")
    try:
        return d.encode("idna").decode("ascii")
    except UnicodeError:
        return d   # el patrón lo rechaza con 422


class DominioCrear(BaseModel):
    dominio: str = Field(..., max_length=255, pattern=PATRON_DOMINIO, examples=["youtube.com"],
                         description="Se acepta una URL completa; se guarda solo el dominio")

    _normalizar = field_validator("dominio", mode="before")(normalizar_dominio)


class DominioActualizar(BaseModel):
    dominio: Optional[str] = Field(None, max_length=255, pattern=PATRON_DOMINIO)
    activo: Optional[bool] = None

    _normalizar = field_validator("dominio", mode="before")(normalizar_dominio)


class DominioRespuesta(Respuesta):
    numero: int
    dominio: str
    activo: bool
