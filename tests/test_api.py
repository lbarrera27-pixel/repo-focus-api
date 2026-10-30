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
    assert client.get("/riesgo", headers=h).status_code == 404  # sin ajustes
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


def test_estadisticas(client, u1, u2):
    e = client.get("/estadisticas", headers=u1).json()
    assert e["total_apps"] == 2 and e["total_eventos"] == 1 and e["minutos_uso"] == 30.0
    assert e["total_pausas"] == 6 and e["pausas_ignoradas"] == 4
    assert e["sesiones_foco_completadas"] == 1 and e["minutos_foco_completados"] == 25
    filtrado = client.get("/estadisticas", headers=u1, params={"desde": "2026-11-01"}).json()
    assert filtrado["total_eventos"] == 0
    assert client.get("/estadisticas", headers=u2).json()["total_apps"] == 1


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
