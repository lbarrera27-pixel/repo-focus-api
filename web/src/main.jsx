import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

// El diseño mide 1440 px de ancho: en pantallas más anchas se amplía para ocupar todo el ancho
const ANCHO_DISENO = 1440
function ajustarZoom() {
  const zoom = Math.max(1, window.innerWidth / ANCHO_DISENO)
  const raiz = document.getElementById('root')
  raiz.style.zoom = zoom
  document.documentElement.style.setProperty('--zoom', zoom)
}
ajustarZoom()
window.addEventListener('resize', ajustarZoom)

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
