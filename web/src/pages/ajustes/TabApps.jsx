import { useState } from 'react'
import Icono from '../../components/Icono.jsx'
import iconoMas from '../../assets/icons/aj-mas.svg'
import iconoBuscarCirculo from '../../assets/icons/aj-buscar-circulo.svg'
import iconoBuscarMango from '../../assets/icons/aj-buscar-mango.svg'
import iconoBotonConfig from '../../assets/icons/aj-boton-config.svg'
import logoInstagram from '../../assets/icons/logo-instagram.svg'
import logoTiktok from '../../assets/icons/logo-tiktok.svg'
import logoX from '../../assets/icons/logo-x.svg'
import logoYoutube from '../../assets/icons/logo-youtube.svg'
import logoFacebook from '../../assets/icons/logo-facebook.svg'
import logoClash from '../../assets/icons/logo-clash.png'
import { Cabecera, Chip, ChipNivel, Interruptor, Nota, Pasos } from './Comunes.jsx'
import { etiquetaCategoria, pausasDeHoy, resumenApps } from '../../data/ajustes.js'
import { api } from '../../api.js'

// Logos del diseño para los paquetes conocidos; el resto usa la inicial de la app
const LOGOS = {
  'com.instagram.android': { src: logoInstagram, gradiente: true },
  'com.zhiliaoapp.musically': { src: logoTiktok },
  'com.twitter.android': { src: logoX },
  'com.google.android.youtube': { src: logoYoutube },
  'com.facebook.katana': { src: logoFacebook },
  'com.supercell.clashroyale': { src: logoClash },
}

function Logo({ app, tam = 38 }) {
  const logo = LOGOS[app.paquete]
  if (!logo) return <span className="aj-logo aj-logo--inicial" style={{ width: tam, height: tam }}>{app.nombre.charAt(0).toUpperCase()}</span>
  return (
    <span className={`aj-logo${logo.gradiente ? ' aj-logo--instagram' : ''}`} style={{ width: tam, height: tam }}>
      <img src={logo.src} alt="" />
    </span>
  )
}

const FILTROS = [
  { id: null, etiqueta: 'Todas' },
  { id: 'social', etiqueta: 'Redes sociales' },
  { id: 'video', etiqueta: 'Video' },
  { id: 'juegos', etiqueta: 'Juegos' },
]

const COLOR_NIVEL = { 1: '#fbbf24', 2: '#38bdf8', 3: '#f87171' }

function NuevaApp({ usuario, onCreada, onCancelar }) {
  const [form, setForm] = useState({ nombre: '', paquete: '', categoria: 'social', limite_aperturas: 10 })
  const [estado, setEstado] = useState({ enviando: false, error: null })
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: k === 'limite_aperturas' ? Number(e.target.value) : e.target.value }))

  async function enviar(e) {
    e.preventDefault()
    setEstado({ enviando: true, error: null })
    try {
      if (!usuario.demo) await api.crearApp(usuario.id, form)
      onCreada()
    } catch (err) {
      setEstado({ enviando: false, error: err.message || 'Sin conexión' })
    }
  }

  return (
    <form className="aj-nueva" onSubmit={enviar}>
      <label>
        <small>NOMBRE</small>
        <input required maxLength={120} value={form.nombre} onChange={set('nombre')} placeholder="Instagram" />
      </label>
      <label>
        <small>PAQUETE ANDROID</small>
        <input required maxLength={255} value={form.paquete} onChange={set('paquete')} placeholder="com.instagram.android" />
      </label>
      <label>
        <small>CATEGORÍA</small>
        <select value={form.categoria} onChange={set('categoria')}>
          <option value="social">Redes sociales</option>
          <option value="video">Video</option>
          <option value="juegos">Juegos</option>
          <option value="mensajeria">Mensajería</option>
        </select>
      </label>
      <label>
        <small>APERTURAS / DÍA</small>
        <input type="number" min="0" max="100" required value={form.limite_aperturas} onChange={set('limite_aperturas')} />
      </label>
      <div className="aj-nueva__botones">
        <button type="button" className="aj-boton-secundario aj-boton-secundario--chico" onClick={onCancelar}>Cancelar</button>
        <button type="submit" className="boton-primario aj-boton-chico" disabled={estado.enviando}>
          {estado.enviando ? 'Guardando…' : usuario.demo ? 'Añadir (demo)' : 'Añadir con POST /apps'}
        </button>
      </div>
      {estado.error && <p className="aj-error aj-nueva__error">No se pudo crear: {estado.error}</p>}
    </form>
  )
}

