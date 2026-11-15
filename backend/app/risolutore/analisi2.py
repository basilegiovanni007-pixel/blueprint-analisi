"""
Risolutori per le funzioni di due variabili (Analisi II):

- gradiente e derivate parziali;
- punti critici e loro classificazione con la matrice hessiana;
- massimi e minimi vincolati con i moltiplicatori di Lagrange;
- integrali doppi su domini normali, con le formule di riduzione.

Ogni risolutore controlla da solo il proprio risultato con un metodo diverso da quello
usato per costruire i passaggi (es. autovalori invece del determinante, calcolo numerico
invece di quello simbolico) e scrive l'esito in "verificato".
"""

import numpy as np
import sympy

from app.grafici.formule import come_numero, in_js
from app.risolutore.integrali import risolvi_integrale
from app.risolutore.modelli import ErroreRisolutore, L, Passaggio, Problema, Svolgimento, riordina
from app.risolutore.verifica import uguali

NOMI_TIPO = {"massimo": "massimo relativo", "minimo": "minimo relativo", "sella": "punto di sella", "dubbio": "caso dubbio"}


# ---------- funzioni di supporto ----------


def _coppia(x, y, a, b) -> str:
    """Scrive in LaTeX il punto (a, b)."""
    return rf"\left({L(a)},\ {L(b)}\right)"


def _reale(valore: sympy.Expr) -> bool:
    return not valore.free_symbols and come_numero(valore) is not None


def _finestra(xs: list[float], ys: list[float], margine_minimo: float = 1.5) -> dict:
    """Sceglie la zona da disegnare in modo che contenga i punti dati, con un po' di margine."""
    if not xs:
        return {"xmin": -3.0, "xmax": 3.0, "ymin": -3.0, "ymax": 3.0}
    ampiezza = max(max(xs) - min(xs), max(ys) - min(ys))
    margine = max(margine_minimo, 0.6 * ampiezza)
    return {"xmin": min(xs) - margine, "xmax": max(xs) + margine, "ymin": min(ys) - margine, "ymax": max(ys) + margine}


def _dati_superficie(f, x, y, finestra: dict, punti: list[dict] | None = None, **altro) -> dict | None:
    """Prepara i dati con cui il frontend disegna la superficie e le curve di livello."""
    try:
        return {
            "tipo": "superficie",
            "funzione": in_js(f),
            "variabili": [str(x), str(y)],
            "finestra": finestra,
            "punti": punti or [],
            "vincolo": None,
            "dominio": None,
            **altro,
        }
    except Exception:
        return None


# ---------- gradiente ----------


def risolvi_gradiente(p: Problema) -> Svolgimento:
    f, variabili = p.funzione, p.variabili
    passi, parziali = [], []
    for v in variabili:
        altre = ", ".join(f"${L(a)}$" for a in variabili if a != v)
        derivata = riordina(sympy.diff(f, v))
        parziali.append(derivata)
        passi.append(
            Passaggio(
                f"Derivata parziale rispetto a {v}",
                f"Deriviamo rispetto a ${L(v)}$ trattando {altre} come se "
                + ("fosse una costante." if len(variabili) == 2 else "fossero costanti."),
                rf"\frac{{\partial f}}{{\partial {L(v)}}} = {L(derivata)}",
                "derivate_parziali",
                domanda=rf"Quanto vale $\frac{{\partial f}}{{\partial {L(v)}}}$?",
                atteso=derivata,
            )
        )
    vettore = r"\left(" + r",\ ".join(L(d) for d in parziali) + r"\right)"
    passi.append(
        Passaggio(
            "Gradiente",
            "Il gradiente è il vettore che ha per componenti le derivate parziali. "
            "In ogni punto indica la direzione in cui la funzione cresce più rapidamente.",
            rf"\nabla f = {vettore}",
            "gradiente",
        )
    )

    # Verifica indipendente: confrontiamo con il rapporto incrementale calcolato numericamente
    punto = {v: sympy.Float(0.37 + 0.41 * i) for i, v in enumerate(variabili)}
    verificato = True
    for v, derivata in zip(variabili, parziali):
        h = sympy.Float(1e-6)
        avanti, indietro = dict(punto), dict(punto)
        avanti[v] += h
        indietro[v] -= h
        numerica = come_numero((f.subs(avanti) - f.subs(indietro)) / (2 * h))
        esatta = come_numero(derivata.subs(punto))
        if numerica is None or esatta is None:
            continue  # la funzione non è definita nel punto di prova: non possiamo confrontare
        if abs(numerica - esatta) > 1e-4 * (1 + abs(esatta)):
            verificato = False

    grafico = None
    if len(variabili) == 2:
        grafico = _dati_superficie(f, variabili[0], variabili[1], _finestra([], []))
    return Svolgimento(
        risultato=None,
        risultato_latex=vettore,
        risposta_latex=rf"\nabla f = {vettore}",
        metodo="derivate parziali",
        passaggi=passi,
        verificato=verificato,
        grafico=grafico,
    )


