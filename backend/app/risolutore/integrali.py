"""
Risolutore degli integrali, con i passaggi.

SymPy ha un modulo ("manualintegrate") che integra come farebbe una persona e ricorda
quali regole ha usato: linearità, sostituzione, per parti, integrali immediati...
Qui percorriamo quell'elenco di regole e lo traduciamo in passaggi in italiano.
"""

import sympy
from sympy.integrals import manualintegrate as mi

from app.risolutore.modelli import ErroreRisolutore, L, Passaggio, Problema, Svolgimento, riordina

INFINITI = (sympy.oo, -sympy.oo)

# Funzioni "speciali": compaiono quando la primitiva non si può scrivere con le funzioni elementari
FUNZIONI_SPECIALI = (
    sympy.erf, sympy.erfi, sympy.Si, sympy.Ci, sympy.Ei, sympy.li, sympy.Shi, sympy.Chi,
    sympy.fresnels, sympy.fresnelc, sympy.uppergamma, sympy.lowergamma, sympy.polylog,
    sympy.elliptic_e, sympy.elliptic_f,
)  # fmt: skip


def _int(funzione: sympy.Expr, variabile: sympy.Symbol) -> str:
    """Scrive in LaTeX l'integrale indefinito di una funzione."""
    testo = L(funzione)
    if funzione.is_Add:
        testo = rf"\left({testo}\right)"
    return rf"\int {testo} \, d{L(variabile)}"


def _nome_variabile(variabile: sympy.Symbol) -> sympy.Symbol:
    """SymPy chiama "_u" la variabile di sostituzione: noi la mostriamo come "u"."""
    return sympy.Symbol(variabile.name.lstrip("_")) if variabile.name.startswith("_") else variabile


def _pulisci(espressione: sympy.Expr) -> sympy.Expr:
    """Rinomina le variabili interne di SymPy (_u) in nomi leggibili (u)."""
    return espressione.xreplace({s: _nome_variabile(s) for s in espressione.free_symbols})


