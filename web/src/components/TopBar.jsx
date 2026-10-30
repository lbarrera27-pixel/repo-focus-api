import Icono from './Icono.jsx'
import iconoBuscar from '../assets/icons/search.svg'
import iconoDescargar from '../assets/icons/download.svg'
import { PERIODOS } from '../data/panel.js'

export default function TopBar({ ruta, titulo, estado, periodo, onPeriodo, busqueda, onBusqueda, onExportar }) {
  return (
    <header className="topbar">
      <div className="topbar__titulos">
        <p className="topbar__ruta">{ruta}</p>
        <h1 className="topbar__titulo">{titulo}</h1>
        {estado && (
          <span className={`estado${estado.error ? ' estado--error' : ''}`}>
            <span className="estado__punto" aria-hidden="true" />
            {estado.texto}
          </span>
        )}
      </div>

      <div className="topbar__acciones">
        <div className="segmentado" role="group" aria-label="Periodo">
          {PERIODOS.map((p) => (
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

        <label className="buscador">
          <Icono src={iconoBuscar} tam={16} />
          <input
            type="search"
            placeholder="Buscar métrica o usuario"
            value={busqueda}
            onChange={(e) => onBusqueda(e.target.value)}
          />
          <kbd>⌘K</kbd>
        </label>

        <button type="button" className="boton-primario" onClick={onExportar}>
          <Icono src={iconoDescargar} tam={16} />
          Exportar Datos
          <span className="boton-primario__extra">CSV/JSON</span>
        </button>
      </div>
    </header>
  )
}
