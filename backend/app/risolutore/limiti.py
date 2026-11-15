"""
Risolutore dei limiti, con i passaggi.

Strategia (la stessa che si segue a mano):
1. Sostituzione diretta: se la funzione è continua nel punto, abbiamo finito.
2. Se la funzione è un rapporto, guardiamo dove tendono numeratore e denominatore.
3. Se esce una forma indeterminata (0/0 oppure ∞/∞) scegliamo un metodo:
   - polinomi: scomposizione (punto finito) o confronto dei gradi (all'infinito);
   - altrimenti: de l'Hôpital oppure limiti notevoli / sviluppi asintotici.
   Tra i metodi possibili preferiamo quello che lo studente ha nel Magazzino.
4. Se nessuna strategia funziona, mostriamo solo il risultato di SymPy, dicendolo.
"""

from collections.abc import Callable

import sympy

from app.risolutore.concetti import CONCETTI
from app.risolutore.modelli import L, Passaggio, Problema, Svolgimento
from app.risolutore.verifica import uguali

INFINITI = (sympy.oo, -sympy.oo)


def calcola_limite(f: sympy.Expr, x: sympy.Symbol, x0: sympy.Expr, direzione: str) -> sympy.Expr | None:
    """Il limite secondo SymPy. Restituisce None se il limite non esiste."""
    if x0 in INFINITI:
        risultato = sympy.limit(f, x, x0)
    elif direzione in ("+", "-"):
        risultato = sympy.limit(f, x, x0, direzione)
    else:
        destro = sympy.limit(f, x, x0, "+")
        sinistro = sympy.limit(f, x, x0, "-")
        if not uguali(destro, sinistro):
            return None
        risultato = destro
    # AccumBounds = la funzione oscilla (es. sin(1/x)); nan = non definito
    if risultato.has(sympy.AccumBounds, sympy.nan) or isinstance(risultato, sympy.Limit):
        return None
    return risultato


def _freccia(x: sympy.Symbol, x0: sympy.Expr, direzione: str) -> str:
    verso = {"+": "^{+}", "-": "^{-}", "+-": ""}[direzione]
    return rf"{L(x)} \to {L(x0)}{verso}"


def _lim(f: sympy.Expr, p: Problema) -> str:
    """Scrive in LaTeX "lim f" per il problema p."""
    return rf"\lim_{{{_freccia(p.variabile, p.punto, p.direzione)}}} {L(f)}"


def _frazione(n: sympy.Expr, d: sympy.Expr) -> str:
    return rf"\frac{{{L(n)}}}{{{L(d)}}}"


def _testo_risultato(risultato: sympy.Expr | None) -> str:
    return r"\text{non esiste}" if risultato is None else L(risultato)


# ---------- i metodi per le forme indeterminate ----------
# Ogni metodo restituisce (passaggi, valore) oppure None se non è applicabile.


def _scomposizione(n, d, p: Problema):
    semplificata = sympy.cancel(n / d)
    if semplificata == n / d:
        return None  # non c'era nessun fattore comune da semplificare
    valore = calcola_limite(semplificata, p.variabile, p.punto, p.direzione)
    passi = [
        Passaggio(
            "Scomponiamo in fattori",
            "Numeratore e denominatore si annullano nello stesso punto, quindi hanno un fattore in comune. Scomponiamoli.",
            rf"{_frazione(n, d)} = {_frazione(sympy.factor(n), sympy.factor(d))}",
            "scomposizione",
        ),
        Passaggio(
            "Semplifichiamo",
            "Eliminiamo il fattore comune: è lecito perché nel limite la variabile si avvicina al punto senza mai raggiungerlo.",
            rf"{_lim(n / d, p)} = {_lim(semplificata, p)}",
            "scomposizione",
            domanda=f"Semplifica la frazione ${_frazione(n, d)}$",
            atteso=semplificata,
        ),
        Passaggio(
            "Sostituiamo",
            "Ora la forma indeterminata è sparita e possiamo sostituire il valore.",
            rf"{_lim(semplificata, p)} = {_testo_risultato(valore)}",
            "continuita",
            domanda=f"Quanto vale ${_lim(semplificata, p)}$?",
            atteso=valore,
        ),
    ]
    return passi, valore


