"""
Test del riconoscimento del testo in foto e scansioni (OCR).

Non avendo foto vere di appunti, le creiamo: testo scritto con un carattere che imita la
scrittura a mano, leggermente storto, su carta giallina, con un po' di rumore e sfocatura,
come una foto fatta con il telefono.
"""

import io
import random
from pathlib import Path

import pymupdf
import pytest
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from app.magazzino.ocr import raggruppa_in_paragrafi

# Caratteri "a mano" di Windows; se mancano (es. su Linux) i test con le foto vengono saltati
CARATTERI = [Path("C:/Windows/Fonts/segoepr.ttf"), Path("C:/Windows/Fonts/Inkfree.ttf")]
CARATTERE = next((c for c in CARATTERI if c.exists()), None)
serve_carattere = pytest.mark.skipif(CARATTERE is None, reason="manca un carattere che imiti la scrittura a mano")

APPUNTI = [
    "Teorema di de l'Hopital. Se il limite del rapporto",
    "si presenta nella forma indeterminata zero su zero",
    "allora coincide con il limite del rapporto delle derivate.",
    "",
    "Esempio. Il limite di sin(x)/x per x che tende a 0 vale 1.",
]


def foto_di_appunti(righe: list[str], formato: str = "JPEG") -> bytes:
    """Crea un'immagine che assomiglia alla foto di un foglio di appunti."""
    random.seed(1)
    carattere = ImageFont.truetype(str(CARATTERE), 34)
    img = Image.new("RGB", (1400, 140 + 64 * len(righe)), (250, 246, 228))
    disegno = ImageDraw.Draw(img)
    y = 60
    for riga in righe:
        disegno.text((70 + random.randint(-8, 8), y), riga, font=carattere, fill=(30, 40, 90))
        y += 64
    img = img.rotate(2, expand=True, fillcolor=(120, 110, 95))
    rumore = Image.effect_noise(img.size, 22).convert("RGB")
    img = Image.blend(img, rumore, 0.1).filter(ImageFilter.GaussianBlur(0.7))
    buffer = io.BytesIO()
    img.save(buffer, formato, quality=85)
    return buffer.getvalue()


def carica(client, nome, contenuto, **etichette):
    return client.post(
        "/api/magazzino/documenti",
        files={"file": (nome, contenuto)},
        data={"argomento": "Limiti", "fonte": "Appunti miei", "data": "2026-11-16", **etichette},
    )


# ---------- raggruppamento delle righe (non serve l'OCR) ----------


def test_righe_raggruppate_in_paragrafi():
    # (x, y in alto, altezza, testo), come le dà l'OCR: righe ogni 60 pixel, con riquadri alti 80
    # che si sovrappongono; prima di "Esempio" c'è una riga lasciata vuota (passo 120)
    righe = [(10, 120, 80, "allora coincide"), (10, 0, 80, "Teorema di"), (10, 60, 80, "de l'Hopital"), (10, 240, 80, "Esempío ×")]
    assert raggruppa_in_paragrafi(righe) == ["Teorema di\nde l'Hopital\nallora coincide", "Esempio x"]
    # Una riga del foglio divisa in due pezzi viene ricomposta da sinistra a destra
    divisa = [(400, 2, 80, "sin(x)/x"), (10, 0, 80, "Il limite di"), (10, 60, 80, "vale 1")]
    assert raggruppa_in_paragrafi(divisa) == ["Il limite di sin(x)/x\nvale 1"]
    # Con due sole righe si confronta il passo con l'altezza di una riga
    assert raggruppa_in_paragrafi([(0, 0, 30, "a"), (0, 35, 30, "b")]) == ["a\nb"]
    assert raggruppa_in_paragrafi([(0, 0, 30, "a"), (0, 90, 30, "b")]) == ["a", "b"]
    assert raggruppa_in_paragrafi([]) == []


# ---------- appunti abbreviati e pagine (non serve l'OCR) ----------


