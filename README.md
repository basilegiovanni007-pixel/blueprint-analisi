# Blueprint – Risolutore di Analisi I e II

Un'app per studiare Analisi Matematica I e II: risolve gli esercizi e spiega ogni
passaggio usando solo ciò che hai caricato nel tuo "Magazzino" (appunti e materiale
del professore).

**Versione 1.0 – tutte e 7 le fasi completate.** Cosa contiene:

- **Magazzino**: carichi appunti e materiale del prof, l'app li divide in blocchi,
  riconosce di quale argomento parla ogni blocco, li indicizza per la ricerca e misura
  la copertura degli argomenti (Mappa).
- **Risolutore**: Analisi I (limiti, derivate, integrali, serie, equazioni
  differenziali) e Analisi II (gradiente, punti critici, massimi e minimi vincolati,
  integrali doppi), con passaggi, citazioni dai tuoi appunti e risultato verificato.
- **Grafici**: studio di funzione animato, tangente, somme di Riemann, Taylor, serie,
  superfici 3D con curve di livello.
- **Studio**: quattro modalità (completa, un passo alla volta, suggerimento, mettimi
  alla prova), Storico, esportazione in PDF.
- **Progressi**: giorni di studio consecutivi, calendario e traguardi.

L'app è completamente gratuita e gira solo sul tuo computer: non usa nessun servizio
a pagamento e i tuoi appunti non vengono inviati su internet.

## Scaricare Blueprint (Windows)

Il modo più semplice è l'installer: vai sul sito del progetto,
<https://basilegiovanni007-pixel.github.io/blueprint-analisi/>, oppure nella sezione
[Releases](https://github.com/basilegiovanni007-pixel/blueprint-analisi/releases/latest)
e scarica `Blueprint-Setup.exe`. Non servono Python né Node.js. Al primo avvio Windows potrebbe dire
«PC protetto da Windows»: premi **Ulteriori informazioni** e poi **Esegui comunque**
(succede con tutti i programmi senza firma digitale a pagamento).

Le istruzioni qui sotto servono invece a chi vuole avviare Blueprint dal codice sorgente
(anche su Mac o Linux) o modificarlo.

## Cosa serve

- **Python 3.13** – <https://www.python.org> (non una versione più nuova: alcune
  librerie di ricerca non esistono ancora per il 3.14 e successivi)
- **Node.js** LTS – <https://nodejs.org>

## Avviare l'app

Fai doppio clic su **`avvia.bat`**.

La prima volta installa le librerie (qualche minuto). Poi apre due finestre nere
(backend e frontend) e il browser su <http://localhost:5173>.

Al primo avvio il backend scarica anche il modello linguistico per la ricerca
(circa 220 MB, serve internet). Nella pagina Magazzino compare un avviso finché non
è pronto; dalla volta successiva parte subito e funziona anche senza internet.

Per spegnere l'app chiudi le due finestre nere.

## Usare il Risolutore

Scrivi l'esercizio nel riquadro e premi **Risolvi** (oppure Ctrl + Invio).

| Cosa vuoi | Come scriverlo |
|---|---|
| Limite | `limite per x che tende a 0 di sin(x)/x` · `lim x->+oo x/e^x` · `lim x->0+ ln(x)` |
| Derivata | `derivata di x^2*sin(x)` · `derivata seconda di x^3` |
| Integrale | `integrale di x*e^x dx` · `integrale da 0 a 1 di x^2 dx` |
| Serie | `serie di termine 1/n^2` · `serie di termine 1/(n*ln(n)) per n da 2 a +oo` |
| Equazione differenziale | `y' + 2y = e^x` · `y'' - 3y' + 2y = 0` |
| Problema di Cauchy | `y' = x/y, y(0) = 1` · `y'' + 4y = 0, y(0) = 1, y'(0) = 2` |
| LaTeX | `\lim_{x \to 0} \frac{\sin x}{x}` · `\int_{0}^{1} x^2 \, dx` · `\sum_{n=1}^{\infty} \frac{1}{n^2}` |
| Gradiente | `gradiente di x^2*y + y^3` · `derivate parziali di x*e^y` |
| Punti critici | `punti critici di x^3 + y^3 - 3*x*y` · `massimi e minimi di x^2 + y^2 - 2x` |
| Massimi e minimi vincolati | `massimi e minimi di x*y con vincolo x^2 + y^2 = 1` |
| Integrale doppio | `integrale doppio di x*y con x da 0 a 1 e y da 0 a x` · `integrale doppio di x + y su [0,1]x[0,2]` |

