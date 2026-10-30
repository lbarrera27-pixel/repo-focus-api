// Riesgo de recaída (Figma e13 con datos, e14 sin datos suficientes, e15 cargando).
import { useCallback, useEffect, useRef, useState } from 'react'
import Icono from '../../components/Icono.jsx'
import { Banner, Barra, Encabezado, EstadoVacio, Esqueleto, Kpi, KpiCargando } from '../../components/web/Comunes.jsx'
import { ALTO, FACTORES, MODELO, cargarRiesgo, consejos, porcentaje } from '../../data/riesgo.js'
import { fechaISO } from '../../data/panel.js'
import iconoAlerta from '../../assets/icons/w-alerta.svg'
import iconoCheckVerde from '../../assets/icons/w-check-verde.svg'
import iconoFlechaAbajo from '../../assets/icons/w-flecha-abajo.svg'
import iconoFlechaArriba from '../../assets/icons/w-flecha-arriba.svg'
import iconoLuna from '../../assets/icons/w-luna.svg'
import iconoCheck from '../../assets/icons/w-check.svg'
import iconoInfo from '../../assets/icons/w-info.svg'
import iconoInfoAzul from '../../assets/icons/w-info-azul.svg'
import iconoReloj from '../../assets/icons/w-reloj.svg'
import iconoBurbuja from '../../assets/icons/w-riesgo-burbuja.svg'
import './Riesgo.css'

const ICONOS_CONSEJO = { luna: iconoLuna, check: iconoCheck }
const NIVEL = {
  bajo: { texto: 'NIVEL BAJO', icono: iconoCheckVerde },
  medio: { texto: 'NIVEL MEDIO', icono: iconoAlerta },
  alto: { texto: 'NIVEL ALTO', icono: iconoAlerta },
}
const DIA_MS = 86_400_000

function kpisModelo(umbral, metricas) {
  return [
    { etiqueta: 'LÍNEA DE ALERTA', valor: porcentaje(umbral), detalle: `desde aquí: medio · desde ${porcentaje(ALTO)}: alto` },
    { etiqueta: 'QUÉ TAN CONFIABLE ES', valor: porcentaje(metricas.auc_roc), detalle: `acierta en ${Math.round(metricas.auc_roc * 100)} de cada 100 casos` },
    { etiqueta: 'ALERTAS ACERTADAS', valor: `${Math.round(metricas.precision * 10)} de 10`, detalle: 'cuando avisa, suele acertar' },
  ]
}

// ---------- Gráfica: probabilidad al cierre de cada semana con zonas bajo / medio / alto ----------
// Mismas proporciones que el diseño (520 × 230): y = 220 − p · 210
const ALTO_GRAF = 230
const y = (p) => 220 - p * 210

function GraficaSemanas({ historial, umbral }) {
  const n = historial.length
  const x = (i) => (n === 1 ? 50 : ((20 + (i * 480) / (n - 1)) / 520) * 100)
  const puntos = historial.map((h, i) => `${(x(i) / 100) * 520},${y(h.probabilidad)}`).join(' ')
  return (
    <figure className="rg-grafica" aria-label="Probabilidad de recaída por semana">
      <div className="rg-grafica__area">
        <svg viewBox={`0 0 520 ${ALTO_GRAF}`} preserveAspectRatio="none" aria-hidden="true">
          <rect className="rg-zona rg-zona--alta" x="0" y="10" width="520" height={y(ALTO) - 10} />
          <rect className="rg-zona rg-zona--media" x="0" y={y(ALTO)} width="520" height={y(umbral) - y(ALTO)} />
          <rect className="rg-zona rg-zona--baja" x="0" y={y(umbral)} width="520" height={220 - y(umbral)} />
          <line className="rg-umbral" x1="0" x2="520" y1={y(ALTO)} y2={y(ALTO)} />
          <line className="rg-umbral" x1="0" x2="520" y1={y(umbral)} y2={y(umbral)} />
          <polyline className="rg-serie" points={puntos} />
        </svg>
        <span className="rg-grafica__etiqueta" style={{ top: y(ALTO) - 18 }}>Alto {porcentaje(ALTO)}</span>
        <span className="rg-grafica__etiqueta" style={{ top: y(umbral) - 18 }}>Alerta {porcentaje(umbral)}</span>
        {historial.map((h, i) => (
          <span
            key={h.semana}
            className="rg-punto"
            style={{ left: `${x(i)}%`, top: y(h.probabilidad) }}
            title={`Semana ${h.semana}: ${porcentaje(h.probabilidad)}`}
          />
        ))}
      </div>
      <div className={`rg-grafica__eje${n === 1 ? ' rg-grafica__eje--uno' : ''}`}>
        {historial.map((h) => <span key={h.semana}>S{h.semana}</span>)}
      </div>
    </figure>
  )
}

