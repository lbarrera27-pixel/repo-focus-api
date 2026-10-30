import { useEffect, useState } from 'react'
import iconoClusteres from '../../assets/icons/pr-clusteres.svg'
import iconoNoche from '../../assets/icons/pr-noche.svg'
import iconoResultados from '../../assets/icons/pr-resultados.svg'
import iconoErrores from '../../assets/icons/pr-errores.svg'
import iconoFirmado from '../../assets/icons/pr-firmado.svg'
import iconoNo from '../../assets/icons/pr-no.svg'
import { Cabecera, Chip, Interruptor, Nota } from './Comunes.jsx'
import { csvDeDatos } from '../../data/ajustes.js'
import { fechaServidor } from '../../data/panel.js'
import { api } from '../../api.js'

const PREFERENCIAS = [
  { id: 'metricas', titulo: 'Compartir métricas de uso agregadas', desc: 'Tiempo de pantalla y aperturas por app, nunca el contenido que ves.', icono: 'barras' },
  { id: 'clusteres', titulo: 'Participar en el análisis de clústeres', desc: 'Permite incluirte en el modelo K-Means de patrones conductuales.', icono: iconoClusteres },
  { id: 'nocturno', titulo: 'Incluir horarios de uso nocturno', desc: 'Usa franjas horarias para detectar patrones de riesgo de recaída.', icono: iconoNoche },
  { id: 'resultados', titulo: 'Compartir resultados de las intervenciones', desc: 'Registra si continuaste o abandonaste después de una pausa.', icono: iconoResultados },
  { id: 'errores', titulo: 'Enviar reportes técnicos de errores', desc: 'Información del dispositivo para mejorar la app, sin datos personales.', icono: iconoErrores },
]

const ANONIMIZACION = [
  { id: 'seudonimizado', titulo: 'Seudonimizado', desc: 'Tu nombre se reemplaza por un código aleatorio antes de salir de tu dispositivo.' },
  { id: 'anonimo', titulo: 'Anónimo', desc: 'Se eliminan nombre, correo e identificadores; no se puede ligar a tu cuenta.' },
  { id: 'agregado', titulo: 'Solo agregado', desc: 'Solo se comparten totales de grupo; nunca tus registros individuales.' },
]

const RETENCION = [
  { dias: 30, titulo: '30 días' },
  { dias: 90, titulo: '90 días' },
  { dias: 0, titulo: 'Hasta fin del estudio' },
]

const NUNCA = ['Contenido de mensajes o publicaciones', 'Fotos, archivos y contactos', 'Lo que escribes en el teclado', 'Ubicación precisa']