def test_intestazioni_abbreviate_e_pagine():
    from app.magazzino.blocchi import dividi_in_blocchi, indovina_tipo

    # Intestazioni tipiche degli appunti a mano, anche con qualche errore dell'OCR
    assert indovina_tipo("Teor (f con deriv. nulla): sia f...") == "teorema"
    assert indovina_tipo("Teoreua (Proprietà f convesse)") == "teorema"
    assert indovina_tipo("Prop. 3 Se f è continua") == "teorema"
    assert indovina_tipo("Corollario (f con stessa derivata)") == "teorema"
    assert indovina_tipo("DEF (DERIVATE DI ORDINE SUPERIORE)") == "definizione"
    assert indovina_tipo("Def. Una funzione si dice convessa") == "definizione"
    assert indovina_tipo("OSS/ESEMPLO: arcsin'(x)") == "esempio"
    assert indovina_tipo("Es. il limite di sin(x)/x") == "esempio"
    # Parole che iniziano allo stesso modo ma non sono intestazioni
    assert indovina_tipo("Deficit di continuità nel punto") == "altro"
    assert indovina_tipo("Esistono funzioni continue") == "altro"

    # Ogni pagina inizia un blocco nuovo, anche se i paragrafi sono corti
    blocchi = dividi_in_blocchi([(1, "Si ha che:"), (1, "f è continua."), (2, "Similmente: f'' è la velocità.")])
    assert [(b.pagina, b.testo) for b in blocchi] == [(1, "Si ha che:\n\nf è continua."), (2, "Similmente: f'' è la velocità.")]


# ---------- foto e scansioni nel Magazzino ----------


@serve_carattere
def test_foto_di_appunti_scritti_a_mano(client):
    risposta = carica(client, "appunti.jpg", foto_di_appunti(APPUNTI))
    assert risposta.status_code == 201, risposta.text
    documento = risposta.json()
    assert documento["letto_con_ocr"] is True
    assert documento["ocr"]["pagine"] == 1 and documento["ocr"]["affidabilita"] > 0.8
    # Il testo letto viene diviso in blocchi e il tipo viene riconosciuto come per i file di testo
    assert documento["blocchi_per_tipo"].get("teorema") == 1
    assert documento["blocchi_per_tipo"].get("esempio") == 1

    blocchi = client.get(f"/api/magazzino/documenti/{documento['id']}").json()["blocchi"]
    testo = " ".join(b["testo"] for b in blocchi).lower()
    for parola in ("teorema", "hopital", "indeterminata", "derivate", "limite"):
        assert parola in testo, f"manca «{parola}» nel testo riconosciuto: {testo}"

    # Il risolutore trova il teorema nelle foto e lo cita
    soluzione = client.post("/api/risolutore/risolvi", json={"testo": "limite per x->0 di sin(x)/x"}).json()
    citazioni = [p["citazione"] for p in soluzione["passaggi"] if p["concetto"] == "teorema di de l'Hôpital"]
    assert citazioni and citazioni[0]["documento_id"] == documento["id"]

    # La ricerca tiene conto delle parole esatte: un blocco con formule lette male (che
    # "sporcano" il significato) viene trovato lo stesso se contiene la parola cercata
    trovati = client.get("/api/magazzino/cerca", params={"q": "teorema di de l'Hopital", "quanti": 1}).json()
    assert trovati[0]["tipo"] == "teorema"

    # Lo studente può correggere un errore di lettura: il testo cambia e resta cercabile
    teorema = next(b for b in blocchi if b["tipo"] == "teorema")
    corretto = "Teorema di de l'Hôpital (versione corretta a mano). Forma indeterminata 0/0."
    risposta = client.patch(f"/api/magazzino/blocchi/{teorema['id']}", json={"testo": corretto})
    assert risposta.json()["testo"] == corretto
    trovati = client.get("/api/magazzino/cerca", params={"q": "versione corretta a mano"}).json()
    assert trovati[0]["id"] == teorema["id"]

    client.delete(f"/api/magazzino/documenti/{documento['id']}")
    client.delete(f"/api/storico/{soluzione['id']}")


@serve_carattere
def test_altri_formati_di_immagine(client):
    risposta = carica(client, "lavagna.png", foto_di_appunti(APPUNTI[:3], "PNG"))
    assert risposta.status_code == 201, risposta.text
    client.delete(f"/api/magazzino/documenti/{risposta.json()['id']}")


