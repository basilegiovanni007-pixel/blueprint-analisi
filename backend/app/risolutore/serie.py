"""
Risolutore delle serie numeriche: stabilisce se una serie converge, usando i criteri
che si studiano in Analisi I, nello stesso ordine in cui si provano a mano:

1. condizione necessaria (il termine generale deve tendere a zero);
2. serie "famose": geometrica e armonica generalizzata;
3. criteri per le serie a termini positivi: rapporto e confronto asintotico;
4. serie a segni alterni: convergenza assoluta, poi criterio di Leibniz.

Alla fine la conclusione viene confrontata con quella che SymPy ottiene per conto suo.
"""

import sympy
from sympy import oo

from app.grafici.formule import come_numero
from app.risolutore.modelli import ErroreRisolutore, L, Passaggio, Problema, Svolgimento

QUANTI_TERMINI = 40  # quanti termini guardiamo per capire il segno della serie


def _limite(espressione, n):
    """Limite per n che tende a infinito; None se non esiste o SymPy non riesce a calcolarlo."""
    try:
        valore = sympy.limit(espressione, n, oo)
    except Exception:
        return None
    if valore.has(sympy.AccumBounds, sympy.nan, sympy.zoo) or isinstance(valore, sympy.Limit):
        return None
    return valore


def _termini_positivi(a, n) -> tuple[bool | None, list[Passaggio]]:
    """
    Studia una serie a termini positivi. Restituisce (converge?, passaggi);
    il primo valore è None se nessun criterio permette di concludere.
    """
    passi: list[Passaggio] = []
    rapporto = sympy.simplify(a.subs(n, n + 1) / a)

    # --- serie geometrica: il rapporto tra due termini consecutivi è costante ---
    if not rapporto.free_symbols:
        converge = bool(rapporto < 1)
        passi.append(
            Passaggio(
                "Serie geometrica",
                "Il rapporto tra un termine e il precedente è sempre lo stesso numero $q$: è una serie geometrica. "
                "Converge se e solo se $|q| < 1$. "
                + ("Qui $|q| < 1$, quindi converge." if converge else "Qui $|q| \\geq 1$, quindi non converge."),
                rf"\frac{{a_{{n+1}}}}{{a_n}} = q = {L(rapporto)}",
                "serie_geometrica",
                domanda="Quanto vale il rapporto $q = \\frac{a_{n+1}}{a_n}$ tra due termini consecutivi?",
                atteso=rapporto,
            )
        )
        return converge, passi

    # --- comportamento all'infinito: a_n "assomiglia" a c / n^p ? ---
    p = _limite(-sympy.log(a) / sympy.log(n), n)
    c = _limite(a * n**p, n) if p is not None and p.is_finite else None
    come_potenza = c is not None and c.is_finite and c != 0

    # --- serie armonica generalizzata: a_n è proprio c / n^p ---
    if come_potenza and not sympy.simplify(a * n**p).free_symbols:
        converge = bool(p > 1)
        passi.append(
            Passaggio(
                "Serie armonica generalizzata",
                "È una serie del tipo $\\sum \\frac{1}{n^p}$ (a meno di una costante): converge se e solo se $p > 1$. "
                + (f"Qui $p = {L(p)} > 1$, quindi converge." if converge else f"Qui $p = {L(p)} \\leq 1$, quindi diverge."),
                rf"a_n = {L(a)}, \qquad p = {L(p)}",
                "serie_armonica",
                domanda="È una serie armonica generalizzata $\\sum \\frac{1}{n^p}$: quanto vale l'esponente $p$?",
                atteso=p,
            )
        )
        return converge, passi

    # --- criterio del rapporto: utile con fattoriali ed esponenziali ---
    limite_rapporto = _limite(rapporto, n)
    if limite_rapporto is not None and limite_rapporto != 1:
        converge = bool(limite_rapporto < 1)
        passi.append(
            Passaggio(
                "Criterio del rapporto",
                "Calcoliamo il limite del rapporto tra un termine e il precedente. Se è minore di 1 la serie converge, "
                "se è maggiore di 1 diverge. "
                + ("Qui il limite è minore di 1: la serie converge." if converge else "Qui il limite è maggiore di 1: la serie diverge."),
                rf"\lim_{{n \to \infty}} \frac{{a_{{n+1}}}}{{a_n}} = \lim_{{n \to \infty}} {L(rapporto)} = {L(limite_rapporto)}",
                "criterio_rapporto",
                domanda="Quanto vale $\\lim_{n \\to \\infty} \\frac{a_{n+1}}{a_n}$?",
                atteso=limite_rapporto,
            )
        )
        return converge, passi

    # --- confronto asintotico con la serie armonica generalizzata ---
    if come_potenza:
        converge = bool(p > 1)
        passi.append(
            Passaggio(
                "Confronto asintotico",
                f"Per $n$ grande il termine generale si comporta come $\\frac{{1}}{{n^{{{L(p)}}}}}$ (a meno di una costante): "
                "il limite del loro rapporto è un numero finito e diverso da zero. Le due serie hanno quindi lo stesso "
                "carattere, e la serie armonica generalizzata converge se e solo se l'esponente è maggiore di 1. "
                + ("Qui l'esponente è maggiore di 1: la serie converge." if converge else "Qui l'esponente non supera 1: la serie diverge."),
                rf"\lim_{{n \to \infty}} \frac{{a_n}}{{1/n^{{{L(p)}}}}} = {L(c)} \quad\Rightarrow\quad a_n \sim \frac{{{L(c)}}}{{n^{{{L(p)}}}}}",
                "confronto_asintotico",
                domanda="Per $n$ grande il termine generale si comporta come $\\frac{c}{n^p}$: quanto vale $p$?",
                atteso=p,
            )
        )
        return converge, passi

    return None, passi


