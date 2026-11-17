"""
Punto d'ingresso del backend di Blueprint.

Qui creiamo l'applicazione FastAPI e colleghiamo i vari "sportelli" (router).
Si avvia con:  uvicorn app.main:app --reload --port 8000
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import grafici, magazzino, progressi, risolutore, stato, storico
from app.db.sessione import crea_tabelle, motore
from app.frontend_statico import monta_frontend
from app.magazzino.argomenti import assegna_mancanti
from app.magazzino.indice import indice


@asynccontextmanager
async def ciclo_di_vita(app: FastAPI):
    """Codice eseguito una volta all'accensione del server."""
    crea_tabelle()  # crea il database se non esiste
    # Carica il modello di ricerca senza bloccare l'avvio; quando è pronto, dà un argomento
    # ai blocchi caricati con le versioni precedenti (che non ce l'hanno ancora)
    indice.prepara_in_sottofondo(poi=lambda: assegna_mancanti(motore))
    yield


app = FastAPI(
    title="Blueprint – Risolutore di Analisi I e II",
    version="1.1.0",
    lifespan=ciclo_di_vita,
)

# CORS: per sicurezza il browser blocca le richieste tra indirizzi diversi.
# Il frontend gira su localhost:5173 e il backend su localhost:8000,
# quindi dobbiamo dire esplicitamente che il frontend è autorizzato.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Colleghiamo gli sportelli. Nelle prossime fasi ne aggiungeremo altri (storico).
app.include_router(stato.router)
app.include_router(magazzino.router)
app.include_router(risolutore.router)
app.include_router(grafici.router)
app.include_router(storico.router)
app.include_router(progressi.router)

# Versione installata: il backend serve anche le pagine del frontend (vedi frontend_statico.py).
# Il programma di avvio (blueprint.py) indica dove si trovano con la variabile BLUEPRINT_FRONTEND.
if cartella_frontend := os.environ.get("BLUEPRINT_FRONTEND"):
    if (Path(cartella_frontend) / "index.html").is_file():
        monta_frontend(app, Path(cartella_frontend))