def _gradi(n, d, p: Problema):
    x = p.variabile
    capo_n, capo_d = sympy.LT(n, x), sympy.LT(d, x)
    rapporto = sympy.simplify(capo_n / capo_d)
    valore = calcola_limite(rapporto, x, p.punto, p.direzione)
    passi = [
        Passaggio(
            "Termini di grado massimo",
            "Per valori molto grandi della variabile contano solo i termini di grado più alto: "
            "raccogliendoli, tutto il resto tende a zero.",
            rf"{_frazione(n, d)} \sim {_frazione(capo_n, capo_d)} = {L(rapporto)}",
            "gradi",
        ),
        Passaggio(
            "Calcoliamo il limite",
            "Resta il limite del rapporto tra i termini di grado massimo.",
            rf"{_lim(rapporto, p)} = {_testo_risultato(valore)}",
            "gradi",
            domanda=f"Quanto vale ${_lim(rapporto, p)}$?",
            atteso=valore,
        ),
    ]
    return passi, valore


def _indeterminata(ln, ld) -> str | None:
    """Riconosce le forme 0/0 e ∞/∞ dai limiti di numeratore e denominatore."""
    if ln is None or ld is None:
        return None
    if ln == 0 and ld == 0:
        return r"\frac{0}{0}"
    if ln in INFINITI and ld in INFINITI:
        return r"\frac{\infty}{\infty}"
    return None


def _hopital(n, d, p: Problema):
    x = p.variabile
    passi = []
    for giro in range(5):
        n_nuovo, d_nuovo = sympy.diff(n, x), sympy.diff(d, x)
        if d_nuovo == 0:
            return None
        # Semplifichiamo il nuovo rapporto (es. (1/x)/(1) = 1/x)
        rapporto = sympy.simplify(n_nuovo / d_nuovo)
        passi.append(
            Passaggio(
                "Applichiamo de l'Hôpital" if giro == 0 else "Applichiamo di nuovo de l'Hôpital",
                "Deriviamo separatamente il numeratore e il denominatore (non è la derivata del quoziente!)."
                if giro == 0
                else "Il limite è ancora una forma indeterminata: deriviamo un'altra volta numeratore e denominatore.",
                rf"{_lim(n / d, p)} = \lim_{{{_freccia(x, p.punto, p.direzione)}}} {_frazione(n_nuovo, d_nuovo)}"
                + (rf" = {_lim(rapporto, p)}" if rapporto != n_nuovo / d_nuovo else ""),
                "hopital",
                domanda="Deriva separatamente numeratore e denominatore: che rapporto ottieni?",
                atteso=n_nuovo / d_nuovo,
            )
        )
        n, d = sympy.fraction(sympy.together(rapporto))
        ln = calcola_limite(n, x, p.punto, p.direzione)
        ld = calcola_limite(d, x, p.punto, p.direzione)
        if _indeterminata(ln, ld):
            continue
        valore = calcola_limite(rapporto, x, p.punto, p.direzione)
        passi.append(
            Passaggio(
                "Calcoliamo il nuovo limite",
                "Il nuovo limite non è più una forma indeterminata: lo calcoliamo direttamente.",
                rf"{_lim(rapporto, p)} = {_testo_risultato(valore)}",
                "continuita",
                domanda=f"Quanto vale ${_lim(rapporto, p)}$?",
                atteso=valore,
            )
        )
        return passi, valore
    return None  # dopo 5 derivazioni è ancora indeterminata: lasciamo perdere


