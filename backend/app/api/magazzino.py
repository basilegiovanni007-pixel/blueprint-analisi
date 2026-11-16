"""
Sportello "magazzino": caricare, vedere, modificare, cercare ed eliminare i documenti.

Ogni funzione decorata con @router.get / .post / .patch / .delete è un indirizzo
che il frontend può chiamare.
"""

import re
import unicodedata
import uuid
from datetime import date
from pathlib import Path

import pymupdf
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from sqlmodel import Session, select

from app import config
from app.db.modelli import Blocco, Documento
from app.db.sessione import apri_sessione
from app.magazzino.blocchi import dividi_in_blocchi
from app.magazzino.estrazione import FileIlleggibile, estrai
from app.magazzino.ocr import OcrNonDisponibile
from app.magazzino.indice import indice

router = APIRouter(prefix="/api/magazzino", tags=["magazzino"])


# ---------- funzioni di supporto ----------


def _errore(codice: int, messaggio: str) -> HTTPException:
    """Crea un errore con un messaggio in italiano che il frontend mostra all'utente."""
    return HTTPException(status_code=codice, detail=messaggio)


def _controlla_etichette(argomento: str, fonte: str, data: str) -> str:
    """Verifica le etichette e restituisce il corso a cui appartiene l'argomento."""
    corso = config.corso_di(argomento)
    if corso is None:
        raise _errore(422, f"Argomento non valido: {argomento}")
    if fonte not in config.FONTI:
        raise _errore(422, f"Fonte non valida: {fonte}")
    try:
        date.fromisoformat(data)
    except ValueError:
        raise _errore(422, "Data non valida: usa il formato AAAA-MM-GG.")
    return corso


def _trova_documento(sessione: Session, id_documento: int) -> Documento:
    documento = sessione.get(Documento, id_documento)
    if documento is None:
        raise _errore(404, "Documento non trovato.")
    return documento


def _blocchi_di(sessione: Session, id_documento: int) -> list[Blocco]:
    return list(
        sessione.exec(
            select(Blocco).where(Blocco.documento_id == id_documento).order_by(Blocco.ordine)
        )
    )


def _riassunto(sessione: Session, documento: Documento) -> dict:
    """I dati di un documento come li vuole il frontend, con il conteggio dei blocchi per tipo."""
    conteggio: dict[str, int] = {}
    blocchi = _blocchi_di(sessione, documento.id)
    for blocco in blocchi:
        conteggio[blocco.tipo] = conteggio.get(blocco.tipo, 0) + 1
    return {
        "id": documento.id,
        "titolo": documento.titolo,
        "nome_file": documento.nome_file,
        "argomento": documento.argomento,
        "corso": documento.corso,
        "fonte": documento.fonte,
        "data": documento.data,
        "attivo": documento.attivo,
        "letto_con_ocr": bool(documento.letto_con_ocr),
        "caricato_il": documento.caricato_il,
        "numero_blocchi": len(blocchi),
        "blocchi_per_tipo": conteggio,
    }


def _blocco_come_dati(blocco: Blocco) -> dict:
    return {
        "id": blocco.id,
        "ordine": blocco.ordine,
        "pagina": blocco.pagina,
        "testo": blocco.testo,
        "tipo": blocco.tipo,
    }


# ---------- elenchi fissi ----------


@router.get("/opzioni")
def leggi_opzioni() -> dict:
    """Gli elenchi tra cui scegliere quando si etichetta un documento."""
    return {
        "argomenti": config.ARGOMENTI,
        "fonti": config.FONTI,
        "tipi_blocco": config.TIPI_BLOCCO,
        "estensioni": sorted(config.ESTENSIONI_ACCETTATE),
    }


# ---------- documenti ----------


@router.post("/documenti", status_code=201)
def carica_documento(
    file: UploadFile = File(...),
    argomento: str = Form(...),
    fonte: str = Form(...),
    data: str = Form(...),
    titolo: str = Form(""),
    sessione: Session = Depends(apri_sessione),
) -> dict:
    """Riceve un file, ne estrae il testo, lo divide in blocchi e lo indicizza."""
    corso = _controlla_etichette(argomento, fonte, data)

    # 1. Controlli sul file
    nome = Path(file.filename or "documento").name
    estensione = Path(nome).suffix.lower()
    if estensione not in config.ESTENSIONI_ACCETTATE:
        accettate = ", ".join(sorted(config.ESTENSIONI_ACCETTATE))
        raise _errore(415, f"Formato {estensione or 'sconosciuto'} non supportato. Formati accettati: {accettate}.")

    contenuto = file.file.read()
    if len(contenuto) == 0:
        raise _errore(422, "Il file è vuoto.")
    if len(contenuto) > config.DIMENSIONE_MASSIMA:
        raise _errore(413, "Il file supera i 50 MB.")

    return salva_documento(sessione, nome, contenuto, argomento, corso, fonte, data, titolo)


