// Estado de la sección "Ajustes y Perfil".
// - Lo que tiene endpoint se guarda en la API: límite diario (PUT /planes/{n}) y límite de aperturas
//   de cada app (PUT /apps/{n}).
// - Lo demás (niveles de fricción, modo foco, privacidad…) se guarda como un JSON por usuario en
//   GET/PUT /configuracion/me. localStorage queda como copia de respaldo si la API no responde, y
//   es el único almacenamiento en el modo demo.
import { api } from '../api.js'
import { fechaISO, fechaServidor } from './panel.js'

const DIA_MS = 86_400_000

export const DEFAULTS = {
  niveles: { 1: 5, 2: 9, 3: 15 },
  temporizador: 9,
  ejercicio: 'respiracion',
  modoFoco: { activo: true, dias: [1, 2, 3, 4, 5], inicio: '08:00', fin: '14:00' },
  appsInactivas: [],
  categorias: { social: 60, video: 45, juegos: 25, mensajeria: 30 },
  reduccionGradual: true,
  descanso: { activo: true, inicio: '23:00', fin: '07:00' },
  excepciones: [],
  privacidad: { metricas: true, clusteres: true, nocturno: true, resultados: true, errores: false },
  anonimizacion: 'seudonimizado',
  retencion: 90,
  consentimientoRetirado: false,
}

const clave = (usuarioId) => `focus.ajustes.${usuarioId}`

const conDefaults = (guardado) => ({ ...structuredClone(DEFAULTS), ...guardado })

// Copia del navegador: se muestra al abrir la sección mientras responde la API
export function leerLocales(usuarioId) {
  try {
    const guardado = JSON.parse(localStorage.getItem(clave(usuarioId)))
    return guardado ? conDefaults(guardado) : structuredClone(DEFAULTS)
  } catch {
    return structuredClone(DEFAULTS)
  }
}

function guardarEnNavegador(usuarioId, locales) {
  try {
    localStorage.setItem(clave(usuarioId), JSON.stringify(locales))
  } catch {
    // Sin almacenamiento (modo privado): la copia del navegador no se conserva
  }
}

// Ajustes guardados en la API, o null si no responde (se sigue con la copia del navegador).
// Si el usuario nunca ha guardado en la API se usa la copia del navegador, que se sube al guardar.
export async function cargarLocales(usuario) {
  if (usuario.demo) return null
  try {
    const remotos = await api.configuracion(usuario.id)
    if (!remotos || Object.keys(remotos).length === 0) return leerLocales(usuario.id)
    const locales = conDefaults(remotos)
    guardarEnNavegador(usuario.id, locales)
    return locales
  } catch {
    return null
  }
}

// En la demo solo se guarda en el navegador; si no, en la API y una copia en el navegador
export async function guardarLocales(usuario, locales) {
  if (!usuario.demo) await api.guardarConfiguracion(usuario.id, locales)
  guardarEnNavegador(usuario.id, locales)
}

// ---------- Utilidades de datos ----------

export const GRUPO_CATEGORIA = (cat = '') => {
  const c = cat.toLowerCase()
  if (/social|redes/.test(c)) return 'social'
  if (/video|stream/.test(c)) return 'video'
  if (/gam|jueg/.test(c)) return 'juegos'
  if (/mens|chat|whats/.test(c)) return 'mensajeria'
  return null
}

export const NOMBRE_CATEGORIA = { social: 'Redes sociales', video: 'Video', juegos: 'Juegos', mensajeria: 'Mensajería' }

export const etiquetaCategoria = (cat) => NOMBRE_CATEGORIA[GRUPO_CATEGORIA(cat)] ?? (cat ? cat.charAt(0).toUpperCase() + cat.slice(1) : 'Sin categoría')

const NIVEL_TIPO = { leve: 1, media: 2, alta: 3 }

