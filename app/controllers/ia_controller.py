"""
Rutas de inteligencia artificial.

Las que llevan X-Usuario-Id leen el contexto de la BD; las demás son cálculos puros
(se les manda todo el contexto) y sirven para probar los modelos desde /docs.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import usuario_actual
from app.ia import busqueda, genetico, modelo_pausas, modelo_uso
from app.models import Usuario
from app.schemas.ia import (
    ContextoPausa, OptimizarPausasEntrada, PrediccionPausa, PronosticoEntrada, PronosticoRespuesta,
    RutaPlanEntrada, TipoPausaEntrada,
)
from app.services.ia_service import IAService, predecir_pausa, pronosticar

router = APIRouter(prefix="/ia", tags=["Inteligencia artificial"])


# ---------- Aprendizaje supervisado: pausas ignoradas ----------
@router.post("/prob-ignorar", response_model=PrediccionPausa)
def prob_ignorar(contexto: ContextoPausa):
    """Probabilidad de que el usuario ignore la pausa y el tipo de pausa con menos riesgo en ese contexto."""
    return predecir_pausa(contexto.model_dump())


@router.post("/prob-ignorar/app/{numero}", response_model=PrediccionPausa)
def prob_ignorar_app(numero: int, entrada: TipoPausaEntrada, u: Usuario = Depends(usuario_actual),
                     db: Session = Depends(get_db)):
    """Igual que /prob-ignorar, pero arma el contexto con la app del usuario y su uso de hoy."""
    return IAService(db).prob_ignorar(u.id, numero, entrada.tipo)


@router.get("/modelo-pausas")
def reporte_modelo_pausas():
    """Métricas en datos de prueba, comparación de modelos y factores que más pesan."""
    return modelo_pausas.modelo().reporte


# ---------- Red neuronal: pronóstico de uso ----------
@router.post("/pronostico-uso", response_model=PronosticoRespuesta)
def pronostico_uso(entrada: PronosticoEntrada):
    """Minutos de pantalla esperados para el día indicado a partir de los 7 anteriores."""
    ultimos = entrada.ultimos_dias[-modelo_uso.VENTANA:]
    return {"pronostico_min": pronosticar(ultimos, entrada.dia_semana), "dia_semana": entrada.dia_semana,
            "ultimos_dias": ultimos}


@router.get("/pronostico-uso", response_model=PronosticoRespuesta)
def pronostico_uso_usuario(u: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    """Pronóstico de hoy con los eventos de los últimos 7 días y si rebasará el límite del plan activo."""
    return IAService(db).pronostico_hoy(u.id)


@router.get("/modelo-uso")
def reporte_modelo_uso():
    """Error de la red neuronal contra las líneas base y su curva de aprendizaje."""
    return modelo_uso.modelo().reporte


# ---------- Algoritmo genético: horario de pausas ----------
@router.post("/optimizar-pausas")
def optimizar_pausas(entrada: OptimizarPausasEntrada):
    """Horario de pausas del día que maximiza los minutos ahorrados (usa el modelo de pausas como evaluador)."""
    return genetico.optimizar(entrada.categoria, entrada.dia_semana, entrada.uso_por_hora,
                              entrada.max_pausas, semilla=entrada.semilla)


# ---------- Búsqueda A*: ruta del plan ----------
@router.post("/ruta-plan")
def ruta_plan(entrada: RutaPlanEntrada):
    """Ruta semanal óptima del límite actual a la meta (A*), comparada con búsqueda de costo uniforme."""
    astar = busqueda.buscar(entrada.limite_actual, entrada.meta, entrada.max_semanas)
    if astar is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f"No se llega a {entrada.meta} min en {entrada.max_semanas} semanas bajando máximo 20 % por semana")
    uniforme = busqueda.buscar(entrada.limite_actual, entrada.meta, entrada.max_semanas, usar_heuristica=False)
    return {**astar, "semanas": len(astar["ruta"]) - 1, "expandidos_costo_uniforme": uniforme["expandidos"]}
