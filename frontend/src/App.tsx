// Struttura generale dell'app: barra laterale a sinistra, pagina a destra, cartiglio in basso.
import { Route, Routes, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";

import BarraLaterale from "./componenti/BarraLaterale";
import Cartiglio from "./componenti/Cartiglio";
import { FornitoreCartiglio } from "./componenti/ContestoCartiglio";
import Risolutore from "./pagine/Risolutore";
import Grafici from "./pagine/Grafici";
import Magazzino from "./pagine/Magazzino";
import Mappa from "./pagine/Mappa";
import Storico from "./pagine/Storico";
import DettaglioEsercizio from "./pagine/DettaglioEsercizio";
import Progressi from "./pagine/Progressi";
import NotificheTraguardi from "./componenti/NotificheTraguardi";

// Titolo mostrato nel cartiglio per ogni pagina (in base alla prima parte dell'indirizzo)
const TITOLI: Record<string, string> = {
  "": "Risolutore",
  grafici: "Grafici",
  magazzino: "Magazzino",
  mappa: "Mappa della conoscenza",
  storico: "Storico",
  progressi: "Progressi",
};

export default function App() {
  const posizione = useLocation(); // in quale pagina siamo
  const sezione = posizione.pathname.split("/")[1] ?? "";

  return (
    <FornitoreCartiglio>
      <div className="impaginazione">
        <BarraLaterale />

        <main className="contenuto">
          {/* AnimatePresence + motion: transizione morbida quando si cambia pagina */}
          <AnimatePresence mode="wait">
            <motion.div
              key={posizione.pathname}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.22 }}
            >
              <Routes location={posizione}>
                <Route path="/" element={<Risolutore />} />
                <Route path="/grafici" element={<Grafici />} />
                <Route path="/magazzino" element={<Magazzino />} />
                <Route path="/mappa" element={<Mappa />} />
                <Route path="/storico" element={<Storico />} />
                <Route path="/storico/:id" element={<DettaglioEsercizio />} />
                <Route path="/progressi" element={<Progressi />} />
              </Routes>

              <Cartiglio pagina={TITOLI[sezione] ?? "Blueprint"} />
            </motion.div>
          </AnimatePresence>
        </main>

        {/* Le notifiche dei traguardi raggiunti, valide in tutte le pagine */}
        <NotificheTraguardi />
      </div>
    </FornitoreCartiglio>
  );
}
