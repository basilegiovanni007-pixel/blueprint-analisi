# ============================================================
#  Crea l'installer di Blueprint: installer\Output\Blueprint-Setup.exe
#
#  Uso (da PowerShell, nella cartella del progetto):
#      .\installer\crea_installer.ps1 -Versione 1.0.0
#
#  Serve aver già avviato l'app almeno una volta con avvia.bat (così esistono
#  backend\.venv e frontend\node_modules) e avere installato Inno Setup 6.
# ============================================================

param(
    [string]$Versione = "1.0.0"
)

# "Continue": alcuni programmi (npm, PyInstaller) scrivono semplici avvisi sul canale degli errori.
# Gli errori veri li riconosciamo dal codice di uscita ($LASTEXITCODE) dopo ogni passo.
$ErrorActionPreference = "Continue"
$radice = Split-Path -Parent $PSScriptRoot
$python = Join-Path $radice "backend\.venv\Scripts\python.exe"
$env:Path = "C:\Program Files\nodejs;" + $env:Path

function Passo($testo) { Write-Host "`n=== $testo ===" -ForegroundColor Cyan }

# Inno Setup può essere installato per utente o per tutto il computer
$iscc = @(
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { throw "Inno Setup 6 non trovato. Installalo con: winget install JRSoftware.InnoSetup" }
if (-not (Test-Path $python)) { throw "Manca backend\.venv: avvia prima l'app con avvia.bat." }

Passo "1/5 Compilo il frontend"
Push-Location (Join-Path $radice "frontend")
npm run build
if ($LASTEXITCODE -ne 0) { throw "Compilazione del frontend non riuscita." }
Pop-Location

Passo "2/5 Strumenti di impacchettamento (PyInstaller, Pillow)"
& $python -m pip install --quiet --disable-pip-version-check pyinstaller pillow
if ($LASTEXITCODE -ne 0) { throw "Installazione di PyInstaller non riuscita." }

Passo "3/5 Icona"
& $python (Join-Path $PSScriptRoot "crea_icona.py")

Passo "4/5 Creo Blueprint.exe con PyInstaller (qualche minuto)"
& $python -m PyInstaller (Join-Path $PSScriptRoot "blueprint.spec") --noconfirm --clean `
    --distpath (Join-Path $PSScriptRoot "build\dist") --workpath (Join-Path $PSScriptRoot "build\work")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller non è riuscito a creare l'eseguibile." }

Passo "5/5 Creo l'installer con Inno Setup"
Push-Location $PSScriptRoot
& $iscc "/DVersione=$Versione" "blueprint.iss"
if ($LASTEXITCODE -ne 0) { throw "Inno Setup non è riuscito a creare l'installer." }
Pop-Location

$installer = Join-Path $PSScriptRoot "Output\Blueprint-Setup.exe"
$mb = [math]::Round((Get-Item $installer).Length / 1MB)
Write-Host "`nFatto! $installer ($mb MB)" -ForegroundColor Green
