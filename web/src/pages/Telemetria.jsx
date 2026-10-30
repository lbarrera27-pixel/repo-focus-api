import { useCallback, useEffect, useMemo, useState } from 'react'
import Icono from '../components/Icono.jsx'
import iconoDispositivo from '../assets/icons/tel-dispositivo.svg'
import iconoBateria from '../assets/icons/tel-bateria.svg'
import iconoHeartbeat from '../assets/icons/tel-heartbeat.svg'
import iconoServicio from '../assets/icons/tel-servicio.svg'
import iconoPermisos from '../assets/icons/tel-permisos.svg'
import iconoCheck from '../assets/icons/tel-check.svg'
import iconoAndroid from '../assets/icons/pipe-android.svg'
import iconoNube from '../assets/icons/pipe-cloud.svg'
import iconoAnalytics from '../assets/icons/pipe-analytics.svg'
import iconoLake from '../assets/icons/pipe-lake.svg'
import iconoFlecha from '../assets/icons/pipe-flecha.svg'
import iconoLogCheck from '../assets/icons/log-check.svg'
import iconoWifi from '../assets/icons/red-wifi.svg'
import iconoSync from '../assets/icons/red-sync.svg'
import { cargarTelemetria, construirTelemetria } from '../data/telemetria.js'
import { haceCuanto } from '../data/panel.js'
import './Telemetria.css'

const INTERVALOS = [
  { etiqueta: '1 min', ms: 60_000 },
  { etiqueta: '5 min', ms: 300_000 },
]

function iniciales(nombre = '') {
  return nombre.split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0].toUpperCase()).join('') || '?'
}

function Cabecera({ usuario, ok }) {
  return (
    <header className="topbar topbar--seccion">
      <div className="topbar__titulos">
        <p className="topbar__ruta">
          FOCUS! CLOUD <span>/</span> TELEMETRÍA <span>/</span> ANDROID
        </p>
        <h1 className="topbar__titulo topbar__titulo--grande">Telemetría Cloud y Dispositivo Android</h1>
        <p className="topbar__desc">Supervisión técnica del cliente móvil, permisos y eventos de ingesta.</p>
      </div>
      <div className="topbar__acciones">
        <span className="chip">{usuario.demo ? 'ENTORNO · DEMO' : 'ENTORNO · PILOTO UAQ'}</span>
        <span className={`estado estado--chip${ok ? '' : ' estado--error'}`}>
          <span className="estado__punto" aria-hidden="true" />
          {ok ? 'Nube sincronizada' : 'Sin conexión con la nube'}
        </span>
        <span className="avatar" title={usuario.nombre}>{iniciales(usuario.nombre)}</span>
      </div>
    </header>
  )
}

function Metrica({ icono, etiqueta, children }) {
  return (
    <div className="tel-metrica">
      <span className="tel-metrica__icono">
        <Icono src={icono} tam={19} />
      </span>
      <div className="tel-metrica__cuerpo">
        <small className="micro">{etiqueta}</small>
        {children}
      </div>
    </div>
  )
}

