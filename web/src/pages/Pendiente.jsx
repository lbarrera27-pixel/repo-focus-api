// Secciones del menú nuevo que todavía no están construidas
import { Encabezado, EstadoVacio } from '../components/web/Comunes.jsx'
import iconoBurbuja from '../assets/icons/w-riesgo-burbuja.svg'

export default function Pendiente({ titulo, sobretitulo, onNavegar }) {
  return (
    <div className="w-pagina">
      <Encabezado sobretitulo={sobretitulo} titulo={titulo} />
      <section className="w-tarjeta" style={{ flex: 1, display: 'grid', placeItems: 'center' }}>
        <EstadoVacio
          icono={iconoBurbuja}
          titulo="Esta sección está en construcción"
          detalle="Muy pronto podrás verla aquí. Mientras tanto, revisa tu panel de inicio."
          accion="Ir a Inicio"
          onAccion={() => onNavegar('inicio')}
        />
      </section>
    </div>
  )
}
