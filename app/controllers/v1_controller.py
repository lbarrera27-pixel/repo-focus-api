"""
Rutas /api/v1 pensadas para los clientes (app Android y portal web):

- GET/PUT /api/v1/apps/limits   apps vigiladas y sus límites, iguales en el teléfono y en la web
- GET /api/v1/users/me/summary  todo lo que pinta el Inicio / panel en UNA petición, calculado aquí

El cálculo vive en el servidor para que el teléfono y la web muestren exactamente los mismos números
(y para que el modelo de riesgo no tenga que copiarse en Kotlin y en JavaScript).
"""
from datetime import date, datetime, time, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import usuario_actual
from app.models import App, EventoUso, MetricaDiaria, Usuario
from app.models._comun import ahora
from app.repositories.ajuste_repository import AjusteRepository
from app.repositories.app_repository import AppRepository
from app.repositories.pausa_repository import PausaRepository
from app.repositories.plan_repository import PlanRepository
from app.schemas.v1 import (
    AppHoy, DiaResumen, LimiteRespuesta, LimitesEntrada, LimitesRespuesta, LoteSesiones, PlanResumen, ResultadoSesiones,
    ResumenRespuesta, RiesgoResumen, SemanaPlan,
)
from app.services.cierre_semanas import limite_tras
from app.services.riesgo_service import RiesgoService
from app.utils.errores import NoEncontrado

router = APIRouter(prefix="/api/v1", tags=["v1 · Clientes (Android y web)"])


# ───────────── Apps vigiladas y límites ─────────────

def _version(apps: list[App]) -> Optional[datetime]:
    return max((a.actualizado for a in apps if a.actualizado), default=None)


def _respuesta(apps: list[App]) -> LimitesRespuesta:
    return LimitesRespuesta(
        version=_version(apps),
        apps=[LimiteRespuesta(
            numero=a.numero, paquete=a.paquete, nombre=a.nombre, categoria=a.categoria,
            limite_minutos=a.limite_minutos, limite_aperturas=a.limite_aperturas, nivel=a.nivel, vigilada=a.vigilada,
        ) for a in sorted(apps, key=lambda a: a.numero)],
    )


