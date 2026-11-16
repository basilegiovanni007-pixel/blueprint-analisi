"""
Test del risolutore con esercizi tipici di Analisi I.

Per ogni esercizio controlliamo che:
- il testo venga capito;
- il risultato sia quello atteso (confrontato in modo matematico, non come testo);
- i passaggi mostrati siano stati verificati con SymPy.
"""

import pytest
import sympy
from sympy import E, cos, exp, log, oo, pi, sin, sqrt, symbols

from app.risolutore.interpreta import interpreta, leggi_espressione
from app.risolutore.modelli import ErroreRisolutore
from app.risolutore.risolvi import risolvi
from app.risolutore.verifica import uguali

x = symbols("x")


class MagazzinoVuoto:
    """Finto Magazzino senza documenti: nessun concetto è conosciuto."""

    def cita(self, chiave):
        return None

    def conosce(self, chiave):
        return False


class MagazzinoCon(MagazzinoVuoto):
    """Finto Magazzino che conosce solo i concetti indicati."""

    def __init__(self, *chiavi):
        self.chiavi = chiavi

    def cita(self, chiave):
        if chiave in self.chiavi:
            return {"documento": "appunti", "fonte": "Appunti miei", "pagina": 1}
        return None

    def conosce(self, chiave):
        return chiave in self.chiavi


def soluzione(testo, magazzino=None, tipo="auto"):
    return risolvi(interpreta(testo, tipo), magazzino or MagazzinoVuoto())


def valore(testo, **argomenti):
    """Risolve e restituisce il risultato come espressione SymPy (None = non esiste)."""
    problema = interpreta(testo)
    risposta = risolvi(problema, MagazzinoVuoto())
    assert risposta["passaggi_verificati"], f"passaggi non verificati per: {testo}"
    assert risposta["passaggi"], f"nessun passaggio per: {testo}"
    return risposta


# ---------- lettura delle formule ----------


@pytest.mark.parametrize(
    "scritta, attesa",
    [
        ("x^2 + 3x", x**2 + 3 * x),
        ("2x sin(x)", 2 * x * sin(x)),
        ("sen(x)/x", sin(x) / x),
        ("e^(2x)", exp(2 * x)),
        ("ln(x) + radq(x)", log(x) + sqrt(x)),
        (r"\frac{\sin x}{x}", sin(x) / x),
        (r"\sqrt{x^2+1}", sqrt(x**2 + 1)),
        (r"x^{3} \cdot e^{-x}", x**3 * exp(-x)),
        ("(x²−1)·π", (x**2 - 1) * pi),
    ],
)
def test_lettura_formule(scritta, attesa):
    assert uguali(leggi_espressione(scritta), attesa)


@pytest.mark.parametrize("pericolosa", ["__import__('os')", "x; print(1)", "open('a')", "xsin(x)", "", "x +* 2"])
def test_formule_non_valide_rifiutate(pericolosa):
    with pytest.raises(ErroreRisolutore):
        leggi_espressione(pericolosa)


# ---------- interpretazione delle frasi ----------


def test_interpretazione_limite():
    p = interpreta("Calcola il limite per x che tende a 0 di sin(x)/x.")
    assert (p.tipo, p.punto, p.direzione) == ("limite", 0, "+-")
    assert uguali(p.funzione, sin(x) / x)

    assert interpreta("limite di 1/x per x che tende a più infinito").punto == oo
    assert interpreta("lim x->0+ ln(x)").direzione == "+"
    assert interpreta(r"\lim_{x \to -\infty} e^{x}").punto == -oo
    assert interpreta(r"\lim_{x \to 0^{-}} \frac{1}{x}").direzione == "-"


def test_interpretazione_derivata_e_integrale():
    p = interpreta("derivata seconda di x^3")
    assert (p.tipo, p.ordine) == ("derivata", 2)

    p = interpreta("integrale da 0 a pi di sin(x) dx")
    assert (p.tipo, p.estremo_a, p.estremo_b) == ("integrale", 0, pi)

    p = interpreta(r"\int_{1}^{2} \frac{1}{t} \, dt")
    assert (str(p.variabile), p.estremo_a, p.estremo_b) == ("t", 1, 2)

    # Tipo scelto dal menu: il testo è la sola formula
    assert interpreta("x^2 * e^x", "derivata").tipo == "derivata"
    assert interpreta("x^2 * e^x", "integrale").tipo == "integrale"


def test_messaggi_di_errore_chiari():
    with pytest.raises(ErroreRisolutore, match="Non ho capito"):
        interpreta("x^2 + 1")
    with pytest.raises(ErroreRisolutore, match="altre lettere"):
        interpreta("derivata di a*x^2")
    with pytest.raises(ErroreRisolutore, match="Scrivi un esercizio"):
        interpreta("   ")


# ---------- limiti ----------


