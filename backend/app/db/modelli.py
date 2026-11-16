"""
Le tabelle del database SQLite.

Con SQLModel ogni classe qui sotto diventa una tabella, e ogni attributo una colonna.
- Documento: un file caricato nel Magazzino, con le sue etichette.
- Blocco: un pezzo di testo estratto da un documento (un paragrafo, una definizione...).
"""

from datetime import datetime

from sqlmodel import Field, SQLModel


class Documento(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    titolo: str  # nome mostrato nell'app (modificabile)
    nome_file: str  # nome originale del file caricato
    file_salvato: str  # nome con cui il file è salvato in dati/file
    argomento: str  # es. "Limiti"
    corso: str  # "Analisi I" oppure "Analisi II"
    fonte: str  # es. "Appunti miei"
    data: str  # data degli appunti, formato AAAA-MM-GG
    attivo: bool = True  # se False il risolutore ignora questo documento
    letto_con_ocr: bool = False  # True se il testo viene da foto o scansioni (da ricontrollare)
    # Momento del caricamento, salvato come testo (es. "2026-11-14T19:30:00")
    caricato_il: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


class Esercizio(SQLModel, table=True):
    """Un esercizio risolto, salvato nello Storico con la sua soluzione."""

    id: int | None = Field(default=None, primary_key=True)
    testo: str  # l'esercizio come l'ha scritto lo studente
    tipo_richiesto: str = "auto"  # il tipo scelto nel menu ("auto" = riconosciuto dall'app)
    tipo: str  # il tipo riconosciuto: limite, derivata, serie...
    descrizione: str  # es. "Limite", "Serie numerica"
    argomento: str  # argomento del corso, es. "Limiti"
    problema_latex: str
    risposta_latex: str
    soluzione: str  # la soluzione completa in formato JSON, come la riceve il browser
    # I risultati attesi di ogni passaggio, in formato JSON: servono a "Mettimi alla prova".
    # Restano sul computer dello studente e non vengono mai inviati al browser.
    controlli: str
    documento_id: int | None = None  # se è stato aggiunto al Magazzino, il documento creato
    risolto_il: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


class Attivita(SQLModel, table=True):
    """
    Un "evento" di studio: un esercizio risolto, una risposta giusta in "Mettimi alla prova"...
    Serve a calcolare i giorni di studio consecutivi e i traguardi.
    """

    id: int | None = Field(default=None, primary_key=True)
    giorno: str = Field(index=True)  # AAAA-MM-GG
    momento: str  # data e ora complete
    tipo: str  # "risolto", "risposta_giusta", "finale_giusto"
    argomento: str | None = None
    esercizio_id: int | None = None


class TraguardoOttenuto(SQLModel, table=True):
    """Un traguardo raggiunto: una volta ottenuto resta, anche se poi si eliminano esercizi."""

    chiave: str = Field(primary_key=True)
    ottenuto_il: str


class Blocco(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    documento_id: int = Field(foreign_key="documento.id", index=True)
    ordine: int  # posizione del blocco dentro al documento (0, 1, 2...)
    pagina: int | None = None  # pagina del PDF da cui viene (se nota)
    testo: str
    tipo: str = "altro"  # definizione, teorema, metodo, esempio, esercizio svolto, altro