@router.get("/apps/limits", response_model=LimitesRespuesta)
def leer_limites(u: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    """Apps del usuario con sus límites. 'version' sirve para detectar cambios hechos en otro dispositivo."""
    return _respuesta(AppRepository(db).listar(u.id))


@router.put("/apps/limits", response_model=LimitesRespuesta)
def guardar_limites(datos: LimitesEntrada, u: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    """Reemplaza el estado de "Mis apps" con la lista completa que manda el cliente."""
    repo = AppRepository(db)
    actuales = repo.listar(u.id)
    # Control de concurrencia optimista: si la web cambió algo después de que el teléfono leyó, no se pisa
    version = _version(actuales)
    if datos.version_base is not None and version is not None and version > datos.version_base:
        raise HTTPException(status_code=409, detail="Las apps cambiaron en otro dispositivo; vuelve a leerlas")

    por_paquete = {a.paquete: a for a in actuales}
    enviados = set()
    for item in datos.apps:
        enviados.add(item.paquete)
        campos = item.model_dump()
        existente = por_paquete.get(item.paquete)
        if existente is None:
            repo.crear(u.id, campos)
        else:
            cambios = {k: v for k, v in campos.items() if getattr(existente, k) != v}
            if cambios:
                repo.actualizar(existente, cambios)
    # Las que ya no están en la lista dejan de vigilarse (se conservan por su historial de pausas/eventos)
    for paquete, app in por_paquete.items():
        if paquete not in enviados and app.vigilada:
            repo.actualizar(app, {"vigilada": False})
    return _respuesta(repo.listar(u.id))


# ───────────── Resumen ─────────────

@router.get("/users/me/summary", response_model=ResumenRespuesta)
def resumen(
    fecha: Optional[date] = Query(None, description="Día del cliente (zona local). Por defecto, hoy en UTC."),
    u: Usuario = Depends(usuario_actual),
    db: Session = Depends(get_db),
):
    """Inicio en una sola petición: uso de hoy, apps en pausa, semana, racha, pausas y riesgo."""
    hoy = fecha or ahora().date()
    inicio_semana = hoy - timedelta(days=6)

    plan = PlanRepository(db).activo(u.id)
    meta = plan.limite_base if plan else None
    apps = {a.paquete: a for a in AppRepository(db).listar(u.id)}

    # Hoy, por app
    filas_hoy = db.scalars(select(MetricaDiaria).where(MetricaDiaria.usuario_id == u.id, MetricaDiaria.fecha == hoy)).all()
    apps_hoy = []
    for m in sorted(filas_hoy, key=lambda m: -m.minutos):
        regla = apps.get(m.paquete)
        vigilada = regla is not None and regla.vigilada
        en_pausa = vigilada and (
            (regla.limite_minutos is not None and m.minutos >= regla.limite_minutos)
            or m.aperturas > regla.limite_aperturas
        )
        apps_hoy.append(AppHoy(
            paquete=m.paquete, nombre=m.nombre or (regla.nombre if regla else None), minutos=m.minutos,
            aperturas=m.aperturas, limite_minutos=regla.limite_minutos if regla else None, en_pausa=en_pausa,
        ))

    # Semana: total por día (los días sin datos van con 0 y cumple = null)
    totales = dict(db.execute(
        select(MetricaDiaria.fecha, func.sum(MetricaDiaria.minutos))
        .where(MetricaDiaria.usuario_id == u.id, MetricaDiaria.fecha >= inicio_semana, MetricaDiaria.fecha <= hoy)
        .group_by(MetricaDiaria.fecha)
    ).all())
    semana = []
    for i in range(7):
        d = inicio_semana + timedelta(days=i)
        minutos = int(totales.get(d) or 0)
        semana.append(DiaResumen(fecha=d, minutos=minutos, cumple=(minutos <= meta) if (meta is not None and d in totales) else None))

    # Racha: días seguidos con datos dentro de la meta, contando hacia atrás desde hoy
    racha = 0
    if meta is not None:
        historial = dict(db.execute(
            select(MetricaDiaria.fecha, func.sum(MetricaDiaria.minutos))
            .where(MetricaDiaria.usuario_id == u.id, MetricaDiaria.fecha <= hoy)
            .group_by(MetricaDiaria.fecha)
        ).all())
        # Si hoy aún no se ha sincronizado, la racha sigue viva y se cuenta desde ayer
        d = hoy if hoy in historial else hoy - timedelta(days=1)
        while d in historial and historial[d] <= meta:
            racha += 1
            d -= timedelta(days=1)

    pausas, ignoradas = PausaRepository(db).contar_entre(
        u.id, datetime.combine(inicio_semana, time.min), datetime.combine(hoy + timedelta(days=1), time.min),
    )

    # Riesgo: el modelo necesita un plan activo con al menos un ajuste semanal
    riesgo, motivo = None, None
    try:
        r = RiesgoService(db).calcular(u.id)
        riesgo = RiesgoResumen(nivel=r["nivel"], probabilidad=r["probabilidad"], semana=r["semana"])
    except NoEncontrado as e:
        motivo = str(e)

    anteriores = int(db.scalar(
        select(func.sum(MetricaDiaria.minutos)).where(
            MetricaDiaria.usuario_id == u.id,
            MetricaDiaria.fecha >= inicio_semana - timedelta(days=7), MetricaDiaria.fecha < inicio_semana,
        )
    ) or 0)

    plan_resumen = None
    if plan is not None:
        ajustes = AjusteRepository(db).listar(plan)
        plan_resumen = PlanResumen(
            fecha_inicio=plan.fecha_inicio,
            # La semana en curso según la fecha (semana_actual del plan es la última ajustada)
            semana_actual=max(1, (hoy - plan.fecha_inicio).days // 7 + 1),
            limite_actual=round(limite_tras(ajustes[-1]) if ajustes else float(plan.limite_base), 1),
            semanas=[SemanaPlan(semana=a.semana, uso_meta=a.uso_meta, adherencia=a.adherencia, cambio_pct=a.cambio_pct)
                     for a in ajustes],
        )

    dias_con_datos = db.scalar(
        select(func.count(func.distinct(MetricaDiaria.fecha))).where(MetricaDiaria.usuario_id == u.id)
    ) or 0
    return ResumenRespuesta(
        fecha=hoy, meta_diaria_minutos=meta,
        minutos_hoy=sum(a.minutos for a in apps_hoy), aperturas_hoy=sum(a.aperturas for a in apps_hoy),
        apps_hoy=apps_hoy, apps_en_pausa=[a.nombre or a.paquete for a in apps_hoy if a.en_pausa],
        semana=semana, dias_con_datos=dias_con_datos, racha_dias=racha,
        pausas_respetadas=pausas - ignoradas, pausas_ignoradas=ignoradas,
        riesgo=riesgo, riesgo_motivo=motivo,
        semana_anterior_minutos=anteriores, plan=plan_resumen,
    )


# ───────────── Sesiones de uso ─────────────

@router.post("/sessions/sync", response_model=ResultadoSesiones)
def sincronizar_sesiones(lote: LoteSesiones, u: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    """Guarda las sesiones de uso del teléfono como eventos, que es lo que dibuja el portal web.

    Idempotente: una sesión de la misma app con la misma hora de inicio no se repite.
    Solo se guardan las apps que el usuario vigila ("Mis apps").
    """
    try:
        return _guardar_sesiones(lote, u, db)
    except IntegrityError:
        # Otro envío en paralelo tomó los mismos números: se reintenta con los nuevos
        db.rollback()
        return _guardar_sesiones(lote, u, db)


def _guardar_sesiones(lote: LoteSesiones, u: Usuario, db: Session) -> ResultadoSesiones:
    apps = {a.paquete: a.id for a in AppRepository(db).listar(u.id) if a.paquete}
    validas = [s for s in lote.sesiones if s.paquete in apps]
    if not validas:
        return ResultadoSesiones(insertadas=0, omitidas=len(lote.sesiones))
    desde, hasta = min(s.inicio for s in validas), max(s.inicio for s in validas)
    existentes = set(db.execute(
        select(EventoUso.app_id, EventoUso.inicio)
        .where(EventoUso.usuario_id == u.id, EventoUso.inicio >= desde, EventoUso.inicio <= hasta)
    ).all())
    numero = (db.scalar(select(func.max(EventoUso.numero)).where(EventoUso.usuario_id == u.id)) or 0) + 1
    insertadas = 0
    for s in sorted(validas, key=lambda s: s.inicio):
        clave = (apps[s.paquete], s.inicio)
        if clave in existentes:
            continue
        existentes.add(clave)
        db.add(EventoUso(
            usuario_id=u.id, numero=numero, app_id=apps[s.paquete], inicio=s.inicio, fin=s.fin,
            duracion_seg=int((s.fin - s.inicio).total_seconds()),
        ))
        numero += 1
        insertadas += 1
    db.commit()
    return ResultadoSesiones(insertadas=insertadas, omitidas=len(lote.sesiones) - insertadas)
