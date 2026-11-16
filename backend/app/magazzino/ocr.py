"""
Riconoscimento del testo nelle immagini (OCR): foto di appunti scritti a mano,
pagine scansionate, screenshot.

Usiamo RapidOCR: gratuito, funziona senza internet e gira sulla stessa libreria
(onnxruntime) che Blueprint usa già per la ricerca. I modelli (circa 20 MB) sono
inclusi nel programma.

Come funziona, in breve:
1. un primo modello trova dove sono le righe di testo nell'immagine;
2. un secondo modello legge ogni riga;
3. noi rimettiamo insieme le righe in paragrafi, guardando quanto sono distanti.

Limiti da conoscere: la scrittura a mano ordinata viene letta bene, quella in corsivo
molto legato peggio; le formule (frazioni, esponenti, integrali) spesso vengono lette
male. Per questo l'app chiede allo studente di controllare il testo riconosciuto.
"""

import logging
import statistics
import threading
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageOps

# Le foto degli iPhone sono in formato HEIC: questa libreria (se c'è) insegna a Pillow a leggerle
try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
except ImportError:  # pragma: no cover - senza la libreria le foto HEIC vengono rifiutate
    pass

LATO_MASSIMO = 2600  # le foto molto grandi vengono rimpicciolite: si legge meglio e più in fretta
LATO_MINIMO = 1100  # quelle molto piccole vengono ingrandite
SOGLIA_RIGA = 0.5  # sotto questa sicurezza (da 0 a 1) una riga viene scartata: quasi sempre è rumore


@dataclass
class TestoRiconosciuto:
    paragrafi: list[str]
    affidabilita: float  # media della sicurezza delle righe lette, da 0 a 1


class OcrNonDisponibile(Exception):
    """La libreria di OCR non è installata (succede solo in installazioni incomplete)."""


_motore = None
_lucchetto = threading.Lock()


def _prepara_motore():
    """Carica i modelli una volta sola (la prima lettura impiega un secondo in più)."""
    global _motore
    with _lucchetto:
        if _motore is None:
            try:
                from rapidocr import LangRec, ModelType, OCRVersion, RapidOCR
            except ImportError as errore:
                raise OcrNonDisponibile("Il riconoscimento del testo nelle foto non è installato.") from errore
            # RapidOCR scrive molti messaggi tecnici: mostriamo solo gli avvisi importanti
            logging.getLogger("RapidOCR").setLevel(logging.WARNING)
            # Per leggere usiamo il modello delle lingue con alfabeto latino: nelle prove su scritture
            # "a mano" riconosce molte più parole del modello predefinito (cinese/inglese), legge
            # bene gli accenti italiani (è, più, così) e separa correttamente le parole.
            _motore = RapidOCR(
                params={
                    "Rec.lang_type": LangRec.LATIN,
                    "Rec.ocr_version": OCRVersion.PPOCRV5,
                    "Rec.model_type": ModelType.MOBILE,
                    # Il controllo dell'orientamento delle singole righe è spento: sugli appunti
                    # scritti a mano scambiava per capovolte righe dritte e le rovinava
                    # (provato su una vera lezione scritta con la tavoletta). La foto intera
                    # viene comunque raddrizzata grazie alle informazioni salvate dal telefono.
                    "Global.use_cls": False,
                }
            )
    return _motore


def prepara_immagine(immagine: Image.Image) -> Image.Image:
    """Raddrizza la foto (orientamento salvato dal telefono) e la porta a una dimensione comoda."""
    immagine = ImageOps.exif_transpose(immagine).convert("RGB")
    lato = max(immagine.size)
    if lato > LATO_MASSIMO:
        scala = LATO_MASSIMO / lato
    elif lato < LATO_MINIMO:
        scala = LATO_MINIMO / lato
    else:
        return immagine
    return immagine.resize((round(immagine.width * scala), round(immagine.height * scala)), Image.LANCZOS)


# Piccole correzioni di errori tipici dell'OCR:
# - lettere con accento acuto che in italiano non esistono ("límite" invece di "limite");
# - la "x" scritta a mano letta come segno di moltiplicazione "×".
CORREZIONI = str.maketrans({"í": "i", "ú": "u", "á": "a", "Í": "I", "Ú": "U", "Á": "A", "×": "x"})


