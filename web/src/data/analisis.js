// Cálculos de la sección "Análisis de Usuario e IA".
// Usa los mismos datos crudos que el Panel General (cargarPanel / datosDemo).
import { fechaISO, fechaServidor } from './panel.js'
import { inferir } from './difuso.js'

const DIA_MS = 86_400_000
const hh = (h) => `${String(((h % 24) + 24) % 24).padStart(2, '0')}:00`

function nivelTexto(v) {
  if (v >= 80) return 'ALTO'
  if (v >= 60) return 'MEDIO-ALTO'
  if (v >= 35) return 'MEDIO'
  return 'BAJO'
}

function pearson(a, b) {
  const n = a.length
  const ma = a.reduce((s, x) => s + x, 0) / n
  const mb = b.reduce((s, x) => s + x, 0) / n
  let num = 0
  let da = 0
  let db = 0
  for (let i = 0; i < n; i++) {
    num += (a[i] - ma) * (b[i] - mb)
    da += (a[i] - ma) ** 2
    db += (b[i] - mb) ** 2
  }
  return da && db ? num / Math.sqrt(da * db) : null
}

const exito = (lista) => (lista.length ? Math.round((lista.filter((p) => !p.ignorada).length / lista.length) * 100) : null)

export function construirAnalisis(datos, ahora = new Date()) {
  const { eventos, pausas, plan, ajustes, desde, hasta } = datos
  const hoy = fechaISO(ahora)
  const hace7 = fechaISO(new Date(ahora.getTime() - 6 * DIA_MS))

  // ---------- Modelo por hora: promedio de minutos de uso de los últimos 7 días ----------
  const ultimos7 = eventos.filter((e) => fechaISO(new Date(e.inicio)) >= hace7)
  const minutosHora = Array(24).fill(0)
  const hoyHora = Array(24).fill(0)
  const diasConUso = Array.from({ length: 24 }, () => new Set())
  for (const e of ultimos7) {
    const d = new Date(e.inicio)
    minutosHora[d.getHours()] += e.duracion_seg / 60 / 7
    diasConUso[d.getHours()].add(fechaISO(d))
    if (fechaISO(d) === hoy) hoyHora[d.getHours()] += e.duracion_seg / 60
  }
  // Suavizado circular de 3 horas: el riesgo de una hora depende también de sus vecinas
  const suave = minutosHora.map((_, h) => (minutosHora[(h + 23) % 24] + 2 * minutosHora[h] + minutosHora[(h + 1) % 24]) / 4)
  const maxModelo = Math.max(...suave, ...hoyHora, 0.0001)
  const estimado = suave.map((v) => Math.round((v / maxModelo) * 100))
  const real = hoyHora.map((v) => Math.round((v / maxModelo) * 100))
  const conDatos = ultimos7.length > 0

  const horaActual = ahora.getHours()
  const riesgoActual = estimado[horaActual]
  const hace2 = estimado[(horaActual + 22) % 24]

  // ---------- Franja más vulnerable (2 h con más riesgo) ----------
  let inicio = 0
  for (let h = 0; h < 24; h++) if (estimado[h] + estimado[(h + 1) % 24] > estimado[inicio] + estimado[(inicio + 1) % 24]) inicio = h
  const diasFranja = new Set([...diasConUso[inicio], ...diasConUso[(inicio + 1) % 24]]).size
  const bloques = Array.from({ length: 12 }, (_, i) => Math.round((estimado[i * 2] + estimado[i * 2 + 1]) / 2))

  // ---------- Curva ----------
  const pico = estimado.indexOf(Math.max(...estimado))
  const horasHoy = real.slice(0, horaActual + 1)
  const r = horasHoy.some((v) => v > 0) ? pearson(estimado.slice(0, horaActual + 1), horasHoy) : null
  const cruce = estimado.findIndex((v, h) => v >= 50 && (h === 0 || estimado[h - 1] < 50))

  // ---------- Efectividad (pausas no ignoradas) ----------
  const enPeriodo = (p, a, b) => {
    const d = fechaISO(fechaServidor(p.fecha))
    return d >= a && d <= b
  }
  const delPeriodo = pausas.filter((p) => enPeriodo(p, desde, hasta))
  const dias = Math.round((new Date(`${hasta}T00:00:00`) - new Date(`${desde}T00:00:00`)) / DIA_MS) + 1
  const antDesde = fechaISO(new Date(new Date(`${desde}T00:00:00`).getTime() - dias * DIA_MS))
  const antHasta = fechaISO(new Date(new Date(`${desde}T00:00:00`).getTime() - DIA_MS))
  const anterior = pausas.filter((p) => enPeriodo(p, antDesde, antHasta))
  const efectividad = exito(delPeriodo)
  const efectividadAnt = exito(anterior)

  const niveles = [
    { tipo: 'leve', nivel: 1, insignia: '5s', titulo: 'Pausa de 5 segundos', color: '#f59e0b', clase: 'n1' },
    { tipo: 'media', nivel: 2, insignia: '10s', titulo: 'Respiración consciente 10s', color: '#0284c7', clase: 'n2' },
    { tipo: 'alta', nivel: 3, insignia: 'IA', titulo: 'Intervención conversacional IA', color: '#0f172a', clase: 'n3' },
  ].map((n) => {
    const lista = delPeriodo.filter((p) => p.tipo === n.tipo)
    return { ...n, total: lista.length, abandono: exito(lista) }
  })

  // ---------- Motor difuso: la semana actual con las reglas de la API ----------
  const ultimoAjuste = [...(ajustes ?? [])].sort((a, b) => b.semana - a.semana)[0]
  const objetivo = ultimoAjuste?.uso_meta ?? plan?.limite_base ?? null
  let difuso = null
  if (objetivo) {
    const usoDia = new Map()
    for (let i = 0; i < 7; i++) usoDia.set(fechaISO(new Date(ahora.getTime() - i * DIA_MS)), 0)
    for (const e of ultimos7) {
      const k = fechaISO(new Date(e.inicio))
      if (usoDia.has(k)) usoDia.set(k, usoDia.get(k) + e.duracion_seg / 60)
    }
    // Adherencia del día: 1 si no pasó la meta; si la pasó, cae en proporción al exceso
    const adherencias = [...usoDia.values()].map((min) => (min <= objetivo ? 1 : Math.max(0, 1 - (min - objetivo) / objetivo)))
    const adherencia = adherencias.reduce((s, x) => s + x, 0) / adherencias.length
    const semana = pausas.filter((p) => fechaISO(fechaServidor(p.fecha)) >= hace7)
    const pctIgnoradas = semana.length ? semana.filter((p) => p.ignorada).length / semana.length : 0
    const inf = inferir(adherencia, pctIgnoradas)
    difuso = { ...inf, objetivo, nuevoLimite: Math.round(objetivo * (1 + inf.cambio / 100)) }
  }

  return {
    conDatos,
    gauge: { valor: riesgoActual, nivel: nivelTexto(riesgoActual), delta: riesgoActual - hace2 },
    franja: { texto: conDatos ? `${hh(inicio)} — ${hh(inicio + 2)}` : '— —', dias: diasFranja, bloques },
    efectividad: { valor: efectividad, delta: efectividad != null && efectividadAnt != null ? efectividad - efectividadAnt : null },
    curva: {
      estimado,
      real,
      horaActual,
      pico: { hora: pico, valor: estimado[pico] },
      r,
      nivelRecomendado: estimado[pico] >= 80 ? 3 : estimado[pico] >= 50 ? 2 : 1,
      insight: !conDatos
        ? 'aún no hay suficientes eventos para estimar la curva de riesgo.'
        : cruce >= 0
          ? `el riesgo supera el 50% a partir de las ${hh(cruce)} y alcanza su máximo a las ${hh(pico)}.`
          : `el riesgo se mantiene por debajo del 50% todo el día; el máximo es a las ${hh(pico)}.`,
    },
    niveles,
    totalIntervenciones: delPeriodo.length,
    difuso,
  }
}