Regole per scrivere le formule:

- potenze con `^` (`x^2`), prodotti con `*` (`x*sin(x)`; `2x` va bene, `xsin(x)` no);
- funzioni: `sin` (o `sen`), `cos`, `tan` (o `tg`), `ln`, `e^x`, `sqrt(x)`, `arctan`...;
- infinito: `+oo`, `-oo`, `infinito`, `più infinito`.

Cosa trovi nella soluzione:

- **Ho capito così**: l'esercizio riscritto come formula, per controllare che sia giusto.
- **Svolgimento**: i passaggi. Sotto ogni passaggio c'è la fonte (📎, cliccabile) se il
  concetto è nel Magazzino, oppure un avviso (⚠) se non c'è ancora.
- **Risultato**: sempre ricalcolato da SymPy in modo indipendente. Se i passaggi non
  portassero allo stesso risultato, l'app non li mostra.
- Se per un limite esistono più metodi, l'app preferisce quello che hai nel Magazzino.

### Risolvere da un file

Nel riquadro **Oppure risolvi da un file** trascina un foglio di esercizi (PDF con
testo, Word, `.txt`, `.md`, `.tex`). Se contiene più esercizi l'app li elenca: clicca
quello che vuoi oppure scrivi "risolvi il 3". Per provare: `esempi/foglio-esercizi.md`.

Limiti di questa versione gratuita (senza intelligenza artificiale):

- capisce solo le frasi più comuni, del tipo mostrato nella tabella;
- nei PDF le formule complesse (frazioni, esponenti) spesso vengono estratte male:
  in quel caso l'esercizio compare nel riquadro e puoi correggerlo a mano;
- puoi caricare anche la **foto** di un foglio di esercizi: il testo viene riconosciuto e
  l'esercizio scelto compare nel riquadro **senza essere risolto subito**, perché le
  formule scritte a mano vengono spesso lette male (es. `x²` come `x2`): controllale e
  poi premi Risolvi;
- per alcuni limiti (es. forme `1^∞`) mostra solo il risultato, senza passaggi.

### Serie ed equazioni differenziali

**Serie numeriche.** L'app stabilisce se la serie converge provando i criteri in
quest'ordine: condizione necessaria, serie geometrica, serie armonica generalizzata,
criterio del rapporto, confronto asintotico; per le serie a segni alterni,
convergenza assoluta e criterio di Leibniz. Quando è possibile calcola anche la somma.
Se nessuno di questi criteri basta (es. `1/(n*ln(n))`) mostra solo la conclusione di
SymPy e lo dice. Se SymPy non riesce a confermare la conclusione, il timbro
"Verificato" non compare e un avviso lo spiega.

**Equazioni differenziali.** La derivata si scrive con l'apostrofo (`y'`, `y''`) oppure
`dy/dx`. Tipi risolti con i passaggi:

- primo ordine a variabili separabili (`y' = x*y`);
- primo ordine lineari (`y' + 2y = e^x`), con il fattore integrante;
- secondo ordine lineari a coefficienti costanti, omogenee (`y'' + y = 0`) e non
  omogenee (`y'' - y = x`);
- problemi di Cauchy: aggiungi le condizioni dopo una virgola (`y(0) = 1`).