function BarraFactor({ contribucion, maximo }) {
  const ancho = maximo ? (Math.abs(contribucion) / maximo) * 105 : 0
  const sube = contribucion > 0
  return (
    <span className="rg-divergente" aria-hidden="true">
      <span className="rg-divergente__centro" />
      <span
        className={`rg-divergente__barra rg-divergente__barra--${sube ? 'sube' : 'baja'}`}
        style={sube ? { left: 111, width: ancho } : { left: 110 - ancho, width: ancho }}
      />
    </span>
  )
}

// ---------- e13 · Con datos ----------
function ConDatos({ r }) {
  const metricas = r.metricas ?? MODELO.metricas
  const maximo = Math.max(...r.factores.map((f) => Math.abs(f.contribucion)))
  const historial = r.historial?.length ? r.historial : [{ semana: r.semana, probabilidad: r.probabilidad }]
  const ultima = historial[historial.length - 1].semana
  return (
    <>
      <div className="w-fila">
        <Kpi etiqueta="PROBABILIDAD" valor={porcentaje(r.probabilidad)} detalle="próxima semana" />
        {kpisModelo(r.umbral, metricas).map((k) => <Kpi key={k.etiqueta} {...k} />)}
      </div>

      <div className="w-fila rg-cuerpo">
        <section className="w-tarjeta rg-tarjeta">
          <h2 className="w-titulo-3">Probabilidad por semana</h2>
          <GraficaSemanas historial={historial} umbral={r.umbral} />
          <p className="w-texto w-texto--2">Las zonas llevan nombre y línea punteada, no dependen solo del color.</p>
          <div className="w-divisor" />
          <p className="w-sobretitulo">VALORES POR SEMANA</p>
          <ul className="rg-semanas">
            {historial.map((h) => (
              <li key={h.semana} className={h.semana === ultima ? 'rg-semanas__actual' : ''}>
                <span className="w-etiqueta">S{h.semana}</span>
                <b className="w-titulo-3">{porcentaje(h.probabilidad)}</b>
              </li>
            ))}
          </ul>
        </section>

        <section className="w-tarjeta rg-tarjeta">
          <h2 className="w-titulo-3">Contribución de cada factor</h2>
          <p className="w-texto w-texto--2">Ordenados por peso. Izquierda: baja el riesgo · derecha: lo sube.</p>
          <ul className="rg-factores">
            {r.factores.map((f) => {
              const info = FACTORES[f.variable] ?? { titulo: f.descripcion, valor: (v) => String(v) }
              const sube = f.efecto === 'sube'
              return (
                <li key={f.variable}>
                  <span className="rg-factores__nombre">
                    <b>{info.titulo}</b>
                    <span>{info.valor(f.valor)}</span>
                  </span>
                  <BarraFactor contribucion={f.contribucion} maximo={maximo} />
                  <span className={`rg-direccion rg-direccion--${sube ? 'sube' : 'baja'}`}>
                    <Icono src={sube ? iconoFlechaArriba : iconoFlechaAbajo} tam={12} />
                    {sube ? 'sube' : 'baja'}
                  </span>
                </li>
              )
            })}
          </ul>
          <div className="w-divisor" />
          <p className="w-sobretitulo">QUÉ PUEDES HACER</p>
          {consejos(r.factores).map((c) => (
            <div key={c.titulo} className="rg-consejo">
              <span className="rg-consejo__icono"><Icono src={ICONOS_CONSEJO[c.icono]} tam={16} /></span>
              <span className="rg-consejo__texto">
                <b className="w-cuerpo">{c.titulo}</b>
                <span className="w-texto w-texto--3">{c.detalle}</span>
              </span>
            </div>
          ))}
        </section>
      </div>

      <p className="rg-ficha">
        <Icono src={iconoInfo} tam={16} />
        Calculamos tu riesgo con 7 datos de tu semana, como tu uso de noche y las pausas que saltaste. Foqui no decide el riesgo: solo te lo explica.
      </p>
    </>
  )
}

