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
from app.db.modelli import Blocco, Documento, Esercizio
from app.db.sessione import apri_sessione
from app.magazzino.argomenti import classifica
from app.magazzino.blocchi import dividi_in_blocchi
from app.magazzino.estrazione import FileIlleggibile, estrai
from app.magazzino.ocr import OcrNonDisponibile
from app.magazzino.indice import indice

router = APIRouter(prefix="/api/magazzino", tags=["magazzino"])


# ---------- funzioni di supporto ----------


def _errore(codice: int, messaggio: str) -> HTTPException:
    """Crea un errore con un messaggio in italiano che il frontend mostra all'utente."""
    return HTTPException(status_code=codice, detail=messaggio)


AUTOMATICO = "auto"  # argomento scelto al caricamento: "riconoscilo tu"

ERRORE_MODELLO = (
    "Non riesco a preparare la ricerca. La prima volta serve internet per scaricare "
    "il modello linguistico (circa 220 MB). Dettaglio: {}"
)


def _controlla_argomento(argomento: str) -> str:
    """Verifica un argomento e restituisce il corso a cui appartiene."""
    corso = config.corso_di(argomento)
    if corso is None:
        raise _errore(422, f"Argomento non valido: {argomento}")
    return corso


def _controlla_etichette(argomento: str, fonte: str, data: str) -> str | None:
    """
    Verifica le etichette e restituisce il corso a cui appartiene l'argomento
    (None se l'argomento è "auto": il corso si saprà dopo averlo riconosciuto).
    """
    corso = None if argomento == AUTOMATICO else _controlla_argomento(argomento)
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
    argomenti: dict[str, int] = {}
    blocchi = _blocchi_di(sessione, documento.id)
    for blocco in blocchi:
        conteggio[blocco.tipo] = conteggio.get(blocco.tipo, 0) + 1
        argomento = blocco.argomento or documento.argomento
        argomenti[argomento] = argomenti.get(argomento, 0) + 1
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
        # Gli argomenti trattati, dal più presente: es. {"Derivate": 9, "Limiti": 2}
        "argomenti_blocchi": dict(sorted(argomenti.items(), key=lambda voce: -voce[1])),
    }