La soluzione viene sempre sostituita nell'equazione per controllo. Il grafico mostra
la soluzione del problema di Cauchy oppure, senza condizioni iniziali, alcune curve
della famiglia di soluzioni. Nelle equazioni non omogenee la soluzione particolare è
indicata e verificata, ma senza il calcolo dei coefficienti passo per passo. Per gli
altri tipi di equazione viene mostrata solo la soluzione di SymPy, quando esiste in
forma esplicita.

### Esercizi di Analisi II

Per le funzioni di due variabili la soluzione mostra, oltre ai passaggi, la
**superficie 3D** (trascina per ruotarla) e la **mappa delle curve di livello**, con:

- i punti critici colorati per tipo: massimo (giallo), minimo (verde), sella (rosa);
- la curva del vincolo, per i massimi e minimi vincolati;
- il dominio di integrazione evidenziato, per gli integrali doppi;
- il campo del gradiente, attivabile con la casella sotto i grafici.

Cosa sa fare e cosa no:

- **Punti critici**: li classifica con la matrice hessiana. Se il determinante è nullo
  lo dichiara ("caso dubbio"); se i punti critici formano una curva si ferma e lo dice.
- **Vincolati**: usa i moltiplicatori di Lagrange con un solo vincolo scritto come
  uguaglianza. Se il vincolo è una curva chiusa trova massimo e minimo assoluti;
  se è illimitato (es. una retta) dice solo cosa succede vicino a ogni candidato.
- **Integrali doppi**: domini rettangolari o "normali", cioè una variabile tra due numeri
  e l'altra tra due funzioni della prima. Non ci sono ancora coordinate polari,
  integrali tripli, curvilinei e di superficie.
- Ogni risultato è controllato con un secondo metodo (autovalori, calcolo numerico
  lungo il vincolo, integrale ricalcolato da SymPy). Se il controllo fallisce l'app
  non mostra il risultato.

## Modalità di studio

Sopra ogni soluzione c'è il riquadro **Come vuoi studiarlo?**. L'app ricorda l'ultima
modalità scelta.

| Modalità | Cosa succede |
|---|---|
| **Soluzione completa** | Tutti i passaggi, subito. |
| **Un passo alla volta** | Riveli tu un passaggio dopo l'altro; il risultato compare alla fine. |
| **Suggerimento** | Vedi solo il nome del prossimo passo, il concetto che serve e la fonte nei tuoi appunti, senza calcoli. |
| **Mettimi alla prova** | Per ogni passaggio con una domanda ("Quanto vale $D[x^2]$?") scrivi la tua risposta e l'app ti dice se è corretta, senza mai rivelare quella giusta. Alla fine c'è la domanda sul risultato e il punteggio. |

In "Mettimi alla prova":

- le risposte sono confrontate in modo matematico: `2x` e `x*2` vanno bene allo
  stesso modo, e per le primitive è accettata qualsiasi costante (`+ c` facoltativo);
- per le equazioni differenziali la tua soluzione viene sostituita nell'equazione
  (le costanti si scrivono `c1`, `c2`); per le serie si risponde con due pulsanti;
- i passaggi che applicano una regola (es. "derivata di un prodotto") non hanno una
  domanda: si leggono e si prosegue;
- per punti critici e massimi/minimi vincolati si controllano solo i passaggi, non
  la risposta finale.

## Storico ed esportazione

- **Storico** (barra laterale): ogni esercizio risolto viene salvato da solo. Puoi
  filtrarli per tipo, cercarli, riaprirli (con tutte le modalità di studio),
  risolverli di nuovo con il Magazzino attuale o eliminarli. Nell'elenco l'esercizio
  compare senza il risultato, così puoi riprovarci.
- **Esporta in PDF**: apre la finestra di stampa del browser con la soluzione completa
  in stile blueprint. Scegli **Salva come PDF** come stampante. Il grafico 3D non viene
  stampato (resta la mappa delle curve di livello).
