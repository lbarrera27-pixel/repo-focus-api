"""
Focus! - Paso 6 (opcional): crear una cuenta de demostración con datos de ejemplo.

Crea el usuario y lo llena por medio de la API (no toca la base directamente), así sirve igual
para la API local que para la de Azure:
  - 6 apps con límite de aperturas
  - ~2 semanas de eventos de uso (más uso de noche y una tendencia a la baja)
  - pausas de fricción de hoy, un plan con 3 ajustes semanales (reglas difusas del servidor),
    un dispositivo, sesiones de foco y dominios bloqueados

Los eventos tienen fechas relativas al día en que se corre. Para que la cuenta no se vea vacía
semanas después (p. ej. el día de la entrega final), --refrescar rellena la MISMA cuenta desde su
último evento hasta hoy, agrega las pausas de hoy y avanza el plan con los ajustes de las semanas que pasaron.

Solo usa la biblioteca estándar de Python. Uso:
    python deploy/06_datos_demo.py --api https://focus-api-<sufijo>.azurewebsites.net --email profesora@focus.app
    python deploy/06_datos_demo.py --api https://focus-api-<sufijo>.azurewebsites.net --email profesora@focus.app --refrescar
La contraseña se pide en pantalla (o se lee de la variable FOCUS_DEMO_PASSWORD).
"""
import argparse
import getpass
import json
import os
import random
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone

APPS = [
    {"nombre": "Instagram", "paquete": "com.instagram.android", "categoria": "social", "limite_aperturas": 10},
    {"nombre": "TikTok", "paquete": "com.zhiliaoapp.musically", "categoria": "social", "limite_aperturas": 8},
    {"nombre": "WhatsApp", "paquete": "com.whatsapp", "categoria": "mensajeria", "limite_aperturas": 25},
    {"nombre": "YouTube", "paquete": "com.google.android.youtube", "categoria": "video", "limite_aperturas": 6},
    {"nombre": "Netflix", "paquete": "com.netflix.mediaclient", "categoria": "video", "limite_aperturas": 3},
    {"nombre": "Clash Royale", "paquete": "com.supercell.clashroyale", "categoria": "juegos", "limite_aperturas": 4},
]
# Qué tanto se usa cada app (mismo orden que APPS)
PESO_APP = [0.26, 0.2, 0.22, 0.14, 0.06, 0.12]
# Peso de uso por hora del día: más alto de noche
PESO_HORA = [0.9, 0.5, 0.3, 0.1, 0.05, 0.05, 0.1, 0.25, 0.3, 0.35, 0.4, 0.4,
             0.45, 0.5, 0.5, 0.55, 0.55, 0.5, 0.45, 0.55, 0.65, 0.75, 0.95, 1]
DURACION_SEG = {"social": (60, 360), "mensajeria": (30, 240), "video": (300, 1500), "juegos": (240, 900)}


class Api:
    def __init__(self, base: str):
        self.base = base.rstrip("/")
        self.usuario_id = None

    def pedir(self, metodo: str, ruta: str, cuerpo=None, esperado=(200, 201)):
        headers = {"Accept": "application/json"}
        if self.usuario_id:
            headers["X-Usuario-Id"] = str(self.usuario_id)
        datos = None
        if cuerpo is not None:
            headers["Content-Type"] = "application/json"
            datos = json.dumps(cuerpo, default=str).encode("utf-8")
        peticion = urllib.request.Request(self.base + ruta, data=datos, headers=headers, method=metodo)
        try:
            with urllib.request.urlopen(peticion, timeout=90) as r:
                status, texto = r.status, r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            status, texto = e.code, e.read().decode("utf-8")
        if status not in esperado:
            raise RuntimeError(f"{metodo} {ruta} -> {status}: {texto[:300]}")
        return status, (json.loads(texto) if texto else None)


def iniciar_sesion(api: Api, email: str, nombre: str, password: str) -> None:
    status, r = api.pedir("POST", "/auth/registro",
                          {"email": email, "nombre": nombre, "password": password}, esperado=(201, 409))
    if status == 201:
        api.usuario_id = r["id"]
        print(f"Cuenta creada: {email} (id {api.usuario_id})")
        return
    # Ya existía: solo se continúa si la contraseña es correcta y la cuenta está vacía
    _, r = api.pedir("POST", "/auth/login", {"email": email, "password": password})
    api.usuario_id = r["usuario_id"]
    _, apps = api.pedir("GET", "/apps")
    if apps:
        sys.exit(f"La cuenta {email} ya tiene datos; usa otro correo para no duplicarlos.")
    print(f"La cuenta {email} ya existía y está vacía (id {api.usuario_id}); se llenará.")


