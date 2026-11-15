// Strumento "Superfici": disegna una funzione di due variabili come superficie 3D e come
// mappa di curve di livello, con i punti critici colorati per tipo.
import { useMemo, useState } from "react";

import { preparaSuperficie, type DatiSuperficie } from "../api/client";
import Formula from "../componenti/Formula";
import Pannello from "../componenti/Pannello";
import VistaSuperficie from "../componenti/VistaSuperficie";
import CampoFunzione from "./CampoFunzione";
import { useRichiesta } from "./useRichiesta";

const ESEMPI = ["x^2 + y^2", "x^2 - y^2", "x^3 + y^3 - 3*x*y", "sin(x)*cos(y)", "x*y*e^(-x^2-y^2)", "x*y*(1 - x - y)"];

export default function Superfici() {
  const [testo, setTesto] = useState("x^3 + y^3 - 3*x*y");
  const { dati, errore } = useRichiesta(() => preparaSuperficie(testo), [testo], testo.trim() !== "");

  // Mettiamo i dati nella stessa forma usata dalle soluzioni del Risolutore
  const superficie: DatiSuperficie | null = useMemo(
    () =>
      dati
        ? { tipo: "superficie", funzione: dati.js, variabili: ["x", "y"], finestra: dati.finestra, punti: dati.punti, vincolo: null, dominio: null }
        : null,
    [dati],
  );

  return (
    <div className="griglia-pannelli">
      <Pannello titolo="Funzione di due variabili" largo>
        <CampoFunzione etichetta="f(x, y) =" valore={testo} onCambia={setTesto} esempi={ESEMPI} errore={errore} />
      </Pannello>

      {dati && superficie && (
        <Pannello titolo="Superficie e curve di livello" largo>
          <div className="formula-scorrevole">
            <Formula latex={`f(x, y) = ${dati.latex} \\qquad ${dati.gradiente_latex}`} />
          </div>
          <VistaSuperficie dati={superficie} />
          {dati.punti.length === 0 && (
            <p className="nota">Per questa funzione non ho trovato punti critici isolati da segnare sul grafico.</p>
          )}
        </Pannello>
      )}
    </div>
  );
}
