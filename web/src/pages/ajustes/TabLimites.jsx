import { useState } from 'react'
import Icono from '../../components/Icono.jsx'
import iconoSocial from '../../assets/icons/cat-social.svg'
import iconoVideo from '../../assets/icons/cat-video.svg'
import iconoJuegos from '../../assets/icons/cat-juegos.svg'
import iconoMensajeria from '../../assets/icons/cat-mensajeria.svg'
import iconoLuna from '../../assets/icons/aj-luna.svg'
import { Cabecera, Chip, Interruptor, Nota, Pasos } from './Comunes.jsx'
import { NOMBRE_CATEGORIA, formatoMin, proximoAjuste, usoHoyPorGrupo, usoPorDiaSemana } from '../../data/ajustes.js'

const CATEGORIAS = [
  { id: 'social', icono: iconoSocial, fondo: '#fff0cf' },
  { id: 'video', icono: iconoVideo, fondo: '#e0f2fe' },
  { id: 'juegos', icono: iconoJuegos, fondo: '#fee2e2' },
  { id: 'mensajeria', icono: iconoMensajeria, fondo: '#dcfce7' },
]

const GLOBAL_MIN = 30
const GLOBAL_MAX = 360
const CAT_MAX = 180

const pct = (v, min, max) => `${((v - min) / (max - min)) * 100}%`

// "3 h", "2 h 30" (formato corto del diseño bajo cada barra)
const etiquetaCorta = (min) => {
  const h = Math.floor(min / 60)
  const m = Math.round(min % 60)
  return h ? `${h} h${m ? ` ${String(m).padStart(2, '0')}` : ''}` : `${m} min`
}

