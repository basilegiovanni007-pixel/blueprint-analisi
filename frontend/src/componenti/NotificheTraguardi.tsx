// Quando lo studente raggiunge un traguardo compare una notifica in basso a sinistra,
// con il timbro che "si stampa" sulla pagina. Sparisce da sola dopo qualche secondo.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";

import { EVENTO_PROGRESSI, type Progressi, type Traguardo } from "../api/client";
import Timbro from "./Timbro";

const DURATA = 6000; // millisecondi in cui la notifica resta visibile

export default function NotificheTraguardi() {
  const [coda, setCoda] = useState<Traguardo[]>([]); // traguardi in attesa di essere mostrati

  // Ascoltiamo l'evento lanciato da aggiornaProgressi() (vedi api/client.ts)
  useEffect(() => {
    const ascolta = (evento: Event) => {
      const nuovi = (evento as CustomEvent<Progressi>).detail.nuovi;
      if (nuovi.length > 0) setCoda((attuale) => [...attuale, ...nuovi]);
    };
    window.addEventListener(EVENTO_PROGRESSI, ascolta);
    return () => window.removeEventListener(EVENTO_PROGRESSI, ascolta);
  }, []);

  // Mostriamo un traguardo alla volta: dopo DURATA passiamo al successivo
  const attuale = coda[0];
  useEffect(() => {
    if (!attuale) return;
    const timer = window.setTimeout(() => setCoda((c) => c.slice(1)), DURATA);
    return () => window.clearTimeout(timer);
  }, [attuale]);

  return (
    <div className="notifiche" aria-live="polite">
      <AnimatePresence>
        {attuale && (
          <motion.div
            key={attuale.chiave}
            className="notifica-traguardo"
            initial={{ opacity: 0, y: 30, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, transition: { duration: 0.25, ease: "easeIn" } }}
            transition={{ type: "spring", stiffness: 260, damping: 22 }}
          >
            {/* Il timbro arriva dall'alto, ruotato, e si "stampa" sulla notifica */}
            <motion.div
              initial={{ scale: 2.2, rotate: -25, opacity: 0 }}
              animate={{ scale: 1, rotate: -8, opacity: 1 }}
              transition={{ delay: 0.25, type: "spring", stiffness: 380, damping: 14 }}
            >
              <Timbro simbolo={attuale.simbolo} ottenuto />
            </motion.div>
            <div>
              <small>Traguardo raggiunto</small>
              <strong>{attuale.titolo}</strong>
              <span>{attuale.descrizione}</span>
              <Link to="/progressi" onClick={() => setCoda([])}>
                Vedi tutti i traguardi
              </Link>
            </div>
            <button className="notifica-chiudi" onClick={() => setCoda((c) => c.slice(1))} aria-label="Chiudi la notifica">
              ×
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
