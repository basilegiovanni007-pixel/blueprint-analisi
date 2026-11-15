"""
Collegamento tra i passaggi della soluzione e i blocchi del Magazzino.

Per ogni concetto usato in un passaggio cerchiamo nel Magazzino un blocco che ne parli:
- se lo troviamo, il passaggio riceve una citazione (📎 fonte, documento, pagina);
- se non lo troviamo, il passaggio riceve un avviso (⚠ concetto non ancora negli appunti).

La ricerca è "ibrida": il blocco deve contenere almeno una parola chiave del concetto
(così la citazione è pertinente), e tra i candidati scegliamo il migliore usando il
tipo di blocco e la ricerca per significato.
"""

import unicodedata

from sqlmodel import Session, select

from app.db.modelli import Blocco, Documento, Esercizio
from app.magazzino.indice import indice
from app.risolutore.concetti import CONCETTI

# Un teorema o una definizione sono fonti migliori di un esercizio svolto
PRIORITA_TIPO = {"teorema": 0, "definizione": 0, "metodo": 0, "esempio": 1, "esercizio svolto": 2, "altro": 3}


def _normalizza(testo: str) -> str:
    """Minuscolo e senza accenti, per confrontare le parole in modo affidabile."""
    testo = unicodedata.normalize("NFD", testo.lower())
    return "".join(c for c in testo if unicodedata.category(c) != "Mn")


class Biblioteca:
    """Legge una volta i blocchi attivi del Magazzino e risponde alle domande "conosco X?"."""

    def __init__(self, sessione: Session) -> None:
        self._documenti = {d.id: d for d in sessione.exec(select(Documento).where(Documento.attivo == True))}  # noqa: E712
        # Gli esercizi svolti dall'app e aggiunti al Magazzino dallo Storico NON valgono come fonte:
        # altrimenti basterebbe risolvere un esercizio una volta perché l'app "imparasse" un metodo
        # che lo studente non ha mai visto nei suoi appunti.
        generati = sessione.exec(select(Esercizio.documento_id).where(Esercizio.documento_id != None))  # noqa: E711
        for documento_id in generati:
            self._documenti.pop(documento_id, None)
        self._blocchi: list[tuple[Blocco, str]] = []
        if self._documenti:
            blocchi = sessione.exec(select(Blocco).where(Blocco.documento_id.in_(list(self._documenti))))
            self._blocchi = [(b, _normalizza(b.testo)) for b in blocchi]
        self._memoria: dict[str, dict | None] = {}  # risposte già calcolate

    def cita(self, chiave: str) -> dict | None:
        """Restituisce la citazione migliore per un concetto, oppure None se non è nel Magazzino."""
        if chiave in self._memoria:
            return self._memoria[chiave]

        concetto = CONCETTI[chiave]
        candidati = [b for b, testo in self._blocchi if any(parola in testo for parola in concetto.parole)]

        citazione = None
        if candidati:
            # Somiglianza "per significato" con la descrizione del concetto (se l'indice è disponibile)
            try:
                somiglianze = dict(indice.cerca(concetto.domanda, 30, list(self._documenti)))
            except Exception:
                somiglianze = {}
            migliore = min(
                candidati,
                key=lambda b: (PRIORITA_TIPO.get(b.tipo, 3), -somiglianze.get(b.id, 0.0), b.id),
            )
            documento = self._documenti[migliore.documento_id]
            estratto = migliore.testo if len(migliore.testo) <= 280 else migliore.testo[:280].rstrip() + "…"
            citazione = {
                "blocco_id": migliore.id,
                "documento_id": documento.id,
                "documento": documento.titolo,
                "fonte": documento.fonte,
                "pagina": migliore.pagina,
                "tipo": migliore.tipo,
                "estratto": estratto,
            }

        self._memoria[chiave] = citazione
        return citazione

    def conosce(self, chiave: str) -> bool:
        return self.cita(chiave) is not None
