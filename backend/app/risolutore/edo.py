"""
Risolutore delle equazioni differenziali ordinarie (EDO):

- primo ordine a variabili separabili:        y' = g(x) · h(y)
- primo ordine lineari:                        y' + a(x) y = b(x)
- secondo ordine lineari a coefficienti costanti, omogenee e non omogenee:
                                               a y'' + b y' + c y = f(x)
- problemi di Cauchy (con le condizioni iniziali) per tutti i tipi sopra.

La soluzione trovata viene sempre sostituita nell'equazione di partenza: se non la
soddisfa (o non rispetta le condizioni iniziali), non viene mostrata.
"""

import sympy

from app.grafici.formule import in_js
from app.risolutore.modelli import ErroreRisolutore, L, Passaggio, Problema, Svolgimento, riordina
from app.risolutore.verifica import uguali

# I simboli con cui l'equazione arriva dall'interprete
Y, Y1, Y2 = sympy.Symbol("y"), sympy.Symbol("y'"), sympy.Symbol("y''")
# Le costanti arbitrarie della soluzione generale
C1, C2 = sympy.symbols("c_1 c_2")


def _rinomina_costanti(espressione: sympy.Expr) -> sympy.Expr:
    """SymPy chiama le costanti C1, C2: noi le scriviamo c_1, c_2."""
    return espressione.subs({sympy.Symbol("C1"): C1, sympy.Symbol("C2"): C2})


def _rami_sympy(equazione: sympy.Expr, x: sympy.Symbol) -> list[sympy.Expr]:
    """
    Soluzioni generali calcolate direttamente da SymPy, in forma esplicita (y = ...).
    Possono essere più di una: per esempio i due rami con il segno + e - davanti a una radice.
    """
    funzione = sympy.Function("y")(x)
    ode = equazione.subs({Y2: funzione.diff(x, 2), Y1: funzione.diff(x), Y: funzione})
    try:
        soluzioni = sympy.dsolve(ode, funzione)
    except Exception:
        return []
    if not isinstance(soluzioni, list):
        soluzioni = [soluzioni]
    # Scartiamo le soluzioni date solo in forma implicita
    return [_rinomina_costanti(s.rhs) for s in soluzioni if s.lhs == funzione]


def _con_sympy(equazione: sympy.Expr, x: sympy.Symbol) -> sympy.Expr | None:
    """Il primo ramo della soluzione generale di SymPy; None se non ne trova in forma esplicita."""
    rami = _rami_sympy(equazione, x)
    return rami[0] if rami else None


def _soddisfa(equazione: sympy.Expr, x: sympy.Symbol, soluzione: sympy.Expr) -> bool:
    """Sostituisce la soluzione nell'equazione e controlla che il risultato sia zero."""
    residuo = equazione.subs({Y2: sympy.diff(soluzione, x, 2), Y1: sympy.diff(soluzione, x), Y: soluzione})
    return uguali(residuo, sympy.S.Zero)


# ---------- primo ordine ----------