function EstadoDispositivo({ d }) {
  return (
    <section className="card tel-dispositivo">
      <header className="card__header card__header--tel">
        <div className="card__titulos">
          <p className="card__etiqueta">HARDWARE &amp; RUNTIME</p>
          <h2 className="card__titulo card__titulo--tel">Estado del dispositivo vinculado</h2>
        </div>
        <span className={`insignia insignia--vivo${d.vivo ? '' : ' insignia--apagada'}`}>
          <span className="estado__punto" aria-hidden="true" />
          {d.vivo ? 'MONITOREO EN VIVO' : 'SIN ACTIVIDAD 24 H'}
        </span>
      </header>

      <div className="tel-dispositivo__fila">
        <div className="tel-principal">
          <span className="tel-principal__telefono">
            <Icono src={iconoDispositivo} tam={31} />
            <span className={`tel-principal__led${d.principal ? '' : ' tel-principal__led--off'}`} />
          </span>
          <div className="tel-principal__texto">
            <small className="micro">DISPOSITIVO PRINCIPAL</small>
            <h3>{d.principal?.nombre ?? 'Sin dispositivo'}</h3>
            <p>{d.principal?.detalle ?? 'La app Android registra su token al iniciar sesión.'}</p>
            <span className={`tel-principal__conexion${d.principal ? '' : ' tel-principal__conexion--off'}`}>
              <i /> {d.principal ? 'Token activo en la nube' : 'Sin token activo'}
            </span>
          </div>
        </div>

        <Metrica icono={iconoBateria} etiqueta="USO DE HOY VS. LÍMITE">
          <b className="tel-metrica__valor">{d.uso.pct != null ? `${d.uso.pct}%` : `${d.uso.minutos} min`}</b>
          <span className="tel-barra">
            <span style={{ width: `${Math.min(100, d.uso.pct ?? 0)}%`, background: (d.uso.pct ?? 0) > 100 ? '#ef4444' : '#10b981' }} />
          </span>
          <small className="tel-metrica__nota">
            {d.uso.limite ? `${d.uso.minutos} de ${d.uso.limite} min del plan` : 'Sin plan activo'}
          </small>
        </Metrica>

        <Metrica icono={iconoHeartbeat} etiqueta="CLOUD HEARTBEAT">
          <b className={`tel-metrica__valor ${d.vivo ? 'ok' : 'apagado'}`}>{d.vivo ? 'Active' : 'Idle'}</b>
          <small className="tel-metrica__nota">
            <i className={`punto ${d.vivo ? 'punto--ok' : 'punto--off'}`} /> Último evento: {d.heartbeat.toLowerCase()}
          </small>
        </Metrica>

        <Metrica icono={iconoServicio} etiqueta="API FOCUS! · APP SERVICE">
          <code className="tel-codigo">{d.api.base}</code>
          <span className={`tel-etiqueta ${d.api.ok ? '' : 'tel-etiqueta--error'}`}>
            {d.api.ok ? `RUNNING · ${d.api.motor}` : 'DOWN'}
          </span>
        </Metrica>

        <div className="tel-permisos">
          <div className="tel-permisos__cabeza">
            <span className="tel-metrica__icono">
              <Icono src={iconoPermisos} tam={19} />
            </span>
            <span>
              <small className="micro">TOKENS DE DISPOSITIVO</small>
              <b>
                {d.tokensActivos} de {d.tokensTotal} activos
              </b>
            </span>
          </div>
          <ul>
            {d.tokens.length ? (
              d.tokens.map((t) => (
                <li key={t.nombre}>
                  <Icono src={iconoCheck} tam={12} />
                  <span>{t.nombre}</span>
                  <em className={t.activo ? '' : 'off'}>{t.activo ? 'Granted' : 'Revoked'}</em>
                </li>
              ))
            ) : (
              <li className="vacio-li">Aún no hay tokens registrados.</li>
            )}
          </ul>
        </div>
      </div>
    </section>
  )
}

const CLASE_TIPO = { APP_OPEN: 'tipo--app', FRICTION_TRIGGERED: 'tipo--friccion', SCREEN_UNLOCK: 'tipo--unlock' }

