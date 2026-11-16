"""
Sportello "risolutore": risolve un esercizio scritto dallo studente e legge gli
esercizi contenuti in un file.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlmodel import Session

from app import config
from app.api.progressi import registra
from app.api.storico import salva_nello_storico
from app.db.sessione import apri_sessione
from app.magazzino.estrazione import FileIlleggibile
from app.magazzino.ocr import OcrNonDisponibile
from app.risolutore.citazioni import Biblioteca
from app.risolutore.da_file import leggi_esercizi
from app.risolutore.interpreta import interpreta
from app.risolutore.modelli import ErroreRisolutore
from app.risolutore.risolvi import risolvi

router = APIRouter(prefix="/api/risolutore", tags=["risolutore"])


class Richiesta(BaseModel):
    testo: str  # l'esercizio: una frase, LaTeX o solo la formula
    tipo: str = "auto"  # "auto", "limite", "derivata" oppure "integrale"


@router.post("/risolvi")
def risolvi_esercizio(richiesta: Richiesta, sessione: Session = Depends(apri_sessione)) -> dict:
    """Capisce l'esercizio, lo risolve con SymPy e collega ogni passaggio al Magazzino."""
    try:
        problema = interpreta(richiesta.testo, richiesta.tipo)
        soluzione = risolvi(problema, Biblioteca(sessione))
    except ErroreRisolutore as errore:
        # 422 = "ho ricevuto la richiesta ma il contenuto non va bene"
        raise HTTPException(status_code=422, detail=str(errore))

    # Ogni esercizio risolto finisce nello Storico
    esercizio = salva_nello_storico(sessione, richiesta.testo.strip(), richiesta.tipo, soluzione)
    registra(sessione, "risolto", esercizio.argomento, esercizio.id)  # per serie di giorni e traguardi
    # Le chiavi che iniziano con "_" (le risposte corrette) non vengono inviate al browser
    pubblica = {chiave: valore for chiave, valore in soluzione.items() if not chiave.startswith("_")}
    return {**pubblica, "id": esercizio.id, "documento_id": esercizio.documento_id, "risolto_il": esercizio.risolto_il}


@router.post("/da-file")
def esercizi_da_file(file: UploadFile = File(...)) -> dict:
    """Legge un file e restituisce l'elenco degli esercizi che contiene."""
    nome = Path(file.filename or "esercizi").name
    estensione = Path(nome).suffix.lower()

    if estensione not in config.ESTENSIONI_ACCETTATE:
        accettate = ", ".join(sorted(config.ESTENSIONI_ACCETTATE))
        raise HTTPException(status_code=415, detail=f"Formato {estensione or 'sconosciuto'} non supportato. Formati accettati: {accettate}.")

    contenuto = file.file.read()
    if not contenuto:
        raise HTTPException(status_code=422, detail="Il file è vuoto.")
    if len(contenuto) > config.DIMENSIONE_MASSIMA:
        raise HTTPException(status_code=413, detail="Il file supera i 50 MB.")

    try:
        esercizi, letto_con_ocr = leggi_esercizi(nome, contenuto)
    except FileIlleggibile as errore:
        raise HTTPException(status_code=422, detail=str(errore))
    except OcrNonDisponibile as errore:
        raise HTTPException(status_code=503, detail=str(errore))
    # letto_con_ocr: il testo viene da una foto, quindi le formule vanno ricontrollate prima di risolvere
    return {"nome_file": nome, "esercizi": esercizi, "letto_con_ocr": letto_con_ocr}
