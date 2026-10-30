"""
Pruebas de todas las rutas de Focus! API.

Ejecutar:  pytest -q
Usan una base SQLite temporal, así que no tocan focus.db ni Azure SQL.
"""
import os
import tempfile

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ.pop("AZURE_SQL_SERVER", None)
os.environ.pop("AZURE_STORAGE_CONNECTION_STRING", None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.models._comun import ahora  # noqa: E402
from main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def registrar(client, email, nombre="Prueba"):
    r = client.post("/auth/registro", json={"email": email, "nombre": nombre, "password": "secreto123"})
    assert r.status_code == 201, r.text
    return {"X-Usuario-Id": str(r.json()["id"])}


@pytest.fixture(scope="module")
def u1(client):
    return registrar(client, "uno@focus.app", "Usuario Uno")


@pytest.fixture(scope="module")
def u2(client):
    return registrar(client, "dos@focus.app", "Usuario Dos")


def test_salud(client):
    r = client.get("/salud")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_registro_y_login(client, u1):
    assert client.post("/auth/registro", json={"email": "UNO@focus.app", "nombre": "x", "password": "secreto123"}).status_code == 409
    r = client.post("/auth/login", json={"email": "uno@focus.app", "password": "secreto123"})
    assert r.status_code == 200 and r.json()["usuario_id"] == int(u1["X-Usuario-Id"])
    assert client.post("/auth/login", json={"email": "uno@focus.app", "password": "malo"}).status_code == 401
    assert client.post("/auth/registro", json={"email": "no-es-email", "nombre": "x", "password": "secreto123"}).status_code == 422


def test_header_obligatorio(client):
    assert client.get("/apps").status_code == 422
    assert client.get("/apps", headers={"X-Usuario-Id": "999"}).status_code == 401


def test_usuario_perfil_y_foto(client, u1):
    r = client.get("/usuarios/me", headers=u1)
    assert r.status_code == 200 and r.json()["email"] == "uno@focus.app"
    r = client.put("/usuarios/me", headers=u1, json={"seudonimo": "piedrita"})
    assert r.status_code == 200 and r.json()["seudonimo"] == "piedrita"
    url = "https://focusstorage.blob.core.windows.net/fotos/u1.jpg"
    r = client.post("/usuarios/me/foto", headers=u1, json={"url": url})
    assert r.status_code == 201 and r.json()["foto_url"] == url
    assert client.post("/usuarios/me/foto", headers=u1, json={"url": "no-es-url"}).status_code == 422
    # sin Blob configurado -> 503; formato inválido -> 415
    r = client.post("/usuarios/me/foto/archivo", headers=u1, files={"archivo": ("f.png", b"\x89PNG", "image/png")})
    assert r.status_code == 503
    r = client.post("/usuarios/me/foto/archivo", headers=u1, files={"archivo": ("f.txt", b"hola", "text/plain")})
    assert r.status_code == 415


def test_apps_crud_y_numeracion_por_usuario(client, u1, u2):
    a1 = client.post("/apps", headers=u1, json={"nombre": "Instagram", "paquete": "com.instagram.android", "categoria": "redes", "limite_aperturas": 5})
    assert a1.status_code == 201 and a1.json()["numero"] == 1
    a2 = client.post("/apps", headers=u1, json={"nombre": "TikTok", "paquete": "com.zhiliad.tiktok"})
    assert a2.json()["numero"] == 2
    # el usuario 2 empieza su propia numeración
    b1 = client.post("/apps", headers=u2, json={"nombre": "YouTube", "paquete": "com.google.youtube"})
    assert b1.json()["numero"] == 1
    assert client.get("/apps/1", headers=u1).json()["nombre"] == "Instagram"
    assert client.get("/apps/1", headers=u2).json()["nombre"] == "YouTube"
    assert len(client.get("/apps", headers=u1).json()) == 2
    r = client.put("/apps/1", headers=u1, json={"limite_aperturas": 3})
    assert r.status_code == 200 and r.json()["limite_aperturas"] == 3 and r.json()["nombre"] == "Instagram"
    assert client.get("/apps/99", headers=u1).status_code == 404
    assert client.delete("/apps/2", headers=u1).status_code == 204
    assert client.get("/apps/2", headers=u1).status_code == 404
    # el siguiente número no reutiliza huecos intermedios incorrectamente
    assert client.post("/apps", headers=u1, json={"nombre": "X", "paquete": "com.x"}).json()["numero"] == 2


def test_franjas_crud(client):
    r = client.post("/franjas/generar", json={"fecha": "2026-10-19"})
    assert r.status_code == 201 and len(r.json()) == 12
    assert len(client.post("/franjas/generar", json={"fecha": "2026-10-19"}).json()) == 12  # idempotente
    assert len(client.get("/franjas", params={"fecha": "2026-10-19"}).json()) == 12
    r = client.post("/franjas", json={"fecha": "2026-10-20", "hora_inicio": "08:00", "hora_fin": "10:00"})
    assert r.status_code == 201
    fid = r.json()["id"]
    assert client.post("/franjas", json={"fecha": "2026-10-20", "hora_inicio": "08:00", "hora_fin": "10:00"}).status_code == 409
    assert client.post("/franjas", json={"fecha": "2026-10-20", "hora_inicio": "10:00", "hora_fin": "08:00"}).status_code == 422
    assert client.put(f"/franjas/{fid}", json={"hora_fin": "09:30"}).json()["hora_fin"] == "09:30:00"
    assert client.get(f"/franjas/{fid}").status_code == 200
    assert client.delete(f"/franjas/{fid}").status_code == 204
    assert client.get(f"/franjas/{fid}").status_code == 404


def test_eventos_crud_e_integridad(client, u1):
    franja = client.get("/franjas", params={"fecha": "2026-10-19"}).json()[4]  # 08:00-10:00
    datos = {"app_numero": 1, "franja_id": franja["id"], "inicio": "2026-10-19T08:15:00", "fin": "2026-10-19T08:30:00"}
    r = client.post("/eventos", headers=u1, json=datos)
    assert r.status_code == 201 and r.json()["duracion_seg"] == 900 and r.json()["app_numero"] == 1
    assert client.post("/eventos", headers=u1, json={**datos, "app_numero": 50}).status_code == 404
    assert client.post("/eventos", headers=u1, json={**datos, "franja_id": 9999}).status_code == 404
    assert client.post("/eventos", headers=u1, json={**datos, "fin": "2026-10-19T08:00:00"}).status_code == 422
    assert len(client.get("/eventos", headers=u1, params={"franja_id": franja["id"]}).json()) == 1
    assert len(client.get("/eventos", headers=u1, params={"app_numero": 1}).json()) == 1
    r = client.put("/eventos/1", headers=u1, json={"fin": "2026-10-19T08:45:00"})
    assert r.status_code == 200 and r.json()["duracion_seg"] == 1800
    assert client.get("/eventos/1", headers=u1).status_code == 200
    # la app 1 ya tiene historial -> no se puede borrar
    assert client.delete("/apps/1", headers=u1).status_code == 409
    # la franja tiene eventos -> no se puede borrar
    assert client.delete(f"/franjas/{franja['id']}").status_code == 409
    client.post("/eventos", headers=u1, json=datos)
    assert client.delete("/eventos/2", headers=u1).status_code == 204


def test_pausas_septima_pausa(client, u1, u2):
    for i in range(7):
        r = client.post("/pausas", headers=u1, json={"app_numero": 1, "tipo": "media", "duracion_seg": 10 + i, "ignorada": i % 2 == 0})
        assert r.status_code == 201
    client.post("/pausas", headers=u2, json={"app_numero": 1, "tipo": "leve", "duracion_seg": 5})
    r = client.get("/pausas/7", headers=u1)
    assert r.status_code == 200 and r.json()["numero"] == 7 and r.json()["duracion_seg"] == 16
    assert client.get("/pausas/7", headers=u2).status_code == 404  # el usuario 2 solo tiene 1
    assert client.get("/pausas/1", headers=u2).json()["tipo"] == "leve"
    assert client.post("/pausas", headers=u1, json={"app_numero": 1, "tipo": "extrema", "duracion_seg": 5}).status_code == 422
    assert client.put("/pausas/7", headers=u1, json={"ignorada": True}).json()["ignorada"] is True
    assert client.delete("/pausas/6", headers=u1).status_code == 204
    assert len(client.get("/pausas", headers=u1).json()) == 6


def test_planes_y_ajustes(client, u1):
    r = client.post("/planes", headers=u1, json={"fecha_inicio": "2026-10-19", "limite_base": 240})
    assert r.status_code == 201 and r.json()["numero"] == 1
    assert client.get("/planes/activo", headers=u1).json()["numero"] == 1
    client.post("/planes", headers=u1, json={"fecha_inicio": "2026-10-26", "limite_base": 200})
    planes = client.get("/planes", headers=u1).json()
    assert [p["activo"] for p in planes] == [False, True]
    assert client.get("/planes/activo", headers=u1).json()["numero"] == 2
    # ajuste sin cambio_pct -> lo calcula con las reglas difusas (0.92 queda entre "buena" y "excelente")
    r = client.post("/planes/2/ajustes", headers=u1, json={"semana": 2, "uso_meta": 210, "adherencia": 0.92})
    assert r.status_code == 201 and -10.0 < r.json()["cambio_pct"] < -5.0
    assert client.get("/planes/2", headers=u1).json()["semana_actual"] == 2
    assert client.post("/planes/2/ajustes", headers=u1, json={"semana": 2, "uso_meta": 210, "adherencia": 0.5}).status_code == 409
    r = client.put("/planes/2/ajustes/2", headers=u1, json={"adherencia": 0.6})
    assert r.json()["cambio_pct"] == 0.0
    assert len(client.get("/planes/2/ajustes", headers=u1).json()) == 1
    assert client.get("/planes/2/ajustes/2", headers=u1).status_code == 200
    assert client.put("/planes/2", headers=u1, json={"limite_base": 180}).json()["limite_base"] == 180
    assert client.delete("/planes/2/ajustes/2", headers=u1).status_code == 204
    client.post("/planes/2/ajustes", headers=u1, json={"semana": 3, "uso_meta": 190, "adherencia": 0.8})
    assert client.delete("/planes/2", headers=u1).status_code == 204  # borra también sus ajustes
    assert client.get("/planes/activo", headers=u1).status_code == 404


def test_ajuste_considera_pausas_ignoradas(client):
    u3 = registrar(client, "cuatro@focus.app")
    client.post("/apps", headers=u3, json={"nombre": "Instagram", "paquete": "com.instagram.android"})
    hoy = ahora().date().isoformat()
    client.post("/planes", headers=u3, json={"fecha_inicio": hoy, "limite_base": 240})
    # sin pausas en la semana: cumplió la meta -> reducción máxima
    r = client.post("/planes/1/ajustes", headers=u3, json={"semana": 1, "uso_meta": 210, "adherencia": 1.0})
    assert r.json()["cambio_pct"] == -10.0
    # ignoró 3 de 4 pausas esa semana -> cumplió "a la fuerza", se reduce menos
    for i in range(4):
        client.post("/pausas", headers=u3, json={"app_numero": 1, "tipo": "media", "duracion_seg": 10, "ignorada": i > 0})
    r = client.put("/planes/1/ajustes/1", headers=u3, json={"adherencia": 1.0})
    assert r.json()["cambio_pct"] == -5.0
    # las pausas de otra semana no cuentan
    r = client.post("/planes/1/ajustes", headers=u3, json={"semana": 2, "uso_meta": 190, "adherencia": 1.0})
    assert r.json()["cambio_pct"] == -10.0


def test_dominios(client, u1):
    r = client.post("/dominios", headers=u1, json={"dominio": "YouTube.com"})
    assert r.status_code == 201 and r.json()["dominio"] == "youtube.com"
    assert client.post("/dominios", headers=u1, json={"dominio": "youtube.com"}).status_code == 409
    assert client.post("/dominios", headers=u1, json={"dominio": "no valido"}).status_code == 422
    assert client.put("/dominios/1", headers=u1, json={"activo": False}).json()["activo"] is False
    assert client.get("/dominios/1", headers=u1).status_code == 200
    assert len(client.get("/dominios", headers=u1).json()) == 1
    assert client.delete("/dominios/1", headers=u1).status_code == 204


def test_sesiones_foco(client, u1):
    r = client.post("/sesiones-foco", headers=u1, json={"duracion_min": 25})
    assert r.status_code == 201 and r.json()["fin"] is None
    r = client.put("/sesiones-foco/1", headers=u1, json={"completada": True})
    assert r.json()["completada"] is True and r.json()["fin"] is not None
    client.post("/sesiones-foco", headers=u1, json={"duracion_min": 50})
    assert len(client.get("/sesiones-foco", headers=u1).json()) == 2
    assert client.get("/sesiones-foco/2", headers=u1).status_code == 200
    assert client.delete("/sesiones-foco/2", headers=u1).status_code == 204


def test_tokens_dispositivo(client, u1, u2):
    r = client.post("/tokens-dispositivo", headers=u1, json={"token": "fcm-token-0123456789"})
    assert r.status_code == 201 and r.json()["plataforma"] == "android"
    assert client.post("/tokens-dispositivo", headers=u2, json={"token": "fcm-token-0123456789"}).status_code == 409
    assert client.put("/tokens-dispositivo/1", headers=u1, json={"activo": False}).json()["activo"] is False
    assert client.get("/tokens-dispositivo/1", headers=u1).status_code == 200
    assert len(client.get("/tokens-dispositivo", headers=u1).json()) == 1
    assert client.delete("/tokens-dispositivo/1", headers=u1).status_code == 204


def test_riesgo_de_recaida(client):
    h = registrar(client, "riesgo@focus.app")
    assert client.get("/riesgo", headers=h).status_code == 404  # sin plan
    hoy = ahora().date().isoformat()
    client.post("/planes", headers=h, json={"fecha_inicio": hoy, "limite_base": 240})
    # sin ajustes: 200 con el avance hacia el primer cálculo, no 404
    r = client.get("/riesgo", headers=h)
    assert r.status_code == 200 and r.json()["estado"] == "insuficiente"
    assert r.json()["progreso"] == {"dias": {"actual": 0, "requeridos": 7}, "semanas": {"actual": 0, "requeridos": 1}}
    assert r.json()["probabilidad"] is None and r.json()["umbral_alto"] >= r.json()["umbral"]
    client.post("/apps", headers=h, json={"nombre": "TikTok", "paquete": "com.zhiliaoapp.musically"})
    # semana 1: una hora de noche y una de día, 1 de 2 pausas ignorada, 1 de 2 sesiones completada
    client.post("/eventos", headers=h, json={"app_numero": 1, "inicio": f"{hoy}T01:00:00", "fin": f"{hoy}T02:00:00"})
    client.post("/eventos", headers=h, json={"app_numero": 1, "inicio": f"{hoy}T10:00:00", "fin": f"{hoy}T11:00:00"})
    for ignorada in (True, False):
        client.post("/pausas", headers=h, json={"app_numero": 1, "tipo": "media", "duracion_seg": 10, "ignorada": ignorada})
    client.post("/sesiones-foco", headers=h, json={"duracion_min": 25})
    client.put("/sesiones-foco/1", headers=h, json={"completada": True})
    client.post("/sesiones-foco", headers=h, json={"duracion_min": 25})
    client.post("/planes/1/ajustes", headers=h, json={"semana": 1, "uso_meta": 210, "adherencia": 1.0})

    r = client.get("/riesgo", headers=h)
    assert r.status_code == 200
    s1 = r.json()
    assert (s1["plan"], s1["semana"]) == (1, 1)
    assert s1["variables"] == {
        "adherencia": 1.0, "tendencia": 0.0, "pct_ignoradas": 0.5, "pct_nocturno": 0.5,
        "pct_foco_completadas": 0.5, "cambio_pct": s1["variables"]["cambio_pct"], "racha": 1.0,
    }
    assert 0 < s1["probabilidad"] < 1 and s1["nivel"] in ("bajo", "medio", "alto")
    assert len(s1["factores"]) == 7

    # semana 2 sin cumplir: la racha se corta y el riesgo sube
    client.post("/planes/1/ajustes", headers=h, json={"semana": 2, "uso_meta": 190, "adherencia": 0.4})
    s2 = client.get("/riesgo", headers=h).json()
    assert s2["semana"] == 2 and s2["variables"]["racha"] == 0.0
    assert s2["variables"]["tendencia"] == pytest.approx(-0.6)
    assert s2["probabilidad"] > s1["probabilidad"]
    # historial: lo que se estimó al cierre de cada semana, y métricas del modelo para la interfaz
    assert s2["historial"] == [{"semana": 1, "probabilidad": s1["probabilidad"]},
                               {"semana": 2, "probabilidad": s2["probabilidad"]}]
    assert 0.5 < s2["metricas"]["auc_roc"] <= 1 and 0 < s2["metricas"]["precision"] <= 1
    assert 0.5 < s2["metricas"]["exactitud"] <= 1 and s2["estado"] == "listo"
    # recomendaciones: solo para factores que suben el riesgo, en el mismo orden de peso
    suben = [f["variable"] for f in s2["factores"] if f["efecto"] == "sube"][:2]
    assert [rec["factor"] for rec in s2["recomendaciones"]] == suben
    assert all(rec["titulo"] and rec["texto"] for rec in s2["recomendaciones"])


def test_estadisticas(client, u1, u2):
    e = client.get("/estadisticas", headers=u1).json()
    assert e["total_apps"] == 2 and e["total_eventos"] == 1 and e["minutos_uso"] == 30.0
    assert e["total_pausas"] == 6 and e["pausas_ignoradas"] == 4
    assert e["sesiones_foco_completadas"] == 1 and e["minutos_foco_completados"] == 25
    filtrado = client.get("/estadisticas", headers=u1, params={"desde": "2026-11-01"}).json()
    assert filtrado["total_eventos"] == 0
    assert client.get("/estadisticas", headers=u2).json()["total_apps"] == 1


def test_configuracion(client, u1, u2):
    assert client.get("/configuracion/me").status_code == 422
    assert client.put("/configuracion/me", json={"tema": "oscuro"}).status_code == 422
    assert client.get("/configuracion/me", headers=u1).json() == {}
    datos = {"tema": "oscuro", "notificaciones": {"resumen": True, "hora": "21:00"}, "idioma": "es-MX"}
    r = client.put("/configuracion/me", headers=u1, json=datos)
    assert r.status_code == 200 and r.json() == datos
    assert client.get("/configuracion/me", headers=u1).json() == datos
    # el PUT reemplaza el JSON completo
    assert client.put("/configuracion/me", headers=u1, json={"tema": "claro"}).json() == {"tema": "claro"}
    assert client.get("/configuracion/me", headers=u1).json() == {"tema": "claro"}
    # cada usuario tiene su propia configuración
    assert client.get("/configuracion/me", headers=u2).json() == {}
    client.put("/configuracion/me", headers=u2, json={"tema": "oscuro"})
    assert client.get("/configuracion/me", headers=u1).json() == {"tema": "claro"}
    # solo objetos y de máximo ~20 KB
    assert client.put("/configuracion/me", headers=u1, json=[1, 2]).status_code == 422
    assert client.put("/configuracion/me", headers=u1, json={"x": "a" * 21000}).status_code == 422
    assert client.get("/configuracion/me", headers=u1).json() == {"tema": "claro"}


def test_ia_prob_ignorar(client):
    contexto = {"categoria": "redes", "tipo": "leve", "hora": 23, "dia_semana": 5,
                "uso_previo_min": 60, "pausas_previas_hoy": 6}
    r = client.post("/ia/prob-ignorar", json=contexto)
    assert r.status_code == 200, r.text
    p = r.json()
    assert p["ignorara"] is True and p["probabilidad_ignorar"] == p["probabilidad_por_tipo"]["leve"]
    assert p["tipo_recomendado"] == "alta"
    # Una categoría desconocida cuenta como "otros"
    assert client.post("/ia/prob-ignorar", json={**contexto, "categoria": "inventada"}).status_code == 200
    assert client.post("/ia/prob-ignorar", json={**contexto, "hora": 24}).status_code == 422
    reporte = client.get("/ia/modelo-pausas").json()
    assert reporte["modelo_elegido"] == p["modelo"]


def test_ia_con_datos_del_usuario(client):
    from datetime import timedelta

    from app.services.ia_service import IAService

    h = registrar(client, "ia@focus.app")
    client.post("/apps", headers=h, json={"nombre": "TikTok", "paquete": "com.tiktok", "categoria": "redes"})
    _, medianoche = IAService._hoy_local()
    fmt = "%Y-%m-%dT%H:%M:%S"
    # Hoy: 20 min en TikTok y 2 pausas
    client.post("/eventos", headers=h, json={"app_numero": 1, "inicio": medianoche.strftime(fmt),
                                             "fin": (medianoche + timedelta(minutes=20)).strftime(fmt)})
    for _ in range(2):
        client.post("/pausas", headers=h, json={"app_numero": 1, "tipo": "media", "duracion_seg": 30})
    # Los 7 días anteriores: 130, 120, …, 70 minutos
    for d in range(7, 0, -1):
        inicio = medianoche - timedelta(days=d) + timedelta(hours=1)
        client.post("/eventos", headers=h, json={"app_numero": 1, "inicio": inicio.strftime(fmt),
                                                 "fin": (inicio + timedelta(minutes=60 + 10 * d)).strftime(fmt)})

    r = client.post("/ia/prob-ignorar/app/1", headers=h, json={"tipo": "leve"})
    assert r.status_code == 200, r.text
    ctx = r.json()["contexto"]
    assert ctx["categoria"] == "redes" and ctx["uso_previo_min"] == 20.0 and ctx["pausas_previas_hoy"] == 2
    assert client.post("/ia/prob-ignorar/app/9", headers=h, json={}).status_code == 404

    p = client.get("/ia/pronostico-uso", headers=h).json()
    assert p["ultimos_dias"] == [130.0, 120.0, 110.0, 100.0, 90.0, 80.0, 70.0]
    assert 30 < p["pronostico_min"] < 200 and p["excedera_limite"] is None
    client.post("/planes", headers=h, json={"fecha_inicio": "2026-10-01", "limite_base": 10})
    assert client.get("/ia/pronostico-uso", headers=h).json()["excedera_limite"] is True


def test_ia_pronostico_genetico_y_ruta(client):
    r = client.post("/ia/pronostico-uso", json={"ultimos_dias": [200] * 7, "dia_semana": 5})
    assert r.status_code == 200 and 150 < r.json()["pronostico_min"] < 300
    assert client.post("/ia/pronostico-uso", json={"ultimos_dias": [200] * 6, "dia_semana": 5}).status_code == 422
    assert client.get("/ia/modelo-uso").json()["arquitectura"]["capas_ocultas"] == [32, 16]

    uso = [8, 3, 0, 0, 0, 0, 2, 10, 12, 10, 8, 8, 15, 12, 8, 8, 12, 18, 22, 25, 30, 30, 25, 15]
    g = client.post("/ia/optimizar-pausas", json={"categoria": "redes", "dia_semana": 5, "uso_por_hora": uso,
                                                  "max_pausas": 6})
    assert g.status_code == 200, g.text
    assert 0 < len(g.json()["horario"]) <= 6
    assert client.post("/ia/optimizar-pausas", json={"categoria": "redes", "dia_semana": 5,
                                                     "uso_por_hora": uso[:10]}).status_code == 422

    ruta = client.post("/ia/ruta-plan", json={"limite_actual": 300, "meta": 120}).json()
    assert ruta["ruta"][-1]["limite_min"] <= 120 and ruta["expandidos"] <= ruta["expandidos_costo_uniforme"]
    assert client.post("/ia/ruta-plan", json={"limite_actual": 300, "meta": 120, "max_semanas": 2}).status_code == 422
    assert client.post("/ia/ruta-plan", json={"limite_actual": 100, "meta": 120}).status_code == 422


def test_desactivar_cuenta(client):
    h = registrar(client, "tres@focus.app")
    assert client.delete("/usuarios/me", headers=h).status_code == 204
    assert client.get("/usuarios/me", headers=h).status_code == 401
    assert client.post("/auth/login", json={"email": "tres@focus.app", "password": "secreto123"}).status_code == 401


def test_conteo_de_rutas(client):
    rutas = client.get("/openapi.json").json()["paths"]
    operaciones = sum(len(v) for v in rutas.values())
    assert operaciones >= 12


def test_companero_sin_llm_usa_respaldo(client, monkeypatch):
    from app.utils import llm
    monkeypatch.setattr(llm, "_obtener_cliente", lambda: None)
    h = registrar(client, "foqui@focus.app", "Dani Pérez")
    r = client.post("/companero/mensaje", headers=h, json={})
    assert r.status_code == 200
    s = r.json()
    assert s["fuente"] == "respaldo" and s["estado_foqui"] == "Normal"
    assert s["contexto"]["nombre"] == "Dani" and "primera semana" in s["mensaje"]

    hoy = ahora().date().isoformat()
    client.post("/planes", headers=h, json={"fecha_inicio": hoy, "limite_base": 200})
    client.post("/planes/1/ajustes", headers=h, json={"semana": 1, "uso_meta": 200, "adherencia": 1.0})
    ctx = client.post("/companero/mensaje", headers=h, json={"mensaje": "¿cómo voy?"}).json()["contexto"]
    assert ctx["semana"] == 1 and ctx["adherencia"] == 1.0 and ctx["cambio_pct"] == -10.0
    assert ctx["limite_diario_min"] == 180.0 and ctx["riesgo_nivel"] in ("bajo", "medio", "alto")

    client.post("/sesiones-foco", headers=h, json={"duracion_min": 25})
    assert client.post("/companero/mensaje", headers=h, json={}).json()["estado_foqui"] == "Enfocado"


def test_companero_con_llm(client, monkeypatch):
    from app.utils import llm
    recibido = {}

    def falso(sistema, mensajes):
        recibido.update(sistema=sistema, mensajes=mensajes)
        return "  **¡Hola, Dani!** Vas muy bien.  "

    monkeypatch.setattr(llm, "responder", falso)
    h = registrar(client, "foqui2@focus.app", "Dani")
    r = client.post("/companero/mensaje", headers=h, json={
        "mensaje": "¿Por qué bajó mi límite?",
        "historial": [{"rol": "foqui", "texto": "Hola"}, {"rol": "usuario", "texto": "Hola Foqui"},
                      {"rol": "foqui", "texto": "¿Cómo te fue?"}],
    })
    assert r.status_code == 200
    assert r.json()["fuente"] == "llm" and r.json()["mensaje"] == "¡Hola, Dani! Vas muy bien."
    # el turno inicial de Foqui se descarta para que el LLM empiece con el usuario
    assert [m["role"] for m in recibido["mensajes"]] == ["user", "assistant", "user"]
    assert recibido["mensajes"][-1]["content"] == "¿Por qué bajó mi límite?"
    assert "DATOS_DEL_USUARIO" in recibido["sistema"]
    assert client.post("/companero/mensaje", headers=h, json={"historial": [{"rol": "x", "texto": "a"}]}).status_code == 422


def test_reglas_de_bloqueo(client):
    h = registrar(client, "bloqueo@focus.app")
    client.post("/apps", headers=h, json={"nombre": "TikTok", "paquete": "com.zhiliaoapp.musically", "limite_aperturas": 2})
    client.post("/apps", headers=h, json={"nombre": "Reloj", "paquete": "com.android.deskclock", "limite_aperturas": 0})
    for hora in ("08", "09"):
        client.post("/eventos", headers=h, json={"app_numero": 1, "inicio": f"2026-10-19T{hora}:00:00", "fin": f"2026-10-19T{hora}:10:00"})
    client.post("/dominios", headers=h, json={"dominio": "tiktok.com"})
    client.post("/dominios", headers=h, json={"dominio": "x.com"})
    client.put("/dominios/2", headers=h, json={"activo": False})

    # sin plan: no hay límite diario, solo pausas por aperturas de más
    r = client.get("/bloqueo/reglas", headers=h, params={"fecha": "2026-10-19"})
    assert r.status_code == 200, r.text
    s = r.json()
    assert s["limite_hoy_min"] is None and s["restante_min"] is None and s["usado_hoy_min"] == 20.0
    assert s["dominios"] == ["tiktok.com"] and s["sesion_foco_activa"] is False
    tiktok, reloj = s["apps"]
    assert tiktok["aperturas_hoy"] == 2 and tiktok["accion"] == "pausa" and tiktok["nivel"] == "leve"
    assert reloj["aperturas_hoy"] == 0 and reloj["duracion_seg"] == 5

    # con plan de 20 min el límite de ese día ya se agotó -> todo se bloquea
    client.post("/planes", headers=h, json={"fecha_inicio": "2026-10-19", "limite_base": 20})
    s = client.get("/bloqueo/reglas", headers=h, params={"fecha": "2026-10-19"}).json()
    assert s["limite_hoy_min"] == 20.0 and s["restante_min"] == 0.0 and s["limite_excedido"] is True
    assert {a["accion"] for a in s["apps"]} == {"bloquear"}

    # otro día empieza de cero
    s = client.get("/bloqueo/reglas", headers=h, params={"fecha": "2026-10-20"}).json()
    assert s["usado_hoy_min"] == 0.0 and s["apps"][0]["accion"] == "permitir"

    # una sesión de foco activa bloquea todo hasta que termina o se completa
    client.post("/sesiones-foco", headers=h, json={"duracion_min": 25})
    s = client.get("/bloqueo/reglas", headers=h, params={"fecha": "2026-10-20"}).json()
    assert s["sesion_foco_activa"] is True and s["sesion_foco_hasta"] is not None
    assert {a["accion"] for a in s["apps"]} == {"bloquear"}
    client.put("/sesiones-foco/1", headers=h, json={"completada": True})
    assert client.get("/bloqueo/reglas", headers=h, params={"fecha": "2026-10-20"}).json()["sesion_foco_activa"] is False
    assert client.get("/bloqueo/reglas").status_code == 422


def test_plan_limite_actual_y_logica_difusa(client):
    from datetime import timedelta
    h = registrar(client, "difuso@focus.app")
    inicio = ahora().date() - timedelta(days=10)
    client.post("/planes", headers=h, json={"fecha_inicio": inicio.isoformat(), "limite_base": 200})
    assert client.get("/planes/activo", headers=h).json()["limite_actual_min"] == 200.0
    assert client.get("/planes/1/proyeccion", headers=h).json()["supuesto"]["origen"] == "por_defecto"
    cambio = client.post("/planes/1/ajustes", headers=h,
                         json={"semana": 1, "uso_meta": 200, "adherencia": 0.86}).json()["cambio_pct"]
    despues = round(200 * (1 + cambio / 100), 1)
    assert client.get("/planes/activo", headers=h).json()["limite_actual_min"] == despues

    # explicación: membresías, fuerza de cada regla y el mismo centroide que se guardó
    e = client.get("/planes/1/ajustes/1/explicacion", headers=h).json()
    assert e["membresias"]["adherencia"] == {"baja": 0.0, "regular": 0.0, "buena": 0.9, "excelente": 0.1}
    assert e["membresias"]["ignoradas"]["pocas"] == 1.0 and len(e["reglas"]) == 6
    assert e["salida"]["centroide_pct"] == cambio and e["manual"] is False
    assert e["limite"] == {"antes_min": 200.0, "despues_min": despues}
    assert max(mu for _, mu in e["salida"]["conjunto_agregado"]) == 0.9
    assert client.get("/planes/1/ajustes/9/explicacion", headers=h).status_code == 404

    # proyección: misma adherencia la semana 2
    p = client.get("/planes/1/proyeccion", headers=h).json()
    assert p["semana"] == 2 and p["proximo_ajuste"] == (inicio + timedelta(weeks=2)).isoformat()
    assert p["limite_actual_min"] == despues and p["cambio_pct"] == cambio
    assert p["supuesto"] == {"adherencia": 0.86, "pct_ignoradas": 0.0, "origen": "ultimo_ajuste"}

    # simulación: 3 sensibilidades; la estricta llega antes (o igual) a la meta
    s = client.post("/planes/1/simulacion", headers=h, json={"semanas": 6, "meta_min": 150}).json()
    suave, normal, estricta = s["perfiles"]
    assert [x["perfil"] for x in s["perfiles"]] == ["suave", "normal", "estricta"]
    assert normal["semanas"][0] == {"semana": 2, "cambio_pct": cambio, "limite_min": p["limite_proyectado_min"]}
    assert suave["semanas"][0]["cambio_pct"] == round(cambio * 0.5, 1)
    assert estricta["semana_meta"] is not None and estricta["semana_meta"] <= (normal["semana_meta"] or 99)
    assert estricta["semanas"][-1]["limite_min"] < normal["semanas"][-1]["limite_min"] < suave["semanas"][-1]["limite_min"]
    # supuestos del cliente y validación
    r = client.post("/planes/1/simulacion", headers=h, json={"perfiles": ["normal"], "adherencia": 0.2})
    assert r.json()["perfiles"][0]["semanas"][0]["cambio_pct"] == 5.0   # adherencia baja -> relajar
    assert client.post("/planes/1/simulacion", headers=h, json={"perfiles": ["extremo"]}).status_code == 422


def test_analitica(client):
    from datetime import timedelta
    h = registrar(client, "analitica@focus.app")
    d0 = ahora().date() - timedelta(days=3)
    d1 = d0 + timedelta(days=1)
    client.post("/planes", headers=h, json={"fecha_inicio": (d0 - timedelta(days=14)).isoformat(), "limite_base": 120})
    client.post("/apps", headers=h, json={"nombre": "Instagram", "paquete": "com.instagram.android", "categoria": "redes"})
    client.post("/apps", headers=h, json={"nombre": "YouTube", "paquete": "com.google.android.youtube", "categoria": "video"})
    for app, inicio, fin in [
        (1, f"{d0}T22:30:00", f"{d0}T23:30:00"),     # 30 min a las 22 h y 30 a las 23 h
        (2, f"{d0}T23:45:00", f"{d1}T00:15:00"),     # cruza la medianoche: 15 + 15
        (1, f"{d0 - timedelta(days=3)}T10:00:00", f"{d0 - timedelta(days=3)}T10:30:00"),  # periodo anterior
    ]:
        assert client.post("/eventos", headers=h, json={"app_numero": app, "inicio": inicio, "fin": fin}).status_code == 201
    rango = {"desde": (d0 - timedelta(days=1)).isoformat(), "hasta": d1.isoformat()}

    a = client.get("/analitica/uso-por-app", headers=h, params=rango).json()
    assert a["total_min"] == 90.0
    insta, yt = a["apps"]
    assert (insta["nombre"], insta["min"], insta["variacion_pct"]) == ("Instagram", 60.0, 100.0)
    assert (yt["nombre"], yt["min"], yt["variacion_pct"]) == ("YouTube", 30.0, None)
    assert len(client.get("/analitica/uso-por-app", headers=h, params={**rango, "limite": 1}).json()["apps"]) == 1

    c = client.get("/analitica/uso-por-categoria", headers=h, params=rango).json()
    assert c["categorias"] == [{"categoria": "redes", "min": 60.0, "pct": 66.7},
                               {"categoria": "video", "min": 30.0, "pct": 33.3}]

    d = client.get("/analitica/uso-diario", headers=h, params=rango).json()
    assert [(x["uso_min"], x["con_datos"]) for x in d["dias"]] == [(0.0, False), (75.0, True), (15.0, True)]
    assert d["dias"][1]["limite_min"] == 120.0 and d["dias"][1]["cumplio"] is True
    assert (d["promedio_min"], d["dias_con_datos"], d["dias_cumplidos"]) == (45.0, 2, 2)

    m = client.get("/analitica/heatmap", headers=h, params=rango).json()
    dia = d0.weekday()
    assert m["celdas"][dia][22] == 30.0 and m["celdas"][dia][23] == 45.0 and m["celdas"][d1.weekday()][0] == 15.0
    assert m["max_min"] == 45.0 and m["pico"] == {"dia": m["dias"][dia], "hora": 23, "min": 45.0}
    assert sum(map(sum, m["celdas"])) == 90.0 and len(m["top"]) == 3

    # sin fechas: últimos 7 días; rango al revés -> 422
    assert len(client.get("/analitica/uso-diario", headers=h).json()["dias"]) == 7
    assert client.get("/analitica/heatmap", headers=h, params={"desde": d1.isoformat(), "hasta": d0.isoformat()}).status_code == 422


def test_quitar_foto_y_validaciones(client):
    h = registrar(client, "validar@focus.app")
    client.post("/usuarios/me/foto", headers=h, json={"url": "https://ejemplo.com/yo.png"})
    assert client.delete("/usuarios/me/foto", headers=h).status_code == 204
    assert client.get("/usuarios/me", headers=h).json()["foto_url"] is None
    assert client.delete("/usuarios/me/foto", headers=h).status_code == 204   # sin foto no falla

    # dominios: se acepta la URL completa y se guarda solo el dominio
    r = client.post("/dominios", headers=h, json={"dominio": "https://www.Reddit.com/r/python?x=1"})
    assert r.status_code == 201 and r.json()["dominio"] == "reddit.com"
    assert client.post("/dominios", headers=h, json={"dominio": "reddit.com/"}).status_code == 409
    assert client.post("/dominios", headers=h, json={"dominio": "localhost"}).status_code == 422

    # apps: paquete Android válido y sin repetir
    ok = {"nombre": "Instagram", "paquete": "com.instagram.android"}
    assert client.post("/apps", headers=h, json=ok).status_code == 201
    assert client.post("/apps", headers=h, json=ok).status_code == 409
    assert client.post("/apps", headers=h, json={"nombre": "X", "paquete": "instagram"}).status_code == 422
    assert client.post("/apps", headers=h, json={"nombre": "X", "paquete": "com.1x"}).status_code == 422
    client.post("/apps", headers=h, json={"nombre": "X", "paquete": "com.twitter.android"})
    assert client.put("/apps/2", headers=h, json={"paquete": "com.instagram.android"}).status_code == 409
    assert client.put("/apps/2", headers=h, json={"paquete": "com.twitter.android"}).status_code == 200
