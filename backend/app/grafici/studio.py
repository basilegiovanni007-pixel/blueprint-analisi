"""
Studio di funzione: dominio, simmetrie, intersezioni, segno, asintoti, massimi e minimi,
flessi. Ogni tappa produce una spiegazione e gli "elementi" da far comparire sul grafico
(punti, rette, fasce), così il disegno cresce insieme alla spiegazione.
"""

import math

import sympy
from sympy import FiniteSet, Interval, S, Union, oo
from sympy.calculus.util import continuous_domain

from app.grafici.formule import come_numero, in_js
from app.risolutore.modelli import L, riordina

RAGGIO = 12  # se le soluzioni sono infinite (funzioni periodiche) guardiamo solo [-RAGGIO, RAGGIO]
INFINITI = (oo, -oo)


def _insieme(insieme) -> str:
    """Scrive un insieme in LaTeX."""
    return L(insieme)


def _punti_esatti(insieme) -> tuple[list, bool] | None:
    """
    Estrae i punti da un insieme di soluzioni. Restituisce (punti, sono_tutti) oppure None
    se SymPy non è riuscito a scriverli in forma esatta.
    """
    if isinstance(insieme, FiniteSet):
        return sorted((p for p in insieme if p.is_real), key=lambda p: float(sympy.N(p))), True
    ristretto = insieme.intersect(Interval(-RAGGIO, RAGGIO))
    if isinstance(ristretto, FiniteSet):
        return sorted((p for p in ristretto if p.is_real), key=lambda p: float(sympy.N(p))), False
    return None


def _radici_numeriche(g: sympy.Expr, x: sympy.Symbol) -> list[float]:
    """Cerca gli zeri di g in [-RAGGIO, RAGGIO] in modo approssimato, dove cambia segno."""
    calcola = sympy.lambdify(x, g, "math")

    def valore(t: float) -> float | None:
        try:
            v = calcola(t)
            return v if isinstance(v, (int, float)) and math.isfinite(v) else None
        except Exception:
            return None

    radici: list[float] = []
    passi = 2400
    precedente_t, precedente_v = None, None
    for i in range(passi + 1):
        t = -RAGGIO + 2 * RAGGIO * i / passi + 1e-7  # piccolo spostamento per non cadere su punti speciali
        v = valore(t)
        if v is not None and precedente_v is not None and v * precedente_v < 0 and abs(v - precedente_v) < 50:
            a, b, va = precedente_t, t, precedente_v
            for _ in range(60):  # bisezione: dimezziamo l'intervallo finché è piccolissimo
                m = (a + b) / 2
                vm = valore(m)
                if vm is None:
                    break
                if va * vm <= 0:
                    b = m
                else:
                    a, va = m, vm
            radici.append(round((a + b) / 2, 6))
        precedente_t, precedente_v = t, v
    return radici


def _soluzioni(g: sympy.Expr, x: sympy.Symbol, dominio) -> tuple[list, str]:
    """
    Risolve g(x) = 0 nel dominio. Restituisce (punti, nota) dove i punti sono valori SymPy
    (esatti) o numeri decimali (approssimati) e la nota spiega eventuali limiti.
    """
    try:
        esatti = _punti_esatti(sympy.solveset(g, x, dominio))
    except Exception:
        esatti = None
    if esatti is not None:
        punti, tutti = esatti
        return punti, "" if tutti else f" (sono infiniti: mostro quelli tra ${-RAGGIO}$ e ${RAGGIO}$)"
    approssimati = [sympy.Float(r, 6) for r in _radici_numeriche(g, x) if dominio.contains(sympy.Float(r)) != False]  # noqa: E712
    return approssimati, " (valori approssimati, cercati tra $-12$ e $12$)" if approssimati else ""