def _righe_visive(pezzi: list[tuple[float, float, float, str]]) -> list[tuple[float, float, str]]:
    """
    L'OCR a volte divide una stessa riga del foglio in più pezzi (es. il testo e una formula).
    Rimettiamo insieme i pezzi alla stessa altezza, da sinistra a destra.
    Ogni pezzo è (x a sinistra, y in alto, altezza, testo); il risultato (y, altezza, testo).
    """
    pezzi = sorted(pezzi, key=lambda p: p[1] + p[2] / 2)
    gruppi: list[list[tuple[float, float, float, str]]] = []
    for pezzo in pezzi:
        centro = pezzo[1] + pezzo[2] / 2
        if gruppi:
            ultimo = gruppi[-1]
            centro_riga = statistics.fmean(p[1] + p[2] / 2 for p in ultimo)
            if abs(centro - centro_riga) < 0.5 * min(pezzo[2], min(p[2] for p in ultimo)):
                ultimo.append(pezzo)
                continue
        gruppi.append([pezzo])
    righe = []
    for gruppo in gruppi:
        gruppo.sort(key=lambda p: p[0])
        alto = min(p[1] for p in gruppo)
        righe.append((alto, max(p[1] + p[2] for p in gruppo) - alto, " ".join(p[3] for p in gruppo)))
    return righe


def raggruppa_in_paragrafi(pezzi: list[tuple[float, float, float, str]]) -> list[str]:
    """
    Unisce le righe lette in paragrafi. Ogni pezzo è (x a sinistra, y in alto, altezza, testo).

    Guardiamo il "passo" tra una riga e la successiva (distanza tra i loro inizi): dentro un
    paragrafo è regolare, mentre una riga lasciata vuota lo rende molto più grande.
    (I riquadri trovati dall'OCR sono più alti della scritta e si sovrappongono tra righe
    vicine: per questo non conviene misurare lo spazio vuoto tra un riquadro e l'altro.)
    """
    righe = _righe_visive(pezzi)
    if not righe:
        return []
    passi = [b[0] - a[0] for a, b in zip(righe, righe[1:])]
    # Il passo normale è quello tipico del foglio. Con poche righe la mediana non è affidabile:
    # usiamo il passo più piccolo, senza superare l'altezza di una riga.
    if len(passi) >= 3:
        passo_normale = statistics.median(passi)
    elif passi:
        passo_normale = min(min(passi), statistics.median(r[1] for r in righe))
    else:
        passo_normale = 0
    paragrafi: list[list[str]] = [[righe[0][2]]]
    for passo, riga in zip(passi, righe[1:]):
        if passo > 1.5 * passo_normale:
            paragrafi.append([])
        paragrafi[-1].append(riga[2])
    # Le righe restano su righe separate: così si vede la struttura degli appunti
    # e le intestazioni come "Esercizio 2" restano a inizio riga
    return ["\n".join(p).translate(CORREZIONI) for p in paragrafi]


def riconosci(immagine: Image.Image) -> TestoRiconosciuto:
    """Legge il testo di un'immagine e lo restituisce diviso in paragrafi."""
    motore = _prepara_motore()
    risultato = motore(np.array(prepara_immagine(immagine)))
    righe, sicurezze = [], []
    for riquadro, testo, sicurezza in zip(risultato.boxes if risultato.boxes is not None else [], risultato.txts or [], risultato.scores or []):
        if sicurezza < SOGLIA_RIGA or not testo.strip():
            continue
        # Righe senza nemmeno una lettera (es. "2.5", "-1 -0.5 0" sugli assi di un grafico)
        # non portano informazioni utili e sporcherebbero il testo
        if not any(c.isalpha() for c in testo):
            continue
        # Il riquadro è dato dai suoi quattro angoli: ricaviamo il bordo sinistro, quello alto e l'altezza
        xs, ys = [punto[0] for punto in riquadro], [punto[1] for punto in riquadro]
        righe.append((min(xs), min(ys), max(ys) - min(ys), testo.strip()))
        sicurezze.append(float(sicurezza))
    return TestoRiconosciuto(
        paragrafi=raggruppa_in_paragrafi(righe),
        affidabilita=round(statistics.fmean(sicurezze), 3) if sicurezze else 0.0,
    )
