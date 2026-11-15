// Pagina Storico: tutti gli esercizi risolti, dal più recente. Un clic apre la soluzione.
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";

import { eliminaEsercizio, elencaStorico, type VoceStorico } from "../api/client";
import Caricamento from "../componenti/Caricamento";
import Formula from "../componenti/Formula";
import Intestazione from "../componenti/Intestazione";
import Pannello from "../componenti/Pannello";

export default function Storico() {
  const [esercizi, setEsercizi] = useState<VoceStorico[] | null>(null); // null = in caricamento
  const [errore, setErrore] = useState("");
  const [filtro, setFiltro] = useState(""); // tipo di esercizio ("" = tutti)
  const [cerca, setCerca] = useState("");

  useEffect(() => {
    elencaStorico()
      .then(setEsercizi)
      .catch((e: Error) => setErrore(e.message));
  }, []);

  // I tipi presenti nello Storico, per il menu del filtro
  const tipi = useMemo(() => [...new Set((esercizi ?? []).map((e) => e.descrizione))].sort(), [esercizi]);

  const mostrati = (esercizi ?? []).filter(
    (e) => (!filtro || e.descrizione === filtro) && e.testo.toLowerCase().includes(cerca.trim().toLowerCase()),
  );

  async function elimina(esercizio: VoceStorico) {
    if (!window.confirm(`Togliere "${esercizio.testo}" dallo Storico?`)) return;
    try {
      await eliminaEsercizio(esercizio.id);
      setEsercizi((attuali) => (attuali ?? []).filter((e) => e.id !== esercizio.id));
    } catch (e) {
      setErrore((e as Error).message);
    }
  }

  return (
    <>
      <Intestazione
        etichetta="Tavola 05"
        titolo="Storico"
        descrizione="Ogni esercizio risolto, con la sua spiegazione. Riaprilo per ripassarlo, metterti alla prova o esportarlo in PDF."
      />

      {errore && <p className="messaggio-errore">{errore}</p>}

      {esercizi === null && !errore && <Caricamento testo="Apro lo Storico…" />}

      <div className="griglia-pannelli">
        {esercizi && esercizi.length === 0 && (
          <Pannello titolo="Ancora nessun esercizio" largo>
            <p>
              Gli esercizi che risolvi compaiono qui automaticamente. <Link to="/">Vai al Risolutore</Link> per cominciare.
            </p>
          </Pannello>
        )}

        {esercizi && esercizi.length > 0 && (
          <Pannello titolo={`Esercizi risolti (${mostrati.length})`} largo>
            <div className="campi filtri-storico">
              <label className="campo">
                <span>Tipo</span>
                <select value={filtro} onChange={(e) => setFiltro(e.target.value)}>
                  <option value="">Tutti</option>
                  {tipi.map((tipo) => (
                    <option key={tipo}>{tipo}</option>
                  ))}
                </select>
              </label>
              <label className="campo">
                <span>Cerca</span>
                <input value={cerca} onChange={(e) => setCerca(e.target.value)} placeholder="es. sin(x)" />
              </label>
            </div>

            <ul className="elenco-storico">
              <AnimatePresence>
                {mostrati.map((esercizio) => (
                  <motion.li key={esercizio.id} layout exit={{ opacity: 0, scale: 0.97 }} className="voce-storico">
                    <Link to={`/storico/${esercizio.id}`} className="voce-storico-link">
                      <div className="etichette">
                        <span className="etichetta accento">{esercizio.descrizione}</span>
                        <span className="etichetta">{esercizio.argomento}</span>
                        <span className="etichetta">{new Date(esercizio.risolto_il).toLocaleDateString("it-IT")}</span>
                        {esercizio.documento_id !== null && <span className="etichetta">nel Magazzino</span>}
                      </div>
                      {/* Mostriamo l'esercizio ma non il risultato: così si può riprovare a risolverlo */}
                      <div className="formula-scorrevole">
                        <Formula latex={esercizio.problema_latex} />
                      </div>
                      <span className="nota">{esercizio.testo}</span>
                    </Link>
                    <button className="bottone-testo pericolo" onClick={() => elimina(esercizio)} aria-label={`Elimina ${esercizio.testo}`}>
                      Elimina
                    </button>
                  </motion.li>
                ))}
              </AnimatePresence>
            </ul>
            {mostrati.length === 0 && <p className="nota">Nessun esercizio corrisponde ai filtri.</p>}
          </Pannello>
        )}
      </div>
    </>
  );
}