def entrar(api: Api, email: str, password: str) -> None:
    status, r = api.pedir("POST", "/auth/login", {"email": email, "password": password}, esperado=(200, 401))
    if status == 401:
        sys.exit(f"No se pudo entrar con {email}: correo o contraseña incorrectos (o la cuenta no existe).")
    api.usuario_id = r["usuario_id"]
    print(f"Sesión iniciada: {email} (id {api.usuario_id})")


def generar_eventos(azar: random.Random, dias: int, ahora: datetime):
    eventos = []
    for d in range(dias - 1, -1, -1):
        # El uso baja poco a poco: el plan gradual está funcionando
        factor = 1.15 - (dias - d) / dias * 0.4
        dia = (ahora - timedelta(days=d)).replace(hour=0, minute=0, second=0, microsecond=0)
        for hora, peso in enumerate(PESO_HORA):
            for _ in range(round(peso * factor * (1 + azar.random() * 2))):
                inicio = dia + timedelta(hours=hora, minutes=azar.randint(0, 50))
                if inicio >= ahora:
                    continue
                app = azar.choices(range(len(APPS)), weights=PESO_APP)[0]
                minimo, maximo = DURACION_SEG[APPS[app]["categoria"]]
                fin = min(inicio + timedelta(seconds=azar.randint(minimo, maximo)), ahora)
                if fin > inicio:
                    eventos.append({"app_numero": app + 1, "inicio": inicio.isoformat(timespec="seconds"),
                                    "fin": fin.isoformat(timespec="seconds")})
    return eventos


def subir_eventos(api: Api, eventos: list) -> None:
    for i, evento in enumerate(eventos, 1):
        api.pedir("POST", "/eventos", evento)
        if i % 50 == 0 or i == len(eventos):
            print(f"Eventos: {i}/{len(eventos)}")


def subir_pausas_de_hoy(api: Api, azar: random.Random, eventos: list) -> None:
    """La API pone la fecha de la pausa al registrarla, así que todas quedan con fecha de hoy."""
    pausas = 0
    for evento in eventos[-60:]:
        if azar.random() < 0.3:
            tipo = azar.choices(["leve", "media", "alta"], weights=[0.55, 0.3, 0.15])[0]
            ignorada = azar.random() < {"leve": 0.28, "media": 0.19, "alta": 0.11}[tipo]
            api.pedir("POST", "/pausas", {"app_numero": evento["app_numero"], "tipo": tipo,
                                          "duracion_seg": 5 if tipo == "leve" else 15, "ignorada": ignorada})
            pausas += 1
    print(f"Pausas de hoy: {pausas}")


def refrescar(api: Api, args, password: str, azar: random.Random) -> None:
    entrar(api, args.email, password)
    _, apps = api.pedir("GET", "/apps")
    if not apps:
        sys.exit("La cuenta no tiene apps; créala primero sin --refrescar.")
    numeros = {a["numero"] for a in apps}

    # Eventos: del último registrado hasta ahora (máximo --dias hacia atrás para no tardar)
    ahora = datetime.now().replace(microsecond=0)
    desde = ahora - timedelta(days=args.dias)
    _, existentes = api.pedir("GET", "/eventos?" + urllib.parse.urlencode({"desde": desde.isoformat()}))
    ultimo = max((datetime.fromisoformat(e["inicio"]) for e in existentes), default=desde)
    dias = (ahora.date() - ultimo.date()).days + 1
    eventos = [e for e in generar_eventos(azar, dias, ahora)
               if datetime.fromisoformat(e["inicio"]) > ultimo and e["app_numero"] in numeros]
    if eventos:
        subir_eventos(api, eventos)
    else:
        print("Eventos: ya estaban al día")

    # Pausas: solo si hoy todavía no hay (el servidor guarda su fecha en UTC)
    hoy_utc = datetime.now(timezone.utc).date().isoformat()
    _, pausas = api.pedir("GET", "/pausas")
    if any(p["fecha"].startswith(hoy_utc) for p in pausas):
        print("Pausas: ya hay pausas de hoy")
    else:
        subir_pausas_de_hoy(api, azar, eventos or existentes)

    # Plan: agrega los ajustes de las semanas que ya pasaron, con una adherencia que sigue mejorando
    status, plan = api.pedir("GET", "/planes/activo", esperado=(200, 404))
    if status == 404:
        print("Plan: la cuenta no tiene plan activo; no se modifica")
    else:
        semana_actual = (date.today() - date.fromisoformat(plan["fecha_inicio"])).days // 7 + 1
        _, ajustes = api.pedir("GET", f"/planes/{plan['numero']}/ajustes")
        previo = max(ajustes, key=lambda a: a["semana"], default=None)
        meta = previo["uso_meta"] if previo else plan["limite_base"]
        adherencia = previo["adherencia"] if previo else 0.6
        nuevos = 0
        for semana in range((previo["semana"] if previo else 0) + 1, semana_actual):
            meta = max(meta - 12, 90)
            adherencia = min(round(adherencia + azar.uniform(0.02, 0.06), 2), 0.97)
            api.pedir("POST", f"/planes/{plan['numero']}/ajustes",
                      {"semana": semana, "uso_meta": meta, "adherencia": adherencia})
            nuevos += 1
        if semana_actual > plan["semana_actual"]:
            api.pedir("PUT", f"/planes/{plan['numero']}", {"semana_actual": semana_actual})
        print(f"Plan: semana {max(semana_actual, plan['semana_actual'])}, {nuevos} ajuste(s) nuevo(s)")

    # Una sesión de foco completada hoy, para que la actividad reciente no se vea vacía
    _, sesion = api.pedir("POST", "/sesiones-foco", {"duracion_min": 25})
    api.pedir("PUT", f"/sesiones-foco/{sesion['numero']}", {"completada": True})
    print("Sesión de foco de hoy: 1")


