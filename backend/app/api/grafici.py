"""
Sportello "grafici": prepara le funzioni da disegnare, lo studio di funzione,
i polinomi di Taylor e le serie numeriche.
"""

import sympy
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from app.db.sessione import apri_sessione
from app.grafici.formule import come_numero, in_js, leggi_funzione_di_x, prepara_funzione
from app.grafici.studio import studia
from app.risolutore.citazioni import Biblioteca
from app.risolutore.concetti import CONCETTI
from app.risolutore.interpreta import leggi_espressione
from app.risolutore.modelli import ErroreRisolutore, L

router = APIRouter(prefix="/api/grafici", tags=["grafici"])


def _protetto(azione):
    """Esegue un'azione trasformando gli errori in messaggi chiari per lo studente."""
    try:
        return azione()
    except ErroreRisolutore as errore:
        raise HTTPException(status_code=422, detail=str(errore))
    except Exception as errore:
        raise HTTPException(status_code=422, detail=f"Non sono riuscito a elaborare questa funzione ({type(errore).__name__}).")


class RichiestaFunzione(BaseModel):
    testo: str
    variabile: str = "x"


@router.post("/funzione")
def funzione(richiesta: RichiestaFunzione) -> dict:
    """Legge una funzione e la prepara per essere disegnata (eventuali altre lettere sono parametri)."""
    return _protetto(lambda: prepara_funzione(richiesta.testo, richiesta.variabile))


@router.post("/studio")
def studio(richiesta: RichiestaFunzione, sessione: Session = Depends(apri_sessione)) -> dict:
    """Studio di funzione completo, con le citazioni dal Magazzino per ogni tappa."""

    def lavoro() -> dict:
        f, x = leggi_funzione_di_x(richiesta.testo)
        risultato = studia(f, x)
        biblioteca = Biblioteca(sessione)
        for tappa in risultato["tappe"]:
            chiave = tappa["concetto"]
            tappa["concetto"] = CONCETTI[chiave].nome if chiave else None
            tappa["citazione"] = biblioteca.cita(chiave) if chiave else None
            tappa["mancante"] = chiave is not None and tappa["citazione"] is None
        return risultato

    return _protetto(lavoro)


@router.post("/superficie")
def superficie(richiesta: RichiestaFunzione) -> dict:
    """Prepara una funzione di due variabili f(x, y) per il grafico 3D, con i suoi punti critici."""

    def lavoro() -> dict:
        import re

        from app.risolutore.analisi2 import risolvi_critici
        from app.risolutore.modelli import Problema

        testo = re.sub(r"^\s*(?:[a-zA-Z]\s*\(\s*x\s*,\s*y\s*\)|z)\s*=", "", richiesta.testo)  # toglie "f(x,y) =" o "z ="
        f = leggi_espressione(testo)
        x, y = sympy.symbols("x y")
        if f.free_symbols != {x, y}:
            raise ErroreRisolutore("Qui serve una funzione delle due variabili x e y, ad esempio x^2 - y^2.")

        # I punti critici sono un "di più": se non si riescono a trovare, il grafico si disegna lo stesso
        punti, finestra = [], {"xmin": -3.0, "xmax": 3.0, "ymin": -3.0, "ymax": 3.0}
        try:
            studio = risolvi_critici(Problema(tipo="critici", funzione=f, variabile=x, variabili=(x, y)))
            if studio.verificato and studio.grafico:
                punti, finestra = studio.grafico["punti"], studio.grafico["finestra"]
        except Exception:
            pass
        fx, fy = sympy.diff(f, x), sympy.diff(f, y)
        return {
            "latex": L(f),
            "js": in_js(f),
            "gradiente_latex": rf"\nabla f = \left({L(fx)},\ {L(fy)}\right)",
            "finestra": finestra,
            "punti": punti,
        }

    return _protetto(lavoro)


