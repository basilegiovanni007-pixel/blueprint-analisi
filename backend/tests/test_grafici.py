"""Test dei grafici: preparazione delle funzioni, studio di funzione, Taylor e serie."""

import math

import pytest


def studio(client, testo):
    risposta = client.post("/api/grafici/studio", json={"testo": testo})
    assert risposta.status_code == 200, risposta.text
    return risposta.json()


def tappa(dati, titolo):
    return next(t for t in dati["tappe"] if t["titolo"].startswith(titolo))


def punti(dati, stile):
    return sorted(
        (round(e["x"], 4), round(e["y"], 4))
        for t in dati["tappe"]
        for e in t["elementi"]
        if e["tipo"] == "punto" and e["stile"] == stile
    )


# ---------- preparazione delle funzioni ----------


def test_funzione_con_parametri(client):
    dati = client.post("/api/grafici/funzione", json={"testo": "f(x) = a*sin(b*x)"}).json()
    assert dati["parametri"] == ["a", "b"]
    assert dati["js"] == "a*sin(b*x)"

    dati = client.post("/api/grafici/funzione", json={"testo": "sqrt(x^2+1) + |x| + e^x"}).json()
    assert dati["parametri"] == []
    # La scrittura deve essere quella che il browser sa calcolare: ^ per le potenze, abs, e
    assert "**" not in dati["js"] and "abs(x)" in dati["js"] and "Abs" not in dati["js"]


def test_funzione_non_valida(client):
    risposta = client.post("/api/grafici/funzione", json={"testo": "xsin(x)"})
    assert risposta.status_code == 422
    assert "Non riconosco" in risposta.json()["detail"]


# ---------- studio di funzione ----------


def test_studio_cubica(client):
    dati = studio(client, "x^3 - 3x")
    assert [t["titolo"].split(":")[0] for t in dati["tappe"]] == [
        "Dominio", "Simmetrie", "Intersezioni con gli assi", "Segno", "Limiti e asintoti",
        "Derivata prima", "Derivata seconda", "Grafico",
    ]  # fmt: skip
    assert "dispari" in tappa(dati, "Simmetrie")["testo"]
    assert punti(dati, "zero") == [(-1.7321, 0.0), (0.0, 0.0), (1.7321, 0.0)]
    assert punti(dati, "massimo") == [(-1.0, 2.0)]
    assert punti(dati, "minimo") == [(1.0, -2.0)]
    assert punti(dati, "flesso") == [(0.0, 0.0)]
    assert "Non ci sono asintoti" in tappa(dati, "Limiti")["testo"]
    # La finestra consigliata contiene tutti i punti importanti
    assert dati["finestra"]["xmin"] < -1.8 and dati["finestra"]["xmax"] > 1.8
    # L'ultima tappa è quella che fa comparire la curva
    assert dati["tappe"][-1]["elementi"] == [{"tipo": "curva"}]


def test_studio_razionale_con_asintoti(client):
    dati = studio(client, "(x^2+1)/(x-1)")
    elementi = tappa(dati, "Limiti")["elementi"]
    assert {"tipo": "verticale", "x": 1.0, "etichetta": "x = 1"} in elementi
    assert {"tipo": "retta", "m": 1.0, "q": 1.0, "etichetta": "y = x + 1"} in elementi
    assert len(punti(dati, "massimo")) == 1 and len(punti(dati, "minimo")) == 1


def test_studio_dominio_limitato_e_asintoto_orizzontale(client):
    dati = studio(client, "ln(x)/x")
    assert tappa(dati, "Dominio")["elementi"] == [{"tipo": "fascia", "da": None, "a": 0.0, "stile": "escluso"}]
    elementi = tappa(dati, "Limiti")["elementi"]
    assert any(e["tipo"] == "orizzontale" and e["y"] == 0 for e in elementi)
    assert any(e["tipo"] == "verticale" and e["x"] == 0 for e in elementi)
    massimo = punti(dati, "massimo")[0]
    assert massimo == (round(math.e, 4), round(1 / math.e, 4))


@pytest.mark.parametrize("funzione", ["sin(x)", "tan(x)", "x - cos(x)", "sqrt(x^2-1)", "abs(x)", "e^(-x^2)", "1/x", "5"])
def test_studio_non_si_blocca_mai(client, funzione):
    dati = studio(client, funzione)
    assert dati["tappe"][0]["titolo"] == "Dominio"
    assert dati["tappe"][-1]["titolo"] == "Grafico"
    assert dati["finestra"]["xmin"] < dati["finestra"]["xmax"]


def test_studio_tangente_trova_gli_asintoti(client):
    dati = studio(client, "tan(x)")
    verticali = [e["x"] for e in tappa(dati, "Limiti")["elementi"] if e["tipo"] == "verticale"]
    assert round(math.pi / 2, 6) in [round(v, 6) for v in verticali]


def test_studio_con_parametri_rifiutato(client):
    risposta = client.post("/api/grafici/studio", json={"testo": "a*x^2"})
    assert risposta.status_code == 422


# ---------- Taylor ----------


def test_taylor_del_seno(client):
    dati = client.post("/api/grafici/taylor", json={"testo": "sin(x)", "ordine_massimo": 5}).json()
    assert [p["ordine"] for p in dati["polinomi"]] == [0, 1, 2, 3, 4, 5]
    assert dati["polinomi"][1]["js"] == "x"
    assert dati["polinomi"][3]["js"] == "-x^3/6 + x"
    assert dati["polinomi"][5]["latex"] == r"x - \frac{x^{3}}{6} + \frac{x^{5}}{120}"


def test_taylor_centro_diverso_e_errori(client):
    dati = client.post("/api/grafici/taylor", json={"testo": "ln(x)", "centro": "1", "ordine_massimo": 2}).json()
    assert dati["centro"] == 1.0
    assert dati["polinomi"][2]["latex"] == r"\left(x - 1\right) - \frac{\left(x - 1\right)^{2}}{2}"

    # ln(x) non è definita in 0: errore chiaro
    risposta = client.post("/api/grafici/taylor", json={"testo": "ln(x)", "centro": "0"})
    assert risposta.status_code == 422
    assert "cambia il centro" in risposta.json()["detail"]


# ---------- serie ----------


def test_serie_convergente_con_somma(client):
    dati = client.post("/api/grafici/serie", json={"testo": "1/n^2"}).json()
    assert dati["converge"] is True
    assert dati["somma_latex"] == r"\frac{\pi^{2}}{6}"
    assert abs(dati["somma"] - math.pi**2 / 6) < 1e-9
    assert dati["termine"]["variabile"] == "n"


def test_serie_divergente_e_geometrica(client):
    assert client.post("/api/grafici/serie", json={"testo": "1/n"}).json()["converge"] is False
    geometrica = client.post("/api/grafici/serie", json={"testo": "(1/2)^n", "inizio": 0}).json()
    assert geometrica["converge"] is True and geometrica["somma"] == 2.0

    # Termine non definito nel punto di partenza
    assert client.post("/api/grafici/serie", json={"testo": "1/n", "inizio": 0}).status_code == 422
