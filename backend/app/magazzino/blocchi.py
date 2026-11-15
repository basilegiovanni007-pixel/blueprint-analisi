"""
Divisione del testo in blocchi e riconoscimento automatico del tipo di blocco.

Un "blocco" è un pezzo di testo abbastanza piccolo da parlare di una cosa sola
(una definizione, un teorema, un esempio...). Il risolutore cercherà tra i blocchi.
"""

import re
from dataclasses import dataclass

from app.magazzino.estrazione import Paragrafo

LUNGHEZZA_IDEALE = 900  # caratteri: oltre questa soglia chiudiamo il blocco
LUNGHEZZA_MASSIMA = 1500  # un singolo paragrafo più lungo viene spezzato


@dataclass
class BloccoGrezzo:
    pagina: int | None
    testo: str
    tipo: str


# Parole che, a inizio paragrafo, indicano l'inizio di un nuovo blocco e il suo tipo.
# L'ordine conta: la prima regola che corrisponde vince.
REGOLE_TIPO: list[tuple[str, str]] = [
    ("esercizio svolto", r"esercizi[oi]\s+svolt[oi]|esercizio|svolgimento|soluzione|\\begin\{(exercise|esercizio)"),
    ("teorema", r"teorema|lemma|proposizione|corollario|\\begin\{(theorem|teorema|lemma)"),
    ("definizione", r"definizione|def\.|\\begin\{(definition|definizione)"),
    ("esempio", r"esempi[oi]|\\begin\{(example|esempio)"),
    ("metodo", r"metodo|procedimento|regola|criterio|strategia|come si (calcola|risolve)"),
]

# Simboli che possono precedere la parola chiave (numeri, cancelletti del Markdown, asterischi...)
PREFISSO = r"^[\s#*_\-\d.)(]*"


def indovina_tipo(testo: str) -> str:
    """Cerca di capire se un testo è una definizione, un teorema, ecc. guardando come inizia."""
    for tipo, schema in REGOLE_TIPO:
        if re.match(PREFISSO + "(" + schema + ")", testo, flags=re.IGNORECASE):
            return tipo
    return "altro"


def _spezza_lungo(testo: str) -> list[str]:
    """Spezza un paragrafo troppo lungo alla fine delle frasi."""
    if len(testo) <= LUNGHEZZA_MASSIMA:
        return [testo]
    pezzi: list[str] = []
    corrente = ""
    for frase in re.split(r"(?<=[.;:])\s+", testo):
        if corrente and len(corrente) + len(frase) > LUNGHEZZA_IDEALE:
            pezzi.append(corrente)
            corrente = frase
        else:
            corrente = f"{corrente} {frase}".strip()
    if corrente:
        pezzi.append(corrente)
    return pezzi


def dividi_in_blocchi(paragrafi: list[Paragrafo]) -> list[BloccoGrezzo]:
    """
    Unisce i paragrafi in blocchi. Si apre un nuovo blocco quando:
    - il paragrafo inizia con una parola chiave (Definizione, Teorema, Esempio...);
    - il blocco corrente ha già raggiunto la lunghezza ideale.
    """
    blocchi: list[BloccoGrezzo] = []
    corrente: BloccoGrezzo | None = None

    for pagina, paragrafo in paragrafi:
        for pezzo in _spezza_lungo(paragrafo):
            tipo = indovina_tipo(pezzo)
            inizia_nuovo = (
                corrente is None
                or tipo != "altro"
                or len(corrente.testo) + len(pezzo) > LUNGHEZZA_IDEALE
            )
            if inizia_nuovo:
                if corrente is not None:
                    blocchi.append(corrente)
                corrente = BloccoGrezzo(pagina=pagina, testo=pezzo, tipo=tipo)
            else:
                corrente.testo += "\n\n" + pezzo

    if corrente is not None:
        blocchi.append(corrente)
    return blocchi