def risolvi_serie(p: Problema) -> Svolgimento:
    # n è un numero intero positivo: dirlo a SymPy gli permette di semplificare (-1)^n, fattoriali...
    n = sympy.Symbol("n", integer=True, positive=True)
    a = p.funzione.subs(p.variabile, n)
    inizio = int(p.estremo_a)
    serie = rf"\sum_{{n={inizio}}}^{{\infty}} {L(a)}"

    def termine(k: int) -> float | None:
        """Valore numerico del termine di indice k (senza arrotondamenti: può essere piccolissimo)."""
        try:
            valore = complex(sympy.N(a.subs(n, k)))
        except (TypeError, ValueError):
            return None
        return valore.real if abs(valore.imag) < 1e-12 and valore.real == valore.real else None

    valori = [termine(inizio + k) for k in range(QUANTI_TERMINI)]
    if any(v is None for v in valori):
        raise ErroreRisolutore(f"Il termine della serie non è definito per tutti gli n a partire da {inizio}: controlla l'indice di partenza.")

    passi: list[Passaggio] = []
    converge: bool | None = None
    esito = ""  # la conclusione a parole

    # --- 1. condizione necessaria ---
    limite = _limite(a, n)
    if limite is None and _limite(sympy.simplify(sympy.Abs(a)), n) == 0:
        limite = sympy.S.Zero  # se il valore assoluto tende a zero, anche il termine tende a zero
    if limite is None or limite != 0:
        converge = False
        esito = "non converge"
        passi.append(
            Passaggio(
                "Condizione necessaria",
                "Perché una serie converga, il suo termine generale deve tendere a zero. "
                + ("Qui il limite non esiste" if limite is None else "Qui il limite è diverso da zero")
                + ": la serie non può convergere.",
                rf"\lim_{{n \to \infty}} {L(a)} " + (r"\ \text{non esiste}" if limite is None else f"= {L(limite)} \\neq 0"),
                "condizione_necessaria",
            )
        )
        if all(v > 0 for v in valori):
            esito = "diverge"
    else:
        passi.append(
            Passaggio(
                "Condizione necessaria",
                "Il termine generale tende a zero: la condizione necessaria è soddisfatta. "
                "Attenzione: non basta per dire che la serie converge, serve un criterio.",
                rf"\lim_{{n \to \infty}} {L(a)} = 0",
                "condizione_necessaria",
                domanda=f"Quanto vale $\\lim_{{n \\to \\infty}} {L(a)}$?",
                atteso=sympy.S.Zero,
            )
        )
        positivi = all(v > 0 for v in valori)
        negativi = all(v < 0 for v in valori)
        alterni = all(valori[k] * valori[k + 1] < 0 for k in range(QUANTI_TERMINI - 1))

        if positivi or negativi:
            if negativi:
                passi.append(Passaggio("Segno dei termini", "I termini sono tutti negativi: studiamo la serie cambiata di segno, che ha lo stesso carattere.", rf"-a_n = {L(-a)}"))
            converge, nuovi = _termini_positivi(a if positivi else -a, n)
            passi.extend(nuovi)
            if converge is not None:
                esito = "converge" if converge else "diverge"

        elif alterni:
            b = sympy.simplify(sympy.Abs(a))
            passi.append(
                Passaggio(
                    "Serie a segni alterni",
                    "I termini cambiano segno a ogni passo. Studiamo prima la serie dei valori assoluti: "
                    "se converge quella, converge anche la serie di partenza (convergenza assoluta).",
                    rf"|a_n| = {L(b)}",
                    "convergenza_assoluta",
                )
            )
            assoluta, nuovi = _termini_positivi(b, n)
            passi.extend(nuovi)
            if assoluta:
                converge, esito = True, "converge assolutamente"
            elif assoluta is False:
                # Non converge assolutamente: proviamo il criterio di Leibniz
                moduli = [abs(v) for v in valori]
                decrescente = all(moduli[k + 1] <= moduli[k] for k in range(QUANTI_TERMINI - 1))
                if decrescente:
                    converge, esito = True, "converge semplicemente (non assolutamente)"
                    passi.append(
                        Passaggio(
                            "Criterio di Leibniz",
                            "La serie dei valori assoluti non converge, ma la serie è a segni alterni, $|a_n|$ tende a zero "
                            "ed è decrescente: per il criterio di Leibniz la serie converge.",
                            rf"|a_n| = {L(b)} \ \searrow \ 0",
                            "leibniz",
                        )
                    )

    # --- verifica indipendente: cosa dice SymPy? ---
    m = sympy.Symbol("n", integer=True)
    try:
        secondo_sympy: bool | None = bool(sympy.Sum(a.subs(n, m), (m, inizio, oo)).is_convergent())
    except Exception:
        secondo_sympy = None

    dettagliato = True
    if converge is None:
        # Nessun criterio tra quelli che conosco: usiamo direttamente la risposta di SymPy
        if secondo_sympy is None:
            raise ErroreRisolutore("Non riesco a stabilire il carattere di questa serie con i criteri che conosco.")
        converge, dettagliato = secondo_sympy, False
        esito = "converge" if converge else "non converge"
        passi.append(
            Passaggio(
                "Risultato",
                "Per questa serie non so indicare il criterio da usare: qui trovi solo la conclusione, stabilita da SymPy.",
                rf"{serie} \ \text{{{esito}}}",
            )
        )
        verificato: bool | None = True
    elif secondo_sympy is None:
        verificato = None  # SymPy non sa rispondere: la conclusione poggia solo sul criterio applicato
    else:
        verificato = secondo_sympy == converge

    # --- somma, quando si riesce a calcolare ---
    risposta = rf"{serie} \ \text{{{esito}}}"
    if converge:
        try:
            somma = sympy.summation(a.subs(n, m), (m, inizio, oo))
            if not somma.has(sympy.Sum) and come_numero(somma) is not None:
                passi.append(
                    Passaggio(
                        "Somma della serie",
                        "In questo caso si riesce anche a calcolare il valore a cui converge la serie.",
                        rf"{serie} = {L(somma)}",
                    )
                )
                risposta += rf", \qquad \text{{somma}} = {L(somma)}"
        except Exception:
            pass

    return Svolgimento(
        risultato=None,
        risultato_latex=rf"\text{{{esito}}}",
        risposta_latex=risposta,
        metodo="criteri di convergenza",
        passaggi=passi,
        dettagliato=dettagliato,
        verificato=verificato,
    )
