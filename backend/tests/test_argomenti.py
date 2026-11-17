"""
Test del riconoscimento automatico degli argomenti.

Qui l'embedding è quello "finto" dei test (conta le parole, non capisce il significato),
quindi a decidere sono soprattutto parole chiave, notazione e contesto del documento.
La bontà del riconoscimento con il modello vero è stata misurata a parte, su frasi
di tutti gli argomenti e su una lezione scritta a mano.
"""

from pathlib import Path

from sqlmodel import Session, select

from app.db.modelli import Blocco, Esercizio
from app.db.sessione import motore
from app.magazzino.argomenti import assegna_mancanti, classifica, indizi

ESEMPI = Path(__file__).resolve().parents[2] / "esempi"
ETICHETTE = {"fonte": "Appunti miei", "data": "2026-11-17"}

APPUNTI_MISTI = """Derivate e studio di funzione

Definizione. La derivata di f in x0 è il limite del rapporto incrementale; la retta tangente
al grafico ha coefficiente angolare f'(x0).

Teorema di Rolle. Se f è continua in [a, b], derivabile in (a, b) e f(a) = f(b),
esiste un punto c con derivata nulla: f'(c) = 0.

Esempio. La serie geometrica di ragione q converge se |q| < 1: lo useremo per Taylor
quando parleremo di serie di potenze, con il criterio del rapporto.
"""


def carica(client, nome, contenuto, argomento):
    if isinstance(contenuto, str):
        contenuto = contenuto.encode("utf-8")
    risposta = client.post(
        "/api/magazzino/documenti",
        files={"file": (nome, contenuto)},
        data={**ETICHETTE, "argomento": argomento},
    )
    assert risposta.status_code == 201, risposta.text
    return risposta.json()


def voce_mappa(client, argomento):
    mappa = client.get("/api/magazzino/mappa").json()
    return next(a for c in mappa for a in c["argomenti"] if a["argomento"] == argomento)


# ---------- il classificatore ----------


def test_parole_chiave_e_notazione():
    assert indizi("Il gradiente e la matrice hessiana nei punti critici").argmax() == 5  # più variabili
    frasi = {
        "Il criterio del rapporto per le serie a termini positivi": "Serie",
        "Il problema di Cauchy per y'' + y = 0 ha una sola soluzione": "Equazioni differenziali",
        "Con il teorema di Fubini l'integrale doppio diventa due integrali semplici": "Integrali multipli",
        "Il flusso del rotore attraverso la superficie: teorema di Stokes": "Integrali di superficie",
        "Una funzione con f''(x) > 0 è convessa": "Derivate",
        "∫ x e^x dx si calcola per parti": "Integrali",
    }
    # Ogni frase da sola, come se fosse un documento a sé
    assert [classifica([frase]).argomenti_blocchi[0] for frase in frasi] == list(frasi.values())


def test_blocco_senza_indizi_prende_l_argomento_del_documento():
    testi = ["Teorema di Lagrange: esiste c con f'(c) = (f(b) - f(a))/(b - a).", "x^2 + 3x - 4 = 0, quindi x = 1."]
    assert classifica(testi, "Derivate").argomenti_blocchi == ["Derivate", "Derivate"]
    # Senza argomento scelto dallo studente, quello del documento viene riconosciuto
    risultato = classifica(testi)
    assert risultato.argomento_documento == "Derivate"
    assert risultato.argomenti_blocchi == ["Derivate", "Derivate"]


def test_documento_vuoto():
    assert classifica([], "Serie").argomenti_blocchi == []


# ---------- caricamento, Mappa e correzioni ----------


def test_argomento_riconosciuto_al_caricamento(client):
    documento = carica(client, "appunti-limiti.md", (ESEMPI / "appunti-limiti.md").read_bytes(), "auto")
    assert documento["argomento"] == "Limiti"
    assert documento["corso"] == "Analisi I"  # il corso segue l'argomento riconosciuto
    assert documento["argomento_riconosciuto"] is True
    # Quasi tutti i blocchi parlano di limiti. Con il modello vero lo sono tutti e 7; l'embedding
    # finto dei test non capisce il significato e mette de l'Hôpital tra le Derivate.
    assert list(documento["argomenti_blocchi"])[0] == "Limiti"
    assert documento["argomenti_blocchi"]["Limiti"] >= documento["numero_blocchi"] - 1

    dettaglio = client.get(f"/api/magazzino/documenti/{documento['id']}").json()
    assert all(b["argomento"] for b in dettaglio["blocchi"])
    # Nell'elenco l'informazione "riconosciuto" non serve più
    assert "argomento_riconosciuto" not in dettaglio
    client.delete(f"/api/magazzino/documenti/{documento['id']}")


def test_argomento_scelto_dallo_studente_resta(client):
    documento = carica(client, "limiti.md", (ESEMPI / "appunti-limiti.md").read_bytes(), "Derivate")
    assert documento["argomento"] == "Derivate"
    assert documento["argomento_riconosciuto"] is False
    client.delete(f"/api/magazzino/documenti/{documento['id']}")


def test_argomento_non_valido(client):
    risposta = client.post(
        "/api/magazzino/documenti",
        files={"file": ("a.txt", b"Testo qualsiasi.")},
        data={**ETICHETTE, "argomento": "Topologia"},
    )
    assert risposta.status_code == 422


