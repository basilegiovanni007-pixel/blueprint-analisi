"""Test degli esercizi di Analisi II: gradiente, punti critici, massimi e minimi vincolati, integrali doppi."""

import math

import pytest
import sympy
from sympy import symbols

from app.risolutore.interpreta import interpreta
from app.risolutore.modelli import ErroreRisolutore
from app.risolutore.risolvi import risolvi

x, y = symbols("x y")


class MagazzinoVuoto:
    def cita(self, chiave):
        return None

    def conosce(self, chiave):
        return False


def soluzione(testo, tipo="auto"):
    risposta = risolvi(interpreta(testo, tipo), MagazzinoVuoto())
    assert risposta["passaggi_verificati"]
    assert risposta["passaggi"], "nessun passaggio"
    return risposta


def punti(risposta):
    """I punti notevoli del grafico, come terne arrotondate (x, y, tipo)."""
    return sorted((round(p["x"], 4), round(p["y"], 4), p["tipo"]) for p in risposta["grafico"]["punti"])


# ---------- interpretazione ----------


def test_interpretazione_analisi2():
    p = interpreta("calcola il gradiente di f(x,y) = x^2*y + sin(x*y)")
    assert (p.tipo, p.variabili) == ("gradiente", (x, y))
    assert interpreta("derivate parziali di x*e^y").tipo == "gradiente"

    assert interpreta("trova i punti critici di x^3 + y^3 - 3*x*y").tipo == "critici"
    assert interpreta("massimi e minimi di f(x,y) = x^2 + y^2 - 2x").tipo == "critici"

    p = interpreta("massimi e minimi di x*y con vincolo x^2 + y^2 = 1")
    assert p.tipo == "vincolati"
    assert sympy.simplify(p.vincolo - (x**2 + y**2 - 1)) == 0

    p = interpreta("integrale doppio di x*y con x da 0 a 1 e y da 0 a x")
    assert (p.tipo, p.variabile, p.interna, p.interno_b) == ("doppio", x, y, x)
    p = interpreta("integrale doppio di x + y su [0,1]x[0,2]")
    assert (p.estremo_a, p.estremo_b, p.interno_a, p.interno_b) == (0, 1, 0, 2)
    # Dominio normale rispetto all'asse y: la variabile esterna diventa y
    p = interpreta("integrale doppio di x con y da 0 a 2 e x da 0 a y")
    assert (p.variabile, p.interna) == (y, x)

    # Il tipo scelto dal menu basta, se il testo è la sola formula
    assert interpreta("x^2 - y^2", "critici").tipo == "critici"
    assert interpreta("x^2 * y", "gradiente").tipo == "gradiente"


def test_errori_analisi2():
    with pytest.raises(ErroreRisolutore, match="Studio di funzione"):
        interpreta("massimi e minimi di x^3 - 3x")
    with pytest.raises(ErroreRisolutore, match="estremi di entrambe"):
        interpreta("integrale doppio di x*y con x da 0 a 1")
    with pytest.raises(ErroreRisolutore, match="Manca il vincolo"):
        interpreta("x*y", "vincolati")
    with pytest.raises(ErroreRisolutore, match="infiniti punti critici"):
        soluzione("punti critici di (x - y)^2")


# ---------- gradiente ----------


def test_gradiente():
    risposta = soluzione("gradiente di x^2*y + y^3")
    assert risposta["risposta_latex"] == r"\nabla f = \left(2 x y,\ x^{2} + 3 y^{2}\right)"
    concetti = [p["concetto"] for p in risposta["passaggi"]]
    assert concetti == ["derivate parziali", "derivate parziali", "gradiente"]
    assert risposta["grafico"]["tipo"] == "superficie"

    # Tre variabili: funziona, ma senza grafico
    tre = soluzione("gradiente di x*y*z")
    assert tre["grafico"] is None and len(tre["passaggi"]) == 4


# ---------- punti critici ----------


@pytest.mark.parametrize(
    "funzione, attesi",
    [
        ("x^2 + y^2", [(0, 0, "minimo")]),
        ("-x^2 - y^2 + 4", [(0, 0, "massimo")]),
        ("x^2 - y^2", [(0, 0, "sella")]),
        ("x^3 + y^3 - 3*x*y", [(0, 0, "sella"), (1, 1, "minimo")]),
        ("x^3 - 3x + y^2", [(-1, 0, "sella"), (1, 0, "minimo")]),
        ("x^4 + y^4", [(0, 0, "dubbio")]),
        ("x*y*(1 - x - y)", [(0, 0, "sella"), (0, 1, "sella"), (0.3333, 0.3333, "massimo"), (1, 0, "sella")]),
    ],
)
def test_punti_critici(funzione, attesi):
    risposta = soluzione(f"punti critici di {funzione}")
    assert punti(risposta) == sorted(attesi)
    assert "matrice hessiana e classificazione dei punti critici" in [p["concetto"] for p in risposta["passaggi"]]


