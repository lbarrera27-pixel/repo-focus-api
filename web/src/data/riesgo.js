// Sección "Riesgo de recaída": GET /riesgo (regresión logística de la API) en el formato de la pantalla.
import { api } from '../api.js'

export const ALTO = 0.6   // desde aquí el nivel es "alto" (app/utils/riesgo.py)

// Umbral y métricas en prueba del modelo (app/utils/modelo_riesgo.json); se muestran aunque aún no haya riesgo
export const MODELO = { umbral: 0.42, metricas: { exactitud: 0.7607, auc_roc: 0.8479, precision: 0.7205, recall: 0.759 } }

// Textos de cada una de las 7 variables del modelo y cómo se muestra su valor
export const FACTORES = {
  adherencia: { titulo: 'Adherencia de la semana', valor: (v) => `${Math.round(v * 100)} %` },
  pct_nocturno: { titulo: 'Uso nocturno (22–06 h)', valor: (v) => `${Math.round(v * 100)} %` },
  racha: { titulo: 'Semanas seguidas cumpliendo', valor: (v) => `${Math.round(v)}` },
  pct_foco_completadas: { titulo: 'Sesiones de foco completadas', valor: (v) => `${Math.round(v * 100)} %` },
  pct_ignoradas: { titulo: 'Pausas ignoradas', valor: (v) => `${Math.round(v * 100)} %` },
  cambio_pct: { titulo: 'Recorte del límite', valor: (v) => `${v < 0 ? '−' : v > 0 ? '+' : ''}${Math.abs(v).toFixed(1)} %` },
  tendencia: { titulo: 'Tendencia de la adherencia', valor: (v) => `${v >= 0 ? '+' : '−'}${Math.abs(Math.round(v * 100))} pts` },
}

// Qué hacer cuando un factor sube el riesgo
const CONSEJOS = {
  pct_nocturno: { icono: 'luna', titulo: 'Baja el uso de noche' },
  pct_ignoradas: { icono: 'check', titulo: 'No saltes las pausas', detalle: 'Cada pausa cumplida lo baja.' },
  adherencia: { icono: 'check', titulo: 'Acércate a tu meta diaria', detalle: 'Cumplir tu límite es lo que más lo baja.' },
  pct_foco_completadas: { icono: 'check', titulo: 'Termina tus sesiones de foco', detalle: 'Cada sesión completada lo baja.' },
  racha: { icono: 'check', titulo: 'Encadena semanas cumpliendo', detalle: 'Las rachas largas lo bajan.' },
  tendencia: { icono: 'check', titulo: 'Recupera tu ritmo', detalle: 'Tu adherencia bajó respecto a la semana pasada.' },
  cambio_pct: { icono: 'check', titulo: 'Ve paso a paso', detalle: 'Un recorte más suave es más fácil de cumplir.' },
}

export function consejos(factores) {
  const suben = factores.filter((f) => f.efecto === 'sube' && CONSEJOS[f.variable])
  if (!suben.length) {
    return [{ icono: 'check', titulo: 'Sigue así', detalle: 'Ningún factor está subiendo tu riesgo esta semana.' }]
  }
  return suben.slice(0, 2).map((f, i) => ({
    ...CONSEJOS[f.variable],
    detalle: CONSEJOS[f.variable].detalle ?? (i === 0 ? 'Es lo que más sube tu riesgo.' : 'También sube tu riesgo.'),
  }))
}

export const porcentaje = (p) => `${Math.round(p * 100)} %`

// En la demo no hay API: un caso fijo con la misma forma que GET /riesgo
const DEMO = {
  plan: 1,
  semana: 8,
  probabilidad: 0.48,
  nivel: 'medio',
  umbral: 0.42,
  variables: {},
  factores: [
    { variable: 'adherencia', valor: 0.86, contribucion: -1.2, efecto: 'baja' },
    { variable: 'pct_nocturno', valor: 0.31, contribucion: 0.52, efecto: 'sube' },
    { variable: 'racha', valor: 3, contribucion: -0.38, efecto: 'baja' },
    { variable: 'pct_foco_completadas', valor: 0.75, contribucion: -0.27, efecto: 'baja' },
    { variable: 'pct_ignoradas', valor: 0.22, contribucion: 0.23, efecto: 'sube' },
    { variable: 'cambio_pct', valor: -5.9, contribucion: -0.19, efecto: 'baja' },
    { variable: 'tendencia', valor: 0.03, contribucion: 0.07, efecto: 'sube' },
  ],
  historial: [0.58, 0.55, 0.52, 0.49, 0.45, 0.41, 0.46, 0.48].map((p, i) => ({ semana: i + 1, probabilidad: p })),
  metricas: MODELO.metricas,
}

export async function cargarRiesgo(usuario) {
  if (usuario.demo) return DEMO
  return api.riesgo(usuario.id)
}
