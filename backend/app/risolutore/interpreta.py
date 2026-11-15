"""
Interpretazione dell'esercizio: dal testo scritto dallo studente a un Problema.

Il testo può essere:
- una frase in italiano:  "calcola il limite per x che tende a 0 di sin(x)/x"
- LaTeX:                  "\\lim_{x \\to 0} \\frac{\\sin x}{x}"
- solo la formula:        "x^2 * sin(x)"   (in questo caso il tipo si sceglie dal menu)

Qui non c'è nessuna intelligenza artificiale: usiamo "espressioni regolari" (regex),
cioè schemi che riconoscono pezzi di testo. Per questo capiamo solo le frasi più comuni.
"""

import re
import unicodedata

import sympy
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

from app.risolutore.modelli import ErroreRisolutore, Problema

# ---------- 1. Dalla formula scritta a un'espressione SymPy ----------

# Nomi che lo studente può usare e a cosa corrispondono in SymPy.
# Accettiamo anche le abbreviazioni italiane (sen, tg, arctg...).
NOMI_PERMESSI: dict[str, object] = {
    "sin": sympy.sin, "sen": sympy.sin, "cos": sympy.cos,
    "tan": sympy.tan, "tg": sympy.tan, "cot": sympy.cot, "cotg": sympy.cot,
    "arcsin": sympy.asin, "arcsen": sympy.asin, "asin": sympy.asin,
    "arccos": sympy.acos, "acos": sympy.acos,
    "arctan": sympy.atan, "arctg": sympy.atan, "atan": sympy.atan,
    "sinh": sympy.sinh, "cosh": sympy.cosh, "tanh": sympy.tanh,
    "ln": sympy.log, "log": sympy.log, "exp": sympy.exp,
    "sqrt": sympy.sqrt, "radq": sympy.sqrt, "abs": sympy.Abs,
    "e": sympy.E, "pi": sympy.pi, "oo": sympy.oo,
}  # fmt: skip

TRASFORMAZIONI = standard_transformations + (
    convert_xor,  # permette di scrivere x^2 invece di x**2
    implicit_multiplication_application,  # permette 2x, 3sin(x), sin x
)

# Simboli "speciali" che può capitare di copiare da un PDF o da una pagina web
SOSTITUZIONI = {
    "·": "*", "×": "*", "⋅": "*", "−": "-", "–": "-", "÷": "/", ":": "/",
    "√": "sqrt", "∞": "oo", "π": "pi", "²": "^2", "³": "^3",
    "[": "(", "]": ")", "{": "(", "}": ")",
}  # fmt: skip


def leggi_espressione(testo: str) -> sympy.Expr:
    """Trasforma una formula scritta (es. "x^2 sin(x)") in un'espressione SymPy."""
    originale = testo
    testo = latex_in_testo(testo)
    for simbolo, sostituto in SOSTITUZIONI.items():
        testo = testo.replace(simbolo, sostituto)
    testo = re.sub(r"\b(inf|infinito|infinity)\b", "oo", testo, flags=re.IGNORECASE)
    testo = testo.strip().strip(".;,=").strip()

    if not testo:
        raise ErroreRisolutore("Manca la formula: scrivi la funzione su cui lavorare.")
    if len(testo) > 300:
        raise ErroreRisolutore("La formula è troppo lunga (massimo 300 caratteri).")

    # Sicurezza: accettiamo solo caratteri "da formula" e solo nomi che conosciamo.
    # (SymPy per leggere la formula la esegue come codice: non deve poter contenere altro.)
    if not re.fullmatch(r"[0-9A-Za-z+\-*/^().,\s|!]+", testo):
        strani = sorted(set(re.findall(r"[^0-9A-Za-z+\-*/^().,\s|!]", testo)))
        raise ErroreRisolutore(f"Nella formula ci sono simboli che non riconosco: {' '.join(strani)}")
    # Prodotti scritti senza segno tra variabili di una lettera: "xy" diventa "x*y", "2xyz" diventa "2x*y*z".
    # Non lo facciamo se dentro c'è il nome di una funzione (es. "xsin"): lì è meglio chiedere il segno *.
    def separa(m: re.Match) -> str:
        nome = m.group(0)
        if nome.lower() in NOMI_PERMESSI or len(nome) > 3:
            return nome
        if any(funzione in nome.lower() for funzione in NOMI_PERMESSI if len(funzione) > 1):
            return nome
        return "*".join(nome)

    testo = re.sub(r"(?<![A-Za-z_])[A-Za-z]{2,3}(?![A-Za-z_(])", separa, testo)

    for nome in re.findall(r"[A-Za-z_]\w*", testo):
        if len(nome) > 1 and nome.lower() not in NOMI_PERMESSI:
            raise ErroreRisolutore(
                f'Non riconosco "{nome}" nella formula. Se è un prodotto, metti il segno *: '
                f'ad esempio x*sin(x) invece di xsin(x).'
            )

    # Valori assoluti scritti con le barre: |x| -> abs(x)
    testo = re.sub(r"\|([^|]+)\|", r"abs(\1)", testo)
    # I nomi delle funzioni valgono anche in maiuscolo (Sin, LN...)
    testo = re.sub(r"[A-Za-z_]\w+", lambda m: m.group(0).lower(), testo)

    try:
        espressione = parse_expr(testo, local_dict=dict(NOMI_PERMESSI), transformations=TRASFORMAZIONI)
    except Exception:
        raise ErroreRisolutore(
            f'Non riesco a leggere la formula "{originale.strip()}". Controlla le parentesi e usa * per i prodotti.'
        )
    if not isinstance(espressione, sympy.Expr):
        raise ErroreRisolutore(f'"{originale.strip()}" non è una formula su cui posso lavorare.')
    return espressione


