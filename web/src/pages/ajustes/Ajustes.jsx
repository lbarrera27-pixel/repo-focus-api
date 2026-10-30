import { useEffect, useMemo, useState } from 'react'
import Icono from '../../components/Icono.jsx'
import iconoCandado from '../../assets/icons/aj-candado.svg'
import iconoRestablecer from '../../assets/icons/aj-restablecer.svg'
import iconoGuardar from '../../assets/icons/aj-guardar.svg'
import { DEFAULTS, cargarLocales, guardarLocales, leerLocales } from '../../data/ajustes.js'
import { haceCuanto } from '../../data/panel.js'
import { api } from '../../api.js'
import TabReglas from './TabReglas.jsx'
import TabApps from './TabApps.jsx'
import TabLimites from './TabLimites.jsx'
import TabPrivacidad from './TabPrivacidad.jsx'
import './Ajustes.css'

const PESTANAS = [
  { id: 'reglas', titulo: 'Reglas de Fricción' },
  { id: 'apps', titulo: 'Apps Restringidas' },
  { id: 'limites', titulo: 'Límites Diarios' },
  { id: 'privacidad', titulo: 'Privacidad Académica' },
]

function iniciales(nombre = '') {
  return nombre.split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0].toUpperCase()).join('') || '?'
}

// Valores que viven en la API y se editan como borrador hasta "Guardar"
function borradorApi(datos) {
  return {
    limiteGlobal: datos?.plan?.limite_base ?? null,
    limitesApps: Object.fromEntries((datos?.apps ?? []).map((a) => [a.numero, a.limite_aperturas])),
  }
}