def _segno_vicino(g: sympy.Expr, x: sympy.Symbol, punto, lato: int) -> int:
    """Segno di g appena a sinistra (lato=-1) o a destra (lato=+1) del punto: -1, 0 oppure +1."""
    for distanza in (1e-3, 1e-5):
        valore = come_numero(g.subs(x, sympy.N(punto) + lato * distanza))
        if valore is not None and abs(valore) > 1e-12:
            return 1 if valore > 0 else -1
    return 0


def _dove(condizione, x: sympy.Symbol, dominio) -> str | None:
    """Risolve una disequazione e restituisce l'insieme in LaTeX (None se SymPy non ci riesce)."""
    try:
        insieme = sympy.solveset(condizione, x, dominio)
    except Exception:
        return None
    # Insiemi che SymPy non riesce a scrivere in modo leggibile: meglio non mostrarli
    if insieme.has(sympy.ConditionSet, sympy.ImageSet):
        return None
    return r"\text{mai}" if insieme is S.EmptySet else _insieme(insieme)


def _limite_valido(valore) -> bool:
    """Un limite è utilizzabile se è un numero reale oppure più/meno infinito (non se oscilla)."""
    if valore in INFINITI:
        return True
    return not valore.has(sympy.AccumBounds, sympy.nan, sympy.zoo) and valore.is_real is not False


def _elenco(punti: list, x: sympy.Symbol) -> str:
    return ", \\quad ".join(f"{L(x)} = {L(p)}" for p in punti)


