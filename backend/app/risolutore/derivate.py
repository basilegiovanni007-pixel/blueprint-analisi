"""
Risolutore delle derivate, con i passaggi.

Una funzione è costruita come un albero: somme di prodotti di funzioni composte...
Il "derivatore" scende lungo l'albero e, a ogni nodo, applica la regola giusta
(somma, prodotto, quoziente, funzione composta, derivata elementare) annotando un passaggio.
"""

import sympy

from app.risolutore.modelli import L, Passaggio, Problema, Svolgimento, riordina


def _D(espressione: sympy.Expr) -> str:
    """Scrive in LaTeX "D[espressione]", la notazione per la derivata."""
    return rf"D\left[{L(espressione)}\right]"


class _Derivatore:
    def __init__(self, x: sympy.Symbol) -> None:
        self.x = x
        self.passi: list[Passaggio] = []
        self._formule_viste: set[str] = set()  # per non ripetere due volte lo stesso passaggio

    def _annota(self, titolo: str, testo: str, formula: str, concetto: str) -> None:
        if formula not in self._formule_viste:
            self._formule_viste.add(formula)
            passaggio = Passaggio(titolo, testo, formula, concetto)
            # Le derivate elementari diventano domande per "Mettimi alla prova".
            # (I passaggi che applicano una regola non hanno una "risposta" da scrivere.)
            if titolo in ("Derivata elementare", "Derivata"):
                passaggio.domanda = f"Quanto vale ${_D(self._corrente)}$?"
                passaggio.atteso = sympy.diff(self._corrente, self.x)
            self.passi.append(passaggio)

    def deriva(self, e: sympy.Expr) -> sympy.Expr:
        """Deriva l'espressione e annota i passaggi. Restituisce la derivata (non semplificata)."""
        x = self.x
        self._corrente = e  # l'espressione che stiamo derivando adesso (serve a _annota)

        if not e.has(x):
            return sympy.S.Zero  # la derivata di una costante è zero
        if e == x:
            return sympy.S.One

        # ----- somma -----
        if e.is_Add:
            self._annota(
                "Derivata di una somma",
                "La derivata di una somma è la somma delle derivate: deriviamo un addendo alla volta.",
                rf"{_D(e)} = " + " + ".join(_D(t) for t in e.args),
                "derivata_somma",
            )
            return sympy.Add(*[self.deriva(t) for t in e.args])

        # ----- prodotto e quoziente -----
        if e.is_Mul:
            costante, resto = e.as_independent(x)
            if costante != 1:
                self._annota(
                    "Costante moltiplicativa",
                    f"La costante ${L(costante)}$ resta fuori dalla derivata.",
                    rf"{_D(e)} = {L(costante)} \cdot {_D(resto)}",
                    "derivata_somma",
                )
                return costante * self.deriva(resto)

            n, d = e.as_numer_denom()
            if d.has(x):
                self._annota(
                    "Derivata di un quoziente",
                    f"Numeratore $N = {L(n)}$, denominatore $M = {L(d)}$. "
                    "La regola è: (derivata del numeratore per il denominatore, meno il numeratore per la "
                    "derivata del denominatore), tutto diviso il denominatore al quadrato.",
                    rf"{_D(e)} = \frac{{{_D(n)} \cdot {_tra_parentesi(d)} - {_tra_parentesi(n)} \cdot {_D(d)}}}{{{_tra_parentesi(d)}^{{2}}}}",
                    "derivata_quoziente",
                )
                dn, dd = self.deriva(n), self.deriva(d)
                return (dn * d - n * dd) / d**2

            f, g = e.args[0], sympy.Mul(*e.args[1:])
            self._annota(
                "Derivata di un prodotto",
                f"Primo fattore $f = {L(f)}$, secondo fattore $g = {L(g)}$. "
                "La regola è: derivata del primo per il secondo, più il primo per la derivata del secondo.",
                rf"{_D(e)} = {_D(f)} \cdot {_tra_parentesi(g)} + {_tra_parentesi(f)} \cdot {_D(g)}",
                "derivata_prodotto",
            )
            return self.deriva(f) * g + f * self.deriva(g)

        # ----- potenze -----
        if e.is_Pow:
            base, esponente = e.as_base_exp()

            if not esponente.has(x):  # base variabile, esponente costante: x^n oppure (...)^n
                if base == x:
                    risultato = esponente * x ** (esponente - 1)
                    self._annota(
                        "Derivata elementare",
                        "Derivata di una potenza: l'esponente scende davanti e si abbassa di uno.",
                        rf"{_D(e)} = {L(risultato)}",
                        "derivate_elementari",
                    )
                    return risultato
                esterna = esponente * base ** (esponente - 1)
                self._annota(
                    "Funzione composta",
                    f"È una potenza di una funzione: la funzione interna è ${L(base)}$. "
                    "Deriviamo la potenza (esterna) lasciando dentro la funzione interna, poi moltiplichiamo "
                    "per la derivata della funzione interna.",
                    rf"{_D(e)} = {L(esterna)} \cdot {_D(base)}",
                    "derivata_composta",
                )
                return esterna * self.deriva(base)

            if not base.has(x):  # base costante, esponente variabile: a^(...)
                if esponente == x:
                    risultato = e * sympy.log(base)
                    self._annota(
                        "Derivata elementare",
                        "Derivata di un'esponenziale.",
                        rf"{_D(e)} = {L(risultato)}",
                        "derivate_elementari",
                    )
                    return risultato
                esterna = e * sympy.log(base)
                self._annota(
                    "Funzione composta",
                    f"È un'esponenziale con esponente ${L(esponente)}$ (funzione interna). "
                    "Deriviamo l'esponenziale, poi moltiplichiamo per la derivata dell'esponente.",
                    rf"{_D(e)} = {L(esterna)} \cdot {_D(esponente)}",
                    "derivata_composta",
                )
                return esterna * self.deriva(esponente)

            # base ed esponente entrambi variabili: f^g = e^(g ln f)
            riscritta = esponente * sympy.log(base)
            self._annota(
                "Riscriviamo la potenza",
                "Base ed esponente dipendono entrambi dalla variabile: riscriviamo la potenza come esponenziale "
                "e la deriviamo come funzione composta.",
                rf"{L(e)} = e^{{{L(riscritta)}}} \quad\Rightarrow\quad {_D(e)} = {L(e)} \cdot {_D(riscritta)}",
                "derivata_composta",
            )
            return e * self.deriva(riscritta)

        # ----- funzioni: sin, cos, exp, ln... -----
        if isinstance(e, sympy.Function) and len(e.args) == 1:
            interna = e.args[0]
            esterna = e.fdiff(1)  # derivata della funzione rispetto al suo argomento
            if interna == x:
                self._annota(
                    "Derivata elementare",
                    "È una derivata della tabella delle funzioni elementari.",
                    rf"{_D(e)} = {L(esterna)}",
                    "derivate_elementari",
                )
                return esterna
            self._annota(
                "Funzione composta",
                f"La funzione interna è ${L(interna)}$. Deriviamo la funzione esterna lasciando dentro "
                "quella interna, poi moltiplichiamo per la derivata della funzione interna.",
                rf"{_D(e)} = {_tra_parentesi(esterna)} \cdot {_D(interna)}",
                "derivata_composta",
            )
            return esterna * self.deriva(interna)

        # ----- qualsiasi altra cosa: lasciamo fare a SymPy -----
        risultato = sympy.diff(e, x)
        self._annota("Derivata", "Calcoliamo direttamente questa derivata.", rf"{_D(e)} = {L(risultato)}", "derivate_elementari")
        return risultato


