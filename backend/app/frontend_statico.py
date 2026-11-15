"""
Pagine del frontend servite direttamente dal backend.

Durante lo sviluppo il frontend gira con Vite (porta 5173). Nella versione installata,
invece, non c'è Node.js: le pagine già "compilate" (cartella frontend/dist) vengono
servite dallo stesso server FastAPI, così basta un solo programma.
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse


def monta_frontend(app: FastAPI, cartella: Path) -> None:
    """Aggiunge all'app una regola che restituisce i file del frontend."""
    cartella = cartella.resolve()
    indice = cartella / "index.html"

    # Questa regola va registrata DOPO gli sportelli /api: FastAPI prova le regole in ordine.
    @app.get("/{percorso:path}", include_in_schema=False)
    def pagina(percorso: str) -> FileResponse:
        if percorso.startswith("api/"):
            raise HTTPException(status_code=404, detail="Indirizzo non trovato.")
        file = (cartella / percorso).resolve()
        # Sicurezza: non si esce mai dalla cartella del frontend (es. con "../../")
        if percorso and file.is_file() and file.is_relative_to(cartella):
            return FileResponse(file)
        # Indirizzi come /storico/12 non sono file: è React a gestirli, partendo da index.html
        return FileResponse(indice)