def _primo_ordine(equazione: sympy.Expr, x: sympy.Symbol) -> tuple[sympy.Expr, list[Passaggio], str] | None:
    try:
        forme = sympy.solve(equazione, Y1)
    except Exception:
        return None
    if len(forme) != 1:
        return None
    F = sympy.simplify(forme[0])
    passi = [Passaggio("Forma normale", "Isoliamo la derivata: scriviamo l'equazione nella forma $y' = F(x, y)$.", rf"y' = {L(F)}")]

    # --- è lineare?  y' = -a(x) y + b(x) ---
    a = b = None
    try:
        polinomio = sympy.Poly(F, Y)
        if polinomio.degree() <= 1:
            a, b = -polinomio.coeff_monomial(Y), polinomio.coeff_monomial(1)
            if a.has(Y) or b.has(Y):
                a = b = None
    except sympy.PolynomialError:
        pass

    # --- è a variabili separabili?  y' = g(x) h(y) ---
    separata = sympy.separatevars(F, symbols=[x, Y], dict=True)

    if a is not None and b != 0 and a != 0:
        # ----- lineare (non omogenea) -----
        A = riordina(sympy.integrate(a, x))
        fattore = sympy.exp(A)
        integrale = riordina(sympy.integrate(sympy.simplify(fattore * b), x))
        if A.has(sympy.Integral) or integrale.has(sympy.Integral):
            return None
        generale = sympy.expand((integrale + C1) / fattore)
        passi += [
            Passaggio(
                "Equazione lineare del primo ordine",
                "L'equazione ha la forma $y' + a(x)\\,y = b(x)$.",
                rf"y' + \left({L(a)}\right) y = {L(b)}",
                "edo_lineari_primo",
            ),
            Passaggio(
                "Fattore integrante",
                "Calcoliamo una primitiva $A(x)$ di $a(x)$ e moltiplichiamo tutta l'equazione per $e^{A(x)}$: "
                "a sinistra compare la derivata del prodotto $e^{A(x)} y$.",
                rf"A(x) = \int {L(a)} \, dx = {L(A)}, \qquad \left({L(fattore)} \, y\right)' = {L(sympy.simplify(fattore * b))}",
                "edo_lineari_primo",
            ),
            Passaggio(
                "Integriamo",
                "Integriamo entrambi i membri (compare la costante $c_1$) e dividiamo per il fattore integrante.",
                rf"{L(fattore)} \, y = {L(integrale)} + c_1 \quad\Rightarrow\quad y = {L(generale)}",
                "edo_lineari_primo",
            ),
        ]
        return generale, passi, "equazione lineare del primo ordine"

    if separata is not None:
        g = sympy.simplify(separata["coeff"] * separata[x])
        h = sympy.simplify(separata[Y])
        generale = _con_sympy(equazione, x)
        if generale is None:
            return None

        if h == 1:
            # ----- y' dipende solo da x: basta integrare -----
            passi.append(
                Passaggio(
                    "Integrazione diretta",
                    "La derivata dipende solo da $x$: la soluzione è una qualsiasi primitiva.",
                    rf"y = \int {L(g)} \, dx = {L(generale)}",
                    "integrali_immediati",
                )
            )
            return generale, passi, "integrazione diretta"

        # ----- variabili separabili -----
        sinistra = riordina(sympy.integrate(1 / h, Y))
        destra = riordina(sympy.integrate(g, x))
        if sinistra.has(sympy.Integral) or destra.has(sympy.Integral):
            return None
        costanti = [s for s in sympy.solve(h, Y) if not s.free_symbols]
        passi += [
            Passaggio(
                "Variabili separabili",
                "Il secondo membro è il prodotto di una funzione della sola $x$ per una funzione della sola $y$. "
                "Portiamo tutto ciò che contiene $y$ a sinistra e tutto ciò che contiene $x$ a destra."
                + (
                    " Dividendo perdiamo le soluzioni costanti " + ", ".join(f"$y = {L(k)}$" for k in costanti) + ": vanno ricordate a parte."
                    if costanti
                    else ""
                ),
                rf"y' = \left({L(g)}\right) \cdot \left({L(h)}\right) \quad\Rightarrow\quad \frac{{dy}}{{{L(h)}}} = {L(g)} \, dx",
                "edo_separabili",
            ),
            Passaggio(
                "Integriamo entrambi i membri",
                "A sinistra integriamo rispetto a $y$, a destra rispetto a $x$. Basta una sola costante arbitraria.",
                rf"\int \frac{{dy}}{{{L(h)}}} = \int {L(g)} \, dx \quad\Rightarrow\quad {L(sinistra)} = {L(destra)} + c",
                "edo_separabili",
            ),
            Passaggio(
                "Ricaviamo y",
                "Esplicitiamo $y$. La costante viene rinominata $c_1$ (per esempio $e^{c}$ diventa una nuova costante).",
                rf"y = {L(generale)}",
                "edo_separabili",
            ),
        ]
        return generale, passi, "variabili separabili"

    return None


# ---------- secondo ordine a coefficienti costanti ----------


