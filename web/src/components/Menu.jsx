// Barra lateral del portal nuevo (Figma "Web/Sidebar", rol Estudiante).
// Cada sección tiene su tono (variables color/nav/*) y el menú se puede contraer a 76 px.
import Icono from './Icono.jsx'
import iconoInicio from '../assets/icons/w-inicio.svg'
import iconoPlan from '../assets/icons/w-plan.svg'
import iconoRiesgo from '../assets/icons/w-riesgo.svg'
import iconoUso from '../assets/icons/w-uso.svg'
import iconoApps from '../assets/icons/w-apps.svg'
import iconoFoqui from '../assets/icons/w-foqui.svg'
import iconoReportes from '../assets/icons/w-reportes.svg'
import iconoAjustes from '../assets/icons/w-ajustes.svg'
import iconoContraer from '../assets/icons/w-contraer.svg'
import './Menu.css'

export const SECCIONES_ESTUDIANTE = [
  { id: 'inicio', titulo: 'Inicio', icono: iconoInicio, tono: 'azul' },
  { id: 'plan', titulo: 'Mi plan', icono: iconoPlan, tono: 'verde' },
  { id: 'riesgo', titulo: 'Riesgo de recaída', icono: iconoRiesgo, tono: 'rojo' },
  { id: 'uso', titulo: 'Uso por app', icono: iconoUso, tono: 'ambar' },
  { id: 'apps', titulo: 'Apps y sitios', icono: iconoApps, tono: 'violeta' },
  { id: 'foqui', titulo: 'Foqui', icono: iconoFoqui, tono: 'cian' },
  { id: 'reportes', titulo: 'Reportes', icono: iconoReportes, tono: 'indigo' },
  { id: 'ajustes', titulo: 'Ajustes', icono: iconoAjustes, tono: 'gris' },
]

const TONOS = {
  azul: '#7dd3fc', verde: '#6ee7b7', rojo: '#fda4af', ambar: '#fbbf24',
  violeta: '#c4b5fd', cian: '#67e8f9', indigo: '#a5b4fc', gris: '#e2e8f0',
}

export function iniciales(nombre = '') {
  return nombre.split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0].toUpperCase()).join('') || '?'
}

export default function Menu({ activa, onNavegar, usuario, contraido, onContraer, onSalir }) {
  return (
    <aside className={`menu${contraido ? ' menu--contraido' : ''}`}>
      <div className="menu__marca">
        <span className="menu__logo">
          {contraido ? 'F' : 'FOCUS'}
          <span className="menu__exclamacion">!</span>
        </span>
        {!contraido && <span className="menu__lema">Menos pantalla, más enfoque</span>}
      </div>

      {!contraido && <p className="menu__seccion">MI PANEL</p>}
      <nav className="menu__nav" aria-label="Navegación principal">
        {SECCIONES_ESTUDIANTE.map((s) => {
          const esActiva = s.id === activa
          return (
            <button
              key={s.id}
              type="button"
              className={`menu__item${esActiva ? ` menu__item--activo menu__item--${s.tono}` : ''}`}
              aria-current={esActiva ? 'page' : undefined}
              aria-label={contraido ? s.titulo : undefined}
              title={contraido ? s.titulo : undefined}
              onClick={() => onNavegar(s.id)}
            >
              <Icono src={s.icono} tam={18} tinta={esActiva ? TONOS[s.tono] : undefined} />
              {!contraido && <span>{s.titulo}</span>}
            </button>
          )
        })}
      </nav>

      <div className="menu__espacio" />
      <button
        type="button"
        className="menu__item"
        onClick={onContraer}
        aria-label={contraido ? 'Expandir menú' : undefined}
        title={contraido ? 'Expandir menú' : undefined}
      >
        <Icono src={iconoContraer} tam={18} />
        {!contraido && <span>Contraer menú</span>}
      </button>

      <button type="button" className="menu__usuario" onClick={onSalir} title="Cerrar sesión">
        <span className="menu__avatar">{iniciales(usuario.nombre)}</span>
        {!contraido && (
          <span className="menu__usuario-texto">
            <b>{usuario.nombre}</b>
            <small>{usuario.demo ? 'Modo demostración' : 'Estudiante · UAQ'}</small>
          </span>
        )}
      </button>
    </aside>
  )
}