# ---------- 2. Da LaTeX a formula "da calcolatrice" ----------


def _gruppo(testo: str, inizio: int) -> tuple[str, int]:
    """Dato l'indice di una graffa aperta, restituisce il contenuto fino alla graffa che la chiude."""
    livello = 0
    for i in range(inizio, len(testo)):
        if testo[i] == "{":
            livello += 1
        elif testo[i] == "}":
            livello -= 1
            if livello == 0:
                return testo[inizio + 1 : i], i + 1
    raise ErroreRisolutore("Nel LaTeX c'è una parentesi graffa che non si chiude.")


def _sostituisci_comando(testo: str, comando: str, costruisci) -> str:
    """Sostituisce \\comando{a}{b}... con ciò che restituisce la funzione "costruisci"."""
    quanti = costruisci.__code__.co_argcount
    while (posizione := testo.find(comando + "{")) != -1:
        argomenti, fine = [], posizione + len(comando)
        for _ in range(quanti):
            if fine >= len(testo) or testo[fine] != "{":
                raise ErroreRisolutore(f"Nel LaTeX il comando {comando} è incompleto.")
            argomento, fine = _gruppo(testo, fine)
            argomenti.append(argomento)
        testo = testo[:posizione] + costruisci(*argomenti) + testo[fine:]
    return testo


def latex_in_testo(testo: str) -> str:
    """Converte i comandi LaTeX più comuni nella scrittura "da calcolatrice"."""
    if "\\" not in testo and "{" not in testo:
        return testo
    testo = testo.replace("$", " ")
    # (?![A-Za-z]) = "il nome del comando finisce qui" (va bene anche se segue _ come in \lim_)
    testo = re.sub(r"\\(left|right|quad|qquad|displaystyle|mathrm|operatorname|text)(?![A-Za-z])|\\[,;!]", " ", testo)
    testo = re.sub(r"\\[dt]frac", r"\\frac", testo)
    testo = re.sub(r"\\sqrt\[([^\]]+)\]", r"\\radice{\1}", testo)  # radice n-esima
    testo = _sostituisci_comando(testo, "\\frac", lambda a, b: f"(({a})/({b}))")
    testo = _sostituisci_comando(testo, "\\radice", lambda n, a: f"(({a})^(1/({n})))")
    testo = _sostituisci_comando(testo, "\\sqrt", lambda a: f"sqrt({a})")
    testo = testo.replace("\\cdot", "*").replace("\\times", "*").replace("\\infty", "oo")
    testo = testo.replace("\\to", "->").replace("\\rightarrow", "->")
    testo = re.sub(r"\\(arcsin|arccos|arctan|sinh|cosh|tanh|sin|cos|tan|cot|ln|log|exp|pi|lim|int)(?![A-Za-z])", r" \1 ", testo)
    testo = testo.replace("\\sum", " serie ").replace("\\geq", ">=").replace("\\ge", ">=")
    testo = testo.replace("\\iint", " integrale doppio di ").replace("\\nabla", " gradiente di ")
    testo = testo.replace("\\leq", "<=").replace("\\le", "<=")
    testo = re.sub(r"\\[A-Za-z]+", " ", testo)  # comandi sconosciuti: li togliamo
    # Le graffe rimaste (es. in x^{2}) diventano parentesi tonde
    return testo.replace("{", "(").replace("}", ")")