def _secondo_ordine(equazione: sympy.Expr, x: sympy.Symbol) -> tuple[sympy.Expr, list[Passaggio], str] | None:
    a, b, c = sympy.diff(equazione, Y2), sympy.diff(equazione, Y1), sympy.diff(equazione, Y)
    resto = sympy.simplify(equazione - a * Y2 - b * Y1 - c * Y)
    # Deve essere lineare, con coefficienti numerici, e il resto deve dipendere solo da x
    if a == 0 or any(k.free_symbols for k in (a, b, c)) or resto.has(Y, Y1, Y2):
        return None
    f = -resto  # termine noto:  a y'' + b y' + c y = f(x)

    lam = sympy.Symbol("lambda")
    caratteristica = a * lam**2 + b * lam + c
    delta = sympy.simplify(b**2 - 4 * a * c)
    passi = []
    if f != 0:
        passi.append(
            Passaggio(
                "Equazione omogenea associata",
                "La soluzione generale è la somma di due pezzi: la soluzione generale dell'equazione omogenea associata "
                "(quella con zero al posto del termine noto) più una soluzione particolare dell'equazione completa. "
                "Partiamo dall'omogenea.",
                rf"{L(a * Y2 + b * Y1 + c * Y)} = 0",
                "edo_caratteristica",
            )
        )

    if delta > 0:
        r1, r2 = sorted(sympy.solve(caratteristica, lam), key=lambda r: float(r))
        omogenea = C1 * sympy.exp(r1 * x) + C2 * sympy.exp(r2 * x)
        caso = "Il discriminante è positivo: due radici reali distinte. A ciascuna corrisponde un esponenziale."
        radici = rf"\lambda_1 = {L(r1)}, \quad \lambda_2 = {L(r2)}"
    elif delta == 0:
        r = sympy.Rational(-1, 2) * b / a
        omogenea = (C1 + C2 * x) * sympy.exp(r * x)
        caso = "Il discriminante è nullo: una radice reale doppia. La seconda soluzione si ottiene moltiplicando l'esponenziale per $x$."
        radici = rf"\lambda_1 = \lambda_2 = {L(r)}"
    else:
        alfa = -b / (2 * a)
        beta = sympy.sqrt(-delta) / (2 * sympy.Abs(a))
        omogenea = sympy.exp(alfa * x) * (C1 * sympy.cos(beta * x) + C2 * sympy.sin(beta * x))
        caso = (
            "Il discriminante è negativo: due radici complesse coniugate $\\alpha \\pm i\\beta$. "
            "La parte reale dà un esponenziale, la parte immaginaria seno e coseno."
        )
        radici = rf"\lambda = {L(alfa)} \pm {L(beta)}\, i"

    passi += [
        Passaggio(
            "Equazione caratteristica",
            "Cerchiamo soluzioni del tipo $y = e^{\\lambda x}$: sostituendo si ottiene un'equazione di secondo grado in $\\lambda$. " + caso,
            rf"{L(caratteristica)} = 0, \qquad \Delta = {L(delta)}, \qquad {radici}",
            "edo_caratteristica",
        ),
        Passaggio(
            "Soluzione dell'omogenea" if f != 0 else "Soluzione generale",
            "Combiniamo le due soluzioni trovate con due costanti arbitrarie.",
            rf"y{'_o' if f != 0 else ''} = {L(omogenea)}",
            "edo_caratteristica",
        ),
    ]
    if f == 0:
        return omogenea, passi, "equazione caratteristica"

    # --- soluzione particolare dell'equazione completa ---
    completa = _con_sympy(equazione, x)
    if completa is None:
        return None
    particolare = riordina(sympy.expand(completa.subs({C1: 0, C2: 0})))
    if not _soddisfa(equazione, x, particolare):
        return None
    sostituita = riordina(a * sympy.diff(particolare, x, 2) + b * sympy.diff(particolare, x) + c * particolare)
    passi += [
        Passaggio(
            "Soluzione particolare",
            f"Il termine noto è ${L(f)}$: cerchiamo una soluzione particolare che gli somigli (metodo di somiglianza), "
            "con coefficienti da determinare. Sostituendola nell'equazione e uguagliando i due membri si trovano i coefficienti.",
            rf"y_p = {L(particolare)}",
            "edo_particolare",
        ),
        Passaggio(
            "Controlliamo la soluzione particolare",
            "Sostituiamo $y_p$ nell'equazione: deve restituire proprio il termine noto.",
            rf"{L(a * Y2 + b * Y1 + c * Y).replace('y', 'y_p')} = {L(sostituita)}",
        ),
        Passaggio(
            "Soluzione generale",
            "Sommiamo la soluzione dell'omogenea e la soluzione particolare.",
            rf"y = y_o + y_p = {L(omogenea + particolare)}",
            "edo_particolare",
        ),
    ]
    return omogenea + particolare, passi, "omogenea associata più soluzione particolare"


# ---------- il risolutore ----------

# Valori dati alle costanti per disegnare alcune curve della famiglia di soluzioni
VALORI_FAMIGLIA = [(1, 0), (-1, 0), (2, 0), (-2, 0), (0.5, 0), (0, 1), (1, 1), (-1, 1), (0, -1)]


