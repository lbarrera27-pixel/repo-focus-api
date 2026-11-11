"""
Rutas /api/v1 para clientes: límites de apps y resumen del usuario.

Ejecutar:  pytest -q tests/test_v1.py
"""
import os
import sqlite3
import tempfile

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ.pop("AZURE_SQL_SERVER", None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def auth(client):
    client.post("/auth/registro", json={"email": "v1@focus.app", "nombre": "V1", "password": "secreto123"})
    token = client.post("/auth/login", json={"email": "v1@focus.app", "password": "secreto123"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


TIKTOK = {"paquete": "com.zhiliaoapp.musically", "nombre": "TikTok", "categoria": "SOCIAL",
          "limite_minutos": 30, "limite_aperturas": 10, "nivel": 3}
NETFLIX = {"paquete": "com.netflix.mediaclient", "nombre": "Netflix", "categoria": "STREAMING",
           "limite_minutos": 60, "limite_aperturas": 2, "nivel": 2}


def test_limites_se_guardan_y_se_leen_igual_en_cualquier_cliente(client, auth):
    r = client.put("/api/v1/apps/limits", json={"apps": [TIKTOK, NETFLIX]}, headers=auth)
    assert r.status_code == 200, r.text
    leidos = client.get("/api/v1/apps/limits", headers=auth).json()
    assert [a["nombre"] for a in leidos["apps"]] == ["TikTok", "Netflix"]
    assert leidos["apps"][0]["limite_minutos"] == 30 and leidos["apps"][0]["vigilada"] is True
    assert leidos["version"] is not None
    # Las rutas anteriores también ven los campos nuevos
    assert client.get("/apps", headers=auth).json()[0]["nivel"] == 3


def test_app_que_ya_no_viene_deja_de_vigilarse_sin_borrarse(client, auth):
    r = client.put("/api/v1/apps/limits", json={"apps": [{**TIKTOK, "limite_minutos": 20}]}, headers=auth)
    apps = {a["nombre"]: a for a in r.json()["apps"]}
    assert apps["TikTok"]["limite_minutos"] == 20
    assert apps["Netflix"]["vigilada"] is False


def test_version_vieja_no_pisa_cambios_de_otro_dispositivo(client, auth):
    vieja = "2000-01-01T00:00:00"
    r = client.put("/api/v1/apps/limits", json={"apps": [TIKTOK], "version_base": vieja}, headers=auth)
    assert r.status_code == 409


def test_resumen_con_metricas_y_plan(client, auth):
    client.post("/planes", headers=auth, json={"fecha_inicio": "2026-11-01", "limite_base": 100})
    client.put("/api/v1/apps/limits", json={"apps": [TIKTOK, NETFLIX]}, headers=auth)
    dias = [
        {"fecha": "2026-11-04", "apps": [{"paquete": TIKTOK["paquete"], "minutos": 40, "aperturas": 5}]},
        {"fecha": "2026-11-05", "apps": [{"paquete": TIKTOK["paquete"], "minutos": 50, "aperturas": 6}]},
        {"fecha": "2026-11-06", "apps": [
            {"paquete": TIKTOK["paquete"], "nombre": "TikTok", "minutos": 65, "aperturas": 28},
            {"paquete": NETFLIX["paquete"], "nombre": "Netflix", "minutos": 30, "aperturas": 1},
        ]},
    ]
    assert client.post("/api/v1/metrics/sync", json={"lote_id": "resumen-01", "dias": dias}, headers=auth).status_code == 200

    r = client.get("/api/v1/users/me/summary?fecha=2026-11-06", headers=auth)
    assert r.status_code == 200, r.text
    s = r.json()
    assert s["meta_diaria_minutos"] == 100
    assert s["minutos_hoy"] == 95 and s["aperturas_hoy"] == 29
    assert s["apps_en_pausa"] == ["TikTok"]                 # 65 ≥ 30 min; Netflix 30 < 60 y 1 ≤ 2 aperturas
    assert len(s["semana"]) == 7 and s["semana"][-1]["minutos"] == 95
    assert s["dias_con_datos"] == 3
    assert s["racha_dias"] == 3                             # 40, 50 y 95 ≤ 100
    # La semana 1 del plan (del 1 al 7 de noviembre) se cierra sola con estas métricas al terminar
    from datetime import date
    if date.today() >= date(2026, 11, 8):
        assert s["riesgo"] is not None and s["plan"]["semanas"][0]["semana"] == 1
    else:
        assert s["riesgo"] is None and "ajustes" in s["riesgo_motivo"]

    # Hoy aún sin sincronizar: la racha sigue viva desde ayer; con un día entero sin datos, se corta
    siguiente = client.get("/api/v1/users/me/summary?fecha=2026-11-07", headers=auth).json()
    assert siguiente["racha_dias"] == 3
    assert client.get("/api/v1/users/me/summary?fecha=2026-11-08", headers=auth).json()["racha_dias"] == 0


def test_resumen_requiere_identificacion(client):
    assert client.get("/api/v1/users/me/summary").status_code == 422


def test_migracion_agrega_columnas_a_tabla_vieja():
    """En Azure la tabla app ya existía sin las columnas nuevas: el arranque debe agregarlas."""
    from sqlalchemy import create_engine, inspect

    import app.database as database

    viejo = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
    con = sqlite3.connect(viejo)
    con.execute("CREATE TABLE app (id INTEGER PRIMARY KEY, numero INTEGER, usuario_id INTEGER, nombre TEXT, "
                "paquete TEXT, categoria TEXT, limite_aperturas INTEGER)")
    con.execute("INSERT INTO app VALUES (1, 1, 1, 'TikTok', 'com.zhiliaoapp.musically', NULL, 10)")
    con.commit(); con.close()

    original = database.engine
    database.engine = create_engine(f"sqlite:///{viejo}")
    try:
        database._agregar_columnas_nuevas()
        database._agregar_columnas_nuevas()   # idempotente
        columnas = {c["name"] for c in inspect(database.engine).get_columns("app")}
    finally:
        database.engine = original
    assert {"limite_minutos", "nivel", "vigilada", "actualizado"} <= columnas
    fila = sqlite3.connect(viejo).execute("SELECT nivel, vigilada FROM app").fetchone()
    assert fila == (2, 1)


def _cuenta(client, email):
    client.post("/auth/registro", json={"email": email, "nombre": "C", "password": "secreto123"})
    token = client.post("/auth/login", json={"email": email, "password": "secreto123"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_las_semanas_terminadas_se_cierran_solas_y_dan_riesgo(client):
    from datetime import date, timedelta

    auth = _cuenta(client, "cierre@focus.app")
    hoy = date.today()
    inicio = hoy - timedelta(days=15)
    client.post("/planes", headers=auth, json={"fecha_inicio": str(inicio), "limite_base": 100})
    # Semana 1: 5 de 7 días dentro de 100 min; semana 2: todos dentro
    dias = []
    for i in range(14):
        minutos = 150 if i in (1, 4) else 80
        dias.append({"fecha": str(inicio + timedelta(days=i)), "apps": [{"paquete": "com.zhiliaoapp.musically", "minutos": minutos, "aperturas": 5}]})
    assert client.post("/api/v1/metrics/sync", json={"lote_id": "cierre-001", "dias": dias}, headers=auth).status_code == 200

    plan = client.get("/planes/activo", headers=auth).json()
    ajustes = client.get(f"/planes/{plan['numero']}/ajustes", headers=auth).json()
    assert [a["semana"] for a in ajustes] == [1, 2]
    assert ajustes[0]["adherencia"] == round(5 / 7, 3) and ajustes[0]["uso_meta"] == 100
    # La semana 2 usa el límite que dejó el ajuste de la 1
    assert ajustes[1]["uso_meta"] == round(100 * (1 + ajustes[0]["cambio_pct"] / 100), 1)

    # Reenviar no duplica ajustes
    client.post("/api/v1/metrics/sync", json={"lote_id": "cierre-002", "dias": dias}, headers=auth)
    assert len(client.get(f"/planes/{plan['numero']}/ajustes", headers=auth).json()) == 2

    s = client.get(f"/api/v1/users/me/summary?fecha={hoy}", headers=auth).json()
    assert s["riesgo"] is not None
    assert [x["semana"] for x in s["plan"]["semanas"]] == [1, 2] and s["plan"]["limite_actual"] > 0
    assert s["semana_anterior_minutos"] > 0
    assert s["plan"]["semana_actual"] == 3   # empezó hace 15 días


def test_sesiones_del_telefono_llegan_como_eventos_sin_duplicarse(client):
    auth = _cuenta(client, "sesiones@focus.app")
    client.put("/api/v1/apps/limits", json={"apps": [TIKTOK]}, headers=auth)
    lote = {"sesiones": [
        {"paquete": TIKTOK["paquete"], "inicio": "2026-11-08T19:00:00", "fin": "2026-11-08T19:25:00"},
        {"paquete": TIKTOK["paquete"], "inicio": "2026-11-08T21:10:00", "fin": "2026-11-08T21:15:00"},
        {"paquete": "com.no.vigilada", "inicio": "2026-11-08T20:00:00", "fin": "2026-11-08T20:30:00"},
    ]}
    r = client.post("/api/v1/sessions/sync", json=lote, headers=auth).json()
    assert r == {"insertadas": 2, "omitidas": 1}
    assert client.post("/api/v1/sessions/sync", json=lote, headers=auth).json()["insertadas"] == 0
    eventos = client.get("/eventos", headers=auth).json()
    assert [e["duracion_seg"] for e in eventos] == [1500, 300] and [e["numero"] for e in eventos] == [1, 2]
