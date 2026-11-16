"""
Sportello "stato": permette al frontend di controllare che il backend sia acceso
e che SymPy (il motore di calcolo) funzioni davvero.
"""

import sympy
from fastapi import APIRouter

from app.magazzino.indice import indice

# Un "router" è un gruppo di indirizzi (endpoint) che poi colleghiamo all'app principale.
router = APIRouter(prefix="/api", tags=["stato"])


@router.get("/stato")
def leggi_stato() -> dict:
    """Risponde a GET /api/stato con alcune informazioni di base."""

    # Piccola prova di calcolo vera: deriviamo x^2 * sin(x).
    # Se questa riga funziona, SymPy è installato correttamente.
    x = sympy.Symbol("x")
    funzione = x**2 * sympy.sin(x)
    derivata = sympy.diff(funzione, x)

    return {
        "stato": "ok",
        "versione_app": "1.1.0",
        "fase": 2,
        # Stato del modello di ricerca: "in caricamento", "pronto" oppure "errore"
        "ricerca": {"stato": indice.stato, "errore": indice.errore},
        "versione_sympy": sympy.__version__,
        # sympy.latex(...) trasforma un'espressione in LaTeX, che il frontend mostra con KaTeX
        "prova_calcolo": {
            "funzione": sympy.latex(funzione),
            "derivata": sympy.latex(derivata),
        },
    }
