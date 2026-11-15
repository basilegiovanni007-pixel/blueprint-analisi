"""Test delle serie numeriche e delle equazioni differenziali."""

import pytest
import sympy
from sympy import Symbol, cos, exp, sin, sqrt, symbols

from app.risolutore.edo import risolvi_edo
from app.risolutore.interpreta import interpreta
from app.risolutore.modelli import ErroreRisolutore
from app.risolutore.risolvi import risolvi
from app.risolutore.verifica import uguali

x, c1, c2 = symbols("x c_1 c_2")
n = Symbol("n")


class MagazzinoVuoto:
    def cita(self, chiave):
        return None

    def conosce(self, chiave):
        return False


def soluzione(testo, tipo="auto"):
    risposta = risolvi(interpreta(testo, tipo), MagazzinoVuoto())
    assert risposta["passaggi"], "nessun passaggio"
    return risposta


def criteri(risposta):
    return [p["concetto"] for p in risposta["passaggi"] if p["concetto"]]


# ---------- serie: interpretazione ----------


def test_interpretazione_serie():
    p = interpreta("studia il carattere della serie di termine generale 1/n^2")
    assert (p.tipo, p.funzione, p.estremo_a) == ("serie", 1 / n**2, 1)
    p = interpreta(r"\sum_{n=2}^{\infty} \frac{1}{n \ln n}")
    assert (p.tipo, p.estremo_a) == ("serie", 2)
    assert interpreta("serie di termine 1/n per n da 3 a +infinito").estremo_a == 3
    # Il punto esclamativo è il fattoriale, non punteggiatura
    assert interpreta("serie di termine 1/n!").funzione == 1 / sympy.factorial(n)
    # Dal menu basta il termine generale
    assert interpreta("1/n^3", "serie").tipo == "serie"
    with pytest.raises(ErroreRisolutore, match="in funzione di n"):
        interpreta("serie di termine 1/k^2")


# ---------- serie: criteri ----------


@pytest.mark.parametrize(
    "termine, esito, criterio",
    [
        ("1/n^2", "converge", "serie armonica generalizzata"),
        ("1/n", "diverge", "serie armonica generalizzata"),
        ("1/sqrt(n)", "diverge", "serie armonica generalizzata"),
        ("(1/2)^n", "converge", "serie geometrica"),
        ("3/4^n", "converge", "serie geometrica"),
        ("(3/2)^n", "diverge", "condizione necessaria di convergenza"),
        ("n/(n+1)", "diverge", "condizione necessaria di convergenza"),
        ("1/n!", "converge", "criterio del rapporto"),
        ("n^2/3^n", "converge", "criterio del rapporto"),
        ("2^n/n!", "converge", "criterio del rapporto"),
        ("1/(n^2+1)", "converge", "criterio del confronto asintotico"),
        ("(n+1)/(n^3+2)", "converge", "criterio del confronto asintotico"),
        ("(2n+1)/(n^2+3)", "diverge", "criterio del confronto asintotico"),
        ("(-1)^n/n^2", "converge assolutamente", "convergenza assoluta"),
        ("(-1)^n/n", "converge semplicemente (non assolutamente)", "criterio di Leibniz"),
        ("(-1)^n", "non converge", "condizione necessaria di convergenza"),
    ],
)
def test_carattere_delle_serie(termine, esito, criterio):
    risposta = soluzione(f"serie di termine {termine}")
    assert risposta["risultato_latex"] == rf"\text{{{esito}}}"
    assert criterio in criteri(risposta)
    assert risposta["verificato"], "la conclusione non è stata confermata da SymPy"


def test_serie_con_somma_e_senza_criterio():
    risposta = soluzione("serie di termine 1/n^2")
    assert r"\text{somma} = \frac{\pi^{2}}{6}" in risposta["risposta_latex"]
    assert soluzione("serie (1/2)^n")["risposta_latex"].endswith(r"\text{somma} = 1")

    # Serie per cui nessuno dei criteri previsti basta: lo si dice, senza inventare passaggi
    difficile = soluzione("serie di termine 1/(n*ln(n)) per n da 2 a +oo")
    assert difficile["risultato_latex"] == r"\text{non converge}"
    assert any("non so ancora mostrare" in avviso for avviso in difficile["avvisi"])


# ---------- equazioni differenziali: interpretazione ----------