def salva_documento(
    sessione: Session,
    nome: str,
    contenuto: bytes,
    argomento: str,
    corso: str,
    fonte: str,
    data: str,
    titolo: str = "",
    tipo_blocchi: str | None = None,
) -> dict:
    """
    Salva un documento nel Magazzino: file, testo diviso in blocchi, indice di ricerca.
    Usata sia dal caricamento dei file sia dallo Storico ("aggiungi al Magazzino").
    tipo_blocchi: se indicato, tutti i blocchi ricevono questo tipo (es. "esercizio svolto").
    """
    estensione = Path(nome).suffix.lower()

    # 2. Salviamo il file con un nome unico, così due file omonimi non si sovrascrivono
    file_salvato = f"{uuid.uuid4().hex}{estensione}"
    percorso = config.CARTELLA_FILE / file_salvato
    percorso.write_bytes(contenuto)

    # 3. Estrazione del testo (con l'OCR per foto e scansioni) e divisione in blocchi
    try:
        estrazione = estrai(percorso)
        blocchi_grezzi = dividi_in_blocchi(estrazione.paragrafi)
    except FileIlleggibile as errore:
        percorso.unlink(missing_ok=True)
        raise _errore(422, str(errore))
    except OcrNonDisponibile as errore:
        percorso.unlink(missing_ok=True)
        raise _errore(503, f"{errore} Reinstalla Blueprint oppure carica un PDF con testo, Word, .txt, .md o .tex.")

    # 4. Salvataggio nel database
    documento = Documento(
        titolo=titolo.strip() or Path(nome).stem,
        nome_file=nome,
        file_salvato=file_salvato,
        argomento=argomento,
        corso=corso,
        fonte=fonte,
        data=data,
        letto_con_ocr=estrazione.letto_con_ocr,
    )
    sessione.add(documento)
    sessione.commit()
    sessione.refresh(documento)

    blocchi = [
        Blocco(documento_id=documento.id, ordine=i, pagina=b.pagina, testo=b.testo, tipo=tipo_blocchi or b.tipo)
        for i, b in enumerate(blocchi_grezzi)
    ]
    sessione.add_all(blocchi)
    sessione.commit()
    for blocco in blocchi:
        sessione.refresh(blocco)

    # 5. Indicizzazione per la ricerca. Se fallisce annulliamo tutto, per non lasciare
    #    nel Magazzino un documento che il risolutore non potrebbe trovare.
    try:
        indice.aggiungi([(b.id, documento.id, b.testo) for b in blocchi])
    except Exception as errore:
        for blocco in blocchi:
            sessione.delete(blocco)
        sessione.delete(documento)
        sessione.commit()
        percorso.unlink(missing_ok=True)
        raise _errore(
            503,
            "Non riesco a preparare la ricerca. La prima volta serve internet per scaricare "
            f"il modello linguistico (circa 220 MB). Dettaglio: {errore}",
        )

    riassunto = _riassunto(sessione, documento)
    # Solo subito dopo il caricamento: com'è andata la lettura di foto e scansioni
    if estrazione.letto_con_ocr:
        riassunto["ocr"] = {
            "pagine": estrazione.pagine_ocr,
            "affidabilita": estrazione.affidabilita,
            "incerta": estrazione.lettura_incerta,
        }
    return riassunto


@router.get("/documenti")
def elenca_documenti(sessione: Session = Depends(apri_sessione)) -> list[dict]:
    """Tutti i documenti, dal più recente."""
    documenti = sessione.exec(select(Documento).order_by(Documento.caricato_il.desc()))
    return [_riassunto(sessione, documento) for documento in documenti]


@router.get("/documenti/{id_documento}")
def leggi_documento(id_documento: int, sessione: Session = Depends(apri_sessione)) -> dict:
    """Un documento con tutti i suoi blocchi."""
    documento = _trova_documento(sessione, id_documento)
    dati = _riassunto(sessione, documento)
    dati["blocchi"] = [_blocco_come_dati(b) for b in _blocchi_di(sessione, id_documento)]
    return dati


class ModificaDocumento(BaseModel):
    """Campi modificabili di un documento. Quelli non inviati restano come sono."""

    titolo: str | None = None
    argomento: str | None = None
    fonte: str | None = None
    data: str | None = None
    attivo: bool | None = None


