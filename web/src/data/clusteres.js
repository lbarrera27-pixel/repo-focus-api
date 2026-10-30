// Sección "Clústeres Big Data": K-Means (k = 3) sobre los días del usuario.
// La API solo expone los datos del usuario autenticado, así que cada punto es un día suyo:
//   x = aperturas (eventos) del día, y = % del tiempo de uso que fue nocturno (20:00–02:00).
// Ambas variables se estandarizan (z-score) y se escalan a ±50 como en el diseño.
import { fechaISO } from './panel.js'
import { construirAnalisis } from './analisis.js'

const DIA_MS = 86_400_000
const ES_NOCHE = (h) => h >= 20 || h < 2

export const ARQUETIPOS = [
  { letra: 'A', nombre: 'Nocturnos / Compulsivos', corto: 'Nocturno / Compulsivo', color: '#f59e0b' },
  { letra: 'B', nombre: 'Aperturas Rápidas y Esporádicas', corto: 'Aperturas rápidas', color: '#38bdf8' },
  { letra: 'C', nombre: 'Enfoque Sostenido / Baja Dependencia', corto: 'Enfoque sostenido', color: '#10b981' },
]

// Generador determinista para que los centros iniciales no cambien entre renders
function aleatorio(semilla) {
  let s = semilla
  return () => {
    s = (s * 1664525 + 1013904223) % 4294967296
    return s / 4294967296
  }
}

const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y)

function kmeans(puntos, k) {
  const r = aleatorio(7)
  // k-means++: el primer centro al azar y los demás lejos de los ya elegidos
  const centros = [puntos[Math.floor(r() * puntos.length)]]
  while (centros.length < k) {
    const d2 = puntos.map((p) => Math.min(...centros.map((c) => dist(p, c) ** 2)))
    const total = d2.reduce((s, x) => s + x, 0)
    let t = r() * total
    let i = 0
    while (i < puntos.length - 1 && t > d2[i]) t -= d2[i++]
    centros.push(puntos[i])
  }
  let c = centros.map((p) => ({ x: p.x, y: p.y }))
  let asign = []
  for (let iter = 0; iter < 50; iter++) {
    asign = puntos.map((p) => c.reduce((mejor, cc, j) => (dist(p, cc) < dist(p, c[mejor]) ? j : mejor), 0))
    const nuevos = c.map((cc, j) => {
      const miembros = puntos.filter((_, i) => asign[i] === j)
      return miembros.length
        ? { x: miembros.reduce((s, p) => s + p.x, 0) / miembros.length, y: miembros.reduce((s, p) => s + p.y, 0) / miembros.length }
        : cc
    })
    const movimiento = nuevos.reduce((s, n, j) => s + dist(n, c[j]), 0)
    c = nuevos
    if (movimiento < 1e-6) break
  }
  return { centros: c, asign }
}

function silhouette(puntos, asign, k) {
  const s = puntos.map((p, i) => {
    const promedio = (j) => {
      const otros = puntos.filter((q, m) => asign[m] === j && m !== i)
      return otros.length ? otros.reduce((t, q) => t + dist(p, q), 0) / otros.length : 0
    }
    const a = promedio(asign[i])
    const b = Math.min(...Array.from({ length: k }, (_, j) => j).filter((j) => j !== asign[i] && asign.includes(j)).map(promedio))
    return Number.isFinite(b) && Math.max(a, b) > 0 ? (b - a) / Math.max(a, b) : 0
  })
  return s.reduce((t, x) => t + x, 0) / s.length
}

