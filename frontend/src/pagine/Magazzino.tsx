// Pagina Magazzino: carica i documenti, cercali, modificali, disattivali o eliminali.
import { useCallback, useEffect, useState } from "react";
import { AnimatePresence } from "framer-motion";

import {
  elencaDocumenti,
  leggiOpzioni,
  leggiStato,
  type Documento,
  type Opzioni,
  type StatoBackend,
} from "../api/client";
import Intestazione from "../componenti/Intestazione";
import Pannello from "../componenti/Pannello";
import RicercaMagazzino from "../componenti/RicercaMagazzino";
import SchedaDocumento from "../componenti/SchedaDocumento";
import ZonaCaricamento from "../componenti/ZonaCaricamento";

export default function Magazzino() {
  const [opzioni, setOpzioni] = useState<Opzioni | null>(null);
  const [documenti, setDocumenti] = useState<Documento[]>([]);
  const [errore, setErrore] = useState("");
  const [ricerca, setRicerca] = useState<StatoBackend["ricerca"] | null>(null);

  // Rilegge l'elenco dei documenti dal backend
  const aggiorna = useCallback(() => {
    elencaDocumenti()
      .then(setDocumenti)
      .catch((e: Error) => setErrore(e.message));
  }, []);

  // Al primo ingresso nella pagina: leggiamo opzioni ed elenco
  useEffect(() => {
    leggiOpzioni()
      .then(setOpzioni)
      .catch((e: Error) => setErrore(e.message));
    aggiorna();
  }, [aggiorna]);

  // Il modello di ricerca impiega un po' a caricarsi (la prima volta va scaricato):
  // chiediamo lo stato ogni 3 secondi finché non è pronto.
  useEffect(() => {
    let attivo = true;
    let timer: number | undefined;
    const controlla = () =>
      leggiStato()
        .then((stato) => {
          if (!attivo) return;
          setRicerca(stato.ricerca);
          if (stato.ricerca.stato !== "pronto" && stato.ricerca.stato !== "errore") {
            timer = window.setTimeout(controlla, 3000);
          }
        })
        .catch(() => {});
    controlla();
    return () => {
      attivo = false;
      window.clearTimeout(timer);
    };
  }, []);

  return (
    <>
      <Intestazione
        etichetta="Tavola 03"
        titolo="Magazzino"
        descrizione="Carica i tuoi appunti e il materiale del professore. Il risolutore userà solo ciò che trova qui dentro."
      />

      {errore && <p className="messaggio-errore">{errore}</p>}

      {ricerca && ricerca.stato !== "pronto" && (
        <p className={ricerca.stato === "errore" ? "messaggio-errore" : "messaggio-avviso"}>
          {ricerca.stato === "errore"
            ? `Il modello di ricerca non si è caricato (serve internet la prima volta). Dettaglio: ${ricerca.errore}`
            : "Sto preparando il modello di ricerca: la prima volta va scaricato (circa 220 MB), poi resta sul computer."}
        </p>
      )}

      <div className="griglia-pannelli">
        <Pannello titolo="Carica documenti" largo>
          {opzioni && <ZonaCaricamento opzioni={opzioni} onCaricato={aggiorna} />}
        </Pannello>

        <Pannello titolo="Cerca nel Magazzino" largo>
          <RicercaMagazzino />
        </Pannello>

        <Pannello titolo={`Documenti (${documenti.length})`} largo>
          {documenti.length === 0 ? (
            <p className="nota">Il Magazzino è vuoto. Carica il primo documento qui sopra.</p>
          ) : (
            <div className="elenco-schede">
              <AnimatePresence>
                {opzioni &&
                  documenti.map((documento) => (
                    <SchedaDocumento
                      key={documento.id}
                      documento={documento}
                      opzioni={opzioni}
                      onCambiato={aggiorna}
                    />
                  ))}
              </AnimatePresence>
            </div>
          )}
        </Pannello>
      </div>
    </>
  );
}
