"""
Impostazioni generali del backend: dove salvare i dati e gli elenchi fissi
(argomenti, fonti, tipi di blocco) usati dal Magazzino.
"""

import os
from pathlib import Path

# Cartella principale del progetto (quella che contiene "backend" e "frontend")
RADICE = Path(__file__).resolve().parents[2]

# Cartella in cui finiscono file caricati, database e indice di ricerca.
# I test automatici la cambiano con la variabile BLUEPRINT_DATI per non toccare i dati veri.
CARTELLA_DATI = Path(os.environ.get("BLUEPRINT_DATI", RADICE / "dati"))
CARTELLA_FILE = CARTELLA_DATI / "file"  # i documenti originali caricati
CARTELLA_INDICE = CARTELLA_DATI / "indice"  # il database vettoriale (ChromaDB)
PERCORSO_DB = CARTELLA_DATI / "blueprint.db"  # il database SQLite

# Modello che trasforma il testo in vettori. È multilingua e funziona bene in italiano.
# La prima volta viene scaricato (circa 220 MB), poi resta sul computer.
MODELLO_EMBEDDING = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Argomenti del corso, divisi per esame
ARGOMENTI: dict[str, list[str]] = {
    "Analisi I": [
        "Limiti",
        "Derivate",
        "Integrali",
        "Serie",
        "Equazioni differenziali",
    ],
    "Analisi II": [
        "Funzioni di più variabili",
        "Integrali multipli",
        "Integrali curvilinei",
        "Integrali di superficie",
    ],
}

FONTI = ["Appunti miei", "Materiale del prof", "Esercitazione"]

# Etichette possibili per un blocco di testo
TIPI_BLOCCO = ["definizione", "teorema", "metodo", "esempio", "esercizio svolto", "altro"]

# Tipi che contano per la copertura di un argomento ("altro" non conta)
TIPI_PER_COPERTURA = [t for t in TIPI_BLOCCO if t != "altro"]

# Formati di file accettati e dimensione massima
ESTENSIONI_TESTO = {".pdf", ".txt", ".md", ".tex", ".docx"}
# Foto e scansioni: il testo viene riconosciuto con l'OCR (vedi magazzino/ocr.py)
ESTENSIONI_IMMAGINE = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".heic", ".heif"}
ESTENSIONI_ACCETTATE = ESTENSIONI_TESTO | ESTENSIONI_IMMAGINE
DIMENSIONE_MASSIMA = 50 * 1024 * 1024  # 50 MB


def corso_di(argomento: str) -> str | None:
    """Restituisce il corso (Analisi I o II) a cui appartiene un argomento."""
    for corso, argomenti in ARGOMENTI.items():
        if argomento in argomenti:
            return corso
    return None