def risolvi_edo(p: Problema) -> Svolgimento:
    equazione, x = p.funzione, p.variabile
    ordine = 2 if equazione.has(Y2) else 1
    if not equazione.has(Y1, Y2):
        raise ErroreRisolutore("Nell'equazione non compare nessuna derivata di y: non è un'equazione differenziale.")
    if len(p.condizioni) not in (0, ordine):
        raise ErroreRisolutore(
            "Per un problema di Cauchy del primo ordine serve una condizione, y(x0) = y0; "
            "per il secondo ordine ne servono due, y(x0) = y0 e y'(x0) = y1."
        )

    esito = (_primo_ordine if ordine == 1 else _secondo_ordine)(equazione, x)
    dettagliato = True
    if esito is None:
        # Tipo di equazione che non so spiegare: chiediamo direttamente a SymPy
        generale = _con_sympy(equazione, x)
        if generale is None:
            raise ErroreRisolutore("Non riesco a risolvere questa equazione differenziale in forma esplicita.")
        dettagliato = False
        passi = [
            Passaggio(
                "Soluzione generale",
                "Per questo tipo di equazione non so ancora mostrare i passaggi: qui trovi la soluzione calcolata da SymPy.",
                rf"y = {L(generale)}",
            )
        ]
        metodo = "calcolo diretto"
    else:
        generale, passi, metodo = esito

    soluzione = generale
    verificato = _soddisfa(equazione, x, generale)

    # --- problema di Cauchy: determiniamo le costanti ---
    if p.condizioni:
        apici = {0: "", 1: "'"}

        def rispetta_le_condizioni(candidata: sympy.Expr) -> bool:
            return all(uguali(sympy.diff(candidata, x, k).subs(x, x0), valore) for k, x0, valore in p.condizioni)

        # Se la soluzione generale ha più rami (es. ± radice), cerchiamo quello che passa per il punto dato
        rami = [generale] + [r for r in _rami_sympy(equazione, x) if not uguali(r, generale)]
        costanti = None
        for ramo in rami:
            equazioni = [sympy.diff(ramo, x, k).subs(x, x0) - valore for k, x0, valore in p.condizioni]
            incognite = sorted(ramo.free_symbols & {C1, C2}, key=str)
            try:
                trovate = sympy.solve(equazioni, incognite, dict=True)
            except Exception:
                trovate = []
            adatte = [t for t in trovate if rispetta_le_condizioni(ramo.subs(t))]
            if adatte:
                generale, costanti = ramo, adatte[0]
                break
        if costanti is None:
            raise ErroreRisolutore("Non riesco a determinare le costanti: le condizioni iniziali non sono compatibili con la soluzione trovata.")
        # Scrittura sviluppata (es. cos(2x) + sin(2x)), più riconoscibile di una forma "compressa"
        sviluppata = sympy.expand(generale.subs(costanti))
        soluzione = min([sviluppata, sympy.factor(sviluppata)], key=lambda e: len(sympy.latex(e)))
        passi.append(
            Passaggio(
                "Condizioni iniziali",
                "Imponiamo le condizioni iniziali alla soluzione generale: otteniamo "
                + ("un'equazione" if len(equazioni) == 1 else "un sistema")
                + " da cui ricavare "
                + ("la costante." if len(incognite) == 1 else "le costanti."),
                r", \qquad ".join(rf"y{apici[k]}\left({L(x0)}\right) = {L(v)}" for k, x0, v in p.condizioni)
                + r" \quad\Rightarrow\quad "
                + r", \quad ".join(rf"{L(k)} = {L(v)}" for k, v in costanti.items()),
                "problema_cauchy",
            )
        )
        passi.append(Passaggio("Soluzione del problema di Cauchy", "Sostituiamo i valori trovati nella soluzione generale.", rf"y = {L(soluzione)}"))
        # Verifica: la soluzione soddisfa l'equazione e tutte le condizioni iniziali
        verificato = _soddisfa(equazione, x, soluzione) and all(
            uguali(sympy.diff(soluzione, x, k).subs(x, x0), valore) for k, x0, valore in p.condizioni
        )

    # --- dati per il grafico: la soluzione, oppure alcune curve della famiglia ---
    grafico = None
    try:
        liberi = sorted(soluzione.free_symbols & {C1, C2}, key=str)
        if not liberi:
            curve = [in_js(soluzione)]
        else:
            curve = []
            for v1, v2 in VALORI_FAMIGLIA:
                if len(liberi) == 1 and v2 != 0:
                    continue
                curve.append(in_js(soluzione.subs({C1: sympy.nsimplify(v1), C2: sympy.nsimplify(v2)})))
        grafico = {"tipo": "funzione", "funzione": curve[0], "variabile": str(x), "derivata": None, "punto": None, "area": None, "altre": curve[1:]}
    except Exception:
        pass

    return Svolgimento(
        risultato=soluzione,
        risultato_latex=rf"y = {L(soluzione)}",
        risposta_latex=rf"y({L(x)}) = {L(soluzione)}",
        metodo=metodo,
        passaggi=passi,
        dettagliato=dettagliato,
        verificato=verificato,
        grafico=grafico,
    )
