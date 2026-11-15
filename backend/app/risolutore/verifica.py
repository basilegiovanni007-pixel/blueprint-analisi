"""
Confronto tra due risultati: servono a controllare che i passaggi mostrati allo
studente portino davvero allo stesso risultato calcolato da SymPy.
"""

import sympy

# Punti di prova per il confronto numerico (scelti per evitare zeri e punti "speciali")
PUNTI_DI_PROVA = [0.37, 0.83, 1.29, 2.11]


def uguali(a: sympy.Expr | None, b: sympy.Expr | None) -> bool:
    """True se le due espressioni rappresentano la stessa cosa (None = "non esiste")."""
    if a is None or b is None:
        return a is b
    if a == b:
        return True

    # 1) Confronto simbolico: la differenza si semplifica a zero?
    try:
        if sympy.simplify(a - b) == 0:
            return True
    except Exception:
        pass

    # 2) Confronto numerico: le due espressioni danno gli stessi numeri in alcuni punti?
    try:
        differenza = a - b
        simboli = sorted(differenza.free_symbols, key=str)
        if not simboli:
            return abs(complex(sympy.N(differenza))) < 1e-9
        for punto in PUNTI_DI_PROVA:
            valore = complex(sympy.N(differenza.subs({s: punto for s in simboli})))
            if abs(valore) > 1e-7:
                return False
        return True
    except Exception:
        return False
