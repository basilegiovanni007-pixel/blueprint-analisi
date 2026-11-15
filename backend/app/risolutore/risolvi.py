"""
Il "direttore d'orchestra" del risolutore. Mette in fila le fasi:

1. Calcolo:   il risolutore giusto costruisce i passaggi;
2. Verifica:  SymPy ricalcola il risultato in modo indipendente e lo confrontiamo;
3. Citazioni: per ogni passaggio cerchiamo la fonte nel Magazzino (o mettiamo l'avviso).

Regola d'oro: se i passaggi non portano al risultato di SymPy, NON vengono mostrati.
"""

import sympy

from app.grafici.formule import come_numero, in_js
from app.risolutore.analisi2 import risolvi_critici, risolvi_doppio, risolvi_gradiente, risolvi_vincolati
from app.risolutore.citazioni import Biblioteca
from app.risolutore.concetti import CONCETTI
from app.risolutore.controllo import prepara
from app.risolutore.derivate import risolvi_derivata
from app.risolutore.edo import risolvi_edo
from app.risolutore.serie import risolvi_serie
from app.risolutore.integrali import risolvi_integrale
from app.risolutore.limiti import calcola_limite, risolvi_limite
from app.risolutore.modelli import ErroreRisolutore, L, Problema, Svolgimento
from app.risolutore.verifica import uguali

DESCRIZIONI = {
    "limite": "Limite",
    "derivata": "Derivata",
    "integrale": "Integrale",
    "gradiente": "Gradiente",
    "critici": "Punti critici",
    "vincolati": "Massimi e minimi vincolati",
    "doppio": "Integrale doppio",
    "serie": "Serie numerica",
    "edo": "Equazione differenziale",
}

# Argomento del corso a cui appartiene ogni tipo di esercizio (per il cartiglio e il Magazzino)
ARGOMENTO_DI_TIPO = {
    "limite": "Limiti",
    "derivata": "Derivate",
    "integrale": "Integrali",
    "serie": "Serie",
    "edo": "Equazioni differenziali",
    "gradiente": "Funzioni di più variabili",
    "critici": "Funzioni di più variabili",
    "vincolati": "Funzioni di più variabili",
    "doppio": "Integrali multipli",
}

# Esercizi il cui risolutore verifica da solo il proprio risultato (con un secondo metodo)
ANALISI2 = {
    "gradiente": risolvi_gradiente,
    "critici": risolvi_critici,
    "vincolati": risolvi_vincolati,
    "doppio": risolvi_doppio,
    "serie": risolvi_serie,
    "edo": risolvi_edo,
}


def _verifica(p: Problema, s: Svolgimento) -> tuple[bool, sympy.Expr | None]:
    """Ricalcola il risultato con SymPy. Restituisce (i passaggi sono corretti?, risultato di SymPy)."""
    if p.tipo == "limite":
        riferimento = calcola_limite(p.funzione, p.variabile, p.punto, p.direzione)
        return uguali(s.risultato, riferimento), riferimento

    if p.tipo == "derivata":
        riferimento = sympy.diff(p.funzione, p.variabile, p.ordine)
        return uguali(s.risultato, riferimento), sympy.simplify(riferimento)

    if p.estremo_a is None:
        # Integrale indefinito: una primitiva è giusta se, derivandola, si riottiene la funzione
        corretto = uguali(sympy.diff(s.risultato, p.variabile), p.funzione)
        return corretto, s.risultato if corretto else sympy.integrate(p.funzione, p.variabile)

    riferimento = sympy.integrate(p.funzione, (p.variabile, p.estremo_a, p.estremo_b))
    if riferimento.has(sympy.Integral):
        raise ErroreRisolutore("Non riesco a calcolare questo integrale definito.")
    return uguali(s.risultato, riferimento), riferimento


def _dati_grafico(p: Problema, s: Svolgimento) -> dict | None:
    """Prepara ciò che serve al frontend per disegnare la funzione accanto alla soluzione."""
    try:
        dati = {"tipo": "funzione", "funzione": in_js(p.funzione), "variabile": str(p.variabile), "derivata": None, "punto": None, "area": None}
        if p.tipo == "limite" and p.punto not in (sympy.oo, -sympy.oo):
            dati["punto"] = come_numero(p.punto)  # il punto a cui tende la variabile
        if p.tipo == "derivata" and p.ordine == 1 and s.risultato is not None:
            dati["derivata"] = in_js(s.risultato)  # disegniamo anche la derivata
        if p.tipo == "integrale" and p.estremo_a is not None:
            a, b = come_numero(p.estremo_a), come_numero(p.estremo_b)
            if a is not None and b is not None:
                dati["area"] = [a, b]  # coloriamo l'area tra gli estremi
        return dati
    except Exception:
        return None  # funzione non disegnabile: la soluzione resta valida, semplicemente senza grafico


