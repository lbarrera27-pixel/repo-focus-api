// Datos de demostración con la misma forma que las respuestas de la API.
// Permiten ver el portal sin servidor (botón "Ver demo" en el inicio de sesión).
import { PERIODOS, fechaISO } from './panel.js'

// Generador pseudoaleatorio determinista para que la demo siempre se vea igual
function aleatorio(semilla) {
  let s = semilla
  return () => {
    s = (s * 1664525 + 1013904223) % 4294967296
    return s / 4294967296
  }
}

const APPS = [
  { numero: 1, nombre: 'Instagram', paquete: 'com.instagram.android', categoria: 'social', limite_aperturas: 10 },
  { numero: 2, nombre: 'TikTok', paquete: 'com.zhiliaoapp.musically', categoria: 'social', limite_aperturas: 8 },
  { numero: 3, nombre: 'X', paquete: 'com.twitter.android', categoria: 'social', limite_aperturas: 10 },
  { numero: 4, nombre: 'YouTube', paquete: 'com.google.android.youtube', categoria: 'video', limite_aperturas: 6 },
  { numero: 5, nombre: 'Netflix', paquete: 'com.netflix.mediaclient', categoria: 'video', limite_aperturas: 3 },
  { numero: 6, nombre: 'Clash Royale', paquete: 'com.supercell.clashroyale', categoria: 'gaming', limite_aperturas: 4 },
  { numero: 7, nombre: 'Roblox', paquete: 'com.roblox.client', categoria: 'gaming', limite_aperturas: 4 },
]

// Peso de uso por hora del día: más alto de noche (patrón del diseño)
const PESO_HORA = [0.9, 0.5, 0.3, 0.1, 0.05, 0.05, 0.1, 0.25, 0.3, 0.35, 0.4, 0.4,
  0.45, 0.5, 0.5, 0.55, 0.55, 0.5, 0.45, 0.55, 0.65, 0.75, 0.95, 1]

export function datosDemo(periodoId) {
  const r = aleatorio(42)
  const hoy = new Date()
  const { dias } = PERIODOS.find((p) => p.id === periodoId) ?? PERIODOS[1]
  const desde = fechaISO(new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate() - (dias - 1)))
  const hasta = fechaISO(hoy)

  const eventos = []
  const pausas = []
  const diasGenerados = Math.max(dias, 7)
  for (let d = diasGenerados - 1; d >= 0; d--) {
    // La tendencia baja con los días: el plan gradual está funcionando
    const factor = 1.15 - (diasGenerados - d) / diasGenerados * 0.35
    for (let h = 0; h < 24; h++) {
      const sesiones = Math.round(PESO_HORA[h] * factor * (1 + r() * 2))
      for (let s = 0; s < sesiones; s++) {
        const app = APPS[Math.floor(r() * APPS.length)]
        const inicio = new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate() - d, h, Math.floor(r() * 50))
        if (inicio > hoy) continue
        const largo = app.categoria === 'video' ? 300 + r() * 900 : app.categoria === 'gaming' ? 240 + r() * 600 : 60 + r() * 300
        eventos.push({
          numero: eventos.length + 1,
          app_numero: app.numero,
          franja_id: null,
          inicio: inicio.toISOString(),
          fin: new Date(inicio.getTime() + largo * 1000).toISOString(),
          duracion_seg: Math.round(largo),
        })
        if (r() < 0.25) {
          const tipo = r() < 0.55 ? 'leve' : r() < 0.7 ? 'media' : 'alta'
          const ignoradaProb = { leve: 0.28, media: 0.19, alta: 0.11 }[tipo]
          pausas.push({
            numero: pausas.length + 1,
            app_numero: app.numero,
            tipo,
            duracion_seg: tipo === 'leve' ? 5 : 15,
            ignorada: r() < ignoradaProb,
            fecha: inicio.toISOString(),
          })
        }
      }
    }
  }

  const delPeriodo = eventos.filter((e) => fechaISO(new Date(e.inicio)) >= desde)
  const plan = { numero: 1, fecha_inicio: desde, limite_base: 240, semana_actual: 3, activo: true }
  return {
    periodo: periodoId,
    desde,
    hasta,
    estadisticas: {
      desde,
      hasta,
      total_apps: APPS.length,
      total_eventos: delPeriodo.length,
      minutos_uso: Math.round(delPeriodo.reduce((s, e) => s + e.duracion_seg, 0) / 6) / 10,
      total_pausas: pausas.length,
      pausas_ignoradas: pausas.filter((p) => p.ignorada).length,
      sesiones_foco: 12,
      sesiones_foco_completadas: 9,
      minutos_foco_completados: 225,
      dominios_bloqueados_activos: 4,
      plan_activo: 1,
    },
    eventos,
    apps: APPS,
    pausas,
    tokens: [{ numero: 1, token: 'fcm-demo-0123456789', plataforma: 'android', fecha_registro: new Date(hoy.getTime() - 20 * 86_400_000).toISOString(), activo: true }],
    plan,
    ajustes: [
      { semana: 2, uso_meta: 225, adherencia: 0.82, cambio_pct: -6, fecha: desde },
      { semana: 3, uso_meta: 210, adherencia: 0.88, cambio_pct: -7, fecha: hasta },
    ],
  }
}
