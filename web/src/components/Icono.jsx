// Ícono del diseño. Por defecto se muestra tal cual; con `tinta` se usa como máscara
// para pintarlo de otro color (p. ej. el ícono activo de la barra lateral).
export default function Icono({ src, tam = 16, tinta, className = '' }) {
  const estilo = { width: tam, height: tam }
  if (tinta) {
    return (
      <span
        aria-hidden="true"
        className={`icono ${className}`}
        style={{ ...estilo, backgroundColor: tinta, maskImage: `url("${src}")`, WebkitMaskImage: `url("${src}")` }}
      />
    )
  }
  return <img alt="" aria-hidden="true" className={`icono ${className}`} src={src} style={estilo} />
}
