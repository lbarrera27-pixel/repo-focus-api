// Convierte los datos crudos de la API en lo que muestra cada tarjeta del Panel General.
import { api } from '../api.js'

export const PERIODOS = [
  { id: 'hoy', etiqueta: 'Hoy', dias: 1 },
  { id: '7d', etiqueta: '7D', dias: 7 },
  { id: '30d', etiqueta: '30D', dias: 30 },
  { id: 'semestre', etiqueta: 'Semestre Piloto', dias: 120 },
]

const DIA_MS = 86_400_000
const DIAS_SEMANA = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb']

export const fechaISO = (d) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

function rango(periodoId, hoy = new Date()) {
  const { dias } = PERIODOS.find((p) => p.id === periodoId) ?? PERIODOS[1]
  const desde = new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate() - (dias - 1))
  return { desde: fechaISO(desde), hasta: fechaISO(hoy) }
}

// ---------- Carga ----------

export async function cargarPanel(usuarioId, periodoId) {
  const { desde, hasta } = rango(periodoId)
  // La gráfica semanal siempre necesita los últimos 7 días aunque el periodo sea "Hoy"
  const desdeEventos = periodoId === 'hoy' ? rango('7d').desde : desde
  const [estadisticas, eventos, apps, pausas, tokens, plan] = await Promise.all([
    api.estadisticas(usuarioId, desde, hasta),
    api.eventos(usuarioId, `${desdeEventos}T00:00:00`, `${hasta}T23:59:59`),
    api.apps(usuarioId),
    api.pausas(usuarioId),
    api.tokens(usuarioId),
    api.planActivo(usuarioId),
  ])
  const ajustes = plan ? await api.ajustes(usuarioId, plan.numero).catch(() => []) : []
  return { periodo: periodoId, desde, hasta, estadisticas, eventos, apps, pausas, tokens, plan, ajustes }
}

// ---------- Cálculos por tarjeta ----------

const minutos = (seg) => seg / 60
const enRango = (fecha, desde, hasta) => {
  const d = fechaISO(fecha instanceof Date ? fecha : new Date(fecha))
  return d >= desde && d <= hasta
}

// Las fechas que pone el servidor (pausa.fecha, token.fecha_registro) se guardan en UTC sin zona
// (ver app/models/_comun.py), así que se interpretan como UTC.
export const fechaServidor = (iso) => new Date(/([zZ]|[+-]\d\d:\d\d)$/.test(iso) ? iso : `${iso}Z`)

export function formatoDuracion(min) {
  const h = Math.floor(min / 60)
  const m = Math.round(min % 60)
  return h ? `${h}h ${String(m).padStart(2, '0')}m` : `${m}m`
}

export function haceCuanto(fecha, ahora = Date.now()) {
  if (!fecha) return 'Sin datos'
  const min = Math.round((ahora - new Date(fecha).getTime()) / 60000)
  if (min < 1) return 'Ahora'
  if (min < 60) return `Hace ${min} min`
  const h = Math.round(min / 60)
  if (h < 24) return `Hace ${h} h`
  return `Hace ${Math.round(h / 24)} d`
}

function telemetria({ tokens, eventos, estadisticas }) {
  const activos = tokens.filter((t) => t.activo)
  const android = activos.find((t) => t.plataforma === 'android') ?? activos[0] ?? null
  const ultimo = eventos.reduce((max, e) => (!max || e.fin > max ? e.fin : max), null)
  const recienteMs = ultimo ? Date.now() - new Date(ultimo).getTime() : Infinity
  return {
    vinculado: Boolean(android),
    dispositivo: android ? `Dispositivo ${android.plataforma === 'android' ? 'Android' : 'Web'} #${android.numero}` : 'Sin dispositivo',
    detalle: android
      ? `Registrado ${fechaServidor(android.fecha_registro).toLocaleDateString('es-MX')} · ${activos.length} activo(s)`
      : 'Registra un token desde la app Android',
    servicioActivo: recienteMs < DIA_MS,
    heartbeat: haceCuanto(ultimo),
    eventos: estadisticas.total_eventos,
    nodos: [
      { titulo: 'Mobile Client', dato: `${activos.length} dispositivo(s)` },
      { titulo: 'Cloud Ingestion', dato: `${estadisticas.total_eventos} eventos` },
      { titulo: 'Analytics', dato: `${Math.round(estadisticas.minutos_uso)} min de uso` },
    ],
  }
}

