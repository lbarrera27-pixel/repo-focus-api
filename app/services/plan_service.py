from datetime import datetime, time, timedelta

from app.repositories.ajuste_repository import AjusteRepository
from app.repositories.pausa_repository import PausaRepository
from app.repositories.plan_repository import PlanRepository
from app.services.base import ServicioPorUsuario
from app.utils.errores import Conflicto, NoEncontrado
from app.utils.reglas_plan import calcular_cambio, explicar, limite_vigente

# Sensibilidad del ajuste: cuánto se escala el cambio que decide la lógica difusa
PERFILES = {"suave": 0.5, "normal": 1.0, "estricta": 1.5}


def rango_semana(plan, semana: int) -> tuple[datetime, datetime]:
    """[inicio, fin) de la semana `semana` del plan (la 1 empieza en fecha_inicio)."""
    desde = datetime.combine(plan.fecha_inicio + timedelta(weeks=semana - 1), time.min)
    return desde, desde + timedelta(weeks=1)


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

    def _pct_ignoradas(self, plan, semana: int) -> float:
        total, ignoradas = self.pausas.contar_entre(plan.usuario_id, *rango_semana(plan, semana))
        return ignoradas / total if total else 0.0

    def _cambio(self, plan, semana: int, adherencia: float) -> float:
        """Cambio % con las reglas difusas, usando las pausas ignoradas de esa semana del plan."""
        cambio, _ = calcular_cambio(adherencia, self._pct_ignoradas(plan, semana))
        return cambio

    def _supuesto(self, plan, ajustes, adherencia: float | None, pct_ignoradas: float | None) -> dict:
        """Entradas para proyectar: las que mande el cliente o, si no, las de la última semana."""
        ultimo = ajustes[-1] if ajustes else None
        if adherencia is None:
            adherencia = ultimo.adherencia if ultimo else 1.0
        if pct_ignoradas is None:
            pct_ignoradas = self._pct_ignoradas(plan, ultimo.semana if ultimo else plan.semana_actual)
        return {"adherencia": adherencia, "pct_ignoradas": round(pct_ignoradas, 4),
                "origen": "ultimo_ajuste" if ultimo else "por_defecto"}

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

    # ---------- lógica difusa: explicación, simulación y proyección (no escriben en la BD) ----------
    def explicacion(self, usuario_id: int, plan_numero: int, semana: int) -> dict:
        ajuste = self.obtener(usuario_id, plan_numero, semana)
        plan = ajuste.plan
        anteriores = [a for a in self.repo.listar(plan) if a.semana < semana]
        detalle = explicar(ajuste.adherencia, self._pct_ignoradas(plan, semana))
        antes = limite_vigente(plan, anteriores)
        return {
            "semana": semana,
            **detalle,
            # Si el cambio se mandó a mano (o se editaron pausas después) no coincide con el centroide
            "cambio_aplicado_pct": ajuste.cambio_pct,
            "manual": abs(ajuste.cambio_pct - detalle["salida"]["centroide_pct"]) > 0.05,
            "limite": {"antes_min": round(antes, 1), "despues_min": round(antes * (1 + ajuste.cambio_pct / 100), 1)},
        }

    def simulacion(self, usuario_id: int, plan_numero: int, datos) -> dict:
        plan = self.planes.obtener(usuario_id, plan_numero)
        ajustes = self.repo.listar(plan)
        supuesto = self._supuesto(plan, ajustes, datos.adherencia, datos.pct_ignoradas)
        cambio, _ = calcular_cambio(supuesto["adherencia"], supuesto["pct_ignoradas"])
        actual = limite_vigente(plan, ajustes)
        primera = (ajustes[-1].semana if ajustes else 0) + 1
        perfiles = []
        for perfil in datos.perfiles:
            limite, semanas, semana_meta = actual, [], None
            cambio_perfil = round(cambio * PERFILES[perfil], 1) + 0.0
            for semana in range(primera, primera + datos.semanas):
                limite *= 1 + cambio_perfil / 100
                semanas.append({"semana": semana, "cambio_pct": cambio_perfil, "limite_min": round(limite, 1)})
                if semana_meta is None and datos.meta_min is not None and limite <= datos.meta_min:
                    semana_meta = semana
            perfiles.append({"perfil": perfil, "semanas": semanas, "semana_meta": semana_meta})
        return {"supuesto": supuesto, "limite_actual_min": round(actual, 1), "perfiles": perfiles}

    def proyeccion(self, usuario_id: int, plan_numero: int) -> dict:
        plan = self.planes.obtener(usuario_id, plan_numero)
        ajustes = self.repo.listar(plan)
        supuesto = self._supuesto(plan, ajustes, None, None)
        cambio, _ = calcular_cambio(supuesto["adherencia"], supuesto["pct_ignoradas"])
        actual = limite_vigente(plan, ajustes)
        semana = (ajustes[-1].semana if ajustes else 0) + 1
        return {
            "semana": semana,
            # el ajuste de la semana n se decide al cerrarla y rige desde el día siguiente
            "proximo_ajuste": plan.fecha_inicio + timedelta(weeks=semana),
            "limite_actual_min": round(actual, 1),
            "cambio_pct": cambio,
            "limite_proyectado_min": round(actual * (1 + cambio / 100), 1),
            "supuesto": supuesto,
        }
