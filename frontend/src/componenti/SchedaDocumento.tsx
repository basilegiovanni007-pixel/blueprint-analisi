// Scheda di un documento del Magazzino: etichette, interruttore attivo/disattivo,
// modifica, eliminazione e l'elenco dei blocchi con il loro tipo e il loro argomento.
import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

import {
  eliminaDocumento,
  indirizzoFile,
  indirizzoPagina,
  leggiDocumento,
  modificaBlocco,
  modificaDocumento,
  type Blocco,
  type Documento,
  type Etichette,
  type Opzioni,
} from "../api/client";
import CampiEtichette from "./CampiEtichette";

type Props = {
  documento: Documento;
  opzioni: Opzioni;
  onCambiato: () => void; // avvisa la pagina di rileggere l'elenco
};

// Il testo di un blocco, con il pulsante "Correggi" che lo trasforma in un riquadro modificabile
type PropsTesto = {
  testo: string;
  onSalva: (testo: string) => Promise<void>;
  originale?: string; // indirizzo dell'immagine originale da mostrare mentre si corregge
};

function TestoBlocco({ testo, onSalva, originale }: PropsTesto) {
  const [bozza, setBozza] = useState<string | null>(null); // null = non in modifica
  const [salvataggio, setSalvataggio] = useState(false);

  if (bozza === null) {
    return (
      <>
        <p>{testo}</p>
        <button className="bottone-testo" onClick={() => setBozza(testo)}>
          Correggi
        </button>
      </>
    );
  }

  async function salva() {
    setSalvataggio(true);
    await onSalva(bozza!.trim());
    setSalvataggio(false);
    setBozza(null);
  }

  return (
    <div className="correzione">
      {/* La pagina originale sopra il testo: così si vede cosa c'era scritto davvero */}
      {originale && (
        <a href={originale} target="_blank" rel="noreferrer" className="correzione-originale" title="Apri l'immagine a tutto schermo">
          <img src={originale} alt="Pagina originale" />
        </a>
      )}
      <textarea
        className="campo-esercizio"
        value={bozza}
        onChange={(e) => setBozza(e.target.value)}
        rows={Math.min(14, bozza.split("\n").length + 2)}
        aria-label="Testo del blocco"
        autoFocus
      />
      <div className="riga-azioni">
        <button className="bottone" onClick={salva} disabled={salvataggio || !bozza.trim() || bozza.trim() === testo}>
          {salvataggio ? "Salvo…" : "Salva correzione"}
        </button>
        <button className="bottone-testo" onClick={() => setBozza(null)} disabled={salvataggio}>
          Annulla
        </button>
      </div>
    </div>
  );
}

