"""
L'elenco dei concetti che il risolutore sa usare (teoremi, regole, metodi).

Per ogni concetto servono:
- nome:    come lo chiamiamo nella spiegazione;
- domanda: la frase con cui lo cerchiamo "per significato" nel Magazzino;
- parole:  parole chiave (senza accenti) che un blocco deve contenere perché possiamo
           citarlo come fonte. Così non citiamo mai un blocco che parla d'altro.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Concetto:
    nome: str
    domanda: str
    parole: tuple[str, ...]


CONCETTI: dict[str, Concetto] = {
    # ----- limiti -----
    "continuita": Concetto(
        "continuità (sostituzione diretta)",
        "funzione continua: il limite coincide con il valore della funzione nel punto",
        ("continu", "sostituzione diretta"),
    ),
    "forma_indeterminata": Concetto(
        "forme indeterminate",
        "forme indeterminate 0/0 e infinito su infinito",
        ("forma indeterminata", "forme indeterminate"),
    ),
    "limite_infinito": Concetto(
        "limite del rapporto quando il denominatore tende a zero",
        "limite infinito, denominatore che tende a zero, asintoto verticale",
        ("asintoto verticale", "limite infinito", "diverge", "tende a zero il denominatore", "denominatore tende a 0"),
    ),
    "scomposizione": Concetto(
        "scomposizione e semplificazione",
        "scomporre in fattori numeratore e denominatore e semplificare il fattore comune",
        ("scompo", "semplific", "fattorizz", "raccogli"),
    ),
    "gradi": Concetto(
        "confronto tra i gradi (raccoglimento del termine di grado massimo)",
        "limite all'infinito di un rapporto di polinomi, termine di grado massimo",
        ("grado massimo", "gradi", "raccogli", "ordine di infinito", "gerarchia degli infiniti"),
    ),
    "hopital": Concetto(
        "teorema di de l'Hôpital",
        "teorema di de l'Hopital per le forme indeterminate",
        ("hopital", "hospital"),
    ),
    "asintotico": Concetto(
        "limiti notevoli e sviluppi asintotici",
        "limiti notevoli, equivalenze asintotiche, sviluppo di Taylor",
        ("limite notevole", "limiti notevoli", "asintotic", "taylor", "maclaurin", "mclaurin"),
    ),
    # ----- studio di funzione -----
    "dominio": Concetto(
        "dominio di una funzione",
        "dominio o campo di esistenza di una funzione",
        ("dominio", "campo di esistenza", "insieme di definizione"),
    ),
    "simmetrie": Concetto(
        "funzioni pari, dispari e periodiche",
        "funzione pari, funzione dispari, simmetrie del grafico, periodicità",
        ("funzione pari", "funzioni pari", "dispari", "simmetri", "periodic"),
    ),
    "intersezioni": Concetto(
        "intersezioni con gli assi",
        "intersezioni del grafico con gli assi cartesiani, zeri della funzione",
        ("intersezion", "zeri della funzione", "zeri di una funzione"),
    ),
    "segno": Concetto(
        "studio del segno",
        "studio del segno di una funzione, dove è positiva e dove negativa",
        ("studio del segno", "segno della funzione", "segno di una funzione", "positivita"),
    ),
    "asintoti": Concetto(
        "asintoti",
        "asintoti verticali, orizzontali e obliqui",
        ("asintot",),
    ),
    "monotonia": Concetto(
        "crescenza, massimi e minimi",
        "funzione crescente e decrescente, punti stazionari, massimi e minimi relativi, segno della derivata prima",
        ("massimi e minimi", "massimo relativo", "minimo relativo", "punti stazionari", "punto stazionario", "crescente", "monotonia", "fermat"),
    ),
    "concavita": Concetto(
        "concavità e flessi",
        "concavità, convessità e punti di flesso, segno della derivata seconda",
        ("concav", "convess", "flesso", "flessi"),
    ),
    # ----- Analisi II: funzioni di due variabili -----
    "derivate_parziali": Concetto(
        "derivate parziali",
        "derivate parziali di una funzione di più variabili",
        ("derivata parziale", "derivate parziali"),
    ),
    "gradiente": Concetto(
        "gradiente",
        "gradiente di una funzione di più variabili, vettore delle derivate parziali",
        ("gradiente",),
    ),
    "punti_critici": Concetto(
        "punti critici (gradiente nullo)",
        "punti critici o stazionari di una funzione di due variabili, condizione necessaria gradiente nullo",
        ("punti critici", "punto critico", "punti stazionari", "punto stazionario", "gradiente nullo", "fermat"),
    ),
    "hessiana": Concetto(
        "matrice hessiana e classificazione dei punti critici",
        "matrice hessiana, determinante hessiano, classificazione di massimi minimi e punti di sella",
        ("hessian",),
    ),
    "lagrange": Concetto(
        "moltiplicatori di Lagrange",
        "massimi e minimi vincolati, metodo dei moltiplicatori di Lagrange",
        ("lagrange", "moltiplicator"),
    ),
    "weierstrass": Concetto(
        "teorema di Weierstrass",
        "teorema di Weierstrass: una funzione continua su un insieme chiuso e limitato ha massimo e minimo",
        ("weierstrass",),
    ),
    "integrale_doppio": Concetto(
        "integrali doppi e formule di riduzione",
        "integrale doppio su un dominio normale, formule di riduzione, teorema di Fubini",
        ("integrale doppio", "integrali doppi", "formule di riduzione", "fubini", "dominio normale", "domini normali"),
    ),
    # ----- serie numeriche -----
    "condizione_necessaria": Concetto(
        "condizione necessaria di convergenza",
        "condizione necessaria per la convergenza di una serie: il termine generale tende a zero",
        ("condizione necessaria", "termine generale tende", "termine generale infinitesimo"),
    ),
    "serie_geometrica": Concetto(
        "serie geometrica",
        "serie geometrica di ragione q, converge se il modulo della ragione è minore di uno",
        ("serie geometric",),
    ),
    "serie_armonica": Concetto(
        "serie armonica generalizzata",
        "serie armonica generalizzata 1/n^p, converge se p maggiore di uno",
        ("serie armonic", "armonica generalizzata"),
    ),
    "criterio_rapporto": Concetto(
        "criterio del rapporto",
        "criterio del rapporto per le serie a termini positivi",
        ("criterio del rapporto", "d'alembert"),
    ),
    "confronto_asintotico": Concetto(
        "criterio del confronto asintotico",
        "criterio del confronto asintotico per le serie a termini positivi",
        ("confronto asintotico", "criterio del confronto"),
    ),
    "convergenza_assoluta": Concetto(
        "convergenza assoluta",
        "convergenza assoluta di una serie: se converge la serie dei valori assoluti allora converge la serie",
        ("convergenza assoluta", "assolutamente convergente", "converge assolutamente"),
    ),
    "leibniz": Concetto(
        "criterio di Leibniz",
        "criterio di Leibniz per le serie a segni alterni",
        ("leibniz", "segni alterni", "segno alterno"),
    ),
    # ----- equazioni differenziali -----
    "edo_separabili": Concetto(
        "equazioni a variabili separabili",
        "equazioni differenziali del primo ordine a variabili separabili",
        ("variabili separabili",),
    ),
    "edo_lineari_primo": Concetto(
        "equazioni lineari del primo ordine",
        "equazioni differenziali lineari del primo ordine, fattore integrante, formula risolutiva",
        ("lineare del primo ordine", "lineari del primo ordine", "fattore integrante"),
    ),
    "edo_caratteristica": Concetto(
        "equazione caratteristica (secondo ordine a coefficienti costanti)",
        "equazioni differenziali lineari del secondo ordine a coefficienti costanti omogenee, equazione caratteristica",
        ("equazione caratteristica", "coefficienti costanti", "omogenea associata"),
    ),
    "edo_particolare": Concetto(
        "soluzione particolare (metodo di somiglianza)",
        "equazione non omogenea: soluzione particolare con il metodo di somiglianza",
        ("soluzione particolare", "metodo di somiglianza", "non omogenea"),
    ),
    "problema_cauchy": Concetto(
        "problema di Cauchy",
        "problema di Cauchy: condizioni iniziali per determinare le costanti",
        ("problema di cauchy", "condizioni iniziali", "condizione iniziale"),
    ),
    # ----- derivate -----
    "derivate_elementari": Concetto(
        "derivate delle funzioni elementari",
        "tabella delle derivate fondamentali delle funzioni elementari",
        ("derivate elementari", "derivate fondamentali", "tabella delle derivate", "derivate delle funzioni elementari", "derivata di x^", "derivata della potenza"),
    ),
    "derivata_somma": Concetto(
        "linearità della derivata",
        "derivata della somma e del prodotto per una costante, linearità",
        ("derivata della somma", "derivata di una somma", "linearita della deriva", "regole di derivazione"),
    ),
    "derivata_prodotto": Concetto(
        "derivata del prodotto",
        "regola di derivazione del prodotto di due funzioni",
        ("derivata del prodotto", "derivata di un prodotto", "regola del prodotto", "leibniz", "regole di derivazione"),
    ),
    "derivata_quoziente": Concetto(
        "derivata del quoziente",
        "regola di derivazione del quoziente di due funzioni",
        ("derivata del quoziente", "derivata di un quoziente", "derivata del rapporto", "regola del quoziente", "regole di derivazione"),
    ),
    "derivata_composta": Concetto(
        "derivata della funzione composta",
        "derivata della funzione composta, regola della catena",
        ("funzione composta", "funzioni composte", "regola della catena"),
    ),
    # ----- integrali -----
    "integrali_immediati": Concetto(
        "integrali immediati",
        "tabella degli integrali immediati, primitive delle funzioni elementari",
        ("integrali immediati", "integrale immediato", "primitive elementari", "tabella degli integrali", "primitive fondamentali", "integrali elementari"),
    ),
    "integrale_linearita": Concetto(
        "linearità dell'integrale",
        "linearità dell'integrale: integrale della somma e costante fuori dall'integrale",
        ("linearita dell'integrale", "integrale della somma", "integrale di una somma", "linearita"),
    ),
    "integrale_parti": Concetto(
        "integrazione per parti",
        "formula di integrazione per parti",
        ("per parti",),
    ),
    "integrale_sostituzione": Concetto(
        "integrazione per sostituzione",
        "integrazione per sostituzione, cambio di variabile",
        ("per sostituzione", "cambio di variabile", "cambiamento di variabile"),
    ),
    "integrale_riscrittura": Concetto(
        "riscrittura dell'integranda",
        "riscrivere l'integranda con identità trigonometriche o algebriche prima di integrare",
        ("formule di bisezione", "formule di duplicazione", "identita trigonometric", "fratti semplici", "completamento del quadrato"),
    ),
    "teorema_fondamentale": Concetto(
        "teorema fondamentale del calcolo integrale",
        "teorema fondamentale del calcolo integrale, formula di Torricelli-Barrow",
        ("teorema fondamentale", "torricelli", "barrow"),
    ),
}
