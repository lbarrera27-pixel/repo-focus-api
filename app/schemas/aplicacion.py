from typing import Optional

from pydantic import BaseModel, Field

from app.schemas._comun import Respuesta

# Nombre de paquete Android: al menos dos segmentos que empiezan con letra (com.instagram.android)
PATRON_PAQUETE = r"^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*)+$"


class AppCrear(BaseModel):
    nombre: str = Field(..., max_length=120, examples=["Instagram"])
    paquete: str = Field(..., max_length=255, pattern=PATRON_PAQUETE, examples=["com.instagram.android"])
    categoria: Optional[str] = Field(None, max_length=60, examples=["redes"])
    limite_aperturas: int = Field(10, ge=0, examples=[5])


class AppActualizar(BaseModel):
    nombre: Optional[str] = Field(None, max_length=120)
    paquete: Optional[str] = Field(None, max_length=255, pattern=PATRON_PAQUETE)
    categoria: Optional[str] = Field(None, max_length=60)
    limite_aperturas: Optional[int] = Field(None, ge=0)


class AppRespuesta(Respuesta):
    numero: int
    nombre: str
    paquete: str
    categoria: Optional[str] = None
    limite_aperturas: int
