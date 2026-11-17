"""
Riconoscimento automatico degli argomenti (Limiti, Derivate, Serie...) dei blocchi del Magazzino.

Usiamo due tipi di indizi, perché nelle prove nessuno dei due da solo bastava:
1. il SIGNIFICATO: il testo del blocco viene confrontato (con lo stesso modello della ricerca)
   con una descrizione di ogni argomento. Funziona bene su testo pulito, ma negli appunti
   scritti a mano le formule lette male lo confondono;
2. le PAROLE CHIAVE e la NOTAZIONE: "convessa", "gradiente", "Cauchy"..., ma anche f'(x)
   (derivate), ∫ (integrali), ∂ (più variabili), y'' (equazioni differenziali).

In più conta il CONTESTO: un blocco senza nessun indizio (una pagina di sole formule, o
con le parole storpiate dall'OCR) prende l'argomento del documento a cui appartiene, e nei
casi in bilico (de l'Hôpital sta sia nei limiti sia nelle derivate) il documento fa da arbitro.

Nelle prove (frasi di tutti gli argomenti, appunti al computer e una lezione scritta a mano)
nessuno dei due indizi da solo superava il 75% di risposte giuste; insieme al contesto
del documento sono state tutte corrette. Su appunti diversi qualche errore ci sarà:
per questo lo studente può sempre correggere l'argomento di un blocco.
"""

import re
import unicodedata
from dataclasses import dataclass

import numpy as np
from sqlmodel import Session, select

from app import config
from app.db.modelli import Blocco, Documento, Esercizio
from app.magazzino.indice import indice

# Una descrizione per ogni argomento: il suo "significato" viene confrontato con quello dei blocchi
DESCRIZIONI: dict[str, str] = {
    "Limiti": "Limiti di funzioni e successioni, continuità, forme indeterminate, limiti notevoli, asintoti, infinitesimi e infiniti.",
    "Derivate": "Derivate e calcolo differenziale in una variabile: retta tangente, regole di derivazione, teoremi di Rolle, Lagrange e de l'Hôpital, monotonia, massimi e minimi, convessità, flessi, studio di funzione, polinomio di Taylor.",
    "Integrali": "Integrali di funzioni di una variabile: primitive, integrale definito e area, teorema fondamentale del calcolo, integrazione per parti e per sostituzione, integrali impropri.",
    "Serie": "Serie numeriche: somme parziali, convergenza e divergenza, serie geometrica e armonica, criteri del confronto, del rapporto, della radice, di Leibniz.",
    "Equazioni differenziali": "Equazioni differenziali ordinarie: primo ordine a variabili separabili e lineari, secondo ordine a coefficienti costanti, equazione caratteristica, problema di Cauchy.",
    "Funzioni di più variabili": "Funzioni di più variabili: derivate parziali, gradiente, differenziabilità, curve di livello, matrice hessiana, punti critici, massimi e minimi vincolati, moltiplicatori di Lagrange.",
    "Integrali multipli": "Integrali doppi e tripli: domini normali, formule di riduzione, teorema di Fubini, cambio di variabili, coordinate polari, cilindriche e sferiche, jacobiano.",
    "Integrali curvilinei": "Curve e integrali curvilinei: lunghezza di una curva, lavoro di un campo vettoriale, forme differenziali, campi conservativi e potenziale, formula di Gauss-Green.",
    "Integrali di superficie": "Superfici parametriche e integrali di superficie: area di una superficie, flusso di un campo, teorema della divergenza, teorema di Stokes, rotore.",
}  # fmt: skip

# Parole chiave (minuscole, senza accenti; bastano le radici: "convess" vale per convessa e convesse)
PAROLE: dict[str, list[str]] = {
    "Limiti": ["limit", "lim ", "tende a", "continu", "forma indeterminata", "forme indeterminate", "infinitesim", "asintot", "notevol"],
    "Derivate": ["deriv", "tangent", "rolle", "lagrange", "monoton", "crescent", "decrescent", "massim", "minim", "convess", "concav", "fless", "taylor", "stazionar"],
    "Integrali": ["integral", "primitiv", "riemann", "per parti", "sostituzion", "area"],
    "Serie": ["serie", "somme parziali", "somma parziale", "criterio del rapporto", "criterio della radice", "armonic", "geometric", "leibniz"],
    "Equazioni differenziali": ["equazion differenzial", "equazioni differenzial", "cauchy", "omogene", "caratteristic", "variabili separabili"],
    "Funzioni di più variabili": ["gradient", "derivate parziali", "derivata parziale", "hessian", "punti critici", "punto critico", "curve di livello", "piu variabili", "due variabili", "moltiplicator"],
    "Integrali multipli": ["integrale doppio", "integrali doppi", "integrale triplo", "integrali tripli", "fubini", "riduzione", "dominio normale", "domini normali", "coordinate polari", "jacobian"],
    "Integrali curvilinei": ["curvilin", "lungo la curva", "lavoro", "conservativ", "potenziale", "green", "circuitazion", "forma differenziale", "forme differenziali"],
    "Integrali di superficie": ["superfici", "flusso", "divergenza", "stokes", "rotore"],
}  # fmt: skip

