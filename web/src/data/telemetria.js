// Datos de la sección Telemetría Cloud: dispositivo vinculado, estado de la API y bitácora de eventos.
import { api } from '../api.js'
import { datosDemo } from './demo.js'
import { fechaISO, fechaServidor, haceCuanto } from './panel.js'

const DIA_MS = 86_400_000

export async function cargarTelemetria(usuario) {
  const hoy = new Date()
  const desde = fechaISO(new Date(hoy.getTime() - 6 * DIA_MS))
  if (usuario.demo) {
    const d = datosDemo('7d')
    return { ...d, salud: { status: 'ok', base_datos: 'ok', motor: 'demo', latenciaMs: 0 }, apiBase: 'modo demo', cargado: Date.now() }
  }
  const id = usuario.id
  const [salud, eventos, apps, pausas, tokens, plan] = await Promise.all([
    api.salud().catch(() => ({ status: 'error', base_datos: 'error', motor: '—', latenciaMs: null })),
    api.eventos(id, `${desde}T00:00:00`, `${fechaISO(hoy)}T23:59:59`),
    api.apps(id),
    api.pausas(id),
    api.tokens(id),
    api.planActivo(id),
  ])
  return { salud, eventos, apps, pausas, tokens, plan, apiBase: api.base, cargado: Date.now() }
}

const formatoHora = (d) =>
  `${d.toLocaleTimeString('es-MX', { hour12: false })}.${String(d.getMilliseconds()).padStart(3, '0')}`

function formatoSeg(seg) {
  const m = Math.floor(seg / 60)
  const s = seg % 60
  return m ? `${m}m ${String(s).padStart(2, '0')}s` : `${s}s`
}

export function construirTelemetria(datos, ahora = Date.now()) {
  const { eventos, apps, pausas, tokens, plan, salud } = datos
  const hoy = fechaISO(new Date(ahora))
  const app = (n) => apps.find((a) => a.numero === n)

  // ---------- Dispositivo ----------
  const activos = tokens.filter((t) => t.activo)
  const principal = activos.find((t) => t.plataforma === 'android') ?? activos[0] ?? null
  const ultimo = eventos.reduce((max, e) => (!max || e.fin > max ? e.fin : max), null)
  const vivo = ultimo && ahora - new Date(ultimo).getTime() < DIA_MS

  const eventosHoy = eventos.filter((e) => fechaISO(new Date(e.inicio)) === hoy)
  const minutosHoy = eventosHoy.reduce((s, e) => s + e.duracion_seg, 0) / 60
  const limite = plan?.limite_base ?? null
  const usoPct = limite ? Math.round((minutosHoy / limite) * 100) : null

  const dispositivo = {
    principal: principal
      ? {
          nombre: `Dispositivo ${principal.plataforma === 'android' ? 'Android' : 'Web'} #${principal.numero}`,
          detalle: `Token ${principal.token.slice(0, 14)}… · desde ${fechaServidor(principal.fecha_registro).toLocaleDateString('es-MX')}`,
        }
      : null,
    vivo,
    uso: { minutos: Math.round(minutosHoy), limite, pct: usoPct },
    heartbeat: haceCuanto(ultimo, ahora),
    api: { ok: salud.status === 'ok' && salud.base_datos === 'ok', motor: salud.motor, base: datos.apiBase },
    tokens: tokens.slice(0, 3).map((t) => ({ nombre: `${t.plataforma === 'android' ? 'Android' : 'Web'} #${t.numero}`, activo: t.activo })),
    tokensActivos: activos.length,
    tokensTotal: tokens.length,
  }

  // ---------- Pipeline ----------
  const horasHoy = Math.max(1, new Date(ahora).getHours() + new Date(ahora).getMinutes() / 60)
  const pipeline = {
    eventosHoy: eventosHoy.length,
    latenciaMs: salud.latenciaMs,
    porHora: (eventosHoy.length / horasHoy).toFixed(1),
    apps: apps.length,
    motor: salud.motor,
  }

  // ---------- Bitácora: últimos eventos y pausas, del más reciente al más viejo ----------
  const registros = [
    ...eventos.map((e) => ({
      clave: `e${e.numero}`,
      fecha: new Date(e.inicio),
      tipo: 'APP_OPEN',
      paquete: app(e.app_numero)?.paquete ?? `app #${e.app_numero}`,
      detalle: formatoSeg(e.duracion_seg),
      registro: `/eventos/${e.numero}`,
    })),
    ...pausas.map((p) => ({
      clave: `p${p.numero}`,
      fecha: fechaServidor(p.fecha),
      tipo: 'FRICTION_TRIGGERED',
      paquete: app(p.app_numero)?.paquete ?? `app #${p.app_numero}`,
      detalle: `${p.tipo} · ${p.duracion_seg}s${p.ignorada ? ' · ignorada' : ''}`,
      registro: `/pausas/${p.numero}`,
    })),
  ]
    .filter((r) => r.fecha.getTime() <= ahora)
    .sort((a, b) => b.fecha - a.fecha)
    .slice(0, 6)
    .map((r) => ({ ...r, hora: formatoHora(r.fecha) }))

  return { dispositivo, pipeline, registros, pesoKB: (JSON.stringify(datos).length / 1024).toFixed(1) }
}
