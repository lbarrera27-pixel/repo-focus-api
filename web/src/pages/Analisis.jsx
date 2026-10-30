import { useMemo } from 'react'
import Icono from '../components/Icono.jsx'
import iconoExportar from '../assets/icons/ia-exportar.svg'
import iconoReloj from '../assets/icons/ia-reloj.svg'
import iconoEscudo from '../assets/icons/ia-escudo.svg'
import iconoInsight from '../assets/icons/ia-insight.svg'
import iconoRegla from '../assets/icons/ia-regla.svg'
import iconoSalida from '../assets/icons/ia-salida.svg'
import iconoChevronOscuro from '../assets/icons/ia-chevron-oscuro.svg'
import iconoChevron from '../assets/icons/ia-chevron.svg'
import { construirAnalisis } from '../data/analisis.js'
import { ADHERENCIA, trapecio } from '../data/difuso.js'
import { PERIODOS, haceCuanto } from '../data/panel.js'
import './Analisis.css'

const PERIODOS_IA = PERIODOS.filter((p) => p.id !== 'semestre')

function iniciales(nombre = '') {
  return nombre.split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0].toUpperCase()).join('') || '?'
}

// ---------- Cabecera ----------

function Cabecera({ usuario, periodo, onPeriodo, actualizado, onExportar, error }) {
  return (
    <header className="topbar topbar--seccion">
      <div className="topbar__titulos">
        <p className="topbar__ruta">
          FOCUS! CLOUD <span>/</span> ANÁLISIS DE USUARIO <span>/</span> IA
        </p>
        <h1 className="topbar__titulo topbar__titulo--grande">Análisis de Usuario e Inteligencia Artificial</h1>
        <p className="topbar__desc">Predicción de recaída, inferencia difusa y efectividad de intervenciones.</p>
      </div>
      <div className="topbar__acciones ia-acciones">
        <div className="segmentado segmentado--ia" role="group" aria-label="Periodo">
          {PERIODOS_IA.map((p) => (
            <button
              key={p.id}
              type="button"
              className={`segmentado__opcion${p.id === periodo ? ' segmentado__opcion--activa' : ''}`}
              aria-pressed={p.id === periodo}
              onClick={() => onPeriodo(p.id)}
            >
              {p.etiqueta}
            </button>
          ))}
        </div>
        <span className={`estado estado--chip ia-modelo${error ? ' estado--error' : ''}`}>
          <span className="estado__punto" aria-hidden="true" />
          {error ? `Error: ${error}` : `Modelo actualizado · ${actualizado.toLowerCase()}`}
        </span>
        <button type="button" className="boton-primario ia-exportar" onClick={onExportar}>
          <Icono src={iconoExportar} tam={15} />
          Exportar reporte
        </button>
        <span className="avatar avatar--ia" title={usuario.nombre}>{iniciales(usuario.nombre)}</span>
      </div>
    </header>
  )
}

// ---------- KPIs ----------

function arco(cx, cy, r, desde, hasta) {
  // Ángulos en % del semicírculo (0 = izquierda, 100 = derecha)
  const p = (pct) => {
    const a = Math.PI * (1 - pct / 100)
    return [cx + r * Math.cos(a), cy - r * Math.sin(a)]
  }
  const [x1, y1] = p(desde)
  const [x2, y2] = p(hasta)
  return `M${x1.toFixed(2)} ${y1.toFixed(2)} A${r} ${r} 0 0 1 ${x2.toFixed(2)} ${y2.toFixed(2)}`
}

