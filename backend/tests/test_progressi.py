"""Test dei progressi: serie di giorni di studio e traguardi."""

from datetime import date, datetime, timedelta

import pytest
from sqlmodel import Session, delete

from app.api.progressi import calcola_serie
from app.db.modelli import Attivita, TraguardoOttenuto
from app.db.sessione import motore

OGGI = date(2026, 11, 15)


def giorni(*distanze):
    """Insieme di giorni, indicati come "quanti giorni fa" rispetto a OGGI."""
    return {OGGI - timedelta(days=d) for d in distanze}


# ---------- serie di giorni (funzione pura) ----------


def test_calcola_serie():
    assert calcola_serie(set(), OGGI) == (0, 0)
    assert calcola_serie(giorni(0), OGGI) == (1, 1)
    assert calcola_serie(giorni(0, 1, 2), OGGI) == (3, 3)
    # Se oggi non hai ancora studiato, la serie di ieri è ancora valida
    assert calcola_serie(giorni(1, 2), OGGI) == (2, 2)
    # Un giorno saltato interrompe la serie, ma il record resta
    assert calcola_serie(giorni(0, 2, 3, 4, 5), OGGI) == (1, 4)
    assert calcola_serie(giorni(3, 4), OGGI) == (0, 2)


# ---------- attraverso il server ----------


@pytest.fixture(autouse=True)
def progressi_vuoti():
    """Ogni test parte senza attività né traguardi (gli altri test ne creano risolvendo esercizi)."""
    with Session(motore) as sessione:
        sessione.exec(delete(Attivita))
        sessione.exec(delete(TraguardoOttenuto))
        sessione.commit()
    yield


def traguardo(progressi, chiave):
    return next(t for t in progressi["traguardi"] if t["chiave"] == chiave)


def test_primo_esercizio_e_traguardi_nuovi(client):
    vuoti = client.get("/api/progressi").json()
    assert vuoti["serie"] == {"attuale": 0, "record": 0, "studiato_oggi": False}
    assert vuoti["nuovi"] == []
    assert len(vuoti["calendario"]) == 105 and vuoti["calendario"][-1]["giorno"] == date.today().isoformat()

    soluzione = client.post("/api/risolutore/risolvi", json={"testo": "integrale di x^2"}).json()
    progressi = client.get("/api/progressi").json()
    assert progressi["serie"]["attuale"] == 1 and progressi["serie"]["studiato_oggi"]
    assert progressi["totali"]["esercizi"] == 1
    assert next(a for a in progressi["per_argomento"] if a["argomento"] == "Integrali")["esercizi"] == 1
    assert [t["chiave"] for t in progressi["nuovi"]] == ["esercizi_1"]
    assert traguardo(progressi, "argomento_Integrali")["attuale"] == 1
    assert progressi["calendario"][-1]["attivita"] == 1

    # Il traguardo è "nuovo" una volta sola
    assert client.get("/api/progressi").json()["nuovi"] == []

    # Risolvere di nuovo lo stesso esercizio non conta come esercizio diverso
    client.post("/api/risolutore/risolvi", json={"testo": "integrale di x^2"})
    assert client.get("/api/progressi").json()["totali"]["esercizi"] == 1

    # Anche se l'esercizio viene tolto dallo Storico, il traguardo resta
    client.delete(f"/api/storico/{soluzione['id']}")
    assert traguardo(client.get("/api/progressi").json(), "esercizi_1")["ottenuto"]


def test_mettimi_alla_prova_conta(client):
    soluzione = client.post("/api/risolutore/risolvi", json={"testo": "derivata di x^3"}).json()
    sbagliata = client.post(f"/api/storico/{soluzione['id']}/controlla", json={"risposta": "x^2"}).json()
    assert not sbagliata["corretto"]
    assert client.get("/api/progressi").json()["totali"]["risposte_giuste"] == 0

    client.post(f"/api/storico/{soluzione['id']}/controlla", json={"risposta": "3x^2"})
    progressi = client.get("/api/progressi").json()
    assert progressi["totali"]["risposte_giuste"] == 1
    assert progressi["totali"]["fatti_da_te"] == 1
    assert {t["chiave"] for t in progressi["nuovi"]} >= {"risposte_1", "fatti_1"}
    client.delete(f"/api/storico/{soluzione['id']}")


def test_serie_di_giorni_e_traguardo(client):
    # Simuliamo due giorni di studio passati (ieri e l'altro ieri), poi studiamo oggi
    oggi = date.today()
    with Session(motore) as sessione:
        for distanza in (1, 2):
            giorno = oggi - timedelta(days=distanza)
            sessione.add(Attivita(giorno=giorno.isoformat(), momento=datetime.now().isoformat(), tipo="risolto"))
        sessione.commit()
    assert client.get("/api/progressi").json()["serie"]["attuale"] == 2

    soluzione = client.post("/api/risolutore/risolvi", json={"testo": "limite per x->0 di sin(x)/x"}).json()
    progressi = client.get("/api/progressi").json()
    assert progressi["serie"] == {"attuale": 3, "record": 3, "studiato_oggi": True}
    assert "serie_3" in [t["chiave"] for t in progressi["nuovi"]]
    assert progressi["totali"]["giorni_di_studio"] == 3
    client.delete(f"/api/storico/{soluzione['id']}")
