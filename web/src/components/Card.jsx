// Tarjeta base del portal: etiqueta en ámbar, título y un elemento a la derecha.
export default function Card({ etiqueta, titulo, extra, className = '', children }) {
  return (
    <section className={`card ${className}`}>
      <header className="card__header">
        <div className="card__titulos">
          <p className="card__etiqueta">{etiqueta}</p>
          <h2 className="card__titulo">{titulo}</h2>
        </div>
        {extra}
      </header>
      {children}
    </section>
  )
}

export function Insignia({ children, vivo = false }) {
  return (
    <span className={`insignia${vivo ? ' insignia--vivo' : ''}`}>
      {vivo && <span className="estado__punto" aria-hidden="true" />}
      {children}
    </span>
  )
}