function Gauge({ valor, nivel }) {
  const cx = 95
  const cy = 72
  const a = Math.PI * (1 - valor / 100)
  return (
    <div className="gauge">
      <svg viewBox="0 0 190 80" width="190" height="80" role="img" aria-label={`Probabilidad de recaída de ${valor} por ciento`}>
        <path d={arco(cx, cy, 58, 2, 37)} stroke="#10b981" strokeWidth="14" fill="none" strokeLinecap="round" />
        <path d={arco(cx, cy, 58, 41, 67)} stroke="#f59e0b" strokeWidth="14" fill="none" strokeLinecap="round" />
        <path d={arco(cx, cy, 58, 71, 98)} stroke="#ef4444" strokeWidth="14" fill="none" strokeLinecap="round" />
        <line x1={cx} y1={cy} x2={cx + 50 * Math.cos(a)} y2={cy - 50 * Math.sin(a)} stroke="#0f172a" strokeWidth="3" strokeLinecap="round" />
        <circle cx={cx} cy={cy} r="5" fill="#0f172a" />
      </svg>
      <p className="gauge__valor">
        {valor}
        <span>%</span>
      </p>
      <p className="gauge__nivel">NIVEL {nivel}</p>
    </div>
  )
}

const COLOR_BLOQUE = (v) => (v >= 60 ? ['#f97316', 20] : v >= 35 ? ['#fbbf24', 13] : ['#e2e8f0', 7])

function Kpis({ a }) {
  const { gauge, franja, efectividad } = a
  return (
    <div className="ia-kpis">
      <article className="ia-kpi ia-kpi--riesgo">
        <div className="ia-kpi__texto">
          <p className="card__etiqueta">PROBABILIDAD ACTUAL</p>
          <h2 className="card__titulo card__titulo--tel">Riesgo de Recaída</h2>
          <p className="ia-tendencia">
            <i />
            {a.conDatos
              ? `${gauge.delta >= 0 ? 'Subió' : 'Bajó'} ${Math.abs(gauge.delta)} pts respecto a hace 2 horas`
              : 'Sin eventos en los últimos 7 días'}
          </p>
        </div>
        <Gauge valor={gauge.valor} nivel={gauge.nivel} />
      </article>

      <article className="ia-kpi ia-kpi--franja">
        <span className="ia-kpi__icono" style={{ background: '#fef3c7' }}>
          <Icono src={iconoReloj} tam={21} />
        </span>
        <div className="ia-kpi__cuerpo">
          <p className="card__etiqueta ia-kpi__etiqueta">FRANJA MÁS VULNERABLE</p>
          <p className="ia-kpi__grande">
            {franja.texto} <span>hrs</span>
          </p>
          <p className="ia-kpi__nota">
            {a.conDatos ? `Patrón recurrente en ${franja.dias} de los últimos 7 días.` : 'Se calcula con los eventos de uso.'}
          </p>
        </div>
        <div className="ia-bloques" title="Riesgo promedio por bloque de 2 horas (00–24 h)">
          {franja.bloques.map((v, i) => {
            const [color, alto] = COLOR_BLOQUE(v)
            return <span key={i} style={{ background: color, height: alto }} />
          })}
        </div>
      </article>

      <article className="ia-kpi ia-kpi--efectividad">
        <span className="ia-kpi__icono" style={{ background: '#e0f2fe' }}>
          <Icono src={iconoEscudo} tam={21} />
        </span>
        <div className="ia-kpi__cuerpo">
          <p className="card__etiqueta ia-kpi__etiqueta">EFECTIVIDAD GLOBAL</p>
          <p className="ia-kpi__enorme">
            {efectividad.valor ?? '—'}
            <span>%</span>
          </p>
          <p className="ia-kpi__nota">de aperturas impulsivas evitadas</p>
        </div>
        <div className="ia-kpi__pie">
          <span className="card__etiqueta">
            {efectividad.delta == null ? 'Sin periodo anterior' : `${efectividad.delta >= 0 ? '+' : '−'}${Math.abs(efectividad.delta)}%`}
          </span>
          <small>vs. periodo anterior</small>
        </div>
      </article>
    </div>
  )
}

// ---------- Curva de riesgo ----------

const CX = (h) => 4 + (h / 23) * 598
const CY = (v) => 165 - (v / 100) * 154

