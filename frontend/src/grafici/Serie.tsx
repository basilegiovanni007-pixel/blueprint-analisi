// Somme parziali di una serie numerica: S_N = a_1 + a_2 + ... + a_N.
// Se i punti (N, S_N) si avvicinano a un valore, la serie converge a quel valore.
import { useMemo, useState } from "react";

import { preparaSerie } from "../api/client";
import Formula from "../componenti/Formula";
import Grafico, { type Elemento } from "../componenti/Grafico";
import Pannello from "../componenti/Pannello";
import CampoFunzione from "./CampoFunzione";
import Cursore from "./Cursore";
import { compila, formatta } from "./calcolo";
import { useRichiesta } from "./useRichiesta";

const ESEMPI = ["1/n^2", "1/n", "(1/2)^n", "(-1)^n/n", "1/(n*(n+1))"];

export default function Serie() {
  const [testo, setTesto] = useState("1/n^2");
  const [quanti, setQuanti] = useState(20); // quanti termini sommiamo

  const { dati, errore } = useRichiesta(() => preparaSerie(testo, 1), [testo], testo.trim() !== "");
  const termine = useMemo(() => (dati ? compila(dati.termine.js, "n") : null), [dati]);

  // Calcoliamo le somme parziali S_1, S_2, ..., S_N
  const somme = useMemo(() => {
    const risultato: { n: number; s: number }[] = [];
    if (termine && dati) {
      let totale = 0;
      for (let n = dati.inizio; n < dati.inizio + quanti; n++) {
        totale += termine(n);
        if (!Number.isFinite(totale)) break;
        risultato.push({ n, s: totale });
      }
    }
    return risultato;
  }, [termine, dati, quanti]);

  const ultima = somme.length > 0 ? somme[somme.length - 1] : null;

  const elementi: Elemento[] = somme.map(({ n, s }) => ({ tipo: "punto", x: n, y: s, stile: "piccolo" }));
  if (dati?.somma != null) {
    elementi.unshift({ tipo: "orizzontale", y: dati.somma, etichetta: "somma della serie" });
  }

  // Scala verticale: deve contenere tutte le somme parziali (e la somma, se nota)
  const valori = somme.map((p) => p.s).concat(dati?.somma != null ? [dati.somma] : [], [0]);
  const basso = Math.min(...valori);
  const alto = Math.max(...valori);
  const margine = (alto - basso || 1) * 0.15;

  const carattere =
    dati?.converge === true ? "La serie converge." : dati?.converge === false ? "La serie non converge." : "Non sono riuscito a stabilire se la serie converge.";

  return (
    <div className="griglia-pannelli">
      <Pannello titolo="Termine generale della serie" largo>
        <CampoFunzione etichetta="aₙ =" valore={testo} onCambia={setTesto} esempi={ESEMPI} errore={errore} />
      </Pannello>

      {dati && ultima && (
        <Pannello titolo="Somme parziali" largo>
          <div className="cursori">
            <Cursore etichetta="numero di termini N" valore={quanti} min={1} max={200} passo={1} onCambia={setQuanti} />
          </div>
          <Grafico
            chiave={`${dati.termine.js}|${quanti}`}
            finestra={{ xmin: -quanti * 0.04, xmax: dati.inizio + quanti * 1.04, ymin: basso - margine, ymax: alto + margine }}
            curve={[]}
            elementi={elementi}
            descrizione={`Somme parziali della serie di termine ${testo}`}
          />
          <div className="letture">
            <div className="lettura">
              <small>Serie</small>
              <div className="formula-scorrevole">
                <Formula latex={dati.serie_latex + (dati.somma_latex ? ` = ${dati.somma_latex}` : "")} />
              </div>
            </div>
            <div className="lettura">
              <small>Somma dei primi {somme.length} termini</small>
              <Formula latex={`S_{${ultima.n}} = ${formatta(ultima.s, 7).replace(",", "{,}")}`} />
            </div>
            {dati.somma != null && (
              <div className="lettura">
                <small>Distanza dalla somma</small>
                <Formula latex={formatta(Math.abs(dati.somma - ultima.s), 4).replace(",", "{,}")} />
              </div>
            )}
          </div>
          <p className="nota">
            {carattere} Ogni punto è una somma parziale: aumenta N e guarda se i punti si stabilizzano.
          </p>
        </Pannello>
      )}
    </div>
  );
}
