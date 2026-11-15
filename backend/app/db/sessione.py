"""
Collegamento al database SQLite.

Una "sessione" è una conversazione aperta con il database: si leggono e scrivono
dati, poi si chiude. FastAPI ne apre una per ogni richiesta.
"""

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


def apri_sessione():
    """Usata da FastAPI: apre una sessione e la chiude a richiesta finita."""
    with Session(motore) as sessione:
        yield sessione