def test_nessun_punto_critico():
    risposta = soluzione("punti critici di x + y")
    assert "non ha punti critici" in risposta["risposta_latex"]


# ---------- massimi e minimi vincolati ----------


def test_vincolati_su_circonferenza():
    risposta = soluzione("massimi e minimi di x*y con vincolo x^2 + y^2 = 1")
    assert r"\max f = \frac{1}{2}" in risposta["risposta_latex"]
    assert r"\min f = - \frac{1}{2}" in risposta["risposta_latex"]
    tipi = [p[2] for p in punti(risposta)]
    assert tipi.count("massimo") == 2 and tipi.count("minimo") == 2
    assert risposta["grafico"]["vincolo"] == "x^2 + y^2 - 1"
    concetti = [p["concetto"] for p in risposta["passaggi"]]
    assert "moltiplicatori di Lagrange" in concetti and "teorema di Weierstrass" in concetti


def test_vincolati_funzione_lineare_ed_ellisse():
    risposta = soluzione("massimo e minimo di x + y soggetta a x^2 + y^2 = 1")
    r2 = round(math.sqrt(2) / 2, 4)
    assert punti(risposta) == [(-r2, -r2, "minimo"), (r2, r2, "massimo")]

    ellisse = soluzione("massimi e minimi di x^2 + y^2 con vincolo x^2/4 + y^2 = 1")
    assert r"\max f = 4" in ellisse["risposta_latex"] and r"\min f = 1" in ellisse["risposta_latex"]


def test_vincolo_illimitato_non_promette_massimi_assoluti():
    # Sulla retta x + y = 2 il prodotto x*y ha un massimo ma nessun minimo
    risposta = soluzione("massimi e minimi di x*y con vincolo x + y = 2")
    assert punti(risposta) == [(1, 1, "massimo")]
    assert "massimo vincolato relativo" in risposta["risposta_latex"]
    assert r"\min" not in risposta["risposta_latex"]
    assert any("non è una curva chiusa e limitata" in p["testo"] for p in risposta["passaggi"])


# ---------- integrali doppi ----------


@pytest.mark.parametrize(
    "testo, atteso",
    [
        ("integrale doppio di x*y su [0,1]x[0,2]", 1),
        ("integrale doppio di x*y con x da 0 a 1 e y da 0 a x", sympy.Rational(1, 8)),
        ("integrale doppio di x + y con x da 0 a 1 e y da x^2 a x", sympy.Rational(3, 20)),
        ("integrale doppio di 1 con x da 0 a 2 e y da 0 a x", 2),  # area di un triangolo
        ("integrale doppio di x con y da 0 a 2 e x da 0 a y", sympy.Rational(4, 3)),
        ("integrale doppio di y*sin(x) con 0 <= x <= pi e 0 <= y <= 1", 1),
    ],
)
def test_integrali_doppi(testo, atteso):
    risposta = soluzione(testo)
    assert risposta["risultato_latex"] == sympy.latex(sympy.sympify(atteso))
    assert risposta["passaggi"][0]["concetto"] == "integrali doppi e formule di riduzione"
    assert risposta["grafico"]["dominio"] is not None


# ---------- attraverso il server ----------


def test_analisi2_dal_server(client):
    risposta = client.post("/api/risolutore/risolvi", json={"testo": "punti critici di x^3 + y^3 - 3*x*y"})
    assert risposta.status_code == 200, risposta.text
    dati = risposta.json()
    assert dati["problema"]["descrizione"] == "Punti critici"
    assert dati["grafico"]["finestra"]["xmin"] < 0 < 1 < dati["grafico"]["finestra"]["xmax"]

    # Scelta dal menu
    risposta = client.post("/api/risolutore/risolvi", json={"testo": "x^2 * y", "tipo": "gradiente"})
    assert risposta.status_code == 200

    # La superficie per la pagina Grafici
    superficie = client.post("/api/grafici/superficie", json={"testo": "x^2 - y^2"}).json()
    assert superficie["js"] == "x^2 - y^2"
    assert superficie["punti"] == [{"x": 0.0, "y": 0.0, "z": 0.0, "tipo": "sella"}]
    assert client.post("/api/grafici/superficie", json={"testo": "x^2"}).status_code == 422
