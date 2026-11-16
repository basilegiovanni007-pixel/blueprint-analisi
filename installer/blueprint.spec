# Ricetta di PyInstaller: trasforma il backend Python (con tutte le librerie) e il frontend
# già compilato in una cartella "Blueprint" con dentro Blueprint.exe.
# Chi installa l'app non ha bisogno di Python né di Node.js.
# Si usa tramite crea_installer.ps1, non a mano.

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

RADICE = Path(SPECPATH).parent  # la cartella del progetto
BACKEND = RADICE / "backend"

datas, binaries, hiddenimports = [], [], []

# Librerie che caricano file e moduli "di nascosto" (DLL, modelli, plugin): le includiamo per intero
for pacchetto in [
    "chromadb",
    "chromadb_rust_bindings",
    "fastembed",
    "onnxruntime",
    "tokenizers",
    "py_rust_stemmers",
    "huggingface_hub",
    "pymupdf",
    "docx",
    "sympy",
    "rapidocr",  # OCR di foto e scansioni, con i suoi modelli (scaricati da crea_installer.ps1)
    "pillow_heif",  # foto HEIC degli iPhone
]:
    d, b, h = collect_all(pacchetto)
    datas += d
    binaries += b
    hiddenimports += h

# Uvicorn sceglie i suoi componenti all'avvio; "app" è il nostro backend
hiddenimports += collect_submodules("uvicorn") + collect_submodules("app")

# Le pagine del frontend (cartella frontend/dist, creata con "npm run build")
datas += [(str(RADICE / "frontend" / "dist"), "frontend")]

a = Analysis(
    [str(BACKEND / "blueprint.py")],
    pathex=[str(BACKEND)],
    datas=datas,
    binaries=binaries,
    hiddenimports=hiddenimports,
    # Cose che non servono all'app: escluderle rende l'installer più leggero
    excludes=["tkinter", "matplotlib", "IPython", "pytest", "PyInstaller", "notebook", "pandas"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Blueprint",
    console=True,  # la finestra nera mostra lo stato; chiudendola si spegne l'app
    icon=str(Path(SPECPATH) / "blueprint.ico"),
)

coll = COLLECT(exe, a.binaries, a.datas, name="Blueprint")