# ---------- punti critici ----------


def _classifica(determinante: float, fxx: float) -> str:
    """Criterio dell'hessiana per le funzioni di due variabili."""
    if abs(determinante) < 1e-9:
        return "dubbio"
    if determinante < 0:
        return "sella"
    return "minimo" if fxx > 0 else "massimo"


def _classifica_con_autovalori(hessiana: sympy.Matrix) -> str:
    """Lo stesso risultato ottenuto in un altro modo (segno degli autovalori): serve da verifica."""
    autovalori = np.linalg.eigvalsh(np.array(hessiana.tolist(), dtype=float))
    if np.any(np.abs(autovalori) < 1e-9):
        return "dubbio"
    if np.all(autovalori > 0):
        return "minimo"
    if np.all(autovalori < 0):
        return "massimo"
    return "sella"


def risolvi_critici(p: Problema) -> Svolgimento:
    f = p.funzione
    x, y = p.variabili
    fx, fy = riordina(sympy.diff(f, x)), riordina(sympy.diff(f, y))
    passi = [
        Passaggio(
            "Derivate parziali",
            "Calcoliamo le due derivate parziali prime: sono le componenti del gradiente.",
            rf"f_{{{L(x)}}} = {L(fx)}, \qquad f_{{{L(y)}}} = {L(fy)}",
            "derivate_parziali",
        )
    ]

    # --- sistema: gradiente uguale a zero ---
    try:
        soluzioni = sympy.solve([fx, fy], [x, y], dict=True)
    except Exception:
        raise ErroreRisolutore("Non riesco a risolvere il sistema delle derivate parziali per questa funzione.")
    if any(s.get(x, x).free_symbols or s.get(y, y).free_symbols for s in soluzioni):
        raise ErroreRisolutore(
            "Questa funzione ha infiniti punti critici (formano una curva): per ora so classificare solo punti isolati."
        )
    punti = [(s[x], s[y]) for s in soluzioni if _reale(s[x]) and _reale(s[y])]
    punti = sorted(set(punti), key=lambda q: (come_numero(q[0]), come_numero(q[1])))

    sistema = rf"\begin{{cases}} {L(fx)} = 0 \\ {L(fy)} = 0 \end{{cases}}"
    passi.append(
        Passaggio(
            "Annulliamo il gradiente",
            "Nei punti di massimo e minimo interni il gradiente è nullo. Risolviamo il sistema: "
            + ("le soluzioni sono i punti critici." if punti else "non ha soluzioni reali, quindi non ci sono punti critici."),
            sistema + (r" \quad\Rightarrow\quad " + r", \quad ".join(_coppia(x, y, a, b) for a, b in punti) if punti else ""),
            "punti_critici",
        )
    )
    if not punti:
        return Svolgimento(
            risultato=None,
            risultato_latex=r"\text{nessun punto critico}",
            risposta_latex=r"\text{La funzione non ha punti critici.}",
            metodo="gradiente e matrice hessiana",
            passaggi=passi,
            verificato=True,
            grafico=_dati_superficie(f, x, y, _finestra([], [])),
        )

    # --- matrice hessiana ---
    fxx, fxy, fyy = (riordina(sympy.diff(f, a, b)) for a, b in ((x, x), (x, y), (y, y)))
    hessiana = sympy.Matrix([[fxx, fxy], [fxy, fyy]])
    determinante = riordina(hessiana.det())
    passi.append(
        Passaggio(
            "Matrice hessiana",
            "Calcoliamo le derivate parziali seconde e le raccogliamo nella matrice hessiana. "
            "Il segno del suo determinante ci dirà la natura di ogni punto critico.",
            rf"H = \begin{{pmatrix}} {L(fxx)} & {L(fxy)} \\ {L(fxy)} & {L(fyy)} \end{{pmatrix}}, \qquad \det H = {L(determinante)}",
            "hessiana",
        )
    )

    # --- classificazione di ogni punto ---
    trovati, verificato, righe = [], True, []
    for a, b in punti:
        dove = {x: a, y: b}
        det_qui, fxx_qui = sympy.simplify(determinante.subs(dove)), sympy.simplify(fxx.subs(dove))
        tipo = _classifica(come_numero(det_qui) or 0.0, come_numero(fxx_qui) or 0.0)
        valore = riordina(f.subs(dove))
        if tipo == "sella":
            perche = "Il determinante è negativo: punto di sella."
        elif tipo == "dubbio":
            perche = "Il determinante è nullo: il criterio dell'hessiana non permette di concludere."
        else:
            verso = "positiva" if tipo == "minimo" else "negativa"
            perche = f"Il determinante è positivo e $f_{{{L(x)}{L(x)}}}$ è {verso}: {NOMI_TIPO[tipo]}."
        passi.append(
            Passaggio(
                f"Classifichiamo il punto ({sympy.sstr(a)}, {sympy.sstr(b)})",
                perche,
                rf"\det H{_coppia(x, y, a, b)} = {L(det_qui)}, \qquad f_{{{L(x)}{L(x)}}}{_coppia(x, y, a, b)} = {L(fxx_qui)}, "
                rf"\qquad f{_coppia(x, y, a, b)} = {L(valore)}",
                "hessiana",
            )
        )
        righe.append(rf"{_coppia(x, y, a, b)}: \ \text{{{NOMI_TIPO[tipo]}}}")
        trovati.append({"x": come_numero(a), "y": come_numero(b), "z": come_numero(valore), "tipo": tipo})

        # Verifica indipendente: gradiente davvero nullo e stessa natura con gli autovalori
        gradiente_nullo = abs(come_numero(fx.subs(dove)) or 0) < 1e-7 and abs(come_numero(fy.subs(dove)) or 0) < 1e-7
        try:
            stessa_natura = _classifica_con_autovalori(hessiana.subs(dove)) == tipo
        except Exception:
            stessa_natura = False
        verificato = verificato and gradiente_nullo and stessa_natura

    elenco = r" \\ ".join(righe)
    finestra = _finestra([q["x"] for q in trovati], [q["y"] for q in trovati])
    return Svolgimento(
        risultato=None,
        risultato_latex=rf"\begin{{array}}{{l}} {elenco} \end{{array}}",
        risposta_latex=rf"\begin{{array}}{{l}} {elenco} \end{{array}}",
        metodo="gradiente e matrice hessiana",
        passaggi=passi,
        verificato=verificato,
        grafico=_dati_superficie(f, x, y, finestra, trovati),
    )


