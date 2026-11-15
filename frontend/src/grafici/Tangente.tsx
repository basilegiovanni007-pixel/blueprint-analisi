// Retta tangente e rapporto incrementale.
// La retta secante passa per i punti di ascissa x0 e x0+h: la sua pendenza è il rapporto
// incrementale. Facendo tendere h a zero la secante diventa la tangente, e la pendenza
// diventa la derivata.
import { useMemo, useState } from "react";

import { preparaFunzione } from "../api/client";
import Formula from "../componenti/Formula";
import Grafico, { type Elemento } from "../componenti/Grafico";
import Pannello from "../componenti/Pannello";
import CampoFunzione from "./CampoFunzione";
import Cursore from "./Cursore";
import { compila, derivataNumerica, formatta } from "./calcolo";
import { useRichiesta } from "./useRichiesta";

const ESEMPI = ["x^2", "sin(x)", "e^x", "x^3 - 2x", "sqrt(x)"];

export default function Tangente() {
  const [testo, setTesto] = useState("x^2");
  const [x0, setX0] = useState(1);
  const [h, setH] = useState(1.5);

  const { dati, errore } = useRichiesta(() => preparaFunzione(testo), [testo], testo.trim() !== "");
  const conParametri = dati && dati.parametri.length > 0;
  const f = useMemo(() => (dati && !conParametri ? compila(dati.js, dati.variabile) : null), [dati, conParametri]);

  // Tutti i numeri che servono, ricalcolati quando si muove un cursore
  const y0 = f ? f(x0) : NaN;
  const y1 = f ? f(x0 + h) : NaN;
  const rapporto = (y1 - y0) / h; // pendenza della secante
  const derivata = f ? derivataNumerica(f, x0) : NaN; // pendenza della tangente

  const elementi: Elemento[] = [];
  if (Number.isFinite(y0)) {
    if (Number.isFinite(derivata)) {
      // Retta per (x0, y0) con pendenza m: y = m·x + (y0 − m·x0)
      elementi.push({ tipo: "retta", m: derivata, q: y0 - derivata * x0, stile: "tangente" });
    }
    if (Number.isFinite(rapporto)) {
      elementi.push({ tipo: "retta", m: rapporto, q: y0 - rapporto * x0, stile: "secante" });
      elementi.push({ tipo: "punto", x: x0 + h, y: y1, etichetta: "Q", stile: "secondario" });
    }
    elementi.push({ tipo: "punto", x: x0, y: y0, etichetta: "P", stile: "zero" });
  }

  return (
    <div className="griglia-pannelli">
      <Pannello titolo="Funzione" largo>
        <CampoFunzione
          etichetta="f(x) ="
          valore={testo}
          onCambia={setTesto}
          esempi={ESEMPI}
          errore={errore || (conParametri ? "Qui serve una funzione della sola x, senza altre lettere." : "")}
        />
      </Pannello>

      {dati && f && (
        <Pannello titolo="Dalla secante alla tangente" largo>
          <div className="cursori">
            <Cursore etichetta="punto x₀" valore={x0} min={-5} max={5} passo={0.05} onCambia={setX0} />
            <Cursore etichetta="incremento h" valore={h} min={0.01} max={3} passo={0.01} onCambia={setH} />
          </div>
          <Grafico
            chiave={dati.js}
            finestra={{ xmin: -6, xmax: 6 }}
            curve={[{ id: "f", f }]}
            elementi={elementi}
            descrizione={`Grafico di ${testo} con retta tangente e retta secante`}
          />
          <div className="letture">
            <div className="lettura">
              <span className="legenda legenda-secante" />
              <small>Rapporto incrementale (pendenza della secante PQ)</small>
              <Formula latex={`\\frac{f(x_0 + h) - f(x_0)}{h} = ${formatta(rapporto, 6).replace(",", "{,}")}`} />
            </div>
            <div className="lettura">
              <span className="legenda legenda-tangente" />
              <small>Derivata (pendenza della tangente in P)</small>
              <Formula latex={`f'(x_0) = ${formatta(derivata, 6).replace(",", "{,}")}`} />
            </div>
          </div>
          <p className="nota">
            Porta <strong>h</strong> verso zero: il punto Q scivola verso P, la secante si sovrappone alla tangente e il
            rapporto incrementale si avvicina alla derivata.
          </p>
        </Pannello>
      )}
    </div>
  );
}
