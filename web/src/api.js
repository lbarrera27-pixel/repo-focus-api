// Cliente de la API de Focus!
// Las rutas privadas se identifican con el header X-Usuario-Id (ver app/dependencies.py).

const BASE = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(status, detail) {
    super(detail || `Error ${status}`)
    this.status = status
  }
}

async function pedir(ruta, { usuarioId, metodo = 'GET', cuerpo, reintentos = 2 } = {}) {
  const headers = { Accept: 'application/json' }
  if (usuarioId) headers['X-Usuario-Id'] = String(usuarioId)
  if (cuerpo) headers['Content-Type'] = 'application/json'

  const resp = await fetch(BASE + ruta, {
    method: metodo,
    headers,
    body: cuerpo ? JSON.stringify(cuerpo) : undefined,
  })

  // Azure SQL serverless responde 503 mientras despierta: se reintenta tras Retry-After
  if (resp.status === 503 && reintentos > 0) {
    const espera = Number(resp.headers.get('Retry-After')) || 30
    await new Promise((r) => setTimeout(r, Math.min(espera, 30) * 1000))
    return pedir(ruta, { usuarioId, metodo, cuerpo, reintentos: reintentos - 1 })
  }

  if (resp.status === 204) return null
  const datos = await resp.json().catch(() => null)
  if (!resp.ok) {
    const detalle = typeof datos?.detail === 'string' ? datos.detail : null
    throw new ApiError(resp.status, detalle)
  }
  return datos
}

function consulta(params) {
  const q = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) if (v != null) q.set(k, v)
  const s = q.toString()
  return s ? `?${s}` : ''
}

export const api = {
  base: BASE,
  login: (email, password) => pedir('/auth/login', { metodo: 'POST', cuerpo: { email, password } }),
  usuario: (id) => pedir('/usuarios/me', { usuarioId: id }),
  estadisticas: (id, desde, hasta) => pedir(`/estadisticas${consulta({ desde, hasta })}`, { usuarioId: id }),
  eventos: (id, desde, hasta) => pedir(`/eventos${consulta({ desde, hasta })}`, { usuarioId: id }),
  apps: (id) => pedir('/apps', { usuarioId: id }),
  pausas: (id) => pedir('/pausas', { usuarioId: id }),
  tokens: (id) => pedir('/tokens-dispositivo', { usuarioId: id }),
  // 404 cuando el usuario aún no tiene plan activo
  planActivo: (id) => pedir('/planes/activo', { usuarioId: id }).catch((e) => {
    if (e.status === 404) return null
    throw e
  }),
  ajustes: (id, numero) => pedir(`/planes/${numero}/ajustes`, { usuarioId: id }),
  // Regresión logística: probabilidad de pasarse del límite la semana siguiente
  // (404 sin plan; estado "insuficiente" si el plan aún no cierra su primera semana)
  riesgo: (id) => pedir('/riesgo', { usuarioId: id }).then((r) => (r.estado === 'insuficiente' ? null : r), (e) => {
    if (e.status === 404) return null
    throw e
  }),
  crearApp: (id, app) => pedir('/apps', { usuarioId: id, metodo: 'POST', cuerpo: app }),
  actualizarPlan: (id, numero, cambios) => pedir(`/planes/${numero}`, { usuarioId: id, metodo: 'PUT', cuerpo: cambios }),
  eliminarCuenta: (id) => pedir('/usuarios/me', { usuarioId: id, metodo: 'DELETE' }),
  actualizarApp: (id, numero, cambios) => pedir(`/apps/${numero}`, { usuarioId: id, metodo: 'PUT', cuerpo: cambios }),
  // Ajustes del portal (JSON libre por usuario); {} si nunca se han guardado
  configuracion: (id) => pedir('/configuracion/me', { usuarioId: id }),
  guardarConfiguracion: (id, datos) => pedir('/configuracion/me', { usuarioId: id, metodo: 'PUT', cuerpo: datos }),
  // Sin cambio_pct: el servidor lo calcula con sus reglas difusas (409 si la semana ya existe)
  crearAjuste: (id, numero, ajuste) => pedir(`/planes/${numero}/ajustes`, { usuarioId: id, metodo: 'POST', cuerpo: ajuste }),
  // Estado del servidor y de la base de datos; también sirve para medir la latencia
  salud: async () => {
    const t0 = performance.now()
    const datos = await pedir('/salud', { reintentos: 0 })
    return { ...datos, latenciaMs: Math.round(performance.now() - t0) }
  },
}
