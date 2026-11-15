@echo off
REM ============================================================
REM  BLUEPRINT - avvio con un solo comando
REM  Fai doppio clic su questo file (oppure scrivi "avvia" nel terminale).
REM  La prima volta installa le librerie, poi accende backend e frontend
REM  in due finestre e apre il browser.
REM ============================================================

REM Spostati nella cartella in cui si trova questo file
cd /d "%~dp0"

REM --- Controlli iniziali -------------------------------------
REM Serve Python 3.13: le librerie di ricerca non esistono ancora per versioni piu' nuove.
REM "py -3.13" chiede a Windows proprio quella versione, anche se ne hai installate altre.
py -3.13 --version >nul 2>nul
if errorlevel 1 (
    echo ERRORE: Python 3.13 non trovato. Installalo da https://www.python.org e riprova.
    pause
    exit /b 1
)
where npm >nul 2>nul
if errorlevel 1 (
    echo ERRORE: Node.js non trovato. Installalo da https://nodejs.org e riprova.
    pause
    exit /b 1
)

REM --- Prima installazione del backend (solo se manca) --------
if not exist "backend\.venv\Scripts\python.exe" (
    echo Prima installazione del backend, attendi qualche minuto...
    py -3.13 -m venv backend\.venv
    backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
    if errorlevel 1 (
        echo ERRORE durante l'installazione delle librerie Python.
        pause
        exit /b 1
    )
)

REM --- Prima installazione del frontend (solo se manca) -------
if not exist "frontend\node_modules" (
    echo Prima installazione del frontend, attendi qualche minuto...
    pushd frontend
    call npm install
    popd
    if errorlevel 1 (
        echo ERRORE durante l'installazione delle librerie del frontend.
        pause
        exit /b 1
    )
)

REM --- Avvio --------------------------------------------------
echo Avvio del backend su http://localhost:8000 ...
start "Blueprint - backend" /d "%~dp0backend" cmd /k ".venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000"

echo Avvio del frontend su http://localhost:5173 ...
start "Blueprint - frontend" /d "%~dp0frontend" cmd /k "npm run dev"

REM Aspetta qualche secondo che i due programmi partano, poi apri il browser
timeout /t 5 /nobreak >nul
start "" http://localhost:5173

echo.
echo Blueprint e' in esecuzione. Per spegnerlo chiudi le due finestre
echo "Blueprint - backend" e "Blueprint - frontend".
pause
