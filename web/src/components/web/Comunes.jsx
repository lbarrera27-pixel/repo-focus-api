// Componentes base del portal nuevo (Figma: Web/KPI, Web/Banner, Web/Esqueleto, Web/Estado vacío)
import Icono from '../Icono.jsx'
import iconoInfo from '../../assets/icons/w-banner-info.svg'
import './web.css'

export function Encabezado({ sobretitulo, titulo, children }) {
  return (
    <header className="w-encabezado">
      <div className="w-encabezado__titulos">
        <p className="w-sobretitulo">{sobretitulo}</p>
        <h1 className="w-display">{titulo}</h1>
      </div>
      {children && <div className="w-encabezado__acciones">{children}</div>}
    </header>
  )
}

export function Kpi({ etiqueta, valor, detalle }) {
  return (
    <div className="w-tarjeta w-kpi">
      <p className="w-etiqueta">{etiqueta}</p>
      <p className="w-display">{valor}</p>
      <p className="w-texto w-texto--2">{detalle}</p>
    </div>
  )
}

export function KpiCargando({ etiqueta }) {
  return (
    <div className="w-tarjeta w-kpi w-kpi--cargando" aria-busy="true">
      <p className="w-etiqueta">{etiqueta}</p>
      <Esqueleto ancho={150} alto={26} />
      <Esqueleto ancho={120} alto={10} />
    </div>
  )
}

export function Esqueleto({ ancho = '100%', alto = 14, className = '' }) {
  return <span className={`w-esqueleto ${className}`} style={{ width: ancho, height: alto }} aria-hidden="true" />
}

export function Banner({ titulo, detalle, tono = 'info', accion }) {
  return (
    <div className={`w-banner w-banner--${tono}`} role={tono === 'error' ? 'alert' : 'status'}>
      <Icono src={iconoInfo} tam={20} tinta={tono === 'error' ? '#b91c1c' : undefined} />
      <div className="w-banner__texto">
        <b>{titulo}</b>
        <span>{detalle}</span>
      </div>
      {accion}
    </div>
  )
}

export function EstadoVacio({ icono, titulo, detalle, accion, onAccion }) {
  return (
    <div className="w-vacio">
      <span className="w-vacio__burbuja">
        <Icono src={icono} tam={24} />
      </span>
      <p className="w-titulo-3">{titulo}</p>
      <p className="w-cuerpo w-texto--3">{detalle}</p>
      {accion && (
        <button type="button" className="w-boton w-boton--primario" onClick={onAccion}>
          {accion}
        </button>
      )}
    </div>
  )
}

export function Barra({ valor }) {
  const pct = Math.max(0, Math.min(1, valor)) * 100
  return (
    <span className="w-barra" role="progressbar" aria-valuenow={Math.round(pct)} aria-valuemin={0} aria-valuemax={100}>
      <span style={{ width: `${pct}%` }} />
    </span>
  )
}
