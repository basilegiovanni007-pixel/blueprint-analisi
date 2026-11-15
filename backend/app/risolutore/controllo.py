"""
"Mettimi alla prova": controllo delle risposte dello studente.

Quando un esercizio viene risolto, le risposte corrette (di ogni passaggio e finale) vengono
salvate nello Storico in un formato testuale ("srepr" di SymPy). Quando lo studente scrive
una risposta, la confrontiamo con quella corretta in modo matematico: x*2 e 2x sono la stessa
cosa, e per le primitive va bene anche un risultato che differisce per una costante.

Le risposte corrette restano solo sul computer: il browser riceve le domande, mai le soluzioni.
"""

import json
import re

import sympy

from app.risolutore.interpreta import leggi_espressione
from app.risolutore.modelli import ErroreRisolutore, Passaggio, Problema, Svolgimento
from app.risolutore.verifica import uguali

INFINITI = (sympy.oo, -sympy.oo)


# ---------- preparazione (al momento della risoluzione) ----------


def _testo(espressione: sympy.Expr | None) -> str | None:
    """Trasforma un'espressione in testo, per salvarla nel database."""
    return None if espressione is None else sympy.srepr(espressione)


def _da_testo(testo: str | None) -> sympy.Expr | None:
    """L'operazione inversa. I dati vengono dal nostro database, quindi sono affidabili."""
    if testo is None:
        return None
    espressione = sympy.sympify(testo)
    # Usiamo simboli "semplici" (senza proprietà come "intero" o "positivo"), uguali a quelli
    # che si ottengono leggendo ciò che scrive lo studente: così il confronto è diretto.
    return espressione.xreplace({s: sympy.Symbol(s.name) for s in espressione.free_symbols})


def prepara(p: Problema, s: Svolgimento, passaggi: list[Passaggio]) -> tuple[dict, dict | None]:
    """
    Restituisce (controlli, controllo_finale):
    - controlli: le risposte corrette, da salvare nello Storico (privato);
    - controllo_finale: il tipo di risposta finale richiesta e la domanda (pubblico), o None.
    """
    controlli: dict = {
        "passaggi": [
            {"atteso": _testo(x.atteso), "costante": x.costante.name if x.costante is not None else None}
            if x.atteso is not None and x.domanda
            else None
            for x in passaggi
        ],
        "finale": None,
    }
    domanda = None

    if p.tipo == "limite":
        controlli["finale"] = {"tipo": "espressione", "atteso": _testo(s.risultato), "costante": None}
        domanda = "Qual è il risultato del limite? Se non esiste, scrivi «non esiste»."
    elif p.tipo == "derivata":
        controlli["finale"] = {"tipo": "espressione", "atteso": _testo(s.risultato), "costante": None}
        domanda = "Quanto vale la derivata?"
    elif p.tipo == "integrale":
        indefinito = p.estremo_a is None
        controlli["finale"] = {
            "tipo": "espressione",
            "atteso": _testo(s.risultato),
            "costante": p.variabile.name if indefinito else None,
        }
        domanda = "Quanto vale l'integrale?" + (" (la costante $+\\,c$ puoi anche ometterla)" if indefinito else "")
    elif p.tipo == "doppio":
        controlli["finale"] = {"tipo": "espressione", "atteso": _testo(s.risultato), "costante": None}
        domanda = "Quanto vale l'integrale doppio?"
    elif p.tipo == "serie":
        converge = (s.risultato_latex or "").startswith(r"\text{converge")
        controlli["finale"] = {"tipo": "scelta", "converge": converge}
        domanda = "La serie converge?"
    elif p.tipo == "gradiente":
        componenti = [sympy.diff(p.funzione, v) for v in p.variabili]
        controlli["finale"] = {"tipo": "vettore", "componenti": [_testo(c) for c in componenti]}
        nomi = ",\\ ".join(rf"\frac{{\partial f}}{{\partial {v}}}" for v in p.variabili)
        domanda = f"Scrivi il gradiente, con le componenti separate da virgole: $\\left({nomi}\\right)$"
    elif p.tipo == "edo":
        ordine = 2 if p.funzione.has(sympy.Symbol("y''")) else 1
        controlli["finale"] = {
            "tipo": "edo",
            "equazione": _testo(p.funzione),
            "variabile": p.variabile.name,
            "ordine": ordine,
            "condizioni": [[k, _testo(x0), _testo(v)] for k, x0, v in p.condizioni],
        }
        domanda = (
            "Scrivi la soluzione del problema di Cauchy: $y = \\dots$"
            if p.condizioni
            else "Scrivi la soluzione generale: $y = \\dots$ (per le costanti arbitrarie usa c1"
            + (" e c2)" if ordine == 2 else ")")
        )
    # Punti critici e vincolati: la risposta è un elenco di punti classificati, che non
    # si può scrivere in una riga. Per questi esercizi si controllano solo i passaggi.

    tipo = controlli["finale"]["tipo"] if controlli["finale"] else None
    return controlli, ({"tipo": tipo, "domanda": domanda} if tipo else None)


