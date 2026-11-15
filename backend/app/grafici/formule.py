"""
Preparazione delle funzioni per i grafici.

Il grafico viene disegnato dal browser, che deve poter calcolare f(x) migliaia di volte
al secondo (per zoom, cursori e animazioni). Per questo il backend traduce la funzione
in una scrittura che la libreria JavaScript "mathjs" sa calcolare da sola.
"""

import re

import sympy

from app.risolutore.interpreta import leggi_espressione
from app.risolutore.modelli import ErroreRisolutore, L

# Funzioni di SymPy che in mathjs hanno un altro nome
RINOMINA = {"Abs": "abs", "E": "e", "ceiling": "ceil"}

# Funzioni che mathjs non sa calcolare: meglio dirlo subito che disegnare un grafico vuoto
NON_DISEGNABILI = (sympy.Piecewise, sympy.Integral, sympy.Derivative, sympy.Limit, sympy.Sum, sympy.zoo, sympy.nan)


def in_js(espressione: sympy.Expr) -> str:
    """Traduce un'espressione SymPy nella scrittura di mathjs (es. x**2 -> x^2)."""
    if espressione.has(*NON_DISEGNABILI):
        raise ErroreRisolutore("Questa funzione non si può disegnare.")
    testo = sympy.sstr(espressione).replace("**", "^")
    return re.sub(r"\b[A-Za-z_]\w*\b", lambda m: RINOMINA.get(m.group(0), m.group(0)), testo)


def come_numero(valore) -> float | None:
    """Converte un valore SymPy in un numero decimale; None se non è un numero reale finito."""
    try:
        numero = complex(sympy.N(valore))
    except (TypeError, ValueError):
        return None
    if abs(numero.imag) > 1e-9 or numero.real != numero.real or abs(numero.real) == float("inf"):
        return None
    return round(numero.real, 10)


def prepara_funzione(testo: str, variabile: str = "x") -> dict:
    """
    Legge una funzione scritta dallo studente e la prepara per il grafico.
    Le lettere diverse dalla variabile sono considerate parametri (es. a e b in a*sin(b*x)).
    """
    testo = re.sub(r"^\s*(?:[a-zA-Z]\s*\(\s*[a-zA-Z]\s*\)|y)\s*=", "", testo)  # toglie "f(x) =" o "y ="
    espressione = leggi_espressione(testo)
    x = sympy.Symbol(variabile)
    parametri = sorted(str(s) for s in espressione.free_symbols - {x})
    if len(parametri) > 4:
        raise ErroreRisolutore("Troppe lettere nella funzione: al massimo 4 parametri oltre alla variabile.")
    return {
        "latex": L(espressione),
        "js": in_js(espressione),
        "variabile": variabile,
        "parametri": parametri,
    }


def leggi_funzione_di_x(testo: str, variabile: str = "x") -> tuple[sympy.Expr, sympy.Symbol]:
    """Come sopra, ma pretende una funzione della sola variabile (senza parametri)."""
    testo = re.sub(r"^\s*(?:[a-zA-Z]\s*\(\s*[a-zA-Z]\s*\)|y|a_n)\s*=", "", testo)
    espressione = leggi_espressione(testo)
    x = sympy.Symbol(variabile)
    altre = espressione.free_symbols - {x}
    if altre:
        nomi = ", ".join(sorted(str(s) for s in altre))
        raise ErroreRisolutore(f"Qui serve una funzione della sola variabile {variabile}: togli {nomi}.")
    return espressione, x