def studia(f: sympy.Expr, x: sympy.Symbol) -> dict:
    """Esegue lo studio completo. Ogni tappa è protetta: se una fallisce, le altre proseguono."""
    tappe: list[dict] = []
    notevoli: list[float] = []  # ascisse importanti, per scegliere la finestra del grafico
    parziale = False  # True se abbiamo trovato infiniti punti (funzioni periodiche) e ne mostriamo solo alcuni

    # Le funzioni periodiche hanno infinite soluzioni: SymPy risolve le disequazioni in un solo periodo
    try:
        periodo = sympy.periodicity(f, x)
    except Exception:
        periodo = None
    in_un_periodo = r" \quad \text{(in un periodo)}" if periodo else ""

    def aggiungi(titolo: str, testo: str, formule: list[str], elementi: list[dict], concetto: str | None) -> None:
        tappe.append({"titolo": titolo, "testo": testo, "formule": formule, "elementi": elementi, "concetto": concetto})

    def punto(px, py, etichetta: str, stile: str) -> dict | None:
        nx, ny = come_numero(px), come_numero(py)
        if nx is None or ny is None:
            return None
        notevoli.append(nx)
        return {"tipo": "punto", "x": nx, "y": ny, "etichetta": etichetta, "stile": stile}

    # ---------- 1. dominio ----------
    try:
        dominio = continuous_domain(f, x, S.Reals)
    except Exception:
        dominio = S.Reals
    elementi = []
    esclusi = S.Reals - dominio
    # Estremi del dominio (per alcune funzioni periodiche SymPy non li sa calcolare: allora tutta la retta)
    try:
        estremo_sinistro, estremo_destro = dominio.inf, dominio.sup
    except Exception:
        estremo_sinistro, estremo_destro = -oo, oo
    for pezzo in esclusi.args if isinstance(esclusi, Union) else [esclusi]:
        if isinstance(pezzo, Interval) and pezzo.measure != 0:
            elementi.append(
                {
                    "tipo": "fascia",
                    "da": None if pezzo.start in INFINITI else come_numero(pezzo.start),
                    "a": None if pezzo.end in INFINITI else come_numero(pezzo.end),
                    "stile": "escluso",
                }
            )
    aggiungi(
        "Dominio",
        "Cerchiamo i valori per cui la funzione ha senso: i denominatori devono essere diversi da zero, "
        "gli argomenti dei logaritmi positivi, quelli delle radici pari non negativi."
        + (" Le zone tratteggiate sul grafico sono escluse." if elementi else ""),
        [rf"D = {_insieme(dominio)}"],
        elementi,
        "dominio",
    )

    # ---------- 2. simmetrie ----------
    try:
        opposta = f.subs(x, -x)
        if sympy.simplify(opposta - f) == 0:
            testo, formula = "La funzione è pari: il grafico è simmetrico rispetto all'asse y.", rf"f(-{L(x)}) = f({L(x)})"
        elif sympy.simplify(opposta + f) == 0:
            testo, formula = "La funzione è dispari: il grafico è simmetrico rispetto all'origine.", rf"f(-{L(x)}) = -f({L(x)})"
        else:
            testo, formula = "La funzione non è né pari né dispari: nessuna simmetria particolare.", rf"f(-{L(x)}) = {L(riordina(opposta))}"
        formule = [formula]
        if periodo:
            testo += " È anche periodica: il grafico si ripete uguale a ogni periodo."
            formule.append(rf"T = {L(periodo)}")
        aggiungi("Simmetrie", testo, formule, [], "simmetrie")
    except Exception:
        pass

    # ---------- 3. intersezioni con gli assi ----------
    try:
        zeri, nota = _soluzioni(f, x, dominio)
        parziale = parziale or bool(nota)
        elementi, formule = [], []
        for zero in zeri:
            if elemento := punto(zero, 0, "", "zero"):
                elementi.append(elemento)
        formule.append(rf"f({L(x)}) = 0 \iff " + (_elenco(zeri, x) if zeri else r"\text{nessuna soluzione}"))
        testo = "Con l'asse x: risolviamo l'equazione $f(x) = 0$" + nota + "."
        if dominio.contains(0) == True:  # noqa: E712
            in_zero = f.subs(x, 0)
            formule.append(rf"f(0) = {L(in_zero)}")
            testo += " Con l'asse y: calcoliamo $f(0)$."
            if in_zero != 0 and (elemento := punto(0, in_zero, "", "zero")):
                elementi.append(elemento)
        else:
            testo += " Non c'è intersezione con l'asse y perché $0$ non appartiene al dominio."
        aggiungi("Intersezioni con gli assi", testo, formule, elementi, "intersezioni")
    except Exception:
        pass

    # ---------- 4. segno ----------
    positiva = _dove(f > 0, x, dominio)
    if positiva is not None:
        aggiungi(
            "Segno",
            "Risolviamo la disequazione $f(x) > 0$: lì il grafico sta sopra l'asse x, altrove sta sotto (o lo tocca).",
            [rf"f({L(x)}) > 0 \iff {L(x)} \in {positiva}{in_un_periodo}"],
            [],
            "segno",
        )

    # ---------- 5. limiti e asintoti ----------
    try:
        elementi, formule, frasi = [], [], []
        # Candidati asintoti verticali: i punti di bordo del dominio (o i punti esclusi)
        try:
            bordo = _punti_esatti(dominio.boundary)
        except Exception:
            bordo = None
        if bordo is None:
            try:
                # Funzioni come la tangente: cerchiamo i punti "problematici" in un intervallo limitato
                bordo = (_punti_esatti(sympy.singularities(f, x, Interval(-RAGGIO, RAGGIO)))[0], False)
            except Exception:
                bordo = None
        if bordo and not bordo[1]:
            parziale = True
        for c in bordo[0] if bordo else []:
            laterali = []
            for lato, simbolo in (("-", "^{-}"), ("+", "^{+}")):
                # Calcoliamo il limite solo dal lato in cui la funzione esiste
                vicino = sympy.N(c) + (-1e-6 if lato == "-" else 1e-6)
                if dominio.contains(vicino) == False:  # noqa: E712
                    continue
                try:
                    valore = sympy.limit(f, x, c, lato)
                except Exception:
                    continue
                if not _limite_valido(valore):
                    continue
                laterali.append(valore)
                formule.append(rf"\lim_{{{L(x)} \to {L(c)}{simbolo}}} f({L(x)}) = {L(valore)}")
            if any(v in INFINITI for v in laterali) and (nc := come_numero(c)) is not None:
                notevoli.append(nc)
                elementi.append({"tipo": "verticale", "x": nc, "etichetta": f"x = {sympy.sstr(c)}"})
                frasi.append(f"asintoto verticale ${L(x)} = {L(c)}$")

        for verso, nome in ((oo, "+\\infty"), (-oo, "-\\infty")):
            illimitato = estremo_destro == oo if verso == oo else estremo_sinistro == -oo
            if not illimitato:
                continue
            valore = sympy.limit(f, x, verso)
            if not _limite_valido(valore):
                formule.append(rf"\lim_{{{L(x)} \to {nome}}} f({L(x)}) \ \text{{non esiste}}")
                continue
            formule.append(rf"\lim_{{{L(x)} \to {nome}}} f({L(x)}) = {L(valore)}")
            if valore not in INFINITI:
                if (ny := come_numero(valore)) is not None and not any(e.get("y") == ny for e in elementi):
                    elementi.append({"tipo": "orizzontale", "y": ny, "etichetta": f"y = {sympy.sstr(valore)}"})
                    frasi.append(f"asintoto orizzontale $y = {L(valore)}$")
                continue
            # Il limite è infinito: cerchiamo un asintoto obliquo y = m x + q
            m = sympy.limit(f / x, x, verso)
            if m in INFINITI or m == 0 or m.has(sympy.AccumBounds, sympy.nan):
                continue
            q = sympy.limit(f - m * x, x, verso)
            if q in INFINITI or q.has(sympy.AccumBounds, sympy.nan):
                continue
            nm, nq = come_numero(m), come_numero(q)
            if nm is not None and nq is not None and not any(e.get("m") == nm and e.get("q") == nq for e in elementi):
                formule.append(rf"m = \lim_{{{L(x)} \to {nome}}} \frac{{f({L(x)})}}{{{L(x)}}} = {L(m)}, \qquad q = \lim_{{{L(x)} \to {nome}}} \left[f({L(x)}) - m{L(x)}\right] = {L(q)}")
                elementi.append({"tipo": "retta", "m": nm, "q": nq, "etichetta": f"y = {sympy.sstr(m * x + q)}"})
                frasi.append(f"asintoto obliquo $y = {L(m * x + q)}$")

        if formule:
            aggiungi(
                "Limiti e asintoti",
                "Calcoliamo i limiti agli estremi del dominio. "
                + ("Troviamo: " + "; ".join(frasi) + "." if frasi else "Non ci sono asintoti."),
                formule,
                elementi,
                "asintoti",
            )
    except Exception:
        pass

    # ---------- 6. derivata prima: crescenza, massimi e minimi ----------
    try:
        f1 = riordina(sympy.diff(f, x))
        stazionari, nota = _soluzioni(f1, x, dominio)
        parziale = parziale or bool(nota)
        elementi, frasi = [], []
        for c in stazionari:
            prima, dopo = _segno_vicino(f1, x, c, -1), _segno_vicino(f1, x, c, +1)
            if prima > 0 > dopo:
                tipo, nome = "massimo", "massimo relativo"
            elif prima < 0 < dopo:
                tipo, nome = "minimo", "minimo relativo"
            else:
                tipo, nome = "flesso", "flesso a tangente orizzontale"
            valore = riordina(f.subs(x, c))
            if elemento := punto(c, valore, {"massimo": "max", "minimo": "min", "flesso": "flesso"}[tipo], tipo):
                elementi.append(elemento)
                frasi.append(f"{nome} in $\\left({L(c)},\\ {L(valore)}\\right)$")
        formule = [rf"f'({L(x)}) = {L(f1)}"]
        formule.append(rf"f'({L(x)}) = 0 \iff " + (_elenco(stazionari, x) if stazionari else r"\text{nessuna soluzione}"))
        crescente = _dove(f1 > 0, x, dominio)
        if crescente is not None:
            formule.append(rf"f'({L(x)}) > 0 \iff {L(x)} \in {crescente}{in_un_periodo}")
        aggiungi(
            "Derivata prima: massimi e minimi",
            "Dove la derivata prima è positiva la funzione cresce, dove è negativa decresce. "
            "I punti in cui si annulla sono i candidati massimi e minimi" + nota + ". "
            + ("Troviamo: " + "; ".join(frasi) + "." if frasi else "Non ci sono massimi né minimi relativi."),
            formule,
            elementi,
            "monotonia",
        )
    except Exception:
        pass

    # ---------- 7. derivata seconda: concavità e flessi ----------
    try:
        f2 = riordina(sympy.diff(f, x, 2))
        candidati, nota = _soluzioni(f2, x, dominio)
        parziale = parziale or bool(nota)
        elementi, frasi = [], []
        for c in candidati:
            if _segno_vicino(f2, x, c, -1) * _segno_vicino(f2, x, c, +1) < 0:  # la concavità cambia
                valore = riordina(f.subs(x, c))
                gia_segnato = any(abs(e["x"] - (come_numero(c) or 0)) < 1e-9 for t in tappe for e in t["elementi"] if e["tipo"] == "punto" and e["stile"] == "flesso")
                if not gia_segnato and (elemento := punto(c, valore, "flesso", "flesso")):
                    elementi.append(elemento)
                frasi.append(f"flesso in $\\left({L(c)},\\ {L(valore)}\\right)$")
        formule = [rf"f''({L(x)}) = {L(f2)}"]
        convessa = _dove(f2 > 0, x, dominio)
        if convessa is not None:
            formule.append(rf"f''({L(x)}) > 0 \iff {L(x)} \in {convessa}{in_un_periodo}")
        aggiungi(
            "Derivata seconda: concavità e flessi",
            "Dove la derivata seconda è positiva il grafico è convesso (concavità verso l'alto), dove è negativa "
            "è concavo. Nei punti in cui la concavità cambia c'è un flesso" + nota + ". "
            + ("Troviamo: " + "; ".join(frasi) + "." if frasi else "Non ci sono flessi."),
            formule,
            elementi,
            "concavita",
        )
    except Exception:
        pass

    # ---------- 8. grafico ----------
    aggiungi(
        "Grafico",
        "Mettiamo insieme tutte le informazioni raccolte e tracciamo il grafico.",
        [],
        [{"tipo": "curva"}],
        None,
    )

    # Finestra consigliata: deve contenere tutti i punti importanti, con un po' di margine
    if parziale:
        # Funzione con infiniti punti notevoli: mostriamo una finestra fissa attorno all'origine
        finestra = {"xmin": -10.0, "xmax": 10.0}
    elif notevoli:
        sinistra, destra = min(notevoli), max(notevoli)
        margine = max(2.0, 0.6 * (destra - sinistra))
        finestra = {"xmin": max(-60.0, sinistra - margine), "xmax": min(60.0, destra + margine)}
    else:
        finestra = {"xmin": -8.0, "xmax": 8.0}
    # Dominio limitato a sinistra o a destra (es. logaritmo): non sprechiamo spazio fuori
    if estremo_sinistro not in INFINITI and (inizio := come_numero(estremo_sinistro)) is not None:
        finestra["xmin"] = max(finestra["xmin"], inizio - 1.0)
    if estremo_destro not in INFINITI and (fine := come_numero(estremo_destro)) is not None:
        finestra["xmax"] = min(finestra["xmax"], fine + 1.0)

    return {
        "funzione": {"latex": L(f), "js": in_js(f), "variabile": str(x)},
        "finestra": finestra,
        "tappe": tappe,
    }
