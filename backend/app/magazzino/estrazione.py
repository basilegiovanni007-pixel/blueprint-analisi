"""
Estrazione del testo dai file caricati.

Il risultato è una lista di "paragrafi": coppie (pagina, testo).
La pagina è un numero per i PDF e None per gli altri formati.

Foto e pagine scansionate non contengono testo "vero", solo pixel: per quelle usiamo
il riconoscimento della scrittura (OCR, vedi ocr.py). Nei PDF lo usiamo solo sulle
pagine che ne hanno bisogno, così un PDF misto (pagine scritte al computer e pagine
scansionate) viene letto nel modo migliore pagina per pagina.
"""

import re
from dataclasses import dataclass
from pathlib import Path

import docx  # libreria python-docx
import pymupdf  # legge i PDF
from PIL import Image, UnidentifiedImageError

from app import config
from app.magazzino.ocr import OcrNonDisponibile, riconosci

# Un paragrafo estratto: (numero di pagina oppure None, testo)
Paragrafo = tuple[int | None, str]

# Una pagina di PDF con meno di così tanti caratteri di testo viene trattata come scansione
MINIMO_CARATTERI_PAGINA = 25
RISOLUZIONE_SCANSIONE = 200  # punti per pollice con cui "fotografiamo" una pagina scansionata
AFFIDABILITA_BASSA = 0.8  # sotto questa soglia avvisiamo lo studente che la lettura è incerta


@dataclass
class Estrazione:
    paragrafi: list[Paragrafo]
    letto_con_ocr: bool = False  # True se almeno una parte viene da foto o scansioni
    pagine_ocr: int = 0
    affidabilita: float | None = None  # sicurezza media dell'OCR (da 0 a 1), se usato
    ocr_tentato: bool = False  # True se abbiamo provato a leggere almeno un'immagine (anche senza risultato)

    @property
    def lettura_incerta(self) -> bool:
        return self.affidabilita is not None and self.affidabilita < AFFIDABILITA_BASSA


class FileIlleggibile(Exception):
    """Errore sollevato quando da un file non si riesce a ricavare testo."""


def estrai(percorso: Path) -> Estrazione:
    """Sceglie il metodo giusto in base all'estensione del file."""
    estensione = percorso.suffix.lower()
    try:
        if estensione == ".pdf":
            estrazione = _da_pdf(percorso)
        elif estensione in config.ESTENSIONI_IMMAGINE:
            estrazione = _da_immagine(percorso)
        elif estensione == ".docx":
            estrazione = Estrazione(_da_docx(percorso))
        elif estensione in {".txt", ".md", ".tex"}:
            estrazione = Estrazione(_da_testo(percorso))
        else:
            raise FileIlleggibile(f"Formato {estensione} non supportato.")
    except (FileIlleggibile, OcrNonDisponibile):
        raise
    except Exception as errore:
        # Qualsiasi altro problema (file rovinato, protetto da password...)
        raise FileIlleggibile(f"Non riesco a leggere il file: {errore}") from errore

    # Teniamo solo i paragrafi che contengono davvero qualcosa
    estrazione.paragrafi = [(pagina, testo.strip()) for pagina, testo in estrazione.paragrafi if testo.strip()]

    if not estrazione.paragrafi:
        if estrazione.ocr_tentato:
            raise FileIlleggibile(
                "Non sono riuscito a leggere il testo di questa foto o scansione. Prova con un'immagine più "
                "nitida: il foglio dritto e intero nell'inquadratura, buona luce, senza ombre."
            )
        raise FileIlleggibile("Il file è vuoto.")
    return estrazione


def estrai_paragrafi(percorso: Path) -> list[Paragrafo]:
    """Come estrai(), ma restituisce solo i paragrafi."""
    return estrai(percorso).paragrafi


def _da_immagine(percorso: Path) -> Estrazione:
    try:
        immagine = Image.open(percorso)
        immagine.load()
    except UnidentifiedImageError as errore:
        raise FileIlleggibile("Non riesco ad aprire questa immagine: il file potrebbe essere rovinato.") from errore
    letto = riconosci(immagine)
    return Estrazione(
        [(None, p) for p in letto.paragrafi],
        letto_con_ocr=True,
        pagine_ocr=1,
        affidabilita=letto.affidabilita,
        ocr_tentato=True,
    )


def _da_pdf(percorso: Path) -> Estrazione:
    paragrafi: list[Paragrafo] = []
    pagine_ocr, sicurezze, tentato = 0, [], False
    # Leggiamo il file in memoria: così Windows non lo tiene "occupato" se qualcosa va storto
    with pymupdf.open(stream=percorso.read_bytes(), filetype="pdf") as pdf:
        for numero, pagina in enumerate(pdf, start=1):
            # get_text("blocks") restituisce il testo già raggruppato in paragrafi.
            # Ogni elemento è (x0, y0, x1, y1, testo, numero_blocco, tipo); tipo 0 = testo.
            blocchi = [b for b in pagina.get_text("blocks") if b[6] == 0]
            if sum(len(b[4].strip()) for b in blocchi) >= MINIMO_CARATTERI_PAGINA:
                for blocco in blocchi:
                    # Dentro un paragrafo il PDF va a capo a ogni riga: uniamo le righe
                    paragrafi.append((numero, re.sub(r"\s*\n\s*", " ", blocco[4])))
                continue

            # Pagina senza testo: è una scansione. La "fotografiamo" e usiamo l'OCR.
            tentato = True
            foto = pagina.get_pixmap(dpi=RISOLUZIONE_SCANSIONE)
            immagine = Image.frombytes("RGB", (foto.width, foto.height), foto.samples)
            letto = riconosci(immagine)
            paragrafi.extend((numero, p) for p in letto.paragrafi)
            if letto.paragrafi:
                pagine_ocr += 1
                sicurezze.append(letto.affidabilita)
    return Estrazione(
        paragrafi,
        letto_con_ocr=pagine_ocr > 0,
        pagine_ocr=pagine_ocr,
        affidabilita=round(sum(sicurezze) / len(sicurezze), 3) if sicurezze else None,
        ocr_tentato=tentato,
    )


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