function CurvaRiesgo({ c, conDatos }) {
  const linea = (vals) => vals.map((v, h) => `${h ? 'L' : 'M'}${CX(h).toFixed(1)} ${CY(v).toFixed(1)}`).join(' ')
  const est = linea(c.estimado)
  const real = linea(c.real.slice(0, c.horaActual + 1))
  const px = CX(c.pico.hora)
  const py = CY(c.pico.valor)
  const vx0 = CX(Math.max(0, c.pico.hora - 3))
  const vx1 = CX(Math.min(23, c.pico.hora + 3))
  return (
    <section className="card ia-curva">
      <header className="card__header card__header--tel">
        <div className="card__titulos">
          <p className="card__etiqueta">MODELO PREDICTIVO · 24 HORAS</p>
          <h2 className="card__titulo card__titulo--tel">Curva de Riesgo por Hora</h2>
        </div>
        <div className="ia-leyenda">
          <span><i style={{ background: '#f59e0b' }} />Riesgo estimado</span>
          <span><i style={{ background: '#0284c7' }} />Uso real (hoy)</span>
        </div>
      </header>

      <div className="ia-resumen">
        <span>
          <b>Pico proyectado</b>
          <small>{conDatos ? `${String(c.pico.hora).padStart(2, '0')}:00 · ${c.pico.valor}%` : '—'}</small>
        </span>
        <span>
          <b>Correlación modelo/uso</b>
          <small>{c.r == null ? 'Sin uso hoy' : `r = ${c.r.toFixed(2)}`}</small>
        </span>
        <span>
          <b>Ventana recomendada</b>
          <small>Fricción Nivel {c.nivelRecomendado}</small>
        </span>
      </div>

      <div className="ia-grafica">
        <div className="ia-grafica__y">
          {['100%', '75%', '50%', '25%', '0%'].map((t) => (
            <small key={t}>{t}</small>
          ))}
        </div>
        <svg viewBox="0 0 610 182" className="ia-grafica__svg" role="img" aria-label="Curva predictiva de riesgo durante 24 horas">
          <defs>
            <linearGradient id="ia-area" x1="0" y1="0" x2="0" y2="1">
              <stop stopColor="#f59e0b" stopOpacity="0.28" />
              <stop offset="1" stopColor="#f59e0b" stopOpacity="0" />
            </linearGradient>
            <linearGradient id="ia-ventana" x1="0" y1="0" x2="0" y2="1">
              <stop stopColor="#ef4444" stopOpacity="0.14" />
              <stop offset="1" stopColor="#ef4444" stopOpacity="0.04" />
            </linearGradient>
          </defs>
          {[0, 25, 50, 75, 100].map((v) => (
            <line key={v} x1="4" x2="602" y1={CY(v)} y2={CY(v)} stroke="#edf1f5" />
          ))}
          {conDatos && <rect x={vx0} y="9" width={vx1 - vx0} height="156" rx="4" fill="url(#ia-ventana)" />}
          <path d={`${est} L${CX(23)} 165 L${CX(0)} 165 Z`} fill="url(#ia-area)" />
          <path d={est} fill="none" stroke="#f59e0b" strokeWidth="2.5" strokeLinejoin="round" />
          {c.real.slice(0, c.horaActual + 1).some((v) => v > 0) && (
            <path d={real} fill="none" stroke="#0284c7" strokeWidth="2" strokeDasharray="5 4" strokeLinejoin="round" />
          )}
          {conDatos && (
            <g>
              <line x1={px} x2={px} y1={py} y2="165" stroke="#ea580c" strokeDasharray="3 3" />
              <circle cx={px} cy={py} r="4" fill="#fff" stroke="#ea580c" strokeWidth="2" />
              <rect x={Math.min(px - 31, 548)} y={Math.max(py - 24, 0)} width="62" height="15" rx="4" fill="#c2410c" />
              <text x={Math.min(px, 579)} y={Math.max(py - 13.5, 10.5)} textAnchor="middle" className="ia-grafica__pico">
                RIESGO {c.pico.valor}%
              </text>
            </g>
          )}
        </svg>
        <div className="ia-grafica__x">
          {['00h', '04h', '08h', '12h', '16h', '20h', '24h'].map((t) => (
            <small key={t}>{t}</small>
          ))}
        </div>
      </div>

      <p className="ia-insight">
        <Icono src={iconoInsight} tam={15} />
        <span>
          <b>Insight del modelo:</b> {c.insight}
        </span>
      </p>
    </section>
  )
}