def risolvi(p: Problema, biblioteca: Biblioteca) -> dict:
    """Risolve il problema e prepara la risposta per il frontend."""
    try:
        if p.tipo in ANALISI2:
            svolgimento = ANALISI2[p.tipo](p)
            if svolgimento.verificato is False:
                # Non abbiamo un secondo risultato sicuro da mostrare al suo posto: meglio fermarsi
                raise ErroreRisolutore(
                    "Ho risolto l'esercizio ma il controllo di verifica non è riuscito, "
                    "quindi preferisco non mostrarti un risultato che potrebbe essere sbagliato."
                )
            verificato, riferimento = True, svolgimento.risultato
        elif p.tipo == "limite":
            svolgimento = risolvi_limite(p, biblioteca.conosce)
            verificato, riferimento = _verifica(p, svolgimento)
        elif p.tipo == "derivata":
            svolgimento = risolvi_derivata(p)
            verificato, riferimento = _verifica(p, svolgimento)
        else:
            svolgimento = risolvi_integrale(p)
            verificato, riferimento = _verifica(p, svolgimento)
    except ErroreRisolutore:
        raise
    except Exception as errore:
        raise ErroreRisolutore(f"Non sono riuscito a risolvere questo esercizio ({type(errore).__name__}).") from errore

    avvisi = list(svolgimento.avvisi)
    passaggi = svolgimento.passaggi
    # verificato = None significa: il controllo indipendente non è stato possibile
    controllo_completo = not (p.tipo in ANALISI2 and svolgimento.verificato is None)
    if not controllo_completo:
        avvisi.append(
            "Per questo esercizio non sono riuscito a fare il controllo indipendente con SymPy: "
            "la conclusione si basa solo sul criterio indicato nei passaggi."
        )

    if not verificato:
        # I nostri passaggi portano a un risultato diverso da quello di SymPy:
        # non li mostriamo e diamo solo il risultato calcolato da SymPy.
        passaggi = []
        svolgimento.risultato, svolgimento.risultato_latex = riferimento, None
        if p.tipo == "integrale" and p.estremo_a is None:
            svolgimento.risultato_latex = rf"{L(riferimento)} + c"
        avvisi.append(
            "I passaggi che avevo costruito non portavano al risultato calcolato da SymPy, quindi non li mostro. "
            "Qui trovi solo il risultato verificato."
        )
    elif not svolgimento.dettagliato:
        avvisi.append("Per questo esercizio non so ancora mostrare tutti i passaggi intermedi: il risultato è comunque verificato da SymPy.")

    if svolgimento.risultato_latex:
        risultato_latex = svolgimento.risultato_latex
    elif svolgimento.risultato is None:
        risultato_latex = r"\text{non esiste}"
    else:
        risultato_latex = L(svolgimento.risultato)

    # --- citazioni dal Magazzino ---
    passaggi_pronti = []
    mancanti: list[str] = []
    for numero, passaggio in enumerate(passaggi, start=1):
        citazione = biblioteca.cita(passaggio.concetto) if passaggio.concetto else None
        manca = passaggio.concetto is not None and citazione is None
        nome = CONCETTI[passaggio.concetto].nome if passaggio.concetto else None
        if manca and nome not in mancanti:
            mancanti.append(nome)
        passaggi_pronti.append(
            {
                "numero": numero,
                "titolo": passaggio.titolo,
                "testo": passaggio.testo,
                "formula": passaggio.formula,
                "concetto": nome,
                "citazione": citazione,
                "mancante": manca,
                # La domanda di "Mettimi alla prova" (la risposta corretta resta nel backend)
                "domanda": passaggio.domanda if passaggio.atteso is not None else None,
            }
        )

    # Risposte corrette per "Mettimi alla prova": vengono salvate nello Storico, non mostrate
    try:
        controlli, controllo_finale = prepara(p, svolgimento, passaggi)
    except Exception:
        controlli, controllo_finale = {"passaggi": [None] * len(passaggi), "finale": None}, None

    return {
        "problema": {
            "tipo": p.tipo,
            "descrizione": DESCRIZIONI[p.tipo],
            "latex": p.latex(),
            "argomento": ARGOMENTO_DI_TIPO[p.tipo],
        },
        "controllo_finale": controllo_finale,
        "_controlli": controlli,  # chiave privata: l'API la toglie prima di rispondere al browser
        "risultato_latex": risultato_latex,
        "risposta_latex": svolgimento.risposta_latex or rf"{p.latex()} = {risultato_latex}",
        "verificato": controllo_completo,  # False = niente timbro "verificato" nell'interfaccia
        "passaggi_verificati": verificato,
        "metodo": svolgimento.metodo,
        "passaggi": passaggi_pronti,
        "concetti_mancanti": mancanti,
        "avvisi": avvisi,
        "grafico": svolgimento.grafico if p.tipo in ANALISI2 else _dati_grafico(p, svolgimento),
    }
