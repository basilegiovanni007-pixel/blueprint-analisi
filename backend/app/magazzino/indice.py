"""
Indice di ricerca "per significato".

Come funziona, in breve:
1. Un modello linguistico trasforma ogni blocco di testo in un "embedding":
   una lista di numeri che rappresenta il significato del testo.
2. Testi con significato simile hanno numeri simili, anche se usano parole diverse.
3. ChromaDB conserva questi numeri e, data una domanda, trova i blocchi più vicini.

Tutto avviene sul tuo computer: nessun testo viene inviato su internet.
"""

import hashlib
import math
import os
import re
import threading

import chromadb
from chromadb.config import Settings

from app import config

# Nei test automatici usiamo un embedding "finto" (velocissimo, senza scaricare il modello).
USA_EMBEDDING_FINTO = os.environ.get("BLUEPRINT_EMBEDDING") == "finto"


def _embedding_finto(testo: str, dimensioni: int = 128) -> list[float]:
    """Embedding semplificato per i test: conta le parole, senza capire il significato."""
    vettore = [0.0] * dimensioni
    for parola in re.findall(r"\w+", testo.lower()):
        posizione = int(hashlib.md5(parola.encode()).hexdigest(), 16) % dimensioni
        vettore[posizione] += 1.0
    norma = math.sqrt(sum(v * v for v in vettore)) or 1.0
    return [v / norma for v in vettore]


class Indice:
    def __init__(self) -> None:
        self._modello = None  # caricato solo quando serve (è lento da caricare)
        self._collezione = None
        self._lucchetto = threading.Lock()  # evita che due richieste carichino il modello insieme
        self.stato = "non caricato"  # "non caricato" | "in caricamento" | "pronto" | "errore"
        self.errore: str | None = None

    # ---------- preparazione ----------

    def _prepara(self) -> None:
        """Apre ChromaDB e carica il modello, una volta sola."""
        with self._lucchetto:
            if self._collezione is None:
                config.CARTELLA_INDICE.mkdir(parents=True, exist_ok=True)
                cliente = chromadb.PersistentClient(
                    path=str(config.CARTELLA_INDICE),
                    # Disattiva l'invio di statistiche d'uso anonime agli autori di ChromaDB
                    settings=Settings(anonymized_telemetry=False),
                )
                # "cosine" = misura la somiglianza guardando la direzione dei vettori
                self._collezione = cliente.get_or_create_collection(
                    "blocchi", metadata={"hnsw:space": "cosine"}
                )
            if self._modello is None and not USA_EMBEDDING_FINTO:
                self.stato = "in caricamento"
                try:
                    from fastembed import TextEmbedding

                    self._modello = TextEmbedding(
                        config.MODELLO_EMBEDDING,
                        cache_dir=str(config.CARTELLA_DATI / "modelli"),
                    )
                except Exception as errore:
                    self.stato = "errore"
                    self.errore = str(errore)
                    raise
            self.stato = "pronto"
            self.errore = None

    def prepara_in_sottofondo(self) -> None:
        """Avvia il caricamento del modello senza bloccare l'avvio del server."""

        def lavoro() -> None:
            try:
                self._prepara()
            except Exception:
                pass  # l'errore resta salvato in self.errore e verrà mostrato all'utente

        threading.Thread(target=lavoro, daemon=True).start()

    def _vettori(self, testi: list[str]) -> list[list[float]]:
        """Trasforma una lista di testi in una lista di embedding."""
        if USA_EMBEDDING_FINTO:
            return [_embedding_finto(testo) for testo in testi]
        return [vettore.tolist() for vettore in self._modello.embed(testi)]

    # ---------- operazioni ----------

    def aggiungi(self, blocchi: list[tuple[int, int, str]]) -> None:
        """Aggiunge (o aggiorna) blocchi nell'indice. Ogni blocco è (id, id_documento, testo)."""
        if not blocchi:
            return
        self._prepara()
        self._collezione.upsert(
            ids=[str(id_blocco) for id_blocco, _, _ in blocchi],
            embeddings=self._vettori([testo for _, _, testo in blocchi]),
            metadatas=[{"documento_id": id_documento} for _, id_documento, _ in blocchi],
        )

    def rimuovi(self, id_blocchi: list[int]) -> None:
        """Toglie dall'indice i blocchi indicati."""
        if not id_blocchi:
            return
        self._prepara()
        self._collezione.delete(ids=[str(i) for i in id_blocchi])

    def cerca(self, domanda: str, quanti: int, id_documenti: list[int]) -> list[tuple[int, float]]:
        """
        Trova i blocchi più simili alla domanda, cercando solo nei documenti indicati.
        Restituisce coppie (id del blocco, somiglianza da 0 a 1).
        """
        if not id_documenti:
            return []
        self._prepara()
        risultato = self._collezione.query(
            query_embeddings=self._vettori([domanda]),
            n_results=quanti,
            where={"documento_id": {"$in": id_documenti}},
        )
        ids = risultato["ids"][0]
        distanze = risultato["distances"][0]
        # La distanza coseno va da 0 (identici) a 2 (opposti): la convertiamo in somiglianza
        return [(int(i), round(max(0.0, 1.0 - d), 3)) for i, d in zip(ids, distanze)]


# Un solo indice condiviso da tutta l'applicazione
indice = Indice()