# ---------- controllo (quando lo studente risponde) ----------

ESATTO = "Esatto!"


def _pulisci(risposta: str) -> str:
    """Toglie ciò che sta attorno alla risposta: "y =", "f'(x) =", "+ c" finale..."""
    risposta = risposta.strip().rstrip(".;")
    if "=" in risposta:
        risposta = risposta.rsplit("=", 1)[1]  # teniamo ciò che sta dopo l'ultimo "="
    return risposta.strip()


def _leggi(risposta: str) -> sympy.Expr:
    testo = _pulisci(risposta)
    if not testo:
        raise ErroreRisolutore("Scrivi una risposta prima di controllarla.")
    return leggi_espressione(testo)


def _confronta(risposta: str, atteso: sympy.Expr, costante: str | None) -> dict:
    """Confronto tra una risposta scritta e un'espressione attesa."""
    testo = _pulisci(risposta)
    if costante:
        # Nelle primitive la costante di integrazione si può scrivere o no
        testo = re.sub(r"\s*\+\s*[cCkK]\s*$", "", testo)
    data = leggi_espressione(testo) if testo else None
    if data is None:
        raise ErroreRisolutore("Scrivi una risposta prima di controllarla.")

    if costante:
        variabile = sympy.Symbol(costante)
        corretto = uguali(sympy.diff(data - atteso, variabile), sympy.S.Zero)
        if corretto:
            return {"corretto": True, "messaggio": ESATTO + " (Ricorda che una primitiva è definita a meno di una costante.)"}
        return {"corretto": False, "messaggio": "Non è corretto: prova a derivare il tuo risultato e controlla se ottieni la funzione di partenza."}

    if uguali(data, atteso):
        identica = sympy.srepr(data) == sympy.srepr(atteso)
        return {"corretto": True, "messaggio": ESATTO if identica else ESATTO + " L'hai scritto in una forma diversa, ma è equivalente."}
    if atteso in INFINITI and data in INFINITI:
        return {"corretto": False, "messaggio": "Quasi: il limite è infinito, ma attento al segno."}
    if data.free_symbols - atteso.free_symbols and not atteso.free_symbols:
        return {"corretto": False, "messaggio": "Qui il risultato è un numero: nella tua risposta compaiono ancora delle lettere."}
    return {"corretto": False, "messaggio": "Non è corretto: ricontrolla i calcoli."}


def _finale(finale: dict, risposta: str) -> dict:
    tipo = finale["tipo"]

    if tipo == "scelta":
        testo = risposta.strip().lower()
        if testo.startswith("non") or "diverg" in testo or "indeterminat" in testo or "oscill" in testo:
            data = False
        elif testo.startswith("converge") or testo in ("si", "sì"):
            data = True
        else:
            raise ErroreRisolutore("Rispondi «converge» oppure «non converge».")
        if data == finale["converge"]:
            return {"corretto": True, "messaggio": ESATTO}
        return {"corretto": False, "messaggio": "Non è corretto: ricontrolla il criterio che hai usato."}

    if tipo == "espressione":
        atteso = _da_testo(finale["atteso"])
        non_esiste = "non esiste" in risposta.lower() or risposta.strip().lower() in ("ne", "∄")
        if atteso is None:
            if non_esiste:
                return {"corretto": True, "messaggio": ESATTO + " Il limite non esiste."}
            return {"corretto": False, "messaggio": "Non è corretto: ricontrolla, e guarda bene anche i limiti destro e sinistro."}
        if non_esiste:
            return {"corretto": False, "messaggio": "Non è corretto: questo limite esiste."}
        return _confronta(risposta, atteso, finale["costante"])

    if tipo == "vettore":
        attesi = [_da_testo(c) for c in finale["componenti"]]
        testo = _pulisci(risposta).strip()
        # Togliamo le parentesi esterne e dividiamo alle virgole che non stanno dentro altre parentesi
        if testo[:1] in "([" and testo[-1:] in ")]":
            testo = testo[1:-1]
        pezzi, livello, corrente = [], 0, ""
        for carattere in testo:
            if carattere in "([":
                livello += 1
            elif carattere in ")]":
                livello -= 1
            if carattere in ",;" and livello == 0:
                pezzi.append(corrente)
                corrente = ""
            else:
                corrente += carattere
        pezzi.append(corrente)
        if len(pezzi) != len(attesi):
            raise ErroreRisolutore(f"Il gradiente ha {len(attesi)} componenti: scrivile separate da virgole.")
        sbagliate = [i + 1 for i, (pezzo, atteso) in enumerate(zip(pezzi, attesi)) if not uguali(leggi_espressione(pezzo), atteso)]
        if not sbagliate:
            return {"corretto": True, "messaggio": ESATTO}
        elenco = " e ".join(f"la {n}ª" for n in sbagliate)
        return {"corretto": False, "messaggio": f"Non è corretto: ricontrolla {elenco} componente."}

    if tipo == "edo":
        return _controlla_edo(finale, risposta)

    raise ErroreRisolutore("Per questo esercizio la risposta finale non si può controllare automaticamente.")


