from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import ConfiguracionUsuario


class ConfiguracionRepository:
    def __init__(self, db: Session):
        self.db = db

    def obtener(self, usuario_id: int) -> ConfiguracionUsuario | None:
        return self.db.query(ConfiguracionUsuario).filter(ConfiguracionUsuario.usuario_id == usuario_id).first()

    def guardar(self, usuario_id: int, datos: str) -> ConfiguracionUsuario:
        """Crea la fila del usuario o reemplaza sus datos.

        Si dos peticiones crean la fila al mismo tiempo, UNIQUE(usuario_id) rechaza una
        y esa segunda se convierte en actualización.
        """
        for intento in range(2):
            config = self.obtener(usuario_id)
            if config is None:
                config = ConfiguracionUsuario(usuario_id=usuario_id, datos=datos)
                self.db.add(config)
            else:
                config.datos = datos
            try:
                self.db.commit()
                self.db.refresh(config)
                return config
            except IntegrityError:
                self.db.rollback()
                if intento == 1:
                    raise
        raise RuntimeError("inalcanzable")