export function construirClusteres(datos, ahora = new Date()) {
  const { eventos, apps, plan, ajustes, pausas } = datos

  // ---------- Un punto por día con actividad ----------
  const porDia = new Map()
  for (const e of eventos) {
    const d = new Date(e.inicio)
    const k = fechaISO(d)
    const v = porDia.get(k) ?? { dia: k, aperturas: 0, seg: 0, segNoche: 0 }
    v.aperturas += 1
    v.seg += e.duracion_seg
    if (ES_NOCHE(d.getHours())) v.segNoche += e.duracion_seg
    porDia.set(k, v)
  }
  const dias = [...porDia.values()].sort((a, b) => a.dia.localeCompare(b.dia))
  const crudos = dias.map((d) => ({ ...d, nocturno: d.seg ? (d.segNoche / d.seg) * 100 : 0 }))

  // Estandarización (z-score) escalada a ±50; se guarda la función para proyectar el perfil
  const escala = (vals) => {
    const m = vals.reduce((s, x) => s + x, 0) / (vals.length || 1)
    const sd = Math.sqrt(vals.reduce((s, x) => s + (x - m) ** 2, 0) / (vals.length || 1)) || 1
    return (v) => Math.max(-48, Math.min(48, ((v - m) / sd) * 18))
  }
  const fx = escala(crudos.map((d) => d.aperturas))
  const fy = escala(crudos.map((d) => d.nocturno))
  const puntos = crudos.map((d) => ({ ...d, x: fx(d.aperturas), y: fy(d.nocturno) }))

  const k = Math.min(3, puntos.length)
  const suficiente = puntos.length >= 6
  let grupos = []
  let asignacion = []
  let sil = null
  if (suficiente) {
    const { centros, asign } = kmeans(puntos, k)
    // Ordena los clústeres: más aperturas + más uso nocturno = arquetipo A
    const orden = centros.map((c, j) => ({ c, j })).sort((a, b) => b.c.x + b.c.y - (a.c.x + a.c.y))
    const mapa = new Map(orden.map((o, nuevo) => [o.j, nuevo]))
    asignacion = asign.map((j) => mapa.get(j))
    grupos = orden.map((o, nuevo) => {
      const miembros = puntos.filter((_, i) => asignacion[i] === nuevo)
      const sd = (eje) => Math.sqrt(miembros.reduce((s, p) => s + (p[eje] - o.c[eje]) ** 2, 0) / (miembros.length || 1))
      return {
        ...ARQUETIPOS[nuevo],
        centro: o.c,
        radio: { x: sd('x') * 1.6 + 8, y: sd('y') * 1.6 + 8 },
        porcentaje: Math.round((miembros.length / puntos.length) * 100),
        miembros: miembros.length,
      }
    })
    sil = silhouette(puntos, asignacion, k)
  }
  const puntosAsignados = puntos.map((p, i) => ({ ...p, grupo: asignacion[i] ?? 0 }))

  // ---------- Perfil: promedio de los últimos 7 días completos (hoy aún no termina) ----------
  const hoy = fechaISO(ahora)
  const perfilDe = (desdeDias, hastaDias) => {
    const a = fechaISO(new Date(ahora.getTime() - desdeDias * DIA_MS))
    const b = fechaISO(new Date(ahora.getTime() - hastaDias * DIA_MS))
    const sel = crudos.filter((d) => d.dia >= a && d.dia <= b && d.dia !== hoy)
    if (!sel.length) return null
    const ap = sel.reduce((s, d) => s + d.aperturas, 0) / sel.length
    const no = sel.reduce((s, d) => s + d.nocturno, 0) / sel.length
    const p = { x: fx(ap), y: fy(no), dias: sel.length }
    p.grupo = grupos.length ? grupos.reduce((m, g, j) => (dist(p, g.centro) < dist(p, grupos[m].centro) ? j : m), 0) : 0
    return p
  }
  const tu = perfilDe(7, 1) ?? perfilDe(400, 0)
  const anterior = perfilDe(14, 8)
  const similitudDe = (p) => {
    if (!p || !grupos.length) return null
    // 100% = justo en el centro del clúster; 0% = tan lejos como el día más alejado de ese centro
    const g = grupos[p.grupo]
    const maxD = Math.max(...puntosAsignados.map((q) => dist(q, g.centro)), 1)
    return Math.max(0, Math.round((1 - dist(p, g.centro) / maxD) * 1000) / 10)
  }
  const similitud = similitudDe(tu)
  const similitudAnt = anterior && anterior.grupo === tu?.grupo ? similitudDe(anterior) : null

  // ---------- Riesgo de abandonar el plan: días por encima del límite ----------
  const ultimoAjuste = [...(ajustes ?? [])].sort((a, b) => b.semana - a.semana)[0]
  const objetivo = ultimoAjuste?.uso_meta ?? plan?.limite_base ?? null
  const sobreLimite = objetivo ? crudos.filter((d) => d.seg / 60 > objetivo).length : 0
  const abandono = objetivo && crudos.length ? Math.round((sobreLimite / crudos.length) * 100) : null
  const nivelAbandono = abandono == null ? 'SIN PLAN' : abandono >= 60 ? 'ALTA' : abandono >= 30 ? 'MODERADA' : 'BAJA'

  // ---------- Rasgos del arquetipo (reutiliza el análisis por hora y por nivel) ----------
  const a = construirAnalisis(datos, ahora)
  const n1 = a.niveles[0]
  const n2 = a.niveles[1]
  const promHora = a.curva.estimado.reduce((s, v) => s + v, 0) / 24 || 1
  const [hIni] = a.franja.texto.split(' — ')
  const hFranja = parseInt(hIni, 10)
  const factorFranja = Number.isFinite(hFranja)
    ? ((a.curva.estimado[hFranja] + a.curva.estimado[(hFranja + 1) % 24]) / 2 / promHora).toFixed(1)
    : null

  // ---------- Recomendaciones aplicables con la API ----------
  const hace7 = fechaISO(new Date(ahora.getTime() - 6 * DIA_MS))
  const enFranja = eventos.filter((e) => {
    const h = new Date(e.inicio).getHours()
    return fechaISO(new Date(e.inicio)) >= hace7 && Number.isFinite(hFranja) && (h === hFranja || h === (hFranja + 1) % 24)
  })
  const aperturasApp = new Map()
  for (const e of enFranja) aperturasApp.set(e.app_numero, (aperturasApp.get(e.app_numero) ?? 0) + 1)
  const [appTop, abrTop] = [...aperturasApp.entries()].sort((x, y) => y[1] - x[1])[0] ?? []
  const app = apps.find((x) => x.numero === appTop)
  const recomendaciones = []
  if (app && app.limite_aperturas > 1) {
    const nuevo = Math.max(1, Math.round(app.limite_aperturas * 0.7))
    recomendaciones.push({
      id: `app-${app.numero}-${nuevo}`,
      icono: 'reloj',
      titulo: `Bajar el límite de ${app.nombre} a ${nuevo} aperturas`,
      detalle: `Es la app más abierta en tu franja vulnerable (${a.franja.texto}); hoy su límite es ${app.limite_aperturas}.`,
      impacto: `Cubre ${Math.round((abrTop / enFranja.length) * 100)}%`,
      accion: { tipo: 'app', numero: app.numero, cambios: { limite_aperturas: nuevo } },
    })
  }
  if (plan && a.difuso) {
    const semana = Math.max(1, Math.floor((ahora - new Date(`${plan.fecha_inicio}T00:00:00`)) / (7 * DIA_MS)) + 1)
    const registrada = (ajustes ?? []).some((x) => x.semana === semana)
    recomendaciones.push({
      id: `ajuste-${semana}`,
      icono: 'escudo',
      titulo: `Registrar el ajuste difuso de la semana ${semana}`,
      detalle: `Adherencia ${Math.round(a.difuso.adherencia * 100)}% → el servidor calcula el nuevo límite con sus reglas Mamdani.`,
      impacto: `Límite ${a.difuso.cambio > 0 ? '+' : ''}${a.difuso.cambio}%`,
      registrada,
      accion: {
        tipo: 'ajuste',
        numero: plan.numero,
        cuerpo: { semana, uso_meta: Math.round(a.difuso.objetivo), adherencia: Math.round(a.difuso.adherencia * 1000) / 1000 },
      },
    })
  }

  return {
    suficiente,
    k,
    silhouette: sil,
    puntos: puntosAsignados,
    grupos,
    tu,
    similitud,
    deltaSimilitud: similitud != null && similitudAnt != null ? Math.round((similitud - similitudAnt) * 10) / 10 : null,
    dias: crudos.length,
    eventos: eventos.length,
    aperturasRecientes: crudos.slice(-9).map((d) => d.aperturas),
    abandono,
    nivelAbandono,
    rasgos: {
      franja: a.franja.texto,
      factorFranja,
      nivelFranja: a.gauge.nivel,
      n1: n1.abandono,
      n2: n2.abandono,
      global: a.efectividad.valor,
    },
    recomendaciones,
    pausas: pausas.length,
  }
}
