// Scheda di un documento del Magazzino: etichette, interruttore attivo/disattivo,
// modifica, eliminazione e l'elenco dei blocchi con il loro tipo.
import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

import {
  eliminaDocumento,
  indirizzoFile,
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

  const dataLeggibile = new Date(documento.data).toLocaleDateString("it-IT");

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
          </div>
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
                  {blocco.pagina && (
                    <a className="nota" href={indirizzoFile(documento.id, blocco.pagina)} target="_blank" rel="noreferrer">
                      p. {blocco.pagina}
                    </a>
                  )}
                </div>
                <p>{blocco.testo}</p>
              </li>
            ))}
          </motion.ol>
        )}
      </AnimatePresence>
    </motion.article>
  );
}
