"""
Sportello "storico": gli esercizi risolti, il controllo delle risposte ("Mettimi alla prova")
e l'aggiunta di un esercizio risolto al Magazzino come "esercizio svolto".
"""

import json
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app import config
from app.api.magazzino import salva_documento
from app.api.progressi import registra
from app.db.modelli import Documento, Esercizio
from app.db.sessione import apri_sessione
from app.risolutore.controllo import controlla
from app.risolutore.modelli import ErroreRisolutore

router = APIRouter(prefix="/api/storico", tags=["storico"])


def salva_nello_storico(sessione: Session, testo: str, tipo_richiesto: str, soluzione: dict) -> Esercizio:
    """
    Salva (o aggiorna) un esercizio risolto. Se lo stesso esercizio era già nello Storico,
    aggiorniamo quello invece di crearne un doppione.
    """
    pubblica = {k: v for k, v in soluzione.items() if not k.startswith("_")}  # senza le risposte corrette
    dati = {
        "tipo": soluzione["problema"]["tipo"],
        "descrizione": soluzione["problema"]["descrizione"],
        "argomento": soluzione["problema"]["argomento"],
        "problema_latex": soluzione["problema"]["latex"],
        "risposta_latex": soluzione["risposta_latex"],
        "soluzione": json.dumps(pubblica, ensure_ascii=False),
        "controlli": json.dumps(soluzione.get("_controlli", {"passaggi": [], "finale": None})),
        "risolto_il": datetime.now().isoformat(timespec="seconds"),
    }
    esercizio = sessione.exec(
        select(Esercizio).where(Esercizio.testo == testo, Esercizio.tipo_richiesto == tipo_richiesto)
    ).first()
    if esercizio is None:
        esercizio = Esercizio(testo=testo, tipo_richiesto=tipo_richiesto, **dati)
    else:
        for chiave, valore in dati.items():
            setattr(esercizio, chiave, valore)
    sessione.add(esercizio)
    sessione.commit()
    sessione.refresh(esercizio)
    return esercizio


def _trova(sessione: Session, id_esercizio: int) -> Esercizio:
    esercizio = sessione.get(Esercizio, id_esercizio)
    if esercizio is None:
        raise HTTPException(status_code=404, detail="Esercizio non trovato nello Storico.")
    # Se il documento creato nel Magazzino è stato eliminato, dimentichiamo il collegamento
    if esercizio.documento_id is not None and sessione.get(Documento, esercizio.documento_id) is None:
        esercizio.documento_id = None
        sessione.add(esercizio)
        sessione.commit()
    return esercizio


def _riassunto(esercizio: Esercizio) -> dict:
    return {
        "id": esercizio.id,
        "testo": esercizio.testo,
        "tipo": esercizio.tipo,
        "tipo_richiesto": esercizio.tipo_richiesto,
        "descrizione": esercizio.descrizione,
        "argomento": esercizio.argomento,
        "problema_latex": esercizio.problema_latex,
        "risposta_latex": esercizio.risposta_latex,
        "documento_id": esercizio.documento_id,
        "risolto_il": esercizio.risolto_il,
    }


@router.get("")
def elenca(sessione: Session = Depends(apri_sessione)) -> list[dict]:
    """Tutti gli esercizi risolti, dal più recente."""
    esercizi = sessione.exec(select(Esercizio).order_by(Esercizio.risolto_il.desc(), Esercizio.id.desc()))
    return [_riassunto(e) for e in esercizi]


@router.get("/{id_esercizio}")
def leggi(id_esercizio: int, sessione: Session = Depends(apri_sessione)) -> dict:
    """Un esercizio con la sua soluzione completa (la stessa che mostra il Risolutore)."""
    esercizio = _trova(sessione, id_esercizio)
    return {
        **json.loads(esercizio.soluzione),
        **_riassunto(esercizio),  # id, testo, data... (sovrascrivono eventuali valori vecchi)
    }


@router.delete("/{id_esercizio}", status_code=204)
def elimina(id_esercizio: int, sessione: Session = Depends(apri_sessione)) -> None:
    """Toglie l'esercizio dallo Storico (l'eventuale documento nel Magazzino resta)."""
    sessione.delete(_trova(sessione, id_esercizio))
    sessione.commit()


class Risposta(BaseModel):
    passaggio: int | None = None  # indice del passaggio (da 0); None = risposta finale
    risposta: str


@router.post("/{id_esercizio}/controlla")
def controlla_risposta(id_esercizio: int, richiesta: Risposta, sessione: Session = Depends(apri_sessione)) -> dict:
    """"Mettimi alla prova": dice se la risposta dello studente è corretta, senza rivelare quella giusta."""
    esercizio = _trova(sessione, id_esercizio)
    try:
        esito = controlla(esercizio.controlli, richiesta.passaggio, richiesta.risposta)
    except ErroreRisolutore as errore:
        raise HTTPException(status_code=422, detail=str(errore))
    # Le risposte giuste contano per i traguardi
    if esito["corretto"]:
        registra(sessione, "risposta_giusta", esercizio.argomento, esercizio.id)
        if richiesta.passaggio is None:
            registra(sessione, "finale_giusto", esercizio.argomento, esercizio.id)
    return esito


def _come_testo(esercizio: Esercizio) -> str:
    """Scrive la soluzione come testo Markdown, per salvarla nel Magazzino."""
    soluzione = json.loads(esercizio.soluzione)
    parti = [f"Esercizio svolto. {esercizio.testo}", f"{esercizio.descrizione}: $${esercizio.problema_latex}$$"]
    for passaggio in soluzione.get("passaggi", []):
        riga = f"Passo {passaggio['numero']} – {passaggio['titolo']}. {passaggio['testo']}"
        if passaggio.get("formula"):
            riga += f" $${passaggio['formula']}$$"
        parti.append(riga)
    parti.append(f"Risultato: $${esercizio.risposta_latex}$$")
    return "\n\n".join(parti) + "\n"


@router.post("/{id_esercizio}/magazzino", status_code=201)
def aggiungi_al_magazzino(id_esercizio: int, sessione: Session = Depends(apri_sessione)) -> dict:
    """Salva l'esercizio risolto nel Magazzino come documento di tipo "esercizio svolto"."""
    esercizio = _trova(sessione, id_esercizio)
    if esercizio.documento_id is not None:
        raise HTTPException(status_code=409, detail="Questo esercizio è già nel Magazzino.")

    argomento = esercizio.argomento
    documento = salva_documento(
        sessione,
        nome=f"esercizio-svolto-{esercizio.id}.md",
        contenuto=_come_testo(esercizio).encode("utf-8"),
        argomento=argomento,
        corso=config.corso_di(argomento) or "Analisi I",
        fonte="Esercitazione",
        data=date.today().isoformat(),
        titolo=f"Esercizio svolto: {esercizio.testo[:80]}",
        tipo_blocchi="esercizio svolto",
    )
    esercizio.documento_id = documento["id"]
    sessione.add(esercizio)
    sessione.commit()
    return documento
