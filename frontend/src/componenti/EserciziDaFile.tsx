// "Risolvi da file": lo studente carica un foglio di esercizi (PDF, Word, testo...),
// l'app elenca gli esercizi trovati e lui sceglie quale risolvere,
// cliccandolo oppure scrivendo il numero nella casella.
import { useRef, useState, type FormEvent } from "react";

import { leggiEserciziDaFile, type EsercizioDaFile } from "../api/client";

type Props = {
  onScelto: (testo: string) => void; // chiamata quando lo studente sceglie un esercizio
};

export default function EserciziDaFile({ onScelto }: Props) {
  const [nomeFile, setNomeFile] = useState("");
  const [esercizi, setEsercizi] = useState<EsercizioDaFile[]>([]);
  const [scelto, setScelto] = useState<number | null>(null);
  const [richiesta, setRichiesta] = useState(""); // ciò che lo studente scrive nella casella
  const [errore, setErrore] = useState("");
  const [inCorso, setInCorso] = useState(false);
  const [sopra, setSopra] = useState(false);
  const campoFile = useRef<HTMLInputElement>(null);

  async function leggi(file: File | undefined) {
    if (!file) return;
    setInCorso(true);
    setErrore("");
    setEsercizi([]);
    setScelto(null);
    try {
      const risposta = await leggiEserciziDaFile(file);
      setNomeFile(risposta.nome_file);
      setEsercizi(risposta.esercizi);
      // Un solo esercizio nel file: non c'è niente da scegliere, lo risolviamo subito
      if (risposta.esercizi.length === 1) scegli(risposta.esercizi[0]);
    } catch (e) {
      setErrore((e as Error).message);
    }
    setInCorso(false);
  }

  function scegli(esercizio: EsercizioDaFile) {
    setScelto(esercizio.numero);
    setErrore("");
    onScelto(esercizio.testo);
  }

  // Lo studente ha scritto qualcosa tipo "il 3" oppure "esercizio 2": cerchiamo il numero
  function scegliDaTesto(evento: FormEvent) {
    evento.preventDefault();
    const numero = Number(richiesta.match(/\d+/)?.[0]);
    const esercizio = esercizi.find((e) => e.numero === numero);
    if (esercizio) {
      scegli(esercizio);
      setRichiesta("");
    } else {
      const numeri = esercizi.map((e) => e.numero).join(", ");
      setErrore(`Non trovo quell'esercizio. In questo file ci sono gli esercizi: ${numeri}.`);
    }
  }

  return (
    <div>
      <div
        className={"zona-rilascio compatta" + (sopra ? " sopra" : "")}
        role="button"
        tabIndex={0}
        onClick={() => campoFile.current?.click()}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && campoFile.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setSopra(true);
        }}
        onDragLeave={() => setSopra(false)}
        onDrop={(e) => {
          e.preventDefault();
          setSopra(false);
          leggi(e.dataTransfer.files[0]);
        }}
      >
        <strong>{inCorso ? "Leggo il file…" : "Trascina qui un file di esercizi"}</strong>
        <span className="nota">oppure clicca per sceglierlo · .pdf .docx .txt .md .tex</span>
        <input
          ref={campoFile}
          type="file"
          hidden
          accept=".pdf,.docx,.txt,.md,.tex"
          onChange={(e) => {
            leggi(e.target.files?.[0]);
            e.target.value = "";
          }}
        />
      </div>

      {errore && <p className="messaggio-errore" style={{ marginTop: 14 }}>{errore}</p>}

      {esercizi.length > 1 && (
        <div className="scelta-esercizio">
          <p>
            In <strong>{nomeFile}</strong> ho trovato {esercizi.length} esercizi. Quale risolvo?
          </p>
          <ul className="elenco-esercizi">
            {esercizi.map((esercizio) => (
              <li key={esercizio.numero}>
                <button
                  className={"esercizio" + (scelto === esercizio.numero ? " scelto" : "")}
                  onClick={() => scegli(esercizio)}
                >
                  <span className="passaggio-numero">{String(esercizio.numero).padStart(2, "0")}</span>
                  <span>{esercizio.testo}</span>
                </button>
              </li>
            ))}
          </ul>
          <form className="riga-ricerca" onSubmit={scegliDaTesto}>
            <input
              className="campo-ricerca"
              value={richiesta}
              onChange={(e) => setRichiesta(e.target.value)}
              placeholder='Oppure scrivi quale: "risolvi il 3"'
              aria-label="Quale esercizio risolvere"
            />
            <button className="bottone" disabled={!richiesta.trim()}>
              Risolvi
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
