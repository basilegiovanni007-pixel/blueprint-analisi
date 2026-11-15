// Grafico libero: scrivi una funzione e guardala. Se contiene altre lettere oltre a x
// (es. a*sin(b*x)), per ognuna compare un cursore che cambia il grafico in tempo reale.
import { useMemo, useState } from "react";

import { preparaFunzione } from "../api/client";
import Formula from "../componenti/Formula";
import Grafico from "../componenti/Grafico";
import Pannello from "../componenti/Pannello";
import CampoFunzione from "./CampoFunzione";
import Cursore from "./Cursore";
import { compila } from "./calcolo";
import { useRichiesta } from "./useRichiesta";

const ESEMPI = ["a*sin(b*x)", "a*x^2 + b*x + c", "e^(-a*x)*cos(b*x)", "1/(x^2 + a)", "sin(x)/x"];

export default function Esplora() {
  const [testo, setTesto] = useState("a*sin(b*x)");
  const [valori, setValori] = useState<Record<string, number>>({}); // valore attuale di ogni parametro

  // Chiediamo al backend di leggere la funzione (poco dopo che lo studente smette di scrivere)
  const { dati, errore } = useRichiesta(() => preparaFunzione(testo), [testo], testo.trim() !== "");

  // I parametri non ancora toccati valgono 1
  const parametri = useMemo(() => {
    const risultato: Record<string, number> = {};
    for (const nome of dati?.parametri ?? []) risultato[nome] = valori[nome] ?? 1;
    return risultato;
  }, [dati, valori]);

  const f = useMemo(() => (dati ? compila(dati.js, dati.variabile, parametri) : null), [dati, parametri]);

  return (
    <div className="griglia-pannelli">
      <Pannello titolo="Funzione" largo>
        <CampoFunzione etichetta="f(x) =" valore={testo} onCambia={setTesto} esempi={ESEMPI} errore={errore} />
      </Pannello>

      {dati && f && (
        <Pannello titolo="Grafico" largo>
          <div className="formula-scorrevole">
            <Formula latex={`f(x) = ${dati.latex}`} />
          </div>
          {dati.parametri.length > 0 && (
            <div className="cursori">
              {dati.parametri.map((nome) => (
                <Cursore
                  key={nome}
                  etichetta={nome}
                  valore={parametri[nome]}
                  min={-5}
                  max={5}
                  passo={0.1}
                  onCambia={(v) => setValori({ ...valori, [nome]: v })}
                />
              ))}
            </div>
          )}
          {/* Scala verticale fissa: così muovendo i cursori si vede la curva cambiare, non gli assi */}
          <Grafico
            chiave={dati.js}
            finestra={dati.parametri.length > 0 ? { xmin: -8, xmax: 8, ymin: -6, ymax: 6 } : { xmin: -8, xmax: 8 }}
            curve={[{ id: "f", f, disegna: dati.parametri.length === 0 }]}
            descrizione={`Grafico della funzione ${testo}`}
          />
          <p className="nota">Trascina per spostarti · Ctrl + rotella per lo zoom · doppio clic per tornare all'inizio</p>
        </Pannello>
      )}
    </div>
  );
}