export default function SchedaDocumento({ documento, opzioni, onCambiato }: Props) {
  const [blocchi, setBlocchi] = useState<Blocco[] | null>(null); // null = blocchi chiusi
  const [inModifica, setInModifica] = useState(false);
  const [bozza, setBozza] = useState<Etichette>({ ...documento }); // valori del modulo di modifica
  const [errore, setErrore] = useState("");

  // Esegue un'azione e, se fallisce, mostra il messaggio d'errore nella scheda
  async function prova(azione: () => Promise<unknown>) {
    setErrore("");
    try {
      await azione();
    } catch (e) {
      setErrore((e as Error).message);
    }
  }

  const apriChiudiBlocchi = () =>
    prova(async () => {
      if (blocchi) setBlocchi(null);
      else setBlocchi((await leggiDocumento(documento.id)).blocchi);
    });

  const cambiaAttivo = () =>
    prova(async () => {
      await modificaDocumento(documento.id, { attivo: !documento.attivo });
      onCambiato();
    });

  const salvaModifica = () =>
    prova(async () => {
      await modificaDocumento(documento.id, {
        titolo: bozza.titolo,
        argomento: bozza.argomento,
        fonte: bozza.fonte,
        data: bozza.data,
      });
      setInModifica(false);
      // Cambiando l'argomento del documento cambiano anche quelli dei blocchi: li rileggiamo
      if (blocchi) setBlocchi((await leggiDocumento(documento.id)).blocchi);
      onCambiato();
    });

  const elimina = () => {
    if (!window.confirm(`Eliminare "${documento.titolo}" dal Magazzino? L'operazione non si può annullare.`)) return;
    prova(async () => {
      await eliminaDocumento(documento.id);
      onCambiato();
    });
  };

  const cambiaTipo = (blocco: Blocco, tipo: string) =>
    prova(async () => {
      const aggiornato = await modificaBlocco(blocco.id, { tipo });
      setBlocchi((attuali) => attuali?.map((b) => (b.id === blocco.id ? aggiornato : b)) ?? null);
      onCambiato();
    });

  // L'argomento di un blocco è riconosciuto in automatico: qui lo studente lo può correggere
  const cambiaArgomento = (blocco: Blocco, argomento: string) =>
    prova(async () => {
      const aggiornato = await modificaBlocco(blocco.id, { argomento });
      setBlocchi((attuali) => attuali?.map((b) => (b.id === blocco.id ? aggiornato : b)) ?? null);
      onCambiato(); // aggiorna "Tratta anche" e la Mappa
    });

  // Correzione del testo di un blocco (utile soprattutto per il testo letto dalle foto)
  const correggi = (blocco: Blocco, testo: string) =>
    prova(async () => {
      const aggiornato = await modificaBlocco(blocco.id, { testo });
      setBlocchi((attuali) => attuali?.map((b) => (b.id === blocco.id ? aggiornato : b)) ?? null);
    });

  const dataLeggibile = new Date(documento.data).toLocaleDateString("it-IT");
  // Il file originale è una foto? Allora la mostriamo accanto ai blocchi, per confrontare
  const eFoto = /\.(png|jpe?g|webp|bmp|gif)$/i.test(documento.nome_file);
  // Gli altri argomenti di cui parla il documento, oltre al suo (es. un paragrafo sui limiti)
  const altriArgomenti = Object.entries(documento.argomenti_blocchi ?? {}).filter(([a]) => a !== documento.argomento);

  return (
    <motion.article
      layout
      className={"scheda" + (documento.attivo ? "" : " spenta")}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.97 }}
    >
      <div className="scheda-testa">
        <div className="scheda-titolo">
          <h3>{documento.titolo}</h3>
          <div className="etichette">
            <span className="etichetta accento">{documento.argomento}</span>
            <span className="etichetta">{documento.corso}</span>
            <span className="etichetta">{documento.fonte}</span>
            <span className="etichetta">{dataLeggibile}</span>
            <span className="etichetta">{documento.numero_blocchi} blocchi</span>
            {documento.letto_con_ocr && (
              <span className="etichetta etichetta-ocr" title="Il testo è stato riconosciuto da una foto o da una scansione">
                testo riconosciuto
              </span>
            )}
          </div>
          {altriArgomenti.length > 0 && (
            <p className="nota argomenti-trattati" title="Argomenti riconosciuti nei singoli blocchi: puoi correggerli da «Vedi blocchi»">
              Tratta anche:{" "}
              {altriArgomenti.map(([argomento, quanti]) => `${argomento} (${quanti} ${quanti === 1 ? "blocco" : "blocchi"})`).join(" · ")}
            </p>
          )}
        </div>

        {/* Interruttore: un documento disattivato resta nel Magazzino ma il risolutore lo ignora */}
        <label className="interruttore" title="Se disattivato, il risolutore ignora questo documento">
          <input type="checkbox" checked={documento.attivo} onChange={cambiaAttivo} />
          <span className="interruttore-binario" />
          <span className="interruttore-testo">{documento.attivo ? "Attivo" : "Disattivato"}</span>
        </label>
      </div>

      <div className="scheda-azioni">
        <button className="bottone-testo" onClick={apriChiudiBlocchi}>
          {blocchi ? "Nascondi blocchi" : "Vedi blocchi"}
        </button>
        <button
          className="bottone-testo"
          onClick={() => {
            setBozza({ ...documento });
            setInModifica(!inModifica);
          }}
        >
          {inModifica ? "Annulla modifica" : "Modifica"}
        </button>
        <a className="bottone-testo" href={indirizzoFile(documento.id)} target="_blank" rel="noreferrer">
          Apri originale
        </a>
        <button className="bottone-testo pericolo" onClick={elimina}>
          Elimina
        </button>
      </div>

      {errore && <p className="messaggio-errore">{errore}</p>}

      {inModifica && (
        <div className="scheda-modifica">
          <label className="campo">
            <span>Titolo</span>
            <input value={bozza.titolo ?? ""} onChange={(e) => setBozza({ ...bozza, titolo: e.target.value })} />
          </label>
          <CampiEtichette opzioni={opzioni} valori={bozza} onCambia={setBozza} />
          <div className="riga-azioni">
            <button className="bottone" onClick={salvaModifica}>
              Salva
            </button>
          </div>
        </div>
      )}

      {/* Testo letto da foto o scansioni: invito a controllarlo, con la foto accanto per confronto */}
      {blocchi && documento.letto_con_ocr && (
        <p className="messaggio-avviso avviso-ocr">
          Questo testo è stato riconosciuto automaticamente da pagine scritte a mano o fotografate. Controlla
          soprattutto titoli, definizioni e teoremi: con «Correggi» vedi la pagina originale e sistemi le parole
          sbagliate. Ricerca e risolutore usano subito il testo corretto.
        </p>
      )}

      <div className={blocchi && eFoto ? "revisione" : undefined}>
        {blocchi && eFoto && (
          <a className="revisione-foto" href={indirizzoFile(documento.id)} target="_blank" rel="noreferrer" title="Apri la foto a tutto schermo">
            <img src={indirizzoFile(documento.id)} alt={`Foto originale: ${documento.titolo}`} loading="lazy" />
          </a>
        )}
      <AnimatePresence>
        {blocchi && (
          <motion.ol
            className="elenco-blocchi"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
          >
            {blocchi.map((blocco) => (
              <li key={blocco.id} className="blocco">
                <div className="blocco-testa">
                  <select
                    className={"tipo tipo-" + blocco.tipo.replace(" ", "-")}
                    value={blocco.tipo}
                    onChange={(e) => cambiaTipo(blocco, e.target.value)}
                    aria-label="Tipo del blocco"
                  >
                    {opzioni.tipi_blocco.map((tipo) => (
                      <option key={tipo}>{tipo}</option>
                    ))}
                  </select>
                  {/* Argomento del blocco: evidenziato se è diverso da quello del documento */}
                  <select
                    className={"argomento-blocco" + (blocco.argomento !== documento.argomento ? " diverso" : "")}
                    value={blocco.argomento}
                    onChange={(e) => cambiaArgomento(blocco, e.target.value)}
                    aria-label="Argomento del blocco"
                    title="Argomento riconosciuto in automatico: correggilo se è sbagliato"
                  >
                    {Object.entries(opzioni.argomenti).map(([corso, argomenti]) => (
                      <optgroup key={corso} label={corso}>
                        {argomenti.map((argomento) => (
                          <option key={argomento}>{argomento}</option>
                        ))}
                      </optgroup>
                    ))}
                  </select>
                  {blocco.pagina && (
                    <a className="nota" href={indirizzoFile(documento.id, blocco.pagina)} target="_blank" rel="noreferrer">
                      p. {blocco.pagina}
                    </a>
                  )}
                </div>
                <TestoBlocco
                  testo={blocco.testo}
                  onSalva={(testo) => correggi(blocco, testo)}
                  originale={
                    // Testo letto con l'OCR da un PDF: mostriamo la sua pagina mentre lo si corregge
                    documento.letto_con_ocr && blocco.pagina ? indirizzoPagina(documento.id, blocco.pagina) : undefined
                  }
                />
              </li>
            ))}
          </motion.ol>
        )}
      </AnimatePresence>
      </div>
    </motion.article>
  );
}