export default function TabApps({ usuario, datos, locales, setLocales, borrador, setBorrador, original, onRecargar }) {
  const [busqueda, setBusqueda] = useState('')
  const [filtro, setFiltro] = useState(null)
  const [editando, setEditando] = useState(null)
  const [nueva, setNueva] = useState(false)
  const [aviso, setAviso] = useState(null)

  const apps = resumenApps(datos)
  const inactivas = new Set(locales.appsInactivas)
  const q = busqueda.trim().toLowerCase()
  const visibles = apps.filter(
    (a) => (!filtro || a.grupo === filtro) && (!q || a.nombre.toLowerCase().includes(q) || a.paquete.toLowerCase().includes(q)),
  )
  const hoy = pausasDeHoy(datos)

  // Distribución de apps por el nivel de fricción que más se les aplica
  const porNivel = [1, 2, 3].map((n) => ({ nivel: n, apps: apps.filter((a) => a.nivel === n) }))
  const conNivel = apps.filter((a) => a.nivel).length || 1
  const top = [...apps].sort((a, b) => b.pausas7 - a.pausas7).filter((a) => a.pausas7 > 0).slice(0, 4)
  const maxPausas = Math.max(1, ...top.map((a) => a.pausas7))

  const alternar = (numero, activa) =>
    setLocales((l) => ({ ...l, appsInactivas: activa ? l.appsInactivas.filter((n) => n !== numero) : [...l.appsInactivas, numero] }))
  const cambiarLimite = (numero, delta) =>
    setBorrador((b) => ({ ...b, limitesApps: { ...b.limitesApps, [numero]: Math.max(0, Math.min(100, b.limitesApps[numero] + delta)) } }))

  return (
    <div className="aj-grid aj-grid--apps">
      <section className="aj-panel">
        <Cabecera
          etiqueta="APPS MONITORIZADAS"
          titulo="Catálogo de Apps Restringidas"
          desc="Administra todas las apps y su nivel de intervención antes de abrirse."
          extra={<Chip>{apps.length - apps.filter((a) => inactivas.has(a.numero)).length} activas</Chip>}
        />
        <div className="aj-filtros">
          <label className="aj-buscar">
            <span className="aj-buscar__icono" aria-hidden="true">
              <img src={iconoBuscarCirculo} alt="" className="aj-buscar__circulo" />
              <img src={iconoBuscarMango} alt="" className="aj-buscar__mango" />
            </span>
            <input type="search" placeholder="Buscar app o paquete..." value={busqueda} onChange={(e) => setBusqueda(e.target.value)} />
          </label>
          {FILTROS.map((f) => (
            <button
              key={f.etiqueta}
              type="button"
              aria-pressed={filtro === f.id}
              className={`aj-filtro${filtro === f.id ? ' aj-filtro--activo' : ''}`}
              onClick={() => setFiltro(f.id)}
            >
              {f.etiqueta}
            </button>
          ))}
        </div>

        <div className="aj-tabla__cabeza">
          <small>APP</small>
          <small>CATEGORÍA</small>
          <small>FRICCIÓN</small>
          <small>LÍMITE DIARIO</small>
          <small>USO HOY</small>
        </div>
        <div className="aj-tabla">
          {visibles.length ? (
            visibles.map((a) => {
              const activa = !inactivas.has(a.numero)
              const limite = borrador.limitesApps[a.numero]
              const cambiado = limite !== original.limitesApps[a.numero]
              const lleno = limite > 0 && a.aperturasHoy >= limite
              return (
                <div key={a.numero} className={`aj-fila${activa ? '' : ' aj-fila--inactiva'}`}>
                  <Logo app={a} />
                  <span className="aj-fila__app">
                    <b>{a.nombre}</b>
                    <small>{a.paquete}</small>
                  </span>
                  <span><span className="aj-categoria">{etiquetaCategoria(a.categoria)}</span></span>
                  <span><ChipNivel nivel={a.nivel} /></span>
                  <span className="aj-fila__limite">
                    <b className={cambiado ? 'aj-cambiado' : ''}>{limite} aperturas</b>
                    {editando === a.numero && (
                      <Pasos
                        etiqueta={`el límite de ${a.nombre}`}
                        deshabilitarMenos={limite <= 0}
                        deshabilitarMas={limite >= 100}
                        onMenos={() => cambiarLimite(a.numero, -1)}
                        onMas={() => cambiarLimite(a.numero, 1)}
                      />
                    )}
                  </span>
                  <span className="aj-fila__uso">
                    <b className={lleno ? 'aj-rojo' : ''}>{a.aperturasHoy} / {limite} aperturas</b>
                    <span className="aj-barra-uso">
                      <span style={{ width: `${limite ? Math.min(100, (a.aperturasHoy / limite) * 100) : 0}%`, background: lleno ? '#ef4444' : '#f59e0b' }} />
                    </span>
                  </span>
                  <button
                    type="button"
                    className={`aj-boton-config${editando === a.numero ? ' aj-boton-config--activo' : ''}`}
                    aria-label={`Configurar ${a.nombre}`}
                    aria-expanded={editando === a.numero}
                    onClick={() => setEditando(editando === a.numero ? null : a.numero)}
                  >
                    <img src={iconoBotonConfig} alt="" />
                  </button>
                  <Interruptor activo={activa} etiqueta={`Fricción para ${a.nombre}`} onCambio={(v) => alternar(a.numero, v)} />
                </div>
              )
            })
          ) : (
            <p className="vacio">{apps.length ? 'Ninguna app coincide con el filtro.' : 'Aún no hay apps registradas.'}</p>
          )}
        </div>

        {nueva ? (
          <NuevaApp
            usuario={usuario}
            onCancelar={() => setNueva(false)}
            onCreada={() => {
              setNueva(false)
              setAviso(usuario.demo ? 'En la demo no se crean apps en la API.' : 'App creada en la API.')
              if (!usuario.demo) onRecargar()
            }}
          />
        ) : (
          <button type="button" className="aj-boton-punteado" onClick={() => setNueva(true)}>
            <Icono src={iconoMas} tam={16} />
            Añadir nueva app restringida
          </button>
        )}
        <div className="aj-pie">
          <Nota>
            {aviso ?? 'El límite (aperturas por día) y las apps desactivadas se guardan en tu cuenta en la nube.'}
          </Nota>
        </div>
      </section>

      <section className="aj-panel">
        <Cabecera
          etiqueta="RESUMEN DE INTERVENCIONES"
          titulo="Fricción Activa Hoy"
          desc="Cómo se aplican los niveles en tus apps."
          extra={<Chip>{hoy.total} pausas</Chip>}
        />
        <div className="aj-stats">
          <div><small>PAUSAS MOSTRADAS</small><b>{hoy.total}</b></div>
          <div><small>ABANDONARON</small><b className="aj-verde">{hoy.abandonaron}</b></div>
          <div><small>CONTINUARON</small><b className="aj-ambar">{hoy.continuaron}</b></div>
        </div>

        <p className="aj-subtitulo">DISTRIBUCIÓN POR NIVEL · ÚLTIMOS 7 DÍAS</p>
        <div className="aj-distribucion">
          {porNivel.map(({ nivel, apps: lista }) => (
            <div key={nivel} className="aj-distribucion__fila">
              <ChipNivel nivel={nivel} />
              <span>
                <b>{lista.length ? lista.map((a) => a.nombre).join(' · ') : 'Ninguna app'}</b>
                <span className="aj-barra-uso aj-barra-uso--larga">
                  <span style={{ width: `${(lista.length / conNivel) * 100}%`, background: COLOR_NIVEL[nivel] }} />
                </span>
              </span>
              <strong>{lista.length} app{lista.length === 1 ? '' : 's'}</strong>
            </div>
          ))}
        </div>

        <p className="aj-subtitulo">APPS CON MÁS PAUSAS · ÚLTIMOS 7 DÍAS</p>
        <div className="aj-top">
          {top.length ? (
            top.map((a) => (
              <div key={a.numero} className="aj-top__fila">
                <Logo app={a} tam={28} />
                <span>
                  <b>{a.nombre}</b>
                  <span className="aj-barra-uso aj-barra-uso--top">
                    <span style={{ width: `${(a.pausas7 / maxPausas) * 100}%` }} />
                  </span>
                </span>
                <strong>{a.pausas7} pausas</strong>
              </div>
            ))
          ) : (
            <p className="vacio">Sin pausas registradas esta semana.</p>
          )}
        </div>
        <div className="aj-pie">
          <Nota>Los niveles suben solos si detectamos recaídas.</Nota>
        </div>
      </section>
    </div>
  )
}
