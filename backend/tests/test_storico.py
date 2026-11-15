"""Test dello Storico, di "Mettimi alla prova" e dell'aggiunta di un esercizio al Magazzino."""

import pytest


def risolvi(client, testo, tipo="auto"):
    risposta = client.post("/api/risolutore/risolvi", json={"testo": testo, "tipo": tipo})
    assert risposta.status_code == 200, risposta.text
    return risposta.json()


def prova(client, id_esercizio, risposta, passaggio=None):
    esito = client.post(f"/api/storico/{id_esercizio}/controlla", json={"passaggio": passaggio, "risposta": risposta})
    assert esito.status_code == 200, esito.text
    return esito.json()


def indice_domanda(soluzione, titolo):
    """Posizione del primo passaggio con quel titolo che ha una domanda."""
    return next(i for i, p in enumerate(soluzione["passaggi"]) if p["titolo"] == titolo and p["domanda"])


# ---------- storico ----------


def test_ogni_esercizio_finisce_nello_storico(client):
    soluzione = risolvi(client, "derivata di x^3*e^x")
    assert isinstance(soluzione["id"], int)
    # Le risposte corrette non devono mai arrivare al browser
    assert "_controlli" not in soluzione

    # Risolvere di nuovo lo stesso esercizio non crea un doppione
    di_nuovo = risolvi(client, "derivata di x^3*e^x")
    assert di_nuovo["id"] == soluzione["id"]

    elenco = client.get("/api/storico").json()
    assert elenco[0]["id"] == soluzione["id"]
    assert elenco[0]["argomento"] == "Derivate"
    assert [e["testo"] for e in elenco].count("derivata di x^3*e^x") == 1

    dettaglio = client.get(f"/api/storico/{soluzione['id']}").json()
    assert dettaglio["passaggi"] == soluzione["passaggi"]
    assert dettaglio["testo"] == "derivata di x^3*e^x"
    assert "controlli" not in dettaglio and "_controlli" not in dettaglio

    assert client.delete(f"/api/storico/{soluzione['id']}").status_code == 204
    assert client.get(f"/api/storico/{soluzione['id']}").status_code == 404


# ---------- mettimi alla prova: passaggi ----------


def test_domande_sui_passaggi_della_derivata(client):
    soluzione = risolvi(client, "derivata di x^2*sin(x)")
    elementare = indice_domanda(soluzione, "Derivata elementare")
    assert soluzione["passaggi"][elementare]["domanda"] == r"Quanto vale $D\left[x^{2}\right]$?"
    # La regola del prodotto non ha una "risposta" da scrivere
    assert soluzione["passaggi"][0]["domanda"] is None

    assert prova(client, soluzione["id"], "2x", elementare) == {"corretto": True, "messaggio": "Esatto!"}
    assert prova(client, soluzione["id"], "x*2", elementare)["corretto"]
    assert not prova(client, soluzione["id"], "x^2", elementare)["corretto"]

    # Sviluppato o raccolto, il risultato è giusto; una delle due forme è diversa da quella dell'app
    sviluppato = prova(client, soluzione["id"], "2x sin(x) + x^2 cos(x)")
    raccolto = prova(client, soluzione["id"], "x*(x cos(x) + 2 sin(x))")
    assert sviluppato["corretto"] and raccolto["corretto"]
    assert any("forma diversa" in esito["messaggio"] for esito in (sviluppato, raccolto))
    assert soluzione["controllo_finale"]["tipo"] == "espressione"


def test_integrale_a_meno_di_una_costante(client):
    soluzione = risolvi(client, "integrale di x*e^x dx")
    parti = indice_domanda(soluzione, "Integrazione per parti")
    assert prova(client, soluzione["id"], "e^x", parti)["corretto"]
    assert prova(client, soluzione["id"], "e^x + 5", parti)["corretto"]  # anche g + costante è una primitiva

    assert prova(client, soluzione["id"], "x e^x - e^x + c")["corretto"]
    assert prova(client, soluzione["id"], "(x-1)*e^x")["corretto"]
    sbagliata = prova(client, soluzione["id"], "x e^x")
    assert not sbagliata["corretto"] and "derivare" in sbagliata["messaggio"]


