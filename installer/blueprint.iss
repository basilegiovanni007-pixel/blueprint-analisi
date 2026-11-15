; Ricetta di Inno Setup: impacchetta la cartella creata da PyInstaller in un unico
; file Blueprint-Setup.exe, con collegamenti nel menu Start e sul desktop e il disinstallatore.
; Si usa tramite crea_installer.ps1, che passa la versione con /DVersione=...

#ifndef Versione
  #define Versione "1.0.0"
#endif

[Setup]
; Identificativo unico dell'app: NON cambiarlo, serve a Windows per riconoscere gli aggiornamenti
AppId={{6B7C1E4A-3B1F-4F55-9C3E-0B3D91B1E001}
AppName=Blueprint
AppVersion={#Versione}
AppVerName=Blueprint {#Versione}
AppPublisher=Giovanni Basile
AppComments=Risolutore di Analisi I e II con spiegazioni passo passo
DefaultDirName={localappdata}\Programs\Blueprint
DefaultGroupName=Blueprint
; Installazione "per utente": non servono i permessi di amministratore
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=Blueprint-Setup
SetupIconFile=blueprint.ico
UninstallDisplayIcon={app}\Blueprint.exe
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "italiano"; MessagesFile: "compiler:Languages\Italian.isl"

[Tasks]
Name: "desktop"; Description: "Crea un collegamento sul desktop"; GroupDescription: "Collegamenti:"

[Files]
Source: "build\dist\Blueprint\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Blueprint"; Filename: "{app}\Blueprint.exe"
Name: "{group}\Disinstalla Blueprint"; Filename: "{uninstallexe}"
Name: "{userdesktop}\Blueprint"; Filename: "{app}\Blueprint.exe"; Tasks: desktop

[Run]
Filename: "{app}\Blueprint.exe"; Description: "Avvia Blueprint adesso"; Flags: nowait postinstall skipifsilent

; Nota: la disinstallazione NON cancella i dati dello studente (appunti caricati, storico,
; progressi), che restano in %LOCALAPPDATA%\Blueprint. Così reinstallando non si perde nulla.
