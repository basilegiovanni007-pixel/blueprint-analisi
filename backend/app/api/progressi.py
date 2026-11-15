"""
Sportello "progressi": giorni di studio consecutivi, statistiche e traguardi.

Ogni volta che lo studente risolve un esercizio o risponde bene in "Mettimi alla prova"
viene registrata un'Attivita. Da queste si calcolano:
- la serie di giorni di studio (quanti giorni di fila, fino a oggi, con almeno un'attività);
- i traguardi, come "10 esercizi di Integrali" o "7 giorni di fila".
Un traguardo raggiunto viene salvato e non si perde più.
"""

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlmodel import Session, func, select

from app import config
from app.db.modelli import Attivita, Documento, Esercizio, TraguardoOttenuto
from app.db.sessione import apri_sessione

router = APIRouter(prefix="/api/progressi", tags=["progressi"])

GIORNI_CALENDARIO = 15 * 7  # il calendario mostra le ultime 15 settimane


def registra(sessione: Session, tipo: str, argomento: str | None = None, esercizio_id: int | None = None) -> None:
    """Annota un'attività di studio (chiamata dal Risolutore e da "Mettimi alla prova")."""
    adesso = datetime.now()
    sessione.add(
        Attivita(
            giorno=adesso.date().isoformat(),
            momento=adesso.isoformat(timespec="seconds"),
            tipo=tipo,
            argomento=argomento,
            esercizio_id=esercizio_id,
        )
    )
    sessione.commit()


def calcola_serie(giorni: set[date], oggi: date) -> tuple[int, int]:
    """
    Restituisce (serie attuale, record).
    La serie attuale conta i giorni consecutivi fino a oggi; se oggi non hai ancora studiato,
    la serie di ieri è ancora "viva" (hai tempo fino a stasera per allungarla).
    """
    attuale = 0
    giorno = oggi if oggi in giorni else oggi - timedelta(days=1)
    while giorno in giorni:
        attuale += 1
        giorno -= timedelta(days=1)

    record, corrente, precedente = 0, 0, None
    for g in sorted(giorni):
        corrente = corrente + 1 if precedente is not None and g - precedente == timedelta(days=1) else 1
        record = max(record, corrente)
        precedente = g
    return attuale, record


# ---------- definizione dei traguardi ----------


@dataclass(frozen=True)
class Traguardo:
    chiave: str
    titolo: str
    descrizione: str
    simbolo: str  # mostrato nel "timbro" del traguardo
    obiettivo: int
    misura: str  # nome della statistica che fa avanzare il traguardo


SIMBOLI_ARGOMENTO = {
    "Limiti": "lim",
    "Derivate": "d/dx",
    "Integrali": "∫",
    "Serie": "Σ",
    "Equazioni differenziali": "y′",
    "Funzioni di più variabili": "∇",
    "Integrali multipli": "∬",
}

TRAGUARDI: list[Traguardo] = [
    Traguardo("esercizi_1", "Primo progetto", "Risolvi il tuo primo esercizio.", "01", 1, "esercizi"),
    Traguardo("esercizi_10", "Dieci tavole", "Risolvi 10 esercizi diversi.", "10", 10, "esercizi"),
    Traguardo("esercizi_50", "Archivio tecnico", "Risolvi 50 esercizi diversi.", "50", 50, "esercizi"),
    Traguardo("esercizi_100", "Cento tavole", "Risolvi 100 esercizi diversi.", "100", 100, "esercizi"),
    *[
        Traguardo(f"argomento_{argomento}", f"10 esercizi di {argomento}", f"Risolvi 10 esercizi di {argomento}.", simbolo, 10, f"argomento:{argomento}")
        for argomento, simbolo in SIMBOLI_ARGOMENTO.items()
    ],
    Traguardo("panoramica_1", "Panoramica di Analisi I", "Risolvi almeno un esercizio per ogni argomento di Analisi I.", "I", 5, "argomenti_analisi1"),
    Traguardo("analisi2", "Nuova dimensione", "Risolvi il tuo primo esercizio di Analisi II.", "II", 1, "esercizi_analisi2"),
    Traguardo("serie_3", "Tre giorni di fila", "Studia per 3 giorni consecutivi.", "3g", 3, "record"),
    Traguardo("serie_7", "Una settimana di fila", "Studia per 7 giorni consecutivi.", "7g", 7, "record"),
    Traguardo("serie_30", "Un mese di fila", "Studia per 30 giorni consecutivi.", "30g", 30, "record"),
    Traguardo("risposte_1", "Primo passo giusto", "Rispondi correttamente a una domanda di «Mettimi alla prova».", "✓", 1, "risposte_giuste"),
    Traguardo("risposte_25", "Mano ferma", "Rispondi correttamente a 25 domande di «Mettimi alla prova».", "25✓", 25, "risposte_giuste"),
    Traguardo("risposte_100", "Calcolatore umano", "Rispondi correttamente a 100 domande di «Mettimi alla prova».", "100✓", 100, "risposte_giuste"),
    Traguardo("fatti_1", "Fatto da me", "Trova da solo il risultato finale di un esercizio in «Mettimi alla prova».", "★", 1, "fatti_da_te"),
    Traguardo("fatti_10", "In autonomia", "Trova da solo il risultato finale di 10 esercizi.", "10★", 10, "fatti_da_te"),
    Traguardo("magazzino_1", "Il primo scaffale", "Carica il tuo primo documento nel Magazzino.", "▤", 1, "documenti"),
    Traguardo("mappa_1", "Argomento coperto", "Porta un argomento al 100% nella Mappa della conoscenza.", "100%", 1, "argomenti_coperti"),
]  # fmt: skip