export default function TabPrivacidad({ usuario, datos, locales, setLocales, onCuentaEliminada }) {
  const [perfil, setPerfil] = useState(null)
  const [verDocumento, setVerDocumento] = useState(false)
  const [estado, setEstado] = useState({ eliminando: false, error: null, exportado: false })
  const cambiar = (fn) => setLocales((l) => fn(structuredClone(l)))

  useEffect(() => {
    if (usuario.demo) return
    api.usuario(usuario.id).then(setPerfil).catch(() => setPerfil(null))
  }, [usuario])

  const retirado = locales.consentimientoRetirado
  const fechaConsentimiento = perfil ? fechaServidor(perfil.fecha_registro).toLocaleDateString('es-MX', { day: 'numeric', month: 'short', year: 'numeric' }) : null

  function exportar() {
    const url = URL.createObjectURL(new Blob([csvDeDatos(datos)], { type: 'text/csv' }))
    Object.assign(document.createElement('a'), { href: url, download: `focus-mis-datos_${usuario.demo ? 'demo' : usuario.id}.csv` }).click()
    URL.revokeObjectURL(url)
    setEstado((e) => ({ ...e, exportado: true }))
  }

  async function eliminar() {
    if (usuario.demo) {
      setEstado((e) => ({ ...e, error: 'En la demo no hay cuenta que desactivar.' }))
      return
    }
    const ok = window.confirm(
      'Se desactivará tu cuenta (DELETE /usuarios/me) y se cerrará la sesión.\n\nLa API marca la cuenta como inactiva; los registros se conservan en la base de datos para el estudio.\n\n¿Continuar?',
    )
    if (!ok) return
    setEstado((e) => ({ ...e, eliminando: true, error: null }))
    try {
      await api.eliminarCuenta(usuario.id)
      onCuentaEliminada()
    } catch (err) {
      setEstado((e) => ({ ...e, eliminando: false, error: err.message || 'Sin conexión' }))
    }
  }

  const anon = ANONIMIZACION.find((a) => a.id === locales.anonimizacion)

  return (
    <div className="aj-grid aj-grid--privacidad">
      <section className="aj-panel">
        <Cabecera
          etiqueta="PRIVACIDAD ACADÉMICA"
          titulo="Uso de Datos en el Estudio Piloto"
          desc="Controla qué información se comparte con el equipo de investigación."
          extra={<Chip tono={retirado ? 'rojo' : 'verde'}>{retirado ? 'Consentimiento retirado' : 'Datos protegidos'}</Chip>}
        />
        <div className="aj-preferencias">
          {PREFERENCIAS.map((p) => (
            <div key={p.id} className={`aj-pref${retirado ? ' aj-pref--bloqueada' : ''}`}>
              <span className="aj-pref__icono">
                {p.icono === 'barras' ? (
                  <span className="aj-barras-icono" aria-hidden="true"><i /><i /><i /></span>
                ) : (
                  <img src={p.icono} alt="" />
                )}
              </span>
              <span className="aj-pref__texto">
                <b>{p.titulo}</b>
                <small>{p.desc}</small>
              </span>
              <Interruptor
                activo={!retirado && locales.privacidad[p.id]}
                etiqueta={p.titulo}
                onCambio={(v) => !retirado && cambiar((l) => ((l.privacidad[p.id] = v), l))}
              />
            </div>
          ))}
        </div>

        <div className="aj-bloque-gris">
          <small className="aj-micro">NIVEL DE ANONIMIZACIÓN</small>
          <div className="aj-segmentado" role="radiogroup" aria-label="Nivel de anonimización">
            {ANONIMIZACION.map((a) => (
              <button
                key={a.id}
                type="button"
                role="radio"
                aria-checked={a.id === locales.anonimizacion}
                className={`aj-segmento${a.id === locales.anonimizacion ? ' aj-segmento--activo' : ''}`}
                onClick={() => cambiar((l) => ((l.anonimizacion = a.id), l))}
              >
                {a.titulo}
              </button>
            ))}
          </div>
          <small className="aj-bloque-gris__desc">{anon.desc}</small>
        </div>

        <div className="aj-bloque-gris aj-bloque-gris--retencion">
          <small className="aj-micro">CONSERVAR MIS DATOS DURANTE</small>
          <div className="aj-retencion">
            {RETENCION.map((r) => (
              <button
                key={r.dias}
                type="button"
                aria-pressed={r.dias === locales.retencion}
                className={`aj-retencion__op${r.dias === locales.retencion ? ' aj-retencion__op--activa' : ''}`}
                onClick={() => cambiar((l) => ((l.retencion = r.dias), l))}
              >
                {r.titulo}
              </button>
            ))}
          </div>
        </div>

        <div className="aj-pie">
          <Nota>Estas preferencias se guardan en tu cuenta en la nube.</Nota>
        </div>
      </section>

      <section className="aj-panel">
        <Cabecera etiqueta="TUS DERECHOS" titulo="Consentimiento y Datos" desc="Gestiona tu participación en el estudio." />

        <div className="aj-consentimiento">
          <img src={iconoFirmado} alt="" className="aj-consentimiento__icono" />
          <span className="aj-consentimiento__texto">
            <b>Consentimiento informado</b>
            <small>
              {usuario.demo ? 'Cuenta de demostración' : fechaConsentimiento ? `Aceptado al registrarte · ${fechaConsentimiento}` : 'Aceptado al registrarte'}
            </small>
          </span>
          <Chip tono={retirado ? 'rojo' : 'verde'}>{retirado ? 'Retirado' : 'Firmado'}</Chip>
          <div className="aj-consentimiento__botones">
            <button type="button" className="aj-boton-blanco" onClick={() => setVerDocumento((v) => !v)} aria-expanded={verDocumento}>
              {verDocumento ? 'Ocultar documento' : 'Ver documento'}
            </button>
            <button
              type="button"
              className={retirado ? 'aj-boton-blanco' : 'aj-boton-rojo'}
              onClick={() => cambiar((l) => ((l.consentimientoRetirado = !l.consentimientoRetirado), l))}
            >
              {retirado ? 'Volver a dar consentimiento' : 'Retirar consentimiento'}
            </button>
          </div>
          {verDocumento && (
            <p className="aj-documento">
              Focus! registra cuánto tiempo y cuántas veces abres las apps que tú eliges, las pausas que te muestra y
              cómo respondes. Los datos se usan solo con fines académicos en el estudio piloto de la Facultad de
              Informática (UAQ). Puedes retirar tu consentimiento o desactivar tu cuenta en cualquier momento.
            </p>
          )}
        </div>

        <div className="aj-nunca">
          <small className="aj-micro">DATOS QUE NUNCA RECOPILAMOS</small>
          <ul>
            {NUNCA.map((t) => (
              <li key={t}>
                <img src={iconoNo} alt="" />
                {t}
              </li>
            ))}
          </ul>
        </div>

        <div className="aj-tus-datos">
          <small className="aj-micro">TUS DATOS</small>
          <button type="button" className="aj-boton-ancho aj-boton-ancho--ambar" onClick={exportar}>
            {estado.exportado ? 'Descargado · exportar de nuevo (CSV)' : 'Exportar mis datos (CSV)'}
          </button>
          <button type="button" className="aj-boton-ancho aj-boton-ancho--rojo" onClick={eliminar} disabled={estado.eliminando}>
            {estado.eliminando ? 'Desactivando…' : 'Desactivar mi cuenta y cerrar sesión'}
          </button>
          <small className={estado.error ? 'aj-error' : ''}>
            {estado.error ?? `El CSV incluye ${datos.eventos.length} eventos, ${datos.pausas.length} pausas y ${datos.apps.length} apps del periodo cargado.`}
          </small>
        </div>

        <div className="aj-institucion">
          <span className="aj-institucion__uaq">UAQ</span>
          <span>
            <b>Estudio aprobado por el Comité de Ética</b>
            <small>Facultad de Informática · Universidad Autónoma de Querétaro</small>
          </span>
        </div>

        <div className="aj-pie">
          <Nota>¿Dudas? Escribe al equipo de investigación desde Ayuda.</Nota>
        </div>
      </section>
    </div>
  )
}
