// Polinomi di Taylor: un polinomio che imita la funzione vicino a un punto.
// Aumentando l'ordine il polinomio "abbraccia" la funzione su un tratto sempre più lungo.
import { useMemo, useState } from "react";

import { polinomiTaylor } from "../api/client";
import Formula from "../componenti/Formula";
import Grafico from "../componenti/Grafico";
import Pannello from "../componenti/Pannello";
import CampoFunzione from "./CampoFunzione";
import Cursore from "./Cursore";
import { compila } from "./calcolo";
import { useRichiesta } from "./useRichiesta";

const ESEMPI = ["sin(x)", "cos(x)", "e^x", "ln(1+x)", "1/(1-x)", "sqrt(1+x)"];
const ORDINE_MASSIMO = 10;

export default function Taylor() {
  const [testo, setTesto] = useState("sin(x)");
  const [centro, setCentro] = useState("0");
  const [ordine, setOrdine] = useState(3);

  // Il backend calcola in una volta sola tutti i polinomi fino all'ordine massimo
  const { dati, errore } = useRichiesta(
    () => polinomiTaylor(testo, centro, ORDINE_MASSIMO),
    [testo, centro],
    testo.trim() !== "" && centro.trim() !== "",
  );

  const f = useMemo(() => (dati ? compila(dati.funzione.js) : null), [dati]);
  const polinomio = dati?.polinomi[ordine];
  const p = useMemo(() => (polinomio ? compila(polinomio.js) : null), [polinomio]);

  return (
    <div className="griglia-pannelli">
      <Pannello titolo="Funzione e centro dello sviluppo" largo>
        <CampoFunzione etichetta="f(x) =" valore={testo} onCambia={setTesto} esempi={ESEMPI} errore={errore}>
          <label className="campo campo-stretto">
            <span>centro x₀ =</span>
            <input value={centro} onChange={(e) => setCentro(e.target.value)} />
          </label>
        </CampoFunzione>
      </Pannello>

      {dati && f && p && polinomio && (
        <Pannello titolo="Polinomio di Taylor" largo>
          <div className="cursori">
            <Cursore etichetta="ordine n" valore={ordine} min={0} max={ORDINE_MASSIMO} passo={1} onCambia={setOrdine} />
          </div>
          <Grafico
            chiave={`${dati.funzione.js}|${dati.centro}`}
            finestra={{ xmin: dati.centro - 7, xmax: dati.centro + 7 }}
            curve={[
              { id: "f", f },
              { id: "p", f: p, stile: "seconda" },
            ]}
            elementi={[{ tipo: "punto", x: dati.centro, y: f(dati.centro), etichetta: "x₀" }]}
            descrizione={`Grafico di ${testo} e del suo polinomio di Taylor di ordine ${ordine}`}
          />
          <div className="letture">
            <div className="lettura">
              <span className="legenda legenda-principale" />
              <small>Funzione</small>
              <div className="formula-scorrevole">
                <Formula latex={`f(x) = ${dati.funzione.latex}`} />
              </div>
            </div>
            <div className="lettura">
              <span className="legenda legenda-seconda" />
              <small>Polinomio di Taylor di ordine {ordine}</small>
              <div className="formula-scorrevole">
                <Formula latex={`P_{${ordine}}(x) = ${polinomio.latex}`} />
              </div>
            </div>
          </div>
          <p className="nota">Aumenta l'ordine: il polinomio segue la funzione sempre più lontano dal centro.</p>
        </Pannello>
      )}
    </div>
  );
}