def _statistiche(sessione: Session, record: int) -> dict[str, int]:
    """Calcola tutti i numeri da cui dipendono i traguardi."""
    attivita = list(sessione.exec(select(Attivita)))
    risolti = {a.esercizio_id: a.argomento for a in attivita if a.tipo == "risolto" and a.esercizio_id is not None}
    per_argomento = Counter(risolti.values())

    # Documenti caricati dallo studente (non quelli creati dallo Storico)
    generati = {d for d in sessione.exec(select(Esercizio.documento_id)) if d is not None}
    documenti = [d for d in sessione.exec(select(Documento)) if d.id not in generati]

    # Argomenti coperti al 100% nella Mappa (import qui per evitare un ciclo tra moduli)
    from app.api.magazzino import leggi_mappa

    coperti = sum(1 for corso in leggi_mappa(sessione=sessione) for voce in corso["argomenti"] if voce["copertura"] >= 1)

    statistiche = {
        "esercizi": len(risolti),
        "argomenti_analisi1": sum(1 for a in config.ARGOMENTI["Analisi I"] if per_argomento[a] > 0),
        "esercizi_analisi2": sum(per_argomento[a] for a in config.ARGOMENTI["Analisi II"]),
        "record": record,
        "risposte_giuste": sum(1 for a in attivita if a.tipo == "risposta_giusta"),
        "fatti_da_te": len({a.esercizio_id for a in attivita if a.tipo == "finale_giusto"}),
        "documenti": len(documenti),
        "argomenti_coperti": coperti,
    }
    for argomenti in config.ARGOMENTI.values():
        for argomento in argomenti:
            statistiche[f"argomento:{argomento}"] = per_argomento[argomento]
    return statistiche


@router.get("")
def leggi_progressi(sessione: Session = Depends(apri_sessione)) -> dict:
    """Serie di giorni, statistiche, calendario e traguardi (segnalando quelli appena raggiunti)."""
    oggi = date.today()
    conteggi = dict(sessione.exec(select(Attivita.giorno, func.count()).group_by(Attivita.giorno)).all())
    giorni = {date.fromisoformat(g) for g in conteggi}
    attuale, record = calcola_serie(giorni, oggi)
    statistiche = _statistiche(sessione, record)

    # Traguardi: quelli appena raggiunti vengono salvati e restituiti come "nuovi"
    ottenuti = {t.chiave: t.ottenuto_il for t in sessione.exec(select(TraguardoOttenuto))}
    traguardi, nuovi = [], []
    for t in TRAGUARDI:
        valore = statistiche[t.misura]
        if valore >= t.obiettivo and t.chiave not in ottenuti:
            ottenuti[t.chiave] = datetime.now().isoformat(timespec="seconds")
            sessione.add(TraguardoOttenuto(chiave=t.chiave, ottenuto_il=ottenuti[t.chiave]))
            nuovi.append(t.chiave)
        traguardi.append(
            {
                "chiave": t.chiave,
                "titolo": t.titolo,
                "descrizione": t.descrizione,
                "simbolo": t.simbolo,
                "attuale": min(valore, t.obiettivo),
                "obiettivo": t.obiettivo,
                "ottenuto": t.chiave in ottenuti,
                "ottenuto_il": ottenuti.get(t.chiave),
            }
        )
    sessione.commit()

    # Calendario delle ultime settimane: quante attività per giorno
    inizio = oggi - timedelta(days=GIORNI_CALENDARIO - 1)
    calendario = [
        {"giorno": (inizio + timedelta(days=i)).isoformat(), "attivita": conteggi.get((inizio + timedelta(days=i)).isoformat(), 0)}
        for i in range(GIORNI_CALENDARIO)
    ]

    return {
        "oggi": oggi.isoformat(),
        "serie": {"attuale": attuale, "record": record, "studiato_oggi": oggi in giorni},
        "totali": {
            "esercizi": statistiche["esercizi"],
            "risposte_giuste": statistiche["risposte_giuste"],
            "fatti_da_te": statistiche["fatti_da_te"],
            "giorni_di_studio": len(giorni),
        },
        "per_argomento": [
            {"argomento": a, "corso": corso, "esercizi": statistiche[f"argomento:{a}"]}
            for corso, argomenti in config.ARGOMENTI.items()
            for a in argomenti
        ],
        "calendario": calendario,
        "traguardi": traguardi,
        "nuovi": [t for t in traguardi if t["chiave"] in nuovi],
    }
