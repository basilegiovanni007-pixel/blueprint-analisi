"""
Collegamento al database SQLite.

Una "sessione" è una conversazione aperta con il database: si leggono e scrivono
dati, poi si chiude. FastAPI ne apre una per ogni richiesta.
"""

from sqlalchemy import Boolean, inspect, text
from sqlmodel import Session, SQLModel, create_engine

from app import config
from app.db import modelli  # noqa: F401  (import necessario perché le tabelle vengano registrate)

config.CARTELLA_DATI.mkdir(parents=True, exist_ok=True)
config.CARTELLA_FILE.mkdir(parents=True, exist_ok=True)

# Il "motore" sa dove si trova il file del database.
# check_same_thread=False serve perché FastAPI lavora su più thread.
motore = create_engine(
    f"sqlite:///{config.PERCORSO_DB}",
    connect_args={"check_same_thread": False},
)


def crea_tabelle() -> None:
    """Crea le tabelle se non esistono ancora (non cancella nulla)."""
    SQLModel.metadata.create_all(motore)
    aggiungi_colonne_mancanti(motore)
    togli_collegamenti_orfani(motore)


def togli_collegamenti_orfani(motore_db) -> None:
    """
    Gli esercizi dello Storico ricordano il documento creato nel Magazzino. Fino a Blueprint 1.1,
    eliminando quel documento il collegamento restava: qui lo togliamo, prima che SQLite
    riusi quel numero per un altro documento.
    """
    with motore_db.begin() as connessione:
        connessione.execute(text(
            "UPDATE esercizio SET documento_id = NULL "
            "WHERE documento_id IS NOT NULL AND documento_id NOT IN (SELECT id FROM documento)"
        ))  # fmt: skip


def aggiungi_colonne_mancanti(motore_db) -> list[str]:
    """
    Aggiorna un database creato da una versione precedente di Blueprint.

    create_all() crea le tabelle nuove ma non tocca quelle che esistono già: se in una
    nuova versione una tabella ha una colonna in più (es. documento.letto_con_ocr), qui la
    aggiungiamo con il suo valore predefinito. I dati già presenti restano intatti.
    Restituisce l'elenco delle colonne aggiunte.
    """
    esistenti = inspect(motore_db)
    aggiunte = []
    with motore_db.begin() as connessione:
        for tabella in SQLModel.metadata.sorted_tables:
            if not esistenti.has_table(tabella.name):
                continue
            presenti = {c["name"] for c in esistenti.get_columns(tabella.name)}
            for colonna in tabella.columns:
                if colonna.name in presenti:
                    continue
                tipo = colonna.type.compile(dialect=motore_db.dialect)
                predefinito = colonna.default.arg if colonna.default is not None and not callable(colonna.default.arg) else None
                if predefinito is None and isinstance(colonna.type, Boolean):
                    predefinito = False  # i valori sì/no nuovi partono da "no"
                valore = "" if predefinito is None else f" DEFAULT {int(predefinito) if isinstance(predefinito, bool) else repr(predefinito)}"
                connessione.execute(text(f'ALTER TABLE "{tabella.name}" ADD COLUMN "{colonna.name}" {tipo}{valore}'))
                aggiunte.append(f"{tabella.name}.{colonna.name}")
    return aggiunte


def apri_sessione():
    """Usata da FastAPI: apre una sessione e la chiude a richiesta finita."""
    with Session(motore) as sessione:
        yield sessione
