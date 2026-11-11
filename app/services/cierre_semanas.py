"""
Cierre automático de las semanas del plan con el uso que manda el teléfono.

Cuando una semana del plan activo ya terminó y no tiene ajuste, se crea uno con:
- uso_meta: el límite que regía esa semana (el base, recortado por los ajustes anteriores)
- adherencia: proporción de días con datos que quedaron dentro de ese límite

Las reglas difusas calculan el cambio del límite como en un ajuste manual, y con eso el modelo
de riesgo ya tiene con qué estimar. Las semanas sin ningún dato no se cierran.
"""
from collections import defaultdict
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import MetricaDiaria
from app.repositories.ajuste_repository import AjusteRepository
from app.repositories.pausa_repository import PausaRepository
from app.repositories.plan_repository import PlanRepository
from app.schemas.ajuste_plan import AjusteCrear
from app.services.plan_service import AjusteService, PlanService, rango_semana


def limite_tras(ajuste) -> float:
    """Límite de la semana siguiente a un ajuste."""
    return ajuste.uso_meta * (1 + ajuste.cambio_pct / 100)


def cerrar_semanas(db: Session, usuario_id: int, hoy: date) -> int:
    """Crea los ajustes de las semanas ya terminadas que no tienen uno. Devuelve cuántos creó."""
    plan = PlanRepository(db).activo(usuario_id)
    if plan is None:
        return 0
    ajustes = {a.semana: a for a in AjusteRepository(db).listar(plan)}
    servicio = AjusteService(PlanService(PlanRepository(db)), AjusteRepository(db), PausaRepository(db))

    totales = defaultdict(int)
    for fecha, minutos in db.execute(
        select(MetricaDiaria.fecha, func.sum(MetricaDiaria.minutos))
        .where(MetricaDiaria.usuario_id == usuario_id, MetricaDiaria.fecha >= plan.fecha_inicio)
        .group_by(MetricaDiaria.fecha)
    ).all():
        totales[fecha] = int(minutos or 0)

    creados, limite, semana = 0, float(plan.limite_base), 1
    while True:
        desde, hasta = rango_semana(plan, semana)
        if hasta.date() > hoy:
            break
        if semana in ajustes:
            limite = limite_tras(ajustes[semana])
        else:
            dias = [m for f, m in totales.items() if desde.date() <= f < hasta.date()]
            if not dias:
                break
            adherencia = round(sum(1 for m in dias if m <= limite) / len(dias), 3)
            ajuste = servicio.crear(usuario_id, plan.numero, AjusteCrear(semana=semana, uso_meta=round(limite, 1), adherencia=adherencia))
            limite = limite_tras(ajuste)
            creados += 1
        semana += 1
    return creados