def _traduci(regola: mi.Rule, passi: list[Passaggio]) -> None:
    """Aggiunge a "passi" la spiegazione della regola e, a cascata, delle regole al suo interno."""
    f, v = _pulisci(regola.integrand), _nome_variabile(regola.variable)

    if isinstance(regola, mi.AlternativeRule):
        # SymPy ha trovato più strade: prendiamo la prima che arriva fino in fondo
        scelta = next((a for a in regola.alternatives if not a.contains_dont_know()), regola.alternatives[0])
        _traduci(scelta, passi)

    elif isinstance(regola, mi.AddRule):
        passi.append(
            Passaggio(
                "Integrale di una somma",
                "L'integrale di una somma è la somma degli integrali: integriamo un addendo alla volta.",
                rf"{_int(f, v)} = " + " + ".join(_int(_pulisci(s.integrand), v) for s in regola.substeps),
                "integrale_linearita",
            )
        )
        for sotto in regola.substeps:
            _traduci(sotto, passi)

    elif isinstance(regola, mi.ConstantTimesRule):
        passi.append(
            Passaggio(
                "Costante fuori dall'integrale",
                f"La costante ${L(regola.constant)}$ si può portare fuori dal segno di integrale.",
                rf"{_int(f, v)} = {L(regola.constant)} {_int(_pulisci(regola.other), v)}",
                "integrale_linearita",
            )
        )
        _traduci(regola.substep, passi)

    elif isinstance(regola, mi.URule):
        u = _nome_variabile(regola.u_var)
        du = sympy.diff(regola.u_func, regola.variable)
        passi.append(
            Passaggio(
                "Sostituzione",
                f"Poniamo ${L(u)} = {L(_pulisci(regola.u_func))}$. Derivando: "
                f"$d{L(u)} = {L(_pulisci(du))} \\, d{L(v)}$. Riscriviamo tutto l'integrale nella nuova variabile.",
                rf"{_int(f, v)} = {_int(_pulisci(regola.substep.integrand), u)}",
                "integrale_sostituzione",
            )
        )
        _traduci(regola.substep, passi)
        passi.append(
            Passaggio(
                "Torniamo alla variabile di partenza",
                f"Sostituiamo di nuovo ${L(u)} = {L(_pulisci(regola.u_func))}$ nel risultato.",
                rf"{L(_pulisci(regola.substep.eval()))} \;\longrightarrow\; {L(_pulisci(regola.eval()))}",
                "integrale_sostituzione",
            )
        )

    elif isinstance(regola, mi.PartsRule):
        u, dv = _pulisci(regola.u), _pulisci(regola.dv)
        primitiva = _pulisci(regola.v_step.eval())
        du = sympy.diff(u, v)
        passi.append(
            Passaggio(
                "Integrazione per parti",
                f"Scegliamo il fattore da derivare $f = {L(u)}$ e quello da integrare $g' = {L(dv)}$. "
                f"Allora $f' = {L(du)}$ e $g = {L(primitiva)}$. "
                "La formula è: $\\int f g' = f g - \\int f' g$.",
                rf"{_int(f, v)} = {L(u * primitiva)} - {_int(sympy.simplify(primitiva * du), v)}",
                "integrale_parti",
                domanda=f"Il fattore da integrare è $g' = {L(dv)}$: quanto vale $g$?",
                atteso=primitiva,
                costante=v,
            )
        )
        _traduci(regola.second_step, passi)

    elif isinstance(regola, mi.CyclicPartsRule):
        for giro, parti in enumerate(regola.parts_rules, start=1):
            passi.append(
                Passaggio(
                    f"Integrazione per parti ({giro}ª volta)",
                    f"Fattore da derivare $f = {L(_pulisci(parti.u))}$, fattore da integrare "
                    f"$g' = {L(_pulisci(parti.dv))}$, quindi $g = {L(_pulisci(parti.v_step.eval()))}$.",
                    None,
                    "integrale_parti",
                )
            )
        passi.append(
            Passaggio(
                "L'integrale di partenza ricompare",
                "Dopo aver integrato per parti ritroviamo a destra lo stesso integrale da cui siamo partiti: "
                "lo portiamo a sinistra e ricaviamo il suo valore come in un'equazione.",
                rf"{_int(f, v)} = {L(_pulisci(regola.eval()))}",
                "integrale_parti",
            )
        )

    elif isinstance(regola, (mi.RewriteRule, mi.CompleteSquareRule)):
        passi.append(
            Passaggio(
                "Riscriviamo la funzione",
                "Prima di integrare conviene scrivere la funzione in una forma equivalente più comoda.",
                rf"{L(f)} = {L(_pulisci(regola.rewritten))}",
                "integrale_riscrittura",
            )
        )
        _traduci(regola.substep, passi)

    elif isinstance(regola, mi.TrigSubstitutionRule):
        passi.append(
            Passaggio(
                "Sostituzione trigonometrica",
                f"Poniamo ${L(v)} = {L(_pulisci(regola.func))}$ per eliminare la radice.",
                rf"{_int(f, v)} = {_int(_pulisci(regola.substep.integrand), _nome_variabile(regola.theta))}",
                "integrale_sostituzione",
            )
        )
        _traduci(regola.substep, passi)
        passi.append(
            Passaggio(
                "Torniamo alla variabile di partenza",
                "Riscriviamo il risultato nella variabile iniziale.",
                rf"{_int(f, v)} = {L(_pulisci(regola.eval()))}",
                "integrale_sostituzione",
            )
        )

    elif isinstance(regola, mi.ConstantRule):
        passi.append(
            Passaggio(
                "Integrale di una costante",
                "L'integrale di una costante è la costante per la variabile.",
                rf"{_int(f, v)} = {L(_pulisci(regola.eval()))}",
                "integrali_immediati",
                domanda=f"Quanto vale ${_int(f, v)}$?",
                atteso=_pulisci(regola.eval()),
                costante=v,
            )
        )

    elif regola.eval().has(*FUNZIONI_SPECIALI):
        passi.append(
            Passaggio(
                "Primitiva non elementare",
                "La primitiva di questa funzione non si può scrivere con le funzioni elementari "
                "(polinomi, esponenziali, logaritmi, funzioni trigonometriche): si indica con una funzione speciale.",
                rf"{_int(f, v)} = {L(_pulisci(regola.eval()))}",
            )
        )

    else:
        # Tutte le regole "atomiche": potenze, esponenziali, seno, coseno, 1/x, arcotangente...
        passi.append(
            Passaggio(
                "Integrale immediato",
                "È un integrale della tabella degli integrali immediati.",
                rf"{_int(f, v)} = {L(_pulisci(regola.eval()))}",
                "integrali_immediati",
                domanda=f"Quanto vale ${_int(f, v)}$?",
                atteso=_pulisci(regola.eval()),
                costante=v,
            )
        )
        if hasattr(regola, "substep") and isinstance(regola.substep, mi.Rule):
            _traduci(regola.substep, passi)