// ---------- e14 · Sin datos suficientes ----------
function SinDatos({ datos, onNavegar }) {
  const medir = useRef(null)
  const plan = datos?.plan
  const hoy = new Date()
  const inicio = plan ? new Date(`${plan.fecha_inicio}T00:00:00`) : null
  const diasPlan = inicio ? Math.max(0, Math.floor((hoy - inicio) / DIA_MS) + 1) : 0
  const conEventos = new Set((datos?.eventos ?? []).map((e) => fechaISO(new Date(e.inicio)))).size
  const dias = Math.min(7, plan ? Math.min(diasPlan, conEventos || diasPlan) : conEventos)
  const primerCalculo = inicio ? new Date(inicio.getTime() + 7 * DIA_MS) : null
  const fecha = primerCalculo?.toLocaleDateString('es-MX', { weekday: 'long', day: 'numeric', month: 'long' })
  const faltan = primerCalculo ? Math.max(1, Math.ceil((primerCalculo - hoy) / DIA_MS)) : null

  const listo = {
    pct_nocturno: (datos?.eventos ?? []).length > 0,
    pct_ignoradas: (datos?.pausas ?? []).length > 0,
  }
  const pendiente = plan ? 'falta 1 semana' : 'falta tu plan'

  return (
    <>
      <div className="w-fila">
        <Kpi etiqueta="PROBABILIDAD" valor="—" detalle={faltan ? `disponible en ${faltan} día${faltan === 1 ? '' : 's'}` : 'disponible al crear tu plan'} />
        {kpisModelo(MODELO.umbral, MODELO.metricas).map((k) => (
          <Kpi key={k.etiqueta} {...k} detalle={k.etiqueta === 'LÍNEA DE ALERTA' ? `desde ${porcentaje(ALTO)} el riesgo es alto` : k.detalle} />
        ))}
      </div>

      <div className="w-fila rg-cuerpo">
        <section className="w-tarjeta rg-tarjeta rg-tarjeta--vacia">
          {plan ? (
            <EstadoVacio
              icono={iconoBurbuja}
              titulo="Todavía no podemos estimar tu riesgo"
              detalle={`Necesitamos 7 datos de tu primera semana completa del plan. Llevas ${dias} de 7 días: el primer cálculo llega el ${fecha}.`}
              accion="Ver qué datos usamos"
              onAccion={() => medir.current?.focus()}
            />
          ) : (
            <EstadoVacio
              icono={iconoBurbuja}
              titulo="Todavía no podemos estimar tu riesgo"
              detalle="El riesgo se calcula con las semanas de tu plan. Crea tu plan y después de una semana verás aquí tu primer cálculo."
              accion="Crear mi plan"
              onAccion={() => onNavegar('plan')}
            />
          )}
          <div className="w-divisor" />
          <p className="w-sobretitulo">TU AVANCE</p>
          <div className="w-fila rg-avance">
            <div>
              <span className="w-etiqueta">SEMANAS CON DATOS</span>
              <b className="w-titulo-2">0 de 1</b>
              <Barra valor={0} />
            </div>
            <div>
              <span className="w-etiqueta">DÍAS REGISTRADOS</span>
              <b className="w-titulo-2">{dias} de 7</b>
              <Barra valor={dias / 7} />
            </div>
          </div>
        </section>

        <section className="w-tarjeta rg-tarjeta rg-medir" ref={medir} tabIndex={-1} aria-labelledby="rg-medir-titulo">
          <div>
            <h2 className="w-titulo-3" id="rg-medir-titulo">Qué va a medir</h2>
            <p className="w-cuerpo w-texto--3">Estos son los 7 datos. Los marcados ya están listos.</p>
          </div>
          <ul className="rg-medir__lista">
            {Object.entries(FACTORES).map(([variable, info]) => {
              const ok = listo[variable]
              return (
                <li key={variable}>
                  <span className={`rg-medir__icono${ok ? ' rg-medir__icono--ok' : ''}`}>
                    <Icono src={ok ? iconoCheckVerde : iconoReloj} tam={14} />
                  </span>
                  <span className="w-cuerpo">{info.titulo}</span>
                  <span className={`rg-medir__estado${ok ? ' rg-medir__estado--ok' : ''}`}>{ok ? 'listo' : pendiente}</span>
                </li>
              )
            })}
          </ul>
          <div className="w-divisor" />
          <p className="w-sobretitulo">POR QUÉ ESPERAMOS</p>
          <div className="rg-porque">
            <Icono src={iconoInfoAzul} tam={16} />
            <span>
              <b className="w-cuerpo">Una semana completa da un cálculo justo</b>
              <span className="w-texto w-texto--2">Con menos datos el riesgo cambiaría mucho de un día a otro.</span>
            </span>
          </div>
        </section>
      </div>
    </>
  )
}