def _controlla_edo(finale: dict, risposta: str) -> dict:
    x = sympy.Symbol(finale["variabile"])
    A, B = sympy.Symbol("A"), sympy.Symbol("B")
    # Le costanti si possono scrivere c1, c_1, C1, k1...: le trasformiamo in A e B
    testo = _pulisci(risposta)
    testo = re.sub(r"\b[cCkK]_?\{?1\}?(?!\w)", " A ", testo)
    testo = re.sub(r"\b[cCkK]_?\{?2\}?(?!\w)", " B ", testo)
    testo = re.sub(r"\b[cCkK]\b", " A ", testo)
    soluzione = leggi_espressione(testo)
    estranei = soluzione.free_symbols - {x, A, B}
    if estranei:
        raise ErroreRisolutore(f"Nella soluzione possono comparire solo {x} e le costanti c1, c2.")

    equazione = _da_testo(finale["equazione"])
    Y, Y1, Y2 = sympy.Symbol("y"), sympy.Symbol("y'"), sympy.Symbol("y''")
    residuo = equazione.subs({Y2: sympy.diff(soluzione, x, 2), Y1: sympy.diff(soluzione, x), Y: soluzione})
    if not uguali(residuo, sympy.S.Zero):
        return {"corretto": False, "messaggio": "Non è corretto: sostituendo la tua funzione nell'equazione non si ottiene un'identità."}

    costanti = soluzione.free_symbols & {A, B}
    if finale["condizioni"]:
        if costanti:
            return {"corretto": False, "messaggio": "È una soluzione dell'equazione, ma le costanti vanno determinate con le condizioni iniziali."}
        for k, x0, valore in finale["condizioni"]:
            if not uguali(sympy.diff(soluzione, x, k).subs(x, _da_testo(x0)), _da_testo(valore)):
                return {"corretto": False, "messaggio": "Risolve l'equazione, ma non rispetta le condizioni iniziali."}
        return {"corretto": True, "messaggio": ESATTO + " Risolve l'equazione e rispetta le condizioni iniziali."}

    if len(costanti) < finale["ordine"]:
        servono = "una costante arbitraria" if finale["ordine"] == 1 else "due costanti arbitrarie"
        return {"corretto": False, "messaggio": f"È una soluzione, ma non quella generale: servono {servono}."}
    return {"corretto": True, "messaggio": ESATTO + " Ho controllato sostituendo la tua soluzione nell'equazione."}


def controlla(controlli_json: str, passaggio: int | None, risposta: str) -> dict:
    """
    Controlla la risposta dello studente.
    passaggio: indice del passaggio (da 0); None = risposta finale.
    """
    controlli = json.loads(controlli_json)
    try:
        if passaggio is None:
            if controlli["finale"] is None:
                raise ErroreRisolutore("Per questo esercizio la risposta finale non si può controllare automaticamente.")
            return _finale(controlli["finale"], risposta)

        elenco = controlli["passaggi"]
        if not 0 <= passaggio < len(elenco) or elenco[passaggio] is None:
            raise ErroreRisolutore("Questo passaggio non ha una domanda da controllare.")
        voce = elenco[passaggio]
        atteso = _da_testo(voce["atteso"])
        if atteso in INFINITI and "non esiste" in risposta.lower():
            return {"corretto": False, "messaggio": "Non è corretto: qui il limite esiste (è infinito)."}
        return _confronta(risposta, atteso, voce["costante"])
    except ErroreRisolutore:
        raise
    except Exception:
        raise ErroreRisolutore("Non riesco a leggere la tua risposta: controlla le parentesi e usa * per i prodotti.")