@router.patch("/documenti/{id_documento}")
def modifica_documento(
    id_documento: int,
    modifica: ModificaDocumento,
    sessione: Session = Depends(apri_sessione),
) -> dict:
    documento = _trova_documento(sessione, id_documento)

    if modifica.titolo is not None:
        if not modifica.titolo.strip():
            raise _errore(422, "Il titolo non può essere vuoto.")
        documento.titolo = modifica.titolo.strip()
    if modifica.attivo is not None:
        documento.attivo = modifica.attivo

    argomento = modifica.argomento or documento.argomento
    fonte = modifica.fonte or documento.fonte
    data = modifica.data or documento.data
    documento.corso = _controlla_etichette(argomento, fonte, data)
    documento.argomento, documento.fonte, documento.data = argomento, fonte, data

    sessione.add(documento)
    sessione.commit()
    sessione.refresh(documento)
    return _riassunto(sessione, documento)


@router.delete("/documenti/{id_documento}", status_code=204)
def elimina_documento(id_documento: int, sessione: Session = Depends(apri_sessione)) -> None:
    """Elimina il documento, i suoi blocchi, le voci dell'indice e il file originale."""
    documento = _trova_documento(sessione, id_documento)
    blocchi = _blocchi_di(sessione, id_documento)

    indice.rimuovi([b.id for b in blocchi])
    for blocco in blocchi:
        sessione.delete(blocco)
    sessione.delete(documento)
    sessione.commit()
    (config.CARTELLA_FILE / documento.file_salvato).unlink(missing_ok=True)


@router.get("/documenti/{id_documento}/file")
def apri_file(id_documento: int, sessione: Session = Depends(apri_sessione)) -> FileResponse:
    """Restituisce il file originale, per aprirlo nel browser."""
    documento = _trova_documento(sessione, id_documento)
    percorso = config.CARTELLA_FILE / documento.file_salvato
    if not percorso.exists():
        raise _errore(404, "Il file originale non è più disponibile.")
    # "inline" = il browser prova a mostrarlo invece di scaricarlo
    return FileResponse(percorso, filename=documento.nome_file, content_disposition_type="inline")


@router.get("/documenti/{id_documento}/pagina/{numero}")
def immagine_pagina(id_documento: int, numero: int, sessione: Session = Depends(apri_sessione)) -> Response:
    """
    Una pagina di un PDF come immagine. Serve per correggere il testo riconosciuto
    con l'OCR guardando la pagina originale accanto.
    """
    documento = _trova_documento(sessione, id_documento)
    percorso = config.CARTELLA_FILE / documento.file_salvato
    if percorso.suffix.lower() != ".pdf" or not percorso.exists():
        raise _errore(404, "Per questo documento non ci sono pagine da mostrare.")
    with pymupdf.open(stream=percorso.read_bytes(), filetype="pdf") as pdf:
        if not 1 <= numero <= pdf.page_count:
            raise _errore(404, f"Il documento ha {pdf.page_count} pagine.")
        immagine = pdf[numero - 1].get_pixmap(dpi=110).tobytes("png")
    # Le pagine non cambiano: il browser può tenerle in memoria per un po'
    return Response(immagine, media_type="image/png", headers={"Cache-Control": "max-age=3600"})


# ---------- blocchi ----------


class ModificaBlocco(BaseModel):
    tipo: str | None = None
    testo: str | None = None


@router.patch("/blocchi/{id_blocco}")
def modifica_blocco(
    id_blocco: int,
    modifica: ModificaBlocco,
    sessione: Session = Depends(apri_sessione),
) -> dict:
    """Cambia il tipo di un blocco (es. da "altro" a "teorema") o ne corregge il testo."""
    blocco = sessione.get(Blocco, id_blocco)
    if blocco is None:
        raise _errore(404, "Blocco non trovato.")

    if modifica.tipo is not None:
        if modifica.tipo not in config.TIPI_BLOCCO:
            raise _errore(422, f"Tipo non valido: {modifica.tipo}")
        blocco.tipo = modifica.tipo

    if modifica.testo is not None:
        if not modifica.testo.strip():
            raise _errore(422, "Il testo non può essere vuoto.")
        blocco.testo = modifica.testo.strip()
        # Il testo è cambiato: va ricalcolato anche il suo embedding nell'indice
        indice.aggiungi([(blocco.id, blocco.documento_id, blocco.testo)])

    sessione.add(blocco)
    sessione.commit()
    sessione.refresh(blocco)
    return _blocco_come_dati(blocco)


# ---------- ricerca ----------


PESO_PAROLE = 0.4  # quanto vale, al massimo, contenere tutte le parole cercate