// Colores de los clústeres en el orden del diseño (A ámbar, B rojo, C verde)
export const COLORES_CLUSTER = ['#f59e0b', '#ef4444', '#10b981']

function clusteres({ eventos, apps, desde, hasta }) {
  const delPeriodo = eventos.filter((e) => enRango(e.inicio, desde, hasta))
  const categoria = (n) => apps.find((a) => a.numero === n)?.categoria || 'sin categoría'
  const nombre = (n) => apps.find((a) => a.numero === n)?.nombre || `App ${n}`

  // Cada punto es una app en un día: aperturas de ese día y duración media de sus sesiones
  const porAppDia = new Map()
  for (const e of delPeriodo) {
    const clave = `${e.app_numero}|${fechaISO(new Date(e.inicio))}`
    const a = porAppDia.get(clave) ?? { app_numero: e.app_numero, dia: clave.split('|')[1], aperturas: 0, segundos: 0 }
    a.aperturas += 1
    a.segundos += e.duracion_seg
    porAppDia.set(clave, a)
  }

  // Un clúster por categoría (las 3 con más aperturas)
  const totales = new Map()
  for (const a of porAppDia.values()) totales.set(categoria(a.app_numero), (totales.get(categoria(a.app_numero)) ?? 0) + a.aperturas)
  const top = [...totales.entries()].sort((a, b) => b[1] - a[1]).slice(0, 3)
  const total = delPeriodo.length || 1

  const grupos = top.map(([cat, aperturas], i) => ({
    letra: String.fromCharCode(65 + i),
    nombre: cat.charAt(0).toUpperCase() + cat.slice(1),
    porcentaje: Math.round((aperturas / total) * 100),
    color: COLORES_CLUSTER[i],
  }))
  const puntos = [...porAppDia.values()]
    .map((a) => ({
      id: `${a.app_numero}|${a.dia}`,
      app: `${nombre(a.app_numero)} · ${a.dia}`,
      aperturas: a.aperturas,
      duracionMedia: minutos(a.segundos) / a.aperturas,
      grupo: top.findIndex(([cat]) => cat === categoria(a.app_numero)),
    }))
    .filter((p) => p.grupo >= 0)
  return { total: delPeriodo.length, grupos, puntos }
}

// Escala de color del mapa de riesgo (de BAJO a ALTO, como el diseño)
const NIVELES_RIESGO = [
  { hasta: 20, fondo: '#f1f5f9', texto: '#475569' },
  { hasta: 40, fondo: '#fef3c7', texto: '#854d0e' },
  { hasta: 60, fondo: '#fed7aa', texto: '#9a3412' },
  { hasta: 80, fondo: '#fb923c', texto: '#ffffff' },
  { hasta: 101, fondo: '#c2410c', texto: '#ffffff' },
]
export const nivelRiesgo = (valor) => NIVELES_RIESGO.find((n) => valor < n.hasta)

function riesgo({ eventos, desde, hasta }) {
  const porHora = Array(24).fill(0)
  for (const e of eventos) if (enRango(e.inicio, desde, hasta)) porHora[new Date(e.inicio).getHours()] += e.duracion_seg
  const max = Math.max(...porHora)
  const valores = porHora.map((s) => (max ? Math.round((s / max) * 100) : 0))

  // Ventana de 2 h con más uso
  let inicio = 0
  for (let h = 0; h < 24; h++) if (valores[h] + valores[(h + 1) % 24] > valores[inicio] + valores[(inicio + 1) % 24]) inicio = h
  // Grado de pertenencia al conjunto "riesgo alto": promedio normalizado de la ventana
  const pico = (valores[inicio] + valores[(inicio + 1) % 24]) / 2
  const hh = (h) => `${String(h % 24).padStart(2, '0')}:00`
  const nivel = pico >= 80 ? 3 : pico >= 50 ? 2 : 1
  const etiquetaNivel = ['Low', 'Medium', 'High'][nivel - 1]
  const conDatos = max > 0
  return {
    valores,
    conDatos,
    ventana: conDatos ? `${hh(inicio)}–${hh(inicio + 2)}` : 'Sin datos',
    regla: { hora: hh(inicio + 1), nivel, etiquetaNivel, mu: (pico / 100).toFixed(2) },
    analizados: eventos.filter((e) => enRango(e.inicio, desde, hasta)).length,
  }
}