export default function TabLimites({ datos, locales, setLocales, borrador, setBorrador, original }) {
  const [nuevaFecha, setNuevaFecha] = useState('')
  const cambiar = (fn) => setLocales((l) => fn(structuredClone(l)))
  const limite = borrador.limiteGlobal
  const semana = usoPorDiaSemana(datos)
  const hoy = semana.find((d) => d.esHoy)
  const usoGrupo = usoHoyPorGrupo(datos)
  const sumaCategorias = Object.values(locales.categorias).reduce((s, v) => s + v, 0)
  const ultimoAjuste = [...(datos.ajustes ?? [])].sort((a, b) => b.semana - a.semana)[0]
  const proximo = proximoAjuste(datos.plan)

  // Comparación de la semana: uso promedio de los días ya transcurridos contra el límite
  const pasados = semana.filter((d) => !d.futuro)
  const promedio = pasados.reduce((s, d) => s + d.minutos, 0) / (pasados.length || 1)
  const vsLimite = limite ? Math.round(((promedio - limite) / limite) * 100) : null
  const maxBarra = Math.max(limite ?? 0, ...semana.map((d) => d.minutos), 60)

  const acotarGlobal = (v) => Math.max(GLOBAL_MIN, Math.min(GLOBAL_MAX, v))
  const setGlobal = (v) => setBorrador((b) => ({ ...b, limiteGlobal: acotarGlobal(v) }))
  const pasoGlobal = (delta) => setBorrador((b) => ({ ...b, limiteGlobal: acotarGlobal(b.limiteGlobal + delta) }))

  return (
    <div className="aj-grid aj-grid--limites">
      <section className="aj-panel">
        <Cabecera
          etiqueta="PRESUPUESTO DE PANTALLA"
          titulo="Límite Diario Global"
          desc="Define cuánto tiempo puedes dedicar a las apps restringidas por día."
          extra={<Chip tono={limite ? 'verde' : 'gris'}>{limite ? 'Activo' : 'Sin plan'}</Chip>}
        />
        {limite ? (
          <div className="aj-global">
            <div className="aj-global__fila">
              <span>
                <small>LÍMITE TOTAL POR DÍA · PLAN #{datos.plan.numero}</small>
                <b className={limite !== original.limiteGlobal ? 'aj-cambiado' : ''}>{formatoMin(limite)}</b>
              </span>
              <span className="aj-global__hoy">
                <small>HOY</small>
                <b>{formatoMin(hoy?.minutos ?? 0)}</b>
                <span className="aj-chip-estado aj-chip-estado--ambar">{Math.round(((hoy?.minutos ?? 0) / limite) * 100)} % usado</span>
              </span>
              <Pasos
                etiqueta="el límite diario"
                deshabilitarMenos={limite <= GLOBAL_MIN}
                deshabilitarMas={limite >= GLOBAL_MAX}
                onMenos={() => pasoGlobal(-5)}
                onMas={() => pasoGlobal(5)}
              />
            </div>
            <input
              type="range"
              min={GLOBAL_MIN}
              max={GLOBAL_MAX}
              step="5"
              value={limite}
              onChange={(e) => setGlobal(Number(e.target.value))}
              className="aj-rango aj-rango--perilla"
              style={{ '--pct': pct(limite, GLOBAL_MIN, GLOBAL_MAX) }}
              aria-label="Límite diario global en minutos"
            />
            <div className="aj-global__escala">
              <small>30 min</small>
              <small>2 h</small>
              <small>4 h</small>
              <small>6 h</small>
            </div>
            <p className="aj-global__meta">
              {ultimoAjuste
                ? `Meta del último ajuste (semana ${ultimoAjuste.semana}): ${formatoMin(ultimoAjuste.uso_meta)} · cambio ${ultimoAjuste.cambio_pct}%`
                : `Semana ${datos.plan.semana_actual} del plan · se guarda en la API (PUT /planes/${datos.plan.numero})`}
            </p>
          </div>
        ) : (
          <p className="vacio">No tienes un plan activo. Créalo desde la app Android o con POST /planes para fijar un límite diario.</p>
        )}

        <p className="aj-subtitulo">LÍMITE POR CATEGORÍA</p>
        <div className="aj-categorias">
          {CATEGORIAS.map((c) => {
            const lim = locales.categorias[c.id]
            const uso = usoGrupo[c.id]
            const lleno = lim > 0 && uso >= lim
            return (
              <div key={c.id} className="aj-cat">
                <span className="aj-cat__icono" style={{ background: c.fondo }}><Icono src={c.icono} tam={24} /></span>
                <span className="aj-cat__texto">
                  <b>{NOMBRE_CATEGORIA[c.id]}</b>
                  <small className={lleno ? 'aj-rojo' : ''}>Uso hoy · {uso} / {lim} min</small>
                </span>
                <input
                  type="range"
                  min="0"
                  max={CAT_MAX}
                  step="5"
                  value={lim}
                  onChange={(e) => cambiar((l) => ((l.categorias[c.id] = Number(e.target.value)), l))}
                  className={`aj-rango aj-rango--perilla${lleno ? ' aj-rango--rojo' : ''}`}
                  style={{ '--pct': pct(lim, 0, CAT_MAX) }}
                  aria-label={`Límite de ${NOMBRE_CATEGORIA[c.id]} en minutos`}
                />
                <b className="aj-cat__valor">{lim} min</b>
                <Pasos
                  etiqueta={`el límite de ${NOMBRE_CATEGORIA[c.id]}`}
                  deshabilitarMenos={lim <= 0}
                  deshabilitarMas={lim >= CAT_MAX}
                  onMenos={() => cambiar((l) => ((l.categorias[c.id] = Math.max(0, l.categorias[c.id] - 5)), l))}
                  onMas={() => cambiar((l) => ((l.categorias[c.id] = Math.min(CAT_MAX, l.categorias[c.id] + 5)), l))}
                />
              </div>
            )
          })}
        </div>

        <div className="aj-gradual">
          <span>
            <b>Reducción gradual del límite</b>
            <small>El servidor ajusta el límite cada semana con lógica difusa (Mamdani) según tu adherencia.</small>
            {proximo && <span className="aj-categoria">Próximo ajuste: {proximo.toLocaleDateString('es-MX', { weekday: 'long', day: 'numeric', month: 'short' })}</span>}
          </span>
          <Interruptor activo={locales.reduccionGradual} etiqueta="Reducción gradual del límite" onCambio={(v) => cambiar((l) => ((l.reduccionGradual = v), l))} />
        </div>

        <div className="aj-pie">
          <Nota>
            {limite && sumaCategorias > limite
              ? `La suma por categoría (${sumaCategorias} min) supera el límite total (${limite} min).`
              : 'La suma de los límites por categoría no puede superar el límite total.'}
          </Nota>
        </div>
      </section>

      <section className="aj-panel">
        <Cabecera
          etiqueta="DISTRIBUCIÓN SEMANAL"
          titulo="Límite por Día de la Semana"
          desc="Uso real de esta semana contra el límite de tu plan."
          extra={vsLimite != null && <Chip tono={vsLimite <= 0 ? 'verde' : 'ambar'}>{vsLimite > 0 ? '+' : '−'}{Math.abs(vsLimite)} % vs. límite</Chip>}
        />
        <div className="aj-semanal">
          <div className="aj-semanal__cabeza">
            <small>USO REAL VS. LÍMITE</small>
            <span>
              <i className="aj-semanal__punto" /> Uso real
              <i className="aj-semanal__punto aj-semanal__punto--limite" /> Límite del día
            </span>
          </div>
          <div className="aj-semanal__barras">
            {semana.map((d) => {
              const alto = (v) => `${(v / maxBarra) * 100}%`
              return (
                <div key={d.dia} className="aj-semanal__dia">
                  <div className="aj-semanal__zona">
                    {limite && <span className="aj-semanal__limite" style={{ height: alto(limite) }} />}
                    {!d.futuro && d.minutos > 0 && (
                      <span className="aj-semanal__uso" style={{ height: alto(d.minutos), background: limite && d.minutos > limite ? '#ef4444' : '#f59e0b' }}>
                        <em>{(d.minutos / 60).toFixed(1)} h</em>
                      </span>
                    )}
                  </div>
                  <b className={d.esHoy ? 'aj-ambar-texto' : ''}>{d.dia}</b>
                  <small>{limite ? etiquetaCorta(limite) : '—'}</small>
                  {d.esHoy && <span className="aj-hoy">HOY</span>}
                </div>
              )
            })}
          </div>
        </div>

        <div className="aj-opcion">
          <span className="aj-opcion__icono"><img src={iconoLuna} alt="" /></span>
          <span className="aj-opcion__texto">
            <b>Descanso nocturno</b>
            <small>Bloquea todas las apps restringidas durante tu horario de sueño.</small>
          </span>
          <input type="time" className="aj-hora-chip" value={locales.descanso.inicio} onChange={(e) => cambiar((l) => ((l.descanso.inicio = e.target.value), l))} aria-label="Inicio del descanso" />
          <small className="aj-a">a</small>
          <input type="time" className="aj-hora-chip" value={locales.descanso.fin} onChange={(e) => cambiar((l) => ((l.descanso.fin = e.target.value), l))} aria-label="Fin del descanso" />
          <Interruptor activo={locales.descanso.activo} etiqueta="Descanso nocturno" onCambio={(v) => cambiar((l) => ((l.descanso.activo = v), l))} />
        </div>

        <div className="aj-opcion">
          <span className="aj-opcion__icono aj-opcion__icono--calendario" aria-hidden="true"><i /></span>
          <span className="aj-opcion__texto">
            <b>Días de examen y entregas</b>
            <small>
              {locales.excepciones.length
                ? locales.excepciones.map((f) => (
                    <button key={f} type="button" className="aj-excepcion" onClick={() => cambiar((l) => ((l.excepciones = l.excepciones.filter((x) => x !== f)), l))} title="Quitar">
                      {new Date(`${f}T00:00:00`).toLocaleDateString('es-MX', { day: 'numeric', month: 'short' })} ×
                    </button>
                  ))
                : 'Ajusta el límite en fechas marcadas del calendario académico.'}
            </small>
          </span>
          <form
            className="aj-excepcion-form"
            onSubmit={(e) => {
              e.preventDefault()
              if (nuevaFecha && !locales.excepciones.includes(nuevaFecha)) cambiar((l) => ((l.excepciones = [...l.excepciones, nuevaFecha].sort()), l))
              setNuevaFecha('')
            }}
          >
            <input type="date" value={nuevaFecha} onChange={(e) => setNuevaFecha(e.target.value)} aria-label="Fecha de examen o entrega" />
            <button type="submit" className="aj-boton-punteado aj-boton-punteado--chico" disabled={!nuevaFecha}>+ Agregar excepción</button>
          </form>
        </div>

        <div className="aj-pie">
          <Nota>Los cambios se aplican a partir de las 00:00 del siguiente día.</Nota>
        </div>
      </section>
    </div>
  )
}