def _asintotico(n, d, p: Problema):
    x, x0 = p.variabile, p.punto
    if x0 in INFINITI:
        return None
    # Ci mettiamo vicino al punto: x = x0 + h con h piccolo, e prendiamo il termine principale
    h = sympy.Symbol("h")
    capo_n = n.subs(x, x0 + h).as_leading_term(h).subs(h, x - x0)
    capo_d = d.subs(x, x0 + h).as_leading_term(h).subs(h, x - x0)
    if capo_n.has(sympy.Order) or capo_d.has(sympy.Order) or capo_d == 0:
        return None
    rapporto = sympy.simplify(capo_n / capo_d)
    valore = calcola_limite(rapporto, x, x0, p.direzione)
    passi = [
        Passaggio(
            "Termini principali",
            f"Vicino a ${L(x)} = {L(x0)}$ sostituiamo numeratore e denominatore con la loro parte principale, "
            "ricavata dai limiti notevoli (o dallo sviluppo di Taylor).",
            rf"{L(n)} \sim {L(capo_n)}, \qquad {L(d)} \sim {L(capo_d)}",
            "asintotico",
        ),
        Passaggio(
            "Rapporto dei termini principali",
            "Il limite del rapporto è uguale al limite del rapporto delle parti principali.",
            rf"{_lim(n / d, p)} = \lim_{{{_freccia(x, x0, p.direzione)}}} {_frazione(capo_n, capo_d)} = {_testo_risultato(valore)}",
            "asintotico",
            domanda=f"Quanto vale $\\lim_{{{_freccia(x, x0, p.direzione)}}} {_frazione(capo_n, capo_d)}$?",
            atteso=valore,
        ),
    ]
    return passi, valore


# ---------- il risolutore ----------