@serve_carattere
def test_pdf_scansionato_e_misto(client):
    """Una pagina scritta al computer e una scansionata: la seconda viene letta con l'OCR."""
    pdf = pymupdf.open()
    pdf.new_page().insert_text((72, 72), "Definizione. Una serie converge se la successione delle somme parziali ha limite finito.")
    pagina = pdf.new_page()
    pagina.insert_image(pagina.rect, stream=foto_di_appunti(APPUNTI))
    risposta = carica(client, "scansione.pdf", pdf.tobytes(), argomento="Serie")
    assert risposta.status_code == 201, risposta.text
    documento = risposta.json()
    assert documento["letto_con_ocr"] and documento["ocr"]["pagine"] == 1

    blocchi = client.get(f"/api/magazzino/documenti/{documento['id']}").json()["blocchi"]
    assert blocchi[0]["pagina"] == 1 and blocchi[0]["tipo"] == "definizione"
    # I blocchi letti dalla scansione ricordano la loro pagina (per le citazioni "p. 2")
    assert any(b["pagina"] == 2 and "hopital" in b["testo"].lower() for b in blocchi)

    # Per correggere il testo si può vedere la pagina originale come immagine
    pagina = client.get(f"/api/magazzino/documenti/{documento['id']}/pagina/2")
    assert pagina.status_code == 200 and pagina.headers["content-type"] == "image/png"
    assert pagina.content.startswith(b"\x89PNG")
    assert client.get(f"/api/magazzino/documenti/{documento['id']}/pagina/3").status_code == 404
    client.delete(f"/api/magazzino/documenti/{documento['id']}")


def test_foto_senza_testo(client):
    vuota = io.BytesIO()
    Image.new("RGB", (800, 600), (250, 246, 228)).save(vuota, "JPEG")
    risposta = carica(client, "foglio_bianco.jpg", vuota.getvalue())
    assert risposta.status_code == 422
    assert "più nitida" in risposta.json()["detail"]
    assert client.get("/api/magazzino/documenti").json() == []


# ---------- esercizi da una foto ----------


@serve_carattere
def test_esercizi_da_foto(client):
    foglio = ["Esercizio 1. Calcolare la derivata di x^2", "", "Esercizio 2. Calcolare l'integrale di x dx"]
    risposta = client.post("/api/risolutore/da-file", files={"file": ("foglio.jpg", foto_di_appunti(foglio))})
    assert risposta.status_code == 200, risposta.text
    dati = risposta.json()
    assert dati["letto_con_ocr"] is True
    assert [e["numero"] for e in dati["esercizi"]] == [1, 2]
    assert "derivata" in dati["esercizi"][0]["testo"].lower()


# ---------- aggiornamento di un database vecchio ----------


def test_colonna_aggiunta_a_un_database_vecchio(tmp_path):
    """Un Magazzino creato da Blueprint 1.0 (senza la colonna letto_con_ocr) viene aggiornato."""
    from sqlalchemy import create_engine, inspect, text

    from app.db.sessione import aggiungi_colonne_mancanti

    motore = create_engine(f"sqlite:///{tmp_path / 'vecchio.db'}")
    with motore.begin() as connessione:
        connessione.execute(text(
            "CREATE TABLE documento (id INTEGER PRIMARY KEY, titolo VARCHAR NOT NULL, nome_file VARCHAR NOT NULL, "
            "file_salvato VARCHAR NOT NULL, argomento VARCHAR NOT NULL, corso VARCHAR NOT NULL, fonte VARCHAR NOT NULL, "
            "data VARCHAR NOT NULL, attivo BOOLEAN NOT NULL, caricato_il VARCHAR NOT NULL)"
        ))  # fmt: skip
        connessione.execute(text(
            "INSERT INTO documento VALUES (1, 'Appunti', 'a.pdf', 'x.pdf', 'Limiti', 'Analisi I', 'Appunti miei', "
            "'2026-11-01', 1, '2026-11-01T10:00:00')"
        ))  # fmt: skip

    assert aggiungi_colonne_mancanti(motore) == ["documento.letto_con_ocr"]
    assert "letto_con_ocr" in {c["name"] for c in inspect(motore).get_columns("documento")}
    with motore.connect() as connessione:
        # Il documento che c'era resta, con il nuovo campo a "no"
        assert connessione.execute(text("SELECT titolo, letto_con_ocr FROM documento")).one() == ("Appunti", 0)
    # Una seconda volta non c'è più niente da aggiungere
    assert aggiungi_colonne_mancanti(motore) == []