# ---------- 3. Dalla frase al Problema ----------


def _senza_accenti(testo: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", testo) if unicodedata.category(c) != "Mn")


def _leggi_punto(testo: str) -> tuple[sympy.Expr, str]:
    """Legge il punto a cui tende la variabile. Restituisce (punto, direzione)."""
    testo = testo.strip().strip("()").replace(" ", "")
    testo = re.sub(r"(piu|più)", "+", testo)
    testo = re.sub(r"meno", "-", testo)
    direzione = "+-"
    # 0+  0^+  0-  0^-  indicano limite destro o sinistro
    if (m := re.fullmatch(r"(.+?)\^?\(?([+-])\)?", testo)) and re.search(r"[0-9a-z)]$", m.group(1)):
        testo, direzione = m.group(1), m.group(2)
    punto = leggi_espressione(testo)
    if punto.free_symbols:
        raise ErroreRisolutore(f'Il punto del limite deve essere un numero, non "{testo}".')
    return punto, direzione


FRECCIA = r"(?:->|→|⟶|che\s+tende\s+a|tendente\s+a|tende\s+a)"


def _come_limite(testo: str) -> Problema | None:
    # Frase con la funzione prima: "limite di sin(x)/x per x che tende a 0"
    if m := re.search(
        rf"lim(?:ite)?\s+(?:di|della funzione)\s+(.+?)\s+(?:per|quando|con)\s+([a-z])\s*{FRECCIA}\s*(\S+)\s*$",
        testo,
        re.I | re.S,
    ):
        funzione, variabile, punto = m.group(1), m.group(2), m.group(3)
    # Scrittura LaTeX: lim_(x -> 0) ...   (le graffe sono già diventate parentesi)
    elif m := re.search(
        rf"lim\s*_?\s*\(\s*([a-z])\s*{FRECCIA}\s*([^()]*(?:\([^()]*\))?[^()]*)\)\s*(.+)", testo, re.I | re.S
    ):
        variabile, punto, funzione = m.group(1), m.group(2), m.group(3)
    # Frase: "limite per x che tende a 0 di ..."  /  "lim x->0 ..."
    elif m := re.search(
        rf"lim(?:ite)?\b.*?\b([a-z])\s*{FRECCIA}\s*([^\s,]+)(?:\s*,\s*|\s+)(?:(?:di|della funzione)\b)?\s*(.+)",
        testo,
        re.I | re.S,
    ):
        variabile, punto, funzione = m.group(1), m.group(2), m.group(3)
    else:
        return None

    punto_letto, direzione = _leggi_punto(punto)
    return Problema(
        tipo="limite",
        funzione=leggi_espressione(_pulisci_funzione(funzione)),
        variabile=sympy.Symbol(variabile.lower()),
        punto=punto_letto,
        direzione=direzione,
    )


def _come_integrale(testo: str) -> Problema | None:
    if not re.search(r"integra|∫|\bint\b", testo, re.I):
        return None
    a = b = None
    resto = testo

    # Estremi in LaTeX: int_(0)^(1)  oppure  int_0^1
    if m := re.search(r"(?:∫|\bint)\s*_\s*(\([^()]*\)|\S+?)\s*\^\s*(\([^()]*\)|[^\s(]+)\s*(.+)", testo, re.I | re.S):
        a, b, resto = m.group(1), m.group(2), m.group(3)
    # Estremi a parole: "da 0 a 1", "tra 0 e 1", "fra 0 e pi"
    elif m := re.search(r"\b(?:da|tra|fra)\s+(\S+)\s+(?:a|e|ad)\s+(\S+)", testo, re.I):
        a, b = m.group(1), m.group(2)
        resto = testo[: m.start()] + " " + testo[m.end() :]

    # La funzione è ciò che segue "integrale ... di" oppure il simbolo di integrale
    if m := re.search(r"integra\w*.*?\b(?:di|della funzione)\b\s*(.+)", resto, re.I | re.S):
        resto = m.group(1)
    else:
        resto = re.sub(r"^.*?(?:∫|\bint\b|integra\w*)", "", resto, flags=re.I | re.S)

    # Il "dx" finale dice qual è la variabile di integrazione
    variabile = "x"
    if m := re.search(r"\bd\s*([a-z])\s*[.;]?\s*$", resto.strip(), re.I):
        variabile = m.group(1).lower()
        resto = resto.strip()[: m.start()]

    problema = Problema(
        tipo="integrale",
        funzione=leggi_espressione(_pulisci_funzione(resto)),
        variabile=sympy.Symbol(variabile),
    )
    if a is not None:
        problema.estremo_a = leggi_espressione(a)
        problema.estremo_b = leggi_espressione(b)
        if problema.estremo_a.free_symbols or problema.estremo_b.free_symbols:
            raise ErroreRisolutore("Gli estremi di integrazione devono essere numeri.")
    return problema


ORDINI = {"prima": 1, "seconda": 2, "terza": 3, "quarta": 4}


def _come_derivata(testo: str) -> Problema | None:
    if not re.search(r"deriva|\bd\s*/\s*d[a-z]\b", testo, re.I):
        return None
    ordine = next((n for parola, n in ORDINI.items() if re.search(rf"\b{parola}\b", testo, re.I)), 1)
    variabile = "x"
    if m := re.search(r"rispetto\s+ad?\s+([a-z])\b", testo, re.I):
        variabile = m.group(1).lower()
        testo = testo[: m.start()] + " " + testo[m.end() :]
    elif m := re.search(r"\bd\s*/\s*d([a-z])\b", testo, re.I):
        variabile = m.group(1).lower()

    if m := re.search(r"deriva\w*.*?\b(?:di|della funzione)\b\s*(.+)", testo, re.I | re.S):
        resto = m.group(1)
    else:
        resto = re.sub(r"^.*?(?:deriva\w*(?:\s+(?:prima|seconda|terza|quarta))?|\bd\s*/\s*d[a-z]\b)", "", testo, flags=re.I | re.S)

    return Problema(
        tipo="derivata",
        funzione=leggi_espressione(_pulisci_funzione(resto)),
        variabile=sympy.Symbol(variabile),
        ordine=ordine,
    )


def _pulisci_funzione(testo: str) -> str:
    """Toglie ciò che sta attorno alla formula: "f(x) =", "la funzione", il punto finale..."""
    testo = testo.strip()
    testo = re.sub(r"^(?:della\s+|la\s+)?funzione\s+", "", testo, flags=re.I)
    testo = re.sub(r"^[a-z]\s*\(\s*[a-z](?:\s*,\s*[a-z])*\s*\)\s*=", "", testo, flags=re.I)  # f(x) =  oppure  f(x,y) =
    testo = re.sub(r"^[a-z]\s*=", "", testo, flags=re.I)  # y =  oppure  z =
    return testo.strip().rstrip(".;,")


# ---------- Analisi II: funzioni di due variabili ----------

# Parole che separano la funzione dal resto della frase ("... con vincolo", "... su [0,1]x[0,2]")
SEPARATORE = r"\s+(?:con|su|sul|sulla|sotto|per|dove|nel|soggett\w+|vincolat\w+|in\s+cui)\b|,\s"


def _funzione_dopo(testo: str, schema: str) -> str | None:
    """Estrae la funzione che segue le parole indicate da "schema" (es. "gradiente ... di")."""
    m = re.search(schema + r".*?\b(?:di|della\s+funzione)\b\s*(.+)", testo, re.I | re.S)
    if not m:
        return None
    return re.split(SEPARATORE, m.group(1), maxsplit=1, flags=re.I)[0]


def _come_gradiente(testo: str) -> Problema | None:
    if not re.search(r"gradiente|parzial", testo, re.I):
        return None
    funzione = _funzione_dopo(testo, r"(?:gradiente|parzial\w+)")
    if funzione is None:
        return None
    return Problema(tipo="gradiente", funzione=leggi_espressione(_pulisci_funzione(funzione)), variabile=sympy.Symbol("x"))


def _come_critici(testo: str) -> Problema | None:
    schema = r"(?:punt\w+\s+(?:critic\w+|stazionar\w+)|massim\w+|minim\w+|estrem\w+)"
    if not re.search(schema, testo, re.I):
        return None
    funzione = _funzione_dopo(testo, schema)
    if funzione is None:
        return None
    return Problema(tipo="critici", funzione=leggi_espressione(_pulisci_funzione(funzione)), variabile=sympy.Symbol("x"))


def _come_vincolati(testo: str) -> Problema | None:
    m = re.search(r"(?:vincolo|vincolat\w+\s+(?:a|da)|soggett\w+\s+a|condizione)\s*(?:dato\s+da)?\s*:?\s*([^=]+)=([^=]+)$", testo, re.I | re.S)
    if not m:
        return None
    funzione = _funzione_dopo(testo[: m.start()] + " ", r"(?:massim\w+|minim\w+|estrem\w+|ottimizz\w+)")
    if funzione is None:
        raise ErroreRisolutore('Non ho capito di quale funzione cercare massimi e minimi: scrivi "massimi e minimi di x*y con vincolo x^2 + y^2 = 1".')
    sinistra, destra = leggi_espressione(m.group(1)), leggi_espressione(m.group(2))
    return Problema(
        tipo="vincolati",
        funzione=leggi_espressione(_pulisci_funzione(funzione)),
        variabile=sympy.Symbol("x"),
        vincolo=sinistra - destra,
        vincolo_latex=f"{sympy.latex(sinistra)} = {sympy.latex(destra)}",
    )


def _come_doppio(testo: str) -> Problema | None:
    if not re.search(r"integrale\s+doppio|∬", testo, re.I):
        return None
    estremi: dict[str, tuple[str, str]] = {}

    # Rettangolo scritto come [0,1]x[0,2]: il primo intervallo è per x, il secondo per y
    if m := re.search(r"\[\s*([^,\]]+),\s*([^,\]]+)\]\s*[x×*]\s*\[\s*([^,\]]+),\s*([^,\]]+)\]", testo, re.I):
        estremi = {"x": (m.group(1), m.group(2)), "y": (m.group(3), m.group(4))}
        testo = testo[: m.start()] + " " + testo[m.end() :]
    # "x da 0 a 1", "y tra 0 e x"
    for m in re.finditer(r"\b([a-z])\s+(?:da|tra|fra|compres[ao]\s+tra)\s+(\S+)\s+(?:a|e|ad)\s+(\S+)", testo, re.I):
        estremi[m.group(1).lower()] = (m.group(2), m.group(3))
    # "0 <= x <= 1"
    for m in re.finditer(r"(\S+)\s*(?:<=|≤|<)\s*([a-z])\s*(?:<=|≤|<)\s*(\S+)", testo, re.I):
        estremi[m.group(2).lower()] = (m.group(1), m.group(3))

    if len(estremi) != 2:
        raise ErroreRisolutore(
            "Per un integrale doppio servono gli estremi di entrambe le variabili. Scrivi ad esempio "
            '"integrale doppio di x*y con x da 0 a 1 e y da 0 a x" oppure "integrale doppio di x*y su [0,1]x[0,2]".'
        )

    # La funzione è ciò che segue "integrale doppio (di)", fino alle parole che introducono il dominio
    resto = re.split(r"integrale\s+doppio(?:\s+di|\s+della\s+funzione)?|∬", testo, maxsplit=1, flags=re.I)[1]
    resto = re.split(SEPARATORE + r"|\bd\s*[a-z]\s*d\s*[a-z]\b|\b[a-z]\s+(?:da|tra|fra)\s|\S+\s*(?:<=|≤)", resto, maxsplit=1, flags=re.I)[0]
    funzione = leggi_espressione(_pulisci_funzione(resto))

    letti = {sympy.Symbol(nome): (leggi_espressione(a.strip(".,;")), leggi_espressione(b.strip(".,;"))) for nome, (a, b) in estremi.items()}
    (v1, e1), (v2, e2) = sorted(letti.items(), key=lambda coppia: str(coppia[0]))
    liberi1 = e1[0].free_symbols | e1[1].free_symbols
    liberi2 = e2[0].free_symbols | e2[1].free_symbols
    # La variabile esterna è quella con gli estremi numerici; l'altra può dipendere da lei
    if not liberi1 and liberi2 <= {v1}:
        esterna, interna, est, int_ = v1, v2, e1, e2
    elif not liberi2 and liberi1 <= {v2}:
        esterna, interna, est, int_ = v2, v1, e2, e1
    else:
        raise ErroreRisolutore(
            "Non riesco a interpretare il dominio: una variabile deve avere estremi numerici, "
            "e gli estremi dell'altra possono dipendere solo dalla prima."
        )
    if funzione.free_symbols - {esterna, interna}:
        raise ErroreRisolutore(f"La funzione deve dipendere solo da {esterna} e {interna}.")
    return Problema(
        tipo="doppio", funzione=funzione, variabile=esterna, estremo_a=est[0], estremo_b=est[1],
        interna=interna, interno_a=int_[0], interno_b=int_[1], variabili=(v1, v2),
    )  # fmt: skip


def _controlla_due_variabili(problema: Problema) -> Problema:
    """Controlli per gli esercizi di Analisi II: quante variabili ha la funzione?"""
    if problema.tipo == "doppio":
        return problema
    simboli = problema.funzione.free_symbols
    if problema.vincolo is not None:
        simboli = simboli | problema.vincolo.free_symbols
    variabili = tuple(sorted(simboli, key=str))

    if problema.tipo == "gradiente":
        if len(variabili) < 2:
            raise ErroreRisolutore('Questa funzione ha una sola variabile: per derivarla scrivi "derivata di ...".')
        if len(variabili) > 3:
            raise ErroreRisolutore("Calcolo il gradiente di funzioni con al massimo tre variabili.")
    elif len(variabili) < 2:
        raise ErroreRisolutore(
            "Questa è una funzione di una sola variabile: per massimi e minimi usa lo Studio di funzione "
            "nella pagina Grafici. Qui cerco i punti critici delle funzioni di due variabili, es. x^2 + y^2."
        )
    elif len(variabili) > 2:
        nomi = ", ".join(str(v) for v in variabili)
        raise ErroreRisolutore(f"Per ora lavoro con funzioni di due variabili, qui ne trovo di più ({nomi}).")
    problema.variabili = variabili
    return problema


# ---------- serie numeriche ed equazioni differenziali ----------


def _come_serie(testo: str) -> Problema | None:
    if not re.search(r"\bserie\b|∑|\bsum\b|sommatoria", testo, re.I):
        return None
    # Indice di partenza: "n = 1", "n da 1", "n >= 1" (se manca, si parte da 1)
    inizio = 1
    if m := re.search(r"\bn\s*(?:=|>=|≥|da)\s*(\d+)", testo, re.I):
        inizio = int(m.group(1))
    # Togliamo le indicazioni sull'indice: "_(n=1)^(oo)", "per n da 1 a +oo", "n >= 1"
    t = re.sub(r"_?\s*\(?\s*n\s*=\s*\d+\s*\)?\s*\^\s*\(?\s*\+?oo\s*\)?", " ", testo, flags=re.I)
    t = re.sub(r"\b(?:per|con|da)\s+n\s*(?:=|>=|≥|da|che\s+va\s+da)\s*\d+(?:\s*(?:a|fino\s+a)\s*\+?oo)?", " ", t, flags=re.I)
    t = re.sub(r"\bn\s*(?:=|>=|≥)\s*\d+", " ", t, flags=re.I)
    # Il termine generale è ciò che segue l'ultima di queste parole
    pezzi = re.split(
        r"termine\s+generale|\btermine\b|a_n\s*=|serie\s+(?:numerica\s+)?(?:di\s+|della\s+)?|\bsum\b|∑|sommatoria\s+(?:di\s+)?",
        t,
        flags=re.I,
    )
    termine = re.sub(r"^\s*(?:di|del|:)\s+", "", pezzi[-1])
    funzione = leggi_espressione(_pulisci_funzione(termine))
    n = sympy.Symbol("n")
    if funzione.free_symbols - {n}:
        raise ErroreRisolutore('Scrivi il termine della serie in funzione di n, ad esempio "serie di termine 1/n^2".')
    return Problema(tipo="serie", funzione=funzione, variabile=n, estremo_a=sympy.Integer(inizio))


def _come_edo(testo: str) -> Problema | None:
    # Uniformiamo i vari modi di scrivere la derivata: y′, y’, dy/dx, d^2y/dx^2
    t = testo.replace("’", "'").replace("′", "'").replace("″", "''").replace("`", "'")
    t = re.sub(r"d\s*\^\s*\(?2\)?\s*y\s*/\s*d\s*[a-z]\s*\^\s*\(?2\)?", "y''", t, flags=re.I)
    variabile = "t" if re.search(r"dy\s*/\s*dt|y\s*'*\s*\(\s*t\s*\)", t, re.I) else "x"
    t = re.sub(r"\bdy\s*/\s*d[a-z]\b", "y'", t, flags=re.I)
    t = re.sub(r"y\s+'", "y'", t)
    if "y'" not in t:
        return None
    # y(x) e y'(x) si scrivono semplicemente y e y'
    t = re.sub(rf"y('*)\s*\(\s*{variabile}\s*\)", r"y\1", t)

    # Condizioni iniziali: y(0) = 1, y'(0) = 2. Le leggiamo e le togliamo dal testo.
    condizioni: list[tuple[int, sympy.Expr, sympy.Expr]] = []

    def prendi(m: re.Match) -> str:
        condizioni.append((len(m.group(1)), leggi_espressione(m.group(2)), leggi_espressione(m.group(3))))
        return " "

    t = re.sub(r"y('{0,2})\s*\(\s*([^()]+?)\s*\)\s*=\s*([^,;=]+?)(?=\s*(?:,|;|\be\b\s+y|\bcon\b|$))", prendi, t)

    # Togliamo le parole attorno all'equazione
    for _ in range(3):
        t = re.sub(r"^.*?(?:equazione\s+differenziale|problema\s+di\s+cauchy|risolv\w+|\bedo\b|\bode\b)\s*:?\s*", "", t, count=1, flags=re.I)
    contorno = r"(?:[\s,;.:]|\b(?:con|e|dove|condizion\w+|inizial\w+|dat\w+)\b)+"
    t = re.sub("^" + contorno, "", t)
    t = re.sub(contorno + "$", "", t)

    if t.count("=") != 1:
        raise ErroreRisolutore("Scrivi l'equazione differenziale con un solo segno di uguale, ad esempio y' + 2y = e^x.")

    def leggi(lato: str) -> sympy.Expr:
        # U e W sono segnaposto per y' e y'' (gli apostrofi non sono ammessi nelle formule)
        lato = lato.replace("y''", " W ").replace("y'", " U ")
        espressione = leggi_espressione(lato)
        return espressione.subs({sympy.Symbol("U"): sympy.Symbol("y'"), sympy.Symbol("W"): sympy.Symbol("y''")})

    sinistra, destra = (leggi(lato) for lato in t.split("="))
    x = sympy.Symbol(variabile)
    ammessi = {x, sympy.Symbol("y"), sympy.Symbol("y'"), sympy.Symbol("y''")}
    estranei = (sinistra.free_symbols | destra.free_symbols) - ammessi
    if estranei:
        nomi = ", ".join(sorted(str(s) for s in estranei))
        raise ErroreRisolutore(f"Nell'equazione possono comparire solo {variabile}, y, y' e y'': qui trovo anche {nomi}.")
    return Problema(
        tipo="edo",
        funzione=sinistra - destra,
        variabile=x,
        condizioni=tuple(sorted(condizioni, key=lambda c: c[0])),
        equazione_latex=f"{_latex_edo(sinistra)} = {_latex_edo(destra)}",
    )


def _latex_edo(espressione: sympy.Expr) -> str:
    """Scrive un membro dell'equazione mettendo prima y'', poi y', poi y, come si fa di solito."""

    def ordine(termine: sympy.Expr) -> int:
        nomi = {str(s) for s in termine.free_symbols}
        return 0 if "y''" in nomi else 1 if "y'" in nomi else 2 if "y" in nomi else 3

    termini = sorted(sympy.Add.make_args(espressione), key=ordine)
    testo = sympy.latex(termini[0], ln_notation=True)
    for termine in termini[1:]:
        if termine.could_extract_minus_sign():
            testo += " - " + sympy.latex(-termine, ln_notation=True)
        else:
            testo += " + " + sympy.latex(termine, ln_notation=True)
    return testo


def interpreta(testo: str, tipo: str = "auto") -> Problema:
    """
    Capisce che esercizio è. "tipo" può essere "auto" (prova a capirlo dalla frase)
    oppure "limite", "derivata", "integrale" (scelto dallo studente nel menu).
    """
    if not testo or not testo.strip():
        raise ErroreRisolutore("Scrivi un esercizio da risolvere.")
    # Lavoriamo su una copia semplificata: senza accenti, LaTeX convertito, spazi puliti
    pulito = _senza_accenti(latex_in_testo(testo))
    # (il punto esclamativo non si toglie: in una formula è il fattoriale, es. 1/n!)
    pulito = re.sub(r"\s+", " ", pulito).strip().rstrip(".;,?")
    # "più infinito", "+ infinito", "meno infinito" -> +oo, -oo
    pulito = re.sub(r"(?:\bpiu|\+)\s*(?:infinito|inf|oo|∞)\b", "+oo", pulito, flags=re.I)
    pulito = re.sub(r"(?:\bmeno|-)\s*(?:infinito|inf|oo|∞)\b", "-oo", pulito, flags=re.I)
    pulito = re.sub(r"\binfinito\b|∞", "oo", pulito, flags=re.I)

    # L'ordine conta: i casi più specifici vanno provati prima
    # (es. "integrale doppio" prima di "integrale", "derivate parziali" prima di "derivata").
    tentativi = {
        "edo": _come_edo,
        "serie": _come_serie,
        "doppio": _come_doppio,
        "vincolati": _come_vincolati,
        "critici": _come_critici,
        "gradiente": _come_gradiente,
        "limite": _come_limite,
        "integrale": _come_integrale,
        "derivata": _come_derivata,
    }
    due_variabili = ("doppio", "vincolati", "critici", "gradiente")

    def controlla(problema: Problema) -> Problema:
        if problema.tipo in ("serie", "edo"):
            return problema  # già controllati mentre venivano letti
        return _controlla_due_variabili(problema) if problema.tipo in due_variabili else _controlla(problema)

    if tipo == "auto":
        for prova in tentativi.values():
            if problema := prova(pulito):
                return controlla(problema)
        raise ErroreRisolutore(
            "Non ho capito cosa devo calcolare. Scrivi ad esempio "
            '"limite per x che tende a 0 di sin(x)/x", "derivata di x^2*sin(x)", '
            '"integrale di x*e^x" oppure "punti critici di x^2 + y^2", '
            "oppure scegli il tipo di esercizio dal menu."
        )

    if tipo not in tentativi:
        raise ErroreRisolutore(f"Tipo di esercizio non valido: {tipo}")

    # Tipo scelto dal menu: prima proviamo a leggere la frase, altrimenti il testo è la sola formula
    if problema := tentativi[tipo](pulito):
        return controlla(problema)
    if tipo == "limite":
        raise ErroreRisolutore('Per un limite devo sapere dove tende la variabile: scrivi ad esempio "x -> 0 sin(x)/x".')
    if tipo == "vincolati":
        raise ErroreRisolutore('Manca il vincolo: scrivi ad esempio "massimi e minimi di x*y con vincolo x^2 + y^2 = 1".')
    if tipo == "doppio":
        raise ErroreRisolutore('Scrivi ad esempio "integrale doppio di x*y con x da 0 a 1 e y da 0 a x".')
    if tipo == "edo":
        raise ErroreRisolutore("Scrivi l'equazione con la derivata indicata dall'apostrofo, ad esempio y' = x*y oppure y'' + y = 0.")
    if tipo == "serie":
        # Dal menu basta scrivere il termine generale, es. 1/n^2
        return _come_serie("serie di termine " + pulito)
    return controlla(Problema(tipo=tipo, funzione=leggi_espressione(_pulisci_funzione(pulito)), variabile=sympy.Symbol("x")))


def _controlla(problema: Problema) -> Problema:
    """Ultimi controlli: la funzione deve dipendere da una sola variabile."""
    altre = problema.funzione.free_symbols - {problema.variabile}
    if altre:
        # Caso tipico: lo studente ha usato t ma la variabile sottintesa era x
        if len(problema.funzione.free_symbols) == 1 and problema.tipo != "limite":
            problema.variabile = next(iter(problema.funzione.free_symbols))
        else:
            nomi = ", ".join(sorted(str(s) for s in altre))
            raise ErroreRisolutore(
                f"Nella funzione compaiono altre lettere oltre a {problema.variabile} ({nomi}). "
                "Per ora risolvo solo esercizi in una variabile, senza parametri."
            )
    return problema