# Notazione matematica tipica di ogni argomento (espressioni regolari sul testo originale)
NOTAZIONE: dict[str, list[str]] = {
    "Derivate": [r"[a-z]\s*'+\s*\(", r"[a-z]\s*\"\s*\(", r"d\s*/\s*dx", r"\bderw", r"\bderiv"],
    "Integrali": [r"∫", r"\bdx\b"],
    "Serie": [r"Σ|∑", r"\ba_?n\b"],
    "Limiti": [r"\blim\b", r"→\s*[0-9∞+-]"],
    "Equazioni differenziali": [r"\by\s*'+(?!\s*\()", r"\by\s*''"],
    "Funzioni di più variabili": [r"∂", r"∇", r"f\s*\(\s*x\s*,\s*y\s*\)"],
    "Integrali multipli": [r"∬|∭", r"dx\s*dy|dy\s*dx"],
    "Integrali curvilinei": [r"∮"],
    "Integrali di superficie": [r"\bdS\b|dσ"],
}  # fmt: skip

ARGOMENTI: list[str] = [a for argomenti in config.ARGOMENTI.values() for a in argomenti]
PESO_INDIZI = 0.5  # quanto contano parole e notazione rispetto al significato
PESO_CONTESTO = 0.1  # piccolo vantaggio per l'argomento del documento, nei casi in bilico


@dataclass
class Classificazione:
    argomento_documento: str  # l'argomento più probabile per tutto il documento
    argomenti_blocchi: list[str]  # l'argomento di ogni blocco, nello stesso ordine


def _normalizza(testo: str) -> str:
    testo = unicodedata.normalize("NFD", testo.lower())
    return "".join(c for c in testo if unicodedata.category(c) != "Mn")


def indizi(testo: str) -> np.ndarray:
    """Quante parole chiave e quanti segni di notazione di ogni argomento compaiono nel testo."""
    normale = _normalizza(testo)
    return np.array(
        [
            sum(normale.count(p) for p in PAROLE[a]) + sum(len(re.findall(r, testo)) for r in NOTAZIONE[a])
            for a in ARGOMENTI
        ],
        dtype=float,
    )


_prototipi: np.ndarray | None = None


def _vettori_normalizzati(testi: list[str]) -> np.ndarray:
    vettori = np.array(indice.vettori(testi), dtype=float)
    norme = np.linalg.norm(vettori, axis=1, keepdims=True)
    return vettori / np.where(norme == 0, 1, norme)


def _somiglianze(testi: list[str]) -> np.ndarray:
    """Somiglianza di significato tra ogni testo e ogni argomento (una riga per testo)."""
    global _prototipi
    if _prototipi is None:
        _prototipi = _vettori_normalizzati([DESCRIZIONI[a] for a in ARGOMENTI])
    return _vettori_normalizzati(testi) @ _prototipi.T


def classifica(testi: list[str], argomento_documento: str | None = None) -> Classificazione:
    """
    Riconosce l'argomento dei blocchi di un documento.
    argomento_documento: quello scelto dallo studente; se è None lo riconosciamo noi.
    """
    if not testi:
        return Classificazione(argomento_documento or ARGOMENTI[0], [])
    somiglianze = _somiglianze(testi)
    tutti_indizi = np.array([indizi(t) for t in testi])

    # Argomento del documento: contano soprattutto gli indizi di tutti i blocchi insieme,
    # il significato serve a decidere quando gli indizi mancano o sono in parità
    if argomento_documento is None:
        punteggio = tutti_indizi.sum(axis=0) + 0.01 * somiglianze.sum(axis=0)
        argomento_documento = ARGOMENTI[int(np.argmax(punteggio))]

    contesto = np.array([PESO_CONTESTO if a == argomento_documento else 0.0 for a in ARGOMENTI])
    argomenti_blocchi = []
    for somiglianza, trovati in zip(somiglianze, tutti_indizi):
        if trovati.sum() == 0:
            # Nessun indizio (solo formule, o parole storpiate): vale l'argomento del documento
            argomenti_blocchi.append(argomento_documento)
        else:
            punteggio = somiglianza + PESO_INDIZI * trovati / trovati.sum() + contesto
            argomenti_blocchi.append(ARGOMENTI[int(np.argmax(punteggio))])
    return Classificazione(argomento_documento, argomenti_blocchi)


def assegna_mancanti(motore) -> int:
    """
    Dà un argomento ai blocchi che non ce l'hanno ancora: quelli caricati con Blueprint 1.0
    o 1.1, prima che esistesse il riconoscimento. Gira una volta all'avvio, in sottofondo.
    L'argomento scelto dallo studente per il documento fa da contesto e non viene cambiato.
    Restituisce quanti blocchi sono stati aggiornati.
    """
    aggiornati = 0
    with Session(motore) as sessione:
        da_fare = list(sessione.exec(select(Blocco).where(Blocco.argomento == None)))  # noqa: E711
        if not da_fare:
            return 0
        # Gli esercizi risolti dall'app hanno già il loro argomento: niente da riconoscere
        generati = set(sessione.exec(select(Esercizio.documento_id).where(Esercizio.documento_id != None)))  # noqa: E711
        per_documento: dict[int, list[Blocco]] = {}
        for blocco in da_fare:
            per_documento.setdefault(blocco.documento_id, []).append(blocco)
        for id_documento, blocchi in per_documento.items():
            documento = sessione.get(Documento, id_documento)
            if documento is None:
                continue
            if id_documento in generati:
                argomenti = [documento.argomento] * len(blocchi)
            else:
                argomenti = classifica([b.testo for b in blocchi], documento.argomento).argomenti_blocchi
            for blocco, argomento in zip(blocchi, argomenti):
                blocco.argomento = argomento
                sessione.add(blocco)
            aggiornati += len(blocchi)
        sessione.commit()
    return aggiornati