@pytest.mark.parametrize(
    "testo, atteso",
    [
        ("limite per x che tende a 0 di sin(x)/x", 1),  # limite notevole
        ("limite per x->0 di (1-cos(x))/x^2", sympy.Rational(1, 2)),  # limite notevole
        ("limite per x->0 di (e^x-1)/x", 1),  # limite notevole
        ("limite per x->0 di ln(1+x)/x", 1),  # limite notevole
        ("lim x->1 (x^2-1)/(x-1)", 2),  # scomposizione
        ("lim x->+oo (3x^2+1)/(x^2-x)", 3),  # confronto dei gradi
        ("lim x->+oo x/e^x", 0),  # de l'Hopital, forma inf/inf
        ("limite per x->2 di x^2+1", 5),  # sostituzione diretta
        ("lim x->0+ 1/x", oo),  # denominatore che tende a zero
        ("lim x->+oo (1+1/x)^x", E),  # numero di Nepero (senza passaggi dettagliati)
    ],
)
def test_limiti(testo, atteso):
    risposta = soluzione(testo)
    assert risposta["passaggi_verificati"]
    assert risposta["risultato_latex"] == sympy.latex(sympy.sympify(atteso), ln_notation=True)


def test_limite_che_non_esiste():
    risposta = soluzione("limite di 1/x per x che tende a 0")
    assert risposta["risultato_latex"] == r"\text{non esiste}"
    assert any("destro e sinistro" in p["testo"] for p in risposta["passaggi"])


def test_limite_sceglie_il_metodo_che_lo_studente_conosce():
    testo = "limite per x che tende a 0 di sin(x)/x"

    # Magazzino vuoto: usa de l'Hôpital e segnala che manca
    vuoto = soluzione(testo)
    assert "Hôpital" in vuoto["metodo"]
    assert "teorema di de l'Hôpital" in vuoto["concetti_mancanti"]
    assert any(p["mancante"] for p in vuoto["passaggi"])

    # Lo studente conosce solo i limiti notevoli: strada alternativa, con spiegazione
    notevoli = soluzione(testo, MagazzinoCon("asintotico", "forma_indeterminata"))
    assert "limiti notevoli" in notevoli["metodo"]
    assert any("strada alternativa" in avviso for avviso in notevoli["avvisi"])
    assert notevoli["concetti_mancanti"] == []
    assert all(p["citazione"] for p in notevoli["passaggi"] if p["concetto"])

    # Lo studente conosce de l'Hôpital: lo usa e lo cita
    hopital = soluzione(testo, MagazzinoCon("hopital", "forma_indeterminata", "continuita"))
    assert "Hôpital" in hopital["metodo"]
    assert hopital["concetti_mancanti"] == []


# ---------- derivate ----------


@pytest.mark.parametrize(
    "testo, attesa, regola",
    [
        ("derivata di x^2*sin(x)", 2 * x * sin(x) + x**2 * cos(x), "derivata del prodotto"),
        ("derivata di sin(x)/x", (x * cos(x) - sin(x)) / x**2, "derivata del quoziente"),
        ("derivata di e^(x^2)", 2 * x * exp(x**2), "derivata della funzione composta"),
        ("derivata di ln(cos(x))", -sin(x) / cos(x), "derivata della funzione composta"),
        ("derivata di sqrt(x^2+1)", x / sqrt(x**2 + 1), "derivata della funzione composta"),
        ("derivata di x^3 - 5x + 7", 3 * x**2 - 5, "linearità della derivata"),
        ("derivata seconda di x^3 + 2x", 6 * x, "derivate delle funzioni elementari"),
        ("derivata di x^x", x**x * (log(x) + 1), "derivata della funzione composta"),
    ],
)
def test_derivate(testo, attesa, regola):
    problema = interpreta(testo)
    risposta = risolvi(problema, MagazzinoVuoto())
    assert risposta["passaggi_verificati"]
    assert regola in [p["concetto"] for p in risposta["passaggi"]], "la regola attesa non compare nei passaggi"
    # Il risultato atteso coincide con la derivata calcolata da SymPy (controllo dei dati del test)
    assert uguali(sympy.diff(problema.funzione, x, problema.ordine), attesa)


# ---------- integrali ----------


@pytest.mark.parametrize(
    "testo, regola",
    [
        ("integrale di x*e^x dx", "integrazione per parti"),
        ("integrale di ln(x)", "integrazione per parti"),
        ("integrale di e^x*sin(x)", "integrazione per parti"),  # per parti due volte
        ("integrale di 2x*cos(x^2) dx", "integrazione per sostituzione"),
        ("integrale di x/(x^2+1)", "integrazione per sostituzione"),
        ("integrale di sin(x)^2", "riscrittura dell'integranda"),
        ("integrale di x^3 + 2x - 1", "linearità dell'integrale"),
        ("integrale di 1/(x^2+1)", "integrali immediati"),
    ],
)
def test_integrali_indefiniti(testo, regola):
    problema = interpreta(testo)
    risposta = risolvi(problema, MagazzinoVuoto())
    assert risposta["passaggi_verificati"]
    assert risposta["risultato_latex"].endswith("+ c")
    assert regola in [p["concetto"] for p in risposta["passaggi"]]