function semanal({ eventos, plan, ajustes, hasta }) {
  const fin = new Date(`${hasta}T00:00:00`)
  const dias = Array.from({ length: 7 }, (_, i) => new Date(fin.getTime() - (6 - i) * DIA_MS))
  const usoPorDia = new Map(dias.map((d) => [fechaISO(d), 0]))
  for (const e of eventos) {
    const k = fechaISO(new Date(e.inicio))
    if (usoPorDia.has(k)) usoPorDia.set(k, usoPorDia.get(k) + minutos(e.duracion_seg))
  }
  // La meta vigente es la del último ajuste semanal; si no hay, el límite base del plan
  const ultimoAjuste = [...(ajustes ?? [])].sort((a, b) => b.semana - a.semana)[0]
  const objetivo = ultimoAjuste?.uso_meta ?? plan?.limite_base ?? null

  const barras = dias.map((d) => ({ dia: DIAS_SEMANA[d.getDay()], uso: usoPorDia.get(fechaISO(d)), objetivo }))
  const promedio = barras.reduce((s, b) => s + b.uso, 0) / 7
  const diferencia = objetivo ? promedio - objetivo : null
  return {
    barras,
    objetivo,
    cambioPct: objetivo ? ((promedio - objetivo) / objetivo) * 100 : null,
    diferencia,
  }
}

const COLORES_CATEGORIA = ['#f59e0b', '#0f172a', '#10b981']

function uso({ eventos, apps, desde, hasta }) {
  const delPeriodo = eventos.filter((e) => enRango(e.inicio, desde, hasta))
  const totalSeg = delPeriodo.reduce((s, e) => s + e.duracion_seg, 0)
  const porCat = new Map()
  for (const e of delPeriodo) {
    const cat = apps.find((a) => a.numero === e.app_numero)?.categoria || 'otros'
    porCat.set(cat, (porCat.get(cat) ?? 0) + e.duracion_seg)
  }
  const categorias = [...porCat.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([cat, seg], i) => ({
      nombre: cat.charAt(0).toUpperCase() + cat.slice(1),
      porcentaje: totalSeg ? Math.round((seg / totalSeg) * 100) : 0,
      color: COLORES_CATEGORIA[i],
    }))

  // Sesiones (eventos) por hora en las 12 horas que terminan en el último evento
  const ultimo = delPeriodo.reduce((max, e) => Math.max(max, new Date(e.inicio).getTime()), 0) || Date.now()
  const finVentana = new Date(ultimo)
  finVentana.setMinutes(0, 0, 0)
  const inicioVentana = finVentana.getTime() - 11 * 3_600_000
  const frecuencia = Array.from({ length: 12 }, (_, i) => ({ hora: new Date(inicioVentana + i * 3_600_000).getHours(), sesiones: 0 }))
  for (const e of delPeriodo) {
    const i = Math.floor((new Date(e.inicio).getTime() - inicioVentana) / 3_600_000)
    if (i >= 0 && i < 12) frecuencia[i].sesiones += 1
  }
  return { totalMin: minutos(totalSeg), categorias, frecuencia }
}

const NIVELES_PAUSA = [
  { tipo: 'leve', nivel: 1, nombre: 'Timer 5s', fondo: '#fef3c7', texto: '#b45309' },
  { tipo: 'media', nivel: 2, nombre: 'Respiración', fondo: '#d1fae5', texto: '#047857' },
  { tipo: 'alta', nivel: 3, nombre: 'Chatbot IA', fondo: '#e0e7ff', texto: '#4338ca' },
]

function friccion({ pausas, desde, hasta }) {
  const delPeriodo = pausas.filter((p) => enRango(fechaServidor(p.fecha), desde, hasta))
  const exito = (lista) => (lista.length ? Math.round((lista.filter((p) => !p.ignorada).length / lista.length) * 100) : 0)
  const niveles = NIVELES_PAUSA.map((n) => {
    const lista = delPeriodo.filter((p) => p.tipo === n.tipo)
    return { ...n, total: lista.length, exito: exito(lista) }
  })
  return { prevenidas: delPeriodo.filter((p) => !p.ignorada).length, total: delPeriodo.length, global: exito(delPeriodo), niveles }
}

export function construirPanel(datos) {
  return {
    eventosTotales: datos.estadisticas.total_eventos,
    telemetria: telemetria(datos),
    clusteres: clusteres(datos),
    riesgo: riesgo(datos),
    semanal: semanal(datos),
    uso: uso(datos),
    friccion: friccion(datos),
  }
}