# ---------- massimi e minimi vincolati ----------

RAGGIO = 8.0  # cerchiamo la curva del vincolo nel quadrato [-RAGGIO, RAGGIO] x [-RAGGIO, RAGGIO]


def _punti_sul_vincolo(g, x, y) -> tuple[np.ndarray, np.ndarray]:
    """
    Trova numericamente molti punti della curva g(x, y) = 0: calcola g su una griglia fitta
    e, dove cambia segno tra due nodi vicini, stima il punto esatto dell'attraversamento.
    """
    calcola = sympy.lambdify((x, y), g, "numpy")
    asse = np.linspace(-RAGGIO, RAGGIO, 801)
    X, Y = np.meshgrid(asse, asse)
    with np.errstate(all="ignore"):
        G = np.broadcast_to(np.asarray(calcola(X, Y), dtype=float), X.shape)
    xs, ys = [], []
    for A, B, XA, XB, YA, YB in (
        (G[:, :-1], G[:, 1:], X[:, :-1], X[:, 1:], Y[:, :-1], Y[:, 1:]),  # coppie di nodi affiancati
        (G[:-1, :], G[1:, :], X[:-1, :], X[1:, :], Y[:-1, :], Y[1:, :]),  # coppie di nodi sovrapposti
    ):
        cambia = np.isfinite(A) & np.isfinite(B) & (A * B < 0)
        t = A[cambia] / (A[cambia] - B[cambia])  # posizione dello zero tra i due nodi (da 0 a 1)
        xs.append(XA[cambia] + t * (XB[cambia] - XA[cambia]))
        ys.append(YA[cambia] + t * (YB[cambia] - YA[cambia]))
    return np.concatenate(xs), np.concatenate(ys)


