// Zona "trascina e rilascia" per caricare i file nel Magazzino.
// 1) si scelgono i file  2) si mettono le etichette  3) si preme "Carica".
import { useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

import { caricaDocumento, type Etichette, type Opzioni } from "../api/client";
import CampiEtichette, { AUTOMATICO } from "./CampiEtichette";

type Props = {
  opzioni: Opzioni;
  onCaricato: () => void; // avvisa la pagina che c'è un documento nuovo
};

// Esito del caricamento di un singolo file
type Esito = { nome: string; ok: boolean; messaggio: string };

// Data di oggi nel formato AAAA-MM-GG richiesto dai campi data
const oggi = () => new Date().toLocaleDateString("sv-SE");

export default function ZonaCaricamento({ opzioni, onCaricato }: Props) {
  const [file, setFile] = useState<File[]>([]); // file scelti ma non ancora caricati
  const [sopra, setSopra] = useState(false); // true mentre un file è trascinato sopra la zona
  const [inCorso, setInCorso] = useState(false);
  const [esiti, setEsiti] = useState<Esito[]>([]);
  const [etichette, setEtichette] = useState<Etichette>({
    argomento: AUTOMATICO, // di solito l'app capisce da sola di cosa parlano gli appunti
    fonte: opzioni.fonti[0],
    data: oggi(),
  });
  const campoFile = useRef<HTMLInputElement>(null); // il selettore di file nascosto

  function aggiungi(nuovi: FileList | null) {
    if (nuovi && nuovi.length > 0) {
      setFile((precedenti) => [...precedenti, ...Array.from(nuovi)]);
      setEsiti([]);
    }
  }

  async function caricaTutti() {
    setInCorso(true);
    const risultati: Esito[] = [];
    // Un file alla volta, così se uno fallisce gli altri vengono caricati lo stesso
    for (const singolo of file) {
      try {
        const documento = await caricaDocumento(singolo, etichette);
        let messaggio = `${documento.numero_blocchi} blocchi indicizzati`;
        const altri = Object.keys(documento.argomenti_blocchi).filter((a) => a !== documento.argomento);
        if (documento.argomento_riconosciuto) messaggio += ` · argomento riconosciuto: ${documento.argomento}`;
        if (altri.length > 0) messaggio += ` · parla anche di ${altri.join(", ")}`;
        if (documento.ocr) {
          // Testo letto da foto o scansioni: invitiamo a ricontrollarlo
          const pagine = documento.ocr.pagine === 1 ? "1 pagina scritta a mano o fotografata" : `${documento.ocr.pagine} pagine scritte a mano o fotografate`;
          messaggio += ` · ${pagine}: controlla il testo riconosciuto con «Vedi blocchi»`;
          if (documento.ocr.incerta) {
            messaggio += " (lettura incerta: diverse parole potrebbero essere sbagliate, correggi almeno titoli, definizioni e teoremi)";
          }
        }
        risultati.push({ nome: singolo.name, ok: true, messaggio });
      } catch (errore) {
        risultati.push({ nome: singolo.name, ok: false, messaggio: (errore as Error).message });
      }
      setEsiti([...risultati]);
    }
    setFile([]);
    setInCorso(false);
    onCaricato();
  }

  return (
    <div>
      <div
        className={"zona-rilascio" + (sopra ? " sopra" : "")}
        role="button"
        tabIndex={0}
        onClick={() => campoFile.current?.click()}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && campoFile.current?.click()}
        onDragOver={(e) => {
          e.preventDefault(); // necessario perché il browser accetti il rilascio
          setSopra(true);
        }}
        onDragLeave={() => setSopra(false)}
        onDrop={(e) => {
          e.preventDefault();
          setSopra(false);
          aggiungi(e.dataTransfer.files);
        }}
      >
        <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true">
          <path d="M12 16V4 M7 9l5-5 5 5 M4 20h16" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <strong>Trascina qui i tuoi file</strong>
        <span className="nota">oppure clicca per sceglierli · {opzioni.estensioni.join("  ")}</span>
        <span className="nota">Anche foto e scansioni di appunti scritti a mano: il testo viene riconosciuto in automatico.</span>
        <input
          ref={campoFile}
          type="file"
          multiple
          hidden
          accept={opzioni.estensioni.join(",")}
          onChange={(e) => {
            aggiungi(e.target.files);
            e.target.value = ""; // permette di riscegliere lo stesso file
          }}
        />
      </div>

      <AnimatePresence>
        {file.length > 0 && (
          <motion.div
            className="da-caricare"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
          >
            <ul className="elenco-file">
              {file.map((singolo, i) => (
                <li key={singolo.name + i}>
                  <span>{singolo.name}</span>
                  <button
                    className="bottone-testo"
                    disabled={inCorso}
                    onClick={() => setFile(file.filter((_, j) => j !== i))}
                    aria-label={`Togli ${singolo.name}`}
                  >
                    togli
                  </button>
                </li>
              ))}
            </ul>
            <CampiEtichette opzioni={opzioni} valori={etichette} onCambia={setEtichette} conAuto />
            <div className="riga-azioni">
              <button className="bottone" onClick={caricaTutti} disabled={inCorso}>
                {inCorso ? "Caricamento…" : `Carica ${file.length} file`}
              </button>
              <span className="nota">
                {inCorso
                  ? "Le foto e le pagine scansionate richiedono qualche secondo l'una: il testo viene letto sul tuo computer."
                  : etichette.argomento === AUTOMATICO
                    ? "L'argomento viene riconosciuto per ogni file (e per ogni paragrafo): potrai correggerlo da «Vedi blocchi». Fonte e data valgono per tutti i file."
                    : "Le etichette valgono per tutti i file di questo gruppo; l'argomento di ogni paragrafo viene comunque riconosciuto."}
              </span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {esiti.length > 0 && (
        <ul className="elenco-esiti" aria-live="polite">
          {esiti.map((esito, i) => (
            <li key={i} className={esito.ok ? "ok" : "errore"}>
              <strong>{esito.ok ? "✓" : "✕"} {esito.nome}</strong> — {esito.messaggio}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
