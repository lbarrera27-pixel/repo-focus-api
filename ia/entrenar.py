"""
Entrena y evalúa el modelo de riesgo de recaída.

Ejecutar desde la raíz del repo:
    pip install -r ia/requirements.txt
    python -m ia.entrenar

Pasos:
1. Genera usuarios-semana sintéticos (ia/generador.py).
2. Divide POR USUARIO: 70 % entrenamiento, 15 % validación, 15 % prueba.
3. Estandariza con la media y desviación del entrenamiento.
4. Elige λ con la pérdida de validación (α = 1.0 fijo: con variables
   estandarizadas es el paso más grande que converge, y α solo cambia la
   velocidad, no el mínimo), y como umbral el más alto que en
   validación detecta al menos RECALL_MINIMO de las recaídas (se prioriza el
   recall: es peor no detectar una recaída que avisar de más).
5. Evalúa en prueba contra la línea base y contra scikit-learn.
6. Guarda los parámetros en app/utils/modelo_riesgo.json (los usa GET /riesgo)
   y las métricas y gráficas en ia/resultados/.
"""
import json
from pathlib import Path

import numpy as np

from app.utils.riesgo import RUTA_MODELO, VARIABLES
from ia import metricas
from ia.generador import generar
from ia.regresion_logistica import Normalizador, costo, entrenar, predecir_proba

RESULTADOS = Path(__file__).with_name("resultados")
ALFA = 1.0
LAMBDAS = [0.0, 0.1, 1.0, 10.0, 100.0]
EPOCAS = 5000
RECALL_MINIMO = 0.80
SEMILLA = 42


