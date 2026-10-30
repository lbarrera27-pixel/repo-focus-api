import { useMemo, useState } from 'react'
import Icono from '../components/Icono.jsx'
import iconoExportar from '../assets/icons/bd-exportar.svg'
import iconoCluster from '../assets/icons/bd-cluster.svg'
import iconoSimilitud from '../assets/icons/bd-similitud.svg'
import iconoMuestra from '../assets/icons/bd-muestra.svg'
import iconoAbandono from '../assets/icons/bd-abandono.svg'
import iconoBase from '../assets/icons/bd-base.svg'
import iconoArquetipo from '../assets/icons/bd-arquetipo.svg'
import iconoPico from '../assets/icons/bd-pico.svg'
import iconoResistencia from '../assets/icons/bd-resistencia.svg'
import iconoRespiracion from '../assets/icons/bd-respiracion.svg'
import iconoRecReloj from '../assets/icons/bd-rec-reloj.svg'
import iconoRecEscudo from '../assets/icons/bd-rec-escudo.svg'
import iconoRecChevron from '../assets/icons/bd-rec-chevron.svg'
import iconoRecInfo from '../assets/icons/bd-rec-info.svg'
import { construirClusteres } from '../data/clusteres.js'
import { api } from '../api.js'
import './Clusteres.css'

const PERIODOS_BD = [
  { id: 'hoy', etiqueta: '24h' },
  { id: '7d', etiqueta: '7D' },
  { id: '30d', etiqueta: '30D' },
  { id: 'semestre', etiqueta: 'Piloto' },
]

function iniciales(nombre = '') {
  return nombre.split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0].toUpperCase()).join('') || '?'
}

const fmt = (n) => n.toLocaleString('es-MX')

// ---------- Cabecera ----------

