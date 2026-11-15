"""
Programma di avvio della versione installata di Blueprint.

Fa quattro cose:
1. sceglie dove salvare i dati dello studente (in %LOCALAPPDATA%\\Blueprint, mai nella
   cartella del programma, che su Windows può essere protetta da scrittura);
2. sceglie una porta libera sul computer;
3. avvia il server (backend + pagine del frontend) solo su questo computer (127.0.0.1);
4. appena il server è pronto, apre il browser sull'app.

Per spegnere Blueprint basta chiudere la finestra nera.
"""

import json
import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

PORTE = range(8765, 8785)  # porte provate in ordine (lontane dalla 8000 usata durante lo sviluppo)


def cartella_risorse() -> Path:
    """Dove si trovano i file del programma: dentro l'eseguibile (PyInstaller) o accanto a questo file."""
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def blueprint_gia_acceso(porta: int) -> bool:
    """True se su questa porta risponde già un Blueprint (es. avviato due volte)."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{porta}/api/stato", timeout=1) as risposta:
            return json.load(risposta).get("stato") == "ok"
    except Exception:
        return False


def porta_libera(porta: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as prova:
        return prova.connect_ex(("127.0.0.1", porta)) != 0


def apri_browser_quando_pronto(indirizzo: str) -> None:
    """Aspetta che il server risponda, poi apre il browser."""
    for _ in range(120):
        try:
            urllib.request.urlopen(f"{indirizzo}/api/stato", timeout=1)
            webbrowser.open(indirizzo)
            return
        except Exception:
            time.sleep(0.5)
    print("Il server non risponde: prova ad aprire a mano", indirizzo)


def main() -> None:
    print("=" * 60)
    print("  BLUEPRINT - Risolutore di Analisi I e II")
    print("=" * 60)

    # Se Blueprint è già acceso basta riaprire il browser
    for porta in PORTE:
        if blueprint_gia_acceso(porta):
            print("Blueprint è già in esecuzione: apro il browser.")
            webbrowser.open(f"http://127.0.0.1:{porta}")
            time.sleep(2)
            return

    porta = next((p for p in PORTE if porta_libera(p)), None)
    if porta is None:
        input("Nessuna porta libera tra 8765 e 8784. Chiudi altri programmi e riprova. (Invio per uscire)")
        return

    # Le variabili d'ambiente vanno impostate PRIMA di importare l'app, che le legge all'avvio
    dati = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Blueprint"
    os.environ.setdefault("BLUEPRINT_DATI", str(dati))
    risorse = cartella_risorse()
    frontend = risorse / "frontend" if hasattr(sys, "_MEIPASS") else risorse.parent / "frontend" / "dist"
    os.environ.setdefault("BLUEPRINT_FRONTEND", str(frontend))

    import uvicorn

    from app.main import app

    indirizzo = f"http://127.0.0.1:{porta}"
    print(f"I tuoi dati sono in: {os.environ['BLUEPRINT_DATI']}")
    print(f"L'app è su: {indirizzo}  (si apre da sola nel browser)")
    print("La prima volta viene scaricato il modello per la ricerca (circa 220 MB).")
    print()
    print("Per spegnere Blueprint chiudi questa finestra.")
    print("=" * 60)

    threading.Thread(target=apri_browser_quando_pronto, args=(indirizzo,), daemon=True).start()
    # 127.0.0.1 = raggiungibile solo da questo computer, non dalla rete
    uvicorn.run(app, host="127.0.0.1", port=porta, log_level="warning")


if __name__ == "__main__":
    try:
        main()
    except Exception as errore:  # in una finestra che si chiude subito l'errore non si vedrebbe
        print("\nERRORE:", errore)
        input("Premi Invio per chiudere.")