- **Aggiungi al Magazzino**: salva l'esercizio risolto come documento di tipo
  "esercizio svolto" (fonte: Esercitazione). Compare nella ricerca e nella Mappa, ma
  **non** viene usato come fonte per le citazioni: i metodi devono venire dai tuoi
  appunti, non dalle soluzioni scritte dall'app.

## Progressi e traguardi

- In fondo alla barra laterale vedi la **serie di giorni di studio** consecutivi: si
  allunga ogni giorno in cui risolvi almeno un esercizio o rispondi bene in "Mettimi
  alla prova". Se oggi non hai ancora studiato, la serie di ieri resta valida fino a
  mezzanotte.
- La pagina **Progressi** mostra il record di giorni, il calendario delle ultime 15
  settimane, gli esercizi risolti per argomento e i **traguardi** (es. "10 esercizi di
  Integrali", "Una settimana di fila", "Fatto da me").
- Quando raggiungi un traguardo compare una notifica con il suo timbro. I traguardi
  raggiunti restano anche se poi elimini esercizi dallo Storico.
- Risolvere di nuovo lo stesso esercizio non conta come esercizio diverso.

## Usare i Grafici

Dalla barra laterale apri **Grafici** e scegli uno strumento con le schede in alto.

| Strumento | Cosa fa |
|---|---|
| **Studio di funzione** | Scrivi la funzione e premi **Studia**: dominio, simmetrie, intersezioni, segno, asintoti, massimi, minimi e flessi compaiono sul grafico una tappa alla volta. Con i pulsanti vai avanti, indietro o fai ripartire l'animazione. |
| **Grafico e parametri** | Disegna qualsiasi funzione. Se contiene altre lettere (es. `a*sin(b*x)`) compare un cursore per ognuna. |
| **Tangente** | Mostra la secante per due punti e la tangente: portando `h` a zero il rapporto incrementale diventa la derivata. |
| **Somme di Riemann** | Rettangoli sotto la curva, con numero regolabile, e confronto con il valore dell'integrale. |
| **Taylor** | La funzione e il suo polinomio di Taylor, con ordine e centro regolabili. |
| **Serie** | Le somme parziali di una serie (scrivi il termine in funzione di `n`), con la somma quando è nota. |
| **Superfici 3D** | Una funzione di `x` e `y` come superficie ruotabile e come mappa di curve di livello, con gradiente e punti critici. |

Nei grafici piani: **trascina** per spostarti, **Ctrl + rotella** (o pulsanti + e −) per
lo zoom, **doppio clic** (o ⟲) per tornare alla vista iniziale. Passando il mouse
compaiono le coordinate del punto sulla curva. La rotella da sola scorre la pagina.

Anche il **Risolutore** mostra un grafico sotto ogni soluzione: il punto a cui tende
la variabile nei limiti, la derivata accanto alla funzione, l'area negli integrali definiti.

Limiti di questa versione:

- lo studio di funzione lavora con funzioni di una variabile senza parametri;
- per le funzioni periodiche (es. `sin(x)`) zeri, massimi e minimi sono infiniti:
  vengono mostrati solo quelli vicini all'origine;
- quando un'equazione non si risolve in forma esatta i punti sono approssimati, e lo
  studio lo dice;
- "Taylor" e "Serie" chiedono i calcoli al backend, "Tangente" e "Riemann" usano
  valori numerici approssimati.

## Usare il Magazzino

1. Apri **Magazzino** dalla barra laterale.
2. Trascina uno o più file nella zona tratteggiata (oppure cliccala). Per una prova
   veloce puoi usare `esempi/appunti-limiti.md`.
3. Scegli fonte e data, poi premi **Carica**. L'argomento parte da **Riconosci in
   automatico**; se preferisci puoi sceglierlo tu.
4. L'app estrae il testo, lo divide in blocchi e prova a riconoscere il tipo di ogni
   blocco (definizione, teorema, metodo, esempio, esercizio svolto) e il suo argomento.
   Con **Vedi blocchi** puoi correggere tipo e argomento dai menu a tendina.
5. Con l'interruttore **Attivo** puoi mettere da parte un documento senza eliminarlo.
6. **Cerca nel Magazzino** trova i blocchi per significato, non solo per parole uguali.
7. La **Mappa** mostra per ogni argomento quali tipi di blocco hai già e quali mancano.

### Argomenti riconosciuti in automatico

Ogni blocco riceve un argomento del corso (Limiti, Derivate, Serie...). Per deciderlo
l'app guarda insieme:

- il **significato** del blocco, con lo stesso modello linguistico della ricerca;
- le **parole chiave** ("convessa", "gradiente", "Cauchy") e la **notazione** (f'(x),
  ∫, ∂, y'');
- il **contesto**: un blocco senza indizi (per esempio solo formule) o in bilico (de
  l'Hôpital sta sia nei limiti sia nelle derivate) prende l'argomento del documento.

Se un documento parla anche d'altro, la scheda lo dice ("Tratta anche: Serie (1
blocco)") e nella **Mappa** quel blocco conta per il suo argomento. Nelle citazioni, a
parità di tipo, l'app preferisce i blocchi sull'argomento dell'esercizio. Tutto avviene
sul tuo computer. I documenti caricati con le versioni precedenti ricevono gli argomenti
da soli, al primo avvio.

Il riconoscimento non è infallibile, soprattutto sugli appunti scritti a mano letti
male: se sbaglia, correggi l'argomento del blocco con **Vedi blocchi**. Se cambi
l'argomento di un documento, lo seguono i blocchi che avevano quello vecchio.

Formati accettati: PDF (anche scansionati), Word (`.docx`), `.txt`, `.md`, `.tex` e
foto (`.jpg`, `.png`, `.webp`, `.heic` degli iPhone, `.bmp`, `.tif`).

### Foto e appunti scritti a mano

Le foto e le pagine scansionate non contengono testo "vero", solo pixel: Blueprint lo
riconosce con l'**OCR** (RapidOCR, con il modello per le lingue con alfabeto latino).
Tutto avviene sul tuo computer, gratis e senza internet. Nei PDF l'OCR viene usato solo
sulle pagine scansionate; quelle scritte al computer vengono lette direttamente.

- Ci vogliono un paio di secondi per ogni foto o pagina scansionata.
- Il documento riceve l'etichetta **letto da foto**. Con **Vedi blocchi** vedi la foto
  accanto al testo riconosciuto e puoi sistemare ogni blocco con **Correggi**: il
  risolutore e la ricerca usano subito il testo corretto.
- Funziona bene con lo stampatello e con la scrittura a mano ordinata; il corsivo molto
  legato viene letto peggio. **Le formule** (frazioni, esponenti, integrali) spesso
  vengono lette male: per le citazioni contano soprattutto le parole ("Teorema di de
  l'Hôpital", "Definizione di limite"), che di solito vengono lette bene.
- Per foto migliori: foglio dritto e intero nell'inquadratura, buona luce, niente ombre,
  una pagina per foto.

## Come è fatta

```
risolutore-analisi/
├── avvia.bat          ← avvia tutto
├── esempi/            ← file di prova
├── dati/              ← i TUOI dati: file caricati, database, indice (creata al primo avvio)
├── backend/           ← la parte Python: calcoli e dati
│   ├── app/
│   │   ├── main.py      ← punto d'ingresso del server
│   │   ├── config.py    ← cartelle ed elenchi (argomenti, fonti, tipi di blocco)
│   │   ├── api/         ← gli "sportelli" a cui il frontend fa richieste
│   │   ├── db/          ← tabelle del database SQLite
│   │   ├── magazzino/   ← estrazione del testo, blocchi, indice di ricerca
│   │   ├── risolutore/  ← lettura dell'esercizio, passaggi, verifica, citazioni
│   │   └── grafici/     ← studio di funzione e preparazione delle funzioni da disegnare
│   ├── tests/           ← test automatici
│   └── requirements.txt
└── frontend/          ← la parte che vedi nel browser
    └── src/
        ├── pagine/      ← Risolutore, Grafici, Magazzino, Mappa, Storico
        ├── grafici/     ← gli strumenti della pagina Grafici
        ├── componenti/  ← pezzi riutilizzabili (barra, cartiglio, schede...)
        ├── tema/        ← colori, griglia e font blueprint
        └── api/         ← chiamate al backend
```

- Il **backend** (FastAPI + SymPy) gira su `http://localhost:8000`.
- Il **frontend** (React + Vite) gira su `http://localhost:5173` e inoltra al backend
  tutte le richieste che iniziano con `/api`.
- Per ricominciare da zero con un Magazzino vuoto, spegni l'app ed elimina la
  cartella `dati`.

## Eseguire i test

Apri un terminale nella cartella `backend` e scrivi:

```
.venv\Scripts\python.exe -m pytest
```

I test usano una cartella temporanea: non toccano i tuoi documenti.

## Problemi comuni

| Cosa vedi | Cosa fare |
|---|---|
| "Backend non raggiungibile" | Controlla che la finestra "Blueprint - backend" sia aperta e senza errori, poi ricarica la pagina. |
| "Python 3.13 non trovato" / "Node.js non trovato" | Installa il programma mancante dai link sopra, poi riavvia `avvia.bat`. |
| "Il modello di ricerca non si è caricato" | La prima volta serve internet. Collegati e riavvia l'app. |
| "Non sono riuscito a leggere il testo di questa foto o scansione" | Rifai la foto più nitida: foglio dritto e intero, buona luce, senza ombre. |
| La pagina non si apre | Aspetta qualche secondo e apri a mano <http://localhost:5173>. |

## Chiave API di Claude

Per ora **non serve**: l'app è gratuita. Le spiegazioni scritte da Claude sono una
funzione opzionale che potrà essere aggiunta più avanti; in quel caso qui troverai
le istruzioni per ottenere e inserire la chiave.

## Creare l'installer e pubblicare una nuova versione

Per chi sviluppa Blueprint. Servono Inno Setup 6 (`winget install JRSoftware.InnoSetup`) e
GitHub CLI (`winget install GitHub.cli`), e aver avviato almeno una volta l'app con `avvia.bat`.

1. Crea l'installer (circa 5 minuti), indicando il numero di versione:

   ```
   .\installer\crea_installer.ps1 -Versione 1.2.0
   ```

   Il risultato è `installer\Output\Blueprint-Setup.exe`.

2. Pubblicalo come nuova Release su GitHub:

   ```
   gh release create v1.2.0 installer\Output\Blueprint-Setup.exe --title "Blueprint 1.2.0" --notes "Cosa cambia..."
   ```

Il sito non va modificato: il pulsante «Scarica» punta sempre all'ultima Release
(`releases/latest/download/Blueprint-Setup.exe`) e mostra da solo versione e dimensione.

Come è fatto il pacchetto:

- `backend/blueprint.py` è il programma di avvio: sceglie una porta libera, salva i dati
  in `%LOCALAPPDATA%\Blueprint`, avvia il server e apre il browser;
- `installer/blueprint.spec` (PyInstaller) mette Python, le librerie e il frontend
  compilato in una cartella con `Blueprint.exe`;
- `installer/blueprint.iss` (Inno Setup) la impacchetta in `Blueprint-Setup.exe`, con
  collegamenti nel menu Start e disinstallatore. La disinstallazione non cancella i dati.

## Il sito web

Il sito di download è la cartella `docs/` (un'unica pagina `index.html`, senza librerie
esterne). GitHub Pages la pubblica su `https://<utente>.github.io/blueprint-analisi/`.

## Licenza

MIT: vedi il file `LICENSE`.
