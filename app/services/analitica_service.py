"""
Analítica de uso para el portal: tiempo por app, por categoría, por día y mapa de calor.

Se calcula al vuelo desde evento_uso. Un evento que cruza de hora (o de día) se reparte
entre las horas que toca, así el mapa de calor y los totales cuadran entre sí.
Las horas están en UTC hasta que el usuario tenga zona horaria.
"""
from collections import defaultdict
from datetime import date, datetime, time, timedelta

from app.models._comun import ahora
from app.repositories.ajuste_repository import AjusteRepository
from app.repositories.app_repository import AppRepository
from app.repositories.evento_repository import EventoRepository
from app.repositories.plan_repository import PlanRepository
from app.utils.errores import DatosInvalidos
from app.utils.reglas_plan import limite_vigente

DIAS_POR_DEFECTO = 7
DIAS_MAXIMOS = 366
DIAS = ["lun", "mar", "mie", "jue", "vie", "sab", "dom"]
SIN_CATEGORIA = "sin_categoria"


def rango(desde: date | None, hasta: date | None) -> tuple[date, date]:
    """[desde, hasta] inclusivo; por defecto los últimos 7 días contando hoy."""
    hasta = hasta or ahora().date()
    desde = desde or hasta - timedelta(days=DIAS_POR_DEFECTO - 1)
    if desde > hasta:
        raise DatosInvalidos("'desde' no puede ser posterior a 'hasta'")
    if (hasta - desde).days >= DIAS_MAXIMOS:
        raise DatosInvalidos(f"El rango no puede pasar de {DIAS_MAXIMOS} días")
    return desde, hasta


def trozos_por_hora(inicio: datetime, fin: datetime, desde: datetime, hasta: datetime):
    """(hora en punto, segundos) de la parte del intervalo [inicio, fin) que cae en [desde, hasta)."""
    actual, fin = max(inicio, desde), min(fin, hasta)
    while actual < fin:
        hora = actual.replace(minute=0, second=0, microsecond=0)
        corte = min(hora + timedelta(hours=1), fin)
        yield hora, (corte - actual).total_seconds()
        actual = corte


def _minutos(segundos: float) -> float:
    return round(segundos / 60, 1)


def _pct(parte: float, total: float) -> float:
    return round(100 * parte / total, 1) if total else 0.0


