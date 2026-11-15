// Un esercizio dello Storico, con la sua soluzione e le stesse modalità di studio del Risolutore.
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { leggiEsercizio, risolvi, type EsercizioSalvato, type Soluzione } from "../api/client";
import Caricamento from "../componenti/Caricamento";
import Intestazione from "../componenti/Intestazione";
import VistaSoluzione from "../componenti/VistaSoluzione";

export default function DettaglioEsercizio() {
  const { id } = useParams(); // il numero nell'indirizzo, es. /storico/12
  const [esercizio, setEsercizio] = useState<EsercizioSalvato | null>(null);
  const [errore, setErrore] = useState("");
  const [inCorso, setInCorso] = useState(false);

  useEffect(() => {
    leggiEsercizio(Number(id))
      .then(setEsercizio)
      .catch((e: Error) => setErrore(e.message));
  }, [id]);

  // Risolve di nuovo l'esercizio: utile se nel frattempo hai caricato nuovi appunti
  // (le citazioni e la scelta del metodo dipendono dal Magazzino).
  async function risolviDiNuovo() {
    if (!esercizio) return;
    setInCorso(true);
    setErrore("");
    try {
      const nuova: Soluzione = await risolvi(esercizio.testo, esercizio.tipo_richiesto);
      setEsercizio({ ...esercizio, ...nuova });
    } catch (e) {
      setErrore((e as Error).message);
    }
    setInCorso(false);
  }

  return (
    <>
      <Intestazione
        etichetta="Tavola 05 · Storico"
        titolo={esercizio?.descrizione ?? "Esercizio"}
        descrizione={esercizio ? esercizio.testo : "Caricamento…"}
      />

      <div className="riga-azioni non-stampare" style={{ marginTop: -12, marginBottom: 22 }}>
        <Link className="bottone-contorno" to="/storico">
          ← Torna allo Storico
        </Link>
        {esercizio && (
          <button className="bottone-contorno" onClick={risolviDiNuovo} disabled={inCorso}>
            {inCorso ? "Risolvo…" : "⟲ Risolvi di nuovo con il Magazzino attuale"}
          </button>
        )}
      </div>

      {errore && <p className="messaggio-errore">{errore}</p>}
      {!esercizio && !errore && <Caricamento testo="Apro l'esercizio…" />}
      {inCorso && <Caricamento testo="Sto risolvendo di nuovo l'esercizio…" />}

      {esercizio && (
        <div className="griglia-pannelli">
          <VistaSoluzione soluzione={esercizio} testo={esercizio.testo} />
        </div>
      )}
    </>
  );
}