// ---------- Motor difuso ----------

const COLORES_SET = { baja: '#94a3b8', regular: '#0284c7', buena: '#f59e0b', excelente: '#10b981' }
const ETIQUETA_SALIDA = { reducir_mucho: 'Reducir mucho', reducir_poco: 'Reducir poco', mantener: 'Mantener', relajar: 'Relajar' }
const FX = (x) => 21.4 + x * 385.3
const FY = (mu) => 76.8 - mu * 64.8

function curvaSet([a, b, c, d]) {
  // Recorta el trapecio al rango visible 0..1
  const pts = []
  for (let i = 0; i <= 100; i++) {
    const x = i / 100
    pts.push([x, trapecio(x, a, b, c, d)])
  }
  return pts
}

function MotorDifuso({ d }) {
  if (!d) {
    return (
      <section className="card ia-difuso">
        <header className="card__header card__header--tel">
          <div className="card__titulos">
            <p className="card__etiqueta">IA EXPLICABLE</p>
            <h2 className="card__titulo card__titulo--tel">Motor de Inferencia Difusa</h2>
          </div>
        </header>
        <p className="vacio">Crea un plan (POST /planes) para que el motor pueda comparar el uso contra una meta.</p>
      </section>
    )
  }
  const x = d.adherencia
  const disparo = d.principal.fuerza
  const p = d.principal
  // La etiqueta de la entrada no debe salirse del gráfico en los extremos
  const chipX = Math.min(Math.max(FX(x), FX(0) + 12), 417.447 - 12)
  return (
    <section className="card ia-difuso">
      <header className="card__header card__header--tel">
        <div className="card__titulos">
          <p className="card__etiqueta">IA EXPLICABLE</p>
          <h2 className="card__titulo card__titulo--tel">Motor de Inferencia Difusa</h2>
          <p className="ia-difuso__sub">Mamdani · mismas reglas que el ajuste semanal de la API</p>
        </div>
        <span className="insignia insignia--vivo">
          <span className="estado__punto" aria-hidden="true" />
          ACTIVO
        </span>
      </header>

      <div className="ia-pertenencia">
        <div className="ia-pertenencia__cabeza">
          <b>Funciones de pertenencia</b>
          <small>Adherencia de los últimos 7 días</small>
        </div>
        <svg viewBox="0 0 417.447 91.987" className="ia-pertenencia__svg" role="img" aria-label="Funciones de pertenencia difusa">
          {[0.5, 1].map((mu) => (
            <line key={mu} x1={FX(0)} x2={FX(1)} y1={FY(mu)} y2={FY(mu)} stroke="#e2e8f0" strokeDasharray="3 3" />
          ))}
          {[0.25, 0.5, 0.75].map((t) => (
            <line key={t} x1={FX(t)} x2={FX(t)} y1={FY(1)} y2={FY(0)} stroke="#e2e8f0" strokeDasharray="3 3" />
          ))}
          <line x1={FX(0)} x2={FX(1)} y1={FY(0)} y2={FY(0)} stroke="#cbd5e1" />
          <line x1={FX(0)} x2={FX(0)} y1={FY(1)} y2={FY(0)} stroke="#cbd5e1" />
          {Object.entries(ADHERENCIA).map(([nombre, set]) => {
            const pts = curvaSet(set)
            const lin = pts.map(([px, mu], i) => `${i ? 'L' : 'M'}${FX(px).toFixed(1)} ${FY(mu).toFixed(1)}`).join(' ')
            return (
              <g key={nombre}>
                <path d={`${lin} L${FX(1)} ${FY(0)} L${FX(0)} ${FY(0)} Z`} fill={COLORES_SET[nombre]} fillOpacity="0.1" />
                <path d={lin} fill="none" stroke={COLORES_SET[nombre]} strokeWidth="1.6" />
              </g>
            )
          })}
          {/* Corte de la regla que más se dispara */}
          <line x1={FX(x)} x2={FX(1)} y1={FY(disparo)} y2={FY(disparo)} stroke="#ef4444" strokeWidth="1.6" />
          <line x1={FX(x)} x2={FX(x)} y1="11" y2={FY(0)} stroke="#0f172a" strokeWidth="1" />
          {Object.entries(d.pertenencia).map(([nombre, mu]) => (
            <circle key={nombre} cx={FX(x)} cy={FY(mu)} r="3.2" fill={COLORES_SET[nombre]} stroke="#fff" strokeWidth="1.3" />
          ))}
          <rect x={chipX - 12} y="0" width="24" height="11" rx="5.5" fill="#0f172a" />
          <text x={chipX} y="8" textAnchor="middle" className="ia-pertenencia__entrada">{x.toFixed(2)}</text>
          <text x={FX(0.12)} y="22" className="ia-set" fill="#64748b">BAJA</text>
          <text x={FX(0.52)} y="22" className="ia-set" fill="#0369a1">REGULAR</text>
          <text x={FX(0.74)} y="34" className="ia-set" fill="#b45309">BUENA</text>
          <text x={FX(0.9)} y="22" className="ia-set" fill="#047857">EXCEL.</text>
          {[0, 0.25, 0.5, 0.75, 1].map((t) => (
            <text key={t} x={FX(t)} y="88" textAnchor="middle" className="ia-eje">{t}</text>
          ))}
          <text x="7" y="15" className="ia-eje ia-eje--y">1.0</text>
          <text x="7" y="47" className="ia-eje ia-eje--y">0.5</text>
        </svg>
        <div className="ia-pertenencia__leyenda">
          {Object.entries(d.pertenencia).map(([nombre, mu]) => (
            <span key={nombre}>
              <i style={{ background: COLORES_SET[nombre] }} />
              {nombre.charAt(0).toUpperCase() + nombre.slice(1)} μ {mu.toFixed(2)}
            </span>
          ))}
          <span>
            <i style={{ background: '#ef4444' }} />
            Disparo μ {disparo.toFixed(2)}
          </span>
        </div>
      </div>

      <div className="ia-regla">
        <div className="ia-regla__cabeza">
          <span className="ia-regla__icono">
            <Icono src={iconoRegla} tam={16} />
          </span>
          <span>
            <small>REGLA ACTIVA #{p.numero}</small>
            <b>Disparo con pertenencia μ = {p.fuerza.toFixed(2)}</b>
          </span>
          <em>{d.cambio < 0 ? 'REDUCIR' : d.cambio > 0 ? 'RELAJAR' : 'MANTENER'}</em>
        </div>
        <div className="ia-regla__codigo">
          <p>
            <b>SI</b> Adherencia es <i>{p.adherencia.toUpperCase()}</i>
          </p>
          <p>
            <b>Y</b> Pausas_ignoradas es <i>{p.ignoradas ? p.ignoradas.toUpperCase() : 'CUALQUIERA'}</i>{' '}
            <span className="ia-regla__dato">({Math.round(d.ignoradas * 100)}% esta semana)</span>
          </p>
          <hr />
          <p>
            <b>ENTONCES</b> Cambio = <i>{ETIQUETA_SALIDA[p.salida]}</i>
          </p>
        </div>
        <div className="ia-regla__salida">
          <span className="ia-regla__icono ia-regla__icono--azul">
            <Icono src={iconoSalida} tam={15} />
          </span>
          <span>
            <small>SALIDA (CENTROIDE)</small>
            <b>
              {d.cambio > 0 ? '+' : ''}
              {d.cambio}% · límite {Math.round(d.objetivo)} → {d.nuevoLimite} min/día
            </b>
          </span>
          <Icono src={iconoChevronOscuro} tam={15} />
        </div>
      </div>
    </section>
  )
}

