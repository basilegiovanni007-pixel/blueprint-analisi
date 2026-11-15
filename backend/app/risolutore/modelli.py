"""
Le "forme" dei dati usati dal risolutore.

- Problema: l'esercizio dopo che è stato capito (tipo, funzione, variabile...).
- Passaggio: un singolo passo della spiegazione.
- Svolgimento: l'insieme dei passaggi con il risultato finale.
"""

from dataclasses import dataclass, field

import sympy


class ErroreRisolutore(Exception):
    """Errore con un messaggio in italiano da mostrare allo studente."""


@dataclass
class Problema:
    tipo: str  # "limite", "derivata" oppure "integrale"
    funzione: sympy.Expr
    variabile: sympy.Symbol
    # Solo per i limiti
    punto: sympy.Expr | None = None
    direzione: str = "+-"  # "+" da destra, "-" da sinistra, "+-" da entrambi i lati
    # Solo per le derivate
    ordine: int = 1
    # Solo per gli integrali definiti
    estremo_a: sympy.Expr | None = None
    estremo_b: sympy.Expr | None = None
    # ----- Analisi II (funzioni di due variabili) -----
    variabili: tuple[sympy.Symbol, ...] = ()  # es. (x, y)
    vincolo: sympy.Expr | None = None  # massimi e minimi vincolati: il vincolo è "vincolo = 0"
    vincolo_latex: str = ""  # il vincolo come l'ha scritto lo studente, es. x^2 + y^2 = 1
    # Integrale doppio: "variabile" è quella esterna (estremi numerici estremo_a, estremo_b),
    # "interna" è quella interna, i cui estremi possono dipendere dalla variabile esterna.
    interna: sympy.Symbol | None = None
    interno_a: sympy.Expr | None = None
    interno_b: sympy.Expr | None = None

    # ----- Equazioni differenziali -----
    # "funzione" contiene l'equazione portata tutta a sinistra (= 0), scritta con i simboli y, y', y''.
    # Ogni condizione iniziale è (ordine della derivata, punto, valore): y(0) = 1 diventa (0, 0, 1).
    condizioni: tuple[tuple[int, sympy.Expr, sympy.Expr], ...] = ()
    equazione_latex: str = ""  # l'equazione come l'ha scritta lo studente

    def latex(self) -> str:
        """Il problema scritto in LaTeX, per mostrarlo allo studente."""
        f, x = L(self.funzione), L(self.variabile)
        if self.tipo == "serie":
            return rf"\sum_{{{x}={L(self.estremo_a)}}}^{{\infty}} {_tra_parentesi(self.funzione)}"
        if self.tipo == "edo":
            apici = {0: "", 1: "'", 2: "''"}
            iniziali = [rf"y{apici[k]}\left({L(x0)}\right) = {L(v)}" for k, x0, v in self.condizioni]
            if not iniziali:
                return self.equazione_latex
            return r"\begin{cases} " + r" \\ ".join([self.equazione_latex, *iniziali]) + r" \end{cases}"
        if self.tipo in ("gradiente", "critici", "vincolati"):
            nome = f"f({', '.join(L(v) for v in self.variabili)})"
            if self.tipo == "gradiente":
                return rf"\nabla f, \qquad {nome} = {f}"
            if self.tipo == "critici":
                return rf"\text{{punti critici di }} {nome} = {f}"
            return rf"\text{{massimi e minimi di }} {nome} = {f} \ \text{{ con il vincolo }} \ {self.vincolo_latex}"
        if self.tipo == "doppio":
            y = L(self.interna)
            return (
                rf"\int_{{{L(self.estremo_a)}}}^{{{L(self.estremo_b)}}} \int_{{{L(self.interno_a)}}}^{{{L(self.interno_b)}}} "
                rf"{_tra_parentesi(self.funzione)} \, d{y} \, d{x}"
            )
        if self.tipo == "limite":
            verso = {"+": "^{+}", "-": "^{-}", "+-": ""}[self.direzione]
            return rf"\lim_{{{x} \to {L(self.punto)}{verso}}} {_tra_parentesi(self.funzione)}"
        if self.tipo == "derivata":
            if self.ordine == 1:
                return rf"\frac{{d}}{{d{x}}}\left[{f}\right]"
            return rf"\frac{{d^{{{self.ordine}}}}}{{d{x}^{{{self.ordine}}}}}\left[{f}\right]"
        if self.estremo_a is not None:
            return rf"\int_{{{L(self.estremo_a)}}}^{{{L(self.estremo_b)}}} {_tra_parentesi(self.funzione)} \, d{x}"
        return rf"\int {_tra_parentesi(self.funzione)} \, d{x}"


def _tra_parentesi(espressione: sympy.Expr) -> str:
    """Mette le parentesi attorno alle somme, così "lim x + 1" non è ambiguo."""
    testo = L(espressione)
    return rf"\left({testo}\right)" if espressione.is_Add else testo


@dataclass
class Passaggio:
    titolo: str
    testo: str  # spiegazione in italiano; le formule in linea stanno tra $...$
    formula: str | None = None  # formula principale del passaggio, in LaTeX
    concetto: str | None = None  # chiave del concetto usato (vedi concetti.py)
    # ----- per la modalità "Mettimi alla prova" -----
    domanda: str | None = None  # la domanda posta allo studente (formule tra $...$)
    atteso: sympy.Expr | None = None  # la risposta corretta
    costante: sympy.Symbol | None = None  # se indicata, la risposta può differire per una costante (primitive)


@dataclass
class Svolgimento:
    risultato: sympy.Expr | None  # None = "il limite non esiste"
    passaggi: list[Passaggio] = field(default_factory=list)
    metodo: str = ""
    risultato_latex: str | None = None  # se serve una scrittura particolare (es. "+ c")
    avvisi: list[str] = field(default_factory=list)
    dettagliato: bool = True  # False = non siamo riusciti a mostrare i passaggi intermedi
    # ----- usati dagli esercizi di Analisi II -----
    risposta_latex: str | None = None  # la frase finale completa, quando non è "problema = risultato"
    verificato: bool | None = None  # esito del controllo indipendente fatto dal risolutore stesso
    grafico: dict | None = None  # dati per disegnare superficie e curve di livello


def L(espressione) -> str:
    """Scorciatoia: trasforma un'espressione SymPy in LaTeX, con la notazione usata in Italia."""
    # ln invece di log, arctan invece di atan
    return sympy.latex(espressione, ln_notation=True, inv_trig_style="full")


def riordina(espressione: sympy.Expr) -> sympy.Expr:
    """Sceglie la scrittura più semplice tra alcune forme equivalenti del risultato."""
    candidati = [espressione]
    for trasforma in (sympy.factor, sympy.simplify, sympy.expand):
        try:
            candidati.append(trasforma(espressione))
        except Exception:
            pass

    # La scrittura "più semplice" è quella più corta; a parità preferiamo quelle che non iniziano col meno
    def lunghezza(e: sympy.Expr) -> int:
        testo = sympy.latex(e)
        return len(testo) + (15 if testo.startswith("-") else 0)

    return min(candidati, key=lunghezza)