class AnaliticaService:
    def __init__(self, db):
        self.apps = AppRepository(db)
        self.eventos = EventoRepository(db)
        self.planes = PlanRepository(db)
        self.ajustes = AjusteRepository(db)

    def _segundos_por_hora(self, usuario_id: int, desde: date, hasta: date) -> list[tuple[datetime, int, float]]:
        """(hora, app_id, segundos) de todo el uso entre los dos días (inclusivos)."""
        inicio = datetime.combine(desde, time.min)
        fin = datetime.combine(hasta + timedelta(days=1), time.min)
        # Un día antes para no perder los eventos que empezaron antes y terminan dentro del rango
        eventos = self.eventos.listar_filtrado(usuario_id, None, None, inicio - timedelta(days=1), fin)
        return [(hora, e.app_id, seg) for e in eventos for hora, seg in trozos_por_hora(e.inicio, e.fin, inicio, fin)]

    def _por_app(self, usuario_id: int, desde: date, hasta: date) -> dict[int, float]:
        segundos = defaultdict(float)
        for _, app_id, seg in self._segundos_por_hora(usuario_id, desde, hasta):
            segundos[app_id] += seg
        return segundos

    def uso_por_app(self, usuario_id: int, desde: date | None, hasta: date | None, limite: int | None) -> dict:
        desde, hasta = rango(desde, hasta)
        actual = self._por_app(usuario_id, desde, hasta)
        dias = (hasta - desde).days + 1
        anterior = self._por_app(usuario_id, desde - timedelta(days=dias), desde - timedelta(days=1))
        apps = {a.id: a for a in self.apps.listar(usuario_id)}
        filas = [
            {
                "app_numero": apps[app_id].numero,
                "nombre": apps[app_id].nombre,
                "paquete": apps[app_id].paquete,
                "categoria": apps[app_id].categoria or SIN_CATEGORIA,
                "min": _minutos(seg),
                # % contra el mismo número de días justo antes; None si entonces no se usó
                "variacion_pct": _pct(seg - anterior[app_id], anterior[app_id]) if anterior.get(app_id) else None,
            }
            for app_id, seg in actual.items() if app_id in apps
        ]
        filas.sort(key=lambda f: f["min"], reverse=True)
        return {"desde": desde, "hasta": hasta, "total_min": _minutos(sum(actual.values())),
                "apps": filas[:limite] if limite else filas}

    def uso_por_categoria(self, usuario_id: int, desde: date | None, hasta: date | None) -> dict:
        desde, hasta = rango(desde, hasta)
        apps = {a.id: a for a in self.apps.listar(usuario_id)}
        segundos = defaultdict(float)
        for app_id, seg in self._por_app(usuario_id, desde, hasta).items():
            app = apps.get(app_id)
            segundos[(app.categoria if app else None) or SIN_CATEGORIA] += seg
        total = sum(segundos.values())
        categorias = sorted(
            ({"categoria": c, "min": _minutos(s), "pct": _pct(s, total)} for c, s in segundos.items()),
            key=lambda f: f["min"], reverse=True,
        )
        return {"desde": desde, "hasta": hasta, "total_min": _minutos(total), "categorias": categorias}

    def _limite_del_dia(self, plan, ajustes, dia: date) -> float | None:
        """Límite que regía ese día: el ajuste de la semana n aplica desde la semana n + 1."""
        if plan is None or dia < plan.fecha_inicio:
            return None
        semana = (dia - plan.fecha_inicio).days // 7 + 1
        return round(limite_vigente(plan, [a for a in ajustes if a.semana < semana]), 1)

    def uso_diario(self, usuario_id: int, desde: date | None, hasta: date | None) -> dict:
        desde, hasta = rango(desde, hasta)
        segundos = defaultdict(float)
        for hora, _, seg in self._segundos_por_hora(usuario_id, desde, hasta):
            segundos[hora.date()] += seg
        plan = self.planes.activo(usuario_id)
        ajustes = self.ajustes.listar(plan) if plan else []
        hoy = ahora().date()
        dias = []
        for i in range((hasta - desde).days + 1):
            dia = desde + timedelta(days=i)
            uso = _minutos(segundos.get(dia, 0.0))   # .get: leer no debe crear el día en el defaultdict
            limite = self._limite_del_dia(plan, ajustes, dia)
            dias.append({
                "fecha": dia,
                "uso_min": uso,
                "con_datos": dia in segundos,
                "limite_min": limite,
                # Solo se juzga un día que ya pasó o es hoy y que tiene plan
                "cumplio": uso <= limite if limite is not None and dia <= hoy else None,
            })
        con_datos = [d for d in dias if d["con_datos"]]
        juzgados = [d for d in dias if d["cumplio"] is not None and d["con_datos"]]
        return {
            "desde": desde, "hasta": hasta, "dias": dias,
            "promedio_min": round(sum(d["uso_min"] for d in con_datos) / len(con_datos), 1) if con_datos else 0.0,
            "dias_con_datos": len(con_datos),
            "dias_cumplidos": sum(1 for d in juzgados if d["cumplio"]),
        }

    def heatmap(self, usuario_id: int, desde: date | None, hasta: date | None) -> dict:
        desde, hasta = rango(desde, hasta)
        celdas = [[0.0] * 24 for _ in DIAS]
        for hora, _, seg in self._segundos_por_hora(usuario_id, desde, hasta):
            celdas[hora.weekday()][hora.hour] += seg / 60
        celdas = [[round(m, 1) for m in fila] for fila in celdas]
        ordenadas = sorted(((m, d, h) for d, fila in enumerate(celdas) for h, m in enumerate(fila) if m > 0),
                           reverse=True)
        top = [{"dia": DIAS[d], "hora": h, "min": m} for m, d, h in ordenadas[:3]]
        return {
            "desde": desde, "hasta": hasta, "dias": DIAS, "horas": list(range(24)), "celdas": celdas,
            "max_min": ordenadas[0][0] if ordenadas else 0.0,
            "pico": top[0] if top else None,
            "top": top,
        }
