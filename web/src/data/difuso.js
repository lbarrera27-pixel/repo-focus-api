// Port de app/utils/reglas_plan.py (inferencia Mamdani del ajuste semanal).
// Mismas constantes que la API para que el portal explique exactamente lo que calcula el servidor.

export function trapecio(x, a, b, c, d) {
  if (x <= a || x >= d) return 0
  if (x < b) return (x - a) / (b - a)
  if (x <= c) return 1
  return (d - x) / (d - c)
}

const triangulo = (x, a, b, c) => trapecio(x, a, b, b, c)

export const ADHERENCIA = {
  baja: [-1.0, -0.5, 0.4, 0.55],
  regular: [0.4, 0.55, 0.65, 0.8],
  buena: [0.65, 0.8, 0.85, 0.95],
  excelente: [0.85, 0.95, 1.5, 2.0],
}
export const IGNORADAS = {
  pocas: [-1.0, -0.5, 0.2, 0.45],
  muchas: [0.25, 0.6, 1.5, 2.0],
}
const CAMBIO = {
  reducir_mucho: [-15, -10, -5],
  reducir_poco: [-9, -5, -1],
  mantener: [-3, 0, 3],
  relajar: [1, 5, 9],
}
const RANGO_CAMBIO = [-15, 10]
const PASO = 0.1

export const REGLAS = [
  ['excelente', 'pocas', 'reducir_mucho'],
  ['excelente', 'muchas', 'reducir_poco'],
  ['buena', 'pocas', 'reducir_poco'],
  ['buena', 'muchas', 'mantener'],
  ['regular', null, 'mantener'],
  ['baja', null, 'relajar'],
]

const acotar = (x) => Math.min(1, Math.max(0, x))

// Devuelve el detalle completo de la inferencia para poder explicarla en pantalla
export function inferir(adherencia, pctIgnoradas = 0) {
  const adh = acotar(adherencia)
  const ign = acotar(pctIgnoradas)
  const pertenencia = Object.fromEntries(Object.entries(ADHERENCIA).map(([k, v]) => [k, trapecio(adh, ...v)]))
  const pertenenciaIgn = Object.fromEntries(Object.entries(IGNORADAS).map(([k, v]) => [k, trapecio(ign, ...v)]))

  const reglas = REGLAS.map(([a, p, salida], i) => ({
    numero: i + 1,
    adherencia: a,
    ignoradas: p,
    salida,
    fuerza: Math.min(pertenencia[a], p ? pertenenciaIgn[p] : 1),
  }))
  const activas = reglas.filter((r) => r.fuerza > 0)

  let cambio = 0
  if (activas.length) {
    let num = 0
    let den = 0
    const [inicio, fin] = RANGO_CAMBIO
    for (let i = 0; i <= Math.round((fin - inicio) / PASO); i++) {
      const z = inicio + i * PASO
      const mu = Math.max(...activas.map((r) => Math.min(r.fuerza, triangulo(z, ...CAMBIO[r.salida]))))
      num += z * mu
      den += mu
    }
    cambio = den ? Math.round((num / den) * 10) / 10 : 0
  }
  const principal = [...reglas].sort((a, b) => b.fuerza - a.fuerza)[0]
  return { adherencia: adh, ignoradas: ign, pertenencia, pertenenciaIgn, reglas, principal, cambio: cambio + 0 }
}
