"""Sincronización por lotes de las métricas de uso que mide la app Android."""
import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import usuario_actual
from app.models import MetricaDiaria, Usuario
from app.models._comun import ahora
from app.schemas.metricas import LoteMetricas, ResultadoSync
from app.services.cierre_semanas import cerrar_semanas

router = APIRouter(prefix="/api/v1/metrics", tags=["Métricas (sincronización)"])
log = logging.getLogger("focus.metricas")


@router.post("/sync", response_model=ResultadoSync)
def sincronizar(lote: LoteMetricas, u: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    """Guarda (o actualiza) el uso por app de cada día del lote.

    Idempotente: reenviar el mismo día sustituye sus valores, así que la app puede reintentar
    sin miedo a duplicar (por ejemplo, si Azure SQL estaba despertando y respondió 503).
    Todo el lote se guarda en una sola transacción.
    """
    try:
        resultado = _guardar(lote, u, db)
    except IntegrityError:
        # Otro envío del mismo teléfono insertó esas filas en paralelo: ahora existen, se actualizan
        db.rollback()
        resultado = _guardar(lote, u, db)
    # Con el uso nuevo se cierran las semanas del plan que ya terminaron (ajuste + reglas difusas)
    try:
        cerrar_semanas(db, u.id, ahora().date())
    except Exception:  # noqa: BLE001 - el lote ya quedó guardado; el cierre se reintenta en el siguiente
        db.rollback()
        log.exception("No se pudieron cerrar las semanas del usuario %s", u.id)
    return resultado


def _guardar(lote: LoteMetricas, u: Usuario, db: Session) -> ResultadoSync:
    fechas = [d.fecha for d in lote.dias]
    existentes = {
        (m.fecha, m.paquete): m
        for m in db.scalars(
            select(MetricaDiaria).where(MetricaDiaria.usuario_id == u.id, MetricaDiaria.fecha.in_(fechas))
        )
    }
    insertadas = actualizadas = 0
    for dia in lote.dias:
        for app in dia.apps:
            fila = existentes.get((dia.fecha, app.paquete))
            if fila is None:
                db.add(MetricaDiaria(
                    usuario_id=u.id, fecha=dia.fecha, paquete=app.paquete, nombre=app.nombre,
                    minutos=app.minutos, aperturas=app.aperturas,
                ))
                insertadas += 1
            else:
                fila.minutos, fila.aperturas = app.minutos, app.aperturas
                if app.nombre:
                    fila.nombre = app.nombre
                actualizadas += 1
    db.commit()
    log.info("Lote %s del usuario %s: %s nuevas, %s actualizadas", lote.lote_id, u.id, insertadas, actualizadas)
    return ResultadoSync(lote_id=lote.lote_id, dias=len(lote.dias), insertadas=insertadas, actualizadas=actualizadas)