def test_limiti_infinito_e_non_esiste(client):
    soluzione = risolvi(client, "limite per x che tende a 0 di sin(x)/x")
    hopital = indice_domanda(soluzione, "Applichiamo de l'Hôpital")
    assert prova(client, soluzione["id"], "cos(x)/1", hopital)["corretto"]
    assert prova(client, soluzione["id"], "1")["corretto"]

    destro = risolvi(client, "lim x->0+ 1/x")
    assert prova(client, destro["id"], "+oo")["corretto"]
    segno = prova(client, destro["id"], "-infinito")
    assert not segno["corretto"] and "segno" in segno["messaggio"]

    bilatero = risolvi(client, "limite di 1/x per x che tende a 0")
    assert prova(client, bilatero["id"], "non esiste")["corretto"]
    assert not prova(client, bilatero["id"], "oo")["corretto"]


def test_serie_gradiente_edo(client):
    serie = risolvi(client, "serie di termine 1/n^2")
    assert serie["controllo_finale"] == {"tipo": "scelta", "domanda": "La serie converge?"}
    assert prova(client, serie["id"], "converge")["corretto"]
    assert not prova(client, serie["id"], "non converge")["corretto"]
    armonica = indice_domanda(serie, "Serie armonica generalizzata")
    assert prova(client, serie["id"], "2", armonica)["corretto"]

    gradiente = risolvi(client, "gradiente di x^2*y + y^3")
    assert prova(client, gradiente["id"], "(2xy, x^2 + 3y^2)")["corretto"]
    sbagliato = prova(client, gradiente["id"], "(2xy, x^2)")
    assert not sbagliato["corretto"] and "2ª" in sbagliato["messaggio"]

    generale = risolvi(client, "y'' + y = 0")
    assert prova(client, generale["id"], "y = c1 cos(x) + c2 sin(x)")["corretto"]
    assert prova(client, generale["id"], "C_1*sin(x) + C_2*cos(x)")["corretto"]
    parziale = prova(client, generale["id"], "c1 cos(x)")
    assert not parziale["corretto"] and "generale" in parziale["messaggio"]
    assert not prova(client, generale["id"], "c1 e^x")["corretto"]

    cauchy = risolvi(client, "y' = y, y(0) = 2")
    assert prova(client, cauchy["id"], "2e^x")["corretto"]
    assert not prova(client, cauchy["id"], "3e^x")["corretto"]
    assert not prova(client, cauchy["id"], "c e^x")["corretto"]


def test_errori_di_controllo(client):
    critici = risolvi(client, "punti critici di x^2 + y^2")
    assert critici["controllo_finale"] is None
    assert client.post(f"/api/storico/{critici['id']}/controlla", json={"risposta": "(0,0)"}).status_code == 422

    soluzione = risolvi(client, "derivata di x^3")
    illeggibile = client.post(f"/api/storico/{soluzione['id']}/controlla", json={"risposta": "x^^2"})
    assert illeggibile.status_code == 422
    assert client.post(f"/api/storico/{soluzione['id']}/controlla", json={"risposta": "3x^2", "passaggio": 99}).status_code == 422
    assert client.post("/api/storico/99999/controlla", json={"risposta": "1"}).status_code == 404


# ---------- aggiunta al Magazzino ----------


def test_esercizio_svolto_nel_magazzino(client):
    soluzione = risolvi(client, "limite per x->0 di (e^x-1)/x")
    # Prima: de l'Hôpital non è negli appunti
    assert "teorema di de l'Hôpital" in soluzione["concetti_mancanti"]

    documento = client.post(f"/api/storico/{soluzione['id']}/magazzino")
    assert documento.status_code == 201, documento.text
    documento = documento.json()
    assert documento["argomento"] == "Limiti" and documento["fonte"] == "Esercitazione"
    assert set(documento["blocchi_per_tipo"]) == {"esercizio svolto"}
    assert client.get(f"/api/storico/{soluzione['id']}").json()["documento_id"] == documento["id"]
    # Una seconda volta non si può
    assert client.post(f"/api/storico/{soluzione['id']}/magazzino").status_code == 409

    # L'esercizio svolto dall'app NON diventa una fonte per i metodi: de l'Hôpital resta "mancante"
    di_nuovo = risolvi(client, "limite per x->0 di (e^x-1)/x")
    assert "teorema di de l'Hôpital" in di_nuovo["concetti_mancanti"]

    # Se il documento viene eliminato dal Magazzino, lo Storico se ne accorge
    client.delete(f"/api/magazzino/documenti/{documento['id']}")
    assert client.get(f"/api/storico/{soluzione['id']}").json()["documento_id"] is None


@pytest.fixture(autouse=True, scope="module")
def svuota_storico(client):
    """Alla fine dei test lo Storico torna vuoto."""
    yield
    for esercizio in client.get("/api/storico").json():
        client.delete(f"/api/storico/{esercizio['id']}")
