"""Test automatico: controlla che lo sportello /api/stato risponda correttamente."""


def test_stato_risponde_ok(client):
    risposta = client.get("/api/stato")
    assert risposta.status_code == 200
    dati = risposta.json()
    assert dati["stato"] == "ok"
    # La derivata di x^2*sin(x) deve contenere sia il seno sia il coseno
    assert "\\sin" in dati["prova_calcolo"]["derivata"]
    assert "\\cos" in dati["prova_calcolo"]["derivata"]
