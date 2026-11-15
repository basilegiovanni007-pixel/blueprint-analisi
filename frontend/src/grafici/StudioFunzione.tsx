// Studio di funzione animato: a sinistra le tappe (dominio, asintoti, massimi e minimi...),
// a destra il grafico che si costruisce un pezzo alla volta, in sincronia con le tappe.
import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";

import { studiaFunzione, type StudioFunzione as Studio } from "../api/client";
import Fonte from "../componenti/Fonte";
import Formula from "../componenti/Formula";
import Grafico from "../componenti/Grafico";
import Pannello from "../componenti/Pannello";
import TestoConFormule from "../componenti/TestoConFormule";
import CampoFunzione from "./CampoFunzione";
import { compila } from "./calcolo";

const ESEMPI = ["x^3 - 3x", "(x^2+1)/(x-1)", "x*e^(-x)", "ln(x)/x", "e^(-x^2)", "sin(x)"];

export default function StudioFunzione() {
  const [testo, setTesto] = useState("x^3 - 3x");
  const [studio, setStudio] = useState<Studio | null>(null);
  const [errore, setErrore] = useState("");
  const [inCorso, setInCorso] = useState(false);
  const [corrente, setCorrente] = useState(0); // indice dell'ultima tappa mostrata
  const [riproduzione, setRiproduzione] = useState(false); // true = le tappe avanzano da sole

  async function avvia() {
    if (!testo.trim()) return;
    setInCorso(true);
    setErrore("");
    try {
      setStudio(await studiaFunzione(testo));
      setCorrente(0);
      setRiproduzione(true); // appena pronto, parte l'animazione
    } catch (e) {
      setStudio(null);
      setErrore((e as Error).message);
    }
    setInCorso(false);
  }

  const ultima = studio ? studio.tappe.length - 1 : 0;

  // Riproduzione automatica: ogni 2,8 secondi si passa alla tappa successiva
  useEffect(() => {
    if (!riproduzione || !studio) return;
    if (corrente >= ultima) {
      setRiproduzione(false);
      return;
    }
    const timer = window.setTimeout(() => setCorrente((c) => c + 1), 2800);
    return () => window.clearTimeout(timer);
  }, [riproduzione, corrente, ultima, studio]);

  // La funzione in una forma che il browser può calcolare
  const f = useMemo(() => (studio ? compila(studio.funzione.js, studio.funzione.variabile) : null), [studio]);

  // Sul grafico compaiono solo gli elementi delle tappe già raggiunte
  const elementi = useMemo(
    () => (studio ? studio.tappe.slice(0, corrente + 1).flatMap((t) => t.elementi) : []),
    [studio, corrente],
  );
  const curvaVisibile = elementi.some((e) => e.tipo === "curva");

  // Scala verticale: la scegliamo in modo che massimi, minimi, flessi e zeri stiano comodi nel
  // disegno. (Se lasciassimo fare alla funzione, i valori enormi ai bordi schiaccerebbero tutto.)
  const finestra = useMemo(() => {
    if (!studio) return { xmin: -8, xmax: 8 };
    const altezze = studio.tappe.flatMap((t) => t.elementi).flatMap((e) => (e.tipo === "punto" ? [e.y] : []));
    const basso = Math.min(...altezze);
    const alto = Math.max(...altezze);
    if (altezze.length < 2 || alto - basso < 1e-9) return studio.finestra; // pochi punti: scala automatica
    const margine = (alto - basso) * 1.2;
    return { ...studio.finestra, ymin: basso - margine, ymax: alto + margine };
  }, [studio]);

  function vai(indice: number) {
    setRiproduzione(false);
    setCorrente(Math.max(0, Math.min(ultima, indice)));
  }

  return (
    <div className="griglia-pannelli">
      <Pannello titolo="Funzione da studiare" largo>
        <CampoFunzione etichetta="f(x) =" valore={testo} onCambia={setTesto} esempi={ESEMPI} errore={errore}>
          <button className="bottone" onClick={avvia} disabled={inCorso || !testo.trim()}>
            {inCorso ? "Studio…" : "Studia"}
          </button>
        </CampoFunzione>
      </Pannello>

      {studio && f && (
        <div className="studio pannello-largo">
          <Pannello titolo="Tappe dello studio">
            <ol className="tappe">
              {studio.tappe.map((tappa, i) => (
                <li key={tappa.titolo} className={"tappa" + (i === corrente ? " attuale" : "") + (i > corrente ? " futura" : "")}>
                  <button className="tappa-titolo" onClick={() => vai(i)} aria-current={i === corrente}>
                    <span className="passaggio-numero">{String(i + 1).padStart(2, "0")}</span>
                    {tappa.titolo}
                  </button>
                  {/* Il contenuto si vede solo per le tappe già raggiunte */}
                  {i <= corrente && (
                    <motion.div className="tappa-corpo" initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }}>
                      <p>
                        <TestoConFormule testo={tappa.testo} />
                      </p>
                      {tappa.formule.map((formula) => (
                        <div key={formula} className="formula-scorrevole">
                          <Formula blocco latex={formula} />
                        </div>
                      ))}
                      <Fonte concetto={tappa.concetto} citazione={tappa.citazione} mancante={tappa.mancante} />
                    </motion.div>
                  )}
                </li>
              ))}
            </ol>
          </Pannello>

          <div className="studio-grafico">
            <Pannello titolo="Grafico">
              <div className="formula-scorrevole">
                <Formula latex={`f(x) = ${studio.funzione.latex}`} />
              </div>
              <Grafico
                chiave={studio.funzione.js}
                finestra={finestra}
                elementi={elementi}
                curve={[{ id: "f", f, disegna: true, visibile: curvaVisibile }]}
                descrizione={`Grafico della funzione ${testo}`}
              />
              <div className="riga-azioni comandi-studio">
                <button className="bottone-contorno" onClick={() => vai(corrente - 1)} disabled={corrente === 0}>
                  ◀ Indietro
                </button>
                <button className="bottone-contorno" onClick={() => vai(corrente + 1)} disabled={corrente === ultima}>
                  Avanti ▶
                </button>
                <button
                  className="bottone-contorno"
                  onClick={() => {
                    if (corrente === ultima) setCorrente(0); // dalla fine si ricomincia da capo
                    setRiproduzione(!riproduzione);
                  }}
                >
                  {riproduzione ? "❚❚ Pausa" : "▶ Riproduci"}
                </button>
                <button className="bottone-contorno" onClick={() => vai(ultima)} disabled={corrente === ultima}>
                  Mostra tutto
                </button>
              </div>
              <p className="nota">Trascina per spostarti · Ctrl + rotella per lo zoom · doppio clic per tornare all'inizio</p>
            </Pannello>
          </div>
        </div>
      )}
    </div>
  );
}