function Pipeline({ p, registros, enVivo }) {
  const pasos = [
    { icono: iconoAndroid, titulo: 'Android Client', sub: `${p.apps} apps monitoreadas` },
    { icono: iconoNube, titulo: 'Cloud Ingestion', sub: 'FastAPI · validación + ACK', arista: 'HTTPS/TLS 1.3' },
    { icono: iconoAnalytics, titulo: 'Analytics Stream', sub: 'Functions · ajuste semanal', arista: 'ORM' },
    { icono: iconoLake, titulo: 'Research Lake', sub: `Azure SQL · ${p.motor}`, arista: 'Write' },
  ]
  return (
    <section className="card tel-pipeline">
      <header className="card__header card__header--tel">
        <div className="card__titulos">
          <p className="card__etiqueta">DATA INGESTION PIPELINE</p>
          <h2 className="card__titulo card__titulo--tel">Flujo de eventos en tiempo real</h2>
        </div>
        <div className="tel-kpis">
          <div>
            <small className="micro">EVENTOS PROCESADOS HOY</small>
            <b>{p.eventosHoy.toLocaleString('es-MX')}</b>
          </div>
          <i />
          <div>
            <small className="micro">LATENCIA DE SINCRONIZACIÓN</small>
            <b>
              {p.latenciaMs ?? '—'}
              <span>ms</span>
            </b>
          </div>
          <i />
          <div>
            <small className="micro">THROUGHPUT DE HOY</small>
            <b className="ok">
              {p.porHora}
              <span> evt/h</span>
            </b>
          </div>
        </div>
      </header>

      <div className="tel-flujo">
        {pasos.map((paso, i) => (
          <div className="tel-flujo__paso" key={paso.titulo}>
            {i > 0 && (
              <span className="tel-flujo__arista" aria-hidden="true">
                <small>{paso.arista}</small>
                <span className="tel-flujo__linea" />
                <Icono src={iconoFlecha} tam={13} />
              </span>
            )}
            <span className="tel-metrica__icono tel-metrica__icono--chico">
              <Icono src={paso.icono} tam={16} />
            </span>
            <span className="tel-flujo__texto">
              <b>{paso.titulo}</b>
              <small>{paso.sub}</small>
            </span>
          </div>
        ))}
      </div>

      <div className="terminal">
        <div className="terminal__barra">
          <span className="terminal__luces">
            <i style={{ background: '#ef4444' }} />
            <i style={{ background: '#f59e0b' }} />
            <i style={{ background: '#10b981' }} />
            <code>focus-cloud / telemetry-stream</code>
          </span>
          <span className={`terminal__vivo${enVivo ? '' : ' terminal__vivo--off'}`}>
            <i /> {enVivo ? 'LIVE TAIL' : 'PAUSADO'}
          </span>
        </div>
        <table className="terminal__tabla">
          <thead>
            <tr>
              <th>TIMESTAMP</th>
              <th>EVENT TYPE</th>
              <th>TARGET PACKAGE</th>
              <th>DETALLE</th>
              <th>REGISTRO</th>
              <th>CLOUD SYNC</th>
            </tr>
          </thead>
          <tbody>
            {registros.length ? (
              registros.map((r) => (
                <tr key={r.clave}>
                  <td><code>{r.hora}</code></td>
                  <td><span className={`tipo ${CLASE_TIPO[r.tipo]}`}>{r.tipo}</span></td>
                  <td><code>{r.paquete}</code></td>
                  <td>{r.detalle}</td>
                  <td><code>{r.registro}</code></td>
                  <td>
                    <span className="ack">
                      <i /> <Icono src={iconoLogCheck} tam={11} /> Ack: 200 OK
                    </span>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={6} className="terminal__vacio">Sin eventos en los últimos 7 días.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function ControlesRed({ autoActualizar, onAuto, intervalo, onIntervalo, pesoKB, ultimaSync, apiBase, onForzar, sincronizando }) {
  const host = apiBase.replace(/^https?:\/\//, '')
  return (
    <section className="card tel-red">
      <div className="tel-red__titulo">
        <p className="card__etiqueta">DATA CACHING &amp; NETWORK</p>
        <h2 className="card__titulo card__titulo--tel">Política de sincronización</h2>
        <p className="tel-red__desc">Configura cada cuánto este portal consulta la telemetría en la nube.</p>
      </div>

      <div className="tel-red__opcion">
        <span className="tel-red__icono">
          <Icono src={iconoWifi} tam={20} />
        </span>
        <span>
          <b>Actualización automática</b>
          <small>Mantiene la bitácora en vivo.</small>
        </span>
        <button
          type="button"
          role="switch"
          aria-checked={autoActualizar}
          aria-label="Actualización automática"
          className={`switch${autoActualizar ? ' switch--on' : ''}`}
          onClick={() => onAuto(!autoActualizar)}
        >
          <span />
        </button>
      </div>

      <div className="tel-red__intervalo">
        <small className="micro micro--normal">FRECUENCIA DE MUESTREO</small>
        <b>Intervalo de consulta</b>
        <div className="segmentado segmentado--chico" role="group" aria-label="Intervalo de consulta">
          {INTERVALOS.map((i) => (
            <button
              key={i.ms}
              type="button"
              className={`segmentado__opcion${i.ms === intervalo ? ' segmentado__opcion--activa' : ''}`}
              aria-pressed={i.ms === intervalo}
              onClick={() => onIntervalo(i.ms)}
            >
              {i.etiqueta}
            </button>
          ))}
        </div>
      </div>

      <dl className="tel-red__datos">
        <div>
          <dt>CACHÉ LOCAL</dt>
          <dd>{pesoKB} KB</dd>
        </div>
        <div>
          <dt>ÚLTIMA SYNC</dt>
          <dd>{ultimaSync}</dd>
        </div>
        <div>
          <dt>API ACTUAL</dt>
          <dd title={apiBase}>{host}</dd>
        </div>
      </dl>

      <button type="button" className="boton-primario tel-red__boton" onClick={onForzar} disabled={sincronizando}>
        <Icono src={iconoSync} tam={17} />
        {sincronizando ? 'Sincronizando…' : 'Forzar sincronización inmediata'}
      </button>
    </section>
  )
}

export default function Telemetria({ usuario, onSesionInvalida }) {
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState(null)
  const [cargando, setCargando] = useState(false)
  const [autoActualizar, setAuto] = useState(true)
  const [intervalo, setIntervalo] = useState(INTERVALOS[0].ms)
  const [ahora, setAhora] = useState(Date.now())

  const cargar = useCallback(async () => {
    setCargando(true)
    try {
      setDatos(await cargarTelemetria(usuario))
      setError(null)
    } catch (err) {
      if (err.status === 401) return onSesionInvalida()
      setError(err.status ? err.message : 'No se pudo conectar con la API')
    } finally {
      setCargando(false)
      setAhora(Date.now())
    }
  }, [usuario, onSesionInvalida])

  useEffect(() => {
    cargar()
  }, [cargar])

  // Consulta periódica mientras la actualización automática esté encendida
  useEffect(() => {
    if (!autoActualizar) return
    const id = setInterval(cargar, intervalo)
    return () => clearInterval(id)
  }, [autoActualizar, intervalo, cargar])

  // Reloj para "Última sync: hace X"
  useEffect(() => {
    const id = setInterval(() => setAhora(Date.now()), 15_000)
    return () => clearInterval(id)
  }, [])

  const vista = useMemo(() => (datos ? construirTelemetria(datos, ahora) : null), [datos, ahora])
  const ok = Boolean(vista?.dispositivo.api.ok) && !error

  return (
    <>
      <Cabecera usuario={usuario} ok={ok} />
      {vista ? (
        <div className="tel">
          <EstadoDispositivo d={vista.dispositivo} />
          <Pipeline p={vista.pipeline} registros={vista.registros} enVivo={autoActualizar} />
          <ControlesRed
            autoActualizar={autoActualizar}
            onAuto={setAuto}
            intervalo={intervalo}
            onIntervalo={setIntervalo}
            pesoKB={vista.pesoKB}
            ultimaSync={haceCuanto(new Date(datos.cargado).toISOString(), ahora)}
            apiBase={datos.apiBase}
            onForzar={cargar}
            sincronizando={cargando}
          />
        </div>
      ) : (
        <div className="panel panel--una">
          <p className="vacio">
            {error ? (
              <>
                {error}. <button type="button" className="enlace" onClick={cargar}>Reintentar</button>
              </>
            ) : (
              'Cargando telemetría…'
            )}
          </p>
        </div>
      )}
    </>
  )
}
