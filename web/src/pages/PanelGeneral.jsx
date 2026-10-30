import Card, { Insignia } from '../components/Card.jsx'
import Icono from '../components/Icono.jsx'
import iconoTelefono from '../assets/icons/phone.svg'
import iconoCheck from '../assets/icons/check.svg'
import iconoMovil from '../assets/icons/mobile-client.svg'
import iconoNube from '../assets/icons/cloud-ingestion.svg'
import iconoAnalytics from '../assets/icons/analytics.svg'
import iconoFlecha from '../assets/icons/arrow-head.svg'
import iconoCerebro from '../assets/icons/brain.svg'
import iconoPulso from '../assets/icons/pulse.svg'
import { formatoDuracion, nivelRiesgo } from '../data/panel.js'

// ---------- Telemetría ----------

function TelemetryCard({ t }) {
  return (
    <Card
      className="card--telemetria"
      etiqueta="ANDROID CLOUD SYNC"
      titulo="Telemetry Pipeline"
      extra={<Insignia vivo={t.servicioActivo}>{t.servicioActivo ? 'EN VIVO' : 'SIN SEÑAL'}</Insignia>}
    >
      <div className="dispositivo">
        <span className="dispositivo__icono">
          <Icono src={iconoTelefono} tam={23} />
        </span>
        <span className="dispositivo__texto">
          <b>{t.dispositivo}</b>
          <small>{t.detalle}</small>
        </span>
        {t.vinculado ? (
          <span className="vinculado">
            <Icono src={iconoCheck} tam={12} /> Vinculado
          </span>
        ) : (
          <span className="vinculado vinculado--no">Sin vincular</span>
        )}
      </div>

      <dl className="metricas3">
        <div>
          <dt>SERVICIO</dt>
          <dd>
            <span className={`punto ${t.servicioActivo ? 'punto--ok' : 'punto--off'}`} />
            {t.servicioActivo ? 'Background activo' : 'Sin actividad 24 h'}
          </dd>
        </div>
        <div>
          <dt>HEARTBEAT</dt>
          <dd>{t.heartbeat}</dd>
        </div>
        <div>
          <dt>EVENTOS</dt>
          <dd>{t.eventos} eventos</dd>
        </div>
      </dl>

      <div className="pipeline">
        {t.nodos.map((n, i) => (
          <div className="pipeline__paso" key={n.titulo}>
            {i > 0 && (
              <span className="pipeline__flecha" aria-hidden="true">
                <span className="pipeline__linea" />
                <Icono src={iconoFlecha} tam={12.5} />
              </span>
            )}
            <div className="pipeline__nodo">
              <Icono src={[iconoMovil, iconoNube, iconoAnalytics][i]} tam={16} />
              <b>{n.titulo}</b>
              <small>{n.dato}</small>
            </div>
          </div>
        ))}
      </div>
    </Card>
  )
}

// ---------- Clústeres ----------

const ANCHO_D = 568
const ALTO_D = 151
const EJE = { izq: 103, der: 487, arr: 13, abj: 129 }