// ---------- Intervenciones ----------

function Intervenciones({ niveles, total }) {
  return (
    <section className="card ia-intervenciones">
      <header className="ia-intervenciones__cabeza">
        <div className="card__titulos">
          <p className="card__etiqueta">FRICTION INTERVENTIONS BREAKDOWN</p>
          <h2 className="card__titulo card__titulo--tel">Rendimiento por Nivel de Fricción</h2>
          <p className="ia-difuso__sub">Comparación del abandono voluntario antes de abrir una app restringida.</p>
        </div>
        <div className="ia-intervenciones__total">
          <b>{total}</b>
          <small>intervenciones totales</small>
        </div>
      </header>
      <div className="ia-niveles">
        {niveles.map((n) => (
          <article key={n.nivel} className={`ia-nivel ia-nivel--${n.clase}`}>
            <div className="ia-nivel__cabeza">
              <span className="ia-nivel__insignia">{n.insignia}</span>
              <span>
                <small>NIVEL {n.nivel}</small>
                <b>{n.titulo}</b>
              </span>
              <span className="ia-nivel__chevron">
                <img src={iconoChevron} alt="" />
              </span>
            </div>
            <div className="ia-nivel__cifra">
              <p>
                <b>
                  {n.abandono ?? '—'}
                  <span>%</span>
                </b>
                <small>abandono voluntario</small>
              </p>
              <small>{n.total} intervenciones</small>
            </div>
            <div className="ia-nivel__pista">
              <span style={{ width: `${n.abandono ?? 0}%`, background: n.color }} />
              <i style={{ left: '70%' }} />
            </div>
            <div className="ia-nivel__escala">
              <small>0%</small>
              <small>Objetivo 70%</small>
              <small>100%</small>
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}

// ---------- Página ----------

export default function Analisis({ usuario, datos, periodo, onPeriodo, error, cargadoEn, onReintentar }) {
  const a = useMemo(() => (datos ? construirAnalisis(datos) : null), [datos])

  function exportar() {
    if (!a) return
    const url = URL.createObjectURL(new Blob([JSON.stringify({ periodo: datos.periodo, desde: datos.desde, hasta: datos.hasta, ...a }, null, 2)], { type: 'application/json' }))
    Object.assign(document.createElement('a'), { href: url, download: `focus-reporte-ia_${datos.desde}_${datos.hasta}.json` }).click()
    URL.revokeObjectURL(url)
  }

  return (
    <>
      <Cabecera
        usuario={usuario}
        periodo={periodo}
        onPeriodo={onPeriodo}
        actualizado={cargadoEn ? haceCuanto(new Date(cargadoEn).toISOString()) : 'cargando'}
        onExportar={exportar}
        error={error}
      />
      {a ? (
        <div className="ia">
          <Kpis a={a} />
          <div className="ia-fila">
            <CurvaRiesgo c={a.curva} conDatos={a.conDatos} />
            <MotorDifuso d={a.difuso} />
          </div>
          <Intervenciones niveles={a.niveles} total={a.totalIntervenciones} />
        </div>
      ) : (
        <div className="panel panel--una">
          <p className="vacio">
            {error ? (
              <>
                No se pudieron cargar los datos. <button type="button" className="enlace" onClick={onReintentar}>Reintentar</button>
              </>
            ) : (
              'Cargando análisis…'
            )}
          </p>
        </div>
      )}
    </>
  )
}
