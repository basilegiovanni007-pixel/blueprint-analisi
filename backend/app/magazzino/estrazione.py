"""
Estrazione del testo dai file caricati.

Ogni funzione restituisce una lista di "paragrafi": coppie (pagina, testo).
La pagina è un numero per i PDF e None per gli altri formati.
"""

import re
from pathlib import Path

import docx  # libreria python-docx
import pymupdf  # legge i PDF

# Un paragrafo estratto: (numero di pagina oppure None, testo)
Paragrafo = tuple[int | None, str]


class FileIlleggibile(Exception):
    """Errore sollevato quando da un file non si riesce a ricavare testo."""


def estrai_paragrafi(percorso: Path) -> list[Paragrafo]:
    """Sceglie il metodo giusto in base all'estensione del file."""
    estensione = percorso.suffix.lower()
    try:
        if estensione == ".pdf":
            paragrafi = _da_pdf(percorso)
        elif estensione == ".docx":
            paragrafi = _da_docx(percorso)
        elif estensione in {".txt", ".md", ".tex"}:
            paragrafi = _da_testo(percorso)
        else:
            raise FileIlleggibile(f"Formato {estensione} non supportato.")
    except FileIlleggibile:
        raise
    except Exception as errore:
        # Qualsiasi altro problema (file rovinato, protetto da password...)
        raise FileIlleggibile(f"Non riesco a leggere il file: {errore}") from errore

    # Teniamo solo i paragrafi che contengono davvero qualcosa
    paragrafi = [(pagina, testo.strip()) for pagina, testo in paragrafi if testo.strip()]

    if not paragrafi:
        if estensione == ".pdf":
            raise FileIlleggibile(
                "In questo PDF non ho trovato testo: probabilmente è una scansione o una foto. "
                "Il riconoscimento della scrittura (OCR) non è ancora disponibile."
            )
        raise FileIlleggibile("Il file è vuoto.")
    return paragrafi


def _da_pdf(percorso: Path) -> list[Paragrafo]:
    paragrafi: list[Paragrafo] = []
    # Leggiamo il file in memoria: così Windows non lo tiene "occupato" se qualcosa va storto
    with pymupdf.open(stream=percorso.read_bytes(), filetype="pdf") as pdf:
        for numero, pagina in enumerate(pdf, start=1):
            # get_text("blocks") restituisce il testo già raggruppato in paragrafi.
            # Ogni elemento è (x0, y0, x1, y1, testo, numero_blocco, tipo); tipo 0 = testo.
            for blocco in pagina.get_text("blocks"):
                if blocco[6] == 0:
                    # Dentro un paragrafo il PDF va a capo a ogni riga: uniamo le righe
                    testo = re.sub(r"\s*\n\s*", " ", blocco[4])
                    paragrafi.append((numero, testo))
    return paragrafi


def _da_docx(percorso: Path) -> list[Paragrafo]:
    documento = docx.Document(str(percorso))
    return [(None, paragrafo.text) for paragrafo in documento.paragraphs]


def _da_testo(percorso: Path) -> list[Paragrafo]:
    dati = percorso.read_bytes()
    # Proviamo la codifica moderna (UTF-8); se fallisce usiamo quella vecchia di Windows
    try:
        testo = dati.decode("utf-8")
    except UnicodeDecodeError:
        testo = dati.decode("cp1252", errors="replace")
    # I paragrafi sono separati da una o più righe vuote
    return [(None, pezzo) for pezzo in re.split(r"\n\s*\n", testo)]