function ClusterCard({ c }) {
  const maxDur = Math.max(1, ...c.puntos.map((p) => p.duracionMedia))
  const maxAp = Math.max(1, ...c.puntos.map((p) => p.aperturas))
  const pos = (p) => ({
    x: EJE.izq + 14 + (p.duracionMedia / maxDur) * (EJE.der - EJE.izq - 28),
    y: EJE.abj - 12 - (p.aperturas / maxAp) * (EJE.abj - EJE.arr - 24),
    r: 2 + (p.aperturas / maxAp) * 2.5,
  })
  const elipses = c.grupos.map((g, i) => {
    const pts = c.puntos.filter((p) => p.grupo === i).map(pos)
    if (!pts.length) return null
    // Elipse centrada en la media con radio de 1.2 desviaciones estándar (acotada al área del gráfico)
    const media = (v) => v.reduce((s, x) => s + x, 0) / v.length
    const desv = (v, m) => Math.sqrt(media(v.map((x) => (x - m) ** 2)))
    const xs = pts.map((p) => p.x)
    const ys = pts.map((p) => p.y)
    const cx = media(xs)
    const cy = media(ys)
    return {
      color: g.color,
      cx,
      cy,
      rx: Math.min(desv(xs, cx) * 1.2 + 14, (EJE.der - EJE.izq) / 5),
      ry: Math.min(desv(ys, cy) * 1.2 + 12, (EJE.abj - EJE.arr) / 2.6),
    }
  })

  return (
    <Card
      className="card--clusteres"
      etiqueta="BIG DATA · PERIODO SELECCIONADO"
      titulo="Clústeres de Comportamiento"
      extra={
        <div className="cifra-header">
          <b>{c.total.toLocaleString('es-MX')}</b>
          <small>eventos procesados</small>
        </div>
      }
    >
      <div className="clusteres">
        <svg className="dispersion" viewBox={`0 0 ${ANCHO_D} ${ALTO_D}`} role="img" aria-label="Gráfico de dispersión de clústeres conductuales">
          {[0.25, 0.5, 0.75].map((f) => (
            <line key={f} x1={EJE.izq} x2={EJE.der} y1={EJE.arr + f * (EJE.abj - EJE.arr)} y2={EJE.arr + f * (EJE.abj - EJE.arr)} stroke="#edf1f5" />
          ))}
          <polyline points={`${EJE.izq},${EJE.arr} ${EJE.izq},${EJE.abj} ${EJE.der},${EJE.abj}`} fill="none" stroke="#e2e8f0" />
          <clipPath id="area-dispersion">
            <rect x={EJE.izq} y={0} width={EJE.der - EJE.izq + 40} height={EJE.abj} />
          </clipPath>
          <g clipPath="url(#area-dispersion)">
          {elipses.map(
            (e, i) =>
              e && (
                <ellipse key={i} cx={e.cx} cy={e.cy} rx={e.rx} ry={e.ry} fill={e.color} fillOpacity="0.08" stroke={e.color} strokeOpacity="0.35" strokeDasharray="3 3" />
              ),
          )}
          </g>
          {c.puntos.map((p) => {
            const { x, y, r } = pos(p)
            return (
              <circle key={p.id} cx={x} cy={y} r={r} fill={c.grupos[p.grupo].color}>
                <title>{`${p.app}: ${p.aperturas} aperturas · ${p.duracionMedia.toFixed(1)} min de media`}</title>
              </circle>
            )
          })}
          <text x="74" y="66" className="dispersion__eje">Aperturas</text>
          <text x="274" y="148" className="dispersion__eje">Duración media de sesión</text>
          {!c.puntos.length && (
            <text x="295" y="72" textAnchor="middle" className="dispersion__vacio">Sin eventos en el periodo</text>
          )}
        </svg>

        <ul className="leyenda-clusteres">
          {c.grupos.map((g) => (
            <li key={g.letra}>
              <span className="punto-color" style={{ background: g.color }} />
              <span>
                <b>Cluster {g.letra}</b>
                <small>{g.nombre}</small>
              </span>
              <strong>{g.porcentaje}%</strong>
            </li>
          ))}
        </ul>
      </div>
    </Card>
  )
}

// ---------- Riesgo ----------

function RiskCard({ r }) {
  return (
    <Card
      className="card--riesgo"
      etiqueta="IA EXPLICABLE · MAMDANI"
      titulo="Mapa de Riesgo de Recaída"
      extra={<Insignia>{r.analizados} eventos analizados</Insignia>}
    >
      <div className="riesgo">
        <div className="riesgo__mapa">
          <div className="escala">
            <small>BAJO</small>
            {['#f1f5f9', '#fde68a', '#fb923c', '#c2410c'].map((c) => (
              <span key={c} style={{ background: c }} />
            ))}
            <small>ALTO</small>
          </div>
          <div className="horas">
            {r.valores.map((v, h) => {
              const n = nivelRiesgo(v)
              return (
                <div key={h} className="hora" style={{ background: n.fondo, color: n.texto }} title={`${String(h).padStart(2, '0')}:00 · riesgo ${v}`}>
                  <b>{v}</b>
                  <small>{String(h).padStart(2, '0')}</small>
                </div>
              )
            })}
          </div>
          <div className="ventana">
            <span className="punto-color" style={{ background: '#ea580c' }} />
            <span>
              <b>{r.conDatos ? 'Ventana crítica detectada' : 'Aún no hay ventana crítica'}</b>
              <small>{r.conDatos ? `${r.ventana} · hora con más tiempo de uso` : 'Se calcula con los eventos de uso'}</small>
            </span>
          </div>
        </div>

        <div className="inferencia">
          <div className="inferencia__cabeza">
            <span className="inferencia__icono">
              <Icono src={iconoCerebro} tam={16} />
            </span>
            <span>
              <small>MOTOR DE INFERENCIA</small>
              <b>Regla activa #{String(r.regla.nivel * 3 - 2).padStart(2, '0')}</b>
            </span>
          </div>
          <pre className="codigo">
            <span className="kw">IF</span> uso_hora &gt; promedio{'\n'}
            <span className="kw">AND</span> time = {r.regla.hora}{'\n'}
            <span className="kw">THEN</span> Friction_Level = <b className="alto">{r.regla.etiquetaNivel}</b>
          </pre>
          <div className="inferencia__pie">
            <span className="mu">μ = {r.regla.mu}</span>
            <span className="nivel">Fricción Nivel {r.regla.nivel}</span>
          </div>
        </div>
      </div>
    </Card>
  )
}