def _blocco_come_dati(blocco: Blocco, documento: Documento | None = None) -> dict:
    return {
        "id": blocco.id,
        "ordine": blocco.ordine,
        "pagina": blocco.pagina,
        "testo": blocco.testo,
        "tipo": blocco.tipo,
        # Senza argomento proprio (blocchi delle versioni precedenti) vale quello del documento
        "argomento": blocco.argomento or (documento.argomento if documento else None),
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
    corso: str | None,
    fonte: str,
    data: str,
    titolo: str = "",
    tipo_blocchi: str | None = None,
    riconosci_argomenti: bool = True,
) -> dict:
    """
    Salva un documento nel Magazzino: file, testo diviso in blocchi, indice di ricerca.
    Usata sia dal caricamento dei file sia dallo Storico ("aggiungi al Magazzino").
    argomento: quello scelto dallo studente, oppure "auto" per riconoscerlo dal contenuto.
    tipo_blocchi: se indicato, tutti i blocchi ricevono questo tipo (es. "esercizio svolto").
    riconosci_argomenti: se False tutti i blocchi prendono l'argomento del documento.
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

    # 3b. Argomenti: di ogni blocco e, se lo studente ha scelto "auto", del documento
    testi = [b.testo for b in blocchi_grezzi]
    if riconosci_argomenti:
        try:
            classificazione = classifica(testi, None if argomento == AUTOMATICO else argomento)
        except Exception as errore:
            percorso.unlink(missing_ok=True)
            raise _errore(503, ERRORE_MODELLO.format(errore))
        argomento_riconosciuto = argomento == AUTOMATICO
        argomento, argomenti_blocchi = classificazione.argomento_documento, classificazione.argomenti_blocchi
    else:
        argomento_riconosciuto = False
        argomenti_blocchi = [argomento] * len(testi)
    corso = config.corso_di(argomento) or corso

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
        Blocco(
            documento_id=documento.id,
            ordine=i,
            pagina=b.pagina,
            testo=b.testo,
            tipo=tipo_blocchi or b.tipo,
            argomento=argomenti_blocchi[i],
        )
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
        raise _errore(503, ERRORE_MODELLO.format(errore))

    riassunto = _riassunto(sessione, documento)
    riassunto["argomento_riconosciuto"] = argomento_riconosciuto  # per dirlo allo studente
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
    dati["blocchi"] = [_blocco_come_dati(b, documento) for b in _blocchi_di(sessione, id_documento)]
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
    documento.corso = _controlla_argomento(argomento)
    _controlla_etichette(argomento, fonte, data)
    if argomento != documento.argomento:
        # Se lo studente corregge l'argomento del documento, lo seguono i blocchi che avevano
        # quello vecchio; quelli riconosciuti (o corretti) come un altro argomento restano com'erano.
        for blocco in _blocchi_di(sessione, documento.id):
            if blocco.argomento in (None, documento.argomento):
                blocco.argomento = argomento
                sessione.add(blocco)
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
    # Se era un esercizio dello Storico, l'esercizio "dimentica" il collegamento. Va fatto subito:
    # SQLite riusa i numeri dei documenti eliminati, e il prossimo documento caricato verrebbe
    # scambiato per un esercizio generato dall'app (e non citato come fonte).
    for esercizio in sessione.exec(select(Esercizio).where(Esercizio.documento_id == id_documento)):
        esercizio.documento_id = None
        sessione.add(esercizio)
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
    argomento: str | None = None


@router.patch("/blocchi/{id_blocco}")
def modifica_blocco(
    id_blocco: int,
    modifica: ModificaBlocco,
    sessione: Session = Depends(apri_sessione),
) -> dict:
    """Cambia il tipo (es. da "altro" a "teorema") o l'argomento di un blocco, o ne corregge il testo."""
    blocco = sessione.get(Blocco, id_blocco)
    if blocco is None:
        raise _errore(404, "Blocco non trovato.")

    if modifica.tipo is not None:
        if modifica.tipo not in config.TIPI_BLOCCO:
            raise _errore(422, f"Tipo non valido: {modifica.tipo}")
        blocco.tipo = modifica.tipo

    if modifica.argomento is not None:
        _controlla_argomento(modifica.argomento)
        blocco.argomento = modifica.argomento

    if modifica.testo is not None:
        if not modifica.testo.strip():
            raise _errore(422, "Il testo non può essere vuoto.")
        blocco.testo = modifica.testo.strip()
        # Il testo è cambiato: va ricalcolato anche il suo embedding nell'indice
        indice.aggiungi([(blocco.id, blocco.documento_id, blocco.testo)])

    sessione.add(blocco)
    sessione.commit()
    sessione.refresh(blocco)
    return _blocco_come_dati(blocco, sessione.get(Documento, blocco.documento_id))


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
                **_blocco_come_dati(blocco, documento),
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

    Conta l'argomento di ogni BLOCCO, non solo quello del documento: se negli appunti sulle
    derivate c'è un paragrafo sui limiti, quel paragrafo conta per i Limiti. Un documento
    conta per tutti gli argomenti di cui ha almeno un blocco.

    Copertura = quanti dei 5 tipi di blocco (definizione, teorema, metodo, esempio,
    esercizio svolto) sono presenti per quell'argomento. 5 su 5 = 100%.
    """
    attivi = list(sessione.exec(select(Documento).where(Documento.attivo == True)))  # noqa: E712

    per_argomento: dict[str, dict[str, int]] = {}  # argomento -> tipo -> numero di blocchi
    documenti_di: dict[str, set[int]] = {}  # argomento -> documenti che ne parlano
    for documento in attivi:
        blocchi = _blocchi_di(sessione, documento.id)
        if not blocchi:
            documenti_di.setdefault(documento.argomento, set()).add(documento.id)
        for blocco in blocchi:
            argomento = blocco.argomento or documento.argomento
            documenti_di.setdefault(argomento, set()).add(documento.id)
            tipi = per_argomento.setdefault(argomento, {})
            tipi[blocco.tipo] = tipi.get(blocco.tipo, 0) + 1

    mappa = []
    for corso, argomenti in config.ARGOMENTI.items():
        voci = []
        for argomento in argomenti:
            per_tipo = {tipo: 0 for tipo in config.TIPI_BLOCCO} | per_argomento.get(argomento, {})
            presenti = [t for t in config.TIPI_PER_COPERTURA if per_tipo[t] > 0]
            voci.append(
                {
                    "argomento": argomento,
                    "documenti": len(documenti_di.get(argomento, ())),
                    "blocchi": sum(per_tipo.values()),
                    "blocchi_per_tipo": per_tipo,
                    "tipi_mancanti": [t for t in config.TIPI_PER_COPERTURA if per_tipo[t] == 0],
                    "copertura": len(presenti) / len(config.TIPI_PER_COPERTURA),
                }
            )
        mappa.append({"corso": corso, "argomenti": voci})
    return mappa
