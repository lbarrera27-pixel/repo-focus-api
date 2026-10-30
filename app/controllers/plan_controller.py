"""CRUD de PLAN y de sus AJUSTE_PLAN (rutas anidadas /planes/{numero}/ajustes)."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import usuario_actual
from app.models import Usuario
from app.repositories.ajuste_repository import AjusteRepository
from app.repositories.pausa_repository import PausaRepository
from app.repositories.plan_repository import PlanRepository
from app.schemas.ajuste_plan import AjusteActualizar, AjusteCrear, AjusteRespuesta
from app.schemas.plan import (
    ExplicacionAjuste, PlanActualizar, PlanCrear, PlanRespuesta, ProyeccionRespuesta, SimulacionEntrada,
    SimulacionRespuesta,
)
from app.services.plan_service import AjusteService, PlanService

router = APIRouter(prefix="/planes", tags=["Planes y ajustes"])


def get_service(db: Session = Depends(get_db)) -> PlanService:
    return PlanService(PlanRepository(db))


def get_ajustes(db: Session = Depends(get_db)) -> AjusteService:
    return AjusteService(PlanService(PlanRepository(db)), AjusteRepository(db), PausaRepository(db))


# ---------- PLAN ----------
@router.post("", response_model=PlanRespuesta, status_code=status.HTTP_201_CREATED)
def crear_plan(datos: PlanCrear, u: Usuario = Depends(usuario_actual), service: PlanService = Depends(get_service)):
    return service.crear(u.id, datos)


@router.get("", response_model=list[PlanRespuesta])
def listar_planes(u: Usuario = Depends(usuario_actual), service: PlanService = Depends(get_service)):
    return service.listar(u.id)


@router.get("/activo", response_model=PlanRespuesta)
def plan_activo(u: Usuario = Depends(usuario_actual), service: PlanService = Depends(get_service)):
    return service.activo(u.id)


@router.get("/{numero}", response_model=PlanRespuesta)
def obtener_plan(numero: int, u: Usuario = Depends(usuario_actual), service: PlanService = Depends(get_service)):
    return service.obtener(u.id, numero)


@router.put("/{numero}", response_model=PlanRespuesta)
def actualizar_plan(numero: int, cambios: PlanActualizar, u: Usuario = Depends(usuario_actual),
                    service: PlanService = Depends(get_service)):
    return service.actualizar(u.id, numero, cambios)


@router.delete("/{numero}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_plan(numero: int, u: Usuario = Depends(usuario_actual), service: PlanService = Depends(get_service)):
    service.eliminar(u.id, numero)


# ---------- AJUSTE_PLAN ----------
@router.post("/{numero}/ajustes", response_model=AjusteRespuesta, status_code=status.HTTP_201_CREATED)
def crear_ajuste(numero: int, datos: AjusteCrear, u: Usuario = Depends(usuario_actual),
                 service: AjusteService = Depends(get_ajustes)):
    return service.crear(u.id, numero, datos)


@router.get("/{numero}/ajustes", response_model=list[AjusteRespuesta])
def listar_ajustes(numero: int, u: Usuario = Depends(usuario_actual), service: AjusteService = Depends(get_ajustes)):
    return service.listar(u.id, numero)


@router.get("/{numero}/ajustes/{semana}", response_model=AjusteRespuesta)
def obtener_ajuste(numero: int, semana: int, u: Usuario = Depends(usuario_actual),
                   service: AjusteService = Depends(get_ajustes)):
    return service.obtener(u.id, numero, semana)


@router.put("/{numero}/ajustes/{semana}", response_model=AjusteRespuesta)
def actualizar_ajuste(numero: int, semana: int, cambios: AjusteActualizar, u: Usuario = Depends(usuario_actual),
                      service: AjusteService = Depends(get_ajustes)):
    return service.actualizar(u.id, numero, semana, cambios)


@router.delete("/{numero}/ajustes/{semana}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_ajuste(numero: int, semana: int, u: Usuario = Depends(usuario_actual),
                    service: AjusteService = Depends(get_ajustes)):
    service.eliminar(u.id, numero, semana)


# ---------- Lógica difusa (solo calcula, no guarda) ----------
@router.get("/{numero}/ajustes/{semana}/explicacion", response_model=ExplicacionAjuste)
def explicar_ajuste(numero: int, semana: int, u: Usuario = Depends(usuario_actual),
                    service: AjusteService = Depends(get_ajustes)):
    """Pasos del controlador Mamdani para ese ajuste: membresías, fuerza de cada regla y centroide."""
    return service.explicacion(u.id, numero, semana)


@router.post("/{numero}/simulacion", response_model=SimulacionRespuesta)
def simular_plan(numero: int, datos: SimulacionEntrada, u: Usuario = Depends(usuario_actual),
                 service: AjusteService = Depends(get_ajustes)):
    """Cómo bajaría el límite las próximas semanas con cada sensibilidad (suave ×0.5, normal, estricta ×1.5)."""
    return service.simulacion(u.id, numero, datos)


@router.get("/{numero}/proyeccion", response_model=ProyeccionRespuesta)
def proyectar_plan(numero: int, u: Usuario = Depends(usuario_actual), service: AjusteService = Depends(get_ajustes)):
    """Límite que tendría la próxima semana si se mantienen la adherencia y las pausas actuales."""
    return service.proyeccion(u.id, numero)
