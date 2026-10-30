"""Modelos ORM: cada clase es una tabla de la base de datos.

Importarlos aquí permite que Base.metadata.create_all() los conozca todos.
"""
from app.models.usuario import Usuario
from app.models.aplicacion import App
from app.models.franja import Franja
from app.models.evento_uso import EventoUso
from app.models.plan import Plan
from app.models.ajuste_plan import AjustePlan
from app.models.pausa import Pausa
from app.models.dominio_bloqueado import DominioBloqueado
from app.models.sesion_foco import SesionFoco
from app.models.token_dispositivo import TokenDispositivo
from app.models.configuracion_usuario import ConfiguracionUsuario

__all__ = [
    "Usuario", "App", "Franja", "EventoUso", "Plan", "AjustePlan",
    "Pausa", "DominioBloqueado", "SesionFoco", "TokenDispositivo", "ConfiguracionUsuario",
]