def risolvi_vincolati(p: Problema) -> Svolgimento:
    f, g = p.funzione, p.vincolo
    x, y = p.variabili
    lam = sympy.Symbol("lambda")
    fx, fy, gx, gy = (riordina(sympy.diff(e, v)) for e, v in ((f, x), (f, y), (g, x), (g, y)))

    passi = [
        Passaggio(
            "Impostiamo il problema",
            "Scriviamo il vincolo nella forma $g(x, y) = 0$. Nei punti di massimo e minimo vincolato il gradiente "
            "di $f$ è parallelo al gradiente di $g$: esiste un numero $\\lambda$ (moltiplicatore di Lagrange) "
            "tale che $\\nabla f = \\lambda \\nabla g$.",
            rf"g({L(x)}, {L(y)}) = {L(g)} = 0, \qquad \nabla f = \left({L(fx)},\ {L(fy)}\right), \qquad \nabla g = \left({L(gx)},\ {L(gy)}\right)",
            "lagrange",
        )
    ]

    try:
        soluzioni = sympy.solve([fx - lam * gx, fy - lam * gy, g], [x, y, lam], dict=True)
    except Exception:
        raise ErroreRisolutore("Non riesco a risolvere il sistema di Lagrange per questo esercizio.")
    candidati = sorted(
        {(s[x], s[y]) for s in soluzioni if x in s and y in s and _reale(s[x]) and _reale(s[y])},
        key=lambda q: (come_numero(q[0]), come_numero(q[1])),
    )
    if not candidati:
        raise ErroreRisolutore("Il sistema di Lagrange non ha soluzioni reali: non trovo punti candidati sul vincolo.")

    sistema = rf"\begin{{cases}} {L(fx)} = \lambda \left({L(gx)}\right) \\ {L(fy)} = \lambda \left({L(gy)}\right) \\ {L(g)} = 0 \end{{cases}}"
    passi.append(
        Passaggio(
            "Sistema di Lagrange",
            "Mettiamo a sistema le due equazioni $\\nabla f = \\lambda \\nabla g$ con il vincolo e risolviamo: "
            "le soluzioni sono i punti candidati.",
            sistema + r" \quad\Rightarrow\quad " + r", \quad ".join(_coppia(x, y, a, b) for a, b in candidati),
            "lagrange",
        )
    )

    valori = [riordina(f.subs({x: a, y: b})) for a, b in candidati]
    numeri = [come_numero(v) for v in valori]
    passi.append(
        Passaggio(
            "Valore della funzione nei candidati",
            "Calcoliamo $f$ in ogni punto candidato.",
            r", \qquad ".join(rf"f{_coppia(x, y, a, b)} = {L(v)}" for (a, b), v in zip(candidati, valori)),
        )
    )

    # --- la curva del vincolo, cercata numericamente: serve per capire se è limitata e per la verifica ---
    try:
        cx, cy = _punti_sul_vincolo(g, x, y)
        with np.errstate(all="ignore"):
            f_sulla_curva = np.asarray(sympy.lambdify((x, y), f, "numpy")(cx, cy), dtype=float)
    except Exception:
        cx = cy = f_sulla_curva = np.array([])
    trovata = cx.size > 20
    # Se la curva tocca il bordo della zona esplorata, quasi certamente prosegue all'infinito
    limitata = trovata and float(np.max(np.abs(np.concatenate([cx, cy])))) < RAGGIO * 0.97

    massimo, minimo = max(numeri), min(numeri)
    tolleranza = 1e-3 * (1 + abs(massimo) + abs(minimo))
    trovati, righe = [], []
    verificato = all(abs(come_numero(g.subs({x: a, y: b})) or 0) < 1e-7 for a, b in candidati)

    if limitata:
        # Vincolo chiuso e limitato: massimo e minimo assoluti esistono e sono tra i candidati
        for (a, b), v, n in zip(candidati, valori, numeri):
            tipo = "massimo" if abs(n - massimo) < 1e-9 else "minimo" if abs(n - minimo) < 1e-9 else "candidato"
            trovati.append({"x": come_numero(a), "y": come_numero(b), "z": n, "tipo": tipo})
        v_max = valori[numeri.index(massimo)]
        v_min = valori[numeri.index(minimo)]
        dove_max = r",\ ".join(_coppia(x, y, a, b) for (a, b), n in zip(candidati, numeri) if abs(n - massimo) < 1e-9)
        dove_min = r",\ ".join(_coppia(x, y, a, b) for (a, b), n in zip(candidati, numeri) if abs(n - minimo) < 1e-9)
        righe = [rf"\max f = {L(v_max)} \ \text{{ in }} \ {dove_max}", rf"\min f = {L(v_min)} \ \text{{ in }} \ {dove_min}"]
        passi.append(
            Passaggio(
                "Confronto dei valori",
                "Il vincolo è una curva chiusa e limitata e $f$ è continua: per il teorema di Weierstrass massimo e "
                "minimo assoluti esistono, e si trovano tra i candidati. Basta confrontare i valori.",
                r", \qquad ".join(righe),
                "weierstrass",
            )
        )
        # Verifica indipendente: lungo tutta la curva nessun valore supera il massimo o scende sotto il minimo
        buoni = f_sulla_curva[np.isfinite(f_sulla_curva)]
        if buoni.size:
            verificato = verificato and buoni.max() <= massimo + tolleranza and buoni.min() >= minimo - tolleranza
            verificato = verificato and abs(buoni.max() - massimo) < 50 * tolleranza and abs(buoni.min() - minimo) < 50 * tolleranza
    else:
        # Vincolo illimitato (o non trovato): possiamo solo dire cosa succede vicino a ogni candidato
        for (a, b), v, n in zip(candidati, valori, numeri):
            na, nb = come_numero(a), come_numero(b)
            tipo = "candidato"
            if trovata:
                vicini = (np.hypot(cx - na, cy - nb) < 0.4) & np.isfinite(f_sulla_curva)
                if vicini.sum() >= 4:
                    if np.all(f_sulla_curva[vicini] <= n + tolleranza):
                        tipo = "massimo"
                    elif np.all(f_sulla_curva[vicini] >= n - tolleranza):
                        tipo = "minimo"
            nome = {"massimo": "massimo vincolato relativo", "minimo": "minimo vincolato relativo", "candidato": "né massimo né minimo"}[tipo]
            righe.append(rf"{_coppia(x, y, a, b)}: \ \text{{{nome}}}, \ f = {L(v)}")
            trovati.append({"x": na, "y": nb, "z": n, "tipo": tipo})
        passi.append(
            Passaggio(
                "Natura dei candidati",
                "Qui il vincolo non è una curva chiusa e limitata, quindi il teorema di Weierstrass non si applica e "
                "non è detto che esistano massimo e minimo assoluti. Guardiamo come si comporta $f$ lungo il vincolo "
                "vicino a ogni candidato.",
                rf"\begin{{array}}{{l}} {r' \\ '.join(righe)} \end{{array}}",
                "weierstrass",
            )
        )

    risposta = rf"\begin{{array}}{{l}} {r' \\ '.join(righe)} \end{{array}}"
    if limitata:
        finestra = _finestra([float(cx.min()), float(cx.max())], [float(cy.min()), float(cy.max())], 0.8)
    else:
        finestra = _finestra([q["x"] for q in trovati], [q["y"] for q in trovati], 2.5)
    return Svolgimento(
        risultato=None,
        risultato_latex=risposta,
        risposta_latex=risposta,
        metodo="moltiplicatori di Lagrange",
        passaggi=passi,
        verificato=verificato,
        grafico=_dati_superficie(f, x, y, finestra, trovati, vincolo=in_js(g)),
    )