def _termine_latex(coefficiente: sympy.Expr, k: int, centro: sympy.Expr) -> str:
    """Scrive in LaTeX un termine del polinomio di Taylor: coefficiente per (x - centro)^k."""
    if k == 0:
        return L(coefficiente)
    base = "x" if centro == 0 else rf"\left({L(sympy.Symbol('x') - centro)}\right)"
    potenza = base if k == 1 else f"{base}^{{{k}}}"
    if coefficiente == 1:
        return potenza
    if coefficiente == -1:
        return f"- {potenza}"
    if coefficiente.is_Rational and coefficiente.q != 1:
        # Frazioni: mettiamo la potenza al numeratore, es. x^3/6 invece di (1/6) x^3
        segno = "- " if coefficiente < 0 else ""
        numeratore = "" if abs(coefficiente.p) == 1 else f"{abs(coefficiente.p)} "
        return rf"{segno}\frac{{{numeratore}{potenza}}}{{{coefficiente.q}}}"
    testo = L(coefficiente)
    return rf"\left({testo}\right) {potenza}" if coefficiente.is_Add else f"{testo} {potenza}"


def _somma_latex(termini: list[str]) -> str:
    """Unisce i termini con + e -, dal grado più basso al più alto."""
    if not termini:
        return "0"
    testo = termini[0]
    for termine in termini[1:]:
        testo += f" {termine}" if termine.startswith("-") else f" + {termine}"
    return testo


class RichiestaTaylor(BaseModel):
    testo: str
    centro: str = "0"
    ordine_massimo: int = 10


@router.post("/taylor")
def taylor(richiesta: RichiestaTaylor) -> dict:
    """Polinomi di Taylor della funzione, dall'ordine 0 all'ordine massimo richiesto."""

    def lavoro() -> dict:
        f, x = leggi_funzione_di_x(richiesta.testo)
        centro = leggi_espressione(richiesta.centro)
        if centro.free_symbols or come_numero(centro) is None:
            raise ErroreRisolutore("Il centro dello sviluppo deve essere un numero.")
        massimo = max(0, min(richiesta.ordine_massimo, 12))

        polinomi, polinomio, derivata, termini = [], sympy.S.Zero, f, []
        for k in range(massimo + 1):
            # Coefficiente k-esimo: derivata k-esima nel centro, divisa per k fattoriale
            valore = sympy.simplify(derivata.subs(x, centro))
            if not valore.is_finite or valore.has(sympy.nan, sympy.zoo):
                raise ErroreRisolutore(f"La funzione non è derivabile {k} volte nel punto scelto: cambia il centro.")
            coefficiente = valore / sympy.factorial(k)
            polinomio += coefficiente * (x - centro) ** k
            if coefficiente != 0:
                termini.append(_termine_latex(coefficiente, k, centro))
            polinomi.append({"ordine": k, "latex": _somma_latex(termini), "js": in_js(polinomio)})
            derivata = sympy.diff(derivata, x)
        return {
            "funzione": {"latex": L(f), "js": in_js(f), "variabile": "x"},
            "centro": come_numero(centro),
            "centro_latex": L(centro),
            "polinomi": polinomi,
        }

    return _protetto(lavoro)


class RichiestaSerie(BaseModel):
    testo: str  # il termine generale a_n, scritto in funzione di n
    inizio: int = 1


@router.post("/serie")
def serie(richiesta: RichiestaSerie) -> dict:
    """Prepara una serie numerica: termine generale, carattere (se SymPy lo sa stabilire) e somma."""

    def lavoro() -> dict:
        a, n = leggi_funzione_di_x(richiesta.testo, "n")
        inizio = max(0, richiesta.inizio)
        if come_numero(a.subs(n, inizio)) is None:
            raise ErroreRisolutore(f"Il termine della serie non è definito per n = {inizio}: cambia l'indice di partenza.")

        converge, somma = None, None
        try:
            converge = bool(sympy.Sum(a, (n, inizio, sympy.oo)).is_convergent())
        except Exception:
            pass
        if converge:
            try:
                valore = sympy.summation(a, (n, inizio, sympy.oo))
                if not valore.has(sympy.Sum) and come_numero(valore) is not None:
                    somma = valore
            except Exception:
                pass
        return {
            "termine": {"latex": L(a), "js": in_js(a), "variabile": "n"},
            "inizio": inizio,
            "serie_latex": rf"\sum_{{n={inizio}}}^{{\infty}} {L(a)}",
            "converge": converge,
            "somma_latex": L(somma) if somma is not None else None,
            "somma": come_numero(somma) if somma is not None else None,
        }

    return _protetto(lavoro)