// ---------- Semanal ----------

function WeeklyCard({ s }) {
  const max = Math.max(1, ...s.barras.flatMap((b) => [b.uso, b.objetivo ?? 0])) / 0.86
  const mejor = s.cambioPct != null && s.cambioPct <= 0
  return (
    <Card
      className="card--semanal"
      etiqueta="HÁBITO SEMANAL"
      titulo="Tiempo vs. Objetivo"
      extra={
        s.cambioPct != null && (
          <span className={`insignia${mejor ? '' : ' insignia--alerta'}`}>
            {s.cambioPct > 0 ? '+' : '−'}
            {Math.abs(s.cambioPct).toFixed(1)}%
          </span>
        )
      }
    >
      <div className="leyenda-barras">
        <span><i style={{ background: '#f59e0b' }} />Uso real</span>
        <span><i style={{ background: '#cbd5e1' }} />Objetivo</span>
      </div>
      <div className="barras">
        {s.barras.map((b, i) => (
          <div className="barras__dia" key={i}>
            <div className="barras__par" title={`${Math.round(b.uso)} min de uso${b.objetivo ? ` · objetivo ${Math.round(b.objetivo)} min` : ''}`}>
              <span className="barra barra--objetivo" style={{ height: `${((b.objetivo ?? 0) / max) * 100}%` }} />
              <span className="barra barra--uso" style={{ height: `${(b.uso / max) * 100}%` }} />
            </div>
            <small>{b.dia}</small>
          </div>
        ))}
      </div>
      <p className="nota">
        <Icono src={iconoPulso} tam={14} />
        {s.diferencia == null ? (
          <span>Sin plan activo: crea uno para comparar contra un objetivo.</span>
        ) : (
          <span>
            <b className={mejor ? 'ok' : 'alerta'}>{Math.round(Math.abs(s.diferencia))} min {mejor ? 'menos' : 'más'}</b> de uso promedio diario que el objetivo.
          </span>
        )}
      </p>
    </Card>
  )
}

// ---------- Uso ----------

