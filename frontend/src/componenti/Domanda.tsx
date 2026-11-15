// Una domanda di "Mettimi alla prova": lo studente scrive la risposta, l'app la controlla
// (senza mai rivelare quella giusta) e dice se è corretta.
import { useState, type FormEvent } from "react";
import { motion, useAnimationControls } from "framer-motion";

import type { EsitoRisposta } from "../api/client";
import TestoConFormule from "./TestoConFormule";

type Props = {
  domanda: string; // può contenere formule tra $...$
  scelta?: boolean; // true = si risponde con due pulsanti (es. "converge" / "non converge")
  controlla: (risposta: string) => Promise<EsitoRisposta>;
  onCorretta: (messaggio: string) => void; // risposta giusta: si va avanti
  onRivela: () => void; // lo studente si arrende e vuole vedere la soluzione
  testoRivela?: string;
};

export default function Domanda({ domanda, scelta, controlla, onCorretta, onRivela, testoRivela = "Mostra il passaggio" }: Props) {
  const [risposta, setRisposta] = useState("");
  const [messaggio, setMessaggio] = useState("");
  const [inCorso, setInCorso] = useState(false);
  const scossone = useAnimationControls(); // a ogni errore il riquadro "trema"

  async function invia(testo: string) {
    if (!testo.trim()) return;
    setInCorso(true);
    try {
      const esito = await controlla(testo);
      if (esito.corretto) {
        onCorretta(esito.messaggio);
      } else {
        setMessaggio(esito.messaggio);
        scossone.start({ x: [0, -9, 9, -5, 5, 0], transition: { duration: 0.4 } });
      }
    } catch (e) {
      // Errori di scrittura (es. parentesi non chiuse): non contano come tentativo sbagliato
      setMessaggio((e as Error).message);
    }
    setInCorso(false);
  }

  function suInvio(evento: FormEvent) {
    evento.preventDefault(); // niente ricaricamento della pagina
    invia(risposta);
  }

  return (
    <motion.div className="domanda" animate={scossone}>
      <p className="domanda-testo">
        <span className="domanda-etichetta">Prova tu</span> <TestoConFormule testo={domanda} />
      </p>

      {scelta ? (
        <div className="riga-azioni">
          <button className="bottone" onClick={() => invia("converge")} disabled={inCorso}>
            Converge
          </button>
          <button className="bottone" onClick={() => invia("non converge")} disabled={inCorso}>
            Non converge
          </button>
          <button className="bottone-testo" onClick={onRivela}>
            {testoRivela}
          </button>
        </div>
      ) : (
        <form className="riga-ricerca" onSubmit={suInvio}>
          <input
            className="campo-ricerca campo-risposta"
            value={risposta}
            onChange={(e) => setRisposta(e.target.value)}
            placeholder="La tua risposta, es. 2x*cos(x)"
            aria-label="La tua risposta"
            spellCheck={false}
            autoComplete="off"
            autoFocus
          />
          <button className="bottone" disabled={inCorso || !risposta.trim()}>
            {inCorso ? "Controllo…" : "Controlla"}
          </button>
          <button type="button" className="bottone-testo" onClick={onRivela}>
            {testoRivela}
          </button>
        </form>
      )}

      {messaggio && (
        <p className="domanda-sbagliata" role="status">
          ✕ {messaggio}
        </p>
      )}
    </motion.div>
  );
}

/** Il "bollino" verde che compare sotto un passaggio indovinato. */
export function Bollino({ messaggio }: { messaggio: string }) {
  return (
    <motion.p
      className="bollino-corretto"
      initial={{ scale: 0.5, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ type: "spring", stiffness: 420, damping: 16 }}
    >
      ✓ {messaggio}
    </motion.p>
  );
}
