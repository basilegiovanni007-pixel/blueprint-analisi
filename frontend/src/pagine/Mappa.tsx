// Pagina Mappa della conoscenza: per ogni argomento mostra quanto è coperto
// dai documenti attivi del Magazzino.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";

import { leggiMappa, type Mappa as DatiMappa, type VoceMappa } from "../api/client";
import Intestazione from "../componenti/Intestazione";
import Pannello from "../componenti/Pannello";

// Una riga della mappa: nome dell'argomento, barra di copertura e cosa manca
function RigaArgomento({ voce }: { voce: VoceMappa }) {
  const percentuale = Math.round(voce.copertura * 100);
  return (
    <li className="mappa-riga">
      <div className="mappa-testa">
        <strong>{voce.argomento}</strong>
        <span className="mappa-percentuale">{percentuale}%</span>
      </div>

      {/* La barra si riempie con un'animazione fino alla percentuale di copertura */}
      <div
        className="barra-copertura"
        role="progressbar"
        aria-valuenow={percentuale}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Copertura di ${voce.argomento}`}
      >
        <motion.div
          className="barra-copertura-piena"
          initial={{ width: 0 }}
          animate={{ width: `${percentuale}%` }}
          transition={{ duration: 0.8, ease: "easeOut" }}
        />
      </div>

      <p className="nota">
        {voce.documenti === 0
          ? "Nessun documento"
          : `${voce.documenti} ${voce.documenti === 1 ? "documento" : "documenti"} · ${voce.blocchi} blocchi`}
        {voce.documenti > 0 && voce.tipi_mancanti.length > 0 && <> · manca: {voce.tipi_mancanti.join(", ")}</>}
        {voce.copertura === 1 && <> · completo ✓</>}
      </p>
    </li>
  );
}

export default function Mappa() {
  const [mappa, setMappa] = useState<DatiMappa | null>(null);
  const [errore, setErrore] = useState("");

  useEffect(() => {
    leggiMappa()
      .then(setMappa)
      .catch((e: Error) => setErrore(e.message));
  }, []);

  return (
    <>
      <Intestazione
        etichetta="Tavola 04"
        titolo="Mappa della conoscenza"
        descrizione="Gli argomenti del corso e quanto sono coperti dai documenti attivi nel tuo Magazzino."
      />

      {errore && <p className="messaggio-errore">{errore}</p>}

      <div className="griglia-pannelli">
        {mappa?.map((gruppo) => (
          <Pannello key={gruppo.corso} titolo={gruppo.corso}>
            <ul className="mappa-elenco">
              {gruppo.argomenti.map((voce) => (
                <RigaArgomento key={voce.argomento} voce={voce} />
              ))}
            </ul>
          </Pannello>
        ))}

        <Pannello titolo="Come si legge" largo>
          <p className="nota">
            Un argomento è coperto al 100% quando nel Magazzino ci sono tutti e cinque i tipi di blocco:
            definizione, teorema, metodo, esempio ed esercizio svolto. Se un tipo è stato riconosciuto male,
            puoi correggerlo dal <Link to="/magazzino">Magazzino</Link> con "Vedi blocchi".
          </p>
        </Pannello>
      </div>
    </>
  );
}