# ---------- integrali doppi ----------


def risolvi_doppio(p: Problema) -> Svolgimento:
    f, esterna, interna = p.funzione, p.variabile, p.interna
    a, b, c, d = p.estremo_a, p.estremo_b, p.interno_a, p.interno_b
    rettangolo = not (c.free_symbols or d.free_symbols)

    passi = [
        Passaggio(
            "Formula di riduzione",
            (
                "Il dominio è un rettangolo: l'integrale doppio si calcola con due integrali semplici, uno dentro l'altro."
                if rettangolo
                else f"Il dominio è normale rispetto all'asse ${L(esterna)}$: per ogni ${L(esterna)}$ fissato, "
                f"${L(interna)}$ varia tra ${L(c)}$ e ${L(d)}$. L'integrale doppio si riduce a due integrali semplici."
            )
            + f" Si parte da quello interno, in ${L(interna)}$, trattando ${L(esterna)}$ come una costante.",
            rf"\iint_D {L(f)} \, d{L(esterna)}\, d{L(interna)} = \int_{{{L(a)}}}^{{{L(b)}}} \left( \int_{{{L(c)}}}^{{{L(d)}}} {L(f)} \, d{L(interna)} \right) d{L(esterna)}",
            "integrale_doppio",
        )
    ]

    # --- integrale interno ---
    interno = risolvi_integrale(Problema(tipo="integrale", funzione=f, variabile=interna, estremo_a=c, estremo_b=d))
    passi.append(Passaggio("Integrale interno", f"Integriamo rispetto a ${L(interna)}$.", rf"\int_{{{L(c)}}}^{{{L(d)}}} {L(f)} \, d{L(interna)}"))
    passi.extend(interno.passaggi)
    intermedio = riordina(interno.risultato)

    # --- integrale esterno ---
    esterno = risolvi_integrale(Problema(tipo="integrale", funzione=intermedio, variabile=esterna, estremo_a=a, estremo_b=b))
    passi.append(
        Passaggio(
            "Integrale esterno",
            f"Il risultato dell'integrale interno è una funzione della sola ${L(esterna)}$: la integriamo tra gli estremi.",
            rf"\int_{{{L(a)}}}^{{{L(b)}}} {L(intermedio)} \, d{L(esterna)}",
        )
    )
    passi.extend(esterno.passaggi)
    valore = esterno.risultato

    # Verifica indipendente: SymPy calcola l'integrale doppio in un colpo solo
    riferimento = sympy.integrate(f, (interna, c, d), (esterna, a, b))
    verificato = not riferimento.has(sympy.Integral) and uguali(valore, riferimento)

    # --- dati per il disegno del dominio ---
    grafico = None
    try:
        na, nb = come_numero(a), come_numero(b)
        campioni = [na + (nb - na) * i / 40 for i in range(41)]
        bordi = [come_numero(e.subs(esterna, t)) for t in campioni for e in (c, d)]
        bordi = [v for v in bordi if v is not None]
        orizzontale, verticale = [na, nb], [min(bordi), max(bordi)]
        x, y = sorted((esterna, interna), key=str)  # nel disegno x è sempre in orizzontale
        finestra = _finestra(orizzontale if esterna == x else verticale, verticale if esterna == x else orizzontale, 0.6)
        grafico = _dati_superficie(
            f, x, y, finestra,
            dominio={"esterna": str(esterna), "a": na, "b": nb, "inferiore": in_js(c), "superiore": in_js(d)},
        )  # fmt: skip
    except Exception:
        pass

    return Svolgimento(
        risultato=valore,
        metodo="formule di riduzione",
        passaggi=passi,
        dettagliato=interno.dettagliato and esterno.dettagliato,
        verificato=verificato,
        grafico=grafico,
    )