def crear(api: Api, args, password: str, azar: random.Random) -> None:
    iniciar_sesion(api, args.email, args.nombre, password)

    for app in APPS:
        api.pedir("POST", "/apps", app)
    print(f"Apps: {len(APPS)}")

    eventos = generar_eventos(azar, args.dias, datetime.now().replace(microsecond=0))
    subir_eventos(api, eventos)
    subir_pausas_de_hoy(api, azar, eventos)

    # Plan de 4 semanas con 3 ajustes; el cambio_pct lo calcula el servidor con sus reglas difusas
    inicio_plan = date.today() - timedelta(days=21)
    _, plan = api.pedir("POST", "/planes", {"fecha_inicio": inicio_plan.isoformat(), "limite_base": 240})
    for semana, (meta, adherencia) in enumerate([(240, 0.62), (228, 0.74), (216, 0.86)], 1):
        api.pedir("POST", f"/planes/{plan['numero']}/ajustes",
                  {"semana": semana, "uso_meta": meta, "adherencia": adherencia})
    api.pedir("PUT", f"/planes/{plan['numero']}", {"semana_actual": 4})
    print("Plan: 240 min/día, semana 4, 3 ajustes")

    api.pedir("POST", "/tokens-dispositivo",
              {"token": f"fcm-demo-{args.email}-{azar.randrange(16**12):012x}", "plataforma": "android"})
    for duracion, completada in [(25, True), (50, True), (25, False)]:
        _, sesion = api.pedir("POST", "/sesiones-foco", {"duracion_min": duracion})
        if completada:
            api.pedir("PUT", f"/sesiones-foco/{sesion['numero']}", {"completada": True})
    for dominio in ["tiktok.com", "instagram.com", "youtube.com"]:
        api.pedir("POST", "/dominios", {"dominio": dominio})
    print("Dispositivo, 3 sesiones de foco y 3 dominios bloqueados")


def main():
    p = argparse.ArgumentParser(description="Crea (o refresca) una cuenta de Focus! con datos de ejemplo")
    p.add_argument("--api", required=True, help="URL de la API, p. ej. https://focus-api-<sufijo>.azurewebsites.net")
    p.add_argument("--email", required=True)
    p.add_argument("--nombre", default="Cuenta Demo")
    p.add_argument("--dias", type=int, default=14, help="días de eventos de uso (default 14)")
    p.add_argument("--semilla", type=int, default=42)
    p.add_argument("--refrescar", action="store_true",
                   help="no crea la cuenta: rellena la existente hasta hoy (eventos, pausas y semanas del plan)")
    args = p.parse_args()

    password = os.environ.get("FOCUS_DEMO_PASSWORD") or getpass.getpass("Contraseña de la cuenta demo: ")
    if len(password) < 6:
        sys.exit("La contraseña debe tener al menos 6 caracteres.")

    # Al refrescar se cambia la semilla para no repetir los mismos eventos de la creación
    azar = random.Random(args.semilla + (date.today().toordinal() if args.refrescar else 0))
    api = Api(args.api)
    print(f"API: {api.base}")
    api.pedir("GET", "/salud")   # despierta la base serverless antes de empezar
    (refrescar if args.refrescar else crear)(api, args, password, azar)

    print(f"\nListo. Inicia sesión en el portal con {args.email} y la contraseña que escribiste.")


if __name__ == "__main__":
    main()