def test_interpretazione_edo():
    p = interpreta("risolvi l'equazione differenziale y' + 2y = e^x")
    assert (p.tipo, p.condizioni) == ("edo", ())
    assert p.equazione_latex == "y' + 2 y = e^{x}"

    p = interpreta("problema di Cauchy y'' + 4y = 0 con y(0) = 1 e y'(0) = 2")
    assert p.condizioni == ((0, 0, 1), (1, 0, 2))
    assert "\\begin{cases}" in p.latex()

    assert interpreta("dy/dx = x*y").tipo == "edo"
    assert interpreta("y'(x) = y(x)").equazione_latex == "y' = y"
    assert str(interpreta("dy/dt = -2y").variabile) == "t"

    with pytest.raises(ErroreRisolutore, match="un solo segno di uguale"):
        interpreta("equazione differenziale y' + y")
    with pytest.raises(ErroreRisolutore, match="possono comparire solo"):
        interpreta("y' = k*y")
    with pytest.raises(ErroreRisolutore, match="ne servono due"):
        soluzione("y'' + y = 0, y(0) = 1")


# ---------- equazioni differenziali: soluzioni ----------


@pytest.mark.parametrize(
    "testo, attesa, metodo",
    [
        ("y' = x*y", c1 * exp(x**2 / 2), "variabili separabili"),
        ("y' = 2x", x**2 + c1, "integrazione diretta"),
        ("y' + 2y = e^x", c1 * exp(-2 * x) + exp(x) / 3, "equazione lineare del primo ordine"),
        ("y' - y/x = x^2", c1 * x + x**3 / 2, "equazione lineare del primo ordine"),
        ("y'' - 3y' + 2y = 0", c1 * exp(x) + c2 * exp(2 * x), "equazione caratteristica"),
        ("y'' + 2y' + y = 0", (c1 + c2 * x) * exp(-x), "equazione caratteristica"),
        ("y'' + y = 0", c1 * cos(x) + c2 * sin(x), "equazione caratteristica"),
        ("y'' + 2y' + 5y = 0", exp(-x) * (c1 * cos(2 * x) + c2 * sin(2 * x)), "equazione caratteristica"),
        ("y'' - y = x", c1 * exp(-x) + c2 * exp(x) - x, "omogenea associata più soluzione particolare"),
        ("y'' + y' - 2y = e^(3x)", c1 * exp(-2 * x) + c2 * exp(x) + exp(3 * x) / 10, "omogenea associata più soluzione particolare"),
    ],
)
def test_soluzione_generale(testo, attesa, metodo):
    problema = interpreta(testo)
    # La soluzione trovata deve coincidere, come espressione matematica, con quella attesa
    assert uguali(risolvi_edo(problema).risultato, attesa)
    risposta = risolvi(problema, MagazzinoVuoto())
    assert risposta["metodo"] == metodo
    assert risposta["verificato"]
    # Le curve della famiglia di soluzioni, per il grafico
    assert risposta["grafico"]["tipo"] == "funzione" and len(risposta["grafico"]["altre"]) >= 3


@pytest.mark.parametrize(
    "testo, attesa",
    [
        ("y' = y, y(0) = 2", r"2 e^{x}"),
        ("problema di Cauchy y' = x/y con y(0) = 1", r"\sqrt{x^{2} + 1}"),  # va scelto il ramo positivo
        ("y' = x/y, y(0) = -1", r"- \sqrt{x^{2} + 1}"),  # e qui quello negativo
        ("y' + y = 1, y(0) = 0", r"1 - e^{- x}"),
        ("y'' + 4y = 0, y(0) = 1, y'(0) = 2", r"\sin{\left(2 x \right)} + \cos{\left(2 x \right)}"),
        ("y'' - y = 0, y(0) = 1, y'(0) = 1", r"e^{x}"),
    ],
)
def test_problema_di_cauchy(testo, attesa):
    risposta = soluzione(testo)
    assert risposta["risposta_latex"] == f"y(x) = {attesa}"
    assert "problema di Cauchy" in criteri(risposta)
    assert risposta["grafico"]["altre"] == []  # una sola curva: la soluzione del problema


def test_edo_non_risolvibile_o_senza_passaggi():
    with pytest.raises(ErroreRisolutore, match="forma esplicita"):
        soluzione("y' = sin(x*y)")
    # Equazione che SymPy sa risolvere ma di cui non sappiamo spiegare i passaggi
    senza_passaggi = soluzione("y'' + x*y = 0")
    assert any("non so ancora mostrare" in avviso for avviso in senza_passaggi["avvisi"])


def test_serie_ed_edo_dal_server(client):
    risposta = client.post("/api/risolutore/risolvi", json={"testo": "serie di termine 1/n^2"})
    assert risposta.status_code == 200, risposta.text
    assert risposta.json()["problema"]["descrizione"] == "Serie numerica"

    risposta = client.post("/api/risolutore/risolvi", json={"testo": "y'' + y = 0"})
    assert risposta.status_code == 200, risposta.text
    assert risposta.json()["problema"]["descrizione"] == "Equazione differenziale"

    assert client.post("/api/risolutore/risolvi", json={"testo": "x^2", "tipo": "edo"}).status_code == 422