def risolvi_integrale(p: Problema) -> Svolgimento:
    f, x = p.funzione, p.variabile
    definito = p.estremo_a is not None
    passi: list[Passaggio] = []
    dettagliato = True

    # --- 1. cerchiamo una primitiva, con i passaggi se possibile ---
    regola = mi.integral_steps(f, x)
    if regola.contains_dont_know():
        primitiva = sympy.integrate(f, x)
        if primitiva.has(sympy.Integral):
            raise ErroreRisolutore(
                "Non riesco a calcolare questo integrale: la primitiva potrebbe non essere esprimibile "
                "con funzioni elementari."
            )
        dettagliato = False
        passi.append(
            Passaggio(
                "Primitiva",
                "Per questo integrale non so ancora mostrare i passaggi intermedi: "
                "qui trovi la primitiva calcolata da SymPy.",
                rf"{_int(f, x)} = {L(primitiva)} + c",
            )
        )
    else:
        _traduci(regola, passi)
        primitiva = riordina(regola.eval())
        if len(passi) > 1:
            passi.append(
                Passaggio(
                    "Mettiamo insieme",
                    "Raccogliamo i risultati dei passaggi precedenti. "
                    + ("" if definito else "Aggiungiamo la costante arbitraria $c$."),
                    rf"{_int(f, x)} = {L(primitiva)}" + ("" if definito else " + c"),
                    domanda=f"Metti insieme i pezzi: quanto vale ${_int(f, x)}$?",
                    atteso=primitiva,
                    costante=x,
                )
            )

    if not definito:
        return Svolgimento(
            risultato=primitiva,
            risultato_latex=rf"{L(primitiva)} + c",
            metodo="integrazione",
            passaggi=passi,
            dettagliato=dettagliato,
        )

    # --- 2. integrale definito: primitiva calcolata agli estremi ---
    a, b = p.estremo_a, p.estremo_b

    def valore_in(estremo: sympy.Expr) -> sympy.Expr:
        # Agli estremi infiniti (integrale improprio) si usa il limite
        return sympy.limit(primitiva, x, estremo) if estremo in INFINITI else primitiva.subs(x, estremo)

    in_b, in_a = valore_in(b), valore_in(a)
    valore = sympy.simplify(in_b - in_a)
    improprio = a in INFINITI or b in INFINITI
    passi.append(
        Passaggio(
            "Calcolo tra gli estremi",
            "Calcoliamo la primitiva nell'estremo superiore e sottraiamo il suo valore nell'estremo inferiore."
            + (" Dove l'estremo è infinito si prende il limite della primitiva." if improprio else ""),
            rf"\left[{L(primitiva)}\right]_{{{L(a)}}}^{{{L(b)}}} = {_parentesi(in_b)} - {_parentesi(in_a)} = {L(valore)}",
            "teorema_fondamentale",
            domanda=rf"Calcola $\left[{L(primitiva)}\right]_{{{L(a)}}}^{{{L(b)}}}$",
            atteso=valore,
        )
    )
    return Svolgimento(risultato=valore, metodo="integrazione", passaggi=passi, dettagliato=dettagliato)


def _parentesi(e: sympy.Expr) -> str:
    testo = L(e)
    return rf"\left({testo}\right)" if e.is_Add or e.could_extract_minus_sign() else testo