def risolvi_limite(p: Problema, conosce: Callable[[str], bool]) -> Svolgimento:
    """
    Costruisce i passaggi del limite. "conosce(chiave)" dice se un concetto è nel Magazzino:
    serve per scegliere, tra i metodi possibili, quello che lo studente ha già studiato.
    """
    f, x, x0 = p.funzione, p.variabile, p.punto
    riferimento = calcola_limite(f, x, x0, p.direzione)

    # --- 1. sostituzione diretta ---
    if x0 not in INFINITI and riferimento is not None:
        try:
            valore = f.subs(x, x0)
        except Exception:
            valore = sympy.nan
        if valore.is_finite and not valore.has(sympy.nan, sympy.zoo) and uguali(valore, riferimento):
            return Svolgimento(
                risultato=valore,
                metodo="sostituzione diretta",
                passaggi=[
                    Passaggio(
                        "Sostituzione diretta",
                        f"La funzione è continua in ${L(x)} = {L(x0)}$: il limite è semplicemente il valore "
                        "della funzione in quel punto.",
                        rf"{_lim(f, p)} = {L(sympy.simplify(valore))}",
                        "continuita",
                        domanda=f"Quanto vale ${_lim(f, p)}$?",
                        atteso=valore,
                    )
                ],
            )

    # --- 2. studio di numeratore e denominatore ---
    n, d = sympy.fraction(sympy.together(f))
    if d.has(x):
        ln = calcola_limite(n, x, x0, p.direzione)
        ld = calcola_limite(d, x, x0, p.direzione)
        passi = [
            Passaggio(
                "Guardiamo numeratore e denominatore",
                "Calcoliamo separatamente a cosa tendono il numeratore e il denominatore.",
                rf"{L(n)} \to {_testo_risultato(ln)}, \qquad {L(d)} \to {_testo_risultato(ld)}",
            )
        ]
        forma = _indeterminata(ln, ld)

        # --- 3. forma indeterminata: scegliamo il metodo ---
        if forma:
            passi.append(
                Passaggio(
                    "Forma indeterminata",
                    "Il limite si presenta in una forma indeterminata: non possiamo concludere subito, serve un metodo.",
                    forma,
                    "forma_indeterminata",
                )
            )
            polinomi = n.is_polynomial(x) and d.is_polynomial(x)
            if polinomi and x0 in INFINITI:
                candidati = [("gradi", _gradi)]
            elif polinomi:
                candidati = [("scomposizione", _scomposizione), ("hopital", _hopital)]
            else:
                candidati = [("hopital", _hopital), ("asintotico", _asintotico)]

            # Proviamo tutti i metodi e teniamo quelli che arrivano al risultato giusto
            riusciti = []
            for chiave, metodo in candidati:
                try:
                    esito = metodo(n, d, p)
                except Exception:
                    esito = None
                if esito and uguali(esito[1], riferimento):
                    riusciti.append((chiave, esito[0]))

            if riusciti:
                # Preferiamo un metodo che lo studente ha nel Magazzino
                scelto = next((r for r in riusciti if conosce(r[0])), riusciti[0])
                avvisi = []
                if scelto is not riusciti[0]:
                    avvisi.append(
                        f"Di solito qui userei: {CONCETTI[riusciti[0][0]].nome}. Non è ancora nei tuoi appunti, "
                        f"quindi ho seguito una strada alternativa con ciò che conosci: {CONCETTI[scelto[0]].nome}."
                    )
                return Svolgimento(
                    risultato=riferimento,
                    metodo=CONCETTI[scelto[0]].nome,
                    passaggi=passi + scelto[1],
                    avvisi=avvisi,
                )

        # --- denominatore che tende a zero, numeratore no: il rapporto diverge ---
        elif ld == 0 and ln is not None and ln != 0:
            destro = calcola_limite(f, x, x0, "+") if x0 not in INFINITI else riferimento
            sinistro = calcola_limite(f, x, x0, "-") if x0 not in INFINITI else riferimento
            if p.direzione == "+-" and x0 not in INFINITI:
                formula = (
                    rf"\lim_{{{_freccia(x, x0, '+')}}} {L(f)} = {_testo_risultato(destro)}, \qquad "
                    rf"\lim_{{{_freccia(x, x0, '-')}}} {L(f)} = {_testo_risultato(sinistro)}"
                )
                conclusione = (
                    "I due limiti coincidono, quindi il limite esiste."
                    if riferimento is not None
                    else "I limiti destro e sinistro sono diversi, quindi il limite non esiste."
                )
            else:
                formula = rf"{_lim(f, p)} = {_testo_risultato(riferimento)}"
                conclusione = ""
            passi.append(
                Passaggio(
                    "Il rapporto diverge",
                    "Il numeratore tende a un numero diverso da zero e il denominatore tende a zero: il rapporto "
                    "diventa infinitamente grande. Per il segno guardiamo da che parte ci avviciniamo. " + conclusione,
                    formula,
                    "limite_infinito",
                )
            )
            return Svolgimento(risultato=riferimento, metodo="studio del segno", passaggi=passi)

        # --- numeratore finito, denominatore infinito: il rapporto tende a zero ---
        elif ld in INFINITI and ln is not None and ln.is_finite:
            passi.append(
                Passaggio(
                    "Il rapporto tende a zero",
                    "Il numeratore resta limitato mentre il denominatore diventa infinitamente grande.",
                    rf"{_lim(f, p)} = 0",
                )
            )
            return Svolgimento(risultato=sympy.S.Zero, metodo="confronto", passaggi=passi)

    # --- 4. nessuna strategia: solo il risultato di SymPy ---
    return Svolgimento(
        risultato=riferimento,
        metodo="calcolo diretto",
        dettagliato=False,
        passaggi=[
            Passaggio(
                "Risultato",
                "Per questo tipo di limite non so ancora mostrare i passaggi intermedi: "
                "qui trovi solo il risultato, calcolato da SymPy.",
                rf"{_lim(f, p)} = {_testo_risultato(riferimento)}",
            )
        ],
    )
