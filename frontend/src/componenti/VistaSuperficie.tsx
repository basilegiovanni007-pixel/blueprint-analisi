// Mostra una funzione di due variabili in due modi affiancati:
// a sinistra la superficie 3D ruotabile, a destra la mappa con le curve di livello.
import { useState } from "react";

import type { DatiSuperficie } from "../api/client";
import { COLORI_PUNTI, NOMI_PUNTI } from "../grafici/livelli";
import MappaLivello from "./MappaLivello";
import Superficie3D from "./Superficie3D";

export default function VistaSuperficie({ dati }: { dati: DatiSuperficie }) {
  const [mostraGradiente, setMostraGradiente] = useState(false);
  // Quali tipi di punto compaiono davvero (per non mostrare voci inutili nella legenda)
  const tipi = [...new Set(dati.punti.map((p) => p.tipo))];

  return (
    <div>
      <div className="superficie-coppia">
        <figure>
          <Superficie3D dati={dati} />
          <figcaption className="nota">Superficie: trascina per ruotare. Per lo zoom usa i pulsanti che compaiono in alto a destra.</figcaption>
        </figure>
        <figure>
          <MappaLivello dati={dati} mostraGradiente={mostraGradiente} />
          <figcaption className="nota">
            Curve di livello viste dall'alto: dal blu (valori bassi) al giallo (valori alti).
          </figcaption>
        </figure>
      </div>

      <div className="legenda-superficie">
        <label className="spunta">
          <input type="checkbox" checked={mostraGradiente} onChange={(e) => setMostraGradiente(e.target.checked)} />
          Mostra il campo del gradiente
        </label>
        {tipi.map((tipo) => (
          <span key={tipo} className="voce-legenda">
            <span className="pallino" style={{ background: COLORI_PUNTI[tipo] ?? "#f4f8ff" }} />
            {NOMI_PUNTI[tipo] ?? tipo}
          </span>
        ))}
        {dati.vincolo && (
          <span className="voce-legenda">
            <span className="trattino-vincolo" />
            Vincolo
          </span>
        )}
        {dati.dominio && (
          <span className="voce-legenda">
            <span className="quadretto-dominio" />
            Dominio di integrazione
          </span>
        )}
      </div>
      {mostraGradiente && (
        <p className="nota">
          Le frecce indicano la direzione in cui la funzione cresce più in fretta: sono sempre perpendicolari alle
          curve di livello e si annullano nei punti critici.
        </p>
      )}
    </div>
  );
}
