"""Test del Magazzino: caricamento, blocchi, ricerca, modifica, mappa, eliminazione, errori."""

import pymupdf

APPUNTI_LIMITI = """Appunti sui limiti

Definizione. Si dice che f(x) tende a L per x che tende a x0 se per ogni epsilon
positivo esiste un delta positivo tale che |f(x) - L| < epsilon.

Teorema (de l'Hopital). Se f e g sono derivabili e il limite del rapporto f/g
presenta una forma indeterminata 0/0, allora il limite coincide con quello di f'/g'.

Esempio. Il limite notevole di sin(x)/x per x che tende a 0 vale 1.

Esercizio svolto. Calcolare il limite di (e^x - 1)/x per x che tende a 0.
Applicando de l'Hopital si ottiene 1.
"""

APPUNTI_INTEGRALI = """Metodo di integrazione per parti. L'integrale di f per g' è uguale
a f per g meno l'integrale di f' per g.
"""

ETICHETTE = {"argomento": "Limiti", "fonte": "Appunti miei", "data": "2026-10-01"}


def carica(client, nome, contenuto, **etichette):
    """Aiuto: carica un file e restituisce la risposta."""
    if isinstance(contenuto, str):
        contenuto = contenuto.encode("utf-8")
    return client.post(
        "/api/magazzino/documenti",
        files={"file": (nome, contenuto)},
        data={**ETICHETTE, **etichette},
    )


def test_ciclo_completo_di_un_documento(client):
    # --- caricamento ---
    risposta = carica(client, "limiti.txt", APPUNTI_LIMITI)
    assert risposta.status_code == 201, risposta.text
    documento = risposta.json()
    assert documento["titolo"] == "limiti"
    assert documento["corso"] == "Analisi I"  # ricavato dall'argomento
    assert documento["attivo"] is True

    # --- i blocchi sono stati riconosciuti per tipo ---
    per_tipo = documento["blocchi_per_tipo"]
    for tipo in ["definizione", "teorema", "esempio", "esercizio svolto"]:
        assert per_tipo.get(tipo) == 1, f"manca il blocco di tipo {tipo}: {per_tipo}"

    id_documento = documento["id"]
    dettaglio = client.get(f"/api/magazzino/documenti/{id_documento}").json()
    assert len(dettaglio["blocchi"]) == documento["numero_blocchi"]

    # --- il file originale si può riaprire ---
    assert client.get(f"/api/magazzino/documenti/{id_documento}/file").status_code == 200

    # --- la ricerca trova il teorema giusto ---
    trovati = client.get("/api/magazzino/cerca", params={"q": "teorema derivabili rapporto forma indeterminata"}).json()
    assert trovati, "la ricerca non ha trovato nulla"
    assert trovati[0]["tipo"] == "teorema"
    assert trovati[0]["documento"]["id"] == id_documento

    # --- la mappa segna i Limiti come coperti per 4 tipi su 5 ---
    mappa = client.get("/api/magazzino/mappa").json()
    limiti = next(a for c in mappa for a in c["argomenti"] if a["argomento"] == "Limiti")
    assert limiti["documenti"] == 1
    assert limiti["copertura"] == 4 / 5
    assert limiti["tipi_mancanti"] == ["metodo"]

    # --- cambio del tipo di un blocco ---
    blocco_altro = next(b for b in dettaglio["blocchi"] if b["tipo"] == "altro")
    risposta = client.patch(f"/api/magazzino/blocchi/{blocco_altro['id']}", json={"tipo": "metodo"})
    assert risposta.json()["tipo"] == "metodo"
    assert client.patch(f"/api/magazzino/blocchi/{blocco_altro['id']}", json={"tipo": "boh"}).status_code == 422

    # --- modifica delle etichette ---
    risposta = client.patch(
        f"/api/magazzino/documenti/{id_documento}",
        json={"titolo": "Limiti – lezione 3", "argomento": "Integrali multipli"},
    )
    assert risposta.json()["titolo"] == "Limiti – lezione 3"
    assert risposta.json()["corso"] == "Analisi II"
    client.patch(f"/api/magazzino/documenti/{id_documento}", json={"argomento": "Limiti"})

    # --- disattivazione: il documento sparisce da ricerca e mappa ---
    client.patch(f"/api/magazzino/documenti/{id_documento}", json={"attivo": False})
    assert client.get("/api/magazzino/cerca", params={"q": "de l'Hopital"}).json() == []
    mappa = client.get("/api/magazzino/mappa").json()
    limiti = next(a for c in mappa for a in c["argomenti"] if a["argomento"] == "Limiti")
    assert limiti["documenti"] == 0
    client.patch(f"/api/magazzino/documenti/{id_documento}", json={"attivo": True})

    # --- eliminazione ---
    assert client.delete(f"/api/magazzino/documenti/{id_documento}").status_code == 204
    assert client.get(f"/api/magazzino/documenti/{id_documento}").status_code == 404
    assert client.get("/api/magazzino/cerca", params={"q": "de l'Hopital"}).json() == []


def test_la_ricerca_distingue_i_documenti(client):
    primo = carica(client, "limiti.md", APPUNTI_LIMITI).json()
    secondo = carica(client, "parti.tex", APPUNTI_INTEGRALI, argomento="Integrali").json()
    assert secondo["blocchi_per_tipo"] == {"metodo": 1}

    trovati = client.get("/api/magazzino/cerca", params={"q": "integrazione per parti"}).json()
    assert trovati[0]["documento"]["id"] == secondo["id"]

    for documento in (primo, secondo):
        client.delete(f"/api/magazzino/documenti/{documento['id']}")


def test_pdf_con_numeri_di_pagina(client):
    # Creiamo al volo un PDF di due pagine
    pdf = pymupdf.open()
    pdf.new_page().insert_text((72, 72), "Definizione. Una serie converge se la successione delle somme parziali ha limite finito.")
    pdf.new_page().insert_text((72, 72), "Teorema. Criterio del rapporto per le serie a termini positivi.")
    risposta = carica(client, "serie.pdf", pdf.tobytes(), argomento="Serie", fonte="Materiale del prof")
    assert risposta.status_code == 201, risposta.text

    dettaglio = client.get(f"/api/magazzino/documenti/{risposta.json()['id']}").json()
    assert [(b["tipo"], b["pagina"]) for b in dettaglio["blocchi"]] == [("definizione", 1), ("teorema", 2)]
    client.delete(f"/api/magazzino/documenti/{dettaglio['id']}")


def test_errori_spiegati_chiaramente(client):
    # PDF senza testo (come una scansione)
    pdf = pymupdf.open()
    pdf.new_page()
    risposta = carica(client, "scansione.pdf", pdf.tobytes())
    assert risposta.status_code == 422
    assert "scansione" in risposta.json()["detail"]

    # Foto: non ancora supportate
    assert carica(client, "foto.jpg", b"\xff\xd8\xff").status_code == 415
    # Formato sconosciuto
    assert carica(client, "programma.exe", b"abc").status_code == 415
    # File vuoto
    assert carica(client, "vuoto.txt", b"").status_code == 422
    # PDF rovinato
    assert carica(client, "rotto.pdf", b"questo non e' un pdf").status_code == 422
    # Etichette sbagliate
    assert carica(client, "a.txt", "ciao", argomento="Cucina").status_code == 422
    assert carica(client, "a.txt", "ciao", data="ieri").status_code == 422

    # Nessuno di questi tentativi deve aver lasciato documenti nel Magazzino
    assert client.get("/api/magazzino/documenti").json() == []
