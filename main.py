"""
Focus! API — backend de la app Android Focus! (Servicios Cloud, UAQ).

Arquitectura en capas:
    Controller (rutas)  ->  Service (reglas de negocio)  ->  Repository (SQLAlchemy)  ->  Azure SQL / SQLite

Ejecutar en local:
    uvicorn main:app --reload

En Azure App Service (comando de inicio):
    gunicorn -w 2 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 main:app
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.config import CORS_ORIGINS
from app.controllers import (
    app_controller, auth_controller, bloqueo_controller, companero_controller, configuracion_controller,
    dominio_controller, estadisticas_controller, evento_controller, franja_controller, ia_controller,
    pausa_controller, plan_controller, riesgo_controller, salud_controller, sesion_controller,
    token_controller, usuario_controller,
)
from app.database import sincronizar_esquema
from app.utils.errores import Conflicto, NoEncontrado

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("focus.api")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # El ORM crea en la BD las tablas que falten al arrancar el servidor
    sincronizar_esquema()
    yield


app = FastAPI(
    title="Focus! API",
    version="2.0.0",
    description=(
        "Backend de Focus!, app Android para reducir gradualmente el tiempo en pantalla.\n\n"
        "**Identificación:** las rutas privadas requieren el header `X-Usuario-Id`. "
        "Los números en las rutas son relativos a ese usuario: "
        "`GET /pausas/7` con `X-Usuario-Id: 1` devuelve la 7.ª pausa del usuario 1."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Errores de negocio -> respuestas HTTP ----------
@app.exception_handler(NoEncontrado)
async def manejar_no_encontrado(_: Request, exc: NoEncontrado):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(Conflicto)
async def manejar_conflicto(_: Request, exc: Conflicto):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(IntegrityError)
async def manejar_integridad(_: Request, exc: IntegrityError):
    return JSONResponse(status_code=409, content={"detail": "El registro viola una restricción de la base de datos"})


@app.exception_handler(DBAPIError)
async def manejar_bd_no_disponible(_: Request, exc: DBAPIError):
    # Azure SQL serverless se pausa tras 1 h sin uso; la primera petición falla mientras despierta
    log.warning("Base de datos no disponible: %s", exc.orig)
    return JSONResponse(
        status_code=503,
        headers={"Retry-After": "30"},
        content={"detail": "La base de datos se está iniciando; reintenta en unos 30 segundos"},
    )


# ---------- Controladores ----------
@app.get("/", include_in_schema=False)
def inicio():
    return {"api": "Focus!", "version": "2.0.0", "docs": "/docs", "salud": "/salud"}


for modulo in (
    salud_controller, auth_controller, usuario_controller, app_controller, evento_controller,
    franja_controller, plan_controller, pausa_controller, dominio_controller, sesion_controller,
    token_controller, estadisticas_controller, configuracion_controller, bloqueo_controller, riesgo_controller,
    companero_controller, ia_controller,
):
    app.include_router(modulo.router)