export function resumenApps(datos, ahora = new Date()) {
  const hoy = fechaISO(ahora)
  const hace7 = fechaISO(new Date(ahora.getTime() - 6 * DIA_MS))
  return datos.apps.map((app) => {
    const eventosHoy = datos.eventos.filter((e) => e.app_numero === app.numero && fechaISO(new Date(e.inicio)) === hoy)
    const pausas7 = datos.pausas.filter((p) => p.app_numero === app.numero && fechaISO(fechaServidor(p.fecha)) >= hace7)
    // Nivel de fricción que más se le ha aplicado a la app en la semana
    const conteo = [0, 0, 0, 0]
    for (const p of pausas7) conteo[NIVEL_TIPO[p.tipo] ?? 1] += 1
    const nivel = conteo.some((c) => c > 0) ? conteo.indexOf(Math.max(...conteo)) : null
    return {
      ...app,
      grupo: GRUPO_CATEGORIA(app.categoria),
      aperturasHoy: eventosHoy.length,
      minutosHoy: Math.round(eventosHoy.reduce((s, e) => s + e.duracion_seg, 0) / 60),
      pausas7: pausas7.length,
      nivel,
    }
  })
}

export function pausasDeHoy(datos, ahora = new Date()) {
  const hoy = fechaISO(ahora)
  const lista = datos.pausas.filter((p) => fechaISO(fechaServidor(p.fecha)) === hoy)
  return { total: lista.length, abandonaron: lista.filter((p) => !p.ignorada).length, continuaron: lista.filter((p) => p.ignorada).length }
}

export function usoPorDiaSemana(datos, ahora = new Date()) {
  // Semana de lunes a domingo que contiene hoy
  const lunes = new Date(ahora.getFullYear(), ahora.getMonth(), ahora.getDate() - ((ahora.getDay() + 6) % 7))
  return ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'].map((dia, i) => {
    const d = fechaISO(new Date(lunes.getTime() + i * DIA_MS))
    const min = datos.eventos.filter((e) => fechaISO(new Date(e.inicio)) === d).reduce((s, e) => s + e.duracion_seg, 0) / 60
    return { dia, fecha: d, minutos: Math.round(min), esHoy: d === fechaISO(ahora), futuro: d > fechaISO(ahora) }
  })
}

export function usoHoyPorGrupo(datos, ahora = new Date()) {
  const hoy = fechaISO(ahora)
  const uso = { social: 0, video: 0, juegos: 0, mensajeria: 0 }
  for (const e of datos.eventos) {
    if (fechaISO(new Date(e.inicio)) !== hoy) continue
    const g = GRUPO_CATEGORIA(datos.apps.find((a) => a.numero === e.app_numero)?.categoria)
    if (g) uso[g] += e.duracion_seg / 60
  }
  return Object.fromEntries(Object.entries(uso).map(([k, v]) => [k, Math.round(v)]))
}

// Nivel sugerido por semana a partir de los ajustes difusos guardados en la API
export function progresionSemanal(ajustes = []) {
  const orden = [...ajustes].sort((a, b) => a.semana - b.semana).slice(-4)
  return orden.map((a) => ({
    semana: a.semana,
    nivel: a.adherencia >= 0.85 ? 1 : a.adherencia >= 0.65 ? 2 : 3,
    adherencia: a.adherencia,
    cambio: a.cambio_pct,
  }))
}

export function proximoAjuste(plan, ahora = new Date()) {
  if (!plan) return null
  const inicio = new Date(`${plan.fecha_inicio}T00:00:00`)
  const semanas = Math.floor((ahora - inicio) / (7 * DIA_MS)) + 1
  return new Date(inicio.getTime() + semanas * 7 * DIA_MS)
}

export function formatoMin(min) {
  const h = Math.floor(min / 60)
  const m = Math.round(min % 60)
  return h ? `${h} h ${String(m).padStart(2, '0')} min` : `${m} min`
}

export function csvDeDatos(datos) {
  const esc = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`
  const nombre = (n) => datos.apps.find((a) => a.numero === n)?.nombre ?? ''
  const filas = [
    ['tipo', 'numero', 'app', 'inicio', 'fin', 'duracion_seg', 'detalle'],
    ...datos.eventos.map((e) => ['evento', e.numero, nombre(e.app_numero), e.inicio, e.fin, e.duracion_seg, '']),
    ...datos.pausas.map((p) => ['pausa', p.numero, nombre(p.app_numero), p.fecha, '', p.duracion_seg, `${p.tipo}${p.ignorada ? ' (ignorada)' : ''}`]),
    ...datos.apps.map((a) => ['app', a.numero, a.nombre, '', '', '', `${a.paquete} · ${a.categoria ?? ''} · límite ${a.limite_aperturas}`]),
  ]
  return filas.map((f) => f.map(esc).join(',')).join('\n')
}