def dividir_por_usuario(usuarios: np.ndarray, semilla: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    ids = np.random.default_rng(semilla).permutation(np.unique(usuarios))
    corte1, corte2 = int(0.70 * len(ids)), int(0.85 * len(ids))
    return (np.isin(usuarios, ids[:corte1]), np.isin(usuarios, ids[corte1:corte2]),
            np.isin(usuarios, ids[corte2:]))


def buscar_hiperparametros(Xe, ye, Xv, yv) -> tuple[dict, list[dict]]:
    """Prueba cada λ y se queda con la menor pérdida logística (sin penalización) en validación."""
    pruebas = []
    for lam in LAMBDAS:
        w, b, historial = entrenar(Xe, ye, ALFA, lam, EPOCAS)
        pruebas.append({"alfa": ALFA, "lambda": lam, "w": w, "b": b, "historial": historial,
                        "costo_validacion": costo(Xv, yv, w, b, 0.0)})
    mejor = min(pruebas, key=lambda r: r["costo_validacion"])
    return mejor, [{k: r[k] for k in ("alfa", "lambda", "costo_validacion")} for r in pruebas]


def elegir_umbral(y: np.ndarray, p: np.ndarray) -> float:
    umbrales = np.round(np.arange(0.10, 0.91, 0.01), 2)
    validos = [u for u in umbrales if metricas.evaluar(y, p, u)["recall"] >= RECALL_MINIMO]
    return float(max(validos, default=umbrales[0]))


def comparar_con_sklearn(Xe, ye, Xp, lam: float, w: np.ndarray, b: float) -> dict | None:
    """Mismo problema con scikit-learn: nuestro costo × m/λ es su costo con C = 1/λ."""
    try:
        from sklearn.linear_model import LogisticRegression
    except ImportError:
        return None
    modelo = LogisticRegression(C=1 / lam if lam else np.inf, tol=1e-10, max_iter=10000)
    modelo.fit(Xe, ye)
    p_nuestra, p_sk = predecir_proba(Xp, w, b), modelo.predict_proba(Xp)[:, 1]
    return {
        "w_sklearn": modelo.coef_[0].tolist(),
        "b_sklearn": float(modelo.intercept_[0]),
        "max_dif_coeficientes": float(np.max(np.abs(modelo.coef_[0] - w))),
        "max_dif_probabilidad": float(np.max(np.abs(p_nuestra - p_sk))),
    }


def graficar(historial, y, p, w, umbral) -> list[str]:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return []
    archivos = []

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(historial, color="#0F172A")
    ax.set(xlabel="Época", ylabel="Costo J(w, b)", title="Curva de entrenamiento")
    ax.grid(alpha=0.3)
    archivos.append("curva_entrenamiento.png")
    fig.tight_layout(), fig.savefig(RESULTADOS / archivos[-1], dpi=150), plt.close(fig)

    tfp, tvp = metricas.curva_roc(y, p)
    mc = metricas.evaluar(y, p, umbral)["matriz_confusion"]
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot(tfp, tvp, color="#F59E0B", lw=2, label=f"Modelo (AUC = {metricas.auc_roc(y, p):.3f})")
    ax.plot([0, 1], [0, 1], "--", color="#64748B", label="Azar")
    ax.scatter([mc["fp"] / (mc["fp"] + mc["vn"])], [mc["vp"] / (mc["vp"] + mc["fn"])],
               color="#0F172A", zorder=3, label=f"Umbral {umbral:.2f}")
    ax.set(xlabel="Tasa de falsos positivos", ylabel="Tasa de verdaderos positivos (recall)",
           title="Curva ROC (prueba)")
    ax.legend(loc="lower right"), ax.grid(alpha=0.3)
    archivos.append("roc.png")
    fig.tight_layout(), fig.savefig(RESULTADOS / archivos[-1], dpi=150), plt.close(fig)

    orden = np.argsort(w)
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.barh(np.array(VARIABLES)[orden], w[orden],
            color=["#10B981" if v < 0 else "#F59E0B" for v in w[orden]])
    ax.axvline(0, color="#64748B", lw=0.8)
    ax.set(xlabel="Coeficiente w (variables estandarizadas)",
           title="Qué sube (+) y qué baja (−) el riesgo")
    archivos.append("coeficientes.png")
    fig.tight_layout(), fig.savefig(RESULTADOS / archivos[-1], dpi=150), plt.close(fig)
    return archivos


def main() -> None:
    X, y, _, usuarios = generar(semilla=SEMILLA)
    ent, val, pru = dividir_por_usuario(usuarios, SEMILLA)
    norm = Normalizador().ajustar(X[ent])
    Xe, Xv, Xp = (norm.transformar(X[m]) for m in (ent, val, pru))
    ye, yv, yp = y[ent], y[val], y[pru]

    mejor, busqueda = buscar_hiperparametros(Xe, ye, Xv, yv)
    w, b = mejor["w"], mejor["b"]
    umbral = elegir_umbral(yv, predecir_proba(Xv, w, b))

    p_prueba = predecir_proba(Xp, w, b)
    prueba = metricas.evaluar(yp, p_prueba, umbral)
    prueba_05 = metricas.evaluar(yp, p_prueba, 0.5)
    # Línea base: siempre la clase mayoritaria del entrenamiento (aquí "no recae")
    mayoritaria = int(ye.mean() >= 0.5)
    base = metricas.evaluar(yp, np.full(len(yp), float(mayoritaria)), 0.5)
    sklearn = comparar_con_sklearn(Xe, ye, Xp, mejor["lambda"], w, b)

    RESULTADOS.mkdir(exist_ok=True)
    graficas = graficar(mejor["historial"], yp, p_prueba, w, umbral)

    modelo = {
        "variables": VARIABLES,
        "w": [round(float(v), 6) for v in w],
        "b": round(float(b), 6),
        "media": [round(float(v), 6) for v in norm.media],
        "desviacion": [round(float(v), 6) for v in norm.desviacion],
        "umbral": umbral,
        "hiperparametros": {"alfa": mejor["alfa"], "lambda": mejor["lambda"], "epocas": EPOCAS},
        "datos": {"origen": "sintético (ia/generador.py)", "semilla": SEMILLA,
                  "filas_entrenamiento": int(ent.sum())},
        # Métricas en prueba que la API muestra junto al riesgo (qué tan confiable es el modelo)
        "prueba": {k: round(float(prueba[k]), 4) for k in ("exactitud", "auc_roc", "precision", "recall")},
    }
    RUTA_MODELO.write_text(json.dumps(modelo, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    reporte = {
        "datos": {"filas": len(y), "usuarios": int(len(np.unique(usuarios))), "tasa_recaida": float(y.mean()),
                  "entrenamiento": int(ent.sum()), "validacion": int(val.sum()), "prueba": int(pru.sum())},
        "hiperparametros": modelo["hiperparametros"],
        "busqueda": busqueda,
        "umbral": umbral,
        "prueba": prueba,
        "prueba_umbral_0_5": prueba_05,
        "linea_base_mayoritaria": base,
        "coeficientes": dict(zip(VARIABLES, modelo["w"])),
        "sklearn": sklearn,
        "graficas": graficas,
    }
    (RESULTADOS / "metricas.json").write_text(
        json.dumps(reporte, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Datos: {len(y)} usuarios-semana, {y.mean():.1%} recaídas "
          f"({ent.sum()} / {val.sum()} / {pru.sum()})")
    print(f"Mejor α = {mejor['alfa']}, λ = {mejor['lambda']}; "
          f"umbral (recall ≥ {RECALL_MINIMO:.0%} en validación) = {umbral:.2f}")
    print(f"\n{'Prueba':<24}{'exactitud':>10}{'precisión':>11}{'recall':>8}{'F1':>7}{'AUC':>7}")
    for nombre, r in (("Modelo (umbral elegido)", prueba), ("Modelo (umbral 0.5)", prueba_05),
                      ("Línea base mayoritaria", base)):
        print(f"{nombre:<24}{r['exactitud']:>10.3f}{r['precision']:>11.3f}{r['recall']:>8.3f}"
              f"{r['f1']:>7.3f}{r['auc_roc']:>7.3f}")
    mc = prueba["matriz_confusion"]
    print(f"\nMatriz de confusión: VP={mc['vp']} FP={mc['fp']} FN={mc['fn']} VN={mc['vn']}")
    print("\nCoeficientes (variables estandarizadas):")
    for v, c in sorted(zip(VARIABLES, w), key=lambda t: -abs(t[1])):
        print(f"  {v:<21} {c:+.3f}  si aumenta, {'sube' if c > 0 else 'baja'} el riesgo")
    if sklearn:
        print(f"\nscikit-learn: máx. diferencia en coeficientes {sklearn['max_dif_coeficientes']:.4f}, "
              f"en probabilidades {sklearn['max_dif_probabilidad']:.4f}")
    print(f"\nModelo guardado en {RUTA_MODELO.relative_to(Path.cwd())}; métricas en ia/resultados/")


if __name__ == "__main__":
    main()