@pytest.mark.parametrize(
    "testo, atteso",
    [
        ("integrale da 0 a 1 di x^2 dx", sympy.Rational(1, 3)),
        ("integrale tra 0 e pi di sin(x) dx", 2),
        ("integrale da 1 a e di ln(x)", 1),
        ("integrale da 0 a 1 di x*e^x", 1),
        ("integrale da 1 a +infinito di 1/x^2", 1),  # integrale improprio
    ],
)
def test_integrali_definiti(testo, atteso):
    risposta = soluzione(testo)
    assert risposta["passaggi_verificati"]
    assert risposta["risultato_latex"] == sympy.latex(sympy.sympify(atteso))
    assert risposta["passaggi"][-1]["concetto"] == "teorema fondamentale del calcolo integrale"


def test_integrale_non_elementare_dichiarato():
    risposta = soluzione("integrale di e^(-x^2)")
    assert any("non si può scrivere con le funzioni elementari" in p["testo"] for p in risposta["passaggi"])


# ---------- attraverso il server, con un Magazzino vero ----------

APPUNTI = """Teorema (di de l'Hopital). Se il limite di f/g è una forma indeterminata 0/0,
allora coincide con il limite di f'/g'.

Definizione. Le forme indeterminate sono 0/0 e infinito/infinito.

Metodo. Integrazione per parti: l'integrale di f g' è f g meno l'integrale di f' g.
"""


def test_risolutore_dal_server_con_citazioni(client):
    documento = client.post(
        "/api/magazzino/documenti",
        files={"file": ("appunti.txt", APPUNTI.encode())},
        data={"argomento": "Limiti", "fonte": "Appunti miei", "data": "2026-11-01"},
    ).json()

    risposta = client.post("/api/risolutore/risolvi", json={"testo": "limite per x->0 di sin(x)/x"})
    assert risposta.status_code == 200, risposta.text
    passaggi = risposta.json()["passaggi"]
    hopital = next(p for p in passaggi if p["concetto"] == "teorema di de l'Hôpital")
    assert hopital["citazione"]["documento"] == "appunti"
    assert hopital["citazione"]["tipo"] == "teorema"
    assert not hopital["mancante"]

    # La regola del prodotto non è negli appunti: deve comparire l'avviso
    risposta = client.post("/api/risolutore/risolvi", json={"testo": "derivata di x*sin(x)"}).json()
    assert "derivata del prodotto" in risposta["concetti_mancanti"]

    # Documento disattivato: le citazioni spariscono
    client.patch(f"/api/magazzino/documenti/{documento['id']}", json={"attivo": False})
    risposta = client.post("/api/risolutore/risolvi", json={"testo": "limite per x->0 di sin(x)/x"}).json()
    assert all(p["citazione"] is None for p in risposta["passaggi"])

    client.delete(f"/api/magazzino/documenti/{documento['id']}")

    # Errori spiegati
    risposta = client.post("/api/risolutore/risolvi", json={"testo": "ciao come stai"})
    assert risposta.status_code == 422
    assert "Non ho capito" in risposta.json()["detail"]


FOGLIO = """Foglio di esercizi n. 3

Esercizio 1. Calcolare il limite per x che tende a 0 di sin(x)/x.

Esercizio 2. Calcolare la derivata di x^2*sin(x).

Esercizio 3. Calcolare l'integrale di x*e^x dx.
"""


def test_esercizi_da_file(client):
    risposta = client.post("/api/risolutore/da-file", files={"file": ("foglio.txt", FOGLIO.encode())})
    assert risposta.status_code == 200, risposta.text
    esercizi = risposta.json()["esercizi"]
    assert [e["numero"] for e in esercizi] == [1, 2, 3]

    # Ogni esercizio letto dal file si può passare direttamente al risolutore
    tipi = []
    for esercizio in esercizi:
        soluzione = client.post("/api/risolutore/risolvi", json={"testo": esercizio["testo"]})
        assert soluzione.status_code == 200, soluzione.text
        tipi.append(soluzione.json()["problema"]["tipo"])
    assert tipi == ["limite", "derivata", "integrale"]

    # Elenco numerato "1) 2)" e file senza intestazioni
    numerato = client.post("/api/risolutore/da-file", files={"file": ("a.md", b"1) derivata di x^2\n2) integrale di x\n")}).json()
    assert len(numerato["esercizi"]) == 2
    singolo = client.post("/api/risolutore/da-file", files={"file": ("b.txt", b"derivata di x^3")}).json()
    assert singolo["esercizi"] == [{"numero": 1, "testo": "derivata di x^3"}]

    # Foto e formati sconosciuti: errore chiaro
    # Foto rovinata: errore chiaro (le foto vere sono provate in test_ocr.py)
    assert client.post("/api/risolutore/da-file", files={"file": ("foto.png", b"\x89PNG")}).status_code == 422
    assert client.post("/api/risolutore/da-file", files={"file": ("x.zip", b"PK")}).status_code == 415
