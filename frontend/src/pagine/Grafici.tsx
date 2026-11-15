// Pagina Grafici: lo studio di funzione animato e il laboratorio di visualizzazioni.
// In alto ci sono le schede per passare da uno strumento all'altro.
import { useState } from "react";

import Intestazione from "../componenti/Intestazione";
import Esplora from "../grafici/Esplora";
import Riemann from "../grafici/Riemann";
import Serie from "../grafici/Serie";
import StudioFunzione from "../grafici/StudioFunzione";
import Superfici from "../grafici/Superfici";
import Tangente from "../grafici/Tangente";
import Taylor from "../grafici/Taylor";

const STRUMENTI = [
  { chiave: "studio", nome: "Studio di funzione", descrizione: "Dominio, asintoti, massimi, minimi e flessi compaiono sul grafico una tappa alla volta.", Componente: StudioFunzione },
  { chiave: "esplora", nome: "Grafico e parametri", descrizione: "Disegna una funzione e, se contiene parametri, muovili con i cursori.", Componente: Esplora },
  { chiave: "tangente", nome: "Tangente", descrizione: "Dal rapporto incrementale alla derivata: la secante che diventa tangente.", Componente: Tangente },
  { chiave: "riemann", nome: "Somme di Riemann", descrizione: "L'integrale come somma delle aree di tanti rettangoli.", Componente: Riemann },
  { chiave: "taylor", nome: "Taylor", descrizione: "Polinomi che approssimano una funzione vicino a un punto.", Componente: Taylor },
  { chiave: "serie", nome: "Serie", descrizione: "Le somme parziali di una serie numerica, una dopo l'altra.", Componente: Serie },
  { chiave: "superfici", nome: "Superfici 3D", descrizione: "Funzioni di due variabili: superficie ruotabile, curve di livello, gradiente e punti critici.", Componente: Superfici },
];  // prettier-ignore

export default function Grafici() {
  const [scelto, setScelto] = useState("studio");
  const strumento = STRUMENTI.find((s) => s.chiave === scelto)!;
  const Componente = strumento.Componente;

  return (
    <>
      <Intestazione etichetta="Tavola 02" titolo="Grafici" descrizione={strumento.descrizione} />

      <div className="schede" role="tablist" aria-label="Strumenti grafici">
        {STRUMENTI.map((s) => (
          <button
            key={s.chiave}
            role="tab"
            aria-selected={s.chiave === scelto}
            className={"scheda-strumento" + (s.chiave === scelto ? " attiva" : "")}
            onClick={() => setScelto(s.chiave)}
          >
            {s.nome}
          </button>
        ))}
      </div>

      {/* key: cambiando scheda lo strumento riparte da zero */}
      <Componente key={scelto} />
    </>
  );
}