function lineaFrecuencia(frecuencia) {
  const x0 = 5.62
  const x1 = 455.27
  const yArr = 23.96
  const yAbj = 136.17
  const max = Math.max(1, ...frecuencia.map((f) => f.sesiones))
  const pts = frecuencia.map((f, i) => [
    x0 + (i / (frecuencia.length - 1)) * (x1 - x0),
    yAbj - 0.08 * (yAbj - yArr) - (f.sesiones / max) * 0.92 * (yAbj - yArr),
  ])
  const linea = pts.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`).join(' ')
  const pico = pts[frecuencia.findIndex((f) => f.sesiones === max)] ?? pts[0]
  return { linea, area: `${linea} V${yAbj} H${x0} Z`, pico }
}

function UsageCard({ u }) {
  const { linea, area, pico } = lineaFrecuencia(u.frecuencia)
  let acumulado = 0
  const dona = u.categorias.length
    ? `conic-gradient(${u.categorias
        .map((c) => {
          const tramo = `${c.color} ${acumulado}% ${acumulado + c.porcentaje}%`
          acumulado += c.porcentaje
          return tramo
        })
        .join(', ')}, #e2e8f0 ${acumulado}% 100%)`
    : '#f1f5f9'
  const marcas = [0, 4, 8, 11].map((i) => `${String(u.frecuencia[i].hora).padStart(2, '0')}h`)

  return (
    <Card className="card--uso" etiqueta="APPS RESTRINGIDAS" titulo="Uso y Frecuencia de Sesiones" extra={<Insignia>Actualizado ahora</Insignia>}>
      <div className="uso">
        <div className="uso__resumen">
          <div className="dona" style={{ background: dona }}>
            <div className="dona__centro">
              <b>{formatoDuracion(u.totalMin)}</b>
              <small>uso total</small>
            </div>
          </div>
          <ul className="leyenda-categorias">
            {u.categorias.map((c) => (
              <li key={c.nombre}>
                <i style={{ background: c.color }} />
                <b>{c.nombre}</b>
                <span>{c.porcentaje}%</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="uso__frecuencia">
          <div className="uso__frecuencia-cabeza">
            <b>Frecuencia de sesiones</b>
            <small>Últimas 12 horas con actividad</small>
          </div>
          <svg viewBox="0 0 460.886 144.991" className="tendencia" role="img" aria-label="Tendencia de frecuencia de sesiones">
            <defs>
              <linearGradient id="relleno-tendencia" x1="0" y1="23.96" x2="0" y2="136.17" gradientUnits="userSpaceOnUse">
                <stop stopColor="#F59E0B" stopOpacity="0.25" />
                <stop offset="1" stopColor="#F59E0B" stopOpacity="0" />
              </linearGradient>
            </defs>
            <path d="M5.62 25.22H455.27M5.62 69.34H455.27M5.62 113.47H455.27" stroke="#EDF1F5" strokeWidth="1.19" />
            <path d={area} fill="url(#relleno-tendencia)" />
            <path d={linea} fill="none" stroke="#F59E0B" strokeWidth="2.98" strokeLinejoin="round" />
            <ellipse cx={pico[0]} cy={pico[1]} rx="5.62" ry="6.3" fill="white" stroke="#F59E0B" strokeWidth="2.38" />
          </svg>
          <div className="tendencia__horas">
            {marcas.map((m, i) => (
              <small key={i}>{m}</small>
            ))}
          </div>
        </div>
      </div>
    </Card>
  )
}

// ---------- Fricción ----------

function FrictionCard({ f }) {
  return (
    <Card className="card--friccion" etiqueta="INTERVENCIONES" titulo="Éxito por Nivel" extra={<Insignia>{f.global}% global</Insignia>}>
      <div className="prevenidas">
        <b>{f.prevenidas}</b>
        <span>recaídas prevenidas</span>
        <small>de {f.total} pausas en el periodo</small>
      </div>
      <ul className="niveles">
        {f.niveles.map((n) => (
          <li key={n.nivel}>
            <span className="niveles__num" style={{ background: n.fondo, color: n.texto }}>{n.nivel}</span>
            <span className="niveles__nombre">
              <b>Nivel {n.nivel}</b>
              <small>{n.nombre}</small>
            </span>
            <span className="niveles__pista">
              <span style={{ width: `${n.exito}%` }} />
            </span>
            <span className="niveles__cifra">
              <b>{n.total}</b>
              <small>{n.exito}%</small>
            </span>
          </li>
        ))}
      </ul>
    </Card>
  )
}

// ---------- Página ----------

const TARJETAS = [
  { id: 'telemetria', claves: 'telemetria android dispositivo heartbeat pipeline', C: TelemetryCard, prop: 't', dato: 'telemetria' },
  { id: 'clusteres', claves: 'clusteres big data comportamiento aperturas', C: ClusterCard, prop: 'c', dato: 'clusteres' },
  { id: 'riesgo', claves: 'riesgo recaida mamdani ia hora fricción', C: RiskCard, prop: 'r', dato: 'riesgo' },
  { id: 'semanal', claves: 'semanal habito tiempo objetivo plan', C: WeeklyCard, prop: 's', dato: 'semanal' },
  { id: 'uso', claves: 'uso frecuencia sesiones apps categorias', C: UsageCard, prop: 'u', dato: 'uso' },
  { id: 'friccion', claves: 'friccion intervenciones pausas nivel exito', C: FrictionCard, prop: 'f', dato: 'friccion' },
]

const normalizar = (s) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()

export default function PanelGeneral({ panel, busqueda }) {
  const q = normalizar(busqueda.trim())
  return (
    <div className="panel">
      {TARJETAS.map((t) => {
        const Tarjeta = t.C
        return (
          <div key={t.id} className={`panel__celda panel__celda--${t.id}${q && !normalizar(t.claves).includes(q) ? ' panel__celda--atenuada' : ''}`}>
            <Tarjeta {...{ [t.prop]: panel[t.dato] }} />
          </div>
        )
      })}
    </div>
  )
}
