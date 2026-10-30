from datetime import datetime, time, timedelta

from app.repositories.ajuste_repository import AjusteRepository
from app.repositories.pausa_repository import PausaRepository
from app.repositories.plan_repository import PlanRepository
from app.services.base import ServicioPorUsuario
from app.utils.errores import Conflicto, NoEncontrado
from app.utils.reglas_plan import calcular_cambio


def rango_semana(plan, semana: int) -> tuple[datetime, datetime]:
    """[inicio, fin) de la semana `semana` del plan (la 1 empieza en fecha_inicio)."""
    desde = datetime.combine(plan.fecha_inicio + timedelta(weeks=semana - 1), time.min)
    return desde, desde + timedelta(weeks=1)


def limite_vigente(plan, ajustes) -> float:
    """Minutos diarios: el límite base con todos los ajustes semanales aplicados en orden."""
    limite = plan.limite_base
    for ajuste in ajustes:
        limite *= 1 + ajuste.cambio_pct / 100
    return limite


class PlanService(ServicioPorUsuario):
    no_encontrado = "No existe el plan {numero} para este usuario"
    repo: PlanRepository

    def crear(self, usuario_id: int, datos):
        # Solo puede haber un plan activo: el nuevo reemplaza al anterior.
        self.repo.desactivar_todos(usuario_id)
        return super().crear(usuario_id, datos)

    def activo(self, usuario_id: int):
        plan = self.repo.activo(usuario_id)
        if plan is None:
            raise NoEncontrado("El usuario no tiene un plan activo")
        return plan


class AjusteService:
    def __init__(self, planes: PlanService, repo: AjusteRepository, pausas: PausaRepository):
        self.planes = planes
        self.repo = repo
        self.pausas = pausas

    def _cambio(self, plan, semana: int, adherencia: float) -> float:
        """Cambio % con las reglas difusas, usando las pausas ignoradas de esa semana del plan."""
        total, ignoradas = self.pausas.contar_entre(plan.usuario_id, *rango_semana(plan, semana))
        cambio, _ = calcular_cambio(adherencia, ignoradas / total if total else 0.0)
        return cambio

    def listar(self, usuario_id: int, plan_numero: int):
        return self.repo.listar(self.planes.obtener(usuario_id, plan_numero))

    def obtener(self, usuario_id: int, plan_numero: int, semana: int):
        plan = self.planes.obtener(usuario_id, plan_numero)
        ajuste = self.repo.obtener(plan, semana)
        if ajuste is None:
            raise NoEncontrado(f"El plan {plan_numero} no tiene ajuste en la semana {semana}")
        return ajuste

    def crear(self, usuario_id: int, plan_numero: int, datos):
        plan = self.planes.obtener(usuario_id, plan_numero)
        if self.repo.obtener(plan, datos.semana):
            raise Conflicto(f"Ya existe un ajuste para la semana {datos.semana}")
        valores = datos.model_dump()
        if valores["cambio_pct"] is None:
            valores["cambio_pct"] = self._cambio(plan, datos.semana, valores["adherencia"])
        ajuste = self.repo.crear(plan, valores)
        if datos.semana > plan.semana_actual:
            self.planes.repo.actualizar(plan, {"semana_actual": datos.semana})
        return ajuste

    def actualizar(self, usuario_id: int, plan_numero: int, semana: int, cambios):
        ajuste = self.obtener(usuario_id, plan_numero, semana)
        datos = {k: v for k, v in cambios.model_dump(exclude_unset=True).items() if v is not None}
        if "adherencia" in datos and "cambio_pct" not in datos:
            datos["cambio_pct"] = self._cambio(ajuste.plan, semana, datos["adherencia"])
        return self.repo.actualizar(ajuste, datos) if datos else ajuste

    def eliminar(self, usuario_id: int, plan_numero: int, semana: int) -> None:
        self.repo.eliminar(self.obtener(usuario_id, plan_numero, semana))