function Cabecera({ usuario, eventos, periodo, onPeriodo, onExportar, error }) {
  return (
    <header className="topbar topbar--seccion bd-topbar">
      <div className="topbar__titulos">
        <p className="topbar__ruta">FOCUS! CLOUD / BIG DATA / SEGMENTACIÓN</p>
        <h1 className="topbar__titulo bd-titulo">FOCUS! Big Data Engine — Segmentación de Patrones de Uso</h1>
        <p className="topbar__desc">Clustering conductual de tus días de uso y recomendaciones adaptativas.</p>
      </div>
      <div className="topbar__acciones ia-acciones">
        <span className={`estado estado--chip ia-modelo${error ? ' estado--error' : ''}`}>
          <span className="estado__punto" aria-hidden="true" />
          {error ? `Error: ${error}` : `${fmt(eventos)} puntos de datos procesados`}
        </span>
        <div className="segmentado segmentado--ia" role="group" aria-label="Periodo">
          {PERIODOS_BD.map((p) => (
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
        <button type="button" className="boton-primario ia-exportar" onClick={onExportar}>
          <Icono src={iconoExportar} tam={15} />
          Exportar análisis
        </button>
        <span className="avatar avatar--bd" title={usuario.nombre}>{iniciales(usuario.nombre)}</span>
      </div>
    </header>
  )
}

// ---------- KPIs ----------

function Kpis({ c }) {
  const g = c.tu && c.grupos[c.tu.grupo]
  const max = Math.max(1, ...c.aperturasRecientes)
  return (
    <div className="bd-kpis">
      <article className="bd-kpi bd-kpi--cluster">
        <span className="bd-kpi__icono" style={{ background: '#fef3c7' }}><Icono src={iconoCluster} tam={21} /></span>
        <div className="bd-kpi__cuerpo">
          <small className="micro">CLÚSTER ASIGNADO AL USUARIO</small>
          <b>{g ? `Clúster ${g.letra}` : '—'}</b>
          <p>{g ? `Usuario ${g.corto}` : 'Se necesitan al menos 6 días con actividad'}</p>
        </div>
        {g && <span className="bd-kpi__letra">{g.letra}</span>}
      </article>

      <article className="bd-kpi">
        <span className="bd-kpi__icono" style={{ background: '#e0f2fe' }}><Icono src={iconoSimilitud} tam={21} /></span>
        <div className="bd-kpi__cuerpo">
          <small className="micro">ÍNDICE DE SIMILITUD</small>
          <b>
            {c.similitud ?? '—'}
            <span>%</span>
          </b>
          <p>de coincidencia con el grupo</p>
        </div>
        {c.deltaSimilitud != null && (
          <span className={`bd-kpi__chip${c.deltaSimilitud < 0 ? ' bd-kpi__chip--baja' : ''}`}>
            {c.deltaSimilitud >= 0 ? '+' : '−'}
            {Math.abs(c.deltaSimilitud)} pts
          </span>
        )}
      </article>

      <article className="bd-kpi">
        <span className="bd-kpi__icono" style={{ background: '#d1fae5' }}><Icono src={iconoMuestra} tam={21} /></span>
        <div className="bd-kpi__cuerpo">
          <small className="micro">MUESTRA ANALIZADA</small>
          <b>{fmt(c.dias)}</b>
          <p>días con actividad en el periodo</p>
        </div>
        <div className="bd-kpi__barras" title="Aperturas por día (últimos 9 días)">
          {c.aperturasRecientes.map((v, i) => (
            <span key={i} style={{ height: 6 + (v / max) * 11 }} />
          ))}
        </div>
      </article>

      <article className="bd-kpi">
        <span className="bd-kpi__icono" style={{ background: '#ffe4e6' }}><Icono src={iconoAbandono} tam={21} /></span>
        <div className="bd-kpi__cuerpo">
          <small className="micro">PROBABILIDAD DE ABANDONO</small>
          <b>
            {c.abandono ?? '—'}
            <span>%</span>
          </b>
          <p>de días por encima del límite del plan</p>
        </div>
        <span className={`bd-kpi__chip bd-kpi__chip--${c.nivelAbandono === 'BAJA' ? 'ok' : 'alerta'}`}>{c.nivelAbandono}</span>
      </article>
    </div>
  )
}

// ---------- Dispersión ----------

const SX = (x) => 462 + (x / 50) * 306
const SY = (y) => 148.5 - (y / 50) * 123.5

function Dispersion({ c, aislado, onAislar }) {
  const visible = (j) => aislado == null || aislado === j
  return (
    <section className="card bd-dispersion">
      <header className="card__header card__header--tel">
        <div className="card__titulos">
          <p className="card__etiqueta">CLUSTERING K-MEANS · PROYECCIÓN ESTANDARIZADA</p>
          <h2 className="card__titulo card__titulo--tel">Mapa de Dispersión Conductual</h2>
          <p className="ia-difuso__sub">Cada punto es un día de uso; ejes normalizados (z-score).</p>
        </div>
        <div className="bd-dispersion__acciones">
          <button type="button" className={`bd-todos${aislado == null ? ' bd-todos--activo' : ''}`} onClick={() => onAislar(null)}>
            Todos
          </button>
          <small>{c.suficiente ? `k = ${c.k} · Silhouette ${c.silhouette.toFixed(2)}` : 'k-means requiere 6+ días'}</small>
        </div>
      </header>

      <div className="bd-dispersion__cuerpo">
        <div className="bd-mapa">
          <svg viewBox="0 0 876 307" className="bd-mapa__svg" role="img" aria-label="Dispersión de días por clúster">
            <defs>
              <radialGradient id="bd-brillo">
                <stop offset="0" stopColor="#f59e0b" stopOpacity="0.55" />
                <stop offset="1" stopColor="#f59e0b" stopOpacity="0" />
              </radialGradient>
            </defs>
            {Array.from({ length: 11 }, (_, i) => -50 + i * 10).map((v) => (
              <g key={v}>
                <line x1={SX(v)} x2={SX(v)} y1={SY(50)} y2={SY(-50)} stroke={v === 0 ? '#cbd5e1' : '#f1f5f9'} />
                <line x1={SX(-50)} x2={SX(50)} y1={SY(v)} y2={SY(v)} stroke={v === 0 ? '#cbd5e1' : '#f1f5f9'} />
              </g>
            ))}
            {[-50, -40, -30, -20, -10, 0, 10, 20, 30, 40, 50].map((v) => (
              <text key={`x${v}`} x={SX(v)} y="289" textAnchor="middle" className="bd-eje">{v < 0 ? `−${-v}` : v}</text>
            ))}
            {[-50, -30, -10, 10, 30, 50].map((v) => (
              <text key={`y${v}`} x="146" y={SY(v) + 4} textAnchor="end" className="bd-eje">{v < 0 ? `−${-v}` : v}</text>
            ))}
            <text x="462" y="304" textAnchor="middle" className="bd-eje-titulo">Aperturas por día</text>
            <text x="8" y="150" textAnchor="middle" transform="rotate(-90 8 150)" className="bd-eje-titulo">% de uso nocturno (20:00–02:00)</text>

            {c.grupos.map((g, j) => (
              <ellipse
                key={g.letra}
                cx={SX(g.centro.x)}
                cy={SY(g.centro.y)}
                rx={(Math.min(g.radio.x, 45) / 50) * 306}
                ry={(Math.min(g.radio.y, 45) / 50) * 123.5}
                fill={g.color}
                fillOpacity={visible(j) ? 0.08 : 0.02}
                stroke={g.color}
                strokeOpacity={visible(j) ? 0.45 : 0.1}
                strokeDasharray="4 3"
              />
            ))}
            {c.puntos.map((p) => (
              <circle
                key={p.dia}
                cx={SX(p.x)}
                cy={SY(p.y)}
                r={2.6 + Math.min(2.6, p.aperturas / 10)}
                fill={c.grupos[p.grupo]?.color ?? '#94a3b8'}
                opacity={visible(p.grupo) ? 0.9 : 0.12}
              >
                <title>{`${p.dia}: ${p.aperturas} aperturas · ${Math.round(p.nocturno)}% nocturno`}</title>
              </circle>
            ))}
            {c.grupos.map((g, j) => (
              <g key={`c${g.letra}`} opacity={visible(j) ? 1 : 0.2}>
                <circle cx={SX(g.centro.x)} cy={SY(g.centro.y)} r="8.5" fill="#fff" stroke={g.color} strokeWidth="1.8" />
                <path d={`M${SX(g.centro.x) - 4} ${SY(g.centro.y)}h8M${SX(g.centro.x)} ${SY(g.centro.y) - 4}v8`} stroke={g.color} strokeWidth="1.6" />
              </g>
            ))}
            {c.tu && (
              <g>
                <circle cx={SX(c.tu.x)} cy={SY(c.tu.y)} r="17" fill="url(#bd-brillo)" />
                <circle cx={SX(c.tu.x)} cy={SY(c.tu.y)} r="7" fill="#0f172a" stroke="#fff" strokeWidth="1.5" />
                <text x={SX(c.tu.x)} y={SY(c.tu.y) + 2.3} textAnchor="middle" className="bd-tu">TU</text>
                <line x1={SX(c.tu.x) + 6} y1={SY(c.tu.y) - 6} x2={SX(c.tu.x) + 20} y2={SY(c.tu.y) - 20} stroke="#b45309" />
                <rect x={Math.min(SX(c.tu.x) + 18, 800)} y={SY(c.tu.y) - 37} width="66" height="17" rx="5" fill="#0f172a" />
                <text x={Math.min(SX(c.tu.x) + 18, 800) + 33} y={SY(c.tu.y) - 25.5} textAnchor="middle" className="bd-tu-etiqueta">TU PERFIL</text>
              </g>
            )}
          </svg>
        </div>

        <div className="bd-arquetipos">
          <div className="bd-arquetipos__cabeza">
            <b>Arquetipos detectados</b>
            <small>Selecciona para aislar</small>
          </div>
          {c.grupos.length ? (
            c.grupos.map((g, j) => (
              <button
                key={g.letra}
                type="button"
                className={`bd-arquetipo${aislado === j ? ' bd-arquetipo--activo' : ''}`}
                aria-pressed={aislado === j}
                onClick={() => onAislar(aislado === j ? null : j)}
              >
                <i style={{ background: g.color }} />
                <span>
                  <b>Cluster {g.letra}</b>
                  <small>{g.nombre}</small>
                  <code>C ({g.centro.x.toFixed(1)}, {g.centro.y.toFixed(1)})</code>
                </span>
                <strong>{g.porcentaje}%</strong>
              </button>
            ))
          ) : (
            <p className="vacio">Aún no hay suficientes días con actividad para agrupar.</p>
          )}
          <div className="bd-muestra">
            <span><Icono src={iconoBase} tam={15} /></span>
            <span>
              <small>MUESTRA VISUALIZADA</small>
              <b>{fmt(c.dias)} días · {fmt(c.eventos)} eventos</b>
            </span>
          </div>
        </div>
      </div>
    </section>
  )
}

// ---------- Perfil del arquetipo ----------

function Perfil({ c }) {
  const g = c.tu && c.grupos[c.tu.grupo]
  const r = c.rasgos
  const nivelFranja = r.factorFranja == null ? '—' : r.factorFranja >= 2 ? 'ALTO' : r.factorFranja >= 1.3 ? 'MEDIO' : 'BAJO'
  const diff = (a, b) => (a == null || b == null ? '—' : `${a - b >= 0 ? '+' : '−'}${Math.abs(a - b)}%`)
  const nombre = g?.corto.split(' / ') ?? ['Sin', 'arquetipo']
  return (
    <section className="card bd-perfil">
      <header className="card__header card__header--tel bd-cabeza60">
        <div className="card__titulos">
          <p className="card__etiqueta">ARQUETIPO ACTUAL</p>
          <h2 className="card__titulo card__titulo--tel">Perfil del Arquetipo Actual</h2>
        </div>
        <span className="bd-etiqueta-ambar">{g ? `CLÚSTER ${g.letra}` : 'SIN CLÚSTER'}</span>
      </header>
      <div className="bd-perfil__cuerpo">
        <div className="bd-perfil__tarjeta">
          <span className="bd-perfil__icono"><Icono src={iconoArquetipo} tam={24} /></span>
          <b>
            {nombre[0]}
            {nombre[1] && (
              <>
                {' /'}
                <br />
                {nombre[1]}
              </>
            )}
          </b>
          <small>{c.similitud != null ? `Confianza de asignación ${c.similitud}%` : 'Sin datos suficientes'}</small>
        </div>
        <ul className="bd-rasgos">
          <li>
            <span style={{ background: '#fef3c7' }}><Icono src={iconoPico} tam={15} /></span>
            <span>
              <b>Picos de uso entre {r.franja.replace(' — ', ' y ')} hrs</b>
              <small>{r.factorFranja ? `Actividad en esa franja ${r.factorFranja}× sobre tu promedio por hora.` : 'Sin datos suficientes.'}</small>
            </span>
            <em>{nivelFranja}</em>
          </li>
          <li>
            <span style={{ background: '#ffe4e6' }}><Icono src={iconoResistencia} tam={15} /></span>
            <span>
              <b>Respuesta a Fricción Nivel 1</b>
              <small>{r.n1 != null ? `${r.n1}% de abandono voluntario con pausas simples.` : 'Sin pausas de nivel 1 en el periodo.'}</small>
            </span>
            <em>{diff(r.n1, r.global)}</em>
          </li>
          <li>
            <span style={{ background: '#e0f2fe' }}><Icono src={iconoRespiracion} tam={15} /></span>
            <span>
              <b>Respuesta a respiración guiada</b>
              <small>{r.n2 != null ? `Nivel 2 lleva el abandono voluntario a ${r.n2}%.` : 'Sin pausas de nivel 2 en el periodo.'}</small>
            </span>
            <em>{diff(r.n2, r.n1)}</em>
          </li>
        </ul>
      </div>
    </section>
  )
}

// ---------- Recomendaciones ----------

function Recomendaciones({ recs, usuario, onAplicado }) {
  const [estado, setEstado] = useState({})

  async function aplicar(rec) {
    setEstado((e) => ({ ...e, [rec.id]: { cargando: true } }))
    try {
      if (usuario.demo) {
        await new Promise((r) => setTimeout(r, 400))
      } else if (rec.accion.tipo === 'app') {
        await api.actualizarApp(usuario.id, rec.accion.numero, rec.accion.cambios)
      } else {
        await api.crearAjuste(usuario.id, rec.accion.numero, rec.accion.cuerpo)
      }
      setEstado((e) => ({ ...e, [rec.id]: { listo: true } }))
      if (!usuario.demo) onAplicado()
    } catch (err) {
      setEstado((e) => ({ ...e, [rec.id]: { error: err.status === 409 ? 'Ya registrado' : err.message || 'Sin conexión' } }))
    }
  }

  return (
    <section className="card bd-recs">
      <header className="card__header card__header--tel bd-cabeza60">
        <div className="card__titulos">
          <p className="card__etiqueta">BIG DATA · RECOMENDACIONES</p>
          <h2 className="card__titulo card__titulo--tel">Intervenciones Dinámicas de IA</h2>
        </div>
        <span className="bd-etiqueta-azul">
          <i /> {recs.length} propuesta{recs.length === 1 ? '' : 's'}
        </span>
      </header>
      <div className="bd-recs__lista">
        {recs.length ? (
          recs.map((rec) => {
            const e = estado[rec.id] ?? {}
            const hecho = e.listo || rec.registrada
            return (
              <article key={rec.id} className="bd-rec">
                <span className="bd-rec__icono">
                  <Icono src={rec.icono === 'reloj' ? iconoRecReloj : iconoRecEscudo} tam={17} />
                </span>
                <span className="bd-rec__texto">
                  <b>{rec.titulo}</b>
                  <small>{e.error ? `No se aplicó: ${e.error}` : rec.detalle}</small>
                </span>
                <em>{rec.impacto}</em>
                <button type="button" className="bd-rec__boton" onClick={() => aplicar(rec)} disabled={hecho || e.cargando}>
                  {e.cargando ? 'Aplicando…' : hecho ? (usuario.demo && e.listo ? 'Hecho (demo)' : rec.registrada && !e.listo ? 'Registrado' : 'Aplicado') : 'Aplicar'}
                  {!hecho && !e.cargando && <Icono src={iconoRecChevron} tam={13} />}
                </button>
              </article>
            )
          })
        ) : (
          <p className="vacio">Sin propuestas: hace falta un plan activo y eventos en la franja vulnerable.</p>
        )}
      </div>
      <p className="bd-recs__nota">
        <Icono src={iconoRecInfo} tam={15} />
        <span>Las recomendaciones se recalculan con cada carga según tu clúster, tu franja vulnerable y tu adherencia.</span>
      </p>
    </section>
  )
}

// ---------- Página ----------

export default function Clusteres({ usuario, datos, periodo, onPeriodo, error, onRecargar }) {
  const c = useMemo(() => (datos ? construirClusteres(datos) : null), [datos])
  const [aislado, setAislado] = useState(null)

  function exportar() {
    if (!c) return
    const { puntos, grupos, tu, silhouette, recomendaciones } = c
    const url = URL.createObjectURL(new Blob([JSON.stringify({ periodo: datos.periodo, desde: datos.desde, hasta: datos.hasta, silhouette, grupos, tu, puntos, recomendaciones }, null, 2)], { type: 'application/json' }))
    Object.assign(document.createElement('a'), { href: url, download: `focus-clusteres_${datos.desde}_${datos.hasta}.json` }).click()
    URL.revokeObjectURL(url)
  }

  return (
    <>
      <Cabecera usuario={usuario} eventos={c?.eventos ?? 0} periodo={periodo} onPeriodo={onPeriodo} onExportar={exportar} error={error} />
      {c ? (
        <div className="bd">
          <Kpis c={c} />
          <Dispersion c={c} aislado={aislado} onAislar={setAislado} />
          <div className="bd-fila">
            <Perfil c={c} />
            <Recomendaciones recs={c.recomendaciones} usuario={usuario} onAplicado={onRecargar} />
          </div>
        </div>
      ) : (
        <div className="panel panel--una">
          <p className="vacio">
            {error ? (
              <>
                No se pudieron cargar los datos. <button type="button" className="enlace" onClick={onRecargar}>Reintentar</button>
              </>
            ) : (
              'Cargando clústeres…'
            )}
          </p>
        </div>
      )}
    </>
  )
}
