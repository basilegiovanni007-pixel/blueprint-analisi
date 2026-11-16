"""
Lettura degli esercizi da un file (PDF, Word, testo, Markdown, LaTeX).

Il file viene letto con gli stessi strumenti del Magazzino, poi il testo viene diviso
nei singoli esercizi cercando le intestazioni tipiche: "Esercizio 1", "Es. 2", "3)", "4."...
Lo studente sceglie poi quale esercizio risolvere.
"""

import re
import tempfile
from pathlib import Path

from app.magazzino.estrazione import estrai

# Inizio di un esercizio: "Esercizio 3", "Es. 3", "Problema 3", "3)", "3.", "(3)" a inizio riga
INTESTAZIONE = re.compile(
    r"^\s*(?:#+\s*)?(?:\*\*)?(?:(?:esercizio|es\.?|problema|quesito)\s*(?:n\.?\s*)?(\d+)|\(?(\d{1,2})[.)])(?!\d)",
    re.IGNORECASE | re.MULTILINE,
)

LUNGHEZZA_MASSIMA = 1200  # caratteri mostrati per ogni esercizio


def leggi_esercizi(nome_file: str, contenuto: bytes) -> tuple[list[dict], bool]:
    """
    Restituisce (esercizi, letto_con_ocr): l'elenco degli esercizi trovati nel file,
    [{numero, testo}, ...], e se il testo viene da una foto o da una scansione.
    """
    # Salviamo il file in una cartella temporanea solo per il tempo necessario a leggerlo
    with tempfile.TemporaryDirectory() as cartella:
        percorso = Path(cartella) / ("esercizi" + Path(nome_file).suffix.lower())
        percorso.write_bytes(contenuto)
        estrazione = estrai(percorso)
    paragrafi, ocr = estrazione.paragrafi, estrazione.letto_con_ocr

    testo = "\n".join(paragrafo for _, paragrafo in paragrafi)
    inizi = list(INTESTAZIONE.finditer(testo))

    # Nessuna intestazione riconosciuta: tutto il file è un unico esercizio
    if not inizi:
        return [{"numero": 1, "testo": _accorcia(testo)}], ocr

    esercizi = []
    for i, inizio in enumerate(inizi):
        fine = inizi[i + 1].start() if i + 1 < len(inizi) else len(testo)
        corpo = testo[inizio.end() : fine].strip(" .:-–\n\t*")
        if corpo:
            esercizi.append({"numero": int(inizio.group(1) or inizio.group(2)), "testo": _accorcia(corpo)})

    # Se i numeri si ripetono (es. più fogli nello stesso file) rinumeriamo da 1
    numeri = [e["numero"] for e in esercizi]
    if len(set(numeri)) != len(numeri):
        for posizione, esercizio in enumerate(esercizi, start=1):
            esercizio["numero"] = posizione
    return (esercizi or [{"numero": 1, "testo": _accorcia(testo)}]), ocr


def _accorcia(testo: str) -> str:
    testo = re.sub(r"[ \t]+", " ", testo).strip()
    return testo if len(testo) <= LUNGHEZZA_MASSIMA else testo[:LUNGHEZZA_MASSIMA].rstrip() + "…"