// ---------- e15 · Cargando ----------
function Cargando({ lento }) {
  return (
    <>
      {lento && (
        <Banner
          titulo="Estamos preparando tus datos…"
          detalle="Tarda un poco más de lo normal. Suele estar listo en menos de un minuto; no tienes que hacer nada."
        />
      )}
      <div className="w-fila">
        {['PROBABILIDAD', 'LÍNEA DE ALERTA', 'QUÉ TAN CONFIABLE ES', 'ALERTAS ACERTADAS'].map((e) => <KpiCargando key={e} etiqueta={e} />)}
      </div>
      <div className="w-fila rg-cuerpo" aria-busy="true">
        <section className="w-tarjeta rg-tarjeta rg-tarjeta--cargando">
          <h2 className="w-titulo-3">Probabilidad por semana</h2>
          <div className="rg-zonas-cargando">
            <Esqueleto alto={90} />
            <Esqueleto alto={40} />
            <Esqueleto alto={110} />
          </div>
          <div className="rg-eje-cargando">
            {Array.from({ length: 8 }, (_, i) => <Esqueleto key={i} alto={10} />)}
          </div>
        </section>
        <section className="w-tarjeta rg-tarjeta rg-tarjeta--cargando">
          <h2 className="w-titulo-3">Contribución de cada factor</h2>
          {Object.values(FACTORES).map((f, i) => (
            <div key={f.titulo} className="rg-factor-cargando">
              <span>
                <b className="w-cuerpo">{f.titulo}</b>
                <Esqueleto ancho={40} alto={10} />
              </span>
              <Esqueleto ancho={[100, 56, 40, 30, 24, 20, 12][i]} alto={10} />
            </div>
          ))}
          <Esqueleto />
          <Esqueleto />
          <Esqueleto />
        </section>
      </div>
    </>
  )
}

export default function Riesgo({ usuario, datos, onNavegar }) {
  const [estado, setEstado] = useState({ cargando: true, riesgo: null, error: null })
  const [lento, setLento] = useState(false)

  const cargar = useCallback(async () => {
    setEstado((e) => ({ ...e, cargando: true, error: null }))
    setLento(false)
    const aviso = setTimeout(() => setLento(true), 3000)
    try {
      const riesgo = await cargarRiesgo(usuario)
      setEstado({ cargando: false, riesgo, error: null })
    } catch (err) {
      setEstado({ cargando: false, riesgo: null, error: err.message || 'No se pudo conectar con la API' })
    } finally {
      clearTimeout(aviso)
    }
  }, [usuario])

  useEffect(() => {
    cargar()
  }, [cargar])

  const { cargando, riesgo, error } = estado
  const nivel = riesgo && NIVEL[riesgo.nivel]

  return (
    <div className="w-pagina rg">
      <Encabezado sobretitulo="RIESGO · PRÓXIMA SEMANA" titulo="Riesgo de recaída">
        {nivel && !cargando && (
          <span className={`rg-nivel rg-nivel--${riesgo.nivel}`}>
            <Icono src={nivel.icono} tam={14} tinta={riesgo.nivel === 'alto' ? '#b91c1c' : undefined} />
            {nivel.texto}
          </span>
        )}
      </Encabezado>

      {error ? (
        <Banner
          tono="error"
          titulo="No pudimos calcular tu riesgo"
          detalle={error}
          accion={<button type="button" className="w-boton w-boton--secundario" onClick={cargar}>Reintentar</button>}
        />
      ) : cargando ? (
        <Cargando lento={lento} />
      ) : riesgo ? (
        <ConDatos r={riesgo} />
      ) : (
        <SinDatos datos={datos} onNavegar={onNavegar} />
      )}
    </div>
  )
}