# Parole troppo comuni per dire qualcosa sul contenuto di un blocco
PAROLE_VUOTE = {
    "della", "delle", "dello", "degli", "nella", "nelle", "come", "quando", "dove", "sono", "essere",
    "questo", "questa", "quale", "quali", "anche", "sulla", "sulle", "dalla", "dalle", "perche", "cosa",
}  # fmt: skip


def _senza_accenti(testo: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", testo) if unicodedata.category(c) != "Mn")


def _radici_parole(domanda: str) -> list[str]:
    """
    Le parole importanti della domanda, accorciate alla "radice" (es. "convessa" -> "conves"),
    così "funzione convessa" trova anche "funzioni convesse".
    """
    parole = re.findall(r"[a-z]{4,}", _senza_accenti(domanda.lower()))
    return list(dict.fromkeys(p[: max(5, len(p) - 2)] for p in parole if p not in PAROLE_VUOTE))


@router.get("/cerca")
def cerca(q: str, quanti: int = 8, sessione: Session = Depends(apri_sessione)) -> list[dict]:
    """
    Cerca tra i blocchi dei documenti attivi. La ricerca è "ibrida":
    - per significato (embedding), che trova anche sinonimi e frasi diverse;
    - più un bonus ai blocchi che contengono proprio le parole cercate.
    Il bonus conta molto negli appunti scritti a mano: lì le formule lette male "sporcano"
    il significato del blocco, mentre le parole giuste (es. "arccos") restano riconoscibili.
    """
    if not q.strip():
        raise _errore(422, "Scrivi qualcosa da cercare.")
    quanti = max(1, min(quanti, 30))

    attivi = {d.id: d for d in sessione.exec(select(Documento).where(Documento.attivo == True))}  # noqa: E712
    try:
        # Prendiamo più candidati del necessario, poi li riordiniamo con il bonus delle parole
        candidati = indice.cerca(q, max(60, quanti), list(attivi))
    except Exception as errore:
        raise _errore(503, f"La ricerca non è disponibile: {errore}")

    radici = _radici_parole(q)
    punteggiati = []
    for id_blocco, somiglianza in candidati:
        blocco = sessione.get(Blocco, id_blocco)
        if blocco is None:
            continue
        testo = _senza_accenti(blocco.testo.lower())
        presenti = sum(1 for radice in radici if radice in testo)
        bonus = PESO_PAROLE * presenti / len(radici) if radici else 0.0
        punteggiati.append((round(min(1.0, somiglianza + bonus), 3), blocco))
    punteggiati.sort(key=lambda coppia: -coppia[0])

    risultati = []
    for somiglianza, blocco in punteggiati[:quanti]:
        documento = attivi[blocco.documento_id]
        risultati.append(
            {
                **_blocco_come_dati(blocco),
                "somiglianza": somiglianza,
                "documento": {
                    "id": documento.id,
                    "titolo": documento.titolo,
                    "fonte": documento.fonte,
                    "argomento": documento.argomento,
                },
            }
        )
    return risultati


# ---------- mappa della conoscenza ----------


@router.get("/mappa")
def leggi_mappa(sessione: Session = Depends(apri_sessione)) -> list[dict]:
    """
    Per ogni argomento dice quanti documenti e blocchi attivi ci sono e calcola la copertura.

    Copertura = quanti dei 5 tipi di blocco (definizione, teorema, metodo, esempio,
    esercizio svolto) sono presenti per quell'argomento. 5 su 5 = 100%.
    """
    attivi = list(sessione.exec(select(Documento).where(Documento.attivo == True)))  # noqa: E712

    mappa = []
    for corso, argomenti in config.ARGOMENTI.items():
        voci = []
        for argomento in argomenti:
            documenti = [d for d in attivi if d.argomento == argomento]
            per_tipo = {tipo: 0 for tipo in config.TIPI_BLOCCO}
            for documento in documenti:
                for blocco in _blocchi_di(sessione, documento.id):
                    per_tipo[blocco.tipo] = per_tipo.get(blocco.tipo, 0) + 1
            presenti = [t for t in config.TIPI_PER_COPERTURA if per_tipo[t] > 0]
            voci.append(
                {
                    "argomento": argomento,
                    "documenti": len(documenti),
                    "blocchi": sum(per_tipo.values()),
                    "blocchi_per_tipo": per_tipo,
                    "tipi_mancanti": [t for t in config.TIPI_PER_COPERTURA if per_tipo[t] == 0],
                    "copertura": len(presenti) / len(config.TIPI_PER_COPERTURA),
                }
            )
        mappa.append({"corso": corso, "argomenti": voci})
    return mappa