export default function Ajustes({ usuario, datos, error, cargadoEn, onRecargar, onCuentaEliminada }) {
  const [pestana, setPestana] = useState('reglas')
  // Se empieza con la copia del navegador y se reemplaza con lo que devuelva GET /configuracion/me
  const [inicial] = useState(() => leerLocales(usuario.id))
  const [locales, setLocales] = useState(() => structuredClone(inicial))
  const [guardadosLocales, setGuardadosLocales] = useState(inicial)
  const [borrador, setBorrador] = useState(() => borradorApi(datos))
  const [estado, setEstado] = useState({ guardando: false, mensaje: null, error: false })
  const [ultimaSync, setUltimaSync] = useState(cargadoEn)

  const original = useMemo(() => borradorApi(datos), [datos])

  // Cuando llegan datos nuevos de la API (p. ej. tras crear una app) se toman los valores nuevos,
  // pero se conservan los campos que el usuario ya había editado y aún no guarda
  const [originalPrevio, setOriginalPrevio] = useState(original)
  if (original !== originalPrevio) {
    const editado = (k, v) => v !== undefined && v !== (k === null ? originalPrevio.limiteGlobal : originalPrevio.limitesApps[k])
    setBorrador((b) => ({
      limiteGlobal: editado(null, b.limiteGlobal) ? b.limiteGlobal : original.limiteGlobal,
      limitesApps: Object.fromEntries(
        Object.entries(original.limitesApps).map(([n, v]) => [n, editado(n, b.limitesApps[n]) ? b.limitesApps[n] : v]),
      ),
    }))
    setOriginalPrevio(original)
  }

  useEffect(() => {
    setUltimaSync(cargadoEn)
  }, [cargadoEn])

  // Si el usuario ya empezó a editar antes de que responda la API, se conservan sus cambios
  useEffect(() => {
    let vigente = true
    cargarLocales(usuario).then((remotos) => {
      if (!vigente || !remotos) return
      setLocales((l) => (JSON.stringify(l) === JSON.stringify(inicial) ? structuredClone(remotos) : l))
      setGuardadosLocales(remotos)
    })
    return () => {
      vigente = false
    }
  }, [usuario, inicial])

  const cambiosApi = useMemo(() => {
    const apps = Object.entries(borrador.limitesApps).filter(([n, v]) => original.limitesApps[n] !== v)
    return { plan: borrador.limiteGlobal !== original.limiteGlobal, apps }
  }, [borrador, original])
  const cambiosLocales = JSON.stringify(locales) !== JSON.stringify(guardadosLocales)
  const pendientes = cambiosLocales || cambiosApi.plan || cambiosApi.apps.length > 0

  // Aviso del navegador si se intenta salir con cambios sin guardar
  useEffect(() => {
    if (!pendientes) return
    const avisar = (e) => e.preventDefault()
    window.addEventListener('beforeunload', avisar)
    return () => window.removeEventListener('beforeunload', avisar)
  }, [pendientes])

  async function guardar() {
    setEstado({ guardando: true, mensaje: null, error: false })
    try {
      if (!usuario.demo) {
        if (cambiosApi.plan && datos.plan) await api.actualizarPlan(usuario.id, datos.plan.numero, { limite_base: borrador.limiteGlobal })
        for (const [numero, limite] of cambiosApi.apps) await api.actualizarApp(usuario.id, numero, { limite_aperturas: limite })
      }
      // PUT /configuracion/me (en la demo, solo en el navegador)
      if (cambiosLocales) await guardarLocales(usuario, locales)
      setGuardadosLocales(structuredClone(locales))
      // En la demo no hay API: los cambios de límites se descartan
      if (usuario.demo) setBorrador(borradorApi(datos))
      const enApi = (cambiosApi.plan ? 1 : 0) + cambiosApi.apps.length + (cambiosLocales ? 1 : 0)
      setEstado({
        guardando: false,
        error: false,
        mensaje: usuario.demo ? 'Guardado en este navegador (demo: no se envía nada a la API)' : `Guardado · ${enApi} cambio(s) enviados a la API`,
      })
      setUltimaSync(Date.now())
      if ((cambiosApi.plan || cambiosApi.apps.length) && !usuario.demo) onRecargar()
    } catch (err) {
      setEstado({ guardando: false, error: true, mensaje: `No se pudo guardar: ${err.message || 'sin conexión'}` })
    }
  }

  function restablecer() {
    setLocales(structuredClone(DEFAULTS))
    setBorrador(borradorApi(datos))
    setEstado({ guardando: false, error: false, mensaje: 'Valores por defecto cargados; pulsa Guardar para aplicarlos' })
  }

  const actual = PESTANAS.find((p) => p.id === pestana)
  const props = { usuario, datos, locales, setLocales, borrador, setBorrador, original, onRecargar, onCuentaEliminada }

  return (
    <div className="aj">
      <header className="topbar topbar--seccion">
        <div className="topbar__titulos">
          <p className="topbar__ruta">
            FOCUS! CLOUD <span>/</span> AJUSTES <span>/</span> {actual.titulo.toUpperCase()}
          </p>
          <h1 className="topbar__titulo topbar__titulo--grande">Configuración del Sistema y Reglas de Fricción</h1>
          <p className="topbar__desc">Administra límites, intervenciones progresivas y horarios de concentración.</p>
        </div>
        <div className="topbar__acciones aj-acciones">
          <span className="chip aj-chip">
            <Icono src={iconoCandado} tam={13} />
            Cambios protegidos y auditados
          </span>
          <span className={`estado estado--chip ia-modelo${error ? ' estado--error' : ''}`}>
            <span className="estado__punto" aria-hidden="true" />
            {error ? 'Sin conexión con la nube' : usuario.demo ? 'Modo demostración' : 'Nube sincronizada'}
          </span>
          <span className="avatar avatar--bd" title={usuario.nombre}>{iniciales(usuario.nombre)}</span>
        </div>
      </header>

      <nav className="aj-pestanas" aria-label="Secciones de configuración" role="tablist">
        {PESTANAS.map((p) => (
          <button
            key={p.id}
            type="button"
            role="tab"
            aria-selected={p.id === pestana}
            className={`aj-pestana${p.id === pestana ? ' aj-pestana--activa' : ''}`}
            onClick={() => setPestana(p.id)}
          >
            {p.titulo}
          </button>
        ))}
      </nav>

      <div className="aj-contenido">
        {!datos ? (
          <p className="vacio">
            {error ? (
              <>
                No se pudieron cargar los datos. <button type="button" className="enlace" onClick={onRecargar}>Reintentar</button>
              </>
            ) : (
              'Cargando ajustes…'
            )}
          </p>
        ) : pestana === 'reglas' ? (
          <TabReglas {...props} />
        ) : pestana === 'apps' ? (
          <TabApps {...props} />
        ) : pestana === 'limites' ? (
          <TabLimites {...props} />
        ) : (
          <TabPrivacidad {...props} />
        )}
      </div>

      <footer className="aj-barra">
        <div className="aj-barra__estado">
          <span className={`aj-barra__titulo${pendientes ? '' : ' aj-barra__titulo--ok'}`}>
            <i />
            {estado.mensaje && !pendientes ? estado.mensaje : pendientes ? 'Cambios locales pendientes' : 'Todo guardado'}
          </span>
          <small className={estado.error ? 'aj-error' : ''}>
            {estado.error
              ? estado.mensaje
              : `La última sincronización con la nube fue ${ultimaSync ? haceCuanto(new Date(ultimaSync).toISOString()).toLowerCase() : 'pendiente'}.`}
          </small>
        </div>
        <div className="aj-barra__botones">
          <button type="button" className="aj-boton-secundario" onClick={restablecer}>
            <Icono src={iconoRestablecer} tam={16} />
            Restablecer valores por defecto
          </button>
          <button type="button" className="boton-primario aj-boton-primario" onClick={guardar} disabled={!pendientes || estado.guardando}>
            <Icono src={iconoGuardar} tam={17} />
            {estado.guardando ? 'Guardando…' : 'Guardar y sincronizar con móvil'}
          </button>
        </div>
      </footer>
    </div>
  )
}