def test_documento_con_piu_argomenti_e_correzioni(client):
    serie_prima = voce_mappa(client, "Serie")
    derivate_prima = voce_mappa(client, "Derivate")

    documento = carica(client, "derivate.txt", APPUNTI_MISTI, "Derivate")
    assert documento["argomenti_blocchi"] == {"Derivate": documento["numero_blocchi"] - 1, "Serie": 1}

    # La Mappa conta il paragrafo sulle serie per le Serie, il resto per le Derivate
    serie = voce_mappa(client, "Serie")
    assert serie["documenti"] == serie_prima["documenti"] + 1
    assert serie["blocchi"] == serie_prima["blocchi"] + 1
    assert voce_mappa(client, "Derivate")["blocchi"] == derivate_prima["blocchi"] + documento["numero_blocchi"] - 1

    # Lo studente corregge l'argomento di un blocco
    blocchi = client.get(f"/api/magazzino/documenti/{documento['id']}").json()["blocchi"]
    sulle_serie = next(b for b in blocchi if b["argomento"] == "Serie")
    risposta = client.patch(f"/api/magazzino/blocchi/{sulle_serie['id']}", json={"argomento": "Limiti"})
    assert risposta.status_code == 200
    assert risposta.json()["argomento"] == "Limiti"
    assert voce_mappa(client, "Serie") == serie_prima
    assert client.patch(f"/api/magazzino/blocchi/{sulle_serie['id']}", json={"argomento": "Boh"}).status_code == 422

    # Cambiando l'argomento del documento lo seguono i blocchi che avevano quello vecchio,
    # non quelli con un argomento diverso
    client.patch(f"/api/magazzino/documenti/{documento['id']}", json={"argomento": "Integrali"})
    dettaglio = client.get(f"/api/magazzino/documenti/{documento['id']}").json()
    assert dettaglio["argomenti_blocchi"] == {"Integrali": documento["numero_blocchi"] - 1, "Limiti": 1}

    client.delete(f"/api/magazzino/documenti/{documento['id']}")
    assert voce_mappa(client, "Derivate") == derivate_prima


def test_esercizio_svolto_tiene_il_suo_argomento(client):
    """Un esercizio risolto aggiunto al Magazzino non viene "riconosciuto": il suo argomento è noto."""
    esercizio = client.post("/api/risolutore/risolvi", json={"testo": "lim x->0 sin(x)/x"}).json()
    documento = client.post(f"/api/storico/{esercizio['id']}/magazzino").json()
    assert documento["argomenti_blocchi"] == {"Limiti": documento["numero_blocchi"]}
    client.delete(f"/api/magazzino/documenti/{documento['id']}")


def test_blocchi_delle_versioni_precedenti(client):
    """I blocchi caricati con Blueprint 1.0/1.1 non hanno argomento: lo ricevono all'avvio."""
    documento = carica(client, "derivate.txt", APPUNTI_MISTI, "Derivate")
    with Session(motore) as sessione:
        for blocco in sessione.exec(select(Blocco).where(Blocco.documento_id == documento["id"])):
            blocco.argomento = None
            sessione.add(blocco)
        sessione.commit()

    # Prima dell'aggiornamento vale l'argomento del documento
    dettaglio = client.get(f"/api/magazzino/documenti/{documento['id']}").json()
    assert dettaglio["argomenti_blocchi"] == {"Derivate": documento["numero_blocchi"]}

    assert assegna_mancanti(motore) == documento["numero_blocchi"]
    dettaglio = client.get(f"/api/magazzino/documenti/{documento['id']}").json()
    assert dettaglio["argomenti_blocchi"] == documento["argomenti_blocchi"]
    assert assegna_mancanti(motore) == 0  # una seconda volta non c'è niente da fare
    client.delete(f"/api/magazzino/documenti/{documento['id']}")


def test_citazione_preferisce_l_argomento_dell_esercizio(client):
    """Con due teoremi equivalenti, la citazione viene dagli appunti sull'argomento dell'esercizio."""
    from app.risolutore.citazioni import Biblioteca

    teorema = "Teorema di de l'Hôpital. Per la forma 0/0 si passa al rapporto delle derivate.\n"
    documenti = [carica(client, f"{a}.txt", teorema, a) for a in ("Limiti", "Derivate")]
    id_blocchi = {}
    for documento in documenti:
        blocco = client.get(f"/api/magazzino/documenti/{documento['id']}").json()["blocchi"][0]
        client.patch(f"/api/magazzino/blocchi/{blocco['id']}", json={"argomento": documento["argomento"]})
        id_blocchi[documento["argomento"]] = blocco["id"]

    with Session(motore) as sessione:
        for argomento in ("Limiti", "Derivate"):
            assert Biblioteca(sessione, argomento).cita("hopital")["blocco_id"] == id_blocchi[argomento]
    for documento in documenti:
        client.delete(f"/api/magazzino/documenti/{documento['id']}")


def test_documento_eliminato_scollegato_dallo_storico(client):
    """Eliminato dal Magazzino un esercizio svolto, il documento caricato dopo non viene scambiato per lui."""
    esercizio = client.post("/api/risolutore/risolvi", json={"testo": "lim x->0 (e^x - 1)/x"}).json()
    generato = client.post(f"/api/storico/{esercizio['id']}/magazzino").json()
    client.delete(f"/api/magazzino/documenti/{generato['id']}")

    documento = carica(client, "derivate.txt", APPUNTI_MISTI, "Derivate")  # può riusare lo stesso numero
    assert "Serie" in documento["argomenti_blocchi"]  # riconosciuto, non trattato come esercizio
    with Session(motore) as sessione:
        assert sessione.get(Esercizio, esercizio["id"]).documento_id is None
    client.delete(f"/api/magazzino/documenti/{documento['id']}")
