import { useState } from 'react'
import Icono from '../components/Icono.jsx'
import brand from '../assets/icons/brand.svg'
import { api } from '../api.js'

// El diseño web no incluye pantalla de acceso; se arma con los mismos estilos del portal.
export default function Login({ onEntrar }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [cargando, setCargando] = useState(false)

  async function enviar(e) {
    e.preventDefault()
    setError('')
    setCargando(true)
    try {
      const r = await api.login(email, password)
      onEntrar({ id: r.usuario_id, nombre: r.nombre })
    } catch (err) {
      setError(
        err.status === 401
          ? 'Correo o contraseña incorrectos.'
          : err.status
            ? err.message
            : `No se pudo conectar con la API (${api.base}).`,
      )
    } finally {
      setCargando(false)
    }
  }

  return (
    <div className="login">
      <div className="login__marca">
        <div className="sidebar__glow" aria-hidden="true" />
        <div className="brand">
          <Icono src={brand} tam={40} />
          <div className="brand__texto">
            <span className="brand__nombre">
              FOCUS<span className="acento">!</span>
            </span>
            <span className="brand__lema">Menos pantalla, más enfoque</span>
          </div>
        </div>
        <p className="login__lema">
          Menos pantalla.
          <br />
          <span>Más vida.</span>
        </p>
      </div>

      <form className="login__form card" onSubmit={enviar}>
        <p className="card__etiqueta">PORTAL DE INVESTIGACIÓN</p>
        <h1 className="topbar__titulo">Inicia sesión</h1>
        <p className="login__ayuda">Usa la misma cuenta de la app Android de Focus!.</p>

        <label className="campo">
          <span>Correo</span>
          <input type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label className="campo">
          <span>Contraseña</span>
          <input type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>

        {error && <p className="login__error" role="alert">{error}</p>}

        <button type="submit" className="boton-primario boton-primario--ancho" disabled={cargando}>
          {cargando ? 'Entrando…' : 'Entrar'}
        </button>
        <button type="button" className="boton-secundario" onClick={() => onEntrar({ id: 0, nombre: 'Demo', demo: true })}>
          Ver demo sin cuenta
        </button>
      </form>
    </div>
  )
}
