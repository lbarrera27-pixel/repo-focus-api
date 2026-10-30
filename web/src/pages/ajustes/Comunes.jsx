import Icono from '../../components/Icono.jsx'
import iconoInfo from '../../assets/icons/aj-info.svg'

export function Cabecera({ etiqueta, titulo, desc, extra }) {
  return (
    <header className="aj-panel__cabeza">
      <div>
        <p className="card__etiqueta">{etiqueta}</p>
        <h2 className="aj-panel__titulo">{titulo}</h2>
        <p className="aj-panel__desc">{desc}</p>
      </div>
      {extra}
    </header>
  )
}

export function Chip({ children, tono = 'verde', punto = false }) {
  return (
    <span className={`aj-chip-estado aj-chip-estado--${tono}`}>
      {punto && <i className="aj-chip-estado__punto" />}
      {children}
    </span>
  )
}

export function Interruptor({ activo, onCambio, etiqueta }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={activo}
      aria-label={etiqueta}
      className={`aj-switch${activo ? ' aj-switch--on' : ''}`}
      onClick={() => onCambio(!activo)}
    >
      <span />
    </button>
  )
}

export function Nota({ children }) {
  return (
    <p className="aj-nota">
      <Icono src={iconoInfo} tam={14} />
      <span>{children}</span>
    </p>
  )
}

export function Pasos({ onMenos, onMas, etiqueta, deshabilitarMenos, deshabilitarMas }) {
  return (
    <span className="aj-pasos">
      <button type="button" onClick={onMenos} disabled={deshabilitarMenos} aria-label={`Reducir ${etiqueta}`}>−</button>
      <button type="button" onClick={onMas} disabled={deshabilitarMas} aria-label={`Aumentar ${etiqueta}`}>+</button>
    </span>
  )
}

export const CHIP_NIVEL = {
  1: { fondo: '#fef3c7', texto: '#92400e' },
  2: { fondo: '#e0f2fe', texto: '#0369a1' },
  3: { fondo: '#fee2e2', texto: '#b91c1c' },
}

export function ChipNivel({ nivel }) {
  if (!nivel) return <span className="aj-nivel aj-nivel--vacio">—</span>
  const c = CHIP_NIVEL[nivel]
  return (
    <span className="aj-nivel" style={{ background: c.fondo, color: c.texto }}>
      Nivel {nivel}
    </span>
  )
}
