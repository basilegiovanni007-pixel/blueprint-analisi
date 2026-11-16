// Barra laterale di navigazione: tutte le sezioni dell'app, sempre a un clic,
// più la serie di giorni di studio consecutivi.
import { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import { motion } from "framer-motion";

import { EVENTO_PROGRESSI, aggiornaProgressi, type Progressi } from "../api/client";

// Piccole icone disegnate "a tratto", come su un progetto tecnico.
// Ogni icona è un insieme di linee SVG.
function Icona({ tracciato }: { tracciato: string }) {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={tracciato} />
    </svg>
  );
}

const VOCI = [
  // Risolutore: una curva su due assi
  { percorso: "/", nome: "Risolutore", icona: "M3 3v18h18 M6 16c3-9 6-9 8-3s4 2 5-6" },
  // Grafici: una parabola con la sua tangente
  { percorso: "/grafici", nome: "Grafici", icona: "M3 20h18 M5 5c2 14 12 14 14 0 M8 20l9-9" },
  // Magazzino: uno scaffale
  { percorso: "/magazzino", nome: "Magazzino", icona: "M3 4h18v16H3z M3 9.5h18 M3 15h18 M9 4v16" },
  // Mappa: nodi collegati
  {
    percorso: "/mappa",
    nome: "Mappa",
    icona: "M5 6h.01 M19 6h.01 M12 12h.01 M5 18h.01 M19 18h.01 M5 6l7 6 7-6 M5 18l7-6 7 6",
  },
  // Storico: un orologio
  { percorso: "/storico", nome: "Storico", icona: "M12 3a9 9 0 1 0 0 18a9 9 0 0 0 0-18z M12 7v5l3.5 2" },
  // Progressi: una medaglia appesa al nastro
  { percorso: "/progressi", nome: "Progressi", icona: "M8 3l4 6 4-6 M12 9a6 6 0 1 0 0 12a6 6 0 0 0 0-12z M12 13l1.2 2.2h2.3l-1.9 1.4.7 2.3-2.3-1.4-2.3 1.4.7-2.3-1.9-1.4h2.3z" },
];

// La serie di giorni di studio, in fondo alla barra: si aggiorna da sola
function SerieGiorni() {
  const [serie, setSerie] = useState<Progressi["serie"] | null>(null);

  useEffect(() => {
    const ascolta = (evento: Event) => setSerie((evento as CustomEvent<Progressi>).detail.serie);
    window.addEventListener(EVENTO_PROGRESSI, ascolta);
    void aggiornaProgressi(); // prima lettura all'avvio dell'app
    return () => window.removeEventListener(EVENTO_PROGRESSI, ascolta);
  }, []);

  if (!serie) return null;
  return (
    <NavLink to="/progressi" className="barra-serie" title="Giorni di studio consecutivi">
      <motion.strong key={serie.attuale} initial={{ scale: 1.6 }} animate={{ scale: 1 }} className={serie.studiato_oggi ? "accesa" : ""}>
        {serie.attuale}
      </motion.strong>
      <span>
        {serie.attuale === 1 ? "giorno" : "giorni"} di fila
        <br />
        <small>{serie.studiato_oggi ? "oggi ✓" : "studia oggi!"}</small>
      </span>
    </NavLink>
  );
}

export default function BarraLaterale() {
  return (
    <nav className="barra" aria-label="Navigazione principale">
      <div className="barra-logo">
        <strong>BLUEPRINT</strong>
        <span>Analisi I · II</span>
      </div>

      <div className="barra-voci">
        {VOCI.map((voce) => (
          <NavLink
            key={voce.percorso}
            to={voce.percorso}
            end={voce.percorso === "/"} // "Storico" resta evidenziato anche aprendo un esercizio (/storico/12)
            className={({ isActive }) => "barra-voce" + (isActive ? " attiva" : "")}
          >
            {({ isActive }) => (
              <>
                {/* layoutId fa "scivolare" il rettangolo giallo da una voce all'altra */}
                {isActive && (
                  <motion.span
                    layoutId="evidenza-barra"
                    className="barra-evidenza"
                    transition={{ type: "spring", stiffness: 420, damping: 34 }}
                  />
                )}
                <Icona tracciato={voce.icona} />
                <span>{voce.nome}</span>
              </>
            )}
          </NavLink>
        ))}
      </div>

      <SerieGiorni />
      <div className="barra-piede">v1.1 · Analisi I e II</div>
    </nav>
  );
}