def _tra_parentesi(e: sympy.Expr) -> str:
    """Mette le parentesi attorno a somme e numeri negativi, per non creare scritture ambigue."""
    testo = L(e)
    return rf"\left({testo}\right)" if e.is_Add or e.could_extract_minus_sign() else testo


NOMI_ORDINE = {1: "prima", 2: "seconda", 3: "terza", 4: "quarta"}


def risolvi_derivata(p: Problema) -> Svolgimento:
    x, attuale = p.variabile, p.funzione
    passi: list[Passaggio] = []

    for ordine in range(1, p.ordine + 1):
        derivatore = _Derivatore(x)
        grezza = derivatore.deriva(attuale)
        semplificata = riordina(grezza)

        if p.ordine > 1:
            passi.append(
                Passaggio(
                    f"Derivata {NOMI_ORDINE.get(ordine, str(ordine))}",
                    "Partiamo dalla funzione di partenza." if ordine == 1 else "Ora deriviamo il risultato precedente.",
                    _D(attuale),
                )
            )
        if not derivatore.passi:  # funzione costante o uguale alla variabile
            passi.append(
                Passaggio(
                    "Derivata elementare",
                    "La derivata di una costante è zero e la derivata della variabile è uno.",
                    rf"{_D(attuale)} = {L(semplificata)}",
                    "derivate_elementari",
                )
            )
        passi.extend(derivatore.passi)
        if len(derivatore.passi) > 1 or semplificata != grezza:
            passi.append(
                Passaggio(
                    "Mettiamo insieme",
                    "Sostituiamo le derivate calcolate nei passaggi precedenti e riordiniamo.",
                    rf"{_D(attuale)} = {L(grezza)}" + (rf" = {L(semplificata)}" if semplificata != grezza else ""),
                    domanda=f"Metti insieme i pezzi: quanto vale ${_D(attuale)}$?",
                    atteso=semplificata,
                )
            )
        attuale = semplificata

    return Svolgimento(risultato=attuale, metodo="regole di derivazione", passaggi=passi)
